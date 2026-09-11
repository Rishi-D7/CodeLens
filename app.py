from __future__ import annotations

# Streamlit frontend for CodeLens.
# The FastAPI backend URL is configurable through CODELENS_API_URL.

from typing import Any
from html import escape
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
    st.set_page_config(
        page_title="CodeLens | Semantic Code Search",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --codelens-bg: #0b1120;
            --codelens-sidebar: #0f1728;
            --codelens-surface: #121c2f;
            --codelens-surface-raised: #16233a;
            --codelens-border: #25344b;
            --codelens-ink: #f4f7fb;
            --codelens-muted: #91a0b5;
            --codelens-accent: #7487ff;
            --codelens-accent-soft: #1b2750;
            --codelens-cyan: #58c7d9;
        }
        .stApp { background: var(--codelens-bg); color: var(--codelens-ink); }
        .block-container { max-width: 1180px; padding: 3rem 2rem 2.2rem; }
        [data-testid="stSidebar"] { background: var(--codelens-sidebar); border-right: 1px solid var(--codelens-border); }
        [data-testid="stSidebar"] .block-container { padding: 2.25rem 1.35rem; }
        [data-testid="stSidebar"], [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: var(--codelens-ink) !important; }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--codelens-muted) !important; }
        [data-testid="stSidebar"] input { background: #0b1425 !important; border-color: var(--codelens-border) !important; color: var(--codelens-ink) !important; }
        [data-testid="stSidebar"] input::placeholder { color: #718198 !important; }
        [data-testid="stSidebar"] button { border-radius: 6px; }
        [data-testid="stSidebar"] [data-testid="stAlert"] { background: var(--codelens-surface); }
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input { background: var(--codelens-surface) !important; border: 1px solid var(--codelens-border) !important; color: var(--codelens-ink) !important; }
        [data-testid="stTextInput"] input:focus { border-color: var(--codelens-accent) !important; box-shadow: 0 0 0 1px var(--codelens-accent) !important; }
        [data-testid="stTextInput"] input::placeholder { color: #718198 !important; }
        [data-testid="stSlider"] [role="slider"] { background: var(--codelens-accent); }
        .codelens-brand { align-items: center; display: flex; gap: 0.7rem; margin-bottom: 0.35rem; }
        .codelens-mark { align-items: center; background: var(--codelens-accent); border-radius: 6px; color: #08101e; display: inline-flex; font-size: 0.9rem; font-weight: 800; height: 2rem; justify-content: center; letter-spacing: -0.04em; width: 2rem; }
        .codelens-title { color: var(--codelens-ink); font-size: 1.35rem; font-weight: 750; letter-spacing: -0.02em; }
        .codelens-subtitle { color: var(--codelens-muted); font-size: 0.88rem; margin: 0 0 1rem 2.7rem; }
        .ready-status { color: var(--codelens-cyan); font-size: 0.76rem; font-weight: 650; letter-spacing: 0.02em; margin-bottom: 4.5rem; }
        .ready-dot { background: var(--codelens-cyan); border-radius: 50%; display: inline-block; height: 6px; margin: 0 0.35rem 1px 0; width: 6px; }
        .eyebrow { color: var(--codelens-accent); font-size: 0.7rem; font-weight: 750; letter-spacing: 0.14em; text-transform: uppercase; }
        .hero-title { color: var(--codelens-ink); font-size: clamp(2rem, 4vw, 3.3rem); font-weight: 760; letter-spacing: -0.045em; line-height: 1.04; margin: 0.65rem 0 0.65rem; }
        .hero-copy { color: var(--codelens-muted); font-size: 1.02rem; margin-bottom: 1.7rem; }
        .section-heading { color: var(--codelens-ink); font-size: 1.1rem; font-weight: 700; margin: 2.4rem 0 0.2rem; }
        .section-copy { color: var(--codelens-muted); margin-bottom: 0.8rem; }
        .indexed-card, .empty-card, .how-card { background: var(--codelens-surface); border: 1px solid var(--codelens-border); border-radius: 8px; }
        .indexed-card { color: var(--codelens-muted); font-size: 0.83rem; margin: 0 0 2.3rem; padding: 0.7rem 0.9rem; overflow-wrap: anywhere; }
        .indexed-card strong { color: var(--codelens-ink); }
        .empty-card { padding: 1.5rem 1.6rem; margin-top: 1rem; }
        .empty-title { color: var(--codelens-ink); font-size: 1.05rem; font-weight: 700; }
        .empty-copy { color: var(--codelens-muted); font-size: 0.9rem; margin-top: 0.35rem; }
        .result-summary { align-items: baseline; display: flex; gap: 0.55rem; margin: 2.2rem 0 0.9rem; }
        .result-summary-title { color: var(--codelens-ink); font-size: 1.15rem; font-weight: 700; }
        .result-summary-count { color: var(--codelens-muted); font-size: 0.84rem; }
        .result-card { background: var(--codelens-surface); border: 1px solid var(--codelens-border); border-radius: 8px; margin: 0.75rem 0 0; padding: 1rem 1.15rem 0.7rem; }
        .result-card.top-result { border-color: #4f62c7; box-shadow: 0 0 0 1px rgba(116, 135, 255, 0.12); }
        .result-header { align-items: flex-start; display: flex; gap: 0.85rem; }
        .result-rank { align-items: center; background: var(--codelens-accent-soft); border-radius: 5px; color: #aab5ff; display: flex; flex: 0 0 1.7rem; font-size: 0.78rem; font-weight: 750; height: 1.7rem; justify-content: center; }
        .result-file { color: var(--codelens-ink); font-size: 0.96rem; font-weight: 700; overflow-wrap: anywhere; padding-top: 0.15rem; }
        .result-meta { color: var(--codelens-muted); font-size: 0.78rem; margin: 0.3rem 0 0 2.55rem; }
        .code-label { color: #6f83a1; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; margin: 0.65rem 0 0.25rem; text-transform: uppercase; }
        .how-card { padding: 1.15rem 1.25rem; margin-top: 0.85rem; }
        .how-title { color: var(--codelens-ink); font-size: 1rem; font-weight: 700; }
        .how-copy { color: var(--codelens-muted); font-size: 0.84rem; margin-top: 0.35rem; }
        .pipeline { align-items: center; color: var(--codelens-ink); display: flex; flex-wrap: wrap; font-size: 0.82rem; gap: 0.4rem; margin-top: 0.8rem; }
        .pipeline-step { background: #182641; border: 1px solid var(--codelens-border); border-radius: 5px; padding: 0.45rem 0.55rem; }
        .pipeline-arrow { color: var(--codelens-cyan); }
        .footer { border-top: 1px solid var(--codelens-border); color: #6f7e94; font-size: 0.76rem; margin-top: 3rem; padding-top: 1rem; text-align: center; }
        [data-testid="stCodeBlock"] { border: 1px solid var(--codelens-border); border-radius: 6px; margin-top: 0; }
        [data-testid="stMetric"] { background: var(--codelens-surface); border: 1px solid var(--codelens-border); border-radius: 7px; padding: 0.75rem; }
        @media (max-width: 640px) {
            .block-container { padding: 2rem 1rem 1.5rem; }
            .ready-status { margin-bottom: 2.5rem; }
            .hero-title { font-size: 2.25rem; }
            .pipeline { align-items: flex-start; flex-direction: column; }
            .pipeline-arrow { display: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown('<div class="eyebrow">Repository</div>', unsafe_allow_html=True)
        st.markdown("### Index a workspace")
        st.caption("Use a local path or a public GitHub URL.")
        repo_path = st.text_input("Repository path / GitHub URL", value=".")
        if st.button("Index repository", type="primary", use_container_width=True):
            if not repo_path.strip():
                st.warning("Enter a repository path or GitHub URL first.")
            else:
                with st.spinner("Indexing repository..."):
                    try:
                        result = index_repository(repo_path)
                        st.session_state["indexed_repository"] = result.get("indexed_repository", repo_path)
                        st.session_state.pop("search_results", None)
                        st.success("Repository indexed")
                    except requests.exceptions.RequestException as exc:
                        response = getattr(exc, "response", None)
                        if response is not None:
                            try:
                                detail = response.json()
                            except ValueError:
                                detail = str(exc)
                        else:
                            detail = "Could not reach the CodeLens backend."
                        st.error(f"Indexing failed: {detail}")

    st.markdown(
        '<div class="codelens-brand"><span class="codelens-mark">CL</span><span class="codelens-title">CodeLens</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="codelens-subtitle">Semantic code search for unfamiliar repositories.</div><div class="ready-status"><span class="ready-dot"></span>Semantic search &nbsp;•&nbsp; Ready</div>',
        unsafe_allow_html=True,
    )

    indexed_repository = st.session_state.get("indexed_repository")
    if indexed_repository:
        st.markdown(
            f'<div class="indexed-card"><strong>Indexed repository</strong><br>{escape(str(indexed_repository))}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="eyebrow">Semantic search</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Understand any codebase.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Ask questions in plain English and jump directly to the most relevant code.</div>',
        unsafe_allow_html=True,
    )
    query = st.text_input(
        "Search query",
        placeholder="Where is repository scanning implemented?",
        label_visibility="collapsed",
    )
    search_options = st.columns([3, 1])
    with search_options[0]:
        top_k = st.slider("Number of results", min_value=1, max_value=10, value=5)
    with search_options[1]:
        st.write("")
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if search_clicked:
        if not query.strip():
            st.warning("Enter a question to search the indexed codebase.")
        else:
            with st.spinner("Searching semantic index..."):
                try:
                    data = search_query(query, int(top_k))
                    st.session_state["search_results"] = data.get("results", [])
                except requests.exceptions.RequestException as exc:
                    st.error(f"Search request failed: {exc}")
                except Exception as exc:
                    st.error(f"Search failed: {exc}")

    results = st.session_state.get("search_results")
    if results is None:
        st.markdown(
            '<div class="empty-card"><div class="empty-title">Ready to explore.</div><div class="empty-copy">Index a repository, then ask a natural-language question to find relevant code.</div></div>',
            unsafe_allow_html=True,
        )
    elif not results:
        st.info("No matching code was found. Try a broader question or index another repository.")
    else:
        st.markdown(
            f'<div class="result-summary"><span class="result-summary-title">Relevant code passages</span><span class="result-summary-count">{len(results)} found</span></div>',
            unsafe_allow_html=True,
        )
        for rank, result in enumerate(results, start=1):
            file = escape(str(result.get("file", "Unknown file")))
            start = result.get("start_line") or "N/A"
            end = result.get("end_line") or "N/A"
            score = float(result.get("score", 0.0))
            content = result.get("content", "")
            card_class = "result-card top-result" if rank == 1 else "result-card"
            st.markdown(
                f'<div class="{card_class}"><div class="result-header"><div class="result-rank">{rank:02d}</div><div class="result-file">{file}</div></div><div class="result-meta">Lines {start}–{end} &nbsp; • &nbsp; Similarity {score:.4f}</div><div class="code-label">Code excerpt</div></div>',
                unsafe_allow_html=True,
            )
            st.code(content)

    st.markdown('<div class="section-heading">How CodeLens works</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="how-card"><div class="how-title">From repository to ranked answers.</div><div class="how-copy">CodeLens uses transformer embeddings and vector similarity instead of simple keyword matching.</div><div class="pipeline"><span class="pipeline-step">Repository</span><span class="pipeline-arrow">→</span><span class="pipeline-step">Code chunks</span><span class="pipeline-arrow">→</span><span class="pipeline-step">Transformer embeddings</span><span class="pipeline-arrow">→</span><span class="pipeline-step">FAISS vector search</span><span class="pipeline-arrow">→</span><span class="pipeline-step">Ranked semantic results</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="footer">CodeLens • Semantic code search for developers</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
