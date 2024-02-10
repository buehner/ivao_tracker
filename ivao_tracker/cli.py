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

    print("\nReading IVAO data now")
    start = timer()

    with urllib.request.urlopen(IVAO_WHAZZUP_URL) as url:
        data = decode(url.read(), type=Snapshot)

    end = timer()
    duration = end - start

    print("Got {:d} pilots in {:.2f}s".format(len(data.clients.pilots), duration))
