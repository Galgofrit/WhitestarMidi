import time
import digitalio

HOLD_TIME = 0.8    # seconds
COMBO_TIME = 0.05  # seconds — window for simultaneous press detection
LED_SLOT = 0.0015  # seconds per LED — fixed slot time, brightness sets the duty cycle within it

class Whitestar:
    def __init__(self, pins, hold_buttons=None):
        self._ios = []
        self._states = [False] * len(pins)
        self._last_vals = [True] * len(pins)
        self._last_debounce = [0] * len(pins)
        self._press_start = [0] * len(pins)
        self._hold_fired = [False] * len(pins)
        self._pending_press = None
        self._pending_time = 0
        self._hold_buttons = set(hold_buttons or [])
        self._combo_consumed = [False] * len(pins)
        self._count = len(pins)

        self._press_handlers = {}
        self._hold_handlers = {}
        self._combo_handlers = {}

        for p in pins:
            io = digitalio.DigitalInOut(p)
            io.direction = digitalio.Direction.INPUT
            io.pull = None
            self._ios.append(io)

    def set_led(self, index, val):
        # val: True/False or float 0.0–1.0 for brightness
        if val is True:
            self._states[index] = 1.0
        elif val is False:
            self._states[index] = 0.0
        else:
            self._states[index] = max(0.0, min(1.0, val))

    def get_led(self, index):
        return self._states[index] > 0

    def on_press(self, sw_num, handler):
        self._press_handlers[sw_num] = handler

    def on_hold(self, sw_num, handler):
        self._hold_handlers[sw_num] = handler

    def on_combo(self, pair, handler):
        self._combo_handlers[tuple(sorted(pair))] = handler

    def _drive(self):
        for i in range(self._count):
            self._ios[i].direction = digitalio.Direction.OUTPUT
            on_time = LED_SLOT * self._states[i]
            if on_time > 0:
                self._ios[i].value = True
                time.sleep(on_time)
                self._ios[i].value = False
            time.sleep(LED_SLOT - on_time)

    def _scan(self):
        new_press = None
        new_hold = None
        combo = None
        release_press = None

        for i in range(self._count):
            # --- 1. SENSE ---
            self._ios[i].direction = digitalio.Direction.INPUT
            self._ios[i].pull = digitalio.Pull.UP

            current_val = self._ios[i].value
            now = time.monotonic()

            # Falling edge — button just pressed
            if current_val == False and self._last_vals[i] == True:
                if (now - self._last_debounce[i]) > 0.15:
                    new_press = i
                    self._press_start[i] = now
                    self._hold_fired[i] = False
                    self._last_debounce[i] = now

            # Still held — check for hold threshold
            if current_val == False and not self._hold_fired[i] and self._press_start[i] > 0:
                if (now - self._press_start[i]) >= HOLD_TIME:
                    new_hold = i
                    self._hold_fired[i] = True

            # Released — fire press on release for hold buttons (if hold didn't fire)
            if current_val == True and self._press_start[i] > 0:
                if i in self._hold_buttons and not self._hold_fired[i] and not self._combo_consumed[i]:
                    release_press = i
                self._press_start[i] = 0
                self._hold_fired[i] = False
                self._combo_consumed[i] = False

            self._last_vals[i] = current_val

            # --- 2. DRIVE / GHOST KILL ---
            self._ios[i].direction = digitalio.Direction.OUTPUT
            on_time = LED_SLOT * self._states[i]
            if on_time > 0:
                self._ios[i].value = True
                time.sleep(on_time)
                self._ios[i].value = False
            time.sleep(LED_SLOT - on_time)

        # Combo detection
        if new_press is not None:
            if self._pending_press is not None:
                combo = (self._pending_press, new_press)
                self._combo_consumed[self._pending_press] = True
                self._combo_consumed[new_press] = True
                self._pending_press = None
                new_press = None
            else:
                self._pending_press = new_press
                self._pending_time = time.monotonic()
                new_press = None

        if self._pending_press is not None and combo is None:
            if (time.monotonic() - self._pending_time) >= COMBO_TIME:
                # Hold buttons only fire on release, not here
                if self._pending_press in self._hold_buttons:
                    self._pending_press = None
                else:
                    new_press = self._pending_press
                    self._pending_press = None

        # Release press bypasses combo buffer
        if release_press is not None and new_press is None:
            new_press = release_press

        return new_press, new_hold, combo

    def run(self, before_press=None):
        while True:
            sw, hold, combo = self._scan()

            if combo is not None:
                key = tuple(sorted((combo[0] + 1, combo[1] + 1)))
                if key in self._combo_handlers:
                    self._combo_handlers[key](*combo)
                continue

            if hold is not None:
                sw_num = hold + 1
                if sw_num in self._hold_handlers:
                    self._hold_handlers[sw_num]()
                continue

            if sw is not None:
                if before_press:
                    before_press(sw)

                sw_num = sw + 1
                if sw_num in self._press_handlers:
                    self._press_handlers[sw_num](sw)
