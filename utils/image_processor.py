"""Image processing utilities."""
import base64
import io
from typing import List, Tuple

from PIL import Image
from pdf2image import convert_from_bytes

from config import config
from exceptions import PDFProcessingError, ImageProcessingError
from logger import setup_logger

logger = setup_logger(__name__)


class ImageProcessor:
    """Handles image and PDF processing operations."""

    @staticmethod
    def get_resampling_filter():
        """Get the appropriate resampling filter for the installed Pillow version."""
        try:
            return Image.Resampling.LANCZOS
        except AttributeError:
            try:
                return Image.LANCZOS
            except AttributeError:
                return Image.BICUBIC

    @staticmethod
    def resize_image(img: Image.Image, target_size: Tuple[int, int] = None) -> Image.Image:
        """Resize an image to the target size while maintaining aspect ratio."""
        if target_size is None:
            target_size = config.DEFAULT_IMAGE_SIZE

        try:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Calculate aspect ratio preserving resize
            img.thumbnail(target_size, ImageProcessor.get_resampling_filter())

            # Create a new image with the target size and paste the resized image
            new_img = Image.new('RGB', target_size, (255, 255, 255))
            paste_x = (target_size[0] - img.width) // 2
            paste_y = (target_size[1] - img.height) // 2
            new_img.paste(img, (paste_x, paste_y))

            return new_img
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            raise ImageProcessingError(f"Image resize failed: {e}")

    @staticmethod
    def image_to_base64(img: Image.Image, format: str = None, quality: int = None) -> str:
        """Convert PIL Image to base64 encoded string."""
        if format is None:
            format = config.IMAGE_FORMAT
        if quality is None:
            quality = config.IMAGE_QUALITY

        try:
            buffer = io.BytesIO()
            img.save(buffer, format=format, quality=quality)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}")
            raise ImageProcessingError(f"Base64 encoding failed: {e}")

    @staticmethod
    def pdf_to_images(pdf_bytes: bytes, dpi: int = None) -> List[Image.Image]:
        """Convert PDF bytes to a list of PIL Images."""
        if dpi is None:
            dpi = config.PDF_DPI

        try:
            images = convert_from_bytes(pdf_bytes, dpi=dpi)

            if len(images) > config.MAX_PDF_PAGES:
                logger.warning(f"PDF has {len(images)} pages, exceeding max of {config.MAX_PDF_PAGES}")
                images = images[:config.MAX_PDF_PAGES]

            return images
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise PDFProcessingError(f"PDF conversion failed: {e}")

    @staticmethod
    def pdf_to_base64_images(pdf_bytes: bytes, target_size: Tuple[int, int] = None) -> List[str]:
        """
        Convert PDF bytes to a list of base64-encoded images.

        Args:
            pdf_bytes: PDF file content as bytes
            target_size: Target size for resized images (width, height)

        Returns:
            List of base64-encoded image strings
        """
        if target_size is None:
            target_size = config.DEFAULT_IMAGE_SIZE

        try:
            images = ImageProcessor.pdf_to_images(pdf_bytes)
            b64_images = []

            for idx, img in enumerate(images):
                logger.debug(f"Processing PDF page {idx + 1}/{len(images)}")
                resized_img = ImageProcessor.resize_image(img, target_size)
                b64_img = ImageProcessor.image_to_base64(resized_img)
                b64_images.append(b64_img)

            logger.info(f"Successfully converted PDF to {len(b64_images)} base64 images")
            return b64_images
        except (PDFProcessingError, ImageProcessingError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in pdf_to_base64_images: {e}")
            raise PDFProcessingError(f"PDF to base64 conversion failed: {e}")
