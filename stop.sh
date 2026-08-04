#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${1:-}"
if [ -z "$PORT" ]; then
    PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -n1 || true)
fi

if [ -z "$PORT" ]; then
    echo "No USB serial device found (looked for /dev/cu.usbmodem*)." >&2
    echo "Make sure the board is plugged in, or pass the port explicitly:" >&2
    echo "  ./stop.sh /dev/cu.usbmodemXXXX" >&2
    exit 1
fi

# Free up the port: a screen.sh session (attached or detached) holds it
# open, which would otherwise make our write below unreliable — this
# device doesn't consistently enforce exclusive-open locking, so a plain
# busy check can't be trusted to catch it.
./screen-kill.sh

# In case something other than screen.sh still holds the port, checked via
# lsof (who actually holds it open) rather than by probing with our own
# open(), for the same reliability reason as above.
if command -v lsof >/dev/null 2>&1; then
    HOLDER_PIDS=$(lsof -t -- "$PORT" 2>/dev/null || true)
    if [ -n "$HOLDER_PIDS" ]; then
        echo "$PORT is still busy — held open by PID(s): $(echo "$HOLDER_PIDS" | tr '\n' ' ')" >&2
        exit 1
    fi
fi

ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT

echo "Stopping code.py on $PORT..."
if ! printf '\x03' 2>"$ERR" >"$PORT"; then
    cat "$ERR" >&2
    exit 1
fi
