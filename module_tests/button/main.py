from machine import Pin, ADC
import time

sensor = ADC(Pin(36)) #Analog sensor connected to pin A0
sensor.atten(ADC.ATTN_11DB)

blank_button = Pin(33, Pin.IN, Pin.PULL_UP)
led = Pin(18, Pin.OUT) # LED connected to pin 17

while True:
    if blank_button.value() == 0:
        led.value(1)
    else:
        led.value(0)
        
    #print(led.value())

    #time.sleep(0.1)
    #read = sensor.read()
    #print(read)

    #time.sleep(1)

