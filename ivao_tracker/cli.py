"""
CLI interface for ivao_tracker project.
"""
import logging

from timeit import default_timer as timer  # pragma: no cover

from ivao_tracker.base import track_snapshots
from ivao_tracker.config_loader import config
from ivao_tracker.sql import create_schema  # pragma: no cover

from ivao_tracker.logger.config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m ivao_tracker` and `$ ivao_tracker `.

    This is the program's entry point.
    """

    logger.info("Processing DB schema")
    start = timer()
    create_schema()
    end = timer()
    duration = end - start
    logger.info("Processed DB in {:.2f}s".format(duration))

    interval = config.config["ivao"]["interval"]
    logger.info("Starting to fetch a snapshot every {:d} seconds".format(interval))
    track_snapshots(interval)
