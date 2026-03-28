#!/usr/bin/env python3
"""
Article-to-Video Pipeline

Converts an HTML article into a narrated video with:
- Text-to-speech narration (ElevenLabs)
- Synchronized captions (SRT burned in)
- QR codes for citation URLs
- User-specified diagrams on a separate visual track
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
from diagram_specs import (
    parse_diagram_specs_text,
    load_diagram_specs_text,
    resolve_diagram_specs,
    resolved_specs_to_json,
)
from parse_article import fetch_html, parse_article, get_all_citation_urls, segments_from_json, segments_to_json
from generate_qr import generate_all_qr_codes
from generate_visuals import generate_frames_for_segments, generate_diagram_track_frames
from generate_audio import generate_all_audio
from generate_captions import generate_srt
from assemble_video import assemble_video


def run_pipeline(
    config: PipelineConfig,
    dry_run: bool = False,
    segments_json: str = "",
    diagram_specs_text: str = "",
    diagram_specs_file: str = "",
    video_modes: list[str] | None = None,
):
    """
    Run the full article-to-video pipeline.

    Args:
        config: Pipeline configuration
        dry_run: If True, estimate audio durations without calling TTS API
        segments_json: Path to pre-parsed segments JSON (skips HTML fetch/parse)
        diagram_specs_text: Raw multiline text with one diagram rule per line
        diagram_specs_file: Optional file path containing diagram rules
        video_modes: Requested output video modes (text, diagrams, combined)
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

    if diagram_specs_file:
        diagram_specs_text = load_diagram_specs_text(diagram_specs_file)
    diagram_specs = parse_diagram_specs_text(diagram_specs_text) if diagram_specs_text.strip() else []
    resolved_diagrams = resolve_diagram_specs(diagram_specs, segments) if diagram_specs else []
    with open(os.path.join(output_dir, "diagram_specs.txt"), "w", encoding="utf-8") as f:
        f.write(diagram_specs_text or "")
    with open(os.path.join(output_dir, "diagram_specs.json"), "w", encoding="utf-8") as f:
        f.write(resolved_specs_to_json(resolved_diagrams))
    print(f"  Resolved {len(resolved_diagrams)} user-specified diagrams")

    # ── Step 2: Generate QR Codes ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Generating QR codes")
    print("=" * 60)
    all_urls = get_all_citation_urls(segments)
    for diagram in resolved_diagrams:
        if diagram.image_url not in all_urls:
            all_urls.append(diagram.image_url)
    print(f"  {len(all_urls)} unique citation URLs")
    qr_dir = os.path.join(output_dir, "qr_codes")
    qr_map = generate_all_qr_codes(all_urls, qr_dir, size=config.qr_size)
    print(f"  Generated {len(qr_map)} QR code images")

    # ── Step 3: Generate Visual Frames ────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Generating visual frames")
    print("=" * 60)
    text_frames_dir = os.path.join(output_dir, "frames", "text")
    visual_frames = generate_frames_for_segments(segments, qr_map, config, text_frames_dir)
    diagram_frames_dir = os.path.join(output_dir, "frames", "diagrams")
    diagram_frames = generate_diagram_track_frames(resolved_diagrams, qr_map, config, diagram_frames_dir)
    with open(os.path.join(output_dir, "frames.json"), "w", encoding="utf-8") as f:
        json.dump([frame.__dict__ for frame in visual_frames], f, indent=2)
    with open(os.path.join(output_dir, "diagram_frames.json"), "w", encoding="utf-8") as f:
        json.dump([frame.__dict__ for frame in diagram_frames], f, indent=2)
    print(f"  Generated {len(visual_frames)} text-track frames")
    print(f"  Generated {len(diagram_frames)} diagram-track frames")

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
        print(f"  - qr_codes/: QR code images for {len(qr_map)} URLs")
        print(f"  - frames/text/: {len(visual_frames)} text-track frames")
        print(f"  - frames/diagrams/: {len(diagram_frames)} diagram-track frames")
        print(f"  - captions.srt: subtitle file")
        print(f"\nTo generate the full video, run without --dry-run:")
        print(f"  ELEVENLABS_API_KEY=<key> python pipeline.py {config.article_url}")
    else:
        print("\n" + "=" * 60)
        print("STEP 6: Assembling video")
        print("=" * 60)
        final_path, _sync_report = assemble_video(
            visual_frames, audio_segments, srt_path, config, output_dir,
            diagram_frames=diagram_frames,
            video_modes=video_modes,
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
    parser.add_argument("--diagram-specs-file", default="",
                        help="Path to text file with diagram rules: <url> >> <start phrase> >> <stop phrase>")
    parser.add_argument("--diagram-specs-text", default="",
                        help="Raw multiline diagram rule text")
    parser.add_argument("--video-modes", default="text,diagrams,combined",
                        help="Comma-separated output modes: text,diagrams,combined")
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

    video_modes = [mode.strip() for mode in args.video_modes.split(",") if mode.strip()]
    run_pipeline(
        config,
        dry_run=args.dry_run,
        segments_json=args.segments_json,
        diagram_specs_text=args.diagram_specs_text,
        diagram_specs_file=args.diagram_specs_file,
        video_modes=video_modes,
    )


if __name__ == "__main__":
    main()
