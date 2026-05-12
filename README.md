# 🗃️ Files Unzip Bot

A clean, fast Telegram bot that **automatically decompresses ZIP files** and sends extracted files back to the user.

![logo](https://placehold.co/1200x420/0f172a/e2e8f0?text=File+Unzip+Bot+)

---

## ✨ Highlights

- 🚀 **Automatic ZIP extraction*
- 🤖 Built with **Telethon `>=1.43.2`**
- 📦 Smart upload flow for extracted files
- 🧹 Auto-cleanup of temporary files after each task
- 🔒 In-bot **Privacy Policy** and detailed **Help**
- 🎛️ Better `/start` experience with inline buttons

---

## 🧩 Commands & UI

- `/start` → beautiful start message with quick action buttons
- `/help` → detailed usage and limits
- **Inline Buttons**:
  - `📘 Help & Usage`
  - `🔒 Privacy Policy`

---

## ⚙️ Configuration

Create environment variables:

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `TEMP_DOWNLOAD_DIRECTORY` (optional, default: `./temp_downloads`)
- `MAX_ARCHIVE_SIZE_MB` (optional, default: ``)

---

## 🛠️ Installation

```bash
pip install -r requirements.txt
python main.py
```

---

## 🔐 Privacy Policy (Summary)

- Files are processed only to extract and return contents.
- Temporary files are deleted automatically after processing.
- No permanent storage of user file contents by design.

---

## 📌 Notes

- Current optimized workflow supports ZIP archives.
- If you deploy on cloud/VPS, make sure enough disk is available for temporary extraction.
