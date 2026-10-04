import os

os.environ.setdefault("API_ID", "1")
os.environ.setdefault("API_HASH", "test")
os.environ.setdefault("BOT_TOKEN", "test:test")
os.environ.setdefault("OWNER_ID", "1")

from pathlib import Path

import pytest

from src.handlers.security import ArchiveSecurityError, safe_member_path, validate_member_name


def test_safe_member_path_accepts_normal_file():
    root = Path("/tmp/archive-test")
    result = safe_member_path(root, "folder/file.txt")
    assert result == root / "folder" / "file.txt"


@pytest.mark.parametrize(
    "name",
    ["../escape.txt", "/etc/passwd", "folder/../../escape", "", "C:/Windows/system32"],
)
def test_safe_member_path_rejects_traversal(name):
    with pytest.raises(ArchiveSecurityError):
        safe_member_path(Path("/tmp/archive-test"), name)


def test_validate_member_name_rejects_windows_drive():
    with pytest.raises(ArchiveSecurityError):
        validate_member_name("D:/secret/file.txt")
