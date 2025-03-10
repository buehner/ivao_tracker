import logging
from datetime import UTC, datetime, timedelta
from timeit import default_timer as timer
from urllib.request import urlopen

from msgspec import json
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.constants import State, airport_field_map
from ivao_tracker.model.json import JsonSnapshot
from ivao_tracker.model.sql import Aircraft, PilotSession
from ivao_tracker.service.airport import create_or_find_and_update_airport
from ivao_tracker.service.sql import engine, ensure_db_partitions
from ivao_tracker.util.model import json2sqlPilotSession, json_to_sql_snapshot

setup_logging()
logger = logging.getLogger(__name__)

last_snapshot = datetime.now(UTC)


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
                pilot_session.takeoffTime = new_track.timestamp - timedelta(
                    minutes=1
                )
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
