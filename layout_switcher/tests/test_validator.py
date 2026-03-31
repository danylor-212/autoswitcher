
import unittest
import sys
import os
import inspect

# Monkey-patch inspect for pymorphy2 (mocking context)
if not hasattr(inspect, 'getargspec'):
    def getargspec(func):
        spec = inspect.getfullargspec(func)
        return (spec.args, spec.varargs, spec.varkw, spec.defaults)
    inspect.getargspec = getargspec

# Create path to source code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator import DictionaryValidator

class TestValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize once to save time loading dicts
        cls.validator = DictionaryValidator()

    def test_english_words(self):
        self.assertTrue(self.validator.is_english("hello"))
        self.assertTrue(self.validator.is_english("WORLD")) # Case insensitive
        self.assertTrue(self.validator.is_english("test"))

    def test_ukrainian_words(self):
        self.assertTrue(self.validator.is_ukrainian("привіт"))
        self.assertTrue(self.validator.is_ukrainian("світ"))
        # "баги" (bugs) - plural
        self.assertTrue(self.validator.is_ukrainian("баги"))

    def test_punctuation(self):
        # Should return true for word+punctuation if strip logic works
        self.assertTrue(self.validator.is_english("hello,"))
        self.assertTrue(self.validator.is_english("world!"))
        self.assertTrue(self.validator.is_ukrainian("привіт,"))
        
        # Test the user-reported "шптщку" -> "ignore" case with punctuation?
        # "ignore." should be valid English
        self.assertTrue(self.validator.is_english("ignore."))

    def test_nonsense(self):
        self.assertFalse(self.validator.is_english("ghbdsn"))
        self.assertFalse(self.validator.is_ukrainian("ghbdsn"))
        
        self.assertFalse(self.validator.is_english("руддщ"))
        # Note: "руддщ" might inadvertently be a word, but unlikely.
        
    def test_mixed_chars(self):
        # "dі" (latin d + cyrillic i)
        # Should probably be false for both unless dictionary has mix
        self.assertFalse(self.validator.is_english("dі"))
        
if __name__ == '__main__':
    unittest.main()
