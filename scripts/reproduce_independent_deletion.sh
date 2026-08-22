#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

SOURCE="data/r45extreme/r4522.113.g6"
VALID="data/r4522.112.deletions.independent.valid.g6"
PRIMARY_VALID="data/r4522.112.deletions.valid.g6"
CANONICAL="data/r4522.112.nonsaturated.independent.g6"
REFERENCE="data/r4522.112.nonsaturated.g6"
MANIFEST="results/independent_deletion_filter.json"
FILTER="build/independent_delete_filter"
SHORTG="third_party/nauty2_9_3/shortg"

test "$(shasum -a 256 "$SOURCE" | awk '{print $1}')" = \
  "1e1a54b719dcdebb57581ee6f3cd4e1721e828680a72128010f1f888a4dda9db"

"$FILTER" \
  --input "$SOURCE" \
  --output "$VALID" \
  --manifest "$MANIFEST"

test "$(awk '/\"input_records\"/{gsub(/[^0-9]/, ""); print}' "$MANIFEST")" = \
  "30976"
test "$(awk '/\"all_edge_deletions\"/{gsub(/[^0-9]/, ""); print}' "$MANIFEST")" = \
  "3500288"
test "$(wc -l < "$VALID" | tr -d ' ')" = "887138"
test "$(shasum -a 256 "$VALID" | awk '{print $1}')" = \
  "0f35a09c6f6f6d91b5e115144809ab70aecb57a3bddd54e1c8053fff9ca70d28"
cmp "$PRIMARY_VALID" "$VALID"
"$SHORTG" -q "$VALID" "$CANONICAL"
test "$(wc -l < "$CANONICAL" | tr -d ' ')" = "785888"
test "$(shasum -a 256 "$CANONICAL" | awk '{print $1}')" = \
  "d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2"
cmp "$REFERENCE" "$CANONICAL"

python3 scripts/finalize_independent_manifest.py \
  --manifest "$MANIFEST" \
  --source "$SOURCE" \
  --valid "$VALID" \
  --primary-valid "$PRIMARY_VALID" \
  --canonical "$CANONICAL" \
  --reference-canonical "$REFERENCE" \
  --canonicalizer "$SHORTG"

echo "independent deletion/filter cross-check reproduced"
