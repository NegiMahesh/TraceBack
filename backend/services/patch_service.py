"""
TraceBack Patch Service.

The service follows this rule:

    ORIGINAL SOURCE
          ↓
    PATCH PREVIEW
          ↓
    MODIFIED SOURCE
          ↓
    APPROVAL
          ↓
    WRITE EXACT MODIFIED SOURCE

The final file written to disk is therefore the exact file that the
user saw in the Before / After diff.

The service also supports automatic backup and rollback.
"""

from __future__ import annotations

import hashlib
import logging
import re
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


logger = logging.getLogger(
    "traceback.patch"
)


_patch_history: list[PatchRecord] = []

_file_backups: dict[str, str] = {}


# ============================================================================
# PATH HELPERS
# ============================================================================

def resolve_repository(
    repo_path: str,
) -> Path:
    """Resolve repository path."""

    if not repo_path:
        raise ValueError(
            "Repository path is required."
        )

    repo = (
        Path(repo_path)
        .expanduser()
        .resolve()
    )

    if not repo.exists():
        raise ValueError(
            f"Repository does not exist: {repo}"
        )

    if not repo.is_dir():
        raise ValueError(
            f"Repository is not a directory: {repo}"
        )

    return repo


def resolve_target_file(
    repo_path: str,
    target_file: str,
) -> Path:
    """Resolve target file and prevent path traversal."""

    if not target_file:
        raise ValueError(
            "Target file is required."
        )

    repo = resolve_repository(
        repo_path
    )

    candidate = (
        Path(target_file)
        .expanduser()
    )

    if not candidate.is_absolute():
        candidate = (
            repo / candidate
        )

    target = candidate.resolve()

    try:
        target.relative_to(
            repo
        )

    except ValueError as exc:
        raise ValueError(
            f"Target file is outside repository: "
            f"{target_file}"
        ) from exc

    return target


def relative_target_file(
    repo_path: str,
    target_file: str,
) -> str:
    """Return repository-relative POSIX path."""

    repo = resolve_repository(
        repo_path
    )

    target = resolve_target_file(
        repo_path,
        target_file,
    )

    return (
        target
        .relative_to(repo)
        .as_posix()
    )


# ============================================================================
# HASHING
# ============================================================================

def sha256_text(
    text: str,
) -> str:
    """Calculate SHA-256 for source text."""

    return hashlib.sha256(
        text.encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(
    target: Path,
) -> str:
    """Calculate SHA-256 for a file."""

    return sha256_text(
        target.read_text(
            encoding="utf-8"
        )
    )


# ============================================================================
# PATCH PREVIEW
# ============================================================================

def preview_patch(
    patch: str,
    target_file: str,
    repo_path: str,
) -> str:
    """
    Generate the exact modified source without changing the file.
    """

    if not patch or not patch.strip():
        raise ValueError(
            "Patch is empty."
        )

    target = resolve_target_file(
        repo_path,
        target_file,
    )

    if not target.is_file():
        raise FileNotFoundError(
            f"Target file does not exist: {target}"
        )

    original = target.read_text(
        encoding="utf-8"
    )

    normalized_patch = (
        normalize_patch(
            patch=patch,
            repo_path=repo_path,
            target_file=target_file,
        )
    )

    modified = apply_unified_diff(
        original=original,
        patch=normalized_patch,
    )

    if modified is None:
        raise ValueError(
            "The patch does not match the current source."
        )

    if modified == original:
        raise ValueError(
            "The patch produces no actual source change."
        )

    return modified


# ============================================================================
# PATCH NORMALIZATION
# ============================================================================

def normalize_patch(
    patch: str,
    repo_path: str,
    target_file: str,
) -> str:
    """Normalize AI-generated patch headers."""

    if not patch:
        return ""

    relative_path = relative_target_file(
        repo_path,
        target_file,
    )

    text = (
        patch
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .strip()
    )

    # Remove markdown fences.
    text = re.sub(
        r"^```(?:diff|patch)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    lines = text.splitlines()

    # Locate actual diff.
    hunk_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("@@ ")
        ),
        None,
    )

    old_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("--- ")
        ),
        None,
    )

    new_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("+++ ")
        ),
        None,
    )

    # No hunk at all.
    if hunk_index is None:
        return text

    # Build proper headers.
    if (
        old_index is None
        or new_index is None
    ):

        body = lines[
            hunk_index:
        ]

        lines = [
            f"--- a/{relative_path}",
            f"+++ b/{relative_path}",
            *body,
        ]

    else:

        lines[old_index] = (
            f"--- a/{relative_path}"
        )

        lines[new_index] = (
            f"+++ b/{relative_path}"
        )

    return (
        "\n".join(lines).strip()
        + "\n"
    )


# ============================================================================
# VALIDATION
# ============================================================================

def validate_patch(
    patch: str,
    target_file: str,
    repo_path: str,
) -> PatchValidation:
    """Validate patch against current source."""

    result = PatchValidation(
        target_file=target_file
    )

    try:

        repo = resolve_repository(
            repo_path
        )

        target = resolve_target_file(
            repo_path,
            target_file,
        )

    except ValueError as exc:

        result.reason = str(exc)
        return result

    if not target.is_file():

        result.reason = (
            f"Target file does not exist: "
            f"{target_file}"
        )

        return result

    result.target_exists = True

    try:

        result.has_uncommitted_changes = (
            git_service.has_uncommitted_changes(
                str(repo)
            )
        )

    except Exception:

        result.has_uncommitted_changes = (
            False
        )

    try:

        original = target.read_text(
            encoding="utf-8"
        )

        modified = preview_patch(
            patch=patch,
            target_file=target_file,
            repo_path=str(repo),
        )

        if modified == original:

            result.reason = (
                "Patch produces no source change."
            )

            return result

        result.context_matches = True
        result.valid = True
        result.reason = (
            "Patch validated successfully."
        )

    except Exception as exc:

        result.context_matches = False
        result.valid = False
        result.reason = str(exc)

    return result


# ============================================================================
# APPLY
# ============================================================================

def apply_patch(
    patch: str,
    target_file: str,
    repo_path: str,
    investigation_id: str = "",
    expected_original_sha256: str = "",
    expected_modified_code: str = "",
) -> PatchApplyResult:
    """
    Apply a patch.

    If expected_modified_code is supplied, it becomes the authoritative
    source that gets written.

    If expected_original_sha256 is supplied, approval is refused when the
    file has changed since analysis.
    """

    result = PatchApplyResult()

    try:

        repo = resolve_repository(
            repo_path
        )

        target = resolve_target_file(
            repo_path,
            target_file,
        )

    except ValueError as exc:

        result.message = str(exc)
        return result

    if not target.is_file():

        result.message = (
            f"Target file not found: "
            f"{target_file}"
        )

        return result

    # -----------------------------------------------------------------------
    # Read current source.
    # -----------------------------------------------------------------------

    try:

        current_source = (
            target.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:

        result.message = (
            f"Could not read target file: "
            f"{exc}"
        )

        return result

    current_hash = (
        sha256_text(
            current_source
        )
    )

    # -----------------------------------------------------------------------
    # Detect source changing after analysis.
    # -----------------------------------------------------------------------

    if (
        expected_original_sha256
        and
        current_hash
        != expected_original_sha256
    ):

        result.message = (
            "Patch rejected because the source file "
            "changed after analysis. Please run a new analysis."
        )

        return result

    # -----------------------------------------------------------------------
    # Determine exact modified source.
    # -----------------------------------------------------------------------

    try:

        if expected_modified_code:

            modified_source = (
                expected_modified_code
            )

        else:

            normalized_patch = (
                normalize_patch(
                    patch=patch,
                    repo_path=str(repo),
                    target_file=target_file,
                )
            )

            modified_source = (
                apply_unified_diff(
                    original=current_source,
                    patch=normalized_patch,
                )
            )

            if modified_source is None:
                result.message = (
                    "Patch does not match the current source."
                )
                return result

    except Exception as exc:

        result.message = (
            f"Could not prepare modified source: "
            f"{exc}"
        )

        return result

    # -----------------------------------------------------------------------
    # Validate actual change.
    # -----------------------------------------------------------------------

    if modified_source == current_source:

        result.message = (
            "Patch produces no actual source change."
        )

        return result

    # -----------------------------------------------------------------------
    # Backup.
    # -----------------------------------------------------------------------

    backup_ref = (
        f"backup-{uuid.uuid4().hex[:8]}"
    )

    try:

        backup_dir = (
            Path(BACKUPS_DIR)
            .resolve()
        )

        backup_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        backup_file = (
            backup_dir
            / f"{backup_ref}_{target.name}"
        )

        backup_file.write_text(
            current_source,
            encoding="utf-8",
        )

        _file_backups[
            backup_ref
        ] = current_source

        result.backup_ref = (
            backup_ref
        )

    except Exception as exc:

        result.message = (
            f"Failed to create backup: "
            f"{exc}"
        )

        return result

    # -----------------------------------------------------------------------
    # Write exact modified source.
    # -----------------------------------------------------------------------

    try:

        target.write_text(
            modified_source,
            encoding="utf-8",
        )

        written_source = (
            target.read_text(
                encoding="utf-8"
            )
        )

        if written_source != modified_source:

            raise IOError(
                "Written source does not match "
                "verified modified source."
            )

        result.success = True

        result.message = (
            "Patch applied successfully."
        )

        result.files_modified = [
            relative_target_file(
                str(repo),
                target_file,
            )
        ]

        record = PatchRecord(
            id=(
                f"PATCH-"
                f"{len(_patch_history) + 1:04d}"
            ),
            investigation_id=(
                investigation_id
            ),
            file=relative_target_file(
                str(repo),
                target_file,
            ),
            patch=(
                normalize_patch(
                    patch=patch,
                    repo_path=str(repo),
                    target_file=target_file,
                )
                if patch
                else ""
            ),
            status=PatchStatus.APPLIED,
            applied_at=time.strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            backup_ref=backup_ref,
        )

        _patch_history.append(
            record
        )

    except Exception as exc:

        logger.exception(
            "Patch application failed"
        )

        try:

            target.write_text(
                current_source,
                encoding="utf-8",
            )

        except Exception:

            logger.exception(
                "Emergency restoration failed"
            )

        result.message = (
            f"Patch application failed: "
            f"{exc}"
        )

    return result


# ============================================================================
# ROLLBACK
# ============================================================================

def rollback(
    backup_ref: str,
    target_file: str,
    repo_path: str,
) -> RollbackResult:

    result = RollbackResult()

    if not backup_ref:

        result.message = (
            "Backup reference is required."
        )

        return result

    try:

        target = resolve_target_file(
            repo_path,
            target_file,
        )

    except ValueError as exc:

        result.message = str(exc)
        return result

    original = (
        _file_backups.get(
            backup_ref
        )
    )

    # Try disk backup.
    if original is None:

        backup_dir = (
            Path(BACKUPS_DIR)
            .resolve()
        )

        matches = list(
            backup_dir.glob(
                f"{backup_ref}_*"
            )
        )

        if matches:

            try:

                original = (
                    matches[0]
                    .read_text(
                        encoding="utf-8"
                    )
                )

            except OSError:
                original = None

    if original is None:

        result.message = (
            f"No backup found for reference: "
            f"{backup_ref}"
        )

        return result

    try:

        target.write_text(
            original,
            encoding="utf-8",
        )

        restored = (
            target.read_text(
                encoding="utf-8"
            )
        )

        if restored != original:

            raise IOError(
                "Rollback verification failed."
            )

        result.success = True

        result.message = (
            "Rollback completed successfully."
        )

        for record in _patch_history:

            if (
                record.backup_ref
                == backup_ref
            ):

                record.status = (
                    PatchStatus.ROLLED_BACK
                )

                break

    except Exception as exc:

        result.message = (
            f"Rollback failed: {exc}"
        )

    return result


def get_patch_history() -> list[PatchRecord]:
    return list(
        _patch_history
    )


# ============================================================================
# UNIFIED DIFF ENGINE
# ============================================================================

_HUNK_RE = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?"
    r"\s+\+(\d+)(?:,(\d+))?"
    r"\s+@@"
)


def apply_unified_diff(
    original: str,
    patch: str,
) -> str | None:
    """
    Convert original source into modified source.

    The implementation uses actual hunk content rather than blindly
    trusting AI-generated line counts.
    """

    source = (
        original
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
    )

    source_lines = (
        source.splitlines()
    )

    had_final_newline = (
        source.endswith("\n")
    )

    text = (
        patch
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
    )

    patch_lines = (
        text.splitlines()
    )

    hunks = []

    current_hunk = None

    for line in patch_lines:

        if line.startswith("--- "):
            continue

        if line.startswith("+++ "):
            continue

        match = _HUNK_RE.match(
            line
        )

        if match:

            if current_hunk is not None:
                hunks.append(
                    current_hunk
                )

            current_hunk = {
                "old_start": int(
                    match.group(1)
                ),
                "old_count": int(
                    match.group(2)
                    or "1"
                ),
                "new_start": int(
                    match.group(3)
                ),
                "new_count": int(
                    match.group(4)
                    or "1"
                ),
                "lines": [],
            }

            continue

        if current_hunk is None:
            continue

        if line == (
            r"\ No newline at end of file"
        ):
            continue

        if (
            line.startswith(" ")
            or line.startswith("+")
            or line.startswith("-")
        ):

            current_hunk[
                "lines"
            ].append(
                line
            )

        else:

            # Be tolerant when AI omitted a context marker.
            current_hunk[
                "lines"
            ].append(
                " " + line
            )

    if current_hunk is not None:

        hunks.append(
            current_hunk
        )

    if not hunks:
        return None

    # Apply from bottom to top.
    for hunk in reversed(
        hunks
    ):

        old_lines = []
        new_lines = []

        for line in hunk["lines"]:

            prefix = line[0]

            content = line[1:]

            if prefix in (
                " ",
                "-",
            ):
                old_lines.append(
                    content
                )

            if prefix in (
                " ",
                "+",
            ):
                new_lines.append(
                    content
                )

        expected_index = max(
            0,
            hunk["old_start"] - 1,
        )

        location = (
            find_hunk_location(
                source_lines=source_lines,
                expected_index=expected_index,
                old_lines=old_lines,
            )
        )

        if location is None:

            return None

        source_lines[
            location:
            location + len(old_lines)
        ] = new_lines

    modified = "\n".join(
        source_lines
    )

    if had_final_newline:
        modified += "\n"

    return modified


def find_hunk_location(
    source_lines: list[str],
    expected_index: int,
    old_lines: list[str],
) -> int | None:
    """Find exact or whitespace-tolerant hunk location."""

    if not old_lines:

        return min(
            max(
                0,
                expected_index,
            ),
            len(source_lines),
        )

    # Exact expected location.
    if (
        expected_index >= 0
        and
        expected_index
        + len(old_lines)
        <= len(source_lines)
    ):

        candidate = source_lines[
            expected_index:
            expected_index
            + len(old_lines)
        ]

        if candidate == old_lines:

            return expected_index

    # Exact full-file search.
    maximum = (
        len(source_lines)
        - len(old_lines)
        + 1
    )

    if maximum <= 0:
        return None

    for index in range(
        maximum
    ):

        candidate = source_lines[
            index:
            index
            + len(old_lines)
        ]

        if candidate == old_lines:

            return index

    # Whitespace-tolerant search.
    normalized_old = [
        line.strip()
        for line in old_lines
    ]

    for index in range(
        maximum
    ):

        candidate = source_lines[
            index:
            index
            + len(old_lines)
        ]

        if [
            line.strip()
            for line in candidate
        ] == normalized_old:

            return index

    return None