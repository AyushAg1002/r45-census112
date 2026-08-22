#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
LOG="$PROJECT_ROOT/results/reproduction.log"

if {
  echo "started_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "python=$($PYTHON_BIN --version 2>&1)"
  "$PYTHON_BIN" -c 'import pysat; print("pysat=" + pysat.__version__)'
  make -C "$PROJECT_ROOT" build-nauty all
  make -C "$PROJECT_ROOT" test PYTHON="$PYTHON_BIN"
  make -C "$PROJECT_ROOT" reproduce-nonsaturated
  make -C "$PROJECT_ROOT" independent-deletion-crosscheck
  make -C "$PROJECT_ROOT" verify-low-degree PYTHON="$PYTHON_BIN"
  make -C "$PROJECT_ROOT" reproduce-saturated-witness PYTHON="$PYTHON_BIN"
  "$PYTHON_BIN" "$PROJECT_ROOT/scripts/finalize_reproduction_summary.py"
  echo "completed_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$LOG" 2>&1; then
  cat "$LOG"
else
  status=$?
  cat "$LOG"
  exit "$status"
fi
