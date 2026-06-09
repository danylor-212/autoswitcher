# appconfig.py — config persistence done safely.
#
# V1 kept config.json next to the exe (read-only under Program Files) and
# wrote it truncate-mode from three threads concurrently (listener, Tk, tray)
# — a torn write corrupted it and silently reset every setting. V2:
#   - lives in %APPDATA%/AutoSwitcher (XDG/home fallback off-Windows)
#   - atomic writes: temp file + os.replace, serialized by a lock
#   - migrates a v1 exe-dir config on first run

import json
import os
import sys
import tempfile
import threading

_lock = threading.Lock()

DEFAULTS = {
    'enabled':               True,
    'switch_en_to_uk':       True,
    'switch_uk_to_en':       True,
    't9_eng':                False,
    't9_ukr':                False,
    'whitelist':             [],      # canonical physical-key (EN-char) form
    'notifications_enabled': True,
    'disabled_apps':         [],
    'correction_count':      0,
    'correction_date':       '',
    'layout_variant':        'standard',
    'revert_shortcut':       'alt+2',
    'correct_on_enter':      False,   # chat apps submit on Enter — unsafe
    'correct_on_tab':        False,   # forms move focus on Tab — unsafe
}


def config_dir() -> str:
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or os.path.expanduser('~')
        return os.path.join(base, 'AutoSwitcher')
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, 'autoswitcher')


def config_path() -> str:
    return os.path.join(config_dir(), 'config.json')


def _legacy_path() -> str:
    """v1 location: next to the exe / source dir."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'config.json')


def load(path: str = None) -> dict:
    """Load config merged over defaults. Migrates a v1 file if present."""
    path = path or config_path()
    data = dict(DEFAULTS)
    src = path if os.path.exists(path) else _legacy_path()
    try:
        with open(src, encoding='utf-8') as f:
            on_disk = json.load(f)
        for key in DEFAULTS:
            if key in on_disk:
                data[key] = on_disk[key]
    except (OSError, ValueError):
        pass
    return data


def save(data: dict, path: str = None):
    """Atomic write: serialize to a temp file, then os.replace into place."""
    path = path or config_path()
    payload = {k: data[k] for k in DEFAULTS if k in data}
    with _lock:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
