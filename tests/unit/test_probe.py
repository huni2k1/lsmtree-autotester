import logging
import unittest

from canary.probe import CANARY_KEY, run_probe


class TestProbeConstants(unittest.TestCase):
    def test_canary_key_is_bytes(self) -> None:
        self.assertEqual(CANARY_KEY, b"__canary__")


class TestRunProbe(unittest.TestCase):
    """Probe tests that call run_probe; silence logger to avoid traceback spam."""

    def setUp(self) -> None:
        self._probe_log = logging.getLogger("canary.probe")
        self._saved_level = self._probe_log.level
        self._probe_log.setLevel(logging.CRITICAL)

    def tearDown(self) -> None:
        self._probe_log.setLevel(self._saved_level)

    def test_returns_false_and_latency_when_server_unreachable(self) -> None:
        # No server on port 9; run_probe fails and returns (False, latency, key, value, error)
        ok, latency, key_repr, value_repr, error_reason = run_probe("http://127.0.0.1:9")
        self.assertFalse(ok)
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0)
        self.assertIsInstance(key_repr, str)
        self.assertIsInstance(value_repr, str)
        self.assertIsInstance(error_reason, str)

    def test_returns_tuple_of_five_elements(self) -> None:
        ok, latency, key_repr, value_repr, error_reason = run_probe("http://127.0.0.1:9")
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(latency, float)
        self.assertIsInstance(key_repr, str)
        self.assertIsInstance(value_repr, str)
        self.assertIsInstance(error_reason, (str, type(None)))
