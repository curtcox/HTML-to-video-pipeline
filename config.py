"""
Configuration for article-to-video pipeline.
"""
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineConfig:
    # Input
    article_url: str = ""

    # Output
    output_dir: str = "output"
    output_filename: str = "video.mp4"

    # Video settings
    video_width: int = 1920
    video_height: int = 1080
    fps: int = 30
    background_color: str = "#1a1a2e"  # Dark navy
    text_color: str = "#e0e0e0"
    accent_color: str = "#4fc3f7"  # Light blue
    heading_color: str = "#ffffff"

    # Typography
    font_size_title: int = 72
    font_size_heading: int = 56
    font_size_body: int = 36
    font_size_caption: int = 32
    line_spacing: float = 1.5
    margin: int = 120  # pixels from edge

    # QR code settings
    qr_size: int = 200  # pixels
    qr_position: str = "bottom_right"  # bottom_right, bottom_left
    qr_margin: int = 40

    # TTS settings
    tts_provider: str = "elevenlabs"  # elevenlabs, openai, google
    elevenlabs_api_key: str = field(default_factory=lambda: os.environ.get("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"  # "Adam" - documentary style
    elevenlabs_model: str = "eleven_multilingual_v2"

    # Pacing
    pause_after_heading: float = 1.5  # seconds
    pause_between_paragraphs: float = 0.8
    pause_after_section: float = 2.0

    # Caption settings
    words_per_caption_line: int = 8
    max_caption_lines: int = 2
    caption_position: str = "bottom"  # bottom, top

    @property
    def output_path(self):
        return os.path.join(self.output_dir, self.output_filename)
