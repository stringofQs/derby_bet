# Imports
from pathlib import Path
import datetime as dt
from typing import Optional, Dict, List
import json
import threading

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
POOL_DIR = Path(_BASE_DIR, 'drb', 'pool')

if not Path(POOL_DIR).exists():
    Path(POOL_DIR).mkdir(parents=True)


class PoolManager:

    """
    Pool data represented as a JSON

    {
        "1": {
            "win": {
                "1": 0,
                "2": 60,
                ...
            },
            "place": {
                "1": 30,
                "2": 0, 
                ...
            },
            "show": {
                ...
            }
        },
        ...
    }
    """

    def __init__(self):
        self.pool_file = None
        self._get_pool_file()
        self.lock = threading.Lock()
        self.pools = self._load_pools()
    
    def _get_pool_file(self):
        self.pool_file = Path(POOL_DIR, 'pool_data.json')
    
    def _load_pools(self):
        if not Path(self.pool_file).exists():
            return {}
        
        with self.lock:
            with open(str(self.pool_file), 'r') as file:
                data = json.load(file)
        return data

    def _save_pools(self):
        if not Path(self.pool_file).parent.exists():
            Path(self.pool_file).parent.mkdir(parents=True)
        
        with self.lock:
            with open(str(self.pool_file), 'w') as file:
                json.dump(self.pools, file, indent=2)
    
    def _setup_new_race_pool(self, race_num):
        pool_dict = {'win': {}, 'place': {}, 'show': {}}
        if str(race_num) not in self.pools.keys():
            with self.lock:
                self.pools[str(race_num)] = pool_dict.copy()
            self._save_pools()
    
    def get_pool_info(self, race_num, spec_pool=None):
        if isinstance(race_num, int) or isinstance(race_num, float):
            race_num = str(int(race_num))
        assert isinstance(race_num, str), 'Invalid race number ID received: {}'.format(race_num)

        with self.lock:
            pool = self.pools.get(race_num, {}).copy()
        
        if isinstance(spec_pool, str) and (spec_pool.lower() in ['win', 'place', 'show']):
            pool = pool.get(spec_pool.lower(), {}).copy()
        return pool

    def get_from_win_pool(self, race_num, post):
        pool = self.get_pool_info(race_num, 'win')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        return pool.get(post, 0)

    def get_from_place_pool(self, race_num, post):
        pool = self.get_pool_info(race_num, 'place')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        return pool.get(post, 0)

    def get_from_show_pool(self, race_num, post):
        pool = self.get_pool_info(race_num, 'show')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        return pool.get(post, 0)

    def set_win_pool(self, race_num, post, value):
        self._setup_new_race_pool(race_num)
        pool = self.get_pool_info(race_num, 'win')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        pool[post] = value
        with self.lock:
            self.pools[str(race_num)]['win'] = pool
        self._save_pools()

    def set_place_pool(self, race_num, post, value):
        self._setup_new_race_pool(race_num)
        pool = self.get_pool_info(race_num, 'place')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        pool[post] = value
        with self.lock:
            self.pools[str(race_num)]['place'] = pool
        self._save_pools()

    def set_show_pool(self, race_num, post, value):
        self._setup_new_race_pool(race_num)
        pool = self.get_pool_info(race_num, 'show')
        if isinstance(post, int) or isinstance(post, float):
            post = str(int(post))
        pool[post] = value
        with self.lock:
            self.pools[str(race_num)]['show'] = pool
        self._save_pools()

    def apply_to_win_pool(self, race_num, post, amount):
        curr_win = self.get_from_win_pool(race_num, post)
        new_total = int(curr_win) + int(amount)
        self.set_win_pool(race_num, post, new_total)
        
    def apply_to_place_pool(self, race_num, post, amount):
        curr_win = self.get_from_place_pool(race_num, post)
        new_total = int(curr_win) + int(amount)
        self.set_place_pool(race_num, post, new_total)
        
    def apply_to_show_pool(self, race_num, post, amount):
        curr_win = self.get_from_show_pool(race_num, post)
        new_total = int(curr_win) + int(amount)
        self.set_show_pool(race_num, post, new_total)
    
    def total_in_win(self, race_num):
        pool = self.get_pool_info(race_num, 'win')
        total = 0
        for v in pool.values():
            total += int(round(float(v), 0))
        return total

    def total_in_place(self, race_num):
        pool = self.get_pool_info(race_num, 'place')
        total = 0
        for v in pool.values():
            total += int(round(float(v), 0))
        return total

    def total_in_show(self, race_num):
        pool = self.get_pool_info(race_num, 'show')
        total = 0
        for v in pool.values():
            total += int(round(float(v), 0))
        return total
    
    def total_in_bet_type(self, race_num, bet_type):
        if 'win' in bet_type.lower():
            return self.total_in_win(race_num)
        elif 'place' in bet_type.lower():
            return self.total_in_place(race_num)
        elif 'show' in bet_type.lower():
            return self.total_in_show(race_num)
        else:
            raise LookupError('Invalid bet type received: {}'.format(bet_type))
