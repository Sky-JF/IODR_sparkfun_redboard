import machine
import sys
from time import sleep
import sensors
import full_setting_test as fst
from math import log10

led = machine.Pin(17, machine.Pin.OUT) # LED connected to pin 17

warning_array_size = 300

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

"""
Get a command from the user, validate it, and execute it
"""
def start_OD_tests(configs):
  while True:
    command = get_command()

    # Check if a blank value is set before computing optical density (od is dependent on blank)
    if (command == "od" or command == "od5") and not configs["blank_set"]:
      print("Error: blank value has not been set")
      continue

    execute_command(configs, command)
    if len(configs["data"]) > warning_array_size:
      print("Warning! Data collected in this run is over 300 data points. Another read may result in a crash. Consider saving or dropping the current data before proceeding.")

"""
Get input from user, validate it, and print a status message for each command
"""
def get_command():
  command = input(">> ").strip().lower()

  if command == "help":
    print("Control commands:")
    print("\tas726xconfig\t\t-- Adjust configuration settings for the as726x sensor")
    print("\tblank\t\t\t-- Collect a blank value to use as a reference for the optical density calculation")
    print("\tcs\t\t\t-- Change the sensor being used to measure optical density")
    print("\tdrop\t\t\t-- Drop (delete) all data from the current session (does not affect data.txt)")
    print("\tfst-as726x\t\t-- Tests all the settings for the as726x sensor")
    print("\tfst-veml6030\t\t-- Tests all the settings for the veml6030 sensor")
    print("\thelp\t\t\t-- Print a list of available commands")
    print("\tod\t\t\t-- Collect a single data point of optical density. A blank value must be collected before measuring OD.")
    print("\tod5\t\t\t-- Collect 5 data points of optical density. A blank value must be collected before measuring OD.")
    print("\tread\t\t\t-- Read and print a sensor value with the led on")
    print("\tread5\t\t\t-- Read and print 5 sensor values with the led on")
    print("\tread-off\t\t-- Read and print 5 sensor values with the led off")
    print("\tread-off5\t\t-- Read and print 5 sensor values with the led off")
    print("\tsave\t\t\t-- Save all measured values of this session into a file (will overwrite files from previous sessions)")
    print("\tvemlconfig\t\t-- Adjust configuration settings for the veml6030 sensor")
  elif command == "blank":
    print("Measuring blank value")
  elif command == "od" or command == "od5":
    print("Measuring optical density")
  elif command == "cs":
    print("Changing sensor")
  elif command == "read" or command == "read5":
    print("Measuring sensor value with LED on")
  elif command == "vemlconfig":
    print("Configuring veml6030")
  elif command == "as726xconfig":
    print("Configuring as726x")
  elif command == "save":
    print("Saving data from current session into data.txt")
  elif command == "drop":
    print("Dropping data from current session")
  elif command == "read-off" or command == "read-off5":
    print("Measuring sensor value with LED off")
  elif command == "fst-as726x":
    print("Testing all settings for the as726x")
  elif command == "fst-veml6030":
    print("Testing all settings for the veml6030")
  else:
    print("Type 'help' for a list of available commands")
  #sleep(0.5)
  return command

"""
Use the given command to execute its instruction of data collection or configuration
"""
def execute_command(configs, command):
  if command == "blank":
    configs["blank"] = sensors.read_light(configs, led)
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
    light_in_readings = sensors.read_light(configs, led)
    for i in range(len(light_in_readings)):
      od = compute_od(light_in_readings[i], configs["blank"][i], configs)
      print(f"{i}: OD: {od}\t\tblank: {configs["blank"][i]}\t\tlight in: {light_in_readings[i]}")
  elif command == "od5":
    as726x_warning() # remove this later once clarified
    # Repeat 5 times
    for i in range(5):
      light_in_readings = sensors.read_light(configs, led)
      for j in range(len(light_in_readings)):
        reading = light_in_readings[j]
        blank = configs["blank"][j]
        od = compute_od(reading, blank, configs)
        print(f"{i}: OD: {od}\t\tblank: {blank}\t\tlight in: {reading}")
      print()
  elif command == "cs":
    get_sensor_name(configs)
    configs["blank_set"] = False
  elif command == "read":
    as726x_warning() # remove this later once clarified
    j = 0
    light_in_readings = sensors.read_light(configs, led)
    for reading in light_in_readings:
      print(f"{j}: Sensor value: {reading}")
      configs["data"].append(reading) # Make file saving prettier %%%
      j += 1
  elif command == "read5":
    as726x_warning() # remove this later once clarified
    for i in range(5):
      j = 0
      light_in_readings = sensors.read_light(configs, led)
      for reading in light_in_readings:
        print(f"{j}: Sensor value: {reading}")
        configs["data"].append(reading) # Make file saving prettier %%%
        j += 1
      print()
  elif command == "read-off":
    as726x_warning() # remove this later once clarified
    j = 0
    light_in_readings = sensors.read_light(configs, led, led_on=False)
    for reading in light_in_readings:
      print(f"{j}: Sensor value: {reading}")
      configs["data"].append(reading) # Make file saving prettier %%%
      j += 1
  elif command == "read-off5":
    as726x_warning() # remove this later once clarified
    for i in range(5):
      j = 0
      light_in_readings = sensors.read_light(configs, led, led_on=False)
      for reading in light_in_readings:
        print(f"{j}: Sensor value: {reading}")
        configs["data"].append(reading) # Make file saving prettier %%%
        j += 1
      print()
  elif command == "vemlconfig" and configs["sensor"] == "veml6030":
    sensors.adjust_veml6030_settings()
  elif command == "as726xconfig" and configs["sensor"] == "as726x":
    sensors.adjust_as726x_settings()
  elif command == "save":
    write_to_file(configs)
  elif command == "drop":
    configs["data"] = []
  elif command == "fst-as726x":
    fst.test_all_settings_as726x(configs)
  elif command == "fst-veml6030":
    fst.test_all_settings_veml6030(configs)


"""
Assign an index to each color of each reading by the as726x
"""
def as726x_warning():
  if configs["sensor"] == "as726x":
      print("Sensor readings correspond to the following:\n" \
      "0: Violet light in\n" \
      "1: Blue light in\n" \
      "2: Green light in\n" \
      "3: Yellow light in\n" \
      "4: Orange light in\n" \
      "5: Red light in\n")

"""
use the light in and blank value to calculate absorbance/optical density
"""
def compute_od(light_in, blank_val, configs):
  if (light_in > 0 and blank_val > 0):
    od = log10(blank_val/light_in)
    #print(f"OD: {od}\t\tblank: {blank_val}\t\tlight in: {light_in}")
    configs["data"].append(od) # Make file saving prettier %%%
    return od
  elif light_in <= 0:
    print(f"Error: light in value of {light_in} is less than or equal to 0 (outside function domain)\nMake sure that the sensor is well connected and is not blocked")
  elif blank_val <= 0:
    print(f"Error: blank value of {blank_val} is less than or equal to 0 (outside function domain)\nMake sure that the sensor is well connected and is not blocked")
  else:
    print("Error: unknown")
  return -1 # In case of error, invalid od value is returned



"""
Save the data points collected in this session to a file
"""
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