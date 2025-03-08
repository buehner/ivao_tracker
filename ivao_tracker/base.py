"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

import logging
import re
import ssl
import threading
import time
import traceback
from datetime import UTC, datetime, timedelta
from io import StringIO
from timeit import default_timer as timer  # pragma: no cover
from urllib.request import urlopen

import pandas
from msgspec import json
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, func, select

from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.constants import (
    AirportType,
    Continent,
    State,
    airport_field_map,
    pandas_na_values,
)
from ivao_tracker.model.json import JsonSnapshot
from ivao_tracker.model.sql import Aircraft, Airport, PilotSession
from ivao_tracker.sql import (
    create_pilottrack_partitions,
    engine,
    pilottrack_partitions_exist,
)
from ivao_tracker.util.model import json2sqlPilotSession, json2sqlSnapshot

setup_logging()
logger = logging.getLogger(__name__)

lastSnapshot = datetime.now(UTC)


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


def sync_airports():
    start = timer()
    logger.info("Syncing airports")

    url = config.config["airports"]["url"]
    with urlopen(url, context=ssl._create_unverified_context()) as response:
        csv_data = response.read().decode("utf-8")
        logger.debug("Downloaded airport csv data")

    fullCsv = pandas.read_csv(
        StringIO(csv_data), keep_default_na=False, na_values=pandas_na_values
    )

    # convert columns to correct types
    fullCsv["scheduled_service"] = fullCsv["scheduled_service"].astype(bool)
    fullCsv["last_updated"] = pandas.to_datetime(
        fullCsv["last_updated"], errors="coerce", utc=True
    )

    fullCsv = fullCsv.where(pandas.notna(fullCsv), None)

    logger.debug("Parsed airport csv data")

    session = Session(engine)
    with session.no_autoflush:

        # get latest last_updated date from db
        last_updated_db = session.exec(
            select(func.max(Airport.last_updated))
        ).first()

        # get all existing airport idents
        existingIdents = set(session.exec(select(Airport.ident)).all())

        # filter out airports that are missing in the db
        newAirportsCsv = fullCsv[~fullCsv["ident"].isin(existingIdents)]

        # filter out airports that exist and have been updated
        lastUpdatedCsv = fullCsv[
            (fullCsv["ident"].isin(existingIdents))
            & (
                fullCsv["last_updated"]
                > pandas.Timestamp(last_updated_db, tz="UTC")
            )
        ]

        airportsToAdd = []
        for row in newAirportsCsv.itertuples(index=False):
            ident = row.ident
            elevation_ft = row.elevation_ft
            elevation_ft = (
                int(elevation_ft) if pandas.notna(elevation_ft) else None
            )

            airport = Airport(
                id=int(row.id),
                code=ident,
                ident=ident,
                type=AirportType(row.type),
                name=row.name,
                elevation_ft=elevation_ft,
                continent=Continent(row.continent),
                country_name=row.country_name,
                iso_country=row.iso_country,
                region_name=row.region_name,
                iso_region=row.iso_region,
                local_region=row.local_region,
                municipality=row.municipality,
                scheduled_service=bool(row.scheduled_service),
                gps_code=row.gps_code,
                icao_code=row.icao_code,
                iata_code=row.iata_code,
                local_code=row.local_code,
                home_link=row.home_link,
                wikipedia_link=row.wikipedia_link,
                keywords=row.keywords,
                score=row.score,
                last_updated=row.last_updated,
                geom=f"SRID=4326;POINT({row.longitude_deg} {row.latitude_deg})",
            )

            airportsToAdd.append(airport)
            logger.debug("Adding airport %s", ident)

        for row in lastUpdatedCsv.itertuples(index=False):
            # get existing airport from db
            airport = session.get(Airport, row.ident)
            elevation_ft = row.elevation_ft
            elevation_ft = (
                int(elevation_ft) if pandas.notna(elevation_ft) else None
            )

            # update airport
            airport.id = int(row.id)
            # do not update/overwrite "code" attribute
            airport.ident = row.ident
            airport.type = AirportType(row.type)
            airport.name = row.name
            airport.elevation_ft = elevation_ft
            airport.continent = Continent(row.continent)
            airport.country_name = row.country_name
            airport.iso_country = row.iso_country
            airport.region_name = row.region_name
            airport.iso_region = row.iso_region
            airport.local_region = row.local_region
            airport.municipality = row.municipality
            airport.scheduled_service = bool(row.scheduled_service)
            airport.gps_code = row.gps_code
            airport.icao_code = row.icao_code
            airport.iata_code = row.iata_code
            airport.local_code = row.local_code
            airport.home_link = row.home_link
            airport.wikipedia_link = row.wikipedia_link
            airport.keywords = row.keywords
            airport.score = row.score
            airport.last_updated = row.last_updated
            airport.geom = (
                f"SRID=4326;POINT({row.longitude_deg} {row.latitude_deg})"
            )

            logger.debug("Updating airport %s", airport.ident)
            session.merge(airport)

        if len(airportsToAdd) > 0:
            session.add_all(airportsToAdd)

        session.flush()
        session.commit()
        session.close()

    end = timer()
    duration = end - start
    msgTpl = "Synced airports in {:.2f}s. Added {:d} new airports and updated {:d} existing airports."
    logger.info(
        msgTpl.format(duration, len(airportsToAdd), len(lastUpdatedCsv))
    )


def import_ivao_snapshot():
    global lastSnapshot
    jsonSnapshot = read_ivao_snapshot()

    # check if the snapshot is the same as the last one
    snapshotsAreEqual = abs(jsonSnapshot.updatedAt - lastSnapshot) < timedelta(
        microseconds=1
    )

    if snapshotsAreEqual:
        logger.info("No update available")
    else:
        ensure_db_partitions()

        logger.debug("Importing new snapshot")
        start = timer()

        try:
            session = Session(engine)
            with session.no_autoflush:
                snapshot = json2sqlSnapshot(jsonSnapshot)
                session.add(snapshot)

                lastActiveSessions = session.exec(
                    select(PilotSession).where(PilotSession.isActive)
                ).all()

                aircrafts = session.exec(select(Aircraft)).all()

                logger.debug(
                    "Found %d last active sessions", len(lastActiveSessions)
                )

                # iterate over all sessions in the snapshot
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
                            revivedSession = True
                            logger.debug(
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
                    inactivePilotSession.disconnectTime = snapshot.updatedAt
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


def ensure_db_partitions():
    today = datetime.now(UTC)
    yesterday = today - timedelta(days=1)

    for date in [yesterday, today]:
        if not pilottrack_partitions_exist(engine, date):
            create_pilottrack_partitions(engine, date)


def createPilotSession(session, snapshot, pilotSessionRaw, aircrafts):
    pilotSession = pilotSessionRaw

    # handle flightplans
    for fp in pilotSession.flightplans:
        if fp.aircraft:
            if fp.aircraft.icaoCode:
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

            for airport_id_field, airport_field in airport_field_map.items():
                airport_id = getattr(fp, airport_id_field)
                if airport_id:
                    airport = create_or_find_and_update_airport(
                        airport_id, session
                    )
                    setattr(fp, airport_field, airport)

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

            for airport_id_field, airport_field in airport_field_map.items():
                airport_id = getattr(fp, airport_id_field)
                if airport_id:
                    airport = create_or_find_and_update_airport(
                        airport_id, session
                    )
                    setattr(fp, airport_field, airport)

            fp.pilotSession = pilotSession
            session.add(fp)
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
                lastState == State.BOARDING
                and newState == State.DEPARTING
                and pilotSession.taxiTime is None
            ):
                pilotSession.taxiTime = newTrack.timestamp
                logger.debug("%s started to taxi", pilotSession.callsign)
            elif (
                lastState == State.DEPARTING
                and newState == State.INITIAL_CLIMB
                and pilotSession.takeoffTime is None
            ):
                pilotSession.takeoffTime = newTrack.timestamp
                logger.debug("%s departed", pilotSession.callsign)
            elif lastState == State.EN_ROUTE and newState == State.APPROACH:
                pilotSession.approachTime = newTrack.timestamp
                logger.debug("%s is approaching", pilotSession.callsign)
            elif lastState == State.APPROACH and newState == State.LANDED:
                pilotSession.landingTime = newTrack.timestamp
                logger.debug("%s landed", pilotSession.callsign)
            elif lastState == State.LANDED and newState == State.ON_BLOCKS:
                pilotSession.onBlocksTime = newTrack.timestamp
                logger.debug("%s is on blocks", pilotSession.callsign)

    pilotSession.textureId = pilotSessionRaw.textureId
    snapshot.pilotSessions.append(pilotSession)
    session.merge(pilotSession)


def create_or_find_and_update_airport(airport_id, session):
    # try to find existing airport in db by pk "code" attribute
    airport = session.get(Airport, airport_id)

    # gps_code will work in most cases
    if airport is None:
        airport = session.exec(
            select(Airport).where(Airport.gps_code == airport_id)
        ).first()

        if airport:
            airport.code = airport_id
            logger.debug(
                "Found correct airport value %s in 'gps_code'",
                airport.gps_code,
            )
            return airport

    # try local_code next
    if airport is None:
        airport = session.exec(
            select(Airport).where(Airport.local_code == airport_id)
        ).first()

        if airport:
            airport.code = airport_id
            logger.debug(
                "Found correct airport value %s in 'local_code'",
                airport.local_code,
            )
            return airport

    # known special cases
    if airport is None:
        airport_fix_map = {
            "SVPQ": "SVTP",
            "X21": "KX21",
            "SSUB": "SDLF",
            "VHHX": "HK-0099",
        }

        if airport_id in airport_fix_map:
            wrong_airport_id = airport_fix_map[airport_id]
            airport = session.get(Airport, wrong_airport_id)
            if airport:
                airport.code = airport_id
                logger.debug(
                    "Replacing '%s' with '%s' via custom airport mapping",
                    wrong_airport_id,
                    airport_id,
                )
                return airport

        # if airport is still None, try to find it in keywords
        # this is fuzzy and might not work in all cases
        if airport is None:
            airports = session.exec(
                select(Airport).where(Airport.keywords.like(f"%{airport_id}%"))
            ).all()

            for airport in airports:
                if airport:
                    if airport_id_is_in_keywords(airport_id, airport.keywords):
                        airport.code = airport_id
                        logger.debug(
                            "Found correct airport value %s in 'keywords'",
                            airport.keywords,
                        )
                        return airport

        # if airport is still None, create a new one
        if airport is None:
            airport = Airport(
                code=airport_id,
                ident=airport_id,
                keywords="Created by IVAO Tracker",
            )
            session.add(airport)
            logger.warning(
                "Could not find airport value for %s. Creating a new one",
                airport_id,
            )

    return airport


def airport_id_is_in_keywords(airport_id: str, keywords: str) -> bool:
    pattern = rf"(^|\s|[,;]){re.escape(airport_id)}(\s|[,;]|$)"
    return bool(re.search(pattern, keywords))


def track_snapshots(interval):
    logger.info(
        "Starting to import a IVAO snapshot every {:d} seconds".format(
            interval
        )
    )
    threading.Thread(
        target=lambda: every(interval, import_ivao_snapshot)
    ).start()


def scheduled_sync_airports(interval):
    interval_minutes = interval / 60
    interval_hours = round(interval_minutes / 60)
    logger.info(
        "Starting to sync airports every {:d} hours".format(interval_hours)
    )
    threading.Thread(target=lambda: every(interval, sync_airports)).start()
