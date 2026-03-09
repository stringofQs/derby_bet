# Imports
from pathlib import Path
import datetime as dt
from typing import Optional, Dict, List
import json
import threading
import logging

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
PLYR_DIR = Path(_BASE_DIR, 'drb', 'players')

if not Path(PLYR_DIR).exists():
    Path(PLYR_DIR).mkdir(parents=True)


class PlayerManager:

    """
    Player data is represented as a JSON, where the player ID
    is the key, and the player details are in a dictionary assigned to the values. 
    
    The data for each player looks like the following:
    {
        player_id: 1,
        player_name: "Nichole Beck",
        latest_update: '2026-05-02T14:30:00",
        bids: {
            purchased: 100,
            available: 100,
            won: 0,
            active_pending: 0,
            lost: 0            
        }        
    }
    """

    _map_name_id_dict = {}

    def __init__(self):
        self.player_file = None
        self._get_player_file()
        self.lock = threading.Lock()
        self.players = self._load_players()
        self.total_players = None
        self._update_player_count()

    def _get_player_file(self):
        self.player_file = Path(PLYR_DIR, 'player_data.json')

    def _load_players(self):
        self._map_name_id_dict = {}  # Reset ID/name map

        if not Path(self.player_file).exists():
            return {}
        
        with self.lock:
            with open(str(self.player_file), 'r') as file:
                data = json.load(file)
        
        for k, v in data.items():
            player_name = data.get('player_name')
            self._map_name_id_dict[str(player_name)] = str(int(k))
            
        return data
    
    def _save_players(self):
        if not Path(self.player_file).parent.exists():
            Path(self.player_file).parent.mkdir(parents=True)
        
        with self.lock:
            with open(str(self.player_file), 'w') as file:
                json.dump(self.players, file, indent=2)
    
    def _update_player_count(self):
        self.total_players = len(self.players.keys())
    
    def _timestamp_player_change(self, player_id):
        with self.lock:
            self.players[str(int(player_id))]['latest_update'] = dt.datetime.now().isoformat()
    
    def _get_player_id(self, player_name=None, player_id=None):
        assert (not isinstance(player_name, type(None))) or (not isinstance(player_id, type(None))), 'Expected to receive either player ID or player name for info lookup, received neither.'

        if isinstance(player_id, type(None)):
            assert str(player_name) in self._map_name_id_dict.keys(), 'Player name received does not exist in the current player data. Received {}'.format(player_name)
            player_id = self._map_name_id_dict.get(str(player_name))
        return player_id

    def add_new_player(self, player_name):
        if player_name in self._map_name_id_dict.keys():
            logging.warning('Provided player ({}) already exists. Not adding as a new player.'.format(player_name))
        else:
            new_id = self.total_players + 1
            with self.lock:
                self.players[str(int(new_id))] = {
                    'player_id': int(new_id),
                    'player_name': player_name,
                    'latest_update': None,  # Timestamping happens in a separate method
                    'bids': {
                        'purchased': 0,
                        'available': 0,
                        'won': 0,
                        'active_pending': 0,
                        'lost': 0
                    }
                }

            self._timestamp_player_change()
            self._map_name_id_dict[player_name] = str(int(new_id))
            self._update_player_count()
    
    def get_player_info(self, player_name=None, player_id=None):
        player_id = self._get_player_id(player_name=player_name, player_id=player_id)
        
        pid_key = str(int(player_id))
        assert pid_key in self.players.keys(), 'Player ID received ({}) does not exist in the current player data.'.format(player_id)

        with self.lock:
            return self.players.get(pid_key, {}).copy()
    
    def get_bids_data(self, player_name=None, player_id=None):
        ind_plyr = self.get_player_info(player_name=player_name, player_id=player_id)
        return ind_plyr.get('bids', {}).copy()

    def get_bids_purchased(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('purchased', 0)

    def get_bids_available(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('available', 0)

    def get_bids_won(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('won', 0)

    def get_bids_pending(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('active_pending', 0)
    
    def get_bids_lost(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('lost', 0)

    def set_bid_data(self, bid_data, player_name=None, player_id=None):
        ind_plyr = self.get_player_info(player_name=player_name, player_id=player_id)
        ind_plyr['bids'] = bid_data.copy()

        with self.lock:
            self.players[str(int(ind_plyr.get('player_id')))] = ind_plyr.copy()
        self._timestamp_player_change(ind_player.get('player_id'))
        self._save_players()

    def set_bids_purchased(self, bids, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['purchased'] = bids
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_available(self, bids, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['available'] = bids
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)
    
    def set_bids_won(self, bids, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['won'] = bids
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_pending(self, bids, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['active_pending'] = bids
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_lost(self, bids, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['lost'] = bids
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def has_bids_available(self, bids, player_name=None, player_id=None):
        bids_avail = self.get_bids_available(player_name=player_name, player_id=player_id)
        return int(bids_avail) >= int(bids)
    
    def apply_bid_exchange(self, bids, from_bid, to_bid, player_name=None, player_id=None):
        assert isinstance(from_bid, str), 'Expected a string to indicate where the bid exchange is coming from. Received {}'.format(from_bid)
        assert isinstance(to_bid, str), 'Expected a string to indicate where the bid exchange is going to. Received {}'.format(to_bid)

        # Determine the from_bid
        if any([i in from_bid.lower() for i in ['avail', 'available']]):  # From bid is "available"
            pass
        elif ..
            pass
        
        # Determine the to_bid
        if any([i in to_bid.lower() for i in ['avail', 'available']]):  # To bid is "available"
            pass
        elif ..
            pass


_PLAYER_MANAGER = PlayerManager()
