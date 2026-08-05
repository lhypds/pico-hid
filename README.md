
Pico HID
========


A small server running on a Raspberry Pi Pico W receives requests and simulates keyboard/mouse input to the machine connected to it. It can be used to remotely control another machine’s keyboard and mouse at the hardware level.


Dependencies
------------

CircuitPython, https://docs.circuitpython.org/en/latest/README.html  


Hardware Requirements
---------------------

<img width="320" alt="202603270045_pico" src="https://github.com/user-attachments/assets/89578cca-fda1-4f4d-8fff-52c2eebbb5e8" />

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

* Media and system keys

Send `consumer=name` to tap a media key — these go out as HID Consumer
Control usages, the channel a real keyboard's media keys use, so brightness
and volume work where a plain `F1` keycode wouldn't.  
Supported names:  
`BRIGHTNESS_UP`, `BRIGHTNESS_DOWN`, `PREV_TRACK`, `PLAY_PAUSE`, `NEXT_TRACK`,
`MUTE`, `VOLUME_UP`, `VOLUME_DOWN`, and four a Mac reads as its function-row
features: `MISSION_CONTROL`, `LAUNCHPAD`, `SPOTLIGHT`, `DICTATION`.  
Use `,` for a sequence, e.g. `consumer=VOLUME_UP,VOLUME_UP`. These don't chord
with `keycode=` modifiers — the consumer report has no room for them.  

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
4. Drag  
   `PRESS(x,y)` holds the left button down, `RELEASE(x,y)` lets it go.  
   `MOVE`s sent in between drag with the button held.  
   `DOUBLE_CLICK` sent while the button is held lands as up-down-up,  
   completing the held press into a double-click.  
Note: the `x` and `y` is relative coordinate.  

* Auto Movement

The board periodically jiggles the mouse every `MOUSE_MOVE_INTERVAL` seconds
(set in `settings.toml`, defaults to 30 if unset). Whether it starts on boot is
controlled by `AUTOMOVE_AUTOSTART` in `settings.toml`: `1` (or unset) starts it
automatically, `0` boots with it off. Either way it can be toggled remotely:  
Send `automove=START` to start the auto mouse movement.  
Send `automove=STOP` to stop it.  

* De-duplication (optional)

A command may carry a `seq=<token>&` prefix, e.g. `seq=k3f9-42&keycode=CTRL+c`.
The board skips a command whose token matches the one it just executed, so a
client that retries on a lost response (like the web UI) can't type a key
twice. Commands without the prefix always execute.  


Web UI
------

<img width="320" alt="202608050341_pico" src="https://github.com/user-attachments/assets/5c743fc2-034c-4612-ae45-af75616a891c" />

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
right click, two-finger drag to scroll. Tap and immediately touch again to
press the button right there — the grab happens at the double-click point, and
moving then drags until the finger lifts. A quick lift in place is a
double-click; holding before lifting makes it a plain press-and-release.


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

**Limitation: shortcuts the browser reserves can't be intercepted.**  

`Cmd+W` (close tab), `Cmd+R`, `Cmd+T`, `Cmd+N`, `Cmd+Q` and `Cmd+Tab` are handled by the
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


Virtual Keyboard
----------------

<img width="840" alt="202608050734_pico" src="https://github.com/user-attachments/assets/c3ae2e5d-b9b6-472d-acd3-50a16d6af349" />

`keyboard/` is a desktop window holding a full-size keyboard with a
square trackpad beside it, for driving the board from a computer instead of a
browser. The window is only those two things; everything else is behind
`Settings…` in the menu bar.

Run `./keyboard.sh`. It sets the Go module up the first time, builds the app and
starts it, and passes any arguments through — so `./keyboard.sh -url
http://ph-1234.local` works.  

To set it up by hand instead, `cd keyboard` and:

`go mod init pico-hid-keyboard`  
`go get fyne.io/fyne/v2 github.com/joho/godotenv`  
`go mod tidy`  

then `go run .`.  
The GUI is drawn through OpenGL, so building it needs a C compiler — on macOS
that means the Xcode command line tools.  

`Settings…` holds the board, the target and the pointer speed, all remembered
between runs. The board is asked for as `http://ph-` **id** `.local`, because
only the id varies: it is four hex digits of the board's CPU id, which it prints
on boot and writes to `hostname.txt` on the CIRCUITPY drive. A whole address
pasted into the field is reduced to the id, so that works too. `-url` or
`PICO_HID_SERVER_URL` in `keyboard/.env` — read the way the macro client reads
its own — can name any host instead, an IP included. With nothing set yet the window opens
the settings straight away.  

Nothing else is on screen, and there is no status display at all: a command that
fails is retried and then let go, since a keystroke that didn't land is something
you see on the target machine anyway.  

Resolving a `.local` name takes a few seconds on some networks — five, where the
router answers such queries slowly — and the board closes every connection, so
that cost would otherwise land on every keystroke. The address is looked up once
at startup, and again whenever the setting changes, then reused; only that first
lookup waits. To skip it altogether, give the board's IP instead:
`./keyboard.sh -url http://192.168.0.41`.  

* Keyboard

A full-size 104-key ANSI layout: function row, main block, navigation cluster
and numeric keypad. Keys send the *physical* key rather than the character it
would produce, so the target machine applies its own layout.  

Clicking a modifier latches it for the next key; clicking again locks it down
until clicked off, for typing a run of keys with it held.  

Keys pressed on the real keyboard are forwarded as well while the window has
focus, and the keycap they belong to is drawn held so you can see what went.
Modifiers combine as you would expect, so `Ctrl`+`c` typed for real arrives as
one chord. Key repeat is dropped rather than flooding the board, and
combinations the window manager claims first (`Cmd+Tab`, `Alt+Tab`) can't be
forwarded — click those on screen instead. Typing pauses while the settings
dialog has focus, so its own field behaves normally.  

* Target

The `Target` setting says which machine the board is plugged into, and reshapes
the board into the one that machine expects. It starts on whichever the machine
running the window is.  

On Windows it is a plain 104-key PC layout. On macOS:

- The two caps either side of the space bar become `⌥` and `⌘`, in the order a
  Mac really has them.
- The `menu` key becomes `fn`, as on Apple's full-size keyboard.
- `prtsc` / `scrlk` / `pause` become `F13`-`F15`, and `F16`-`F19` appear above
  the keypad — the keys Apple puts in those positions.

* fn (macOS target only)

`fn` latches like a modifier — once for the next key, twice to lock — but acts
only on the window: nothing is sent for fn itself, since Apple's fn never
leaves the keyboard as a normal HID key. While it is latched the function row
takes on Apple's printed features and sends them as `consumer=` media codes:
brightness on `F1`/`F2`, Mission Control on `F3`, Spotlight on `F4`, Dictation
on `F5`, media and volume on `F7`-`F12`. `F6` stays `F6`: its Focus feature has
no code a third-party keyboard can send.  

* Num

`Num` acts only on the window. The API has no keypad key names, so it picks
whether the keypad sends digits or the navigation keys printed on its faces,
which is what Num Lock chooses between on a real board.  

* Trackpad

The gestures are the web UI's: dragging moves the pointer, click, right-click
and double-click do the obvious thing, and the wheel scrolls the target machine.  

To drag something *on* the target rather than just move the pointer over it,
click and then press again straight away, as you would to double-click, but keep
the button down and move: the second press grabs and holds, and lifting lets go.
Lifting quickly without moving completes the double-click instead. It is the same
gesture the page uses from a touchscreen, which is where it comes from.  


Macro
-----

There is a client example code (`client/client_example.go`) written in Go language.  
You can add your own code in `main()`.  

It is a Go module of its own, separate from the desktop app. To use it,
`cd client` first, then set it up with:

`go mod init pico-hid`  
`go get github.com/joho/godotenv`  

Copy `.env.example` to `.env` and add the server URL as,  
`PICO_HID_SERVER_URL=your_server_url`  

Run it with `go run client_example.go`.  
