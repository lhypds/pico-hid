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
import wifi
import socketpool
import mdns
import microcontroller
import supervisor

print(sys.version)


def write_error_file(message):
    try:
        with open("/error.txt", "w") as f:
            f.write(message + "\n")
    except OSError as e:
        print(f"Could not write error.txt (is boot.py remounting storage?): {e}")


# Clear any stale error from a previous boot so error.txt reflects this run.
try:
    os.remove("/error.txt")
except OSError:
    pass

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
mouse = Mouse(usb_hid.devices)

# Onboard LED as an activity light. On the Pico W it hangs off the WiFi chip
# rather than a GPIO, so guard the setup — a board without board.LED should
# still run the server.
try:
    status_led = digitalio.DigitalInOut(board.LED)
    status_led.direction = digitalio.Direction.OUTPUT
    status_led.value = False
except Exception as e:
    status_led = None
    print(f"No onboard LED available: {e}")

led_min_on = 0.05  # a single keystroke handles too fast to blink visibly
led_off_after = None  # when the LED is due off, or None while off


def led_on():
    global led_off_after
    if status_led is None:
        return
    status_led.value = True
    led_off_after = time.monotonic() + led_min_on


def service_led():
    """Turn the LED off from the main loop, so the blink never delays a keystroke."""
    global led_off_after
    if led_off_after is not None and time.monotonic() >= led_off_after:
        status_led.value = False
        led_off_after = None


time.sleep(1)  # let the HID devices finish initializing
wt = 0.2
# Keys hold much shorter than wt: USB HID polls every few ms, and the board
# can't accept connections while sleeping — a slow hold loses keys when
# typing fast.
key_wt = 0.03

wifi_ssid = os.getenv("WIFI_SSID")
wifi_password = os.getenv("WIFI_PASSWORD")

if not wifi_ssid or not wifi_password:
    message = "WiFi SSID or Password not set in environment variables"
    print(message)
    write_error_file(message)
    sys.exit(1)

# Board identity: ph-<uid>, from the CPU's hardware UID — unique per board and
# stable across reboots. Used as the network name for both DHCP and mDNS.
uid_suffix = "".join(f"{b:02x}" for b in microcontroller.cpu.uid[-2:])
board_id = f"ph-{uid_suffix}"
print(f"Board id: {board_id}")

# Present the id to the router's DHCP; must be set before wifi.radio.connect().
try:
    wifi.radio.hostname = board_id
except Exception as e:
    print(f"Could not set WiFi hostname: {e}")

# Disable the CYW43 WiFi chip's power-save mode: with it on (the default) the
# chip naps after idle periods and stops answering network traffic — the
# server works at first, then turns unreachable minutes later. Power draw is
# a non-issue since the board runs off the target machine's USB.
try:
    import cyw43

    cyw43.set_power_management(cyw43.PM_DISABLED)
    print("WiFi power-save disabled")
except Exception as e:
    print(f"Could not disable WiFi power-save: {e}")

print("Connecting to WiFi: " + wifi_ssid + "...")

# After a soft reload (auto-reload on file save, or Ctrl-D) the CYW43 radio
# comes up wedged: every connect raises "Unknown failure 1", and neither
# toggling wifi.radio.enabled nor resetting power management recovers it.
# Only a hard reset does. So on a reload-run a single failed attempt is
# already conclusive — recover with microcontroller.reset() below. That run
# is then a fresh STARTUP, which keeps a genuinely dead network from
# reset-looping forever.
is_fresh_boot = supervisor.runtime.run_reason is supervisor.RunReason.STARTUP
max_attempts = 5 if is_fresh_boot else 1

connected = False
for attempt in range(1, max_attempts + 1):
    try:
        wifi.radio.connect(wifi_ssid, wifi_password)
        print("Connected to WiFi")
        connected = True
        break
    except Exception as e:
        print(f"Failed to connect to WiFi (Attempt {attempt}/{max_attempts}): {e}")
        if attempt < max_attempts:
            time.sleep(5)

if not connected:
    if not is_fresh_boot:
        print("WiFi radio wedged by the soft reload -- hard-resetting to recover")
        time.sleep(1)  # let the message reach the serial console before USB drops
        microcontroller.reset()
    message = "Could not connect to WiFi after several attempts."
    print(message)
    write_error_file(message)
    sys.exit(1)

ip_address = wifi.radio.ipv4_address
print(f"IP Address: {ip_address}")

pool = socketpool.SocketPool(wifi.radio)

HOST = "0.0.0.0"
PORT = 80

# Write the IP and mDNS name to the CIRCUITPY drive so they can be read from
# the PC without scanning the network. Needs boot.py to remount storage
# writable; otherwise the filesystem is read-only and this is skipped.
try:
    with open("/ip.txt", "w") as f:
        f.write(f"{ip_address}\n")
    with open("/hostname.txt", "w") as f:
        f.write(f"{board_id}.local\n")
    print("Wrote IP to ip.txt and hostname to hostname.txt")
except OSError as e:
    print(f"Could not write ip.txt/hostname.txt (is boot.py remounting storage?): {e}")

# Advertise over mDNS so the board is reachable at a fixed name
# (http://<board_id>.local) regardless of the DHCP-assigned IP.
try:
    mdns_server = mdns.Server(wifi.radio)
    mdns_server.hostname = board_id
    mdns_server.advertise_service(service_type="_http", protocol="_tcp", port=PORT)
    print(f"mDNS advertised: http://{board_id}.local")
except Exception as e:
    print(f"Could not start mDNS: {e}")

try:
    server_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    # Backlog of 4: while a key is held this loop isn't in accept(), and with
    # a backlog of 1 the next request in a fast burst was refused outright —
    # a silently lost keystroke. The extra slots let bursts wait.
    server_socket.listen(4)
    server_socket.settimeout(1)  # so accept() doubles as the main-loop tick
except Exception as e:
    message = f"Could not start server on {HOST}:{PORT}: {e}"
    print(message)
    write_error_file(message)
    sys.exit(1)
print(f"Listening on {HOST}:{PORT}")

# Key names accepted in keycode= commands, mapped to (Keycode, needs_shift).
keycode_map = {}
for _c in "abcdefghijklmnopqrstuvwxyz":
    _code = getattr(Keycode, _c.upper())
    keycode_map[_c] = (_code, False)
    keycode_map[_c.upper()] = (_code, True)
for _digit, _shifted, _name in zip(
    "1234567890",
    "!@#$%^&*()",
    ("ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "ZERO"),
):
    _code = getattr(Keycode, _name)
    keycode_map[_digit] = (_code, False)
    keycode_map[_shifted] = (_code, True)
for _i in range(1, 25):
    keycode_map[f"F{_i}"] = (getattr(Keycode, f"F{_i}"), False)
# Names matching Keycode attributes. Modifiers are only useful in a chord
# ("CTRL+c"); alone they do nothing. Punctuation is by physical key — the
# target machine's own layout decides what a shifted key actually types.
for _name in (
    "TAB ENTER SPACE CONTROL SHIFT ALT GUI "
    "ESCAPE BACKSPACE DELETE INSERT HOME END PAGE_UP PAGE_DOWN "
    "CAPS_LOCK PRINT_SCREEN SCROLL_LOCK PAUSE APPLICATION "
    "MINUS EQUALS LEFT_BRACKET RIGHT_BRACKET BACKSLASH SEMICOLON QUOTE "
    "GRAVE_ACCENT COMMA PERIOD FORWARD_SLASH"
).split():
    keycode_map[_name] = (getattr(Keycode, _name), False)
for _alias, _name in (
    ("UP", "UP_ARROW"),
    ("DOWN", "DOWN_ARROW"),
    ("LEFT", "LEFT_ARROW"),
    ("RIGHT", "RIGHT_ARROW"),
    ("CTRL", "CONTROL"),
    ("ESC", "ESCAPE"),
    ("OPTION", "ALT"),
    ("CMD", "GUI"),
    ("COMMAND", "GUI"),
    ("WIN", "GUI"),
    ("WINDOWS", "GUI"),
    ("META", "GUI"),
):
    keycode_map[_alias] = (getattr(Keycode, _name), False)


def press_chord(chord):
    """Press every key in a "+"-joined chord at once, e.g. "CTRL+SHIFT+c".

    Held simultaneously and released together — that's what makes a shortcut
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


def parse_mouse(action_str):
    """Split "MOVE(3,-4)" into ("MOVE", 3, -4); (None, 0, 0) if malformed."""
    try:
        action, rest = action_str.split("(", 1)
        x_str, y_str = rest.strip(") ").split(",", 1)
        return action.strip(), int(x_str), int(y_str)
    except ValueError:
        return None, 0, 0


# Periodic mouse jiggle. Interval defaults to 30s when MOUSE_MOVE_INTERVAL is
# unset; AUTOMOVE_AUTOSTART=0 boots with it off. Either way it stays
# controllable at runtime via automove=START / automove=STOP.
mouse_move_interval = int(os.getenv("MOUSE_MOVE_INTERVAL") or 30)
last_mouse_move_time = time.monotonic()
auto_move_enabled = str(
    os.getenv("AUTOMOVE_AUTOSTART") or "on"
).strip().lower() not in (
    "0",
    "false",
    "no",
    "off",
)
print(f"Auto movement: {'enabled' if auto_move_enabled else 'disabled'}")
print(f"Interval: {mouse_move_interval}s")

# Static files for the browser UI, served on GET. One self-contained page —
# CSS and JS inlined — so loading it costs one request instead of one per asset.
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

    A single recv can return just the first TCP segment, and closing the
    socket with unread bytes left turns the close into a RST — the browser
    then reports a network error for a request that actually ran, retries it,
    and a keystroke comes out doubled.
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
            # speculative connection — from here a slow client gets 5s per
            # read (a send() tripping a short timeout would lose the reply).
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
        send_response(
            sock, "500 Internal Server Error", "text/plain", "Internal Server Error"
        )


# Seq token of the most recently executed command. The web UI retries a
# command when the response got lost even though the request may have run —
# a repeat of this token identifies such a retry so it isn't run twice.
last_seq = None

while True:
    current_time = time.monotonic()
    service_led()

    client_socket = None
    try:
        client_socket, client_address = server_socket.accept()
        led_on()
        # The accepted socket inherits the listener's 1s timeout, meant for
        # polling accept(). Don't jump straight to a long timeout: Safari
        # (iOS above all) opens speculative connections it never sends a byte
        # on, and this single-threaded loop would sit blocked on each one
        # while real requests queue behind it. So 0.5s for the first byte;
        # read_request() relaxes to 5s once data is actually flowing.
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
            # Reply before running the command: HID actions are slow on
            # purpose and the caller doesn't need a result, so answering
            # afterwards just surfaces as "Failed to fetch" in the browser
            # even though the command ran fine.
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

            # "," separates keys pressed one after another, "+" joins keys
            # held together as a chord: "CTRL+c" or "CTRL+c,CTRL+v".
            elif body.startswith("keycode="):
                for chord in body.split("=", 1)[1].strip().split(","):
                    press_chord(chord)

            elif body.startswith("typing="):
                # No strip() here: fetch bodies arrive exact, and a lone or
                # trailing space is a real keystroke — the web UI's mirror
                # mode sends each space as its own typing= command.
                text = body.split("=", 1)[1]
                print(f"Typing text: {text}")
                keyboard_layout.write(text)

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

            elif body.startswith("mouse="):
                action, x, y = parse_mouse(body.split("=", 1)[1].strip())
                print(f"Mouse event: {action} ({x},{y})")
                # The pre-click sleep lets the host settle after a real move;
                # clicking in place (0,0) — all the web UI ever sends — skips
                # it, so a click lands the moment the command arrives.
                if action == "CLICK":
                    if x or y:
                        mouse.move(x, y)
                        time.sleep(wt)
                    mouse.click(Mouse.LEFT_BUTTON)
                    time.sleep(wt)
                elif action == "RIGHT_CLICK":
                    if x or y:
                        mouse.move(x, y)
                        time.sleep(wt)
                    mouse.click(Mouse.RIGHT_BUTTON)
                    time.sleep(wt)
                elif action == "DOUBLE_CLICK":
                    # While the left button is held (a PRESS the web UI ends
                    # with a quick in-place lift), pressing again is a no-op,
                    # so this lands as up, down, up — completing the held
                    # press into a double-click with tight timing.
                    if x or y:
                        mouse.move(x, y)
                        time.sleep(wt)
                    mouse.click(Mouse.LEFT_BUTTON)
                    mouse.click(Mouse.LEFT_BUTTON)
                    time.sleep(wt)
                elif action == "MOVE":
                    # No trailing sleep: the web UI's trackpad drag sends many
                    # of these in a row, so latency here is directly felt.
                    mouse.move(x, y)
                elif action == "PRESS":
                    # Hold the left button down until RELEASE; MOVEs in
                    # between become a drag. No sleeps: these bracket a
                    # stream of MOVEs, and USB HID keeps events ordered.
                    mouse.move(x, y)
                    mouse.press(Mouse.LEFT_BUTTON)
                elif action == "RELEASE":
                    mouse.move(x, y)
                    mouse.release(Mouse.LEFT_BUTTON)
                elif action == "SCROLL":
                    # Wheel notches in y; positive scrolls up. Coalesced
                    # client-side like MOVE, so no trailing sleep either.
                    mouse.move(0, 0, y)
                else:
                    print(f"Invalid mouse action: {action}")

    except Exception as e:
        # errno 116 (ETIMEDOUT) is the accept() poll finding no connection,
        # or an accepted connection that never sent a byte (browsers abandon
        # speculative connections). getattr because not every exception has
        # an errno.
        if getattr(e, "errno", None) == 116:
            pass
        else:
            message = f"An unexpected error occurred: {e}"
            print(message)
            write_error_file(message)
    finally:
        # Always close the client socket — each leaked socket is gone for
        # good, and an exhausted pool stops the server accepting entirely.
        if client_socket is not None:
            client_socket.close()

    if auto_move_enabled and current_time - last_mouse_move_time >= mouse_move_interval:
        mouse.move(1, 0)
        time.sleep(wt)
        mouse.move(-1, 0)
        last_mouse_move_time = current_time
