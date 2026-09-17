from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union


def _is_ignored_dir(path: Path, ignore_dirs: List[str]) -> bool:
	"""Return True if any part of `path` matches an ignored directory name."""
	return any(part in ignore_dirs for part in path.parts)


def _read_file_text(path: Path) -> Optional[str]:
	"""Read file contents as text, trying utf-8 then falling back.

	Returns the text on success, or None if the file cannot be read.
	"""
	try:
		return path.read_text(encoding="utf-8")
	except UnicodeDecodeError:
		try:
			return path.read_text(encoding="latin-1")
		except Exception:
			return None
	except Exception:
		return None


def scan_repository(repo_path: Union[str, Path]) -> List[Dict[str, str]]:
	"""Recursively scan a repository for source files and return their contents.

	The scanner supports common source, web, configuration, and documentation
	file extensions. It ignores common build/virtualenv directories and skips
	files larger than 500 KB. File-reading errors are handled gracefully by
	skipping the problematic file.

	Args:
		repo_path: Path to the repository root (str or Path).

	Returns:
		A list of dictionaries with keys `file` (relative path) and
		`content` (file contents as text).
	"""
	root = Path(repo_path)
	if not root.exists():
		return []

	supported_exts = {
		".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h", ".cpp",
		".hpp", ".cc", ".cxx", ".go", ".rs", ".rb", ".php", ".cs", ".swift",
		".kt", ".kts", ".scala", ".sh", ".bash", ".sql", ".html", ".htm",
		".css", ".scss", ".sass", ".vue", ".svelte", ".json", ".yaml", ".yml",
		".toml", ".xml", ".md", ".txt",
	}
	supported_filenames = {".env.example"}
	ignore_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
	max_size_bytes = 500 * 1024  # 500 KB

	results: List[Dict[str, str]] = []

	def _scan_dir(directory: Path) -> None:
		try:
			for entry in directory.iterdir():
				# Skip symlinks that would cause cycles or are unreadable
				try:
					if entry.is_symlink():
						continue
				except Exception:
					continue

				if entry.is_dir():
					if entry.name in ignore_dirs:
						continue
					# also skip if any parent matches ignored dirs
					if _is_ignored_dir(entry, list(ignore_dirs)):
						continue
					_scan_dir(entry)
				elif entry.is_file():
					if entry.suffix.lower() not in supported_exts and entry.name.lower() not in supported_filenames:
						continue
					try:
						size = entry.stat().st_size
					except Exception:
						continue
					if size > max_size_bytes:
						continue
					text = _read_file_text(entry)
					if text is None:
						continue
					rel_path = str(entry.relative_to(root))
					results.append({"file": rel_path, "content": text})
		except PermissionError:
			# Skip directories we can't access
			return

	_scan_dir(root)
	return results



def chunk_documents(documents: List[Dict[str, str]], max_lines: int = 80) -> List[Dict[str, Union[str, int]]]:
	"""Split scanned documents into line-based chunks.

	Each input document should be a dict with `file` and `content` keys as
	returned by `scan_repository()`. This function yields a list of chunk
	dictionaries with the original relative `file`, the chunk `content`, and
	1-based inclusive `start_line` and `end_line` numbers.

	Args:
		documents: List of documents from `scan_repository()`.
		max_lines: Maximum number of lines per chunk (default 80).

	Returns:
		A list of dicts with keys: `file`, `content`, `start_line`, `end_line`.
	"""

	if not documents:
		return []

	chunks: List[Dict[str, Union[str, int]]] = []
	for doc in documents:
		file_path = doc.get("file", "")
		content = doc.get("content", "")
		# splitlines preserves logical lines and handles different line endings
		lines = content.splitlines()
		total = len(lines)
		if total == 0:
			# skip empty files (no chunks)
			continue

		for start in range(0, total, max_lines):
			end = min(start + max_lines, total)
			chunk_lines = lines[start:end]
			chunk_content = "\n".join(chunk_lines)
			chunks.append({
				"file": file_path,
				"content": chunk_content,
				"start_line": start + 1,
				"end_line": end,
			})

	return chunks

