from machine import I2C, Pin

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

devices = i2c.scan()
print("I2C devices found:", devices)
