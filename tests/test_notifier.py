import unittest
import json
from unittest.mock import Mock, patch

import requests

from src.notifier import _download_photo, format_message, send_notification


class NotifierTests(unittest.TestCase):
    def test_format_message_escapes_html_and_url_quotes(self):
        parsed = {
            "title": "Console <PS5>",
            "price": "649,99",
            "currency": "EUR",
            "sku": "SKU-123",
            "url": 'https://example.test/product?x="quoted"&y=1',
        }

        message = format_message("Disponible", parsed, "22/11/2026 23:00")

        self.assertIn("Console &lt;PS5&gt;", message)
        self.assertIn("&quot;quoted&quot;&amp;y=1", message)

    @patch("src.notifier.requests.get")
    def test_download_photo_requests_small_jpeg(self, mock_get):
        response = Mock()
        response.headers = {"Content-Type": "image/jpeg"}
        response.iter_content.return_value = [b"jpeg-data"]
        mock_get.return_value = response

        filename, content, content_type = _download_photo(
            "https://gmedia.playstation.com/is/image/SIEPDC/console?$native--t$"
        )

        self.assertEqual((filename, content, content_type), ("produit.jpg", b"jpeg-data", "image/jpeg"))
        self.assertIn(
            "$wid=800&$hei=800&$fit=constrain&$fmt=jpg",
            mock_get.call_args.args[0],
        )
        response.close.assert_called_once()

    @patch("src.notifier.requests.post")
    @patch("src.notifier.requests.get")
    def test_send_photo_uses_multipart_and_falls_back_to_text(self, mock_get, mock_post):
        image_response = Mock()
        image_response.headers = {"Content-Type": "image/jpeg"}
        image_response.iter_content.return_value = [b"jpeg-data"]
        mock_get.return_value = image_response

        photo_response = Mock(status_code=400)
        photo_response.json.return_value = {
            "ok": False,
            "description": "PHOTO_REJECTED",
        }
        text_response = Mock(status_code=200)
        text_response.json.return_value = {"ok": True}
        mock_post.side_effect = [photo_response, text_response]

        parsed = {
            "title": "Console PS5",
            "price": "649,99",
            "currency": "EUR",
            "sku": "SKU-123",
            "url": "https://example.test/ps5",
            "image": "https://gmedia.playstation.com/is/image/SIEPDC/console?$native--t$",
        }

        with self.assertLogs("ps5-watcher", level="WARNING") as logs:
            sent = send_notification("test-token", "123", "Disponible", parsed, "22/11/2026 23:00")

        self.assertTrue(sent)
        logged_errors = "\n".join(logs.output)
        self.assertIn("PHOTO_REJECTED", logged_errors)
        self.assertNotIn("test-token", logged_errors)
        photo_call = mock_post.call_args_list[0]
        self.assertIn("files", photo_call.kwargs)
        self.assertEqual(photo_call.kwargs["data"]["caption"].splitlines()[0], "🛒 <b>Disponible</b>")
        self.assertEqual(
            json.loads(photo_call.kwargs["data"]["reply_markup"])["inline_keyboard"][0][0]["url"],
            parsed["url"],
        )
        self.assertIn("json", mock_post.call_args_list[1].kwargs)

    @patch("src.notifier.requests.post")
    @patch("src.notifier.requests.get", side_effect=requests.Timeout)
    def test_download_failure_falls_back_to_text(self, mock_get, mock_post):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        mock_post.return_value = response
        parsed = {
            "title": "Console PS5",
            "price": "649,99",
            "currency": "EUR",
            "sku": "SKU-123",
            "url": "https://example.test/ps5",
            "image": "https://gmedia.playstation.com/is/image/SIEPDC/console",
        }

        self.assertTrue(send_notification("test-token", "123", "Disponible", parsed, "22/11/2026 23:00"))
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        self.assertIn("json", mock_post.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
