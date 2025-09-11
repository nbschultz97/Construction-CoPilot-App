import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "openai")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    CHROMA_DIR = os.getenv("CHROMA_DIR", ".chroma")
    DOCS_DIR = os.getenv("DOCS_DIR", "./project_docs")
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    TOP_K = int(os.getenv("TOP_K", "6"))
    MIN_SCORE = float(os.getenv("MIN_SCORE", "0.24"))


settings = Settings()
