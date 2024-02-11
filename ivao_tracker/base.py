"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

from datetime import datetime
from typing import List
from urllib.request import urlopen

from msgspec import Struct, json

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


def get_ivao_snapshot():
    with urlopen(IVAO_WHAZZUP_URL) as url:
        json_data = url.read()
        snapshot = json.decode(json_data, type=Snapshot)
        return snapshot
