import unittest
import formatting
import report

class RefactorTest(unittest.TestCase):
    def test_new_name(self):
        self.assertEqual(formatting.display_name("Ada", "Lovelace"), "Lovelace, Ada")
    def test_callers_updated(self):
        self.assertEqual(report.render_people([("Ada", "Lovelace")]), ["Lovelace, Ada"])
        self.assertNotIn("format_name", report.__dict__)
    def test_old_name_removed(self):
        self.assertFalse(hasattr(formatting, "format_name"))
