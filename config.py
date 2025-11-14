import os

from dotenv import load_dotenv


class Config:
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    # Rate Limiting (future enhancement)

    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    # CORS

    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    # Logging

    MAX_PDF_PAGES: int = int(os.getenv("MAX_PDF_PAGES", "50"))
    PDF_DPI: int = int(os.getenv("PDF_DPI", "200"))
    # PDF Processing

    IMAGE_QUALITY: int = int(os.getenv("IMAGE_QUALITY", "95"))
    IMAGE_FORMAT: str = "JPEG"
    MAX_IMAGE_SIZE: tuple = (2048, 2048)
    DEFAULT_IMAGE_SIZE: tuple = (1024, 1024)
    # Image Processing

    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUESTS_TIMEOUT: float = float(os.getenv("REQUESTS_TIMEOUT", "60"))
    # Request Configuration

    VLM_TEMPERATURE: float = float(os.getenv("VLM_TEMPERATURE", "0.0"))
    VLM_MODEL: str = os.getenv("VLM_MODEL", "Qwen3-VL-30B-A3B-Instruct-AWQ")
    VLM_API_URL: str = os.getenv("VLM_API_URL", "https://vllm-4090.workstation.ritsdev.top/v1/chat/completions")
    # VLM Model Configuration

    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    # API Configuration


load_dotenv()

config = Config()


