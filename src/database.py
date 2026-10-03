from datetime import datetime, timezone
from typing import Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:
    AsyncIOMotorClient = None

from .config import SETTINGS

class Database:
    def __init__(self) -> None:
        self.enabled = bool(SETTINGS.mongo_uri and AsyncIOMotorClient)
        self.client = AsyncIOMotorClient(SETTINGS.mongo_uri) if self.enabled else None
        self.db = self.client.archivex if self.client else None

    @property
    def users(self):
        return self.db.users if self.db else None

    @property
    def jobs(self):
        return self.db.jobs if self.db else None

    @property
    def stats(self):
        return self.db.stats if self.db else None

    async def init(self) -> None:
        if not self.enabled:
            return
        await self.users.create_index("user_id", unique=True)
        await self.jobs.create_index("job_id", unique=True)
        await self.jobs.create_index([("user_id", 1), ("created_at", -1)])
        await self.stats.create_index("_id", unique=True)

    async def close(self) -> None:
        if self.client:
            self.client.close()

    async def user(self, user_id: int) -> dict[str, Any]:
        defaults = {"user_id": user_id, "agreed": False, "auto_delete": True}
        if not self.enabled:
            return defaults
        doc = await self.users.find_one({"user_id": user_id})
        if not doc:
            now = datetime.now(timezone.utc)
            await self.users.insert_one({**defaults, "created_at": now, "updated_at": now})
            return defaults
        return {**defaults, **doc}

    async def update_user(self, user_id: int, values: dict[str, Any]) -> None:
        if not self.enabled:
            return
        now = datetime.now(timezone.utc)
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {**values, "updated_at": now}, "$setOnInsert": {"user_id": user_id, "created_at": now}},
            upsert=True,
        )

    async def create_job(self, job_id: str, user_id: int, chat_id: int, filename: str) -> None:
        if not self.enabled:
            return
        now = datetime.now(timezone.utc)
        await self.jobs.insert_one({
            "job_id": job_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "filename": filename,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
        })

    async def update_job(self, job_id: str, values: dict[str, Any]) -> None:
        if not self.enabled:
            return
        await self.jobs.update_one(
            {"job_id": job_id},
            {"$set": {**values, "updated_at": datetime.now(timezone.utc)}},
        )

    async def increment(self, key: str, amount: int = 1) -> None:
        if not self.enabled:
            return
        await self.stats.update_one({"_id": key}, {"$inc": {"value": amount}}, upsert=True)

    async def snapshot(self) -> dict[str, int]:
        if not self.enabled:
            return {}
        result: dict[str, int] = {}
        async for row in self.stats.find({}):
            result[str(row["_id"])] = int(row.get("value", 0))
        return result

    async def user_count(self) -> int:
        if not self.enabled:
            return 0
        return await self.users.count_documents({})
