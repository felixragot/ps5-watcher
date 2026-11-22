import html
import logging
import time

import requests


LOGGER = logging.getLogger("ps5-watcher")
API_ROOT = "https://api.telegram.org"


def escape(value):
    return html.escape(str(value), quote=False)


def format_message(label, parsed, timestamp):
    title = escape(parsed["title"])
    price = escape(parsed["price"])
    currency = escape(parsed["currency"])
    sku = escape(parsed["sku"])
    url = escape(parsed["url"], quote=True)
    return (
        f"🛒 <b>{escape(label)}</b>\n"
        f"<b>{title}</b>\n"
        f"Prix : {price} {currency}\n"
        f"SKU : {sku}\n"
        f"Date : {escape(timestamp)}\n"
        f"🔗 {url}"
    )


def _post(token, method, payload):
    delays = (5, 15)
    for attempt in range(3):
        try:
            response = requests.post(
                f"{API_ROOT}/bot{token}/{method}",
                json=payload,
                timeout=(10, 20),
            )
            if response.status_code == 429:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
                LOGGER.warning("Telegram 429, nouvel essai dans %d s", retry_after)
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise RuntimeError(data)
            return True
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            LOGGER.warning("Envoi Telegram échoué (essai %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(delays[attempt])
    return False


def send_notification(token, chat_id, label, parsed, timestamp):
    text = format_message(label, parsed, timestamp)
    markup = {
        "inline_keyboard": [[{"text": "Acheter", "url": parsed["url"]}]]
    }
    payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "text": text,
        "reply_markup": markup,
        "disable_web_page_preview": False,
    }

    if parsed.get("image"):
        photo_payload = dict(payload)
        photo_payload["photo"] = parsed["image"]
        photo_payload.pop("text", None)
        photo_payload["caption"] = text
        if _post(token, "sendPhoto", photo_payload):
            return True
        LOGGER.warning("Échec de sendPhoto, tentative avec sendMessage")

    return _post(token, "sendMessage", payload)
