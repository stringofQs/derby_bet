# Imports
from typing import Dict, List, Tuple
import csv
import json
from pathlib import Path
import datetime as dt
import threading
import pandas as pd

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
PAY_DIR = Path(_BASE_DIR, 'drb', 'payouts')

if not Path(PAY_DIR).exists():
    Path(PAY_DIR).mkdir(parents=True)


class PayoutCalculator:

    def __init__(self):
        self.payout_file = None
        self._get_payout_file()
        self.lock = threading.Lock()
        self.payouts = self._load_payouts()
        self.next_transaction_id = len(self.payouts.keys())
    
    def _get_payout_file(self):
        self.payout_file = Path(PAY_DIR, 'payouts_data.json')

    def _load_payouts(self):
        if not Path(self.payout_file).exists():
            return {}
        
        with self.lock:
            with open(str(self.payout_file), 'r') as file:
                data = json.load(file)
        
        return data
        
    def _save_payouts(self):
        if not Path(self.payout_file).parent.exists():
            Path(self.payout_file).parent.mkdir(parents=True)
        
        with self.lock:
            with open(str(self.payout_file), 'w') as file:
                json.dump(self.payouts, file, indent=2)
    
    def add_new_payout(self, race_num, player_id, bet_type, post, bids_wagered, bids_paid):
        if (str(self.next_transaction_id) in self.payouts.keys()):
            self.next_transaction_id = max([int(i) for i in self.payouts.keys()])
        
        with self.lock:
            self.payouts[str(int(self.next_transaction_id))] = {
                'payout_id': int(self.next_transaction_id),
                'timestamp': dt.datetime.now().isoformat(),
                'race_number': int(race_num),
                'player_id': int(player_id),
                'bet_type': str(bet_type),
                'post': int(post),
                'bids_wagered': float(bids_wagered),
                'bids_paid': float(bids_paid),
                'bid_profit': float(bids_paid) - float(bids_wagered)
            }
        
        self.next_transaction_id = len(self.payouts.keys())
        self._save_payouts()

    def _data_to_df(self):
        with self.lock:
            vals = self.payout.values()
        
        df_dict = {}
        for dd in vals:
            for k, v in dd.items():
                if k not in df_dict.keys():
                    df_dict[k] = []
                df_dict[k].append(v)
        
        df = pd.DataFrame(df_dict)
        return df

    def _parse_out_data(self, payout_id=None, race_num=None, player_id=None, bet_type=None, post=None):
        assert ((not isinstance(payout_id, type(None))) or (not isinstance(race_num, type(None))) or (not isinstance(player_id, type(None))) or (not isinstance(bet_type, type(None))) or (not isinstance(post, type(None)))), 'Expected payout parser to contain at least one input to find'

        data = self._data_to_df()
        filt = pd.Series([False] * len(data))

        if not isinstance(transaction_id, type(None)):
            filt &= (data['payout_id'] == int(payout_id))
        if not isinstance(race_num, type(None)):
            filt &= (data['race_number'] == int(race_num))
        if not isinstance(player_id, type(None)):
            filt &= (data['player_id'] == int(player_id))
        if not isinstance(bet_type, type(None)):
            filt &= (data['bet_type'] == str(bet_type))
        if not isinstance(post, type(None)):
            filt &= (data['post'] == int(post))
        
        filtered_data = data[filt]
        return filtered_data

    def summarize_race_payouts(self, race_num):
        payout_by_race = self._parse_out_data(race_num=race_num)
        return payout_by_race.copy()
    
    def summarize_player_payouts(self, player_id):
        payout_by_player = self._parse_out_data(player_id=player_id)
        return payout_by_player.copy()
    
    def summarize_bettype_payouts(self, bet_type):
        payout_by_bettype = self._parse_out_data(bet_type=bet_type)
        return payout_by_bettype.copy()
    
    def summarize_post_payouts(self, post):
        payout_by_post = self._parse_out_data(post=post)
        return payout_by_post.copy()
