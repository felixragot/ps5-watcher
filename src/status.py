import unicodedata

from .config import (
    NEGATIVE_AVAILABILITY,
    NEGATIVE_TEXT,
    NEGATIVE_TYPES,
    POSITIVE_AVAILABILITY,
    POSITIVE_TEXT,
    POSITIVE_TYPES,
)


def normalize(value):
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.lower().replace("’", "'").split())


def classify_signals(parsed):
    if not parsed:
        return "INCONNU"

    availability = normalize(parsed.get("availability"))
    button_type = normalize(parsed.get("button_type"))
    visible_text = normalize(parsed.get("visible_text"))

    positive = False
    negative = False

    availability_tail = availability.rsplit("/", 1)[-1].replace(" ", "")
    if availability_tail in NEGATIVE_AVAILABILITY:
        negative = True
    elif availability_tail in POSITIVE_AVAILABILITY:
        positive = True

    button_type_upper = str(parsed.get("button_type") or "").upper()
    if button_type_upper in NEGATIVE_TYPES:
        negative = True
    elif button_type_upper in POSITIVE_TYPES:
        positive = True

    if any(text in visible_text for text in (normalize(v) for v in NEGATIVE_TEXT)):
        negative = True
    elif any(text in visible_text for text in (normalize(v) for v in POSITIVE_TEXT)):
        positive = True

    if negative and positive:
        return "INCONNU"
    if negative:
        return "INDISPONIBLE"
    if positive:
        return "DISPONIBLE"
    return "INCONNU"
