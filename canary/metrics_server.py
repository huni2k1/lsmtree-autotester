"""Prometheus metrics HTTP server. Serves /metrics in exposition format."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


def _availability_line(metrics: dict[str, Any]) -> str:
    """Compute availability %: (checks - failures) / checks * 100 when checks > 0."""
    total = metrics.get("total_checks", 0) or 0
    fail = metrics.get("total_failures", 0) or 0
    if total == 0:
        return "canary_availability_pct 100"
    pct = round(100.0 * (total - fail) / total, 2)
    return f"canary_availability_pct {pct}"


def _prometheus_format(metrics: dict[str, Any]) -> str:
    """Convert metrics dict to Prometheus exposition format."""
    lines = [
        "# HELP canary_last_ok Whether the last probe succeeded (1=ok, 0=fail)",
        "# TYPE canary_last_ok gauge",
        f"canary_last_ok {1 if metrics.get('last_ok') else 0}",
        "",
        "# HELP canary_last_latency_ms Latency of last probe in milliseconds",
        "# TYPE canary_last_latency_ms gauge",
        f"canary_last_latency_ms {metrics.get('last_latency_ms', 0)}",
        "",
        "# HELP canary_total_checks Total number of probe checks",
        "# TYPE canary_total_checks gauge",
        f"canary_total_checks {metrics.get('total_checks', 0)}",
        "",
        "# HELP canary_total_failures Total number of failed probes",
        "# TYPE canary_total_failures gauge",
        f"canary_total_failures {metrics.get('total_failures', 0)}",
        "",
        "# HELP canary_consecutive_failures Consecutive failures count",
        "# TYPE canary_consecutive_failures gauge",
        f"canary_consecutive_failures {metrics.get('consecutive_failures', 0)}",
        "",
        "# HELP canary_availability_pct Availability percentage (100 * (checks - failures) / checks)",
        "# TYPE canary_availability_pct gauge",
        _availability_line(metrics),
        "",
        "# HELP canary_last_check_ts Timestamp of last check (ms since epoch)",
        "# TYPE canary_last_check_ts gauge",
        f"canary_last_check_ts {metrics.get('last_check_ts', 0)}",
        "",
    ]
    return "\n".join(lines)


class MetricsHandler(BaseHTTPRequestHandler):
    """Serve /metrics; 404 for other paths."""

    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        metrics = getattr(self.server, "metrics", {})
        body = _prometheus_format(metrics).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass  # Suppress request logging


def start_metrics_server(port: int, metrics: dict[str, Any]) -> HTTPServer:
    """Start a daemon thread serving Prometheus metrics at :port."""
    server = HTTPServer(("", port), MetricsHandler)
    server.metrics = metrics
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
