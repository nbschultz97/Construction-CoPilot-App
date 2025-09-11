import os, io, uuid
import fitz
from typing import Tuple
from tqdm import tqdm
from api.settings import settings
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import numpy as np

# Lazy init globals
_chroma_client = None
_collection_cache = {}
_embedder = None


def get_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(ChromaSettings(
            persist_directory=settings.CHROMA_DIR
        ))
    return _chroma_client


def get_collection(project_id: str):
    client = get_client()
    if project_id not in _collection_cache:
        _collection_cache[project_id] = client.get_or_create_collection(project_id)
    return _collection_cache[project_id]


def local_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embedder


def embed_texts(texts):
    from api.rag import openai_embed
    if os.getenv("EMBEDDINGS_PROVIDER", "openai") == "openai":
        return openai_embed(texts)
    # local
    model = local_embedder()
    vecs = model.encode(texts, normalize_embeddings=True)
    return vecs.tolist()


def ensure_dirs():
    os.makedirs(settings.DOCS_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)


def ocr_page_pix(page):
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img)


def ingest_pdf(path: str, project_id: str, do_ocr: bool) -> Tuple[int, int]:
    doc = fitz.open(path)
    pages = 0
    chunks = 0
    coll = get_collection(project_id)
    for pno in range(len(doc)):
        pages += 1
        page = doc.load_page(pno)
        text = page.get_text("text")
        if len(text.strip()) < 40 and do_ocr:
            text = ocr_page_pix(page)
        text = text.replace("\x00", " ").strip()
        if not text:
            continue
        # chunk
        words = text.split()
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk = " ".join(chunk_words)
            meta = {"source": os.path.basename(path), "page": pno + 1}
            # embed & upsert
            vec = embed_texts([chunk])[0]
            uid = f"{os.path.basename(path)}-{pno + 1}-{i}"
            coll.upsert(ids=[uid], embeddings=[vec], metadatas=[meta], documents=[chunk])
            chunks += 1
            i += (chunk_size - overlap)
    doc.close()
    return pages, chunks


def ingest_folder(folder: str, project_id: str, do_ocr: bool = False) -> Tuple[int, int, int]:
    ensure_dirs()
    files = 0
    total_pages = 0
    total_chunks = 0
    for root, _, fnames in os.walk(folder):
        for fn in fnames:
            if fn.lower().endswith(".pdf"):
                files += 1
                p, c = ingest_pdf(os.path.join(root, fn), project_id, do_ocr)
                total_pages += p
                total_chunks += c
    # persist
    get_client().persist()
    return files, total_pages, total_chunks


def save_zip_and_extract(upload, project_id: str) -> str:
    import zipfile, tempfile, shutil
    tmpdir = tempfile.mkdtemp()
    zpath = os.path.join(tmpdir, "upload.zip")
    with open(zpath, "wb") as f:
        f.write(upload)
    with zipfile.ZipFile(zpath, "r") as zip_ref:
        zip_ref.extractall(tmpdir)
    proj_dir = os.path.join(settings.DOCS_DIR, project_id)
    os.makedirs(proj_dir, exist_ok=True)
    # copy PDFs only
    for root, _, files in os.walk(tmpdir):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                src = os.path.join(root, fn)
                dst = os.path.join(proj_dir, fn)
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(src, "rb") as s, open(dst, "wb") as d:
                        d.write(s.read())
    return proj_dir
