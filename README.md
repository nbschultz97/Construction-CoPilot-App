# Construction Doc Copilot (MVP)

Local RAG app for contractors: drag in PDFs, ask questions, get answers **with citations** to (filename, page).

## One-click run (local)

```bash
./run.sh
# Open http://localhost:8501
```

## Docker

```bash
docker compose up --build
# UI: http://localhost:8501  API: http://localhost:8000
```

## Static web deployment (GitHub Pages friendly)

The repository ships with a zero-dependency browser client under `ui/web`. It speaks directly to the FastAPI backend over CORS, so you can expose the full workflow (health check, document ingest, Q&A with previews) from any static host.

### Local preview

```bash
python -m http.server 8080 --directory ui/web
# Open http://localhost:8080 and point it at your API
```

### GitHub Pages (recommended)

1. Decide where the API will live. When serving the static page from an HTTPS origin (GitHub Pages), the API should also be reachable over HTTPS to avoid mixed-content blocking.
2. Copy the contents of `ui/web/` into a `docs/` folder (or your `gh-pages` branch) and enable GitHub Pages for that path.
3. Visit the published page, set the **API base URL** in the banner (or append `?api=https://your-api.example.com` to the URL). The setting is cached in localStorage for returning operators.

The web client mirrors the Streamlit feature set:

- `/healthz` probe with visual badges for storage/OCR status.
- ZIP or server-folder ingest with OCR toggle.
- Project registry viewer (backed by `/projects`).
- Retrieval UI that streams `/ask` answers and renders `/page_preview` images inline.

## OCR (optional)

- macOS: `brew install tesseract`
- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- Docker image already includes Tesseract.

## Troubleshooting

- API not reachable → check port 8000 in use, see `.api.log`
- OCR missing → install Tesseract or use Docker
- Empty answers → confirm docs in `project_docs/`, re-index from UI

## Feature matrix

| Feature | Status |
| --- | --- |
| Citations | ✅ |
| Local embeddings | ✅ |
| OCR (Tesseract) | ⚠️ if not installed |
| Config panel | ✅ |
| Docs table | ✅ |
| Export roadmap | 📋 |
