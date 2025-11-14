"""Streamlit UI for OCR-VLM PDF Form Extraction."""
import base64
import io
import json

import requests
import streamlit as st
from PIL import Image

from config import config

# Page configuration
st.set_page_config(
    page_title="OCR-VLM Form Extractor",
    page_icon="📄",
    layout="wide"
)

# API endpoint
API_URL = f"http://127.0.0.1:{config.API_PORT}"


def check_api_health() -> bool:
    """Check if API server is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.ok
    except Exception:
        return False


def display_image_from_base64(b64_string: str, caption: str = ""):
    """Display an image from a base64 string."""
    try:
        image_bytes = base64.b64decode(b64_string)
        image = Image.open(io.BytesIO(image_bytes))
        st.image(image, caption=caption, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to display image: {e}")


def display_results(result_data: dict):
    """Display extraction results in an organized manner."""
    # Show JSON schemas
    with st.expander("📋 Generated JSON Schemas", expanded=False):
        schemas = result_data.get("json_schemas", [])
        if schemas:
            for idx, schema in enumerate(schemas):
                st.subheader(f"Schema for Page {idx + 1}")
                st.json(schema)
        else:
            st.warning("No schemas generated")

    # Show Qualtrics mapping if available
    qualtrics_mapping = result_data.get("qualtrics_mapping")
    if qualtrics_mapping:
        with st.expander("🔗 Qualtrics Field Mapping", expanded=False):
            st.json(qualtrics_mapping)

    # Show template images
    template_images = result_data.get("template_base64_images", [])
    if template_images:
        with st.expander("📄 Template Pages", expanded=False):
            cols = st.columns(min(len(template_images), 3))
            for idx, img_b64 in enumerate(template_images):
                with cols[idx % 3]:
                    display_image_from_base64(img_b64, f"Template Page {idx + 1}")

    # Show extraction results
    st.subheader("📊 Extraction Results")
    results = result_data.get("results", [])

    if not results:
        st.warning("No extraction results available")
        return

    # Create tabs for each file
    if len(results) == 1:
        display_file_results(results[0])
    else:
        tabs = st.tabs([r.get("filename", f"File {i + 1}") for i, r in enumerate(results)])
        for tab, result in zip(tabs, results):
            with tab:
                display_file_results(result)


def display_file_results(file_result: dict):
    """Display results for a single file."""
    filename = file_result.get("filename", "Unknown")
    status = file_result.get("status", "unknown")

    if status == "error":
        st.error(f"❌ Error processing {filename}: {file_result.get('error', 'Unknown error')}")
        return

    pages = file_result.get("pages", [])

    if not pages:
        st.warning(f"No pages extracted from {filename}")
        return

    # Success metrics
    total_pages = len(pages)
    success_pages = sum(1 for p in pages if p.get("status") == "success")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Pages", total_pages)
    with col2:
        st.metric("Successful Extractions", success_pages)
    with col3:
        success_rate = (success_pages / total_pages * 100) if total_pages > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")

    st.divider()

    # Display each page
    for page_data in pages:
        page_idx = page_data.get("page_index", 0)
        page_status = page_data.get("status", "unknown")

        with st.container(border=True):
            if page_status == "error":
                st.error(f"Page {page_idx + 1} - Error: {page_data.get('error', 'Unknown error')}")
            else:
                col_img, col_data = st.columns([1, 1])

                with col_img:
                    st.markdown(f"**Page {page_idx + 1}**")
                    img_b64 = page_data.get("base64_image")
                    if img_b64:
                        display_image_from_base64(img_b64, f"Page {page_idx + 1}")

                with col_data:
                    st.markdown(f"**Extracted Data - Page {page_idx + 1}**")
                    answers = page_data.get("answers")
                    if answers:
                        st.json(answers)

                        # Download button for this page's data
                        json_str = json.dumps(answers, indent=2)
                        st.download_button(
                            label=f"📥 Download Page {page_idx + 1} Data",
                            data=json_str,
                            file_name=f"{filename}_page_{page_idx + 1}.json",
                            mime="application/json",
                            key=f"download_{filename}_{page_idx}"
                        )
                    else:
                        st.warning("No data extracted")


# Main UI
st.title("📄 OCR-VLM PDF Form Extraction")
st.markdown("""
Extract structured data from filled PDF forms using Vision Language Models.

**How it works:**
1. Upload a template PDF (blank form)
2. Upload one or more filled PDF forms
3. Optionally provide a Qualtrics survey link for field mapping
4. Click "Extract Data" to process
""")

# Check API health
with st.sidebar:
    st.header("⚙️ Settings")

    api_health = check_api_health()
    if api_health:
        st.success("✅ API Server: Connected")
    else:
        st.error("❌ API Server: Not Available")
        st.warning(f"Please ensure the API server is running on port {config.API_PORT}")

    st.divider()

    st.markdown("""
    **Configuration:**
    - Model: Qwen3-VL-30B
    - Image Size: 1024x1024
    - Timeout: 60s per request
    """)

    if st.button("🔄 Refresh API Status"):
        st.rerun()

# Main content
st.divider()

# File upload section
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ Template PDF")
    template_file = st.file_uploader(
        "Upload blank form template",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload the blank PDF form that will be used to generate extraction schemas"
    )

    if template_file:
        st.success(f"✅ Template: {template_file.name}")

with col2:
    st.subheader("2️⃣ Filled Forms")
    filled_files = st.file_uploader(
        "Upload completed forms",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload one or more filled PDF forms to extract data from"
    )

    if filled_files:
        st.success(f"✅ {len(filled_files)} file(s) uploaded")
        with st.expander("View uploaded files"):
            for f in filled_files:
                st.text(f"• {f.name}")

st.divider()

# Optional Qualtrics link
st.subheader("3️⃣ Qualtrics Integration (Optional)")
qualtrics_link = st.text_input(
    "Qualtrics Survey URL",
    placeholder="https://your-survey-url.qualtrics.com/...",
    help="Provide a Qualtrics survey URL to map form fields to survey questions"
)

st.divider()

# Extract button
if template_file and filled_files:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        extract_button = st.button(
            "🚀 Extract Data",
            type="primary",
            use_container_width=True
        )

    if extract_button:
        if not api_health:
            st.error("❌ Cannot proceed: API server is not available")
        else:
            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # Prepare files
                status_text.text("📤 Uploading files...")
                progress_bar.progress(10)

                files_data = [(f.name, f.getvalue()) for f in filled_files]

                # Prepare request
                status_text.text("🔄 Processing template...")
                progress_bar.progress(30)

                files_payload = [
                                    ("template",
                                     (template_file.name, io.BytesIO(template_file.getvalue()), "application/pdf"))
                                ] + [
                                    ("files", (name, io.BytesIO(data), "application/pdf"))
                                    for name, data in files_data
                                ]

                # Make request
                status_text.text("🤖 Extracting data with VLM...")
                progress_bar.progress(50)

                response = requests.post(
                    f"{API_URL}/extract",
                    data={"qualtrics_link": qualtrics_link},
                    files=files_payload,
                    timeout=config.REQUESTS_TIMEOUT * len(filled_files) * 2  # Longer timeout for batch
                )

                progress_bar.progress(90)

                if response.ok:
                    status_text.text("✅ Processing complete!")
                    progress_bar.progress(100)

                    result = response.json()

                    # Clear progress indicators
                    import time

                    time.sleep(0.5)
                    progress_bar.empty()
                    status_text.empty()

                    # Display results
                    st.success("🎉 Extraction completed successfully!")
                    st.divider()
                    display_results(result)

                    # Download all results
                    st.divider()
                    json_str = json.dumps(result, indent=2)
                    st.download_button(
                        label="📥 Download Complete Results (JSON)",
                        data=json_str,
                        file_name="extraction_results.json",
                        mime="application/json"
                    )
                else:
                    progress_bar.empty()
                    status_text.empty()
                    error_msg = response.json().get("error", "Unknown error") if response.text else "Server error"
                    st.error(f"❌ Extraction failed: {error_msg}")

                    with st.expander("Error Details"):
                        st.code(response.text)

            except requests.exceptions.Timeout:
                progress_bar.empty()
                status_text.empty()
                st.error("❌ Request timeout. The processing is taking longer than expected.")
                st.info("Try processing fewer files or check the API server logs.")

            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Unexpected error: {str(e)}")
                with st.expander("Error Details"):
                    st.exception(e)

else:
    st.info("👆 Please upload both a template PDF and at least one filled form PDF to begin extraction.")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>OCR-VLM PDF Form Extraction Service v2.0</p>
    <p>Powered by Vision Language Models</p>
</div>
""", unsafe_allow_html=True)
