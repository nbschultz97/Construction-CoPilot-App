import os
import json
import requests
import streamlit as st
from pathlib import Path
from PIL import Image
from io import BytesIO

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Construction Doc Copilot", layout="wide")
st.title("👷 Construction Doc Copilot (MVP)")

# --- Sidebar: System Check ---
with st.sidebar:
    st.subheader("System check")
    health = None
    try:
        r = requests.get(f"{API_BASE}/healthz", timeout=5)
        if r.ok:
            health = r.json()
    except Exception as e:
        st.error(f"API not reachable at {API_BASE}: {e}")

    def badge(ok: bool, label: str):
        color = "✅" if ok else "⚠️"
        st.write(f"{color} {label}")

    if health:
        badge(True, "API reachable")
        badge(health.get("chroma", False), "Chroma writable")
        badge(health.get("ocr", False), "OCR (Tesseract)")
        st.write(f"Model: `{health.get('embedding_model')}`")
        st.write(f"Docs indexed: **{health.get('docs_indexed', 0)}**")
        if not health.get("ocr", False):
            st.info("OCR not detected. Install Tesseract to extract text from scans.")
    else:
        badge(False, "API reachable")
        st.stop()

# --- Settings ---
st.sidebar.subheader("Settings")
use_openai = st.sidebar.checkbox(
    "Use OpenAI embeddings (override local)",
    value=bool(os.getenv("OPENAI_API_KEY")),
)
chunk_size = st.sidebar.number_input(
    "Chunk size",
    value=int(os.getenv("CHUNK_SIZE", "800")),
    min_value=100,
    max_value=4000,
    step=50,
)
chunk_overlap = st.sidebar.number_input(
    "Chunk overlap",
    value=int(os.getenv("CHUNK_OVERLAP", "100")),
    min_value=0,
    max_value=1000,
    step=10,
)
top_k_setting = st.sidebar.number_input(
    "Top-K results",
    value=int(os.getenv("TOP_K", "5")),
    min_value=1,
    max_value=50,
    step=1,
)

if st.sidebar.button("Save settings"):
    env_path = Path(".env")
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    env["CHUNK_SIZE"] = str(chunk_size)
    env["CHUNK_OVERLAP"] = str(chunk_overlap)
    env["TOP_K"] = str(top_k_setting)
    if use_openai:
        env["EMBEDDING_BACKEND"] = "openai"
    else:
        env["EMBEDDING_BACKEND"] = "local"

    with env_path.open("w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    st.success("Settings saved to .env")

# --- Ingest PDFs ---
st.sidebar.header("Ingest PDFs")
up = st.sidebar.file_uploader("ZIP of PDFs", type=["zip"])
folder_hint = st.sidebar.text_input("OR local folder path (server-side)", "")
pid = st.sidebar.text_input("Project ID (optional)", "")
ocr = st.sidebar.checkbox("Enable OCR for scanned pages", value=False)
if st.sidebar.button("Ingest"):
    data = {"project_id": pid, "ocr": str(ocr).lower()}
    files = None
    if up is not None:
        files = {"zipfile": (up.name, up.getvalue(), "application/zip")}
        r = requests.post(f"{API_BASE}/ingest", data=data, files=files, timeout=600)
    elif folder_hint:
        data["folder_path"] = folder_hint
        r = requests.post(f"{API_BASE}/ingest", data=data, timeout=600)
    else:
        st.error("Provide a ZIP or a folder path.")
        r = None
    if r is not None:
        if r.ok:
            resp = r.json()
            st.success(
                f"Ingested: {resp['files']} files, {resp['pages']} pages, {resp['chunks']} chunks. Project: {resp['project_id']}"
            )
            st.session_state["project_id"] = resp["project_id"]
        else:
            st.error(r.text)

# --- Documents Table ---
st.subheader("Project documents")
docs_dir = Path("project_docs")
docs_dir.mkdir(exist_ok=True)
files = sorted([p for p in docs_dir.iterdir() if p.is_file()])

if files:
    for p in files:
        cols = st.columns([6, 2, 1, 1])
        with cols[0]:
            st.write(f"**{p.name}**  \n{p.stat().st_size/1024:.1f} KB")
        with cols[2]:
            if st.button("Re-index", key=f"reidx-{p.name}"):
                # TODO: call your existing ingest API for this file/path
                # requests.post(f"{API_BASE}/ingest", json={"path": str(p)})
                st.info("Re-index requested (wire to ingest endpoint).")
        with cols[3]:
            if st.button("Delete", key=f"del-{p.name}"):
                try:
                    p.unlink()
                    st.success(f"Deleted {p.name}. Re-run indexing if needed.")
                except Exception as e:
                    st.error(f"Delete failed: {e}")
else:
    st.info("Drop or add files to the `project_docs/` folder to index.")

# --- Ask Section ---
st.header("Ask your documents")
project_id = st.text_input("Project ID", st.session_state.get("project_id", ""))
question = st.text_input("Your question", "When is substantial completion required?")
top_k = st.slider("Top K", 1, 12, int(top_k_setting))
if st.button("Ask"):
    if not project_id:
        st.error("Enter a project_id.")
    else:
        r = requests.post(
            f"{API_BASE}/ask",
            json={"project_id": project_id, "question": question, "top_k": top_k},
            timeout=180,
        )
        if r.ok:
            data = r.json()
            st.subheader("Answer")
            st.write(data["answer"])
            st.subheader("Citations")
            for c in data["citations"]:
                st.write(f"- [{c['source']} p.{c['page']}] (score: {c['score']:.2f})")
                params = {"source": c["source"], "page": c["page"], "project_id": project_id}
                img = requests.get(f"{API_BASE}/page_preview", params=params, timeout=60)
                if img.ok:
                    image = Image.open(BytesIO(img.content))
                    st.image(image, caption=f"{c['source']} p.{c['page']}", use_column_width=True)
                else:
                    st.error(r.text)

st.caption("Tip: upload a ZIP of spec book + contract + addenda for best results.")
