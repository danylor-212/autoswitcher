# pipeline.py — event capture and correction execution.
#
# Threading model (the V1 killer was doing everything in the hook callback
# with wall-clock guards):
#
#   pynput listener thread:  filter injected events, snapshot
#                            (vk, modifiers, caps, foreground hwnd), enqueue.
#   worker thread:           owns ALL mutable detection state — buffer, undo,
#                            whitelist, counters. Single consumer, no locks
#                            around detection state, no re-entrancy guards.
#   UI threads (Tk, tray):   touch only config attributes + save_config().
#
# Buffer integrity rules (each one closes a confirmed v1 corruption class):
#   - injected events never enter the pipeline        (pynput `injected` flag)
#   - Ctrl/Alt+key never enters the buffer            (no '\x13' pollution)
#   - mouse click resets the buffer                   (caret moved)
#   - word remembers its hwnd + layout; if either changed at the boundary,
#     the word is dropped, never corrected            (wrong-field deletions)
#   - boundary keys with non-shift modifiers held flush without correcting
#                                                     (Alt+Tab corrections)
#   - Enter/Tab flush only by default                 (chat double-send,
#                                                      form focus moves)

import datetime
import logging
import os
import queue
import threading
import time
from logging.handlers import RotatingFileHandler

import appconfig
import engine
import winapi
from dictionaries import Lexicon, STRIP_PUNCT
from injector import Injector
from keymap import KeyMap, vk_to_en_char
from shortcut import parse_shortcut, PYNPUT_MODIFIER_MAP, pynput_key_matches

VERSION = "2.0.0a1"

_UNDO_WINDOW_S = 5.0
_COUNTER_SAVE_INTERVAL_S = 30.0

# vk codes that invalidate the buffer (caret moved / context changed)
_RESET_VKS = {
    0x1B,                    # esc
    0x2E,                    # delete
    0x25, 0x26, 0x27, 0x28,  # arrows
    0x24, 0x23, 0x21, 0x22,  # home end pgup pgdn
}
_VK_BACKSPACE = 0x08
_VK_SPACE     = 0x20
_VK_ENTER     = 0x0D
_VK_TAB       = 0x09

_BOUNDARY_VKS = {_VK_SPACE, _VK_ENTER, _VK_TAB}

# pynput Key-enum equivalents: some backends deliver Key members whose vk is
# None, so special keys are recognised by identity as well as by vk code.
from pynput.keyboard import Key as _Key

_KEY_TO_VK = {
    _Key.esc: 0x1B, _Key.delete: 0x2E,
    _Key.left: 0x25, _Key.up: 0x26, _Key.right: 0x27, _Key.down: 0x28,
    _Key.home: 0x24, _Key.end: 0x23, _Key.page_up: 0x21, _Key.page_down: 0x22,
    _Key.backspace: _VK_BACKSPACE,
    _Key.space: _VK_SPACE, _Key.enter: _VK_ENTER, _Key.tab: _VK_TAB,
}


def _log_path():
    return os.path.join(appconfig.config_dir(), 'debug.log')


def _build_logger():
    logger = logging.getLogger('autoswitcher')
    import sys
    logger.setLevel(logging.INFO if getattr(sys, 'frozen', False) else logging.DEBUG)
    if not logger.handlers:
        try:
            os.makedirs(appconfig.config_dir(), exist_ok=True)
            handler = RotatingFileHandler(
                _log_path(), maxBytes=1024 * 1024, backupCount=3, encoding='utf-8')
            handler.setFormatter(
                logging.Formatter('%(asctime)s %(message)s', datefmt='%H:%M:%S'))
            logger.addHandler(handler)
        except OSError:
            logger.addHandler(logging.NullHandler())
    return logger


class LayoutSwitcherCore:
    """V2 core. Keeps the v1 attribute surface used by settings.py/tray.py."""

    def __init__(self, keymap: KeyMap = None, *,
                 lexicon: Lexicon = None, injector=None, grammar=None,
                 layout_detector=None, hwnd_detector=None,
                 app_detector=None, caps_detector=None):
        self.mapper = keymap or KeyMap()
        self.injector = injector or Injector()
        self._layout_detector = layout_detector or winapi.layout_of_foreground
        self._hwnd_detector   = hwnd_detector or winapi.foreground_hwnd
        self._app_detector    = app_detector or winapi.foreground_app
        self._caps_detector   = caps_detector or winapi.caps_lock_on
        self._log = _build_logger()

        # ── Config (attribute surface kept compatible with v1 UI code) ──
        cfg = appconfig.load()
        self.enabled               = cfg['enabled']
        self.switch_en_to_uk       = cfg['switch_en_to_uk']
        self.switch_uk_to_en       = cfg['switch_uk_to_en']
        self.t9_eng                = cfg['t9_eng']
        self.t9_ukr                = cfg['t9_ukr']
        self.notifications_enabled = cfg['notifications_enabled']
        self.disabled_apps         = cfg['disabled_apps']
        self.correction_count      = cfg['correction_count']
        self.correction_date       = cfg['correction_date']
        self.layout_variant        = cfg['layout_variant']
        self.correct_on_enter      = cfg['correct_on_enter']
        self.correct_on_tab        = cfg['correct_on_tab']
        self.mapper.set_variant(self.layout_variant)
        try:
            self._revert_shortcut = parse_shortcut(cfg['revert_shortcut'])
        except ValueError:
            self._revert_shortcut = parse_shortcut('alt+2')
        self.whitelist = self._canonicalize_whitelist(cfg['whitelist'])
        self._whitelist_lower = {w.lower() for w in self.whitelist}
        self.shortcut_capture_active = False
        self.notify_callback = None

        # ── Heavy resources ──────────────────────────────────────────────
        self.lexicon = lexicon or Lexicon()
        self.grammar = grammar   # lazy: built on first T9 use if enabled

        # ── Worker state (touched only by the worker thread) ────────────
        self._events: queue.Queue = queue.Queue()
        self._buffer: list = []
        self._word_hwnd = None
        self._word_layout = None
        self.last_correction = None
        self._keys_since_correction = 0
        self._pending_whitelist = None
        self._counter_dirty_ts = None

        # ── Listener state (touched only by the listener thread) ────────
        self._modifiers_held = set()

        self.running = False
        self._worker = None
        self._kb_listener = None
        self._mouse_listener = None

    # ══════════════════════════════════════════════════════════════════
    # Config persistence
    # ══════════════════════════════════════════════════════════════════
    def _canonicalize_whitelist(self, words):
        """Whitelist entries are stored as the physical-key (EN-char) form.
        Migrates v1 entries that were saved as on-screen Cyrillic text."""
        out = []
        for w in words:
            cw = self.mapper.to_english(w) if any('Ѐ' <= c <= 'ӿ' for c in w) else w
            if cw and cw not in out:
                out.append(cw)
        return out

    def save_config(self):
        appconfig.save({
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
            'correct_on_enter':      self.correct_on_enter,
            'correct_on_tab':        self.correct_on_tab,
        })

    def load_config(self):  # kept for v1 UI compatibility
        pass

    # ══════════════════════════════════════════════════════════════════
    # Lifecycle
    # ══════════════════════════════════════════════════════════════════
    def start(self):
        self.running = True
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name='SwitcherWorker')
        self._worker.start()

        from pynput import keyboard, mouse
        self._kb_listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._kb_listener.daemon = True
        self._kb_listener.start()
        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def stop(self):
        self.running = False
        self._events.put(('stop',))
        for listener in (self._kb_listener, self._mouse_listener):
            if listener:
                listener.stop()
        if self._counter_dirty_ts is not None:
            self.save_config()

    # ══════════════════════════════════════════════════════════════════
    # Listener thread: filter, snapshot, enqueue — nothing else
    # ══════════════════════════════════════════════════════════════════
    def _on_press(self, key, injected=False):
        if injected or not self.running:
            return
        mod = PYNPUT_MODIFIER_MAP.get(key)
        if mod:
            self._modifiers_held.add(mod)
            return
        self._events.put((
            'key', key,
            getattr(key, 'vk', None),
            frozenset(self._modifiers_held),
            self._caps_detector(),
            self._hwnd_detector(),
        ))

    def _on_release(self, key, injected=False):
        if injected:
            return
        mod = PYNPUT_MODIFIER_MAP.get(key)
        if mod:
            self._modifiers_held.discard(mod)

    def _on_click(self, x, y, button, pressed):
        if pressed and self.running:
            self._events.put(('mouse',))

    # ══════════════════════════════════════════════════════════════════
    # Worker thread
    # ══════════════════════════════════════════════════════════════════
    def _worker_loop(self):
        while True:
            try:
                event = self._events.get(timeout=_COUNTER_SAVE_INTERVAL_S)
            except queue.Empty:
                self._flush_counter_if_due(force=True)
                continue
            if event[0] == 'stop':
                return
            try:
                self._handle(event)
            except Exception as e:
                self._log.info("ERROR worker: %r", e)
                self._reset_word()
            self._flush_counter_if_due()

    def _handle(self, event):
        if event[0] == 'mouse':
            self._reset_word()
            return
        _, key, vk, mods, caps, hwnd = event
        self._dispatch_key(key, vk, mods, caps, hwnd)

    def _dispatch_key(self, key, vk, mods, caps, hwnd):
        # Revert shortcut — works even while disabled
        if (not self.shortcut_capture_active
                and mods == self._revert_shortcut.modifiers
                and pynput_key_matches(key, self._revert_shortcut.key)):
            self._handle_revert_shortcut()
            return

        self._keys_since_correction += 1

        # Key-enum identity is authoritative: on non-Windows backends the
        # member's vk is an X keysym, not a Windows virtual-key code.
        mapped = _KEY_TO_VK.get(key)
        if mapped is not None:
            vk = mapped

        if vk in _RESET_VKS:
            self._reset_word()
            return

        if not self.enabled:
            self._reset_word()
            return

        if vk == _VK_BACKSPACE:
            if self._buffer:
                self._buffer.pop()
            return

        if vk in _BOUNDARY_VKS:
            # Modifier-chord boundaries (Alt+Tab, Ctrl+Space…) never correct.
            if mods - {'shift'}:
                self._reset_word()
                return
            correct_allowed = (
                vk == _VK_SPACE
                or (vk == _VK_ENTER and self.correct_on_enter)
                or (vk == _VK_TAB and self.correct_on_tab)
            )
            self._finish_word(separator=' ' if vk == _VK_SPACE else None,
                              correct=correct_allowed, hwnd=hwnd)
            return

        # Ctrl/Alt chords are commands, not text — never buffer them.
        if mods - {'shift'}:
            return

        char = vk_to_en_char(vk, 'shift' in mods, caps) if vk is not None else None
        if char is None:
            return
        if not self._buffer:
            self._word_hwnd = hwnd
            self._word_layout = self._layout_detector()
        self._buffer.append(char)

    # ── Word completion ────────────────────────────────────────────────
    def _finish_word(self, *, separator, correct, hwnd):
        en_token = ''.join(self._buffer)
        word_hwnd, word_layout = self._word_hwnd, self._word_layout
        self._reset_word()
        if not en_token or not correct:
            return
        # Caret integrity: same window and same layout as when the word began.
        if hwnd != word_hwnd:
            self._log.debug("drop '%s': focus changed", en_token)
            return
        layout = self._layout_detector()
        if word_layout is not None and layout != word_layout:
            self._log.debug("drop '%s': layout changed mid-word", en_token)
            return

        if en_token.lower() in self._whitelist_lower or \
                en_token.strip(STRIP_PUNCT).lower() in self._whitelist_lower:
            self._log.debug("whitelisted: '%s'", en_token)
            return

        if self.disabled_apps:
            app = self._app_detector()
            if app and any(app == d.lower() for d in self.disabled_apps):
                return

        decision = engine.decide(
            en_token, layout,
            lex=self.lexicon, keymap=self.mapper,
            en_to_uk=self.switch_en_to_uk, uk_to_en=self.switch_uk_to_en,
            t9_en=self.t9_eng, t9_uk=self.t9_ukr, t9=self._get_grammar(),
        )
        if decision.action == 'none':
            return

        self._log.info("CORRECT(%s): '%s' -> '%s'",
                       decision.reason, decision.app_text, decision.replacement)
        self._apply_replacement(decision.app_text, decision.replacement, separator)
        self.last_correction = {
            'en_token':    en_token,
            'app_text':    decision.app_text,
            'replacement': decision.replacement,
            'separator':   separator,
            'ts':          time.time(),
        }
        self._keys_since_correction = 0
        self._bump_counter()

    def _apply_replacement(self, app_text, replacement, separator):
        backspaces = len(app_text) + (1 if separator else 0)
        self.injector.replace(backspaces, replacement + (separator or ''))

    def _get_grammar(self):
        if not (self.t9_eng or self.t9_ukr):
            return None
        if self.grammar is None:
            from corrector import GrammarEngine
            self.grammar = GrammarEngine()
        return self.grammar

    def _reset_word(self):
        self._buffer = []
        self._word_hwnd = None
        self._word_layout = None

    # ── Revert shortcut: whitelist offer → undo → force-swap ──────────
    def _handle_revert_shortcut(self):
        now = time.time()

        if (self._pending_whitelist is not None
                and now - self._pending_whitelist['ts'] < _UNDO_WINDOW_S):
            token = self._pending_whitelist['en_token']
            self._pending_whitelist = None
            if token.lower() not in self._whitelist_lower:
                self.whitelist.append(token)
                self._whitelist_lower.add(token.lower())
                self.save_config()
                self._log.info("WHITELIST: '%s'", token)
                self._notify(f"'{token}' / '{self.mapper.to_ukrainian(token)}' "
                             f"added to whitelist")
            return

        lc = self.last_correction
        if lc is not None and now - lc['ts'] < _UNDO_WINDOW_S:
            self.last_correction = None
            if self._keys_since_correction > 0:
                # The caret moved on — undoing would splice into new text.
                self._notify("Can't undo: text was typed after the correction")
                return
            backspaces = len(lc['replacement']) + (1 if lc['separator'] else 0)
            self.injector.replace(
                backspaces, lc['app_text'] + (lc['separator'] or ''))
            self._log.info("UNDO: '%s' -> '%s'", lc['replacement'], lc['app_text'])
            self._pending_whitelist = {'en_token': lc['en_token'], 'ts': now}
            self._notify(f"Reverted to '{lc['app_text']}'. "
                         f"Press again to whitelist.")
            return

        # Force-swap the word still in the buffer (pre-boundary)
        self._pending_whitelist = None
        en_token = ''.join(self._buffer)
        self._reset_word()
        if not en_token:
            return
        layout = self._layout_detector()
        if layout == 'UK':
            app_text, replacement = (self.mapper.to_ukrainian(en_token), en_token)
        else:
            app_text, replacement = (en_token, self.mapper.to_ukrainian(en_token))
        self._log.info("FORCE-SWAP: '%s' -> '%s'", app_text, replacement)
        self.injector.replace(len(app_text), replacement)
        self.last_correction = {
            'en_token': en_token, 'app_text': app_text,
            'replacement': replacement, 'separator': None, 'ts': now,
        }
        self._keys_since_correction = 0
        self._bump_counter()

    # ── Counters / notifications ──────────────────────────────────────
    def _bump_counter(self):
        today = datetime.date.today().isoformat()
        if self.correction_date != today:
            self.correction_count = 0
            self.correction_date = today
        self.correction_count += 1
        if self._counter_dirty_ts is None:
            self._counter_dirty_ts = time.time()

    def _flush_counter_if_due(self, force=False):
        if self._counter_dirty_ts is None:
            return
        if force or time.time() - self._counter_dirty_ts >= _COUNTER_SAVE_INTERVAL_S:
            self._counter_dirty_ts = None
            self.save_config()

    def _notify(self, msg):
        if self.notify_callback and self.notifications_enabled:
            try:
                self.notify_callback(msg)
            except Exception:
                pass

    # ── Whitelist mutation from the UI thread ─────────────────────────
    def whitelist_add(self, word: str):
        token = self._canonicalize_whitelist([word])
        if token and token[0].lower() not in self._whitelist_lower:
            self.whitelist.append(token[0])
            self._whitelist_lower.add(token[0].lower())

    def whitelist_remove(self, word: str):
        self.whitelist = [w for w in self.whitelist if w.lower() != word.lower()]
        self._whitelist_lower = {w.lower() for w in self.whitelist}
