"""Custom exceptions for the OCR-VLM service."""


class OCRVLMException(Exception):
    """Base exception for OCR-VLM service."""
    pass


class PDFProcessingError(OCRVLMException):
    """Raised when PDF processing fails."""
    pass


class ImageProcessingError(OCRVLMException):
    """Raised when image processing fails."""
    pass


class VLMAPIError(OCRVLMException):
    """Raised when VLM API call fails."""
    pass


class SchemaGenerationError(OCRVLMException):
    """Raised when JSON schema generation fails."""
    pass


class ExtractionError(OCRVLMException):
    """Raised when data extraction fails."""
    pass


class ValidationError(OCRVLMException):
    """Raised when validation fails."""
    pass


class QualtricsError(OCRVLMException):
    """Raised when Qualtrics-related operations fail."""
    pass
