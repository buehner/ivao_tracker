"""
CLI interface for ivao_tracker project.
"""
import urllib.request
from msgspec.json import decode
from ivao_tracker.base import Snapshot
from ivao_tracker.base import IVAO_WHAZZUP_URL
from timeit import default_timer as timer


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m ivao_tracker` and `$ ivao_tracker `.

    This is the program's entry point.
    """

    start = timer()

    snapshot = read_ivao_whazzup()
    nrOfPilots = len(snapshot.clients.pilots)

    end = timer()
    duration = end - start

    msgTpl = "Got {:d} pilots in {:.2f}s\n"
    print(msgTpl.format(nrOfPilots, duration))


def read_ivao_whazzup():
    print("\nReading IVAO data now")
    with urllib.request.urlopen(IVAO_WHAZZUP_URL) as url:
        return decode(url.read(), type=Snapshot)
