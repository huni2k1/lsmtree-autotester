import json
import os
import unittest

from canary.cli import build_metrics, parse_args, write_metrics


class TestParseArgs(unittest.TestCase):
    def test_url_from_flag(self) -> None:
        args = parse_args(["--url", "http://localhost:8000"])
        self.assertEqual(args.url, "http://localhost:8000")

    def test_default_interval(self) -> None:
        args = parse_args(["--url", "http://localhost:8000"])
        self.assertEqual(args.interval, 10.0)

    def test_interval_override(self) -> None:
        args = parse_args(["--url", "http://x", "--interval", "5"])
        self.assertEqual(args.interval, 5.0)

    def test_max_failures_default_zero(self) -> None:
        args = parse_args(["--url", "http://localhost:8000"])
        self.assertEqual(args.max_failures, 0)


class TestBuildMetrics(unittest.TestCase):
    def test_contains_expected_keys(self) -> None:
        m = build_metrics(True, 12.5, 1, 0, 0)
        self.assertIn("last_check_ts", m)
        self.assertIn("last_ok", m)
        self.assertIn("last_latency_ms", m)
        self.assertIn("total_checks", m)
        self.assertIn("total_failures", m)
        self.assertIn("consecutive_failures", m)

    def test_values_reflected(self) -> None:
        m = build_metrics(False, 99.0, 10, 3, 2)
        self.assertFalse(m["last_ok"])
        self.assertEqual(m["last_latency_ms"], 99.0)
        self.assertEqual(m["total_checks"], 10)
        self.assertEqual(m["total_failures"], 3)
        self.assertEqual(m["consecutive_failures"], 2)


class TestWriteMetrics(unittest.TestCase):
    def test_writes_valid_json(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            write_metrics({"last_ok": True, "x": 1}, path)
            with open(path) as f:
                data = json.load(f)
            self.assertTrue(data["last_ok"])
            self.assertEqual(data["x"], 1)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
