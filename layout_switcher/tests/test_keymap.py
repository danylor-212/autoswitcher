from keymap import KeyMap, vk_to_en_char


def test_vk_letters():
    assert vk_to_en_char(0x41, shift=False) == 'a'
    assert vk_to_en_char(0x41, shift=True) == 'A'
    assert vk_to_en_char(0x5A, shift=False) == 'z'


def test_vk_caps_lock_inverts_letters_only():
    assert vk_to_en_char(0x41, shift=False, caps=True) == 'A'
    assert vk_to_en_char(0x41, shift=True, caps=True) == 'a'
    # digits unaffected by caps
    assert vk_to_en_char(0x31, shift=False, caps=True) == '1'
    assert vk_to_en_char(0x31, shift=True, caps=True) == '!'


def test_vk_oem_keys():
    assert vk_to_en_char(0xBC, shift=False) == ','
    assert vk_to_en_char(0xBE, shift=False) == '.'
    assert vk_to_en_char(0xDE, shift=False) == "'"
    assert vk_to_en_char(0xC0, shift=False) == '`'


def test_vk_non_text_key():
    assert vk_to_en_char(0x70, shift=False) is None  # F1


def test_round_trip_standard():
    km = KeyMap('standard')
    assert km.to_ukrainian('ghbdsn') == 'привіт'
    assert km.to_english('привіт') == 'ghbdsn'
    assert km.to_ukrainian('`') == "'"          # backtick → apostrophe


def test_enhanced_variant():
    km = KeyMap('enhanced')
    assert km.to_ukrainian('`') == 'ґ'
    km.set_variant('standard')
    assert km.to_ukrainian('`') == "'"


def test_punct_keys_map_to_letters():
    km = KeyMap()
    assert km.to_ukrainian(',elt') == 'буде'    # ',' is б on UK layout
    assert km.to_ukrainian('.') == 'ю'
