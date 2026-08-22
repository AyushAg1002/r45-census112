#!/bin/sh
# Fetch third-party inputs from their authors' public sites and verify hashes.
# The release archive intentionally does not redistribute these files.
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DOWNLOAD_DIR="$PROJECT_ROOT/downloads"
DATA_ARCHIVE="$DOWNLOAD_DIR/r45extreme.tar.gz"
NAUTY_ARCHIVE="$DOWNLOAD_DIR/nauty2_9_3.tar.gz"
DATA_URL="https://users.cecs.anu.edu.au/~bdm/data/r45extreme.tar.gz"
NAUTY_URL="https://pallini.di.uniroma1.it/nauty2_9_3.tar.gz"

hash_file() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

mkdir -p "$DOWNLOAD_DIR" "$PROJECT_ROOT/data" "$PROJECT_ROOT/third_party"

# Reuse archives from the development tree when present.  Clean releases use
# downloads/ and obtain the same pinned bytes from the public URLs.
if [ -f "$PROJECT_ROOT/data/r45extreme.tar.gz" ]; then
  DATA_ARCHIVE="$PROJECT_ROOT/data/r45extreme.tar.gz"
fi
if [ -f "$PROJECT_ROOT/nauty2_9_3.tar.gz" ]; then
  NAUTY_ARCHIVE="$PROJECT_ROOT/nauty2_9_3.tar.gz"
fi

if [ ! -f "$DATA_ARCHIVE" ]; then
  curl -L --fail --show-error --output "$DATA_ARCHIVE" "$DATA_URL"
fi
test "$(hash_file "$DATA_ARCHIVE")" = \
  "9cfac9dbd1c209cfa342e5d5424df2a7a3fbb008ca00bf0a992e5bbe72f925b6"
if [ ! -d "$PROJECT_ROOT/data/r45extreme" ]; then
  tar -xzf "$DATA_ARCHIVE" -C "$PROJECT_ROOT/data"
fi

test "$(hash_file "$PROJECT_ROOT/data/r45extreme/r4522.113.g6")" = \
  "1e1a54b719dcdebb57581ee6f3cd4e1721e828680a72128010f1f888a4dda9db"
test "$(hash_file "$PROJECT_ROOT/data/r45extreme/r4522.114.g6")" = \
  "54dffec4ecab0f863b75620ccf8b228e5d6299c799e2d6b284fd51c51aa96ed7"
test "$(hash_file "$PROJECT_ROOT/data/r45extreme/r4521.106.g6")" = \
  "2be4df6ba89b1c55743624fb6e8141741aef82b06a922aa0a069923942389593"
test "$(hash_file "$PROJECT_ROOT/data/r45extreme/r4521.107.g6")" = \
  "6ef8619d5d6be9efa15cb9a5ccb6b0da7304cfbfd57fff29bb0dec2e46f81bef"

if [ ! -f "$NAUTY_ARCHIVE" ]; then
  curl -L --fail --show-error --output "$NAUTY_ARCHIVE" "$NAUTY_URL"
fi
test "$(hash_file "$NAUTY_ARCHIVE")" = \
  "9fc4edae04f88a0f5883985be3b39cf7f898fd6cc96e96b9ee25452743cc1b5b"
if [ ! -d "$PROJECT_ROOT/third_party/nauty2_9_3" ]; then
  tar -xzf "$NAUTY_ARCHIVE" -C "$PROJECT_ROOT/third_party"
fi

echo "third-party inputs fetched and verified"
