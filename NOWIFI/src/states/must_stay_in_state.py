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

import src.hardware as hardware
from src.logger import logger
from src.states.state import State


class must_stay_in_state(State):
    """State in which the dog must stay in."""

    def __init__(self, state_machine) -> None:
        self.logger = logger
        self.state_machine = state_machine

    def enter(self) -> None:
        """Called when the state is entered."""

        self.logger.info('Entered "must stay in" state')
        self.status_changes = 0

        # Lock doors
        self.state_machine.lock_door_out(True)
        self.state_machine.lock_door_in(True)

        # LEDs white
        hardware.pixels.fill((255, 255, 255))
        hardware.pixels.show()

    def update(self) -> None:
        """Called periodically to update the state."""

        rfid_status = self.state_machine.read_RFID()

        # Parse RFID status reading
        if rfid_status == 200:

            # Correct tag read, unlock door inwards
            # LEDs green
            hardware.pixels.fill((0, 255, 0))
            hardware.pixels.show()
            self.state_machine.lock_door_in(False)

            # Sense the door for movement, send notification if dog is trying to
            # go out, update dog status if it is going inside
            self.logger.info('Sensing door...')
            if self.state_machine.door_open():
                self.state_machine.send_notification(
                    title='Dog is trying to go out',
                    data="It's dark outside, the dog should stay in",
                    tags='first_quarter_moon_with_face')
            else:
                self.status_changes += 1
                self.state_machine.dog_in = True
                self.logger.debug(
                    f'Dog status changed: now is {"in" if self.state_machine.dog_in else "out"}')

        elif rfid_status == 400:
            # Unknown tag read, send notification
            self.state_machine.send_notification(
                title='Error: unknown ID badge',
                data='An unknown ID badge has been scanned',
                tags='x')

            # LEDs red
            hardware.pixels.fill((255, 0, 0))
            hardware.pixels.show()

        elif rfid_status == 500:
            # Timeout reached, no tag read
            self.logger.info('RFID timeout reached')
            
            # Lock doors
            self.state_machine.lock_door_in(True)
            self.state_machine.lock_door_out(True)

            # LEDs white
            hardware.pixels.fill((255, 255, 255))
            hardware.pixels.show()

    def exit(self) -> None:
        self.logger.info('Exiting "must stay in" state')
