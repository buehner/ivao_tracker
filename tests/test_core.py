import datetime
import unittest
import json
from unittest.mock import patch
from ivao_tracker.service import ivao


class TestIvaoTracker(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        with open("tests/mock_data/snapshot.json", "r") as snapshot_json:
            self.mock_snapshot_json = json.dumps(json.load(snapshot_json))

        self.expected_updatedAt = datetime.datetime(
            2024, 2, 10, 22, 5, 0, 607809, tzinfo=datetime.timezone.utc
        )

        self.expected_nr_of_pilots = 2
        self.expectedAircraftId = "B77W"
        self.expectedAltitude = 35076

    @patch.object(ivao, "urlopen", autospec=True)
    def test_read_ivao_snapshot(self, mock_urlopen):

        # mock the result of urlopen(...).read()
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            self.mock_snapshot_json
        )

        # call the function to test
        snapshot = ivao.read_ivao_snapshot()

        assert abs(
            self.expected_updatedAt - snapshot.updatedAt
        ) < datetime.timedelta(
            microseconds=1
        ), f"updatedAt is {snapshot.updatedAt}, but expected {self.expected_updatedAt}"

        assert (
            len(snapshot.clients.pilots) == self.expected_nr_of_pilots
        ), f"pilot array has length {len(snapshot.clients.pilots)}, but expected is {self.expected_nr_of_pilots}"

        assert (
            snapshot.clients.pilots[0].flightPlan.aircraftId
            == self.expectedAircraftId
        ), f"aircraftId of flightPlan is {snapshot.clients.pilots[0].flightPlan.aircraftId}, but expected is {self.expectedAircraftId}"

        assert (
            snapshot.clients.pilots[0].lastTrack.altitude
            == self.expectedAltitude
        ), f"altitude of lastTrack is {snapshot.clients.pilots[0].lastTrack.altitude}, but expected is {self.expectedAltitude}"
