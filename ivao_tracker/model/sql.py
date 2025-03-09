from datetime import datetime
from typing import Any, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import (
    ARRAY,
    Column,
    Enum,
    Field,
    Integer,
    Relationship,
    SmallInteger,
    SQLModel,
    String,
    func,
)

from ivao_tracker.model.constants import (
    AirportType,
    Continent,
    State,
    TransponderMode,
    WakeTurbulence,
)

# SQL MODELS


class Airport(SQLModel, table=True):
    id: Optional[int]
    is_fixed: bool = Field(default=False, index=True)
    code: str = Field(primary_key=True)
    ident: str = Field(index=True)
    gps_code: str | None = Field(index=True)
    local_code: str | None = Field(index=True)
    icao_code: str | None
    iata_code: str | None
    keywords: str | None = Field(index=True)
    name: str | None
    type: AirportType = Field(
        sa_column=Column(
            Enum(AirportType, name="airport_type_enum", create_type=True)
        )
    )
    continent: Continent = Field(
        sa_column=Column(
            Enum(Continent, name="continent_enum", create_type=True)
        )
    )
    country_name: str | None
    iso_country: str | None
    region_name: str | None
    iso_region: str | None
    local_region: str | None
    elevation_ft: int | None = Field(sa_column=Column(SmallInteger))
    municipality: str | None
    scheduled_service: bool | None
    home_link: str | None
    wikipedia_link: str | None
    score: int | None
    last_updated: datetime | None
    geom: str | None = Field(
        sa_column=Column(Geometry("POINT", srid=4326, spatial_index=True))
    )


class SnapshotPilotSessionLink(SQLModel, table=True):
    snapshotId: Optional[int] = Field(
        default=None, foreign_key="snapshot.id", primary_key=True
    )
    pilotsessionId: Optional[int] = Field(
        default=None, foreign_key="pilotsession.id", primary_key=True
    )
    created_at: Optional[datetime] = Field(
        sa_column_kwargs={"server_default": func.now()}
    )


class Snapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    updatedAt: datetime
    total: int = Field(sa_column=Column(SmallInteger))
    supervisor: int = Field(sa_column=Column(SmallInteger))
    atc: int = Field(sa_column=Column(SmallInteger))
    observer: int = Field(sa_column=Column(SmallInteger))
    pilot: int = Field(sa_column=Column(SmallInteger))
    worldTour: int = Field(sa_column=Column(SmallInteger))
    followMe: int = Field(sa_column=Column(SmallInteger))
    pilotSessions: List["PilotSession"] = Relationship(
        back_populates="snapshots", link_model=SnapshotPilotSessionLink
    )


class UserSessionBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    isActive: bool = Field(default=True, nullable=False, index=True)
    userId: int
    callsign: str = Field(index=True)
    serverId: str
    softwareTypeId: str
    softwareVersion: str
    createdAt: datetime


class Aircraft(SQLModel, table=True):
    icaoCode: Optional[str] = Field(default=None, primary_key=True)
    model: str
    wakeTurbulence: WakeTurbulence = Field(
        sa_column=Column(
            Enum(WakeTurbulence, name="wake_turbulence_enum", create_type=True)
        )
    )
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
    departure: Optional[Airport] = Relationship(
        sa_relationship=RelationshipProperty(
            "Airport",
            back_populates=None,
            foreign_keys="[FlightPlan.departureId]",
        )
    )
    departureId: Optional[str] = Field(
        default=None, foreign_key="airport.code"
    )
    arrival: Optional[Airport] = Relationship(
        sa_relationship=RelationshipProperty(
            "Airport",
            back_populates=None,
            foreign_keys="[FlightPlan.arrivalId]",
        )
    )
    arrivalId: Optional[str] = Field(default=None, foreign_key="airport.code")
    alternative: Optional[Airport] = Relationship(
        sa_relationship=RelationshipProperty(
            "Airport",
            back_populates=None,
            foreign_keys="[FlightPlan.alternativeId]",
        )
    )
    alternativeId: Optional[str] = Field(
        default=None, foreign_key="airport.code"
    )
    alternative2: Optional[Airport] = Relationship(
        sa_relationship=RelationshipProperty(
            "Airport",
            back_populates=None,
            foreign_keys="[FlightPlan.alternative2Id]",
        )
    )
    alternative2Id: Optional[str] = Field(
        default=None, foreign_key="airport.code"
    )
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
    taxiTime: Optional[datetime]
    takeoffTime: Optional[datetime]
    approachTime: Optional[datetime]
    landingTime: Optional[datetime]
    onBlocksTime: Optional[datetime]
    disconnectTime: Optional[datetime]
    simulatorId: Optional[str]
    textureId: Optional[int]
    rating: int = Field(sa_column=Column(SmallInteger))
    tracks: List["PilotTrack"] = Relationship(back_populates="pilotSession")
    flightplans: List["FlightPlan"] = Relationship(
        back_populates="pilotSession"
    )
    snapshots: List["Snapshot"] = Relationship(
        back_populates="pilotSessions", link_model=SnapshotPilotSessionLink
    )


class AtcSession(UserSessionBase, table=True):
    atis: "Atis" = Relationship(
        back_populates="atcSession", sa_relationship_kwargs={"uselist": False}
    )
    simulatorId: Optional[str]
    textureId: Optional[int]
    rating: int = Field(sa_column=Column(SmallInteger))
    tracks: List["AtcTrack"] = Relationship(back_populates="atcSession")


class PilotTrack(SQLModel, table=True):
    __table_args__ = {"postgresql_partition_by": "RANGE (timestamp)"}
    id: int = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    timestamp: datetime = Field(sa_column=Column(TIMESTAMP, primary_key=True))
    pilotSessionId: int = Field(foreign_key="pilotsession.id", index=True)
    pilotSession: PilotSession = Relationship(back_populates="tracks")
    altitude: int
    groundSpeed: int
    heading: int = Field(sa_column=Column(SmallInteger))
    onGround: bool
    state: State = Field(
        sa_column=Column(Enum(State, name="state_enum", create_type=True))
    )
    transponder: int
    transponderMode: TransponderMode = Field(
        sa_column=Column(
            Enum(
                TransponderMode, name="transponder_mode_enum", create_type=True
            )
        )
    )
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
