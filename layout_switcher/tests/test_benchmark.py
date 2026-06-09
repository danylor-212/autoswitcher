# Frequency-weighted quality benchmark over the real dictionaries.
#
# These are the measurements that condemned v1 (1.74% of correctly-typed
# Ukrainian destroyed). The ceilings below make any regression of the
# decision rule a test failure.
#
# Scenarios:
#   A  correct Ukrainian typed in UK layout   → corrections are FALSE POSITIVES
#   B  correct English typed in EN layout     → corrections are FALSE POSITIVES
#   C  Ukrainian intended, EN layout active   → corrections are HITS (recall)
#   D  English intended, UK layout active     → corrections are HITS (recall)

import os

import pytest

from engine import decide
from keymap import KeyMap

_DICT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'dictionaries')
_N = 8000  # top-N words per language (frequency-ranked)


def _load(name, n):
    out = []
    with open(os.path.join(_DICT, name), encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                out.append((parts[0], int(parts[1])))
            if len(out) >= n:
                break
    return out


@pytest.fixture(scope='module')
def km():
    return KeyMap()


@pytest.fixture(scope='module')
def uk_words():
    return _load('freq_uk_clean.txt', _N)


@pytest.fixture(scope='module')
def en_words():
    return _load('freq_en.txt', _N)


def _weighted_rate(rows):
    """rows: [(weight, flag)] → weighted share where flag is True."""
    total = sum(w for w, _ in rows)
    hit = sum(w for w, f in rows if f)
    return hit / total if total else 0.0


def test_A_correct_ukrainian_survives_uk_layout(lexicon, km, uk_words):
    rows = []
    destroyed = []
    for word, count in uk_words:
        en_token = km.to_english(word)
        d = decide(en_token, 'UK', lex=lexicon, keymap=km)
        fp = d.action != 'none'
        rows.append((count, fp))
        if fp:
            destroyed.append((word, d.replacement, count))
    rate = _weighted_rate(rows)
    worst = sorted(destroyed, key=lambda x: -x[2])[:8]
    assert rate < 0.003, f"{rate:.4%} of Ukrainian destroyed; worst: {worst}"


def test_B_correct_english_survives_en_layout(lexicon, km, en_words):
    rows = []
    destroyed = []
    for word, count in en_words:
        d = decide(word, 'EN', lex=lexicon, keymap=km)
        fp = d.action != 'none'
        rows.append((count, fp))
        if fp:
            destroyed.append((word, d.replacement, count))
    rate = _weighted_rate(rows)
    worst = sorted(destroyed, key=lambda x: -x[2])[:8]
    assert rate < 0.0005, f"{rate:.4%} of English destroyed; worst: {worst}"


def test_C_ukrainian_in_en_layout_gets_fixed(lexicon, km, uk_words):
    rows = []
    missed = []
    for word, count in uk_words:
        en_token = km.to_english(word)
        d = decide(en_token, 'EN', lex=lexicon, keymap=km)
        hit = d.action == 'switch' and d.replacement == word
        rows.append((count, hit))
        if not hit:
            missed.append((word, en_token, count))
    recall = _weighted_rate(rows)
    worst = sorted(missed, key=lambda x: -x[2])[:8]
    assert recall > 0.93, f"recall {recall:.4%}; top misses: {worst}"


def test_D_english_in_uk_layout_gets_fixed(lexicon, km, en_words):
    rows = []
    missed = []
    for word, count in en_words:
        d = decide(word, 'UK', lex=lexicon, keymap=km)
        hit = d.action == 'switch' and d.replacement == word
        rows.append((count, hit))
        if not hit:
            missed.append((word, count))
    recall = _weighted_rate(rows)
    worst = sorted(missed, key=lambda x: -x[1])[:8]
    assert recall > 0.93, f"recall {recall:.4%}; top misses: {worst}"
