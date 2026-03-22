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
    font_size_title: int = 88
    font_size_heading: int = 64
    font_size_body: int = 40
    font_size_caption: int = 34
    font_size_section_label: int = 32
    line_spacing: float = 1.4
    margin: int = 72  # pixels from edge

    # QR code settings
    qr_size: int = 260  # pixels
    qr_position: str = "bottom_right"  # bottom_right, bottom_left
    qr_margin: int = 32

    # TTS settings
    tts_provider: str = "say"  # say, piper, elevenlabs, kokoro

    # macOS say
    say_voice: str = "Daniel"  # `say -v ?` for full list
    say_rate: int = 175  # words per minute

    # Piper (local neural TTS)
    piper_model: str = "en_US-lessac-medium"  # `python3 -m piper.download_voices` for list
    piper_length_scale: float = 1.0  # >1 = slower

    # ElevenLabs (cloud)
    elevenlabs_api_key: str = field(default_factory=lambda: os.environ.get("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"  # "Adam" - documentary style
    elevenlabs_model: str = "eleven_multilingual_v2"

    # Kokoro (local, 82M params)
    kokoro_voice: str = "af_heart"  # see https://huggingface.co/hexgrad/Kokoro-82M
    kokoro_lang: str = "a"  # a=American English, b=British
    kokoro_speed: float = 1.0

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
