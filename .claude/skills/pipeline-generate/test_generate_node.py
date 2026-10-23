import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_node


class GenerateNodeMainTests(unittest.TestCase):
    def test_main_reports_selected_screen_size_after_merging(self):
        for width, height in ((1080, 1920), (1440, 2560)):
            with self.subTest(width=width, height=height), tempfile.TemporaryDirectory() as temp_dir:
                pipeline_path = Path(temp_dir) / "pipeline.json"
                argv = [
                    "generate_node.py",
                    "目标",
                    "TargetNode",
                    str(pipeline_path),
                    "--screen-width",
                    str(width),
                    "--screen-height",
                    str(height),
                ]
                output = io.StringIO()

                with (
                    patch.object(sys, "argv", argv),
                    patch.object(generate_node, "find_project_root", return_value=Path(temp_dir)),
                    patch.object(generate_node, "resolve_pipeline_path", return_value=pipeline_path),
                    patch.object(generate_node, "connect_device", return_value="controller"),
                    patch.object(
                        generate_node,
                        "find_target_box",
                        return_value=([10, 20, 30, 40], 0.95),
                    ),
                    patch.object(generate_node, "merge_into_pipeline", return_value=pipeline_path),
                    contextlib.redirect_stdout(output),
                ):
                    generate_node.main()

                self.assertIn(f"基准分辨率: {width}x{height}", output.getvalue())
                self.assertIn("[OK] 已写入:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
