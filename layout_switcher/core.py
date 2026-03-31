
# core.py
import ctypes
import ctypes.wintypes
import time
import json
import logging
import os
import sys
import string
from logging.handlers import RotatingFileHandler
from pynput import keyboard
from pynput.keyboard import Key, Controller
from mapper import LayoutMapper
from validator import DictionaryValidator
from corrector import GrammarEngine

from shortcut import (
    ShortcutDef, parse_shortcut, format_shortcut,
    pynput_key_matches, PYNPUT_MODIFIER_MAP,
)

VERSION = "0.4.1"

# ── Windows API helpers ───────────────────────────────────────────────────────
try:
    _user32   = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _psapi    = ctypes.windll.psapi
    _WIN32_OK = True
except AttributeError:
    _WIN32_OK = False


def _get_active_layout() -> str:
    """Return 'EN', 'UK', or 'unknown' based on the foreground window's input layout.

    Queries the foreground window's thread layout — the thread whose keypresses we
    are correcting — not the pynput listener's own background thread.

    Layout detection diagram:
        GetForegroundWindow() → hwnd
                ↓
        GetWindowThreadProcessId(hwnd) → thread_id
                ↓
        GetKeyboardLayout(thread_id) → HKL handle
                ↓
        HKL & 0xFFFF → primary language identifier
            0x0422 → UK
            0x0409 → EN
            else   → unknown
    """
    if not _WIN32_OK:
        return 'unknown'
    try:
        hwnd    = _user32.GetForegroundWindow()
        tid     = _user32.GetWindowThreadProcessId(hwnd, None)
        hkl     = _user32.GetKeyboardLayout(tid)
        lang_id = hkl & 0xFFFF   # low word = primary language identifier
        if lang_id == 0x0422:    # Ukrainian
            return 'UK'
        if lang_id == 0x0409:    # English (US)
            return 'EN'
        return 'unknown'
    except Exception:
        return 'unknown'


def _get_foreground_app() -> str:
    """Return the lowercase exe name of the foreground window's process.

    Returns '' on any failure so the per-app disable check is silently skipped.
    Example return: 'notepad.exe', 'chrome.exe'
    """
    if not _WIN32_OK:
        return ''
    try:
        hwnd  = _user32.GetForegroundWindow()
        pid   = ctypes.c_ulong(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010)
        hproc = _kernel32.OpenProcess(0x0410, False, pid.value)
        if not hproc:
            return ''
        buf = ctypes.create_unicode_buffer(260)
        _psapi.GetModuleBaseNameW(hproc, None, buf, ctypes.c_ulong(260))
        _kernel32.CloseHandle(hproc)
        return buf.value.lower()
    except Exception:
        return ''


# ── Path helpers ──────────────────────────────────────────────────────────────
def _get_config_path():
    """Returns config.json path next to the exe (or script when developing)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


def _get_log_path():
    """Returns debug.log path next to the exe (or script when developing)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "debug.log")


# ── Logger ────────────────────────────────────────────────────────────────────
def _build_logger() -> logging.Logger:
    """Rotating file logger (max 1 MB × 3 backups).

    Privacy levels:
      Dev  (script) → DEBUG: logs every word checked (typed words appear in log)
      Prod (frozen) → INFO:  logs only correction events, NOT raw typed words
    """
    logger = logging.getLogger("autoswitcher")
    logger.setLevel(logging.INFO if getattr(sys, 'frozen', False) else logging.DEBUG)
    if not logger.handlers:
        handler = RotatingFileHandler(
            _get_log_path(),
            maxBytes=1 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
    return logger


_logger = _build_logger()

# ── Constants ─────────────────────────────────────────────────────────────────
# Keys that invalidate the buffer (cursor moved, context changed).
# Key.tab is intentionally EXCLUDED: Tab triggers a word-boundary check instead
# of a silent buffer reset, so words typed before Tab in forms are corrected.
_RESET_KEYS = {
    Key.esc, Key.delete,
    Key.left, Key.right, Key.up, Key.down,
    Key.home, Key.end, Key.page_up, Key.page_down,
}

# Keys that trigger a word-boundary check (flush + clear buffer)
_BOUNDARY_KEYS = {Key.space, Key.enter, Key.tab}

# Punctuation chars to strip from word TRAILING EDGE before layout mapping.
# Apostrophe is excluded — it appears mid-word in contractions and Ukrainian.
# Stripping trailing punct fixes the "ghbdsn." → "привітю" false-negative where
# '.' maps to 'ю' (a letter) and causes validator.is_ukrainian() to fail.
_STRIP_PUNCT = string.punctuation.replace("'", "")


class LayoutSwitcherCore:
    def __init__(self, mapper: LayoutMapper):
        self.mapper = mapper
        self.controller = Controller()
        self.buffer: list = []
        self.is_correcting = False
        self.running = False
        self.listener = None

        # Injectable layout / app detectors — replace in tests to avoid Win32 calls
        self._layout_detector = _get_active_layout
        self._app_detector    = _get_foreground_app

        # Modifier tracking for configurable shortcut
        self._modifiers_held: set = set()
        self._revert_shortcut = parse_shortcut('alt+2')  # overwritten by load_config
        self.shortcut_capture_active = False  # suppress during settings UI capture

        # Undo: most recent auto-correction, cleared after use
        # Structure: {'original': str, 'corrected': str, 'separator': key|None, 'ts': float}
        self.last_correction = None

        # Post-correction cooldown: SendInput events get queued and re-enter
        # the hook AFTER is_correcting is False.  Ignore events briefly.
        self._correction_ts = 0.0

        # Notification callback — set from main.py after TrayIcon is created:
        #   core.notify_callback = tray.notify
        self.notify_callback = None

        # Pending whitelist offer: set after undo so next Shift-tap adds word
        # Structure: {'word': str, 'ts': float}
        self._pending_whitelist = None

        # Settings (defaults — overwritten by load_config)
        self.enabled               = True
        self.switch_en_to_uk       = True
        self.switch_uk_to_en       = True
        self.t9_eng                = False
        self.t9_ukr                = False
        self.whitelist:      list  = []
        self.notifications_enabled = True
        self.disabled_apps:  list  = []   # lowercase exe names to skip correction
        self.correction_count      = 0
        self.correction_date       = ''   # ISO date "YYYY-MM-DD", resets counter daily
        self.layout_variant        = 'standard'  # 'standard' or 'enhanced'
        self.load_config()

        print("Initializing Validator...")
        self.validator = DictionaryValidator()
        print("Initializing Grammar Engine...")
        self.grammar = GrammarEngine()

    # ── Config ────────────────────────────────────────────────────────────────
    def load_config(self):
        config_path = _get_config_path()
        if not os.path.exists(config_path):
            return
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.enabled               = data.get('enabled',               True)
            self.switch_en_to_uk       = data.get('switch_en_to_uk',       True)
            self.switch_uk_to_en       = data.get('switch_uk_to_en',       True)
            self.t9_eng                = data.get('t9_eng',                False)
            self.t9_ukr                = data.get('t9_ukr',                False)
            self.whitelist             = data.get('whitelist',             [])
            self.notifications_enabled = data.get('notifications_enabled', True)
            self.disabled_apps         = data.get('disabled_apps',         [])
            self.correction_count      = data.get('correction_count',      0)
            self.correction_date       = data.get('correction_date',       '')
            self.layout_variant        = data.get('layout_variant',        'standard')
            shortcut_str               = data.get('revert_shortcut',     'alt+2')
            try:
                self._revert_shortcut = parse_shortcut(shortcut_str)
            except ValueError:
                self._revert_shortcut = parse_shortcut('alt+2')
            self.mapper.set_variant(self.layout_variant)
            print(
                f"Loaded config: EN->UK={self.switch_en_to_uk}, "
                f"T9_EN={self.t9_eng}, T9_UK={self.t9_ukr}, "
                f"variant={self.layout_variant}"
            )
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        data = {
            'enabled':               self.enabled,
            'switch_en_to_uk':       self.switch_en_to_uk,
            'switch_uk_to_en':       self.switch_uk_to_en,
            't9_eng':                self.t9_eng,
            't9_ukr':                self.t9_ukr,
            'whitelist':             self.whitelist,
            'notifications_enabled': self.notifications_enabled,
            'disabled_apps':         self.disabled_apps,
            'correction_count':      self.correction_count,
            'correction_date':       self.correction_date,
            'layout_variant':        self.layout_variant,
            'revert_shortcut':       self._revert_shortcut.raw,
        }
        try:
            with open(_get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    # ── Listener lifecycle ────────────────────────────────────────────────────
    def start(self):
        """Start the keyboard listener (non-blocking — runs in its own thread)."""
        self.running = True
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release,
        )
        self.listener.daemon = True
        self.listener.start()
        print("Core Listener Started.")

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log(self, msg: str, *, info: bool = False):
        """Log at DEBUG (default) or INFO level.

        In production (frozen exe), DEBUG messages are filtered — only INFO
        (correction events) appear in debug.log for privacy.
        """
        try:
            if info:
                _logger.info(msg)
            else:
                _logger.debug(msg)
        except Exception:
            pass

    # ── Daily counter ─────────────────────────────────────────────────────────
    def _bump_counter(self):
        """Increment the daily correction counter, resetting on a new calendar day."""
        import datetime
        today = datetime.date.today().isoformat()
        if self.correction_date != today:
            self.correction_count = 0
            self.correction_date  = today
        self.correction_count += 1
        self.save_config()

    # ── Layout-safe text injection ───────────────────────────────────────────
    @staticmethod
    def _type_unicode(text: str):
        """Inject text via SendInput with KEYBDINPUT.UNICODE flag.

        Bypasses the keyboard layout: 'hello' produces 'hello' even when
        the foreground app has UK layout active, and 'привіт' produces
        'привіт' even with EN layout.  pynput's controller.type() uses
        VkKeyScan for ASCII which goes through the active layout.
        """
        if not _WIN32_OK or not text:
            return
        _UNICODE  = 0x0004
        _KEYUP    = 0x0002
        _INPUT_KB = 1

        class _KBI(ctypes.Structure):
            _fields_ = [
                ('wVk',     ctypes.wintypes.WORD),
                ('wScan',   ctypes.wintypes.WORD),
                ('dwFlags', ctypes.wintypes.DWORD),
                ('time',    ctypes.wintypes.DWORD),
                ('extra',   ctypes.POINTER(ctypes.c_ulong)),
            ]

        class _INP(ctypes.Structure):
            _fields_ = [
                ('type', ctypes.wintypes.DWORD),
                ('ki',   _KBI),
                ('pad',  ctypes.c_ubyte * 8),
            ]

        for ch in text:
            sc = ord(ch)
            for flags in (_UNICODE, _UNICODE | _KEYUP):
                ki = _KBI(0, sc, flags, 0, None)
                inp = _INP(_INPUT_KB, ki)
                ctypes.windll.user32.SendInput(
                    1, ctypes.byref(inp), ctypes.sizeof(_INP))
            time.sleep(0.003)

    # ── Correction ────────────────────────────────────────────────────────────
    def perform_correction(self, wrong_text: str, correct_text: str, separator_key,
                           *, record_undo: bool = True):
        """Replace wrong_text with correct_text in the active text field.

        separator_key — the key that triggered the check (space/enter/tab) or None.
        record_undo=False skips storing the undo record (used by _undo_last_correction
        itself to prevent double-undo).

        Backspace count:
            word_length + (1 if separator was already delivered, else 0)
        """
        self.is_correcting = True
        try:
            backspaces = len(wrong_text) + (0 if separator_key is None else 1)
            for _ in range(backspaces):
                self.controller.press(Key.backspace)
                self.controller.release(Key.backspace)
                time.sleep(0.005)

            self._type_unicode(correct_text)
            time.sleep(0.01)

            # Re-deliver the separator so the user's typing flow continues naturally
            if separator_key == Key.enter:
                self.controller.press(Key.enter)
                self.controller.release(Key.enter)
            elif separator_key in (Key.space, Key.tab):
                self.controller.press(separator_key)
                self.controller.release(separator_key)
            elif (separator_key is not None
                  and hasattr(separator_key, 'char')
                  and separator_key.char):
                self.controller.type(separator_key.char)

            self.buffer = []

            if record_undo:
                self.last_correction = {
                    'original':  wrong_text,
                    'corrected': correct_text,
                    'separator': separator_key,
                    'ts':        time.time(),
                }

        except Exception as e:
            print(f"Error during correction: {e}")
            self._log(f"ERROR correction: {e}", info=True)
        finally:
            self.is_correcting = False
            self._correction_ts = time.time()

    def _undo_last_correction(self):
        """Reverse the most recent auto-correction (Shift-tap within 5 s).

        After undo, sets _pending_whitelist so a second Shift-tap within 5 s
        adds the original word to the whitelist (preventing future corrections).
        """
        lc = self.last_correction
        self.last_correction = None     # clear first to prevent double-undo
        self._log(f"UNDO: '{lc['corrected']}' -> '{lc['original']}'", info=True)
        self.perform_correction(
            lc['corrected'],
            lc['original'],
            lc['separator'],
            record_undo=False,
        )
        # Offer to whitelist — next Shift-tap within 5 s adds word
        self._pending_whitelist = {
            'word': lc['original'],
            'ts':   time.time(),
        }
        if self.notify_callback and self.notifications_enabled:
            try:
                self.notify_callback(
                    f"Reverted '{lc['corrected']}' \u2192 '{lc['original']}'. "
                    f"Shift again to whitelist."
                )
            except Exception:
                pass

    # ── Word detection ────────────────────────────────────────────────────────
    def _check_word(self, word: str, trigger_key):
        """Detect wrong-layout word and apply correction if confident.

        CRITICAL PYNPUT INSIGHT
        ───────────────────────
        pynput caches the keyboard layout of its own listener thread at
        startup (always EN on a bilingual EN/UK system).  Every key.char is
        the EN translation of the physical key, **regardless of the user's
        active layout**.  So the buffer always contains EN characters:

          User types "руддщ" (UK layout) → pynput delivers h,e,l,l,o
          User types "ghbdsn" (EN layout) → pynput delivers g,h,b,d,s,n

        DUAL-TRANSLATION ARCHITECTURE
        ─────────────────────────────
        Because the buffer is always EN chars, we derive BOTH possible
        readings from it:

          en_text = buffer word          (what EN layout would produce)
          uk_text = to_ukrainian(buffer) (what UK layout would produce)

        Then we use the Windows layout API to decide which reading matches
        what the foreground app actually shows, and check if correction is
        needed.  The layout API is called ONCE per word, at the moment the
        boundary key fires — the user just finished typing so the foreground
        window still has the layout they typed with.

        Period-before-space fix:
          Trailing punctuation is stripped before layout mapping because
          '.' → 'ю' (a letter) in the EN→UK table, causing "ghbdsn." to map
          to "привітю" which fails is_ukrainian().  After stripping:
            word_for_map = "ghbdsn"   → maps to "привіт"
            candidate    = "привіт."  (trailing punct re-appended)
        """
        if not word:
            return

        # Whitelist — never correct these words
        if word.lower() in {w.lower() for w in self.whitelist}:
            self._log(f"Whitelisted: '{word}'")
            return

        # Per-app disable — skip correction in specified applications
        try:
            app = self._app_detector()
            if app and any(app == d.lower() for d in self.disabled_apps):
                self._log(f"Disabled for '{app}': skipping")
                return
        except Exception as e:
            self._log(f"app-check error: {e}")

        self._log(f"Check: '{word}'")

        # Strip trailing punctuation for layout mapping (period/comma → letter bug)
        word_for_map   = word.rstrip(_STRIP_PUNCT)
        trailing_punct = word[len(word_for_map):]
        if not word_for_map:
            return  # was pure punctuation

        layout = self._layout_detector()
        self._log(f"Layout={layout}")

        # ── Dual translation ─────────────────────────────────────────────
        # Buffer always has EN chars (pynput behaviour).
        # Derive what each layout would show in the foreground app.
        en_text = word_for_map                              # EN reading
        uk_text = self.mapper.to_ukrainian(word_for_map)    # UK reading

        en_valid = self.validator.is_english(en_text)
        uk_valid = self.validator.is_ukrainian(uk_text)
        self._log(f"en='{en_text}' valid={en_valid}, uk='{uk_text}' valid={uk_valid}")

        candidate       = None
        layout_switched = False
        # app_text: what the foreground app actually shows (for backspace count)
        app_text        = None

        # ── Case 1: Layout is EN — app shows en_text ─────────────────────
        # The user typed with EN layout.  The app shows en_text.
        # If en_text is valid English → nothing to do.
        # If en_text is NOT valid English but uk_text IS valid Ukrainian →
        #   the user had wrong layout.  Correct en_text → uk_text.
        if layout in ('EN', 'unknown') and self.switch_en_to_uk:
            if not en_valid and uk_valid:
                candidate       = uk_text + trailing_punct
                app_text        = en_text + trailing_punct  # what to delete
                layout_switched = True
                self._log(f"EN->UK: '{en_text}' -> '{uk_text}'")

            # Punct heuristic: en_text IS valid English but contains punct
            # that disappears in the UK mapping (e.g. ",fub" → "баги").
            if not layout_switched and en_valid:
                has_punct = any(c in string.punctuation for c in word)
                if has_punct:
                    as_ukr = self.mapper.to_ukrainian(word)
                    if (not any(c in string.punctuation for c in as_ukr)
                            and self.validator.is_ukrainian(as_ukr)):
                        candidate       = as_ukr
                        app_text        = word
                        layout_switched = True
                        self._log(f"Punct EN->UK: '{word}' -> '{as_ukr}'")

        # ── Case 2: Layout is UK — app shows uk_text ─────────────────────
        # The user typed with UK layout.  The app shows uk_text (Cyrillic).
        # pynput gave us en_text (the EN translation of the same keys).
        #
        # When layout is KNOWN to be UK and en_text is a valid English word,
        # the user almost certainly had the wrong layout — correct to EN.
        # This handles "туц"→"new" where pymorphy2 considers "туц" valid
        # (as an interjection).  Shift-tap to undo if the correction is wrong.
        #
        # When layout is unknown, be conservative: only correct when the UK
        # reading is NOT valid (to avoid false positives without layout proof).
        if not layout_switched and self.switch_uk_to_en:
            if layout == 'UK' and en_valid:
                # Known UK layout + valid EN word → strong signal for correction
                candidate       = en_text + trailing_punct
                app_text        = uk_text + trailing_punct
                layout_switched = True
                self._log(f"UK->EN: '{uk_text}' -> '{en_text}'")
            elif layout == 'unknown' and en_valid and not uk_valid:
                # Unknown layout — only correct when unambiguous
                candidate       = en_text + trailing_punct
                app_text        = uk_text + trailing_punct
                layout_switched = True
                self._log(f"UK->EN(unk): '{uk_text}' -> '{en_text}'")

        # ── T9 autocorrect — only if no layout switch was applied ────────
        if not layout_switched:
            if layout in ('EN', 'unknown'):
                # App shows en_text
                if self.t9_eng and not en_valid:
                    suggestion = self.grammar.correct_english(en_text)
                    if suggestion and suggestion != en_text:
                        candidate = suggestion
                        app_text  = en_text + trailing_punct
                        self._log(f"T9 EN: '{en_text}' -> '{suggestion}'")
            if not candidate and layout in ('UK', 'unknown'):
                # App shows uk_text
                if self.t9_ukr and not uk_valid:
                    suggestion = self.grammar.correct_ukrainian(uk_text)
                    if suggestion and suggestion != uk_text:
                        candidate = suggestion
                        app_text  = uk_text + trailing_punct
                        self._log(f"T9 UK: '{uk_text}' -> '{suggestion}'")

        if candidate and app_text and candidate != app_text:
            print(f"Correcting '{app_text}' -> '{candidate}'")
            self._log(f"CORRECTING: '{app_text}' -> '{candidate}'", info=True)
            self.perform_correction(app_text, candidate, trigger_key)
            self._bump_counter()
            # No tray notification on correction — Shift-tap to undo shows one.

    # ── Revert shortcut handler ──────────────────────────────────────────────
    def _handle_revert_shortcut(self):
        """Three-priority revert triggered by the configurable shortcut.

        Priority 1: Accept pending whitelist offer (2nd press after undo).
        Priority 2: Undo the most recent correction (within 5 s).
        Priority 3: Force-swap the current buffered word.
        """
        # Priority 1: pending whitelist offer
        if (self._pending_whitelist is not None
                and time.time() - self._pending_whitelist['ts'] < 5.0):
            w = self._pending_whitelist['word']
            self._pending_whitelist = None
            if w.lower() not in {x.lower() for x in self.whitelist}:
                self.whitelist.append(w)
                self.save_config()
                self._log(f"WHITELIST: added '{w}'", info=True)
                if self.notify_callback and self.notifications_enabled:
                    try:
                        self.notify_callback(f"'{w}' added to whitelist")
                    except Exception:
                        pass
            return

        # Priority 2: undo recent correction
        if (self.last_correction is not None
                and time.time() - self.last_correction['ts'] < 5.0):
            self._undo_last_correction()
            return

        # Priority 3: force-swap current buffered word
        self._pending_whitelist = None  # expired
        word_to_swap = "".join(self.buffer).strip()
        if word_to_swap:
            # Determine what the app actually shows based on layout
            layout = self._layout_detector()
            if layout == 'UK':
                # Buffer has EN chars, app shows UK translation
                app_word = self.mapper.to_ukrainian(word_to_swap)
                candidate = word_to_swap  # swap to EN
            else:
                # Buffer has EN chars = app text, swap to UK
                app_word = word_to_swap
                candidate = self.mapper.to_ukrainian(word_to_swap)
            self._log(f"Force-swap: '{app_word}' -> '{candidate}'", info=True)
            self.perform_correction(app_word, candidate, None)
            self._bump_counter()

    # ── Key events ────────────────────────────────────────────────────────────
    def on_release(self, key):
        if self.is_correcting:
            return
        # Track modifier release
        mod = PYNPUT_MODIFIER_MAP.get(key)
        if mod:
            self._modifiers_held.discard(mod)

    def on_press(self, key):
        if not self.running or self.is_correcting:
            return
        # Cooldown: SendInput events from _type_unicode are queued and arrive
        # AFTER is_correcting is cleared.  Ignore them for 150 ms.
        if time.time() - self._correction_ts < 0.15:
            return

        # ── Modifier tracking ────────────────────────────────────────────────
        mod = PYNPUT_MODIFIER_MAP.get(key)
        if mod:
            self._modifiers_held.add(mod)
            return  # modifiers alone don't go into the buffer

        # ── Shortcut detection ───────────────────────────────────────────────
        if (not self.shortcut_capture_active
                and self._modifiers_held == self._revert_shortcut.modifiers
                and pynput_key_matches(key, self._revert_shortcut.key)):
            self._handle_revert_shortcut()
            return

        # ── Reset keys ───────────────────────────────────────────────────────
        try:
            if key in _RESET_KEYS:
                self.buffer = []
                return
        except TypeError:
            pass

        # ── Master toggle ────────────────────────────────────────────────────
        if not self.enabled:
            try:
                if key in _BOUNDARY_KEYS or key == Key.backspace:
                    self.buffer = []
            except TypeError:
                pass
            return

        try:
            # ── Buffer maintenance ───────────────────────────────────────────
            if key == Key.backspace:
                if self.buffer:
                    self.buffer.pop()
                return

            if hasattr(key, 'char') and key.char:
                self.buffer.append(key.char)

            # ── Word boundary ────────────────────────────────────────────────
            try:
                is_boundary = key in _BOUNDARY_KEYS
            except TypeError:
                is_boundary = False

            if not is_boundary:
                return

            word = "".join(self.buffer).strip()
            self.buffer = []
            self._check_word(word, key)

        except Exception as e:
            print(f"Error in listener: {e}")
            self._log(f"ERROR on_press: {e}", info=True)
            self.buffer = []
