import os
import stat
from pathlib import Path

class ArchiveSecurityError(Exception):
    pass

def validate_member_name(name: str) -> str:
    if not name or "\x00" in name:
        raise ArchiveSecurityError("Archive contains an invalid filename.")
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise ArchiveSecurityError(f"Unsafe absolute archive path: {name}")
    drive, _ = os.path.splitdrive(normalized)
    if drive or (
        len(normalized) >= 2
        and normalized[0].isalpha()
        and normalized[1] == ":"
    ):
        raise ArchiveSecurityError(f"Unsafe drive archive path: {name}")
    return normalized

def safe_member_path(root: Path, name: str) -> Path:
    normalized = validate_member_name(name)
    base = root.resolve()
    target = (base / normalized).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ArchiveSecurityError(f"Unsafe archive path: {name}") from exc
    return target

def is_special_mode(mode: int) -> bool:
    return any(
        (
            stat.S_ISCHR(mode),
            stat.S_ISBLK(mode),
            stat.S_ISFIFO(mode),
            stat.S_ISSOCK(mode),
        )
    )

def is_symlink_mode(mode: int) -> bool:
    return stat.S_ISLNK(mode)

def validate_output_tree(root: Path) -> None:
    base = root.resolve()
    if not base.is_dir():
        raise ArchiveSecurityError("Extraction destination is invalid.")
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        try:
            current_path.resolve().relative_to(base)
        except ValueError as exc:
            raise ArchiveSecurityError("Extraction escaped the destination.") from exc
        for name in (*dirs, *files):
            path = current_path / name
            if path.is_symlink():
                raise ArchiveSecurityError(f"Symbolic links are not allowed: {name}")
            try:
                path.resolve().relative_to(base)
            except ValueError as exc:
                raise ArchiveSecurityError("Extraction escaped the destination.") from exc
