from typing import Dict, List, Optional
from uuid import uuid4
import datetime as dt
import csv
import io
import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from core.config import settings
from core.schemas import Issue, ScribeOut

router = APIRouter()


# === Helpers ===
def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Try PyPDF2 first (fast), fall back to pdfminer.six if needed.
    """
    # PyPDF2
    try:
        import PyPDF2  # type: ignore

        text_parts: List[str] = []
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts)
        if text.strip():
            return text
    except Exception:
        pass

    # pdfminer.six fallback
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        with io.BytesIO(pdf_bytes) as f:
            text = extract_text(f)
            if text and text.strip():
                return text
    except Exception:
        pass

    return ""


DATE_RX = re.compile(
    r"\b(20\d{2}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])|"
    r"(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2}))\b"
)
INT_RX = re.compile(r"\b(\d{1,5})\b", re.MULTILINE)


def _basic_extract(text: str) -> ScribeOut:
    """
    Lightweight rule-based extractor with confidences.
    Replace/augment with spaCy NER when model is available.
    """
    fields_conf: Dict[str, float] = {}

    # Date
    date_match = DATE_RX.search(text)
    date_val: Optional[str] = None
    if date_match:
        fields_conf["date"] = 0.9
        raw = date_match.group(0)
        # Normalize to ISO if possible
        try:
            # Try YYYY/MM/DD or YYYY-MM-DD
            if re.match(r"^20\d{2}[-/]", raw):
                sep = "-" if "-" in raw else "/"
                y, m, d = raw.split(sep)
                date_val = dt.date(int(y), int(m), int(d)).isoformat()
            else:
                # DD/MM/YYYY
                sep = "-" if "-" in raw else "/"
                d, m, y = raw.split(sep)
                date_val = dt.date(int(y), int(m), int(d)).isoformat()
        except Exception:
            date_val = raw
    else:
        fields_conf["date"] = 0.2

    # Personnel count (first small-ish integer hint)
    personnel = None
    m = INT_RX.search(text)
    if m:
        try:
            personnel = int(m.group(1))
            fields_conf["personnel_count"] = 0.6
        except Exception:
            fields_conf["personnel_count"] = 0.2
    else:
        fields_conf["personnel_count"] = 0.2

    # Subcontractors (very naive: lines with "Contractor" or "Subcontractor")
    subs: List[str] = []
    for line in text.splitlines():
        if "contractor" in line.lower():
            # keep short chunks
            piece = line.strip()
            if 3 <= len(piece) <= 80:
                subs.append(piece)
    subs = subs[:5]
    fields_conf["subcontractors"] = 0.5 if subs else 0.2

    # Completed tasks / issues (naive keyword split)
    completed_tasks: List[str] = []
    issues: List[Issue] = []
    safety: List[str] = []

    for para in re.split(r"\n\s*\n", text):
        pl = para.lower()
        if any(k in pl for k in ["completed", "finished", "achieved", "done"]):
            completed_tasks.append(para.strip())
        if any(k in pl for k in ["delay", "blocked", "issue", "problem", "shortage"]):
            issues.append(Issue(type="delay" if "delay" in pl else "issue", summary=para.strip()))
        if any(k in pl for k in ["safety", "ppe", "incident", "hazard", "near miss", "near-miss"]):
            safety.append(para.strip())

    fields_conf["completed_tasks"] = 0.6 if completed_tasks else 0.2
    fields_conf["issues"] = 0.6 if issues else 0.2
    fields_conf["safety_observations"] = 0.6 if safety else 0.2

    low_conf = any(v <= 0.25 for v in fields_conf.values())

    return ScribeOut(
        date=date_val,
        project=None,
        location=None,
        subcontractors=subs,
        personnel_count=personnel,
        completed_tasks=completed_tasks[:5],
        issues=issues[:5],
        safety_observations=safety[:5],
        low_confidence=low_conf,
        confidence=fields_conf,
    )


def _write_csv(out: ScribeOut) -> str:
    """
    Save a compact CSV snapshot and return a relative URL to download it.
    """
    name = f"{uuid4().hex}.csv"
    path = (settings.exports_dir / name).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["field", "value"])
        w.writerow(["date", out.date or ""])
        w.writerow(["personnel_count", out.personnel_count or ""])
        w.writerow(["subcontractors", "; ".join(out.subcontractors)])
        w.writerow(["completed_tasks", " | ".join(out.completed_tasks)])
        w.writerow(["issues", " | ".join([i.summary for i in out.issues])])
        w.writerow(["safety_observations", " | ".join(out.safety_observations)])

    rel = f"/exports/scribe/{name}"
    return rel


@router.post("/extract", response_model=ScribeOut)
async def extract(
    request: Request,
    file: Optional[UploadFile] = File(None),
    text_form: Optional[str] = Form(None),
):
    """
    Accepts:
      1) multipart/form-data with 'file' (PDF)
      2) JSON: {"text": "..."}     (application/json)
      3) multipart/form-data with 'text' field
      4) text/plain raw body
    """
    extracted_text: Optional[str] = None

    try:
        # Case 1: PDF file upload
        if file is not None:
            content = await file.read()
            extracted_text = _extract_text_from_pdf_bytes(content)
        else:
            # Case 2: multipart form field 'text'
            if text_form and text_form.strip():
                extracted_text = text_form

            ct = (request.headers.get("content-type") or "").lower()

            # Case 3: JSON body field 'text' (plus a few aliases)
            if extracted_text is None and "application/json" in ct:
                try:
                    payload = await request.json()
                except Exception:
                    payload = None

                if isinstance(payload, dict):
                    for key in ("text", "content", "raw_text"):
                        value = payload.get(key)
                        if isinstance(value, str) and value.strip():
                            extracted_text = value
                            break
                elif isinstance(payload, str) and payload.strip():
                    extracted_text = payload

            # Case 4: raw text/plain
            if extracted_text is None and ct.startswith("text/plain"):
                raw = await request.body()
                candidate = raw.decode("utf-8", errors="ignore")
                if candidate.strip():
                    extracted_text = candidate

        if not extracted_text or not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Provide a PDF file or raw text.")

        out = _basic_extract(extracted_text)
        out.export_csv_url = _write_csv(out)
        return out

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction failed: {e}")
