"""Real Python traceback parser.

Extracts structured information from raw traceback text.
Supports all common Python exception types.
"""

from __future__ import annotations

import re
from backend.models.crash import ParsedTraceback, TracebackFrame

# ── Regex patterns ─────────────────────────────────────────────────────
# Matches:  File "foo.py", line 3, in bar
_FRAME_RE = re.compile(
    r'^\s*File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+)'
    r'(?:,\s+in\s+(?P<func>\S+))?',
    re.MULTILINE,
)

# Matches the final exception line:  ExceptionType: message
_EXCEPTION_RE = re.compile(
    r"^(?P<type>[A-Za-z_][\w.]*)(?::\s*(?P<msg>.*))?$",
    re.MULTILINE,
)

# Common Python built-in exception types for validation
KNOWN_EXCEPTIONS = {
    "TypeError",
    "ValueError",
    "KeyError",
    "IndexError",
    "AttributeError",
    "NameError",
    "ImportError",
    "ModuleNotFoundError",
    "ZeroDivisionError",
    "FileNotFoundError",
    "PermissionError",
    "RuntimeError",
    "AssertionError",
    "SyntaxError",
    "StopIteration",
    "OSError",
    "IOError",
    "RecursionError",
    "OverflowError",
    "UnicodeError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "NotImplementedError",
    "ConnectionError",
    "TimeoutError",
    "Exception",
}


def parse_traceback(raw: str) -> ParsedTraceback:
    """Parse a raw Python traceback string into structured data.

    Handles the standard CPython traceback format::

        Traceback (most recent call last):
          File "foo.py", line 3, in bar
            some_code()
        ZeroDivisionError: division by zero
    """
    if not raw or not raw.strip():
        return ParsedTraceback(error_type="Unknown", message="Empty traceback", raw=raw)

    frames = _extract_frames(raw)
    error_type, message = _extract_exception(raw)

    # The innermost (last) frame is where the error actually occurred
    file = ""
    line = 0
    function = ""
    if frames:
        innermost = frames[-1]
        file = innermost.file
        line = innermost.line
        function = innermost.function

    return ParsedTraceback(
        error_type=error_type,
        message=message,
        file=file,
        line=line,
        function=function,
        frames=frames,
        raw=raw,
    )


def _extract_frames(raw: str) -> list[TracebackFrame]:
    """Extract all stack frames from traceback text."""
    frames: list[TracebackFrame] = []
    lines = raw.splitlines()

    i = 0
    while i < len(lines):
        m = _FRAME_RE.match(lines[i])
        if m:
            code = ""
            # The next non-blank, non-File line is usually the source code
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith("File "):
                    code = next_line
            frames.append(
                TracebackFrame(
                    file=m.group("file"),
                    line=int(m.group("line")),
                    function=m.group("func") or "<module>",
                    code=code,
                )
            )
        i += 1

    return frames


def _extract_exception(raw: str) -> tuple[str, str]:
    """Extract the exception type and message from the last line(s)."""
    lines = raw.strip().splitlines()

    # Walk backwards to find the exception line
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that look like source code or "File ..." frames
        if stripped.startswith("File ") or stripped.startswith("Traceback"):
            continue
        # Skip lines that are clearly just indented source code
        if line.startswith("    ") and "Error" not in stripped and "Exception" not in stripped:
            continue

        m = _EXCEPTION_RE.match(stripped)
        if m:
            etype = m.group("type")
            msg = m.group("msg") or ""
            # Validate it looks like a real exception name
            if etype[0].isupper() and (etype in KNOWN_EXCEPTIONS or "Error" in etype or "Exception" in etype):
                return etype, msg.strip()

    return "UnknownError", "Could not parse exception from traceback"


def is_traceback(text: str) -> bool:
    """Check whether text contains a Python traceback."""
    return "Traceback (most recent call last)" in text or bool(_FRAME_RE.search(text))
