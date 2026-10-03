import asyncio
import tempfile
from pathlib import Path

from telethon import events

from .archive import ArchiveSecurityError, archive_kind, extract, inspect
from .config import SETTINGS
from .database import Database
from .queue import Job, JobQueue
from .ui import back_button, commands_text, help_text, home_text, privacy_text, settings_buttons, settings_text, start_buttons

def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return "0 B"

class Progress:
    def __init__(self, message, label: str):
        self.message = message
        self.label = label
        self.last = 0.0
        self.started = asyncio.get_running_loop().time()

    async def update(self, current: int, total: int) -> None:
        now = asyncio.get_running_loop().time()
        if current < total and now - self.last < SETTINGS.progress_interval:
            return
        self.last = now
        elapsed = max(now - self.started, 0.1)
        percent = 100 if total <= 0 else min(current * 100 / total, 100)
        speed = current / elapsed
        filled = int(percent // 10)
        bar = "▰" * filled + "▱" * (10 - filled)
        try:
            await self.message.edit(
                f"{self.label}\n\n"
                f"{bar} {percent:.1f}%\n"
                f"{format_bytes(current)} / {format_bytes(total)}\n"
                f"⚡ {format_bytes(int(speed))}/s"
            )
        except Exception:
            pass

class BotHandlers:
    def __init__(self, client, db: Database, queue: JobQueue):
        self.client = client
        self.db = db
        self.queue = queue
        self.cleanup_tasks: set[asyncio.Task] = set()

    def register(self) -> None:
        self.client.add_event_handler(self.start, events.NewMessage(pattern=r"^/start(?:@\\w+)?$"))
        self.client.add_event_handler(self.help, events.NewMessage(pattern=r"^/help(?:@\\w+)?$"))
        self.client.add_event_handler(self.settings, events.NewMessage(pattern=r"^/settings(?:@\\w+)?$"))
        self.client.add_event_handler(self.stats, events.NewMessage(pattern=r"^/stats(?:@\\w+)?$"))
        self.client.add_event_handler(self.queue_status, events.NewMessage(pattern=r"^/queue(?:@\\w+)?$"))
        self.client.add_event_handler(self.cancel, events.NewMessage(pattern=r"^/cancel(?:@\\w+)?$"))
        self.client.add_event_handler(self.admin, events.NewMessage(pattern=r"^/admin(?:@\\w+)?$"))
        self.client.add_event_handler(self.broadcast, events.NewMessage(pattern=r"^/broadcast(?:@\\w+)?(?:\\s+(.+))?$"))
        self.client.add_event_handler(self.maintenance, events.NewMessage(pattern=r"^/maintenance(?:@\\w+)?$"))
        self.client.add_event_handler(self.callbacks, events.CallbackQuery())
        self.client.add_event_handler(self.archive_message, events.NewMessage(func=lambda event: bool(event.message and event.message.file)))

    async def start(self, event) -> None:
        user = await self.db.user(event.sender_id)
        name = getattr(event.sender, "first_name", None) or "there"
        text = home_text(name, bool(user.get("agreed")))
        if SETTINGS.start_image_url:
            await event.respond(file=SETTINGS.start_image_url, message=text, buttons=start_buttons(bool(user.get("agreed"))), link_preview=False)
        else:
            await event.respond(text, buttons=start_buttons(bool(user.get("agreed"))), link_preview=False)

    async def help(self, event) -> None:
        await event.respond(help_text(), buttons=back_button(), link_preview=False)

    async def settings(self, event) -> None:
        user = await self.db.user(event.sender_id)
        await event.respond(settings_text(bool(user.get("auto_delete", True))), buttons=settings_buttons(bool(user.get("auto_delete", True))))

    async def stats(self, event) -> None:
        values = await self.db.snapshot()
        await event.respond(
            f"**{SETTINGS.app_name} • Stats**\n\n"
            f"Successful jobs: **{values.get('successful_jobs', 0)}**\n"
            f"Failed jobs: **{values.get('failed_jobs', 0)}**\n"
            f"Rejected archives: **{values.get('rejected_jobs', 0)}**\n"
            f"Queue active: **{self.queue.status()['active']}**"
        )

    async def queue_status(self, event) -> None:
        state = self.queue.status()
        await event.respond(
            f"**{SETTINGS.app_name} • Queue**\n\n"
            f"Your active: **{self.queue.active_for_user(event.sender_id)}**\n"
            f"Your waiting: **{self.queue.queued_for_user(event.sender_id)}**\n"
            f"Global active: **{state['active']}**\n"
            f"Global waiting: **{state['queued']}**\n"
            f"Workers: **{state['workers']}**"
        )

    async def cancel(self, event) -> None:
        removed = await self.queue.cancel_user(event.sender_id)
        await event.respond(f"🛑 Cancelled **{removed}** waiting job(s). Active jobs continue safely.")

    async def admin(self, event) -> None:
        if event.sender_id != SETTINGS.owner_id:
            return
        state = self.queue.status()
        count = await self.db.user_count()
        await event.respond(
            f"**{SETTINGS.app_name} • Owner Panel**\n\n"
            f"Users: **{count}**\n"
            f"Queue: **{state['active']} active / {state['queued']} waiting**\n"
            f"MongoDB: **{'enabled' if self.db.enabled else 'disabled'}**\n"
            f"Archive limit: **{SETTINGS.max_archive_mb} MB**\n"
            f"Expanded limit: **{SETTINGS.max_extracted_mb} MB**"
        )

    async def broadcast(self, event) -> None:
        if event.sender_id != SETTINGS.owner_id:
            return
        text = event.pattern_match.group(1)
        if not text or not self.db.enabled:
            await event.respond("Usage: /broadcast your message\nMongoDB must be enabled.")
            return
        sent = 0
        async for user in self.db.users.find({}, {"user_id": 1}):
            try:
                await self.client.send_message(user["user_id"], text)
                sent += 1
            except Exception:
                pass
            await asyncio.sleep(0.05)
        await event.respond(f"📣 Broadcast finished: **{sent}** delivered.")

    async def maintenance(self, event) -> None:
        if event.sender_id == SETTINGS.owner_id:
            state = "ON" if SETTINGS.maintenance_mode else "OFF"
            await event.respond(f"🛠️ Maintenance mode: **{state}**\nChange MAINTENANCE_MODE and restart the bot.")

    async def callbacks(self, event) -> None:
        data = event.data.decode()
        user = await self.db.user(event.sender_id)
        if data == "home":
            name = getattr(event.sender, "first_name", None) or "there"
            await event.edit(home_text(name, bool(user.get("agreed"))), buttons=start_buttons(bool(user.get("agreed"))))
        elif data == "help":
            await event.edit(help_text(), buttons=back_button())
        elif data == "commands":
            await event.edit(commands_text(), buttons=back_button())
        elif data == "privacy":
            await event.edit(privacy_text(), buttons=back_button())
        elif data == "settings":
            value = bool(user.get("auto_delete", True))
            await event.edit(settings_text(value), buttons=settings_buttons(value))
        elif data == "toggle_delete":
            value = not bool(user.get("auto_delete", True))
            await self.db.update_user(event.sender_id, {"auto_delete": value})
            await event.edit(settings_text(value), buttons=settings_buttons(value))
        elif data == "stats":
            values = await self.db.snapshot()
            await event.edit(
                f"**{SETTINGS.app_name} • Stats**\n\n"
                f"Successful: **{values.get('successful_jobs', 0)}**\n"
                f"Failed: **{values.get('failed_jobs', 0)}**\n"
                f"Rejected: **{values.get('rejected_jobs', 0)}**",
                buttons=back_button(),
            )
        elif data == "agree":
            await self.db.update_user(event.sender_id, {"agreed": True})
            name = getattr(event.sender, "first_name", None) or "there"
            await event.edit(home_text(name, True), buttons=start_buttons(True))
            await event.answer("Terms accepted")
            return
        await event.answer()

    async def archive_message(self, event) -> None:
        message = event.message
        if not message or not message.file:
            return
        filename = message.file.name or "archive"
        if not archive_kind(filename):
            return
        user = await self.db.user(event.sender_id)
        if not user.get("agreed"):
            await event.reply("🔐 Open /start and accept the terms before sending archives.")
            return
        if SETTINGS.maintenance_mode and event.sender_id != SETTINGS.owner_id:
            await event.reply("🛠️ The bot is temporarily in maintenance mode.")
            return
        size = int(message.file.size or 0)
        if size > SETTINGS.max_archive_mb * 1024 * 1024:
            await event.reply(f"❌ Archive exceeds the {SETTINGS.max_archive_mb} MB limit.")
            await self.db.increment("rejected_jobs")
            return
        if self.queue.active_for_user(event.sender_id) + self.queue.queued_for_user(event.sender_id) >= SETTINGS.max_jobs_per_user:
            await event.reply("⏳ You already have a job in progress. Use /queue to check it.")
            return
        job = await self.queue.submit(event.sender_id, event.chat_id, message.id, filename)
        await self.db.create_job(job.job_id, job.user_id, job.chat_id, job.filename)
        await event.reply(f"🧾 Job {job.job_id} queued.\nPosition: {self.queue.queued_for_user(event.sender_id)}")
        await job.future

    async def process_job(self, job: Job) -> bool:
        status = None
        message_ids: list[int] = []
        try:
            await self.db.update_job(job.job_id, {"status": "downloading"})
            status = await self.client.send_message(job.chat_id, f"⏬ {job.filename}\nPreparing secure download...")
            message_ids.append(status.id)
            async with tempfile.TemporaryDirectory(prefix=f"{job.job_id}_", dir=SETTINGS.temp_dir) as temp:
                root = Path(temp)
                archive_path = root / Path(job.filename).name
                output = root / "output"
                reporter = Progress(status, "⏬ Downloading archive")
                original = await self.client.get_messages(job.chat_id, ids=job.message_id)
                if not original:
                    raise RuntimeError("Original archive message is unavailable.")
                async def download_progress(current, total):
                    await reporter.update(current, total)
                await self.client.download_media(original, file=str(archive_path), progress_callback=download_progress)
                plan = inspect(archive_path, job.filename)
                await self.db.update_job(job.job_id, {"status": "extracting", "files": plan.files, "expanded_bytes": plan.extracted_bytes})
                await status.edit(f"🔎 Validated {plan.files} files • {format_bytes(plan.extracted_bytes)} expanded")
                reporter = Progress(status, "🗂 Extracting archive")
                last = 0
                def extraction_progress(current):
                    nonlocal last
                    if current - last >= 2 * 1024 * 1024 or current == plan.extracted_bytes:
                        last = current
                        asyncio.create_task(reporter.update(current, plan.extracted_bytes))
                result = await extract(archive_path, job.filename, output, extraction_progress)
                files = [path for path in result.files if path.is_file()]
                await self.db.update_job(job.job_id, {"status": "uploading", "files": len(files)})
                uploaded = 0
                upload_reporter = Progress(status, f"📤 Uploading {len(files)} files")
                for path in files:
                    file_size = path.stat().st_size
                    async def upload_progress(current, total, base=uploaded):
                        await upload_reporter.update(base + current, result.extracted_bytes)
                    try:
                        sent = await self.client.send_file(job.chat_id, str(path), force_document=True, allow_cache=False, reply_to=job.message_id, progress_callback=upload_progress)
                        message_ids.append(sent.id)
                        uploaded += file_size
                    except Exception:
                        await self.db.increment("failed_uploads")
                await status.edit(
                    f"✅ Completed\n\n"
                    f"📦 Files: {len(files)}\n"
                    f"💾 Expanded: {format_bytes(result.extracted_bytes)}\n"
                    f"📤 Uploaded: {format_bytes(uploaded)}"
                )
                await self.db.update_job(job.job_id, {"status": "completed", "uploaded_bytes": uploaded})
                await self.db.increment("successful_jobs")
                user = await self.db.user(job.user_id)
                if user.get("auto_delete", True):
                    task = asyncio.create_task(self._cleanup(job.chat_id, message_ids + [job.message_id]))
                    self.cleanup_tasks.add(task)
                    task.add_done_callback(self.cleanup_tasks.discard)
            return True
        except ArchiveSecurityError as exc:
            await self.db.update_job(job.job_id, {"status": "rejected", "error": str(exc)[:1000]})
            await self.db.increment("rejected_jobs")
            if status:
                await status.edit(f"🛡️ Archive rejected\n\n{exc}")
            return False
        except Exception as exc:
            await self.db.update_job(job.job_id, {"status": "failed", "error": str(exc)[:1000]})
            await self.db.increment("failed_jobs")
            if status:
                try:
                    await status.edit(f"❌ Job failed\n\n{type(exc).__name__}: {exc}")
                except Exception:
                    pass
            return False

    async def _cleanup(self, chat_id: int, message_ids: list[int]) -> None:
        await asyncio.sleep(SETTINGS.auto_delete_hours * 3600)
        try:
            await self.client.delete_messages(chat_id, list(dict.fromkeys(message_ids)))
        except Exception:
            pass
