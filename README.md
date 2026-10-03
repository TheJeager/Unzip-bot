# ArchiveX

<div align="center">

<img src="https://upload.wikimedia.org/wikipedia/commons/3/32/Sketch_of_gojo_satoru.jpg" alt="Satoru Gojo banner" width="100%">

### A fast, secure Telegram bot for extracting archives

[![Stars](https://img.shields.io/github/stars/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot/stargazers)
[![Forks](https://img.shields.io/github/forks/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot/network/members)
[![License](https://img.shields.io/github/license/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/Telethon-1.45.0-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://github.com/LonamiWebs/Telethon)
[![PyMongo](https://img.shields.io/badge/PyMongo-4.18.2-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/docs/languages/python/pymongo-driver/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## About

ArchiveX is a Telegram archive extraction bot built to be simple to use and safe to run.

Send an archive to the bot and it handles the download, validation, extraction, upload and cleanup for you. Jobs are processed asynchronously, so one large archive does not have to block everything else.

The project is written as a modular Python application rather than one large bot file. Telegram handlers, archive processing, database access, queue management and security checks are kept separate so the code is easier to maintain and extend.

## What it can do

- Extract ZIP archives
- Extract TAR archives
- Extract TAR.GZ / TGZ archives
- Extract TAR.BZ2 / TBZ2 archives
- Extract TAR.XZ / TXZ archives
- Process multiple jobs through an async queue
- Limit jobs per user
- Show download, extraction and upload progress
- Keep temporary files isolated per job
- Automatically clean temporary data
- Store user settings and job statistics in MongoDB
- Run locally or inside Docker
- Run the container as a non-root user

## Security

Archive files are untrusted input, so ArchiveX does not simply unpack everything into the filesystem.

Before and during extraction, the bot checks things such as:

- Path traversal
- Unsafe archive member paths
- Symlinks
- Hard links
- Device and special files
- Archive size
- Expanded size
- Individual file size
- Number of extracted files
- Compression ratio
- Duplicate archive members

Every job gets its own temporary directory and that directory is removed when the job finishes.

MongoDB is used for metadata only. Archive contents are processed on the bot host and are not stored inside the database.

## How it works

```text
Telegram
   │
   ▼
Archive received
   │
   ▼
Format + security checks
   │
   ▼
Async job queue
   │
   ▼
Secure extraction
   │
   ▼
Upload extracted files
   │
   ▼
Cleanup + statistics
```

## Project structure

```text
Unzip-bot/
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── bot.py
│   ├── config.py
│   ├── database/
│   │   ├── mongo.py
│   │   ├── users.py
│   │   ├── jobs.py
│   │   └── stats.py
│   ├── plugins/
│   │   ├── start.py
│   │   ├── archive.py
│   │   ├── settings.py
│   │   ├── admin.py
│   │   └── callbacks.py
│   ├── utils/
│   │   ├── downloader.py
│   │   ├── extractor.py
│   │   ├── uploader.py
│   │   ├── queue.py
│   │   └── cleanup.py
│   └── handlers/
│       ├── progress.py
│       ├── security.py
│       └── formatting.py
├── Dockerfile
├── compose.yaml
├── requirements.txt
└── .env.example
```

The idea is straightforward:

- `plugins/` handles Telegram commands and callbacks
- `utils/` handles downloading, extraction, uploading and cleanup
- `handlers/` contains progress, security and formatting helpers
- `database/` handles MongoDB operations
- `bot.py` starts the application and connects the pieces together

## Commands

### User commands

| Command | Description |
|---|---|
| `/start` | Open the main bot panel |
| `/help` | Show help and supported archive formats |
| `/settings` | Configure user preferences |
| `/queue` | View queued and active jobs |
| `/cancel` | Cancel waiting jobs |
| `/stats` | View processing statistics |

### Owner commands

| Command | Description |
|---|---|
| `/admin` | View bot and job statistics |
| `/broadcast <message>` | Send a message to registered users |

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Then configure the required Telegram credentials.

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API hash |
| `BOT_TOKEN` | Telegram bot token |
| `MONGODB_URI` | MongoDB connection string |
| `OWNER_ID` | Telegram user ID of the bot owner |
| `TEMP_DOWNLOAD_DIRECTORY` | Temporary working directory |
| `MAX_ARCHIVE_SIZE_MB` | Maximum input archive size |
| `MAX_EXTRACTED_SIZE_MB` | Maximum total extracted size |
| `MAX_EXTRACTED_FILE_MB` | Maximum individual extracted file size |
| `MAX_EXTRACTED_FILES` | Maximum number of extracted files |
| `MAX_COMPRESSION_RATIO` | Maximum allowed compression ratio |
| `MAX_CONCURRENT_JOBS` | Global concurrent job limit |
| `MAX_JOBS_PER_USER` | Per-user job limit |
| `AUTO_DELETE_HOURS` | Automatic cleanup window |
| `PROGRESS_INTERVAL` | Progress update interval |
| `START_IMAGE_URL` | Optional start-panel image |
| `APP_NAME` | Bot application name |

Keep `.env` private and never commit real credentials.

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/TheJeager/Unzip-bot.git
cd Unzip-bot
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the bot

```bash
cp .env.example .env
```

Add your Telegram API credentials, bot token and other required settings.

### 5. Start

```bash
python3 -m src
```

## Docker

Build the image:

```bash
docker build -t archivex .
```

Run it:

```bash
docker run --env-file .env archivex
```

The container uses a dedicated non-root user and `tini` for clean process handling.

## Docker Compose

Start the bot:

```bash
docker compose up -d --build
```

Stop it:

```bash
docker compose down
```

Temporary archive data is kept in a dedicated Docker volume.

## Runtime

ArchiveX separates Telegram events from the actual archive work.

```text
Telegram handler
      │
      ▼
    JobQueue
   ┌──┼──┐
   ▼  ▼  ▼
 Worker Worker Worker
   │  │  │
   └──┼──┘
      ▼
Secure extractor
      │
      ▼
Telegram uploader
```

The global queue controls total concurrency while the per-user limit prevents a single user from occupying all available workers.

## Progress

The bot can report progress during:

- Archive download
- Archive extraction
- File upload

Progress messages are throttled so the bot does not continuously edit the same Telegram message.

## Technology

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| Telegram framework | Telethon 1.45.0 |
| Database driver | PyMongo 4.18.2 |
| Database | MongoDB |
| Concurrency | asyncio |
| Containers | Docker |
| Init process | tini |
| Archive handling | Python standard library |

## Contributing

Pull requests and improvements are welcome.

For larger changes, keep the existing separation between Telegram handlers, processing utilities, database code and configuration.

## License

See the repository license file for the license terms.

## Banner credit

The Gojo Satoru artwork used in the README banner is the work of Aarlen and is published under **CC BY 4.0**. The image is used as a visual banner and is not part of the bot's source code.

---

<div align="center">

**ArchiveX**

A clean Telegram archive bot built with Python, Telethon and async processing.

</div>
