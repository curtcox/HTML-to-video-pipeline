"""
Generate visual frames for each segment of the video.

Creates section title cards, text frames with key phrases highlighted,
and diagram frames for concepts that benefit from illustration.
"""
import os
import textwrap
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass

from config import PipelineConfig
from parse_article import Segment


@dataclass
class VisualFrame:
    """A single visual frame for the video."""
    image_path: str
    duration: float  # seconds this frame should display
    segment_index: int  # which segment it corresponds to


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font at the given size."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_title_card(
    title: str,
    subtitle: str,
    config: PipelineConfig,
    output_path: str,
) -> str:
    """Create an opening title card."""
    img = Image.new("RGB", (config.video_width, config.video_height),
                     hex_to_rgb(config.background_color))
    draw = ImageDraw.Draw(img)

    # Title
    font_title = get_font(config.font_size_title, bold=True)
    wrapped = textwrap.wrap(title, width=28)
    y = config.video_height // 3
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (config.video_width - text_width) // 2
        draw.text((x, y), line, fill=hex_to_rgb(config.heading_color), font=font_title)
        y += bbox[3] - bbox[1] + 20

    # Subtitle / byline
    if subtitle:
        y += 40
        font_sub = get_font(config.font_size_body)
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        text_width = bbox[2] - bbox[0]
        x = (config.video_width - text_width) // 2
        draw.text((x, y), subtitle, fill=hex_to_rgb(config.accent_color), font=font_sub)

    # Decorative line
    line_y = config.video_height // 3 - 30
    line_width = 200
    line_x = (config.video_width - line_width) // 2
    draw.line([(line_x, line_y), (line_x + line_width, line_y)],
              fill=hex_to_rgb(config.accent_color), width=3)

    img.save(output_path)
    return output_path


def create_section_card(
    section_title: str,
    section_number: int,
    total_sections: int,
    config: PipelineConfig,
    output_path: str,
) -> str:
    """Create a section transition card."""
    img = Image.new("RGB", (config.video_width, config.video_height),
                     hex_to_rgb(config.background_color))
    draw = ImageDraw.Draw(img)

    # Section number
    font_num = get_font(config.font_size_body)
    num_text = f"Section {section_number + 1} of {total_sections}"
    bbox = draw.textbbox((0, 0), num_text, font=font_num)
    text_width = bbox[2] - bbox[0]
    x = (config.video_width - text_width) // 2
    y = config.video_height // 3 - 40
    draw.text((x, y), num_text, fill=hex_to_rgb(config.accent_color), font=font_num)

    # Section title
    font_title = get_font(config.font_size_heading, bold=True)
    wrapped = textwrap.wrap(section_title, width=35)
    y = config.video_height // 3 + 30
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (config.video_width - text_width) // 2
        draw.text((x, y), line, fill=hex_to_rgb(config.heading_color), font=font_title)
        y += bbox[3] - bbox[1] + 15

    # Decorative accent
    accent_y = config.video_height // 3 + 10
    draw.line([(config.margin * 2, accent_y),
               (config.video_width - config.margin * 2, accent_y)],
              fill=hex_to_rgb(config.accent_color), width=2)

    img.save(output_path)
    return output_path


def create_text_frame(
    text: str,
    section_title: str,
    config: PipelineConfig,
    output_path: str,
    highlight_phrases: Optional[List[str]] = None,
    qr_image_path: Optional[str] = None,
) -> str:
    """
    Create a frame showing narrated text with optional QR code overlay.

    Shows the key sentence or pull-quote from the paragraph being narrated,
    not the full paragraph (which is too dense for video).
    """
    img = Image.new("RGB", (config.video_width, config.video_height),
                     hex_to_rgb(config.background_color))
    draw = ImageDraw.Draw(img)

    # Section title at top
    font_section = get_font(24)
    draw.text((config.margin, 40), section_title.upper(),
              fill=hex_to_rgb(config.accent_color), font=font_section)

    # Thin separator line
    draw.line([(config.margin, 75),
               (config.video_width - config.margin, 75)],
              fill=hex_to_rgb(config.accent_color), width=1)

    # Main text area - fit text to available space
    text_area_width = config.video_width - (config.margin * 2)
    qr_reserved = 0
    if qr_image_path:
        qr_reserved = config.qr_size + config.qr_margin * 2
        text_area_width -= qr_reserved

    # Available vertical space: below header (y=100) to above QR/bottom margin
    y_top = 100
    y_bottom = config.video_height - config.margin
    if qr_image_path:
        # Leave room for QR label + code at bottom-right; text can still
        # use the full height on the left, but cap it to keep breathing room
        y_bottom = config.video_height - config.qr_margin
    available_height = y_bottom - y_top

    # Start with the configured font size and shrink until the text fits
    font_size = config.font_size_body
    MIN_FONT_SIZE = 20
    while font_size >= MIN_FONT_SIZE:
        font_body = get_font(font_size)
        chars_per_line = text_area_width // (font_size * 0.55)
        wrapped = textwrap.wrap(text, width=int(chars_per_line))
        line_height = int(font_size * config.line_spacing)
        total_text_height = len(wrapped) * line_height
        if total_text_height <= available_height:
            break
        font_size -= 2
    else:
        # Still too long at minimum size — truncate to what fits
        font_body = get_font(MIN_FONT_SIZE)
        line_height = int(MIN_FONT_SIZE * config.line_spacing)
        max_lines = available_height // line_height
        wrapped = wrapped[:max_lines]
        if wrapped:
            wrapped[-1] = wrapped[-1].rstrip() + " …"

    # Center text vertically within the available area
    total_text_height = len(wrapped) * line_height
    y_start = y_top + max(0, (available_height - total_text_height) // 2)

    y = y_start
    for line in wrapped:
        draw.text((config.margin, y), line,
                  fill=hex_to_rgb(config.text_color), font=font_body)
        y += line_height

    # QR code overlay
    if qr_image_path and os.path.exists(qr_image_path):
        qr_img = Image.open(qr_image_path).convert("RGBA")
        qr_x = config.video_width - config.qr_size - config.qr_margin
        qr_y = config.video_height - qr_img.size[1] - config.qr_margin

        # Semi-transparent background behind QR
        bg_padding = 10
        qr_bg = Image.new("RGBA", (qr_img.size[0] + bg_padding * 2,
                                     qr_img.size[1] + bg_padding * 2),
                           (255, 255, 255, 220))
        img.paste(Image.new("RGB", qr_bg.size, (255, 255, 255)),
                  (qr_x - bg_padding, qr_y - bg_padding))
        img.paste(qr_img, (qr_x, qr_y), qr_img if qr_img.mode == "RGBA" else None)

        # Label above QR
        font_qr_label = get_font(18)
        draw.text((qr_x - bg_padding, qr_y - 25), "Scan for source",
                  fill=hex_to_rgb(config.accent_color), font=font_qr_label)

    img.save(output_path)
    return output_path


def create_blockquote_frame(
    text: str,
    section_title: str,
    config: PipelineConfig,
    output_path: str,
) -> str:
    """Create a visually distinct frame for blockquotes / pull-quotes."""
    img = Image.new("RGB", (config.video_width, config.video_height),
                     hex_to_rgb(config.background_color))
    draw = ImageDraw.Draw(img)

    # Large quotation mark
    font_quote = get_font(120, bold=True)
    draw.text((config.margin, config.video_height // 4 - 60), "\u201c",
              fill=hex_to_rgb(config.accent_color), font=font_quote)

    # Quote text — shrink font if needed to fit frame
    text_area_width = config.video_width - config.margin * 3
    y_top = config.video_height // 4 + 60
    y_bottom = config.video_height - config.margin
    available_height = y_bottom - y_top

    font_size = config.font_size_body + 4
    MIN_FONT_SIZE = 22
    while font_size >= MIN_FONT_SIZE:
        font_body = get_font(font_size)
        chars_per_line = text_area_width // (font_size * 0.55)
        wrapped = textwrap.wrap(text, width=int(chars_per_line))
        line_height = int(font_size * config.line_spacing)
        if len(wrapped) * line_height <= available_height:
            break
        font_size -= 2
    else:
        font_body = get_font(MIN_FONT_SIZE)
        line_height = int(MIN_FONT_SIZE * config.line_spacing)
        max_lines = available_height // line_height
        wrapped = wrapped[:max_lines]
        if wrapped:
            wrapped[-1] = wrapped[-1].rstrip() + " …"

    line_height = int(font_size * config.line_spacing)
    y = y_top
    for line in wrapped:
        draw.text((config.margin + 40, y), line,
                  fill=hex_to_rgb(config.heading_color), font=font_body)
        y += line_height

    # Left accent bar
    bar_top = config.video_height // 4 + 50
    bar_bottom = y + 10
    draw.line([(config.margin + 20, bar_top), (config.margin + 20, bar_bottom)],
              fill=hex_to_rgb(config.accent_color), width=4)

    img.save(output_path)
    return output_path


def create_diagram_frame(
    diagram_type: str,
    labels: List[str],
    config: PipelineConfig,
    output_path: str,
    title: str = "",
) -> str:
    """
    Create a simple diagram/illustration frame.

    diagram_type: "flow", "comparison", "cycle", "hierarchy", "stats"
    """
    img = Image.new("RGB", (config.video_width, config.video_height),
                     hex_to_rgb(config.background_color))
    draw = ImageDraw.Draw(img)

    bg = hex_to_rgb(config.background_color)
    accent = hex_to_rgb(config.accent_color)
    text_c = hex_to_rgb(config.text_color)
    heading_c = hex_to_rgb(config.heading_color)

    # Title
    if title:
        font_title = get_font(40, bold=True)
        bbox = draw.textbbox((0, 0), title, font=font_title)
        x = (config.video_width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 50), title, fill=heading_c, font=font_title)

    font_label = get_font(28)
    font_small = get_font(22)

    if diagram_type == "flow":
        # Horizontal flow diagram with arrows
        n = len(labels)
        box_width = min(300, (config.video_width - config.margin * 2 - 60 * (n - 1)) // n)
        box_height = 80
        total_width = n * box_width + (n - 1) * 60
        start_x = (config.video_width - total_width) // 2
        y = config.video_height // 2 - box_height // 2

        for i, label in enumerate(labels):
            x = start_x + i * (box_width + 60)
            # Box
            draw.rounded_rectangle(
                [(x, y), (x + box_width, y + box_height)],
                radius=10, outline=accent, width=2
            )
            # Label (centered)
            wrapped = textwrap.wrap(label, width=box_width // 16)
            label_y = y + (box_height - len(wrapped) * 30) // 2
            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font_small)
                lx = x + (box_width - (bbox[2] - bbox[0])) // 2
                draw.text((lx, label_y), line, fill=text_c, font=font_small)
                label_y += 30

            # Arrow to next box
            if i < n - 1:
                arrow_x = x + box_width + 5
                arrow_y = y + box_height // 2
                draw.line([(arrow_x, arrow_y), (arrow_x + 50, arrow_y)],
                          fill=accent, width=2)
                # Arrowhead
                draw.polygon([(arrow_x + 50, arrow_y),
                              (arrow_x + 42, arrow_y - 6),
                              (arrow_x + 42, arrow_y + 6)],
                             fill=accent)

    elif diagram_type == "comparison":
        # Side-by-side comparison bars
        bar_max_width = config.video_width // 2 - config.margin - 40
        y = 150
        for i, label in enumerate(labels):
            parts = label.split("|") if "|" in label else [label, ""]
            name = parts[0].strip()
            value_str = parts[1].strip() if len(parts) > 1 else ""

            # Try to extract numeric value for bar width
            try:
                value = float(value_str.replace("%", ""))
                bar_width = int(bar_max_width * value / 100)
            except (ValueError, ZeroDivisionError):
                bar_width = bar_max_width // 2

            draw.text((config.margin, y), name, fill=text_c, font=font_label)
            y += 40
            draw.rounded_rectangle(
                [(config.margin, y), (config.margin + bar_width, y + 35)],
                radius=5, fill=accent
            )
            if value_str:
                draw.text((config.margin + bar_width + 15, y + 3),
                          value_str, fill=heading_c, font=font_label)
            y += 60

    elif diagram_type == "stats":
        # Big number stats display
        n = len(labels)
        col_width = (config.video_width - config.margin * 2) // min(n, 3)
        y_base = config.video_height // 3

        for i, label in enumerate(labels):
            parts = label.split("|") if "|" in label else [label, ""]
            number = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""

            col = i % 3
            row = i // 3
            x = config.margin + col * col_width + col_width // 2
            y = y_base + row * 200

            # Big number
            font_big = get_font(64, bold=True)
            bbox = draw.textbbox((0, 0), number, font=font_big)
            nx = x - (bbox[2] - bbox[0]) // 2
            draw.text((nx, y), number, fill=accent, font=font_big)

            # Description
            if desc:
                wrapped = textwrap.wrap(desc, width=20)
                dy = y + 80
                for line in wrapped:
                    bbox = draw.textbbox((0, 0), line, font=font_small)
                    lx = x - (bbox[2] - bbox[0]) // 2
                    draw.text((lx, dy), line, fill=text_c, font=font_small)
                    dy += 28

    img.save(output_path)
    return output_path


# Diagram definitions keyed by section title.
# Each entry: (diagram_type, labels, diagram_title)
SECTION_DIAGRAMS = {
    "What hallucinations actually are": (
        "flow",
        ["Training Data\n(patterns)", "Statistical\nPrediction", "Next Word\nGeneration", "Output Text\n(may be false)"],
        "How LLMs Generate Text"
    ),
    "The psychology: citations boost trust whether or not they're valid": (
        "stats",
        ["↑ Trust|Citations present\n(even random ones)",
         "↓ Trust|Only when users\nactually click & read",
         "Gap|Between confidence\nand accuracy"],
        "How Citations Affect User Trust"
    ),
    "How AI training creates the problem": (
        "flow",
        ["LLM generates\nmultiple responses", "Human raters\nrank them", "Reward model\nlearns preferences", "LLM optimized\nfor high scores"],
        "The RLHF Training Loop"
    ),
    "The solutions exist — they're just not widely deployed": (
        "comparison",
        ["GopherCite (2022) | 80|80% accurate cited answers",
         "Fine-grained NLI rewards | 90|Outperformed standard RLHF",
         "RLVR (automated checks) | 85|Programmatic verification",
         "CiteAudit / CiteLab | 75|Post-hoc audit tools"],
        "Existing Citation Verification Approaches"
    ),
    "What will probably get better — and what probably won't": (
        "comparison",
        ["GPT-3.5 fabrication rate | 39.6|39.6%",
         "GPT-4 fabrication rate | 28.6|28.6%",
         "Custom RAG model | 15.8|3 of 19 questions",
         "Legal AI tools | 25|17-33%"],
        "Hallucination Rates Across Models"
    ),
}


def generate_frames_for_segments(
    segments: List[Segment],
    qr_map: Dict[str, str],
    config: PipelineConfig,
    output_dir: str,
) -> List[VisualFrame]:
    """
    Generate all visual frames for the video.

    Returns ordered list of VisualFrame objects.
    """
    os.makedirs(output_dir, exist_ok=True)
    frames: List[VisualFrame] = []
    total_sections = max(s.section_index for s in segments) + 1
    seen_sections = set()

    for i, seg in enumerate(segments):
        frame_path = os.path.join(output_dir, f"frame_{i:04d}.png")

        if seg.segment_type == "title":
            create_title_card(
                seg.text,
                "An AI-written essay about AI accuracy",
                config, frame_path,
            )
            frames.append(VisualFrame(frame_path, 5.0, i))

        elif seg.segment_type == "heading":
            # Section card
            create_section_card(
                seg.text, seg.section_index, total_sections,
                config, frame_path,
            )
            frames.append(VisualFrame(frame_path, config.pause_after_heading + 1.0, i))

            # Check if we have a diagram for this section
            if seg.text in SECTION_DIAGRAMS and seg.text not in seen_sections:
                seen_sections.add(seg.text)
                diagram_type, labels, diagram_title = SECTION_DIAGRAMS[seg.text]
                diagram_path = os.path.join(output_dir, f"diagram_{i:04d}.png")
                create_diagram_frame(diagram_type, labels, config, diagram_path,
                                     title=diagram_title)
                # Diagram duration will be set during audio alignment
                frames.append(VisualFrame(diagram_path, 6.0, i))

        elif seg.segment_type == "blockquote":
            create_blockquote_frame(seg.text, seg.section_title, config, frame_path)
            frames.append(VisualFrame(frame_path, 0, i))  # duration set by audio

        else:  # paragraph
            # Pick the first citation's QR code if available
            qr_path = None
            if seg.citations:
                first_url = seg.citations[0].url
                qr_path = qr_map.get(first_url)

            create_text_frame(seg.text, seg.section_title, config, frame_path,
                              qr_image_path=qr_path)
            frames.append(VisualFrame(frame_path, 0, i))  # duration set by audio

    return frames


if __name__ == "__main__":
    from parse_article import fetch_html, parse_article
    config = PipelineConfig()
    # Quick test with a dummy segment
    create_title_card("Why AI Still Makes Things Up", "Test", config, "output/test_title.png")
    create_section_card("What hallucinations actually are", 0, 10, config, "output/test_section.png")
    create_diagram_frame("flow",
                         ["Training Data", "Prediction", "Generation", "Output"],
                         config, "output/test_diagram.png",
                         title="How LLMs Generate Text")
    print("Test frames generated in output/")
