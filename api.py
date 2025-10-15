import json
import os
import base64
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import requests
import dotenv
import io
from pdf2image import convert_from_bytes
from PIL import Image

dotenv.load_dotenv()

app = FastAPI(title="OCR API", description="Extract text from images and PDFs using Qwen3-VL-30B-A3B-Instruct-AWQ.", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

NEW_API_URL = "https://vllm-4090.workstation.ritsdev.top/v1/chat/completions"
NEW_MODEL = "Qwen3-VL-30B-A3B-Instruct-AWQ"
# API_KEY = os.getenv("OPENAI_API_KEY", None)
API_KEY = None

def pdf_to_base64_images(pdf_bytes, target_size=(1024, 1024)):
    """
    Convert PDF bytes to a list of base64-encoded images, one per page, resized to target_size.
    """
    images = convert_from_bytes(pdf_bytes)
    b64_images = []
    for img in images:
        img = img.convert('RGB')
        img = img.resize(target_size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        b64_img = base64.b64encode(buf.getvalue()).decode()
        b64_images.append(b64_img)
    return b64_images

@app.post("/extract", summary="Extract answers from PDFs using a template", response_description="JSON schema and extracted answers")
async def extract(template: UploadFile = File(...), files: List[UploadFile] = File(...)):
    results = []
    # Step 1: Generate JSON schema from template PDF
    try:
        template_bytes = await template.read()
        template_images_b64 = pdf_to_base64_images(template_bytes)
        # Each page as a separate content part in a single message
        template_content = [
            {"type": "text", "text": "Analyze this PDF form template and generate a JSON schema for extracting answers from similar filled forms."}
        ]
        for img_b64 in template_images_b64:
            template_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })
        template_messages = [
            {"role": "user", "content": template_content}
        ]
        schema_payload = {
            "model": NEW_MODEL,
            "messages": template_messages
        }
        print("Schema payload:", json.dumps(schema_payload))
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
        schema_resp = requests.post(NEW_API_URL, json=schema_payload, headers=headers)
        schema_resp.raise_for_status()
        json_schema = schema_resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return JSONResponse(content={"error": f"Template processing failed: {str(e)}"}, status_code=400)
    # Step 2: Extract answers from each PDF using the schema
    for file in files:
        try:
            file_bytes = await file.read()
            file_images_b64 = pdf_to_base64_images(file_bytes)
            # Each page as a separate content part in a single message
            extract_content = [
                {"type": "text", "text": f"Using this JSON schema, extract answers from the attached filled form PDF. Return only the answers as JSON. Schema: {json_schema}"}
            ]
            for img_b64 in file_images_b64:
                extract_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
            extract_messages = [
                {"role": "user", "content": extract_content}
            ]
            extract_payload = {
                "model": NEW_MODEL,
                "messages": extract_messages
            }
            extract_resp = requests.post(NEW_API_URL, json=extract_payload, headers=headers)
            extract_resp.raise_for_status()
            answers = extract_resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            answers = f"Error: {str(e)}"
        results.append({"filename": file.filename, "answers": answers, "base64_images": file_images_b64})
    return JSONResponse(content={"json_schema": json_schema, "results": results, "template_base64_images": template_images_b64})
