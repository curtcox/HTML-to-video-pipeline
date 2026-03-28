"""
Generate visual frames for each segment of the video.

Creates section/title cards and text frames for the vertical text track,
plus diagram overlay frames for a separate horizontal track.
"""
import os
import textwrap
import hashlib
from io import BytesIO
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from dataclasses import dataclass

from config import PipelineConfig
from diagram_specs import ResolvedDiagramSpec
from parse_article import Segment


@dataclass
class VisualFrame:
    """A single visual frame for the video."""
    image_path: str
    duration: float  # seconds this frame should display
    segment_index: int  # which segment it corresponds to


@dataclass
class DiagramTrackFrame:
    """One diagram overlay bound to a segment range."""
    image_path: str
    source_image_path: str
    source_url: str
    qr_image_path: Optional[str]
    start_segment_index: int
    stop_segment_index: int


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font at the given size. Works on Linux and macOS."""
    if bold:
        candidates = [
            # Linux (DejaVu)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # macOS system fonts
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    # Last resort: Pillow's built-in default (tiny bitmap)
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


DIAGRAM_KEY_COLOR_HEX = "#00FF00"


def diagram_key_color_rgb() -> Tuple[int, int, int]:
    """Color keyed out when composing diagram track over the text track."""
    return hex_to_rgb(DIAGRAM_KEY_COLOR_HEX)


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
    W, H = config.video_width, config.video_height

    # Title — measure first, then center vertically
    font_title = get_font(config.font_size_title, bold=True)
    max_chars = (W - config.margin * 2) // int(config.font_size_title * 0.58)
    wrapped = textwrap.wrap(title, width=max_chars)
    line_heights = []
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        line_heights.append(bbox[3] - bbox[1])
    title_block_h = sum(line_heights) + 24 * (len(wrapped) - 1)

    # Subtitle height
    font_sub = get_font(config.font_size_body)
    sub_h = 0
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        sub_h = bbox[3] - bbox[1] + 50  # gap above subtitle

    total_block = title_block_h + sub_h
    y = (H - total_block) // 2

    # Decorative line above title
    line_width = 300
    line_x = (W - line_width) // 2
    draw.line([(line_x, y - 30), (line_x + line_width, y - 30)],
              fill=hex_to_rgb(config.accent_color), width=4)

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (W - text_width) // 2
        draw.text((x, y), line, fill=hex_to_rgb(config.heading_color), font=font_title)
        y += line_heights[i] + 24

    # Subtitle / byline
    if subtitle:
        y += 26
        bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
        text_width = bbox[2] - bbox[0]
        x = (W - text_width) // 2
        draw.text((x, y), subtitle, fill=hex_to_rgb(config.accent_color), font=font_sub)

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
    W, H = config.video_width, config.video_height

    # Measure everything to center the block vertically
    font_num = get_font(config.font_size_section_label)
    num_text = f"Section {section_number + 1} of {total_sections}"
    num_bbox = draw.textbbox((0, 0), num_text, font=font_num)
    num_h = num_bbox[3] - num_bbox[1]

    font_title = get_font(config.font_size_heading, bold=True)
    max_chars = (W - config.margin * 2) // int(config.font_size_heading * 0.55)
    wrapped = textwrap.wrap(section_title, width=max_chars)
    title_line_h = []
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        title_line_h.append(bbox[3] - bbox[1])
    title_block_h = sum(title_line_h) + 16 * (len(wrapped) - 1)

    gap = 40  # between number and accent line + title
    total_block = num_h + gap + title_block_h
    y = (H - total_block) // 2

    # Section number
    num_w = num_bbox[2] - num_bbox[0]
    draw.text(((W - num_w) // 2, y), num_text,
              fill=hex_to_rgb(config.accent_color), font=font_num)
    y += num_h + 16

    # Accent line
    line_w = W - config.margin * 2
    draw.line([(config.margin, y), (config.margin + line_w, y)],
              fill=hex_to_rgb(config.accent_color), width=3)
    y += 24

    # Section title
    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font_title)
        text_width = bbox[2] - bbox[0]
        x = (W - text_width) // 2
        draw.text((x, y), line, fill=hex_to_rgb(config.heading_color), font=font_title)
        y += title_line_h[i] + 16

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
    font_section = get_font(config.font_size_section_label)
    draw.text((config.margin, 30), section_title.upper(),
              fill=hex_to_rgb(config.accent_color), font=font_section)

    # Thin separator line
    sep_y = 30 + config.font_size_section_label + 12
    draw.line([(config.margin, sep_y),
               (config.video_width - config.margin, sep_y)],
              fill=hex_to_rgb(config.accent_color), width=2)

    # Main text area - fit text to available space
    text_area_width = config.video_width - (config.margin * 2)
    qr_reserved = 0
    if qr_image_path:
        qr_reserved = config.qr_size + config.qr_margin * 2
        text_area_width -= qr_reserved

    # Available vertical space: below header to above bottom margin
    y_top = sep_y + 20
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
        font_qr_label = get_font(24)
        draw.text((qr_x - bg_padding, qr_y - 32), "Scan for source",
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

    W, H = config.video_width, config.video_height
    M = config.margin

    # Title
    if title:
        font_title = get_font(56, bold=True)
        bbox = draw.textbbox((0, 0), title, font=font_title)
        x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((x, 50), title, fill=heading_c, font=font_title)

    content_top = 140  # below title
    content_bottom = H - M
    content_height = content_bottom - content_top

    font_label = get_font(36)
    font_small = get_font(30)

    if diagram_type == "flow":
        # Horizontal flow diagram with arrows — fill the width
        n = len(labels)
        arrow_gap = 70
        usable_w = W - M * 2 - arrow_gap * (n - 1)
        box_width = usable_w // n
        box_height = min(160, content_height // 2)
        total_width = n * box_width + (n - 1) * arrow_gap
        start_x = (W - total_width) // 2
        y = content_top + (content_height - box_height) // 2

        for i, label in enumerate(labels):
            x = start_x + i * (box_width + arrow_gap)
            # Box
            draw.rounded_rectangle(
                [(x, y), (x + box_width, y + box_height)],
                radius=14, outline=accent, width=3
            )
            # Label (centered)
            wrapped = textwrap.wrap(label, width=box_width // 18)
            line_h = 38
            label_y = y + (box_height - len(wrapped) * line_h) // 2
            for line in wrapped:
                bbox = draw.textbbox((0, 0), line, font=font_small)
                lx = x + (box_width - (bbox[2] - bbox[0])) // 2
                draw.text((lx, label_y), line, fill=text_c, font=font_small)
                label_y += line_h

            # Arrow to next box
            if i < n - 1:
                arrow_x = x + box_width + 8
                arrow_end = arrow_x + arrow_gap - 16
                arrow_y = y + box_height // 2
                draw.line([(arrow_x, arrow_y), (arrow_end, arrow_y)],
                          fill=accent, width=3)
                # Arrowhead
                draw.polygon([(arrow_end, arrow_y),
                              (arrow_end - 12, arrow_y - 9),
                              (arrow_end - 12, arrow_y + 9)],
                             fill=accent)

    elif diagram_type == "comparison":
        # Horizontal comparison bars — spread to fill vertical space
        n = len(labels)
        row_height = min(content_height // n, 180)
        total_h = row_height * n
        y_start = content_top + (content_height - total_h) // 2
        bar_max_width = W - M * 2 - 200  # leave room for value label

        for i, label in enumerate(labels):
            parts = label.split("|") if "|" in label else [label, ""]
            name = parts[0].strip()
            value_str = parts[1].strip() if len(parts) > 1 else ""

            try:
                value = float(value_str.replace("%", ""))
                bar_width = int(bar_max_width * value / 100)
            except (ValueError, ZeroDivisionError):
                bar_width = bar_max_width // 2

            y = y_start + i * row_height
            draw.text((M, y), name, fill=text_c, font=font_label)
            bar_y = y + 48
            bar_h = max(row_height - 70, 40)
            draw.rounded_rectangle(
                [(M, bar_y), (M + bar_width, bar_y + bar_h)],
                radius=8, fill=accent
            )
            if value_str:
                draw.text((M + bar_width + 20, bar_y + (bar_h - 36) // 2),
                          value_str, fill=heading_c, font=font_label)

    elif diagram_type == "stats":
        # Big number stats — fill the frame
        n = len(labels)
        col_width = (W - M * 2) // min(n, 3)
        y_center = content_top + content_height // 2

        for i, label in enumerate(labels):
            parts = label.split("|") if "|" in label else [label, ""]
            number = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""

            col = i % 3
            row = i // 3
            x = M + col * col_width + col_width // 2
            y = y_center - 80 + row * 260

            # Big number
            font_big = get_font(96, bold=True)
            bbox = draw.textbbox((0, 0), number, font=font_big)
            nx = x - (bbox[2] - bbox[0]) // 2
            draw.text((nx, y), number, fill=accent, font=font_big)

            # Description
            if desc:
                wrapped = textwrap.wrap(desc, width=18)
                dy = y + 110
                for line in wrapped:
                    bbox = draw.textbbox((0, 0), line, font=font_small)
                    lx = x - (bbox[2] - bbox[0]) // 2
                    draw.text((lx, dy), line, fill=text_c, font=font_small)
                    dy += 38

    img.save(output_path)
    return output_path


def _download_diagram_source_image(
    image_url: str,
    output_dir: str,
    index: int,
) -> str:
    """Download/load a user diagram image and normalize it to PNG."""
    os.makedirs(output_dir, exist_ok=True)
    url_hash = hashlib.sha1(image_url.encode("utf-8")).hexdigest()[:12]
    out_path = os.path.join(output_dir, f"diagram_source_{index:04d}_{url_hash}.png")
    if os.path.exists(out_path):
        return out_path

    if os.path.isfile(image_url):
        Image.open(image_url).convert("RGBA").save(out_path)
        return out_path

    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(
            f"Unsupported diagram image reference: {image_url!r}. "
            "Use an http(s) URL or a local file path."
        )

    resp = requests.get(image_url, timeout=30)
    resp.raise_for_status()
    Image.open(BytesIO(resp.content)).convert("RGBA").save(out_path)
    return out_path


def create_diagram_overlay_frame(
    source_image_path: str,
    source_url: str,
    qr_image_path: Optional[str],
    config: PipelineConfig,
    output_path: str,
) -> str:
    """
    Build one diagram track frame with a key-color background.

    The key color can later be treated as transparent when overlaid.
    """
    key_bg = diagram_key_color_rgb()
    img = Image.new("RGB", (config.video_width, config.video_height), key_bg)
    draw = ImageDraw.Draw(img)

    W, H = config.video_width, config.video_height
    M = config.margin
    accent = hex_to_rgb(config.accent_color)

    # Main image panel
    panel_x1 = M
    panel_y1 = M
    panel_x2 = int(W * 0.74)
    panel_y2 = H - M
    draw.rounded_rectangle(
        [(panel_x1, panel_y1), (panel_x2, panel_y2)],
        radius=22,
        fill=(12, 12, 18),
        outline=accent,
        width=4,
    )

    # Right QR panel
    qr_panel_x1 = panel_x2 + 24
    qr_panel_y1 = panel_y1
    qr_panel_x2 = W - M
    qr_panel_y2 = panel_y2
    draw.rounded_rectangle(
        [(qr_panel_x1, qr_panel_y1), (qr_panel_x2, qr_panel_y2)],
        radius=22,
        fill=(18, 24, 34),
        outline=accent,
        width=3,
    )

    src_img = Image.open(source_image_path).convert("RGBA")
    image_padding = 26
    box = (
        panel_x1 + image_padding,
        panel_y1 + image_padding,
        panel_x2 - image_padding,
        panel_y2 - image_padding,
    )
    fitted = ImageOps.contain(src_img, (box[2] - box[0], box[3] - box[1]))
    fit_x = box[0] + ((box[2] - box[0]) - fitted.size[0]) // 2
    fit_y = box[1] + ((box[3] - box[1]) - fitted.size[1]) // 2
    img.paste(fitted, (fit_x, fit_y), fitted)

    draw.text(
        (qr_panel_x1 + 24, qr_panel_y1 + 20),
        "Scan Diagram URL",
        fill=hex_to_rgb(config.heading_color),
        font=get_font(32, bold=True),
    )

    qr_size = min(config.qr_size, 260)
    qr_y = qr_panel_y1 + 86
    if qr_image_path and os.path.exists(qr_image_path):
        qr_img = Image.open(qr_image_path).convert("RGBA")
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        qr_x = qr_panel_x1 + ((qr_panel_x2 - qr_panel_x1) - qr_size) // 2
        img.paste(qr_img, (qr_x, qr_y), qr_img)
    else:
        draw.rectangle(
            [(qr_panel_x1 + 36, qr_y), (qr_panel_x2 - 36, qr_y + qr_size)],
            outline=(255, 255, 255),
            width=2,
        )
        draw.text(
            (qr_panel_x1 + 52, qr_y + qr_size // 2 - 16),
            "QR unavailable",
            fill=(255, 255, 255),
            font=get_font(28),
        )

    text_y = qr_y + qr_size + 26
    for line in textwrap.wrap(source_url, width=28)[:7]:
        draw.text(
            (qr_panel_x1 + 24, text_y),
            line,
            fill=hex_to_rgb(config.text_color),
            font=get_font(22),
        )
        text_y += 32

    img.save(output_path)
    return output_path


def generate_diagram_track_frames(
    resolved_diagrams: List[ResolvedDiagramSpec],
    qr_map: Dict[str, str],
    config: PipelineConfig,
    output_dir: str,
) -> List[DiagramTrackFrame]:
    """Create keyed diagram frames mapped to segment index ranges."""
    os.makedirs(output_dir, exist_ok=True)
    source_dir = os.path.join(output_dir, "diagram_sources")
    os.makedirs(source_dir, exist_ok=True)

    frames: List[DiagramTrackFrame] = []
    for i, diagram in enumerate(resolved_diagrams):
        source_image_path = _download_diagram_source_image(diagram.image_url, source_dir, i)
        qr_path = qr_map.get(diagram.image_url)
        frame_path = os.path.join(output_dir, f"diagram_overlay_{i:04d}.png")
        create_diagram_overlay_frame(
            source_image_path=source_image_path,
            source_url=diagram.image_url,
            qr_image_path=qr_path,
            config=config,
            output_path=frame_path,
        )
        frames.append(
            DiagramTrackFrame(
                image_path=frame_path,
                source_image_path=source_image_path,
                source_url=diagram.image_url,
                qr_image_path=qr_path,
                start_segment_index=diagram.start_segment_index,
                stop_segment_index=diagram.stop_segment_index,
            )
        )

    return frames


def generate_frames_for_segments(
    segments: List[Segment],
    qr_map: Dict[str, str],
    config: PipelineConfig,
    output_dir: str,
) -> List[VisualFrame]:
    """
    Generate all visual frames for the video.

    Returns ordered list of text-track VisualFrame objects.
    """
    os.makedirs(output_dir, exist_ok=True)
    frames: List[VisualFrame] = []
    total_sections = sum(1 for s in segments if s.segment_type == "heading")

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
            create_section_card(
                seg.text, seg.section_index, total_sections,
                config, frame_path,
            )
            frames.append(VisualFrame(frame_path, config.pause_after_heading + 1.0, i))

        elif seg.segment_type == "blockquote":
            create_blockquote_frame(seg.text, seg.section_title, config, frame_path)
            frames.append(VisualFrame(frame_path, 0, i))  # duration set by audio

        else:  # paragraph
            # Text track is intentionally text-only.
            create_text_frame(seg.text, seg.section_title, config, frame_path,
                              qr_image_path=None)
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
