"""
CLI interface for ivao_tracker project.
"""

from timeit import default_timer as timer  # pragma: no cover

from ivao_tracker.base import get_ivao_snapshot, track_snapshots
from ivao_tracker.config_loader import config
from ivao_tracker.sql import create_schema  # pragma: no cover


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m ivao_tracker` and `$ ivao_tracker `.

    This is the program's entry point.
    """

    start = timer()
    print("Creating DB now...")
    create_schema()
    end = timer()
    duration = end - start
    msgTpl = "Created DB in {:.2f}s"
    print(msgTpl.format(duration))

    interval = config.config["ivao"]["interval"]
    msgTpl = "Starting to fetch a snapshot every {:d} seconds..."
    print(msgTpl.format(interval))
    track_snapshots(interval)
