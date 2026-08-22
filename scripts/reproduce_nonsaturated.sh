#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
NAUTY="third_party/nauty2_9_3"
SOURCE="data/r45extreme/r4522.113.g6"
ALL="data/r4522.112.deletions.all.g6"
VALID="data/r4522.112.deletions.valid.g6"
OUTPUT="data/r4522.112.nonsaturated.g6"
TRACES="data/r4522.112.nonsaturated.traces.g6"
RECANON="data/r4522.112.nonsaturated.traces.recanon.g6"
SOURCE114="data/r45extreme/r4522.114.g6"
FROM114_ALL="data/r4522.113.from114.all.g6"
FROM114_VALID="data/r4522.113.from114.valid.g6"
FROM114_UNIQUE="data/r4522.113.from114.unique.g6"
SOURCE113_CANON="data/r4522.113.published.canonical.g6"
SOURCE113_UNION="data/r4522.113.published_plus_from114.g6"

test "$(shasum -a 256 "$SOURCE" | awk '{print $1}')" = \
  "1e1a54b719dcdebb57581ee6f3cd4e1721e828680a72128010f1f888a4dda9db"
test "$(wc -l < "$SOURCE" | tr -d ' ')" = "30976"
test "$(shasum -a 256 "$SOURCE114" | awk '{print $1}')" = \
  "54dffec4ecab0f863b75620ccf8b228e5d6299c799e2d6b284fd51c51aa96ed7"
test "$(wc -l < "$SOURCE114" | tr -d ' ')" = "133"

"$NAUTY/deledgeg" -q "$SOURCE" "$ALL"
"$NAUTY/pickg" -q -h:4 "$ALL" "$VALID"
"$NAUTY/shortg" -q "$VALID" "$OUTPUT"

test "$(wc -l < "$ALL" | tr -d ' ')" = "3500288"
test "$(wc -l < "$VALID" | tr -d ' ')" = "887138"
test "$(wc -l < "$OUTPUT" | tr -d ' ')" = "785888"
test "$(shasum -a 256 "$OUTPUT" | awk '{print $1}')" = \
  "d2c556f52d13dd4d38ed955bedd3db5f52b883faafc45fe5561e611afa5cd6a2"
gzip -9 -n -kf "$OUTPUT"
test "$(shasum -a 256 "$OUTPUT.gz" | awk '{print $1}')" = \
  "fcb0ef605eee3150d95d5b91535934ba9b711450a2edb7e55fd39a37ec3211d5"

# Cross-check isomorphism rejection with Traces, then map that result back to
# the ordinary-nauty canonical convention and require byte-for-byte identity.
"$NAUTY/shortg" -t -q "$VALID" "$TRACES"
test "$(wc -l < "$TRACES" | tr -d ' ')" = "785888"
"$NAUTY/shortg" -q "$TRACES" "$RECANON"
cmp "$OUTPUT" "$RECANON"

"$NAUTY/countg" -q -n22 -e112 -k:3 -h:4 "$OUTPUT"
AUTOMORPHISM_COUNTS=$("$NAUTY/countg" -q -1 --a "$OUTPUT")
test "$AUTOMORPHISM_COUNTS" = "1 783907
2 1911
4 70"
printf '%s\n' "$AUTOMORPHISM_COUNTS" > \
  "results/nonsaturated_automorphism_counts.txt"
python3 "verify_nonsaturated.py" \
  --catalogue "$OUTPUT" \
  --output "results/nonsaturated_validation.json"

# One-level-up regression: reproduce the nonsaturated part of e=113 from the
# complete e=114 layer, then prove every resulting class occurs in the
# published e=113 catalogue.
"$NAUTY/deledgeg" -q "$SOURCE114" "$FROM114_ALL"
"$NAUTY/pickg" -q -h:4 "$FROM114_ALL" "$FROM114_VALID"
"$NAUTY/shortg" -q "$FROM114_VALID" "$FROM114_UNIQUE"
test "$(wc -l < "$FROM114_ALL" | tr -d ' ')" = "15162"
test "$(wc -l < "$FROM114_VALID" | tr -d ' ')" = "4077"
test "$(wc -l < "$FROM114_UNIQUE" | tr -d ' ')" = "3296"
"$NAUTY/shortg" -q "$SOURCE" "$SOURCE113_CANON"
"$NAUTY/catg" -x "$SOURCE" "$FROM114_UNIQUE" |
  "$NAUTY/shortg" -q - "$SOURCE113_UNION"
cmp "$SOURCE113_CANON" "$SOURCE113_UNION"

python3 "scripts/finalize_nonsaturated_manifest.py"

echo "nonsaturated census reproduced"
