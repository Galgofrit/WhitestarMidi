import board
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import whitestar

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

class MODE:
    # Preset: Pressing a switch turns on its LED and turns off all other preset LEDs.
    # Toggle: Pressing a switch toggles its LED on/off without affecting other switches.
    # Can be used for every switch individually.
    PRESET = 0
    TOGGLE = 1

SWITCH_MODES = {
    1: MODE.PRESET,
    2: MODE.PRESET,
    3: MODE.PRESET,
    4: MODE.PRESET,
    5: MODE.PRESET,
    6: MODE.PRESET,
}

TUNER_SWITCH = 6

MY_PINS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
ws = whitestar.Whitestar(MY_PINS, hold_buttons=[TUNER_SWITCH - 1])

tuner_mode = False
saved_leds = [False] * 6

def send_midi(sw, val=127):
    midi.send(ControlChange(sw, val))
    print(f"MIDI CC {sw} -> {val}")

def handle_preset(sw):
    for num, mode in SWITCH_MODES.items():
        if mode == MODE.PRESET:
            ws.set_led(num - 1, False)
    ws.set_led(sw, True)
    send_midi(sw + 1)
    print(f"Whitestar Preset: {sw + 1}")

def handle_toggle(sw):
    ws.set_led(sw, not ws.get_led(sw))
    val = 127 if ws.get_led(sw) else 0
    send_midi(sw + 1, val)
    print(f"Whitestar Toggle {sw + 1}: {'ON' if ws.get_led(sw) else 'OFF'}")

COMBOS = {
    (4, 5): 7,
    (5, 6): 8,
}

def handle_combo(a, b):
    key = tuple(sorted((a + 1, b + 1)))
    if key in COMBOS:
        virt = COMBOS[key]
        send_midi(virt)
        print(f"Whitestar Virtual Button {virt} (combo {key[0]}+{key[1]})")
    else:
        print(f"Whitestar Combo: {a + 1} + {b + 1} (unmapped)")

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

# Starting State
ws.set_led(0, True)

while True:
    sw, hold, combo = ws.update()

    if combo is not None:
        handle_combo(*combo)
        continue

    if hold is not None and hold + 1 == TUNER_SWITCH and not tuner_mode:
        enter_tuner()
        continue

    if sw is not None:
        if tuner_mode:
            exit_tuner()

        sw_num = sw + 1
        if SWITCH_MODES[sw_num] == MODE.PRESET:
            handle_preset(sw)
        elif SWITCH_MODES[sw_num] == MODE.TOGGLE:
            handle_toggle(sw)
