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
