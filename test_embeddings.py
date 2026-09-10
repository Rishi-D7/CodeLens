from core.embeddings import EmbeddingModel
import numpy as np


def main() -> None:
	model = EmbeddingModel()
	texts = [
		"user authentication and password verification",
		"database connection and SQL queries",
	]
	embeddings = model.encode(texts)
	print("embeddings shape:", embeddings.shape)
	norms = np.linalg.norm(embeddings, axis=1)
	is_normalized = np.allclose(norms, 1.0, atol=1e-6)
	print("normalized:", is_normalized)
	print("norms:", norms)


if __name__ == "__main__":
	main()

