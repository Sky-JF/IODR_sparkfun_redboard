"""
influxdb.py
-----------
InfluxDB v2 upload library for MicroPython (SparkFun ESP32).
Mirrors the uploadDataToInfluxDB() logic from the Arduino IODR project.

Usage:
    from influxdb import InfluxDBClient
    db = InfluxDBClient(host="10.12.14.133", port=8086, token="...", org="IODR", bucket="IODR_test")
    db.write_od_data(device_id=1, od_readings=[(1, 0.42), (2, 0.38)])
    db.write_temperature(device_id=1, temperature=23.5)
"""

import urequests
import ujson


class InfluxDBClient:
    """
    Minimal InfluxDB v2 HTTP client for MicroPython.

    Parameters
    ----------
    host   : str   IP address or hostname of the InfluxDB server
    port   : int   HTTP port (default 8086)
    token  : str   InfluxDB API token
    org    : str   InfluxDB organisation name
    bucket : str   InfluxDB bucket name
    """

    def __init__(self, host, port, token, org, bucket):
        self.host   = host
        self.port   = port
        self.token  = token
        self.org    = org
        self.bucket = bucket
        self._base_url = "http://{}:{}/api/v2/write?org={}&bucket={}&precision=s".format(
            host, port, org, bucket
        )
        self._headers = {
            "Authorization": "Token " + token,
            "Content-Type":  "text/plain; charset=utf-8",
            "Accept":        "application/json",
        }

    # ------------------------------------------------------------------
    # Low-level write
    # ------------------------------------------------------------------

    def _post(self, line_protocol: str) -> int:
        """
        Send one or more lines of InfluxDB line-protocol data.
        Returns the HTTP status code (204 = success for InfluxDB v2).
        Returns -1 on a network / connection error.
        """
        try:
            response = urequests.post(
                self._base_url,
                headers=self._headers,
                data=line_protocol
            )
            status = response.status_code
            response.close()
            return status
        except OSError as e:
            print("InfluxDB connection error:", e)
            return -1

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def write_od_data(self, device_id: int, od_readings: list) -> int:
        """
        Upload optical density readings for multiple tubes/sensors.

        Parameters
        ----------
        device_id   : int    IODR device number (e.g. 1, 2, 3)
        od_readings : list   list of (tube_number, od_value) tuples
                              tube_number is 1-indexed (matches Arduino convention)

        Returns HTTP status code.

        Example line-protocol produced:
            IODR_1,tube_number=1 OD=0.42
            IODR_1,tube_number=2 OD=0.38
        """
        lines = []
        for tube_number, od_value in od_readings:
            line = "IODR_{},tube_number={} OD={}".format(
                device_id, tube_number, od_value
            )
            lines.append(line)

        payload = "\n".join(lines)
        status = self._post(payload)
        print("InfluxDB OD upload status:", status)
        return status

    def write_temperature(self, device_id: int, temperature: float) -> int:
        """
        Upload a temperature reading.

        Parameters
        ----------
        device_id   : int    IODR device number
        temperature : float  temperature in degrees Celsius

        Returns HTTP status code.

        Example line-protocol produced:
            IODR_1,IODR_ID=1 temperature=23.5
        """
        line = "IODR_{},IODR_ID={} temperature={}".format(
            device_id, device_id, temperature
        )
        status = self._post(line)
        print("InfluxDB temperature upload status:", status)
        return status

    def write_spectral_od(self, device_id: int, tube_number: int,
                          spectral_od: dict) -> int:
        """
        Upload per-wavelength OD values from the AS726x spectral sensor.

        Parameters
        ----------
        device_id   : int   IODR device number
        tube_number : int   1-indexed tube number
        spectral_od : dict  mapping of wavelength label to OD value
                             e.g. {"violet": 0.1, "blue": 0.2, ...}

        Returns HTTP status code.

        Example line-protocol:
            IODR_1,tube_number=1 violet=0.1,blue=0.2,green=0.15,...
        """
        fields = ",".join(
            "{}={}".format(k, v) for k, v in spectral_od.items()
        )
        line = "IODR_{}_spectral,tube_number={} {}".format(
            device_id, tube_number, fields
        )
        status = self._post(line)
        print("InfluxDB spectral OD upload status:", status)
        return status

    def write_raw_light(self, device_id: int, tube_number: int,
                        raw_values: list, sensor_name: str) -> int:
        """
        Upload raw (non-OD) light sensor readings.

        Parameters
        ----------
        device_id   : int   IODR device number
        tube_number : int   1-indexed tube number
        raw_values  : list  list of raw float readings
        sensor_name : str   sensor type ("temt6000", "veml6030", "as726x")

        Returns HTTP status code.
        """
        if len(raw_values) == 1:
            fields = "value={}".format(raw_values[0])
        else:
            # AS726x: index maps to violet/blue/green/yellow/orange/red
            labels = ["violet", "blue", "green", "yellow", "orange", "red"]
            fields = ",".join(
                "{}={}".format(labels[i] if i < len(labels) else "ch{}".format(i), v)
                for i, v in enumerate(raw_values)
            )

        line = "IODR_{}_raw_{},tube_number={} {}".format(
            device_id, sensor_name, tube_number, fields
        )
        status = self._post(line)
        print("InfluxDB raw light upload status:", status)
        return status