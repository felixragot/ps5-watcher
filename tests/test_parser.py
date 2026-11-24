from pathlib import Path
import unittest

from src.parser import parse_page
from src.status import classify_signals


SKU = "PSD001-PSDE01929_59-PS5CONSOLEHB2OYE-E000Y5GPO"


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.product = {
            "name": "Console PlayStation®5 - 1 To",
            "url": "https://www.playstation.com/fr-fr/ps5/1-tb-disc/product/PSD001-PSDE01929_59-PS5CONSOLEHB2OYE/",
            "sku": SKU,
        }

    def test_parses_unavailable_fixture(self):
        html = """
        <html><head>
        <meta name="name" content="Console PlayStation®5 - 1 To">
        <meta name="image" content="https://gmedia.playstation.com/test.jpg">
        </head><body>
        <script type="application/ld+json">{"@type":"Product","sku":"PSD001-PSDE01929_59-PS5CONSOLEHB2OYE-E000Y5GPO","offers":{"price":"649.99","priceCurrency":"EUR","availability":"https://schema.org/OutOfStock","url":"https://example.test/ps5"}}</script>
        <div>{"GameCTA":{"sku":"PSD001-PSDE01929_59-PS5CONSOLEHB2OYE-E000Y5GPO","type":"UNAVAILABLE"}}</div>
        <div data-qa="mfeCtaMain#offer0#finalPrice">Non disponible à l'achat</div>
        </body></html>
        """
        parsed = parse_page(html, self.product)
        self.assertEqual(parsed["availability"], "https://schema.org/OutOfStock")
        self.assertEqual(parsed["button_type"], "UNAVAILABLE")
        self.assertEqual(classify_signals(parsed), "INDISPONIBLE")

    def test_parses_available_fixture(self):
        html = """
        <html><head><meta name="name" content="Console PS5"></head><body>
        <script type="application/ld+json">{"@type":"Product","sku":"PSD001-PSDE01929_59-PS5CONSOLEHB2OYE-E000Y5GPO","offers":{"price":"649.99","priceCurrency":"EUR","availability":"https://schema.org/InStock","url":"https://example.test/ps5"}}</script>
        <div>{"GameCTA":{"sku":"PSD001-PSDE01929_59-PS5CONSOLEHB2OYE-E000Y5GPO","type":"ADD_TO_CART"}}</div>
        <div data-qa="mfeCtaMain#offer0#finalPrice">Ajouter au panier</div>
        </body></html>
        """
        parsed = parse_page(html, self.product)
        self.assertEqual(parsed["availability"], "https://schema.org/InStock")
        self.assertEqual(parsed["button_type"], "ADD_TO_CART")
        self.assertEqual(classify_signals(parsed), "DISPONIBLE")

    def test_parses_escaped_nextjs_gamecta_fixture(self):
        fixture_path = Path(__file__).parent / "fixtures" / "nextjs_gamecta_unavailable.html"
        html = fixture_path.read_text(encoding="utf-8")
        parsed = parse_page(html, self.product)
        self.assertEqual(parsed["button_type"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
