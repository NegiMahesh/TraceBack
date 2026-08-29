"""Pydantic models for AI analysis and investigations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    DIAGNOSED = "DIAGNOSED"
    PATCH_READY = "PATCH_READY"
    PATCH_APPLIED = "PATCH_APPLIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class AIAnalysis(BaseModel):
    """Structured output expected from the LLM."""

    summary: str = ""
    root_cause: str = ""
    severity: str = "MEDIUM"
    confidence: float = Field(0.0, ge=0, le=100)
    explanation: str = ""
    affected_file: str = ""
    affected_line: int = 0
    fix_strategy: str = ""
    patch: str = ""
    test_case: str = ""
    potential_risks: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)


class ExplanationMode(str, Enum):
    BEGINNER = "beginner"
    DEVELOPER = "developer"
    EXPERT = "expert"


class GitBlameInfo(BaseModel):
    """Git blame data for a specific line."""

    author: str = ""
    commit_hash: str = ""
    commit_date: str = ""
    commit_message: str = ""
    line: int = 0


class SourceContext(BaseModel):
    """Source code context around the error."""

    file_path: str = ""
    content: str = ""
    start_line: int = 0
    end_line: int = 0
    error_line: int = 0
    function_name: str = ""
    imports: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Result from running tests."""

    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_ms: int = 0
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    success: bool = False


class VerificationStep(BaseModel):
    """A single step in the verification pipeline."""

    name: str
    status: str = "pending"  # pending | running | passed | failed | skipped
    message: str = ""
    duration_ms: int = 0


class VerificationReport(BaseModel):
    """Full verification report after applying a fix."""

    steps: list[VerificationStep] = Field(default_factory=list)
    overall_success: bool = False
    generated_test_result: Optional[TestResult] = None
    existing_test_result: Optional[TestResult] = None
    rerun_result: Optional[dict] = None
    verdict: str = "PENDING"


class Investigation(BaseModel):
    """A complete investigation record."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: InvestigationStatus = InvestigationStatus.PENDING
    error_type: str = ""
    error_message: str = ""
    file: str = ""
    line: int = 0
    function: str = ""
    severity: str = "MEDIUM"
    confidence: float = 0.0
    root_cause: str = ""
    explanation: str = ""
    fix_strategy: str = ""
    patch: str = ""
    test_case: str = ""
    potential_risks: list[str] = Field(default_factory=list)
    source_context: Optional[SourceContext] = None
    git_blame: Optional[GitBlameInfo] = None
    verification: Optional[VerificationReport] = None
    duration_ms: int = 0
    raw_traceback: str = ""
    repo_path: str = ""
