import os
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List
from api.models import IngestResponse, AskRequest, AskResponse, ProjectInfo
from api.settings import settings
from api import ingest as ing
from api import rag
import fitz
import io

app = FastAPI(title="Construction Doc Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# In-memory registry of projects (lightweight)
_PROJECT_INDEX = {}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- helper checks ---
def _has_tesseract() -> bool:
    return shutil.which("tesseract") is not None


def _chroma_writable() -> bool:
    p = Path(".chroma")
    try:
        p.mkdir(parents=True, exist_ok=True)
        testfile = p / ".write_test"
        with open(testfile, "w") as f:
            f.write("ok")
        testfile.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _docs_indexed_count() -> int:
    d = Path("project_docs")
    if not d.exists():
        return 0
    return sum(1 for x in d.iterdir() if x.is_file())


@app.get("/healthz")
def healthz():
    embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    return {
        "api": "ok",
        "chroma": _chroma_writable(),
        "ocr": _has_tesseract(),
        "embedding_model": embedding_model,
        "docs_indexed": _docs_indexed_count(),
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(
    zipfile: Optional[UploadFile] = File(default=None),
    folder_path: Optional[str] = Form(default=None),
    project_id: Optional[str] = Form(default=None),
    ocr: bool = Form(default=False)
):
    pid = project_id or str(uuid.uuid4())
    if zipfile is None and not folder_path:
        raise HTTPException(status_code=400, detail="Provide a zip file or folder_path.")
    if zipfile:
        content = await zipfile.read()
        proj_dir = ing.save_zip_and_extract(content, pid)
    else:
        proj_dir = folder_path
    files, pages, chunks = ing.ingest_folder(proj_dir, pid, do_ocr=ocr)
    _PROJECT_INDEX[pid] = {"docs": files, "chunks": chunks}
    return IngestResponse(project_id=pid, files=files, pages=pages, chunks=chunks)


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    ans = rag.answer(req.project_id, req.question, req.top_k)
    return AskResponse(**ans)


@app.get("/projects", response_model=List[ProjectInfo])
def projects():
    out = []
    for pid, meta in _PROJECT_INDEX.items():
        out.append(ProjectInfo(project_id=pid, docs=meta["docs"], chunks=meta["chunks"]))
    return out


@app.get("/page_preview")
def page_preview(source: str, page: int, project_id: str):
    # Render a single PDF page as PNG stream
    pdf_path = None
    base = os.path.join(settings.DOCS_DIR, project_id)
    for root, _, files in os.walk(base):
        for fn in files:
            if fn == source:
                pdf_path = os.path.join(root, fn)
                break
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Source not found.")
    doc = fitz.open(pdf_path)
    if page < 1 or page > len(doc):
        doc.close()
        raise HTTPException(status_code=400, detail="Invalid page.")
    p = doc.load_page(page - 1)
    pix = p.get_pixmap(matrix=fitz.Matrix(2, 2))
    bio = io.BytesIO()
    bio.write(pix.tobytes("png"))
    bio.seek(0)
    doc.close()
    return StreamingResponse(bio, media_type="image/png")
