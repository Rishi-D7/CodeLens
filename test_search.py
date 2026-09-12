from pathlib import Path

import numpy as np

from core.embeddings import EmbeddingModel
from core.search import CodeSearchEngine


class StubEmbeddingModel:
    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = {
            "best duplicate chunk": [1.0, 0.0],
            "lower duplicate chunk": [0.95, 0.0],
            "different file": [0.9, 0.0],
            "another file": [0.8, 0.0],
            "query": [1.0, 0.0],
        }
        return np.asarray([vectors[text] for text in texts], dtype=np.float32)


def test_search_returns_one_best_chunk_per_file() -> None:
    engine = CodeSearchEngine(StubEmbeddingModel())
    engine.build_index(
        [
            {"file": "src/duplicate.py", "content": "best duplicate chunk", "start_line": 1, "end_line": 2},
            {"file": "src/duplicate.py", "content": "lower duplicate chunk", "start_line": 81, "end_line": 82},
            {"file": "src/different.py", "content": "different file", "start_line": 1, "end_line": 2},
            {"file": "src/another.py", "content": "another file", "start_line": 1, "end_line": 2},
        ]
    )

    results = engine.search("query", top_k=3)

    assert [result["file"] for result in results] == [
        "src/duplicate.py",
        "src/different.py",
        "src/another.py",
    ]
    assert results[0]["content"] == "best duplicate chunk"
    assert results[0]["start_line"] == 1


def main() -> None:
    repo_root = Path(".")

    model = EmbeddingModel()
    engine = CodeSearchEngine(model)
    # build index from the real repository (scans and chunks files)
    engine.build_from_repository(repo_root)

    query = "Where is the code that scans files in the repository?"
    results = engine.search(query, top_k=5)

    print("Top results:")
    for res in results:
        file = res.get("file", "")
        start = res.get("start_line", None)
        end = res.get("end_line", None)
        score = res.get("score", 0.0)
        content = res.get("content", "")
        preview = " ".join(str(content).splitlines())[:120]
        print(f"{file} | {start}-{end} | {score:.4f} | {preview}")


if __name__ == "__main__":
    main()
