
from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List, Optional, Union

import numpy as np
import faiss

from core.embeddings import EmbeddingModel


class CodeSearchEngine:
	"""Simple semantic search engine using FAISS and an EmbeddingModel.

	The engine builds an IndexFlatIP index over L2-normalized embeddings so
	inner products correspond to cosine similarity.
	"""

	def __init__(self, embedder: EmbeddingModel) -> None:
		self.embedder = embedder
		self.index: Optional[faiss.IndexFlatIP] = None
		# doc_store may contain chunk metadata (start_line/end_line ints)
		self.doc_store: List[Dict[str, Union[str, int]]] = []
	def build_index(self, documents: List[Dict[str, Union[str, int]]]) -> None:
		"""Build a FAISS index from `documents`.

		Args:
			documents: List of dicts containing `file` and `content` keys.

		Notes:
			If `documents` is empty, the index and store are cleared.
		"""
		if not documents:
			self.index = None
			self.doc_store = []
			return

		contents = [doc.get("content", "") for doc in documents]
		embeddings = self.embedder.encode(contents)
		embeddings = np.asarray(embeddings, dtype=np.float32)

		if embeddings.ndim != 2 or embeddings.shape[0] == 0:
			# Nothing to index
			self.index = None
			self.doc_store = []
			return

		dim = embeddings.shape[1]
		index = faiss.IndexFlatIP(dim)
		index.add(embeddings)

		self.index = index
		# store documents (including any chunk metadata) for result lookup
		self.doc_store = list(documents)

	def build_from_repository(self, repo_path: Union[str, Path]) -> None:
		"""Scan a repository, chunk files, and build the FAISS index.

		This loads `scan_repository` and `chunk_documents` from
		`core.parser` at runtime to avoid a top-level import dependency.
		"""
		from core.parser import scan_repository, chunk_documents

		scanned = scan_repository(repo_path)
		# chunk_documents returns list of dicts with file, content, start_line, end_line
		chunks = chunk_documents(scanned)
		if not chunks:
			raise RuntimeError("No supported source files found in repository.")
		# build the index from chunk documents
		self.build_index(chunks)

	@staticmethod
	def _query_tokens(query: str) -> List[str]:
		stop_words = {
			"where", "is", "the", "a", "an", "are", "was", "were", "how",
			"what", "which", "does", "do", "implemented", "handled", "located",
			"defined", "code", "function",
		}
		return [
			token
			for token in re.findall(r"[a-z0-9_]+", query.lower())
			if token not in stop_words
		]

	@staticmethod
	def _compact_identifier(value: str) -> str:
		return re.sub(r"[^a-z0-9]", "", value.lower())

	@classmethod
	def _lexical_score(cls, query: str, doc: Dict[str, Union[str, int]]) -> float:
		query_tokens = cls._query_tokens(query)
		if not query_tokens:
			return 0.0

		file_path = str(doc.get("file", "")).replace("\\", "/").lower()
		file_name = file_path.rsplit("/", 1)[-1]
		content = str(doc.get("content", ""))
		content_lower = content.lower()
		candidate_text = f"{file_path} {content_lower}"
		candidate_compact = cls._compact_identifier(candidate_text)
		candidate_identifiers = {
			cls._compact_identifier(identifier)
			for identifier in re.findall(r"[a-zA-Z_][a-zA-Z0-9_-]*", candidate_text)
		}

		matched_terms = sum(
			1 for token in query_tokens
			if cls._compact_identifier(token) in candidate_compact
		)
		coverage = matched_terms / len(query_tokens)

		# Compact forms make camelCase, snake_case, and kebab-case equivalent.
		exact_identifier = any(
			cls._compact_identifier(token) in candidate_identifiers
			for token in query_tokens
			if len(cls._compact_identifier(token)) >= 3
		)

		query_routes = re.findall(r"/[a-zA-Z0-9_./:{}-]+", query)
		route_match = any(
			cls._compact_identifier(route.rstrip(".,;:!?"))
			in cls._compact_identifier(candidate_text)
			for route in query_routes
		)

		query_filenames = re.findall(r"[a-zA-Z0-9_.-]+\.[a-zA-Z0-9]+", query)
		filename_match = any(
			cls._compact_identifier(filename) == cls._compact_identifier(file_name)
			for filename in query_filenames
		)

		if exact_identifier or route_match:
			return 1.0
		if filename_match:
			return 0.9
		return min(1.0, coverage)

	def search(self, query: str, top_k: int = 5) -> List[Dict[str, Union[str, float]]]:
		"""Search the index for the most similar documents to `query`.

		Args:
			query: Query text.
			top_k: Number of top results to return.

		Returns:
			A list of dicts each containing `file`, `content`, and `score`.

		Raises:
			RuntimeError: If the index has not been built yet.
		"""
		if self.index is None or not self.doc_store:
			raise RuntimeError("Index has not been built. Call build_index() first with documents.")

		q_emb = self.embedder.encode([query])
		q_emb = np.asarray(q_emb, dtype=np.float32)

		# Retrieve a wider pool so lexical matches can rerank beyond semantic top_k.
		k = min(max(top_k * 10, top_k + 20, 50), len(self.doc_store))
		distances, indices = self.index.search(q_emb, k)
		candidates: List[Dict[str, Union[str, float]]] = []
		for semantic_score, idx in zip(distances[0].tolist(), indices[0].tolist()):
			if idx < 0:
				continue
			doc = dict(self.doc_store[idx])
			semantic_relevance = (float(semantic_score) + 1.0) / 2.0
			lexical_relevance = self._lexical_score(query, doc)
			doc["score"] = 0.45 * semantic_relevance + 0.55 * lexical_relevance
			candidates.append(doc)
		candidates.sort(key=lambda candidate: float(candidate["score"]), reverse=True)

		non_test_results: List[Dict[str, Union[str, float]]] = []
		test_results: List[Dict[str, Union[str, float]]] = []
		seen_files = set()
		for doc in candidates:
			file_key = str(doc.get("file", ""))
			if file_key in seen_files:
				continue
			seen_files.add(file_key)
			file_path = str(doc.get("file", "")).replace("\\", "/").lower()
			file_name = file_path.rsplit("/", 1)[-1]
			path_parts = set(part for part in file_path.split("/") if part)
			is_test_file = (
				"test" in path_parts
				or "tests" in path_parts
				or bool(re.match(r"test_.*\.py$", file_name))
				or bool(re.match(r".*_test\.py$", file_name))
			)
			if is_test_file:
				test_results.append(doc)
			else:
				non_test_results.append(doc)

		# Keep tests indexed, but deprioritize them so implementation code is easier to discover.
		selected = non_test_results[:top_k]
		if len(selected) < top_k:
			selected.extend(test_results[:top_k - len(selected)])
		return selected

