from pathlib import Path

from core.embeddings import EmbeddingModel
from core.search import CodeSearchEngine


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
