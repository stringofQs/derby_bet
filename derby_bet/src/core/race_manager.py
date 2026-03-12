# Imports
from pathlib import Path
import datetime as dt
from typing import Optional, Dict, List
import json
import threading

from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
RACE_DIR = Path(_BASE_DIR, 'drb', 'races')

if not Path(RACE_DIR).exists():
    Path(RACE_DIR).mkdir(parents=True)


class RaceManager:

    """
    Race data is represented as a JSON, where the race number (race ID) 
    is the key, and the race details are in a dictionary assigned to the values. 
    
    The data for each race value looks like the following:
    {
        race_id: 1,
        race_description: "Kentucky Derby",
        post_time: '2026-05-01T11:00:00",
        win: null,
        place: null,
        show: null,
        status: "pending"  # Has options: "pending", "next", "closed"
    }
    """

    def __init__(self):
        self.races_file = None
        self._get_race_file()
        self.lock = threading.Lock()
        self.races = self._load_races()
    
    def _get_race_file(self):
        self.races_file = Path(RACE_DIR, 'races_data.json')

    def _load_races(self):
        if not Path(self.races_file).exists():
            return {}
        
        with self.lock:
            with open(str(self.races_file), 'r') as file:
                data = json.load(file)
        return data
    
    def _save_races(self):
        if not Path(self.races_file).parent.exists():
            Path(self.races_file).parent.mkdir(parents=True)
        
        with self.lock:
            with open(str(self.races_file), 'w') as file:
                json.dump(self.races, file, indent=2)
            
    def get_race_info(self, race_num):
        if isinstance(race_num, int) or isinstance(race_num, float):
            race_num = str(int(race_num))
        assert isinstance(race_num, str), 'Invalid race number ID received: {}'.format(race_num)
        with self.lock:
            return self.races.get(race_num, {}).copy()

    def is_race_pending(self, race_num):
        ind_race = self.get_race_info(race_num)
        return str(ind_race.get('status')).lower() == 'pending'
    
    def is_race_complete(self, race_num):
        ind_race = self.get_race_info(race_num)
        return str(ind_race.get('status')).lower() == 'complete'

    def is_race_next(self, race_num):
        ind_race = self.get_race_info(race_num)
        return str(ind_race.get('status')).lower() == 'next'

    def set_results(self, race_num, win, place, show):
        ind_race = self.get_race_info(race_num)
        
        ind_race['win'] = win
        ind_race['place'] = place
        ind_race['show'] = show
        ind_race['status'] = 'complete'
        with self.lock:
            self.races[str(int(race_num))] = ind_race

        if str(int(race_num) + 1) in self.races.keys():
            next_race = self.get_race_info(int(race_num)+1)
            next_race['status'] = 'next'
            with self.lock:
                self.races[str(int(int(race_num)+1))] = next_race

        self._save_races()
    
    def has_results(self, race_num):
        ind_race = self.get_race_info(race_num)
        win_bool = isinstance(ind_race.get('win'), int)
        place_bool = isinstance(ind_race.get('place'), int)
        show_bool = isinstance(ind_race.get('show'), int)
        return win_bool and place_bool and show_bool

    def get_results(self, race_num):
        ind_race = self.get_race_info(race_num)
        if self.has_results(race_num):
            return {'win': ind_race.get('win'), 'place': ind_race.get('place'), 'show': ind_race.get('show')}
        
    def get_upcoming_races(self, minutes_ahead):
        assert isinstance(minutes_ahead, int) or isinstance(minutes_ahead, float), 'Expected a number of minutes ahead, received {}'.format(minutes_ahead)
        now_ts = dt.datetime.now()
        upcoming = []

        for r_id in sorted(list(self.races.keys())):
            r_dict = self.get_race_info(str(int(r_id)))
            if str(r_dict['status']).lower() == 'closed':
                continue

            post_time = dt.datetime.fromisoformat(r_dict['post_time'])
            minutes_until = (post_time - now_ts).total_seconds() / 60.

            if (0 <= minutes_until <= minutes_ahead):
                upcoming.append(r_dict)

        return upcoming
    
    def get_previous_race(self, race_num):
        if str(int(race_num) - 1) not in self.races.keys():
            return {}
        
        prev_race = self.get_race_info(int(race_num) - 1)
        return prev_rece            
    
    def close_betting(self, race_num):
        ind_race = self.get_race_info(race_num)
        ind_race['status'] = 'closed'

        with self.lock:
            self.races[str(int(race_num))] = ind_race
        self._save_races()

    def add_race(self, race_id, race_desc, post_time):
        if str(int(race_id)) in self.races.keys():
            raise KeyError('The race ID provided ({}) already exists.'.format(race_id))
        
        new_race = {
            'race_id': race_id,
            'race_description': race_desc,
            'post_time': post_time.isoformat(),
            'win': None, 
            'place': None, 
            'show': None,
            'status': 'pending'
        }

        with self.lock:
            self.races[str(int(race_id))] = new_race
        self._save_races()

_RACE_MANAGER = RaceManager()
