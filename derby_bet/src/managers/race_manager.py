# Imports
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json
import threading

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
RACE_DIR = Path(_BASE_DIR, 'drb', 'races')

if not Path(RACE_DIR).exists():
    Path(RACE_DIR).mkdir(parents=True)


class RaceManager:

    def __init__(self, races_file=None):
        self.races_file = races_file
        self.lock = threading.Lock()
        self.races = self._load_races()

    

