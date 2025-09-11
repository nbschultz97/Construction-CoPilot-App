# Construction Doc Copilot (MVP)

Local RAG app for contractors: drag in PDFs, ask questions, get answers **with citations** to (filename, page).

## Quick start

```bash
cp .env.example .env
# (optional) put your OPENAI_API_KEY in .env

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start API
uvicorn api.app:app --reload --port 8000

# In a new terminal, start UI
streamlit run ui/app.py --server.port 8501

Open UI at http://localhost:8501

Docker (optional)

cp .env.example .env
# add OPENAI_API_KEY if using OpenAI

docker compose up --build

Notes
•Data stays local in `.chroma/` and `project_docs/`.
•If no OPENAI_API_KEY is set, the app uses:
•local embeddings via sentence-transformers (BAAI/bge-small-en-v1.5)
•an “extractive” answer mode (returns best snippet + citations)
•OCR is attempted for low-text pages if Tesseract is installed; otherwise skipped.
