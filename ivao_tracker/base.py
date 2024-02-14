"""
ivao_tracker base module.

This is the principal module of the ivao_tracker project.
"""

from datetime import datetime
from typing import List
from urllib.request import urlopen

from msgspec import Struct, json

from ivao_tracker.model import JsonSnapshot

# the IVAO whazzup url
IVAO_WHAZZUP_URL = "https://api.ivao.aero/v2/tracker/whazzup"

def get_ivao_snapshot():
    with urlopen(IVAO_WHAZZUP_URL) as url:
        json_data = url.read()
        snapshot = json.decode(json_data, type=JsonSnapshot)
        return snapshot
