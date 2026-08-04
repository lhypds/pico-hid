#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DEST="upload-to-board"

rm -rf "$DEST"
mkdir -p "$DEST"

cp code.py boot.py "$DEST"/
cp -r lib "$DEST"/
cp -r public "$DEST"/

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

if [ -f settings.toml ]; then
    cp settings.toml "$DEST"/
else
    echo "Warning: settings.toml not found. Copy settings.toml.example to settings.toml and fill in your WiFi credentials, then re-run this script." >&2
fi

echo "Upload-ready files placed in $DEST/"

# Look for a mounted CIRCUITPY drive (macOS, and common Linux mount points).
BOARD=""
for candidate in /Volumes/CIRCUITPY /media/*/CIRCUITPY /run/media/*/CIRCUITPY; do
    if [ -d "$candidate" ]; then
        BOARD="$candidate"
        break
    fi
done

if [ -z "$BOARD" ]; then
    echo "No CIRCUITPY drive found — copy $DEST/'s contents onto it manually once it's plugged in."
    exit 0
fi

echo
read -r -p "Found board at $BOARD — copy $DEST/ onto it now? This overwrites its existing files. [y/N] " reply
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
