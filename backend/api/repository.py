"""Repository and file browsing endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.config import DEFAULT_REPO_PATH
from backend.services.source_analyzer import get_file_tree, read_file_safe, validate_path

router = APIRouter(tags=["repository"])


@router.get("/repository")
async def get_repository_info(repo_path: str = Query(default=DEFAULT_REPO_PATH)):
    """Get repository metadata."""
    rp = Path(repo_path)
    if not rp.is_dir():
        raise HTTPException(status_code=404, detail="Repository path not found")

    return {
        "path": str(rp.resolve()),
        "name": rp.name,
        "exists": True,
    }


@router.get("/repository/files")
async def get_files(repo_path: str = Query(default=DEFAULT_REPO_PATH)):
    """Get file tree for the repository."""
    rp = Path(repo_path)
    if not rp.is_dir():
        raise HTTPException(status_code=404, detail="Repository path not found")

    tree = get_file_tree(str(rp))
    return {"tree": tree, "repo_path": str(rp.resolve())}


@router.get("/file")
async def get_file_content(
    path: str = Query(..., description="File path (relative or absolute)"),
    repo_path: str = Query(default=DEFAULT_REPO_PATH),
):
    """Read a file's content."""
    # Resolve relative paths
    if not Path(path).is_absolute():
        full_path = str(Path(repo_path) / path)
    else:
        full_path = path

    try:
        validate_path(full_path, repo_path)
        content = read_file_safe(full_path, repo_path)

        p = Path(full_path)
        return {
            "path": full_path,
            "name": p.name,
            "content": content,
            "size": p.stat().st_size,
            "language": _detect_lang(p.name),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


def _detect_lang(filename: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".jsx": "javascript",
        ".ts": "typescript", ".tsx": "typescript", ".json": "json",
        ".md": "markdown", ".yml": "yaml", ".yaml": "yaml",
        ".html": "html", ".css": "css", ".txt": "text",
    }
    return ext_map.get(Path(filename).suffix.lower(), "text")
