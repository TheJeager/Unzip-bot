import asyncio
import logging

from telethon import TelegramClient

from .config import SETTINGS
from .database import Database
from .handlers import BotHandlers
from .queue import JobQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("archivex")

async def run() -> None:
    db = Database()
    queue = JobQueue()
    client = TelegramClient("archivex_bot", SETTINGS.api_id, SETTINGS.api_hash)
    handlers = BotHandlers(client, db, queue)
    queue.configure(handlers.process_job)
    await db.init()
    await queue.start()
    handlers.register()
    await client.start(bot_token=SETTINGS.telegram_credential)
    log.info("%s started with %s workers", SETTINGS.app_name, SETTINGS.max_concurrent_jobs)
    try:
        await client.run_until_disconnected()
    finally:
        await queue.stop()
        await db.close()

def main() -> None:
    asyncio.run(run())
