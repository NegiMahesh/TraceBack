"""System health and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.ollama_service import ollama_service
from backend.services import git_service
from backend.config import DEFAULT_REPO_PATH, OLLAMA_MODEL

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "TraceBack"}


@router.get("/system/status")
async def system_status():
    """Full system status: Ollama, Git, model, repo."""
    ollama = await ollama_service.health_check()

    git_available = False
    try:
        import subprocess
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        git_available = r.returncode == 0
    except Exception:
        pass

    repo_status = {}
    if git_service.is_git_repo(DEFAULT_REPO_PATH):
        repo_status = git_service.get_status(DEFAULT_REPO_PATH)
    else:
        repo_status = {"is_repo": False}

    return {
        "ollama": ollama,
        "git": {"available": git_available},
        "model": OLLAMA_MODEL,
        "repo": repo_status,
        "repo_path": DEFAULT_REPO_PATH,
    }
