import unittest
from pricing import subtotal_cents
from invoice import invoice_cents

ITEMS = [{"price_cents": 125, "quantity": 3}, {"price_cents": 50, "quantity": 2}]

class InvoiceTest(unittest.TestCase):
    def test_quantity(self):
        self.assertEqual(subtotal_cents(ITEMS), 475)
    def test_shipping(self):
        self.assertEqual(invoice_cents(ITEMS, 75), 550)
    def test_empty(self):
        self.assertEqual(invoice_cents([], 75), 75)
