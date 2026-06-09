# keymap.py — physical-key capture and layout rendering.
#
# V2 captures Windows virtual-key codes (layout-independent) and derives the
# EN-layout character itself, instead of trusting pynput's key.char (which is
# translated through whatever layout the listener thread happened to cache at
# startup — Cyrillic for users whose default input language is Ukrainian).

# ── US-QWERTY virtual-key table: vk → (base_char, shifted_char) ──────────────
_VK_TABLE = {}
for _i in range(26):  # letters A–Z
    _VK_TABLE[0x41 + _i] = (chr(0x61 + _i), chr(0x41 + _i))
for _d, _s in zip("0123456789", ")!@#$%^&*("):  # digit row
    _VK_TABLE[0x30 + ord(_d) - ord('0')] = (_d, _s)
_VK_TABLE.update({
    0xBA: (';', ':'),   # VK_OEM_1
    0xBB: ('=', '+'),   # VK_OEM_PLUS
    0xBC: (',', '<'),   # VK_OEM_COMMA
    0xBD: ('-', '_'),   # VK_OEM_MINUS
    0xBE: ('.', '>'),   # VK_OEM_PERIOD
    0xBF: ('/', '?'),   # VK_OEM_2
    0xC0: ('`', '~'),   # VK_OEM_3
    0xDB: ('[', '{'),   # VK_OEM_4
    0xDC: ('\\', '|'),  # VK_OEM_5
    0xDD: (']', '}'),   # VK_OEM_6
    0xDE: ("'", '"'),   # VK_OEM_7
})

_LETTER_VKS = set(range(0x41, 0x5B))


def vk_to_en_char(vk: int, shift: bool, caps: bool = False):
    """EN-layout character for a virtual key, or None if not a text key.

    Caps Lock inverts the case of letter keys only (standard behaviour).
    """
    pair = _VK_TABLE.get(vk)
    if pair is None:
        return None
    if vk in _LETTER_VKS:
        return pair[1] if (shift != caps) else pair[0]
    return pair[1] if shift else pair[0]


class KeyMap:
    """EN↔UK rendering of the same physical key sequence.

    Two Ukrainian layout variants:
        standard (KBDUR.DLL)  — backtick → ' (apostrophe)
        enhanced (KBDUR1.DLL) — backtick → ґ / Ґ
    """

    EN_LOWER   = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
    EN_UPPER   = "QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?~"
    EN_SPECIAL = "@#$^&"

    _UK_STD_LOWER = "йцукенгшщзхїфівапролджєячсмитьбю.'"
    _UK_STD_UPPER = "ЙЦУКЕНГШЩЗХЇФІВАПРОЛДЖЄЯЧСМИТЬБЮ,₴"
    _UK_ENH_LOWER = "йцукенгшщзхїфівапролджєячсмитьбю.ґ"
    _UK_ENH_UPPER = "ЙЦУКЕНГШЩЗХЇФІВАПРОЛДЖЄЯЧСМИТЬБЮ,Ґ"
    _UK_SPECIAL   = "\"№;:?"

    def __init__(self, variant: str = 'standard'):
        self.set_variant(variant)

    def set_variant(self, variant: str):
        self.variant = variant
        if variant == 'enhanced':
            uk = self._UK_ENH_LOWER + self._UK_ENH_UPPER + self._UK_SPECIAL
        else:
            uk = self._UK_STD_LOWER + self._UK_STD_UPPER + self._UK_SPECIAL
        en = self.EN_LOWER + self.EN_UPPER + self.EN_SPECIAL
        self.eng_to_ukr = str.maketrans(en, uk)
        self.ukr_to_eng = str.maketrans(uk, en)

    def to_ukrainian(self, text: str) -> str:
        return text.translate(self.eng_to_ukr)

    def to_english(self, text: str) -> str:
        return text.translate(self.ukr_to_eng)
