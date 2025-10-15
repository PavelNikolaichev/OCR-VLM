import streamlit as st
import requests
import io
# Add quadricks link -> download and map into pdf json schema.
# Add semaphore for sending the pdf pages to the api. Upload only one pdf file with many pages -> 1 page = 1 form.
# Add docker containers.
st.title("PDF Form Extraction with Template")
st.write("Upload a template PDF and filled form PDFs. The template will be used to generate a JSON schema for extracting answers from the filled forms.")
template_file = st.file_uploader("Template PDF (form)", type=["pdf"], accept_multiple_files=False)
filled_files = st.file_uploader("Filled Form PDFs", type=["pdf"], accept_multiple_files=True)
if template_file and filled_files:
    if st.button("Extract Answers"):
        files = [(f.name, f.getvalue()) for f in filled_files]
        response = requests.post(
            "http://127.0.0.1:8000/extract",
            files=[
                ("template", (template_file.name, io.BytesIO(template_file.getvalue()), "application/pdf"))
            ] + [
                ("files", (name, io.BytesIO(data), "application/pdf")) for name, data in files
            ]
        )
        if response.ok:
            resp_json = response.json()
            st.subheader("Generated JSON Schema")
            st.code(resp_json["json_schema"])
            st.subheader("Extracted Answers")
            for r in resp_json["results"]:
                st.markdown(f"**{r['filename']}**")
                st.code(r["answers"])
        else:
            st.error(f"API error: {response.text}")
