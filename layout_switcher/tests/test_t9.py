
import sys
import os

# Fix imports path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corrector import GrammarEngine

def test_grammar():
    print("Loading Grammar Engine...")
    grammar = GrammarEngine()
    
    if not grammar.is_loaded_en:
        print("FAIL: English dict not loaded.")
        return
        
    if not grammar.is_loaded_uk:
        print("FAIL: Ukrainian dict not loaded.")
        return

    # test corrections
    cases = [
        ("hllo", "hello"), # missing letter
        ("thsi", "this"),  # transposition (distance 2)
        ("gud", "good"),   # substitution
        ("привт", "привіт"), # missing letter ukr
    ]
    
    print("\nRunning T9 Test Cases:")
    for inp, expected in cases:
        # Determine language
        if inp[0] in "abcdefghijklmnopqrstuvwxyz":
            res = grammar.correct_english(inp)
            lang = "EN"
        else:
            res = grammar.correct_ukrainian(inp)
            lang = "UK"
            
        print(f"[{lang}] In: '{inp}' -> Out: '{res}' | Expected: '{expected}'")
        
        if res == expected:
            print("  PASS")
        else:
            print("  FAIL")

    # Negative tests (valid words should be None)
    print("\nNegative Tests (Valid words):")
    valid_cases = ["hello", "привіт", "ignore"]
    for word in valid_cases:
        if word[0] in "abcdefghijklmnopqrstuvwxyz":
            res = grammar.correct_english(word)
        else:
            res = grammar.correct_ukrainian(word)
            
        if res is None:
            print(f"  PASS: '{word}' -> None")
        else:
            print(f"  FAIL: '{word}' -> '{res}' (Should be None)")

if __name__ == "__main__":
    test_grammar()
