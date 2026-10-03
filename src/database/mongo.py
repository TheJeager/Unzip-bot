from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from ..config import SETTINGS

class Database:
    def __init__(self) -> None:
        self.client = AsyncIOMotorClient(SETTINGS.mongo_uri) if SETTINGS.mongo_uri else None
        self.db = self.client.archivex if self.client else None

    @property
    def enabled(self) -> bool:
        return self.db is not None

    async def init(self) -> None:
        if not self.db:
            return
        await self.db.users.create_index("user_id", unique=True)
        await self.db.jobs.create_index("job_id", unique=True)
        await self.db.jobs.create_index([("user_id", 1), ("created_at", -1)])

    async def close(self) -> None:
        if self.client:
            self.client.close()

    async def user(self, user_id: int) -> dict[str, Any]:
        defaults = {"user_id": user_id, "agreed": False, "auto_delete": True}
        if not self.db:
            return defaults
        now = datetime.now(timezone.utc)
        await self.db.users.update_one({"user_id": user_id},{"$setOnInsert": {**defaults, "created_at": now}},upsert=True)
        doc = await self.db.users.find_one({"user_id": user_id}) or defaults
        return {**defaults, **doc}

    async def update_user(self, user_id: int, values: dict[str, Any]) -> None:
        if not self.db:
            return
        await self.db.users.update_one({"user_id": user_id},{"$set": {**values, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"user_id": user_id}},upsert=True)

    async def create_job(self, job_id: str, user_id: int, chat_id: int, message_id: int, filename: str) -> None:
        if not self.db:
            return
        now = datetime.now(timezone.utc)
        await self.db.jobs.insert_one({"job_id": job_id,"user_id": user_id,"chat_id": chat_id,"message_id": message_id,"filename": filename,"status":"queued","created_at":now,"updated_at":now})

    async def update_job(self, job_id: str, values: dict[str, Any]) -> None:
        if self.db:
            await self.db.jobs.update_one({"job_id": job_id},{"$set": {**values,"updated_at": datetime.now(timezone.utc)}})

    async def increment(self, key: str, amount: int = 1) -> None:
        if self.db:
            await self.db.stats.update_one({"_id": key},{"$inc":{"value":amount}},upsert=True)

    async def snapshot(self) -> dict[str, int]:
        if not self.db:
            return {}
        result = {}
        async for row in self.db.stats.find({}):
            result[str(row["_id"])] = int(row.get("value", 0))
        return result

    async def user_count(self) -> int:
        return await self.db.users.count_documents({}) if self.db else 0

    async def user_ids(self):
        if not self.db:
            return
        async for row in self.db.users.find({}, {"user_id": 1}):
            yield int(row["user_id"])
