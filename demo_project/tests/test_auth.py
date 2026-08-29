"""Tests for the demo auth module.

These tests demonstrate the bug and will verify fixes.
"""

import pytest
import sys
import os

# Add demo_project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import login_user, get_user_profile, calculate_score


class TestLoginUser:
    def test_login_with_trust_level(self):
        """Should work when trust_level is provided."""
        result = login_user({"username": "admin", "trust_level": 5})
        assert result["status"] == "success"
        assert result["risk"] == 20.0

    def test_login_valid(self):
        """Should work with standard user data."""
        result = login_user({"username": "user1", "trust_level": 10})
        assert result["status"] == "success"
        assert result["username"] == "user1"



class TestGetUserProfile:
    def test_valid_user(self):
        profile = get_user_profile(1)
        assert profile["name"] == "Alice"

    def test_invalid_user(self):
        with pytest.raises(KeyError):
            get_user_profile(999)


class TestCalculateScore:
    def test_normal_scores(self):
        assert calculate_score([10, 20, 30]) == 20.0

    def test_empty_scores(self):
        with pytest.raises(ZeroDivisionError):
            calculate_score([])
