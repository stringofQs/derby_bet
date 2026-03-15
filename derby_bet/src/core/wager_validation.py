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
    output_wagers = []

    for wager in wager_data:
        errors = []
        norm_wager_data = normalize_wager_fields(wager)

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
        win_bid = norm_wager_data.get('win_bid', 0)
        if ((len(str(win_post)) == 0) and (len(str(win_bid)) != 0)) or ((len(str(win_post)) != 0) and (len(str(win_bid)) == 0)):
            errors.append('Win post + bid received are incompatible: {} + {}'.format(win_post, win_bid))

        place_post = norm_wager_data.get('place_post', -1)
        place_bid = norm_wager_data.get('place_bid', 0)
        if ((len(str(place_post)) == 0) and (len(str(place_bid)) != 0)) or ((len(str(place_post)) != 0) and (len(str(place_bid)) == 0)):
            errors.append('Place post + bid received are incompatible: {} + {}'.format(place_post, place_bid))
        
        show_post = norm_wager_data.get('show_post', -1)
        show_bid = norm_wager_data.get('show_bid', 0)
        if ((len(str(show_post)) == 0) and (len(str(show_bid)) != 0)) or ((len(str(show_post)) != 0) and (len(str(show_bid)) == 0)):
            errors.append('Show post + bid received are incompatible: {} + {}'.format(show_post, show_bid))

        win_bid = 0 if len(str(win_bid)) == 0 else int(str(win_bid))
        place_bid = 0 if len(str(place_bid)) == 0 else int(str(place_bid))
        show_bid = 0 if len(str(show_bid)) == 0 else int(str(show_bid))
        total_bids = win_bid + place_bid + show_bid
        norm_wager_data['total_bid'] = total_bids

        if _PLAYER_MANAGER.has_bids_available(total_bids, player_name=player_name):
            norm_wager_data['PlayerHasBids'] = True
        else:
            norm_wager_data['PlayerHasBids'] = False
            errors.append('Player does not have {} bids available to fulfill wager.'.format(total_bids))
        
        if (len(errors) > 0):
            norm_wager_data['Valid'] = False
        else:
            norm_wager_data['Valid'] = True
        
        output_wagers.append(norm_wager_data)

    return output_wagers


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
