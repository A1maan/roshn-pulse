"""
ROSHN PULSE Module 3: Core NLP Extraction Engine
=================================================
Extracts structured data from construction daily logs

Extracts 3 key fields:
1. Completed Tasks
2. Blockers
3. Incidents
"""

import spacy
import re
from datetime import datetime
from typing import List, Dict, Tuple
from schema import (
    DailyLogExtraction,
    CompletedTask,
    Blocker,
    Incident,
    TASK_COMPLETION_KEYWORDS,
    BLOCKER_KEYWORDS,
    INCIDENT_KEYWORDS,
    LOCATION_PATTERNS,
    SITE_NAMES
)


class DailyLogExtractor:
    """
    Extracts structured information from construction daily logs
    using spaCy NLP and rule-based patterns
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize the extractor with spaCy model"""
        try:
            self.nlp = spacy.load(model_name)
            print(f"[OK] Loaded spaCy model: {model_name}")
        except OSError:
            print(f"[ERROR] Model '{model_name}' not found.")
            print("Please run: python -m spacy download en_core_web_sm")
            raise

    def extract_from_text(self, text: str) -> DailyLogExtraction:
        """
        Main extraction method - processes raw text and returns structured data

        Args:
            text: Raw daily log text

        Returns:
            DailyLogExtraction object with all extracted fields
        """

        # Initialize extraction result
        extraction = DailyLogExtraction(raw_text=text)

        # Extract metadata from header
        extraction.log_date = self._extract_date(text)
        extraction.site_name = self._extract_site_name(text)
        extraction.submitted_by = self._extract_manager_name(text)

        # Process text with spaCy
        doc = self.nlp(text)

        # Split into sentences for analysis
        sentences = list(doc.sents)

        # Extract the 3 core fields
        # IMPORTANT: Extract incidents FIRST to prevent misclassification as blockers
        extraction.incidents = self._extract_incidents(sentences, doc)

        # Get sentence indices that are already classified as incidents
        incident_sentences = set(inc.description for inc in extraction.incidents)

        extraction.completed_tasks = self._extract_tasks(sentences, doc)
        extraction.blockers = self._extract_blockers(sentences, doc, incident_sentences)

        # Calculate statistics
        extraction.calculate_stats()

        return extraction

    def _extract_date(self, text: str) -> datetime.date:
        """Extract date from log header"""
        # Look for patterns like "Date: 15/10/2025" or "October 15, 2025"
        patterns = [
            r"Date:\s*(\d{1,2}/\d{1,2}/\d{4})",
            r"Date:\s*(\d{1,2}-\d{1,2}-\d{4})",
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try different parsing formats
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %B %Y"]:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
        return None

    def _extract_site_name(self, text: str) -> str:
        """Extract project/site name"""
        # First check if any known ROSHN site names appear in the text
        for site_name in SITE_NAMES:
            if site_name.lower() in text.lower():
                return site_name

        # Look for project name in header patterns
        patterns = [
            r"(?:Project|Site):\s*(.+?)(?:\n|$)",
            r"^(.+?)\s*(?:Daily|Site)\s*(?:Report|Log)",
            r"(?:Daily|Site)\s+(?:Report|Log)\s*[-:]\s*(.+?)(?:\n|Date)",
            r"Report\s*[-:]\s*(.+?)(?:\n|Date)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                site = match.group(1).strip()
                if len(site) > 3:  # Minimum sensible length
                    return site
        return None

    def _extract_manager_name(self, text: str) -> str:
        """Extract site manager name"""
        patterns = [
            r"(?:Site\s+Manager|Logged\s+by|Manager|Reporting\s+Officer|Supervisor):\s*([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z-]+)+)",
            r"by:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z-]+)+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_tasks(self, sentences, doc) -> List[CompletedTask]:
        """Extract completed tasks from text"""
        tasks = []

        for sent in sentences:
            sent_text = sent.text.lower()

            # Skip very short sentences that are likely continuations
            if len(sent.text.strip()) < 25:
                continue

            # Skip metadata headers
            if sent_text.strip() in ["progress achieved:", "incidents and issues:"]:
                continue

            # Check if sentence contains task completion keywords
            has_completion_keyword = any(kw in sent_text for kw in TASK_COMPLETION_KEYWORDS)

            if has_completion_keyword:
                # Skip sentences that are just measurements/summaries
                if sent_text.strip().startswith(('total ', 'only ')):
                    continue

                # Skip if it's just a standalone quantity sentence (no context)
                if re.match(r'^(completed|total|only)\s+\d+', sent_text.strip()):
                    continue

                # Skip crew count metadata
                if "crew count" in sent_text:
                    continue

                # Extract task details
                task = CompletedTask(
                    task_name=sent.text.strip(),
                    location=self._extract_location_from_span(sent),
                    crew=self._extract_crew_name(sent.text)
                )
                tasks.append(task)

            # Also check for bullet points with work items
            if sent_text.startswith('-') or sent_text.startswith('•'):
                # This is likely a task item
                clean_text = sent_text.lstrip('-•').strip()
                if len(clean_text) > 10:  # Minimum reasonable task description
                    task = CompletedTask(
                        task_name=sent.text.strip(),
                        location=self._extract_location_from_span(sent),
                        crew=self._extract_crew_name(sent.text)
                    )
                    tasks.append(task)

        return tasks

    def _extract_blockers(self, sentences, doc, incident_sentences=None) -> List[Blocker]:
        """Extract blocking issues from text"""
        blockers = []
        if incident_sentences is None:
            incident_sentences = set()

        for sent in sentences:
            sent_text = sent.text.lower()

            # Skip if this sentence is already classified as an incident
            if sent.text.strip() in incident_sentences:
                continue

            # Skip if sentence contains strong incident indicators
            if any(indicator in sent_text for indicator in ["incident", "safety incident", "accident", "injury", "injured", "tipped over", "fall", "fell"]):
                continue

            # Skip incident-related investigation/inspection sentences
            if ("inspected" in sent_text or "inspection" in sent_text) and any(word in sent_text for word in ["lift", "platform", "failed", "ground"]):
                continue

            # Check for blocker keywords
            has_blocker_keyword = any(kw in sent_text for kw in BLOCKER_KEYWORDS)

            if has_blocker_keyword:
                # Determine the cause category
                cause = None
                if any(word in sent_text for word in ['material', 'supply', 'delivery', 'shortage', 'steel', 'concrete', 'rebar']):
                    cause = "material_delay"
                elif any(word in sent_text for word in ['equipment', 'crane', 'machine']):
                    cause = "equipment_failure"
                elif any(word in sent_text for word in ['weather', 'rain', 'wind', 'storm']):
                    cause = "weather"
                elif any(word in sent_text for word in ['approval', 'permit']):
                    cause = "approval_delay"

                blocker = Blocker(
                    issue=sent.text.strip(),
                    affected_task=None,  # Could be enhanced to extract this
                    cause=cause
                )
                blockers.append(blocker)

        return blockers

    def _extract_incidents(self, sentences, doc) -> List[Incident]:
        """Extract incidents from text"""
        incidents = []
        text = doc.text

        # Look for incident header patterns (like "SAFETY INCIDENT - MAJOR:")
        # Match from "SAFETY INCIDENT" until we hit a paragraph break or blocker section
        incident_header_pattern = r"\bSAFETY\s+INCIDENT\b[\s\-:]*(\w+)?:?\s*(.+?)(?=\n\n(?:Additionally|Crew count)|\Z)"
        matches = list(re.finditer(incident_header_pattern, text, re.IGNORECASE | re.DOTALL))

        # De-duplicate: Remove matches that are just section headers without content
        final_matches = []
        for match in matches:
            match_text = match.group(0).strip()

            # Skip if it's just the header line with minimal description
            # A real incident should have at least 80 characters
            if len(match_text) < 80:
                continue

            # Check if this match is a substring of another match
            is_duplicate = False
            for other_match in matches:
                if match != other_match:
                    if match_text in other_match.group(0) and len(match_text) < len(other_match.group(0)):
                        is_duplicate = True
                        break

            if not is_duplicate:
                final_matches.append(match)

        for match in final_matches:
            incident_block = match.group(0)
            severity_match = match.group(1)

            # Determine severity from header or content
            severity = "minor"
            if severity_match and severity_match.lower() == "major":
                severity = "major"
            elif any(word in incident_block.lower() for word in ['major', 'serious', 'severe', 'critical']):
                severity = "major"
            elif any(word in incident_block.lower() for word in ['moderate', 'significant']):
                severity = "moderate"

            # Extract action taken
            action_taken = self._extract_action_taken(incident_block)

            incident = Incident(
                incident_type="safety",
                description=incident_block.strip(),
                severity=severity,
                action_taken=action_taken
            )
            incidents.append(incident)

        # Also check sentence-by-sentence for incidents not caught by headers
        for sent in sentences:
            sent_text = sent.text.lower()

            # Skip if already part of a detected incident block
            if any(sent.text.strip() in inc.description for inc in incidents):
                continue

            # Skip generic headers or metadata
            if sent_text.strip() in ["incidents and issues:", "incidents:", "incident and issues"]:
                continue
            if "crew count" in sent_text or "operations continue" in sent_text:
                continue

            # Skip if sentence contains "SAFETY INCIDENT" (these should be caught by block detection)
            if "safety incident" in sent_text or "incident -" in sent_text:
                continue

            # Check each incident category
            for incident_type, keywords in INCIDENT_KEYWORDS.items():
                if any(kw in sent_text for kw in keywords):

                    # Determine severity
                    severity = "minor"
                    if any(word in sent_text for word in ['major', 'serious', 'severe', 'critical']):
                        severity = "major"
                    elif any(word in sent_text for word in ['moderate', 'significant']):
                        severity = "moderate"

                    incident = Incident(
                        incident_type=incident_type,
                        description=sent.text.strip(),
                        severity=severity,
                        action_taken=self._extract_action_taken(sent.text)
                    )
                    incidents.append(incident)
                    break  # Only classify as one type

        return incidents

    def _extract_location_from_span(self, span) -> str:
        """Extract location mentions from a text span"""
        text = span.text

        # Try to find location patterns
        for pattern in LOCATION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        # Also check for named entities that might be locations
        for ent in span.ents:
            if ent.label_ in ['GPE', 'LOC', 'FAC']:  # Geopolitical, Location, Facility
                return ent.text

        return None

    def _extract_crew_name(self, text: str) -> str:
        """Extract contractor/crew name from text"""
        # Common crew name patterns
        crew_patterns = [
            r"(?:by|from|contractor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z-]+)*)\s+(?:crew|team|contractor)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z-]+)*)\s+(?:crew|team|contractor)",
        ]

        for pattern in crew_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_action_taken(self, text: str) -> str:
        """Extract action taken from incident description"""
        # Look for action phrases
        action_patterns = [
            r"(?:Ambulance|First aid|treatment|medical attention)\s+(.+?)(?:\.|$)",
            r"(?:action|response):\s*(.+?)(?:\.|$)",
            r"worker\s+(?:transported|taken)\s+to\s+[\w\s]+(?:Hospital|Medical|Clinic)",
            r"(?:suspended|stopped|halted)\s+(?:all|the)?\s*[\w\s]+(?:operations|work|activities)",
            r"(?:investigation|team|manager|officer)\s+(?:formed|notified|dispatched|en route)",
        ]

        actions = []
        for pattern in action_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                actions.append(match.group(0).strip())

        if actions:
            return "; ".join(actions)
        return None


def test_extractor():
    """Test the extractor on sample logs"""
    import glob

    print("\n" + "=" * 80)
    print("TESTING NLP EXTRACTOR")
    print("=" * 80)

    extractor = DailyLogExtractor()

    # Test on first few sample logs
    log_files = sorted(glob.glob("data/sample_logs/log_*.txt"))[:3]

    for log_file in log_files:
        print(f"\n[TESTING] {log_file}")
        print("-" * 80)

        with open(log_file, 'r', encoding='utf-8') as f:
            text = f.read()

        result = extractor.extract_from_text(text)

        print(f"Date: {result.log_date}")
        print(f"Site: {result.site_name}")
        print(f"Manager: {result.submitted_by}")
        print(f"\nCompleted Tasks: {result.total_tasks_completed}")
        for task in result.completed_tasks[:3]:  # Show first 3
            print(f"  - {task.task_name[:80]}...")
        print(f"\nBlockers: {result.total_blockers}")
        for blocker in result.blockers:
            print(f"  - {blocker.issue[:80]}...")
        print(f"\nIncidents: {result.total_incidents}")
        for incident in result.incidents:
            print(f"  - [{incident.incident_type}] {incident.description[:60]}...")


if __name__ == "__main__":
    test_extractor()
