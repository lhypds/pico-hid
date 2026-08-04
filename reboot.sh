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
    echo "  ./reboot.sh /dev/cu.usbmodemXXXX" >&2
    exit 1
fi

# Free up the port: a screen.sh session (attached or detached) holds it
# open, which would otherwise make our writes below unreliable — this
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

echo "Rebooting board on $PORT..."

# Ctrl-C breaks out of whatever code.py is doing and drops to the REPL.
# microcontroller.reset() then performs a real hardware reset (same as
# the physical reset button / a power cycle), so boot.py runs again too —
# unlike Ctrl-D, which only soft-reloads code.py.
{
    printf '\x03'
    sleep 0.5
    printf 'import microcontroller; microcontroller.reset()\r\n'
} 2>"$ERR" >"$PORT"

# A hard reset can leave the board sitting at the REPL instead of
# auto-starting code.py. Give it a moment to come back up over USB, then
# nudge it with Ctrl-D — harmless either way: it starts code.py if idle,
# or just soft-reloads it if it's already running.
sleep 2
printf '\x04' 2>/dev/null >"$PORT" || true

echo "Reboot command sent."
