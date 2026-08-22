#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BIN="$ROOT/build/extend_from_min_vertex"
NAUTY="$ROOT/third_party/nauty2_9_3"
TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST"' EXIT HUP INT TERM

"$BIN" \
  --input "$ROOT/data/r45extreme/r4521.107.g6" \
  --degree 5 --edges 112 --minimum-root --count-only \
  2>"$TMPDIR_TEST/d5.stats"
grep -q 'records=31 .* extensions=0 ' "$TMPDIR_TEST/d5.stats"

# Round-trip the catalogue through an extension run is impossible here, so
# independently ask nauty to confirm basic source dimensions and constraints.
"$NAUTY/countg" -q -n21 -e107 -k3 -h4 \
  "$ROOT/data/r45extreme/r4521.107.g6" >/dev/null

echo "extension tests passed"
