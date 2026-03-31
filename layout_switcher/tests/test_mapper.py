
import unittest
import sys
import os

# Create path to source code
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapper import LayoutMapper

class TestMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = LayoutMapper()

    def test_basic_mapping(self):
        # "ghbdsn" -> "привіт"
        self.assertEqual(self.mapper.to_ukrainian("ghbdsn"), "привіт")
        # "ghbd" -> "прив"
        self.assertEqual(self.mapper.to_ukrainian("ghbd"), "прив")

    def test_reverse_mapping(self):
        # "привіт" -> "ghbdsn"
        self.assertEqual(self.mapper.to_english("привіт"), "ghbdsn")

    def test_special_chars(self):
        # Check comma mapping: "," -> "б"
        # User reported ",fub" -> "баги"
        self.assertEqual(self.mapper.to_ukrainian(","), "б")
        self.assertEqual(self.mapper.to_ukrainian(",fub"), "баги")
        
        # Check period: "." -> "ю"
        self.assertEqual(self.mapper.to_ukrainian("."), "ю")

    def test_integrity(self):
        # Check bi-directional consistency for all chars
        test_str = self.mapper.en_layout
        converted = self.mapper.to_ukrainian(test_str)
        restored = self.mapper.to_english(converted)
        self.assertEqual(test_str, restored)

if __name__ == '__main__':
    unittest.main()
