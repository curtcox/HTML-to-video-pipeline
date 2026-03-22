"""
Generate TTS audio for each segment.

Supports four backends:
  - say       : macOS built-in TTS (default, no install needed)
  - piper     : fast local neural TTS  (pip install piper-tts)
  - elevenlabs: cloud TTS              (pip install elevenlabs)
  - kokoro    : local 82M-param model  (pip install kokoro soundfile)

Produces individual audio files per segment plus timing metadata
for synchronizing captions and visuals.
"""
import os
import json
import subprocess
import wave
from typing import List
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


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------

def get_wav_duration(filepath: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(filepath, 'r') as wav:
        return wav.getnframes() / float(wav.getframerate())


def get_audio_duration(filepath: str) -> float:
    """Get duration of any audio file via ffprobe, with WAV fast-path."""
    if filepath.endswith(".wav"):
        return get_wav_duration(filepath)
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            capture_output=True, text=True,
        )
        return float(result.stdout.strip())
    except Exception:
        # Fallback: estimate from file size assuming 128 kbps MP3
        return os.path.getsize(filepath) / (128 * 1000 / 8)


def estimate_duration(text: str, wpm: float = 155) -> float:
    """Estimate speech duration from text. Fallback when no TTS available."""
    words = len(text.split())
    return words / wpm * 60


def generate_silence(duration: float, output_path: str, sample_rate: int = 44100):
    """Generate a silent WAV file of the given duration."""
    n_frames = int(sample_rate * duration)
    with wave.open(output_path, 'w') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00\x00' * n_frames)


# ---------------------------------------------------------------------------
# Backend: macOS say
# ---------------------------------------------------------------------------

def generate_audio_say(text: str, output_path: str, config: PipelineConfig) -> float:
    """
    Generate audio using macOS built-in `say` command.
    Outputs AIFF then converts to WAV via ffmpeg for consistency.
    """
    aiff_path = output_path.rsplit(".", 1)[0] + ".aiff"
    subprocess.run(
        ["say", "-v", config.say_voice, "-r", str(config.say_rate),
         "-o", aiff_path, text],
        check=True,
    )
    # Convert AIFF → WAV (pipeline expects WAV)
    subprocess.run(
        ["ffmpeg", "-y", "-i", aiff_path, "-ar", "44100", "-ac", "1", output_path],
        capture_output=True, check=True,
    )
    os.remove(aiff_path)
    return get_wav_duration(output_path)


# ---------------------------------------------------------------------------
# Backend: Piper  (pip install piper-tts)
# ---------------------------------------------------------------------------

def generate_audio_piper(text: str, output_path: str, config: PipelineConfig) -> float:
    """
    Generate audio using Piper local neural TTS.
    First run downloads the voice model automatically.
    """
    from piper import PiperVoice
    from piper.download import get_voices, ensure_voice_exists

    # Ensure model is downloaded
    data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "piper_voices")
    os.makedirs(data_dir, exist_ok=True)
    voices = get_voices(data_dir, update_voices=False)
    ensure_voice_exists(config.piper_model, data_dir, data_dir, voices)

    model_path = os.path.join(data_dir, config.piper_model, f"{config.piper_model}.onnx")
    voice = PiperVoice.load(model_path)

    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize(text, wav_file, length_scale=config.piper_length_scale)

    return get_wav_duration(output_path)


# ---------------------------------------------------------------------------
# Backend: ElevenLabs  (pip install elevenlabs)
# ---------------------------------------------------------------------------

def generate_audio_elevenlabs(text: str, output_path: str, config: PipelineConfig) -> float:
    """Generate audio using ElevenLabs cloud API. Returns duration in seconds."""
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=config.elevenlabs_api_key)
    audio_generator = client.text_to_speech.convert(
        voice_id=config.elevenlabs_voice_id,
        text=text,
        model_id=config.elevenlabs_model,
        output_format="mp3_44100_128",
    )

    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    return get_audio_duration(output_path)


# ---------------------------------------------------------------------------
# Backend: Kokoro  (pip install kokoro soundfile)
# ---------------------------------------------------------------------------

# Module-level cache so we only load the model once per process
_kokoro_pipeline = None

def _get_kokoro_pipeline(lang: str):
    global _kokoro_pipeline
    if _kokoro_pipeline is None or _kokoro_pipeline._lang != lang:
        from kokoro import KPipeline
        _kokoro_pipeline = KPipeline(lang_code=lang)
        _kokoro_pipeline._lang = lang  # tag for cache check
    return _kokoro_pipeline

def generate_audio_kokoro(text: str, output_path: str, config: PipelineConfig) -> float:
    """Generate audio using Kokoro local TTS (82M params). Outputs WAV at 24 kHz."""
    import soundfile as sf
    import numpy as np

    pipeline = _get_kokoro_pipeline(config.kokoro_lang)
    chunks = []
    for _graphemes, _phonemes, audio in pipeline(
        text, voice=config.kokoro_voice, speed=config.kokoro_speed
    ):
        chunks.append(audio)

    if not chunks:
        # Fallback: generate brief silence
        generate_silence(0.5, output_path, sample_rate=24000)
        return 0.5

    combined = np.concatenate(chunks)
    sf.write(output_path, combined, 24000)
    return len(combined) / 24000.0


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

TTS_BACKENDS = {
    "say":        (generate_audio_say,        ".wav"),
    "piper":      (generate_audio_piper,      ".wav"),
    "elevenlabs": (generate_audio_elevenlabs, ".mp3"),
    "kokoro":     (generate_audio_kokoro,     ".wav"),
}


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
        dry_run: If True, estimate durations without calling any TTS

    Returns:
        List of AudioSegment with timing metadata
    """
    os.makedirs(output_dir, exist_ok=True)
    audio_segments: List[AudioSegment] = []

    provider = config.tts_provider
    if provider not in TTS_BACKENDS:
        raise ValueError(
            f"Unknown tts_provider '{provider}'. "
            f"Choose from: {', '.join(TTS_BACKENDS)}"
        )
    backend_fn, ext = TTS_BACKENDS[provider]

    print(f"TTS provider: {provider}" + (" (dry run)" if dry_run else ""))

    for i, seg in enumerate(segments):
        audio_path = os.path.join(output_dir, f"audio_{i:04d}{ext}")
        text = seg.text
        if not text.strip():
            continue

        if dry_run:
            duration = estimate_duration(text)
        else:
            duration = backend_fn(text, audio_path, config)

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
    config = PipelineConfig()
    segments = [
        Segment("title", "Why AI Still Makes Things Up"),
        Segment("heading", "The problem in plain terms"),
        Segment("paragraph", "You've probably heard that AI chatbots hallucinate."),
    ]
    results = generate_all_audio(segments, config, "output/audio", dry_run=True)
    for r in results:
        print(f"  {r.segment_type}: {r.duration:.1f}s")
