import unittest

from assemble_video import _plan_clip_sequence, _scroll_overlay_position_expr
from config import PipelineConfig


class ScrollMotionTests(unittest.TestCase):
    def test_vertical_scroll_expression_is_linear(self):
        x_expr, y_expr = _scroll_overlay_position_expr("vertical", 30)
        self.assertEqual(x_expr, "0")
        self.assertEqual(y_expr, "H-((H+h)*n/29)")

    def test_horizontal_scroll_expression_is_linear(self):
        x_expr, y_expr = _scroll_overlay_position_expr("horizontal", 30)
        self.assertEqual(x_expr, "W-((W+w)*n/29)")
        self.assertEqual(y_expr, "0")

    def test_scroll_expression_handles_single_frame(self):
        x_expr, y_expr = _scroll_overlay_position_expr("vertical", 1)
        self.assertEqual(x_expr, "0")
        self.assertEqual(y_expr, "H-((H+h)*n/1)")

    def test_no_transitions_when_disabled(self):
        config = PipelineConfig(fps=30)
        sequence = [
            {"file": "/tmp/a.png", "duration": 2.0},
            {"file": "/tmp/b.png", "duration": 2.0},
        ]
        plan = _plan_clip_sequence(sequence, config, use_transitions=False)
        self.assertEqual(len(plan), 2)
        self.assertTrue(all(entry.kind == "hold" for entry in plan))


if __name__ == "__main__":
    unittest.main()
