# Imports
from pathlib import Path
import threading
from derby_bet.src.utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
_DRB_DIR = Path(_BASE_DIR, 'drb')

class WagerState:

    def __init__(self):
        self.all_wagers_unprocessed = []
        self.all_wagers_processed = []
        self.last_processed_row = 0
        self.lock = threading.Lock()
    
    def update(self, new_unp_wagers, new_proc_wagers, total_rows):
        with self.lock:
            self.all_wagers_unprocessed.extend(new_unp_wagers)
            self.all_wagers_processed.extend(new_proc_wagers)
            self.last_processed_row = total_rows
    
    def get_all(self, processed=False):
        with self.lock:
            if processed:
                return self.all_wagers_processed.copy()
            else:
                return self.all_wagers_unprocessed.copy()

    def get_wagers_by_race(self, race_num):
        proc_wagers = self.get_all(processed=True)
        filtered_wagers = []
        for wager in proc_wagers:
            if int(wager.get('race_number', 0)) == int(race_num):
                filtered_wagers.append(wager)
            
        return filtered_wagers
    
    def get_wagers_by_player(self, player_name=None, player_id=None)
        assert (not isinstance(player_name, type(None))) or (not isinstance(player_id, type(None))), 'Expected either player name or player ID to be populated.'

        proc_wagers = self.get_all(processed=True)
        filtered_wagers = []
        for wager in proc_wagers:
            if (not isinstance(player_id, type(None))) and (int(wager.get('player_id', 0)) == int(player_id)):
                filtered_wagers.append(wager)
            elif (not isinstance(player_name, type(None))) and (str(wager.get('player_name', '')) == str(player_name)):
                filtered_wagers.append(wager)
        
        return filtered_wagers
    
    def get_wagers_by_race_and_player(self, race_num, player_name=None, player_id=None):
        assert (not isinstance(player_name, type(None))) or (not isinstance(player_id, type(None))), 'Expected either player name or player ID to be populated.'

        proc_wagers = self.get_all(processed=True)
        filtered_wagers = []
        for wager in proc_wagers:
            if int(wager.get('race_number', 0)) == int(race_num):
                if (not isinstance(player_id, type(None))) and (int(wager.get('player_id', 0)) == int(player_id)):
                    filtered_wagers.append(wager)
                elif (not isinstance(player_name, type(None))) and (str(wager.get('player_name', '')) == str(player_name)):
                    filtered_wagers.append(wager)

        return filtered_wagers  


if __name__ == '__main__':
    start_background_polling()
    sleep(1200)
