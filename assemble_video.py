"""
Assemble final video from audio, visual frames, and captions using FFmpeg.

Creates a video where each segment's visual frame is displayed for the
duration of its corresponding audio, with captions burned in.
"""
import os
import subprocess
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

from config import PipelineConfig
from generate_audio import AudioSegment
from generate_visuals import VisualFrame


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
) -> str:
    """
    Concatenate all audio segments into a single audio file,
    with pauses between sections.
    """
    # Build concat list with silence gaps
    list_path = output_path + ".list.txt"
    silence_dir = os.path.dirname(output_path)

    with open(list_path, "w") as f:
        for i, seg in enumerate(audio_segments):
            if not os.path.exists(seg.audio_path):
                continue
            f.write(f"file '{os.path.abspath(seg.audio_path)}'\n")

            # Add pause after certain segment types
            if seg.segment_type == "heading":
                pause = config.pause_after_heading
            elif seg.segment_type == "paragraph":
                pause = config.pause_between_paragraphs
            else:
                pause = 0.3

            if pause > 0:
                silence_path = os.path.join(silence_dir, f"silence_{i}.mp3")
                _generate_silence_mp3(pause, silence_path)
                f.write(f"file '{os.path.abspath(silence_path)}'\n")

    # Concatenate with ffmpeg
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c:a", "libmp3lame", "-q:a", "2",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _generate_silence_mp3(duration: float, output_path: str):
    """Generate a silent MP3 file."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration),
        "-c:a", "libmp3lame", "-q:a", "9",
        output_path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def build_frame_sequence(
    visual_frames: List[VisualFrame],
    audio_segments: List[AudioSegment],
    config: PipelineConfig,
) -> List[Dict]:
    """
    Build the sequence of (image, duration) pairs for the video.

    Maps audio durations onto visual frames, handling the many-to-one
    relationship (multiple paragraphs may map to frames with different
    durations than their audio).
    """
    # Create a map from segment_index to audio duration
    audio_duration_map = {}
    for aseg in audio_segments:
        audio_duration_map[aseg.segment_index] = aseg.duration

    sequence = []
    for vf in visual_frames:
        if vf.duration > 0:
            # Fixed duration frame (title cards, section cards, diagrams)
            duration = vf.duration
        else:
            # Duration from audio
            duration = audio_duration_map.get(vf.segment_index, 5.0)
            # Add pause
            duration += config.pause_between_paragraphs

        sequence.append({
            "file": os.path.abspath(vf.image_path),
            "duration": duration,
        })

    return sequence


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
    combined_audio = os.path.join(output_dir, "combined_audio.mp3")
    concatenate_audio_files(audio_segments, config, combined_audio)

    # Get total audio duration
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", combined_audio,
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    total_audio_duration = float(result.stdout.strip())
    print(f"  Total audio: {total_audio_duration:.1f}s")

    print("Step 2: Building frame sequence...")
    frame_sequence = build_frame_sequence(visual_frames, audio_segments, config)

    # Adjust frame durations to match total audio
    total_frame_duration = sum(f["duration"] for f in frame_sequence)
    if total_frame_duration > 0:
        scale = total_audio_duration / total_frame_duration
        for f in frame_sequence:
            f["duration"] *= scale

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
