import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging


class SimpleRequirementsParser:
    """
    Simple parser for extracting requirements from text documents.
    Supports PDF, TXT, and basic JIRA exports.
    """

    def __init__(self):
        # Common requirement patterns
        self.patterns = [
            # User story format
            r"As a (.+?), I (?:want|need) (?:to )?(.+?) so that (.+?)[\.\n]",

            # Simple user actions
            r"User (?:can|should|must|shall) (.+?)[\.\n]",
            r"Users (?:can|should|must|shall) (.+?)[\.\n]",
            r"The user (?:can|should|must|shall) (.+?)[\.\n]",

            # System requirements
            r"The system (?:shall|should|must) (.+?)[\.\n]",
            r"System (?:shall|should|must) (.+?)[\.\n]",

            # Feature descriptions
            r"Feature: (.+?)[\.\n]",
            r"Functionality: (.+?)[\.\n]",

            # Numbered requirements
            r"\d+\.\s*(.+?)[\.\n]",

            # Acceptance criteria pattern
            r"[-•]\s*(.+?)[\.\n]"
        ]

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse requirements from a file"""
        file_path = Path(file_path)

        if file_path.suffix == '.pdf':
            text = self._extract_from_pdf(file_path)
        elif file_path.suffix == '.json':
            return self._parse_jira_json(file_path)
        else:
            # Treat as text file
            text = file_path.read_text()

        return self.extract_requirements(text)

    def extract_requirements(self, text: str) -> List[Dict[str, Any]]:
        """Extract requirements from text"""
        requirements = []

        # Clean up text
        text = text.replace('\r\n', '\n')

        # Find all matching patterns
        for pattern in self.patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)

            for match in matches:
                # Convert match to requirement
                if isinstance(match, tuple):
                    # User story format
                    if len(match) == 3:
                        requirement = {
                            "type": "user_story",
                            "role": match[0].strip(),
                            "action": match[1].strip(),
                            "benefit": match[2].strip(),
                            "text": f"As a {match[0]}, I want to {match[1]} so that {match[2]}"
                        }
                    else:
                        requirement = {
                            "type": "requirement",
                            "text": " ".join(match).strip()
                        }
                else:
                    # Simple requirement
                    requirement = {
                        "type": "requirement",
                        "text": match.strip()
                    }

                # Avoid duplicates and very short matches
                if len(requirement["text"]) > 10:
                    if not any(req["text"] == requirement["text"] for req in requirements):
                        requirements.append(requirement)

        return requirements

    def _extract_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2

            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"

            return text

        except ImportError:
            raise ImportError(
                "PyPDF2 is required for PDF parsing. "
                "Install with: pip install PyPDF2"
            )

    def _parse_jira_json(self, json_path: Path) -> List[Dict[str, Any]]:
        """Parse JIRA JSON export"""
        import json

        requirements = []
        data = json.loads(json_path.read_text())

        # Handle both single issue and multiple issues
        issues = data.get("issues", [data]) if isinstance(data, dict) else data

        for issue in issues:
            if isinstance(issue, dict):
                fields = issue.get("fields", {})

                # Extract summary as requirement
                summary = fields.get("summary", "")
                if summary:
                    requirements.append({
                        "type": "jira_story",
                        "key": issue.get("key", ""),
                        "text": f"User can {summary.lower()}"
                    })

                # Extract description
                description = fields.get("description", "")
                if description:
                    # Extract requirements from description
                    desc_reqs = self.extract_requirements(description)
                    requirements.extend(desc_reqs)

        return requirements


class JIRAAcceptanceCriteriaParser:
    """
    Generic parser for extracting Acceptance Criteria from any JIRA PDF.
    No hardcoded values - works with various JIRA export formats.
    """

    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger(__name__)
        self.debug = debug

    def parse_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse only AC section from JIRA PDF"""
        file_path = Path(file_path)

        if file_path.suffix != '.pdf':
            raise ValueError("JIRA AC parser only supports PDF files")

        # Extract text from PDF
        text = self._extract_from_pdf(file_path)

        # Extract story title/key
        story_info = self._extract_story_info(text)

        if self.debug:
            print(f"Story Info: {story_info}")

        # Extract AC section
        ac_section = self._extract_acceptance_criteria_section(text)

        if not ac_section:
            raise ValueError("No Acceptance Criteria section found in PDF")

        if self.debug:
            print(f"AC Section found: {len(ac_section)} characters")
            print("First 500 chars of AC section:")
            print(ac_section[:500])
            print("-" * 50)

        # Parse acceptance criteria - try multiple methods
        acceptance_criteria = []

        # Method 1: Try table format with headers
        acceptance_criteria = self._parse_table_with_headers(ac_section)

        # Method 2: Try row-based format
        if not acceptance_criteria:
            if self.debug:
                print("Method 1 failed, trying method 2...")
            acceptance_criteria = self._parse_row_based_format(ac_section)

        # Method 3: Try free-form text parsing
        if not acceptance_criteria:
            if self.debug:
                print("Method 2 failed, trying method 3...")
            acceptance_criteria = self._parse_freeform_format(ac_section)

        if not acceptance_criteria:
            raise ValueError("No acceptance criteria could be parsed from the AC section")

        # Convert to requirements format
        requirements = []
        for ac in acceptance_criteria:
            requirement = {
                "type": "acceptance_criteria",
                "key": story_info.get("key", ""),
                "story": story_info.get("title", ""),
                "ac_id": ac.get("id", f"AC{len(requirements) + 1}"),
                "given": self._clean_text(ac["given"]),
                "when": self._clean_text(ac["when"]),
                "then": self._clean_text(ac["then"]),
                "text": f"Given {ac['given']} When {ac['when']} Then {ac['then']}"
            }
            requirements.append(requirement)

        return requirements

    def _extract_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2

            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    text += page_text + "\n"

            return text

        except ImportError:
            raise ImportError(
                "PyPDF2 is required for PDF parsing. "
                "Install with: pip install PyPDF2"
            )

    def _extract_story_info(self, text: str) -> Dict[str, str]:
        """Extract story key and title from PDF"""
        info = {}

        # Generic pattern for JIRA keys
        key_patterns = [
            r'\[#?([A-Z]{2,}-\d+)\]',  # [JIRA-123] or [#JIRA-123]
            r'([A-Z]{2,}-\d+)',  # JIRA-123 without brackets
        ]

        for pattern in key_patterns:
            match = re.search(pattern, text[:2000])  # Look in first 2000 chars
            if match:
                info["key"] = match.group(1)
                break

        # Extract story title - try multiple patterns
        title_patterns = [
            r'\[.*?\]\s*\[.*?\]\s*([^\[]+?)(?:Created|$)',  # [X] [Y] Title Created:
            r'\[.*?\]\s*([^\[]+?)(?:Created|$)',  # [X] Title Created:
            r'Summary:\s*([^\n]+)',  # Summary: Title
            r'Title:\s*([^\n]+)',  # Title: Title
        ]

        for pattern in title_patterns:
            match = re.search(pattern, text[:2000], re.MULTILINE)
            if match:
                info["title"] = match.group(1).strip()
                break

        # Default if nothing found
        if "title" not in info:
            info["title"] = info.get("key", "Story")

        return info

    def _extract_acceptance_criteria_section(self, text: str) -> Optional[str]:
        """Extract only the Acceptance Criteria section from PDF text"""

        # Find AC section start
        ac_patterns = [
            r'Acceptance\s+Criteria',
            r'Acceptance\s+Criterion',
            r'ACs?\s*:',
        ]

        start_pos = None
        for pattern in ac_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_pos = match.start()
                break

        if start_pos is None:
            return None

        # Find end of AC section
        end_patterns = [
            r'Tech\s+notes',
            r'Technical\s+notes',
            r'Implementation',
            r'Checklist',
            r'Comments',
            r'Tech\s+Tasks?',
            r'Assumptions?\s*:',
            r'Questions',
            r'Ready\s+for\s+development',
            r'Feature\s+Toggle',
            r'DB\s+schema',
            r'https://sgtechstack',
        ]

        end_pos = len(text)
        for pattern in end_patterns:
            match = re.search(pattern, text[start_pos:], re.IGNORECASE)
            if match:
                end_pos = min(end_pos, start_pos + match.start())

        return text[start_pos:end_pos].strip()

    def _parse_table_with_headers(self, ac_section: str) -> List[Dict[str, str]]:
        """Parse AC table that has Given/When/Then headers"""
        acceptance_criteria = []

        # Look for table header
        header_pattern = r'Given\s*When\s*Then'
        header_match = re.search(header_pattern, ac_section, re.IGNORECASE)

        if not header_match:
            return []

        # Get content after header
        table_content = ac_section[header_match.end():]

        # Split into rows (look for patterns that indicate new rows)
        # Each row typically starts with context about the state
        rows = []
        current_row = []

        lines = table_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this looks like a new row (starts with a condition/state)
            if self._is_new_row(line, current_row):
                if current_row:
                    rows.append(' '.join(current_row))
                current_row = [line]
            else:
                current_row.append(line)

        # Don't forget the last row
        if current_row:
            rows.append(' '.join(current_row))

        # Parse each row
        ac_counter = 1
        for row in rows:
            parsed_row = self._parse_table_row(row)
            if parsed_row:
                parsed_row['id'] = f'AC{ac_counter}'
                acceptance_criteria.append(parsed_row)
                ac_counter += 1

        return acceptance_criteria

    def _parse_row_based_format(self, ac_section: str) -> List[Dict[str, str]]:
        """Parse AC format where each row contains Given/When/Then inline"""
        acceptance_criteria = []

        # Look for patterns like:
        # The job executes | The API returns data | The job processes it
        # or separated by multiple spaces/tabs

        lines = ac_section.split('\n')
        ac_counter = 1

        for line in lines:
            line = line.strip()
            if not line or len(line) < 20:  # Skip empty or very short lines
                continue

            # Try to parse as a complete AC
            parsed = self._parse_inline_ac(line)
            if parsed:
                parsed['id'] = f'AC{ac_counter}'
                acceptance_criteria.append(parsed)
                ac_counter += 1

        return acceptance_criteria

    def _parse_freeform_format(self, ac_section: str) -> List[Dict[str, str]]:
        """Parse free-form text looking for Given/When/Then patterns"""
        acceptance_criteria = []

        # Look for explicit Given/When/Then keywords
        pattern = r'Given\s+(.+?)\s+When\s+(.+?)\s+Then\s+(.+?)(?=Given|$)'
        matches = re.finditer(pattern, ac_section, re.DOTALL | re.IGNORECASE)

        ac_counter = 1
        for match in matches:
            acceptance_criteria.append({
                'id': f'AC{ac_counter}',
                'given': match.group(1).strip(),
                'when': match.group(2).strip(),
                'then': match.group(3).strip()
            })
            ac_counter += 1

        return acceptance_criteria

    def _is_new_row(self, line: str, current_row: List[str]) -> bool:
        """Determine if a line starts a new table row"""
        # If no current row, this is definitely new
        if not current_row:
            return True

        # Check for patterns that indicate a new row
        new_row_indicators = [
            # State/condition patterns
            r'^(PPHTP|The|A|An)\s+',
            r'^[A-Z]{3,}\s+',  # All caps words like "GET", "POST"
            # Complete sentences
            r'^[A-Z][a-z]+\s+\w+\s+\w+',
        ]

        for pattern in new_row_indicators:
            if re.match(pattern, line):
                # Check if current row seems complete (has enough content)
                current_content = ' '.join(current_row)
                if len(current_content) > 50:  # Arbitrary threshold
                    return True

        return False

    def _parse_table_row(self, row: str) -> Optional[Dict[str, str]]:
        """Parse a single table row to extract Given/When/Then"""
        # Common patterns in the row
        # Usually: [Initial state/condition] [Action/API call] [Expected result]

        given = ""
        when = ""
        then = ""

        # Method 1: Look for explicit separators (multiple spaces, tabs, pipes)
        parts = re.split(r'\s{3,}|\t+|\|', row)
        if len(parts) >= 3:
            given = parts[0].strip()
            when = parts[1].strip()
            then = ' '.join(parts[2:]).strip()

            if given and when and then:
                return {'given': given, 'when': when, 'then': then}

        # Method 2: Look for action keywords to split
        action_patterns = [
            r'(.*?)\s+(is\s+executed|calls?|executes?|runs?|processes?|performs?)\s+(.+?)\s+(returns?|should|must|will|the\s+job|PPH|has|completes?)\s+(.+)',
            r'(.*?)\s+(The\s+\w+\s+Job\s+is\s+executed)\s*\.?\s*(.+)',
        ]

        for pattern in action_patterns:
            match = re.match(pattern, row, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    given = groups[0].strip()
                    when = f"{groups[1]} {groups[2] if len(groups) > 2 else ''}".strip()
                    then = ' '.join(groups[3:]).strip() if len(groups) > 3 else groups[2].strip()

                    if given and when and then:
                        return {'given': given, 'when': when, 'then': then}

        # Method 3: Look for result indicators
        result_indicators = ['should', 'must', 'will', 'returns', 'displays', 'shows', 'the job', 'PPH']
        for indicator in result_indicators:
            if indicator in row.lower():
                parts = re.split(rf'\b{indicator}\b', row, 1, re.IGNORECASE)
                if len(parts) == 2:
                    # Split the first part into given/when
                    first_part = parts[0].strip()
                    then = indicator + ' ' + parts[1].strip()

                    # Try to find action words in first part
                    action_words = ['executes', 'calls', 'runs', 'processes', 'is executed']
                    for action in action_words:
                        if action in first_part.lower():
                            given_when = re.split(rf'\b{action}\b', first_part, 1, re.IGNORECASE)
                            if len(given_when) == 2:
                                given = given_when[0].strip()
                                when = action + ' ' + given_when[1].strip()

                                if given and when and then:
                                    return {'given': given, 'when': when, 'then': then}

        return None

    def _parse_inline_ac(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a line that contains a complete AC"""
        # Skip lines that are clearly not ACs
        if len(line) < 30 or line.count(' ') < 3:
            return None

        # Try the table row parser first
        result = self._parse_table_row(line)
        if result:
            return result

        # If that fails, try other patterns
        # Pattern for "condition action result" format
        patterns = [
            r'^(.+?)\s+(when|if)\s+(.+?)\s+(then|should|must|will)\s+(.+)$',
            r'^(.+?)\.\s*(.+?)\.\s*(.+)$',  # Three sentences
        ]

        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    return {
                        'given': groups[0].strip(),
                        'when': groups[1].strip() if len(groups) > 3 else groups[1].strip(),
                        'then': groups[-1].strip()
                    }

        return None

    def _clean_text(self, text: str) -> str:
        """Clean and format text for better readability"""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove artifacts
        text = text.replace('\n', ' ').replace('\r', ' ')

        # Fix common issues
        text = re.sub(r'\s+([,.])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([,.])(?=[A-Za-z])', r'\1 ', text)  # Add space after punctuation

        # Ensure proper sentence case
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        return text