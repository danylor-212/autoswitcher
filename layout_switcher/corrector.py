
import os
import sys
from symspellpy import SymSpell, Verbosity

class GrammarEngine:
    def __init__(self):
        # SymSpell configuration
        # max_dictionary_edit_distance=2 allows correcting "hll" -> "hello" (insert e, o) or "hllo" -> "hello"
        self.sym_spell_en = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        self.sym_spell_uk = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        
        self.is_loaded_en = False
        self.is_loaded_uk = False
        
        self._load_dictionaries()

    def _get_resource_path(self, filename):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, 'dictionaries', filename)

    def _load_dictionaries(self):
        path_en = self._get_resource_path('freq_en.txt')
        path_uk = self._get_resource_path('freq_uk.txt')
        
        # Load English
        if os.path.exists(path_en):
            print("Loading English T9 Dictionary...")
            if self.sym_spell_en.load_dictionary(path_en, term_index=0, count_index=1):
                self.is_loaded_en = True
                print("English T9 Loaded.")
            else:
                print("Failed to load English T9.")
        else:
            print(f"English T9 dict not found at {path_en}")

        # Load Ukrainian
        if os.path.exists(path_uk):
            print("Loading Ukrainian T9 Dictionary...")
            # uk_50k.txt is "word count" format (space separator matches default?)
            # SymSpell default separator is space.
            if self.sym_spell_uk.load_dictionary(path_uk, term_index=0, count_index=1, encoding="utf-8"):
                self.is_loaded_uk = True
                print("Ukrainian T9 Loaded.")
            else:
                print("Failed to load Ukrainian T9.")
        else:
            print(f"Ukrainian T9 dict not found at {path_uk}")

    def correct_english(self, word: str):
        if not self.is_loaded_en or not word:
            return None
            
        # 1. Check if word is already valid (distance 0)
        suggestions = self.sym_spell_en.lookup(word, Verbosity.TOP, max_edit_distance=0)
        if suggestions:
            return None # Already correct
            
        # 2. Check for corrections (distance 2)
        suggestions = self.sym_spell_en.lookup(word, Verbosity.TOP, max_edit_distance=2)
        if suggestions:
            best_term = suggestions[0].term
            # Preserve capitalisation of the first letter only —
            # capitalize() would lowercase everything after the first char,
            # breaking e.g. "HEllo" -> "Hello" instead of "Hello".
            if word[0].isupper():
                return best_term[0].upper() + best_term[1:]
            return best_term

        return None

    def correct_ukrainian(self, word: str):
        if not self.is_loaded_uk or not word:
            return None

        # 1. Check valid
        suggestions = self.sym_spell_uk.lookup(word, Verbosity.TOP, max_edit_distance=0)
        if suggestions:
            return None

        # 2. Correct
        suggestions = self.sym_spell_uk.lookup(word, Verbosity.TOP, max_edit_distance=2)
        if suggestions:
            best_term = suggestions[0].term
            if word[0].isupper():
                return best_term[0].upper() + best_term[1:]
            return best_term

        return None
