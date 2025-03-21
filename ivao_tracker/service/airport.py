import logging
import re
import ssl
from datetime import UTC, datetime
from io import StringIO
from timeit import default_timer as timer
from urllib.request import urlopen

import pandas
from sqlmodel import Session, func, select

from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging
from ivao_tracker.model.constants import (
    AirportType,
    Continent,
    FixOrigin,
    airport_fix_map,
    correct_airport_codes,
    pandas_na_values,
)
from ivao_tracker.model.sql import Airport
from ivao_tracker.service.sql import engine

setup_logging()
logger = logging.getLogger(__name__)

known_airports = {}


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
        id = int(row.id)
        airport = session.exec(
            select(Airport).where(Airport.id is not None and Airport.id == id)
        ).first()
        elevation_ft = row.elevation_ft
        elevation_ft = (
            int(elevation_ft) if pandas.notna(elevation_ft) else None
        )

        if airport is None:
            logger.error("Could not find airport with id %d", id)
            # import pdb
            # pdb.set_trace()

        # update airport
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


def create_or_find_and_update_airport(airport_id, session) -> Airport:
    global known_airports

    # try to use a previously processed airport
    if airport_id in known_airports:
        return known_airports[airport_id]

    # try to find existing airport in db by pk attribute "code"
    airport = session.get(Airport, airport_id)

    # gps_code will work in most cases
    if airport is None:
        airport = session.exec(
            select(Airport).where(Airport.gps_code == airport_id)
        ).first()

        if airport:
            if airport.code in correct_airport_codes:
                logger.info(
                    "Airport code %s is in the list of correct airport codes. Not using %s",
                    airport.code,
                    airport_id,
                )
            elif airport.is_used:
                logger.debug(
                    "Re-using airport %s for %s (gps_code)",
                    airport.code,
                    airport_id,
                )
            elif not airport.is_fixed:
                airport.code = airport_id
                airport.is_fixed = True
                airport.fix_origin = FixOrigin.GPS_CODE
                logger.info(
                    "Found airport value %s in 'gps_code'",
                    airport.gps_code,
                )
            elif airport.code != airport_id:
                logger.debug(
                    "Re-using fixed code %s for %s (gps_code)",
                    airport.code,
                    airport_id,
                )
            return airport

    # try local_code next
    if airport is None:
        airport = session.exec(
            select(Airport).where(Airport.local_code == airport_id)
        ).first()

        if airport:
            if airport.code in correct_airport_codes:
                logger.info(
                    "Airport code %s is in the list of correct airport codes. Not using %s",
                    airport.code,
                    airport_id,
                )
            elif airport.is_used:
                logger.debug(
                    "Re-using airport %s for %s (local_code)",
                    airport.code,
                    airport_id,
                )
            elif not airport.is_fixed:
                airport.code = airport_id
                airport.is_fixed = True
                airport.fix_origin = FixOrigin.LOCAL_CODE
                logger.info(
                    "Found airport value %s in 'local_code'",
                    airport.local_code,
                )
            elif airport.code != airport_id:
                logger.debug(
                    "Re-using fixed code %s for %s (local_code)",
                    airport.code,
                    airport_id,
                )
            return airport

    # known special cases
    if airport is None:
        if airport_id in airport_fix_map:
            wrong_airport_id = airport_fix_map[airport_id]
            airport = session.get(Airport, wrong_airport_id)
            if airport:
                if airport.code in correct_airport_codes:
                    logger.info(
                        "Airport code %s is in the list of correct airport codes. Not using %s",
                        airport.code,
                        airport_id,
                    )
                elif airport.is_used:
                    logger.debug(
                        "Re-using airport %s for %s (custom_mapping)",
                        airport.code,
                        airport_id,
                    )
                elif not airport.is_fixed:
                    airport.code = airport_id
                    airport.is_fixed = True
                    airport.fix_origin = FixOrigin.CUSTOM_MAPPING
                    logger.info(
                        "Found airport value %s in 'custom_mapping'",
                        airport_id,
                    )
                elif airport.code != airport_id:
                    logger.debug(
                        "Re-using fixed code %s for %s (custom_mapping)",
                        airport.code,
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
                        if airport.code in correct_airport_codes:
                            logger.info(
                                "Airport code %s is in the list of correct airport codes. Not using %s",
                                airport.code,
                                airport_id,
                            )
                        elif airport.is_used:
                            logger.debug(
                                "Re-using airport %s for %s (keywords)",
                                airport.code,
                                airport_id,
                            )
                        elif not airport.is_fixed:
                            airport.code = airport_id
                            airport.is_fixed = True
                            airport.fix_origin = FixOrigin.KEYWORDS
                            logger.info(
                                "Found correct airport value %s in 'keywords' '%s'",
                                airport_id,
                                airport.keywords,
                            )
                        elif airport.code != airport_id:
                            logger.debug(
                                "Re-using fixed code %s for %s (keywords)",
                                airport.code,
                                airport_id,
                            )
                        return airport

        # if airport is still None, create a new one
        if airport is None:
            airport = Airport(
                code=airport_id,
                is_fixed=True,
                fix_origin=FixOrigin.DUMMY,
                ident=airport_id,
                keywords="Dummy created by IVAO Tracker",
                last_updated=datetime.now(UTC),
            )
            session.add(airport)
            logger.warning(
                "Could not find airport value for %s. "
                "Creating a new dummy airport",
                airport_id,
            )

    airport.is_used = True
    known_airports[airport_id] = airport

    return airport


def airport_id_is_in_keywords(airport_id: str, keywords: str) -> bool:
    pattern = rf"(^|\s|[,;]){re.escape(airport_id)}(\s|[,;]|$)"
    return bool(re.search(pattern, keywords))
