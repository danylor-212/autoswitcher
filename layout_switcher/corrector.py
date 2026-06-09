# corrector.py — T9-style typo correction via SymSpell.
#
# V2 changes: the two language paths share one implementation; the Ukrainian
# dictionary is the pymorphy2-filtered freq_uk_clean.txt (the raw
# OpenSubtitles list was ~25% Russian, so UK T9 could "correct" Ukrainian
# typos into Russian words).

from symspellpy import SymSpell, Verbosity

from dictionaries import resource_path


class GrammarEngine:
    def __init__(self):
        self._engines = {}
        for lang, fname in (('en', 'freq_en.txt'), ('uk', 'freq_uk_clean.txt')):
            sym = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
            path = resource_path('dictionaries', fname)
            if sym.load_dictionary(path, term_index=0, count_index=1,
                                   encoding='utf-8'):
                self._engines[lang] = sym

    def _correct(self, lang: str, word: str):
        sym = self._engines.get(lang)
        if not sym or not word:
            return None
        # Already a known word? Leave it alone.
        if sym.lookup(word, Verbosity.TOP, max_edit_distance=0):
            return None
        suggestions = sym.lookup(word, Verbosity.TOP, max_edit_distance=2)
        if not suggestions:
            return None
        best = suggestions[0].term
        # Preserve first-letter capitalisation only (capitalize() would
        # lowercase the rest, breaking 'HEllo' -> 'Hello').
        if word[0].isupper():
            return best[0].upper() + best[1:]
        return best

    def correct_english(self, word: str):
        return self._correct('en', word)

    def correct_ukrainian(self, word: str):
        return self._correct('uk', word)
