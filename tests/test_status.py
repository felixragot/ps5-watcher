import unittest

from src.status import classify_signals


class StatusTests(unittest.TestCase):
    def test_out_of_stock(self):
        parsed = {
            "availability": "https://schema.org/OutOfStock",
            "button_type": "UNAVAILABLE",
            "visible_text": "Non disponible à l'achat",
        }
        self.assertEqual(classify_signals(parsed), "INDISPONIBLE")

    def test_in_stock(self):
        parsed = {
            "availability": "https://schema.org/InStock",
            "button_type": "ADD_TO_CART",
            "visible_text": "Ajouter au panier",
        }
        self.assertEqual(classify_signals(parsed), "DISPONIBLE")

    def test_no_signal_is_unknown(self):
        self.assertEqual(classify_signals({"availability": None, "button_type": None, "visible_text": None}), "INCONNU")

    def test_conflicting_signals_are_unknown(self):
        parsed = {
            "availability": "https://schema.org/InStock",
            "button_type": "UNAVAILABLE",
            "visible_text": None,
        }
        self.assertEqual(classify_signals(parsed), "INCONNU")


if __name__ == "__main__":
    unittest.main()
