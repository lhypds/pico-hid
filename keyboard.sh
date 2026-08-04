#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/keyboard"

# The binary is built rather than `go run`, and named the way the app should
# read: on macOS the menu bar takes the application name from the running
# executable, so this is what appears beside the Settings item. `go run` would
# put its own temporary name up there instead.
BIN="Pico HID Keyboard"

if ! command -v go >/dev/null 2>&1; then
    echo "Go is not installed (or not on PATH)." >&2
    echo "Install it from https://go.dev/dl/ and re-run this script." >&2
    exit 1
fi

# go.mod and go.sum are deliberately not in the repo, so set the module up on
# the first run instead of leaving everyone to follow the README by hand.
if [ ! -f go.mod ]; then
    echo "Setting up the Go module (first run only)..."
    go mod init pico-hid-keyboard
fi

# go list resolves the imports without compiling, so this is a cheap way to ask
# whether anything is still missing. Also covers a go.mod that predates a new
# import being added.
if [ ! -f go.sum ] || ! go list -deps . >/dev/null 2>&1; then
    echo "Fetching dependencies (first run takes a while)..."
    go mod tidy
fi

echo "Building $BIN..."
if ! go build -o "$BIN" .; then
    echo >&2
    echo "Build failed. The GUI draws through OpenGL, so it needs a C compiler:" >&2
    echo "  macOS  xcode-select --install" >&2
    echo "  Debian/Ubuntu  sudo apt install gcc libgl1-mesa-dev xorg-dev" >&2
    exit 1
fi

# Pass arguments through, so `./keyboard.sh -url http://ph-1234.local` works.
exec "./$BIN" "$@"
