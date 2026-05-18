"""
wifi.py
-------
WiFi connection helper for the SparkFun IoT RedBoard (ESP32).

The ESP32 chip on the RedBoard has built-in WiFi — no external shield needed.
Connection is handled by MicroPython's standard `network` module.

Call connect() once at the start of main.py setup(), before any urequests
calls are made. The board will reconnect automatically on each power cycle
since main.py calls this during setup.
"""

import network
import time
import sys
from secrets import SSID, PASSWORD

# ---------------------------------------------------------------------------
# Credentials — edit these to match your network
# ---------------------------------------------------------------------------
WIFI_SSID     = SSID
WIFI_PASSWORD = PASSWORD

# How long to wait for a connection before giving up (seconds)
CONNECTION_TIMEOUT_S = 20

# ---------------------------------------------------------------------------
# WLAN station object (kept at module level so connect() can reuse it)
# ---------------------------------------------------------------------------
_station = network.WLAN(network.STA_IF)


def connect():
    """
    Connect the board to the WiFi network defined by WIFI_SSID / WIFI_PASSWORD.

    Blocks until connected or CONNECTION_TIMEOUT_S is exceeded.
    Prints the assigned IP address on success.
    Raises RuntimeError if the connection times out, which will surface as a
    crash in main.py and let you know the network is unreachable.
    """
    if _station.isconnected():
        print("WiFi already connected. IP:", _station.ifconfig()[0])
        return

    _station.active(True)
    _station.connect(WIFI_SSID, WIFI_PASSWORD)

    print("Connecting to WiFi network '{}'...".format(WIFI_SSID))

    deadline = time.time() + CONNECTION_TIMEOUT_S
    while not _station.isconnected():
        if time.time() > deadline:
            _station.active(False)
            raise RuntimeError(
                "WiFi connection timed out after {}s. "
                "Check SSID, password, and signal strength.".format(CONNECTION_TIMEOUT_S)
            )
        time.sleep_ms(200)

    ip, subnet, gateway, dns = _station.ifconfig()
    print("WiFi connected!")
    print("  IP address : {}".format(ip))
    print("  Gateway    : {}".format(gateway))


def disconnect():
    """Disconnect from WiFi (useful for power-saving between uploads)."""
    if _station.isconnected():
        _station.disconnect()
    _station.active(False)
    print("WiFi disconnected.")


def is_connected() -> bool:
    """Return True if the station currently has an active WiFi connection."""
    return _station.isconnected()


def reconnect_if_needed():
    """
    Re-establish the connection if it has dropped.
    Call this before each InfluxDB upload to guard against link loss.
    """
    if not _station.isconnected():
        print("WiFi link lost — reconnecting...")
        connect()