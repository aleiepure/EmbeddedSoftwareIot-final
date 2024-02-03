########################################################
#
#   Embedded Systems for IoT, University of Trento
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

import gc
import rtc
from adafruit_datetime import datetime as cpy_datetime

import src.hardware as hardware
from src.state_machine import StateMachine
from src.logger import logger


def request_time() -> None:
    """
    Sends request for time to the other microcontroller via UART and waits for 
    the response.
    Request format: '?T;', response format: '!T:YYYY-MM-DD HH:MM:SS;'

    Args:
        None
    Returns:
        None
    """

    # Send request
    hardware.uart.write(bytes(f"?T;", "ascii"))
    logger.info("Sent time request, waiting for response...")

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

                if "".join(response).startswith("T"):
                    date_time = cpy_datetime.fromisoformat(
                        "".join(response)[2:])
                    rtc.RTC().datetime = date_time.timetuple()
                    logger.info(f"Received time: {date_time}")
                    done = True
            
            # Else, accumulate response bytes.
            else:
                response.append(chr(byte_read[0]))


def main() -> None:
    """Main function and loop. Initializes state machine and keeps running it."""

    # Request time from the other microcontroller
    request_time()

    state_machine = StateMachine()
    logger.info("Initialized state machine")

    while True:
        
        # Collect garbage, frees idling memory
        gc.collect()
        
        # Update state machine
        state_machine.go_to()
        state_machine.update()


if __name__ == "__main__":
    main()
