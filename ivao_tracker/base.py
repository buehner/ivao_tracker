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
from sqlmodel import Session

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
            # logger.exception("Problem while executing repetitive task.")
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
        logger.info(msgTpl.format(duration))
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
        session = Session(engine)

        snapshot = json2sqlSnapshot(jsonSnapshot)
        session.add(snapshot)

        for jsonPilot in jsonSnapshot.clients.pilots:
            pilotSessionRaw = json2sqlPilotSession(jsonPilot)
            pilotSession = session.get(PilotSession, jsonPilot.id)
            if pilotSession is None:
                pilotSession = pilotSessionRaw

                # use aircrafts from db
                for fp in pilotSession.flightplans:
                    if fp.aircraft and fp.aircraft.icaoCode:
                        ac = session.get(Aircraft, fp.aircraft.icaoCode)
                        if ac:
                            fp.aircraft = ac

                session.add(pilotSession)
                snapshot.pilotSessions.append(pilotSession)
                logger.debug("Created new pilot session " + jsonPilot.callsign)
            else:
                for fp in pilotSessionRaw.flightplans:
                    if not any(
                        sessionFp.id == fp.id
                        for sessionFp in pilotSession.flightplans
                    ):
                        if fp.aircraft and fp.aircraft.icaoCode:
                            ac = session.get(Aircraft, fp.aircraft.icaoCode)
                            if ac:
                                fp.aircraft = ac
                        fp.pilotSession = pilotSession
                        pilotSession.flightplans.append(fp)
                        logger.debug(
                            "Appended a new flightplan for "
                            + pilotSession.callsign
                        )

                pilotSession.time = pilotSessionRaw.time
                pilotSession.textureId = pilotSessionRaw.textureId
                pilotSession.snapshots.append(snapshot)
                session.merge(pilotSession)

        session.commit()
        session.close()

        end = timer()
        duration = end - start
        msgTpl = "Updated DB in {:.2f}s"
        logger.info(msgTpl.format(duration))

        lastSnapshot = jsonSnapshot.updatedAt


def track_snapshots(interval):
    threading.Thread(
        target=lambda: every(interval, import_ivao_snapshot)
    ).start()
