from datetime import datetime
from typing import List, Optional

from msgspec import Struct


class JsonFlightPlan(Struct, frozen=True):
    id: int
    revision: int
    aircraftId: Optional[str]
    aircraftNumber: int
    departureId: Optional[str]
    arrivalId: Optional[str]


class JsonLastTrack(Struct, frozen=True):
    altitude: int
    altitudeDifference: int


class JsonPilotSession(Struct, frozen=True):
    simulatorId: Optional[str]
    textureId: Optional[int]


class JsonAtcSession(Struct, frozen=True):
    frequency: float
    position: str


class JsonAtis(Struct, frozen=True):
    lines: List[str]
    revision: str
    timestamp: datetime


class JsonUser(Struct, frozen=True):
    id: int
    userId: int
    callsign: str
    serverId: str
    softwareTypeId: str
    softwareVersion: str
    rating: int
    createdAt: datetime
    lastTrack: Optional[JsonLastTrack]


class JsonFollowMe(JsonUser, frozen=True):
    pilotSession: JsonPilotSession


class JsonPilot(JsonFollowMe, frozen=True):
    flightPlan: Optional[JsonFlightPlan]


class JsonObserver(JsonUser, frozen=True):
    atcSession: JsonAtcSession


class JsonAtc(JsonObserver, frozen=True):
    atis: Optional[JsonAtis]


class JsonClients(Struct, frozen=True):
    pilots: List[JsonPilot]
    atcs: List[JsonAtc]


class JsonServer(Struct, frozen=True):
    id: str
    hostname: str
    ip: str
    description: str
    countryId: str
    currentConnections: int
    maximumConnections: int


class JsonConnectionStats(Struct, frozen=True):
    total: int
    supervisor: int
    atc: int
    observer: int
    pilot: int
    worldTour: int
    followMe: int


class JsonSnapshot(Struct, frozen=True):
    updatedAt: datetime
    servers: List[JsonServer]
    voiceServers: List[JsonServer]
    connections: JsonConnectionStats
    clients: JsonClients
