"""Patch service — validation, application, rollback with safety checks."""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path

from backend.config import BACKUPS_DIR
from backend.models.patch import (
    PatchApplyResult,
    PatchRecord,
    PatchStatus,
    PatchValidation,
    RollbackResult,
)
from backend.services import git_service

logger = logging.getLogger("traceback.patch")

# In-memory patch history (in production would use a DB)
_patch_history: list[PatchRecord] = []
_file_backups: dict[str, str] = {}  # backup_ref -> original content


def validate_patch(
    patch: str, target_file: str, repo_path: str
) -> PatchValidation:
    """Validate a patch before application."""
    result = PatchValidation(target_file=target_file)

    if not patch or not patch.strip():
        result.reason = "Patch is empty"
        return result

    # Check target file exists
    target = Path(repo_path) / target_file if not Path(target_file).is_absolute() else Path(target_file)
    if not target.is_file():
        result.reason = f"Target file does not exist: {target_file}"
        return result
    result.target_exists = True

    # Check for uncommitted changes
    result.has_uncommitted_changes = git_service.has_uncommitted_changes(repo_path)

    # Validate patch format — basic checks
    if not _is_valid_patch_format(patch):
        result.reason = "Patch does not appear to be a valid unified diff or code change"
        return result

    # Check context matches (if it's a unified diff)
    result.context_matches = _check_context_matches(patch, target)

    if not result.context_matches:
        result.reason = "Patch context does not match current source"
        return result

    result.valid = True
    result.reason = "Patch validated successfully"
    return result


def apply_patch(
    patch: str,
    target_file: str,
    repo_path: str,
    investigation_id: str = "",
) -> PatchApplyResult:
    """Apply a patch with backup and safety checks."""
    result = PatchApplyResult()

    # Resolve target path
    target = Path(repo_path) / target_file if not Path(target_file).is_absolute() else Path(target_file)
    if not target.is_file():
        result.message = f"Target file not found: {target_file}"
        return result

    # Create backup
    backup_ref = f"backup-{uuid.uuid4().hex[:8]}"
    try:
        original_content = target.read_text(encoding="utf-8")
        _file_backups[backup_ref] = original_content

        # Also save to disk
        backup_dir = Path(BACKUPS_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / f"{backup_ref}_{target.name}"
        backup_file.write_text(original_content, encoding="utf-8")
        result.backup_ref = backup_ref
    except Exception as e:
        result.message = f"Failed to create backup: {e}"
        return result

    # Try to apply the patch
    try:
        new_content = _apply_patch_to_content(original_content, patch, target_file)
        if new_content is None:
            result.message = "Failed to apply patch — could not match context"
            return result

        # Write the patched file
        target.write_text(new_content, encoding="utf-8")
        result.success = True
        result.message = "Patch applied successfully"
        result.files_modified = [str(target_file)]

        # Record in history
        record = PatchRecord(
            id=f"PATCH-{len(_patch_history) + 1:04d}",
            investigation_id=investigation_id,
            file=target_file,
            patch=patch,
            status=PatchStatus.APPLIED,
            applied_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            backup_ref=backup_ref,
        )
        _patch_history.append(record)

    except Exception as e:
        # Rollback on failure
        logger.error("Patch application failed, rolling back: %s", e)
        try:
            target.write_text(original_content, encoding="utf-8")
        except Exception:
            pass
        result.message = f"Patch failed: {e}"

    return result


def rollback(backup_ref: str, target_file: str, repo_path: str) -> RollbackResult:
    """Rollback a patch using the backup reference."""
    result = RollbackResult()

    # Try in-memory backup first
    original = _file_backups.get(backup_ref)

    # Then try disk backup
    if not original:
        backup_dir = Path(BACKUPS_DIR)
        for f in backup_dir.glob(f"{backup_ref}_*"):
            try:
                original = f.read_text(encoding="utf-8")
                break
            except Exception:
                continue

    if not original:
        result.message = f"No backup found for reference: {backup_ref}"
        return result

    target = Path(repo_path) / target_file if not Path(target_file).is_absolute() else Path(target_file)

    try:
        target.write_text(original, encoding="utf-8")
        result.success = True
        result.message = "Rollback completed successfully"

        # Update patch history
        for record in _patch_history:
            if record.backup_ref == backup_ref:
                record.status = PatchStatus.ROLLED_BACK
                break

    except Exception as e:
        result.message = f"Rollback failed: {e}"

    return result


def get_patch_history() -> list[PatchRecord]:
    """Get all patch records."""
    return list(_patch_history)


def _is_valid_patch_format(patch: str) -> bool:
    """Basic validation that this looks like a patch."""
    lines = patch.strip().splitlines()
    if not lines:
        return False

    # It's a unified diff if it has +/- lines
    has_add = any(l.startswith("+") and not l.startswith("+++") for l in lines)
    has_remove = any(l.startswith("-") and not l.startswith("---") for l in lines)

    return has_add or has_remove


def _check_context_matches(patch: str, target: Path) -> bool:
    """Check that removed lines in the patch match the current file content."""
    try:
        content = target.read_text(encoding="utf-8")
        lines = content.splitlines()

        for pline in patch.strip().splitlines():
            if pline.startswith("-") and not pline.startswith("---"):
                # This line should exist in the file
                check = pline[1:].strip()
                if check and not any(check in fl for fl in lines):
                    return False
        return True
    except Exception:
        return False


def _apply_patch_to_content(
    original: str, patch: str, target_file: str
) -> str | None:
    """Apply a unified diff patch to file content.

    This is a simplified patch applier that handles common cases.
    For production, use `git apply` or `patch` command.
    """
    original_lines = original.splitlines(keepends=True)
    patch_lines = patch.strip().splitlines()

    # Extract the removed and added lines from the diff
    remove_lines: list[str] = []
    add_lines: list[str] = []

    for pline in patch_lines:
        if pline.startswith("---") or pline.startswith("+++"):
            continue
        if pline.startswith("@@"):
            continue
        if pline.startswith("-"):
            remove_lines.append(pline[1:])
        elif pline.startswith("+"):
            add_lines.append(pline[1:])

    if not remove_lines and not add_lines:
        return None

    # Find the location of removed lines in the original
    result_lines = list(original_lines)

    if remove_lines:
        start_idx = _find_block(result_lines, remove_lines)
        if start_idx is None:
            return None

        # Detect original indentation from the matched line
        orig_line = result_lines[start_idx]
        indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]

        formatted_adds = []
        for l in add_lines:
            line_str = l.rstrip("\r\n")
            if line_str.strip() and not line_str.startswith(" ") and not line_str.startswith("\t"):
                line_str = indent + line_str
            formatted_adds.append(line_str + "\n")

        end_idx = start_idx + len(remove_lines)
        result_lines[start_idx:end_idx] = formatted_adds
    else:
        new_add = [l + "\n" if not l.endswith("\n") else l for l in add_lines]
        result_lines.extend(new_add)

    return "".join(result_lines)



def _find_block(lines: list[str], block: list[str]) -> int | None:
    """Find the starting index of a block of lines in the file."""
    if not block:
        return None

    first = block[0].strip()
    for i in range(len(lines)):
        if lines[i].strip() == first:
            # Check if the rest of the block matches
            match = True
            for j, bline in enumerate(block):
                if i + j >= len(lines):
                    match = False
                    break
                if lines[i + j].strip() != bline.strip():
                    match = False
                    break
            if match:
                return i
    return None
