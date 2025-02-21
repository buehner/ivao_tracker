from datetime import datetime
from typing import Any, List, Optional

from geoalchemy2 import Geometry
from msgspec import Struct
from sqlmodel import ARRAY, Column, Field, Relationship, SQLModel, String


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


# SQL MODELS


class Snapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    updatedAt: datetime
    total: int
    supervisor: int
    atc: int
    observer: int
    pilot: int
    worldTour: int
    followMe: int


class UserSessionBase(SQLModel):
    userId: int
    callsign: str
    serverId: str
    softwareTypeId: str
    softwareVersion: str
    rating: int
    createdAt: datetime
    time: int


class Aircraft(SQLModel, table=True):
    icaoCode: Optional[str] = Field(default=None, primary_key=True)
    model: str
    wakeTurbulence: str
    isMilitary: Optional[bool]
    description: str
    flightplans: List["FlightPlan"] = Relationship(back_populates="aircraft")


class FlightPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pilotSessionId: int = Field(foreign_key="pilotsession.id")
    # pilotSession: "PilotSession" = Relationship(back_populates="flightplan")
    aircraftId: str = Field(foreign_key="aircraft.icaoCode")
    aircraft: Aircraft = Relationship(back_populates="flightplans")
    revision: int
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
    aircraftEquipments: str
    aircraftTransponderTypes: str


class Atis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lines: List[str] = Field(sa_column=Column(ARRAY(String)))
    revision: str
    timestamp: datetime
    atcSession: "AtcSession" = Relationship(back_populates="atis")


class PilotSession(UserSessionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flightPlanId: int = Field(foreign_key="flightplan.id")
    # flightplan: FlightPlan = Relationship(back_populates="pilotSession")
    simulatorId: Optional[str]
    textureId: Optional[int]
    tracks: List["PilotTrack"] = Relationship(back_populates="pilotSession")


class AtcSession(UserSessionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    atisId: int = Field(foreign_key="atis.id")
    atis: Atis = Relationship(back_populates="atcSession")
    simulatorId: Optional[str]
    textureId: Optional[int]
    tracks: List["AtcTrack"] = Relationship(back_populates="atcSession")


class PilotTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pilotSessionId: int = Field(foreign_key="pilotsession.id")
    pilotSession: PilotSession = Relationship(back_populates="tracks")
    # previousTrackId: Optional[int] = Field(
    #     default=None, foreign_key="pilottrack.id"
    # )
    # nextTrackId: Optional[int] = Field(
    #     default=None, foreign_key="pilottrack.id"
    # )
    # previousTrack: Optional["PilotTrack"] = Relationship(
    #     back_populates="nextTrack"
    # )
    # nextTrack: Optional["PilotTrack"] = Relationship(
    #     back_populates="previousTrack"
    # )
    altitude: int
    altitudeDifference: int
    arrivalDistance: Optional[float]
    departureDistance: Optional[float]
    groundSpeed: int
    heading: int
    onGround: bool
    state: str
    timestamp: datetime
    transponder: int
    transponderMode: str
    time: int
    geometry: Any = Field(
        sa_column=Column(Geometry("POINT", srid=4326, spatial_index=True))
    )


class AtcTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    atcSessionId: int = Field(foreign_key="atcsession.id")
    atcSession: AtcSession = Relationship(back_populates="tracks")
    geometry: Any = Field(
        sa_column=Column(Geometry("POINT", srid=4326, spatial_index=True))
    )
