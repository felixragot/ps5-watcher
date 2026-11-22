from pathlib import Path
import json
import os


ROOT_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = ROOT_DIR / "config" / "products.json"
STATE_FILE = ROOT_DIR / "state.json"

NEGATIVE_AVAILABILITY = ("outofstock", "soldout")
POSITIVE_AVAILABILITY = ("instock", "limitedavailability", "preorder")
NEGATIVE_TYPES = ("UNAVAILABLE", "NOT_AVAILABLE")
POSITIVE_TYPES = ("AVAILABLE", "ADD_TO_CART", "BUY_NOW", "BUY")
NEGATIVE_TEXT = ("non disponible à l'achat",)
POSITIVE_TEXT = ("ajouter au panier",)


def load_products():
    with PRODUCTS_FILE.open("r", encoding="utf-8") as file:
        products = json.load(file)
    if not isinstance(products, list):
        raise ValueError("La configuration doit être une liste de produits")
    for product in products:
        if not all(product.get(key) for key in ("name", "url", "sku")):
            raise ValueError("Chaque produit doit avoir name, url et sku")
    return products


def load_environment():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID sont requis "
            "(variables d'environnement ou Secrets GitHub Actions)"
        )
    return token, chat_id
