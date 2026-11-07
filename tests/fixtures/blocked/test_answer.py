import unittest
from answer import answer

class AnswerTest(unittest.TestCase):
    def test_answer(self):
        self.assertEqual(answer(), 5)
