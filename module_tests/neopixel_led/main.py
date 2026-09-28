from machine import Pin, ADC
import time
import neopixel as np


led = Pin(18, Pin.OUT)
pin = Pin(4)
neo_leds = np.NeoPixel(pin, 8)

while True:
    led.value(not led.value())
    neo_leds[0] = (255, 0, 0)
    neo_leds[1] = (0, 255, 0)
    neo_leds.write()

    time.sleep(3)

    led.value(not led.value())
    neo_leds[0] = (0, 255, 0)
    neo_leds[1] = (0, 0, 0)
    neo_leds.write()

    time.sleep(3)



