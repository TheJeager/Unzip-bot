import asyncio
import logging

from pyrogram import Client

from .config import SETTINGS
from .database.mongo import Database
from .plugins import admin, archive, callbacks, settings, start
from .utils.queue import JobQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
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
    start.register(client)
    settings.register(client, db)
    callbacks.register(client, db)
    admin.register(client, db, queue)
    archive.register(client, db, queue)

    try:
        await db.init()
        await queue.start()
        await client.start()
        log.info(
            "%s started with %s workers",
            SETTINGS.app_name,
            SETTINGS.max_concurrent_jobs,
        )
        await asyncio.Event().wait()
    finally:
        await queue.stop()
        await client.stop()
        await db.close()


def main() -> None:
    asyncio.run(run())
