import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.mouse import Mouse
import os
import sys
import ssl
import wifi
import socketpool
import adafruit_requests
import mdns
import microcontroller
import re

print(sys.version)


def write_error_file(message):
    try:
        with open("/error.txt", "w") as f:
            f.write(message + "\n")
    except OSError as e:
        print(f"Could not write error.txt (is boot.py remounting storage?): {e}")


# Clear any stale error from a previous boot so error.txt always reflects
# the current run.
try:
    os.remove("/error.txt")
except OSError:
    pass

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
mouse = Mouse(usb_hid.devices)

# Onboard LED, used as an activity light: it lights up whenever a request comes
# in. On the Pico W the LED hangs off the WiFi chip rather than a normal GPIO,
# so guard the setup — a board without board.LED should still run the server.
try:
    status_led = digitalio.DigitalInOut(board.LED)
    status_led.direction = digitalio.Direction.OUTPUT
    status_led.value = False
except Exception as e:
    status_led = None
    print(f"No onboard LED available: {e}")

# How long the LED stays lit per request. Handling a single keystroke takes only
# tens of ms, which would blink too briefly to see.
led_min_on = 0.05
# When the LED is due to go back off, or None while it is already off.
led_off_after = None


def led_on():
    """Light the LED and schedule it to go off again."""
    global led_off_after
    if status_led is None:
        return
    status_led.value = True
    led_off_after = time.monotonic() + led_min_on


def service_led():
    """Turn the LED off once it has been lit long enough.

    Called from the main loop instead of switching the LED off straight after a
    request, so waiting out the blink never delays a keystroke.
    """
    global led_off_after
    if led_off_after is not None and time.monotonic() >= led_off_after:
        status_led.value = False
        led_off_after = None


# Ensure the keyboard and mouse objects are initialized
time.sleep(1)
wt = 0.2
# Keys get a much shorter hold than wt: USB HID polls every few milliseconds, so
# tens of ms is plenty for the host to register a press, and anything longer caps
# how fast keys can be typed. While the board is busy sleeping here it isn't
# accepting connections, so a slow hold is what makes fast typing lose keys.
key_wt = 0.03

wifi_ssid = os.getenv("WIFI_SSID")
wifi_password = os.getenv("WIFI_PASSWORD")

if not wifi_ssid or not wifi_password:
    message = "WiFi SSID or Password not set in environment variables"
    print(message)
    write_error_file(message)
    sys.exit(1)

# Board identity: ph-<uid>, derived from the CPU's hardware UID —
# unique per board and stable across reboots, so no persistence needed.
# It becomes the board's network name for both DHCP and mDNS, and is
# written to hostname.txt after WiFi connects.
uid_suffix = "".join(f"{b:02x}" for b in microcontroller.cpu.uid[-2:])
board_id = f"ph-{uid_suffix}"
print(f"Board id: {board_id}")

# Present the id as hostname to the router's DHCP. Must be set before
# wifi.radio.connect().
try:
    wifi.radio.hostname = board_id
except Exception as e:
    print(f"Could not set WiFi hostname: {e}")

# Disable the CYW43 WiFi chip's power-save mode. With it on (the default),
# the chip naps after idle periods and stops answering network traffic —
# the server works at first, then turns unreachable minutes later. Power
# draw is a non-issue since the board runs off the target machine's USB.
try:
    import cyw43

    cyw43.set_power_management(cyw43.PM_DISABLED)
    print("WiFi power-save disabled")
except Exception as e:
    print(f"Could not disable WiFi power-save: {e}")

print("Connecting to WiFi: " + wifi_ssid + "...")

max_retries = 5
retry_count = 0
connected = False

while retry_count < max_retries and not connected:
    try:
        wifi.radio.connect(wifi_ssid, wifi_password)
        print("Connected to WiFi")
        connected = True
    except Exception as e:
        retry_count += 1
        print(f"Failed to connect to WiFi (Attempt {retry_count}/{max_retries}): {e}")
        time.sleep(5)  # Wait before retrying

if not connected:
    message = "Could not connect to WiFi after several attempts."
    print(message)
    write_error_file(message)
    sys.exit(1)

# Print the IP address
ip_address = wifi.radio.ipv4_address
print(f"IP Address: {ip_address}")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Set up the server
HOST = "0.0.0.0"
PORT = 80

# Advertise over mDNS so the board is reachable at a fixed name
# (http://<hostname>.local) regardless of the DHCP-assigned IP.
# board_id is unique per board, so multiple boards on the same network
# never collide.
mdns_hostname = board_id

# Write the IP and mDNS name to ip.txt / hostname.txt on the CIRCUITPY
# drive so they can be read from the PC without scanning the network.
# Requires boot.py to remount storage writable; if missing the filesystem is
# read-only and this is skipped.
try:
    with open("/ip.txt", "w") as f:
        f.write(f"{ip_address}\n")
    with open("/hostname.txt", "w") as f:
        f.write(f"{mdns_hostname}.local\n")
    print("Wrote IP to ip.txt and hostname to hostname.txt")
except OSError as e:
    print(f"Could not write ip.txt/hostname.txt (is boot.py remounting storage?): {e}")

try:
    mdns_server = mdns.Server(wifi.radio)
    mdns_server.hostname = mdns_hostname
    mdns_server.advertise_service(service_type="_http", protocol="_tcp", port=PORT)
    print(f"mDNS advertised: http://{mdns_hostname}.local")
except Exception as e:
    print(f"Could not start mDNS: {e}")

try:
    server_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    # Backlog of 4: while a key is being pressed this loop isn't in accept(),
    # and with a backlog of 1 the next request in a fast burst was refused
    # outright — a silently lost keystroke. The extra slots let bursts wait.
    server_socket.listen(4)
    server_socket.settimeout(1)  # Set a timeout for accept
except Exception as e:
    message = f"Could not start server on {HOST}:{PORT}: {e}"
    print(message)
    write_error_file(message)
    sys.exit(1)
print(f"Listening on {HOST}:{PORT}")

# Mapping of key names to Keycode values
keycode_map = {
    "A": (Keycode.A, True),
    "a": (Keycode.A, False),
    "B": (Keycode.B, True),
    "b": (Keycode.B, False),
    "C": (Keycode.C, True),
    "c": (Keycode.C, False),
    "D": (Keycode.D, True),
    "d": (Keycode.D, False),
    "E": (Keycode.E, True),
    "e": (Keycode.E, False),
    "F": (Keycode.F, True),
    "f": (Keycode.F, False),
    "G": (Keycode.G, True),
    "g": (Keycode.G, False),
    "H": (Keycode.H, True),
    "h": (Keycode.H, False),
    "I": (Keycode.I, True),
    "i": (Keycode.I, False),
    "J": (Keycode.J, True),
    "j": (Keycode.J, False),
    "K": (Keycode.K, True),
    "k": (Keycode.K, False),
    "L": (Keycode.L, True),
    "l": (Keycode.L, False),
    "M": (Keycode.M, True),
    "m": (Keycode.M, False),
    "N": (Keycode.N, True),
    "n": (Keycode.N, False),
    "O": (Keycode.O, True),
    "o": (Keycode.O, False),
    "P": (Keycode.P, True),
    "p": (Keycode.P, False),
    "Q": (Keycode.Q, True),
    "q": (Keycode.Q, False),
    "R": (Keycode.R, True),
    "r": (Keycode.R, False),
    "S": (Keycode.S, True),
    "s": (Keycode.S, False),
    "T": (Keycode.T, True),
    "t": (Keycode.T, False),
    "U": (Keycode.U, True),
    "u": (Keycode.U, False),
    "V": (Keycode.V, True),
    "v": (Keycode.V, False),
    "W": (Keycode.W, True),
    "w": (Keycode.W, False),
    "X": (Keycode.X, True),
    "x": (Keycode.X, False),
    "Y": (Keycode.Y, True),
    "y": (Keycode.Y, False),
    "Z": (Keycode.Z, True),
    "z": (Keycode.Z, False),
    "1": (Keycode.ONE, False),
    "!": (Keycode.ONE, True),
    "2": (Keycode.TWO, False),
    "@": (Keycode.TWO, True),
    "3": (Keycode.THREE, False),
    "#": (Keycode.THREE, True),
    "4": (Keycode.FOUR, False),
    "$": (Keycode.FOUR, True),
    "5": (Keycode.FIVE, False),
    "%": (Keycode.FIVE, True),
    "6": (Keycode.SIX, False),
    "^": (Keycode.SIX, True),
    "7": (Keycode.SEVEN, False),
    "&": (Keycode.SEVEN, True),
    "8": (Keycode.EIGHT, False),
    "*": (Keycode.EIGHT, True),
    "9": (Keycode.NINE, False),
    "(": (Keycode.NINE, True),
    "0": (Keycode.ZERO, False),
    ")": (Keycode.ZERO, True),
    "UP": (Keycode.UP_ARROW, False),
    "DOWN": (Keycode.DOWN_ARROW, False),
    "LEFT": (Keycode.LEFT_ARROW, False),
    "RIGHT": (Keycode.RIGHT_ARROW, False),
    "F1": (Keycode.F1, False),
    "F2": (Keycode.F2, False),
    "F3": (Keycode.F3, False),
    "F4": (Keycode.F4, False),
    "F5": (Keycode.F5, False),
    "F6": (Keycode.F6, False),
    "F7": (Keycode.F7, False),
    "F8": (Keycode.F8, False),
    "F9": (Keycode.F9, False),
    "F10": (Keycode.F10, False),
    "F11": (Keycode.F11, False),
    "F12": (Keycode.F12, False),
    "F13": (Keycode.F13, False),
    "F14": (Keycode.F14, False),
    "F15": (Keycode.F15, False),
    "F16": (Keycode.F16, False),
    "F17": (Keycode.F17, False),
    "F18": (Keycode.F18, False),
    "F19": (Keycode.F19, False),
    "F20": (Keycode.F20, False),
    "F21": (Keycode.F21, False),
    "F22": (Keycode.F22, False),
    "F23": (Keycode.F23, False),
    "F24": (Keycode.F24, False),
    "TAB": (Keycode.TAB, False),
    "ENTER": (Keycode.ENTER, False),
    "SPACE": (Keycode.SPACE, False),
    # Modifiers. Only useful combined into a chord ("CTRL+c"); pressed alone
    # they do nothing on the target machine.
    "CTRL": (Keycode.CONTROL, False),
    "CONTROL": (Keycode.CONTROL, False),
    "SHIFT": (Keycode.SHIFT, False),
    "ALT": (Keycode.ALT, False),
    "OPTION": (Keycode.ALT, False),
    "GUI": (Keycode.GUI, False),
    "CMD": (Keycode.GUI, False),
    "COMMAND": (Keycode.GUI, False),
    "WIN": (Keycode.GUI, False),
    "WINDOWS": (Keycode.GUI, False),
    "META": (Keycode.GUI, False),
    # Editing and navigation
    "ESC": (Keycode.ESCAPE, False),
    "ESCAPE": (Keycode.ESCAPE, False),
    "BACKSPACE": (Keycode.BACKSPACE, False),
    "DELETE": (Keycode.DELETE, False),
    "INSERT": (Keycode.INSERT, False),
    "HOME": (Keycode.HOME, False),
    "END": (Keycode.END, False),
    "PAGE_UP": (Keycode.PAGE_UP, False),
    "PAGE_DOWN": (Keycode.PAGE_DOWN, False),
    "CAPS_LOCK": (Keycode.CAPS_LOCK, False),
    "PRINT_SCREEN": (Keycode.PRINT_SCREEN, False),
    "SCROLL_LOCK": (Keycode.SCROLL_LOCK, False),
    "PAUSE": (Keycode.PAUSE, False),
    "APPLICATION": (Keycode.APPLICATION, False),
    # Punctuation, by physical key. The shifted character (e.g. "_" on MINUS)
    # comes from adding SHIFT, so the target machine's own layout decides what
    # actually gets typed.
    "MINUS": (Keycode.MINUS, False),
    "EQUALS": (Keycode.EQUALS, False),
    "LEFT_BRACKET": (Keycode.LEFT_BRACKET, False),
    "RIGHT_BRACKET": (Keycode.RIGHT_BRACKET, False),
    "BACKSLASH": (Keycode.BACKSLASH, False),
    "SEMICOLON": (Keycode.SEMICOLON, False),
    "QUOTE": (Keycode.QUOTE, False),
    "GRAVE_ACCENT": (Keycode.GRAVE_ACCENT, False),
    "COMMA": (Keycode.COMMA, False),
    "PERIOD": (Keycode.PERIOD, False),
    "FORWARD_SLASH": (Keycode.FORWARD_SLASH, False),
}


def press_chord(chord):
    """Press every key in a "+"-joined chord at once, e.g. "CTRL+SHIFT+c".

    Held simultaneously and released together, which is what makes a shortcut
    register as a shortcut instead of separate keystrokes.
    """
    codes = []
    for token in chord.split("+"):
        token = token.strip()
        if not token:
            continue
        entry = keycode_map.get(token)
        if entry is None:
            print(f"Invalid key: {token}")
            return
        code, requires_shift = entry
        if requires_shift and Keycode.SHIFT not in codes:
            codes.append(Keycode.SHIFT)
        if code not in codes:
            codes.append(code)

    if not codes:
        return
    keyboard.press(*codes)
    time.sleep(key_wt)
    keyboard.release_all()
    time.sleep(key_wt)


def parse_coordinates(action_str):
    match = re.search(r"\((-?\d+),\s*(-?\d+)\)", action_str)
    if match:
        x = int(match.group(1))
        y = int(match.group(2))
        return x, y
    return None, None


# Time interval for periodic mouse movement (in seconds).
# Defaults to 30s so automove works even when MOUSE_MOVE_INTERVAL is unset.
mouse_move_interval = int(os.getenv("MOUSE_MOVE_INTERVAL") or 30)
last_mouse_move_time = time.monotonic()
# Whether auto movement runs on boot; set AUTOMOVE_AUTOSTART=0 in settings.toml
# to boot with it off. Either way it stays controllable at runtime via
# automove=START / automove=STOP.
_autostart = os.getenv("AUTOMOVE_AUTOSTART")
auto_move_enabled = _autostart is None or str(_autostart).strip().lower() not in (
    "0",
    "false",
    "no",
    "off",
)
print(f"Auto movement: {'enabled' if auto_move_enabled else 'disabled'}")
print(f"Interval: {mouse_move_interval}s")

# Static files for the browser-based control UI, served on GET requests.
# One self-contained page — its CSS and JS are inlined — so loading the UI
# costs a single request instead of one per asset.
STATIC_FILES = {
    "/": ("public/index.html", "text/html"),
    "/index.html": ("public/index.html", "text/html"),
}


def send_all(sock, data):
    view = memoryview(data)
    sent = 0
    while sent < len(view):
        sent += sock.send(view[sent:])


def read_request(sock):
    """Read one full HTTP request: headers plus Content-Length bytes of body.

    A single recv can return just the first TCP segment. Closing the socket
    while unread bytes remain turns the close into a RST, and on a RST the
    browser discards our "200 OK" and reports a network error for a request
    that actually ran — which the web UI answers with a retry, i.e. a
    duplicated keystroke.
    """
    buffer = bytearray(2048)
    request = b""
    body_start = -1
    content_length = 0
    # 8KB cap so a malformed request can't grow the buffer unbounded.
    while len(request) < 8192:
        n = sock.recv_into(buffer)
        if n == 0:  # client closed its end, nothing more is coming
            break
        if not request:
            # First byte arrived, so this is a real request, not an idle
            # speculative connection — from here a slow client gets the
            # full 5s per read (a send() that trips a short timeout would
            # leave the reply unsent).
            sock.settimeout(5)
        request += bytes(buffer[:n])
        if body_start < 0:
            i = request.find(b"\r\n\r\n")
            if i >= 0:
                body_start = i + 4
                for line in str(request[:i], "utf8").split("\r\n")[1:]:
                    if line.lower().startswith("content-length:"):
                        try:
                            content_length = int(line[15:].strip())
                        except ValueError:
                            pass
        if body_start >= 0 and len(request) - body_start >= content_length:
            break
    return str(request, "utf8")


def send_response(sock, status, content_type, body):
    if isinstance(body, str):
        body = body.encode("utf8")
    headers = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    send_all(sock, headers.encode("utf8") + body)


def serve_static(sock, path):
    entry = STATIC_FILES.get(path.split("?")[0])
    if entry is None:
        send_response(sock, "404 Not Found", "text/plain", "Not Found")
        return
    file_path, content_type = entry
    try:
        with open(file_path, "rb") as f:
            body = f.read()
        send_response(sock, "200 OK", content_type, body)
    except OSError as e:
        print(f"Could not read {file_path}: {e}")
        send_response(sock, "500 Internal Server Error", "text/plain", "Internal Server Error")


# Seq token of the most recently executed command. The web UI retries a
# command when the response got lost, even though the request may have run —
# a repeat of this token identifies such a retry so it isn't run twice.
last_seq = None

while True:
    current_time = time.monotonic()
    service_led()

    # Check for new connections
    client_socket = None
    try:
        client_socket, client_address = server_socket.accept()
        led_on()
        # The accepted socket inherits the listener's 1s timeout, which is
        # meant for polling accept(), not for talking to a client. But don't
        # jump straight to a long timeout either: Safari (iOS above all)
        # opens speculative connections it never sends a byte on, and this
        # single-threaded loop would sit blocked on each one while real
        # requests queue behind it — the web UI felt completely dead from an
        # iPhone. So allow 0.5s for the first byte; read_request() relaxes
        # the timeout to 5s once data is actually flowing.
        client_socket.settimeout(0.5)

        request_str = read_request(client_socket)

        request_line = request_str.split("\r\n", 1)[0]
        request_parts = request_line.split(" ")
        method = request_parts[0] if request_parts else ""
        path = request_parts[1] if len(request_parts) > 1 else "/"
        body = request_str.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in request_str else ""

        print(f"{method} {path}{' ' + body if body else ''} from {client_address[0]}")

        if method == "GET":
            serve_static(client_socket, path)
        else:
            # Reply before running the command. HID actions are slow on
            # purpose (each key/click holds for wt, and typing a long string
            # takes seconds), and the caller doesn't need a result — so
            # answering afterwards just leaves the client waiting, which
            # surfaces in the browser as "Failed to fetch" even though the
            # command ran fine.
            send_response(client_socket, "200 OK", "text/plain", "OK")
            client_socket.close()
            client_socket = None

            # Commands from the web UI carry a "seq=<token>&" prefix; commands
            # sent without one (curl, the Go client) always execute.
            duplicate = False
            if body.startswith("seq="):
                parts = body.split("&", 1)
                seq = parts[0][4:]
                body = parts[1] if len(parts) > 1 else ""
                duplicate = seq == last_seq
                last_seq = seq

            if duplicate:
                print(f"Duplicate command (seq {last_seq}), skipping")

            # Check if the request body starts with "keycode="
            # "," separates keys pressed one after another, "+" joins keys held
            # together as a chord: "CTRL+c" or "CTRL+c,CTRL+v".
            elif body.startswith("keycode="):
                for chord in body.split("=", 1)[1].strip().split(","):
                    press_chord(chord)

            elif body.startswith("typing="):
                # No strip() here: fetch bodies arrive exact, and a lone or
                # trailing space is a real keystroke — the web UI's mirror
                # mode sends each space as its own typing= command, which
                # strip() was silently swallowing.
                text = body.split("=", 1)[1]
                print(f"Typing text: {text}")
                keyboard_layout.write(text)

            # Check if the request body starts with "automove="
            elif body.startswith("automove="):
                command = body.split("=", 1)[1].strip()
                if command == "START":
                    auto_move_enabled = True
                    last_mouse_move_time = current_time
                    print("Auto mouse movement started")
                elif command == "STOP":
                    auto_move_enabled = False
                    print("Auto mouse movement stopped")
                else:
                    print(f"Invalid automove command: {command}")

            # Check if the request body starts with "mouse="
            elif body.startswith("mouse="):
                action_str = body.split("=", 1)[1].strip()
                action, coords = (
                    action_str.split("(")[0].strip(),
                    action_str.split("(")[1].strip(),
                )

                # Parse the coordinates
                x, y = parse_coordinates(f"({coords}")
                if x is None or y is None:
                    print(f"Invalid mouse coordinates: {coords}")
                print(f"Triggering mouse event: {action} at x: {x}, y: {y}")

                if action == "CLICK":
                    mouse.move(x, y)
                    time.sleep(wt)
                    mouse.click(Mouse.LEFT_BUTTON)
                    time.sleep(wt)
                elif action == "RIGHT_CLICK":
                    mouse.move(x, y)
                    time.sleep(wt)
                    mouse.click(Mouse.RIGHT_BUTTON)
                    time.sleep(wt)
                elif action == "DOUBLE_CLICK":
                    mouse.move(x, y)
                    time.sleep(wt)
                    mouse.click(Mouse.LEFT_BUTTON)
                    mouse.click(Mouse.LEFT_BUTTON)
                    time.sleep(wt)
                elif action == "MOVE":
                    # No trailing sleep here: nothing else follows in this
                    # request, and the web UI's trackpad drag sends many of
                    # these in a row, so latency here is directly felt.
                    mouse.move(x, y)
                elif action == "SCROLL":
                    # Wheel notches in y; positive scrolls up. Coalesced
                    # client-side like MOVE, so no trailing sleep either.
                    mouse.move(0, 0, y)
                else:
                    print(f"Invalid mouse action: {action}")

    except Exception as e:
        # errno 116 (ETIMEDOUT) is either the accept() poll finding no
        # connection this iteration, or an accepted connection that never
        # sent a byte (browsers open speculative connections and may abandon
        # them). getattr because not every exception has an errno, and
        # touching e.errno on one that doesn't would crash the server.
        if getattr(e, "errno", None) == 116:
            pass  # Continue to periodic task
        else:
            message = f"An unexpected error occurred: {e}"
            print(message)
            write_error_file(message)
    finally:
        # Always close the client socket, including on errors — each leaked
        # socket is gone for good, and once the pool is exhausted the server
        # stops accepting connections entirely.
        if client_socket is not None:
            client_socket.close()

    # Perform periodic mouse movement if no connections are being handled
    if auto_move_enabled and current_time - last_mouse_move_time >= mouse_move_interval:
        # print("Performing periodic mouse movement")
        mouse.move(3, 0)  # Move mouse right 10 pixels
        time.sleep(wt)
        mouse.move(-3, 0)  # Move mouse left 10 pixels
        last_mouse_move_time = current_time
