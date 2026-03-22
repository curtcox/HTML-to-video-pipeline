"""
Generate QR code images for citation URLs.

Produces clean QR codes with optional label text,
cached to avoid regenerating for duplicate URLs.
"""
import os
import hashlib
from typing import Dict, List
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.constants import ERROR_CORRECT_H


def url_to_filename(url: str) -> str:
    """Create a safe filename from a URL using its hash."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"qr_{url_hash}.png"


def generate_qr_image(
    url: str,
    size: int = 200,
    bg_color: str = "#ffffff",
    fg_color: str = "#000000",
    label: str = "",
) -> Image.Image:
    """
    Generate a QR code image for a URL.

    Args:
        url: The URL to encode
        size: Width/height in pixels
        bg_color: Background color
        fg_color: Foreground (module) color
        label: Optional short label below the QR code

    Returns:
        PIL Image of the QR code
    """
    qr = qrcode.QRCode(
        version=None,  # auto-size
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)

    if label:
        # Add label below QR code
        label_height = 30
        combined = Image.new("RGBA", (size, size + label_height), bg_color)
        combined.paste(img, (0, 0))
        draw = ImageDraw.Draw(combined)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except IOError:
            font = ImageFont.load_default()

        # Truncate label if too long
        max_chars = size // 8
        display_label = label[:max_chars] + "..." if len(label) > max_chars else label
        bbox = draw.textbbox((0, 0), display_label, font=font)
        text_width = bbox[2] - bbox[0]
        x = (size - text_width) // 2
        draw.text((x, size + 4), display_label, fill=fg_color, font=font)
        return combined

    return img


def generate_all_qr_codes(
    urls: List[str],
    output_dir: str,
    size: int = 200,
) -> Dict[str, str]:
    """
    Generate QR code images for all URLs, saving to output_dir.

    Returns:
        Dict mapping URL -> file path of generated QR image
    """
    os.makedirs(output_dir, exist_ok=True)
    url_to_path = {}

    for url in urls:
        filename = url_to_filename(url)
        filepath = os.path.join(output_dir, filename)

        if not os.path.exists(filepath):
            # Use domain as label
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            img = generate_qr_image(url, size=size, label=domain)
            img.save(filepath)

        url_to_path[url] = filepath

    return url_to_path


if __name__ == "__main__":
    test_urls = [
        "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC11153973/",
        "https://ojs.aaai.org/index.php/AAAI/article/view/34550",
    ]
    result = generate_all_qr_codes(test_urls, "output/qr_codes", size=200)
    for url, path in result.items():
        print(f"  {url[:60]}... -> {path}")
