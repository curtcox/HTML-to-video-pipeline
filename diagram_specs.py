"""
Parse and resolve user-provided diagram display specifications.

Each non-empty line must follow:
    image_url >> start phrase >> stop phrase
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import List

from parse_article import Segment

DELIMITER = ">>"


@dataclass
class DiagramSpec:
    """User-specified diagram placement rule."""
    image_url: str
    start_phrase: str
    stop_phrase: str
    line_number: int


@dataclass
class ResolvedDiagramSpec:
    """Diagram rule resolved onto segment boundaries."""
    image_url: str
    start_phrase: str
    stop_phrase: str
    line_number: int
    start_segment_index: int
    stop_segment_index: int


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def parse_diagram_specs_text(text: str) -> List[DiagramSpec]:
    """Parse user input where each line defines one diagram placement rule."""
    specs: List[DiagramSpec] = []
    if not text.strip():
        return specs

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(DELIMITER)]
        if len(parts) != 3 or any(not part for part in parts):
            raise ValueError(
                f"Invalid diagram spec at line {idx}. "
                f"Expected: image_url {DELIMITER} start phrase {DELIMITER} stop phrase"
            )

        specs.append(
            DiagramSpec(
                image_url=parts[0],
                start_phrase=parts[1],
                stop_phrase=parts[2],
                line_number=idx,
            )
        )

    return specs


def load_diagram_specs_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_diagram_specs(path: str) -> List[DiagramSpec]:
    return parse_diagram_specs_text(load_diagram_specs_text(path))


def resolve_diagram_specs(
    specs: List[DiagramSpec],
    segments: List[Segment],
) -> List[ResolvedDiagramSpec]:
    """
    Resolve phrase-based rules onto segment indexes.

    The start phrase is matched against any segment text.
    The stop phrase is matched at or after the start segment.
    """
    resolved: List[ResolvedDiagramSpec] = []
    normalized_segment_text = [_normalize_text(seg.text) for seg in segments]

    for spec in specs:
        start_key = _normalize_text(spec.start_phrase)
        stop_key = _normalize_text(spec.stop_phrase)
        start_idx = _find_phrase_index(normalized_segment_text, start_key, start_from=0)
        if start_idx is None:
            raise ValueError(
                f"Diagram spec line {spec.line_number}: "
                f"start phrase not found: {spec.start_phrase!r}"
            )

        stop_idx = _find_phrase_index(normalized_segment_text, stop_key, start_from=start_idx)
        if stop_idx is None:
            raise ValueError(
                f"Diagram spec line {spec.line_number}: "
                f"stop phrase not found after start phrase: {spec.stop_phrase!r}"
            )

        resolved.append(
            ResolvedDiagramSpec(
                image_url=spec.image_url,
                start_phrase=spec.start_phrase,
                stop_phrase=spec.stop_phrase,
                line_number=spec.line_number,
                start_segment_index=start_idx,
                stop_segment_index=stop_idx,
            )
        )

    return resolved


def _find_phrase_index(
    normalized_segments: List[str],
    normalized_phrase: str,
    start_from: int,
) -> int | None:
    for idx in range(start_from, len(normalized_segments)):
        if normalized_phrase in normalized_segments[idx]:
            return idx
    return None


def resolved_specs_to_json(resolved_specs: List[ResolvedDiagramSpec]) -> str:
    data = [asdict(spec) for spec in resolved_specs]
    return json.dumps(data, indent=2)


def resolved_specs_from_json(path: str) -> List[ResolvedDiagramSpec]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [ResolvedDiagramSpec(**item) for item in data]
