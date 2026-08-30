"""
TraceBack Ollama Service

AI repair protocol:

    traceback + complete source
              ↓
           Ollama
              ↓
       old_code + new_code
              ↓
    TraceBack validates both
              ↓
    replace EXACT old block
              ↓
    AST / structure validation
              ↓
       TraceBack creates diff

The model never creates the unified diff and never returns a complete
replacement file.
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
import re
from pathlib import Path
from typing import Optional

import httpx

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT,
)

from backend.models.analysis import AIAnalysis


logger = logging.getLogger(
    "traceback.ollama"
)


MAX_PATCH_ATTEMPTS = 2


class OllamaService:
    """Local Ollama debugging and minimal-repair service."""

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

    # ======================================================================
    # HEALTH
    # ======================================================================

    async def health_check(self) -> dict:
        try:

            async with httpx.AsyncClient(
                timeout=5
            ) as client:

                response = await client.get(
                    f"{self.base_url}/api/tags"
                )

            response.raise_for_status()

            data = response.json()

            models = [
                str(item.get("name", ""))
                for item in data.get(
                    "models",
                    [],
                )
            ]

            return {
                "status": "connected",
                "models": models,
                "current_model": self.model,
                "model_available": any(
                    name == self.model
                    or self.model in name
                    for name in models
                ),
            }

        except httpx.ConnectError:

            return {
                "status": "offline",
                "message": "Cannot connect to Ollama.",
            }

        except Exception as exc:

            logger.exception(
                "Ollama health check failed"
            )

            return {
                "status": "error",
                "message": str(exc),
            }

    # ======================================================================
    # MAIN CRASH ANALYSIS
    # ======================================================================

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

        rejection_reason = ""

        for attempt in range(
            1,
            MAX_PATCH_ATTEMPTS + 1,
        ):

            logger.info(
                "AI repair attempt %s/%s",
                attempt,
                MAX_PATCH_ATTEMPTS,
            )

            prompt = self._build_prompt(
                error_type=error_type,
                error_message=error_message,
                source_code=source_code,
                file_path=file_path,
                line_number=line_number,
                function_name=function_name,
                git_blame=git_blame,
                related_code=related_code,
                traceback_raw=traceback_raw,
                rejection_reason=rejection_reason,
                attempt=attempt,
            )

            try:

                raw = await self._generate(
                    prompt
                )

            except Exception as exc:

                logger.exception(
                    "Ollama generation failed"
                )

                return self._empty_analysis(
                    file_path=file_path,
                    line_number=line_number,
                    error_type=error_type,
                    error_message=(
                        f"Ollama generation failed: {exc}"
                    ),
                )

            result, rejection = (
                self._parse_and_validate(
                    raw_response=raw,
                    source_code=source_code,
                    file_path=file_path,
                    line_number=line_number,
                    error_type=error_type,
                    error_message=error_message,
                )
            )

            if result is not None:
                return result

            rejection_reason = (
                rejection
                or
                "Repair proposal was rejected."
            )

            logger.warning(
                "AI repair attempt %s rejected: %s",
                attempt,
                rejection_reason,
            )

        return self._empty_analysis(
            file_path=file_path,
            line_number=line_number,
            error_type=error_type,
            error_message=error_message,
            rejection_reason=rejection_reason,
        )

    # ======================================================================
    # OLLAMA REQUEST
    # ======================================================================

    async def _generate(
        self,
        prompt: str,
    ) -> str:

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

            return str(
                data.get(
                    "response",
                    "",
                )
            )

    # ======================================================================
    # PROMPT
    # ======================================================================

    def _build_prompt(
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
        rejection_reason: str = "",
        attempt: int = 1,
    ) -> str:

        path = Path(
            file_path.replace(
                "\\",
                "/",
            )
        ).as_posix()

        retry = ""

        if rejection_reason:

            retry = f"""
======================================================================
PREVIOUS REPAIR REJECTED
======================================================================

TraceBack rejected your previous proposal.

Reason:
{rejection_reason}

Generate a DIFFERENT and safer repair.
Do not repeat the rejected proposal.
"""

        return f"""
You are TraceBack, an autonomous Python repair engine.

Repair attempt: {attempt}

Your task is to fix the reported error with the SMALLEST possible
change.

YOU ARE NOT ALLOWED TO RETURN A COMPLETE FILE.

YOU ARE NOT ALLOWED TO RETURN A UNIFIED DIFF.

YOU MUST RETURN TWO EXACT SOURCE BLOCKS:

    old_code
    new_code

TraceBack itself performs the replacement and creates the final diff.

======================================================================
ERROR
======================================================================

Type:
{error_type}

Message:
{error_message}

======================================================================
FILE
======================================================================

{path}

Line:
{line_number}

Function:
{function_name}

======================================================================
TRACEBACK
======================================================================

{traceback_raw}

======================================================================
COMPLETE CURRENT SOURCE
======================================================================

{source_code}

======================================================================
REPAIR REQUIREMENTS
======================================================================

1. Identify the actual root cause.
2. Inspect the caller/callee relationship.
3. Make the smallest possible repair.
4. old_code MUST be copied EXACTLY from the supplied source.
5. new_code MUST replace only that old_code block.
6. old_code must occur exactly once in the source.
7. Do not delete unrelated functions.
8. Do not delete unrelated classes.
9. Do not delete imports.
10. Do not delete the __main__ block.
11. Do not rewrite the whole file.
12. Do not return a complete file in either field.
13. Do not return Markdown.
14. Do not use code fences.
15. new_code must be valid Python when inserted.
16. Preserve indentation.
17. Preserve surrounding code.
18. Fix the actual reported error rather than merely moving it.

Example:

SOURCE:

def generate_token(user_id):
    user = get_user(user_id)
    permissions = user.get("permissions", [])

    return permissions[0]


GOOD RESPONSE:

{{
  "old_code": "    return permissions[0]",
  "new_code": "    if permissions:\\n        return permissions[0]\\n    return None"
}}

BAD RESPONSE:

{{
  "old_code": "whole file here...",
  "new_code": "completely rewritten file..."
}}

======================================================================
RETURN EXACTLY THIS JSON
======================================================================

{{
  "summary": "...",
  "root_cause": "...",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 95,
  "explanation": "...",
  "affected_file": "{path}",
  "affected_line": {line_number},
  "fix_strategy": "...",
  "old_code": "...",
  "new_code": "...",
  "test_case": "...",
  "potential_risks": [],
  "related_files": []
}}

{retry}
"""

    # ======================================================================
    # PARSE + VALIDATE
    # ======================================================================

    def _parse_and_validate(
        self,
        raw_response: str,
        source_code: str,
        file_path: str,
        line_number: int,
        error_type: str,
        error_message: str,
    ) -> tuple[
        Optional[AIAnalysis],
        str,
    ]:

        data = self._extract_json(
            raw_response
        )

        if not data:

            return (
                None,
                "Ollama returned invalid JSON.",
            )

        old_code = str(
            data.get(
                "old_code",
                "",
            )
            or ""
        )

        new_code = str(
            data.get(
                "new_code",
                "",
            )
            or ""
        )

        old_code = self._clean_block(
            old_code
        )

        new_code = self._clean_block(
            new_code
        )

        if not old_code:

            return (
                None,
                "AI returned an empty old_code block.",
            )

        if not new_code:

            return (
                None,
                "AI returned an empty new_code block.",
            )

        # --------------------------------------------------------------
        # old_code must exist exactly once.
        # --------------------------------------------------------------

        count = source_code.count(
            old_code
        )

        if count == 0:

            return (
                None,
                (
                    "old_code does not exactly match "
                    "the current source."
                ),
            )

        if count != 1:

            return (
                None,
                (
                    f"old_code occurs {count} times; "
                    "repair location is ambiguous."
                ),
            )

        # --------------------------------------------------------------
        # Construct candidate source.
        # --------------------------------------------------------------

        modified = source_code.replace(
            old_code,
            new_code,
            1,
        )

        if modified == source_code:

            return (
                None,
                "Repair produces no source change.",
            )

        # --------------------------------------------------------------
        # Python validation.
        # --------------------------------------------------------------

        syntax_error = (
            self._validate_python(
                modified
            )
        )

        if syntax_error:

            return (
                None,
                (
                    "Proposed repair produces invalid "
                    f"Python: {syntax_error}"
                ),
            )

        # --------------------------------------------------------------
        # Structural preservation.
        # --------------------------------------------------------------

        safe, reason = (
            self._validate_structure(
                original=source_code,
                modified=modified,
            )
        )

        if not safe:

            return (
                None,
                reason,
            )

        # --------------------------------------------------------------
        # Change size.
        # --------------------------------------------------------------

        if not self._reasonable_change(
            old_code,
            new_code,
        ):

            return (
                None,
                (
                    "Repair block is too large. "
                    "TraceBack only accepts minimal changes."
                ),
            )

        # --------------------------------------------------------------
        # Create diff.
        # --------------------------------------------------------------

        normalized_file = (
            Path(
                file_path.replace(
                    "\\",
                    "/",
                )
            ).as_posix()
        )

        patch = self._create_diff(
            source_code,
            modified,
            normalized_file,
        )

        if not self._has_real_change(
            patch
        ):

            return (
                None,
                "Generated patch contains no real changes.",
            )

        return (
            AIAnalysis(
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

                confidence=self._confidence(
                    data.get(
                        "confidence",
                        80,
                    )
                ),

                explanation=str(
                    data.get(
                        "explanation",
                        "",
                    )
                ),

                affected_file=normalized_file,

                affected_line=self._safe_int(
                    data.get(
                        "affected_line",
                        line_number,
                    ),
                    line_number,
                ),

                fix_strategy=str(
                    data.get(
                        "fix_strategy",
                        "",
                    )
                ),

                patch=patch,

                test_case=str(
                    data.get(
                        "test_case",
                        "",
                    )
                    or ""
                ).strip(),

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
            ),
            "",
        )

    # ======================================================================
    # STRUCTURE VALIDATION
    # ======================================================================

    def _validate_structure(
        self,
        original: str,
        modified: str,
    ) -> tuple[bool, str]:

        try:

            old_tree = ast.parse(
                original
            )

            new_tree = ast.parse(
                modified
            )

        except SyntaxError as exc:

            return (
                False,
                f"Syntax error: {exc}",
            )

        old_structure = (
            self._structure(
                old_tree
            )
        )

        new_structure = (
            self._structure(
                new_tree
            )
        )

        removed_functions = (
            old_structure["functions"]
            -
            new_structure["functions"]
        )

        if removed_functions:

            return (
                False,
                (
                    "Repair removed function(s): "
                    +
                    ", ".join(
                        sorted(
                            removed_functions
                        )
                    )
                ),
            )

        removed_classes = (
            old_structure["classes"]
            -
            new_structure["classes"]
        )

        if removed_classes:

            return (
                False,
                (
                    "Repair removed class(es): "
                    +
                    ", ".join(
                        sorted(
                            removed_classes
                        )
                    )
                ),
            )

        removed_imports = (
            old_structure["imports"]
            -
            new_structure["imports"]
        )

        if removed_imports:

            return (
                False,
                (
                    "Repair removed import(s): "
                    +
                    ", ".join(
                        sorted(
                            removed_imports
                        )
                    )
                ),
            )

        if (
            old_structure["main_guard"]
            and
            not new_structure["main_guard"]
        ):

            return (
                False,
                "Repair removed the __main__ block.",
            )

        return (
            True,
            "",
        )

    @staticmethod
    def _structure(
        tree: ast.AST,
    ) -> dict:

        functions = set()
        classes = set()
        imports = set()
        main_guard = False

        for node in getattr(
            tree,
            "body",
            [],
        ):

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                functions.add(
                    node.name
                )

            elif isinstance(
                node,
                ast.ClassDef,
            ):

                classes.add(
                    node.name
                )

            elif isinstance(
                node,
                ast.Import,
            ):

                imports.add(
                    "import:"
                    +
                    ",".join(
                        alias.name
                        for alias
                        in node.names
                    )
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):

                imports.add(
                    "from:"
                    +
                    str(
                        node.module
                        or
                        ""
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

            elif isinstance(
                node,
                ast.If,
            ):

                if (
                    isinstance(
                        node.test,
                        ast.Compare,
                    )
                    and
                    isinstance(
                        node.test.left,
                        ast.Name,
                    )
                    and
                    node.test.left.id
                    == "__name__"
                    and
                    node.test.comparators
                    and
                    isinstance(
                        node.test.comparators[0],
                        ast.Constant,
                    )
                    and
                    node.test.comparators[0].value
                    == "__main__"
                ):

                    main_guard = True

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "main_guard": main_guard,
        }

    # ======================================================================
    # DIFF
    # ======================================================================

    @staticmethod
    def _create_diff(
        original: str,
        modified: str,
        file_path: str,
    ) -> str:

        old_lines = (
            original
            .replace(
                "\r\n",
                "\n",
            )
            .splitlines(
                keepends=True
            )
        )

        new_lines = (
            modified
            .replace(
                "\r\n",
                "\n",
            )
            .splitlines(
                keepends=True
            )
        )

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        text = "\n".join(
            line.rstrip(
                "\r\n"
            )
            for line in diff
        )

        return (
            text + "\n"
            if text
            else ""
        )

    # ======================================================================
    # HELPERS
    # ======================================================================

    @staticmethod
    def _clean_block(
        value: str,
    ) -> str:

        value = (
            value
            .replace(
                "\r\n",
                "\n",
            )
            .replace(
                "\r",
                "\n",
            )
        )

        value = re.sub(
            r"^```(?:python|py)?\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"\s*```$",
            "",
            value,
            flags=re.IGNORECASE,
        )

        return value

    @staticmethod
    def _reasonable_change(
        old_code: str,
        new_code: str,
    ) -> bool:

        old_lines = len(
            old_code.splitlines()
        )

        new_lines = len(
            new_code.splitlines()
        )

        changed = (
            old_lines
            +
            new_lines
        )

        if changed <= 12:
            return True

        return (
            changed <= 20
        )

    @staticmethod
    def _has_real_change(
        patch: str,
    ) -> bool:

        for line in patch.splitlines():

            if (
                line.startswith("+")
                and
                not line.startswith("+++")
            ):
                return True

            if (
                line.startswith("-")
                and
                not line.startswith("---")
            ):
                return True

        return False

    @staticmethod
    def _validate_python(
        source: str,
    ) -> str | None:

        if not source.strip():

            return "Source is empty."

        try:

            tree = ast.parse(
                source
            )

            if not tree.body:

                return "Python source is empty."

            return None

        except SyntaxError as exc:

            return (
                f"{exc.msg} at line {exc.lineno}"
            )

    @staticmethod
    def _extract_json(
        text: str,
    ) -> dict | None:

        if not text:
            return None

        text = text.strip()

        try:

            value = json.loads(
                text
            )

            if isinstance(
                value,
                dict,
            ):

                return value

        except json.JSONDecodeError:
            pass

        fenced = re.search(
            r"```(?:json)?\s*(.*?)\s*```",
            text,
            re.DOTALL,
        )

        if fenced:

            text = (
                fenced.group(
                    1
                )
                .strip()
            )

        start = text.find(
            "{"
        )

        end = text.rfind(
            "}"
        )

        if (
            start == -1
            or
            end == -1
            or
            end <= start
        ):

            return None

        try:

            value = json.loads(
                text[
                    start:
                    end + 1
                ]
            )

            if isinstance(
                value,
                dict,
            ):

                return value

        except json.JSONDecodeError:
            return None

        return None

    @staticmethod
    def _confidence(
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

        if (
            0 < number <= 1
        ):

            number *= 100

        return max(
            0,
            min(
                100,
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

    # ======================================================================
    # EMPTY RESULT
    # ======================================================================

    @staticmethod
    def _empty_analysis(
        file_path: str,
        line_number: int,
        error_type: str,
        error_message: str,
        rejection_reason: str = "",
    ) -> AIAnalysis:

        normalized = (
            Path(
                file_path.replace(
                    "\\",
                    "/",
                )
            ).as_posix()
        )

        reason = (
            rejection_reason
            or
            "No safe repair was generated."
        )

        return AIAnalysis(
            summary=(
                "No safe automatic patch generated."
            ),
            root_cause=(
                error_message
            ),
            severity="HIGH",
            confidence=0,
            explanation=(
                "TraceBack rejected the AI repair because "
                "it did not meet the minimal-change and "
                "source-preservation rules."
            ),
            affected_file=normalized,
            affected_line=line_number,
            fix_strategy="Manual review required.",
            patch="",
            test_case="",
            potential_risks=[
                reason
            ],
            related_files=[],
        )


ollama_service = OllamaService()