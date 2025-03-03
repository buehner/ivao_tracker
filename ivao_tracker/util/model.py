import logging

from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.constants import State, TransponderMode, WakeTurbulence
from ivao_tracker.model.sql import (
    Aircraft,
    FlightPlan,
    PilotSession,
    PilotTrack,
    Snapshot,
)

setup_logging()
logger = logging.getLogger(__name__)


def json2sqlSnapshot(jsonSnapshot):
    stats = jsonSnapshot.connections
    snapshot = Snapshot(
        updatedAt=jsonSnapshot.updatedAt,
        total=stats.total,
        supervisor=stats.supervisor,
        atc=stats.atc,
        observer=stats.observer,
        pilot=stats.pilot,
        worldTour=stats.worldTour,
        followMe=stats.followMe,
        pilotSessions=[],
    )

    return snapshot


def json2sqlPilotSession(jsonPilot):
    flightplans = []
    if jsonPilot.flightPlan:
        fp = jsonPilot.flightPlan
        if fp.aircraft:
            aircraft = createAircraft(fp)
        else:
            aircraft = None
        flightplan = createFlightplan(jsonPilot.id, fp, aircraft)
        flightplans.append(flightplan)

    tracks = []
    if jsonPilot.lastTrack:
        lt = jsonPilot.lastTrack
        track = PilotTrack(
            altitude=lt.altitude,
            groundSpeed=lt.groundSpeed,
            heading=lt.heading,
            onGround=lt.onGround,
            state=State(lt.state),
            timestamp=lt.timestamp,
            transponder=lt.transponder,
            transponderMode=TransponderMode(lt.transponderMode),
            geometry=f"SRID=4326;POINT({lt.longitude} {lt.latitude})",
        )
        tracks.append(track)

    pilotSession = PilotSession(
        id=jsonPilot.id,
        isActive=True,
        userId=jsonPilot.userId,
        callsign=jsonPilot.callsign,
        serverId=jsonPilot.serverId,
        softwareTypeId=jsonPilot.softwareTypeId,
        softwareVersion=jsonPilot.softwareVersion,
        rating=jsonPilot.rating,
        createdAt=jsonPilot.createdAt,
        simulatorId=jsonPilot.pilotSession.simulatorId,
        textureId=jsonPilot.pilotSession.textureId,
        flightplans=flightplans,
        tracks=tracks,
        snapshots=[],
    )

    return pilotSession


def createAircraft(fp):
    ac = fp.aircraft
    aircraft = Aircraft(
        icaoCode=ac.icaoCode,
        model=ac.model,
        wakeTurbulence=WakeTurbulence(ac.wakeTurbulence),
        isMilitary=ac.isMilitary,
        description=ac.description,
    )

    return aircraft


def createFlightplan(pilotSessionId, fp, aircraft):
    flightplan = FlightPlan(
        id=fp.id,
        pilotSessionId=pilotSessionId,
        revision=fp.revision,
        aircraftId=fp.aircraftId,
        aircraftNumber=fp.aircraftNumber,
        departureId=fp.departureId,
        arrivalId=fp.arrivalId,
        alternativeId=fp.alternativeId,
        alternative2Id=fp.alternative2Id,
        route=fp.route,
        remarks=fp.remarks,
        speed=fp.speed,
        level=fp.level,
        flightRules=fp.flightRules,
        eet=fp.eet,
        endurance=fp.endurance,
        departureTime=fp.departureTime,
        actualDepartureTime=fp.actualDepartureTime,
        peopleOnBoard=fp.peopleOnBoard,
        createdAt=fp.createdAt,
        aircraft=aircraft,
        aircraftEquipments=fp.aircraftEquipments,
        aircraftTransponderTypes=fp.aircraftTransponderTypes,
    )

    return flightplan
