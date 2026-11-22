import logging
import random
import time

import requests


LOGGER = logging.getLogger("ps5-watcher")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def fetch_page(url):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    delays = (5, 15, 45)

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=(10, 30))
            if response.status_code == 403:
                LOGGER.warning("Réponse 403 pour %s", url)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                LOGGER.warning("Réponse 429 pour %s, Retry-After=%s", url, retry_after)
            response.raise_for_status()
            if not response.text or not response.text.strip():
                LOGGER.warning("Réponse vide pour %s", url)
                return None
            return response.text
        except requests.RequestException as exc:
            LOGGER.warning("Échec récupération %s (essai %d/3): %s", url, attempt + 1, exc)

        if attempt < 2:
            delay = delays[attempt] + random.uniform(0, 3)
            time.sleep(delay)

    LOGGER.error("Cycle abandonné après 3 essais pour %s", url)
    return None
