from pydantic import BaseModel
from typing import List, Optional


class IngestResponse(BaseModel):
    project_id: str
    files: int
    pages: int
    chunks: int


class AskRequest(BaseModel):
    project_id: str
    question: str
    top_k: int = 6


class Citation(BaseModel):
    source: str
    page: int
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
    used_chunks: int


class ProjectInfo(BaseModel):
    project_id: str
    docs: int
    chunks: int
