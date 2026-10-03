import os
import stat
from pathlib import Path

class ArchiveSecurityError(Exception):
    pass

def safe_member_path(root: Path, name: str) -> Path:
    if not name or chr(0) in name:
        raise ArchiveSecurityError("Archive contains an invalid filename.")
    normalized = name.replace("\\", "/")
    target = (root / normalized).resolve()
    base = root.resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ArchiveSecurityError(f"Unsafe archive path: {name}") from exc
    return target

def is_symlink_mode(mode: int) -> bool:
    return stat.S_ISLNK(mode)

def is_special_mode(mode: int) -> bool:
    return stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)

def validate_output_tree(root: Path) -> None:
    base = root.resolve()
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current).resolve()
        try:
            current_path.relative_to(base)
        except ValueError as exc:
            raise ArchiveSecurityError("Extraction escaped the destination.") from exc
        for name in dirs + files:
            path = Path(current) / name
            if path.is_symlink():
                raise ArchiveSecurityError(f"Archive created a symbolic link: {name}")
            resolved = path.resolve()
            try:
                resolved.relative_to(base)
            except ValueError as exc:
                raise ArchiveSecurityError(f"Extraction escaped the destination: {name}") from exc
