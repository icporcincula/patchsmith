import unittest
from labels import slugify

class LabelsTest(unittest.TestCase):
    def test_words(self):
        self.assertEqual(slugify("  Hello, WORLD!  "), "hello-world")
    def test_separators(self):
        self.assertEqual(slugify("one___two -- three"), "one-two-three")
    def test_empty(self):
        self.assertEqual(slugify(" ! "), "")
    def test_ascii_only(self):
        self.assertEqual(slugify("café 42"), "caf-42")
