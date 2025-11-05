from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from uuid import uuid4
from pathlib import Path
import io

import numpy as np

from core.config import settings
from core.schemas import VisionOut, VisionDetection

# Try to import ultralytics lazily
_yolo = None
_ultra_ok = None


def _lazy_yolo():
    global _yolo, _ultra_ok
    if _ultra_ok is not None:
        return
    try:
        from ultralytics import YOLO  # type: ignore
        weights_path = (settings.base_dir / settings.vision_weights).resolve()
        _yolo = YOLO(str(weights_path))
        _ultra_ok = True
    except Exception as e:
        _yolo = None
        _ultra_ok = False
        raise RuntimeError(f"Failed to load YOLO weights: {e}")


router = APIRouter()


def _save_overlay_image(result, out_path: Path):
    """
    Uses Ultralytics built-in plotting to produce an annotated image.
    """
    try:
        plotted = result.plot()  # returns a numpy array (H, W, 3) BGR
        # We must save it ourselves without assuming cv2 import availability.
        from PIL import Image  # pillow
        img = Image.fromarray(plotted[..., ::-1])  # BGR->RGB
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="JPEG", quality=90)
    except Exception as e:
        raise RuntimeError(f"Failed to save overlay: {e}")


@router.post("/analyze-image", response_model=VisionOut)
async def analyze_image(file: UploadFile = File(...)):
    _lazy_yolo()

    if not _ultra_ok or _yolo is None:
        raise HTTPException(status_code=500, detail="Vision model not available")

    # 1) Basic content-type/extension validation
    ct = (file.content_type or "").lower()
    allowed_ct = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"}
    if ct and ct not in allowed_ct:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image content-type '{ct}'. Allowed: {', '.join(sorted(allowed_ct))}",
        )

    try:
        content = await file.read()

        # 2) Try Pillow → NumPy array first
        img_np = None
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(io.BytesIO(content))
            # Some formats may be RGBA/LA; convert to RGB
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img_np = np.array(img)
        except Exception as e:
            img_np = None  # will try fallback
            # (do not raise yet, we’ll try a path-based fallback)

        # 3) Run YOLO either on NumPy array or a temp file with extension
        if img_np is not None:
            results = _yolo.predict(source=img_np, conf=0.2, iou=0.45, verbose=False)
        else:
            # Fallback: write a temp file with the right extension (or .jpg)
            suffix = ".jpg"
            if file.filename:
                lower = file.filename.lower()
                if lower.endswith((".jpeg", ".jpg", ".png", ".webp", ".bmp")):
                    suffix = "." + lower.rsplit(".", 1)[-1]
            tmp_path = (settings.base_dir / f"_tmp_{uuid4().hex}{suffix}").resolve()
            with open(tmp_path, "wb") as f:
                f.write(content)
            try:
                results = _yolo.predict(source=str(tmp_path), conf=0.25, iou=0.45, verbose=False)
            finally:
                # Best effort cleanup
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

        if not results:
            raise HTTPException(status_code=400, detail="No results returned by model")

        result = results[0]
        names = result.names  # class index -> name
        det_list: List[VisionDetection] = []

        persons = 0
        hardhat = 0
        no_hardhat = 0

        if result.boxes is not None and len(result.boxes) > 0:
            xyxy = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            clss = result.boxes.cls.cpu().numpy().astype(int)

            for i in range(len(clss)):
                cls_name = names.get(int(clss[i]), str(clss[i]))
                x1, y1, x2, y2 = xyxy[i]
                det_list.append(
                    VisionDetection(
                        cls=cls_name,
                        bbox=(float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
                        conf=float(confs[i]),
                    )
                )
                # Adjust these label strings if your model uses different naming
                if cls_name.lower() == "person":
                    persons += 1
                elif cls_name.lower() in {"hardhat", "helmet", "helmet-on", "helmet_on"}:
                    hardhat += 1
                elif cls_name.lower() in {"no-hardhat", "no_helmet", "no-helmet"}:
                    no_hardhat += 1

        denom = max(1, hardhat + no_hardhat)
        compliance_rate = float(hardhat / denom)

        # Save overlay image
        overlay_name = f"{uuid4().hex}.jpg"
        overlay_path = (settings.overlays_dir / overlay_name).resolve()
        _save_overlay_image(result, overlay_path)
        overlay_rel = f"/static/overlays/{overlay_name}"

        return VisionOut(
            detections=det_list,
            persons=persons,
            helmeted_persons=hardhat,
            compliance_rate=round(compliance_rate, 4),
            overlay_url=overlay_rel,
        )

    except HTTPException:
        raise
    except Exception as e:
        # More actionable message than Ultralytics default
        raise HTTPException(
            status_code=400,
            detail=f"Vision inference failed: {e}"
        )
