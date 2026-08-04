
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

3. Run `./upload.sh` to upload the code to the board.

4. Run `./reboot.sh` to reboot the board.


Monitoring
----------

Use `screen.sh` to open a serial console to the board.  
You should see it booting and connecting to WiFi.  


API Interface
-------------

Send POST request to the board (port 80 by default).  

* Keyboard  

Send with raw text: `keycode=your_key_code` to trigger key input.  
Send `typing=your_text_string` to trigger string input.  
Keycode support:  
1. Alphabet (lower/upper)  
2. Function keys, `F1` ~ `F24`  
3. Arrow Keys  
   Keycode is `UP`, `DOWN`, `LEFT`, `RIGHT`  
4. Numbers and Symbols  
5. Enter, Space, Tab key.  
   Keycode is `ENTER`, `SPACE`, `TAB`  
6. Editing and navigation  
   `ESC`, `BACKSPACE`, `DELETE`, `INSERT`, `HOME`, `END`, `PAGE_UP`, `PAGE_DOWN`,
   `CAPS_LOCK`, `PRINT_SCREEN`, `SCROLL_LOCK`, `PAUSE`, `APPLICATION`  
7. Punctuation by physical key  
   `MINUS`, `EQUALS`, `LEFT_BRACKET`, `RIGHT_BRACKET`, `BACKSLASH`, `SEMICOLON`,
   `QUOTE`, `GRAVE_ACCENT`, `COMMA`, `PERIOD`, `FORWARD_SLASH`  
8. Modifiers, for use in chords  
   `CTRL`, `SHIFT`, `ALT` (`OPTION`), `GUI` (`CMD`, `COMMAND`, `WIN`, `META`)  

Use `,` to separate keys pressed one after another, and `+` to join keys held
together as a chord.  
For example, `keycode=TAB,ENTER` triggers Tab then Enter, while `keycode=CTRL+c`
holds both at once so the target machine sees a copy shortcut. They combine:
`keycode=CTRL+c,CTRL+v`.  

An unrecognised key name cancels its whole chord rather than sending part of it,
so a typo can't leave a modifier stuck down on the target machine.  

* Mouse

Send with raw text: `mouse=mouse_event` to trigger mouse input.  
Mouse event support:  
1. Click  
   `CLICK(x,y)`, `RIGHT_CLICK(x,y)`, `DOUBLE_CLICK(x,y)`  
   Click the current position use `LEFT_CLICK(0,0)`
2. Move  
   `MOVE(x,y)`  
Note: the `x` and `y` is relative coordinate.  


Auto Movement
-------------

The board periodically jiggles the mouse every `MOUSE_MOVE_INTERVAL` seconds
(set in `settings.toml`, defaults to 30 if unset). Whether it starts on boot is
controlled by `AUTOMOVE_AUTOSTART` in `settings.toml`: `1` (or unset) starts it
automatically, `0` boots with it off. Either way it can be toggled remotely:  
Send `automove=START` to start the auto mouse movement.  
Send `automove=STOP` to stop it.  


Web UI
------

Visiting the board's address in a browser (e.g. `http://ph-3f9a.local`) serves a
small control page from `public/index.html`:

* A text field — sends whatever you type via `typing=`.
* A trackpad area — click for a left click, right-click for a right click,
  double-click for a double click, and dragging moves the cursor (translated into
  relative `mouse=MOVE(dx,dy)` calls).
* A keyboard button, right of the send button, that toggles **mirror mode**. The
  filled button is the live one: send by default, keyboard once toggled on. While
  it's on, every key you press is forwarded to the target machine as a `keycode=`
  chord including modifiers, and the text field turns into a read-only display of
  the last key. Click the button again to leave.

  Mirror mode forwards the *physical* key (`KeyboardEvent.code`), not the character
  it produced, so the target machine applies its own keyboard layout. It also
  swallows the keys locally, so `Ctrl+C` copies on the target machine rather than in
  your browser — which means browser shortcuts like reload stop working until you
  toggle back out, and you must click the button (not press a key) to exit. A few
  combinations the OS reserves for itself, such as `Cmd+Tab` or `Alt+Tab`, never
  reach the page and so can't be forwarded. Auto-repeat from a held key is ignored,
  to avoid flooding the board.

Its CSS and JS are inlined into that single file, so loading the UI costs the board
one request instead of one per asset — it serves connections one at a time, and the
extra round trips were failing under load. Plain HTML/CSS/JS with no build step, so
editing it is just editing that file; `upload.sh` copies `public/` to the board like
everything else.


Macro
-----

There is a client example code (`client/client_example.go`) written in Go language.  
You can add your own code in `main()`.  

To use it, `cd client` first, then set it up with:

`go mod init pico-hid`  
`go get github.com/joho/godotenv`  

Copy `.env.example` to `.env` and add the server URL as,  
`PICO_HID_SERVER_URL=your_server_url`  

Run it with `go run client_example.go`.  
