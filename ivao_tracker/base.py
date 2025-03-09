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
    airport_fix_map,
    pandas_na_values,
)
from ivao_tracker.model.json import JsonSnapshot
from ivao_tracker.model.sql import Aircraft, Airport, PilotSession
from ivao_tracker.sql import engine, ensure_db_partitions
from ivao_tracker.util.model import json2sqlPilotSession, json_to_sql_snapshot

setup_logging()
logger = logging.getLogger(__name__)

last_snapshot = datetime.now(UTC)


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


def read_ivao_snapshot() -> JsonSnapshot:
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

    full_csv = parse_airport_csv()

    session = Session(engine)
    with session.no_autoflush:

        # get latest last_updated date from db
        last_updated_db = session.exec(
            select(func.max(Airport.last_updated))
        ).first()

        # get all existing airport idents
        existing_idents = set(session.exec(select(Airport.ident)).all())

        # filter out airports that are missing in the db
        new_airports_csv = full_csv[~full_csv["ident"].isin(existing_idents)]

        # filter out airports that exist and have been updated
        last_updated_csv = full_csv[
            (full_csv["ident"].isin(existing_idents))
            & (
                full_csv["last_updated"]
                > pandas.Timestamp(last_updated_db, tz="UTC")
            )
        ]

        airports_to_add = create_new_airports(new_airports_csv)

        update_airports(last_updated_csv, session)

        if len(airports_to_add) > 0:
            session.add_all(airports_to_add)

        session.flush()
        session.commit()
        session.close()

    end = timer()
    duration = end - start
    msgTpl = (
        "Synced airports in {:.2f}s. Added {:d} new airports and "
        "updated {:d} existing airports."
    )
    logger.info(
        msgTpl.format(duration, len(airports_to_add), len(last_updated_csv))
    )


def import_ivao_snapshot():
    global last_snapshot
    json_snapshot = read_ivao_snapshot()

    # check if the snapshot is the same as the last one
    snapshots_are_equal = abs(
        json_snapshot.updatedAt - last_snapshot
    ) < timedelta(microseconds=1)

    if snapshots_are_equal:
        logger.info("No update available")
    else:
        ensure_db_partitions()

        logger.debug("Importing new snapshot")
        start = timer()

        try:
            session = Session(engine)
            with session.no_autoflush:
                snapshot = json_to_sql_snapshot(json_snapshot)
                session.add(snapshot)

                last_active_sessions = session.exec(
                    select(PilotSession).where(PilotSession.isActive)
                ).all()

                aircrafts = session.exec(select(Aircraft)).all()

                logger.debug(
                    "Found %d last active sessions", len(last_active_sessions)
                )

                # iterate over all sessions in the snapshot
                for json_pilot in json_snapshot.clients.pilots:
                    pilot_session_raw = json2sqlPilotSession(json_pilot)
                    pilot_session = next(
                        (
                            s
                            for s in last_active_sessions
                            if s.id == json_pilot.id
                        ),
                        None,
                    )

                    revived_session = False
                    if pilot_session is None:
                        # try to revive possible ghost connections
                        pilot_session = session.get(
                            PilotSession, json_pilot.id
                        )
                        if pilot_session:
                            pilot_session.isActive = True
                            revived_session = True
                            logger.debug(
                                "Revived pilot session %s", pilot_session.id
                            )

                    if pilot_session is None:
                        # no pilotSession in db...
                        pilot_session = create_pilot_session(
                            session, snapshot, pilot_session_raw, aircrafts
                        )
                    else:
                        # we found an existing pilotSession in db
                        mergePilotSession(
                            session,
                            snapshot,
                            pilot_session_raw,
                            pilot_session,
                            aircrafts,
                        )
                        if revived_session is False:
                            last_active_sessions.remove(pilot_session)

                for inactive_pilot_session in last_active_sessions:
                    inactive_pilot_session.isActive = False
                    inactive_pilot_session.disconnectTime = snapshot.updatedAt
                    session.merge(inactive_pilot_session)
                    logger.debug("Ended session %d", inactive_pilot_session.id)

                session.commit()
                session.close()

                end = timer()
                duration = end - start
                msgTpl = "Updated DB in {:.2f}s"
                logger.info(msgTpl.format(duration))

                last_snapshot = json_snapshot.updatedAt
        except SQLAlchemyError as e:
            logger.error("SQL Alchemy Error: %s", str(e))
            session.rollback()

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))


def parse_airport_csv() -> pandas.DataFrame:
    url = config.config["airports"]["url"]
    with urlopen(url, context=ssl._create_unverified_context()) as response:
        csv_data = response.read().decode("utf-8")
        logger.debug("Downloaded airport csv data")

    full_csv = pandas.read_csv(
        StringIO(csv_data), keep_default_na=False, na_values=pandas_na_values
    )

    # convert columns to correct types
    full_csv["scheduled_service"] = full_csv["scheduled_service"].astype(bool)
    full_csv["last_updated"] = pandas.to_datetime(
        full_csv["last_updated"], errors="coerce", utc=True
    )

    full_csv = full_csv.where(pandas.notna(full_csv), None)

    logger.debug("Parsed airport csv data")

    return full_csv


def create_new_airports(csv) -> list[Airport]:
    new_airports = []
    for row in csv.itertuples(index=False):
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

        new_airports.append(airport)
        logger.debug("Adding airport %s", ident)

    return new_airports


def update_airports(last_updated_csv, session):
    for row in last_updated_csv.itertuples(index=False):
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


def create_pilot_session(
    session, snapshot, pilot_session_raw, aircrafts
) -> PilotSession:
    pilot_session = pilot_session_raw

    # handle flightplans
    for fp in pilot_session.flightplans:
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

    session.add(pilot_session)
    snapshot.pilotSessions.append(pilot_session)
    logger.debug("Created new pilot session " + pilot_session_raw.callsign)
    return pilot_session


def mergePilotSession(
    session, snapshot, raw_pilot_session, pilot_session, aircrafts
):
    for fp in raw_pilot_session.flightplans:
        # handle flightplans
        if not any(
            session_fp.id == fp.id for session_fp in pilot_session.flightplans
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

            fp.pilotSession = pilot_session
            session.add(fp)
            logger.debug(
                "Appended a new flightplan for " + pilot_session.callsign
            )

    last_state = None
    if len(pilot_session.tracks) > 0:
        last_track = pilot_session.tracks[-1]
        last_state = last_track.state

    if len(raw_pilot_session.tracks) > 0:
        new_track = raw_pilot_session.tracks[0]
        new_track.pilotSession = pilot_session
        session.add(new_track)
        pilot_session.tracks.append(new_track)
        new_state = new_track.state
        if last_state and last_state != new_state:
            if (
                last_state == State.BOARDING
                and new_state == State.DEPARTING
                and pilot_session.taxiTime is None
            ):
                pilot_session.taxiTime = new_track.timestamp
                logger.debug("%s started to taxi", pilot_session.callsign)
            elif (
                last_state == State.DEPARTING
                and new_state == State.INITIAL_CLIMB
                and pilot_session.takeoffTime is None
            ):
                pilot_session.takeoffTime = new_track.timestamp
                logger.debug("%s departed", pilot_session.callsign)
            elif last_state == State.EN_ROUTE and new_state == State.APPROACH:
                pilot_session.approachTime = new_track.timestamp
                logger.debug("%s is approaching", pilot_session.callsign)
            elif last_state == State.APPROACH and new_state == State.LANDED:
                pilot_session.landingTime = new_track.timestamp
                logger.debug("%s landed", pilot_session.callsign)
            elif last_state == State.LANDED and new_state == State.ON_BLOCKS:
                pilot_session.onBlocksTime = new_track.timestamp
                logger.debug("%s is on blocks", pilot_session.callsign)

    pilot_session.textureId = raw_pilot_session.textureId
    snapshot.pilotSessions.append(pilot_session)
    session.merge(pilot_session)


def create_or_find_and_update_airport(airport_id, session) -> Airport:
    # try to find existing airport in db by pk "code" attribute
    airport = session.get(Airport, airport_id)

    # gps_code will work in most cases
    if airport is None:
        airport = session.exec(
            select(Airport).where(Airport.gps_code == airport_id)
        ).first()

        if airport:
            airport.code = airport_id
            logger.info(
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
            logger.info(
                "Found correct airport value %s in 'local_code'",
                airport.local_code,
            )
            return airport

    # known special cases
    if airport is None:
        if airport_id in airport_fix_map:
            wrong_airport_id = airport_fix_map[airport_id]
            airport = session.get(Airport, wrong_airport_id)
            if airport:
                airport.code = airport_id
                logger.info(
                    "Replacing '%s' with '%s' via custom airport mapping",
                    wrong_airport_id,
                    airport_id,
                )
                return airport

        # if airport is still None, try to find it in keywords
        # this is fuzzy and might not work in all cases
        if airport is None:
            airports = session.exec(
                select(Airport).where(
                    Airport.keywords.like(f"%{airport_id}%")  # type: ignore
                )
            ).all()

            for airport in airports:
                if airport:
                    if airport_id_is_in_keywords(airport_id, airport.keywords):
                        airport.code = airport_id
                        logger.info(
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
