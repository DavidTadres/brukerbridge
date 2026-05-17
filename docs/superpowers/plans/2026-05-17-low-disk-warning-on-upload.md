# Low-disk warning at upload start — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect insufficient disk space when a client announces an upload, print a loud console warning, and send a per-user Telegram alert. The upload proceeds regardless — this is a notification-only feature.

**Architecture:** Two small new modules (`brukerbridge/disk_check.py`, `brukerbridge/notify.py`) plus identical inline edits to each of the four `*_server.py` files. Telegram config (bot token + chat_id map) lives at `~/.brukerbridge/telegram.json`, outside the repo.

**Tech Stack:** Python stdlib only — `shutil.disk_usage`, `urllib.request`, `pathlib`, `json`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-17-low-disk-warning-on-upload-design.md`

---

## File map

| Path | Status | Responsibility |
|---|---|---|
| `brukerbridge/disk_check.py` | new | Pure function — compute whether free space < source + margin |
| `brukerbridge/notify.py` | new | Load Telegram config from `~/.brukerbridge/telegram.json` and send messages |
| `brukerbridge/ripping_PC/mikaela_server.py` | modify | Call disk check + alert at upload start |
| `brukerbridge/ripping_PC/david_server.py` | modify | Same as mikaela |
| `brukerbridge/ripping_PC/jacob_server.py` | modify | Same as mikaela |
| `brukerbridge/ripping_PC/blueprint_server.py` | modify | Same as mikaela |
| `README.md` | modify | Document `~/.brukerbridge/telegram.json` path and pairing flow |

---

### Task 1: Create `brukerbridge/disk_check.py`

**Files:**
- Create: `brukerbridge/disk_check.py`

- [ ] **Step 1: Write the module with smoke assertions in `__main__`**

```python
"""Pre-upload disk-space check for the ripping server.

Pure function — no side effects, no logging. The caller decides what to do
with the result (print warnings, send notifications, etc.).
"""
import pathlib
import shutil
import socket


def check_disk_space(target_directory, source_size_gb):
    """Compare free space on the target drive against announced upload size.

    Returns (low_disk, info) where:
        low_disk: bool. True if free_gb < source_size_gb + margin_gb.
        info: dict with keys free_gb, required_gb, margin_gb,
              source_size_gb, drive, hostname.
    """
    target = pathlib.Path(target_directory)
    usage = shutil.disk_usage(target)
    free_gb = usage.free / 1e9
    margin_gb = max(source_size_gb * 0.10, 50.0)
    required_gb = source_size_gb + margin_gb
    drive = target.anchor or str(target)
    info = {
        'free_gb': free_gb,
        'required_gb': required_gb,
        'margin_gb': margin_gb,
        'source_size_gb': source_size_gb,
        'drive': drive,
        'hostname': socket.gethostname(),
    }
    return (free_gb < required_gb, info)


if __name__ == '__main__':
    # Smoke test: zero-size upload must always fit; impossibly large upload
    # must always fail.
    target = pathlib.Path.home()
    low, info = check_disk_space(target, 0)
    print('source_size=0 GB:  ', 'LOW' if low else 'OK ', info)
    assert not low, 'Expected OK for zero-size upload'
    low, info = check_disk_space(target, 10**9)  # 1 billion GB
    print('source_size=1e9 GB:', 'LOW' if low else 'OK ', info)
    assert low, 'Expected LOW for impossible upload size'
    print('disk_check smoke test passed.')
```

- [ ] **Step 2: Run the smoke test**

```bash
python -m brukerbridge.disk_check
```

Expected output (drive letter and free_gb will differ):
```
source_size=0 GB:   OK  {'free_gb': ..., 'required_gb': 50.0, 'margin_gb': 50.0, 'source_size_gb': 0, 'drive': 'C:\\', 'hostname': '...'}
source_size=1e9 GB: LOW {'free_gb': ..., 'required_gb': 1100000000.0, ...}
disk_check smoke test passed.
```

If either assertion fires, fix the function before moving on.

- [ ] **Step 3: Commit**

```bash
git add brukerbridge/disk_check.py
git commit -m "Add disk_check.check_disk_space() helper

Pure function comparing free space on the target drive against an
announced upload size plus a margin of max(10%, 50 GB). Used by the
ripping server's pre-upload check.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: Create `brukerbridge/notify.py`

**Files:**
- Create: `brukerbridge/notify.py`

- [ ] **Step 1: Write the module**

```python
"""Telegram notification helper for the ripping server.

Best-effort: any failure (missing config, bad JSON, network error, bad token)
is logged to console and swallowed. We never raise to the caller; the
upload must continue regardless of notification success.

Config file (outside the repo, one per ripping PC):
    ~/.brukerbridge/telegram.json
    {
      "bot_token": "...",
      "chat_ids": {"David": "...", "Mikaela": "...", "Jacob": "..."}
    }
"""
import json
import pathlib
import urllib.error
import urllib.parse
import urllib.request


CONFIG_PATH = pathlib.Path.home() / '.brukerbridge' / 'telegram.json'
API_TIMEOUT_SEC = 10


def load_telegram_config():
    """Read the config file. Return dict or None if missing/invalid.

    Logs one warning line on malformed JSON; silent on missing file.
    """
    if not CONFIG_PATH.is_file():
        return None
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print('!!! could not read {}: {}'.format(CONFIG_PATH, e), flush=True)
        return None
    if not isinstance(data, dict) or not data.get('bot_token'):
        print('!!! {} missing bot_token'.format(CONFIG_PATH), flush=True)
        return None
    data.setdefault('chat_ids', {})
    return data


def send_telegram(bot_token, chat_id, text):
    """POST a message to a Telegram chat. Returns True on HTTP 200, else False.

    Best-effort: network and HTTP errors are caught and logged.
    """
    url = 'https://api.telegram.org/bot{}/sendMessage'.format(bot_token)
    body = urllib.parse.urlencode({'chat_id': chat_id, 'text': text}).encode()
    req = urllib.request.Request(url, data=body)
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_SEC) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError) as e:
        print('!!! Telegram send failed: {}'.format(e), flush=True)
        return False


def send_low_disk_alert(config, user_folder, disk_info, num_files):
    """Build and send the low-disk message for one user.

    No-op (returns False) if config is None or the user has no chat_id.
    """
    if config is None:
        return False
    chat_id = config.get('chat_ids', {}).get(user_folder)
    if not chat_id:
        return False
    text = (
        u'⚠️ brukerbridge low disk on {hostname}\n'
        'User:    {user}\n'
        'Upload:  {size:.1f} GB, {nfiles:,} files\n'
        'Free:    {free:.1f} GB on {drive}\n'
        'Margin:  {margin:.0f} GB\n'
        'Upload proceeding but may fail mid-transfer.'
    ).format(
        hostname=disk_info['hostname'],
        user=user_folder,
        size=disk_info['source_size_gb'],
        nfiles=num_files,
        free=disk_info['free_gb'],
        drive=disk_info['drive'],
        margin=disk_info['margin_gb'],
    )
    return send_telegram(config['bot_token'], chat_id, text)


if __name__ == '__main__':
    cfg = load_telegram_config()
    if cfg is None:
        print('No telegram config at {} - nothing to test.'.format(CONFIG_PATH))
        print('Create the file (see module docstring) and re-run to send a test message.')
    else:
        print('Loaded config from {}. chat_ids: {}'.format(
            CONFIG_PATH, list(cfg['chat_ids'].keys())))
        if cfg['chat_ids']:
            user = next(iter(cfg['chat_ids']))
            ok = send_telegram(cfg['bot_token'], cfg['chat_ids'][user],
                               'brukerbridge notify.py smoke test')
            print('Sent to {}: {}'.format(user, 'OK' if ok else 'FAILED'))
        else:
            print('No chat_ids configured; skipped send test.')
```

- [ ] **Step 2: Run the module with no config present (verifies graceful degradation)**

```bash
python -m brukerbridge.notify
```

Expected output (when the config file doesn't exist yet):
```
No telegram config at C:\Users\<you>\.brukerbridge\telegram.json - nothing to test.
Create the file (see module docstring) and re-run to send a test message.
```

No traceback, no error. If you get a traceback, fix the module before proceeding.

- [ ] **Step 3: Commit**

```bash
git add brukerbridge/notify.py
git commit -m "Add notify module for Telegram alerts

load_telegram_config reads ~/.brukerbridge/telegram.json (outside repo).
send_telegram POSTs to api.telegram.org using urllib (no new deps).
send_low_disk_alert formats and sends the low-disk message for one user.
All functions are best-effort: errors are logged and swallowed so a
failed notification never breaks an in-progress upload.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: Set up the Telegram config file and verify end-to-end send

**This task does not produce a commit.** It produces a file on your machine, outside the repo.

- [ ] **Step 1: Create `~/.brukerbridge/telegram.json`**

PowerShell:
```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.brukerbridge" | Out-Null
```

Then create `%USERPROFILE%\.brukerbridge\telegram.json` with this content (fill in your real values):

```json
{
  "bot_token": "<paste bot token from BotFather>",
  "chat_ids": {
    "David": "<paste chat_id>"
  }
}
```

**Where to get the values:**
- `bot_token`: copy from `%USERPROFILE%\.claude\channels\telegram\.env` (line `TELEGRAM_BOT_TOKEN=...`) — or get a fresh one from BotFather (`/newbot` or `/token`).
- chat_id for yourself: open Telegram, find the bot, send `/start`. Then in a browser visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and read the `chat.id` field from the JSON response.

- [ ] **Step 2: Run notify.py to send a real test message**

```bash
python -m brukerbridge.notify
```

Expected output:
```
Loaded config from C:\Users\<you>\.brukerbridge\telegram.json. chat_ids: ['David']
Sent to David: OK
```

You should receive a Telegram message: `brukerbridge notify.py smoke test`. If `FAILED`, check that the bot_token is current and that you sent `/start` to the bot.

- [ ] **Step 3: Add chat_ids for other users (optional, can be done later)**

For each user who should receive their own alerts: have them send `/start` to the bot, fetch their chat_id via `getUpdates`, add an entry to the `chat_ids` map. Per-user pairing can be done lazily as users join.

---

### Task 4: Wire the check into `mikaela_server.py` (pilot)

This is the file where the low-disk bug bit. Get this one working end-to-end before propagating.

**Files:**
- Modify: `brukerbridge/ripping_PC/mikaela_server.py`

- [ ] **Step 1: Add imports at the top**

Find the existing import block at the top of `mikaela_server.py` (around lines 1-17). Add the new imports right after `from brukerbridge import utils`:

```python
from brukerbridge import utils
from brukerbridge import disk_check, notify  # <-- NEW
```

- [ ] **Step 2: Load the Telegram config once at module level**

Just after the imports, before the `verbose = False` line, add:

```python
# Load Telegram alert config once at startup. None if not configured.
TELEGRAM_CONFIG = notify.load_telegram_config()
if TELEGRAM_CONFIG is None:
    print('No telegram config at {} - Telegram alerts disabled.'.format(
        notify.CONFIG_PATH), flush=True)
else:
    print('Telegram alerts enabled for: {}'.format(
        list(TELEGRAM_CONFIG.get('chat_ids', {}).keys())), flush=True)
```

- [ ] **Step 3: Initialize low-disk state inside the per-upload block**

Find the lines that initialize per-upload counters (around lines 48-50):

```python
		do_checksums_match = []
		num_files_transfered = 0
		total_gb_transfered = 0
```

Add two lines immediately after them:

```python
		do_checksums_match = []
		num_files_transfered = 0
		total_gb_transfered = 0
		low_disk = False           # <-- NEW
		disk_info = None           # <-- NEW
```

- [ ] **Step 4: Run the disk check after `source_directory_size` is read**

Find the block that reads `source_directory_size` and `total_num_files` (around lines 60-64):

```python
				if num_files_transfered == 0:
					source_directory_size = int(float(clientfile.readline().strip().decode()))
					total_num_files = int(clientfile.readline().strip().decode())
					start_time = time.time()
					print(F"FIRST LOOP START TIME: {start_time}",flush=True)
```

Add a disk-check block immediately after the `FIRST LOOP START TIME` print, still inside the `if num_files_transfered == 0:` block:

```python
				if num_files_transfered == 0:
					source_directory_size = int(float(clientfile.readline().strip().decode()))
					total_num_files = int(clientfile.readline().strip().decode())
					start_time = time.time()
					print(F"FIRST LOOP START TIME: {start_time}",flush=True)

					# Pre-upload disk-space check
					low_disk, disk_info = disk_check.check_disk_space(
						target_directory, source_directory_size)
					if low_disk:
						print('!' * 60, flush=True)
						print('!!! LOW DISK SPACE on {} ({})'.format(
							disk_info['drive'], disk_info['hostname']), flush=True)
						print('!!! upload: {:.1f} GB, {:,} files'.format(
							source_directory_size, total_num_files), flush=True)
						print('!!! free:   {:.1f} GB; need {:.1f} GB (margin {:.0f} GB)'.format(
							disk_info['free_gb'], disk_info['required_gb'],
							disk_info['margin_gb']), flush=True)
						print('!!! upload will proceed but may fail mid-transfer.', flush=True)
						print('!' * 60, flush=True)
```

- [ ] **Step 5: Send the Telegram alert when the first filename arrives**

Find the line that parses the first filename (around line 77):

```python
				filename = raw.strip().decode()
```

Add an alert block immediately after it:

```python
				filename = raw.strip().decode()

				# Send Telegram alert once, on the first file, only if low_disk
				if low_disk and num_files_transfered == 0:
					user_folder = pathlib.Path(filename).parts[0]
					notify.send_low_disk_alert(
						TELEGRAM_CONFIG, user_folder, disk_info, total_num_files)
					low_disk = False  # one alert per upload
```

- [ ] **Step 6: Sanity-check syntax**

```bash
python -m py_compile brukerbridge/ripping_PC/mikaela_server.py
```

Expected: no output, exit code 0. If you get a `SyntaxError`, fix the indentation (the file uses **tabs**, not spaces — match what's already there).

- [ ] **Step 7: Verify the imports resolve**

```bash
python -c "import sys; sys.path.insert(0, '.'); from brukerbridge import disk_check, notify; print('OK')"
```

Expected output: `OK`. If `ModuleNotFoundError`, you ran this from the wrong directory — `cd` to the repo root first.

- [ ] **Step 8: Commit**

```bash
git add brukerbridge/ripping_PC/mikaela_server.py
git commit -m "Add low-disk warning to mikaela_server

After client announces source_directory_size, check free space on the
target drive. If insufficient, print loud console warning. After first
filename arrives, send per-user Telegram alert. Upload proceeds either
way (warn-and-accept).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: End-to-end verification on Mikaela's server

Run a real upload against the modified server before propagating to the other three files.

- [ ] **Step 1: Start the Mikaela server**

```bash
python brukerbridge/ripping_PC/mikaela_server.py
```

Expected startup output includes:
```
Telegram alerts enabled for: ['David']
[*] Listening as 0.0.0.0:5005
[*] Ready to receive files from Bruker client
```

If you see `Telegram alerts disabled`, the config file is missing — revisit Task 3.

- [ ] **Step 2: Trigger an upload that should NOT trip the low-disk threshold**

Have the Bruker client send a small upload (or any normal-size upload that comfortably fits). Expected: no `LOW DISK SPACE` banner, no Telegram message, upload completes normally.

- [ ] **Step 3: Trigger an upload that SHOULD trip the threshold**

Two options:
- **Real low-disk:** point `target_directory` at a drive with less than `(upload_size + 50 GB)` free.
- **Fake low-disk:** temporarily edit `mikaela_server.py` to add `source_directory_size += 10**12` just after it's read, then run any upload. **Revert this edit before commit.**

Expected console output during the upload:
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! LOW DISK SPACE on D:\ (RIPPING-PC)
!!! upload: 412.0 GB, 12,847 files
!!! free:   280.0 GB; need 462.0 GB (margin 50 GB)
!!! upload will proceed but may fail mid-transfer.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

Expected Telegram message to David's chat:
```
⚠️ brukerbridge low disk on RIPPING-PC
User:    Mikaela
Upload:  412.0 GB, 12,847 files
Free:    280.0 GB on D:\
Margin:  50 GB
Upload proceeding but may fail mid-transfer.
```

- [ ] **Step 4: Confirm the alert fires only once per upload**

Watch the console as more files transfer. The `LOW DISK SPACE` banner must NOT repeat. Only one Telegram message should arrive on your phone.

- [ ] **Step 5: Revert any test-only edits (e.g. the fake `source_directory_size +=`)**

```bash
git diff brukerbridge/ripping_PC/mikaela_server.py
```

Expected: no diff (commit `git status` clean). If there's a diff, you forgot to remove the test edit — revert it before the next task.

---

### Task 6: Propagate to `david_server.py`, `jacob_server.py`, `blueprint_server.py`

The three remaining server files are near-duplicates of `mikaela_server.py`. Apply the same five edits to each.

**Files (apply same changes to all three):**
- Modify: `brukerbridge/ripping_PC/david_server.py`
- Modify: `brukerbridge/ripping_PC/jacob_server.py`
- Modify: `brukerbridge/ripping_PC/blueprint_server.py`

For each of the three files, apply edits 1–5 from Task 4:

- [ ] **Step 1: In each file, add imports near `from brukerbridge import utils`**

```python
from brukerbridge import disk_check, notify
```

- [ ] **Step 2: In each file, add module-level config load**

After the imports block, before any other top-level statements:

```python
TELEGRAM_CONFIG = notify.load_telegram_config()
if TELEGRAM_CONFIG is None:
    print('No telegram config at {} - Telegram alerts disabled.'.format(
        notify.CONFIG_PATH), flush=True)
else:
    print('Telegram alerts enabled for: {}'.format(
        list(TELEGRAM_CONFIG.get('chat_ids', {}).keys())), flush=True)
```

- [ ] **Step 3: In each file, initialize `low_disk` and `disk_info` next to `do_checksums_match = []`**

```python
		low_disk = False
		disk_info = None
```

- [ ] **Step 4: In each file, add the disk-check block inside `if num_files_transfered == 0:`**

(Same code as Task 4 Step 4 — copy verbatim.)

```python
					low_disk, disk_info = disk_check.check_disk_space(
						target_directory, source_directory_size)
					if low_disk:
						print('!' * 60, flush=True)
						print('!!! LOW DISK SPACE on {} ({})'.format(
							disk_info['drive'], disk_info['hostname']), flush=True)
						print('!!! upload: {:.1f} GB, {:,} files'.format(
							source_directory_size, total_num_files), flush=True)
						print('!!! free:   {:.1f} GB; need {:.1f} GB (margin {:.0f} GB)'.format(
							disk_info['free_gb'], disk_info['required_gb'],
							disk_info['margin_gb']), flush=True)
						print('!!! upload will proceed but may fail mid-transfer.', flush=True)
						print('!' * 60, flush=True)
```

- [ ] **Step 5: In each file, add the Telegram-alert block right after `filename = raw.strip().decode()`**

```python
				if low_disk and num_files_transfered == 0:
					user_folder = pathlib.Path(filename).parts[0]
					notify.send_low_disk_alert(
						TELEGRAM_CONFIG, user_folder, disk_info, total_num_files)
					low_disk = False
```

- [ ] **Step 6: Verify all three files compile**

```bash
python -m py_compile brukerbridge/ripping_PC/david_server.py brukerbridge/ripping_PC/jacob_server.py brukerbridge/ripping_PC/blueprint_server.py
```

Expected: no output, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add brukerbridge/ripping_PC/david_server.py brukerbridge/ripping_PC/jacob_server.py brukerbridge/ripping_PC/blueprint_server.py
git commit -m "Propagate low-disk warning to other server variants

Same change as mikaela_server: import disk_check/notify, load config
once at startup, run the free-space check after source_directory_size
is announced, and send a per-user Telegram alert on the first file.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Document the Telegram config in the README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate a good insertion point**

```bash
grep -n -E '^#|^##' README.md | head -30
```

Pick a sensible section (e.g. just before "Architecture" or "Onboarding"). If there's an obvious "Configuration" or "Setup" section, append to that.

- [ ] **Step 2: Add a new subsection**

Insert this block at the chosen location:

```markdown
### Telegram alerts on low disk (optional)

The ripping server can send a Telegram message when an inbound upload looks like it won't fit on the target drive. The upload proceeds either way — this is a warning, not a hard gate.

**Config file** (per ripping PC, outside the repo):

`%USERPROFILE%\.brukerbridge\telegram.json` (Windows) or `~/.brukerbridge/telegram.json` (Linux/Mac):

```json
{
  "bot_token": "<bot token from BotFather>",
  "chat_ids": {
    "David": "<chat id>",
    "Mikaela": "<chat id>"
  }
}
```

**Pairing a new user:**

1. User opens Telegram and sends `/start` to the bot.
2. Admin visits `https://api.telegram.org/bot<TOKEN>/getUpdates` and reads the `chat.id` field from the JSON response.
3. Admin adds an entry to `chat_ids` in `~/.brukerbridge/telegram.json` on each ripping PC.

If the config file is missing, alerts are silently disabled and only the console warning fires. The token is a hard secret — keep it out of the repo and rotate via BotFather (`/revoke` then `/token`) if it leaks.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Document Telegram low-disk alert config in README

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Final smoke test on the propagated servers

- [ ] **Step 1: Start one of the other server variants (e.g. david_server.py)**

```bash
python brukerbridge/ripping_PC/david_server.py
```

Expected: startup prints `Telegram alerts enabled for: [...]` (assuming the config has at least one chat_id).

- [ ] **Step 2: Trigger one normal upload, one low-disk upload**

Same as Task 5 steps 2–3, but against `david_server` (or whichever variant you chose). Confirm console warning + Telegram alert both fire on low-disk; neither fires on normal.

- [ ] **Step 3: Confirm the existing oak-transfer / ripping pipeline still works**

After the upload, the server should rename the folder to `__queue__` exactly as before. `queue_watcher.py` should pick it up and run main.py. Verify by checking that ripping starts as usual.

If anything in the existing pipeline is broken, revert Task 6's commit and re-investigate — the changes are purely additive and must not affect the existing flow.

---

## Done when

- All eight tasks have been completed and committed (Tasks 3, 5, 8 do not produce commits — those are config and verification only).
- Mikaela's server and at least one other variant have been manually verified end-to-end: normal upload silent, low-disk upload triggers console banner + Telegram message.
- The Telegram config file exists on at least one ripping PC, outside the repo.
- The README documents the config path and pairing flow.
- No secrets land in any git commit.
