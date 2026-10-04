import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(slots=True)
class Job:
    job_id: str
    user_id: int
    chat_id: int
    message_id: int
    filename: str
    created_at: datetime
    future: asyncio.Future
    cancelled: bool = False


class JobQueue:
    def __init__(self, workers: int, per_user: int):
        self.queue = asyncio.Queue()
        self.waiting = deque()
        self.active = {}
        self.worker_count = max(1, workers)
        self.per_user = max(1, per_user)
        self.user_locks = {}
        self.workers = []
        self.handler = None
        self.stopping = False

    def configure(self, handler) -> None:
        self.handler = handler

    async def start(self) -> None:
        if self.workers:
            return
        self.stopping = False
        self.workers = [asyncio.create_task(self._worker()) for _ in range(self.worker_count)]

    async def stop(self) -> None:
        self.stopping = True
        for job in self.waiting:
            job.cancelled = True
            if not job.future.done():
                job.future.set_result(False)
        self.waiting.clear()
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        for job in list(self.active.values()):
            job.cancelled = True
            if not job.future.done():
                job.future.set_result(False)
        self.active.clear()
        self.user_locks.clear()

    async def submit(self, user_id: int, chat_id: int, message_id: int, filename: str) -> Job:
        if self.stopping:
            raise RuntimeError("Job queue is shutting down.")
        loop = asyncio.get_running_loop()
        job = Job(
            uuid4().hex[:10],
            user_id,
            chat_id,
            message_id,
            filename,
            datetime.now(timezone.utc),
            loop.create_future(),
        )
        self.waiting.append(job)
        await self.queue.put(job)
        return job

    def active_for_user(self, user_id: int) -> int:
        return sum(j.user_id == user_id for j in self.active.values())

    def queued_for_user(self, user_id: int) -> int:
        return sum(j.user_id == user_id and not j.cancelled for j in self.waiting)

    async def cancel_user(self, user_id: int) -> list[Job]:
        cancelled = []
        for job in self.waiting:
            if job.user_id == user_id and not job.cancelled:
                job.cancelled = True
                cancelled.append(job)
                if not job.future.done():
                    job.future.set_result(False)
        self.waiting = deque(j for j in self.waiting if not j.cancelled)
        return cancelled

    async def _worker(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                if job in self.waiting:
                    self.waiting.remove(job)
                if job.cancelled or self.stopping:
                    if not job.future.done():
                        job.future.set_result(False)
                    continue
                lock = self.user_locks.setdefault(job.user_id, asyncio.Semaphore(self.per_user))
                self.active[job.job_id] = job
                async with lock:
                    result = await self.handler(job) if self.handler and not job.cancelled else False
                if not job.future.done():
                    job.future.set_result(result)
            except asyncio.CancelledError:
                if not job.future.done():
                    job.future.set_result(False)
                raise
            except Exception as exc:
                if not job.future.done():
                    job.future.set_exception(exc)
            finally:
                self.active.pop(job.job_id, None)
                self.queue.task_done()

    def status(self) -> dict[str, int]:
        return {"queued": len(self.waiting), "active": len(self.active), "workers": len(self.workers)}
