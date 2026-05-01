import time
import digitalio
import supervisor

NETWORKS = [
    ("Test-Network", "testtest"),
]
SYNC_PORT = 8080
_mdns_server = None

def check_wifi_mode(ws):
    import os
    # Check if switch 1 (index 0) is held on boot, or if RST left a pending marker
    ws._ios[0].direction = digitalio.Direction.INPUT
    ws._ios[0].pull = digitalio.Pull.UP
    time.sleep(0.05)
    held = ws._ios[0].value == False
    pending = False
    try:
        os.stat("/wifi_pending")
        pending = True
    except OSError:
        pass
    if held or pending:
        # One-shot: remove marker so next boot is normal unless switch is held
        if pending:
            try:
                os.remove("/wifi_pending")
            except Exception:
                pass
        supervisor.runtime.autoreload = False
        import wifi
        import socketpool

        print(f"WiFi mode: trying {len(NETWORKS)} networks...")
        ws.set_led(1, True)
        blink_on = True
        last_blink = time.monotonic()

        # Give WiFi chip ~1.5s to fully init on cold boot before first attempt
        warmup_end = time.monotonic() + 1.5
        while time.monotonic() < warmup_end:
            now = time.monotonic()
            if now - last_blink >= 0.2:
                blink_on = not blink_on
                ws.set_led(1, blink_on)
                last_blink = now
            ws._drive()

        last_attempt = 0
        attempts = 0
        MAX_ATTEMPTS = 5

        while wifi.radio.ipv4_address is None:
            now = time.monotonic()
            if now - last_blink >= 0.2:
                blink_on = not blink_on
                ws.set_led(1, blink_on)
                last_blink = now
            ws._drive()
            if now - last_attempt >= 5:
                last_attempt = now
                attempts += 1
                # Full radio cycle to recover from a stuck state
                try:
                    wifi.radio.enabled = False
                    time.sleep(0.5)
                    wifi.radio.enabled = True
                    time.sleep(0.5)
                except Exception:
                    pass
                try:
                    wifi.radio.start_station()
                except Exception:
                    pass
                # Scan for visible networks
                visible = set()
                try:
                    for net in wifi.radio.start_scanning_networks():
                        visible.add(net.ssid)
                except Exception as e:
                    print(f"  scan failed: {e}")
                finally:
                    try:
                        wifi.radio.stop_scanning_networks()
                    except Exception:
                        pass
                # Try only known networks that are visible, in priority order
                for ssid, password in NETWORKS:
                    if wifi.radio.ipv4_address is not None:
                        break
                    if ssid not in visible:
                        print(f"  {ssid}: not visible")
                        continue
                    try:
                        print(f"  trying {ssid}...")
                        wifi.radio.connect(ssid, password, timeout=8)
                    except Exception as e:
                        print(f"  {ssid}: {e}")
                if wifi.radio.ipv4_address is None and attempts >= MAX_ATTEMPTS:
                    # Make sure the marker stays so we re-enter WiFi mode
                    try:
                        with open("/wifi_pending", "w"):
                            pass
                    except Exception:
                        pass
                    print("WiFi mode: stuck, hard-resetting device")
                    time.sleep(0.2)
                    import microcontroller
                    microcontroller.reset()

        print(f"WiFi mode: connected at {wifi.radio.ipv4_address}:{SYNC_PORT}")

        # Let connection settle before announcing mDNS
        time.sleep(0.5)

        # Advertise via mDNS so the device is reachable as whitestar.local.
        # Stored as a module-level reference so it isn't GC'd.
        try:
            import mdns
            global _mdns_server
            _mdns_server = mdns.Server(wifi.radio)
            _mdns_server.hostname = "whitestar"
            _mdns_server.advertise_service(service_type="_whitestar", protocol="_tcp", port=SYNC_PORT)
            print("mDNS: whitestar.local")
        except Exception as e:
            print(f"mDNS failed: {e}")

        boot_animation(ws)
        for i in range(ws._count):
            ws.set_led(i, True)

        run_sync_server(ws, wifi)

def run_sync_server(ws, wifi):
    import socketpool
    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", SYNC_PORT))
    server.listen(1)
    server.settimeout(0.05)

    buf = bytearray(1024)
    while True:
        ws._drive()
        try:
            conn, _ = server.accept()
        except OSError:
            continue
        try:
            handle(conn, buf)
        except Exception as e:
            try:
                conn.send(f"ERR {e}\n".encode())
            except Exception:
                pass
        conn.close()

def handle(conn, buf):
    conn.settimeout(5)
    header = b""
    while b"\n" not in header or header.count(b"\n") < 2:
        n = conn.recv_into(buf)
        if n == 0:
            return
        header += bytes(buf[:n])
    first, rest = header.split(b"\n", 1)
    parts = first.decode().split(" ", 1)
    cmd = parts[0]

    if cmd == "PING":
        conn.send(b"OK\n")
    elif cmd == "RST":
        # Write marker so boot stays in WiFi mode without holding switch 1
        try:
            with open("/wifi_pending", "w") as f:
                pass
        except Exception:
            pass
        conn.send(b"OK\n")
        conn.close()
        time.sleep(0.2)
        import microcontroller
        microcontroller.reset()
    elif cmd == "PUT":
        size_line, body = rest.split(b"\n", 1)
        size = int(size_line)
        path = "/" + parts[1].lstrip("/")
        f = open(path, "wb")
        try:
            f.write(body)
            written = len(body)
            while written < size:
                n = conn.recv_into(buf)
                if n == 0:
                    break
                f.write(bytes(buf[:n]))
                written += n
        finally:
            f.close()
        conn.send(f"OK {written}\n".encode())
    elif cmd == "LS":
        import os
        path = "/" + parts[1].lstrip("/") if len(parts) > 1 else "/"
        out = "\n".join(os.listdir(path)) + "\n"
        conn.send(out.encode())
    elif cmd == "CAT":
        path = "/" + parts[1].lstrip("/")
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                conn.send(chunk)
    else:
        conn.send(b"ERR unknown\n")

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
