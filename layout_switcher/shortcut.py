"""Configurable keyboard shortcut parsing, formatting, and pynput matching."""

from dataclasses import dataclass, field
from pynput.keyboard import Key

# ── Data structure ───────────────────────────────────────────────────────────

@dataclass
class ShortcutDef:
    """Parsed shortcut definition."""
    modifiers: set       # e.g. {'alt'}, {'ctrl', 'shift'}
    key: str             # e.g. '2', 'z', 'f5'
    raw: str             # original config string, e.g. 'alt+2'


# ── Modifier mapping ────────────────────────────────────────────────────────

VALID_MODIFIERS = {'alt', 'ctrl', 'shift'}

# pynput Key enum → modifier name string
PYNPUT_MODIFIER_MAP = {
    Key.alt:     'alt',
    Key.alt_l:   'alt',
    Key.alt_r:   'alt',
    Key.alt_gr:  'alt',
    Key.ctrl:    'ctrl',
    Key.ctrl_l:  'ctrl',
    Key.ctrl_r:  'ctrl',
    Key.shift:   'shift',
    Key.shift_l: 'shift',
    Key.shift_r: 'shift',
}

# VK codes for digits and letters (used when Alt is held — pynput gives vk, not char)
_VK_DIGITS  = {0x30 + i: str(i) for i in range(10)}          # 0x30='0' .. 0x39='9'
_VK_LETTERS = {0x41 + i: chr(0x61 + i) for i in range(26)}   # 0x41='a' .. 0x5A='z'

# F-key mapping
_FKEY_MAP = {getattr(Key, f'f{n}', None): f'f{n}' for n in range(1, 25)}
_FKEY_MAP = {k: v for k, v in _FKEY_MAP.items() if k is not None}

# Valid trigger keys (non-modifier part of the shortcut)
_VALID_KEYS = (
    set(str(i) for i in range(10))                # 0-9
    | set(chr(c) for c in range(ord('a'), ord('z') + 1))  # a-z
    | set(f'f{n}' for n in range(1, 25))          # f1-f24
    | {'space', 'tab', 'backquote', 'minus', 'equal',
       'bracketleft', 'bracketright', 'backslash',
       'semicolon', 'apostrophe', 'comma', 'period', 'slash'}
)


# ── Parsing ──────────────────────────────────────────────────────────────────

def parse_shortcut(s: str) -> ShortcutDef:
    """Parse a shortcut string like 'alt+2' or 'ctrl+shift+z'.

    Raises ValueError on invalid input.
    """
    s = s.strip().lower()
    if not s:
        raise ValueError("Empty shortcut string")

    parts = [p.strip() for p in s.split('+') if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"Shortcut must have modifier+key, got: {s!r}")

    key = parts[-1]
    mods = set(parts[:-1])

    # Validate modifiers
    bad_mods = mods - VALID_MODIFIERS
    if bad_mods:
        raise ValueError(f"Invalid modifier(s): {bad_mods}")

    # Validate key
    if key not in _VALID_KEYS:
        raise ValueError(f"Invalid key: {key!r}")

    raw = '+'.join(sorted(mods) + [key])
    return ShortcutDef(modifiers=mods, key=key, raw=raw)


# ── Formatting ───────────────────────────────────────────────────────────────

def format_shortcut(sd: ShortcutDef) -> str:
    """Human-readable display: 'Alt + 2'."""
    parts = [m.capitalize() for m in sorted(sd.modifiers)]
    parts.append(sd.key.upper() if len(sd.key) == 1 else sd.key.capitalize())
    return ' + '.join(parts)


# ── pynput matching ──────────────────────────────────────────────────────────

def pynput_key_matches(pynput_key, shortcut_key: str) -> bool:
    """Check if a pynput key event matches the trigger key of a shortcut.

    Handles three cases:
      1. key.char matches (normal typing)
      2. key.vk matches via VK code lookup (when Alt is held, char is often None)
      3. Key.fN enum matches for function keys
    """
    # Case 1: character match
    char = getattr(pynput_key, 'char', None)
    if char is not None and char.lower() == shortcut_key:
        return True

    # Case 2: virtual key code match (digits/letters when modifiers are held)
    vk = getattr(pynput_key, 'vk', None)
    if vk is not None:
        vk_char = _VK_DIGITS.get(vk) or _VK_LETTERS.get(vk)
        if vk_char == shortcut_key:
            return True

    # Case 3: F-key enum match
    fkey_name = _FKEY_MAP.get(pynput_key)
    if fkey_name == shortcut_key:
        return True

    return False
