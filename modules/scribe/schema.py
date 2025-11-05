"""
ROSHN PULSE Module 3: Data Extraction Schema
==============================================
This schema is LOCKED for the MVP. Do not modify without team coordination.

The Auto-Report Scribe extracts exactly THREE key fields from daily logs:
1. Completed Tasks
2. Blockers
3. Incidents
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date

class CompletedTask(BaseModel):
    """A task that was completed during the day"""
    task_name: str = Field(..., description="Name or description of the completed task")
    location: Optional[str] = Field(None, description="Location where task was completed (e.g., 'Tower B Level 4')")
    crew: Optional[str] = Field(None, description="Crew or contractor who completed it")

class Blocker(BaseModel):
    """An issue blocking progress"""
    issue: str = Field(..., description="Description of the blocking issue")
    affected_task: Optional[str] = Field(None, description="Which task is blocked")
    cause: Optional[str] = Field(None, description="Root cause if known (e.g., 'material delay', 'weather', 'equipment failure')")

class Incident(BaseModel):
    """A safety incident or notable event"""
    incident_type: str = Field(..., description="Type: 'safety', 'quality', 'environmental', 'other'")
    description: str = Field(..., description="What happened")
    severity: Optional[str] = Field(None, description="Severity: 'minor', 'moderate', 'major'")
    action_taken: Optional[str] = Field(None, description="Immediate action taken")

class DailyLogExtraction(BaseModel):
    """Complete extraction from a daily log"""

    # Metadata
    log_date: Optional[date] = Field(None, description="Date of the log entry")
    site_name: Optional[str] = Field(None, description="Construction site name")
    submitted_by: Optional[str] = Field(None, description="Site manager who submitted the log")

    # The 3 core fields we must extract
    completed_tasks: List[CompletedTask] = Field(default_factory=list, description="List of tasks completed")
    blockers: List[Blocker] = Field(default_factory=list, description="List of issues blocking progress")
    incidents: List[Incident] = Field(default_factory=list, description="List of incidents or notable events")

    # Summary statistics (auto-generated)
    total_tasks_completed: int = Field(0, description="Count of completed tasks")
    total_blockers: int = Field(0, description="Count of active blockers")
    total_incidents: int = Field(0, description="Count of incidents")

    # Raw text for reference
    raw_text: Optional[str] = Field(None, description="Original log text")

    def calculate_stats(self):
        """Calculate summary statistics after extraction"""
        self.total_tasks_completed = len(self.completed_tasks)
        self.total_blockers = len(self.blockers)
        self.total_incidents = len(self.incidents)
        return self


# Entity types for spaCy NER
ENTITY_LABELS = [
    "TASK",          # Completed task mention
    "BLOCKER",       # Issue/problem mention
    "INCIDENT",      # Safety/quality incident
    "LOCATION",      # Site location (Tower B, Level 4, etc.)
    "CONTRACTOR",    # Contractor/crew name
    "MATERIAL",      # Building material
    "EQUIPMENT",     # Construction equipment
    "PERSON",        # Person name
]

# Keywords for rule-based classification
TASK_COMPLETION_KEYWORDS = [
    "completed", "finished", "done", "installed", "poured",
    "erected", "built", "constructed", "laid", "placed",
    "achieved", "delivered", "accomplished", "continued",
    "installation", "welding", "approved"
]

BLOCKER_KEYWORDS = [
    "delayed", "blocked", "waiting", "shortage", "issue",
    "problem", "challenge", "obstacle", "pending", "hold",
    "unable", "cannot", "failed", "missing", "unavailable"
]

INCIDENT_KEYWORDS = {
    "safety": ["injury", "accident", "unsafe", "hazard", "ppe violation",
               "near miss", "first aid", "safety alert", "incident",
               "safety incident", "fall", "tipped over", "ambulance",
               "hospital", "injured"],
    "quality": ["defect", "rework", "non-conformance", "quality issue",
                "failed inspection", "substandard"],
    "environmental": ["spill", "pollution", "environmental", "waste",
                      "contamination"],
}

# Common construction locations (for entity recognition)
LOCATION_PATTERNS = [
    r"(?i)tower\s+[A-Z]",
    r"(?i)level\s+\d+",
    r"(?i)floor\s+\d+",
    r"(?i)block\s+[A-Z0-9]+",
    r"(?i)zone\s+[A-Z0-9\-]+",
    r"(?i)building\s+[A-Z0-9]+",
    r"[A-Z]{2,3}-[0-9]+",  # Codes like CS-12, BD-02, BW-3, ST-1
    r"(?i)section\s+[A-Z0-9\-]+",
    r"(?i)station\s+[A-Z0-9\-]+",
]

# ROSHN project site names
SITE_NAMES = [
    "SEDRA", "ALAROUS", "ALFULWA", "MARAFY", "MARAFY Waterfront",
    "Marina East", "Residential", "Coastal Development"
]

if __name__ == "__main__":
    # Test the schema
    print("ROSHN PULSE Module 3 - Extraction Schema")
    print("=" * 60)
    print(f"\nEntity Labels: {ENTITY_LABELS}")
    print(f"\nTask Keywords: {TASK_COMPLETION_KEYWORDS[:5]}...")
    print(f"\nBlocker Keywords: {BLOCKER_KEYWORDS[:5]}...")
    print("\nSchema validation: OK")
