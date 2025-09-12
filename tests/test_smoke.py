import requests
from pathlib import Path

def test_smoke_run_and_health():
    r = requests.get("http://localhost:8000/healthz", timeout=10)
    assert r.ok
    j = r.json()
    assert j.get("api") == "ok"

def test_demo_doc_present():
    assert Path("sample_docs/demo.pdf").exists()
