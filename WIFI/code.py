########################################################
#
#   Embedded Software for IoT, University of Trento
#   A.Y. 2023/2024
#   Final project
#
#   Authors: Carlotta Cazzolli 226912
#            Alessandro Iepure 228023
#            Martina Panini 226621
#
#   Smart Pet Door
#
#   MIT license, see LICENSE file
#
########################################################

import board
import busio
import wifi
import socketpool
import rtc
import os
import ssl
import time

import adafruit_ntp
import adafruit_requests
import adafruit_logging as logging
import adafruit_datetime as cpy_datetime

# Initialize the logger
logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)

# Try connecting to WiFi (SSID and password are stored in settings.toml) every 5
# seconds until a connection is established
connected = False
while not connected:
    try:
        wifi.radio.connect(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
    except ConnectionError:
        logger.error(
            f'WiFi: failed to connect to {os.getenv("WIFI_SSID")}, retrying in 5 sec...')
        time.sleep(5)

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
logger.info(f'WiFi: connected to {os.getenv("WIFI_SSID")}')


# Retrieve the current time from an NTP server
ntp = adafruit_ntp.NTP(pool, tz_offset=1)
rtc.RTC().datetime = ntp.datetime
logger.info(f"NTP time: {cpy_datetime.datetime.now()}")

# UART for serial communication between Pico and Pico W
uart = busio.UART(tx=board.GP0, rx=board.GP1, baudrate=115200)
logger.info('UART initialized at 115200 bauds')


def send_notification(title: str, data, tags: str = "") -> None:
    """
    Sends a notification to the NTFY.SH service.

    Args:
        title (str): The title of the notification.
        data (str): The data of the notification.
        tags (str, optional): The tags of the notification. Defaults to "".
    Returns:
        None
    """

    response = requests.post(
        os.getenv("NTFYSH_URL"),
        data=data,
        headers={"Title": title, "Tags": tags},
    )
    response.close()
    logger.info(f'Notification sent: title={title}, data={data}, tags={tags}')


def _json_extract(obj, key):

    arr = []

    def extract(obj, arr, key):

        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values


def response_weather():
    """Retrieves the weather data from the OpenWeatherMap API and sends it over UART"""

    logger.debug(
        f'Started retrieving weather data for ({os.getenv("LATITUDE")}, {os.getenv("LONGITUDE")})...'
    )
    response = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?lat={os.getenv("LATITUDE")}&lon={os.getenv("LONGITUDE")}&appid={os.getenv("OWM_API_KEY")}'
    )

    # Parse response
    if response.status_code != 200:
        # Error: send error message over UART

        logger.error(f"Error retrieving weather data: {response.status_code}")
        uart.write(bytes(f"!W:E;", "ascii"))

    # Extract relevant data from json response
    weather = _json_extract(response.json(), "main")[0]
    timezone = _json_extract(response.json(), "timezone")[0]
    sunset = cpy_datetime.datetime.fromtimestamp(
        _json_extract(response.json(), "sunset")[0]
    ) + cpy_datetime.timedelta(seconds=timezone)
    sunrise = cpy_datetime.datetime.fromtimestamp(
        _json_extract(response.json(), "sunrise")[0]
    ) + cpy_datetime.timedelta(seconds=timezone)

    logger.info(
        f"Retrieved new weather data: {weather}, sunrise: {sunrise}, sunset: {sunset}"
    )

    # Send data over UART
    uart.write(bytes(
        f"!W:{'Clear'}^{cpy_datetime.datetime(2009, 1, 1, hour=6, minute=0, second=0)}^{cpy_datetime.datetime(2009, 1, 1, hour=18, minute=0, second=0)};", "ascii"))
    logger.debug(f"UART <-- !W:{weather}^{sunrise}^{sunset};")


def response_time():
    """Sends the current time over UART"""

    uart.write(bytes(f"!T:{cpy_datetime.datetime.now()};", "ascii"))
    logger.debug(f"UART <-- !T:{cpy_datetime.datetime.now()};")


def main():
    """Main loop of the program. Reads UART lines for requests and sends the 
    appropriate responses."""
    
    request_started = False
    
    # Keep listening for requests
    while True:
        
        # Read byte from UART
        byte_read = uart.read(1)

        if not byte_read:
            continue

        # Start of request. Don't save '?'.
        if byte_read == b"?":
            request = []
            request_started = True
            continue

        if request_started:
            
            # Check for end of request. Don't save ';'.
            if byte_read == b";":
                request_started = False

                # Parse request
                request_parts = "".join(request).split("^")
                
                # Weather request
                if request_parts[0].startswith("W"):
                    response_weather()

                # Time request
                elif request_parts[0].startswith("T"):
                    response_time()

                # Notification request
                elif request_parts[0].startswith("N:"):
                    title = request_parts[0][2:]
                    data = request_parts[1]
                    tags = request_parts[2]
                    send_notification(title=title, data=data, tags=tags)
                    uart.write(bytes(f"!N;", "ascii"))
            
            # Else, accumulate response bytes.
            else:
                request.append(chr(byte_read[0]))


if __name__ == "__main__":
    main()
