"""Canary for LSMTree: periodic put/get probes and liveness metrics."""
from __future__ import annotations

from .cli import main, parse_args
from .probe import CANARY_KEY, run_probe

__all__ = [
    "main",
    "parse_args",
    "run_probe",
    "CANARY_KEY",
]
