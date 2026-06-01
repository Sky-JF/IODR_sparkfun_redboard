"""
main.py
-------
Continuous optical density data collection loop.
MicroPython port of the Arduino IODR project.

Architecture
------------
- Reads light sensors at a fast interval (OD_READ_INTERVAL_MS)
- Averages readings over POINTS_TO_AVERAGE samples
- Uploads averaged OD + temperature data to InfluxDB every UPLOAD_INTERVAL_MS

Hardware assumptions
--------------------
- LED controlled by a single transistor on pin 17 (shared across all tubes)
- VEML6030 sensors wired to separate I2C buses, or a single sensor for testing
- AS726x sensor on I2C bus 0 (SCL=22, SDA=21)
- Temperature: onboard or external sensor (replace get_temperature() as needed)

To add more tubes
-----------------
- VEML6030:  instantiate more QwiicVEML6030 objects and add them to VEML_SENSORS
- AS726x:    instantiate more QwiicAS726x objects and add them to AS726X_SENSORS
Tube numbers are 1-indexed in InfluxDB (matching Arduino convention).
"""

import machine
import time
import sys

import sensors as sens
import config_routine
import wifi
from influxdb_lib import InfluxDBClient
from secrets import INFLUX_DB_API_TOKEN

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEVICE_ID           = 1          # IODR device number (written to every InfluxDB point)
UPLOAD_INTERVAL_MS  = 90_000     # how often to push data to InfluxDB (90 s, matches Arduino)
OD_READ_INTERVAL_MS = 800        # how often to take a light reading (matches Arduino)
POINTS_TO_AVERAGE   = 10         # readings averaged before upload (matches Arduino)

# Which sensor type is active: "veml6030" | "as726x"
ACTIVE_SENSOR = "as726x"

# InfluxDB connection — edit to match your server
INFLUXDB_HOST   = "olsonlab-iodr.kiewit.dartmouth.edu"
INFLUXDB_PORT   = 8086
INFLUXDB_TOKEN  = INFLUX_DB_API_TOKEN
INFLUXDB_ORG    = "olsonlab"
INFLUXDB_BUCKET = "iodr_test"

# ---------------------------------------------------------------------------
# Hardware setup
# ---------------------------------------------------------------------------

# Shared LED transistor pin (controls all LEDs across all tubes)
led = machine.Pin(17, machine.Pin.OUT)

# Blank button — pin A5, active high (reads 1 when pressed)
# Only checked when ACTIVE_SENSOR == "as726x"
blank_button = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)  # A5 on ESP32 is GPIO33

# I2C bus for sensors
i2c0 = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400_000)

# ---------------------------------------------------------------------------
# Multi-tube sensor lists
# ---------------------------------------------------------------------------
# Add one sensor object per test tube.
# If you only have one sensor, leave a single-element list.
# For multiple VEML6030s on different I2C buses, create separate I2C objects:
#   i2c1 = machine.I2C(1, scl=machine.Pin(xx), sda=machine.Pin(yy), freq=400_000)
#   veml2 = qwiic_veml6030.QwiicVEML6030(i2c=i2c1)

import qwiic_veml6030
import qwiic_as726x

VEML_SENSORS   = [
    qwiic_veml6030.QwiicVEML6030(),   # Tube 1
    # qwiic_veml6030.QwiicVEML6030(i2c=i2c1),  # Tube 2 – add more buses as needed
]

AS726X_SENSORS = [
    qwiic_as726x.QwiicAS726x(i2c0),  # Tube 1
    # qwiic_as726x.QwiicAS726x(i2c1),  # Tube 2
]

# configs dict mirrors the original main.py structure
# wind_up_time / wind_down_time start at 0.5 s.
# For the AS726x, setup() runs config_routine which overwrites these with
# values derived from the ideal integration time found by binary search.
configs = {
    "sensor":         ACTIVE_SENSOR,
    "blank":          None,
    "blank_set":      False,
    "data":           [],
    "wind_up_time":   0.5,   # updated by config_routine for AS726x
    "wind_down_time": 0.5,   # updated by config_routine for AS726x
}

# ---------------------------------------------------------------------------
# InfluxDB client
# ---------------------------------------------------------------------------
db = InfluxDBClient(
    host   = INFLUXDB_HOST,
    port   = INFLUXDB_PORT,
    token  = INFLUXDB_TOKEN,
    org    = INFLUXDB_ORG,
    bucket = INFLUXDB_BUCKET,
)

# ---------------------------------------------------------------------------
# Blank values — one per tube (mirrors Arduino's blankValue[] array)
# ---------------------------------------------------------------------------
blank_values = [None] * max(len(VEML_SENSORS), len(AS726X_SENSORS), 1)

# ---------------------------------------------------------------------------
# Timing state (mirrors Arduino's millis() pattern)
# ---------------------------------------------------------------------------
last_od_read_time    = time.ticks_ms()
last_upload_time     = time.ticks_ms()
accumulated_readings = []   # list of per-cycle results, averaged before upload

# ---------------------------------------------------------------------------
# Temperature helper
# ---------------------------------------------------------------------------

def get_temperature():
    """
    Placeholder — replace with your actual temperature sensor code.
    Returns None if no sensor is available.
    """
    # Example using a DS18x20 on a OneWire bus (install micropython-onewire):
    # import onewire, ds18x20
    # ow  = onewire.OneWire(machine.Pin(8))
    # ds  = ds18x20.DS18X20(ow)
    # roms = ds.scan()
    # if roms:
    #     ds.convert_temp()
    #     time.sleep_ms(750)
    #     return ds.read_temp(roms[0])
    return None


# ---------------------------------------------------------------------------
# Blank calibration
# ---------------------------------------------------------------------------

def set_blank():
    """
    Measure blank values for all tubes using the active sensor type.
    Called once before OD collection begins.
    """
    global blank_values, configs

    print("Setting blank values for sensor:", ACTIVE_SENSOR)

    if ACTIVE_SENSOR == "veml6030":
        light_in = sens.read_all_veml6030(
            VEML_SENSORS, led, configs, POINTS_TO_AVERAGE
        )
        blank_values = light_in
        configs["blank"]     = light_in
        configs["blank_set"] = True

    elif ACTIVE_SENSOR == "as726x":
        light_in = sens.read_all_as726x(
            AS726X_SENSORS, led, configs, POINTS_TO_AVERAGE
        )
        blank_values = light_in
        configs["blank"]     = light_in[0] if light_in else None
        configs["blank_set"] = True

    print("Blank set:", blank_values)


# ---------------------------------------------------------------------------
# OD reading
# ---------------------------------------------------------------------------

def read_od_all_tubes():
    """
    Read all tubes for the active sensor type.

    Returns
    -------
    list of (tube_number, od_float) — tube numbers are 1-indexed.
    """
    results = []

    if ACTIVE_SENSOR == "veml6030":
        light_in = sens.read_all_veml6030(
            VEML_SENSORS, led, configs, POINTS_TO_AVERAGE
        )
        for i, val in enumerate(light_in):
            blank = blank_values[i] if i < len(blank_values) else 1.0
            blank = blank if blank is not None else val
            od    = sens.compute_od(val, blank)
            results.append((i + 1, od))

    elif ACTIVE_SENSOR == "as726x":
        light_in = sens.read_all_as726x(
            AS726X_SENSORS, led, configs, POINTS_TO_AVERAGE
        )
        for i, val in enumerate(light_in):
            blank = blank_values[i] if i < len(blank_values) else 1.0
            blank = blank if blank is not None else val
            od    = sens.compute_od(val, blank)
            results.append((i + 1, od))

    return results


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_to_influxdb(od_results):
    """
    Upload the averaged OD results and current temperature to InfluxDB.

    Parameters
    ----------
    od_results : list – output of read_od_all_tubes(), always
                 [(tube_number, od_float), ...] regardless of sensor type
    """
    wifi.reconnect_if_needed()   # guard against link loss between upload cycles
    print("Uploading to InfluxDB...")
    db.write_od_data(DEVICE_ID, od_results)

    temp = get_temperature()
    if temp is not None:
        db.write_temperature(DEVICE_ID, temp)
        print("Temperature uploaded: {:.2f} °C".format(temp))
    else:
        print("No temperature sensor found, skipping temperature upload.")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup():
    print("IODR MicroPython — starting up")
    print("Active sensor:", ACTIVE_SENSOR)
    print("Device ID:", DEVICE_ID)

    # Connect to WiFi before anything else — urequests needs an active link
    wifi.connect()
    if ACTIVE_SENSOR == "veml6030":
        for i, veml in enumerate(VEML_SENSORS):
            ok = veml.begin()
            if not ok:
                print("VEML6030 tube {} not found. Check wiring.".format(i + 1))
            else:
                veml.set_gain(0.125)
                veml.set_integ_time(100.0)
                print("VEML6030 tube {} initialised.".format(i + 1))

    elif ACTIVE_SENSOR == "as726x":
        for i, sensor in enumerate(AS726X_SENSORS):
            if not sensor.is_connected():
                print("AS726x tube {} not connected.".format(i + 1))
            elif not sensor.begin():
                print("AS726x tube {} failed to begin.".format(i + 1))
            else:
                sensor.set_gain(2)
                print("AS726x tube {} initialised.".format(i + 1))

        print("\nRunning AS726x integration-time calibration (orange channel)...")
        config_routine.find_ideal_integration_time(configs, led)
        print("Calibration complete. wind_up={:.4f}s  wind_down={:.4f}s".format(
            configs["wind_up_time"], configs["wind_down_time"]
        ))

    # Set blank
    print("\nSetting blank values — ensure tube holders are filled with blank solution.")
    set_blank()
    print("Blank set. Starting continuous data collection.\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def loop():
    """
    Continuous data collection loop — mirrors the Arduino loop() function.

    Reads OD at OD_READ_INTERVAL_MS and uploads averaged data
    to InfluxDB every UPLOAD_INTERVAL_MS.

    For the AS726x only: if the blank button (pin A5) is held high,
    re-runs set_blank() and clears the accumulated readings buffer so
    the next upload only contains post-blank data.
    """
    global last_od_read_time, last_upload_time, accumulated_readings

    # --- Blank button check (AS726x only) ---
    if ACTIVE_SENSOR == "as726x" and blank_button.value() == 0:
        print("Blank button pressed — re-calibrating...")
        # Integration time
        print("\nRunning AS726x integration-time calibration (orange channel)...")
        config_routine.find_ideal_integration_time(configs, led)
        print("Calibration complete. wind_up={:.4f}s  wind_down={:.4f}s".format(
            configs["wind_up_time"], configs["wind_down_time"]
        ))

        # Blank values
        set_blank()
        accumulated_readings = []  # discard readings taken before the new blank
        print("Re-blank complete. Resuming data collection.")
        # Wait for the button to be released before continuing
        while blank_button.value() == 0 and False: # Currently disabled because of hardware issues with button
            time.sleep_ms(50)

    # --- OD read cycle ---
    now = time.ticks_ms()
    if time.ticks_diff(now, last_od_read_time) >= OD_READ_INTERVAL_MS:
        od_results = read_od_all_tubes()

        # Print current readings to REPL
        for tube_num, od_val in od_results:
            print("Tube {}: OD = {:.4f}".format(tube_num, od_val))

        accumulated_readings.append(od_results)
        last_od_read_time = time.ticks_ms()

    # --- Upload cycle ---
    if time.ticks_diff(time.ticks_ms(), last_upload_time) >= UPLOAD_INTERVAL_MS:
        if accumulated_readings:
            # Average the OD readings collected since the last upload
            averaged = average_od_readings(accumulated_readings)
            upload_to_influxdb(averaged)
            accumulated_readings = []   # clear the buffer
        last_upload_time = time.ticks_ms()

    # Small sleep to avoid busy-waiting
    time.sleep_ms(50)


def average_od_readings(reading_list):
    """
    Average a list of OD reading sets.

    Parameters
    ----------
    reading_list : list of list – each inner list is one cycle's output of
                   read_od_all_tubes(), i.e. [(tube_num, od_float), ...]

    Returns
    -------
    list of (tube_num, averaged_od_float)
    """
    if not reading_list:
        return []

    num_tubes = len(reading_list[0])
    result    = []

    for t in range(num_tubes):
        tube_num = reading_list[0][t][0]
        valid    = [r[t][1] for r in reading_list if r[t][1] >= 0]
        avg      = sum(valid) / len(valid) if valid else -1.0
        result.append((tube_num, avg))

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    setup()
    try:
        while True:
            loop()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping data collection.")
        led.value(led_OFF)
        sys.exit(0)