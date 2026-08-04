#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DEST="upload-to-board"

rm -rf "$DEST"
mkdir -p "$DEST"

cp code.py boot.py "$DEST"/
cp -r lib "$DEST"/

if [ -f settings.toml ]; then
    cp settings.toml "$DEST"/
else
    echo "Warning: settings.toml not found. Copy settings.toml.example to settings.toml and fill in your WiFi credentials, then re-run this script." >&2
fi

echo "Upload-ready files placed in $DEST/ — copy its contents onto the CIRCUITPY drive."
