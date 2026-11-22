import json
import tempfile
import unittest
from pathlib import Path

from src.state import load_state, save_state


class StateTests(unittest.TestCase):
    def test_atomic_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_state(path, {"sku": {"status": "INDISPONIBLE", "last_message": None}})
            self.assertEqual(load_state(path)["sku"]["status"], "INDISPONIBLE")

    def test_corrupted_state_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_state(path), {})


if __name__ == "__main__":
    unittest.main()
