from enum import Enum


class TransponderMode(Enum):
    N = "N"
    S = "S"
    Y = "Y"


class WakeTurbulence(Enum):
    H = "H"
    J = "J"
    L = "L"
    M = "M"


class Continent(Enum):
    AFRICA = "AF"
    EUROPE = "EU"
    ASIA = "AS"
    NORTH_AMERICA = "NA"
    SOUTH_AMERICA = "SA"
    ANTARCTICA = "AN"
    OCEANIA = "OC"


class AirportType(Enum):
    SMALL_AIRPORT = "small_airport"
    MEDIUM_AIRPORT = "medium_airport"
    LARGE_AIRPORT = "large_airport"
    SEAPLANE_BASE = "seaplane_base"
    HELIPORT = "heliport"
    BALLOONPORT = "balloonport"
    CLOSED = "closed"


class State(Enum):
    BOARDING = "Boarding"
    DEPARTING = "Departing"
    INITIAL_CLIMB = "Initial Climb"
    EN_ROUTE = "En Route"
    APPROACH = "Approach"
    LANDED = "Landed"
    ON_BLOCKS = "On Blocks"


airport_field_map = {
    "departureId": "departure",
    "arrivalId": "arrival",
    "alternativeId": "alternative",
    "alternative2Id": "alternative2",
}

pandas_na_values = [
    "-1.#IND",
    "1.#QNAN",
    "1.#IND",
    "-1.#QNAN",
    "#N/A N/A",
    "#N/A",
    "N/A",
    "n/a",
    # "NA", # excluded because it is a continent code in our csv
    "<NA>",
    "#NA",
    "NULL",
    "null",
    "NaN",
    "-NaN",
    "nan",
    "-nan",
    "None",
    "",
]


airport_fix_map = {
    "X21": "KX21",
    "LKOZ": "CZ-0019",
    "MMIC": "MM81",
    "SSUB": "SDLF",
    "SVID": "SVDM",
    "SVIT": "SVDA",
    "SVPQ": "SVTP",
    "VHHX": "HK-0099",
}
