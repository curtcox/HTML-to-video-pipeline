"""
Parse and resolve user-provided diagram display specifications.

Each non-empty line must follow:
    image_url >> start phrase >> stop phrase
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import List, Tuple

from parse_article import Segment

DELIMITER = ">>"
TIME_SELECTOR_RE = re.compile(r"^(\d+):([0-5]\d):([0-9]\d)$")


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
    start_segment_index: int | None = None
    stop_segment_index: int | None = None
    start_time_seconds: float | None = None
    stop_time_seconds: float | None = None


def _normalize_text(text: str) -> str:
    """Lowercase and normalize punctuation/whitespace for fuzzy matching."""
    text = text.replace("…", "...").lower()
    text = re.sub(r"[^a-z0-9.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    allow_overlaps: bool = False,
) -> List[ResolvedDiagramSpec]:
    """
    Resolve rules onto segment indexes and/or explicit timeline times.

    Selector behavior:
    - If selector is exactly mm:ss:hh, treat it as a time.
    - Otherwise, treat it as a text fragment to match.
    """
    resolved: List[ResolvedDiagramSpec] = []
    normalized_segment_text = [_normalize_text(seg.text) for seg in segments]

    for spec in specs:
        start_time = _parse_time_selector(spec.start_phrase)
        stop_time = _parse_time_selector(spec.stop_phrase)

        start_idx: int | None = None
        stop_idx: int | None = None

        if start_time is None:
            start_idx = _find_phrase_index(normalized_segment_text, spec.start_phrase, start_from=0)
            if start_idx is None:
                raise ValueError(
                    f"Diagram spec line {spec.line_number}: "
                    f"start phrase not found: {spec.start_phrase!r}"
                )

        if stop_time is None:
            stop_search_from = start_idx if start_idx is not None else 0
            stop_idx = _find_phrase_index(normalized_segment_text, spec.stop_phrase, start_from=stop_search_from)
            if stop_idx is None:
                raise ValueError(
                    f"Diagram spec line {spec.line_number}: "
                    f"stop phrase not found after start phrase: {spec.stop_phrase!r}"
                )

        if start_time is not None and stop_time is not None and stop_time < start_time:
            raise ValueError(
                f"Diagram spec line {spec.line_number}: stop time {spec.stop_phrase!r} "
                f"is before start time {spec.start_phrase!r}"
            )

        resolved.append(
            ResolvedDiagramSpec(
                image_url=spec.image_url,
                start_phrase=spec.start_phrase,
                stop_phrase=spec.stop_phrase,
                line_number=spec.line_number,
                start_segment_index=start_idx,
                stop_segment_index=stop_idx,
                start_time_seconds=start_time,
                stop_time_seconds=stop_time,
            )
        )

    if not allow_overlaps:
        _raise_if_overlapping_resolved_diagrams(resolved)
    return resolved


def _raise_if_overlapping_resolved_diagrams(resolved_specs: List[ResolvedDiagramSpec]) -> None:
    """Fail fast when diagram display intervals overlap."""
    overlaps = _find_overlapping_pairs(resolved_specs)
    if not overlaps:
        return
    raise ValueError(overlap_error_message(overlaps))


def overlap_error_message(
    overlaps: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]],
    manual_required_pairs: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]] | None = None,
) -> str:
    """Render a detailed overlap error with line/range/url context."""
    if not overlaps:
        return ""

    details = []
    for left, right in overlaps:
        details.append(
            (
                f"line {left.line_number} "
                f"[{_range_label(left)}] "
                f"url={left.image_url!r} overlaps line {right.line_number} "
                f"[{_range_label(right)}] "
                f"url={right.image_url!r}"
            )
        )

    message = (
        "Overlapping diagram intervals detected. "
        "Please adjust start/stop phrase ranges so they do not overlap. "
        "Details: " + "; ".join(details)
    )
    if manual_required_pairs:
        manual_details = []
        for left, right in manual_required_pairs:
            manual_details.append(
                (
                    f"line {left.line_number} and line {right.line_number} share identical "
                    f"start/stop ranges [{_range_label(left)}]"
                )
            )
        message += (
            ". Manual changes required for identical start/stop ranges: "
            + "; ".join(manual_details)
        )
    return message


def find_overlapping_resolved_diagrams(
    resolved_specs: List[ResolvedDiagramSpec],
) -> List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]]:
    """Public overlap detector for parse-stage validation/auto-fix prompts."""
    return _find_overlapping_pairs(resolved_specs)


def auto_adjust_overlapping_resolved_diagrams(
    resolved_specs: List[ResolvedDiagramSpec],
) -> tuple[
    List[ResolvedDiagramSpec],
    List[dict],
    List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]],
]:
    """
    Shrink overlapping ranges by moving earlier stop and later start inward.

    Returns:
      - adjusted resolved specs (same order as input)
      - adjustment records for UI/logging
      - remaining overlaps that could not be auto-fixed
    """
    adjusted = [ResolvedDiagramSpec(**asdict(spec)) for spec in resolved_specs]
    adjustments: List[dict] = []
    manual_required: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]] = []

    for domain in ("segment", "time"):
        ordered = sorted(
            [spec for spec in adjusted if _interval_domain(spec) == domain],
            key=lambda spec: (
                _interval_start_units(spec, domain),
                _interval_end_units(spec, domain),
                spec.line_number,
            ),
        )
        for i in range(1, len(ordered)):
            left = ordered[i - 1]
            right = ordered[i]
            left_start = _interval_start_units(left, domain)
            left_end = _interval_end_units(left, domain)
            right_start = _interval_start_units(right, domain)
            right_end = _interval_end_units(right, domain)
            if not _intervals_overlap(domain, left_start, left_end, right_start, right_end):
                continue

            if left_start == right_start and left_end == right_end:
                manual_required.append((left, right))
                continue

            overlap_len = _overlap_units(domain, left_end, right_start)
            left_room = left_end - left_start
            right_room = right_end - right_start

            move_left = min(left_room, (overlap_len + 1) // 2)
            move_right = min(right_room, overlap_len - move_left)
            remaining = overlap_len - (move_left + move_right)
            if remaining > 0:
                extra_left = min(left_room - move_left, remaining)
                move_left += extra_left
                remaining -= extra_left
            if remaining > 0:
                extra_right = min(right_room - move_right, remaining)
                move_right += extra_right
                remaining -= extra_right
            if remaining > 0:
                manual_required.append((left, right))
                continue

            _set_interval_end_units(left, domain, left_end - move_left)
            _set_interval_start_units(right, domain, right_start + move_right)

            adjustments.append(
                {
                    "domain": domain,
                    "left_line": left.line_number,
                    "right_line": right.line_number,
                    "left_stop_before": _format_units(domain, left_end),
                    "left_stop_after": _format_units(domain, _interval_end_units(left, domain)),
                    "right_start_before": _format_units(domain, right_start),
                    "right_start_after": _format_units(domain, _interval_start_units(right, domain)),
                }
            )

    remaining_overlaps = _find_overlapping_pairs(adjusted)
    manual_required_unique = _dedupe_overlap_pairs(manual_required + remaining_overlaps)
    return adjusted, adjustments, manual_required_unique


def _find_overlapping_pairs(
    resolved_specs: List[ResolvedDiagramSpec],
) -> List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]]:
    """Return all overlapping pairs by segment index (inclusive ranges)."""
    overlaps: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]] = []
    for domain in ("segment", "time"):
        ordered = sorted(
            [spec for spec in resolved_specs if _interval_domain(spec) == domain],
            key=lambda spec: (
                _interval_start_units(spec, domain),
                _interval_end_units(spec, domain),
                spec.line_number,
            ),
        )
        for i, left in enumerate(ordered):
            left_start = _interval_start_units(left, domain)
            left_end = _interval_end_units(left, domain)
            for right in ordered[i + 1:]:
                right_start = _interval_start_units(right, domain)
                right_end = _interval_end_units(right, domain)
                if not _intervals_can_still_overlap(domain, left_end, right_start):
                    break
                if _intervals_overlap(domain, left_start, left_end, right_start, right_end):
                    overlaps.append((left, right))
    return overlaps


def _dedupe_overlap_pairs(
    pairs: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]],
) -> List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]]:
    deduped: List[Tuple[ResolvedDiagramSpec, ResolvedDiagramSpec]] = []
    seen = set()
    for left, right in pairs:
        key = (left.line_number, right.line_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((left, right))
    return deduped


def _parse_time_selector(value: str) -> float | None:
    value = value.strip()
    match = TIME_SELECTOR_RE.fullmatch(value)
    if not match:
        return None
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    hundredths = int(match.group(3))
    return minutes * 60 + seconds + (hundredths / 100.0)


def _format_seconds_mm_ss_hh(seconds: float) -> str:
    total_hundredths = int(round(seconds * 100))
    minutes = total_hundredths // 6000
    remainder = total_hundredths % 6000
    secs = remainder // 100
    hundredths = remainder % 100
    return f"{minutes:02d}:{secs:02d}:{hundredths:02d}"


def _range_label(spec: ResolvedDiagramSpec) -> str:
    domain = _interval_domain(spec)
    if domain == "segment":
        return f"segments {spec.start_segment_index}-{spec.stop_segment_index}"
    if domain == "time":
        return (
            f"time {_format_seconds_mm_ss_hh(spec.start_time_seconds or 0.0)}"
            f"-{_format_seconds_mm_ss_hh(spec.stop_time_seconds or 0.0)}"
        )
    return "mixed selectors (time+text)"


def _interval_domain(spec: ResolvedDiagramSpec) -> str | None:
    if spec.start_segment_index is not None and spec.stop_segment_index is not None:
        return "segment"
    if spec.start_time_seconds is not None and spec.stop_time_seconds is not None:
        return "time"
    return None


def _interval_start_units(spec: ResolvedDiagramSpec, domain: str) -> int:
    if domain == "segment":
        return int(spec.start_segment_index or 0)
    return int(round((spec.start_time_seconds or 0.0) * 100))


def _interval_end_units(spec: ResolvedDiagramSpec, domain: str) -> int:
    if domain == "segment":
        return int(spec.stop_segment_index or 0)
    return int(round((spec.stop_time_seconds or 0.0) * 100))


def _set_interval_start_units(spec: ResolvedDiagramSpec, domain: str, value: int) -> None:
    if domain == "segment":
        spec.start_segment_index = value
    else:
        spec.start_time_seconds = value / 100.0


def _set_interval_end_units(spec: ResolvedDiagramSpec, domain: str, value: int) -> None:
    if domain == "segment":
        spec.stop_segment_index = value
    else:
        spec.stop_time_seconds = value / 100.0


def _intervals_overlap(
    domain: str,
    left_start: int,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    if domain == "segment":
        return right_start <= left_end
    return right_start < left_end


def _intervals_can_still_overlap(domain: str, left_end: int, right_start: int) -> bool:
    if domain == "segment":
        return right_start <= left_end
    return right_start < left_end


def _overlap_units(domain: str, left_end: int, right_start: int) -> int:
    if domain == "segment":
        return left_end - right_start + 1
    return left_end - right_start


def _format_units(domain: str, value: int) -> str:
    if domain == "segment":
        return str(value)
    return _format_seconds_mm_ss_hh(value / 100.0)


def _find_phrase_index(
    normalized_segments: List[str],
    phrase: str,
    start_from: int,
) -> int | None:
    normalized_phrase = _normalize_text(phrase)
    raw_phrase = phrase.replace("…", "...")
    parts = [_normalize_text(part) for part in raw_phrase.split("...")]
    parts = [part for part in parts if part]

    for idx in range(start_from, len(normalized_segments)):
        if _phrase_matches(normalized_segments[idx], normalized_phrase, parts):
            return idx
    return None


def _phrase_matches(
    normalized_segment: str,
    normalized_phrase: str,
    wildcard_parts: List[str],
) -> bool:
    if "..." not in normalized_phrase:
        return normalized_phrase in normalized_segment

    cursor = 0
    for part in wildcard_parts:
        found = normalized_segment.find(part, cursor)
        if found < 0:
            return False
        cursor = found + len(part)
    return True


def resolved_specs_to_json(resolved_specs: List[ResolvedDiagramSpec]) -> str:
    data = [asdict(spec) for spec in resolved_specs]
    return json.dumps(data, indent=2)


def resolved_specs_from_json(path: str) -> List[ResolvedDiagramSpec]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [ResolvedDiagramSpec(**item) for item in data]
