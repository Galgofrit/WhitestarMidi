import time
import digitalio

HOLD_TIME = 0.8   # seconds
COMBO_TIME = 0.05 # seconds — window for simultaneous press detection

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

        for p in pins:
            io = digitalio.DigitalInOut(p)
            io.direction = digitalio.Direction.INPUT
            io.pull = None
            self._ios.append(io)

    def set_led(self, index, val):
        """Set the internal state for an LED (True/False)"""
        self._states[index] = val

    def get_led(self, index):
        return self._states[index]

    def update(self):
        """
        Processes one full cycle of the matrix.
        Returns (press, hold, combo):
            press - index of a newly pressed switch, or None
            hold  - index of a newly held switch, or None
            combo - tuple (a, b) of two simultaneously pressed switches, or None
        """
        new_press = None
        new_hold = None
        combo = None

        for i in range(len(self._ios)):
            # --- 1. SENSE ---
            self._ios[i].direction = digitalio.Direction.INPUT
            self._ios[i].pull = digitalio.Pull.UP

            # Raw read
            current_val = self._ios[i].value
            now = time.monotonic()

            # Falling edge — button just pressed
            if current_val == False and self._last_vals[i] == True:
                if (now - self._last_debounce[i]) > 0.15:
                    if i not in self._hold_buttons:
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
                if i in self._hold_buttons and not self._hold_fired[i]:
                    new_press = i
                self._press_start[i] = 0
                self._hold_fired[i] = False

            self._last_vals[i] = current_val

            # --- 2. DRIVE / GHOST KILL ---
            if self._states[i]:
                self._ios[i].direction = digitalio.Direction.OUTPUT
                self._ios[i].value = True
                # Essential pulse time for brightness
                time.sleep(0.003)
            else:
                self._ios[i].direction = digitalio.Direction.OUTPUT
                self._ios[i].value = False # Active Grounding

        # Combo detection: buffer presses and check for a second within COMBO_TIME
        if new_press is not None:
            if self._pending_press is not None:
                # Second press within window — combo
                combo = (self._pending_press, new_press)
                self._pending_press = None
                new_press = None
            else:
                # Buffer this press
                self._pending_press = new_press
                self._pending_time = time.monotonic()
                new_press = None

        # Flush pending press if combo window expired
        if self._pending_press is not None and combo is None:
            if (time.monotonic() - self._pending_time) >= COMBO_TIME:
                new_press = self._pending_press
                self._pending_press = None

        return new_press, new_hold, combo
