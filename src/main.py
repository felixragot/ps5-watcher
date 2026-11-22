import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import load_environment, load_products, STATE_FILE
from .fetcher import fetch_page
from .notifier import send_notification
from .parser import parse_page
from .state import load_state, save_state
from .status import classify_signals


LOGGER = logging.getLogger("ps5-watcher")
PARIS = ZoneInfo("Europe/Paris")
REMINDER_MINUTES = 30


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def parse_timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=PARIS)
        return parsed
    except (TypeError, ValueError):
        return None


def process_product(product, state, token=None, chat_id=None, dry_run=False):
    sku = product["sku"]
    previous = state.get(sku, {})
    previous_status = previous.get("status", "INDISPONIBLE")

    html_text = fetch_page(product["url"])
    if html_text is None:
        LOGGER.warning("Produit ignoré à cause d'un échec de récupération | SKU=%s", sku)
        return False

    parsed = parse_page(html_text, product)
    current_status = classify_signals(parsed) if parsed else "INCONNU"
    if parsed is None:
        parsed = {
            "title": product["name"],
            "price": "499,99",
            "currency": "EUR",
            "url": product["url"],
            "sku": sku,
            "image": None,
        }

    now = datetime.now(PARIS)
    timestamp = now.isoformat(timespec="seconds")
    last_message = parse_timestamp(previous.get("last_message"))
    reminder_due = (
        current_status == "DISPONIBLE"
        and (
            last_message is None
            or now >= last_message + timedelta(minutes=REMINDER_MINUTES)
        )
    )

    send = False
    label = None
    if previous_status == "INDISPONIBLE" and current_status in ("DISPONIBLE", "INCONNU"):
        send = True
        label = "Disponible" if current_status == "DISPONIBLE" else "Statut inconnu, vérifie la page"
    elif previous_status == "INCONNU" and current_status == "DISPONIBLE":
        send = True
        label = "Disponible"
    elif previous_status == "DISPONIBLE" and current_status == "DISPONIBLE" and reminder_due:
        send = True
        label = "Toujours disponible"

    if send:
        if dry_run:
            LOGGER.info("[DRY-RUN] Notification %s | SKU=%s", label, sku)
        else:
            if send_notification(token, chat_id, label, parsed, now.strftime("%d/%m/%Y %H:%M")):
                previous["last_message"] = timestamp
            else:
                LOGGER.error("Notification échouée | SKU=%s | le minuteur reste inchangé", sku)

    state[sku] = {
        "status": current_status,
        "last_message": previous.get("last_message"),
    }
    LOGGER.info(
        "Résumé produit | %s | précédent=%s | courant=%s | notification=%s",
        product["name"],
        previous_status,
        current_status,
        label or "aucune",
    )
    return True


def main(argv=None):
    configure_logging()
    parser = argparse.ArgumentParser(description="Surveillance de disponibilité PlayStation")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-notify", action="store_true")
    parser.add_argument("--jitter", type=int, default=30)
    args = parser.parse_args(argv)

    try:
        products = load_products()
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        LOGGER.critical("Configuration invalide: %s", exc)
        return 2

    token = chat_id = None
    if not args.dry_run:
        try:
            token, chat_id = load_environment()
        except RuntimeError as exc:
            LOGGER.critical("%s", exc)
            return 2

    jitter = random.uniform(0, max(0, args.jitter))
    LOGGER.info("Jitter initial: %.1f s", jitter)
    time.sleep(jitter)

    state = load_state(STATE_FILE)
    successful_cycle = True

    for index, product in enumerate(products):
        try:
            if args.force_notify:
                sku = product["sku"]
                parsed = {
                    "title": product["name"],
                    "price": "499,99",
                    "currency": "EUR",
                    "url": product["url"],
                    "sku": sku,
                    "image": None,
                }
                LOGGER.info("[FORCE-NOTIFY] Produit simulé disponible | SKU=%s", sku)
                if args.dry_run:
                    LOGGER.info("[DRY-RUN] Notification Disponible | SKU=%s", sku)
                else:
                    now = datetime.now(PARIS)
                    if send_notification(
                        token,
                        chat_id,
                        "Disponible",
                        parsed,
                        now.strftime("%d/%m/%Y %H:%M"),
                    ):
                        state[sku] = {
                            "status": "DISPONIBLE",
                            "last_message": now.isoformat(timespec="seconds"),
                        }
                    else:
                        LOGGER.error("Notification forcée échouée | SKU=%s", sku)
            else:
                if not process_product(product, state, token, chat_id, args.dry_run):
                    successful_cycle = False
        except Exception as exc:
            LOGGER.exception("Erreur isolée pour le produit %s: %s", product["sku"], exc)
            successful_cycle = False

        if index < len(products) - 1:
            time.sleep(random.uniform(3, 8))

    if not save_state(STATE_FILE, state):
        LOGGER.critical("Échec de sauvegarde de l'état")
        return 2

    LOGGER.info("Cycle terminé | produits=%d", len(products))
    return 0 if successful_cycle else 1


if __name__ == "__main__":
    sys.exit(main())
