"""Ollama / LLM service for TraceBack crash analysis."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
)
from backend.models.analysis import AIAnalysis

logger = logging.getLogger("traceback.ollama")


class OllamaService:
    """Client for local Ollama."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        temperature: float = OLLAMA_TEMPERATURE,
        timeout: int = OLLAMA_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    async def health_check(self) -> dict:
        """Check whether Ollama is available."""

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self.base_url}/api/tags"
                )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"HTTP {response.status_code}",
                }

            data = response.json()

            models = [
                item.get("name", "")
                for item in data.get("models", [])
            ]

            available = any(
                self.model == model
                or self.model in model
                for model in models
            )

            return {
                "status": "connected",
                "models": models,
                "current_model": self.model,
                "model_available": available,
            }

        except httpx.ConnectError:
            return {
                "status": "offline",
                "message": "Cannot connect to Ollama",
            }

        except Exception as exc:
            logger.exception(
                "Ollama health check failed"
            )

            return {
                "status": "error",
                "message": str(exc),
            }

    async def analyze_crash(
        self,
        error_type: str,
        error_message: str,
        source_code: str,
        file_path: str,
        line_number: int,
        function_name: str,
        git_blame: str = "",
        related_code: str = "",
        traceback_raw: str = "",
    ) -> AIAnalysis:
        """Analyze a crash and generate a source-aware repair."""

        prompt = self._build_analysis_prompt(
            error_type=error_type,
            error_message=error_message,
            source_code=source_code,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            git_blame=git_blame,
            related_code=related_code,
            traceback_raw=traceback_raw,
        )

        raw_response = await self._generate(prompt)

        return self._parse_analysis(
            raw_response,
            fallback_file=file_path,
            fallback_line=line_number,
            source_code=source_code,
            error_type=error_type,
            error_message=error_message,
        )

    async def _generate(
        self,
        prompt: str,
    ) -> str:
        """Call Ollama."""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "num_predict": 4096,
            },
        }

        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "response",
                "",
            )

    def _build_analysis_prompt(
        self,
        error_type: str,
        error_message: str,
        source_code: str,
        file_path: str,
        line_number: int,
        function_name: str,
        git_blame: str = "",
        related_code: str = "",
        traceback_raw: str = "",
    ) -> str:
        """Create the debugging prompt."""

        normalized_file = Path(
            file_path.replace("\\", "/")
        ).as_posix()

        return f"""
You are TraceBack, an autonomous Python debugging and repair engine.

Analyze ONLY the supplied crash and source.

CRITICAL RULES:

- Never assume auth.py.
- Never assume another filename.
- The target file is exactly:
  {normalized_file}
- Never patch unrelated files.
- Do not invent source code.
- Do not invent functions.
- Make the smallest possible change.
- Return valid JSON only.

CRASH
=====
Error type:
{error_type}

Error message:
{error_message}

Target file:
{normalized_file}

Target line:
{line_number}

Function:
{function_name}

TRACEBACK
=========
{traceback_raw}

SOURCE
======
{source_code}

GIT
===
{git_blame}

RETURN THIS JSON:
{{
  "summary": "...",
  "root_cause": "...",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0,
  "explanation": "...",
  "affected_file": "{normalized_file}",
  "affected_line": {line_number},
  "fix_strategy": "...",
  "patch": "...",
  "test_case": "...",
  "potential_risks": [],
  "related_files": []
}}

PATCH FORMAT RULES
==================
The patch value MUST be a complete unified diff.

It MUST start with:

--- a/{normalized_file}
+++ b/{normalized_file}

Then provide one or more valid hunks.

Example structure:

--- a/example.py
+++ b/example.py
@@ -10,3 +10,3 @@
 old line
 old line
+new line

Never return:
- prose
- markdown fences
- JSON inside the patch
- a partial hunk
- only '+' and '-' lines without @@ headers

TEST FORMAT RULES
=================
The test must test the actual bug.

The test must import the actual target module.

Never use:
from auth import *

unless the supplied file is actually auth.py.
"""

    def _parse_analysis(
        self,
        raw: str,
        fallback_file: str,
        fallback_line: int,
        source_code: str = "",
        error_type: str = "",
        error_message: str = "",
    ) -> AIAnalysis:
        """Parse and normalize LLM output."""

        data = self._parse_json(raw)

        if not data:
            logger.warning(
                "Could not parse Ollama response; using fallback"
            )

            return self._fallback_analysis(
                fallback_file=fallback_file,
                fallback_line=fallback_line,
                source_code=source_code,
                error_type=error_type,
                error_message=error_message,
            )

        confidence = self._normalize_confidence(
            data.get("confidence", 75)
        )

        affected_file = str(
            data.get(
                "affected_file"
            )
            or fallback_file
        )

        affected_line = self._safe_int(
            data.get(
                "affected_line",
                fallback_line,
            ),
            fallback_line,
        )

        patch = str(
            data.get(
                "patch",
                "",
            )
            or ""
        )

        patch = self._normalize_patch(
            patch=patch,
            target_file=fallback_file,
            source_code=source_code,
            error_type=error_type,
            error_message=error_message,
            line_number=fallback_line,
        )

        test_case = str(
            data.get(
                "test_case",
                "",
            )
            or ""
        ).strip()

        if not test_case:
            test_case = self._build_fallback_test(
                target_file=fallback_file,
                source_code=source_code,
                line_number=fallback_line,
            )

        try:
            return AIAnalysis(
                summary=str(
                    data.get(
                        "summary",
                        "",
                    )
                ),
                root_cause=str(
                    data.get(
                        "root_cause",
                        "",
                    )
                ),
                severity=str(
                    data.get(
                        "severity",
                        "MEDIUM",
                    )
                ).upper(),
                confidence=confidence,
                explanation=str(
                    data.get(
                        "explanation",
                        "",
                    )
                ),
                affected_file=affected_file,
                affected_line=affected_line,
                fix_strategy=str(
                    data.get(
                        "fix_strategy",
                        "",
                    )
                ),
                patch=patch,
                test_case=test_case,
                potential_risks=self._string_list(
                    data.get(
                        "potential_risks",
                        [],
                    )
                ),
                related_files=self._string_list(
                    data.get(
                        "related_files",
                        [],
                    )
                ),
            )

        except Exception as exc:
            logger.exception(
                "Failed constructing AIAnalysis: %s",
                exc,
            )

            return self._fallback_analysis(
                fallback_file=fallback_file,
                fallback_line=fallback_line,
                source_code=source_code,
                error_type=error_type,
                error_message=error_message,
            )

    def _normalize_patch(
        self,
        patch: str,
        target_file: str,
        source_code: str,
        error_type: str,
        error_message: str,
        line_number: int,
    ) -> str:
        """Normalize model patch and replace it with a safe fallback when malformed."""

        if not patch.strip():
            return self._build_fallback_patch(
                target_file=target_file,
                source_code=source_code,
                error_type=error_type,
                error_message=error_message,
                line_number=line_number,
            )

        patch = patch.strip()

        # Remove accidental code fences.
        patch = re.sub(
            r"^```(?:diff|patch)?\s*",
            "",
            patch,
            flags=re.IGNORECASE,
        )

        patch = re.sub(
            r"\s*```$",
            "",
            patch,
            flags=re.IGNORECASE,
        ).strip()

        normalized_file = Path(
            target_file.replace("\\", "/")
        ).as_posix()

        lines = patch.splitlines()

        # Find a real unified diff.
        old_header_index = next(
            (
                i
                for i, line in enumerate(lines)
                if line.startswith("--- ")
            ),
            None,
        )

        new_header_index = next(
            (
                i
                for i, line in enumerate(lines)
                if line.startswith("+++ ")
            ),
            None,
        )

        hunk_index = next(
            (
                i
                for i, line in enumerate(lines)
                if line.startswith("@@ ")
            ),
            None,
        )

        valid_structure = (
            old_header_index is not None
            and new_header_index is not None
            and hunk_index is not None
            and old_header_index
            < new_header_index
            < hunk_index
        )

        if not valid_structure:
            logger.warning(
                "LLM returned malformed unified diff; using fallback"
            )

            return self._build_fallback_patch(
                target_file=target_file,
                source_code=source_code,
                error_type=error_type,
                error_message=error_message,
                line_number=line_number,
            )

        # Force headers to target the actual file.
        lines[old_header_index] = (
            f"--- a/{normalized_file}"
        )

        lines[new_header_index] = (
            f"+++ b/{normalized_file}"
        )

        # Make sure every hunk contains at least one
        # valid change/context line.
        has_change = any(
            (
                line.startswith("+")
                and not line.startswith("+++")
            )
            or (
                line.startswith("-")
                and not line.startswith("---")
            )
            or line.startswith(" ")
            for line in lines[hunk_index + 1:]
        )

        if not has_change:
            logger.warning(
                "LLM unified diff has no actual hunk content; using fallback"
            )

            return self._build_fallback_patch(
                target_file=target_file,
                source_code=source_code,
                error_type=error_type,
                error_message=error_message,
                line_number=line_number,
            )

        return "\n".join(
            lines
        ).strip() + "\n"

    def _build_fallback_patch(
        self,
        target_file: str,
        source_code: str,
        error_type: str,
        error_message: str,
        line_number: int,
    ) -> str:
        """Create a valid patch for the known demo pattern."""

        if not source_code:
            return ""

        is_zero_division = (
            "ZeroDivisionError"
            in str(error_type)
            or
            "division by zero"
            in str(error_message).lower()
        )

        if not is_zero_division:
            return ""

        lines = source_code.splitlines()

        # Search around the traceback line first.
        start = max(
            0,
            line_number - 4,
        )

        end = min(
            len(lines),
            line_number + 4,
        )

        candidate_indexes = list(
            range(start, end)
        )

        candidate_indexes.extend(
            range(len(lines))
        )

        for index in candidate_indexes:

            if index < 0 or index >= len(lines):
                continue

            current = lines[index]

            if (
                "/ 0" not in current
                and " / " not in current
            ):
                continue

            # Convert:
            # risk_score = 100 / trust_level
            #
            # into:
            # risk_score = 100 / trust_level if trust_level else 0

            if " / " not in current:
                continue

            indent = (
                current[
                    :len(current)
                    - len(current.lstrip())
                ]
            )

            left, right = current.split(
                " / ",
                1,
            )

            denominator = right.strip()

            if (
                not re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*",
                    denominator,
                )
            ):
                continue

            new_line = (
                f"{left.strip()} / "
                f"{denominator} "
                f"if {denominator} else 0"
            )

            new_line = (
                indent
                + new_line
            )

            # Determine a useful small context window.
            context_before = (
                lines[index - 1]
                if index > 0
                else None
            )

            context_after = (
                lines[index + 1]
                if index + 1 < len(lines)
                else None
            )

            old_count = 1
            context_lines = []

            if context_before is not None:
                context_lines.append(
                    context_before
                )
                old_count += 1

            context_lines.append(
                current
            )

            if context_after is not None:
                context_lines.append(
                    context_after
                )
                old_count += 1

            context_start = (
                index
                if context_before is None
                else index - 1
            )

            new_context = []

            for line_index, context_line in enumerate(
                context_lines
            ):
                absolute_index = (
                    context_start
                    + line_index
                )

                if absolute_index == index:
                    new_context.append(
                        f"+{new_line}"
                    )
                else:
                    new_context.append(
                        f" {context_line}"
                    )

            old_context = []

            for line_index, context_line in enumerate(
                context_lines
            ):
                absolute_index = (
                    context_start
                    + line_index
                )

                if absolute_index == index:
                    old_context.append(
                        f"-{context_line}"
                    )
                else:
                    old_context.append(
                        f" {context_line}"
                    )

            hunk_start = context_start + 1

            return (
                f"--- a/{Path(target_file).as_posix()}\n"
                f"+++ b/{Path(target_file).as_posix()}\n"
                f"@@ -{hunk_start},{old_count} "
                f"+{hunk_start},{old_count} @@\n"
                + "\n".join(
                    old_context
                )
                + "\n"
                + "\n".join(
                    new_context
                )
                + "\n"
            )

        return ""

    def _build_fallback_test(
        self,
        target_file: str,
        source_code: str,
        line_number: int,
    ) -> str:
        """Build a generic import regression test."""

        path = Path(
            target_file.replace("\\", "/")
        )

        module_name = path.stem

        function_name = (
            self._guess_function_name(
                source_code,
                line_number,
            )
        )

        if function_name:
            return (
                "import pytest\n"
                f"from {module_name} import "
                f"{function_name}\n\n"
                f"def test_{function_name}_exists():\n"
                f"    assert callable({function_name})\n"
            )

        return (
            "import importlib\n\n"
            f"def test_{module_name}_imports():\n"
            f"    importlib.import_module({module_name!r})\n"
        )

    def _guess_function_name(
        self,
        source_code: str,
        line_number: int,
    ) -> str:
        """Find nearest enclosing function."""

        lines = source_code.splitlines()

        if not lines:
            return ""

        start = min(
            max(
                0,
                line_number - 1,
            ),
            len(lines) - 1,
        )

        for index in range(
            start,
            -1,
            -1,
        ):
            match = re.match(
                r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                lines[index],
            )

            if match:
                return match.group(1)

        return ""

    def _fallback_analysis(
        self,
        fallback_file: str,
        fallback_line: int,
        source_code: str,
        error_type: str,
        error_message: str,
    ) -> AIAnalysis:
        """Return a safe fallback."""

        patch = self._build_fallback_patch(
            target_file=fallback_file,
            source_code=source_code,
            error_type=error_type,
            error_message=error_message,
            line_number=fallback_line,
        )

        return AIAnalysis(
            summary=(
                f"Potential {error_type} at "
                f"{Path(fallback_file).name}:"
                f"{fallback_line}"
            ),
            root_cause=(
                error_message
                or "An exception occurred."
            ),
            severity="HIGH",
            confidence=60,
            explanation=(
                "TraceBack could not parse the model response. "
                "A source-aware fallback was attempted."
            ),
            affected_file=fallback_file,
            affected_line=fallback_line,
            fix_strategy=(
                "Use a minimal source-aware correction."
            ),
            patch=patch,
            test_case=self._build_fallback_test(
                fallback_file,
                source_code,
                fallback_line,
            ),
            potential_risks=[],
            related_files=[],
        )

    @staticmethod
    def _parse_json(
        raw: str,
    ) -> dict | None:
        """Extract JSON from model output."""

        if not raw:
            return None

        raw = raw.strip()

        try:
            parsed = json.loads(
                raw
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            pass

        match = re.search(
            r"\{.*\}",
            raw,
            re.DOTALL,
        )

        if not match:
            return None

        try:
            parsed = json.loads(
                match.group(0)
            )

            if isinstance(
                parsed,
                dict,
            ):
                return parsed

        except json.JSONDecodeError:
            return None

        return None

    @staticmethod
    def _normalize_confidence(
        value,
    ) -> float:
        try:
            number = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return 75.0

        if 0 < number <= 1:
            number *= 100

        return max(
            0.0,
            min(
                100.0,
                number,
            ),
        )

    @staticmethod
    def _safe_int(
        value,
        fallback: int,
    ) -> int:
        try:
            return int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return fallback

    @staticmethod
    def _string_list(
        value,
    ) -> list[str]:
        if not isinstance(
            value,
            list,
        ):
            return []

        return [
            str(item)
            for item in value
        ]


ollama_service = OllamaService()