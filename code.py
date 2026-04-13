import board
import whitestar

class MODE:
    PRESET = 0
    TOGGLE = 1

SWITCH_MODES = {
    1: MODE.PRESET,
    2: MODE.PRESET,
    3: MODE.PRESET,
    4: MODE.PRESET,
    5: MODE.TOGGLE,
    6: MODE.TOGGLE,
}

TUNER_SWITCH = 6

MY_PINS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
ws = whitestar.Whitestar(MY_PINS)

tuner_mode = False
saved_leds = [False] * 6

def handle_preset(sw):
    for num, mode in SWITCH_MODES.items():
        if mode == MODE.PRESET:
            ws.set_led(num - 1, False)
    ws.set_led(sw, True)
    print(f"Whitestar Preset: {sw + 1}")

def handle_toggle(sw):
    ws.set_led(sw, not ws.get_led(sw))
    print(f"Whitestar Toggle {sw + 1}: {'ON' if ws.get_led(sw) else 'OFF'}")

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
    sw, hold = ws.update()

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
