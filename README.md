
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
small control page from the `public/` folder (`index.html`, `style.css`, `app.js`):

* A text field — sends whatever you type via `typing=`.
* A square trackpad area — click for a left click, right-click for a right click,
  double-click for a double click, and dragging moves the cursor (translated into
  relative `mouse=MOVE(dx,dy)` calls).

It's plain HTML/CSS/JS with no build step, so editing it is just editing those three
files directly; `upload.sh` copies the `public/` folder to the board like everything else.


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
