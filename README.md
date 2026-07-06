
Pico HID
========


A small server running on a Raspberry Pi Pico W receives requests and simulates keyboard/mouse input to the machine connected to it. It can be used to remotely control another machine’s keyboard and mouse at the hardware level.


Dependencies
------------

CircuitPython, https://docs.circuitpython.org/en/latest/README.html  


Hardware Requirements
---------------------

1. Raspberry Pi Pico W  
2. USB cable (micro USB to USB-A/C to connect to PC)  


Setup
-----

1. Setup the CricuitPython for Raspberry Pi Pico W.  
   Press and hold the button on the Pico, connect to PC/Macbook
   Drag-and-drop the [.uf2 file](https://circuitpython.org/board/raspberry_pi_pico_w/) to the `RPI-RP2` drive.
   It will auto reboot with a CircultPython environment.

2. Copy `lib`, `code.py`, and `boot.py` to the board.  
   Copy `settings.toml.example` to `settings.toml` and set your WiFi SSID and password.  
   Optionally set `MDNS_HOSTNAME` to give this board a friendly name (see below).  

Re-power it (a full power-cycle, not a soft reload — `boot.py` only runs at hard reset).  
Done.  


Finding the board's address
---------------------------

You no longer need to scan the local network. Two options are provided:

* **`myip.txt`** — on every boot the board writes its address to `myip.txt` on the
  `CIRCUITPY` drive. Open the drive on your PC to read it, e.g.:

  ```
  http://192.168.1.42:8080
  http://pico-hid-3f9a.local:8080
  ```

  This requires `boot.py`, which remounts the filesystem so the board can write to it.
  Side effect: while `boot.py` is present the drive is **read-only from the PC**, so you
  cannot drag-drop files to update `code.py`. To edit code later, use the serial REPL or
  temporarily remove `boot.py`.

* **mDNS** — the board advertises itself so you can reach it at a fixed `.local` name
  regardless of the DHCP-assigned IP, e.g. `http://pico-hid-3f9a.local:8080`.

  Each board must have a unique name or multiple devices collide. By default the name is
  `pico-hid-XXXX`, where `XXXX` is derived from the board's hardware UID (stable per board).
  Set `MDNS_HOSTNAME` in `settings.toml` to override it with a friendly name, e.g.
  `MDNS_HOSTNAME=pico-livingroom` → reachable at `pico-livingroom.local:8080`.


API Interface
-------------

Find the board's address (see "Finding the board's address" above) — either its IP
from `myip.txt` or its `.local` mDNS name.  
Send POST request to the board, port 8080.  

* Keyboard  

Send with raw text: `keycode=your_key_code` to trigger key input.  
Send `typing=your_text_string` to trigger string input.  
Keycode support:  
1. Alphabet (lower/upper)  
2. Function keys, `F1` ~ `F12`  
3. Arrow Keys  
   Keycode is `UP`, `DOWN`, `LEFT`, `RIGHT`  
4. Numbers and Symbols  
5. Enter, Space, Tab key.  
   Keycode is `ENTER`, `SPACE`, `TAB`  

Use the `,` to separate keys.  
For example, `keycode=TAB,ENTER` will trigger Tab key then Enter key.  

* Mouse

Send with raw text: `mouse=mouse_event` to trigger mouse input.  
Mouse event support:  
1. Click  
   `CLICK(x,y)`, `RIGHT_CLICK(x,y)`, `DOUBLE_CLICK(x,y)`  
   Click the current position use `LEFT_CLICK(0,0)`
2. Move  
   `MOVE(x,y)`  
Note: the `x` and `y` is relative coordinate.  


Client Code
-----------

There is a client example code (`client.go`) written in Go language.  
You can add your own code in `main()`.  

To use it first setup with:

`go mod init pico-hid`  
`go get github.com/joho/godotenv`  

Add server URL in `.env` as,  
`PICO_HID_SERVER_URL=your_server_url`  

Run it with `go run client_example.go`.  
