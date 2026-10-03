import asyncio
import logging

from telethon import TelegramClient

from .config import SETTINGS
from .database.mongo import Database
from .plugins import admin, archive, callbacks, settings, start
from .utils.queue import JobQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger(SETTINGS.app_name)

async def run() -> None:
    db = Database()
    queue = JobQueue(SETTINGS.max_concurrent_jobs, SETTINGS.max_jobs_per_user)
    client = TelegramClient("archivex_bot", SETTINGS.api_id, SETTINGS.api_hash)
    queue.configure(lambda job: archive.process_job(client, db, job))
    await db.init()
    await queue.start()
    start.register(client)
    settings.register(client, db)
    callbacks.register(client, db)
    admin.register(client, db, queue)
    archive.register(client, db, queue)
    await client.start(bot_token=SETTINGS.bot_token)
    log.info("%s started with %s workers", SETTINGS.app_name, SETTINGS.max_concurrent_jobs)
    try:
        await client.run_until_disconnected()
    finally:
        await queue.stop()
        await db.close()

def main() -> None:
    asyncio.run(run())
