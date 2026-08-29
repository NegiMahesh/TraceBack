"""TraceBack configuration — all settings centralized here."""

import os
from pathlib import Path


# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_PROJECT_DIR = PROJECT_ROOT / "demo_project"
GENERATED_TESTS_DIR = PROJECT_ROOT / "generated_tests"
BACKUPS_DIR = PROJECT_ROOT / ".traceback_backups"

# ── Ollama / AI ────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))

# ── Repository ─────────────────────────────────────────────────────────
DEFAULT_REPO_PATH = os.getenv("TRACEBACK_REPO", str(DEMO_PROJECT_DIR))

# ── Security ───────────────────────────────────────────────────────────
# Allowed base directories for file operations (prevents path traversal)
ALLOWED_ROOTS = [
    str(PROJECT_ROOT),
]

MAX_FILE_SIZE_BYTES = 1_000_000  # 1 MB — don't send huge files to LLM
MAX_CONTEXT_LINES = 60  # surrounding-context window for LLM

# ── Server ─────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
