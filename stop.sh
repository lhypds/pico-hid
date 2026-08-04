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
        echo "$PORT is still busy — held open by:" >&2
        for pid in $HOLDER_PIDS; do
            echo "  PID $pid: $(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")" >&2
        done
        echo "Quit or disconnect that program (e.g. Thonny stays connected to the" >&2
        echo "board the whole time it's open), then re-run this script." >&2
        exit 1
    fi
fi

ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT

echo "Stopping code.py on $PORT..."
# The first Ctrl-C interrupts code.py, which drops to CircuitPython's
# "Press any key to enter the REPL" screen — not a live >>> prompt yet.
# The second Ctrl-C is that "any key": without it, whatever a caller
# writes next has its first character eaten by that screen instead of
# reaching the REPL, silently corrupting the command.
if ! { printf '\x03'; sleep 0.3; printf '\x03'; } 2>"$ERR" >"$PORT"; then
    cat "$ERR" >&2
    exit 1
fi
sleep 0.3
