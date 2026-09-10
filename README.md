# CodeLens — Semantic Code Search

CodeLens is a lightweight semantic code search engine that lets developers ask natural-language questions about a local source-code repository and quickly retrieve the most relevant code sections.

## Problem statement

Large or unfamiliar codebases make it hard to find the right code quickly. Keyword search often returns many irrelevant matches, and understanding where a feature or check lives may require reading many files and following call chains. Developers need a faster, context-aware way to find the most relevant code fragments using natural language.

## Solution

CodeLens solves this by converting code fragments into dense vector embeddings and using nearest-neighbor search to surface semantically relevant code sections for a natural-language query. This helps developers locate functionality, checks, or examples even when they don't know the exact identifier names.

## How it works

Pipeline:

- Repository (local path provided to the app)
- source-code parsing (scan repository for supported files)
- chunking (split files into manageable line-based chunks)
- Sentence Transformer embeddings (generate vector embeddings for chunks)
- FAISS similarity search (fast nearest-neighbor search over embeddings)
- FastAPI (backend exposing /index and /search)
- Streamlit (simple frontend to index and query the repository)

The current implementation runs locally and accepts a path to a repository on the same machine.

## Key features

- Natural-language search over code
- Line-based chunking so results point to exact ranges
- Uses transformer embeddings and FAISS for semantic search
- Simple REST API and a beginner-friendly Streamlit UI

## Tech stack

- Python 3.11+ (development)
- sentence-transformers (embedding model)
- numpy
- faiss (IndexFlatIP for inner-product similarity)
- FastAPI (backend)
- Streamlit (frontend)
- requests (frontend→backend HTTP client)

## Project structure

Top-level files and directories in this repository:

- api.py — FastAPI application exposing /index and /search endpoints
- app.py — Streamlit frontend that talks to the FastAPI backend
- requirements.txt — Python dependencies
- test_parser.py — small script to exercise the repository scanner and chunker
- test_embeddings.py — small script to verify the embedding model
- test_search.py — small script to exercise the search pipeline
- core/
  - __init__.py
  - parser.py — repository scanner and `chunk_documents()` implementation
  - embeddings.py — `EmbeddingModel` wrapper loading a sentence-transformers model
  - search.py — `CodeSearchEngine` that builds FAISS indexes and searches

(Only the files above are part of the project source for the current version.)

## Installation and setup (Windows)

1. Clone the repository or copy the project files to a local folder.
2. Open PowerShell and navigate to the project folder:

```powershell
cd C:\path\to\CodeLens
```

3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

Notes: `faiss` may require platform-specific wheels. If you encounter issues installing `faiss`, consult the FAISS installation instructions for Windows or use an environment where FAISS is supported (Linux is commonly easier for FAISS setups).

## Running the FastAPI backend

Start the backend (from the project root):

```powershell
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

This exposes three endpoints used by the frontend:

- `POST /index` — body `{ "repo_path": "<local path>" }` to index a local repository path
- `GET /search?q=<query>&top_k=<n>` — search the indexed repository
- `GET /health` — health check

Indexing is performed in-process and stores embeddings in memory; the service expects a local repository path and does not persist the index to disk.

## Running the Streamlit frontend

With the backend running at `http://127.0.0.1:8000`, run the frontend:

```powershell
streamlit run app.py
```

The UI lets you enter a repository path (default `.`), click **Index Repository**, and then ask natural-language questions. The app will display top results with file path, line range, similarity score, and the code snippet.

If you need the frontend to talk to a remote backend URL, set the `CODELENS_API_URL` environment variable before launching Streamlit, for example:

```powershell
$env:CODELENS_API_URL = "http://backend-host:8000"
streamlit run app.py
```

## Example natural-language queries

- "Where is the password checked?"
- "Where do we connect to the database?"
- "Where is the payment processed?"
- "How is authentication implemented?"

These queries should return code fragments and the line ranges where the relevant logic appears.

## Architecture overview

CodeLens separates concerns into a small, testable pipeline:

- Parser (`core/parser.py`) discovers files and produces chunks with line ranges.
- Embeddings (`core/embeddings.py`) produce fixed-size vector representations using a sentence-transformer model.
- Search engine (`core/search.py`) builds a FAISS IndexFlatIP index over normalized embeddings and maps search results back to chunk metadata.
- FastAPI (`api.py`) exposes the indexing and search operations as simple REST endpoints.
- Streamlit (`app.py`) provides a minimal UI that calls the REST API.

## Testing

The repository includes small, manual test scripts:

- `test_parser.py` — runs `scan_repository()` and `chunk_documents()` and prints results
- `test_embeddings.py` — encodes two short texts and checks embedding shapes and normalization
- `test_search.py` — exercises the search engine (sample or real repository depending on the script variant)

Run these scripts directly with `python <script>.py` for quick checks.

## Future improvements

- Add persistent index storage and incremental re-indexing.
- Add authentication and access controls for multi-user deployments.
- Add an async job queue for indexing large repositories.
- Improve chunking heuristics using language-aware parsers (AST-based chunking).
- Add automated tests and CI configuration.
- Provide containerized deployment recipes for easier reproducibility.

---

If you have questions or want help running the project locally, open an issue or reach out — I can help with environment-specific setup notes.
