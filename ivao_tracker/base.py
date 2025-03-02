"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

import logging
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from timeit import default_timer as timer  # pragma: no cover
from urllib.request import urlopen

from msgspec import json
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.json import JsonSnapshot
from ivao_tracker.model.sql import Aircraft, PilotSession
from ivao_tracker.sql import engine
from ivao_tracker.util.model import json2sqlPilotSession, json2sqlSnapshot

setup_logging()
logger = logging.getLogger(__name__)

lastSnapshot = datetime.now(timezone.utc)


# https://gist.github.com/allanfreitas/e2cd0ff49bbf7ddf1d85a3962d577dbf
def every(delay, task):
    next_time = time.time() + delay
    while True:
        time.sleep(max(0, next_time - time.time()))
        try:
            task()
        except Exception:
            traceback.print_exc()
            # in production code you might want to have this instead of course:
            logger.exception("Problem while executing repetitive task.")
            # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay


def read_ivao_snapshot():
    whazzup_url = config.config["ivao"]["whazzup_url"]
    with urlopen(whazzup_url) as url:
        start = timer()
        json_data = url.read()
        snapshot = json.decode(json_data, type=JsonSnapshot)
        end = timer()
        duration = end - start
        msgTpl = "Parsed whazzup json in {:.2f}s"
        logger.debug(msgTpl.format(duration))
        return snapshot


def import_ivao_snapshot():
    global lastSnapshot
    jsonSnapshot = read_ivao_snapshot()

    snapshotsAreEqual = abs(jsonSnapshot.updatedAt - lastSnapshot) < timedelta(
        microseconds=1
    )

    if snapshotsAreEqual:
        logger.info("No update available")
    else:
        logger.debug("Importing new snapshot")
        start = timer()

        try:
            session = Session(engine)
            with session.no_autoflush:
                snapshot = json2sqlSnapshot(jsonSnapshot)
                session.add(snapshot)

                lastActiveSessions = session.exec(
                    select(PilotSession).where(PilotSession.isActive == True)
                ).all()

                aircrafts = session.exec(select(Aircraft)).all()

                logger.debug(
                    "Found %d last active sessions", len(lastActiveSessions)
                )

                for jsonPilot in jsonSnapshot.clients.pilots:
                    pilotSessionRaw = json2sqlPilotSession(jsonPilot)
                    pilotSession = next(
                        (
                            s
                            for s in lastActiveSessions
                            if s.id == jsonPilot.id
                        ),
                        None,
                    )

                    revivedSession = False
                    if pilotSession is None:
                        # try to revive possible ghost connections
                        pilotSession = session.get(PilotSession, jsonPilot.id)
                        if pilotSession:
                            pilotSession.isActive = True
                            # lastActiveSessions.append(pilotSession)
                            revivedSession = True
                            logger.info(
                                "Revived pilot session %s", pilotSession.id
                            )

                    if pilotSession is None:
                        # no pilotSession in db...
                        pilotSession = createPilotSession(
                            session, snapshot, pilotSessionRaw, aircrafts
                        )
                    else:
                        # we found an existing pilotSession in db
                        mergePilotSession(
                            session,
                            snapshot,
                            pilotSessionRaw,
                            pilotSession,
                            aircrafts,
                        )
                        if revivedSession is False:
                            lastActiveSessions.remove(pilotSession)

                for inactivePilotSession in lastActiveSessions:
                    inactivePilotSession.isActive = False
                    session.merge(inactivePilotSession)
                    logger.debug("Ended session %d", inactivePilotSession.id)

                session.commit()
                session.close()

                end = timer()
                duration = end - start
                msgTpl = "Updated DB in {:.2f}s"
                logger.info(msgTpl.format(duration))

                lastSnapshot = jsonSnapshot.updatedAt
        except SQLAlchemyError as e:
            logger.error("SQL Alchemy Error: %s", str(e))
            session.rollback()

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))


def createPilotSession(session, snapshot, pilotSessionRaw, aircrafts):
    pilotSession = pilotSessionRaw

    # handle flightplan
    for fp in pilotSession.flightplans:
        if fp.aircraft and fp.aircraft.icaoCode:
            ac = next(
                (a for a in aircrafts if a.icaoCode == fp.aircraft.icaoCode),
                None,
            )
            if ac:
                fp.aircraft = ac
            else:
                aircrafts.append(fp.aircraft)

    session.add(pilotSession)
    snapshot.pilotSessions.append(pilotSession)
    logger.debug("Created new pilot session " + pilotSessionRaw.callsign)
    return pilotSession


def mergePilotSession(
    session, snapshot, pilotSessionRaw, pilotSession, aircrafts
):
    for fp in pilotSessionRaw.flightplans:
        # handle flightplans
        if not any(
            sessionFp.id == fp.id for sessionFp in pilotSession.flightplans
        ):
            if fp.aircraft and fp.aircraft.icaoCode:
                ac = next(
                    (
                        a
                        for a in aircrafts
                        if a.icaoCode == fp.aircraft.icaoCode
                    ),
                    None,
                )
                if ac:
                    fp.aircraft = ac
                else:
                    aircrafts.append(fp.aircraft)
            fp.pilotSession = pilotSession
            pilotSession.flightplans.append(fp)
            logger.debug(
                "Appended a new flightplan for " + pilotSession.callsign
            )

    lastState = None
    if len(pilotSession.tracks) > 0:
        lastTrack = pilotSession.tracks[-1]
        lastState = lastTrack.state

    if len(pilotSessionRaw.tracks) > 0:
        newTrack = pilotSessionRaw.tracks[0]
        newTrack.pilotSession = pilotSession
        session.add(newTrack)
        pilotSession.tracks.append(newTrack)
        newState = newTrack.state
        if lastState and lastState != newState:
            if (
                lastState == "Boarding"
                and newState == "Departing"
                and pilotSession.taxiTime is None
            ):
                pilotSession.taxiTime = newTrack.timestamp
                logger.debug("%s started to taxi", pilotSession.callsign)
            elif (
                lastState == "Departing"
                and newState == "Initial Climb"
                and pilotSession.takeoffTime is None
            ):
                pilotSession.takeoffTime = newTrack.timestamp
                logger.debug("%s departed", pilotSession.callsign)
            elif (
                lastState == "En Route"
                and newState == "Approach"
                and pilotSession.approachTime is None
            ):
                pilotSession.approachTime = newTrack.timestamp
                logger.debug("%s is approaching", pilotSession.callsign)
            elif lastState == "Approach" and newState == "Landed":
                pilotSession.landingTime = newTrack.timestamp
                logger.debug("%s landed", pilotSession.callsign)
            elif lastState == "Landed" and newState == "On Blocks":
                pilotSession.onBlocksTime = newTrack.timestamp
                logger.debug("%s is on blocks", pilotSession.callsign)

    pilotSession.textureId = pilotSessionRaw.textureId
    pilotSession.snapshots.append(snapshot)
    session.merge(pilotSession)


def track_snapshots(interval):
    threading.Thread(
        target=lambda: every(interval, import_ivao_snapshot)
    ).start()
