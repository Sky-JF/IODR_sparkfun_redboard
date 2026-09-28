from machine import Pin, ADC
import time

sensor = ADC(Pin(36)) #Analog sensor connected to pin A0
sensor.atten(ADC.ATTN_11DB)


led = Pin(18, Pin.OUT) # builtin LED connected to pin 18

while True:
    led.value(not led.value())
    print(led.value())

    time.sleep(0.1)
    #read = sensor.read()
    #print(read)

    time.sleep(5)

