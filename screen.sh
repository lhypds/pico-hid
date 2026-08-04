#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

BAUD=115200

PORT="${1:-}"
if [ -z "$PORT" ]; then
    PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -n1 || true)
fi

if [ -z "$PORT" ]; then
    echo "No USB serial device found (looked for /dev/cu.usbmodem*)." >&2
    echo "Make sure the board is plugged in, or pass the port explicitly:" >&2
    echo "  ./screen.sh /dev/cu.usbmodemXXXX" >&2
    exit 1
fi

echo "Connecting to $PORT at ${BAUD} baud."
echo "Press Ctrl-A then K, then Y to exit."
exec screen "$PORT" "$BAUD"
