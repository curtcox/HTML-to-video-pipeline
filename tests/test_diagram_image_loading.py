import os
import tempfile
import unittest
from io import BytesIO

from PIL import Image

from generate_visuals import (
    _is_svg_payload,
    _preferred_download_url,
    _try_decode_image_bytes,
    _try_decode_svg_bytes,
    can_rasterize_svg,
)


class DiagramImageLoadingTests(unittest.TestCase):
    def test_png_bytes_decode(self):
        with tempfile.TemporaryDirectory(prefix="img-test-") as tmpdir:
            src = Image.new("RGB", (16, 16), (255, 0, 0))
            buf = BytesIO()
            src.save(buf, format="PNG")
            out_path = os.path.join(tmpdir, "decoded.png")
            self.assertTrue(_try_decode_image_bytes(buf.getvalue(), out_path))
            self.assertTrue(os.path.exists(out_path))

    def test_svg_payload_detection(self):
        svg = b"<svg xmlns='http://www.w3.org/2000/svg' width='2' height='2'></svg>"
        self.assertTrue(_is_svg_payload(svg, "image/svg+xml", "https://example.com/a.svg"))
        self.assertTrue(_is_svg_payload(svg, "", "https://example.com/a.svg"))
        self.assertFalse(_is_svg_payload(b"not-an-image", "text/plain", "https://example.com/a.txt"))

    def test_wikimedia_download_url_rewrite(self):
        src = "https://upload.wikimedia.org/wikipedia/commons/3/3d/Neural_network.svg"
        rewritten = _preferred_download_url(src)
        self.assertIn("upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Neural_network.svg", rewritten)
        self.assertIn("px-Neural_network.svg.png", rewritten)

    def test_svg_rasterization_if_backend_available(self):
        if not can_rasterize_svg():
            self.skipTest("No SVG rasterizer backend available (cairosvg or ffmpeg SVG decode).")

        svg = (
            b"<svg xmlns='http://www.w3.org/2000/svg' width='40' height='30'>"
            b"<rect width='40' height='30' fill='blue'/>"
            b"</svg>"
        )
        with tempfile.TemporaryDirectory(prefix="svg-test-") as tmpdir:
            out_path = os.path.join(tmpdir, "rasterized.png")
            ok = _try_decode_svg_bytes(
                svg,
                out_path,
                "https://example.com/simple.svg",
                "https://example.com/simple.svg",
            )
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(out_path))
            with Image.open(out_path) as img:
                self.assertGreaterEqual(img.size[0], 1)
                self.assertGreaterEqual(img.size[1], 1)


if __name__ == "__main__":
    unittest.main()
