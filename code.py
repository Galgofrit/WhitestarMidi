import board
import busio
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
import whitestar
import startup

uart = busio.UART(tx=board.GP0, baudrate=31250)
midi_usb = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
midi_trs = adafruit_midi.MIDI(midi_out=uart, out_channel=0)

TUNER_SWITCH = 6
MY_PINS = [board.GP2, board.GP3, board.GP4, board.GP5, board.GP6, board.GP7]
ws = whitestar.Whitestar(MY_PINS, hold_buttons=[TUNER_SWITCH - 1])

# --- MIDI ---

def midi_send(msg):
    midi_usb.send(msg)
    midi_trs.send(msg)

def send_midi(sw, val=127):
    midi_send(ControlChange(sw, val))
    print(f"MIDI CC {sw} -> {val}")

# --- Button Handlers ---

SCENE_CC = 43
PAGE_CC = 64
SCENE_NAMES = ["A(I)", "B(I)", "C(I)", "D(I)", "A(II)", "B(II)", "C(II)", "D(II)"]

def handle_scene(sw):
    for i in range(6):
        ws.set_led(i, False)
    ws.set_led(sw, True)
    midi_send(ControlChange(SCENE_CC, sw))
    page_val = 127 if sw >= 4 else 0
    midi_send(ControlChange(PAGE_CC, page_val))
    print(f"Whitestar Scene {SCENE_NAMES[sw]}")

def handle_toggle(sw):
    ws.set_led(sw, not ws.get_led(sw))
    val = 127 if ws.get_led(sw) else 0
    send_midi(sw + 1, val)
    print(f"Whitestar Toggle {sw + 1}: {'ON' if ws.get_led(sw) else 'OFF'}")

# --- Tuner Mode ---

tuner_mode = False
saved_leds = [False] * 6

TUNER_CC = 45

def enter_tuner():
    global tuner_mode, saved_leds
    tuner_mode = True
    saved_leds = [ws.get_led(i) for i in range(6)]
    for i in range(6):
        ws.set_led(i, False)
    midi_send(ControlChange(TUNER_CC, 127))
    print("Tuner Mode: ON")

def exit_tuner():
    global tuner_mode
    tuner_mode = False
    for i in range(6):
        ws.set_led(i, saved_leds[i])
    midi_send(ControlChange(TUNER_CC, 0))
    print("Tuner Mode: OFF")

def before_press(sw):
    if tuner_mode:
        exit_tuner()

# --- Register Callbacks ---

ws.on_press(1, handle_scene)
ws.on_press(2, handle_scene)
ws.on_press(3, handle_scene)
ws.on_press(4, handle_scene)
ws.on_press(5, handle_scene)
ws.on_press(6, handle_scene)

ws.on_hold(TUNER_SWITCH, enter_tuner)

def handle_combo_scene(sw_a, sw_b, scene_val):
    for i in range(6):
        ws.set_led(i, False)
    ws.set_led(sw_a, True)
    ws.set_led(sw_b, True)
    midi_send(ControlChange(SCENE_CC, scene_val))
    midi_send(ControlChange(PAGE_CC, 127))
    print(f"Whitestar Scene {SCENE_NAMES[scene_val]}")

ws.on_combo((4, 5), lambda a, b: handle_combo_scene(a, b, 6))
ws.on_combo((5, 6), lambda a, b: handle_combo_scene(a, b, 7))

# --- Start ---

startup.boot_animation(ws)
ws.set_led(0, True)
ws.run(before_press=before_press)
