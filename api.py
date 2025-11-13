import base64
import io
import json
import logging
import os
from typing import List

import dotenv
import requests
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pdf2image import convert_from_bytes

# Configure logging for the module. LOG_LEVEL can be set via environment variable (e.g. DEBUG, INFO).
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
try:
    numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
except Exception:
    numeric_level = logging.INFO
logging.basicConfig(level=numeric_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

dotenv.load_dotenv()

app = FastAPI(title="OCR API", description="Extract text from images and PDFs using Qwen3-VL-30B-A3B-Instruct-AWQ.",
              version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

NEW_API_URL = "https://vllm-4090.workstation.ritsdev.top/v1/chat/completions"
NEW_MODEL = "Qwen3-VL-30B-A3B-Instruct-AWQ"
# Seconds to wait for external HTTP calls (avoid hanging forever)
REQUESTS_TIMEOUT = float(os.getenv("REQUESTS_TIMEOUT", "15"))


def pdf_to_base64_images(pdf_bytes, target_size=(1024, 1024)):
    """
    Convert PDF bytes to a list of base64-encoded images, one per page, resized to target_size.
    """
    images = convert_from_bytes(pdf_bytes)
    b64_images = []
    for img in images:
        img = img.convert('RGB')
        # Use a resampling constant compatible with different Pillow versions
        try:
            resample = Image.Resampling.LANCZOS
        except Exception:
            # Pillow may expose resampling enums under Image.Resampling or module-level constants.
            resample = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS', None)
            if resample is None:
                # fallback to commonly available constants via getattr to avoid static resolution warnings
                resample = getattr(Image, 'LANCZOS', getattr(Image, 'BICUBIC', getattr(Image, 'NEAREST', 0)))
        img = img.resize(target_size, resample)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        b64_img = base64.b64encode(buf.getvalue()).decode()
        b64_images.append(b64_img)
    return b64_images


def _extract_json_substring(s: str):
    """Find the first JSON object or array in a string and return it (substring) or None."""
    if not isinstance(s, str):
        return None
    # find first opening bracket
    start = None
    for i, ch in enumerate(s):
        if ch in '{[':
            start = i
            break
    if start is None:
        return None

    stack = []
    pairs = {'{': '}', '[': ']'}
    for i in range(start, len(s)):
        ch = s[i]
        if ch in '{[':
            stack.append(pairs[ch])
        elif ch in '}]':
            if not stack:
                # unmatched closer; ignore
                return None
            expected = stack.pop()
            if ch != expected:
                # mismatch
                return None
            if not stack:
                return s[start:i + 1]
    return None


def parse_model_json(content):
    """Try to parse model response content into a Python object (dict/list). Return parsed object or original string."""
    if isinstance(content, (dict, list)):
        return content
    if not isinstance(content, str):
        return content

    # quick attempt: if the whole string is JSON
    try:
        return json.loads(content)
    except Exception:
        pass

    # extract a JSON substring and parse it
    js = _extract_json_substring(content)
    if js:
        try:
            return json.loads(js)
        except Exception:
            return content
    return content


@app.post("/extract", summary="Extract answers from PDFs using a template",
          response_description="JSON schema and extracted answers")
async def extract(template: UploadFile = File(...), files: List[UploadFile] = File(...),
                  qualtrics_link: str = Form("")):
    results = []

    headers = {"Content-Type": "application/json"}

    # Step 1: Generate JSON schema(s) from template PDF (one schema per template page)
    try:
        template_bytes = await template.read()
        template_images_b64 = pdf_to_base64_images(template_bytes)

        json_schemas = []
        for idx, img_b64 in enumerate(template_images_b64):
            template_content = [
                {"type": "text",
                 "text": "Analyze this PDF form template page and generate a JSON schema for extracting answers from similar filled form pages."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
            template_messages = [
                {"role": "system",
                 "content": "You are a JSON-output-only assistant. Respond with ONLY valid JSON (an object or an array) representing a JSON schema for extracting fields from the form page. Do not include any explanatory text."},
                {"role": "user", "content": template_content}
            ]
            schema_payload = {
                "model": NEW_MODEL,
                "messages": template_messages,
                "temperature": 0.0,
            }

            schema_resp = requests.post(NEW_API_URL, json=schema_payload, headers=headers, timeout=REQUESTS_TIMEOUT)
            schema_resp.raise_for_status()

            schema_content = schema_resp.json()["choices"][0]["message"]["content"]
            parsed_schema = parse_model_json(schema_content)

            logger.info("Generated schema for template page %s: %s", idx, parsed_schema)
            json_schemas.append(parsed_schema)
    except Exception as e:
        return JSONResponse(content={"error": f"Template processing failed: {str(e)}"}, status_code=400)

    # Step 2: Fetch qualtrics link, analyze fields and map to json schema
    qualtrics_page_text = ""
    if qualtrics_link:
        try:
            qualtrics_page = requests.get(qualtrics_link, timeout=REQUESTS_TIMEOUT)
            qualtrics_page.raise_for_status()
            qualtrics_page_text = qualtrics_page.text
        except Exception as e:
            return JSONResponse(content={"error": f"Failed to fetch Qualtrics link: {str(e)}"}, status_code=400)
    else:
        # If no qualtrics link provided, continue with empty mapping
        qualtrics_page_text = ""

    qualtrics_messages = [
        {"role": "system",
         "content": "You are a JSON-output-only assistant. Respond with ONLY valid JSON mapping the Qualtrics fields to the provided JSON schemas. Do not include explanatory text."},
        {"role": "user",
         "content": f"Analyze the following Qualtrics survey page HTML and map its fields to the provided JSON schema. Survey HTML: {qualtrics_page_text}.\nJSON Schemas: {json_schemas}"
         }
    ]

    qualtrics_payload = {
        "model": NEW_MODEL,
        "messages": qualtrics_messages,
        "temperature": 0.0,
    }

    try:
        qualtrics_resp = requests.post(NEW_API_URL, json=qualtrics_payload, headers=headers, timeout=REQUESTS_TIMEOUT)
        qualtrics_resp.raise_for_status()

        mapping_info_raw = qualtrics_resp.json()["choices"][0]["message"]["content"]
        mapping_info = parse_model_json(mapping_info_raw)

        logger.info("Mapping info: %s", mapping_info)
    except Exception as e:
        # Non-fatal: include a warning in results but continue extracting from PDFs using schema only
        logger.warning("Failed to map Qualtrics fields: %s", e, exc_info=True)
        mapping_info = None

    # Step 3: Extract answers from each PDF treating each page/image as a separate form
    for file in files:
        file_pages = []
        file_images_b64 = []
        try:
            file_bytes = await file.read()
            file_images_b64 = pdf_to_base64_images(file_bytes)

            for page_idx, img_b64 in enumerate(file_images_b64):
                # pick schema for this page index, fallback to first schema if not enough template pages
                schema_to_use = json_schemas[page_idx] if page_idx < len(json_schemas) else json_schemas[0]

                extract_content = [
                    {"type": "text",
                     "text": f"Using this JSON schema, extract answers from the attached filled form page. Return only the answers as JSON. Schema: {schema_to_use}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
                extract_messages = [
                    {"role": "system",
                     "content": "You are a JSON-output-only assistant. Respond with ONLY valid JSON containing the extracted answers. Do not include any explanatory text."},
                    {"role": "user", "content": extract_content}
                ]

                logger.info("Extracting answers from file %s, page %s using schema: %s", file.filename, page_idx,
                            schema_to_use)

                extract_payload = {
                    "model": NEW_MODEL,
                    "messages": extract_messages,
                    "temperature": 0.0,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "Answers",
                            "schema": schema_to_use
                        },
                    }
                }

                # Use timeout here too
                extract_resp = requests.post(NEW_API_URL, json=extract_payload, headers=headers,
                                             timeout=REQUESTS_TIMEOUT)
                extract_resp.raise_for_status()
                answers_raw = extract_resp.json()["choices"][0]["message"]["content"]
                logger.debug("Raw model answers for file %s page %s: %s", file.filename, page_idx, answers_raw)
                answers = parse_model_json(answers_raw)

                file_pages.append({
                    "page_index": page_idx,
                    "answers": answers,
                    "base64_image": img_b64
                })
        except Exception as e:
            # If an error occurs per-file, mark it; include any pages processed so far
            file_pages.append({"error": f"Error processing file: {str(e)}"})

        results.append({"filename": file.filename, "pages": file_pages, "base64_images": file_images_b64})

    # Step 4: (placeholder) Generate filled quadricks links and side-by-side view
    qualtrics_links = [
        qualtrics_link + "QPopulateResponse={...filled_data...}"  # Placeholder
    ]

    logger.debug("Extraction results: %s", json.dumps(results, indent=2))

    # Echo qualtrics_link so clients can verify the server received the form field
    return JSONResponse(
        content={
            "json_schemas": json_schemas,
            "results": results,
            "template_base64_images": template_images_b64,
            "received_qualtrics_link": qualtrics_link,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
