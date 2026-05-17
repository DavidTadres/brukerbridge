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
