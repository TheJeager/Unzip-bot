import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .config import SETTINGS

@dataclass(slots=True)
class Job:
    job_id: str
    user_id: int
    chat_id: int
    message_id: int
    filename: str
    created_at: datetime
    future: asyncio.Future | None = None
    cancelled: bool = False

class JobQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self.global_limit = asyncio.Semaphore(SETTINGS.max_concurrent_jobs)
        self.user_limits: dict[int, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(SETTINGS.max_jobs_per_user))
        self.active: dict[str, Job] = {}
        self.waiting: deque[Job] = deque()
        self.workers: list[asyncio.Task] = []
        self.handler = None

    def configure(self, handler) -> None:
        self.handler = handler

    async def start(self) -> None:
        if self.workers:
            return
        self.workers = [asyncio.create_task(self._worker()) for _ in range(SETTINGS.max_concurrent_jobs)]

    async def stop(self) -> None:
        for task in self.workers:
            task.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def submit(self, user_id: int, chat_id: int, message_id: int, filename: str) -> Job:
        job = Job(uuid4().hex[:12], user_id, chat_id, message_id, filename, datetime.now(timezone.utc))
        job.future = asyncio.get_running_loop().create_future()
        self.waiting.append(job)
        await self.queue.put(job)
        return job

    def active_for_user(self, user_id: int) -> int:
        return sum(job.user_id == user_id for job in self.active.values())

    def queued_for_user(self, user_id: int) -> int:
        return sum(job.user_id == user_id for job in self.waiting if not job.cancelled)

    async def cancel_user(self, user_id: int) -> int:
        removed = 0
        for job in self.waiting:
            if job.user_id == user_id and not job.cancelled:
                job.cancelled = True
                removed += 1
                if job.future and not job.future.done():
                    job.future.set_result(False)
        self.waiting = deque(job for job in self.waiting if not job.cancelled)
        return removed

    async def _worker(self) -> None:
        while True:
            job = await self.queue.get()
            if job in self.waiting:
                self.waiting.remove(job)
            if job.cancelled:
                self.queue.task_done()
                continue
            self.active[job.job_id] = job
            try:
                async with self.global_limit, self.user_limits[job.user_id]:
                    if job.cancelled:
                        result = False
                    else:
                        result = await self.handler(job) if self.handler else False
                    if job.future and not job.future.done():
                        job.future.set_result(result)
            except asyncio.CancelledError:
                if job.future and not job.future.done():
                    job.future.set_result(False)
                raise
            except Exception as exc:
                if job.future and not job.future.done():
                    job.future.set_exception(exc)
            finally:
                self.active.pop(job.job_id, None)
                self.queue.task_done()

    def status(self) -> dict[str, int]:
        return {"queued": len(self.waiting), "active": len(self.active), "workers": len(self.workers)}
