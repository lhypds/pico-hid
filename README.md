
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

The onboard LED doubles as an activity light: it lights up whenever a request
arrives and goes out shortly after, so you can tell at a glance whether the
board is receiving anything without opening the console.  


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
3. Scroll  
   `SCROLL(0,n)` — turn the wheel `n` notches; positive scrolls up.  
Note: the `x` and `y` is relative coordinate.  

* De-duplication (optional)

A command may carry a `seq=<token>&` prefix, e.g. `seq=k3f9-42&keycode=CTRL+c`.
The board skips a command whose token matches the one it just executed, so a
client that retries on a lost response (like the web UI) can't type a key
twice. Commands without the prefix always execute.  


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

Open the board's address in a browser (e.g. `http://ph-3f9a.local`). The page is
`public/index.html` — one self-contained file, no build step, CSS and JS inlined so
the board serves it in a single request.

The two buttons right of the text field pick the mode; the filled one is live.


Text Sending Mode

The default. Type in the text field and press Enter or click ↵ to send it as
`typing=`. Below that, the trackpad handles the mouse: click, right-click and
double-click do the obvious thing, dragging moves the cursor, and the scroll
wheel scrolls the target machine.

The page works from a phone or tablet too: tap to click, two-finger tap for a
right click, two-finger drag to scroll.


Keyboard Mirroring Mode

Click the keyboard button to enter it. Every key you press is then forwarded to the
target machine as a `keycode=` chord, modifiers included, and the text field turns
into a read-only display of the last key in macOS notation (`^C`, `⇧⌘A`, `⌘⌫`).
Click either button to go back to send mode.

It forwards the *physical* key rather than the character it produced, so the target
machine applies its own keyboard layout. Keys are swallowed locally, so leave by
clicking — pressing Escape sends Escape to the target. Auto-repeat from a held key
is ignored, to avoid flooding the board.

On a touch device the mode works differently: a soft keyboard doesn't report
physical keys (IMEs, swipe typing and autocorrect rewrite text without them), so
the field stays editable and whatever changes in it is forwarded live. The field
only shows the last character typed — it's a display of what was sent, not an
editor. Return sends Enter. Only characters a US layout can type are forwarded.

**Limitation: shortcuts the browser reserves can't be intercepted.** `Cmd+W`
(close tab), `Cmd+R`, `Cmd+T`, `Cmd+N`, `Cmd+Q` and `Cmd+Tab` are handled by the
browser and the OS before the page is consulted, and `preventDefault()` on them is
ignored — a deliberate security boundary, so no page-level fix exists. They are
forwarded to the target machine *and* still act on your browser, so `Cmd+W` closes
your tab as well. Two ways around it:

* Reach the page from a secure context — over HTTPS, or `localhost` via an SSH
  tunnel. The page then uses the Keyboard Lock API (plus fullscreen) and captures
  those keys properly. It engages automatically when available; over plain HTTP it
  stays off rather than forcing fullscreen for no benefit.
* Send the combination as an API call instead, e.g. `keycode=GUI+w`. A request
  isn't a keystroke, so nothing intercepts it.


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
