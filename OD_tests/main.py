import machine
import sys
from time import sleep
import sensors
from math import log10

led = machine.Pin(17, machine.Pin.OUT) # LED connected to pin 17
led_ON = 1
led_OFF = 0


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

    if command == "od" and not configs["blank_set"]:
      print("Error: blank value has not been set")
      continue

    execute_command(configs, command)

def get_command():
  command = input(">> ").strip()

  if command == "":
    print("Type 'help' for a list of available commands")
  elif command == "help":
    print("Control commands:")
    print("\tblank\t\t-- Collect a blank value to use as a reference for the optical density calculation")
    print("\tcs\t\t-- Change the sensor_being used to measure optical density")
    print("\thelp\t\t-- Print a list of available commands")
    print("\tod\t\t-- Collect a single data point of optical density. A blank value must be collected before measuring OD.")
    print("\tod5\t\t-- Collect 5 data points of optical density. A blank value must be collected before measuring OD.")
  elif command == "blank":
    print("Measuring blank values")
  elif command == "od":
    print("Measuring optical density")
  elif command == "cs":
    print("Changing sensor")
  #sleep(0.5)
  return command

def execute_command(configs, command):
  if command == "blank":
    configs["blank"] = read_light(configs)
    configs["blank_set"] = True
    print(f"Blank value read: {configs["blank"]}")
    print("Note: this value is different for different sensors since they read different measurements")
  elif command == "od":
    light_in = read_light(configs)
    od = compute_od(light_in, configs["blank"])
    print(f"OD: {od}\t\tblank: {configs["blank"]}\t\tlight in: {light_in}")
  elif command == "od5":
    for i in range (5):
      light_in = read_light(configs)
      od = compute_od(light_in, configs["blank"])
      print(f"OD: {od}\t\tblank: {configs["blank"]}\t\tlight in: {light_in}")
  elif command == "cs":
    get_sensor_name(configs)
    configs["blank_set"] = False

def compute_od(light_in, blank_val):
  return log10(blank_val/light_in)

def read_light(configs):
  sensor = configs["sensor"]
  read = 0

  led.value(led_ON) # turn led on
  sleep(0.5)

  if sensor == "temt6000":
    read = sensors.read_temt6000()
  elif sensor == "veml6030":
    read = sensors.read_veml6030()
  elif sensor == "as726x":
    read = sensors.read_as726x_yellow()
  else:
    raise ValueError("No sensor selected")

  led.value(led_OFF) #turn led off
  sleep(0.5)
  return read

if __name__ == '__main__':
  configs = {
    "sensor": None,     # name of sensor being used
    "blank": None,      # value of the blank used to calculate OD
    "blank_set": None
}

  get_sensor_name(configs)
  try:
    start_OD_tests(configs)
  except (KeyboardInterrupt, SystemExit) as exErr:
    print("\nEnding program. Restart board to use again.")
    sys.exit(0)