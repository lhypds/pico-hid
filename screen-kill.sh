#!/usr/bin/env bash
set -euo pipefail

# Kill any existing screen sessions. A stale session left bound to the
# port (e.g. from a crashed terminal) can exhaust the PTY pool and make
# new sessions fail with "Sorry, could not find a PTY."
sessions=$(screen -ls 2>/dev/null | awk '/^\t/{print $1}') || true
for session in $sessions; do
    screen -S "$session" -X quit >/dev/null 2>&1 || true
    echo "Killed screen session: $session"
done
