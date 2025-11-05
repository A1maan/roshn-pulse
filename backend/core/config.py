# backend/core/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


def _env_list(name: str, default: List[str]) -> List[str]:
    """Read comma-separated list from env, fallback to default."""
    raw = os.getenv(name)
    if not raw:
        return default
    return [s.strip() for s in raw.split(",") if s.strip()]


class Settings(BaseSettings):
    # Server
    backend_port: int = Field(8000, alias="BACKEND_PORT")

    # CORS (comma-separated in env)
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Paths (relative to backend/)
    base_dir: Path = Path(__file__).resolve().parents[1]
    static_dir: Path = base_dir / "static"
    overlays_dir: Path = static_dir / "overlays"
    exports_dir: Path = base_dir / "exports" / "scribe"

    # Vision
    vision_weights: Path = Field(default=Path("../modules/vision/weights/best.pt"), alias="VISION_WEIGHTS")
    vision_class_map_path: Path = Field(default=Path("../modules/vision/class_map.yaml"), alias="VISION_CLASS_MAP")

    # Brain
    brain_model_path: Path = Field(default=Path("../modules/brain/artifacts/brain_planning_component_model.pkl"), alias="BRAIN_MODEL")
    brain_schema_path: Path = Field(default=Path("../modules/brain/artifacts/preprocess_schema.json"), alias="BRAIN_SCHEMA")

    # Scribe
    scribe_model_dir: Path = Field(default=Path("../modules/scribe/models"), alias="SCRIBE_MODEL_DIR")

    class Config:
        # Allow environment variables in either style (alias or field name)
        populate_by_name = True

    def load_env_overrides(self) -> None:
        # Let CORS_ORIGINS be a comma-separated string
        self.cors_origins = _env_list("CORS_ORIGINS", self.cors_origins)


settings = Settings()
settings.load_env_overrides()

# Ensure directories exist at import time
settings.static_dir.mkdir(parents=True, exist_ok=True)
settings.overlays_dir.mkdir(parents=True, exist_ok=True)
settings.exports_dir.mkdir(parents=True, exist_ok=True)
