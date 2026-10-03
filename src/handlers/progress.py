import asyncio

from .formatting import format_bytes, progress_bar


class ProgressReporter:
    def __init__(self, message, label: str, interval: float = 1.5):
        self.message = message
        self.label = label
        self.interval = max(0.5, interval)
        self.last_update = 0.0
        self.started = asyncio.get_running_loop().time()
        self.lock = asyncio.Lock()

    async def update(self, current: int, total: int) -> None:
        now = asyncio.get_running_loop().time()
        if current < total and now - self.last_update < self.interval:
            return

        async with self.lock:
            now = asyncio.get_running_loop().time()
            if current < total and now - self.last_update < self.interval:
                return
            self.last_update = now
            elapsed = max(now - self.started, 0.1)
            percent = 100.0 if total <= 0 else min(100.0, current * 100 / total)
            speed = current / elapsed
            text = (
                f"{self.label}\n\n"
                f"{progress_bar(percent)} {percent:.1f}%\n"
                f"{format_bytes(current)} / {format_bytes(total)}\n"
                f"⚡ {format_bytes(speed)}/s"
            )
            try:
                await self.message.edit_text(text)
            except Exception:
                pass
