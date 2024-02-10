"""
CLI interface for ivao_tracker project.
"""

from timeit import default_timer as timer  # pragma: no cover

from ivao_tracker.base import read_ivao_whazzup  # pragma: no cover


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m ivao_tracker` and `$ ivao_tracker `.

    This is the program's entry point.
    """

    start = timer()

    print("Reading IVAO data...")
    snapshot = read_ivao_whazzup()
    nrOfPilots = len(snapshot.clients.pilots)

    msgTpl = "Got {:d} pilots in {:.2f}s"
    end = timer()
    duration = end - start
    print(msgTpl.format(nrOfPilots, duration))
