import logging

from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.sql import Aircraft, FlightPlan, PilotSession, Snapshot

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
        pilotSessions=[]
    )

    return snapshot


def json2sqlPilotSession(jsonPilot):
    flightplans = []
    if jsonPilot.flightPlan is not None:
        fp = jsonPilot.flightPlan
        if fp.aircraft is not None:
            ac = fp.aircraft
            aircraft = Aircraft(
                icaoCode=ac.icaoCode,
                model=ac.model,
                wakeTurbulence=ac.wakeTurbulence,
                isMilitary=ac.isMilitary,
                description=ac.description,
            )
        else:
            aircraft = None
        flightplan = FlightPlan(
            id=fp.id,
            pilotSessionId=jsonPilot.id,
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
        flightplans.append(flightplan)

    pilotSession = PilotSession(
        id=jsonPilot.id,
        userId=jsonPilot.userId,
        callsign=jsonPilot.callsign,
        serverId=jsonPilot.serverId,
        softwareTypeId=jsonPilot.softwareTypeId,
        softwareVersion=jsonPilot.softwareVersion,
        rating=jsonPilot.rating,
        createdAt=jsonPilot.createdAt,
        time=jsonPilot.time,
        simulatorId=jsonPilot.pilotSession.simulatorId,
        textureId=jsonPilot.pilotSession.textureId,
        flightplans=flightplans,
        snapshots=[]
    )

    return pilotSession
