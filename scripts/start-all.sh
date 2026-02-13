#!/usr/bin/env bash
# Start LSMTree server, canary, and Prometheus+Grafana in one command.
# Usage: ./scripts/start-all.sh (from repo root)
#   CANARY_INTERVAL=0.01 ./scripts/start-all.sh   # 100 probes/s (default: 5)

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LSMTREE="${LSMTREE_PATH:-$(dirname "$ROOT")/LSMTree}"
MONITORING="${LSMTREE_MONITORING_PATH:-$(dirname "$ROOT")/LSMTree-monitoring}"
CANARY_INTERVAL="${CANARY_INTERVAL:-5}"

echo "Starting LSMTree server (metrics at /metrics)..."
(cd "$LSMTREE" && python3 -m src.server --dir ./data --port 8000) &
sleep 2

echo "Starting canary (interval=${CANARY_INTERVAL}s)..."
(cd "$ROOT" && python3 -m canary --url http://localhost:8000 --metrics-port 9091 --interval "$CANARY_INTERVAL") &
sleep 2

echo "Starting Prometheus + Grafana..."
if command -v docker &>/dev/null; then
  (cd "$MONITORING" && docker compose up -d)
else
  (cd "$MONITORING" && ./run-local.sh)
fi

echo ""
echo "All running. Grafana: http://localhost:3000 (admin/admin)"
echo "Dashboards: LSMTree Canary, LSMTree"
echo "Stop: kill background jobs; docker compose -f $MONITORING/docker-compose.yml down"
