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
from src.states.state import State
from src.logger import logger


class eating_state(State):
    """State in which the dog is eating."""

    def __init__(self, state_machine) -> None:
        self.logger = logger
        self.state_machine = state_machine

    def enter(self) -> None:
        """Called when the state is entered."""

        self.logger.info('Entered "eating" state')
        self.status_changes = 0

        # Lock doors
        self.state_machine.lock_door_in(True)
        self.state_machine.lock_door_out(True)

        # LEDs orange
        hardware.pixels.fill((253, 112, 57))
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

            if (self.state_machine.weather in ['Clear', 'Clouds', 'Drizzle'] and
                    self.state_machine.temperature > 5.0 and
                    self.state_machine.temperature < 32.0):

                self.logger.info('Weather OK, dog can go out')
                self.state_machine.lock_door_out(False)

            # Sense the door for movement, update dog status if needed
            self.logger.info('Sensing door...')
            if self.state_machine.door_open():
                self.logger.info('Door opened')
                self.state_machine.dog_in = not self.state_machine.dog_in
                self.status_changes += 1
                self.logger.debug(
                    f'Dog status changed: now is {"in" if self.state_machine.dog_in else "out"}')

        elif rfid_status == 400:
            # Unknown tag read, send notification
            self.state_machine.send_notification(
                title='Error: unknown ID badge',
                data='An unknown ID badge has been scanned',
                tags='x')
            self.logger.info('Unknown ID badge detected')

            # LEDs red
            hardware.pixels.fill((255, 0, 0))
            hardware.pixels.show()

        elif rfid_status == 500:
            # Timeout reached, no tag read
            self.logger.info('RFID timeout reached')

            # Lock doors
            self.state_machine.lock_door_in(True)
            self.state_machine.lock_door_out(True)

            # LEDs cyan
            hardware.pixels.fill((0, 255, 255))
            hardware.pixels.show()

    def exit(self) -> None:
        """Called when the state is exited."""

        if self.status_changes == 0 and self.state_machine.dog_in:
            self.state_machine.send_notification(
                title="Its time to go out!",
                data="Food time has ended and dog is still inside",
                tags='alarm_clock'
            )
        elif self.status_changes == 0 and not self.state_machine.dog_in:
            self.state_machine.send_notification(
                title="Food time is over!",
                data="...but dog has not eaten",
                tags='worried'
            )
            
        self.logger.info('Exiting "eating" state')
