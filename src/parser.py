import html
import json
import logging
import re

from bs4 import BeautifulSoup


LOGGER = logging.getLogger("ps5-watcher")


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def parse_page(html_text, product):
    if not html_text or not html_text.strip():
        return None

    soup = BeautifulSoup(html_text, "html.parser")
    result = {
        "title": product["name"],
        "price": "499,99",
        "currency": "EUR",
        "url": product["url"],
        "sku": product["sku"],
        "image": None,
        "availability": None,
        "button_type": None,
        "visible_text": None,
    }

    title_meta = soup.find("meta", attrs={"name": "name"})
    if title_meta and title_meta.get("content"):
        result["title"] = title_meta["content"]

    image_meta = soup.find("meta", attrs={"name": "image"})
    if image_meta and image_meta.get("content"):
        result["image"] = image_meta["content"]

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "")
        except (json.JSONDecodeError, TypeError):
            continue

        for item in _walk_json(data):
            item_sku = item.get("sku")
            offers = item.get("offers")
            if item_sku == product["sku"] or (
                isinstance(item_sku, str) and item_sku.startswith(product["sku"].split("-E", 1)[0])
            ):
                if isinstance(offers, dict):
                    if offers.get("price"):
                        result["price"] = str(offers["price"]).replace(".", ",")
                    if offers.get("priceCurrency"):
                        result["currency"] = offers["priceCurrency"]
                    if offers.get("availability"):
                        result["availability"] = offers["availability"]
                    if offers.get("url"):
                        result["url"] = offers["url"]
                if item.get("image"):
                    image = item["image"]
                    result["image"] = image[0] if isinstance(image, list) else image

    normalized = html.unescape(html_text).replace("\\\"", "\"")
    sku_index = normalized.find(product["sku"])
    if sku_index >= 0:
        window = normalized[max(0, sku_index - 4000):sku_index + 4000]
        type_match = re.search(r'"type"\s*:\s*"([^"]+)"', window)
        if type_match:
            result["button_type"] = type_match.group(1)

        cta_match = re.search(r"GameCTA.*?" + re.escape(product["sku"]) + r".*?\}", window)
        if cta_match:
            cta = cta_match.group(0)
            type_match = re.search(r'"type"\s*:\s*"([^"]+)"', cta)
            if type_match:
                result["button_type"] = type_match.group(1)

    for element in soup.find_all(attrs={"data-qa": re.compile(r"mfeCtaMain#offer.*#finalPrice")}):
        text = element.get_text(" ", strip=True)
        if text:
            result["visible_text"] = text
            break

    LOGGER.info(
        "Signaux bruts | SKU=%s | availability=%r | type=%r | text=%r",
        product["sku"],
        result["availability"],
        result["button_type"],
        result["visible_text"],
    )
    return result
