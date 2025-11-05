from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field


# === Common ===
class Message(BaseModel):
    message: str


# === Brain ===
class RiskContributor(BaseModel):
    feature: str
    impact: float


class BrainPredictIn(BaseModel):
    # Flexible payload: {"features": {...}}
    features: Dict[str, float] = Field(default_factory=dict)


class BrainPredictOut(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_band: str  # "Low" | "Medium" | "High"
    top_contributors: List[RiskContributor]


class BrainWhatIfIn(BaseModel):
    features: Dict[str, float] = Field(default_factory=dict)
    deltas: Dict[str, float] = Field(default_factory=dict)


class BrainWhatIfOut(BaseModel):
    baseline: BrainPredictOut
    scenario: BrainPredictOut


# === Vision ===
class VisionDetection(BaseModel):
    cls: str
    bbox: Tuple[float, float, float, float]
    conf: float


class VisionOut(BaseModel):
    detections: List[VisionDetection]
    persons: int
    helmeted_persons: int
    compliance_rate: float = Field(ge=0.0, le=1.0)
    overlay_url: Optional[str] = None


# === Scribe ===
class Issue(BaseModel):
    type: str
    summary: str


class ScribeOut(BaseModel):
    date: Optional[str] = None
    project: Optional[str] = None
    location: Optional[str] = None
    subcontractors: List[str] = Field(default_factory=list)
    personnel_count: Optional[int] = None
    completed_tasks: List[str] = Field(default_factory=list)
    issues: List[Issue] = Field(default_factory=list)
    safety_observations: List[str] = Field(default_factory=list)
    low_confidence: bool = False
    confidence: Dict[str, float] = Field(default_factory=dict)
    export_csv_url: Optional[str] = None
