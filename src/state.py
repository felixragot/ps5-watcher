import json
import logging
import os
from pathlib import Path


LOGGER = logging.getLogger("ps5-watcher")


def load_state(path):
    path = Path(path)
    if not path.exists():
        LOGGER.warning("Aucun fichier d'état trouvé, départ avec un état vide")
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            state = json.load(file)
        if not isinstance(state, dict):
            raise ValueError("La racine de state.json doit être un objet")
        return state
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        LOGGER.warning("État corrompu ou illisible (%s), départ avec un état vide", exc)
        return {}


def save_state(path, state):
    path = Path(path)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
        return True
    except OSError as exc:
        LOGGER.error("Impossible d'écrire atomiquement state.json: %s", exc)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        return False
