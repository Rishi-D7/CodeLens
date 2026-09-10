from __future__ import annotations

from typing import List, Optional
from tempfile import TemporaryDirectory

from git import GitCommandError, Repo

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from core.embeddings import EmbeddingModel
from core.search import CodeSearchEngine


class IndexRequest(BaseModel):
	repo_path: str


class IndexResponse(BaseModel):
	status: str
	indexed_repository: str


class SearchResult(BaseModel):
	file: str
	start_line: Optional[int]
	end_line: Optional[int]
	score: float
	content: str


class SearchResponse(BaseModel):
	results: List[SearchResult]


app = FastAPI()

# Globals populated at startup
_embedder: Optional[EmbeddingModel] = None
_engine: Optional[CodeSearchEngine] = None


@app.on_event("startup")
def _startup() -> None:
	"""Initialize the embedding model and search engine once on startup."""
	global _embedder, _engine
	_embedder = EmbeddingModel()
	_engine = CodeSearchEngine(_embedder)


@app.post("/index", response_model=IndexResponse)
def index_repo(body: IndexRequest) -> IndexResponse:
	"""Index the repository at `repo_path` using the engine's pipeline."""
	global _engine
	if _engine is None:
		raise HTTPException(status_code=503, detail="Search engine not initialized")

	repo_path = body.repo_path.strip()
	# If a GitHub HTTP(S) URL is provided, clone it into a temporary directory
	if repo_path.startswith("https://github.com/") or repo_path.startswith("http://github.com/"):
		try:
			with TemporaryDirectory() as tmpdir:
				try:
					Repo.clone_from(repo_path, tmpdir)
				except GitCommandError as exc:
					# Could not clone — treat as a bad request with an explanatory message
					raise HTTPException(status_code=400, detail=f"Failed to clone repository: {exc}")
				# Build the index from the cloned repository directory
				try:
					_engine.build_from_repository(tmpdir)
				except Exception as exc:
					# Indexing failed after successful clone
					raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")
		except HTTPException:
			# Re-raise known HTTP errors
			raise
		except Exception as exc:
			# Unexpected failures (tempdir creation, permissions, etc.)
			raise HTTPException(status_code=500, detail=f"Failed to prepare clone: {exc}")
		# Return the original URL as the indexed repository identifier
		return IndexResponse(status="ok", indexed_repository=repo_path)

	# Otherwise treat `repo_path` as a local filesystem path and index in-place
	try:
		_engine.build_from_repository(repo_path)
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")

	return IndexResponse(status="ok", indexed_repository=repo_path)


@app.get("/search", response_model=SearchResponse)
def search(q: str = Query(..., description="Search query"), top_k: int = Query(5, ge=1)) -> SearchResponse:
	"""Search the indexed repository for `q` and return top_k results."""
	global _engine
	if _engine is None:
		raise HTTPException(status_code=503, detail="Search engine not initialized")

	try:
		raw = _engine.search(q, top_k=top_k)
	except RuntimeError as exc:
		raise HTTPException(status_code=400, detail=str(exc))
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Search failed: {exc}")

	results: List[SearchResult] = []
	for r in raw:
		results.append(
			SearchResult(
				file=r.get("file", ""),
				start_line=r.get("start_line"),
				end_line=r.get("end_line"),
				score=float(r.get("score", 0.0)),
				content=r.get("content", ""),
			)
		)

	return SearchResponse(results=results)


@app.get("/health")
def health() -> dict:
	"""Health check endpoint."""
	return {"status": "ok"}

