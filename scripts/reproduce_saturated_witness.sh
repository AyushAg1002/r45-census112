#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
cd "$PROJECT_ROOT"
NAUTY_DIR="third_party/nauty2_9_3"
CNF="data/r4522.112.saturated.cnf"
RAW="data/r4522.112.saturated.witness.g6"
CANONICAL="data/r4522.112.saturated.witness.canonical.g6"
TRACES="data/r4522.112.saturated.witness.traces.g6"
TRACES_RECANON="data/r4522.112.saturated.witness.traces.recanon.g6"

"$PYTHON_BIN" "src/saturated_cnf.py" \
  --cnf "$CNF" \
  --manifest "results/saturated_witness.json" \
  --solve --solver kissat404 --witness "$RAW"

test "$("$PYTHON_BIN" -c 'import json; print(json.load(open("results/saturated_witness.json"))["status"])')" = "SAT"
test "$(shasum -a 256 "$RAW" | awk '{print $1}')" = \
  "aafad0f023aeed590eeb5c413ce20d5e4535f79ca13d5c22d919110010fecdbd"

test "$(shasum -a 256 "$CNF" | awk '{print $1}')" = \
  "e65db47cc9bc70924b6ea7550cc93d8b8370bffc32b16c4275ca7d5b9d70297f"

"$NAUTY_DIR/shortg" -q "$RAW" "$CANONICAL"
"$NAUTY_DIR/shortg" -t -q "$RAW" "$TRACES"
"$NAUTY_DIR/shortg" -q "$TRACES" "$TRACES_RECANON"
cmp "$CANONICAL" "$TRACES_RECANON"
test "$(shasum -a 256 "$CANONICAL" | awk '{print $1}')" = \
  "9f94ad40db08993931c1b798b16e2601afbea7530f2122a0ff6b08a45e017ca4"

python3 "src/saturated_cnf.py" \
  --audit-witness "$RAW" \
  --manifest "results/saturated_witness_audit.json"
python3 "src/saturated_cnf.py" \
  --audit-witness "$CANONICAL" \
  --manifest "results/saturated_witness_canonical_audit.json"
python3 "src/prepare_sms_coverage.py" audit \
  --catalogue "$CANONICAL" \
  --manifest "results/saturated_witness_bitparallel_audit.json"

echo "saturated witness reproduced and audited"
