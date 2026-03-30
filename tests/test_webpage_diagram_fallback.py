import os
import tempfile
import unittest
from unittest import mock

from PIL import Image

from generate_visuals import (
    _generate_url_text_fallback_image,
    _looks_like_html_payload,
    _try_generate_thumbnail_from_webpage,
)


class WebpageDiagramFallbackTests(unittest.TestCase):
    def test_html_payload_detection(self):
        html = b"<!doctype html><html><head></head><body>hi</body></html>"
        self.assertTrue(_looks_like_html_payload(html, "text/html; charset=utf-8", "https://example.com"))
        self.assertTrue(_looks_like_html_payload(html, "", "https://example.com/page.html"))
        self.assertFalse(_looks_like_html_payload(b"\x89PNG\r\n\x1a\n", "image/png", "https://example.com/a.png"))

    def test_generate_url_text_fallback_image(self):
        with tempfile.TemporaryDirectory(prefix="url-fallback-") as tmpdir:
            out_path = os.path.join(tmpdir, "fallback.png")
            _generate_url_text_fallback_image("https://example.com/some/really/long/path", out_path)
            self.assertTrue(os.path.exists(out_path))
            with Image.open(out_path) as img:
                self.assertEqual(img.size, (1920, 1080))

    def test_webpage_thumbnail_uses_meta_image_candidates(self):
        html = b"""
        <html><head>
          <meta property="og:image" content="/images/preview.png">
        </head><body></body></html>
        """
        with tempfile.TemporaryDirectory(prefix="thumb-test-") as tmpdir:
            out_path = os.path.join(tmpdir, "thumb.png")
            with mock.patch("generate_visuals._try_download_remote_image", return_value=True) as mocked:
                ok = _try_generate_thumbnail_from_webpage("https://example.com/article", html, out_path)
            self.assertTrue(ok)
            mocked.assert_called_once()
            called_url = mocked.call_args[0][0]
            self.assertEqual(called_url, "https://example.com/images/preview.png")


if __name__ == "__main__":
    unittest.main()
