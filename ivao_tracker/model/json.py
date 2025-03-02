from datetime import datetime
from typing import List, Optional

from msgspec import Struct

# JSON models (whazzup file)


class JsonAircraft(Struct, frozen=True):
    icaoCode: str
    model: str
    wakeTurbulence: str
    isMilitary: Optional[bool]
    description: str


class JsonFlightPlan(Struct, frozen=True):
    id: int
    revision: int
    aircraftId: Optional[str]
    aircraftNumber: int
    departureId: Optional[str]
    arrivalId: Optional[str]
    alternativeId: Optional[str]
    alternative2Id: Optional[str]
    route: str
    remarks: str
    speed: str
    level: str
    flightRules: str
    eet: int
    endurance: int
    departureTime: int
    actualDepartureTime: Optional[int]
    peopleOnBoard: int
    createdAt: datetime
    aircraft: JsonAircraft
    aircraftEquipments: str
    aircraftTransponderTypes: str


class JsonLastTrack(Struct, frozen=True):
    altitude: int
    altitudeDifference: int
    arrivalDistance: Optional[float]
    departureDistance: Optional[float]
    groundSpeed: int
    heading: int
    latitude: float
    longitude: float
    onGround: bool
    state: str
    timestamp: datetime
    transponder: int
    transponderMode: str
    time: int


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
    time: int
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
