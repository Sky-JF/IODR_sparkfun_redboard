"""
manual_config.py
----------------
Constants that must be configured by hand to match the physical hardware
and deployment of each IODR unit. Edit this file when building, rewiring,
or relocating a device; no other file should need hardware-specific edits.

Secrets (WiFi credentials, InfluxDB API token) remain in secrets.py.
LED colour intensities remain in led.py (TUBE_LED_COLOR).
"""

from secrets import INFLUX_DB_API_TOKEN

# ---------------------------------------------------------------------------
# Device identity and timing
# ---------------------------------------------------------------------------
DEVICE_ID           = 1
UPLOAD_INTERVAL_MS  = 90_000
OD_READ_INTERVAL_MS = 800
POINTS_TO_AVERAGE   = 10

# ---------------------------------------------------------------------------
# Sensors / MUX
# ---------------------------------------------------------------------------
# Which MUX channels host the sensors (one sensor per channel)
# Also, remember to select the correct NeoPixel LEDs below
MUX_CHANNELS = (4, 5, 6, 7) #(2, 1) 

# Which sensor corresponds to each MUX channel ("veml6030" or "as726x")
ACTIVE_SENSOR = "as726x" 

# Sensor settings applied to every tube during main.setup()
VEML6030_GAIN          = 0.125   # valid: 2, 1, 0.25, 0.125
VEML6030_INTEG_TIME_MS = 100.0   # valid: 25, 50, 100, 200, 400, 800
AS726X_GAIN_CODE       = 2       # 0 = 1x, 1 = 3.7x, 2 = 16x, 3 = 64x

# LED read mode:
#   True  -> only one tube LED lit at a time, cycling through the tubes on
#            every read (no light crosstalk between tubes; slower)
#   False -> all tube LEDs lit together in one shared pulse (original behaviour)
# Tube order: NP_IDX[i] must light the tube read by MUX_CHANNELS[i].
SEQUENTIAL_LEDS = True

# ---------------------------------------------------------------------------
# InfluxDB
# ---------------------------------------------------------------------------
INFLUXDB_HOST   = "olsonlab-iodr.kiewit.dartmouth.edu"
INFLUXDB_PORT   = 8086
INFLUXDB_TOKEN  = INFLUX_DB_API_TOKEN
INFLUXDB_ORG    = "olsonlab"
INFLUXDB_BUCKET = "iodr_test"

# ---------------------------------------------------------------------------
# I2C bus
# ---------------------------------------------------------------------------
# NOTE: the qwiic MUX / sensor drivers are created without an i2c argument
# and use the qwiic_i2c default bus; these values apply to machine.I2C
# objects created directly in main.py and sensors.py.
I2C_BUS_ID  = 0
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
I2C_FREQ_HZ = 400_000

# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
BLANK_BUTTON_PIN = 33   # active-low, internal pull-up

# ---------------------------------------------------------------------------
# LEDs
# ---------------------------------------------------------------------------
#NeoPixel LED Setup
NUM_NP_LEDS = 8
NP_PIN_NUM  = 4
# Which NeoPixel LEDs are being used [0-7] (e.g. `(4, 5, 6, 7)`)
NP_IDX = (4, 5, 6, 7) #(1, 2) 

BUILTIN_LED_PIN_NUM = 18