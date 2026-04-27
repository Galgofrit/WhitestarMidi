import time
import digitalio
import supervisor

def check_wifi_mode(ws):
    # Check if switch 1 (index 0) is held on boot
    ws._ios[0].direction = digitalio.Direction.INPUT
    ws._ios[0].pull = digitalio.Pull.UP
    time.sleep(0.05)
    if ws._ios[0].value == False:
        # Disable auto-reload so saving files doesn't kick us out of WiFi mode
        supervisor.runtime.autoreload = False
        import wifi

        print("WiFi mode: waiting for auto-connect...")

        # Blink LED 2 while waiting for auto-connect
        ws.set_led(1, True)
        blink_on = True
        blink_interval = 0.2
        last_blink = time.monotonic()

        while wifi.radio.ipv4_address is None:
            now = time.monotonic()
            if now - last_blink >= blink_interval:
                blink_on = not blink_on
                ws.set_led(1, blink_on)
                last_blink = now
            ws._drive()
            time.sleep(0.01)

        ip = str(wifi.radio.ipv4_address)
        print(f"WiFi mode: connected at http://{ip}")

        # Connected — reuse boot animation, then hold all on
        boot_animation(ws)
        for i in range(ws._count):
            ws.set_led(i, True)

        # Stay here — web workflow runs in background. Yield to network stack.
        while True:
            ws._drive()
            time.sleep(0.01)

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
