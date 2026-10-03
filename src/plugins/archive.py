import asyncio
import tempfile
from pathlib import Path

from telethon import events

from ..config import SETTINGS
from ..handlers import ArchiveSecurityError, ProgressReporter, format_bytes
from ..utils.cleanup import delayed_message_cleanup
from ..utils.downloader import download_media
from ..utils.extractor import archive_kind, extract, inspect
from ..utils.queue import Job
from ..utils.uploader import upload_file

async def process_job(client, db, job: Job) -> bool:
    status = await client.send_message(job.chat_id, f"⏬ Preparing **{job.filename}**")
    message_ids = [status.id]
    try:
        await db.update_job(job.job_id, {"status": "downloading"})
        async with tempfile.TemporaryDirectory(prefix=f"{job.job_id}_", dir=SETTINGS.temp_dir) as temp:
            root = Path(temp)
            archive_path = root / Path(job.filename).name
            output = root / "output"
            source = await client.get_messages(job.chat_id, ids=job.message_id)
            if not source:
                raise RuntimeError("Original archive message is unavailable.")

            download_reporter = ProgressReporter(status, "⏬ Downloading", SETTINGS.progress_interval)

            def download_progress(current, total):
                asyncio.create_task(download_reporter.update(current, total))

            await download_media(client, source, archive_path, download_progress)
            plan = inspect(archive_path, job.filename)
            await db.update_job(job.job_id, {"status": "extracting", "files": plan.files, "expanded_bytes": plan.expanded_bytes})
            await status.edit(f"🔎 Validated **{plan.files}** files • **{format_bytes(plan.expanded_bytes)}** expanded")

            extraction_reporter = ProgressReporter(status, "🗂 Extracting", SETTINGS.progress_interval)

            def extraction_progress(current):
                asyncio.create_task(extraction_reporter.update(current, plan.expanded_bytes))

            result = await extract(archive_path, job.filename, output, extraction_progress)
            files = [p for p in result.files if p.is_file()]
            await db.update_job(job.job_id, {"status": "uploading", "files": len(files)})
            uploaded = 0
            upload_reporter = ProgressReporter(status, "📤 Uploading", SETTINGS.progress_interval)

            for path in files:
                size = path.stat().st_size

                def upload_progress(current, total, base=uploaded):
                    asyncio.create_task(upload_reporter.update(base + int(current), result.expanded_bytes))

                try:
                    sent = await upload_file(client, job.chat_id, path, job.message_id, upload_progress)
                    message_ids.append(sent.id)
                    uploaded += size
                except Exception as exc:
                    await db.increment("failed_uploads")
                    await db.update_job(job.job_id, {"last_upload_error": str(exc)[:500]})

            await db.update_job(job.job_id, {"status": "completed", "uploaded_bytes": uploaded})
            await db.increment("successful_jobs")
            await status.edit(f"✅ **Completed**\n\n📦 Files: **{len(files)}**\n💾 Expanded: **{format_bytes(result.expanded_bytes)}**\n📤 Uploaded: **{format_bytes(uploaded)}**")

            user = await db.user(job.user_id)
            if user.get("auto_delete", True):
                asyncio.create_task(delayed_message_cleanup(client, job.chat_id, message_ids + [job.message_id], SETTINGS.auto_delete_hours))
            return True
    except ArchiveSecurityError as exc:
        await db.update_job(job.job_id, {"status": "rejected", "error": str(exc)[:1000]})
        await db.increment("rejected_jobs")
        await status.edit(f"🛡️ **Archive rejected**\n\n{exc}")
        return False
    except Exception as exc:
        await db.update_job(job.job_id, {"status": "failed", "error": str(exc)[:1000]})
        await db.increment("failed_jobs")
        try:
            await status.edit(f"❌ **Job failed**\n\n{type(exc).__name__}: {exc}")
        except Exception:
            pass
        return False

async def archive_message(event, queue, db):
    message = event.message
    if not message or not message.file:
        return
    filename = message.file.name or "archive"
    if not archive_kind(filename):
        return
    size = int(message.file.size or 0)
    if size > SETTINGS.max_archive_bytes:
        await event.reply(f"❌ Archive exceeds **{SETTINGS.max_archive_mb} MB**.")
        await db.increment("rejected_jobs")
        return
    if queue.active_for_user(event.sender_id) + queue.queued_for_user(event.sender_id) >= SETTINGS.max_jobs_per_user:
        await event.reply("⏳ You already have a job in progress. Use /queue.")
        return
    job = await queue.submit(event.sender_id, event.chat_id, message.id, filename)
    await db.create_job(job.job_id, job.user_id, job.chat_id, job.message_id, job.filename)
    await event.reply(f"🧾 Job **{job.job_id}** queued.")
    try:
        await job.future
    except Exception:
        pass

async def help_command(event):
    await event.respond(f"**{SETTINGS.app_name} • Help**\n\nSend an archive as a Telegram document.\n\nSupported: ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ, TXZ.\n\nLimits: **{SETTINGS.max_archive_mb} MB** archive, **{SETTINGS.max_extracted_mb} MB** expanded data, **{SETTINGS.max_file_mb} MB** per file, **{SETTINGS.max_files}** files and **{SETTINGS.max_ratio}x** compression ratio.\n\n/cancel — cancel waiting jobs\n/queue — queue status\n/stats — aggregate stats\n/settings — preferences")

async def queue_command(event, queue):
    state = queue.status()
    await event.respond(f"**Queue**\n\nYour active: **{queue.active_for_user(event.sender_id)}**\nYour waiting: **{queue.queued_for_user(event.sender_id)}**\nGlobal active: **{state['active']}**\nGlobal waiting: **{state['queued']}**\nWorkers: **{state['workers']}**")

async def cancel_command(event, queue):
    removed = await queue.cancel_user(event.sender_id)
    await event.respond(f"🛑 Cancelled **{removed}** waiting job(s).")

async def stats_command(event, db, queue):
    values = await db.snapshot()
    await event.respond(f"**Statistics**\n\nSuccessful: **{values.get('successful_jobs',0)}**\nFailed: **{values.get('failed_jobs',0)}**\nRejected: **{values.get('rejected_jobs',0)}**\nActive: **{queue.status()['active']}**")

def register(client, db, queue):
    client.add_event_handler(lambda e: archive_message(e, queue, db), events.NewMessage(func=lambda e: bool(e.message and e.message.file)))
    client.add_event_handler(help_command, events.NewMessage(pattern=r"^/help(?:@\w+)?$"))
    client.add_event_handler(lambda e: queue_command(e, queue), events.NewMessage(pattern=r"^/queue(?:@\w+)?$"))
    client.add_event_handler(lambda e: cancel_command(e, queue), events.NewMessage(pattern=r"^/cancel(?:@\w+)?$"))
    client.add_event_handler(lambda e: stats_command(e, db, queue), events.NewMessage(pattern=r"^/stats(?:@\w+)?$"))
