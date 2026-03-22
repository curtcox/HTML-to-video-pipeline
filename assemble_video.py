"""
Assemble final video from audio, visual frames, and captions using FFmpeg.

Creates a video where each segment's visual frame is displayed for the
duration of its corresponding audio, with captions burned in.
"""
import os
import subprocess
import json
import tempfile
import wave
from typing import List, Dict, Optional
from dataclasses import dataclass

from config import PipelineConfig
from generate_audio import AudioSegment
from generate_visuals import VisualFrame


@dataclass
class SegmentTiming:
    """Exact timeline info for one segment in the assembled audio."""
    segment_index: int
    audio_duration: float
    pause_duration: float

    @property
    def total_duration(self) -> float:
        return self.audio_duration + self.pause_duration


def create_concat_file(
    entries: List[Dict],
    output_path: str,
) -> str:
    """
    Create an FFmpeg concat demuxer file.

    entries: list of {"file": path, "duration": seconds}
    """
    with open(output_path, "w") as f:
        for entry in entries:
            f.write(f"file '{entry['file']}'\n")
            f.write(f"duration {entry['duration']}\n")
        # Repeat last entry (FFmpeg concat quirk)
        if entries:
            f.write(f"file '{entries[-1]['file']}'\n")
    return output_path


def concatenate_audio_files(
    audio_segments: List[AudioSegment],
    config: PipelineConfig,
    output_path: str,
) -> Dict[int, SegmentTiming]:
    """
    Concatenate all audio segments into a single audio file,
    with pauses between sections.
    """
    normalized_segments: List[str] = []
    segment_timings: Dict[int, SegmentTiming] = {}
    sample_rate = 44100

    with tempfile.TemporaryDirectory(prefix="audio-concat-", dir=os.path.dirname(output_path)) as tmpdir:
        for i, seg in enumerate(audio_segments):
            if not os.path.exists(seg.audio_path):
                continue

            normalized_path = os.path.join(tmpdir, f"segment_{i:04d}.wav")
            seg.duration = _normalize_audio_for_concat(seg.audio_path, normalized_path, sample_rate)
            normalized_segments.append(normalized_path)

            pause = _pause_after_segment(seg.segment_type, config)
            if pause > 0:
                silence_path = os.path.join(tmpdir, f"silence_{i:04d}.wav")
                pause = _generate_silence_wav(pause, silence_path, sample_rate)
                normalized_segments.append(silence_path)

            segment_timings[seg.segment_index] = SegmentTiming(
                segment_index=seg.segment_index,
                audio_duration=seg.duration,
                pause_duration=pause,
            )

        if not normalized_segments:
            raise ValueError("No audio segments found to concatenate.")

        _concatenate_wav_files(normalized_segments, output_path)

    return segment_timings


def _normalize_audio_for_concat(input_path: str, output_path: str, sample_rate: int) -> float:
    """Convert an audio clip to trimmed mono PCM WAV and return its duration."""
    trim_filter = (
        "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-35dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0.02:start_threshold=-35dB,"
        "areverse"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", str(sample_rate),
        "-af", trim_filter,
        "-c:a", "pcm_s16le",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return _probe_audio_duration(output_path)


def _generate_silence_wav(duration: float, output_path: str, sample_rate: int) -> float:
    """Generate a silent mono PCM WAV segment and return its exact duration."""
    frame_count = max(1, int(round(duration * sample_rate)))
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return frame_count / sample_rate


def _concatenate_wav_files(input_paths: List[str], output_path: str):
    """Join normalized WAV files without introducing lossy encoder padding."""
    with wave.open(input_paths[0], "rb") as first_wav:
        nchannels = first_wav.getnchannels()
        sampwidth = first_wav.getsampwidth()
        framerate = first_wav.getframerate()

    with wave.open(output_path, "wb") as out_wav:
        out_wav.setnchannels(nchannels)
        out_wav.setsampwidth(sampwidth)
        out_wav.setframerate(framerate)

        for path in input_paths:
            with wave.open(path, "rb") as in_wav:
                if (
                    in_wav.getnchannels() != nchannels
                    or in_wav.getsampwidth() != sampwidth
                    or in_wav.getframerate() != framerate
                ):
                    raise ValueError(f"Audio normalization mismatch for {path}")
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))


def _probe_audio_duration(path: str) -> float:
    """Read an audio file's duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def build_frame_sequence(
    visual_frames: List[VisualFrame],
    segment_timings: Dict[int, SegmentTiming],
) -> List[Dict]:
    """
    Build the sequence of (image, duration) pairs for the video.

    Maps audio durations onto visual frames, handling the many-to-one
    relationship (multiple paragraphs may map to frames with different
    durations than their audio).
    """
    grouped_frames: List[tuple[int, List[VisualFrame]]] = []
    for frame in visual_frames:
        if grouped_frames and grouped_frames[-1][0] == frame.segment_index:
            grouped_frames[-1][1].append(frame)
        else:
            grouped_frames.append((frame.segment_index, [frame]))

    sequence = []
    for segment_index, frames in grouped_frames:
        timing = segment_timings.get(segment_index)
        target_duration = _target_segment_duration(timing, frames)
        frame_durations = _allocate_group_durations(frames, target_duration)

        for frame, duration in zip(frames, frame_durations):
            sequence.append({
                "file": os.path.abspath(frame.image_path),
                "duration": duration,
            })

    return sequence


def _target_segment_duration(
    timing: Optional[SegmentTiming],
    frames: List[VisualFrame],
) -> float:
    """Compute how much screen time this segment should get in total."""
    if timing is None:
        explicit = sum(frame.duration for frame in frames if frame.duration > 0)
        return explicit if explicit > 0 else 5.0

    return timing.total_duration


def _pause_after_segment(segment_type: str, config: PipelineConfig) -> float:
    """Use one pause policy for both audio assembly and frame timing."""
    if segment_type == "heading":
        return config.pause_after_heading
    if segment_type in {"paragraph", "blockquote"}:
        return config.pause_between_paragraphs
    if segment_type == "title":
        return 0.3
    return 0.3


def _allocate_group_durations(frames: List[VisualFrame], target_duration: float) -> List[float]:
    """Distribute a segment's time budget across its frames without global drift."""
    if not frames:
        return []

    fixed = [max(frame.duration, 0.0) for frame in frames]
    fixed_total = sum(duration for duration in fixed if duration > 0)
    flexible_indexes = [i for i, duration in enumerate(fixed) if duration == 0]

    if flexible_indexes:
        # Keep most of the time on the narration-matched frame(s).
        max_fixed_total = target_duration * 0.35
        allowed_fixed_total = min(fixed_total, max_fixed_total)
        scale = allowed_fixed_total / fixed_total if fixed_total > 0 else 0.0
        durations = [
            duration * scale if duration > 0 else 0.0
            for duration in fixed
        ]
        remaining = max(0.0, target_duration - sum(durations))
        share = remaining / len(flexible_indexes)
        for idx in flexible_indexes:
            durations[idx] = share
        return durations

    if fixed_total <= 0:
        share = target_duration / len(frames)
        return [share for _ in frames]

    scale = target_duration / fixed_total
    return [duration * scale for duration in fixed]


def assemble_video(
    visual_frames: List[VisualFrame],
    audio_segments: List[AudioSegment],
    srt_path: str,
    config: PipelineConfig,
    output_dir: str,
) -> str:
    """
    Assemble the final video.

    Steps:
    1. Concatenate audio with pauses
    2. Build image sequence with matched durations
    3. Combine video + audio + captions
    """
    os.makedirs(output_dir, exist_ok=True)

    print("Step 1: Concatenating audio...")
    combined_audio = os.path.join(output_dir, "combined_audio.wav")
    segment_timings = concatenate_audio_files(audio_segments, config, combined_audio)

    # Get total audio duration
    total_audio_duration = _probe_audio_duration(combined_audio)
    print(f"  Total audio: {total_audio_duration:.1f}s")

    print("Step 2: Building frame sequence...")
    frame_sequence = build_frame_sequence(visual_frames, segment_timings)

    # Create concat file
    concat_path = os.path.join(output_dir, "frames.txt")
    create_concat_file(frame_sequence, concat_path)

    print("Step 3: Creating video from frames...")
    raw_video = os.path.join(output_dir, "raw_video.mp4")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_path,
        "-vsync", "vfr",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={config.video_width}:{config.video_height}:force_original_aspect_ratio=decrease,pad={config.video_width}:{config.video_height}:(ow-iw)/2:(oh-ih)/2",
        raw_video,
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    print("Step 4: Combining video + audio + captions...")
    final_output = os.path.join(output_dir, config.output_filename)

    # Build subtitle filter
    srt_abs = os.path.abspath(srt_path)
    # Escape special characters for FFmpeg filter
    srt_escaped = srt_abs.replace(":", "\\:").replace("'", "\\'")

    subtitle_style = (
        f"FontSize={config.font_size_caption},"
        f"PrimaryColour=&H00FFFFFF,"  # white
        f"OutlineColour=&H00000000,"  # black outline
        f"BorderStyle=3,"
        f"Outline=2,"
        f"Shadow=1,"
        f"MarginV=60"
    )

    # When passing as a list (no shell), don't wrap force_style value in quotes.
    vf = f"subtitles={srt_escaped}:force_style={subtitle_style}"
    cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-i", combined_audio,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fall back: combine without subtitles
        print(f"  Subtitle burn-in failed (exit {result.returncode}): {result.stderr[-500:]}")
        print("  Falling back to video without burned-in subtitles...")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", raw_video,
            "-i", combined_audio,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            final_output,
        ]
        subprocess.run(cmd_fallback, capture_output=True, check=True)

    print(f"\nFinal video: {final_output}")
    print(f"Duration: {total_audio_duration:.1f}s ({total_audio_duration/60:.1f} minutes)")
    return final_output


if __name__ == "__main__":
    print("Video assembler module loaded. Use via pipeline.py")
