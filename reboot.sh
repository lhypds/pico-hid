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

echo "Reboot command sent."

# The hardware reset drops the USB serial port off the bus while the board
# re-enumerates. Wait out that window before touching the port again —
# attaching screen mid-re-enumeration makes it terminate immediately.
# Both loops fall through on timeout rather than failing: a fast
# re-enumeration can hide the disappearance entirely.
for _ in $(seq 1 20); do # up to ~2s for the port to disappear
    [ ! -e "$PORT" ] && break
    sleep 0.1
done
for _ in $(seq 1 60); do # up to ~15s for it to come back
    [ -e "$PORT" ] && break
    sleep 0.25
done
if [ ! -e "$PORT" ]; then
    echo "$PORT did not reappear after the reset — unplug and replug the board." >&2
    exit 1
fi
sleep 1 # let the OS finish setting up the port before opening it

# A hard reset can leave the board sitting at the REPL instead of
# auto-starting code.py. Nudge it with Ctrl-D — harmless either way: it
# starts code.py if idle, or just soft-reloads it if it's already running.
printf '\x04' 2>/dev/null >"$PORT" || true

rm -f "$ERR"
exec ./screen.sh "$PORT"
