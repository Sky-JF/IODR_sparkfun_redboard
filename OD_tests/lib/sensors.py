import qwiic_veml6030
import qwiic_as726x
import machine
import sys
from time import sleep

led_ON = 1
led_OFF = 0
LED_WINDUP_TIME = 0.5
LED_WINDDOWN_TIME = LED_WINDUP_TIME

i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400_000)

veml = qwiic_veml6030.QwiicVEML6030()
as726x = qwiic_as726x.QwiicAS726x(i2c)

def init_veml6030():
  if not veml.begin():
    print("veml6030 sensor not found. Check wiring.")
  veml.set_gain(1.0) # default gain value set to 1.0
  veml.set_integ_time(50.0) #default integration time set to 50ms
    
def read_veml6030():
  return veml.read_light()

def read_temt6000():
  sensor = machine.ADC(machine.Pin(36)) #Analog sensor connected to pin A0
  sensor.atten(machine.ADC.ATTN_11DB)
  return sensor.read()

def init_as726x():
  if not as726x.is_connected():
    print("as726x sensor not found. Check wiring", 
      file=sys.stderr)
    return
  if not as726x.begin():
    print("as726x sensor not found. Check wiring.")
    

"""
Adjust the veml6030 settings to change gain and integration time
"""
def adjust_veml6030_settings():
  print("Default settings: \nGain: 0.125\nIntegration time: 100ms\n")
  # The set is the available gain values found in https://learn.sparkfun.com/tutorials/qwiic-ambient-light-sensor-veml6030-hookup-guide/all
  valid_gains = {2.0, 1.0, 0.25, 0.125}

  while True:
    try:
      gain = float(input("Insert gain value [2, 1, 0.25, 0.125]: "))
      if gain in valid_gains:
        break
    except ValueError:
      pass
  veml.set_gain(float(gain))
  
  # Available integration times from webpage above
  valid_times = (25, 50, 100, 200, 400, 800)

  while True:
    try:
      integration_time = int(input(
        "Insert integration time (ms) [25, 50, 100, 200, 400, 800]: "
      ))
      if integration_time in valid_times:
        break
    except ValueError:
      pass
  veml.set_integ_time(float(integration_time))

"""
Adjust the integration time or the gain for the as726x
"""
def adjust_as726x_settings():
  print("Default settings: \nGain: 1x\nIntegration time: 2.8 [0]\n")
  # The set is the available gain values found in https://docs.sparkfun.com/qwiic_as726x_py/classqwiic__as726x_1_1_qwiic_a_s726x.html#a64decb58a74ea0b881e1af8649f44a0chttps://docs.sparkfun.com/qwiic_as726x_py/classqwiic__as726x_1_1_qwiic_a_s726x.html#a64decb58a74ea0b881e1af8649f44a0c
  valid_gains = {1.0, 3.7, 16.0, 64.0}

  while True:
    try:
      gain = float(input("Insert gain value [1, 3.7, 16, 64]: "))
      if gain in valid_gains:
        code = 0
        if gain == 1.0:
          code = 0
        elif gain == 3.7:
          code = 1
        elif gain == 16.0:
          code = 2
        elif gain == 64.0:
          code = 3
        as726x.set_gain(code)
        break
    except ValueError:
      pass
  #sensors.as726x.set_gain(float(gain))

  #from 0 to 255
  while True:
    try:
      integration_time = int(input(
          "Insert integration time code [0–255] ([k+1] * 2.8 ms): "
      ))
      if 0 <= integration_time and integration_time <= 255:
          as726x.set_integration_time(integration_time)
          break
    except ValueError:
      pass

"""
Turn the LED on for 0.5 seconds, then read values from the selected sensor
Parameters:
    configs -- Configs dictionary with sensor being used
    led     -- pin number of the led output
    led_on  -- boolean to determine if the measurement is made while the led is on or off
"""
def read_light(configs, led, led_on=True):
  sensor = configs["sensor"]

  offset = []
  if (led_on):
    offset = read_sensor(sensor) # led off reading
    led.value(led_ON) # turn led on
  sleep(LED_WINDUP_TIME)

  read = read_sensor(sensor) # if led is on, get the led on reading

  led.value(led_OFF) #turn led off
  sleep(LED_WINDUP_TIME)

  if led_on: # calculate the difference between the light on reading and light off
    result = [0] * len(read)
    for i in range(len(read)):
      result[i] = read[i] - offset[i]
    return result
  else:
    return read

"""
Helper function to read the light in values of a sensor
"""
def read_sensor(sensor):
  if sensor == "temt6000":
    read = [read_temt6000()]
  elif sensor == "veml6030":
    read = [read_veml6030()]
  elif sensor == "as726x":
    as726x.take_measurements()
    read = [as726x.get_calibrated_violet(),
				as726x.get_calibrated_blue(),
				as726x.get_calibrated_green(),
				as726x.get_calibrated_yellow(),
				as726x.get_calibrated_orange(),
				as726x.get_calibrated_red() 
            ]
  else:
    raise ValueError("No sensor selected")

  return read