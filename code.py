# Test version - pressing switches toggles LEDs on/off, with debounce and ghost-kill
import board
import digitalio
import time

# --- CONFIGURATION ---
# The pins connected to breakout Pins 1 through 6
# Adjust this list if you wired them to different GP numbers
SWITCH_PINS = [
    board.GP2, board.GP3, board.GP4, 
    board.GP5, board.GP6, board.GP7
]

# --- INITIALIZATION ---
switches = []
led_states = [False] * len(SWITCH_PINS)
last_values = [True] * len(SWITCH_PINS)
last_debounce = [0] * len(SWITCH_PINS)

for pin in SWITCH_PINS:
    sw = digitalio.DigitalInOut(pin)
    sw.direction = digitalio.Direction.INPUT
    sw.pull = None # Start floating to be safe
    switches.append(sw)

print("--- Tres 3.0: High-Performance Multiplexing ---")
print(f"Monitoring {len(SWITCH_PINS)} switches. Common Cathode on Pin 7.")

while True:
    for i in range(len(SWITCH_PINS)):
        # --- 1. THE SWITCH READ PHASE ---
        # Briefly flip to Input with Pull-Up to check for a ground-press
        switches[i].direction = digitalio.Direction.INPUT
        switches[i].pull = digitalio.Pull.UP
        
        # Give the voltage a micro-moment to settle before reading
        current_val = switches[i].value
        
        # Detect Falling Edge (Pressing the button)
        if current_val == False and last_values[i] == True:
            # 200ms Non-blocking debounce
            if (time.monotonic() - last_debounce[i]) > 0.2:
                led_states[i] = not led_states[i]
                print(f"Button {i+1} toggled: {'ON' if led_states[i] else 'OFF'}")
                last_debounce[i] = time.monotonic()
        
        last_values[i] = current_val

        # --- 2. THE LED DRIVE / GHOST KILL PHASE ---
        if led_states[i]:
            # LED ON: Drive high (3.3V)
            switches[i].direction = digitalio.Direction.OUTPUT
            switches[i].value = True
            # Brightness Control: How long the LED stays 'on' per cycle
            time.sleep(0.003) 
        else:
            # LED OFF: Drive Low (0V) to kill the 'ghost' glow
            switches[i].direction = digitalio.Direction.OUTPUT
            switches[i].value = False
            # We don't need a sleep here; we want to get back to reading fast
            
    # Small master delay to keep the Pico from running 'too' hot
    time.sleep(0.001)
