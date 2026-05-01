import board
import digitalio
import storage
import supervisor
import time

# Check if switch 1 (GP2) is held on boot — if so, mount filesystem
# read-write for CircuitPython so the web workflow can save files.
# Side effect: USB will see the drive as read-only in this mode.
sw1 = digitalio.DigitalInOut(board.GP2)
sw1.direction = digitalio.Direction.INPUT
sw1.pull = digitalio.Pull.UP
time.sleep(0.05)

import os
wifi_pending = False
try:
    os.stat("/wifi_pending")
    wifi_pending = True
except OSError:
    pass

if sw1.value == False or wifi_pending:
    # WiFi mode: disable USB MSC so CircuitPython has full write access
    storage.disable_usb_drive()
    storage.remount("/", readonly=False)
    # Don't reload code.py when files are saved via web workflow
    supervisor.runtime.autoreload = False
else:
    # Normal mode: skip WiFi auto-connect by clearing the env vars
    import os
    try:
        os.environ.pop("CIRCUITPY_WIFI_SSID", None)
        os.environ.pop("CIRCUITPY_WIFI_PASSWORD", None)
    except Exception:
        pass

sw1.deinit()
