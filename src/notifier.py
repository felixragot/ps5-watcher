import html
import json
import logging
import time
from urllib.parse import urlsplit, urlunsplit

import requests


LOGGER = logging.getLogger("ps5-watcher")
API_ROOT = "https://api.telegram.org"
MAX_PHOTO_BYTES = 5 * 1024 * 1024


def escape(value, quote=False):
    return html.escape(str(value), quote=quote)


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


def _resized_image_url(image_url):
    parts = urlsplit(image_url)
    if parts.hostname and parts.hostname.lower() == "gmedia.playstation.com":
        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                "$wid=800&$hei=800&$fit=constrain&$fmt=jpg",
                "",
            )
        )
    return image_url


def _download_photo(image_url):
    response = requests.get(
        _resized_image_url(image_url),
        headers={"Accept": "image/jpeg,image/png"},
        timeout=(10, 30),
        stream=True,
    )
    try:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type not in ("image/jpeg", "image/png"):
            raise ValueError(f"Format d'image non pris en charge: {content_type or 'inconnu'}")

        image = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            image.extend(chunk)
            if len(image) > MAX_PHOTO_BYTES:
                raise ValueError("Image trop volumineuse (limite 5 Mio)")
        if not image:
            raise ValueError("Image vide")

        extension = "jpg" if content_type == "image/jpeg" else "png"
        return f"produit.{extension}", bytes(image), content_type
    finally:
        response.close()


def _post(token, method, payload, files=None):
    delays = (5, 15)
    for attempt in range(3):
        try:
            post_arguments = {"timeout": (10, 20)}
            if files:
                multipart_payload = dict(payload)
                if isinstance(multipart_payload.get("reply_markup"), dict):
                    multipart_payload["reply_markup"] = json.dumps(
                        multipart_payload["reply_markup"],
                        ensure_ascii=False,
                    )
                post_arguments.update(data=multipart_payload, files=files)
            else:
                post_arguments["json"] = payload
            response = requests.post(f"{API_ROOT}/bot{token}/{method}", **post_arguments)
            if response.status_code == 429:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
                LOGGER.warning("Telegram 429, nouvel essai dans %d s", retry_after)
                time.sleep(retry_after)
                continue
            if response.status_code >= 400:
                try:
                    description = response.json().get("description", "aucun détail fourni")
                except ValueError:
                    description = "réponse non JSON"
                LOGGER.warning("Telegram HTTP %d (%s): %s", response.status_code, method, description)
                if response.status_code < 500:
                    return False
                if attempt < 2:
                    time.sleep(delays[attempt])
                    continue
                return False
            data = response.json()
            if not data.get("ok"):
                LOGGER.warning(
                    "Telegram a refusé %s: %s",
                    method,
                    data.get("description", "aucun détail fourni"),
                )
                return False
            return True
        except (requests.RequestException, ValueError) as exc:
            LOGGER.warning(
                "Envoi Telegram échoué (essai %d/3, %s)",
                attempt + 1,
                type(exc).__name__,
            )
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
        try:
            photo = _download_photo(parsed["image"])
        except (requests.RequestException, ValueError) as exc:
            LOGGER.warning("Téléchargement de l'image échoué (%s): %s", type(exc).__name__, exc)
        else:
            photo_payload = {
                "chat_id": chat_id,
                "parse_mode": "HTML",
                "caption": text,
                "reply_markup": markup,
                "disable_web_page_preview": False,
            }
            photo_file = {"photo": photo}
            if _post(token, "sendPhoto", photo_payload, files=photo_file):
                return True
            LOGGER.warning("Échec de sendPhoto, tentative avec sendMessage")

    return _post(token, "sendMessage", payload)
