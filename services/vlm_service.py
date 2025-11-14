"""Service for interacting with the Vision Language Model API."""
import time
from typing import Any, Dict, List, Optional

import requests

from config import config
from exceptions import VLMAPIError
from logger import setup_logger
from utils.json_parser import JSONParser

logger = setup_logger(__name__)


class VLMService:
    """Handles all interactions with the Vision Language Model API."""

    def __init__(self, api_url: str = None, model: str = None):
        """Initialize VLM service with configuration."""
        self.api_url = api_url or config.VLM_API_URL
        self.model = model or config.VLM_MODEL
        self.timeout = config.REQUESTS_TIMEOUT
        self.max_retries = config.MAX_RETRIES
        self.retry_delay = config.RETRY_DELAY

    def _make_request(self, payload: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """
        Make a request to the VLM API with retry logic.

        Args:
            payload: Request payload
            retry_count: Current retry attempt

        Returns:
            Response JSON

        Raises:
            VLMAPIError: If request fails after all retries
        """
        headers = {"Content-Type": "application/json"}

        try:
            logger.debug(f"Making VLM API request (attempt {retry_count + 1}/{self.max_retries + 1})")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as e:
            logger.warning(f"VLM API request timeout: {e}")
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(payload, retry_count + 1)
            raise VLMAPIError(f"Request timeout after {self.max_retries + 1} attempts")

        except requests.exceptions.HTTPError as e:
            logger.error(f"VLM API HTTP error: {e}")
            if retry_count < self.max_retries and e.response.status_code >= 500:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(payload, retry_count + 1)
            raise VLMAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"VLM API request error: {e}")
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(payload, retry_count + 1)
            raise VLMAPIError(f"Request failed: {str(e)}")

    def generate_schema_from_template(self, image_base64: str) -> Dict[str, Any]:
        """
        Generate a JSON schema from a template image.

        Args:
            image_base64: Base64-encoded template image

        Returns:
            Generated JSON schema
        """
        content = [
            {
                "type": "text",
                "text": (
                    "Analyze this PDF form template page and generate a JSON schema for extracting "
                    "answers from similar filled form pages. The schema should define the structure "
                    "and field names that will be used to extract data from completed forms. "
                    "Include field types and descriptions where applicable."
                )
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a JSON schema generation assistant. Analyze form templates and create "
                    "JSON schemas that define the structure for extracting data from filled forms. "
                    "Respond with ONLY valid JSON (an object or array) representing the schema. "
                    "Do not include any explanatory text outside the JSON."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": config.VLM_TEMPERATURE,
        }

        try:
            response = self._make_request(payload)
            content_raw = response["choices"][0]["message"]["content"]
            schema = JSONParser.parse_model_response(content_raw)
            logger.info("Successfully generated schema from template")
            return schema
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response format from VLM API: {e}")
            raise VLMAPIError(f"Invalid response format: {e}")

    def extract_answers_from_form(
            self,
            image_base64: str,
            schema: Dict[str, Any],
            use_structured_output: bool = True
    ) -> Dict[str, Any]:
        """
        Extract answers from a filled form using a schema.

        Args:
            image_base64: Base64-encoded form image
            schema: JSON schema to use for extraction
            use_structured_output: Whether to use structured output (json_schema mode)

        Returns:
            Extracted answers
        """
        content = [
            {
                "type": "text",
                "text": (
                    f"Using this JSON schema, extract answers from the attached filled form page. "
                    f"Return only the extracted data as JSON matching the schema structure. "
                    f"Schema: {schema}"
                )
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            }
        ]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a data extraction assistant. Extract information from filled forms "
                    "according to the provided JSON schema. Respond with ONLY valid JSON containing "
                    "the extracted answers. Do not include any explanatory text."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": config.VLM_TEMPERATURE,
        }

        # Add structured output if requested and schema is valid
        if use_structured_output and isinstance(schema, dict):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "ExtractedAnswers",
                    "schema": schema
                }
            }

        try:
            response = self._make_request(payload)
            content_raw = response["choices"][0]["message"]["content"]
            answers = JSONParser.parse_model_response(content_raw)
            logger.info("Successfully extracted answers from form")
            return answers
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid response format from VLM API: {e}")
            raise VLMAPIError(f"Invalid response format: {e}")

    def map_qualtrics_fields(
            self,
            qualtrics_html: str,
            schemas: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Map Qualtrics survey fields to JSON schemas.

        Args:
            qualtrics_html: HTML content of Qualtrics survey page
            schemas: List of JSON schemas to map to

        Returns:
            Mapping information or None if mapping fails
        """
        if not qualtrics_html.strip():
            logger.info("No Qualtrics HTML provided, skipping field mapping")
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a field mapping assistant. Analyze Qualtrics survey HTML and map "
                    "its fields to provided JSON schemas. Respond with ONLY valid JSON containing "
                    "the field mappings. Do not include explanatory text."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Analyze the following Qualtrics survey page HTML and map its fields to "
                    f"the provided JSON schemas. Create a mapping that shows how each schema field "
                    f"corresponds to a Qualtrics field.\n\n"
                    f"Qualtrics HTML:\n{qualtrics_html[:5000]}\n\n"  # Limit HTML length
                    f"JSON Schemas:\n{schemas}"
                )
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": config.VLM_TEMPERATURE,
        }

        try:
            response = self._make_request(payload)
            content_raw = response["choices"][0]["message"]["content"]
            mapping = JSONParser.parse_model_response(content_raw)
            logger.info("Successfully mapped Qualtrics fields")
            return mapping
        except VLMAPIError as e:
            logger.warning(f"Failed to map Qualtrics fields: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.warning(f"Invalid response format when mapping Qualtrics fields: {e}")
            return None
