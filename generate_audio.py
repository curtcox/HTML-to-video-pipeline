"""
Generate TTS audio for each segment using ElevenLabs.

Produces individual audio files per segment plus timing metadata
for synchronizing captions and visuals.
"""
import os
import json
import struct
import wave
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

from config import PipelineConfig
from parse_article import Segment


@dataclass
class AudioSegment:
    """Metadata for a generated audio clip."""
    segment_index: int
    audio_path: str
    duration: float  # seconds
    text: str
    segment_type: str


def get_wav_duration(filepath: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(filepath, 'r') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return frames / float(rate)


def get_mp3_duration(filepath: str) -> float:
    """Estimate duration of an MP3 file in seconds."""
    file_size = os.path.getsize(filepath)
    # Rough estimate: typical MP3 bitrate ~128kbps
    # More accurate: use ffprobe
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        # Fallback: estimate from file size assuming 128kbps
        return file_size / (128 * 1000 / 8)


def generate_silence(duration: float, output_path: str, sample_rate: int = 44100):
    """Generate a silent WAV file of the given duration."""
    n_frames = int(sample_rate * duration)
    with wave.open(output_path, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00\x00' * n_frames)


def generate_audio_elevenlabs(
    text: str,
    output_path: str,
    config: PipelineConfig,
) -> float:
    """
    Generate audio using ElevenLabs API.

    Returns duration in seconds.
    """
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=config.elevenlabs_api_key)

    audio_generator = client.text_to_speech.convert(
        voice_id=config.elevenlabs_voice_id,
        text=text,
        model_id=config.elevenlabs_model,
        output_format="mp3_44100_128",
    )

    # Write audio data
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    return get_mp3_duration(output_path)


def estimate_duration(text: str, wpm: float = 155) -> float:
    """Estimate speech duration from text. Fallback when no TTS available."""
    words = len(text.split())
    return words / wpm * 60


def generate_all_audio(
    segments: List[Segment],
    config: PipelineConfig,
    output_dir: str,
    dry_run: bool = False,
) -> List[AudioSegment]:
    """
    Generate audio for all segments.

    Args:
        segments: Parsed article segments
        config: Pipeline configuration
        output_dir: Where to save audio files
        dry_run: If True, estimate durations without calling TTS API

    Returns:
        List of AudioSegment with timing metadata
    """
    os.makedirs(output_dir, exist_ok=True)
    audio_segments: List[AudioSegment] = []

    for i, seg in enumerate(segments):
        audio_path = os.path.join(output_dir, f"audio_{i:04d}.mp3")

        if seg.segment_type == "title":
            # Title cards get a brief pause, not narration
            # (unless you want the title read aloud)
            text = seg.text
        else:
            text = seg.text

        if not text.strip():
            continue

        if dry_run:
            duration = estimate_duration(text)
        else:
            if config.tts_provider == "elevenlabs":
                duration = generate_audio_elevenlabs(text, audio_path, config)
            else:
                raise ValueError(f"Unsupported TTS provider: {config.tts_provider}")

        audio_segments.append(AudioSegment(
            segment_index=i,
            audio_path=audio_path,
            duration=duration,
            text=text,
            segment_type=seg.segment_type,
        ))

        print(f"  [{i:3d}] {seg.segment_type:>10} | {duration:6.1f}s | {text[:60]}...")

    # Save timing metadata
    metadata_path = os.path.join(output_dir, "audio_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump([asdict(a) for a in audio_segments], f, indent=2)

    total = sum(a.duration for a in audio_segments)
    print(f"\nTotal audio duration: {total:.1f}s ({total/60:.1f} minutes)")

    return audio_segments


if __name__ == "__main__":
    from parse_article import fetch_html, parse_article
    config = PipelineConfig()
    # Dry run test
    segments = [
        Segment("title", "Why AI Still Makes Things Up"),
        Segment("heading", "The problem in plain terms"),
        Segment("paragraph", "You've probably heard that AI chatbots hallucinate."),
    ]
    results = generate_all_audio(segments, config, "output/audio", dry_run=True)
    for r in results:
        print(f"  {r.segment_type}: {r.duration:.1f}s")
