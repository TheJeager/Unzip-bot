# ArchiveX

A production-oriented Telegram archive extraction bot built with Telethon, MongoDB and a security-first extraction pipeline.

## Highlights

- ZIP and TAR-family extraction
- Secure path validation
- Symlink and special-file rejection
- Archive, expanded-size, per-file, file-count and compression-ratio limits
- Async worker queue with global and per-user concurrency controls
- Live download, extraction and upload progress
- MongoDB-backed users, jobs and operational statistics
- Persistent auto-delete preference
- Owner controls and broadcast support
- Clean src package architecture
- Non-root Docker image
- Python 3.14 runtime
- Graceful queue and database shutdown

## Commands

/start — Main control panel
/help — Detailed help center
/settings — User preferences
/stats — Operational statistics
/queue — Queue status
/cancel — Cancel waiting jobs
/admin — Owner panel
/broadcast <text> — Owner announcement
/maintenance — Maintenance status

## Supported archives

ZIP
TAR
TAR.GZ
TGZ
TAR.BZ2
TBZ2
TAR.XZ
TXZ

## Security

The extraction engine rejects traversal paths, symbolic links, hard links, device files, FIFOs and sockets. It also enforces archive size, expanded size, per-file size, file-count and compression-ratio limits.

## Run

pip install -r requirements.txt
python3 -m src

## Docker

docker build -t archivex .
docker run --env-file sample.env archivex

## Environment

Configure API_ID, API_HASH and BOT_TOKEN. MongoDB enables persistent preferences, job metadata and aggregate statistics. OWNER_ID and LOG_GROUP_ID are optional.

Archive and queue limits are configurable with environment variables.
