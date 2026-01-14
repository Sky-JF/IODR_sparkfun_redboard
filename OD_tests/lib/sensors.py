import qwiic_veml6030
import qwiic_as726x
import machine
import sys


def read_veml6030():
  i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
  veml = qwiic_veml6030.QwiicVEML6030()

  if veml.begin() == False:
    print("veml6030 sensor not found. Check wiring.")
  else:
  # Example loop to read ambient light every second
    lux = veml.read_light()
    return lux

def read_temt6000():
  sensor = machine.ADC(machine.Pin(36)) #Analog sensor connected to pin A0
  sensor.atten(machine.ADC.ATTN_11DB)
  return sensor.read()

def read_as726x_yellow():
  i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
  myAS726x = qwiic_as726x.QwiicAS726x(i2c)

  if myAS726x.is_connected() == False:
    print("sensor not found. Check wiring", 
      file=sys.stderr)
  else:
    myAS726x.begin()
    myAS726x.take_measurements()
    return myAS726x.get_calibrated_yellow()