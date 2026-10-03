from .mongo import Database

class StatsRepository:
    def __init__(self, db: Database):
        self.db = db

    async def increment(self, key: str, amount: int = 1) -> None:
        await self.db.increment(key, amount)

    async def snapshot(self) -> dict[str, int]:
        return await self.db.snapshot()
