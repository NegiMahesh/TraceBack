"""Source code intelligence — reads files and builds smart LLM context."""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

from backend.config import ALLOWED_ROOTS, MAX_CONTEXT_LINES, MAX_FILE_SIZE_BYTES
from backend.models.analysis import SourceContext


def validate_path(file_path: str, repo_path: str | None = None) -> Path:
    """Resolve and validate a file path against allowed roots.

    Raises ValueError for path traversal attempts.
    """
    resolved = Path(file_path).resolve()

    roots = list(ALLOWED_ROOTS)
    if repo_path:
        roots.append(str(Path(repo_path).resolve()))

    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return resolved
        except ValueError:
            continue

    raise ValueError(f"Path {file_path} is outside allowed directories")


def read_file_safe(file_path: str, repo_path: str | None = None) -> str:
    """Read a file with path validation and size limits."""
    p = validate_path(file_path, repo_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    if p.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File too large: {p.stat().st_size} bytes (max {MAX_FILE_SIZE_BYTES})")
    return p.read_text(encoding="utf-8", errors="replace")


def get_source_context(
    file_path: str,
    error_line: int,
    repo_path: str | None = None,
    context_lines: int = MAX_CONTEXT_LINES,
) -> SourceContext:
    """Build a smart source context around the error line.

    Reads the file, finds the containing function, and gathers imports.
    """
    full_path = _resolve_file(file_path, repo_path)
    if not full_path:
        return SourceContext(file_path=file_path, error_line=error_line)

    content = read_file_safe(str(full_path), repo_path)
    lines = content.splitlines()
    total = len(lines)

    # Calculate window
    half = context_lines // 2
    start = max(1, error_line - half)
    end = min(total, error_line + half)

    snippet_lines = lines[start - 1 : end]
    snippet = "\n".join(snippet_lines)

    # Find containing function
    func_name = _find_containing_function(lines, error_line)

    # Extract imports
    imports = _extract_imports(lines)

    return SourceContext(
        file_path=str(full_path),
        content=snippet,
        start_line=start,
        end_line=end,
        error_line=error_line,
        function_name=func_name,
        imports=imports,
    )


def get_file_tree(repo_path: str, max_depth: int = 4) -> list[dict]:
    """Get a file tree for a repository path."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        return []

    tree: list[dict] = []
    _walk_tree(root, root, tree, 0, max_depth)
    return tree


def _walk_tree(
    current: Path, root: Path, tree: list[dict], depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return

    skip = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".pytest_cache", "dist", ".eggs"}

    try:
        entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return

    for entry in entries:
        if entry.name in skip or entry.name.startswith("."):
            continue

        rel = str(entry.relative_to(root)).replace("\\", "/")
        node: dict = {
            "name": entry.name,
            "path": rel,
            "type": "directory" if entry.is_dir() else "file",
        }

        if entry.is_file():
            try:
                node["size"] = entry.stat().st_size
            except OSError:
                node["size"] = 0
            node["language"] = _detect_language(entry.name)
        elif entry.is_dir():
            children: list[dict] = []
            _walk_tree(entry, root, children, depth + 1, max_depth)
            node["children"] = children

        tree.append(node)


def _detect_language(filename: str) -> str:
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".json": "json",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".txt": "text",
        ".html": "html",
        ".css": "css",
        ".sh": "shell",
        ".sql": "sql",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "text")


def _resolve_file(file_path: str, repo_path: str | None) -> Path | None:
    """Try to resolve a file path, searching the repo if needed."""
    p = Path(file_path)
    if p.is_absolute() and p.is_file():
        return p.resolve()

    if repo_path:
        candidate = Path(repo_path) / file_path
        if candidate.is_file():
            return candidate.resolve()

        # Search recursively (limited depth)
        base_name = p.name
        root = Path(repo_path)
        for f in root.rglob(base_name):
            if f.is_file():
                return f.resolve()

    return None


def _find_containing_function(lines: list[str], target_line: int) -> str:
    """Find the function/method containing the target line."""
    func_re = re.compile(r"^(\s*)def\s+(\w+)\s*\(")
    class_re = re.compile(r"^(\s*)class\s+(\w+)")

    best_func = "<module>"
    best_class = ""

    for i in range(min(target_line, len(lines))):
        line = lines[i]
        cm = class_re.match(line)
        if cm:
            best_class = cm.group(2)
        fm = func_re.match(line)
        if fm:
            # Check indentation to see if it's a method
            indent = len(fm.group(1))
            name = fm.group(2)
            if indent > 0 and best_class:
                best_func = f"{best_class}.{name}"
            else:
                best_func = name

    return best_func


def _extract_imports(lines: list[str]) -> list[str]:
    """Extract import statements from a file."""
    imports: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
        # Stop after first non-import, non-blank, non-comment line
        elif stripped and not stripped.startswith("#") and not stripped.startswith('"""') and not stripped.startswith("'''"):
            if imports:  # we already found some imports
                break
    return imports
