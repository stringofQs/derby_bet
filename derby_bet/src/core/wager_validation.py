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
from derby_bet.src.core.pool_manager import _POOL_MANAGER


_BASE_DIR = find_project_root()
_DRB_DIR = Path(_BASE_DIR, 'drb')
_WAGER_DIR = Path(_DRB_DIR, 'wagers')
_UNPROC_WAGERS = Path(_WAGER_DIR, 'wager_state_unprocessed.csv')
_PROC_WAGERS = Path(_WAGER_DIR, 'wager_state_processed.csv')


def validate_wager_data(wager_data):
    output_wagers = []

    for wager in wager_data:
        errors = []
        out1 = normalize_wager_fields(wager)
        norm_wager_data = normalize_wager_values(out1.copy())

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
            norm_wager_data['player_has_bids'] = True
        else:
            norm_wager_data['player_has_bids'] = False
            errors.append('Player does not have {} bids available to fulfill wager.'.format(total_bids))
        
        if (len(errors) > 0):
            norm_wager_data['valid'] = False
        else:
            norm_wager_data['valid'] = True
        
        err_str = '; '.join(errors)
        norm_wager_data['errors'] = err_str

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


def normalize_wager_values(wager_data):
    output = wager_data.copy()
    output['race_number'] = int(output.get('race_number', 0))
    output['player_id'] = int(output.get('player_id', 0))
    output['win_post'] = int(output.get('win_post', 0))
    output['win_bid'] = int(output.get('win_bid', 0))
    output['place_post'] = int(output.get('place_post', 0))
    output['place_bid'] = int(output.get('place_bid', 0))
    output['show_post'] = int(output.get('show_post', 0))
    output['show_bid'] = int(output.get('show_bid', 0))
    return output


def apply_bids_to_pool(wager_data):
    if wager_data.get('valid', False):
        race_num = wager_data.get('race_number', 0)
        win_bid = wager_data.get('win_bid', 0)
        win_post = wager_data.get('win_post', 0)
        place_bid = wager_data.get('place_bid', 0)
        place_post = wager_data.get('place_post', 0)
        show_bid = wager_data.get('show_bid', 0)
        show_post = wager_data.get('show_post', 0)
        _POOL_MANAGER.apply_to_win_pool(race_num, win_post, win_bid)
        _POOL_MANAGER.apply_to_place_pool(race_num, place_post, place_bid)
        _POOL_MANAGER.apply_to_show_pool(race_num, show_post, show_bid)


def apply_bids_to_player_data(wager_data):
    if wager_data.get('valid', False):
        race_num = wager_data.get('race_number', 0)
        win_bid = wager_data.get('win_bid', 0)
        place_bid = wager_data.get('place_bid', 0)
        show_bid = wager_data.get('show_bid', 0)
        player_id = wager_data.get('player_id', 0)
        total = int(win_bid) + int(place_bid) + int(show_bid)
        _PLAYER_MANAGER.place_bids(total, player_id=int(player_id))
