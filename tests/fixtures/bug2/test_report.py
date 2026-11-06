import unittest

from report import podium

PLAYERS = [
    {"name": "ann", "points": 10},
    {"name": "bo", "points": 30},
    {"name": "cy", "points": 20},
    {"name": "di", "points": 5},
]


class ReportTest(unittest.TestCase):
    def test_podium(self):
        self.assertEqual(podium(PLAYERS), ["bo", "cy", "ann"])


if __name__ == "__main__":
    unittest.main()
