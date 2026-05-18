# IODR_sparkfun_redboard

Second iteration of the IODR Device for the Olson Lab. The current project uses a Sparkfun IoT Redboard ESP32 Development Board. 

The IODR collects optical density/absorbance data of samples in test tubes and uploads them to a locally run database that can be accessed by the IODR frontend server. Find relevant links in the Additional Projects section.

## Navigation
This repository features three main programs for the development board:
- `CLI_controller`
    This program provides a CLI to manually control the IODR. The controller allows for selection and configuration of different sensors (veml6030, temt6000, as726x), measuring of optical density or sensor light values, automatic data collection of all sensor configurations, as well as saving data to download onto a computer. 
    This program contains 2 scripts to download data collected while using the CLI:
    - `retreive_data.ps1`
        Retreives data collected manually
    - `retreive_full_settings_test.ps1`
      Retreives data collected from the test for all settings for both the veml6030 and the as726x sensors
- `single_sensor_IODR`
    This program functions like the Arduino Giga IODR, collecting data and sending it to the database, but with only one sensor. 
- `Multi_sensor_IODR`
    This program implements reading of multiple sensors, similar to the Arduino Giga IODR.

Additionally, several tests for different modules of each main program is included in `module_tests`.

## Setup
Before uploading any programs to the Sparkfun development board, make sure the correct micropython firmware is uploaded first.
1. Download the [SparkFun MicroPython Firmware Uploader](https://github.com/sparkfun/SparkFun_MicroPython_Firmware_Uploader) 
2. Press the boot button on the development board
3. Select the serial port connected to the development board
4. Choose the `ESP32_GENERIC-20251209-v1.27.0.bin` firmware file
5. Flash the firmware
6. Reboot the board

## How to use
This repository features two types of powershell scripts for Windows which are used to interact with the development board:
- `upload.ps1`
    This script uploads each python file to the development board in order to program it. There is a specific `upload.ps1` that uploads all necessary files for each of the main programs. 
    - To upload a local file to the development board, use the command `mpremote.exe fs cp <local_file_path> :<microprocessor_file_path>` (e.g. `mpremote.exe fs cp ./lib/wifi.py :/lib/wifi.py`).
    - To upload a file from github, use the command `mpremote.exe mip install github:<github_user>/<github_repository>` (e.g. `mpremote.exe mip install github:sparkfun/qwiic_veml6030_py`). Before uploading this file, make sure it is installed through pip.
- `connect.ps1`
    This script establishes serial communication with the boards and function as a serial output/input for the program that is currently running on the development board. 

## Dependencies
- mpremote
- sparkfun_qwiic_as726x
- sparkfun_qwiic_i2c
- sparkfun_qwiic_veml6030

### How to install (Windows)
1. Activate python virtual environment
   ```
    py -m venv .venv
    .\.venv\Scripts\activate
    ```
2. Install dependencies
   ```
    pip install mpremote
    pip install sparkfun-qwiic-as726x
    pip install sparkfun-qwiic-i2c
    pip install sparkfun-qwiic-veml6030
   ```

### Other useful dependencies
- esptool 
    Used for uploading firmware to esp32 boards

## Hardware used in this project
- SparkFun IoT Redboard Development Board
- SparkFun Ambient Light Sensor - VEML6030 (Qwiic)
- SparkFun Ambient Light Sensor Breakout - TEMT6000
- SparkFun Spectral Sensor Breakout - AS726x Visible (Qwiic)

## Resources
- [Sparkfun IoT Redboard ESP32 Development Board main page](https://www.sparkfun.com/sparkfun-iot-redboard-esp32-development-board.html)
- [Sparkfun ESP32 data sheet](https://cdn.sparkfun.com/datasheets/IoT/esp32_datasheet_en.pdf)

## Additional Projects
- [Frontend data viewer](https://iodr-605db139538a.herokuapp.com)
- [GitHub repository for frontend data viewer](https://github.com/danolson1/IODR_project?tab=readme-ov-file#readme)
- [Thingspeak data webpage](https://thingspeak.mathworks.com/channels/469909)
- [Arduino Giga IODR repository](https://github.com/Sky-JF/IODR_Device)