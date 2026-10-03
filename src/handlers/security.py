import os
import stat
from pathlib import Path

class ArchiveSecurityError(Exception):
    pass

def validate_member_name(name: str) -> str:
    if not name or "\x00" in name:
        raise ArchiveSecurityError("Archive contains an invalid filename.")
    return name.replace("\\", "/")

def safe_member_path(root: Path, name: str) -> Path:
    target = (root / validate_member_name(name)).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ArchiveSecurityError(f"Unsafe archive path: {name}") from exc
    return target

def is_special_mode(mode: int) -> bool:
    return any((stat.S_ISCHR(mode), stat.S_ISBLK(mode), stat.S_ISFIFO(mode), stat.S_ISSOCK(mode)))

def is_symlink_mode(mode: int) -> bool:
    return stat.S_ISLNK(mode)

def validate_output_tree(root: Path) -> None:
    base = root.resolve()
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in (*dirs, *files):
            path = Path(current) / name
            if path.is_symlink():
                raise ArchiveSecurityError(f"Symbolic links are not allowed: {name}")
            try:
                path.resolve().relative_to(base)
            except ValueError as exc:
                raise ArchiveSecurityError("Extraction escaped the destination.") from exc
