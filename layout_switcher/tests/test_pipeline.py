# Pipeline tests: typing flows against a core with fake Win32 + injector.
# Events are fed synchronously through the same _handle() the worker runs.

import time

import pytest
from pynput.keyboard import Key, KeyCode

from injector import FakeInjector
from keymap import KeyMap
from pipeline import LayoutSwitcherCore

_VK = {c: 0x41 + i for i, c in enumerate('abcdefghijklmnopqrstuvwxyz')}
_VK.update({str(d): 0x30 + d for d in range(10)})
_VK.update({',': 0xBC, '.': 0xBE, "'": 0xDE, '`': 0xC0, '/': 0xBF,
            ';': 0xBA, '[': 0xDB, ']': 0xDD})


class Env:
    """Mutable fake environment: layout, focus, caps."""
    def __init__(self):
        self.layout = 'EN'
        self.hwnd = 100
        self.app = ''
        self.caps = False


@pytest.fixture(scope='module')
def shared_lexicon(lexicon):
    return lexicon


@pytest.fixture
def setup(shared_lexicon, tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    monkeypatch.setenv('APPDATA', str(tmp_path))
    env = Env()
    core = LayoutSwitcherCore(
        KeyMap(),
        lexicon=shared_lexicon,
        injector=FakeInjector(),
        layout_detector=lambda: env.layout,
        hwnd_detector=lambda: env.hwnd,
        app_detector=lambda: env.app,
        caps_detector=lambda: env.caps,
    )
    core.running = True
    return core, env


def press(core, env, key, mods=frozenset()):
    vk = getattr(key, 'vk', None)
    if vk is None and hasattr(key, 'value'):
        vk = key.value.vk
    core._handle(('key', key, vk, mods, env.caps, env.hwnd))


def type_word(core, env, text, mods=frozenset()):
    for ch in text:
        press(core, env, KeyCode(vk=_VK[ch]), mods)


def space(core, env, mods=frozenset()):
    press(core, env, KeyCode(vk=0x20), mods)


# ── Core flows ───────────────────────────────────────────────────────────
def test_wrong_layout_corrected_on_space(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    space(core, env)
    assert core.injector.calls == [(7, 'привіт ')]


def test_valid_word_untouched(setup):
    core, env = setup
    type_word(core, env, 'hello')
    space(core, env)
    assert core.injector.calls == []


def test_uk_layout_direction(setup):
    core, env = setup
    env.layout = 'UK'
    type_word(core, env, 'hello')        # screen shows «руддщ»
    space(core, env)
    assert core.injector.calls == [(6, 'hello ')]


# ── Buffer integrity (each closes a confirmed v1 corruption class) ──────
def test_focus_change_drops_word(setup):
    """[v1-bug] clicking into another field used to delete unrelated text."""
    core, env = setup
    type_word(core, env, 'ghbdsn')
    env.hwnd = 200                        # focus moved
    space(core, env)
    assert core.injector.calls == []


def test_mouse_click_resets_buffer(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    core._handle(('mouse',))
    space(core, env)
    assert core.injector.calls == []


def test_alt_tab_never_corrects(setup):
    """[v1-bug] Alt+Tab used to fire a correction into the next window."""
    core, env = setup
    type_word(core, env, 'ghbdsn')
    press(core, env, Key.tab, mods=frozenset({'alt'}))
    assert core.injector.calls == []
    space(core, env)                      # buffer must have been flushed too
    assert core.injector.calls == []


def test_ctrl_chord_not_buffered(setup):
    """[v1-bug] Ctrl+S used to push '\\x13' into the buffer."""
    core, env = setup
    type_word(core, env, 'ghb')
    press(core, env, KeyCode(vk=_VK['s']), mods=frozenset({'ctrl'}))
    type_word(core, env, 'dsn')
    space(core, env)
    assert core.injector.calls == [(7, 'привіт ')]


def test_enter_flushes_without_correcting_by_default(setup):
    """[v1-bug] Enter in chat apps double-sent the corrected message."""
    core, env = setup
    type_word(core, env, 'ghbdsn')
    press(core, env, Key.enter)
    assert core.injector.calls == []


def test_layout_switch_mid_word_drops(setup):
    core, env = setup
    type_word(core, env, 'ghb')
    env.layout = 'UK'
    type_word(core, env, 'dsn')
    space(core, env)
    assert core.injector.calls == []


def test_backspace_pops_buffer(setup):
    core, env = setup
    type_word(core, env, 'ghbdsnx')
    press(core, env, KeyCode(vk=0x08))    # backspace
    space(core, env)
    assert core.injector.calls == [(7, 'привіт ')]


def test_arrow_key_resets(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    press(core, env, Key.left)
    space(core, env)
    assert core.injector.calls == []


def test_disabled_master_toggle(setup):
    core, env = setup
    core.enabled = False
    type_word(core, env, 'ghbdsn')
    space(core, env)
    assert core.injector.calls == []


def test_per_app_disable(setup):
    core, env = setup
    core.disabled_apps = ['code.exe']
    env.app = 'code.exe'
    type_word(core, env, 'ghbdsn')
    space(core, env)
    assert core.injector.calls == []


# ── Undo / whitelist via revert shortcut ─────────────────────────────────
def alt2(core, env):
    press(core, env, KeyCode(vk=0x32), mods=frozenset({'alt'}))


def test_undo_restores_original(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    space(core, env)
    alt2(core, env)
    assert core.injector.calls == [(7, 'привіт '), (7, 'ghbdsn ')]
    assert core.last_correction is None


def test_undo_blocked_after_more_typing(setup):
    """[v1-bug] undo used to splice into text typed after the correction."""
    core, env = setup
    type_word(core, env, 'ghbdsn')
    space(core, env)
    type_word(core, env, 'is')
    alt2(core, env)
    assert core.injector.calls == [(7, 'привіт ')]   # no undo issued


def test_undo_expires(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    space(core, env)
    core.last_correction['ts'] -= 10
    alt2(core, env)
    # expired undo falls through to force-swap of (empty) buffer → no-op
    assert core.injector.calls == [(7, 'привіт ')]


def test_second_press_whitelists_canonically(setup):
    """[v1-bug] whitelist stored on-screen Cyrillic but compared the EN
    buffer, so whitelisting never prevented the same correction again."""
    core, env = setup
    env.layout = 'UK'
    type_word(core, env, 'hello')         # screen shows «руддщ» → corrected
    space(core, env)
    assert core.injector.calls == [(6, 'hello ')]
    alt2(core, env)                       # undo
    alt2(core, env)                       # whitelist
    assert 'hello' in [w.lower() for w in core.whitelist]
    # typing it again must NOT correct
    core.injector.calls.clear()
    type_word(core, env, 'hello')
    space(core, env)
    assert core.injector.calls == []


def test_force_swap_buffered_word(setup):
    core, env = setup
    type_word(core, env, 'ghbdsn')
    alt2(core, env)                       # no boundary yet → force swap
    assert core.injector.calls == [(6, 'привіт')]


# ── Listener-side filtering ──────────────────────────────────────────────
def test_injected_events_ignored(setup):
    core, env = setup
    core._on_press(KeyCode(vk=_VK['g']), injected=True)
    assert core._events.empty()


def test_whitelist_migration_from_cyrillic(setup, shared_lexicon):
    core, env = setup
    migrated = core._canonicalize_whitelist(['привіт', 'ghbdsn', 'baseword'])
    assert migrated == ['ghbdsn', 'baseword']
