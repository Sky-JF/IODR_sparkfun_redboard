import machine
import sys
from time import sleep
import sensors
from math import log10

led = machine.Pin(17, machine.Pin.OUT) # LED connected to pin 17
led_ON = 1
led_OFF = 0
LED_WINDUP_TIME = 0.5


"""
Configure which sensor the data should come from
To change sensors, reset the board or use command cs
"""
def get_sensor_name(configs):
  valid_sensors = ("temt6000", "veml6030", "as726x")

  while True:
    sensor = input(
      "Sensor name? (temt6000, veml6030, as726x) >> "
    ).strip()

    if sensor in valid_sensors:
      configs["sensor"] = sensor
      configs["blank"] = None
      configs["blank_set"] = False
      return
    else:
      print(f"Sensor '{sensor}' not available")


def start_OD_tests(configs):
  while True:
    command = get_command()

    if (command == "od" or command == "od5") and not configs["blank_set"]:
      print("Error: blank value has not been set")
      continue

    execute_command(configs, command)

def get_command():
  command = input(">> ").strip().lower()

  if command == "help":
    print("Control commands:")
    print("\tas726xconfig\t\t-- Adjust configuration settings for the as726x sensor")
    print("\tblank\t\t\t-- Collect a blank value to use as a reference for the optical density calculation")
    print("\tcs\t\t\t-- Change the sensor being used to measure optical density")
    print("\tdrop\t\t\t-- Drop (delete) all data from the current session (does not affect data.txt)")
    print("\tvemlconfig\t\t-- Adjust configuration settings for the veml6030 sensor")
    print("\thelp\t\t\t-- Print a list of available commands")
    print("\tod\t\t\t-- Collect a single data point of optical density. A blank value must be collected before measuring OD.")
    print("\tod5\t\t\t-- Collect 5 data points of optical density. A blank value must be collected before measuring OD.")
    print("\tread\t\t\t-- Read and print a sensor value")
    print("\tread5\t\t\t-- Read and print 5 sensor values")
    print("\tsave\t\t\t-- Save all measured values of this session into a file (will overwrite files from previous sessions)")
  elif command == "blank":
    print("Measuring blank value")
  elif command == "od" or command == "od5":
    print("Measuring optical density")
  elif command == "cs":
    print("Changing sensor")
  elif command == "read" or command == "read5":
    print("Measuring sensor value")
  elif command == "vemlconfig":
    print("Configuring veml6030")
  elif command == "as726xconfig":
    print("Configuring as726x")
  elif command == "save":
    print("Saving data from current session into data.txt")
  elif command == "drop":
    print("Dropping data from current session")
  else:
    print("Type 'help' for a list of available commands")
  #sleep(0.5)
  return command

def execute_command(configs, command):
  if command == "blank":
    configs["blank"] = read_light(configs)
    configs["blank_set"] = True
    as726x_warning() # remove this later once clarified
    j = 0
    for blankVal in configs["blank"]:
      print(f"{j}: Blank value: {blankVal}")
      j += 1
      configs["data"].append(blankVal) # Make file saving prettier %%%
    print("Note: this value is different for different sensors since they read different measurements")
  elif command == "od":
    as726x_warning() # remove this later once clarified
    light_in_readings = read_light(configs)
    for i in range(len(light_in_readings)):
      compute_od(light_in_readings[i], configs["blank"][i], configs)
  elif command == "od5":
    as726x_warning() # remove this later once clarified
    # Repeat 5 times
    for i in range (5):
      light_in_readings = read_light(configs)
      for j in range(len(light_in_readings)):
        reading = light_in_readings[j]
        blank = configs["blank"][j]
        compute_od(reading, blank, configs)
      print()
  elif command == "cs":
    get_sensor_name(configs)
    configs["blank_set"] = False
  elif command == "read":
    as726x_warning() # remove this later once clarified
    light_in_readings = read_light(configs)
    for reading in light_in_readings:
      print(f"Sensor value: {reading}")
      configs["data"].append(reading) # Make file saving prettier %%%
  elif command == "read5":
    as726x_warning() # remove this later once clarified
    for i in range(5):
      j = 0
      light_in_readings = read_light(configs)
      for reading in light_in_readings:
        print(f"{j}: Sensor value: {reading}")
        configs["data"].append(reading) # Make file saving prettier %%%
        j += 1
      print()
  elif command == "vemlconfig" and configs["sensor"] == "veml6030":
    adjust_veml6030_settings()
  elif command == "as726xconfig" and configs["sensor"] == "as726x":
    adjust_as726x_settings()
  elif command == "save":
    write_to_file(configs)
  elif command == "drop":
    configs["data"] = []

def as726x_warning():
  if configs["sensor"] == "as726x":
      print("Sensor readings correspond to the following:\n" \
      "0: Violet light in\n" \
      "1: Blue light in\n" \
      "2: Green light in\n" \
      "3: Yellow light in\n" \
      "4: Orange light in\n" \
      "5: Red light in\n")

def compute_od(light_in, blank_val, configs):
  if (light_in > 0 and blank_val > 0):
    od = log10(blank_val/light_in)
    print(f"OD: {od}\t\tblank: {blank_val}\t\tlight in: {light_in}")
    configs["data"].append(od) # Make file saving prettier %%%
  elif light_in <= 0:
    print(f"Error: light in value of {light_in} is less than or equal to 0 (outside function domain)\nMake sure that the sensor is well connected and is not blocked")
  elif blank_val <= 0:
    print(f"Error: blank value of {blank_val} is less than or equal to 0 (outside function domain)\nMake sure that the sensor is well connected and is not blocked")
  else:
    print("Error: unknown")

def read_light(configs):
  sensor = configs["sensor"]
  #read = 0

  led.value(led_ON) # turn led on
  sleep(LED_WINDUP_TIME)

  if sensor == "temt6000":
    read = [sensors.read_temt6000()]
  elif sensor == "veml6030":
    read = [sensors.read_veml6030()]
  elif sensor == "as726x":
    sensors.as726x.take_measurements()
    read = [sensors.as726x.get_calibrated_violet(),
				sensors.as726x.get_calibrated_blue(),
				sensors.as726x.get_calibrated_green(),
				sensors.as726x.get_calibrated_yellow(),
				sensors.as726x.get_calibrated_orange(),
				sensors.as726x.get_calibrated_red() 
            ]
  else:
    raise ValueError("No sensor selected")

  led.value(led_OFF) #turn led off
  sleep(LED_WINDUP_TIME)
  return read

def adjust_veml6030_settings():
  print("Default settings: \nGain: 0.125\nIntegration time: 100ms\n")
  # The set is the available gain values found in https://learn.sparkfun.com/tutorials/qwiic-ambient-light-sensor-veml6030-hookup-guide/all
  valid_gains = (2.0, 1.0, 0.25, 0.125)

  while True:
    try:
      gain = float(input("Insert gain value [2, 1, 0.25, 0.125]: "))
      if gain in valid_gains:
        break
    except ValueError:
      pass
  sensors.veml.set_gain(float(gain))
  
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
  sensors.veml.set_integ_time(float(integration_time))

def adjust_as726x_settings():
  print("Default settings: \nGain: 1x\nIntegration time: 2.8 [0]\n")
  # The set is the available gain values found in https://docs.sparkfun.com/qwiic_as726x_py/classqwiic__as726x_1_1_qwiic_a_s726x.html#a64decb58a74ea0b881e1af8649f44a0chttps://docs.sparkfun.com/qwiic_as726x_py/classqwiic__as726x_1_1_qwiic_a_s726x.html#a64decb58a74ea0b881e1af8649f44a0c
  valid_gains = (1.0, 3.7, 16.0, 64.0)

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
        sensors.as726x.set_gain(code)
        break
    except ValueError:
      pass
  #sensors.as726x.set_gain(float(gain))

  #from 0 to 255
  while True:
    try:
      integration_time = int(input(
          "Insert integration time code [0–255] (k × 2.8 ms): "
      ))
      if 0 <= integration_time <= 255:
          sensors.as726x.set_integration_time(integration_time)
          break
    except ValueError:
      pass
  #sensors.as726x.set_integration_time(int(integration_time - 1))

def write_to_file(configs):
  with open("data.txt", "w") as f:
    for data in configs["data"]:
      f.write(f"{data}\n")

if __name__ == '__main__':
  configs = {
    "sensor": None,     # name of sensor being used
    "blank": None,      # value of the blank used to calculate OD
    "blank_set": None,
    "data": []
  }

  sensors.init_veml6030()
  sensors.init_as726x()
  get_sensor_name(configs)
  try:
    start_OD_tests(configs)
  except (KeyboardInterrupt, SystemExit) as exErr:
    print("\nEnding program. Restart board to use again.")
    sys.exit(0)