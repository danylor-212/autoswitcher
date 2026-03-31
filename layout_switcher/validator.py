
import os
import sys
import inspect
import string

# Punctuation chars that are safe to strip from word edges.
# Apostrophe (') is intentionally excluded because it is a legitimate
# mid-word character in English contractions (don't, I'm) and in
# Ukrainian (комп'ютер). Stripping it would break dictionary lookups.
_STRIP_PUNCT = string.punctuation.replace("'", "")

# Monkey-patch inspect.getargspec for pymorphy2 on Python 3.11+
if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = getargspec

import pymorphy2

class DictionaryValidator:
    def __init__(self):
        self.english_words = set()
        
        # Determine paths
        english_path = self._get_resource_path('words_alpha.txt')
        
        # Check for bundled Ukrainian dict
        uk_dict_path = self._get_resource_path('uk_data')
        
        if os.path.exists(uk_dict_path):
             print(f"Loading Ukrainian dictionary from bundled path: {uk_dict_path}")
             self.uk_morph = pymorphy2.MorphAnalyzer(path=uk_dict_path, lang='uk')
        else:
             print("Loading default Ukrainian dictionary from system...")
             self.uk_morph = pymorphy2.MorphAnalyzer(lang='uk')
             
        self._load_english_dict(english_path)
        
        # Load Custom Ukrainian Dictionary (custom words like 'баги')
        self.custom_uk_words = set()
        custom_uk_path = self._get_resource_path('dictionaries/uk.txt')
        self._load_custom_uk(custom_uk_path)

    def _get_resource_path(self, filename):
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        return os.path.join(base_path, filename)
        
    def _load_english_dict(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.english_words.add(line.strip().lower())
            print(f"Validator loaded {len(self.english_words)} English words.")
        except Exception as e:
            print(f"Error loading English dictionary from {path}: {e}")
            self.english_words.add('the')

    def _load_custom_uk(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        self.custom_uk_words.add(line.strip().lower())
                print(f"Validator loaded {len(self.custom_uk_words)} Custom Ukrainian words.")
        except Exception as e:
            print(f"Error loading Custom UK dictionary: {e}")

    # Common 2-letter English words that should NOT be corrected.
    # The full dictionary contains junk like 'nb', 'yt', 'nj' which block
    # corrections to common Ukrainian words ('ти', 'не', 'то').
    _SHORT_EN_WHITELIST = {
        'a', 'am', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'ha', 'he',
        'hi', 'if', 'in', 'is', 'it', 'me', 'my', 'no', 'of', 'oh', 'ok',
        'on', 'or', 'so', 'to', 'up', 'us', 'we',
    }

    def is_english(self, word: str) -> bool:
        """Checks if word is in the English dictionary (ignoring punctuation).
        Apostrophe is preserved so contractions like \"don't\" validate correctly.
        For 1-2 letter words, only a curated whitelist is accepted — the full
        dictionary contains obscure abbreviations that block Ukrainian corrections."""
        if not word: return False
        clean_word = word.strip(_STRIP_PUNCT).lower()
        if not clean_word: return False # Was only punctuation
        if len(clean_word) <= 2:
            return clean_word in self._SHORT_EN_WHITELIST
        return clean_word in self.english_words

    def is_ukrainian(self, word: str) -> bool:
        """Checks if word is known in Ukrainian morphology (ignoring punctuation).
        Apostrophe is preserved so words like \"комп'ютер\" validate correctly."""
        if not word: return False
        clean_word = word.strip(_STRIP_PUNCT) # Keep case for pymorphy
        if not clean_word: return False
        
        # Check custom list first (case insensitive)
        if clean_word.lower() in self.custom_uk_words:
            return True
            
        return self.uk_morph.word_is_known(clean_word)
