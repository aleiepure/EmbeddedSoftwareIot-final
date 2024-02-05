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

import time as py_time

from adafruit_datetime import datetime as cpy_datetime, timedelta as cpy_timedelta

from src.logger import logger
import src.hardware as hardware
from src.states.must_stay_in_state import must_stay_in_state
from src.states.free_in_out_state import free_in_out_state
from src.states.eating_state import eating_state
from src.states.must_stay_out_state import must_stay_out_state


class StateMachine:
    """State machine class. It is responsible for switching between states."""

    dog_in = True

    def __init__(self):

        self.logger = logger
        self.state = 0
        self.states = [
            must_stay_in_state(self),
            free_in_out_state(self),
            eating_state(self),
            must_stay_out_state(self),
        ]

        self.weather, self.sunrise_date, self.sunset_date = self._get_weather()
        self.temperature = hardware.sht.temperature

        # Date unused, only time is important
        self.midnight = cpy_datetime(year=1970, month=1, day=1, hour=0)
        self.breakfast = cpy_datetime(year=1970, month=1, day=1, hour=9)
        self.lunch = cpy_datetime(year=1970, month=1, day=1, hour=13)
        self.dinner = cpy_datetime(year=1970, month=1, day=1, hour=20)

    def go_to(self) -> None:
        """
        Reads the current time from rtc and uses it to determine in which state 
        to switch. Additionally, between 00:00 and 00:10, it updates the weather
        if needed.

        Args:
            None
        Returns:
            None
        """

        time = cpy_datetime.now().time()
        self.logger.info(f'Using time {time}')

        # Weather update
        if (time >= self.midnight.time() and
                time < (self.midnight + cpy_timedelta(minutes=10)).time() and
                cpy_datetime.now().date() != self.sunrise_date.date()

                ):
            self.weather, sunrise_new, sunset_new = self._get_weather()

            if self.weather and sunrise_new and sunset_new:
                if self.sunrise_date.date() != sunrise_new.date():
                    self.sunrise_date = sunrise_new
                    self.sunset_date = sunset_new
                    self.logger.info(
                        f'Weather updated: {self.weather}, sunrise: {self.sunrise_date}, sunset: {self.sunset_date}')

        # State switching, could use a match case statement but it is not supported
        # on python 3.4 running on the microcontroller
        if (time >= self.midnight.time() and time < self.sunrise_date.time()):

            # Switch to 'must stay in' state
            self._switch_state(0)

        if (time >= self.sunrise_date.time() and time < self.breakfast.time()):

            # Switch to 'free in/out' state
            self._switch_state(1)

        if (time >= self.breakfast.time() and
                time < (self.breakfast + cpy_timedelta(minutes=30)).time()):

            # Switch to 'eating' state
            self._switch_state(2)

        if (time >= (self.breakfast + cpy_timedelta(minutes=30)).time() and
                time < self.lunch.time()):

            # Switch to 'must stay out' state
            self._switch_state(3)

        if (time >= self.lunch.time() and
                time < (self.lunch + cpy_timedelta(minutes=30)).time()):

            # Switch to 'eating' state
            self._switch_state(2)

        if (time >= (self.lunch + cpy_timedelta(minutes=30)).time() and
                time < self.sunset_date.time()):

            # Switch to 'must stay out' state
            self._switch_state(3)

        if (time >= self.sunset_date.time() and
                time < self.dinner.time()):

            # Switch to 'free in/out' state
            self._switch_state(1)

        if (time >= self.dinner.time() and
                time < (self.dinner + cpy_timedelta(minutes=30)).time()):

            # Switch to 'eating' state
            self._switch_state(2)

        if (time >= (self.dinner + cpy_timedelta(minutes=30)).time() and
                time < self.midnight.time()):

            # Switch to 'must stay in' state
            self._switch_state(0)

    def update(self) -> None:
        """
        Updates the temperature and calls the update method of the current state.
        """

        self.temperature = hardware.sht.temperature
        self.logger.info(f"Temperature: {self.temperature}")

        self.states[self.state].update()

    def _switch_state(self, new_state: int) -> None:
        """
        Switches to the new state, calling the exit method of the current state
        and the enter method of the new state. Only done if needed.

        Args:
            new_state: int, new state to switch to
        Returns:
            None
        """

        if self.state != new_state:
            self.states[self.state].exit()
            self.state = new_state
            self.states[self.state].enter()
            self.logger.info(f'Switched to state {self.state}')

    def _get_weather(self):
        """
        Sends request for the weather, sunrise and sunset to the other microcontroller
        via UART, waits for the response and returns the data in the order above.
        Request format: '?W;', response format: '!W:weather^YYYY-MM-DD HH:MM:SS^YYYY-MM-DD HH:MM:SS;'

        Args:
            None
        Returns:
            weather: str, weather description
            sunrise_date: datetime, sunrise time
            sunset_date: datetime, sunset time
        """

        # Send request
        hardware.uart.write(bytes("?W;", "ascii"))
        logger.info("Sent weather request, waiting for response...")

        # Wait for response
        done = False
        while not done:

            # Read byte from UART
            byte_read = hardware.uart.read(1)

            if not byte_read:
                continue

            # Start of response. Don't save '!'.
            if byte_read == b"!":
                response = []
                response_started = True
                continue

            if response_started:

                # Check for end of response. Don't save ';'.
                if byte_read == b";":
                    response_started = False

                    # Check for error response
                    if (response == 'W:E'):
                        self.logger.error('Error response received')
                        return None, None, None

                    # Parse response
                    response_parts = "".join(response).split("^")
                    if response_parts[0].startswith("W"):
                        weather = response_parts[0][2:]
                        sunrise_date = cpy_datetime.fromisoformat(
                            response_parts[1])
                        sunset_date = cpy_datetime.fromisoformat(
                            response_parts[2])
                        done = True

                # Else, accumulate response bytes.
                else:
                    response.append(chr(byte_read[0]))

        return weather, sunrise_date, sunset_date

    def send_notification(self, title: str, data, tags: str = "") -> None:
        """
        Sends request for sending a notification to the other microcontroller via UART.
        Does not wait for a response. Format: '?N:title^data^tags;'

        Args:
            title: str, title of the notification
            data: str, data of the notification
            tags: str, tags of the notification, comma separated
        Returns:
            None
        """

        hardware.uart.write(bytes(f"?N:{title}^{data}^{tags};", "ascii"))
        self.logger.info(f"Sent notification request: {title}, {data}, {tags}")

    def read_RFID(self) -> int:
        """
        Tries reading an RFID tag for 5 seconds. It returns 200 if the correct
        tag is detected, 400 if a wrong tag is detected and 500 if no tag is
        detected.

        Args:
            None
        Returns:
            int, 200, 400 or 500
        """

        # Start timer
        self.start_monoton = py_time.monotonic()
        self.logger.info('Started RFID scan...')

        # Keep reading for 5 seconds
        while py_time.monotonic() - self.start_monoton < 5:

            # Check for a card
            (status, _) = hardware.rfid.request(hardware.rfid.REQALL)

            if status == hardware.rfid.OK:

                # Card detected, start reading
                self.logger.debug('RFID: a card detected, start reading...')
                (status, raw_uid) = hardware.rfid.anticoll()

                if status == hardware.rfid.OK:
                    self.logger.debug('RFID: card read, determining id...')
                    rfid_data = "{:02x}{:02x}{:02x}{:02x}".format(raw_uid[0],
                                                                  raw_uid[1],
                                                                  raw_uid[2],
                                                                  raw_uid[3]
                                                                  )
                    self.logger.debug(f'RFID: read id is {rfid_data}')

                    # Parse id
                    if rfid_data == "d951c359":
                        self.logger.info('RFID: correct id detected')
                        return 200
                    else:
                        self.logger.info('RFID: wrong id detected')
                        return 400

        # Timeout reached
        self.logger.info('RFID: no card detected')
        return 500

    def door_open(self) -> bool:
        """
        Reads the force sensor for 5 seconds to determine if the door was open.

        Args:
            None
        Returns:
            bool, True if the door was open, False otherwise
        """

        # Start timer
        start_time = py_time.monotonic()

        # Count times the door was open
        times_opened = 0
        while py_time.monotonic() - start_time < 5:
            if hardware.flex.value > 600 and hardware.flex.value < 800:
                times_opened += 1

        # Return result
        if times_opened > 10:
            return True
        else:
            return False

    def lock_door_in(self, lock: bool) -> None:
        """
        Locks or unlocks the door inwards.

        Args:
            lock: bool, True to lock, False to unlock
        Returns:
            None
        """

        if lock and hardware.motor_in.angle != 0:
            hardware.motor_in.angle = 0
            self.logger.info('Door in locked')
        elif not lock and hardware.motor_in.angle != 180:
            hardware.motor_in.angle = 180
            self.logger.info('Door in unlocked')

    def lock_door_out(self, lock: bool) -> None:
        """
        Locks or unlocks the door outwards.

        Args:
            lock: bool, True to lock, False to unlock
        Returns:
            None
        """

        if lock and hardware.motor_out.angle != 0:
            hardware.motor_out.angle = 0
            self.logger.info('Door out locked')
        elif not lock and hardware.motor_out.angle != 180:
            hardware.motor_out.angle = 180
            self.logger.info('Door out unlocked')
