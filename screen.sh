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

# Kill any existing screen sessions first. A stale session left bound to
# the port (e.g. from a crashed terminal) can exhaust the PTY pool and
# make new sessions fail with "Sorry, could not find a PTY."
sessions=$(screen -ls 2>/dev/null | awk '/^\t/{print $1}') || true
for session in $sessions; do
    screen -S "$session" -X quit >/dev/null 2>&1 || true
done

echo "Connecting to $PORT at ${BAUD} baud."
echo "Press Ctrl-A then K, then Y to exit."
exec screen "$PORT" "$BAUD"
