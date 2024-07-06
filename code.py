import time
import board
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse
import os
import sys
import ssl
import wifi
import socketpool
import adafruit_requests
import re

print(sys.version)

keyboard = Keyboard(usb_hid.devices)
mouse = Mouse(usb_hid.devices)

# Ensure the keyboard and mouse objects are initialized
time.sleep(1)

wifi_ssid = os.getenv("WIFI_SSID")
wifi_password = os.getenv("WIFI_PASSWORD")

if not wifi_ssid or not wifi_password:
    print("WiFi SSID or Password not set in environment variables")
    sys.exit(1)

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
    print("Could not connect to WiFi after several attempts.")
    sys.exit(1)

# Print the IP address
ip_address = wifi.radio.ipv4_address
print(f"IP Address: {ip_address}")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Set up the server
HOST = "0.0.0.0"
PORT = 8080

server_socket = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
server_socket.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(1)
print(f"Listening on {HOST}:{PORT}")
print("Please send request with raw text: keycode=your_key or mouse=LEFT_CLICK(x,y) or mouse=RIGHT_CLICK(x,y) or mouse=MOVE(x,y)")

# Mapping of key names to Keycode values
keycode_map = {
    "A": (Keycode.A, True), "a": (Keycode.A, False),
    "B": (Keycode.B, True), "b": (Keycode.B, False),
    "C": (Keycode.C, True), "c": (Keycode.C, False),
    "D": (Keycode.D, True), "d": (Keycode.D, False),
    "E": (Keycode.E, True), "e": (Keycode.E, False),
    "F": (Keycode.F, True), "f": (Keycode.F, False),
    "G": (Keycode.G, True), "g": (Keycode.G, False),
    "H": (Keycode.H, True), "h": (Keycode.H, False),
    "I": (Keycode.I, True), "i": (Keycode.I, False),
    "J": (Keycode.J, True), "j": (Keycode.J, False),
    "K": (Keycode.K, True), "k": (Keycode.K, False),
    "L": (Keycode.L, True), "l": (Keycode.L, False),
    "M": (Keycode.M, True), "m": (Keycode.M, False),
    "N": (Keycode.N, True), "n": (Keycode.N, False),
    "O": (Keycode.O, True), "o": (Keycode.O, False),
    "P": (Keycode.P, True), "p": (Keycode.P, False),
    "Q": (Keycode.Q, True), "q": (Keycode.Q, False),
    "R": (Keycode.R, True), "r": (Keycode.R, False),
    "S": (Keycode.S, True), "s": (Keycode.S, False),
    "T": (Keycode.T, True), "t": (Keycode.T, False),
    "U": (Keycode.U, True), "u": (Keycode.U, False),
    "V": (Keycode.V, True), "v": (Keycode.V, False),
    "W": (Keycode.W, True), "w": (Keycode.W, False),
    "X": (Keycode.X, True), "x": (Keycode.X, False),
    "Y": (Keycode.Y, True), "y": (Keycode.Y, False),
    "Z": (Keycode.Z, True), "z": (Keycode.Z, False),
    "1": (Keycode.ONE, False), "!": (Keycode.ONE, True),
    "2": (Keycode.TWO, False), "@": (Keycode.TWO, True),
    "3": (Keycode.THREE, False), "#": (Keycode.THREE, True),
    "4": (Keycode.FOUR, False), "$": (Keycode.FOUR, True),
    "5": (Keycode.FIVE, False), "%": (Keycode.FIVE, True),
    "6": (Keycode.SIX, False), "^": (Keycode.SIX, True),
    "7": (Keycode.SEVEN, False), "&": (Keycode.SEVEN, True),
    "8": (Keycode.EIGHT, False), "*": (Keycode.EIGHT, True),
    "9": (Keycode.NINE, False), "(": (Keycode.NINE, True),
    "0": (Keycode.ZERO, False), ")": (Keycode.ZERO, True),
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
    # Add more key mappings as needed
}

mouse_map = {
    "LEFT_CLICK": Mouse.LEFT_BUTTON,
    "RIGHT_CLICK": Mouse.RIGHT_BUTTON,
    "MIDDLE_CLICK": Mouse.MIDDLE_BUTTON
}

def parse_coordinates(action_str):
    match = re.search(r"\((-?\d+),\s*(-?\d+)\)", action_str)
    if match:
        x = int(match.group(1))
        y = int(match.group(2))
        return x, y
    return None, None

while True:
    try:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")

        buffer = bytearray(1024)
        bytes_received = client_socket.recv_into(buffer)
        request_str = str(buffer[:bytes_received], 'utf8')
        print(f"Received: {request_str}")

        # Check if the request contains "keycode"
        if "keycode" in request_str:
            key = request_str.split("=")[1].strip()
            if key in keycode_map:
                keycode, requires_shift = keycode_map[key]
                print(f"Triggering keyboard event for key: {key}")
                if requires_shift:
                    keyboard.press(Keycode.SHIFT, keycode)
                    keyboard.release_all()
                else:
                    keyboard.press(keycode)
                    keyboard.release_all()
            else:
                print(f"Invalid key: {key}")
                
       elif "typing" in request_str:
            text = request_str.split("=")[1].strip()
            print(f"Typing text: {text}")
            keyboard_layout = KeyboardLayout.US
            for char in text:
                if char in keyboard_layout:
                    keycode = keyboard_layout[char]
                    keyboard.press(keycode)
                    keyboard.release_all()
                else:
                    print(f"Invalid character: {char}")

        # Check if the request contains "mouse"
        elif "mouse" in request_str:
            action_str = request_str.split("=")[1].strip()
            action, coords = action_str.split("(")[0].strip(), action_str.split("(")[1].strip()
            x, y = parse_coordinates(f"({coords}")

            if action in mouse_map:
                button = mouse_map[action]
                if x is not None and y is not None:
                    print(f"Triggering mouse event: {action} at x: {x}, y: {y}")
                    mouse.move(x, y)
                    mouse.click(button)
                else:
                    print(f"Triggering mouse event: {action}")
                    mouse.click(button)
            elif action == "MOVE":
                if x is not None and y is not None:
                    print(f"Moving mouse to x: {x}, y: {y}")
                    mouse.move(x, y)
                else:
                    print(f"Invalid MOVE action coordinates: {coords}")
            else:
                print(f"Invalid mouse action: {action}")

        response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK"
        client_socket.send(response.encode('utf8'))
        client_socket.close()
    except Exception as e:
        print(f"An error occurred: {e}")
        
