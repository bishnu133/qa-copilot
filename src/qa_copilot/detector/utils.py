import re
from typing import Dict, Any
from difflib import SequenceMatcher


def parse_element_description(description: str) -> Dict[str, Any]:
    """
    Parse natural language description into structured format.

    Examples:
        "Click on Login button" -> {action: "click", target: "Login", element_type: "button"}
        "Enter email in username field" -> {action: "type", target: "username", element_type: "input"}
        "Select USA from country dropdown" -> {action: "select", target: "country", element_type: "dropdown", value: "USA"}
    """
    original_description = description.strip()
    description = original_description

    # Common action patterns
    action_patterns = {
        r"click\s+(?:on\s+)?(?:the\s+)?": "click",
        r"tap\s+(?:on\s+)?(?:the\s+)?": "click",
        r"press\s+(?:the\s+)?": "click",
        r"enter\s+.*?\s+in\s+(?:the\s+)?": "type",
        r"type\s+.*?\s+in\s+(?:the\s+)?": "type",
        r"fill\s+(?:in\s+)?(?:the\s+)?": "type",
        r"select\s+(.*?)\s+from\s+(?:the\s+)?": "select",
        r"choose\s+(.*?)\s+from\s+(?:the\s+)?": "select",
        r"check\s+(?:the\s+)?": "check",
        r"enter\s+": "type",
        r"type\s+": "type",
        r"input\s+": "type",
    }

    # Element type patterns
    type_patterns = {
        "button": ["button", "btn"],
        "link": ["link", "href", "anchor"],
        "input": ["input", "field", "textbox", "text box", "box"],
        "checkbox": ["checkbox", "check box"],
        "radio": ["radio", "radio button", "option"],
        "dropdown": ["dropdown", "select", "combobox", "combo box"],
        "image": ["image", "img", "picture", "photo"],
        "tab": ["tab"],
        "menu": ["menu"],
    }

    result = {
        "original": original_description,
        "action": None,
        "element_type": None,  # Changed from "type" to "element_type"
        "target": None,  # Changed from "text" to "target"
        "attributes": {},
        "value": None
    }

    # Detect action
    for pattern, action in action_patterns.items():
        match = re.search(pattern, description.lower())
        if match:
            result["action"] = action

            # Special handling for select/choose - extract the value
            if action == "select":
                select_match = re.search(r"(select|choose)\s+(.*?)\s+from\s+(?:the\s+)?(.*)",
                                         description, re.IGNORECASE)
                if select_match:
                    result["value"] = select_match.group(2).strip()
                    description = select_match.group(3).strip()
                else:
                    description = re.sub(pattern, "", description, flags=re.IGNORECASE).strip()
            else:
                # For simple patterns like "Enter username", keep the text after the action
                if pattern in [r"enter\s+", r"type\s+", r"input\s+"]:
                    # Just remove the action word, keep the rest
                    description = re.sub(pattern, "", description, flags=re.IGNORECASE).strip()
                else:
                    description = re.sub(pattern, "", description, flags=re.IGNORECASE).strip()
            break

    # IMPROVED: If action is "type" but no explicit type found, assume it's an input
    if result["action"] == "type" and not result["element_type"]:
        result["element_type"] = "input"

    # Detect element type (only if not already set)
    if not result["element_type"]:
        desc_lower = description.lower()
        for element_type, keywords in type_patterns.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    result["element_type"] = element_type
                    # Remove type keyword from description
                    description = re.sub(rf"\b{keyword}\b", "", description, flags=re.IGNORECASE).strip()
                    break
            if result["element_type"]:
                break

    # Extract attributes (color, position, etc.)
    # Color pattern
    color_match = re.search(r"\b(red|blue|green|yellow|black|white|gray|grey)\b", description.lower())
    if color_match:
        result["attributes"]["color"] = color_match.group(1)
        description = re.sub(rf"\b{color_match.group(1)}\b", "", description, flags=re.IGNORECASE).strip()

    # Position pattern
    position_match = re.search(r"\b(first|second|third|last|top|bottom|left|right)\b", description.lower())
    if position_match:
        result["attributes"]["position"] = position_match.group(1)
        description = re.sub(rf"\b{position_match.group(1)}\b", "", description, flags=re.IGNORECASE).strip()

    # The remaining text is the target
    text = description.strip()
    # Remove common words
    text = re.sub(r"\b(the|a|an)\b", "", text, flags=re.IGNORECASE).strip()

    if text:
        result["target"] = text

    # For compatibility, also include the old keys
    result["text"] = result["target"]
    result["type"] = result["element_type"]

    return result


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    # Convert to lowercase
    text = text.lower()
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove special characters (keep alphanumeric and spaces)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text.strip()


def fuzzy_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """
    Check if two texts match with fuzzy logic.

    Args:
        text1: First text
        text2: Second text
        threshold: Matching threshold (0-1)

    Returns:
        True if texts match above threshold
    """
    # Normalize texts
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    # Exact match after normalization
    if norm1 == norm2:
        return True

    # Calculate similarity
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold


def extract_selector_from_element(element) -> str:
    """Extract a robust selector from an element"""
    # This would analyze the element and create a selector
    # that's less likely to break with UI changes
    pass