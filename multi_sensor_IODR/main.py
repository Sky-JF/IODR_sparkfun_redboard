"""
main.py — MUX-enabled, 3-sensor parallel version.

Uses a SparkFun Qwiic I2C MUX (TCA9548A) to address all sensors that share
a single I2C bus. All LEDs are wired in parallel, with their light up order
determined by the functions in led_ctrl.py. MUX channels are quickly cycled
to read each sensor before turning the LED off again.
"""

import machine
import time
import sys

import sensors as sens
import config_routine
import wifi
import led_ctrl          # NeoPixel / builtin LED setup 
from influxdb_lib import InfluxDBClient

import qwiic_veml6030
import qwiic_as726x
import qwiic_tca9548a          # SparkFun Qwiic MUX driver

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# All hardware/deployment constants (including the InfluxDB token from
# secrets.py) now live in manual_config.py.
from manual_config import (
    DEVICE_ID, UPLOAD_INTERVAL_MS, OD_READ_INTERVAL_MS, POINTS_TO_AVERAGE,
    MUX_CHANNELS, ACTIVE_SENSOR,
    VEML6030_GAIN, VEML6030_INTEG_TIME_MS, AS726X_GAIN_CODE,
    INFLUXDB_HOST, INFLUXDB_PORT, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET,
    I2C_BUS_ID, I2C_SCL_PIN, I2C_SDA_PIN, I2C_FREQ_HZ,
    BLANK_BUTTON_PIN,
)

# ---------------------------------------------------------------------------
# Hardware setup
# ---------------------------------------------------------------------------
i2c0 = machine.I2C(I2C_BUS_ID, scl=machine.Pin(I2C_SCL_PIN),
                   sda=machine.Pin(I2C_SDA_PIN), freq=I2C_FREQ_HZ)  

# Let SparkFun's qwiic_i2c layer create the wrapped driver — its chip
# drivers expect writeCommand()/readBlock(), not raw machine.I2C methods.
mux = qwiic_tca9548a.QwiicTCA9548A()
if not mux.is_connected():
    print("ERROR: Qwiic MUX not found at 0x70. Check wiring.")
    sys.exit(1)
print("Qwiic MUX detected.")


# ---------------------------------------------------------------------------
# MUX-aware sensor proxy
# ---------------------------------------------------------------------------
# Wraps a sensor object so that every attribute access first enables the
# correct MUX channel. This keeps sensors.py unchanged [4] — the wrapped
# objects behave exactly like the underlying QwiicVEML6030 / QwiicAS726x.
class MuxedSensor:
    def __init__(self, mux, channel, sensor):
        self._mux     = mux
        self._channel = channel
        self._sensor  = sensor

    def _select(self):
        # Disable all channels then enable just this one — guarantees only
        # one device is on the bus at a time.
        self._mux.disable_all()
        self._mux.enable_channels(self._channel)

    def __getattr__(self, name):
        attr = getattr(self._sensor, name)
        if callable(attr):
            def wrapped(*args, **kwargs):
                self._select()
                return attr(*args, **kwargs)
            return wrapped
        # Non-callable attribute — still need the right channel selected
        self._select()
        return attr


# ---------------------------------------------------------------------------
# Build sensor lists — one entry per MUX channel
# ---------------------------------------------------------------------------
def _make_veml_for_channel(ch):
    mux.disable_all()
    mux.enable_channels(ch)
    return MuxedSensor(mux, ch, qwiic_veml6030.QwiicVEML6030())

def _make_as726x_for_channel(ch):
    mux.disable_all()
    mux.enable_channels(ch)
    return MuxedSensor(mux, ch, qwiic_as726x.QwiicAS726x())   # no i2c arg

if ACTIVE_SENSOR == "veml6030":
    VEML_SENSORS   = [_make_veml_for_channel(ch) for ch in MUX_CHANNELS]
    AS726X_SENSORS = []
else:
    VEML_SENSORS   = []
    AS726X_SENSORS = [_make_as726x_for_channel(ch) for ch in MUX_CHANNELS]


# ---------------------------------------------------------------------------
# Shared configs dict (used by sensors.py and config_routine.py) [1][2]
# ---------------------------------------------------------------------------
configs = {
    "sensor":         ACTIVE_SENSOR,
    "blank":          None,
    "blank_set":      False,
    "data":           [],
    "wind_up_time":   0.5,
    "wind_down_time": 0.5,
}

blank_values = [None] * len(MUX_CHANNELS)

# ---------------------------------------------------------------------------
# InfluxDB client [3]
# ---------------------------------------------------------------------------
db = InfluxDBClient(
    host   = INFLUXDB_HOST,
    port   = INFLUXDB_PORT,
    token  = INFLUXDB_TOKEN,
    org    = INFLUXDB_ORG,
    bucket = INFLUXDB_BUCKET,
)


# ---------------------------------------------------------------------------
# Temperature helper (unchanged) [1]
# ---------------------------------------------------------------------------
def get_temperature():
    return None

# ---------------------------------------------------------------------------
# Fast multi-sensor read — single LED pulse, multiple reads
# ---------------------------------------------------------------------------
# Because the LEDs are wired in parallel, one LED-on event lights every tube
# simultaneously. We read all channels inside one wind_up / wind_down
# window — the channel switch is microseconds compared to the millisecond-
# scale integration time of the sensors.
def _read_all_channels_one_shot():
    """
    Performs one ambient + one signal read across all MUX channels using
    a single shared LED pulse. Returns ambient-subtracted readings, one
    per channel, in the same order as MUX_CHANNELS.
    """
    sensor_list = AS726X_SENSORS if ACTIVE_SENSOR == "as726x" else VEML_SENSORS

    # --- ambient (LED off) ---
    led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
    time.sleep(configs["wind_up_time"])
    ambient = []
    for s in sensor_list:
        if ACTIVE_SENSOR == "as726x":
            s.take_measurements()
            ambient.append(s.get_calibrated_orange())
        else:
            ambient.append(float(s.read_light()))

    # --- signal (LED on) ---
    led_ctrl.set_tube_leds(led_ctrl.LED_ON)    
    led_ctrl.set_builtin_led(led_ctrl.LED_ON)  
    time.sleep(configs["wind_up_time"])
    signal = []
    for s in sensor_list:
        if ACTIVE_SENSOR == "as726x":
            s.take_measurements()
            signal.append(s.get_calibrated_orange())
        else:
            signal.append(float(s.read_light()))

    led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
    led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
    time.sleep(configs["wind_down_time"])

    # +0.1 to avoid log(0) downstream, matching sensors.py behaviour [4]
    return [signal[i] - ambient[i] + 0.1 for i in range(len(sensor_list))]


def read_light_all_tubes(points_to_average=POINTS_TO_AVERAGE):
    """Average several one-shot reads across all tubes."""
    n = len(MUX_CHANNELS)
    accum = [0.0] * n
    for _ in range(points_to_average):
        readings = _read_all_channels_one_shot()
        for i in range(n):
            accum[i] += readings[i]
    return [v / points_to_average for v in accum]


# ---------------------------------------------------------------------------
# OD calculation per tube [4]
# ---------------------------------------------------------------------------
def read_od_all_tubes():
    light_in = read_light_all_tubes(POINTS_TO_AVERAGE)
    results = []
    for i, val in enumerate(light_in):
        blank = blank_values[i] if blank_values[i] is not None else val
        od    = sens.compute_od(val, blank)
        results.append((i + 1, od))           # tube numbers are 1-indexed
    return results


# ---------------------------------------------------------------------------
# Blank
# ---------------------------------------------------------------------------
def set_blank():
    global blank_values
    print("Setting blank values for sensor:", ACTIVE_SENSOR)
    blank_values = read_light_all_tubes(POINTS_TO_AVERAGE)
    configs["blank"]     = blank_values
    configs["blank_set"] = True
    print("Blank set:", blank_values)


# ---------------------------------------------------------------------------
# InfluxDB upload [3]
# ---------------------------------------------------------------------------
def upload_to_influxdb(od_results):
    wifi.reconnect_if_needed()
    print("Uploading to InfluxDB...")
    db.write_od_data(DEVICE_ID, od_results)

    temp = get_temperature()
    if temp is not None:
        db.write_temperature(DEVICE_ID, temp)
        print("Temperature uploaded: {:.2f} °C".format(temp))
    else:
        pass
        #print("No temperature sensor found, skipping temperature upload.")


def average_od_readings(reading_list):
    if not reading_list:
        return []
    num_tubes = len(reading_list[0])
    result = []
    for t in range(num_tubes):
        tube_num = reading_list[0][t][0]
        valid    = [r[t][1] for r in reading_list if r[t][1] >= 0]
        avg      = sum(valid) / len(valid) if valid else -1.0
        result.append((tube_num, avg))
    return result


# ---------------------------------------------------------------------------
# Timing state
# ---------------------------------------------------------------------------
last_od_read_time    = time.ticks_ms()
last_upload_time     = time.ticks_ms()
accumulated_readings = []

blank_button = machine.Pin(BLANK_BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)  


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
def setup():
    print("IODR MicroPython (MUX edition) — starting up")
    print("Active sensor:", ACTIVE_SENSOR)
    print("Device ID:", DEVICE_ID)

    wifi.connect()

    if ACTIVE_SENSOR == "veml6030":
        for i, veml in enumerate(VEML_SENSORS):
            if not veml.begin():
                print("VEML6030 tube {} not found.".format(i + 1))
            else:
                veml.set_gain(VEML6030_GAIN)                  
                veml.set_integ_time(VEML6030_INTEG_TIME_MS)   
                print("VEML6030 tube {} on MUX ch {} initialised."
                      .format(i + 1, MUX_CHANNELS[i]))

    elif ACTIVE_SENSOR == "as726x":
        for i, s in enumerate(AS726X_SENSORS):
            if not s.is_connected():
                print("AS726x tube {} not connected.".format(i + 1))
            elif not s.begin():
                print("AS726x tube {} failed to begin.".format(i + 1))
            else:
                s.set_gain(AS726X_GAIN_CODE)   
                print("AS726x tube {} on MUX ch {} initialised."
                      .format(i + 1, MUX_CHANNELS[i]))

        # Run integration-time calibration on all tubes — the AS726x parts
        # are identical, and configs["wind_up_time"] / wind_down_time are
        # global, so calibrating once is sufficient.
        print("\nCalibrating AS726x integration time across all tubes...")
        config_routine.find_ideal_integration_time_multi(
            configs, AS726X_SENSORS
        ) 
        print("Calibration complete. wind_up={:.4f}s  wind_down={:.4f}s".format(
            configs["wind_up_time"], configs["wind_down_time"]))

        print("Calibration complete. wind_up={:.4f}s  wind_down={:.4f}s".format(
            configs["wind_up_time"], configs["wind_down_time"]))

    print("\nSetting blank values — ensure tube holders contain blank solution.")
    set_blank()
    print("Blank set. Starting continuous data collection.\n")


# ---------------------------------------------------------------------------
# Main loop [1]
# ---------------------------------------------------------------------------
def loop():
    global last_od_read_time, last_upload_time, accumulated_readings

    # --- OD read cycle ---
    now = time.ticks_ms()
    if time.ticks_diff(now, last_od_read_time) >= OD_READ_INTERVAL_MS:
        od_results = read_od_all_tubes()
        for tube_num, od_val in od_results:
            print("Tube {}: OD = {:.4f}".format(tube_num, od_val))
        print()
        accumulated_readings.append(od_results)
        last_od_read_time = time.ticks_ms()

    # --- Upload cycle ---
    if time.ticks_diff(time.ticks_ms(), last_upload_time) >= UPLOAD_INTERVAL_MS:
        if accumulated_readings:
            averaged = average_od_readings(accumulated_readings)
            upload_to_influxdb(averaged)
            accumulated_readings = []
        last_upload_time = time.ticks_ms()

    # --- Blank button ---
    if blank_button.value() == 0:
        print("Blank button pressed — re-calibrating...")
        set_blank()
        accumulated_readings = []
        print("Re-blank complete.")

    time.sleep_ms(50)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    setup()
    try:
        while True:
            loop()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping data collection.")
        led_ctrl.set_tube_leds(led_ctrl.LED_OFF)    
        led_ctrl.set_builtin_led(led_ctrl.LED_OFF)  
        mux.disable_all()
        sys.exit(0)