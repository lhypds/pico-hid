import storage

# Remount the CIRCUITPY filesystem so that code.py (CircuitPython) can WRITE
# to it. Side effect: while this is active the drive is READ-ONLY to the PC,
# so you cannot drag-drop files to update the board. Update code.py over the
# serial REPL, or temporarily rename/remove this file to edit from the PC.
storage.remount("/", readonly=False)
