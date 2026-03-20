# Imports
from time import sleep
from pathlib import Path
import threading
import pandas as pd
from googleapiclient.discovery import build

from derby_bet.src.utils import google_api as gapi
from derby_bet.src.utils.io_tools import find_project_root
from derby_bet.src.core.wager_validation import normalize_wager_fields, normalize_wager_values
from derby_bet.src.core.race_manager import RaceManager
from derby_bet.src.core.player_manager import PlayerManager
from derby_bet.src.core.pool_manager import PoolManager
from derby_bet.src.core.wager_state import WagerState
from derby_bet.src.core.payout_calculator import PayoutCalculator


_BASE_DIR = find_project_root()


class AppManager:

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.global_lock = threading.Lock()

        # Initialize all managers
        self.race_manager = RaceManager()
        self.player_manager = PlayerManager()
        self.pool_manager = PoolManager()
        self.wager_state = WagerState()
        self.payout_calculator = PayoutCalculator()

        self._initialized = True

    def validate_wager_data(self, wager_data):
        output_wagers = []

        for wager in wager_data:
            errors = []
            out1 = normalize_wager_fields(wager)
            norm_wager_data = normalize_wager_values(out1.copy())

            with self.global_lock:
                player_name = norm_wager_data.get('player_name', '').strip()
                if self.player_manager.is_valid_player(player_name=player_name):
                    player_id = self.player_manager._get_player_id(player_name=player_name)
                else:
                    errors.append('Invalid player name received: {}'.format(player_name))
                    player_id = -1
                norm_wager_data['player_id'] = player_id

                race_number = int(norm_wager_data.get('race_number', 0))
                if not self.race_manager.is_valid_race(race_number):
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

                if self.player_manager.has_bids_available(total_bids, player_name=player_name):
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

    def apply_bids_to_pool(self, in_data):
        for wager_data in in_data:
            if isinstance(wager_data, dict) and (wager_data.get('valid', False)):
                race_num = wager_data.get('race_number', 0)
                win_bid = wager_data.get('win_bid', 0)
                win_post = wager_data.get('win_post', 0)
                place_bid = wager_data.get('place_bid', 0)
                place_post = wager_data.get('place_post', 0)
                show_bid = wager_data.get('show_bid', 0)
                show_post = wager_data.get('show_post', 0)

                with self.global_lock:
                    if len(str(win_post)) > 0:
                        self.pool_manager.apply_to_win_pool(race_num, win_post, win_bid)
                    if len(str(place_post)) > 0:
                        self.pool_manager.apply_to_place_pool(race_num, place_post, place_bid)
                    if len(str(show_post)) > 0:
                        self.pool_manager.apply_to_show_pool(race_num, show_post, show_bid)

    def apply_bids_to_player_data(self, in_data):
        for wager_data in in_data:
            if isinstance(wager_data, dict) and (wager_data.get('valid', False)):
                race_num = wager_data.get('race_number', 0)
                win_bid = wager_data.get('win_bid', 0)
                place_bid = wager_data.get('place_bid', 0)
                show_bid = wager_data.get('show_bid', 0)
                player_id = wager_data.get('player_id', 0)
                total = 0
                if len(str(win_bid)) > 0:
                    total += int(win_bid)
                if len(str(place_bid)) > 0:
                    total += int(place_bid)
                if len(str(show_bid)) > 0:
                    total += int(show_bid)

                with self.global_lock:
                    self.player_manager.place_bids(total, player_id=str(player_id))


app_manager = AppManager()


def save_latest_wager(wager_dir, wager_data, processed=False):
    if not Path(wager_dir).exists():
        Path(wager_dir).mkdir(parents=True)
    proc = 'processed' if processed else 'unprocessed'
    with open(str(Path(wager_dir, f'wager_timeline_{proc}.json')), 'a') as file:
        file.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'wager': wager_data
        }) + '\n')


def process_wager(wager_data):
    print(f'Processing wager: {wager_data}')
    wager_dir = Path(_DRB_DIR, 'wagers')
    save_latest_wager(wager_dir, wager_data, processed=False)
    
    valid_wagers = app_manager.validate_wager_data(wager_data)  # Wager validation
    app_manager.apply_bids_to_pool(valid_wagers)  # Apply wager to pool tracking data
    app_manager.apply_bids_to_player_data(valid_wagers)  # Apply wager to player data

    save_latest_wager(wager_dir, valid_wagers, processed=True)

    return valid_wagers


def output_state(state_data, processed=False):
    wager_dir = Path(_DRB_DIR, 'wagers')
    if not Path(wager_dir).exists():
        Path(wager_dir).mkdir(parents=True)
    df = pd.DataFrame(state_data)
    proc = 'processed' if processed else 'unprocessed'
    df.to_csv(str(Path(wager_dir, f'wager_state_{proc}.csv')), index=False)


def poll_wagers(update_time=5):
    while True:
        try:
            all_responses = gapi.get_form_responses(gapi.WAGER_RANGE_NAME)
            new_responses = all_responses[app_manager.wager_state.last_processed_row:]
            new_processed = process_wager(new_responses)
            app_manager.wager_state.update(new_responses, new_processed, len(all_responses))
            if (len(new_responses) > 0):
                output_state(app_manager.wager_state.get_all(processed=False), processed=False)
                output_state(app_manager.wager_state.get_all(processed=True), processed=True)

            print(f'Processed {len(new_processed)} new wagers. Total received: {len(all_responses)}')

        except Exception as e:
            print(f'Error polling sheets for wagers: {e}')
        
        sleep(update_time)


def start_background_polling():
    polling_thread = threading.Thread(target=poll_wagers, daemon=True)
    polling_thread.start()
    print('Background polling started')
