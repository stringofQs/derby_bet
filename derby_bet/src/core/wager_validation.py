# Imports
from pathlib import Path
import datetime as dt
from typing import Dict, Tuple, Optional, List
import threading
import csv
import json

from derby_bet.src.utils.io_tools import find_project_root
from derby_bet.src.core.player_manager import _PLAYER_MANAGER
from derby_bet.src.core.race_manager import _RACE_MANAGER


_BASE_DIR = find_project_root()
_DRB_DIR = Path(_BASE_DIR, 'drb')
_WAGER_DIR = Path(_DRB_DIR, 'wagers')
_UNPROC_WAGERS = Path(_WAGER_DIR, 'wager_state_unprocessed.csv')
_PROC_WAGERS = Path(_WAGER_DIR, 'wager_state_processed.csv')


def validate_wager_data(wager_data):
    errors = []
    norm_wager_data = normalize_wager_fields(wager_data)

    player_name = norm_wager_data.get('player_name', '').strip()
    if _PLAYER_MANAGER.is_valid_player(player_name=player_name):
        player_id = _PLAYER_MANAGER._get_player_id(player_name=player_name)
    else:
        errors.append('Invalid player name received: {}'.format(player_name))
        player_id = -1
    norm_wager_data['player_id'] = player_id

    race_number = int(norm_wager_data.get('race_number', 0))
    if not _RACE_MANAGER.is_valid_race(race_number):
        errors.append('Invalid race number: {}'.format(race_number))
    
    win_post = norm_wager_data.get('win_post', -1)
    win_bid = norm_wager_data.get('win_bid', -1)
    if ((len(str(win_post)) == 0) and (len(str(win_bid)) != 0)) or ((len(str(win_post)) != 0) and (len(str(win_bid)) == 0)):
        


    place_post = norm_wager_data.get('place_post', -1)
    place_bid = norm_wager_data.get('place_bid', -1)
    
    show_post = norm_wager_data.get('show_post', -1)
    show_bid = norm_wager_data.get('show_bid', -1)
    

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





    
