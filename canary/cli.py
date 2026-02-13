"""CLI and main loop: argparse, probe loop, metrics writing."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from .metrics_server import start_metrics_server
from .probe import run_probe


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    ap = argparse.ArgumentParser(
        description="Canary: exercise LSMTree server and emit liveness metrics"
    )
    ap.add_argument(
        "--url",
        default=os.environ.get("LSMTREE_URL", ""),
        help="LSMTree server URL (e.g. http://localhost:8000). Required, or set LSMTREE_URL.",
    )
    ap.add_argument("--dir", default="", help="Directory for metrics file (default: current dir)")
    ap.add_argument("--interval", type=float, default=10.0, help="Seconds between probes")
    ap.add_argument(
        "--metric-file",
        default="",
        help="Write metrics JSON here (default: <dir>/canary.json)",
    )
    ap.add_argument(
        "--max-failures",
        type=int,
        default=0,
        help="Exit after N consecutive failures (0 = never)",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log each probe step and request/response details",
    )
    ap.add_argument(
        "--metrics-port",
        type=int,
        default=0,
        help="Expose Prometheus metrics at /metrics on this port (0=disabled)",
    )
    return ap.parse_args(argv)


def build_metrics(
    ok: bool,
    latency_ms: float,
    total_checks: int,
    total_failures: int,
    consecutive_failures: int,
) -> dict:
    """Build the metrics dict written to JSON."""
    return {
        "last_check_ts": int(time.time() * 1000),
        "last_ok": ok,
        "last_latency_ms": latency_ms,
        "total_checks": total_checks,
        "total_failures": total_failures,
        "consecutive_failures": consecutive_failures,
    }


def write_metrics(metrics: dict, path: str) -> None:
    """Write metrics JSON to path. Logs to stderr on failure."""
    try:
        with open(path, "w") as f:
            json.dump(metrics, f, separators=(",", ":"))
    except OSError as e:
        print(f"canary: failed to write metrics: {e}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, run probe loop against LSMTree server."""
    args = parse_args(argv)

    if not args.url.strip():
        raise SystemExit("Set --url or LSMTREE_URL to the LSMTree server (e.g. http://localhost:8000).")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    data_dir = os.path.abspath(args.dir or ".")
    metric_file = args.metric_file or os.path.join(data_dir, "canary.json")
    os.makedirs(os.path.dirname(metric_file) or ".", exist_ok=True)

    metrics: dict = {}
    if args.metrics_port:
        start_metrics_server(args.metrics_port, metrics)
        print(f"Prometheus metrics at http://127.0.0.1:{args.metrics_port}/metrics", file=sys.stderr)

    total_checks = 0
    total_failures = 0
    consecutive_failures = 0

    while True:
        if args.verbose:
            logging.getLogger("canary.probe").info(
                "canary: starting probe (total_checks will be %d)", total_checks + 1
            )
        ok, latency_s, key_repr, value_repr, error_reason = run_probe(args.url.strip())
        total_checks += 1
        latency_ms = round(latency_s * 1000, 2)
        if not ok:
            total_failures += 1
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        metrics_dict = build_metrics(
            ok, latency_ms, total_checks, total_failures, consecutive_failures
        )
        write_metrics(metrics_dict, metric_file)
        metrics.update(metrics_dict)

        status = "OK" if ok else "FAIL"
        if ok:
            print(
                f"canary {status} key={key_repr} value={value_repr} latency_ms={latency_ms} checks={total_checks} failures={total_failures}"
            )
        else:
            err = f" error={error_reason}" if error_reason else ""
            print(
                f"canary {status} key={key_repr} value={value_repr}{err} latency_ms={latency_ms} checks={total_checks} failures={total_failures}"
            )

        if args.max_failures and consecutive_failures >= args.max_failures:
            print(
                f"canary: exiting after {consecutive_failures} consecutive failures",
                file=sys.stderr,
            )
            return 1

        time.sleep(args.interval)
