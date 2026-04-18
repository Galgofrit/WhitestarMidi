import board
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import whitestar
import startup

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

TUNER_SWITCH = 6
MY_PINS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
ws = whitestar.Whitestar(MY_PINS, hold_buttons=[TUNER_SWITCH - 1])

# --- MIDI ---

def send_midi(sw, val=127):
    midi.send(ControlChange(sw, val))
    print(f"MIDI CC {sw} -> {val}")

# --- Button Handlers ---

def handle_preset(sw):
    for i in range(6):
        ws.set_led(i, False)
    ws.set_led(sw, True)
    send_midi(sw + 1)
    print(f"Whitestar Preset: {sw + 1}")

def handle_toggle(sw):
    ws.set_led(sw, not ws.get_led(sw))
    val = 127 if ws.get_led(sw) else 0
    send_midi(sw + 1, val)
    print(f"Whitestar Toggle {sw + 1}: {'ON' if ws.get_led(sw) else 'OFF'}")

# --- Tuner Mode ---

tuner_mode = False
saved_leds = [False] * 6

def enter_tuner():
    global tuner_mode, saved_leds
    tuner_mode = True
    saved_leds = [ws.get_led(i) for i in range(6)]
    for i in range(6):
        ws.set_led(i, True)
    print("Tuner Mode: ON")

def exit_tuner():
    global tuner_mode
    tuner_mode = False
    for i in range(6):
        ws.set_led(i, saved_leds[i])
    print("Tuner Mode: OFF")

def before_press(sw):
    if tuner_mode:
        exit_tuner()

# --- Register Callbacks ---

ws.on_press(1, handle_preset)
ws.on_press(2, handle_preset)
ws.on_press(3, handle_preset)
ws.on_press(4, handle_preset)
ws.on_press(5, handle_preset)
ws.on_press(6, handle_preset)

ws.on_hold(TUNER_SWITCH, enter_tuner)

ws.on_combo((4, 5), lambda a, b: (send_midi(7), print("Whitestar Virtual Button 7 (combo 4+5)")))
ws.on_combo((5, 6), lambda a, b: (send_midi(8), print("Whitestar Virtual Button 8 (combo 5+6)")))

# --- Start ---

startup.boot_animation(ws)
ws.set_led(0, True)
ws.run(before_press=before_press)
