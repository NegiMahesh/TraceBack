"""
TraceBack Patch Service.

Security principle:

    AI proposes a patch.
    TraceBack validates the patch.
    TraceBack applies only that patch.

The AI can never directly overwrite the target file with a complete
replacement source file.
"""

from __future__ import annotations

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

from backend.services import (
    git_service,
)

from backend.services.ollama_service import (
    ollama_service,
)


logger = logging.getLogger(
    "traceback.patch"
)


_patch_history: list[
    PatchRecord
] = []

_file_backups: dict[
    str,
    str,
] = {}


# ============================================================================
# PATHS
# ============================================================================

def resolve_repository(
    repo_path: str,
) -> Path:

    if not repo_path:

        raise ValueError(
            "Repository path is required."
        )

    repo = (
        Path(repo_path)
        .expanduser()
        .resolve()
    )

    if not repo.is_dir():

        raise ValueError(
            f"Repository does not exist: {repo}"
        )

    return repo


def resolve_target_file(
    repo_path: str,
    target_file: str,
) -> Path:

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
# PATCH PREVIEW
# ============================================================================

def preview_patch(
    patch: str,
    target_file: str,
    repo_path: str,
) -> str:

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

    normalized = normalize_patch(
        patch=patch,
        repo_path=repo_path,
        target_file=target_file,
    )

    modified = (
        apply_unified_diff(
            original,
            normalized,
        )
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
# VALIDATE
# ============================================================================

def validate_patch(
    patch: str,
    target_file: str,
    repo_path: str,
) -> PatchValidation:

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
            f"Target file does not exist: {target_file}"
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

        # Source must actually change.
        if modified == original:

            result.reason = (
                "Patch produces no source change."
            )

            return result

        # Additional AI safety validation.
        if not (
            _structure_is_safe(
                original,
                modified,
            )
        ):

            result.reason = (
                "Patch removes unrelated program structure."
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
            f"Target file not found: {target_file}"
        )

        return result

    # ========================================================================
    # CURRENT SOURCE
    # ========================================================================

    try:

        current_source = target.read_text(
            encoding="utf-8"
        )

    except Exception as exc:

        result.message = (
            f"Could not read target file: {exc}"
        )

        return result

    # ========================================================================
    # STALE-SOURCE PROTECTION
    # ========================================================================

    if expected_original_sha256:

        import hashlib

        actual_hash = hashlib.sha256(
            current_source.encode(
                "utf-8"
            )
        ).hexdigest()

        if (
            actual_hash
            != expected_original_sha256
        ):

            result.message = (
                "Patch rejected because the file changed "
                "after analysis. Run a new analysis."
            )

            return result

    # ========================================================================
    # BUILD MODIFIED SOURCE
    # ========================================================================

    try:

        if expected_modified_code:

            modified_source = (
                expected_modified_code
            )

            # Never allow the supplied "modified" source to be empty.
            if not modified_source.strip():

                result.message = (
                    "Patch rejected because modified source is empty."
                )

                return result

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
                    current_source,
                    normalized_patch,
                )
            )

            if modified_source is None:

                result.message = (
                    "Patch validation failed: "
                    "the patch does not match the current source."
                )

                return result

    except Exception as exc:

        result.message = (
            f"Patch preparation failed: {exc}"
        )

        return result

    # ========================================================================
    # SOURCE SAFETY
    # ========================================================================

    if modified_source == current_source:

        result.message = (
            "Patch produces no actual source change."
        )

        return result

    if not _python_is_valid(
        modified_source
    ):

        result.message = (
            "Patch rejected because the resulting file "
            "contains invalid Python."
        )

        return result

    safe = _structure_is_safe(
        current_source,
        modified_source,
    )

    if not safe:

        result.message = (
            "Patch rejected because it removes "
            "unrelated program structure."
        )

        return result

    # ========================================================================
    # BACKUP
    # ========================================================================

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

        backup_path = (
            backup_dir
            / f"{backup_ref}_{target.name}"
        )

        backup_path.write_text(
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
            f"Failed to create backup: {exc}"
        )

        return result

    # ========================================================================
    # APPLY EXACT VERIFIED SOURCE
    # ========================================================================

    try:

        target.write_text(
            modified_source,
            encoding="utf-8",
        )

        written = target.read_text(
            encoding="utf-8"
        )

        if written != modified_source:

            raise IOError(
                "Written file differs from validated source."
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
                    patch,
                    str(repo),
                    target_file,
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
                "Emergency rollback failed"
            )

        result.message = (
            f"Patch application failed: {exc}"
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
                    matches[0].read_text(
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

        restored = target.read_text(
            encoding="utf-8"
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


def get_patch_history() -> list[
    PatchRecord
]:

    return list(
        _patch_history
    )


# ============================================================================
# PATCH NORMALIZATION
# ============================================================================

def normalize_patch(
    patch: str,
    repo_path: str,
    target_file: str,
) -> str:

    if not patch:

        return ""

    relative = relative_target_file(
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

    old_found = False
    new_found = False

    for index, line in enumerate(
        lines
    ):

        if line.startswith(
            "--- "
        ):

            lines[index] = (
                f"--- a/{relative}"
            )

            old_found = True

        elif line.startswith(
            "+++ "
        ):

            lines[index] = (
                f"+++ b/{relative}"
            )

            new_found = True

    hunk_index = next(
        (
            i
            for i, line in enumerate(lines)
            if line.startswith("@@ ")
        ),
        None,
    )

    if (
        hunk_index is not None
        and
        not (
            old_found
            and
            new_found
        )
    ):

        lines = [
            f"--- a/{relative}",
            f"+++ b/{relative}",
            *lines[hunk_index:],
        ]

    return (
        "\n".join(lines).strip()
        + "\n"
    )


# ============================================================================
# UNIFIED DIFF APPLICATION
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

    final_newline = (
        source.endswith("\n")
    )

    patch_lines = (
        patch
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .splitlines()
    )

    hunks = []

    current = None

    for line in patch_lines:

        if line.startswith(
            "--- "
        ):
            continue

        if line.startswith(
            "+++ "
        ):
            continue

        match = _HUNK_RE.match(
            line
        )

        if match:

            if current is not None:
                hunks.append(
                    current
                )

            current = {
                "old_start": int(
                    match.group(1)
                ),
                "old_count": int(
                    match.group(2)
                    or "1"
                ),
                "lines": [],
            }

            continue

        if current is None:
            continue

        if line == (
            r"\ No newline at end of file"
        ):
            continue

        if line.startswith(
            (
                " ",
                "+",
                "-",
            )
        ):

            current[
                "lines"
            ].append(
                line
            )

        else:

            current[
                "lines"
            ].append(
                " " + line
            )

    if current is not None:
        hunks.append(
            current
        )

    if not hunks:
        return None

    # Apply bottom-to-top.
    for hunk in reversed(
        hunks
    ):

        old_lines = []
        new_lines = []

        for line in hunk[
            "lines"
        ]:

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

        expected = max(
            0,
            hunk["old_start"] - 1,
        )

        location = (
            _find_location(
                source_lines,
                expected,
                old_lines,
            )
        )

        if location is None:

            return None

        source_lines[
            location:
            location
            + len(old_lines)
        ] = new_lines

    modified = "\n".join(
        source_lines
    )

    if final_newline:

        modified += "\n"

    return modified


def _find_location(
    source_lines: list[str],
    expected: int,
    old_lines: list[str],
) -> int | None:

    if not old_lines:

        return min(
            max(
                0,
                expected,
            ),
            len(source_lines),
        )

    # Exact expected location.
    if (
        expected >= 0
        and
        expected
        + len(old_lines)
        <= len(source_lines)
    ):

        if (
            source_lines[
                expected:
                expected + len(old_lines)
            ]
            == old_lines
        ):

            return expected

    # Exact search.
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

        if (
            source_lines[
                index:
                index + len(old_lines)
            ]
            == old_lines
        ):

            return index

    # Whitespace-tolerant.
    expected_normalized = [
        line.strip()
        for line in old_lines
    ]

    for index in range(
        maximum
    ):

        candidate = source_lines[
            index:
            index + len(old_lines)
        ]

        if [
            line.strip()
            for line in candidate
        ] == expected_normalized:

            return index

    return None


# ============================================================================
# SAFETY
# ============================================================================

def _python_is_valid(
    source: str,
) -> bool:

    if not source.strip():
        return False

    try:

        import ast

        ast.parse(
            source
        )

        return True

    except SyntaxError:

        return False


def _structure_is_safe(
    original: str,
    modified: str,
) -> bool:

    import ast

    try:

        old_tree = ast.parse(
            original
        )

        new_tree = ast.parse(
            modified
        )

    except SyntaxError:

        return False

    old_functions = {
        node.name
        for node in old_tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    new_functions = {
        node.name
        for node in new_tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }

    # Never silently delete functions.
    if (
        old_functions
        - new_functions
    ):

        return False

    old_classes = {
        node.name
        for node in old_tree.body
        if isinstance(
            node,
            ast.ClassDef,
        )
    }

    new_classes = {
        node.name
        for node in new_tree.body
        if isinstance(
            node,
            ast.ClassDef,
        )
    }

    if (
        old_classes
        - new_classes
    ):

        return False

    # Never remove the __main__ block.
    old_has_main = (
        _has_main_guard(
            old_tree
        )
    )

    new_has_main = (
        _has_main_guard(
            new_tree
        )
    )

    if (
        old_has_main
        and
        not new_has_main
    ):

        return False

    # Protect imports.
    old_imports = {
        _import_signature(
            node
        )
        for node in old_tree.body
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        )
    }

    new_imports = {
        _import_signature(
            node
        )
        for node in new_tree.body
        if isinstance(
            node,
            (
                ast.Import,
                ast.ImportFrom,
            ),
        )
    }

    if (
        old_imports
        - new_imports
    ):

        return False

    # A meaningful program should not suddenly become tiny.
    old_lines = [
        line
        for line in original.splitlines()
        if line.strip()
    ]

    new_lines = [
        line
        for line in modified.splitlines()
        if line.strip()
    ]

    if (
        len(old_lines) >= 10
        and
        len(new_lines)
        < max(
            5,
            int(
                len(old_lines)
                * 0.50
            ),
        )
    ):

        return False

    return True


def _has_main_guard(
    tree,
) -> bool:

    import ast

    for node in tree.body:

        if not isinstance(
            node,
            ast.If,
        ):

            continue

        test = node.test

        if not isinstance(
            test,
            ast.Compare,
        ):

            continue

        if not isinstance(
            test.left,
            ast.Name,
        ):

            continue

        if (
            test.left.id
            != "__name__"
        ):

            continue

        if not test.comparators:
            continue

        comparator = (
            test.comparators[0]
        )

        if (
            isinstance(
                comparator,
                ast.Constant,
            )
            and
            comparator.value
            == "__main__"
        ):

            return True

    return False


def _import_signature(
    node,
) -> str:

    import ast

    if isinstance(
        node,
        ast.Import,
    ):

        return (
            "import:"
            +
            ",".join(
                alias.name
                for alias
                in node.names
            )
        )

    if isinstance(
        node,
        ast.ImportFrom,
    ):

        return (
            "from:"
            +
            str(
                node.module
            )
            +
            ":"
            +
            ",".join(
                alias.name
                for alias
                in node.names
            )
        )

    return ""