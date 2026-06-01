"""
config_routine.py
-----------------
Finds the ideal integration time for the AS726x sensor using binary search
on the orange channel (~610 nm).

Two modes:
  * find_ideal_integration_time(configs, led)
      Single-sensor calibration (original behaviour).

  * find_ideal_integration_time_multi(configs, led, sensor_list, mux, channels)
      Multi-sensor calibration via an I2C MUX. Picks the integration time
      such that the BRIGHTEST sensor just reaches the saturation threshold,
      then backs off by PERCENTAGE_REDUCTION so no tube ever saturates.
      Every dimmer tube ends up with proportionally more headroom.

Both modes update configs["wind_up_time"] and configs["wind_down_time"]
using the same LED duty-cycle formula as the original config_routine.
"""

import time
import sensors

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Orange channel saturates at ~59923; use 99.9% to handle slight jitter
ORANGE_SATURATION_VALUE = 59923 * 0.999

# Ideal integration time = this fraction of the minimum saturating code,
# so even the brightest tube sits at ~80% of full-scale on its blank.
PERCENTAGE_REDUCTION = 0.8

# Binary search bounds (integration time code, 1-255; code k -> (k+1)*2.8 ms)
MIN_INTEG_CODE = 1
MAX_INTEG_CODE = 255


# ---------------------------------------------------------------------------
# Public entry point: single-sensor (unchanged)
# ---------------------------------------------------------------------------
def find_ideal_integration_time(configs, led):
    """Original single-sensor calibration. See module docstring."""
    if configs.get("sensor") != "as726x":
        print("config_routine: sensor is not as726x, skipping.")
        return

    print("config_routine: searching for ideal AS726x integration time "
          "(single sensor, orange channel)...")

    ideal_code = _binary_search_saturation_single(configs, led)
    ideal_code = max(1, int(ideal_code * PERCENTAGE_REDUCTION))

    _apply_integration_code(configs, ideal_code, sensors_to_update=None)


# ---------------------------------------------------------------------------
# Public entry point: multi-sensor via MUX
# ---------------------------------------------------------------------------
def find_ideal_integration_time_multi(configs, led, sensor_list,
                                      mux=None, channels=None):
    """
    Calibrate integration time so that the BRIGHTEST sensor in sensor_list
    just reaches the saturation threshold. The result is then reduced by
    PERCENTAGE_REDUCTION (80%) so no tube ever saturates -- every dimmer
    tube gets even more headroom proportionally.

    Parameters
    ----------
    configs     : dict        - shared configs dict; modified in-place
    led         : machine.Pin - shared LED pin (parallel-wired across tubes)
    sensor_list : list        - list of AS726x sensor objects (one per tube).
                                These can be raw QwiicAS726x instances or
                                MuxedSensor proxies; if they're MuxedSensor
                                proxies the mux/channels args are optional.
    mux         : optional    - QwiicTCA9548A instance, used only if the
                                sensors aren't already MUX-aware proxies.
    channels    : optional    - iterable of MUX channels matching sensor_list,
                                used only if mux is provided.
    """
    if configs.get("sensor") != "as726x":
        print("config_routine: sensor is not as726x, skipping.")
        return

    if not sensor_list:
        print("config_routine: empty sensor_list, nothing to calibrate.")
        return

    print("config_routine: searching for ideal AS726x integration time "
          "across {} sensors (brightest-wins, orange channel)...".format(
              len(sensor_list)))

    ideal_code = _binary_search_saturation_multi(
        configs, led, sensor_list, mux, channels
    )
    ideal_code = max(1, int(ideal_code * PERCENTAGE_REDUCTION))

    _apply_integration_code(configs, ideal_code,
                            sensors_to_update=sensor_list)


# ---------------------------------------------------------------------------
# Apply the chosen integration code + wind times
# ---------------------------------------------------------------------------
def _apply_integration_code(configs, ideal_code, sensors_to_update):
    """
    Push ideal_code to the sensor(s) and update wind times in configs.
    If sensors_to_update is None, falls back to sensors.get_as726x().
    """
    integ_time_s = (ideal_code + 1) * 2.8 / 1000.0

    if sensors_to_update is None:
        sensors.get_as726x().set_integration_time(ideal_code)
    else:
        for s in sensors_to_update:
            s.set_integration_time(ideal_code)

    # LED duty-cycle formula (matches original config_routine)
    configs["wind_up_time"]   = integ_time_s / 10.0
    configs["wind_down_time"] = integ_time_s * 3.3

    print("config_routine: ideal integration time code = {}".format(ideal_code))
    print("config_routine: integration period          = {:.2f} ms".format(
        integ_time_s * 1000))
    print("config_routine: wind_up_time                = {:.4f} s".format(
        configs["wind_up_time"]))
    print("config_routine: wind_down_time              = {:.4f} s".format(
        configs["wind_down_time"]))


# ---------------------------------------------------------------------------
# Binary search: single sensor (original logic)
# ---------------------------------------------------------------------------
def _binary_search_saturation_single(configs, led):
    left, right = MIN_INTEG_CODE, MAX_INTEG_CODE

    while left < right:
        mid  = (left + right) // 2
        read = _read_orange_at_integ_time_single(configs, led, mid)
        if read >= ORANGE_SATURATION_VALUE:
            right = mid
        else:
            left = mid + 1

    final_read = _read_orange_at_integ_time_single(configs, led, left)
    if final_read < ORANGE_SATURATION_VALUE:
        print("config_routine: WARNING -- orange channel never saturated. "
              "Using max integration time code ({}).".format(MAX_INTEG_CODE))
        return MAX_INTEG_CODE
    return left


def _read_orange_at_integ_time_single(configs, led, integ_code):
    integ_time_s = (integ_code + 1) * 2.8 / 1000.0
    configs["wind_up_time"]   = max(integ_time_s, integ_time_s / 10.0)
    configs["wind_down_time"] = integ_time_s * 3.3

    sensors.get_as726x().set_integration_time(integ_code)

    read_list  = sensors.read_light(configs, led)   # [orange_value]
    orange_val = read_list[0]

    print("  integ_code={:3d}  orange={:.1f}".format(integ_code, orange_val))
    return orange_val


# ---------------------------------------------------------------------------
# Binary search: multi-sensor (brightest wins -- no tube saturates)
# ---------------------------------------------------------------------------
def _binary_search_saturation_multi(configs, led, sensor_list, mux, channels):
    """
    Binary search using the MAX orange reading across all sensors as the
    decision variable. Tracks the best (smallest) integration code that
    saturated *during* the search, so we don't get tripped up by noise on
    a post-search verification read.
    """
    left, right = MIN_INTEG_CODE, MAX_INTEG_CODE
    best_saturating_code = None       # smallest code that hit threshold

    while left < right:
        mid        = (left + right) // 2
        max_orange = _read_max_orange_at_integ_time(
            configs, led, mid, sensor_list, mux, channels
        )
        if max_orange >= ORANGE_SATURATION_VALUE:
            if best_saturating_code is None or mid < best_saturating_code:
                best_saturating_code = mid
            right = mid          # brightest saturates, try shorter
        else:
            left = mid + 1       # need longer integration

    # Also accept the final 'left' if it saturated during the loop's last
    # comparison (it's the smallest code we ever found that worked).
    if best_saturating_code is None:
        print("config_routine: WARNING -- brightest sensor never reached "
              "saturation during search. Using max integration code "
              "({}).".format(MAX_INTEG_CODE))
        return MAX_INTEG_CODE

    print("config_routine: smallest saturating code found = {}".format(
        best_saturating_code))
    return best_saturating_code


def _read_max_orange_at_integ_time(configs, led, integ_code,
                                   sensor_list, mux, channels):
    """
    Set integration time on every sensor, take one LED-on/LED-off pulse,
    return the MAXIMUM orange-channel reading observed across the list.
    Uses a single LED pulse for all sensors (LEDs are wired in parallel)
    so calibration is fast and consistent with run-time behaviour.
    """
    integ_time_s = (integ_code + 1) * 2.8 / 1000.0
    configs["wind_up_time"]   = max(integ_time_s, integ_time_s / 10.0)
    configs["wind_down_time"] = integ_time_s * 3.3

    # Push the candidate integration code to every sensor
    for s in sensor_list:
        s.set_integration_time(integ_code)

    led_ON, led_OFF = 1, 0

    # --- ambient (LED off) ---
    led.value(led_OFF)
    time.sleep(configs["wind_up_time"])
    ambient = []
    for i, s in enumerate(sensor_list):
        if mux is not None and channels is not None:
            mux.disable_all()
            mux.enable_channels(channels[i])
        s.take_measurements()
        ambient.append(s.get_calibrated_orange())

    # --- signal (LED on) ---
    led.value(led_ON)
    time.sleep(configs["wind_up_time"])
    signal = []
    for i, s in enumerate(sensor_list):
        if mux is not None and channels is not None:
            mux.disable_all()
            mux.enable_channels(channels[i])
        s.take_measurements()
        signal.append(s.get_calibrated_orange())

    led.value(led_OFF)
    time.sleep(configs["wind_down_time"])

    # Ambient-subtracted readings, same +0.1 guard as sensors.py
    deltas = [signal[i] - ambient[i] + 0.1 for i in range(len(sensor_list))]
    max_delta = max(deltas)

    pretty = ", ".join("T{}={:.0f}".format(i + 1, d)
                       for i, d in enumerate(deltas))
    print("  integ_code={:3d}  [{}]  max={:.0f}".format(
        integ_code, pretty, max_delta))

    return max_delta