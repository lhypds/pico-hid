import time
import board
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

# Ensure the keyboard and mouse objects are initialized
time.sleep(1)
wt = 0.2

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
    server_socket.listen(1)
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
    "TAB": (Keycode.TAB, False),
    "ENTER": (Keycode.ENTER, False),
    "SPACE": (Keycode.SPACE, False),
}


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


while True:
    current_time = time.monotonic()

    # Check for new connections
    client_socket = None
    try:
        client_socket, client_address = server_socket.accept()
        # The accepted socket inherits the listener's 1s timeout, which is
        # meant for polling accept(), not for talking to a client. Too short
        # here: a send() that trips it leaves the reply unsent.
        client_socket.settimeout(5)

        buffer = bytearray(2048)
        bytes_received = client_socket.recv_into(buffer)
        request_str = str(buffer[:bytes_received], "utf8")

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

            # Check if the request body starts with "keycode="
            if body.startswith("keycode="):
                keys = body.split("=", 1)[1].strip().split(",")
                for key in keys:
                    if key in keycode_map:
                        keycode, requires_shift = keycode_map[key]
                        print(f"Triggering keyboard event for key: {key}")
                        if requires_shift:
                            keyboard.press(Keycode.SHIFT, keycode)
                            time.sleep(wt)
                            keyboard.release_all()
                            time.sleep(wt)
                        else:
                            keyboard.press(keycode)
                            time.sleep(wt)
                            keyboard.release_all()
                            time.sleep(wt)
                    else:
                        print(f"Invalid key: {key}")

            elif body.startswith("typing="):
                text = body.split("=", 1)[1].strip()
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
                else:
                    print(f"Invalid mouse action: {action}")

    except Exception as e:
        # errno 116 (ETIMEDOUT) is just the accept() timeout — no connection
        # this iteration. getattr because not every exception has an errno,
        # and touching e.errno on one that doesn't would crash the server.
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
