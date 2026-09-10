from pathlib import Path

from core.parser import scan_repository, chunk_documents


def main() -> None:
	repo_root = Path('.')
	results = scan_repository(repo_root)
	print(f"Total source files found: {len(results)}")
	for item in results:
		print(item["file"])

	# Also test chunking
	chunks = chunk_documents(results, max_lines=20)
	print(f"Total chunks created: {len(chunks)}")
	for c in chunks:
		print(f"{c['file']}: {c['start_line']}-{c['end_line']}")


if __name__ == "__main__":
	main()

