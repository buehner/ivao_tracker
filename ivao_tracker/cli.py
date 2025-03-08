"""
CLI interface for ivao_tracker project.
"""

import logging

from ivao_tracker.base import (
    import_ivao_snapshot,
    scheduled_sync_airports,
    sync_airports,
    track_snapshots,
)
from ivao_tracker.config.loader import config
from ivao_tracker.config.logging import setup_logging
from ivao_tracker.sql import create_schema  # pragma: no cover

setup_logging()
logger = logging.getLogger(__name__)


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m ivao_tracker` and `$ ivao_tracker `.

    This is the program's entry point.
    """
    create_schema()

    airports_interval = config.config["airports"]["interval"]
    snapshot_interval = config.config["ivao"]["interval"]
    # sync once
    sync_airports()
    # and then scheduled
    scheduled_sync_airports(airports_interval)

    # start the import once
    import_ivao_snapshot()
    # and then scheduled
    track_snapshots(snapshot_interval)
