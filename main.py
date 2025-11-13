import io
import json

import requests
import streamlit as st

# Add quadricks link -> download and map into pdf json schema.
# Add semaphore for sending the pdf pages to the api. Upload only one pdf file with many pages -> 1 page = 1 form.
st.title("PDF Form Extraction with Template")
st.write(
    "Upload a template PDF and filled form PDFs. The template will be used to generate a JSON schema for extracting answers from the filled forms.")
template_file = st.file_uploader("Template PDF (form)", type=["pdf"], accept_multiple_files=False)
filled_files = st.file_uploader("Filled Form PDFs", type=["pdf"], accept_multiple_files=True)
qualtrics_link = st.text_input("Qualtrics Link", help="Provide a Qualtrics link to the empty survey to map fields.")

if template_file and filled_files:
    if st.button("Extract Answers"):
        files = [(f.name, f.getvalue()) for f in filled_files]
        response = requests.post(
            "http://127.0.0.1:8000/extract",
            data={"qualtrics_link": qualtrics_link},
            files=[
                      ("template", (template_file.name, io.BytesIO(template_file.getvalue()), "application/pdf"))
                  ] + [
                      ("files", (name, io.BytesIO(data), "application/pdf")) for name, data in files
                  ]
        )
        if response.ok:
            resp_json = response.json()
            st.subheader("Server received Qualtrics link")
            st.write(resp_json.get("received_qualtrics_link"))

            st.subheader("Generated JSON Schemas")
            st.code(json.dumps(resp_json.get("json_schemas"), indent=2))

            st.subheader("Extracted Answers")
            for r in resp_json.get("results", []):
                st.markdown(f"**{r.get('filename')}**")
                for page in r.get('pages', []):
                    if 'error' in page:
                        st.error(page['error'])
                    else:
                        st.write(f"Page {page.get('page_index')}")
                        st.code(json.dumps(page.get('answers'), indent=2))
        else:
            st.error(f"API error: {response.text}")
