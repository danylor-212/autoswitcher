# winapi.py — thin Win32 helpers. Every function degrades safely off-Windows
# (returns a neutral value) so the pipeline and tests run anywhere.

import ctypes

try:
    _user32   = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _psapi    = ctypes.windll.psapi
    WIN32 = True
except AttributeError:
    WIN32 = False

_LANG_UK = 0x0422
# All English primary-language IDs (US, UK, AU, CA, ...) share primary id 0x09.
_PRIMARY_EN = 0x09


def foreground_hwnd() -> int:
    if not WIN32:
        return 0
    try:
        return _user32.GetForegroundWindow()
    except Exception:
        return 0


def layout_of_foreground() -> str:
    """'EN', 'UK', or 'unknown' for the foreground window's input layout."""
    if not WIN32:
        return 'unknown'
    try:
        hwnd = _user32.GetForegroundWindow()
        tid  = _user32.GetWindowThreadProcessId(hwnd, None)
        lang = _user32.GetKeyboardLayout(tid) & 0xFFFF
        if lang == _LANG_UK:
            return 'UK'
        if lang & 0x3FF == _PRIMARY_EN:
            return 'EN'
        return 'unknown'
    except Exception:
        return 'unknown'


def foreground_app() -> str:
    """Lowercase exe name of the foreground process, or '' on failure."""
    if not WIN32:
        return ''
    try:
        hwnd = _user32.GetForegroundWindow()
        pid  = ctypes.c_ulong(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        hproc = _kernel32.OpenProcess(0x0410, False, pid.value)
        if not hproc:
            return ''
        try:
            buf = ctypes.create_unicode_buffer(260)
            _psapi.GetModuleBaseNameW(hproc, None, buf, ctypes.c_ulong(260))
            return buf.value.lower()
        finally:
            _kernel32.CloseHandle(hproc)
    except Exception:
        return ''


def caps_lock_on() -> bool:
    if not WIN32:
        return False
    try:
        return bool(_user32.GetKeyState(0x14) & 1)
    except Exception:
        return False
