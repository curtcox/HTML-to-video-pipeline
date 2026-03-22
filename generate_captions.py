"""
Generate SRT caption files from audio segment timing data.

Produces word-level or phrase-level captions synchronized with audio.
"""
import os
import re
from typing import List, Tuple
from dataclasses import dataclass

from generate_audio import AudioSegment
from config import PipelineConfig


def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def split_text_into_caption_chunks(
    text: str,
    words_per_line: int = 8,
    max_lines: int = 2,
) -> List[str]:
    """
    Split text into caption-sized chunks.

    Each chunk has at most max_lines lines of words_per_line words each.
    Tries to break at sentence boundaries when possible.
    """
    words = text.split()
    chunks = []
    current_chunk_words = []
    words_in_chunk = words_per_line * max_lines

    for word in words:
        current_chunk_words.append(word)

        # Check if we've hit the chunk size or a sentence boundary near the limit
        at_limit = len(current_chunk_words) >= words_in_chunk
        near_limit = len(current_chunk_words) >= words_in_chunk - 2
        at_sentence_end = word.endswith(('.', '!', '?', '."', '."'))

        if at_limit or (near_limit and at_sentence_end):
            # Format as multi-line caption
            lines = []
            for j in range(0, len(current_chunk_words), words_per_line):
                line = " ".join(current_chunk_words[j:j + words_per_line])
                lines.append(line)
            chunks.append("\n".join(lines))
            current_chunk_words = []

    # Remaining words
    if current_chunk_words:
        lines = []
        for j in range(0, len(current_chunk_words), words_per_line):
            line = " ".join(current_chunk_words[j:j + words_per_line])
            lines.append(line)
        chunks.append("\n".join(lines))

    return chunks


def generate_srt(
    audio_segments: List[AudioSegment],
    config: PipelineConfig,
    output_path: str,
) -> str:
    """
    Generate an SRT caption file from audio segment timing data.

    Distributes caption chunks proportionally across each segment's duration.
    """
    srt_entries = []
    entry_num = 1
    cumulative_time = 0.0

    for audio_seg in audio_segments:
        text = audio_seg.text
        duration = audio_seg.duration

        # Split into caption chunks
        chunks = split_text_into_caption_chunks(
            text,
            words_per_line=config.words_per_caption_line,
            max_lines=config.max_caption_lines,
        )

        if not chunks:
            cumulative_time += duration
            continue

        # Distribute duration proportionally across chunks by word count
        total_words = len(text.split())
        chunk_word_counts = [len(c.replace("\n", " ").split()) for c in chunks]

        current_time = cumulative_time
        for chunk, word_count in zip(chunks, chunk_word_counts):
            # Duration proportional to word count
            chunk_duration = duration * (word_count / max(total_words, 1))
            # Minimum display time of 1 second
            chunk_duration = max(chunk_duration, 1.0)

            start_time = current_time
            end_time = min(current_time + chunk_duration, cumulative_time + duration)

            srt_entries.append(
                f"{entry_num}\n"
                f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n"
                f"{chunk}\n"
            )
            entry_num += 1
            current_time = end_time

        cumulative_time += duration

        # Add pause after headings
        if audio_seg.segment_type == "heading":
            cumulative_time += config.pause_after_heading
        elif audio_seg.segment_type == "paragraph":
            cumulative_time += config.pause_between_paragraphs

    # Write SRT file
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))

    print(f"Generated {entry_num - 1} caption entries, total duration: {cumulative_time:.1f}s")
    return output_path


if __name__ == "__main__":
    # Test with dummy data
    test_segments = [
        AudioSegment(0, "test.mp3", 5.0, "Why AI Still Makes Things Up", "title"),
        AudioSegment(1, "test.mp3", 3.0, "The problem in plain terms", "heading"),
        AudioSegment(2, "test.mp3", 15.0,
                     "You've probably heard that AI chatbots hallucinate — they generate "
                     "statements that sound authoritative but turn out to be partially or "
                     "entirely false.", "paragraph"),
    ]
    config = PipelineConfig()
    generate_srt(test_segments, config, "output/test_captions.srt")
