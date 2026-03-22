#!/usr/bin/env python3
"""
Article-to-Video Pipeline

Converts an HTML article into a narrated video with:
- Text-to-speech narration (ElevenLabs)
- Synchronized captions (SRT burned in)
- QR codes for citation URLs
- Diagrams and illustrations for key concepts
- Section title cards

Usage:
    python pipeline.py <article_url> [--dry-run] [--output-dir OUTPUT_DIR]

Environment:
    ELEVENLABS_API_KEY - Required for TTS (unless --dry-run)
"""
import argparse
import os
import sys
import json
import time

from config import PipelineConfig
from parse_article import fetch_html, parse_article, get_all_citation_urls, segments_from_json, segments_to_json
from generate_qr import generate_all_qr_codes
from generate_visuals import generate_frames_for_segments
from generate_audio import generate_all_audio
from generate_captions import generate_srt
from assemble_video import assemble_video


def run_pipeline(config: PipelineConfig, dry_run: bool = False, segments_json: str = ""):
    """
    Run the full article-to-video pipeline.

    Args:
        config: Pipeline configuration
        dry_run: If True, estimate audio durations without calling TTS API
        segments_json: Path to pre-parsed segments JSON (skips HTML fetch/parse)
    """
    start_time = time.time()
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # ── Step 1: Parse Article ─────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Parsing article")
    print("=" * 60)
    if segments_json and os.path.exists(segments_json):
        segments = segments_from_json(segments_json)
        print(f"  Loaded {len(segments)} segments from {segments_json}")
    else:
        html = fetch_html(config.article_url)
        segments = parse_article(html)
        print(f"  Parsed {len(segments)} segments")

    # Save parsed segments for debugging
    segments_data = []
    for s in segments:
        segments_data.append({
            "type": s.segment_type,
            "text": s.text,
            "section": s.section_title,
            "section_index": s.section_index,
            "citations": [{"text": c.text, "url": c.url} for c in s.citations],
        })
    with open(os.path.join(output_dir, "segments.json"), "w") as f:
        json.dump(segments_data, f, indent=2)

    # ── Step 2: Generate QR Codes ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Generating QR codes")
    print("=" * 60)
    all_urls = get_all_citation_urls(segments)
    print(f"  {len(all_urls)} unique citation URLs")
    qr_dir = os.path.join(output_dir, "qr_codes")
    qr_map = generate_all_qr_codes(all_urls, qr_dir, size=config.qr_size)
    print(f"  Generated {len(qr_map)} QR code images")

    # ── Step 3: Generate Visual Frames ────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Generating visual frames")
    print("=" * 60)
    frames_dir = os.path.join(output_dir, "frames")
    visual_frames = generate_frames_for_segments(segments, qr_map, config, frames_dir)
    print(f"  Generated {len(visual_frames)} visual frames")

    # ── Step 4: Generate Audio ────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"STEP 4: Generating audio ({'DRY RUN' if dry_run else 'ElevenLabs'})")
    print("=" * 60)
    audio_dir = os.path.join(output_dir, "audio")
    audio_segments = generate_all_audio(segments, config, audio_dir, dry_run=dry_run)
    total_duration = sum(a.duration for a in audio_segments)
    print(f"  Estimated total: {total_duration:.0f}s ({total_duration/60:.1f} min)")

    # ── Step 5: Generate Captions ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 5: Generating captions")
    print("=" * 60)
    srt_path = os.path.join(output_dir, "captions.srt")
    generate_srt(audio_segments, config, srt_path)

    # ── Step 6: Assemble Video ────────────────────────────────────────
    if dry_run:
        print("\n" + "=" * 60)
        print("STEP 6: SKIPPED (dry run — no audio files to assemble)")
        print("=" * 60)
        print(f"\nDry run complete. Assets in: {output_dir}/")
        print(f"  - segments.json: parsed article structure")
        print(f"  - qr_codes/: QR code images for {len(qr_map)} citations")
        print(f"  - frames/: {len(visual_frames)} visual frames")
        print(f"  - captions.srt: subtitle file")
        print(f"\nTo generate the full video, run without --dry-run:")
        print(f"  ELEVENLABS_API_KEY=<key> python pipeline.py {config.article_url}")
    else:
        print("\n" + "=" * 60)
        print("STEP 6: Assembling video")
        print("=" * 60)
        final_path = assemble_video(
            visual_frames, audio_segments, srt_path, config, output_dir
        )
        elapsed = time.time() - start_time
        print(f"\n{'=' * 60}")
        print(f"DONE! Video: {final_path}")
        print(f"Duration: {total_duration:.0f}s ({total_duration/60:.1f} min)")
        print(f"Pipeline took: {elapsed:.0f}s")
        print(f"{'=' * 60}")

    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Convert an HTML article into a narrated video"
    )
    parser.add_argument("url", help="URL of the HTML article (or path to local HTML file)")
    parser.add_argument("--segments-json", default="",
                        help="Path to pre-parsed segments JSON (skips HTML fetch)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Estimate durations without calling TTS API")
    parser.add_argument("--output-dir", default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--voice-id", default=None,
                        help="ElevenLabs voice ID")
    parser.add_argument("--width", type=int, default=1920,
                        help="Video width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080,
                        help="Video height (default: 1080)")
    args = parser.parse_args()

    config = PipelineConfig(
        article_url=args.url,
        output_dir=args.output_dir,
        video_width=args.width,
        video_height=args.height,
    )

    if args.voice_id:
        config.elevenlabs_voice_id = args.voice_id

    if not args.dry_run and not config.elevenlabs_api_key:
        print("ERROR: ELEVENLABS_API_KEY environment variable not set.")
        print("Set it or use --dry-run to test without TTS.")
        sys.exit(1)

    run_pipeline(config, dry_run=args.dry_run, segments_json=args.segments_json)


if __name__ == "__main__":
    main()
