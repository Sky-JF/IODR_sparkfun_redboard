import machine
import sys
import sensors
from time import sleep
from main import read_light

led_ON = 1
led_OFF = 0
LED_WINDUP_TIME = 0.5

AS726X_NUM_CHANNELS = 6
VEML_READINGS = 1

def test_all_settings_as726x(configs):
  with open("as726x_test_all.csv", "w") as f:
    pass
  as726x_warning() # remove this later once clarified
  valid_gains = range(0,4) #gain value of (1, 3.7, 16, 64)
  gains = [1.0, 3.7, 16.0, 64.0]
  valid_integration_times = [0, 32, 64, 96, 128, 160, 192, 224, 255] # 2.8ms to 716.8ms with 89.6ms intervals
  for gain in valid_gains:
    sensors.as726x.set_gain(gain)
    for i_time in valid_integration_times:
      sensors.as726x.set_integration_time(i_time)
      light_in_readings = read_light(configs)
      light_off_readings = read_light(configs, led_on=False)
      j = 0
      for reading in light_in_readings:
        print(f"{j}: Sensor value: {reading}")
        j += 1
      print()
      j = 0
      for reading in light_off_readings:
        print(f"{j}: Sensor value: {reading}")
        j += 1
      print()
      with open("as726x_test_all.csv", "a") as f:
        f.write(f"{gains[gain]},{(i_time + 1) * 2.8}") #calculate integration time, which is (num+1)*2.8ms
        for i in range(0, AS726X_NUM_CHANNELS):
          f.write(f",{light_in_readings[i]},{light_off_readings[i]}")
        f.write("\n")

def test_all_settings_veml6030(configs):
  with open("veml6030_test_all.csv", "w") as f:
    pass
  valid_gains = range(0,4) #gain value of (0.125, 0.25, 1.0, 2.0)
  gains = [0.125, 0.25, 1.0, 2.0]
  valid_integration_times = [25, 50, 100, 200, 400, 800] # integartion time in ms
  for gain in valid_gains:
    sensors.veml.set_gain(gain)
    for i_time in valid_integration_times:
      sensors.veml.set_integ_time(i_time)
      light_in_readings = read_light(configs)
      light_off_readings = read_light(configs, led_on=False)
      j = 0
      for reading in light_in_readings:
        print(f"{j}: Sensor value: {reading}")
        j += 1
      print()
      j = 0
      for reading in light_off_readings:
        print(f"{j}: Sensor value: {reading}")
        j += 1
      print()
      with open("veml6030_test_all.csv", "a") as f:
        f.write(f"{gains[gain]},{i_time}")
        for i in range(0, VEML_READINGS):
          f.write(f",{light_in_readings[i]},{light_off_readings[i]}")
        f.write("\n")


"""
Assign a color to each reading by the as726x
"""
def as726x_warning():
  print("Sensor readings correspond to the following:\n" \
  "0: Violet light in\n" \
  "1: Blue light in\n" \
  "2: Green light in\n" \
  "3: Yellow light in\n" \
  "4: Orange light in\n" \
  "5: Red light in\n")
