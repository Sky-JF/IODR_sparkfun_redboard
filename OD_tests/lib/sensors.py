import qwiic_veml6030
import qwiic_as726x
import machine
import sys

i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400_000)

veml = qwiic_veml6030.QwiicVEML6030()
as726x = qwiic_as726x.QwiicAS726x(i2c)

def init_veml6030():
  if not veml.begin():
    print("veml6030 sensor not found. Check wiring.")
    
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
    