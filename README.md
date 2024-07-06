
Pico HID Keyboard
=================


A small server running on Raspberry Pi Pico W, receive requests and simulate keyborad/mouse input to the machine connected to it.


Dependencies
------------

CircuitPython, https://docs.circuitpython.org/en/latest/README.html  


Hardware Requirements
---------------------

1. Raspberry Pi Pico W  
2. USB cable (micro USB -> USB-A or USB-C)  


Setup
-----

1. Setup the CricuitPython for Raspberry Pi Pico W.  
   Press and hold the button on the Pico, connect to PC/Macbook
   Drag-and-drop the [.uf2 file](https://circuitpython.org/board/raspberry_pi_pico_w/) to the `RPI-RP2` drive.
   It will auto reboot with a CircultPython environment.

2. Copy `lib`, `code.py`, in `settings.toml` setup WiFi SSID and password, copy them to the board.
   Re-power it.

Done.  


How To Use
----------

Scan the local network, and find the Pico board IP.  
Send POST request to the board IP, port 8080.  

* Keyboard  

Send with raw text: `keycode=your_key_code` to trigger key input.  

Keycode support:  
1. Alphabet (lower/upper)
2. Function keys, `F1` ~ `F12`
3. Arrow Keys
   Keycode is `UP`, `DOWN`, `LEFT`, `RIGHT`
4. Numbers and Symbols

* Mouse

Send with raw text: `mouse=mouse_event` to trigger mouse input.  

Mouse event support:  
1. Click  
   `LEFT_CLICK(x,y)`, `RIGHT_CLICK(x,y)`, `MIDDLE_CLICK(x,y)`  
   Click the current position use `LEFT_CLICK(0,0)`
2. Move  
   `MOVE(x,y)`  
Note: the `x` and `y` is relative coordinate.  