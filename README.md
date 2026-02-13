# LSMTree Canary

Small canary that periodically sends put+get requests to an [LSMTree](https://github.com/your-org/LSMTree) HTTP server and writes liveness metrics to a JSON file.

## Requirements

- Python 3.x
- An **LSMTree HTTP server** running (start it from the LSMTree repo with `python3 -m src.server`).

## Project layout

```
LSMTree-canary/
  canary/              # main package
    __init__.py
    __main__.py        # python -m canary
    cli.py             # argparse, probe loop, metrics writing
    probe.py           # HTTP put+get probe
  scripts/
    start-all.sh       # start LSMTree + canary + monitoring
  tests/
    unit/              # unit tests (probe, cli)
  README.md
```

## Build

From the repo root (with a venv and `pip install -r requirements-dev.txt`):

```bash
python3 -m build
```

This creates `dist/` with a source tarball and a wheel. Install locally with `pip install dist/*.whl`; then you can run `canary` from anywhere.

## Run

1. **Start the LSMTree server** (in the LSMTree repo):

   ```bash
   cd /path/to/LSMTree
   python3 -m src.server --dir ./data --port 8000
   ```

2. **Start the canary** (in this repo):

   ```bash
   cd /path/to/LSMTree-canary
   python3 -m canary --url http://localhost:8000 --interval 5
   ```

Or set the URL via environment:

```bash
export LSMTREE_URL=http://localhost:8000
python3 -m canary
```

Metrics are written to `./canary.json` by default (use `--dir` or `--metric-file` to change).

### Options

| Option | Default | Description |
|--------|--------|-------------|
| `--url` | `$LSMTREE_URL` | LSMTree server URL (e.g. `http://localhost:8000`). Required. |
| `--dir` | current dir | Directory for metrics file |
| `--interval` | 10 | Seconds between probes |
| `--metric-file` | `<dir>/canary.json` | Where to write metrics JSON |
| `--max-failures` | 0 | Exit after this many consecutive failures (0 = run forever) |
| `-v`, `--verbose` | false | Log each probe step and request/response (key, value written/read) |
| `--metrics-port` | 0 | Expose Prometheus metrics at `/metrics` on this port (0=disabled) |

### Metrics file

JSON written on each probe, e.g.:

- `last_ok` — last probe succeeded
- `last_latency_ms` — last probe latency (ms)
- `total_checks` / `total_failures` / `consecutive_failures`

Use this file (or the process exit code with `--max-failures`) to confirm the store is alive.

## Monitoring (Prometheus + Grafana)

Monitoring is in the **LSMTree-monitoring** package (sibling repo). It scrapes both:
- **LSMTree-canary** (port 9091) — probe status, latency, availability
- **LSMTree** (port 8000 `/metrics`) — puts, gets, memtable, L0/L1 tables

See `LSMTree-monitoring/README.md` for details.

**Quick start:**

1. Start LSMTree (exposes `/metrics` on port 8000)
2. Start canary with `--metrics-port 9091`
3. Run monitoring: `cd LSMTree-monitoring && docker compose up -d` (or `./run-local.sh` without Docker)

**One-liner (start everything):**

```bash
cd /Users/ninhvan/Coding/LSMTree-canary
./scripts/start-all.sh
```

Or with explicit LSMTree path: `LSMTREE_PATH=/path/to/LSMTree ./scripts/start-all.sh`

## Tests

From the repo root:

```bash
python3 -m unittest discover -s tests -v
```

Unit tests cover probe behavior (unreachable server) and CLI helpers (argparse, metrics building, JSON writing). They do not require the LSMTree repo or a running server.

### Coverage

Use a virtual environment so `pip install` works (Homebrew Python is externally managed). Coverage is required to be at least 90% (build fails otherwise):

```bash
cd /path/to/LSMTree-canary
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python3 -m coverage run -m unittest discover -s tests -v
python3 -m coverage report
```

If coverage is below 90%, `coverage report` exits with a non-zero status. HTML report (open `htmlcov/index.html` in the repo root):

```bash
python3 -m coverage run -m unittest discover -s tests -v && python3 -m coverage html
```

## Workspace

This repo is intended to be used in a multi-root workspace together with LSMTree. Open the `.code-workspace` file from the LSMTree repo to have both in one window.
