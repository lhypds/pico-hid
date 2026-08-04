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

# Stop code.py first — it still owns the console otherwise, and the reboot
# command below wouldn't be read as a command at all.
./stop.sh "$PORT"
sleep 1

ERR=$(mktemp)
trap 'rm -f "$ERR"' EXIT

echo "Rebooting board on $PORT..."

# microcontroller.reset() performs a real hardware reset (same as the
# physical reset button / a power cycle), so boot.py runs again too —
# unlike Ctrl-D, which only soft-reloads code.py.
printf 'import microcontroller; microcontroller.reset()\r\n' 2>"$ERR" >"$PORT"

# A hard reset can leave the board sitting at the REPL instead of
# auto-starting code.py. Give it a moment to come back up over USB, then
# nudge it with Ctrl-D — harmless either way: it starts code.py if idle,
# or just soft-reloads it if it's already running.
sleep 2
printf '\x04' 2>/dev/null >"$PORT" || true

echo "Reboot command sent."

rm -f "$ERR"
exec ./screen.sh "$PORT"
