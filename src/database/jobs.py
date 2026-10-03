from typing import Any
from .mongo import Database

class JobRepository:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, job_id: str, user_id: int, chat_id: int, message_id: int, filename: str) -> None:
        await self.db.create_job(job_id, user_id, chat_id, message_id, filename)

    async def update(self, job_id: str, values: dict[str, Any]) -> None:
        await self.db.update_job(job_id, values)
