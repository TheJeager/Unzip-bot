import asyncio
import tempfile
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler

from ..config import SETTINGS
from ..handlers import ArchiveSecurityError, ProgressReporter, format_bytes
from ..utils.cleanup import delayed_message_cleanup
from ..utils.downloader import download_media
from ..utils.extractor import archive_kind, extract, inspect
from ..utils.queue import Job
from ..utils.uploader import upload_file


async def process_job(client: Client, db, job: Job) -> bool:
    status = None
    message_ids = []

    try:
        status = await client.send_message(job.chat_id, f"⏬ Preparing **{job.filename}**")
        message_ids.append(status.id)
        await db.update_job(job.job_id, {"status": "downloading"})

        async with tempfile.TemporaryDirectory(
            prefix=f"{job.job_id}_",
            dir=SETTINGS.temp_dir,
        ) as temp:
            root = Path(temp)
            archive_path = root / Path(job.filename).name
            output = root / "output"
            source = await client.get_messages(job.chat_id, job.message_id)

            if not source:
                raise RuntimeError("Original archive message is unavailable.")

            download_reporter = ProgressReporter(
                status,
                "⏬ Downloading",
                SETTINGS.progress_interval,
            )

            async def download_progress(current, total):
                await download_reporter.update(current, total)

            await download_media(client, source, archive_path, download_progress)

            plan = inspect(archive_path, job.filename)
            await db.update_job(
                job.job_id,
                {
                    "status": "extracting",
                    "files": plan.files,
                    "expanded_bytes": plan.expanded_bytes,
                },
            )
            await status.edit_text(
                f"🔎 Validated **{plan.files}** files • "
                f"**{format_bytes(plan.expanded_bytes)}** expanded"
            )

            extraction_reporter = ProgressReporter(
                status,
                "🗂 Extracting",
                SETTINGS.progress_interval,
            )

            extraction_tasks = set()

            def extraction_progress(current):
                task = asyncio.create_task(
                    extraction_reporter.update(current, plan.expanded_bytes)
                )
                extraction_tasks.add(task)
                task.add_done_callback(extraction_tasks.discard)

            result = await extract(
                archive_path,
                job.filename,
                output,
                extraction_progress,
                plan,
            )
            if extraction_tasks:
                await asyncio.gather(*extraction_tasks, return_exceptions=True)
            await extraction_reporter.update(
                result.expanded_bytes,
                result.expanded_bytes,
            )
            files = [path for path in result.files if path.is_file()]

            await db.update_job(
                job.job_id,
                {"status": "uploading", "files": len(files)},
            )

            uploaded = 0
            uploaded_files = 0
            failed_files = 0
            upload_reporter = ProgressReporter(
                status,
                "📤 Uploading",
                SETTINGS.progress_interval,
            )

            for path in files:
                size = path.stat().st_size

                async def upload_progress(current, total, base=uploaded):
                    await upload_reporter.update(
                        base + int(current),
                        result.expanded_bytes,
                    )

                try:
                    sent = await upload_file(
                        client,
                        job.chat_id,
                        path,
                        job.message_id,
                        upload_progress,
                    )
                    if not sent:
                        raise RuntimeError("Telegram returned no uploaded message.")
                    message_ids.append(sent.id)
                    uploaded += size
                    uploaded_files += 1
                except Exception as exc:
                    failed_files += 1
                    await db.increment("failed_uploads")
                    await db.update_job(
                        job.job_id,
                        {"last_upload_error": str(exc)[:500]},
                    )

            if failed_files:
                final_status = "completed_with_errors" if uploaded_files else "failed"
                counter = "partial_jobs" if uploaded_files else "failed_jobs"
                await db.update_job(
                    job.job_id,
                    {
                        "status": final_status,
                        "uploaded_bytes": uploaded,
                        "uploaded_files": uploaded_files,
                        "failed_files": failed_files,
                    },
                )
                await db.increment(counter)

                if uploaded_files:
                    await status.edit_text(
                        f"⚠️ **Completed with errors**

"
                        f"📦 Files: **{len(files)}**
"
                        f"✅ Uploaded: **{uploaded_files}**
"
                        f"❌ Failed: **{failed_files}**
"
                        f"📤 Uploaded data: **{format_bytes(uploaded)}**"
                    )
                else:
                    await status.edit_text(
                        f"❌ **Upload failed**

"
                        f"📦 Files: **{len(files)}**
"
                        f"❌ Failed: **{failed_files}**"
                    )
                return False

            await db.update_job(
                job.job_id,
                {
                    "status": "completed",
                    "uploaded_bytes": uploaded,
                    "uploaded_files": uploaded_files,
                    "failed_files": 0,
                },
            )
            await db.increment("successful_jobs")

            await status.edit_text(
                f"✅ **Completed**

"
                f"📦 Files: **{len(files)}**
"
                f"💾 Expanded: **{format_bytes(result.expanded_bytes)}**
"
                f"📤 Uploaded: **{format_bytes(uploaded)}**"
            )

            user = await db.user(job.user_id)
            if user.get("auto_delete", True):
                asyncio.create_task(
                    delayed_message_cleanup(
                        client,
                        job.chat_id,
                        message_ids + [job.message_id],
                        SETTINGS.auto_delete_hours,
                    )
                )
            return True

    except ArchiveSecurityError as exc:
        await db.update_job(
            job.job_id,
            {"status": "rejected", "error": str(exc)[:1000]},
        )
        await db.increment("rejected_jobs")
        if status:
            try:
                await status.edit_text(f"🛡️ **Archive rejected**

{exc}")
            except Exception:
                pass
        return False

    except Exception as exc:
        await db.update_job(
            job.job_id,
            {"status": "failed", "error": str(exc)[:1000]},
        )
        await db.increment("failed_jobs")
        if status:
            try:
                await status.edit_text(
                    f"❌ **Job failed**

{type(exc).__name__}: {exc}"
                )
            except Exception:
                pass
        return False


async def archive_message(client: Client, message, queue, db):
    if not message.document or not message.from_user:
        return

    filename = message.document.file_name or "archive"
    if not archive_kind(filename):
        return

    size = int(message.document.file_size or 0)
    if size > SETTINGS.max_archive_bytes:
        await message.reply_text(
            f"❌ Archive exceeds **{SETTINGS.max_archive_mb} MB**."
        )
        await db.increment("rejected_jobs")
        return

    if (
        queue.active_for_user(message.from_user.id)
        + queue.queued_for_user(message.from_user.id)
        >= SETTINGS.max_jobs_per_user
    ):
        await message.reply_text("⏳ You already have a job in progress. Use /queue.")
        return

    job = await queue.submit(
        message.from_user.id,
        message.chat.id,
        message.id,
        filename,
    )
    await db.create_job(
        job.job_id,
        job.user_id,
        job.chat_id,
        job.message_id,
        job.filename,
    )
    await message.reply_text(f"🧾 Job **{job.job_id}** queued.")

    try:
        await job.future
    except Exception:
        pass


async def help_command(client: Client, message):
    await message.reply_text(
        f"""**{SETTINGS.app_name} • Help**

Send an archive as a Telegram document.

Supported: ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ, TXZ.

Limits: **{SETTINGS.max_archive_mb} MB** archive, **{SETTINGS.max_extracted_mb} MB** expanded data, **{SETTINGS.max_file_mb} MB** per file, **{SETTINGS.max_files}** files and **{SETTINGS.max_ratio}x** compression ratio.

/cancel — cancel waiting jobs
/queue — queue status
/stats — aggregate stats
/settings — preferences"""
    )


async def queue_command(client: Client, message, queue):
    state = queue.status()
    await message.reply_text(
        f"""**Queue**

Your active: **{queue.active_for_user(message.from_user.id)}**
Your waiting: **{queue.queued_for_user(message.from_user.id)}**
Global active: **{state['active']}**
Global waiting: **{state['queued']}**
Workers: **{state['workers']}**"""
    )


async def cancel_command(client: Client, message, queue, db):
    jobs = await queue.cancel_user(message.from_user.id)
    for job in jobs:
        await db.update_job(
            job.job_id,
            {"status": "cancelled", "error": "Cancelled by user."},
        )
    await message.reply_text(f"🛑 Cancelled **{len(jobs)}** waiting job(s).")


async def stats_command(client: Client, message, db, queue):
    values = await db.snapshot()
    await message.reply_text(
        f"""**Statistics**

Successful: **{values.get('successful_jobs', 0)}**
Partial: **{values.get('partial_jobs', 0)}**
Failed: **{values.get('failed_jobs', 0)}**
Rejected: **{values.get('rejected_jobs', 0)}**
Active: **{queue.status()['active']}**"""
    )


def register(client: Client, db, queue) -> None:
    async def archive_handler(client: Client, message):
        await archive_message(client, message, queue, db)

    async def queue_handler(client: Client, message):
        await queue_command(client, message, queue)

    async def cancel_handler(client: Client, message):
        await cancel_command(client, message, queue, db)

    async def stats_handler(client: Client, message):
        await stats_command(client, message, db, queue)

    client.add_handler(MessageHandler(archive_handler, filters.document))
    client.add_handler(MessageHandler(help_command, filters.command("help")))
    client.add_handler(MessageHandler(queue_handler, filters.command("queue")))
    client.add_handler(MessageHandler(cancel_handler, filters.command("cancel")))
    client.add_handler(MessageHandler(stats_handler, filters.command("stats")))
