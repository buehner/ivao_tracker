from datetime import datetime
from typing import Any, List, Optional

from geoalchemy2 import Geometry
from sqlmodel import ARRAY, Column, Field, Relationship, SQLModel, String

# SQL MODELS


class SnapshotPilotSessionLink(SQLModel, table=True):
    snapshotId: Optional[int] = Field(
        default=None, foreign_key="snapshot.id", primary_key=True
    )
    pilotsessionId: Optional[int] = Field(
        default=None, foreign_key="pilotsession.id", primary_key=True
    )


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
    pilotSessions: List["PilotSession"] = Relationship(
        back_populates="snapshots", link_model=SnapshotPilotSessionLink
    )


class UserSessionBase(SQLModel):
    userId: int
    callsign: str = Field(index=True)
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
    pilotSession: Optional["PilotSession"] = Relationship(
        back_populates="flightplans"
    )
    pilotSessionId: Optional[int] = Field(
        default=None, foreign_key="pilotsession.id"
    )
    aircraft: Optional["Aircraft"] = Relationship(back_populates="flightplans")
    aircraftIcao: Optional[str] = Field(
        default=None, foreign_key="aircraft.icaoCode"
    )
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
    atcSession: "AtcSession" = Relationship(
        back_populates="atis", sa_relationship_kwargs={"uselist": False}
    )
    atcSessionId: int = Field(default=None, foreign_key="atcsession.id")


class PilotSession(UserSessionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flightplans: List["FlightPlan"] = Relationship(
        back_populates="pilotSession"
    )
    simulatorId: Optional[str]
    textureId: Optional[int]
    tracks: List["PilotTrack"] = Relationship(back_populates="pilotSession")
    snapshots: List["Snapshot"] = Relationship(
        back_populates="pilotSessions", link_model=SnapshotPilotSessionLink
    )


class AtcSession(UserSessionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    atis: "Atis" = Relationship(
        back_populates="atcSession", sa_relationship_kwargs={"uselist": False}
    )
    simulatorId: Optional[str]
    textureId: Optional[int]
    tracks: List["AtcTrack"] = Relationship(back_populates="atcSession")


class PilotTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pilotSession: PilotSession = Relationship(back_populates="tracks")
    pilotSessionId: int = Field(foreign_key="pilotsession.id", index=True)
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
