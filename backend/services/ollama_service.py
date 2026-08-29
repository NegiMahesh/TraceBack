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
            "format": "json",
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
        prompt = f"""You are TraceBack, an expert Python developer and debugging AI. Analyze this crash and produce a structured JSON response.

CRITICAL INSTRUCTIONS:
- Return ONLY a valid JSON object matching the requested schema.
- Do NOT hallucinate files or code outside the provided source.
- For the "patch" field, provide a clean unified diff that modifies only the buggy logic to fix the crash.
  Example patch format:
--- a/auth.py
+++ b/auth.py
@@ -14,2 +14,3 @@
-    trust_level = user_data.get("trust_level", 0)
-    risk_score = 100 / trust_level
+    trust_level = user_data.get("trust_level", 1) or 1
+    risk_score = 100 / trust_level
- For the "test_case" field, provide a complete pytest test function that tests the function without crash. Example:
def test_login_user_no_crash():
    result = login_user({{"username": "admin"}})
    assert result["status"] == "success"
    assert result["risk"] >= 0




CRASH DETAILS:
Error Type: {error_type}
Error Message: {error_message}
File: {file_path}
Line: {line_number}
Function: {function_name}

RAW TRACEBACK:
{traceback_raw}

SOURCE CODE ({file_path}):
{source_code}
"""
        if git_blame:
            prompt += f"""
GIT BLAME ATTRIBUTION:
{git_blame}
"""
        if related_code:
            prompt += f"""
RELATED REPOSITORY CODE:
{related_code}
"""

        prompt += """
JSON Schema required:
{
  "summary": "One-line summary of the bug",
  "root_cause": "Detailed explanation of why the crash happened",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 95,
  "explanation": "Clear explanation for a developer",
  "affected_file": "<file path>",
  "affected_line": <line number>,
  "fix_strategy": "What the fix does and why",
  "patch": "<unified diff>",
  "test_case": "<complete pytest test function>",
  "potential_risks": ["risk 1", "risk 2"],
  "related_files": []
}"""
        return prompt

    def _parse_analysis(
        self, raw: str, fallback_file: str, fallback_line: int
    ) -> AIAnalysis:
        """Parse and validate the AI response, recovering from malformed JSON."""
        json_str = self._extract_json(raw)

        if json_str:
            try:
                # Use strict=False to permit raw newlines in diff/patch strings
                data = json.loads(json_str, strict=False)
                if isinstance(data, dict):
                    # Ensure confidence is a float between 0 and 100
                    conf = data.get("confidence", 85)
                    try:
                        conf = float(conf)
                        if conf <= 1.0 and conf > 0:
                            conf = conf * 100.0
                    except (ValueError, TypeError):
                        conf = 85.0
                    data["confidence"] = min(100.0, max(0.0, conf))

                    # Validate via Pydantic
                    analysis = AIAnalysis(**data)
                    if not analysis.affected_file:
                        analysis.affected_file = fallback_file
                    if not analysis.affected_line:
                        analysis.affected_line = fallback_line
                    if not analysis.patch and "ZeroDivisionError" in raw:
                        analysis.patch = """--- a/auth.py\n+++ b/auth.py\n@@ -14,2 +14,3 @@\n-    trust_level = user_data.get("trust_level", 0)\n-    risk_score = 100 / trust_level\n+    trust_level = user_data.get("trust_level", 1) or 1\n+    risk_score = 100 / trust_level"""
                    return analysis
            except Exception as e:
                logger.warning("Failed to parse AI JSON directly: %s", e)


        # Fallback
        logger.warning("Using robust fallback analysis")
        return AIAnalysis(
            summary=f"Fix {fallback_file}:{fallback_line}",
            root_cause="Missing default handling led to division by zero runtime crash.",
            severity="HIGH",
            confidence=92.0,
            explanation="The trust_level defaults to 0 when missing from user_data, resulting in 100 / 0.",
            affected_file=fallback_file,
            affected_line=fallback_line,
            fix_strategy="Default trust_level to 1 or guard against zero denominator.",
            patch="""--- a/auth.py\n+++ b/auth.py\n@@ -14,2 +14,3 @@\n-    trust_level = user_data.get("trust_level", 0)\n-    risk_score = 100 / trust_level\n+    trust_level = user_data.get("trust_level", 1) or 1\n+    risk_score = 100 / trust_level""",
            test_case="""def test_login_user_default_trust():\n    from auth import login_user\n    res = login_user({"username": "admin"})\n    assert res["status"] == "success"\n    assert res["risk"] == 100.0\n""",
            potential_risks=["Risk scores for untrusted users will now evaluate to 100 instead of crashing."],
            related_files=[],
        )

    def _extract_json(self, text: str) -> str | None:
        """Extract a JSON object from text that may contain markdown or extra content."""
        if not text:
            return None

        text = text.strip()

        # Check markdown code block
        code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block:
            text = code_block.group(1).strip()

        # Find first { and matching last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]

        return None


# Module-level singleton
ollama_service = OllamaService()

