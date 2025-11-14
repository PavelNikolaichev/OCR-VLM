# OCR-VLM PDF Form Extraction Service

A powerful service for extracting structured data from PDF forms using Vision Language Models (VLM). This application
uses Qwen3-VL models to analyze form templates and extract data from filled forms automatically.

## Features

- 🎯 **Template-Based Extraction**: Upload a blank form template to automatically generate extraction schemas
- 📄 **Multi-Page Support**: Process PDFs with multiple pages
- 🔄 **Batch Processing**: Extract data from multiple forms simultaneously
- 🔗 **Qualtrics Integration**: Map extracted fields to Qualtrics survey questions
- 🎨 **User-Friendly UI**: Clean Streamlit interface with progress tracking
- 🔧 **Robust Error Handling**: Retry logic, timeout management, and comprehensive error reporting
- 📊 **Structured Output**: JSON schema-based extraction with validation

## Architecture

The service is built with a modular architecture:

```
OCR-VLM/
├── api.py                          # FastAPI backend
├── main.py                         # Streamlit UI
├── config.py                       # Centralized configuration
├── logger.py                       # Logging setup
├── exceptions.py                   # Custom exceptions
├── run.py                          # Launch script
├── services/
│   ├── vlm_service.py             # VLM API integration
│   └── extraction_service.py      # Extraction orchestration
└── utils/
    ├── image_processor.py         # PDF/Image processing
    ├── json_parser.py             # JSON parsing utilities
    └── validator.py               # Input validation
```

## Installation

### Prerequisites

- Python 3.13
- poppler (for PDF processing)
    - Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/
    - macOS: `brew install poppler`
    - Linux: `sudo apt-get install poppler-utils`

### Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd OCR-VLM
```

2. Create a virtual environment:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

Or using the docker:

```bash
docker build -t ocr-vlm .
docker run -p 8501:8501 ocr-vlm
```

## Usage

### Starting the Service

Run both API and UI together:

```bash
python run.py
```

Or run them separately:

```bash
# Terminal 1 - API Server
python api.py

# Terminal 2 - Streamlit UI
streamlit run main.py
```

The service will be available at:

- API: http://localhost:8000
- UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

### Using the Web Interface

1. **Upload Template**: Upload a blank PDF form template
2. **Upload Forms**: Upload one or more filled PDF forms
3. **Optional**: Provide a Qualtrics survey URL for field mapping
4. **Extract**: Click "Extract Data" to process
5. **Review**: View extracted data, download JSON results

### API Usage

```python
import requests

# Prepare files
files = {
    'template': open('template.pdf', 'rb'),
    'files': [
        open('filled_form_1.pdf', 'rb'),
        open('filled_form_2.pdf', 'rb')
    ]
}

data = {
    'qualtrics_link': 'https://your-survey-url.qualtrics.com/...'
}

# Make request
response = requests.post(
    'http://localhost:8000/extract',
    files=files,
    data=data
)

result = response.json()
print(result['json_schemas'])
print(result['results'])
```

## Development

### Project Structure

- `api.py`: FastAPI backend with endpoints
- `main.py`: Streamlit frontend application
- `services/`: Business logic layer
    - `vlm_service.py`: VLM API integration with retry logic
    - `extraction_service.py`: Orchestrates extraction workflow
- `utils/`: Utility modules
    - `image_processor.py`: PDF/Image processing
    - `json_parser.py`: Parse JSON from model responses
    - `validator.py`: Input validation
- `config.py`: Configuration management
- `logger.py`: Logging setup
- `exceptions.py`: Custom exception classes

### Adding Features

1. **New Service Method**: Add to appropriate service class in `services/`
2. **New Utility**: Create in `utils/` directory
3. **New Config**: Add to `config.py` and `.env.example`
4. **New Endpoint**: Add to `api.py` with proper error handling

### Testing

```bash
# Test API health
curl http://localhost:8000/health

# Test extraction (requires files)
curl -X POST http://localhost:8000/extract \
  -F "template=@template.pdf" \
  -F "files=@filled_form.pdf" \
  -F "qualtrics_link="
```

## Troubleshooting

### API Server Not Starting

- Check if port 8000 is available
- Verify environment variables in `.env`
- Check logs for error messages

### PDF Processing Errors

- Ensure poppler is installed and in PATH
- Check PDF file is not corrupted
- Verify file size is within limits

### VLM API Errors

- Check VLM_API_URL is correct
- Verify API endpoint is accessible
- Check timeout settings if requests are slow

### Image Quality Issues

- Adjust PDF_DPI in configuration (higher = better quality, slower)
- Modify IMAGE_QUALITY setting
- Check source PDF quality
