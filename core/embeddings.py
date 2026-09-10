
from __future__ import annotations

from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingModel:
	"""Simple embedding wrapper using sentence-transformers.

	Loads the `all-MiniLM-L6-v2` model on initialization and provides an
	`encode()` method that returns L2-normalized embeddings as a NumPy array
	with shape (n_texts, embedding_dim). Normalized embeddings allow cosine
	similarity to be computed via a dot product.
	"""

	def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
		self.model = SentenceTransformer(model_name)

	def encode(self, texts: Iterable[str]) -> np.ndarray:
		"""Encode a list of texts and return normalized embeddings.

		Args:
			texts: An iterable of input strings.

		Returns:
			A NumPy array of shape (len(texts), embedding_dim) containing
			L2-normalized embeddings (dtype=float32).
		"""
		arr = self.model.encode(list(texts), convert_to_numpy=True, show_progress_bar=False)
		# L2-normalize rows. Guard against zero norms.
		norms = np.linalg.norm(arr, axis=1, keepdims=True)
		norms[norms == 0] = 1.0
		return arr / norms

