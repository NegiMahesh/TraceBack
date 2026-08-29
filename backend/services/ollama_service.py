"""Ollama / LLM service — sends structured prompts, parses JSON, validates output."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TEMPERATURE, OLLAMA_TIMEOUT
from backend.models.analysis import AIAnalysis

logger = logging.getLogger("traceback.ollama")


class OllamaService:
    """Configurable LLM client for local Ollama."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        temperature: float = OLLAMA_TEMPERATURE,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    # ── Health ─────────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check Ollama connectivity and model availability."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                if r.status_code != 200:
                    return {"status": "error", "message": f"HTTP {r.status_code}"}

                data = r.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_available = any(self.model in m for m in models)

                return {
                    "status": "connected",
                    "models": models,
                    "current_model": self.model,
                    "model_available": model_available,
                }
        except httpx.ConnectError:
            return {"status": "offline", "message": "Cannot connect to Ollama"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Analysis ───────────────────────────────────────────────────────

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
        """Send a structured crash analysis prompt and parse the response."""

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
        return self._parse_analysis(raw_response, file_path, line_number)

    # ── Internal ───────────────────────────────────────────────────────

    async def _generate(self, prompt: str) -> str:
        """Call Ollama generate endpoint."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": 4096,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
                return data.get("response", "")
        except httpx.TimeoutException:
            logger.error("Ollama request timed out after %ss", self.timeout)
            raise
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            raise
        except Exception:
            logger.exception("Ollama request failed")
            raise

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
        """Build a carefully engineered prompt for crash analysis."""
        prompt = f"""You are TraceBack, an expert Python debugging AI. Analyze this crash and produce a structured JSON response.

RULES:
- Do NOT hallucinate files or code that was not provided.
- Do NOT invent Git information.
- Use ONLY the supplied source code.
- Explain any uncertainty.
- Produce valid JSON only.
- Generate a minimal, targeted patch as a unified diff.
- Preserve all unrelated code.
- Generate a pytest regression test.
- Do NOT suggest destructive operations.
- The patch MUST match the provided source exactly.

ERROR:
Type: {error_type}
Message: {error_message}
File: {file_path}
Line: {line_number}
Function: {function_name}

TRACEBACK:
{traceback_raw}

SOURCE CODE ({file_path}):
{source_code}
"""
        if git_blame:
            prompt += f"""
GIT BLAME (line {line_number}):
{git_blame}
"""
        if related_code:
            prompt += f"""
RELATED CODE:
{related_code}
"""

        prompt += """
Respond with ONLY a JSON object (no markdown, no explanation outside JSON):
{
  "summary": "One-line summary of the problem",
  "root_cause": "Detailed root cause explanation",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": <number 0-100>,
  "explanation": "Clear explanation a developer can understand",
  "affected_file": "<file path>",
  "affected_line": <line number>,
  "fix_strategy": "What the fix does and why",
  "patch": "<unified diff that fixes the issue>",
  "test_case": "<complete pytest test function>",
  "potential_risks": ["risk1", "risk2"],
  "related_files": ["file1.py"]
}"""
        return prompt

    def _parse_analysis(
        self, raw: str, fallback_file: str, fallback_line: int
    ) -> AIAnalysis:
        """Parse and validate the AI response, recovering from malformed JSON."""
        # Try to extract JSON from the response
        json_str = self._extract_json(raw)

        if json_str:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    # Validate via Pydantic
                    analysis = AIAnalysis(**data)
                    # Ensure affected_file/line have fallbacks
                    if not analysis.affected_file:
                        analysis.affected_file = fallback_file
                    if not analysis.affected_line:
                        analysis.affected_line = fallback_line
                    return analysis
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to parse AI JSON: %s", e)

        # Fallback: construct best-effort analysis from raw text
        logger.warning("Using fallback analysis from raw AI response")
        return AIAnalysis(
            summary=f"AI analysis of {fallback_file}:{fallback_line}",
            root_cause=raw[:500] if raw else "AI did not return structured output",
            severity="MEDIUM",
            confidence=30.0,
            explanation=raw[:1000] if raw else "",
            affected_file=fallback_file,
            affected_line=fallback_line,
            fix_strategy="Manual review recommended",
            patch="",
            test_case="",
            potential_risks=["AI output was not in expected JSON format"],
            related_files=[],
        )

    def _extract_json(self, text: str) -> str | None:
        """Extract a JSON object from text that may contain markdown or extra content."""
        if not text:
            return None

        # Try the whole text first
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return text

        # Try to find JSON within markdown code blocks
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # Try to find a JSON object anywhere
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return brace_match.group(0)

        return None


# Module-level singleton
ollama_service = OllamaService()
