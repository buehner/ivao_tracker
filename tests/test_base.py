from ivao_tracker.base import IVAO_WHAZZUP_URL


def test_base():
    assert IVAO_WHAZZUP_URL == "https://api.ivao.aero/v2/tracker/whazzup"
