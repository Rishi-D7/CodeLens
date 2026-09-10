from __future__ import annotations

"""Streamlit frontend for CodeLens.

This app talks to the FastAPI backend at http://127.0.0.1:8000 to index a
repository and perform semantic code search. It uses `requests` for HTTP calls
and keeps UI logic separate from the backend search/indexing logic.
"""

from typing import Any
import os

import requests
import streamlit as st

# Read backend URL from environment, default to local server
API_BASE = os.getenv("CODELENS_API_URL", "http://127.0.0.1:8000")


def index_repository(repo_path: str) -> dict[str, Any]:
    """Call the backend /index endpoint to index the given repository.

    Returns the parsed JSON response on success, otherwise raises an
    exception with a helpful message.
    """
    url = f"{API_BASE}/index"
    resp = requests.post(url, json={"repo_path": repo_path}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def search_query(q: str, top_k: int) -> dict[str, Any]:
    """Call the backend /search endpoint and return parsed JSON results."""
    url = f"{API_BASE}/search"
    params = {"q": q, "top_k": top_k}
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    st.set_page_config(page_title="CodeLens — Semantic Code Search")
    st.title("CodeLens — Semantic Code Search")

    st.write("Search a codebase using natural-language questions.\n"
             "Index a repository first, then ask questions about the code.")

    repo_path = st.text_input("Repository path", value=".")

    if st.button("Index Repository"):
        if not repo_path:
            st.error("Please provide a repository path.")
        else:
            with st.spinner("Indexing repository — this may take a while..."):
                try:
                    result = index_repository(repo_path)
                    st.success(f"Indexed: {result.get('indexed_repository')}")
                except requests.exceptions.RequestException as exc:
                    # Try to surface backend error message when available
                    msg = getattr(exc, "response", None)
                    if msg is not None:
                        try:
                            err = exc.response.json()
                            st.error(f"Indexing failed: {err}")
                        except Exception:
                            st.error(f"Indexing failed: {exc}")
                    else:
                        st.error(f"Indexing failed: {exc}")

    st.markdown("---")

    query = st.text_input("Ask a question about your code")
    top_k = st.number_input("Number of results", min_value=1, max_value=10, value=5, step=1)

    if st.button("Search"):
        if not query:
            st.error("Please enter a question to search the codebase.")
        else:
            with st.spinner("Searching..."):
                try:
                    data = search_query(query, int(top_k))
                    results = data.get("results", [])
                    if not results:
                        st.info("No results found.")
                    for r in results:
                        file = r.get("file", "")
                        start = r.get("start_line")
                        end = r.get("end_line")
                        score = r.get("score", 0.0)
                        content = r.get("content", "")

                        st.subheader(file)
                        st.write(f"Lines: {start or 'N/A'} - {end or 'N/A'}")
                        st.write(f"Similarity: {float(score):.4f}")
                        st.code(content)
                except requests.exceptions.RequestException as exc:
                    st.error(f"Search request failed: {exc}")
                except Exception as exc:
                    st.error(f"Search failed: {exc}")


if __name__ == "__main__":
    main()
