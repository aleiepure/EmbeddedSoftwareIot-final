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

class State:
    """Base class for all states."""

    def __init__(self) -> None:
        pass

    def enter(self) -> None:
        """Called when the state is entered."""

        pass

    def exit(self) -> None:
        """Called when the state is exited."""

        pass

    def update(self) -> None:
        """Called periodically to update the state."""

        pass
