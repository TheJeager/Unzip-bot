from pathlib import Path

import pytest

from src.security import ArchiveSecurityError, safe_member_path

def test_safe_member_path_accepts_normal_file():
    root = Path("/tmp/archive-test")
    result = safe_member_path(root, "folder/file.txt")
    assert result == root / "folder" / "file.txt"

@pytest.mark.parametrize("name", ["../escape.txt", "/etc/passwd", "folder/../../escape", ""])
def test_safe_member_path_rejects_traversal(name):
    with pytest.raises(ArchiveSecurityError):
        safe_member_path(Path("/tmp/archive-test"), name)
