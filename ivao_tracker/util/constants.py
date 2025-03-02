from enum import Enum


class State(Enum):
    BOARDING = "Boarding"
    DEPARTING = "Departing"
    INITIAL_CLIMB = "Initial Climb"
    EN_ROUTE = "En Route"
    APPROACH = "Approach"
    LANDED = "Landed"
    ON_BLOCKS = "On Blocks"
