# injector.py — atomic text replacement via one batched SendInput call.
#
# Every event we inject is tagged with MAGIC_EXTRA in dwExtraInfo so our own
# events are positively identifiable (pynput >= 1.8 also reports the
# LLKHF_INJECTED flag, which the pipeline filters on). Batching the whole
# correction into a single SendInput array makes it effectively atomic with
# respect to other input — no sleeps, no interleaving with user keystrokes.

import ctypes
import ctypes.wintypes as wintypes

MAGIC_EXTRA = 0xA5C0DE

_KEYEVENTF_UNICODE = 0x0004
_KEYEVENTF_KEYUP   = 0x0002
_INPUT_KEYBOARD    = 1
_VK_BACK           = 0x08

_ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk',         wintypes.WORD),
        ('wScan',       wintypes.WORD),
        ('dwFlags',     wintypes.DWORD),
        ('time',        wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_size_t),
    ]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('ki',   _KEYBDINPUT),
        ('pad',  ctypes.c_ubyte * 8),
    ]


def _key_events(vk=0, scan=0, flags=0):
    yield _INPUT(_INPUT_KEYBOARD,
                 _KEYBDINPUT(vk, scan, flags, 0, MAGIC_EXTRA))
    yield _INPUT(_INPUT_KEYBOARD,
                 _KEYBDINPUT(vk, scan, flags | _KEYEVENTF_KEYUP, 0, MAGIC_EXTRA))


class Injector:
    """Replace text in the focused field: N backspaces, then unicode text."""

    def __init__(self):
        try:
            self._send_input = ctypes.windll.user32.SendInput
        except AttributeError:          # not Windows — tests use FakeInjector
            self._send_input = None

    def replace(self, backspaces: int, text: str):
        if self._send_input is None:
            return
        events = []
        for _ in range(backspaces):
            events.extend(_key_events(vk=_VK_BACK))
        for ch in text:
            # utf-16-le yields surrogate pairs for chars beyond the BMP
            encoded = ch.encode('utf-16-le')
            for i in range(0, len(encoded), 2):
                unit = int.from_bytes(encoded[i:i + 2], 'little')
                events.extend(_key_events(scan=unit, flags=_KEYEVENTF_UNICODE))
        if not events:
            return
        arr = (_INPUT * len(events))(*events)
        self._send_input(len(events), arr, ctypes.sizeof(_INPUT))


class FakeInjector:
    """Test double recording (backspaces, text) calls."""

    def __init__(self):
        self.calls = []

    def replace(self, backspaces: int, text: str):
        self.calls.append((backspaces, text))

    @property
    def screen_ops(self):
        return self.calls
