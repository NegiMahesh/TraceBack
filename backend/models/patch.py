"""Pydantic models for patch operations."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PatchStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class PatchValidation(BaseModel):
    """Result of validating a patch before application."""

    valid: bool = False
    reason: str = ""
    target_file: str = ""
    target_exists: bool = False
    has_uncommitted_changes: bool = False
    context_matches: bool = False


class PatchApplyRequest(BaseModel):
    """Request to apply a patch."""

    investigation_id: str = Field(..., description="Investigation this patch belongs to")
    patch: str = Field(..., description="Unified diff content")
    target_file: str = Field(..., description="File to patch")
    repo_path: Optional[str] = Field(None, description="Repository path")


class PatchApplyResult(BaseModel):
    """Result of applying a patch."""

    success: bool = False
    message: str = ""
    backup_ref: str = ""
    files_modified: list[str] = Field(default_factory=list)


class RollbackRequest(BaseModel):
    """Request to rollback a patch."""

    investigation_id: str
    backup_ref: str = ""
    repo_path: Optional[str] = None


class RollbackResult(BaseModel):
    """Result of rolling back a patch."""

    success: bool = False
    message: str = ""


class PatchRecord(BaseModel):
    """Historical record of a patch."""

    id: str = ""
    investigation_id: str = ""
    file: str = ""
    line: int = 0
    patch: str = ""
    status: PatchStatus = PatchStatus.PENDING
    applied_at: str = ""
    backup_ref: str = ""
    test_passed: bool = False
    verified: bool = False
