
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

1. Setup the CircuitPython for Raspberry Pi Pico W.  
   Refer `circuitpython_install/README.md`.

2. Copy `settings.toml.example` to `settings.toml`, set your WiFi SSID and password.  

3. Run `./upload.sh`. It collects everything the board needs — `code.py`, `boot.py`,
   `lib/`, and your `settings.toml` — into `upload-to-board/`. Copy that folder's
   contents onto the `CIRCUITPY` drive.  

Use `screen.sh` to open a serial console to the board.  
You should see it booting and connecting to WiFi.  

Re-power it (a full power-cycle, not a soft reload — `boot.py` only runs at hard reset).  
Done.  


Finding the board's address
---------------------------

You no longer need to scan the local network. Two options are provided:

* **`myip.txt` / `myhostname.txt`** — on every boot the board writes its address to
  these files on the `CIRCUITPY` drive. Open the drive on your PC to read them, e.g.:

  ```
  myip.txt:       192.168.1.42
  myhostname.txt: pico-hid-3f9a.local
  ```

  This requires `boot.py`, which remounts the filesystem so the board can write to it,
  while keeping the drive writable from the PC too (`disable_concurrent_write_protection`).
  There's a small theoretical risk of filesystem corruption if the PC and the board both
  write at the exact same instant, but the board only writes briefly at boot / on a fatal
  error, so in practice this is safe.

* **mDNS** — the board advertises itself so you can reach it at a fixed `.local` name
  regardless of the DHCP-assigned IP, e.g. `http://pico-hid-3f9a.local`.

  Each board must have a unique name or multiple devices collide. By default the name is
  `pico-hid-XXXX`, where `XXXX` is derived from the board's hardware UID (stable per board).
  Set `MDNS_HOSTNAME` in `settings.toml` to override it with a friendly name, e.g.
  `MDNS_HOSTNAME=pico-livingroom` → reachable at `pico-livingroom.local`.

  The server listens on port `80`, so no port is needed in the URL.

If WiFi fails to connect, or another fatal startup/runtime error occurs, the board
writes a description of it to `error.txt` on the `CIRCUITPY` drive. It's cleared at
the start of every boot, so a stale `error.txt` from a previous run never lingers.


API Interface
-------------

Send POST request to the board (port 80 by default).  

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

* Auto Movement

The board periodically jiggles the mouse every `MOUSE_MOVE_INTERVAL` seconds
(set in `settings.toml`, defaults to 30 if unset). Whether it starts on boot is
controlled by `AUTOMOVE_AUTOSTART` in `settings.toml`: `1` (or unset) starts it
automatically, `0` boots with it off. Either way it can be toggled remotely:  
Send `automove=START` to start the auto mouse movement.  
Send `automove=STOP` to stop it.  


Web UI
------

Visiting the board's address in a browser (e.g. `http://pico-hid-3f9a.local`) serves a
small control page from the `public/` folder (`index.html`, `style.css`, `app.js`):

* A text field — sends whatever you type via `typing=`.
* A square trackpad area — click for a left click, right-click for a right click,
  double-click for a double click, and dragging moves the cursor (translated into
  relative `mouse=MOVE(dx,dy)` calls).

It's plain HTML/CSS/JS with no build step, so editing it is just editing those three
files directly; `upload.sh` copies the `public/` folder to the board like everything else.


Client Code
-----------

There is a client example code (`client/client_example.go`) written in Go language.  
You can add your own code in `main()`.  

To use it, `cd client` first, then set it up with:

`go mod init pico-hid`  
`go get github.com/joho/godotenv`  

Copy `.env.example` to `.env` and add the server URL as,  
`PICO_HID_SERVER_URL=your_server_url`  

Run it with `go run client_example.go`.  
