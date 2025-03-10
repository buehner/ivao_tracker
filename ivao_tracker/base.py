"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

import logging
import threading
import time
import traceback

from ivao_tracker.config.logging import setup_logging
from ivao_tracker.service.airport import sync_airports
from ivao_tracker.service.ivao import import_ivao_snapshot

setup_logging()
logger = logging.getLogger(__name__)


# https://gist.github.com/allanfreitas/e2cd0ff49bbf7ddf1d85a3962d577dbf
def every(delay, task):
    next_time = time.time() + delay
    time.sleep(1)  # To prevent task from running twice
    while True:
        time.sleep(max(0, next_time - time.time()))
        try:
            task()
        except Exception:
            traceback.print_exc()
            logger.exception("Problem while executing repetitive task.")
            # skip tasks if we are behind schedule:
        next_time += (time.time() - next_time) // delay * delay + delay


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
    interval_minutes = round(interval / 60)
    logger.info(
        "Starting to sync airports every {:d} minutes".format(interval_minutes)
    )
    threading.Thread(target=lambda: every(interval, sync_airports)).start()
