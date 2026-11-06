import unittest

from scorer import best_score


class ScorerTest(unittest.TestCase):
    def test_best_score(self):
        self.assertEqual(best_score([3, 9, 4]), 9)

    def test_single(self):
        self.assertEqual(best_score([5]), 5)


if __name__ == "__main__":
    unittest.main()
