"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
here you put your main classes and objects.

Be creative! do whatever you want!

If you want to replace this with a Flask application run:

    $ make init

and then choose `flask` as template.
"""

from datetime import datetime
from typing import List

from msgspec import Struct

# the IVAO whazzup url
IVAO_WHAZZUP_URL = "https://api.ivao.aero/v2/tracker/whazzup"


class Pilot(Struct):
    userId: int
    callsign: str


class Atc(Struct):
    userId: int
    callsign: str


class Clients(Struct):
    pilots: List[Pilot]
    atcs: List[Atc]


class Server(Struct):
    id: str
    hostname: str
    ip: str
    description: str
    countryId: str
    currentConnections: int
    maximumConnections: int


class ConnectionStats(Struct):
    total: int
    supervisor: int
    atc: int
    observer: int
    pilot: int
    worldTour: int
    followMe: int


class Snapshot(Struct):
    updatedAt: datetime
    servers: List[Server]
    connections: ConnectionStats
    clients: Clients
