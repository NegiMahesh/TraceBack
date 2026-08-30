import pytest
import sys
import os

_repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

try:
    from auth import *
except ImportError:
    pass


def test_calculate_average_empty_list():
    assert calculate_average([]) == 0