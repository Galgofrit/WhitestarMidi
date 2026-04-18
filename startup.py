import time

def boot_animation(ws, flash=0.1, hold=0.7):
    # Quick flash each LED
    for i in range(ws._count):
        ws.set_led(i, True)
        end = time.monotonic() + flash
        while time.monotonic() < end:
            ws._drive()
        ws.set_led(i, False)

    # Pause — keep driving to hold pins low
    end = time.monotonic() + 0.5
    while time.monotonic() < end:
        ws._drive()

    # All on together
    for i in range(ws._count):
        ws.set_led(i, True)
    end = time.monotonic() + hold
    while time.monotonic() < end:
        ws._drive()

    # Clear
    for i in range(ws._count):
        ws.set_led(i, False)
