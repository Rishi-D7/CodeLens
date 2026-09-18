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


class EqualEmbeddingModel:
    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)


class SemanticEmbeddingModel:
    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = {
            "how does data retrieval work": [1.0, 0.0],
            "retrieves records from the database": [1.0, 0.0],
            "renders the settings page": [0.0, 1.0],
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


def test_exact_function_name_beats_semantic_similarity() -> None:
    engine = CodeSearchEngine(EqualEmbeddingModel())
    engine.build_index(
        [
            {"file": "src/general.py", "content": "appointment booking logic", "start_line": 1, "end_line": 1},
            {"file": "src/booking.py", "content": "def bookAppointment(): pass", "start_line": 1, "end_line": 1},
        ]
    )

    results = engine.search("bookAppointment", top_k=1)

    assert results[0]["file"] == "src/booking.py"


def test_exact_filename_and_route_are_prioritized() -> None:
    engine = CodeSearchEngine(EqualEmbeddingModel())
    engine.build_index(
        [
            {"file": "src/other.py", "content": "generic request handling", "start_line": 1, "end_line": 1},
            {"file": "src/routes.py", "content": "@app.get('/api/bookings')", "start_line": 1, "end_line": 1},
        ]
    )

    assert engine.search("routes.py", top_k=1)[0]["file"] == "src/routes.py"
    assert engine.search("/api/bookings", top_k=1)[0]["file"] == "src/routes.py"


def test_semantic_query_still_uses_semantic_similarity() -> None:
    engine = CodeSearchEngine(SemanticEmbeddingModel())
    engine.build_index(
        [
            {"file": "src/database.py", "content": "retrieves records from the database", "start_line": 1, "end_line": 1},
            {"file": "src/settings.py", "content": "renders the settings page", "start_line": 1, "end_line": 1},
        ]
    )

    results = engine.search("how does data retrieval work", top_k=1)

    assert results[0]["file"] == "src/database.py"


def test_implementation_results_stay_ahead_of_tests() -> None:
    engine = CodeSearchEngine(EqualEmbeddingModel())
    engine.build_index(
        [
            {"file": "tests/test_booking.py", "content": "def bookAppointment(): pass", "start_line": 1, "end_line": 1},
            {"file": "src/booking.py", "content": "def bookAppointment(): pass", "start_line": 1, "end_line": 1},
        ]
    )

    results = engine.search("bookAppointment", top_k=2)

    assert [result["file"] for result in results] == ["src/booking.py", "tests/test_booking.py"]


def test_search_result_contract_is_unchanged() -> None:
    engine = CodeSearchEngine(EqualEmbeddingModel())
    engine.build_index([
        {"file": "src/example.py", "content": "example", "start_line": 3, "end_line": 3},
    ])

    result = engine.search("example", top_k=1)[0]

    assert set(result) == {"file", "content", "start_line", "end_line", "score"}
    assert isinstance(result["score"], float)


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
