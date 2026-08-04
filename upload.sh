#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DEST="upload-to-board"

# Default upload is just code.py and public/. EXTRA_ITEMS ship only with
# --all, or automatically when the board doesn't have them yet.
EXTRA_ITEMS=(boot.py lib settings.toml)

ALL=0
for arg in "$@"; do
    case "$arg" in
        --all) ALL=1 ;;
        *)
            echo "Usage: $0 [--all]" >&2
            echo "  --all  upload boot.py, lib/ and settings.toml too, not just code.py and public/" >&2
            exit 1
            ;;
    esac
done

# Look for a mounted CIRCUITPY drive (macOS, and common Linux mount points).
# Done before staging so we can check which files the board is missing.
BOARD=""
for candidate in /Volumes/CIRCUITPY /media/*/CIRCUITPY /run/media/*/CIRCUITPY; do
    if [ -d "$candidate" ]; then
        BOARD="$candidate"
        break
    fi
done

ITEMS=(code.py public)
if [ "$ALL" -eq 1 ]; then
    ITEMS+=("${EXTRA_ITEMS[@]}")
elif [ -n "$BOARD" ]; then
    for item in "${EXTRA_ITEMS[@]}"; do
        if [ ! -e "$BOARD/$item" ]; then
            echo "$item is missing on the board — including it in this upload."
            ITEMS+=("$item")
        fi
    done
else
    echo "No board mounted to check for missing files — staging only code.py and public/. Use --all to stage everything." >&2
fi

rm -rf "$DEST"
mkdir -p "$DEST"

for item in "${ITEMS[@]}"; do
    if [ ! -e "$item" ]; then
        if [ "$item" = "settings.toml" ]; then
            echo "Warning: settings.toml not found. Copy settings.toml.example to settings.toml and fill in your WiFi credentials, then re-run this script." >&2
        else
            echo "Warning: $item not found locally — skipping it." >&2
        fi
        continue
    fi
    cp -r "$item" "$DEST"/
done

# Shrink the control UI in the staging copy only, so public/index.html stays
# readable. Deliberately line-based: newlines survive, which keeps trailing
# "//" comments and JavaScript's semicolon insertion valid. A smarter
# minifier would save a few hundred more bytes and risk breaking the page.
if command -v python3 >/dev/null 2>&1; then
    python3 - "$DEST/public/index.html" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path) as f:
    source = f.read()

stripped = re.sub(r"<!--[\s\S]*?-->", "", source)  # HTML comments
stripped = re.sub(r"/\*[\s\S]*?\*/", "", stripped)  # CSS block comments

lines = []
for line in stripped.split("\n"):
    line = line.strip()
    if not line or line.startswith("//"):  # blank lines and JS comment lines
        continue
    lines.append(line)
minified = "\n".join(lines) + "\n"

with open(path, "w") as f:
    f.write(minified)

print(f"Minified index.html: {len(source)} -> {len(minified)} bytes")
PY
else
    echo "python3 not found — shipping index.html unminified." >&2
fi

echo "Upload-ready files placed in $DEST/"

if [ -z "$BOARD" ]; then
    echo "No CIRCUITPY drive found — copy $DEST/'s contents onto it manually once it's plugged in."
    exit 0
fi

echo
echo "Files to upload: $(ls "$DEST")"
read -r -p "Found board at $BOARD — copy $DEST/ onto it now? This overwrites those files on the board. [y/N] " reply
case "$reply" in
    [yY]|[yY][eE][sS]) ;;
    *)
        echo "Skipped. Copy $DEST/'s contents onto $BOARD manually when ready."
        exit 0
        ;;
esac

if cp -rv "$DEST"/. "$BOARD"/; then
    echo "Uploaded to $BOARD."
else
    echo "Failed to copy files to $BOARD." >&2
    echo "If the error above says the file system is read-only, see the README's 'Finding the board's address' section." >&2
    exit 1
fi
