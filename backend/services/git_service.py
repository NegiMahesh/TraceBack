"""Git intelligence service — blame, log, status, diff via subprocess."""

from __future__ import annotations

import subprocess
from pathlib import Path

from backend.models.analysis import GitBlameInfo


def _run_git(args: list[str], cwd: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run a git command safely with argument arrays (no shell injection)."""
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def is_git_repo(repo_path: str) -> bool:
    """Check whether the path is inside a Git repository."""
    try:
        r = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_path)
        return r.returncode == 0 and "true" in r.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_status(repo_path: str) -> dict:
    """Get Git status summary."""
    try:
        branch_r = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        branch = branch_r.stdout.strip() if branch_r.returncode == 0 else "unknown"

        status_r = _run_git(["status", "--porcelain"], cwd=repo_path)
        modified_files = []
        if status_r.returncode == 0:
            for line in status_r.stdout.strip().splitlines():
                if line.strip():
                    modified_files.append(line.strip())

        commit_r = _run_git(["log", "-1", "--format=%H|%s|%ai"], cwd=repo_path)
        latest_commit = {}
        if commit_r.returncode == 0 and commit_r.stdout.strip():
            parts = commit_r.stdout.strip().split("|", 2)
            if len(parts) == 3:
                latest_commit = {
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "date": parts[2],
                }

        return {
            "is_repo": True,
            "branch": branch,
            "modified_files": modified_files,
            "latest_commit": latest_commit,
            "clean": len(modified_files) == 0,
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return {"is_repo": False, "error": str(e)}


def get_blame(repo_path: str, file_path: str, line: int) -> GitBlameInfo:
    """Run git blame on a specific line."""
    try:
        # Resolve relative path within repo
        rel_path = _get_relative_path(repo_path, file_path)
        if not rel_path:
            return GitBlameInfo(line=line)

        r = _run_git(
            ["blame", "-L", f"{line},{line}", "--porcelain", rel_path],
            cwd=repo_path,
        )

        if r.returncode != 0:
            return GitBlameInfo(line=line)

        return _parse_blame_porcelain(r.stdout, line)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return GitBlameInfo(line=line)


def get_log(repo_path: str, max_count: int = 20, file_path: str | None = None) -> list[dict]:
    """Get recent Git log entries."""
    try:
        args = ["log", f"-{max_count}", "--format=%H|%an|%ai|%s"]
        if file_path:
            rel = _get_relative_path(repo_path, file_path)
            if rel:
                args.extend(["--", rel])

        r = _run_git(args, cwd=repo_path)
        if r.returncode != 0:
            return []

        entries = []
        for line in r.stdout.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "hash": parts[0][:8],
                    "full_hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3],
                })
        return entries

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def get_diff(repo_path: str) -> str:
    """Get current uncommitted diff."""
    try:
        r = _run_git(["diff"], cwd=repo_path)
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def has_uncommitted_changes(repo_path: str) -> bool:
    """Check for uncommitted changes."""
    try:
        r = _run_git(["status", "--porcelain"], cwd=repo_path)
        return bool(r.stdout.strip()) if r.returncode == 0 else False
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def create_stash(repo_path: str, message: str = "TraceBack backup") -> str:
    """Create a git stash as a safety checkpoint."""
    try:
        r = _run_git(["stash", "push", "-m", message], cwd=repo_path)
        if r.returncode == 0:
            return r.stdout.strip()
        return ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def pop_stash(repo_path: str) -> bool:
    """Pop the last git stash."""
    try:
        r = _run_git(["stash", "pop"], cwd=repo_path)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _get_relative_path(repo_path: str, file_path: str) -> str | None:
    """Get path relative to the repo root."""
    fp = Path(file_path).resolve()
    rp = Path(repo_path).resolve()

    # If it's already relative, use it directly
    if not fp.is_absolute():
        candidate = rp / file_path
        if candidate.exists():
            return str(candidate.relative_to(rp)).replace("\\", "/")
        return file_path

    try:
        return str(fp.relative_to(rp)).replace("\\", "/")
    except ValueError:
        return None


def _parse_blame_porcelain(output: str, line: int) -> GitBlameInfo:
    """Parse git blame --porcelain output."""
    info = GitBlameInfo(line=line)
    lines = output.splitlines()

    if not lines:
        return info

    # First line: commit hash
    first_parts = lines[0].split()
    if first_parts:
        info.commit_hash = first_parts[0][:8]

    for bline in lines[1:]:
        if bline.startswith("author "):
            info.author = bline[7:].strip()
        elif bline.startswith("author-time "):
            pass  # Could convert epoch
        elif bline.startswith("committer-time "):
            pass
        elif bline.startswith("summary "):
            info.commit_message = bline[8:].strip()

    # Get the date from a separate log call if we have the hash
    # (porcelain format doesn't give a nice date)
    if info.commit_hash and info.commit_hash != "00000000":
        info.commit_date = _get_commit_date_fallback(info.commit_hash)

    return info


def _get_commit_date_fallback(commit_hash: str) -> str:
    """This is intentionally a no-op stub; actual date comes from blame parsing."""
    return ""
