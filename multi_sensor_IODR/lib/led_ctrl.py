"""
led.py
------
LED control abstraction for the IODR MicroPython project.

Two kinds of LEDs are handled here:
  * Tube LEDs    - NeoPixel (WS2812) LEDs, one per test tube.
  * Built-in LED - a plain GPIO-driven LED on the board.

All LED hardware configuration (pins, which NeoPixels are in use, and the
colour intensities used when the tube LEDs are on) lives in the constants
below, so no other module needs to know how the LEDs are wired.
Pin numbers and NeoPixel indices are imported from manual_config.py;
colour intensities are defined in this file.

Usage:
    import led as led_ctrl
    led_ctrl.set_tube_leds(led_ctrl.LED_ON)
    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)
"""

import machine
import neopixel

from manual_config import (NUM_NP_LEDS, NP_PIN_NUM, NP_IDX,
                           BUILTIN_LED_PIN_NUM) 

# ---------------------------------------------------------------------------
# On / off commands
# ---------------------------------------------------------------------------
LED_ON  = 1
LED_OFF = 0

# ---------------------------------------------------------------------------
# Tube LED configuration
# ---------------------------------------------------------------------------

# Colour intensities (R, G, B), each 0-255, applied to every tube LED when ON.
# (255, 0, 0) = max brightness red, matching the ideal wavelengths for the as726x.
TUBE_LED_COLOR     = (255, 0, 0)
TUBE_LED_OFF_COLOR = (0, 0, 0)

# ---------------------------------------------------------------------------
# Hardware objects (module-level so every importer shares the same instances)
# ---------------------------------------------------------------------------
_np_led      = neopixel.NeoPixel(machine.Pin(NP_PIN_NUM), NUM_NP_LEDS)
_builtin_led = machine.Pin(BUILTIN_LED_PIN_NUM, machine.Pin.OUT)   # builtin led


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------
def set_tube_leds(state):
    """
    Turn the LED in each tube on or off.

    state : truthy -> every NeoPixel in NP_IDX is set to TUBE_LED_COLOR
            falsy  -> every NeoPixel in NP_IDX is turned off
    """
    color = TUBE_LED_COLOR if state else TUBE_LED_OFF_COLOR
    for np_idx_num in NP_IDX:
        _np_led[np_idx_num] = color
    _np_led.write()


def set_builtin_led(state):
    """
    Turn the built-in LED on or off.

    state : truthy -> on, falsy -> off
    """
    _builtin_led.value(LED_ON if state else LED_OFF)