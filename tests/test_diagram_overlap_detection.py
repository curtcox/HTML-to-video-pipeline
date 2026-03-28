import unittest

from diagram_specs import (
    auto_adjust_overlapping_resolved_diagrams,
    find_overlapping_resolved_diagrams,
    parse_diagram_specs_text,
    resolve_diagram_specs,
)
from parse_article import Segment


class DiagramOverlapDetectionTests(unittest.TestCase):
    def test_resolve_rejects_overlapping_ranges(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha start"),
            Segment(segment_type="paragraph", text="beta middle"),
            Segment(segment_type="paragraph", text="charlie stop"),
            Segment(segment_type="paragraph", text="delta end"),
        ]
        specs = parse_diagram_specs_text(
            "\n".join(
                [
                    "https://example.com/one.png >> alpha >> charlie",
                    "https://example.com/two.png >> beta >> delta",
                ]
            )
        )

        with self.assertRaises(ValueError) as ctx:
            resolve_diagram_specs(specs, segments)

        msg = str(ctx.exception)
        self.assertIn("Overlapping diagram intervals detected", msg)
        self.assertIn("line 1", msg)
        self.assertIn("line 2", msg)
        self.assertIn("segments 0-2", msg)
        self.assertIn("segments 1-3", msg)

    def test_resolve_allows_non_overlapping_ranges(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha start"),
            Segment(segment_type="paragraph", text="beta stop"),
            Segment(segment_type="paragraph", text="charlie start"),
            Segment(segment_type="paragraph", text="delta stop"),
        ]
        specs = parse_diagram_specs_text(
            "\n".join(
                [
                    "https://example.com/one.png >> alpha >> beta",
                    "https://example.com/two.png >> charlie >> delta",
                ]
            )
        )

        resolved = resolve_diagram_specs(specs, segments)
        self.assertEqual(len(resolved), 2)
        self.assertEqual((resolved[0].start_segment_index, resolved[0].stop_segment_index), (0, 1))
        self.assertEqual((resolved[1].start_segment_index, resolved[1].stop_segment_index), (2, 3))

    def test_auto_adjust_resolves_overlap_when_ranges_differ(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha"),
            Segment(segment_type="paragraph", text="beta"),
            Segment(segment_type="paragraph", text="gamma"),
            Segment(segment_type="paragraph", text="delta"),
        ]
        specs = parse_diagram_specs_text(
            "\n".join(
                [
                    "https://example.com/one.png >> alpha >> gamma",
                    "https://example.com/two.png >> beta >> delta",
                ]
            )
        )
        resolved = resolve_diagram_specs(specs, segments, allow_overlaps=True)
        overlaps = find_overlapping_resolved_diagrams(resolved)
        self.assertEqual(len(overlaps), 1)

        adjusted, adjustments, manual = auto_adjust_overlapping_resolved_diagrams(resolved)
        self.assertGreaterEqual(len(adjustments), 1)
        self.assertEqual(len(manual), 0)
        self.assertEqual(find_overlapping_resolved_diagrams(adjusted), [])

    def test_auto_adjust_flags_identical_ranges_for_manual_changes(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha"),
            Segment(segment_type="paragraph", text="beta"),
            Segment(segment_type="paragraph", text="gamma"),
        ]
        specs = parse_diagram_specs_text(
            "\n".join(
                [
                    "https://example.com/one.png >> alpha >> gamma",
                    "https://example.com/two.png >> alpha >> gamma",
                ]
            )
        )
        resolved = resolve_diagram_specs(specs, segments, allow_overlaps=True)
        adjusted, adjustments, manual = auto_adjust_overlapping_resolved_diagrams(resolved)
        self.assertEqual(len(adjustments), 0)
        self.assertGreaterEqual(len(manual), 1)
        self.assertEqual(find_overlapping_resolved_diagrams(adjusted), manual)

    def test_resolve_supports_time_only_selectors(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha"),
            Segment(segment_type="paragraph", text="beta"),
        ]
        specs = parse_diagram_specs_text(
            "https://example.com/timed.png >> 01:02:03 >> 01:04:05"
        )
        resolved = resolve_diagram_specs(specs, segments)
        self.assertEqual(len(resolved), 1)
        spec = resolved[0]
        self.assertIsNone(spec.start_segment_index)
        self.assertIsNone(spec.stop_segment_index)
        self.assertAlmostEqual(spec.start_time_seconds, 62.03, places=2)
        self.assertAlmostEqual(spec.stop_time_seconds, 64.05, places=2)

    def test_resolve_supports_mixed_time_and_text_selectors(self):
        segments = [
            Segment(segment_type="paragraph", text="alpha"),
            Segment(segment_type="paragraph", text="beta marker"),
            Segment(segment_type="paragraph", text="gamma"),
        ]
        specs = parse_diagram_specs_text(
            "https://example.com/mixed.png >> 00:00:50 >> beta marker"
        )
        resolved = resolve_diagram_specs(specs, segments)
        self.assertEqual(len(resolved), 1)
        spec = resolved[0]
        self.assertIsNone(spec.start_segment_index)
        self.assertEqual(spec.stop_segment_index, 1)
        self.assertAlmostEqual(spec.start_time_seconds, 0.5, places=2)
        self.assertIsNone(spec.stop_time_seconds)


if __name__ == "__main__":
    unittest.main()
