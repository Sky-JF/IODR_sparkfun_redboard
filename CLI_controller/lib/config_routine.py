import machine
import sys
from time import sleep
import time
import sensors

yellow_channel_saturation_value_as726x = 59923 * 0.999 #Make this a bit smaller since saturated readings seem to fluctuate a bit

channel_color_selected = 3 # Value from 0 to 5 corresponding to [violet, blue, green, yellow, orange, red]
percentage_reduction = 0.8 # 80% of integration with saturation time

test_timing_of_implementations = False

def find_ideal_integration_time(config, led):
  if test_timing_of_implementations: 
    start1 = time.ticks_ms()
    configure_as726x(config, led)
    end1 = time.ticks_ms()

    start2 = time.ticks_ms()
    configure_as726x2(config, led)
    end2 = time.ticks_ms()

    print("Implementation 1 time (ms):", time.ticks_diff(end1, start1))
    print("Implementation 2 time (ms):", time.ticks_diff(end2, start2))
    return

  if config["sensor"] == "as726x":
    configure_as726x2(config, led)
  else:
    return

""" 
Executes binary search on pairs of integration times until a the minimum integration time with 
saturated readings is found
Only finds the integration time based on the readings from the yellow channel of the as726x sensor
"""
def configure_as726x(config, led):
  # Execute a binary search from integration time 1*2.8 to 255*2.8 to find the smallest time with saturation
  left_integ_time = 1
  right_integ_time = 255

  saturation_value = yellow_channel_saturation_value_as726x

  ideal_integ_time = -1

  while left_integ_time <= right_integ_time:
    mid_integ_time = left_integ_time + (right_integ_time - left_integ_time) // 2
    mid2_integ_time = mid_integ_time + 1
    mid2_integ_time_code = mid2_integ_time # value used in case the integration time is the maximum, which has code 0
    if mid2_integ_time >= 256:
      mid2_integ_time_code = 0 # this integration time is the maximum for the as726x

    # old implementation
    #read1 = get_read_from_integ_time(config, led, mid_integ_time, mid_integ_time)

    read2 = get_read_with_integ_time(config, led, mid2_integ_time, mid2_integ_time_code)

    if read2 >= saturation_value:
      read1 = get_read_with_integ_time(config, led, mid_integ_time, mid_integ_time)
      if read1 < saturation_value:
        ideal_integ_time = mid2_integ_time
        break
      else:  # integ time too large
        right_integ_time = mid_integ_time + 1
    else: #integ time too small
      left_integ_time = mid_integ_time + 1

  """
  # old implementation
    if read1 < saturation_value and read2 >= saturation_value:
      ideal_integ_time = mid2_integ_time
      break
    elif read1 < saturation_value and read2 < saturation_value:
      left_integ_time = mid_integ_time + 1
    elif read1 >= saturation_value and read2 >= saturation_value:
      right_integ_time = mid_integ_time + 1
    else:
      print(f"Error in binary search: read1 {read1}     read2 {read2}")
  """

  if ideal_integ_time == -1:
    ideal_integ_time = mid2_integ_time

  ideal_integ_time = 4 * ideal_integ_time // 5 # 80% of the min integration time with saturation
  sensors.as726x.set_integration_time(ideal_integ_time)
  print(f"Ideal integration time code: {ideal_integ_time}")
  print(f"Ideal integration time: {(ideal_integ_time+1)*2.8}")


def configure_as726x2(config, led):
  left = 1
  right = 255
  saturation_value = yellow_channel_saturation_value_as726x

  while left < right:
      mid = (left + right) // 2

      read = get_read_with_integ_time(config, led, mid, mid)

      if read >= saturation_value:
          right = mid   # mid might be the answer
      else:
          left = mid + 1

  ideal_integ_time = int(left*percentage_reduction)
  sensors.as726x.set_integration_time(ideal_integ_time)
  print(f"Ideal integration time code: {ideal_integ_time}")
  print(f"Ideal integration time: {(ideal_integ_time+1)*2.8}ms")
  

def get_read_with_integ_time(config, led, integ_time, integ_time_code):
  # LED duty cycle of 25%
  config["wind_up_time"] = integ_time*2.8/1000 / 10
  config["wind_down_time"] = integ_time*2.8/1000 * 3.3
  sensors.as726x.set_integration_time(integ_time_code)
  read_list = sensors.read_light(config, led) # First reading of curr pair of integration times

  print(read_list[channel_color_selected])

  return read_list[channel_color_selected]