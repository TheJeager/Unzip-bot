from typing import Any
from .mongo import Database

class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get(self, user_id: int) -> dict[str, Any]:
        return await self.db.user(user_id)

    async def update(self, user_id: int, values: dict[str, Any]) -> None:
        await self.db.update_user(user_id, values)
