# Unzip Bot

<div align="center">

<img src="https://raw.githubusercontent.com/TheJeager/Unzip-bot/main/assets/unzip-bot-hero.svg" alt="Unzip Bot" width="100%">

### A fast, secure Telegram bot for extracting archives

[![Stars](https://img.shields.io/github/stars/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot/stargazers)
[![Forks](https://img.shields.io/github/forks/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot/network/members)
[![License](https://img.shields.io/github/license/TheJeager/Unzip-bot?style=for-the-badge)](https://github.com/TheJeager/Unzip-bot)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Kurigram](https://img.shields.io/badge/Kurigram-2.2.26-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://github.com/kurigram-org/kurigram)
[![PyMongo](https://img.shields.io/badge/PyMongo-4.18.2-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/docs/languages/python/pymongo-driver/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## About

Unzip Bot is a Telegram bot for extracting archive files directly through Telegram.

Send an archive and the bot takes care of downloading it, checking it, extracting its contents, uploading the results and cleaning up temporary files. Processing runs through an asynchronous job queue so multiple users can use the bot without one job blocking the entire application.

The codebase is split into focused modules for Telegram handlers, archive processing, security, queue management, database access and file cleanup.

## Features

- ZIP extraction
- Password-protected ZIP extraction
- AES-encrypted ZIP support
- TAR extraction
- TAR.GZ / TGZ extraction
- TAR.BZ2 / TBZ2 extraction
- TAR.XZ / TXZ extraction
- Asynchronous job queue
- Per-user job limits
- Download, extraction and upload progress
- Isolated temporary workspaces
- Automatic cleanup
- MongoDB-backed user and job data
- Docker support
- Non-root container execution

## Security

Archive files are treated as untrusted input.

Unzip Bot checks archive contents before and during extraction to reduce common archive-extraction risks:

- Path traversal
- Unsafe archive paths
- Symlinks
- Hard links
- Device and special files
- Maximum archive size
- Maximum expanded size
- Maximum individual file size
- Maximum extracted file count
- Compression ratio limits
- Duplicate members
- Passwords kept only in process memory and never persisted

Each job receives an isolated temporary directory. Temporary data is removed after processing, including failure paths.

MongoDB stores application metadata rather than archive contents.

## Processing

```text
Telegram
   │
   ▼
Archive received
   │
   ▼
Validation
   │
   ▼
Async queue
   │
   ▼
Secure extraction
   │
   ▼
Telegram upload
   │
   ▼
Cleanup
```

## Project Structure

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
├── assets/
│   └── unzip-bot-hero.svg
├── Dockerfile
├── compose.yaml
├── requirements.txt
└── .env.example
```

## Commands

### User

| Command | Description |
|---|---|
| `/start` | Open the main bot panel |
| `/help` | Show help and supported formats |
| `/settings` | Configure preferences |
| `/queue` | View queued and active jobs |
| `/cancel` | Cancel waiting jobs |
| `/stats` | View processing statistics |

### Owner

| Command | Description |
|---|---|
| `/admin` | View bot and job statistics |
| `/broadcast <message>` | Broadcast a message to registered users |

## Configuration

Create the environment file:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID |
| `API_HASH` | Telegram API hash |
| `BOT_TOKEN` | Telegram bot token |
| `MONGODB_URI` | MongoDB connection string |
| `OWNER_ID` | Telegram owner user ID |
| `TEMP_DOWNLOAD_DIRECTORY` | Temporary working directory |
| `MAX_ARCHIVE_SIZE_MB` | Maximum input archive size |
| `MAX_EXTRACTED_SIZE_MB` | Maximum total extracted size |
| `MAX_EXTRACTED_FILE_MB` | Maximum individual file size |
| `MAX_EXTRACTED_FILES` | Maximum archive members |
| `MAX_COMPRESSION_RATIO` | Maximum compression ratio |
| `MAX_CONCURRENT_JOBS` | Global concurrent job limit |
| `MAX_JOBS_PER_USER` | Per-user job limit |
| `AUTO_DELETE_HOURS` | Temporary cleanup window |
| `PROGRESS_INTERVAL` | Progress update interval |
| `START_IMAGE_URL` | Optional start image |
| `APP_NAME` | Application name |

Never commit real credentials.

## Local Setup

Clone the repository:

```bash
git clone https://github.com/TheJeager/Unzip-bot.git
cd Unzip-bot
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure the environment:

```bash
cp .env.example .env
```

Start the bot:

```bash
python3 -m src
```

## Docker

Build:

```bash
docker build -t unzip-bot .
```

Run:

```bash
docker run --env-file .env unzip-bot
```

The container runs under a dedicated non-root user and uses a proper init process for clean shutdown handling.

## Docker Compose

Start:

```bash
docker compose up -d --build
```

Stop:

```bash
docker compose down
```

Temporary archive data is stored in a dedicated volume.

## Runtime Model

```text
Telegram Handler
       │
       ▼
    JobQueue
   ┌───┼───┐
   ▼   ▼   ▼
 Worker Worker Worker
   │   │   │
   └───┼───┘
       ▼
Secure Extractor
       │
       ▼
Telegram Uploader
```

The global queue controls overall concurrency while per-user limits stop a single account from consuming the entire worker pool.

## Progress

Progress can be reported during:

- Download
- Extraction
- Upload

Updates are throttled to avoid unnecessary Telegram API requests while keeping the status useful.

## Technology

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| Telegram framework | Kurigram 2.2.26 |
| Database driver | PyMongo 4.18.2 |
| Database | MongoDB |
| Concurrency | asyncio |
| Containers | Docker |
| Init process | tini |
| Archive handling | Python standard library + pyzipper |

## Contributing

Contributions and improvements are welcome.

Keep new functionality separated according to the existing project structure so Telegram behavior, archive processing, security, persistence and configuration remain easy to maintain.

## License

See the repository license file for the applicable terms.

---

<div align="center">

**Unzip Bot**

Fast archive processing directly inside Telegram.

</div>
