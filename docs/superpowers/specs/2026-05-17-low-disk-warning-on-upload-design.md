# Low-disk warning at upload start

**Status:** Approved — ready for implementation plan
**Date:** 2026-05-17
**Branch context:** `Enh_add_Mikaela`

## Problem

Bruker client uploads raw imaging data to a ripping-PC server (`brukerbridge/ripping_PC/*_server.py`). When the target drive runs out of space mid-transfer, the upload fails partway through, leaving partial data and forcing a redo with the source data still on the Bruker PC. We want to detect this condition at the *start* of the upload, alert the user, but still let the upload proceed (the user decides whether to abort manually or free space mid-transfer).

## Behavior

When a client connects and announces an upload:

1. Server reads `source_directory_size` (GB) and `total_num_files` from the client — protocol unchanged (`mikaela_server.py:61-62`).
2. Server queries `shutil.disk_usage(target_directory).free` and converts to GB.
3. If `free_gb < source_directory_size + margin`:
   - Print a prominent multi-line console warning (with `flush=True`).
   - Set a `low_disk = True` flag for the current upload session.
4. Server reads the first file's metadata as usual. The first filename's top-level path component is the user folder (`mikaela_server.py:137` already extracts this for the post-transfer rename — we extract earlier).
5. If `low_disk` and the user has `telegram_chat_id` configured → send one Telegram alert via the bot.
6. Upload proceeds normally. No behavior change beyond the warning + notification.

The flag is checked once per upload — we do not re-poll during the transfer.

### Margin

```
margin_gb = max(source_directory_size * 0.10, 50)
```

10% of upload size or 50 GB, whichever is larger. Covers filesystem overhead, FicTrac/jackfish files written in parallel during ripping/conversion, oak-pass-1 staging, and build-queue artifacts.

### Message format

```
⚠️ brukerbridge low disk on <hostname>
User:    Mikaela
Upload:  412 GB, 12,847 files
Free:    280 GB on D:\
Margin:  ~50 GB
Upload proceeding but may fail mid-transfer.
```

Same text goes to the console (with surrounding `!!!!!!!!!` separator lines) and Telegram.

## Components

### `brukerbridge/notify.py` (new)

Small, single-responsibility module. Two functions:

- `load_telegram_config() -> dict | None`
  - Reads `~/.brukerbridge/telegram.json` (i.e. `%USERPROFILE%\.brukerbridge\telegram.json` on Windows) via `pathlib.Path.home() / '.brukerbridge' / 'telegram.json'`.
  - Returns a dict with keys `bot_token` (str) and `chat_ids` (dict[user_name → chat_id_str]), or `None` if the file is missing or malformed.
  - Logs one warning line on malformed JSON and returns `None`.
- `send_telegram(bot_token: str, chat_id: str, text: str) -> bool`
  - POSTs to `https://api.telegram.org/bot<token>/sendMessage` with `{"chat_id": ..., "text": ...}`.
  - Uses `urllib.request` (stdlib — no new dependency).
  - Returns `True` on HTTP 200, `False` otherwise.
  - Swallows network errors (logs to console) — the alert is best-effort; we never want a failed Telegram POST to break an in-progress upload.

### `brukerbridge/disk_check.py` (new)

A single function:

- `check_disk_space(target_directory: pathlib.Path, source_size_gb: float) -> tuple[bool, dict]`
  - Returns `(low_disk, info)` where `info` has `free_gb`, `required_gb`, `margin_gb`, `source_size_gb`, `drive`, `hostname`.
  - Pure — no side effects. Caller decides what to print/send.

New module rather than appending to `brukerbridge/utils.py` because `utils.py` is already large and mixed-purpose.

### Server changes (`*_server.py`, 4 files)

In each of `david_server.py`, `jacob_server.py`, `mikaela_server.py`, `blueprint_server.py`:

- At module load: call `notify.load_telegram_config()` once, keep the dict (or `None`) in a module-level variable.
- Import `check_disk_space`.
- After the existing `source_directory_size = ...` / `total_num_files = ...` reads:
  - Call `check_disk_space`.
  - If low → print warning to console, set `low_disk = True`.
- Inside the file loop, after the first filename arrives and `user_folder` can be derived:
  - If `low_disk` is set and the loaded config has a `chat_ids[user_folder]` entry → call `notify.send_telegram(bot_token, chat_id, message)`.
  - Clear `low_disk` so we only alert once per upload.

The four server files are near-duplicates today. This spec does not include consolidating them — that would be a separate refactor.

## Configuration

### `~/.brukerbridge/telegram.json` (new, outside the repo)

Lives at `%USERPROFILE%\.brukerbridge\telegram.json` on each ripping PC. Resolved via `pathlib.Path.home() / '.brukerbridge' / 'telegram.json'`. Never committed to git — the path is outside the repo tree, so there is nothing to gitignore.

```json
{
  "bot_token": "<bot token from BotFather>",
  "chat_ids": {
    "David": "<chat id>",
    "Mikaela": "<chat id>",
    "Jacob": "<chat id>"
  }
}
```

- `bot_token` is the shared bot. All users pair with the same bot.
- `chat_ids` maps user folder name (matches the per-user folder in `users/`) → Telegram chat_id as string.
- Each ripping PC needs its own copy of this file. One canonical source can live in a password manager / 1Password / lab-shared encrypted store.
- Missing file → Telegram disabled silently, console warning still fires.
- Missing `chat_ids[user]` for an uploading user → that user gets no Telegram, console warning still fires.

### Threat model summary

- **Bot token is a hard secret.** Possession allows impersonation (send messages as the bot), enumeration (call `getUpdates` to list all chats), and bot modification. Treat like a password. If exposed, rotate via BotFather (`/revoke` then `/token`).
- **Chat IDs are low-sensitivity.** Useless without the token. Kept out of the repo as defense-in-depth and for privacy (chat IDs identify the paired Telegram account).
- **No fields land in the in-repo per-user JSONs.** The existing `users/<Name>.json` files (which are tracked in git) are not touched by this feature.

### Pairing flow (one-time per user)

Each user opens Telegram, finds the bot, sends `/start`. The admin runs `https://api.telegram.org/bot<token>/getUpdates`, reads the `chat.id` from the JSON response, and adds it to `chat_ids` in `~/.brukerbridge/telegram.json` on each ripping PC.

## Error handling

- `shutil.disk_usage` raises on bad path → let it propagate (the path is already used downstream; if it's bad, the upload will fail anyway and the existing failure path is clearer than a swallowed exception).
- `urllib.request` network errors → caught inside `send_telegram`, logged, function returns `False`. Upload continues unaffected.
- Missing or malformed `~/.brukerbridge/telegram.json` → caught inside `load_telegram_config`, logged once at server startup, function returns `None`. Console warning still fires on low disk; Telegram is simply skipped.
- Missing `chat_ids[user]` for the uploading user → no-op, no error. Console warning still fires.

## Testing

- **Unit-style sanity check** for `check_disk_space`: pass a fake `source_size_gb` larger than total drive size → expect `low_disk=True`; pass `0` → expect `low_disk=False`.
- **Manual end-to-end:** trigger an upload from the Bruker PC with `source_directory_size` artificially inflated (or against a server pointed at a near-full mount). Confirm console warning appears and Telegram message arrives.
- **Failure modes to manually verify:**
  - `~/.brukerbridge/telegram.json` missing → server starts fine, only console warning fires on low disk.
  - Bot token invalid → `send_telegram` logs an error, upload continues.
  - User missing from `chat_ids` map → no error, console warning still fires.

No new automated tests are introduced; the server scripts have no existing test harness and adding one is out of scope.

## Non-goals

- Hard rejection of uploads. The user explicitly chose warn-and-proceed.
- Re-polling disk space mid-transfer. One check at the start.
- Idle-time monitoring of disk space when no upload is in flight.
- Consolidating the four near-duplicate `*_server.py` files.
- A separate bot per user (single shared bot is simpler and adequate).

## Files touched

| File | Change |
|------|--------|
| `brukerbridge/notify.py` | new — Telegram helper |
| `brukerbridge/disk_check.py` | new — disk-space check helper |
| `brukerbridge/ripping_PC/david_server.py` | add check + alert |
| `brukerbridge/ripping_PC/jacob_server.py` | add check + alert |
| `brukerbridge/ripping_PC/mikaela_server.py` | add check + alert |
| `brukerbridge/ripping_PC/blueprint_server.py` | add check + alert |
| `~/.brukerbridge/telegram.json` | new file on each ripping PC, **outside the repo** — bot token + chat_id map |
| `README.md` | brief note documenting the config path and pairing flow (in-repo, no secrets) |

No in-repo user JSON files are modified by this feature.
