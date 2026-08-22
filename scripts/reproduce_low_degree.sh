#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
cd "$PROJECT_ROOT"
CPP_LOG="results/low_degree_direct_cpp.txt"

test "$(shasum -a 256 "data/r45extreme/r4521.107.g6" | awk '{print $1}')" = \
  "6ef8619d5d6be9efa15cb9a5ccb6b0da7304cfbfd57fff29bb0dec2e46f81bef"
test "$(shasum -a 256 "data/r45extreme/r4521.106.g6" | awk '{print $1}')" = \
  "2be4df6ba89b1c55743624fb6e8141741aef82b06a922aa0a069923942389593"

: > "$CPP_LOG"
"build/extend_from_min_vertex" \
  --input "data/r45extreme/r4521.107.g6" \
  --degree 5 --edges 112 --minimum-root --count-only 2>> "$CPP_LOG"
"build/extend_from_min_vertex" \
  --input "data/r45extreme/r4521.106.g6" \
  --degree 6 --edges 112 --minimum-root --count-only 2>> "$CPP_LOG"

grep -q 'records=31 subsets=630819 extensions=0' "$CPP_LOG"
grep -q 'records=10188 subsets=552841632 extensions=0 rejected_i4=552841189 rejected_triangle=443' "$CPP_LOG"

"$PYTHON_BIN" "verify_low_degree.py" \
  --catalogue-dir "data/r45extreme" \
  --bruteforce-prefix 10 \
  --output "results/low_degree_transversal.json"

echo "minimum-degree exclusions reproduced"
