# dictionaries.py — word validity and log-probabilities for both languages.
#
# V1 validated English against words_alpha.txt (370k unranked entries full of
# junk like 'elt'/'ult'/'lys' that both blocked real corrections and triggered
# false ones). V2 uses the frequency dictionaries that already ship for T9:
# an entry's presence (above a small count floor) is validity, and its count
# gives the probability used by the engine's dominance rule.

import os
import sys
import math
import inspect
import string

# pymorphy2 compatibility with Python 3.11+ (inspect.getargspec removed)
if not hasattr(inspect, 'getargspec'):
    def _getargspec(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = _getargspec

import pymorphy2

# Edge punctuation that may be stripped from words. Apostrophe is excluded:
# it is a legitimate mid-word char in English (don't) and Ukrainian (комп'ютер).
STRIP_PUNCT = string.punctuation.replace("'", "")

# Common 1-2 letter English words. The frequency list contains junk short
# tokens; only these count as valid at that length.
SHORT_EN = {
    'a', 'i', 'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'ha', 'he',
    'hi', 'if', 'in', 'is', 'it', 'me', 'my', 'no', 'of', 'oh', 'ok',
    'on', 'or', 'so', 'to', 'up', 'us', 'we',
}


def resource_path(*parts) -> str:
    """Path to a bundled data file (PyInstaller _MEIPASS or source dir)."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


def _load_freq(path: str) -> dict:
    """Load a 'word count' frequency file into {word: count}."""
    table = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    table[parts[0].lower()] = int(parts[1])
                except ValueError:
                    continue
    return table


def _load_words(path: str) -> set:
    words = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    words.add(w)
    return words


class Lexicon:
    """Validity + log10-probability for EN and UK words.

    A word can be valid three ways:
      - frequency dictionary entry (count >= MIN_COUNT)
      - custom dictionary entry (user/project-curated)
      - (UK only) known to pymorphy2 morphology

    log-probabilities use the frequency tables; words valid only by
    morphology/custom list get a floor probability so the engine's dominance
    rule can still overrule them when the other reading is overwhelmingly
    more likely.
    """

    EN_MIN_COUNT = 50_000      # freq_en counts span 16k .. 23e9
    UK_MIN_COUNT = 2           # subtitle corpus is small; keep almost all

    def __init__(self,
                 freq_en_path=None, freq_uk_path=None,
                 custom_en_path=None, custom_uk_path=None,
                 uk_morph_path=None):
        freq_en_path   = freq_en_path   or resource_path('dictionaries', 'freq_en.txt')
        freq_uk_path   = freq_uk_path   or resource_path('dictionaries', 'freq_uk_clean.txt')
        custom_en_path = custom_en_path or resource_path('dictionaries', 'en.txt')
        custom_uk_path = custom_uk_path or resource_path('dictionaries', 'uk.txt')

        self.freq_en = {w: c for w, c in _load_freq(freq_en_path).items()
                        if c >= self.EN_MIN_COUNT}
        self.freq_uk = {w: c for w, c in _load_freq(freq_uk_path).items()
                        if c >= self.UK_MIN_COUNT}
        if not self.freq_en or not self.freq_uk:
            # Refuse to run half-blind: a frozen build missing its data files
            # must fail loudly, not ship a switcher that destroys text.
            raise RuntimeError(
                f"Frequency dictionaries missing or empty "
                f"(en: {freq_en_path}, uk: {freq_uk_path})")

        self.custom_en = _load_words(custom_en_path)
        self.custom_uk = _load_words(custom_uk_path)

        morph_kwargs = {'lang': 'uk'}
        if uk_morph_path and os.path.exists(uk_morph_path):
            morph_kwargs['path'] = uk_morph_path
        self.uk_morph = pymorphy2.MorphAnalyzer(**morph_kwargs)

        self._total_en = sum(self.freq_en.values())
        self._total_uk = sum(self.freq_uk.values())
        # Floor: as likely as a count-1 word, minus a notch.
        self._floor_en = math.log10(1.0 / self._total_en) - 1.0
        self._floor_uk = math.log10(1.0 / self._total_uk) - 1.0

    # ── Validity ──────────────────────────────────────────────────────────
    def en_valid(self, word: str) -> bool:
        w = word.strip(STRIP_PUNCT).lower()
        if not w:
            return False
        if len(w) <= 2:
            return w in SHORT_EN
        return w in self.freq_en or w in self.custom_en

    def uk_valid(self, word: str) -> bool:
        w = word.strip(STRIP_PUNCT)
        if not w:
            return False
        if w.lower() in self.custom_uk:
            return True
        if len(w) <= 1:
            return w.lower() in self.freq_uk
        return self.uk_morph.word_is_known(w) or w.lower() in self.freq_uk

    # ── Log-probabilities (only meaningful for valid words) ──────────────
    def logp_en(self, word: str) -> float:
        w = word.strip(STRIP_PUNCT).lower()
        c = self.freq_en.get(w)
        if c is None:
            return self._floor_en
        return math.log10(c / self._total_en)

    def logp_uk(self, word: str) -> float:
        w = word.strip(STRIP_PUNCT).lower()
        c = self.freq_uk.get(w)
        if c is None:
            return self._floor_uk
        return math.log10(c / self._total_uk)
