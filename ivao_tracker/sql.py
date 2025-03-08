import logging
from datetime import datetime, timedelta
from timeit import default_timer as timer  # pragma: no cover

from sqlmodel import Session, SQLModel, create_engine, text

from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def get_db_url():
    db_cfg = config.config["db"]
    db_user = db_cfg["username"]
    db_host = db_cfg["host"]
    db_pass = db_cfg["password"]
    db_port = db_cfg["port"]
    db_database = db_cfg["database"]

    return "postgresql://{:s}:{:s}@{:s}:{:d}/{:s}".format(
        db_user, db_pass, db_host, db_port, db_database
    )


engine = create_engine(get_db_url(), echo=False)


def create_schema():
    # time.sleep(2)
    start = timer()

    SQLModel.metadata.create_all(engine)

    end = timer()
    duration = end - start
    logger.info("Processed DB Schema in {:.2f}s".format(duration))


def pilottrack_partitions_exist(engine, day: datetime) -> bool:
    """
    Checks, whether partitions exist for the given day or not
    """
    day_str = day.strftime("%Y%m%d")

    query = """
        SELECT tablename
        FROM pg_tables
        WHERE tablename = :day_partition OR tablename = :night_partition;
    """

    with Session(engine) as session:
        result = session.exec(
            text(query),  # type: ignore
            params={
                "day_partition": f"pilottrack_{day_str}_day",
                "night_partition": f"pilottrack_{day_str}_night",
            },
        ).all()

    return len(result) == 2


def create_pilottrack_partitions(engine, day: datetime):
    """
    Creates two partitions for the given day:
    - One from 06:00 - 17:59 (day)
    - One from 18:00 - 05:59 (night)
    """
    day_str = day.strftime("%Y%m%d")
    next_day = day + timedelta(days=1)

    partitions = [
        (
            f"pilottrack_{day_str}_day",
            f"'{day.strftime('%Y-%m-%d')} 06:00:00'",
            f"'{day.strftime('%Y-%m-%d')} 18:00:00'",
        ),
        (
            f"pilottrack_{day_str}_night",
            f"'{day.strftime('%Y-%m-%d')} 18:00:00'",
            f"'{next_day.strftime('%Y-%m-%d')} 06:00:00'",
        ),
    ]

    with Session(engine) as session:
        for table_name, start, end in partitions:
            create_stmt = f"""
            CREATE TABLE IF NOT EXISTS {table_name}
            PARTITION OF pilottrack
            FOR VALUES FROM ({start}) TO ({end});
            """
            session.exec(text(create_stmt))  # type: ignore
            logger.info("Created partition table %s", table_name)
        session.commit()
