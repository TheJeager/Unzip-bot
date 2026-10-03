def format_bytes(value: int | float) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return "0 B"

def progress_bar(percent: float, width: int = 12) -> str:
    filled = max(0, min(width, int(percent / 100 * width)))
    return "▰" * filled + "▱" * (width - filled)
