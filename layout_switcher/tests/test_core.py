
import unittest
import sys
import os
import inspect
import time
from types import SimpleNamespace

# ── Compatibility shim for Python 3.11+ which removed inspect.getargspec ──────
if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = getargspec

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import LayoutSwitcherCore
from mapper import LayoutMapper
from pynput.keyboard import Key


class MockController:
    def __init__(self):
        self.history = []

    def press(self, key):
        self.history.append(('press', key))

    def release(self, key):
        self.history.append(('release', key))

    def type(self, text):
        self.history.append(('type', text))


def _make_core(variant='standard'):
    """Create a LayoutSwitcherCore wired for testing (no Win32 calls)."""
    mapper = LayoutMapper(variant=variant)
    core = LayoutSwitcherCore(mapper)
    core.controller = MockController()
    core.running = True
    core.buffer = []
    # Inject no-op detectors to avoid Win32 calls in unit tests
    core._layout_detector = lambda: 'unknown'
    core._app_detector    = lambda: ''
    return core


class TestCore(unittest.TestCase):
    def setUp(self):
        self.core = _make_core()

    @property
    def ctrl(self):
        return self.core.controller

    def _type(self, text):
        for ch in text:
            self.core.on_press(SimpleNamespace(char=ch))

    def _typed_words(self):
        return [evt[1] for evt in self.ctrl.history if evt[0] == 'type']

    def _typed_str(self):
        return "".join(self._typed_words())

    # ──────────────────────────────────────────────────────────────────
    # Original regression tests (kept and updated)
    # ──────────────────────────────────────────────────────────────────

    def test_switch_trigger_en_to_uk(self):
        """EN typing 'ghbdsn' + space → corrects to 'привіт'."""
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertIn("привіт", self._typed_str(),
                      f"Expected 'привіт'. History: {self.ctrl.history}")
        self.assertEqual(len(self.core.buffer), 0)

    def test_no_correction_on_valid_english(self):
        """Valid English word is left untouched."""
        self._type("hello")
        self.core.on_press(Key.space)
        self.assertNotIn("hello", self._typed_str(),
                         "Core should NOT retype a valid English word unchanged")

    def test_switch_ukr_to_eng_ignore(self):
        """Ukrainian 'шптщку' + space → corrects to 'ignore'."""
        self._type("шптщку")
        self.core.on_press(Key.space)
        self.assertIn("ignore", self._typed_str(),
                      f"Expected 'ignore'. History: {self.ctrl.history}")

    def test_switch_ukr_to_eng_hello(self):
        """Ukrainian 'руддщ' + space → corrects to 'hello'."""
        self._type("руддщ")
        self.core.on_press(Key.space)
        self.assertIn("hello", self._typed_str(),
                      f"Expected 'hello'. History: {self.ctrl.history}")

    def test_master_toggle_disabled(self):
        """No correction fires when core.enabled = False."""
        self.core.enabled = False
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Core corrected while disabled!")

    def test_ignore_punctuation_case(self):
        """',fub' (comma prefix) → 'баги' via punct heuristic."""
        self._type(",fub")
        self.core.on_press(Key.space)
        self.assertIn("баги", self._typed_str(),
                      f"Expected 'баги'. History: {self.ctrl.history}")

    # ──────────────────────────────────────────────────────────────────
    # BUG FIX: period-before-space (was broken in v0.3.4)
    # ──────────────────────────────────────────────────────────────────

    def test_period_before_space_correction(self):
        """'ghbdsn.' + space → 'привіт.' (period re-appended after correction)."""
        self._type("ghbdsn.")
        self.core.on_press(Key.space)
        typed = self._typed_str()
        self.assertIn("привіт", typed,
                      f"Expected 'привіт.' but got: '{typed}'")

    def test_pure_punctuation_word_ignored(self):
        """A buffer containing only punctuation produces no correction."""
        self._type("...")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Pure-punctuation word should be ignored")

    # ──────────────────────────────────────────────────────────────────
    # BUG FIX: Tab key triggers word check (was broken in v0.3.4)
    # ──────────────────────────────────────────────────────────────────

    def test_tab_triggers_correction(self):
        """Tab after a wrong-layout word triggers correction (form field use case)."""
        self._type("ghbdsn")
        self.core.on_press(Key.tab)
        typed = self._typed_str()
        self.assertIn("привіт", typed,
                      f"Tab should trigger correction. Got: '{typed}'")

    def test_tab_clears_buffer(self):
        """After Tab boundary, buffer is empty."""
        self._type("hello")
        self.core.on_press(Key.tab)
        self.assertEqual(len(self.core.buffer), 0)

    # ──────────────────────────────────────────────────────────────────
    # Windows API layout detection (injectable _layout_detector)
    # ──────────────────────────────────────────────────────────────────

    def test_layout_en_only_tries_en_to_uk(self):
        """With layout='EN', EN→UK correction fires for wrong-layout input."""
        self.core._layout_detector = lambda: 'EN'
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertIn("привіт", self._typed_str())

    def test_layout_uk_only_tries_uk_to_en(self):
        """With layout='UK', UK→EN correction fires for wrong-layout input."""
        self.core._layout_detector = lambda: 'UK'
        self._type("руддщ")
        self.core.on_press(Key.space)
        self.assertIn("hello", self._typed_str())

    def test_layout_en_skips_uk_to_en(self):
        """With layout='EN', a pure-Ukrainian-chars word typed in EN won't be
        decoded as UK→EN (no chars match EN layout anyway) — no false correction."""
        self.core._layout_detector = lambda: 'EN'
        self.core.switch_uk_to_en = True
        # 'привіт' is valid Ukrainian — should be left alone
        self._type("привіт")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Valid Ukrainian should never be corrected")

    def test_layout_unknown_tries_both_directions(self):
        """layout='unknown' falls back to trying both directions."""
        self.core._layout_detector = lambda: 'unknown'
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertIn("привіт", self._typed_str())

    # ──────────────────────────────────────────────────────────────────
    # Ctrl+Z undo
    # ──────────────────────────────────────────────────────────────────

    def test_undo_reverses_last_correction(self):
        """Ctrl+Z within 5 s undoes the most recent correction."""
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertIn("привіт", self._typed_str())

        # Reset history to track undo output only
        self.ctrl.history.clear()
        # Ctrl+Z is delivered by pynput as char '\x1a'
        self.core.on_press(SimpleNamespace(char='\x1a'))
        typed_after_undo = self._typed_str()
        self.assertIn("ghbdsn", typed_after_undo,
                      f"Undo should retype original. Got: '{typed_after_undo}'")

    def test_undo_clears_last_correction(self):
        """After undo, last_correction is None (no double-undo)."""
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.core.on_press(SimpleNamespace(char='\x1a'))
        self.assertIsNone(self.core.last_correction,
                          "last_correction must be None after undo")

    def test_undo_expires_after_5s(self):
        """Ctrl+Z more than 5 s after correction does NOT undo."""
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        # Back-date the correction timestamp
        self.core.last_correction['ts'] = time.time() - 10
        self.ctrl.history.clear()
        self.core.on_press(SimpleNamespace(char='\x1a'))
        # Nothing should have been retyped
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Undo fired after 5-second window had expired")

    # ──────────────────────────────────────────────────────────────────
    # Per-app disable
    # ──────────────────────────────────────────────────────────────────

    def test_per_app_disable_skips_correction(self):
        """Correction is skipped when the foreground app is in disabled_apps."""
        self.core.disabled_apps = ['keepass.exe']
        self.core._app_detector = lambda: 'keepass.exe'
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Correction should be skipped for disabled app")

    def test_per_app_disable_allows_other_apps(self):
        """Correction still fires for apps NOT in the disabled list."""
        self.core.disabled_apps = ['keepass.exe']
        self.core._app_detector = lambda: 'notepad.exe'
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertIn("привіт", self._typed_str(),
                      "Correction should fire for apps not on the disabled list")

    # ──────────────────────────────────────────────────────────────────
    # Ukrainian layout variant (Standard vs Enhanced)
    # ──────────────────────────────────────────────────────────────────

    def test_standard_variant_backtick_maps_to_apostrophe(self):
        """Standard layout: backtick (EN) → ' (apostrophe) in Ukrainian."""
        mapper = LayoutMapper(variant='standard')
        result = mapper.to_ukrainian('`')
        self.assertEqual(result, "'",
                         f"Standard: backtick should map to apostrophe, got '{result}'")

    def test_enhanced_variant_backtick_maps_to_ghe_upturn(self):
        """Enhanced layout: backtick (EN) → ґ in Ukrainian."""
        mapper = LayoutMapper(variant='enhanced')
        result = mapper.to_ukrainian('`')
        self.assertEqual(result, 'ґ',
                         f"Enhanced: backtick should map to ґ, got '{result}'")

    def test_set_variant_rebuilds_tables(self):
        """set_variant() switches the active translation table in-place."""
        mapper = LayoutMapper(variant='standard')
        self.assertEqual(mapper.to_ukrainian('`'), "'")
        mapper.set_variant('enhanced')
        self.assertEqual(mapper.to_ukrainian('`'), 'ґ')
        mapper.set_variant('standard')
        self.assertEqual(mapper.to_ukrainian('`'), "'")

    # ──────────────────────────────────────────────────────────────────
    # Whitelist
    # ──────────────────────────────────────────────────────────────────

    def test_whitelist_prevents_correction(self):
        """A whitelisted word is never corrected even if it matches wrong-layout."""
        # 'ghbdsn' would normally correct to 'привіт'
        self.core.whitelist = ['ghbdsn']
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Whitelisted word should not be corrected")

    def test_whitelist_case_insensitive(self):
        """Whitelist check is case-insensitive."""
        self.core.whitelist = ['GHBDSN']
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertFalse(any(e[0] == 'type' for e in self.ctrl.history),
                         "Whitelist should match case-insensitively")

    # ──────────────────────────────────────────────────────────────────
    # Notification callback
    # ──────────────────────────────────────────────────────────────────

    def test_notify_callback_fires_on_correction(self):
        """notify_callback is called with the correction message after each correction."""
        notifications = []
        self.core.notify_callback = lambda msg: notifications.append(msg)
        self.core.notifications_enabled = True

        self._type("ghbdsn")
        self.core.on_press(Key.space)

        self.assertEqual(len(notifications), 1,
                         f"Expected 1 notification, got {len(notifications)}")
        self.assertIn("привіт", notifications[0])

    def test_notify_callback_suppressed_when_disabled(self):
        """No notification when notifications_enabled = False."""
        notifications = []
        self.core.notify_callback = lambda msg: notifications.append(msg)
        self.core.notifications_enabled = False

        self._type("ghbdsn")
        self.core.on_press(Key.space)

        self.assertEqual(len(notifications), 0,
                         "Notification should not fire when disabled")

    # ──────────────────────────────────────────────────────────────────
    # Daily correction counter
    # ──────────────────────────────────────────────────────────────────

    def test_correction_counter_increments(self):
        """correction_count increases by 1 for each correction."""
        import datetime
        self.core.correction_date = datetime.date.today().isoformat()
        self.core.correction_count = 0

        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertEqual(self.core.correction_count, 1)

        self.core.buffer = []
        self.ctrl.history.clear()
        self._type("ghbdsn")
        self.core.on_press(Key.space)
        self.assertEqual(self.core.correction_count, 2)

    def test_correction_counter_resets_on_new_day(self):
        """correction_count resets to 1 when the calendar day changes."""
        self.core.correction_date = '2000-01-01'  # simulate yesterday
        self.core.correction_count = 99

        self._type("ghbdsn")
        self.core.on_press(Key.space)

        self.assertEqual(self.core.correction_count, 1,
                         "Counter should reset to 1 on a new calendar day")


if __name__ == '__main__':
    unittest.main()
