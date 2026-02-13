"""Single put+get probe against an LSMTree HTTP server."""
from __future__ import annotations

import base64
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

CANARY_KEY_PREFIX = b"__canary__"
CANARY_KEY = CANARY_KEY_PREFIX  # backward compat; each probe uses a random key with this prefix
log = logging.getLogger(__name__)


def _random_canary_key() -> bytes:
    """Return a random key with canary prefix (e.g. __canary__a1b2c3d4)."""
    return CANARY_KEY_PREFIX + secrets.token_hex(8).encode("ascii")


def _repr_bytes(b: bytes) -> str:
    """Show bytes as plain string if ASCII, else b'...'."""
    try:
        return b.decode("ascii")
    except ValueError:
        return repr(b)


def run_probe(base_url: str) -> tuple[bool, float, str, str, str | None]:
    """
    Perform one put+get probe via HTTP against an LSMTree server.
    base_url should be e.g. http://localhost:8000 (no trailing slash).
    Uses PUT /put and GET /get with base64-encoded key/value.
    Returns (success, latency_seconds, key_repr, value_repr, error_reason or None).
    """
    start = time.perf_counter()
    key = _random_canary_key()
    ts_val = str(int(time.time() * 1000)).encode("ascii")
    key_repr = _repr_bytes(key)
    value_repr = _repr_bytes(ts_val)
    key_b64 = base64.b64encode(key).decode("ascii")
    value_b64 = base64.b64encode(ts_val).decode("ascii")

    try:
        log.info(
            "canary probe: put key=%s value=%s -> %s",
            _repr_bytes(key),
            _repr_bytes(ts_val),
            base_url,
        )
        put_body = json.dumps({"key": key_b64, "value": value_b64}).encode("utf-8")
        req = urllib.request.Request(
            base_url.rstrip("/") + "/put",
            data=put_body,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=30)

        log.info("canary probe: get key=%s", _repr_bytes(key))
        get_url = base_url.rstrip("/") + "/get?key=" + urllib.parse.quote(key_b64, safe="")
        with urllib.request.urlopen(get_url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out_b64 = data.get("value")
        if out_b64 is None:
            log.warning("canary probe: get returned no value")
            return False, time.perf_counter() - start, key_repr, value_repr, "get returned no value"
        out = base64.b64decode(out_b64.encode("ascii"))

        ok = out == ts_val
        if ok:
            log.info("canary probe: get returned value=%s (match)", _repr_bytes(out))
        else:
            log.warning(
                "canary probe: get returned value=%s (expected %s, mismatch)",
                _repr_bytes(out),
                _repr_bytes(ts_val),
            )
        return ok, time.perf_counter() - start, key_repr, value_repr, None if ok else "value mismatch"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        log.exception("canary probe: HTTP %s %s body=%s", e.code, e.reason, body)
        return False, time.perf_counter() - start, key_repr, value_repr, f"HTTP {e.code} {e.reason}"
    except Exception as e:
        log.exception("canary probe: failed: %s", e)
        return False, time.perf_counter() - start, key_repr, "?", str(e)
