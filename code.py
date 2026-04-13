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

MY_PINS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
ws = whitestar.Whitestar(MY_PINS)

# Starting State
ws.set_led(0, True)

while True:
    sw = ws.update()

    if sw is not None:
        sw_num = sw + 1
        if SWITCH_MODES[sw_num] == MODE.PRESET:
            # Turn off all preset switches, leave toggles alone
            for num, mode in SWITCH_MODES.items():
                if mode == MODE.PRESET:
                    ws.set_led(num - 1, False)
            ws.set_led(sw, True)
            print(f"Whitestar Preset: {sw_num}")

        elif SWITCH_MODES[sw_num] == MODE.TOGGLE:
            ws.set_led(sw, not ws.get_led(sw))
            print(f"Whitestar Toggle {sw_num}: {'ON' if ws.get_led(sw) else 'OFF'}")
