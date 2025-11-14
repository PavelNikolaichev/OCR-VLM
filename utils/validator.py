"""Input validation utilities."""
from typing import List

from fastapi import UploadFile

from exceptions import ValidationError
from logger import setup_logger

logger = setup_logger(__name__)


class Validator:
    """Handles input validation for the API."""

    @staticmethod
    def validate_pdf_size(pdf_bytes: bytes) -> None:
        """
            ValidationError: If file is too large
        Raises:

            pdf_bytes: PDF content
        Args:

        Validate PDF file size.
        """
        max_size = 50 * 1024 * 1024  # 50 MB
        if len(pdf_bytes) > max_size:
            raise ValidationError(f"PDF file too large: {len(pdf_bytes)} bytes (max: {max_size})")

    @staticmethod
    def validate_url(url: str) -> bool:
        """
            True if valid, False otherwise
        Returns:

            url: URL string to validate
        Args:

        Validate that a string is a valid URL.
        """
        if not url or not url.strip():
            return False
        return url.startswith('http://') or url.startswith('https://')

    @staticmethod
    def validate_pdf_files(files: List[UploadFile]) -> None:
        """
            ValidationError: If validation fails
        Raises:

            files: List of uploaded files to validate
        Args:

        Validate multiple PDF files.
        """
        if not files:
            raise ValidationError("At least one file must be provided")

        for file in files:
            Validator.validate_pdf_file(file)

    @staticmethod
    def validate_pdf_file(file: UploadFile) -> None:
        """
            ValidationError: If validation fails
        Raises:

            file: Uploaded file to validate
        Args:

        Validate that an uploaded file is a PDF.
        """
        if file.content_type and 'pdf' not in file.content_type.lower():
            raise ValidationError(f"File {file.filename} must be a PDF")
        if not file.filename.lower().endswith('.pdf'):
            raise ValidationError(f"File {file.filename} must be a PDF")
        if not file.filename:
            raise ValidationError("File must have a filename")
