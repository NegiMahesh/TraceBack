"""Tests for the traceback parser service."""

import pytest
from backend.services.traceback_parser import parse_traceback, is_traceback


SAMPLE_TB = """Traceback (most recent call last):
  File "auth.py", line 15, in <module>
    result = login_user({"username": "admin"})
  File "auth.py", line 3, in login_user
    risk_score = 100 / trust_level
ZeroDivisionError: division by zero"""

KEYERROR_TB = """Traceback (most recent call last):
  File "app.py", line 10, in main
    profile = profiles[user_id]
KeyError: 999"""

TYPEERROR_TB = """Traceback (most recent call last):
  File "utils.py", line 5, in process
    result = value + None
TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'"""

IMPORT_TB = """Traceback (most recent call last):
  File "main.py", line 1, in <module>
    import nonexistent_module
ModuleNotFoundError: No module named 'nonexistent_module'"""


class TestIsTraceback:
    def test_valid_traceback(self):
        assert is_traceback(SAMPLE_TB) is True

    def test_plain_text(self):
        assert is_traceback("Hello world") is False

    def test_empty(self):
        assert is_traceback("") is False


class TestParseTraceback:
    def test_zerodivision(self):
        result = parse_traceback(SAMPLE_TB)
        assert result.error_type == "ZeroDivisionError"
        assert result.message == "division by zero"
        assert result.file == "auth.py"
        assert result.line == 3
        assert result.function == "login_user"
        assert len(result.frames) == 2

    def test_keyerror(self):
        result = parse_traceback(KEYERROR_TB)
        assert result.error_type == "KeyError"
        assert result.file == "app.py"
        assert result.line == 10
        assert result.function == "main"

    def test_typeerror(self):
        result = parse_traceback(TYPEERROR_TB)
        assert result.error_type == "TypeError"
        assert result.file == "utils.py"
        assert result.line == 5

    def test_import_error(self):
        result = parse_traceback(IMPORT_TB)
        assert result.error_type == "ModuleNotFoundError"

    def test_empty_input(self):
        result = parse_traceback("")
        assert result.error_type == "Unknown"

    def test_frames_order(self):
        result = parse_traceback(SAMPLE_TB)
        # First frame is the outermost caller
        assert result.frames[0].file == "auth.py"
        assert result.frames[0].line == 15
        # Last frame is the innermost (error location)
        assert result.frames[-1].file == "auth.py"
        assert result.frames[-1].line == 3

    def test_frame_code(self):
        result = parse_traceback(SAMPLE_TB)
        assert "login_user" in result.frames[0].code
        assert "100 / trust_level" in result.frames[1].code
