import time
import digitalio

class Whitestar:
    def __init__(self, pins):
        self._ios = []
        self._states = [False] * len(pins)
        self._last_vals = [True] * len(pins)
        self._last_debounce = [0] * len(pins)

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
        Returns the index of a newly pressed switch, or None.
        """
        new_press = None

        for i in range(len(self._ios)):
            # --- 1. SENSE ---
            self._ios[i].direction = digitalio.Direction.INPUT
            self._ios[i].pull = digitalio.Pull.UP

            # Raw read
            current_val = self._ios[i].value

            # Edge detection
            if current_val == False and self._last_vals[i] == True:
                if (time.monotonic() - self._last_debounce[i]) > 0.15:
                    new_press = i
                    self._last_debounce[i] = time.monotonic()

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

        return new_press
