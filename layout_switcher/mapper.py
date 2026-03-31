
# mapper.py

class LayoutMapper:
    """Maps characters between English and Ukrainian keyboard layouts.

    Two Ukrainian layout variants are supported:
        standard  (KBDUR.DLL)  — traditional ЙЦУКЕН, backtick → ' (apostrophe)
        enhanced  (KBDUR1.DLL) — backtick → ґ / Ґ, adds Ukrainian Ґ character

    Call set_variant() at runtime to switch without recreating the object.
    """

    # ── Layout strings (positional — must match en_layout length exactly) ────
    EN_LOWER    = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
    EN_UPPER    = "QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?~"
    EN_SPECIAL  = "@#$^&"

    # Standard: backtick → ' (apostrophe), Shift+backtick → ₴
    _UK_STD_LOWER = "йцукенгшщзхїфівапролджєячсмитьбю.'"
    _UK_STD_UPPER = "ЙЦУКЕНГШЩЗХЇФІВАПРОЛДЖЄЯЧСМИТЬБЮ,₴"

    # Enhanced: backtick → ґ, Shift+backtick → Ґ
    _UK_ENH_LOWER = "йцукенгшщзхїфівапролджєячсмитьбю.ґ"
    _UK_ENH_UPPER = "ЙЦУКЕНГШЩЗХЇФІВАПРОЛДЖЄЯЧСМИТЬБЮ,Ґ"

    # Same for both variants (@ # $ ^ & → " № ; : ?)
    _UK_SPECIAL   = "\"№;:?"

    def __init__(self, variant: str = 'standard'):
        self.en_layout = self.EN_LOWER + self.EN_UPPER + self.EN_SPECIAL
        self.variant   = variant
        self._build_tables()

    def _build_tables(self):
        """Build (or rebuild) translation tables for the current variant."""
        if self.variant == 'enhanced':
            uk_lower = self._UK_ENH_LOWER
            uk_upper = self._UK_ENH_UPPER
        else:
            uk_lower = self._UK_STD_LOWER
            uk_upper = self._UK_STD_UPPER

        self.uk_layout  = uk_lower + uk_upper + self._UK_SPECIAL
        self.ukr_to_eng = str.maketrans(self.uk_layout, self.en_layout)
        self.eng_to_ukr = str.maketrans(self.en_layout, self.uk_layout)
        self.en_chars   = set(self.en_layout)
        self.uk_chars   = set(self.uk_layout)

    def set_variant(self, variant: str):
        """Switch between 'standard' and 'enhanced' Ukrainian layouts.

        Rebuilds all translation tables in-place — thread-safe as long as
        callers use the GIL (pure Python dict/str operations).
        """
        self.variant = variant
        self._build_tables()

    def to_english(self, text: str) -> str:
        return text.translate(self.ukr_to_eng)

    def to_ukrainian(self, text: str) -> str:
        return text.translate(self.eng_to_ukr)

    def is_english_chars(self, text: str) -> bool:
        if not text:
            return False
        count = sum(1 for c in text if c in self.en_chars)
        return count > len(text) * 0.5

    def is_ukrainian_chars(self, text: str) -> bool:
        if not text:
            return False
        count = sum(1 for c in text if c in self.uk_chars)
        return count > len(text) * 0.5
