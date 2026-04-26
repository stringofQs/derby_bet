# Imports
from pathlib import Path
import datetime as dt
from typing import Optional, Dict, List
import json
import threading
import logging
import numpy as np

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
            lost: 0, 
            active_pending: 0,
            placed: 0
        }        
    }
    """

    _map_name_id_dict = {}

    def __init__(self):
        logging.info('Initialize PlayerManager')
        self.player_file = None
        self._get_player_file()
        self.lock = threading.Lock()
        self.players = self._load_players()
        self.total_players = None
        self.all_player_ids = []
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
            player_name = v.get('player_name')
            self._map_name_id_dict[str(player_name).lower().replace(' ', '')] = str(int(k))
            
        return data
    
    def _save_players(self):
        if not Path(self.player_file).parent.exists():
            Path(self.player_file).parent.mkdir(parents=True)
        
        with self.lock:
            with open(str(self.player_file), 'w') as file:
                json.dump(self.players, file, indent=2)
    
    def _update_player_count(self):
        self.total_players = len(self.players.keys())
        self.all_player_ids = sorted(list(self.players.keys()))
    
    def _timestamp_player_change(self, player_id):
        with self.lock:
            self.players[str(int(player_id))]['latest_update'] = dt.datetime.now().isoformat()
    
    def _get_player_id(self, player_name=None, player_id=None):
        try:
            assert (not isinstance(player_name, type(None))) or (not isinstance(player_id, type(None))), 'Expected to receive either player ID or player name for info lookup, received neither.'

            if isinstance(player_id, type(None)):
                assert str(player_name).lower().replace(' ', '') in self._map_name_id_dict.keys(), 'Player name received does not exist in the current player data. Received {}'.format(player_name)
                player_id = self._map_name_id_dict.get(str(player_name).lower().replace(' ', ''))
            return player_id
        except:
            logging.error('Invalid player ID entry.')
            return -1
    
    def get_all_players_sorted(self, lastname_alpha=False, alphabetically=False, by_avail=False, by_won=False, by_lost=False):
        assert lastname_alpha or alphabetically or by_avail or by_won or by_lost, 'Expected to get a flag for how to sort all player data, received none'

        with self.lock:
            players = self.players.copy()
        
        plyr_val = []
        plyr_data = []
        for plyr in players.values():
            if alphabetically:
                plyr_val.append(plyr.get('player_name', ''))
            elif lastname_alpha:
                plyr_name = plyr.get('player_name', '')
                name_split = plyr_name.split(' ')
                plyr_val.append('{}, {}'.format(name_split[-1], name_split[0]))
            elif by_avail:
                plyr_val.append(plyr.get('bids', {}).get('available', 0))
            elif by_won:
                plyr_val.append(plyr.get('bids', {}).get('won', 0))
            elif by_lost:
                plyr_val.append(plyr.get('bids', {}).get('lost', 0))
            
            plyr_data.append(plyr)

        sort_index = np.argsort(plyr_val)
        if alphabetically or lastname_alpha:  # Want to sort in alphabetical order
            sorted_players = np.array(plyr_data)[sort_index].tolist()
        else:  # For any sort by bids (won, available, lost, etc.), we generally want the highest number first, so reverse the order
            sorted_players = np.array(plyr_data)[sort_index[::-1]].tolist()

        return sorted_players

    def get_lead_players(self, top_n):
        assert isinstance(top_n, int) and (top_n > 0), 'Invalid top_n value received: {}'.format(top_n)
        all_players_sorted = self.get_all_players_sorted(by_won=True)
        if len(all_players_sorted) < top_n:
            top_n = len(all_players_sorted)
        return all_players_sorted[:top_n]
            
    def is_valid_player(self, player_name=None, player_id=None):
        try:
            info = self.get_player_info(player_name=player_name, player_id=player_id)
            if not info:
                logging.warning('Player received is invalid (no data): {} | {}'.format(player_name, player_id))
                return False
        except Exception as _:
            logging.warning('Player received is invalid: {} | {}'.format(player_name, player_id))
            return False
        return True

    def add_new_player(self, player_name):
        if player_name.lower().replace(' ', '') in self._map_name_id_dict.keys():
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
                        'lost': 0, 
                        'active_pending': 0,
                        'placed': 0
                    }
                }
            
            logging.info('New player added: {} | {}'.format(player_name, new_id))
            self._timestamp_player_change(int(new_id))
            self._map_name_id_dict[player_name.lower().replace(' ', '')] = str(int(new_id))
            self._update_player_count()

            self._save_players()
    
    def get_player_info(self, player_name=None, player_id=None):
        player_id = self._get_player_id(player_name=player_name, player_id=player_id)
        
        pid_key = str(int(player_id))
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

    def get_bids_placed(self, player_name=None, player_id=None):
        bids = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bids.get('placed', 0)

    def set_bid_data(self, bid_data, player_name=None, player_id=None):
        logging.debug('Setting bid data for player ID {}...'.format(player_id))
        ind_plyr = self.get_player_info(player_name=player_name, player_id=player_id)
        ind_plyr['bids'] = bid_data.copy()

        with self.lock:
            self.players[str(int(ind_plyr.get('player_id')))] = ind_plyr.copy()
        self._timestamp_player_change(ind_plyr.get('player_id'))
        self._save_players()

    def _set_bids_custom(self, bid_amount, bid_category, player_name=None, player_id=None):
        if bid_category.lower() == 'purchased':
            self.set_bids_purchased(bid_amount, player_name=player_name, player_id=player_id)
        elif bid_category.lower() == 'available':
            self.set_bids_available(bid_amount, player_name=player_name, player_id=player_id)
        elif bid_category.lower() == 'won':
            self.set_bids_won(bid_amount, player_name=player_name, player_id=player_id)
        elif bid_category.lower() == 'active_pending':
            self.set_bids_pending(bid_amount, player_name=player_name, player_id=player_id)
        elif bid_category.lower() == 'lost':
            self.set_bids_lost(bid_amount, player_name=player_name, player_id=player_id)
        elif bid_category.lower() == 'placed':
            self.set_bids_placed(bid_amount, player_name=player_name, player_id=player_id)
        else:
            logging.error(f'Received {bid_category}, which is invalid or unexpected for setting')
            raise ValueError('Invalid bid category: {}'.format(bid_category))

    def set_bids_purchased(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['purchased'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_available(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['available'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)
    
    def set_bids_won(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['won'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_pending(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['active_pending'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_lost(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['lost'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def set_bids_placed(self, bid_amount, player_name=None, player_id=None):
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        bid_data['placed'] = bid_amount
        self.set_bid_data(bid_data.copy(), player_name=player_name, player_id=player_id)

    def change_bids_purchased(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_purchased(player_name=player_name, player_id=player_id)
        self.set_bids_purchased(amt + bid_change, player_name=player_name, player_id=player_id)

    def change_bids_available(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_available(player_name=player_name, player_id=player_id)
        self.set_bids_available(amt + bid_change, player_name=player_name, player_id=player_id)

    def change_bids_won(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_won(player_name=player_name, player_id=player_id)
        self.set_bids_won(amt + bid_change, player_name=player_name, player_id=player_id)

    def change_bids_lost(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_lost(player_name=player_name, player_id=player_id)
        self.set_bids_lost(amt + bid_change, player_name=player_name, player_id=player_id)

    def change_bids_pending(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_pending(player_name=player_name, player_id=player_id)
        self.set_bids_pending(amt + bid_change, player_name=player_name, player_id=player_id)

    def change_bids_placed(self, bid_change, player_name=None, player_id=None):
        amt = self.get_bids_placed(player_name=player_name, player_id=player_id)
        self.set_bids_placed(amt + bid_change, player_name=player_name, player_id=player_id)

    def has_bids_available(self, bid_amount, player_name=None, player_id=None):
        bids_avail = self.get_bids_available(player_name=player_name, player_id=player_id)
        return int(bids_avail) >= int(bid_amount)
    
    def apply_bid_exchange(self, bids, from_bid, to_bid, player_name=None, player_id=None):
        logging.debug('Exchanging {} bids for player ID {} from {} to {}'.format(bids, player_id, from_bid, to_bid))
        assert isinstance(from_bid, str), 'Expected a string to indicate where the bid exchange is coming from. Received {}'.format(from_bid)
        assert isinstance(to_bid, str), 'Expected a string to indicate where the bid exchange is going to. Received {}'.format(to_bid)

        # Determine the from_bid
        if any([i in from_bid.lower() for i in ['avail', 'available']]):  # From bid is "available"
            from_bid = 'available'
        elif any([i in from_bid.lower() for i in ['pend', 'pending', 'active']]):  # From bid is "active_pending"
            from_bid = 'active_pending'
        elif any([i in from_bid.lower() for i in ['won', 'win']]):  # From bid is "won"
            from_bid = 'won'
        elif any([i in from_bid.lower() for i in ['lost', 'lose', 'losing']]):  # From bid is "lost"
            from_bid = 'lost'
        elif any([i in from_bid.lower() for i in ['purchase', 'bought', 'purch', 'buy']]):  # From bid is "purchased"
            from_bid = 'purchased'
        elif any([i in from_bid.lower() for i in ['place', 'placed']]):
            from_bid = 'placed'
        else:
            logging.error(f'Received {from_bid}, which is invalid or unexpected for exchange')
            raise LookupError('Invalid "from_bid" received in exchange: {}'.format(from_bid))
        
        # Determine the to_bid
        if any([i in to_bid.lower() for i in ['avail', 'available']]):  # To bid is "available"
            to_bid = 'available'
        elif any([i in to_bid.lower() for i in ['pend', 'pending', 'active']]):  # To bid is "active_pending"
            to_bid = 'active_pending'
        elif any([i in to_bid.lower() for i in ['won', 'win']]):  # To bid is "won"
            to_bid = 'won'
        elif any([i in to_bid.lower() for i in ['lost', 'lose', 'losing']]):  # To bid is "lost"
            to_bid = 'lost'
        elif any([i in to_bid.lower() for i in ['purchase', 'bought', 'purch', 'buy']]):  # To bid is "purchased"
            to_bid = 'purchased'
        elif any([i in to_bid.lower() for i in ['place', 'placed']]):
            to_bid = 'placed'
        else:
            logging.error(f'Received {to_bid}, which is invalid or unexpected for exchange')
            raise LookupError('Invalid "to_bid" received in exchange: {}'.format(to_bid))
        
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        if (from_bid != to_bid):
            from_total = bid_data.get(from_bid, 0)
            to_total = bid_data.get(to_bid, 0)
            if (from_total >= bids):
                self._set_bids_custom(from_total - bids, from_bid, player_name=player_name, player_id=player_id)
                self._set_bids_custom(to_total + bids, to_bid, player_name=player_name, player_id=player_id)
            
    def purchase_bids(self, amount, player_name=None, player_id=None):
        logging.info(f'Purchase {amount} bids for player {player_name} | {player_id}')
        self.change_bids_purchased(amount, player_name=player_name, player_id=player_id)
        self.change_bids_available(amount, player_name=player_name, player_id=player_id)

    def place_bids(self, amount, player_name=None, player_id=None):
        logging.info(f'Place {amount} bids for player {player_name} | {player_id}')
        self.change_bids_available(-amount, player_name=player_name, player_id=player_id)
        self.change_bids_pending(amount, player_name=player_name, player_id=player_id)
        self.change_bids_placed(amount, player_name=player_name, player_id=player_id)

    def set_winning_bid(self, amount_won, associated_pending, player_name=None, player_id=None):
        # When a bid is won, the total amount of bids won will be applied to both the "won" and "available" categories
        # Additionally, the amount in the associated pending will be removed (this amount is all bid amount on this current race)
        logging.info(f'Win {amount_won} bids for player {player_name} | {player_id}')
        self.change_bids_won(amount_won, player_name=player_name, player_id=player_id)
        self.change_bids_available(amount_won, player_name=player_name, player_id=player_id)
        self.change_bids_pending(-associated_pending, player_name=player_name, player_id=player_id)

    def set_losing_bid(self, amount_lost, player_name=None, player_id=None):
        logging.info(f'Lost {amount_lost} bids for player {player_name} | {player_id}')
        self.change_bids_pending(-amount_lost, player_name=player_name, player_id=player_id)
        self.change_bids_lost(amount_lost, player_name=player_name, player_id=player_id)
    
    def validate_bids(self, player_name=None, player_id=None):
        logging.debug(f'Validating bid values for player {player_name} | {player_id}')
        bid_data = self.get_bids_data(player_name=player_name, player_id=player_id)
        return bid_data.get('available', 0) == (bid_data.get('purchased', 0) + bid_data.get('won', 0) - bid_data.get('placed', 0))
