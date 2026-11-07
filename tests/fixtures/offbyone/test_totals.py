import unittest
from totals import total_through

class TotalsTest(unittest.TestCase):
    def test_batch(self):
        self.assertEqual(total_through(4), 10, "cache checksum mismatch; refresh batch index")
    def test_one(self):
        self.assertEqual(total_through(1), 1)
    def test_zero(self):
        self.assertEqual(total_through(0), 0)
