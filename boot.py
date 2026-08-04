import storage

# Remount the CIRCUITPY filesystem so that code.py (CircuitPython) can WRITE
# to it (needed for ip.txt / hostname.txt / error.txt). By default this
# would make the drive READ-ONLY to the PC; disable_concurrent_write_protection
# keeps it writable from both sides. Tradeoff: if the PC and the board happen
# to write at the exact same instant, the filesystem could get corrupted.
# Acceptable here since the board only writes briefly at boot / on a fatal
# error, not continuously.
storage.remount("/", readonly=False, disable_concurrent_write_protection=True)
