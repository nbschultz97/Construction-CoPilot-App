import streamlit as st
import requests, os
from PIL import Image
from io import BytesIO

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Construction Doc Copilot", layout="wide")
st.title("👷 Construction Doc Copilot (MVP)")

with st.sidebar:
    st.header("Ingest PDFs")
    up = st.file_uploader("ZIP of PDFs", type=["zip"])
    folder_hint = st.text_input("OR local folder path (server-side)", "")
    col1, col2 = st.columns(2)
    pid = st.text_input("Project ID (optional)", "")
    ocr = st.checkbox("Enable OCR for scanned pages", value=False)
    if st.button("Ingest"):
        data = {"project_id": pid, "ocr": str(ocr).lower()}
        files = None
        if up is not None:
            files = {"zipfile": (up.name, up.getvalue(), "application/zip")}
            r = requests.post(f"{API}/ingest", data=data, files=files, timeout=600)
        elif folder_hint:
            data["folder_path"] = folder_hint
            r = requests.post(f"{API}/ingest", data=data, timeout=600)
        else:
            st.error("Provide a ZIP or a folder path.")
            r = None
        if r is not None:
            if r.ok:
                resp = r.json()
                st.success(f"Ingested: {resp['files']} files, {resp['pages']} pages, {resp['chunks']} chunks. Project: {resp['project_id']}")
                st.session_state["project_id"] = resp["project_id"]
            else:
                st.error(r.text)

st.header("Ask your documents")
project_id = st.text_input("Project ID", st.session_state.get("project_id", ""))
question = st.text_input("Your question", "When is substantial completion required?")
top_k = st.slider("Top K", 1, 12, 6)
if st.button("Ask"):
    if not project_id:
        st.error("Enter a project_id.")
    else:
        r = requests.post(f"{API}/ask", json={"project_id": project_id, "question": question, "top_k": top_k}, timeout=180)
        if r.ok:
            data = r.json()
            st.subheader("Answer")
            st.write(data["answer"])
            st.subheader("Citations")
            for c in data["citations"]:
                st.write(f"- [{c['source']} p.{c['page']}] (score: {c['score']:.2f})")
                # preview
                params = {"source": c["source"], "page": c["page"], "project_id": project_id}
                img = requests.get(f"{API}/page_preview", params=params, timeout=60)
                if img.ok:
                    image = Image.open(BytesIO(img.content))
                    st.image(image, caption=f"{c['source']} p.{c['page']}", use_column_width=True)
                else:
                    st.error(r.text)

st.caption("Tip: upload a ZIP of spec book + contract + addenda for best results.")
