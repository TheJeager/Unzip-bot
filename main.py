import asyncio
import logging
import os
import tempfile
import zipfile
from shutil import copyfileobj

FILE_COPY_BUFFER_SIZE = 8 * 1024 * 1024
TRANSFER_PART_SIZE_KB = 512
from datetime import datetime, timezone
from pathlib import Path

from telethon import Button, TelegramClient, events

from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    MAX_ARCHIVE_SIZE_MB,
    MONGODB_URI,
    START_IMAGE_URL,
    TEMP_DOWNLOAD_DIRECTORY,
    LOG_GROUP_ID,
)

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except Exception:  # pragma: no cover
    AsyncIOMotorClient = None

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
LOG = logging.getLogger("files_extract_bot")

HELP_TEXT = (
    "🧰 **How this bot works**\n\n"
    "1. Send a `.zip` file directly to this bot.\n"
    "2. The bot downloads and extracts it automatically.\n"
    "3. Extracted files are sent back to you quickly.\n"
    "4. Temporary files are removed after processing.\n\n"
    "**Supported now:** ZIP\n"
    "**Limit:** up to {limit} MB per ZIP file"
).format(limit=MAX_ARCHIVE_SIZE_MB)

PRIVACY_TEXT = """‼️ **IMPORTANT NOTES**

🛠️ **Basics**
This bot extracts uploaded `.zip` archives and sends extracted files back to the same chat.

• **Safety / Reporting syntax codes**
If extracted content is not allowed, reply to that file with: `/report <code>`

Useful issue syntax codes:
- `cp` → copyrighted/pirated content
- `mal` → malware or suspicious executable
- `nsfw` → explicit/adult material
- `spam` → spam/scam files
- `oth` → other policy violation

Example: `/report cp`

🔒 **Privacy**
Files are processed for extraction only, then temporary data is removed automatically.
"""

START_TEXT = (
    "Hello {mention}.\n\n"
    "**I'm Advance ZIP Extract Bot**\n\n"
    "Send a ZIP archive and I will quickly decompress it and send files back.\n"
    "Use the menu below for help and privacy details."
)

AUTO_DELETE_AFTER_SECONDS = 4 * 60 * 60

user_security_state: dict[int, dict] = {}


def _get_user_state(user_id: int) -> dict:
    state = user_security_state.setdefault(user_id, {})
    state.setdefault("agreed", False)
    return state


def _is_user_verified(user_id: int) -> bool:
    state = _get_user_state(user_id)
    return bool(state.get("agreed"))


class BotStore:
    def __init__(self, mongo_uri: str):
        self.enabled = bool(mongo_uri and AsyncIOMotorClient)
        self._client = AsyncIOMotorClient(mongo_uri) if self.enabled else None
        self._db = self._client["files_extract_bot"] if self.enabled else None

    @property
    def users(self):
        return self._db.users if self._db is not None else None

    @property
    def chats(self):
        return self._db.chats if self._db is not None else None

    @property
    def stats(self):
        return self._db.stats if self._db is not None else None

    async def init(self):
        if not self.enabled:
            LOG.warning("MongoDB disabled. Running without persistent state.")
            return
        await self.users.create_index("user_id", unique=True)
        await self.chats.create_index("chat_id", unique=True)

    async def touch_user_chat(self, user_id: int, chat_id: int):
        if not self.enabled:
            return
        now = datetime.now(timezone.utc)
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"updated_at": now}, "$setOnInsert": {"user_id": user_id, "created_at": now}},
            upsert=True,
        )
        await self.chats.update_one(
            {"chat_id": chat_id},
            {"$set": {"updated_at": now}, "$setOnInsert": {"chat_id": chat_id, "created_at": now}},
            upsert=True,
        )

    async def inc_stat(self, key: str, amount: int = 1):
        if not self.enabled:
            return
        await self.stats.update_one({"_id": key}, {"$inc": {"value": amount}}, upsert=True)

store = BotStore(MONGODB_URI)
active_zip_users: set[int] = set()

async def _load_user_state_from_store(user_id: int) -> dict:
    state = _get_user_state(user_id)
    if not store.enabled:
        return state
    doc = await store.users.find_one({"user_id": user_id}, {"agreed": 1})
    if not doc:
        return state
    state["agreed"] = bool(doc.get("agreed", False))
    return state


async def _save_user_state(user_id: int, state: dict):
    if not store.enabled:
        return
    now = datetime.now(timezone.utc)
    await store.users.update_one(
        {"user_id": user_id},
        {
            "$set": {"agreed": bool(state.get("agreed", False)), "updated_at": now},
            "$setOnInsert": {"user_id": user_id, "created_at": now},
        },
        upsert=True,
    )


def _build_start_buttons(agreed: bool = False):
    row1 = [Button.inline("Help & Usage", b"help"), Button.inline("Privacy", b"privacy")]
    if not agreed:
        return [row1, [Button.inline("Agree Terms", b"agree_terms")]]
    return [row1]


def _build_back_to_start_buttons():
    return [[Button.inline("Back", b"start_menu")]]


def _is_zip(filename: str | None) -> bool:
    return bool(filename and filename.lower().endswith(".zip"))


def _iter_extracted_files(root: Path):
    for base, _, files in os.walk(root):
        for name in files:
            yield Path(base) / name


def _is_within_directory(base_dir: Path, target_path: Path) -> bool:
    try:
        target_path.resolve().relative_to(base_dir.resolve())
        return True
    except ValueError:
        return False


def _extract_member(zf: zipfile.ZipFile, member: zipfile.ZipInfo, output_dir: Path):
    member_path = output_dir / member.filename
    if not _is_within_directory(output_dir, member_path):
        raise zipfile.BadZipFile(f"Unsafe path in archive: {member.filename}")

    if member.is_dir():
        member_path.mkdir(parents=True, exist_ok=True)
        return

    member_path.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(member, "r") as source, member_path.open("wb") as target:
        copyfileobj(source, target, length=FILE_COPY_BUFFER_SIZE)


def _format_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024 or unit == "TB":
            return f"{num_bytes:.2f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024
    return "0 B"




class ProgressReporter:
    def __init__(self, status_message, phase: str, update_interval: float = 1.5):
        self.status_message = status_message
        self.phase = phase
        self.update_interval = update_interval
        self.started_at = datetime.now(timezone.utc)
        self.last_update = self.started_at

    async def update(self, current: int, total: int):
        now = datetime.now(timezone.utc)
        elapsed = max((now - self.started_at).total_seconds(), 0.001)
        interval = max((now - self.last_update).total_seconds(), 0)
        is_complete = total > 0 and current >= total
        if interval < self.update_interval and not is_complete:
            return

        progress = 100.0 if total <= 0 else min((current / total) * 100, 100.0)
        speed_bps = current / elapsed
        bar_fill = min(int(progress // 10), 10)
        bar = "#" * bar_fill + "-" * (10 - bar_fill)

        await self.status_message.edit(
            f"{self.phase}\n"
            f"Progress: [{bar}] {progress:.1f}%\n"
            f"Size: {_format_size(current)} / {_format_size(total)}\n"
            f"Speed: {_format_size(int(speed_bps))}/s\n"
            f"Time: {elapsed:.1f}s"
        )
        self.last_update = now

async def _handle_zip_message(event):
    message = event.message
    if not message or not message.file:
        return

    user_id = event.sender_id
    chat_id = event.chat_id
    await store.touch_user_chat(user_id, chat_id)

    state = _get_user_state(user_id)
    if not state.get("agreed"):
        await event.reply("⚠️ Please review privacy policy and tap Agree Terms from /start before using extraction.")
        return
    filename = message.file.name or ""
    if not _is_zip(filename):
        return

    max_archive_size = MAX_ARCHIVE_SIZE_MB
    max_bytes = max_archive_size * 1024 * 1024
    if (message.file.size or 0) > max_bytes:
        await event.reply(f"❌ File too large. Max allowed for your plan: {max_archive_size} MB")
        return

    if user_id in active_zip_users:
        await event.reply("⚠️ Please wait for your previous ZIP to finish unzipping/uploading before sending another one.")
        return

    active_zip_users.add(user_id)

    status = await event.reply("⏬ Downloading ZIP archive...")
    messages_to_delete = [event.message.id, status.id]
    os.makedirs(TEMP_DOWNLOAD_DIRECTORY, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(prefix="extract_", dir=TEMP_DOWNLOAD_DIRECTORY) as temp_dir:
            temp_path = Path(temp_dir)
            archive_path = temp_path / filename
            extracted_dir = temp_path / "extracted"
            extracted_dir.mkdir(parents=True, exist_ok=True)

            download_reporter = ProgressReporter(status, "⏬ Downloading ZIP archive...")

            async def _download_progress(current, total):
                await download_reporter.update(current, total)

            await event.client.download_media(
                message,
                file=str(archive_path),
                progress_callback=_download_progress,
            )
            await status.edit("🗂️ Reading archive metadata...")
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    members = zf.infolist()
                    total_size = sum(m.file_size for m in members if not m.is_dir())
                    extracted_size = 0
                    unzip_reporter = ProgressReporter(status, "🗂️ Unzipping...")

                    for member in members:
                        _extract_member(zf, member, extracted_dir)
                        if not member.is_dir():
                            extracted_size += member.file_size
                        await unzip_reporter.update(extracted_size, total_size)
            except zipfile.BadZipFile:
                await status.edit("❌ Invalid or corrupted ZIP archive.")
                await store.inc_stat("failed_jobs")
                return
            except Exception as exc:
                await status.edit(f"❌ Extraction failed: {exc}")
                await store.inc_stat("failed_jobs")
                return

            files = list(_iter_extracted_files(extracted_dir))
            if not files:
                await status.edit("⚠️ Archive extracted, but no files were found.")
                await store.inc_stat("empty_jobs")
                return

            total_upload_size = sum(p.stat().st_size for p in files if p.exists())
            uploaded_size = 0
            upload_reporter = ProgressReporter(status, f"📤 Uploading {len(files)} extracted file(s)...")

            for file_path in files:
                file_size = file_path.stat().st_size if file_path.exists() else 0

                async def _upload_progress(current, total, base_uploaded=uploaded_size, this_size=file_size):
                    merged_current = base_uploaded + min(current, this_size)
                    await upload_reporter.update(merged_current, total_upload_size)

                try:
                    sent_message = await event.client.send_file(
                        event.chat_id,
                        str(file_path),
                        force_document=True,
                        allow_cache=False,
                        reply_to=event.message.id,
                        progress_callback=_upload_progress,
                    )
                    messages_to_delete.append(sent_message.id)
                except Exception as exc:
                    LOG.warning("Failed to send %s: %s", file_path, exc)

                uploaded_size += file_size
                await upload_reporter.update(uploaded_size, total_upload_size)

        await status.edit("✅ Done! Archive extracted and uploaded. Files will be auto-deleted in 4 hours.")
        await store.inc_stat("successful_jobs")

        async def _auto_delete_messages():
            await asyncio.sleep(AUTO_DELETE_AFTER_SECONDS)
            try:
                await event.client.delete_messages(event.chat_id, messages_to_delete)
            except Exception as exc:
                LOG.warning("Auto-delete failed in chat %s: %s", event.chat_id, exc)

        event.client.loop.create_task(_auto_delete_messages())
    finally:
        active_zip_users.discard(user_id)


def main():
    client = TelegramClient("files_extract_bot", API_ID, API_HASH)

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        state = await _load_user_state_from_store(event.sender_id)
        caption = (
            START_TEXT.format(mention=event.sender.first_name if event.sender else "there")
            + ("\n\n✨ Tap Agree Terms to enable ZIP extraction." if not state.get("agreed") else ".")
        )
        buttons = _build_start_buttons(agreed=state.get("agreed", False))
        if START_IMAGE_URL:
            await event.respond(file=START_IMAGE_URL, message=caption, buttons=buttons, link_preview=False)
        else:
            await event.respond(caption, buttons=buttons, link_preview=False)

    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def help_handler(event):
        await event.respond(HELP_TEXT, link_preview=False)

    @client.on(events.CallbackQuery(data=b"start_menu"))
    async def start_menu_callback(event):
        await event.answer()
        state = await _load_user_state_from_store(event.sender_id)
        await event.edit(START_TEXT, buttons=_build_start_buttons(agreed=state.get("agreed", False)))

    @client.on(events.CallbackQuery(data=b"help"))
    async def help_callback(event):
        await event.answer()
        await event.edit(HELP_TEXT, buttons=_build_back_to_start_buttons())

    @client.on(events.CallbackQuery(data=b"privacy"))
    async def privacy_callback(event):
        await event.answer()
        await event.edit(PRIVACY_TEXT, buttons=_build_back_to_start_buttons())

    @client.on(events.CallbackQuery(data=b"agree_terms"))
    async def agree_terms_callback(event):
        state = await _load_user_state_from_store(event.sender_id)
        state["agreed"] = True
        await _save_user_state(event.sender_id, state)
        await event.answer("Terms accepted")
        await event.edit("✅ Privacy policy accepted. You can now send ZIP files.", buttons=_build_back_to_start_buttons())

    @client.on(events.NewMessage(pattern=r"^/report(?:\s+([A-Za-z]+))?$"))
    async def report_handler(event):
        code = (event.pattern_match.group(1) or "").lower()
        if not event.is_reply:
            await event.reply("Reply to a file/message and use `/report <code>`.", parse_mode="md")
            return
        if code not in {"cp","mal","nsfw","spam","oth"}:
            await event.reply("Use one code: cp, mal, nsfw, spam, oth")
            return
        await event.reply("✅ Report received. Moderators will review.")
        if LOG_GROUP_ID:
            await event.client.send_message(
                LOG_GROUP_ID,
                (
                    "🚨 New report\n"
                    f"User: `{event.sender_id}`\n"
                    f"Chat: `{event.chat_id}`\n"
                    f"Code: `{code}`\n"
                    f"Link: https://t.me/c/{str(event.chat_id).replace('-100','')}/{event.reply_to_msg_id}"
                ),
                parse_mode="md",
            )

    @client.on(events.NewMessage(func=lambda e: bool(e.message and e.message.file)))
    async def auto_extract_handler(event):
        await _handle_zip_message(event)

    LOG.info("Bot is starting...")
    client.loop.run_until_complete(store.init())
    client.start(bot_token=BOT_TOKEN)
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
