"""
sensors.py
----------
Sensor reading library for the MicroPython OD reader project.
Supports VEML6030 and AS726x sensors.

Single-sensor read functions are used by config_routine and interactive
testing. Multi-sensor functions (read_all_veml6030 / read_all_as726x)
iterate over a list of sensors, one per test tube, mirroring the 8-tube
loop in the Arduino IODR project.

LED control is handled by led.py.
"""

import qwiic_veml6030
import qwiic_as726x
import machine
import sys
from time import sleep
import led_ctrl  
from manual_config import (I2C_BUS_ID, I2C_SCL_PIN, I2C_SDA_PIN,
                           I2C_FREQ_HZ) 

# ---------------------------------------------------------------------------
# Default single-sensor objects (same as original)
# Initialised lazily so importing the module never crashes on missing hardware
# ---------------------------------------------------------------------------
_veml   = None
_as726x = None


def get_veml():
    global _veml
    if _veml is None:
        _veml = qwiic_veml6030.QwiicVEML6030()
    return _veml


def get_as726x(i2c=None):
    global _as726x
    if _as726x is None:
        if i2c is None:
            i2c = machine.I2C(I2C_BUS_ID, scl=machine.Pin(I2C_SCL_PIN),
                              sda=machine.Pin(I2C_SDA_PIN), freq=I2C_FREQ_HZ)  
        _as726x = qwiic_as726x.QwiicAS726x(i2c)
    return _as726x


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_veml6030():
    veml = get_veml()
    if not veml.begin():
        print("veml6030 sensor not found. Check wiring.")
        return False
    veml.set_gain(1.0)
    veml.set_integ_time(50.0)
    return True


def init_as726x(i2c=None):
    sensor = get_as726x(i2c)
    if not sensor.is_connected():
        print("as726x sensor not found. Check wiring.", file=sys.stderr)
        return False
    if not sensor.begin():
        print("as726x sensor failed to begin. Check wiring.")
        return False
    return True


# ---------------------------------------------------------------------------
# Low-level single reads
# ---------------------------------------------------------------------------

def read_veml6030():
    return get_veml().read_light()


# ---------------------------------------------------------------------------
# Core read_light helper 
# ---------------------------------------------------------------------------

def read_light(configs, led_on=True):  
    """
    Turn the LED on/off, wait for the sensor to stabilise, then read.
    Subtracts ambient (LED-off) reading from LED-on reading.

    Parameters
    ----------
    configs : dict – must contain "sensor", "wind_up_time", "wind_down_time"
    led_on  : bool – True = LED-on measurement (ambient subtracted)
                     False = raw LED-off measurement

    Returns list of float readings.
    """
    sensor = configs["sensor"]

    offset = []
    if led_on:
        offset = _read_sensor(sensor)   # ambient (LED off) reading
        led_ctrl.set_builtin_led(led_ctrl.LED_ON)  
        led_ctrl.set_tube_leds(led_ctrl.LED_ON)    
    sleep(configs["wind_up_time"])

    read = _read_sensor(sensor)

    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
    led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
    sleep(configs["wind_down_time"])

    if led_on:
        result = [0.0] * len(read)
        for i in range(len(read)):
            # +0.1 prevents log(0) if read == offset
            result[i] = read[i] - offset[i] + 0.1
        return result
    else:
        return read


def _read_sensor(sensor_name):
    """Internal helper: read from the named sensor, return list of floats.

    AS726x returns only the orange channel (index 4) as a single-element list.
    Orange (~610 nm) sits in the absorption peak of many common growth-media
    chromophores and gives the best OD signal for bacterial cultures.
    """
    if sensor_name == "veml6030":
        return [float(read_veml6030())]
    elif sensor_name == "as726x":
        s = get_as726x()
        s.take_measurements()
        return [s.get_calibrated_orange()]   # orange channel only
    else:
        raise ValueError("Unknown sensor: " + sensor_name)


# ---------------------------------------------------------------------------
# Multi-sensor / multi-tube iteration
# ---------------------------------------------------------------------------

def read_all_veml6030(veml_list, configs, points_to_average=10): 
    """
    Iterate over a list of VEML6030 sensor objects, one per test tube.
    Mirrors the 8-tube loop in the Arduino readLightSensors() function.

    Parameters
    ----------
    veml_list        : list[QwiicVEML6030] – one sensor object per tube
    configs          : dict – must contain "wind_up_time", "wind_down_time"
    points_to_average: int  – number of readings to average (like Arduino's
                              pointsToAverage = 10)

    LEDs (tube LEDs + built-in LED) are controlled through led.py.

    Returns
    -------
    list of float – averaged, ambient-subtracted light-in values, one per tube
    """
    num_tubes  = len(veml_list)

    light_in = [0.0] * num_tubes

    for _ in range(points_to_average):
        # --- LED off: measure ambient ---
        led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
        led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
        sleep(configs["wind_up_time"])

        ambient = []
        for veml in veml_list:
            ambient.append(float(veml.read_light()))

        # --- LED on: measure signal ---
        led_ctrl.set_builtin_led(led_ctrl.LED_ON)  
        led_ctrl.set_tube_leds(led_ctrl.LED_ON)    
        sleep(configs["wind_up_time"])

        signal = []
        for veml in veml_list:
            signal.append(float(veml.read_light()))

        # --- accumulate difference ---
        for i in range(num_tubes):
            light_in[i] += (signal[i] - ambient[i] + 0.1)

    # Turn LED(s) off when done
    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
    led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    

    # Divide by points_to_average
    return [v / points_to_average for v in light_in]


def read_all_as726x(as726x_list, configs, points_to_average=10):  
    """
    Iterate over a list of AS726x sensor objects, one per test tube.
    Returns per-tube orange-channel light-in values (ambient subtracted).

    Only the orange channel (~610 nm) is read — it gives the strongest OD
    signal for typical bacterial cultures and avoids the overhead of reading
    all six channels.

    Parameters
    ----------
    as726x_list      : list[QwiicAS726x] – one sensor object per tube
    configs          : dict – must contain "wind_up_time", "wind_down_time"
    points_to_average: int  – number of readings to average

    LEDs (tube LEDs + built-in LED) are controlled through led.py.

    Returns
    -------
    list of float – averaged, ambient-subtracted orange-channel values,
                    one per tube
    """
    num_tubes  = len(as726x_list)

    accum = [0.0] * num_tubes

    for _ in range(points_to_average):
        # --- LED off: ambient ---
        led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
        led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
        sleep(configs["wind_up_time"])

        ambient = []
        for sensor in as726x_list:
            sensor.take_measurements()
            ambient.append(sensor.get_calibrated_orange())

        # --- LED on: signal ---
        led_ctrl.set_builtin_led(led_ctrl.LED_ON)  
        led_ctrl.set_tube_leds(led_ctrl.LED_ON)    
        sleep(configs["wind_up_time"])

        for t, sensor in enumerate(as726x_list):
            sensor.take_measurements()
            signal_val = sensor.get_calibrated_orange()
            accum[t]  += (signal_val - ambient[t] + 0.1) # Added 0.1 to avoid taking logarithm of 0 in case read and offset are equal

    # Turn LED(s) off
    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
    led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    

    return [v / points_to_average for v in accum]


# ---------------------------------------------------------------------------
# OD calculation
# ---------------------------------------------------------------------------

def compute_od(light_in, blank_val):
    """
    Calculate optical density from a light-in reading and a blank value.
    Returns -1.0 on domain errors (same as original main.py).
    """
    from math import log10
    if light_in > 0 and blank_val > 0:
        return log10(blank_val / light_in)
    print("OD error: light_in={}, blank_val={}".format(light_in, blank_val))
    return -1.0


# ---------------------------------------------------------------------------
# Settings adjustment (unchanged from original)
# ---------------------------------------------------------------------------

def adjust_veml6030_settings():
    print("Default settings: \nGain: 0.125\nIntegration time: 100ms\n")
    valid_gains = {2.0, 1.0, 0.25, 0.125}
    while True:
        try:
            gain = float(input("Insert gain value [2, 1, 0.25, 0.125]: "))
            if gain in valid_gains:
                break
        except ValueError:
            pass
    get_veml().set_gain(gain)

    valid_times = (25, 50, 100, 200, 400, 800)
    while True:
        try:
            t = int(input("Insert integration time (ms) [25, 50, 100, 200, 400, 800]: "))
            if t in valid_times:
                break
        except ValueError:
            pass
    get_veml().set_integ_time(float(t))


def adjust_as726x_settings():
    print("Default settings: \nGain: 1x\nIntegration time: 2.8ms [0]\n")
    valid_gains = {1.0, 3.7, 16.0, 64.0}
    gain_codes  = {1.0: 0, 3.7: 1, 16.0: 2, 64.0: 3}
    while True:
        try:
            gain = float(input("Insert gain value [1, 3.7, 16, 64]: "))
            if gain in valid_gains:
                get_as726x().set_gain(gain_codes[gain])
                break
        except ValueError:
            pass

    while True:
        try:
            t = int(input("Insert integration time code [0-255] ([k+1] * 2.8 ms): "))
            if 0 <= t <= 255:
                get_as726x().set_integration_time(t)
                break
        except ValueError:
            pass