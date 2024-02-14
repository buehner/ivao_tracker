from datetime import datetime
from typing import List

from msgspec import Struct
from sqlmodel import SQLModel


class JsonPilot(Struct):
    userId: int
    callsign: str


class JsonAtc(Struct):
    userId: int
    callsign: str


class JsonClients(Struct):
    pilots: List[JsonPilot]
    atcs: List[JsonAtc]


class JsonServer(Struct):
    id: str
    hostname: str
    ip: str
    description: str
    countryId: str
    currentConnections: int
    maximumConnections: int


class JsonConnectionStats(Struct):
    total: int
    supervisor: int
    atc: int
    observer: int
    pilot: int
    worldTour: int
    followMe: int


class JsonSnapshot(Struct):
    updatedAt: datetime
    servers: List[JsonServer]
    connections: JsonConnectionStats
    clients: JsonClients
