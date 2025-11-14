"""Service for orchestrating the extraction workflow."""
from typing import Dict, List, Any, Optional

import requests

from config import config
from exceptions import (
    SchemaGenerationError,
    QualtricsError,
    PDFProcessingError
)
from logger import setup_logger
from services.vlm_service import VLMService
from utils.image_processor import ImageProcessor

logger = setup_logger(__name__)


class ExtractionService:
    """Orchestrates the complete extraction workflow."""

    def __init__(self, vlm_service: VLMService = None):
        """Initialize extraction service."""
        self.vlm_service = vlm_service or VLMService()
        self.image_processor = ImageProcessor()

    def generate_schemas_from_template(self, template_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Generate JSON schemas from a template PDF.

        Args:
            template_bytes: Template PDF file content

        Returns:
            List of JSON schemas (one per page)

        Raises:
            SchemaGenerationError: If schema generation fails
        """
        try:
            logger.info("Converting template PDF to images")
            template_images = self.image_processor.pdf_to_base64_images(template_bytes)

            schemas = []
            for idx, img_b64 in enumerate(template_images):
                logger.info(f"Generating schema for template page {idx + 1}/{len(template_images)}")
                schema = self.vlm_service.generate_schema_from_template(img_b64)
                schemas.append(schema)

            logger.info(f"Successfully generated {len(schemas)} schemas")
            return schemas

        except PDFProcessingError as e:
            logger.error(f"Template PDF processing failed: {e}")
            raise SchemaGenerationError(f"Failed to process template PDF: {e}")
        except Exception as e:
            logger.error(f"Schema generation failed: {e}")
            raise SchemaGenerationError(f"Schema generation failed: {e}")

    def fetch_qualtrics_html(self, url: str) -> str:
        """
        Fetch HTML content from a Qualtrics URL.

        Args:
            url: Qualtrics survey URL

        Returns:
            HTML content

        Raises:
            QualtricsError: If fetch fails
        """
        if not url or not url.strip():
            return ""

        try:
            logger.info(f"Fetching Qualtrics page from: {url}")
            response = requests.get(url, timeout=config.REQUESTS_TIMEOUT)
            response.raise_for_status()
            logger.info("Successfully fetched Qualtrics HTML")
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Qualtrics page: {e}")
            raise QualtricsError(f"Failed to fetch Qualtrics page: {e}")

    def map_qualtrics_fields(
            self,
            qualtrics_url: str,
            schemas: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Map Qualtrics fields to schemas.

        Args:
            qualtrics_url: Qualtrics survey URL
            schemas: List of JSON schemas

        Returns:
            Mapping information or None
        """
        if not qualtrics_url or not qualtrics_url.strip():
            logger.info("No Qualtrics URL provided, skipping field mapping")
            return None

        try:
            html_content = self.fetch_qualtrics_html(qualtrics_url)
            mapping = self.vlm_service.map_qualtrics_fields(html_content, schemas)
            return mapping
        except QualtricsError as e:
            logger.warning(f"Qualtrics mapping failed: {e}")
            return None

    def extract_from_pdf(
            self,
            pdf_bytes: bytes,
            schemas: List[Dict[str, Any]],
            filename: str = "unknown.pdf"
    ) -> Dict[str, Any]:
        """
        Extract data from a filled PDF form.

        Args:
            pdf_bytes: PDF file content
            schemas: List of JSON schemas to use for extraction
            filename: Name of the PDF file (for logging)

        Returns:
            Dictionary containing extraction results
        """
        result = {
            "filename": filename,
            "pages": [],
            "base64_images": [],
            "status": "success",
            "error": None
        }

        try:
            logger.info(f"Processing PDF: {filename}")
            images_b64 = self.image_processor.pdf_to_base64_images(pdf_bytes)
            result["base64_images"] = images_b64

            for page_idx, img_b64 in enumerate(images_b64):
                logger.info(f"Extracting from {filename}, page {page_idx + 1}/{len(images_b64)}")

                # Use schema for corresponding page, or first schema as fallback
                schema = schemas[page_idx] if page_idx < len(schemas) else schemas[0]

                try:
                    answers = self.vlm_service.extract_answers_from_form(img_b64, schema)
                    result["pages"].append({
                        "page_index": page_idx,
                        "answers": answers,
                        "base64_image": img_b64,
                        "status": "success"
                    })
                except Exception as e:
                    logger.error(f"Failed to extract from {filename} page {page_idx}: {e}")
                    result["pages"].append({
                        "page_index": page_idx,
                        "answers": None,
                        "base64_image": img_b64,
                        "status": "error",
                        "error": str(e)
                    })

            logger.info(f"Completed extraction from {filename}")

        except PDFProcessingError as e:
            logger.error(f"PDF processing failed for {filename}: {e}")
            result["status"] = "error"
            result["error"] = f"PDF processing failed: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error processing {filename}: {e}")
            result["status"] = "error"
            result["error"] = f"Unexpected error: {str(e)}"

        return result

    def extract_batch(
            self,
            template_bytes: bytes,
            pdf_files: List[tuple],  # List of (filename, bytes)
            qualtrics_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform batch extraction from multiple PDFs.

        Args:
            template_bytes: Template PDF content
            pdf_files: List of (filename, bytes) tuples
            qualtrics_url: Optional Qualtrics survey URL

        Returns:
            Complete extraction results
        """
        logger.info(f"Starting batch extraction for {len(pdf_files)} files")

        # Generate schemas from template
        try:
            schemas = self.generate_schemas_from_template(template_bytes)
            template_images = self.image_processor.pdf_to_base64_images(template_bytes)
        except SchemaGenerationError as e:
            return {
                "status": "error",
                "error": str(e),
                "json_schemas": [],
                "results": [],
                "template_base64_images": [],
                "qualtrics_mapping": None
            }

        # Map Qualtrics fields if URL provided
        qualtrics_mapping = None
        if qualtrics_url:
            qualtrics_mapping = self.map_qualtrics_fields(qualtrics_url, schemas)

        # Extract from each PDF
        results = []
        for filename, pdf_bytes in pdf_files:
            result = self.extract_from_pdf(pdf_bytes, schemas, filename)
            results.append(result)

        logger.info("Batch extraction completed")

        return {
            "status": "success",
            "json_schemas": schemas,
            "results": results,
            "template_base64_images": template_images,
            "qualtrics_mapping": qualtrics_mapping,
            "received_qualtrics_link": qualtrics_url or ""
        }
