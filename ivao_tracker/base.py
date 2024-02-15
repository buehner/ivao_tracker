"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

from msgspec import json
from sqlmodel import Session

from ivao_tracker import model
from ivao_tracker.config_loader import config
from ivao_tracker.model import JsonSnapshot, Snapshot
from ivao_tracker.sql import engine

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


def get_ivao_snapshot():
    whazzup_url = config.config["ivao"]["whazzup_url"]
    with urlopen(whazzup_url) as url:
        json_data = url.read()
        snapshot = json.decode(json_data, type=JsonSnapshot)
        return snapshot


def import_ivao_snapshot():
    global lastSnapshot
    jsonSnapshot = get_ivao_snapshot()

    snapshotsAreEqual = abs(jsonSnapshot.updatedAt - lastSnapshot) < timedelta(
        microseconds=1
    )

    if snapshotsAreEqual:
        print("No update available")
    else:
        print("Creating new snapshot entry in db")
        stats = jsonSnapshot.connections

        snapshot = Snapshot(
            updatedAt=jsonSnapshot.updatedAt,
            total=stats.total,
            supervisor=stats.supervisor,
            atc=stats.atc,
            observer=stats.observer,
            pilot=stats.pilot,
            worldTour=stats.worldTour,
            followMe=stats.followMe,
        )

        session = Session(engine)
        session.add(snapshot)
        session.commit()
        session.close()

        lastSnapshot = jsonSnapshot.updatedAt


def track_snapshots(interval):
    threading.Thread(
        target=lambda: every(interval, import_ivao_snapshot)
    ).start()  # does not work in docker container
