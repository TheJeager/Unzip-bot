# ArchiveX

A production-oriented Telegram archive extraction bot built with Telethon, PyMongo Async and an async worker queue.

## Features

- ZIP, TAR, TAR.GZ, TGZ, TAR.BZ2, TBZ2, TAR.XZ and TXZ
- Secure path validation
- Symbolic-link and special-file rejection
- Archive, expanded-size, file-count, per-file and compression-ratio limits
- Global and per-user async queue limits
- Live download, extraction and upload progress
- Temporary-file cleanup
- Optional MongoDB persistence using PyMongo Async
- Owner statistics and broadcast tools
- Non-root Docker runtime
- `python3 -m src` startup

## Commands

`/start` control panel
`/help` help and limits
`/settings` preferences
`/queue` queue status
`/cancel` cancel waiting jobs
`/stats` aggregate counters
`/admin` owner panel
`/broadcast <message>` owner broadcast

## Setup

Copy `.env.example` to `.env`, fill in the Telegram credentials and optionally add MongoDB.

```bash
pip install -r requirements.txt
python3 -m src
```

## Docker

```bash
docker build -t archivex .
docker run --env-file .env archivex
```

## Compose

```bash
docker compose up -d --build
```

## Security

Archive contents are not stored in MongoDB. Extraction writes members individually after validation, rejects unsafe paths and special entries, and removes temporary working data after every job.
