<div align="center">

<a href="https://github.com/TheJeager/Unzip-bot">
  <img src="https://raw.githubusercontent.com/TheJeager/Unzip-bot/main/assets/Unzip-Bot-hero.svg" alt="Unzip-bot animated banner" width="100%">
</a>

<br>

<p>
  <img src="https://img.shields.io/github/stars/TheJeager/Unzip-bot?style=for-the-badge&color=6d7cff&labelColor=080d1d" alt="Stars">
  <img src="https://img.shields.io/github/forks/TheJeager/Unzip-bot?style=for-the-badge&color=5ee7ff&labelColor=080d1d" alt="Forks">
  <img src="https://img.shields.io/github/license/TheJeager/Unzip-bot?style=for-the-badge&color=9defff&labelColor=080d1d" alt="License">
  <img src="https://img.shields.io/github/actions/workflow/status/TheJeager/Unzip-bot/ci.yml?style=for-the-badge&label=CI&color=6d7cff&labelColor=080d1d" alt="CI">
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Telethon-1.45.0-2CA5E0?style=flat-square&logo=telegram&logoColor=white" alt="Telethon">
  <img src="https://img.shields.io/badge/PyMongo-4.18.2-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="PyMongo">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

<h3>Secure Telegram Archive Extraction, Built for Speed.</h3>

<p><b>ArchiveX</b> turns Telegram into a clean, secure archive-processing pipeline with asynchronous workers, live progress, hardened extraction and optional MongoDB persistence.</p>

</div>

---

## ✦ Overview

ArchiveX is a modular Telegram bot designed for reliable archive extraction without turning the codebase into a monolithic script.

It validates an incoming archive before extraction, places work into an asynchronous queue, processes members individually, uploads the resulting files and cleans temporary data after completion.

The visual direction takes inspiration from the cool blue, high-contrast anime aesthetic commonly associated with Satoru Gojo: white highlights, deep navy backgrounds, cyan energy and restrained glow, while keeping the project artwork itself original.

> The hero is an original animated SVG created for ArchiveX rather than copied character artwork.

## ⚡ Why ArchiveX?

| Capability | ArchiveX |
|---|:---:|
| Async job queue | ✓ |
| Per-user concurrency control | ✓ |
| Live transfer progress | ✓ |
| Secure path validation | ✓ |
| Symlink rejection | ✓ |
| Special-file rejection | ✓ |
| Compression-ratio protection | ✓ |
| Expanded-size limits | ✓ |
| Per-file limits | ✓ |
| ZIP + TAR-family support | ✓ |
| MongoDB persistence | Optional |
| Docker deployment | ✓ |
| Non-root container | ✓ |
| Python module startup | ✓ |

## 📦 Supported Archives

~~~text
ZIP
TAR
TAR.GZ / TGZ
TAR.BZ2 / TBZ2
TAR.XZ / TXZ
~~~

Archive handling is performed member-by-member instead of blindly extracting an entire archive tree.

## 🛡️ Security First

Archive extraction is an untrusted-input problem. ArchiveX applies multiple independent checks before and during extraction:

- Path traversal protection
- Normalized archive member paths
- Symlink rejection
- Hard-link rejection for TAR archives
- Device/FIFO/socket rejection
- Maximum archive size
- Maximum expanded size
- Maximum individual file size
- Maximum file count
- Maximum compression ratio
- Duplicate member detection
- Final output-tree validation
- Automatic temporary-directory cleanup

MongoDB never receives the archive payload itself. When persistence is enabled, it stores user preferences, job metadata and aggregate counters.

## 🧠 Processing Pipeline

~~~text
Telegram Document
       │
       ▼
┌───────────────────┐
│ Format Detection  │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Security Inspect  │
│ Size / Ratio /    │
│ Path / File Rules │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Async Job Queue   │
│ Global + Per User │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Secure Extraction │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Telegram Upload   │
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Cleanup + Metrics │
└───────────────────┘
~~~

## 🏗️ Architecture

~~~text
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
│   └── archivex-hero.svg
├── Dockerfile
├── compose.yaml
├── requirements.txt
└── .env.example
~~~

### Design principles

- **Plugins own Telegram behavior**
- **Utils own processing logic**
- **Handlers own security, progress and formatting**
- **Database modules own persistence**
- **Bot bootstrap stays small**
- **Configuration stays environment-driven**
- **Archive data stays outside MongoDB**

## 🎛️ Commands

### User

| Command | Purpose |
|---|---|
| <code>/start</code> | Open the ArchiveX control panel |
| <code>/help</code> | View supported formats and limits |
| <code>/settings</code> | Configure user preferences |
| <code>/queue</code> | View active and waiting jobs |
| <code>/cancel</code> | Cancel waiting jobs |
| <code>/stats</code> | View aggregate processing counters |

### Owner

| Command | Purpose |
|---|---|
| <code>/admin</code> | View users, queue and job counters |
| <code>/broadcast &lt;message&gt;</code> | Broadcast to registered users |

## ⚙️ Configuration

Create a local environment file from the included template:

~~~bash
cp .env.example .env
~~~

| Variable | Purpose |
|---|---|
| <code>API_ID</code> | Telegram API ID |
| <code>API_HASH</code> | Telegram API hash |
| <code>BOT_TOKEN</code> | Telegram bot token |
| <code>MONGODB_URI</code> | Optional MongoDB connection |
| <code>OWNER_ID</code> | Owner Telegram user ID |
| <code>MAX_ARCHIVE_SIZE_MB</code> | Maximum input archive size |
| <code>MAX_EXTRACTED_SIZE_MB</code> | Maximum expanded data |
| <code>MAX_EXTRACTED_FILE_MB</code> | Maximum individual file size |
| <code>MAX_EXTRACTED_FILES</code> | Maximum archive members |
| <code>MAX_COMPRESSION_RATIO</code> | Maximum allowed compression ratio |
| <code>MAX_CONCURRENT_JOBS</code> | Global worker count |
| <code>MAX_JOBS_PER_USER</code> | Per-user job limit |
| <code>AUTO_DELETE_HOURS</code> | Temporary message cleanup window |
| <code>PROGRESS_INTERVAL</code> | Progress update interval |

Never commit real credentials to Git.

## 🚀 Local Development

### 1. Clone

~~~bash
git clone https://github.com/TheJeager/Unzip-bot.git
cd Unzip-bot
~~~

### 2. Install

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

### 3. Configure

~~~bash
cp .env.example .env
~~~

Fill in the required Telegram values.

### 4. Start

~~~bash
python3 -m src
~~~

## 🐳 Docker

Build:

~~~bash
docker build -t archivex .
~~~

Run:

~~~bash
docker run --env-file .env archivex
~~~

The image runs as a dedicated non-root user and uses <code>tini</code> as the container init process.

## 🧩 Docker Compose

~~~bash
docker compose up -d --build
~~~

Stop:

~~~bash
docker compose down
~~~

## 📊 Runtime Model

ArchiveX separates Telegram event handling from archive processing.

~~~text
Telegram Event
      │
      ▼
Archive Plugin
      │
      ▼
JobQueue
 ┌────┼────┐
 ▼    ▼    ▼
Worker Worker Worker
 │      │      │
 └──────┼──────┘
        ▼
Secure Extractor
        │
        ▼
Telegram Uploader
~~~

A per-user semaphore prevents one account from consuming the entire worker pool while the global queue controls total concurrency.

## 🧹 Temporary Data Lifecycle

Each job receives an isolated temporary workspace:

~~~text
temp_downloads/
└── <job-id>/
    ├── archive
    └── output/
        ├── file-a
        ├── file-b
        └── ...
~~~

The workspace is removed automatically when processing finishes, including failure paths handled by the job lifecycle.

## 📈 Progress Reporting

ArchiveX reports progress for:

- Download
- Extraction
- Upload

The reporter throttles Telegram message edits to avoid unnecessary API traffic while keeping the UI responsive.

## 🔧 Technology Stack

| Layer | Technology |
|---|---|
| Bot framework | Telethon 1.45.0 |
| Runtime | Python 3.14 |
| Database | PyMongo Async 4.18.2 |
| Database server | MongoDB |
| Container | Docker |
| Init process | tini |
| Archive engines | Python standard library |
| Configuration | Environment variables |
| Concurrency | asyncio |

## 📜 License

See the repository license file for the terms applicable to this project.

---

<div align="center">

### ArchiveX

**Secure archives. Async workers. Clean Telegram UX.**

<sub>Built for reliability, security and maintainability.</sub>

</div>
