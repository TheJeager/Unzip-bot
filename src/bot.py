import asyncio
import logging

from pyrogram import Client

from .config import SETTINGS
from .database.mongo import Database
from .plugins import admin, archive, callbacks, settings, start
from .utils.queue import JobQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger(SETTINGS.app_name)

async def run() -> None:
    db = Database()
    queue = JobQueue(SETTINGS.max_concurrent_jobs, SETTINGS.max_jobs_per_user)
    client = Client(
        "unzip_bot",
        api_id=SETTINGS.api_id,
        api_hash=SETTINGS.api_hash,
        bot_token=SETTINGS.bot_token,
        workdir=str(SETTINGS.temp_dir),
    )
    queue.configure(lambda job: archive.process_job(client, db, job))
    await db.init()
    await queue.start()
    start.register(client)
    settings.register(client, db)
    callbacks.register(client, db)
    admin.register(client, db, queue)
    archive.register(client, db, queue)
    await client.start()
    log.info("%s started with %s workers", SETTINGS.app_name, SETTINGS.max_concurrent_jobs)
    try:
        await asyncio.Event().wait()
    finally:
        await queue.stop()
        await db.close()
        await client.stop()

def main() -> None:
    asyncio.run(run())

