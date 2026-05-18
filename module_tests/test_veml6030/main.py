import qwiic_veml6030
import time
import machine

# Initialize the sensor (adjust I2C settings as needed for your board)
# The default I2C address for the VEML6030 is 0x48
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)

veml = qwiic_veml6030.QwiicVEML6030()

if veml.begin() == False:
  print("Sensor not found. Check wiring.")
else:
  print("Sensor found!")
  # Example loop to read ambient light every second
  while True:
    lux = veml.read_light()
    print("Ambient Light Level in Lux: {}".format(lux))
    time.sleep(1)


