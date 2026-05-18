import qwiic_as726x
import sys
import machine

def runExample():
	print("\nQwiic AS726x Example 1 - Basic\n")

	i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)

	myAS726x = qwiic_as726x.QwiicAS726x(i2c)

	if myAS726x.is_connected() == False:
		print("The device isn't connected to the system. Please check your connection", \
			file=sys.stderr)
		return

	myAS726x.begin()

	while True:
		myAS726x.take_measurements()
		if myAS726x.get_version() == myAS726x.kSensorTypeAs7262:
			print(" Reading: V[{}] B[{}] G[{}] Y[{}] O[{}] R[{}]".format(
				myAS726x.get_calibrated_violet(),
				myAS726x.get_calibrated_blue(),
				myAS726x.get_calibrated_green(),
				myAS726x.get_calibrated_yellow(),
				myAS726x.get_calibrated_orange(),
				myAS726x.get_calibrated_red()
			), end="")
		
		elif myAS726x.get_version() == myAS726x.kSensorTypeAs7263:
			print(" Reading: R[{}] S[{}] T[{}] U[{}] V[{}] W[{}]".format(
				myAS726x.get_calibrated_r(),
				myAS726x.get_calibrated_s(),
				myAS726x.get_calibrated_t(),
				myAS726x.get_calibrated_u(),
				myAS726x.get_calibrated_v(),
				myAS726x.get_calibrated_w()
			), end="")

		print(" tempF[{}]".format(myAS726x.get_temperature_f()))

if __name__ == '__main__':
	try:
		runExample()
	except (KeyboardInterrupt, SystemExit) as exErr:
		print("\nEnding Example")
		sys.exit(0)
" \"