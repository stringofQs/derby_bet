# Imports
from pathlib import Path
import datetime as dt
from typing import Dict, Tuple, Optional, List
import threading
import csv
import json

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
_DRB_DIR = Path(_BASE_DIR, 'drb')
_WAGER_DIR = Path(_DRB_DIR, 'wagers')
_UNPROC_WAGERS = Path(_WAGER_DIR, 'wager_state_unprocessed.csv')
_PROC_WAGERS = Path(_WAGER_DIR, 'wager_state_processed.csv')


def normalize_wager_fields(wager_data):
    field_map = {
        'Timestamp': 'timestamp_google', 
        'Player Name (First + Last pls)': 'player_name',
        'Player Name': 'player_name',
        'Race Number (1 - 14)': 'race_number', 
        'Race Number': 'race_number',
        'Win Post Position (1 - 20)': 'win_post',
        'Win Post': 'win_post',
        'Win Bid': 'win_bid',
        'Place Post Position (1 - 20)': 'place_post',
        'Place Post': 'place_post',
        'Place Bid': 'place_bid',
        'Show Post Position (1 - 20)': 'show_post',
        'Show Post': 'show_post',
        'Show Bid': 'show_bid'
    }

    output = {}
    for k, v in wager_data.items():
        output[field_map.get(k, k.lower().strip().replace(' ', '_'))] = v
    return output


def normalize_wager_values(wager_data):
    output = wager_data.copy()
    output['race_number'] = int(output.get('race_number', 0))
    output['player_id'] = int(output.get('player_id', 0))
    return output

