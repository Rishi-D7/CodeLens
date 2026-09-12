from __future__ import annotations

# Streamlit frontend for CodeLens.
# The FastAPI backend URL is configurable through CODELENS_API_URL.

from html import escape
import os
from typing import Any

import requests
import streamlit as st


# Read backend URL from environment, default to local server.
API_BASE = os.getenv("CODELENS_API_URL", "http://127.0.0.1:8000")

EXAMPLE_QUERIES = (
	"Where is authentication handled?",
	"Where are API requests handled?",
	"How are embeddings generated?",
)


def index_repository(repo_path: str) -> dict[str, Any]:
	"""Call the backend /index endpoint to index the given repository."""
	url = f"{API_BASE}/index"
	resp = requests.post(url, json={"repo_path": repo_path}, timeout=300)
	resp.raise_for_status()
	return resp.json()


def search_query(q: str, top_k: int) -> dict[str, Any]:
	"""Call the backend /search endpoint and return parsed JSON results."""
	url = f"{API_BASE}/search"
	params = {"q": q, "top_k": top_k}
	resp = requests.get(url, params=params, timeout=300)
	resp.raise_for_status()
	return resp.json()


def _request_error_detail(exc: requests.exceptions.RequestException) -> str:
	"""Return a useful, compact API error message for the status panel."""
	response = getattr(exc, "response", None)
	if response is not None:
		try:
			detail = response.json().get("detail")
			if detail:
				return str(detail)
		except (ValueError, AttributeError):
			pass
	return "Could not reach the CodeLens backend. Check that the API is running."


def _logo(mark_only: bool = False) -> str:
	"""Return the CodeLens geometric lens-and-code mark."""
	mark = (
		'<span class="logo-mark" aria-hidden="true">'
		'<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
		'<path d="M11.5 8.5 7 12v8l4.5 3.5M20.5 8.5 25 12v8l-4.5 3.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
		'<path d="M17.8 11.3a6.1 6.1 0 1 0 0 9.4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>'
		'<circle cx="21.6" cy="21.4" r="1.35" fill="currentColor"/>'
		'</svg></span>'
	)
	if mark_only:
		return mark
	return f'<div class="brand">{mark}<span class="brand-name">Code<span>Lens</span></span></div>'


def _state_surface(state: str, title: str, message: str) -> None:
	"""Render an intentional empty or error state without Streamlit chrome."""
	st.markdown(
		f'<div class="state-surface {state}"><span class="state-surface-dot"></span><div><div class="state-title">{escape(title)}</div><div class="state-copy">{escape(message)}</div></div></div>',
		unsafe_allow_html=True,
	)


def _loading_surface(title: str, message: str) -> Any:
	"""Return a placeholder for a compact CSS-only loading state."""
	loading = st.empty()
	loading.markdown(
		f'<div class="loading-surface"><span class="loading-bars" aria-hidden="true"><i></i><i></i><i></i></span><div><div class="state-title">{escape(title)}</div><div class="state-copy">{escape(message)}</div></div></div>',
		unsafe_allow_html=True,
	)
	return loading


def _render_repository(indexed_repository: Any) -> None:
	"""Render repository controls while preserving the existing index workflow."""
	st.markdown(
		'<div class="section-kicker">REPOSITORY</div><h2 class="workspace-heading">Choose a codebase</h2>'
		'<p class="workspace-copy">Index a local repository or public GitHub URL to make its implementation searchable.</p>',
		unsafe_allow_html=True,
	)
	repository_columns = st.columns([4, 1.35], gap="medium")
	with repository_columns[0]:
		repo_path = st.text_input(
			"Repository path or GitHub URL",
			value=".",
			placeholder="C:/projects/my-repository or https://github.com/...",
			label_visibility="collapsed",
		)
	with repository_columns[1]:
		st.markdown('<div class="button-spacer"></div>', unsafe_allow_html=True)
		index_clicked = st.button("Index repository", type="primary", use_container_width=True)

	indexing_state = st.session_state.get("indexing_state", "idle")
	if index_clicked:
		if not repo_path.strip():
			st.session_state["indexing_state"] = "error"
			st.session_state["indexing_error"] = "Enter a repository path or GitHub URL first."
		else:
			st.session_state["indexing_state"] = "indexing"
			loading = _loading_surface("Indexing repository", "Scanning files and preparing semantic search.")
			try:
				result = index_repository(repo_path)
				st.session_state["indexed_repository"] = result.get("indexed_repository", repo_path)
				st.session_state["indexing_state"] = "success"
				st.session_state.pop("search_results", None)
				st.session_state["search_state"] = "idle"
			except requests.exceptions.RequestException as exc:
				st.session_state["indexing_state"] = "error"
				st.session_state["indexing_error"] = _request_error_detail(exc)
			except Exception as exc:
				st.session_state["indexing_state"] = "error"
				st.session_state["indexing_error"] = f"Indexing failed: {exc}"
			finally:
				loading.empty()

	indexing_state = st.session_state.get("indexing_state", "idle")
	if indexing_state == "indexing":
		_state_surface("progress", "Indexing in progress", "Scanning files and preparing semantic search.")
	elif indexing_state == "error":
		_state_surface("error", "Indexing unavailable", st.session_state.get("indexing_error", "Check the repository path and try again."))
	elif indexed_repository:
		_state_surface("success", "Repository ready for semantic search", str(indexed_repository))
	else:
		_state_surface("empty", "No repository indexed", "Add a local path or public GitHub URL above to begin.")


def _render_search(indexed_repository: Any) -> None:
	"""Render the primary natural-language search workflow."""
	st.markdown(
		'<div class="section-kicker">SEMANTIC CODE SEARCH</div>'
		'<h1 class="hero-title">Understand any codebase.</h1>'
		'<p class="hero-copy">Find the implementation you need without knowing where it lives.</p>',
		unsafe_allow_html=True,
	)
	st.markdown('<div class="search-shell">', unsafe_allow_html=True)
	st.markdown('<div class="search-label">Ask a question about your codebase</div>', unsafe_allow_html=True)
	query_columns = st.columns([5, 1.2], gap="small")
	with query_columns[0]:
		query = st.text_input(
			"Search query",
			placeholder="Ask anything about your codebase...",
			label_visibility="collapsed",
			key="search_query",
		)
	with query_columns[1]:
		st.markdown('<div class="button-spacer"></div>', unsafe_allow_html=True)
		search_clicked = st.button("Search", type="primary", use_container_width=True, disabled=not bool(indexed_repository))
	st.markdown('<div class="suggestion-label">Try asking</div>', unsafe_allow_html=True)
	suggestion_columns = st.columns(3, gap="small")
	for column, suggestion in zip(suggestion_columns, EXAMPLE_QUERIES):
		with column:
			if st.button(suggestion, key=f"suggestion_{suggestion}", use_container_width=True):
				st.session_state["search_query"] = suggestion
	st.markdown('</div>', unsafe_allow_html=True)

	controls = st.columns([1, 4], gap="medium")
	with controls[0]:
		top_k = st.slider("Results", min_value=1, max_value=10, value=5, label_visibility="collapsed")
	with controls[1]:
		st.markdown('<p class="search-hint">Search natural language, a file path, or a behavior. Results are ranked by semantic similarity.</p>', unsafe_allow_html=True)

	if search_clicked:
		if not query.strip():
			st.session_state["search_state"] = "error"
			st.session_state["search_error"] = "Enter a question to search the indexed codebase."
		else:
			st.session_state["search_state"] = "searching"
			loading = _loading_surface("Searching the codebase", "Comparing your question with the indexed implementation.")
			try:
				data = search_query(query, int(top_k))
				st.session_state["search_results"] = data.get("results", [])
				st.session_state["search_state"] = "complete"
			except requests.exceptions.RequestException as exc:
				st.session_state["search_state"] = "error"
				st.session_state["search_error"] = _request_error_detail(exc)
			except Exception as exc:
				st.session_state["search_state"] = "error"
				st.session_state["search_error"] = f"Search failed: {exc}"
			finally:
				loading.empty()

	results = st.session_state.get("search_results")
	search_state = st.session_state.get("search_state", "idle")
	if search_state == "searching":
		_state_surface("progress", "Searching the codebase", "Comparing your question with the indexed implementation.")
	elif search_state == "error":
		_state_surface("error", "Search unavailable", st.session_state.get("search_error", "Try again in a moment."))
	elif not indexed_repository:
		_render_empty_state("Index a repository and ask a question about its implementation.")
	elif results is None:
		_render_empty_state("Index complete. Start with an example above or ask about a function, file, or behavior.")
	elif not results:
		_state_surface("empty", "Nothing relevant found", "Try describing the behavior you are looking for in different words.")
	else:
		_render_results(results)


def _render_empty_state(message: str) -> None:
	"""Render the initial workspace state with a small semantic-search motif."""
	st.markdown(
		f'<div class="empty-workspace"><div class="empty-eyebrow">READY TO EXPLORE</div><div class="empty-title">Your codebase, made legible.</div><div class="empty-copy">{escape(message)}</div><div class="semantic-motif"><span class="motif-points"><i></i><i></i><i></i><b></b></span><span>[ repository ]</span><b class="flow-arrow">→</b><span>[ index ]</span><b class="flow-arrow">→</b><span>[ ask ]</span><b class="flow-arrow">→</b><span>[ find ]</span></div></div>',
		unsafe_allow_html=True,
	)


def _render_results(results: list[dict[str, Any]]) -> None:
	"""Render ranked code results using the existing response fields."""
	st.markdown(
		f'<div class="results-heading"><div><div class="section-kicker">SEARCH RESULTS</div><h2>Relevant implementation</h2></div><span class="result-count">{len(results)} match{"es" if len(results) != 1 else ""}</span></div>',
		unsafe_allow_html=True,
	)
	for rank, result in enumerate(results, start=1):
		file_path = escape(str(result.get("file", "Unknown file")))
		start = result.get("start_line") or "N/A"
		end = result.get("end_line") or "N/A"
		score = float(result.get("score", 0.0))
		match_percent = max(0.0, min(100.0, score * 100))
		content = result.get("content", "")
		card_class = "result-card top-result" if rank == 1 else "result-card"
		badge = '<span class="best-badge">BEST MATCH</span>' if rank == 1 else ""
		st.markdown(
			f'<div class="{card_class}" style="--result-delay: {(rank - 1) * 0.04:.2f}s"><div class="result-topline"><div><div class="result-file">{file_path}</div>{badge}</div><div class="result-match">{match_percent:.0f}% <span>match</span></div></div><div class="result-meta">Lines {start}–{end} <span class="meta-separator">·</span> Semantic similarity</div>',
			unsafe_allow_html=True,
		)
		st.code(content, line_numbers=True)
		st.markdown('</div>', unsafe_allow_html=True)


def _render_how_it_works() -> None:
	"""Render concise technical product documentation."""
	st.markdown(
		'<section class="documentation"><div class="section-kicker">THE SYSTEM</div><h2>How CodeLens works</h2><p class="documentation-copy">From repository to relevant implementation in three steps.</p>'
		'<div class="steps"><div class="step"><span>01</span><div><b>INDEX</b><p>Scan source files and split them into searchable chunks.</p></div></div>'
		'<div class="step"><span>02</span><div><b>UNDERSTAND</b><p>Transform code and natural-language queries into semantic embeddings.</p></div></div>'
		'<div class="step"><span>03</span><div><b>FIND</b><p>Use vector similarity search to surface the most relevant implementation.</p></div></div></div>'
		'<div class="trust-row"><span>Sentence Transformers <i>Semantic embeddings</i></span><span>FAISS <i>Vector similarity search</i></span><span>FastAPI <i>Search API</i></span><span>Streamlit <i>Interactive workspace</i></span></div></section>',
		unsafe_allow_html=True,
	)


def _render_footer() -> None:
	"""Render the minimal product footer."""
	st.markdown(
		f'<footer class="site-footer"><div>{_logo(mark_only=True)}<span>CodeLens</span><small>Semantic code intelligence for unfamiliar codebases.</small></div><span>Built for developers.</span></footer>',
		unsafe_allow_html=True,
	)


def main() -> None:
	st.set_page_config(
		page_title="CodeLens | Semantic Code Intelligence",
		layout="wide",
		initial_sidebar_state="collapsed",
	)
	st.markdown(
		"""
		<style>
		:root {
			--bg: #080b12;
			--surface: #0d111a;
			--surface-raised: #111722;
			--border: #202938;
			--text: #f3f5f7;
			--muted: #8b95a7;
			--faint: #5e6879;
			--indigo: #7c6ff2;
			--green: #4caf88;
			--amber: #c9a35d;
			--red: #c96b73;
		}
		.stApp { background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
		[data-testid="stSidebar"], [data-testid="stDecoration"], [data-testid="stToolbar"] { display: none; }
		#MainMenu, div[data-testid="stStatusWidget"] { visibility: hidden; }
		.block-container { max-width: 1240px; padding: 0 2rem 3rem; }
		header[data-testid="stHeader"] { background: transparent; }
		.topbar { align-items: center; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; margin: 0 -2rem; padding: 1rem 2rem; }
		.brand { align-items: center; display: inline-flex; gap: 0.6rem; }
		.logo-mark { align-items: center; color: var(--text); display: inline-flex; height: 2rem; justify-content: center; position: relative; transition: color 0.2s ease, transform 0.2s ease; width: 2rem; }
		.logo-mark::before { border: 1px solid rgba(176,169,255,0.35); border-radius: 50%; content: ""; inset: 2px; opacity: 0; position: absolute; transform: scale(0.72); transition: opacity 0.25s ease, transform 0.25s ease; }
		.brand:hover .logo-mark, .brand:focus-within .logo-mark { color: #b0a9ff; transform: rotate(-4deg) scale(1.05); }
		.brand:hover .logo-mark::before, .brand:focus-within .logo-mark::before { animation: lens-ring 1.2s ease-out infinite; opacity: 1; }
		.logo-mark svg { height: 32px; width: 32px; }
		.brand-name { color: var(--text); font-size: 1.08rem; font-weight: 720; letter-spacing: -0.025em; }
		.brand-name span { color: #b0a9ff; }
		.product-descriptor { border-left: 1px solid var(--border); color: var(--muted); font-size: 0.75rem; margin-left: 0.7rem; padding-left: 0.7rem; }
		.status-line { align-items: center; color: var(--muted); display: flex; font-size: 0.75rem; gap: 0.4rem; }
		.status-dot, .state-surface-dot { background: var(--faint); border-radius: 50%; display: inline-block; height: 6px; width: 6px; }
		.status-dot.success { background: var(--green); }
		.status-dot.progress { animation: pulse 1.8s ease-in-out infinite; background: var(--amber); }
		.status-dot.error { background: var(--red); }
		.main-column { animation: rise-in 0.5s ease-out both; margin: 0 auto; max-width: 900px; padding-top: 0.85rem; }
		.hero { background-image: radial-gradient(circle at 50% 8%, rgba(124,111,242,0.075), transparent 34%), linear-gradient(rgba(255,255,255,0.017) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.017) 1px, transparent 1px); background-position: 0 0, 0 0, 0 0; background-size: auto, 42px 42px, 42px 42px; border-bottom: 1px solid rgba(32,41,56,0.72); margin-bottom: 1.4rem; padding: 1.85rem 1rem 2.1rem; position: relative; text-align: center; }
		.hero::before { animation: ambient-breathe 8s ease-in-out infinite; background: radial-gradient(ellipse at center, rgba(91,140,255,0.07), transparent 62%); content: ""; inset: 0; pointer-events: none; position: absolute; }
		.hero::after { animation: grid-drift 42s linear infinite; background-image: linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px); background-size: 42px 42px; content: ""; inset: 0; opacity: 0.35; pointer-events: none; position: absolute; }
		.hero > * { position: relative; z-index: 1; }
		.hero-title { color: var(--text); font-size: clamp(3rem, 6vw, 4rem); font-weight: 760; letter-spacing: -0.065em; line-height: 1; margin: 0.6rem 0 0.75rem; }
		.hero-copy { color: var(--muted); font-size: 1.02rem; margin: 0 auto 1.25rem; max-width: 580px; }
		.section-kicker { color: #9b91ff; font-size: 0.66rem; font-weight: 760; letter-spacing: 0.16em; }
		.search-shell { background: rgba(13,17,26,0.94); border: 1px solid var(--border); border-radius: 14px; box-shadow: 0 18px 50px rgba(0,0,0,0.22); margin: 0 auto; max-width: 860px; padding: 1.1rem 1.2rem 0.9rem; text-align: left; transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease; }
		.search-shell:focus-within { border-color: rgba(124,111,242,0.78); box-shadow: 0 0 0 3px rgba(124,111,242,0.1), 0 18px 50px rgba(0,0,0,0.22); }
		.search-label { color: var(--muted); font-size: 0.75rem; font-weight: 650; margin-bottom: 0.55rem; }
		.search-shell [data-testid="stTextInput"] input, [data-testid="stTextInput"] input { background: var(--surface-raised) !important; border: 1px solid var(--border) !important; border-radius: 9px !important; color: var(--text) !important; font-size: 0.96rem !important; min-height: 2.75rem; }
		.search-shell [data-testid="stTextInput"] input:focus { animation: focus-ring 1.8s ease-in-out infinite; border-color: var(--indigo) !important; box-shadow: 0 0 0 3px rgba(124,111,242,0.1) !important; }
		.search-shell [data-testid="stButton"] button { min-height: 2.75rem; }
		.search-shell [data-testid="stButton"] button[kind="primary"] { overflow: hidden; position: relative; }
		.search-shell [data-testid="stButton"] button[kind="primary"]::after { background: linear-gradient(105deg, transparent 35%, rgba(255,255,255,0.2) 50%, transparent 65%); content: ""; inset: 0; opacity: 0; position: absolute; transform: translateX(-120%); transition: opacity 0.2s ease; }
		.search-shell [data-testid="stButton"] button[kind="primary"]:hover::after { animation: button-shine 0.75s ease-out; opacity: 1; }
		.stButton > button { background: var(--surface-raised); border: 1px solid var(--border); border-radius: 8px; color: var(--muted); font-size: 0.78rem; transition: border-color 0.18s ease, color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease; }
		.stButton > button:hover { border-color: var(--indigo); color: var(--text); transform: translateY(-1px); }
		.stButton > button:active { transform: translateY(1px) scale(0.99); }
		.stButton > button[kind="primary"] { background: #7166dc; border-color: #7166dc; box-shadow: 0 5px 16px rgba(65,58,145,0.18); color: white; font-weight: 700; }
		.stButton > button[kind="primary"]:hover { background: #7d73e8; border-color: #7d73e8; box-shadow: 0 8px 20px rgba(65,58,145,0.28); }
		.suggestion-label { color: var(--faint); font-size: 0.72rem; margin: 1rem 0 0.4rem; }
		.search-hint { color: var(--faint); font-size: 0.73rem; margin: 0.65rem 0 0; }
		.button-spacer { height: 1.75rem; }
		[data-testid="stSlider"] { padding-top: 0.4rem; }
		[data-testid="stSlider"] [role="slider"] { background: var(--indigo); }
		.workspace-heading, .documentation h2, .results-heading h2 { color: var(--text); font-size: 1.45rem; font-weight: 700; letter-spacing: -0.035em; margin: 0.35rem 0 0.3rem; }
		.workspace-copy, .documentation-copy { color: var(--muted); font-size: 0.86rem; margin: 0 0 1rem; }
		.state-surface, .loading-surface { align-items: flex-start; background: var(--surface); border: 1px solid var(--border); border-radius: 9px; display: flex; gap: 0.65rem; margin: 0.75rem 0 0; padding: 0.7rem 0.9rem; transition: border-color 0.2s ease, transform 0.2s ease; }
		.state-surface:hover { border-color: #344157; transform: translateY(-1px); }
		.loading-surface { border-color: rgba(201,163,93,0.45); }
		.loading-bars { align-items: center; display: inline-flex; gap: 3px; height: 1rem; margin-top: 0.08rem; }
		.loading-bars i { animation: loading-rise 1s ease-in-out infinite; background: var(--amber); border-radius: 2px; display: block; height: 0.45rem; width: 3px; }
		.loading-bars i:nth-child(2) { animation-delay: 0.12s; }
		.loading-bars i:nth-child(3) { animation-delay: 0.24s; }
		.state-surface.success { border-color: rgba(76,175,136,0.4); }
		.state-surface.progress { border-color: rgba(201,163,93,0.45); }
		.state-surface.error { border-color: rgba(201,107,115,0.45); }
		.state-surface.success .state-surface-dot { background: var(--green); }
		.state-surface.progress .state-surface-dot { animation: pulse 1.8s ease-in-out infinite; background: var(--amber); }
		.state-surface.error .state-surface-dot { background: var(--red); }
		.state-title { color: var(--text); font-size: 0.8rem; font-weight: 700; }
		.state-copy { color: var(--muted); font-size: 0.75rem; line-height: 1.45; margin-top: 0.15rem; overflow-wrap: anywhere; }
		.empty-workspace { border: 1px dashed var(--border); margin-top: 1rem; padding: 1.35rem 1.5rem; text-align: center; }
		.empty-eyebrow { color: var(--faint); font-size: 0.66rem; font-weight: 750; letter-spacing: 0.16em; }
		.empty-title { color: var(--text); font-size: 1.15rem; font-weight: 680; margin-top: 0.45rem; }
		.empty-copy { color: var(--muted); font-size: 0.84rem; margin: 0.35rem auto 1.35rem; max-width: 480px; }
		.semantic-motif { align-items: center; color: var(--faint); display: flex; font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; font-size: 0.68rem; gap: 0.55rem; justify-content: center; }
		.flow-arrow { animation: arrow-breathe 2.8s ease-in-out infinite; color: var(--indigo); font-size: 0.95rem; font-weight: 400; }
		.motif-points { display: inline-flex; gap: 3px; margin-right: 0.1rem; position: relative; }
		.motif-points::after { border-top: 1px solid rgba(124,111,242,0.28); content: ""; left: 2px; position: absolute; right: 2px; top: 4px; }
		.motif-points i { animation: point-drift 2.4s ease-in-out infinite; background: #8f86f6; border-radius: 50%; display: block; height: 4px; position: relative; width: 4px; z-index: 1; }
		.motif-points i:nth-child(2) { animation-delay: 0.3s; }
		.motif-points i:nth-child(3) { animation-delay: 0.6s; }
		.results-heading { align-items: end; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; margin-top: 2.4rem; padding-bottom: 0.75rem; }
		.results-heading h2 { font-size: 1.35rem; margin-bottom: 0; }
		.result-count { color: var(--muted); font-size: 0.76rem; }
		.result-card { animation: rise-in 0.35s ease-out var(--result-delay, 0s) both; background: var(--surface); border: 1px solid var(--border); border-radius: 9px; margin-top: 0.85rem; padding: 1rem 1.1rem 0.45rem; transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease; }
		.result-card:hover { background: var(--surface-raised); border-color: #344157; }
		.result-card:hover { transform: translateY(-2px); }
		.result-card.top-result { border-color: rgba(124,111,242,0.7); box-shadow: inset 3px 0 0 var(--indigo); }
		.result-topline { align-items: flex-start; display: flex; justify-content: space-between; gap: 1rem; }
		.result-file { color: var(--text); font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; font-size: 0.9rem; font-weight: 650; overflow-wrap: anywhere; }
		.best-badge { color: #a9a1ff; display: block; font-size: 0.6rem; font-weight: 760; letter-spacing: 0.12em; margin-top: 0.35rem; }
		.result-match { color: #b1aaff; font-size: 1rem; font-weight: 720; white-space: nowrap; }
		.result-match span { color: var(--muted); font-size: 0.7rem; font-weight: 500; }
		.result-meta { color: var(--muted); font-size: 0.73rem; margin-top: 0.5rem; }
		.meta-separator { color: var(--faint); padding: 0 0.35rem; }
		[data-testid="stCodeBlock"] { border: 1px solid rgba(32,41,56,0.8); border-radius: 7px; margin-top: 0.7rem; overflow: hidden; }
		[data-testid="stCodeBlock"] pre { background: #0a0e16 !important; font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace; font-size: 0.78rem; }
		.documentation { border-top: 1px solid var(--border); margin-top: 3.5rem; padding-top: 2rem; }
		.documentation-copy { margin-bottom: 1.5rem; }
		.steps { border-top: 1px solid var(--border); display: grid; grid-template-columns: repeat(3, 1fr); }
		.step { border-right: 1px solid var(--border); display: flex; gap: 0.9rem; padding: 1.2rem 1.2rem 1.1rem 0; }
		.step + .step { padding-left: 1.2rem; }
		.step:last-child { border-right: 0; }
		.step > span { color: var(--indigo); font-family: "JetBrains Mono", monospace; font-size: 0.72rem; }
		.step b { color: var(--text); font-size: 0.72rem; letter-spacing: 0.12em; }
		.step p { color: var(--muted); font-size: 0.76rem; line-height: 1.5; margin: 0.35rem 0 0; }
		.trust-row { border-top: 1px solid var(--border); display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 1.5rem; padding-top: 1rem; }
		.trust-row span { color: var(--text); font-size: 0.73rem; font-weight: 650; }
		.trust-row i { color: var(--faint); display: block; font-size: 0.68rem; font-style: normal; font-weight: 400; margin-top: 0.25rem; }
		.site-footer { align-items: center; border-top: 1px solid var(--border); color: var(--muted); display: flex; font-size: 0.73rem; justify-content: space-between; margin-top: 2.8rem; padding-top: 1.1rem; }
		.site-footer { visibility: visible; }
		.site-footer > div { align-items: center; display: flex; gap: 0.45rem; }
		.site-footer .logo-mark { height: 1.5rem; width: 1.5rem; }
		.site-footer .logo-mark svg { height: 23px; width: 23px; }
		.site-footer small { color: var(--faint); font-size: 0.7rem; margin-left: 0.35rem; }
		@keyframes rise-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
		@keyframes grid-drift { from { background-position: 0 0; } to { background-position: 42px 42px; } }
		@keyframes ambient-breathe { 0%, 100% { opacity: 0.45; transform: scale(0.98); } 50% { opacity: 0.75; transform: scale(1.02); } }
		@keyframes loading-rise { 0%, 100% { height: 0.4rem; opacity: 0.55; } 50% { height: 0.9rem; opacity: 1; } }
		@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(201,163,93,0.35); } 50% { box-shadow: 0 0 0 4px rgba(201,163,93,0.06); } }
		@keyframes lens-ring { 0% { opacity: 0.45; transform: scale(0.72); } 100% { opacity: 0; transform: scale(1.22); } }
		@keyframes button-shine { from { transform: translateX(-120%); } to { transform: translateX(120%); } }
		@keyframes focus-ring { 0%, 100% { box-shadow: 0 0 0 3px rgba(124,111,242,0.08) !important; } 50% { box-shadow: 0 0 0 4px rgba(124,111,242,0.15) !important; } }
		@keyframes arrow-breathe { 0%, 100% { opacity: 0.45; transform: translateX(0); } 50% { opacity: 0.9; transform: translateX(2px); } }
		@keyframes point-drift { 0%, 100% { opacity: 0.45; transform: translateY(0); } 50% { opacity: 0.95; transform: translateY(-2px); } }
		@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: 0.01ms !important; } }
		@media (max-width: 760px) {
			.block-container { padding: 0 1rem 2rem; }
			.topbar { margin: 0 -1rem; padding: 0.9rem 1rem; }
			.product-descriptor { display: none; }
			.main-column { padding-top: 0.5rem; }
			.hero { padding: 1.6rem 0 1.9rem; }
			.hero-title { font-size: 2.7rem; }
			.hero-copy { font-size: 0.94rem; }
			.steps, .trust-row { grid-template-columns: 1fr; }
			.step, .step + .step { border-bottom: 1px solid var(--border); border-right: 0; padding: 1rem 0; }
			.step:last-child { border-bottom: 0; }
			.trust-row { gap: 0.85rem; }
			.site-footer { align-items: flex-start; flex-direction: column; gap: 0.7rem; }
			.site-footer small { display: block; margin-left: 0; }
		}
		</style>
		""",
		unsafe_allow_html=True,
	)

	indexed_repository = st.session_state.get("indexed_repository")
	indexing_state = st.session_state.get("indexing_state", "idle")
	search_state = st.session_state.get("search_state", "idle")
	if indexing_state == "indexing" or search_state == "searching":
		top_status = ("progress", "Indexing" if indexing_state == "indexing" else "Searching")
	elif indexing_state == "error" or search_state == "error":
		top_status = ("error", "Needs attention")
	elif indexed_repository:
		top_status = ("success", "Indexed")
	else:
		top_status = ("", "Ready")

	st.markdown(
		f'<nav class="topbar"><div>{_logo()}<span class="product-descriptor">Semantic code intelligence</span></div><div class="status-line"><span class="status-dot {top_status[0]}"></span>{top_status[1]}</div></nav>',
		unsafe_allow_html=True,
	)
	st.markdown('<main class="main-column">', unsafe_allow_html=True)
	st.markdown('<section class="hero">', unsafe_allow_html=True)
	_render_search(indexed_repository)
	st.markdown('</section>', unsafe_allow_html=True)
	_render_repository(indexed_repository)
	_render_how_it_works()
	_render_footer()
	st.markdown('</main>', unsafe_allow_html=True)


if __name__ == "__main__":
	main()
