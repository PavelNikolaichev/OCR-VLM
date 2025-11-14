"""JSON parsing utilities for model responses."""
import json
from typing import Any, Union

from logger import setup_logger

logger = setup_logger(__name__)


class JSONParser:
    """Handles parsing of JSON from model responses that may contain extra text."""

    @staticmethod
    def extract_json_substring(text: str) -> Union[str, None]:
        """
        Find and extract the first complete JSON object or array from a string.

        Args:
            text: String that may contain JSON

        Returns:
            JSON substring or None if not found
        """
        if not isinstance(text, str):
            return None

        # Find first opening bracket
        start = None
        for i, ch in enumerate(text):
            if ch in '{[':
                start = i
                break

        if start is None:
            return None

        # Track nested brackets
        stack = []
        pairs = {'{': '}', '[': ']'}
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            ch = text[i]

            # Handle string literals (they may contain brackets)
            if ch == '"' and not escape_next:
                in_string = not in_string

            if ch == '\\' and in_string:
                escape_next = not escape_next
            else:
                escape_next = False

            if in_string:
                continue

            # Track bracket pairs
            if ch in '{[':
                stack.append(pairs[ch])
            elif ch in '}]':
                if not stack:
                    return None
                expected = stack.pop()
                if ch != expected:
                    return None
                if not stack:
                    return text[start:i + 1]

        return None

    @staticmethod
    def parse_model_response(content: Any) -> Any:
        """
        Parse model response content into a Python object (dict/list).

        Args:
            content: Raw content from model response

        Returns:
            Parsed object or original content if parsing fails
        """
        # Already parsed
        if isinstance(content, (dict, list)):
            return content

        if not isinstance(content, str):
            logger.warning(f"Unexpected content type: {type(content)}")
            return content

        # Try parsing the entire string as JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Extract JSON substring and parse
        json_str = JSONParser.extract_json_substring(content)
        if json_str:
            try:
                parsed = json.loads(json_str)
                logger.debug("Successfully extracted and parsed JSON from model response")
                return parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse extracted JSON: {e}")

        logger.warning("Could not parse model response as JSON, returning as-is")
        return content

    @staticmethod
    def validate_json_schema(schema: Any) -> bool:
        """
        Validate that a schema is a proper JSON object.

        Args:
            schema: Schema to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(schema, dict):
            return False

        # Basic validation - should have some structure
        return len(schema) > 0
