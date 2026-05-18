"""
config_routine.py
-----------------
Finds the ideal integration time for the AS726x sensor using binary search
on the orange channel (~610 nm), then writes the result back into configs so
that wind_up_time / wind_down_time are correct for the rest of the session.

Based on configure_as726x2() from the original config_routine.py, adapted to:
  - use the orange channel instead of yellow
  - apply the LED duty-cycle timing formula to configs on completion
  - work with the sensor object accessed via sensors.get_as726x()

Usage (called from main.py setup):
    import config_routine
    config_routine.find_ideal_integration_time(configs, led)
"""

import time
import sensors

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Orange channel saturates at ~59923; use 99.9% to handle slight jitter
ORANGE_SATURATION_VALUE = 59923 * 0.999

# Binary search bounds (integration time code, 1–255; code k → (k+1)*2.8 ms)
MIN_INTEG_CODE = 1
MAX_INTEG_CODE = 255

# Ideal integration time = this fraction of the minimum saturating code
PERCENTAGE_REDUCTION = 0.8


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def find_ideal_integration_time(configs, led):
    """
    Run binary search to find the minimum AS726x integration time code that
    saturates the orange channel, then set the ideal code to 80% of that.

    After the search:
      - sets the integration time on the sensor
      - updates configs["wind_up_time"] and configs["wind_down_time"] to
        match the found integration period (LED duty-cycle formula)

    Parameters
    ----------
    configs : dict – the shared configs dict from main.py; modified in-place
    led     : machine.Pin – LED pin, passed through to read helpers
    """
    if configs.get("sensor") != "as726x":
        print("config_routine: sensor is not as726x, skipping.")
        return

    print("config_routine: searching for ideal AS726x integration time (orange channel)...")

    ideal_code = _binary_search_saturation(configs, led)
    ideal_code = max(1, int(ideal_code * PERCENTAGE_REDUCTION))

    sensors.get_as726x().set_integration_time(ideal_code)

    # --- update wind times in configs ---
    # Integration period for this code in seconds
    integ_time_s = (ideal_code + 1) * 2.8 / 1000.0

    # Wind-up: short enough that it doesn't slow the loop, but at least one
    # integration period so the sensor has settled before we read.
    # Using the same duty-cycle formula as the original (10% of period).
    configs["wind_up_time"]   = max(integ_time_s, integ_time_s / 10.0)

    # Wind-down: allow the sensor to fully settle after LED is off
    # (3.3× the integration period, matching the original script)
    configs["wind_down_time"] = integ_time_s * 3.3

    print("config_routine: ideal integration time code = {}".format(ideal_code))
    print("config_routine: integration period          = {:.2f} ms".format(integ_time_s * 1000))
    print("config_routine: wind_up_time                = {:.4f} s".format(configs["wind_up_time"]))
    print("config_routine: wind_down_time              = {:.4f} s".format(configs["wind_down_time"]))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _binary_search_saturation(configs, led):
    """
    Binary search for the minimum integration time code whose orange-channel
    reading reaches ORANGE_SATURATION_VALUE.

    Returns the found code (int).  If the entire range is below saturation,
    returns MAX_INTEG_CODE as a safe fallback.
    """
    left  = MIN_INTEG_CODE
    right = MAX_INTEG_CODE

    while left < right:
        mid  = (left + right) // 2
        read = _read_orange_at_integ_time(configs, led, mid)

        if read >= ORANGE_SATURATION_VALUE:
            right = mid        # mid might be the minimum saturating code
        else:
            left  = mid + 1    # need a longer integration time

    # Verify the result actually saturates; if not, use MAX as fallback
    final_read = _read_orange_at_integ_time(configs, led, left)
    if final_read < ORANGE_SATURATION_VALUE:
        print("config_routine: WARNING — orange channel never saturated. "
              "Using max integration time code ({}).".format(MAX_INTEG_CODE))
        return MAX_INTEG_CODE

    return left


def _read_orange_at_integ_time(configs, led, integ_code):
    """
    Temporarily set the AS726x integration time to integ_code, apply the
    matching LED duty-cycle timing, take one reading, and return the
    orange-channel value.

    configs wind times are updated in-place for this single reading;
    the caller (find_ideal_integration_time) overwrites them again at the end.
    """
    integ_time_s = (integ_code + 1) * 2.8 / 1000.0

    # Same duty-cycle formula as the original config_routine.py
    configs["wind_up_time"]   = integ_time_s / 10.0
    configs["wind_down_time"] = integ_time_s * 3.3

    sensors.get_as726x().set_integration_time(integ_code)

    read_list = sensors.read_light(configs, led)   # returns [orange_value]
    orange_val = read_list[0]

    print("  integ_code={:3d}  orange={:.1f}".format(integ_code, orange_val))
    return orange_val