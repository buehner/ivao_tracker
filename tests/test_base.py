import datetime
import unittest
import json
from unittest.mock import patch
from ivao_tracker import base


class TestIvaoTracker(unittest.TestCase):

    mock_snapshot_json = json.dumps(
        {
            "updatedAt": "2024-02-10T22:05:00.607809066Z",
            "servers": [],
            "connections": {
                "total": 812,
                "supervisor": 14,
                "atc": 91,
                "observer": 21,
                "pilot": 700,
                "worldTour": 126,
                "followMe": 0,
            },
            "clients": {
                "pilots": [],
                "atcs": [],
                "followMe": [],
                "observers": [],
            },
        }
    )

    def test_constants(self):
        assert (
            base.IVAO_WHAZZUP_URL == "https://api.ivao.aero/v2/tracker/whazzup"
        )

    @patch.object(base, "urlopen", autospec=True)
    def test_read_ivao_whazzup(self, mock_urlopen):

        # mock the result of urlopen(...).read()
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            self.mock_snapshot_json
        )

        # call the function to test
        snapshot = base.read_ivao_whazzup()

        # make assertions
        expected_updatedAt = datetime.datetime(
            2024, 2, 10, 22, 5, 0, 607809, tzinfo=datetime.timezone.utc
        )

        mock_urlopen.assert_called_with(base.IVAO_WHAZZUP_URL)
        self.assertTrue(
            abs(expected_updatedAt - snapshot.updatedAt)
            < datetime.timedelta(microseconds=1)
        )
