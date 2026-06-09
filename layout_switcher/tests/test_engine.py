# Decision-engine tests. Every confirmed v1 bug appears here as a regression
# case, marked with [v1-bug] in the docstring.

import pytest

from engine import decide
from keymap import KeyMap


@pytest.fixture(scope='module')
def km():
    return KeyMap()


def _decide(token, layout, lexicon, km, **kw):
    return decide(token, layout, lex=lexicon, keymap=km, **kw)


# ── The core promise ─────────────────────────────────────────────────────
def test_en_layout_wrong_word_corrected(lexicon, km):
    """Typing «привіт» with EN layout active → 'ghbdsn' becomes «привіт»."""
    d = _decide('ghbdsn', 'EN', lexicon, km)
    assert d.action == 'switch'
    assert d.app_text == 'ghbdsn'
    assert d.replacement == 'привіт'


def test_uk_layout_wrong_word_corrected(lexicon, km):
    """Typing 'hello' with UK layout active → «руддщ» becomes 'hello'."""
    d = _decide('hello', 'UK', lexicon, km)
    assert d.action == 'switch'
    assert d.app_text == 'руддщ'
    assert d.replacement == 'hello'


def test_valid_english_untouched(lexicon, km):
    d = _decide('hello', 'EN', lexicon, km)
    assert d.action == 'none'


def test_valid_ukrainian_untouched(lexicon, km):
    """[v1-bug] «руки» typed in UK layout was destroyed → 'herb' because the
    UK→EN branch never checked Ukrainian validity."""
    for token in ('herb', 'here', 'lys', 'xed'):  # руки руку дні чув
        d = _decide(token, 'UK', lexicon, km)
        assert d.action == 'none', \
            f"{token} → would destroy «{km.to_ukrainian(token)}»: {d}"


def test_bude_protected_in_uk_layout(lexicon, km):
    """[v1-bug] «буде» (keys ',elt') was replaced with ',elt' in UK layout."""
    d = _decide(',elt', 'UK', lexicon, km)
    assert d.action == 'none'


def test_bude_corrected_in_en_layout(lexicon, km):
    """[v1-bug, false negative] «буде» typed with EN layout showed ',elt' and
    was never corrected because 'elt' was in the junk dictionary."""
    d = _decide(',elt', 'EN', lexicon, km)
    assert d.action == 'switch'
    assert d.replacement == 'буде'


def test_dominance_overrules_morphology_anecdote(lexicon, km):
    """«туц» is morphology-valid (interjection) but 'new' dominates —
    the v1 anecdote still works without the blanket no-uk-check hack."""
    d = _decide('new', 'UK', lexicon, km)
    assert d.action == 'switch'
    assert d.replacement == 'new'


# ── Punctuation ──────────────────────────────────────────────────────────
def test_trailing_punct_reattached(lexicon, km):
    d = _decide('ghbdsn.', 'EN', lexicon, km)
    assert d.action == 'switch'
    assert d.app_text == 'ghbdsn.'
    assert d.replacement == 'привіт.'


def test_punct_that_is_a_letter_in_other_layout(lexicon, km):
    """',fub' → «баги»: the comma key is б — full-token reading wins."""
    d = _decide(',fub', 'EN', lexicon, km)
    assert d.action == 'switch'
    assert d.replacement == 'баги'


def test_pure_punct_ignored(lexicon, km):
    assert _decide('...', 'EN', lexicon, km).action == 'none'
    assert _decide('', 'EN', lexicon, km).action == 'none'


# ── Direction toggles ────────────────────────────────────────────────────
def test_direction_toggle_respected(lexicon, km):
    assert _decide('ghbdsn', 'EN', lexicon, km,
                   en_to_uk=False).action == 'none'
    assert _decide('hello', 'UK', lexicon, km,
                   uk_to_en=False).action == 'none'


# ── Unknown layout: conservative ─────────────────────────────────────────
def test_unknown_layout_corrects_unambiguous(lexicon, km):
    d = _decide('ghbdsn', 'unknown', lexicon, km)
    assert d.action == 'switch'


def test_unknown_layout_keeps_valid_english(lexicon, km):
    assert _decide('hello', 'unknown', lexicon, km).action == 'none'


# ── Short words ──────────────────────────────────────────────────────────
def test_short_junk_not_english(lexicon, km):
    """'nb'/'yt' style junk must not block «ти»/«не» corrections."""
    d = _decide('yt', 'EN', lexicon, km)     # «не»
    assert d.action == 'switch'
    assert d.replacement == 'не'
    d = _decide('nb', 'EN', lexicon, km)     # «ти»
    assert d.action == 'switch'
    assert d.replacement == 'ти'


def test_short_real_english_kept(lexicon, km):
    assert _decide('to', 'EN', lexicon, km).action == 'none'


# ── T9 ───────────────────────────────────────────────────────────────────
class _FakeT9:
    def correct_english(self, w):
        return 'hello' if w == 'helo' else None

    def correct_ukrainian(self, w):
        return None


def test_t9_preserves_trailing_punct(lexicon, km):
    """[v1-bug] T9 replaced 'helo.' with 'hello' — the period vanished."""
    d = _decide('helo.', 'EN', lexicon, km, t9_en=True, t9=_FakeT9())
    assert d.action == 't9'
    assert d.app_text == 'helo.'
    assert d.replacement == 'hello.'


def test_t9_skipped_when_word_valid(lexicon, km):
    d = _decide('hello', 'EN', lexicon, km, t9_en=True, t9=_FakeT9())
    assert d.action == 'none'
