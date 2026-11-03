"""Security and path traversal defense unit tests."""
from pathlib import Path
from app.parser.zip_handler import is_safe_path

def test_is_safe_path_valid():
    base = Path("/safe/base/dir")
    safe_child = Path("/safe/base/dir/subdir/file.py")
    assert is_safe_path(base, safe_child) is True

def test_is_safe_path_zip_slip():
    base = Path("/safe/base/dir")
    evil_escape = Path("/safe/base/dir/../../etc/passwd")
    assert is_safe_path(base, evil_escape) is False
