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

TRANSITION_DURATION_SECONDS = 2.0
TRANSITION_BORROW_SECONDS = 1.0
MIN_STATIC_HOLD_SECONDS = 0.5


@dataclass
class SegmentTiming:
    """Exact timeline info for one segment in the assembled audio."""
    segment_index: int
    audio_duration: float
    pause_duration: float

    @property
    def total_duration(self) -> float:
        return self.audio_duration + self.pause_duration


@dataclass
class SyncReport:
    """High-level sync verification for assembled outputs."""
    combined_audio_duration: float
    frame_sequence_duration: float
    clip_plan_duration: float
    raw_video_duration: float
    final_video_duration: float
    clip_plan_minus_audio: float
    raw_minus_audio: float
    final_minus_audio: float
    warnings: List[str]


@dataclass
class ClipPlanEntry:
    """One rendered clip in the raw visual timeline."""
    kind: str  # hold or transition
    frame_count: int
    image_path: str
    next_image_path: Optional[str] = None


def create_concat_file(
    entries: List[Dict],
    output_path: str,
    include_durations: bool = True,
) -> str:
    """
    Create an FFmpeg concat demuxer file.

    entries: list of {"file": path, "duration": seconds}
    """
    with open(output_path, "w") as f:
        for entry in entries:
            f.write(f"file '{entry['file']}'\n")
            if include_durations:
                f.write(f"duration {entry['duration']}\n")
        # Repeat last entry (FFmpeg concat quirk)
        if include_durations and entries:
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
    return _probe_media_duration(output_path)


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


def _probe_media_duration(path: str) -> float:
    """Read a media file's duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _duration_to_frame_count(duration: float, fps: int) -> int:
    """Round a duration onto an exact frame boundary for deterministic video timing."""
    return max(1, round(duration * fps))


def _frame_count_to_duration(frame_count: int, fps: int) -> float:
    """Convert a frame count back to seconds."""
    return frame_count / fps


def _render_frame_clip(
    image_path: str,
    frame_count: int,
    output_path: str,
    config: PipelineConfig,
) -> float:
    """Render one still image into a short video clip with an exact frame count."""
    clip_duration = _frame_count_to_duration(frame_count, config.fps)
    vf = (
        f"scale={config.video_width}:{config.video_height}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={config.video_width}:{config.video_height}:(ow-iw)/2:(oh-ih)/2"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-frames:v", str(frame_count),
        "-r", str(config.fps),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return clip_duration


def _render_transition_clip(
    image_path: str,
    next_image_path: str,
    frame_count: int,
    output_path: str,
    config: PipelineConfig,
) -> float:
    """Render a vertical upward slide transition between two frames."""
    clip_duration = _frame_count_to_duration(frame_count, config.fps)
    scaled = (
        f"scale={config.video_width}:{config.video_height}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={config.video_width}:{config.video_height}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1"
    )
    filter_complex = (
        f"[0:v]{scaled}[v0];"
        f"[1:v]{scaled}[v1];"
        f"[v0][v1]xfade=transition=slideup:duration={clip_duration}:offset=0,format=yuv420p[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", str(clip_duration),
        "-i", image_path,
        "-loop", "1",
        "-t", str(clip_duration),
        "-i", next_image_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-frames:v", str(frame_count),
        "-r", str(config.fps),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return clip_duration


def _plan_clip_sequence(frame_sequence: List[Dict], config: PipelineConfig) -> List[ClipPlanEntry]:
    """Replace most hard cuts with duration-preserving scroll transitions."""
    if not frame_sequence:
        return []

    base_counts = [
        _duration_to_frame_count(entry["duration"], config.fps)
        for entry in frame_sequence
    ]
    remaining_hold_counts = base_counts[:]
    borrow_frames = _duration_to_frame_count(TRANSITION_BORROW_SECONDS, config.fps)
    transition_frames = _duration_to_frame_count(TRANSITION_DURATION_SECONDS, config.fps)
    min_hold_frames = _duration_to_frame_count(MIN_STATIC_HOLD_SECONDS, config.fps)
    apply_transition = [False] * max(0, len(frame_sequence) - 1)

    for i in range(len(frame_sequence) - 1):
        if (
            remaining_hold_counts[i] - borrow_frames >= min_hold_frames
            and remaining_hold_counts[i + 1] - borrow_frames >= min_hold_frames
        ):
            apply_transition[i] = True
            remaining_hold_counts[i] -= borrow_frames
            remaining_hold_counts[i + 1] -= borrow_frames

    clip_plan: List[ClipPlanEntry] = []
    for i, entry in enumerate(frame_sequence):
        if remaining_hold_counts[i] > 0:
            clip_plan.append(
                ClipPlanEntry(
                    kind="hold",
                    frame_count=remaining_hold_counts[i],
                    image_path=entry["file"],
                )
            )
        if i < len(frame_sequence) - 1 and apply_transition[i]:
            clip_plan.append(
                ClipPlanEntry(
                    kind="transition",
                    frame_count=transition_frames,
                    image_path=entry["file"],
                    next_image_path=frame_sequence[i + 1]["file"],
                )
            )

    return clip_plan


def _render_frame_sequence_video(
    frame_sequence: List[Dict],
    raw_video_path: str,
    config: PipelineConfig,
    debug_concat_path: Optional[str] = None,
) -> float:
    """Render the visual timeline as concatenated hold and transition clips."""
    with tempfile.TemporaryDirectory(prefix="frame-clips-", dir=os.path.dirname(raw_video_path)) as tmpdir:
        clip_entries: List[Dict] = []
        total_duration = 0.0
        clip_plan = _plan_clip_sequence(frame_sequence, config)

        for i, plan_entry in enumerate(clip_plan):
            clip_path = os.path.join(tmpdir, f"clip_{i:04d}.mp4")
            if plan_entry.kind == "transition":
                clip_duration = _render_transition_clip(
                    plan_entry.image_path,
                    plan_entry.next_image_path or plan_entry.image_path,
                    plan_entry.frame_count,
                    clip_path,
                    config,
                )
            else:
                clip_duration = _render_frame_clip(
                    plan_entry.image_path,
                    plan_entry.frame_count,
                    clip_path,
                    config,
                )
            clip_entries.append({"file": os.path.abspath(clip_path), "duration": clip_duration})
            total_duration += clip_duration

        clip_list_path = os.path.join(tmpdir, "clips.txt")
        create_concat_file(clip_entries, clip_list_path, include_durations=False)
        if debug_concat_path:
            create_concat_file(clip_entries, debug_concat_path, include_durations=False)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", clip_list_path,
            "-c", "copy",
            raw_video_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    return total_duration


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
        frame_durations = _allocate_group_durations(frames, timing)

        for frame, duration in zip(frames, frame_durations):
            sequence.append({
                "file": os.path.abspath(frame.image_path),
                "duration": duration,
            })

    return sequence


def _pause_after_segment(segment_type: str, config: PipelineConfig) -> float:
    """Use one pause policy for both audio assembly and frame timing."""
    if segment_type == "heading":
        return config.pause_after_heading
    if segment_type in {"paragraph", "blockquote"}:
        return config.pause_between_paragraphs
    if segment_type == "title":
        return 0.3
    return 0.3


def _allocate_group_durations(
    frames: List[VisualFrame],
    timing: Optional[SegmentTiming],
) -> List[float]:
    """Distribute time so narration-matched frames stay aligned with spoken audio."""
    if not frames:
        return []

    if timing is None:
        target_duration = sum(max(frame.duration, 0.0) for frame in frames)
        if target_duration <= 0:
            target_duration = 5.0
        share = target_duration / len(frames)
        return [share for _ in frames]

    audio_budget = timing.audio_duration
    pause_budget = timing.pause_duration
    fixed = [max(frame.duration, 0.0) for frame in frames]
    fixed_total = sum(duration for duration in fixed if duration > 0)
    flexible_indexes = [i for i, duration in enumerate(fixed) if duration == 0]
    durations = [0.0 for _ in frames]

    if flexible_indexes:
        if fixed_total > 0 and pause_budget > 0:
            scale = min(1.0, pause_budget / fixed_total)
            for idx, duration in enumerate(fixed):
                if duration > 0:
                    durations[idx] = duration * scale
        remaining = audio_budget + max(0.0, pause_budget - sum(durations))
        share = remaining / len(flexible_indexes) if flexible_indexes else 0.0
        for idx in flexible_indexes:
            durations[idx] = share
        return durations

    primary_idx = _choose_primary_frame(frames)
    durations[primary_idx] = audio_budget
    supplemental_indexes = [i for i in range(len(frames)) if i != primary_idx]
    supplemental_total = sum(fixed[i] for i in supplemental_indexes if fixed[i] > 0)

    if supplemental_indexes and pause_budget > 0:
        if supplemental_total > 0:
            scale = pause_budget / supplemental_total
            for idx in supplemental_indexes:
                if fixed[idx] > 0:
                    durations[idx] = fixed[idx] * scale
        else:
            share = pause_budget / len(supplemental_indexes)
            for idx in supplemental_indexes:
                durations[idx] = share
    else:
        durations[primary_idx] += pause_budget

    return durations


def _choose_primary_frame(frames: List[VisualFrame]) -> int:
    """Pick the frame that should remain on screen while the segment audio is spoken."""
    for idx, frame in enumerate(frames):
        if not os.path.basename(frame.image_path).startswith("diagram_"):
            return idx
    return 0


def assemble_video(
    visual_frames: List[VisualFrame],
    audio_segments: List[AudioSegment],
    srt_path: str,
    config: PipelineConfig,
    output_dir: str,
) -> tuple[str, SyncReport]:
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
    total_audio_duration = _probe_media_duration(combined_audio)
    print(f"  Total audio: {total_audio_duration:.1f}s")

    print("Step 2: Building frame sequence...")
    frame_sequence = build_frame_sequence(visual_frames, segment_timings)
    frame_sequence_duration = sum(entry["duration"] for entry in frame_sequence)

    # Create debug concat file
    concat_path = os.path.join(output_dir, "frames.txt")
    create_concat_file(frame_sequence, concat_path)

    print("Step 3: Creating video from frames...")
    raw_video = os.path.join(output_dir, "raw_video.mp4")
    clip_plan_duration = _render_frame_sequence_video(frame_sequence, raw_video, config)
    print(f"  Planned visual timeline: {clip_plan_duration:.1f}s")

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

    raw_video_duration = _probe_media_duration(raw_video)
    final_video_duration = _probe_media_duration(final_output)
    sync_report = _build_sync_report(
        total_audio_duration,
        frame_sequence_duration,
        clip_plan_duration,
        raw_video_duration,
        final_video_duration,
    )
    with open(os.path.join(output_dir, "sync_report.json"), "w") as f:
        json.dump(sync_report.__dict__, f, indent=2)

    print(f"\nFinal video: {final_output}")
    print(f"Duration: {total_audio_duration:.1f}s ({total_audio_duration/60:.1f} minutes)")
    if sync_report.warnings:
        print("Sync warnings:")
        for warning in sync_report.warnings:
            print(f"  - {warning}")
    return final_output, sync_report


def _build_sync_report(
    combined_audio_duration: float,
    frame_sequence_duration: float,
    clip_plan_duration: float,
    raw_video_duration: float,
    final_video_duration: float,
) -> SyncReport:
    """Summarize timeline mismatches and emit warnings when they exceed tolerance."""
    clip_plan_minus_audio = clip_plan_duration - combined_audio_duration
    raw_minus_audio = raw_video_duration - combined_audio_duration
    final_minus_audio = final_video_duration - combined_audio_duration
    frame_minus_audio = frame_sequence_duration - combined_audio_duration
    warnings: List[str] = []

    if abs(frame_minus_audio) > 0.05:
        warnings.append(
            f"Frame sequence differs from audio by {frame_minus_audio:.3f}s before raw video render."
        )
    if abs(clip_plan_minus_audio) > 0.05:
        warnings.append(
            f"Rendered clip plan differs from audio by {clip_plan_minus_audio:.3f}s before raw video concat."
        )
    if abs(raw_minus_audio) > 0.15:
        warnings.append(
            f"Raw video differs from combined audio by {raw_minus_audio:.3f}s."
        )
    if abs(final_minus_audio) > 0.15:
        warnings.append(
            f"Final video differs from combined audio by {final_minus_audio:.3f}s."
        )

    return SyncReport(
        combined_audio_duration=combined_audio_duration,
        frame_sequence_duration=frame_sequence_duration,
        clip_plan_duration=clip_plan_duration,
        raw_video_duration=raw_video_duration,
        final_video_duration=final_video_duration,
        clip_plan_minus_audio=clip_plan_minus_audio,
        raw_minus_audio=raw_minus_audio,
        final_minus_audio=final_minus_audio,
        warnings=warnings,
    )


if __name__ == "__main__":
    print("Video assembler module loaded. Use via pipeline.py")
