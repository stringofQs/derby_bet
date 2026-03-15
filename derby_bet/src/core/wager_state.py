# Imports
from pathlib import Path
import threading
from time import sleep
from datetime import datetime
import json
import pandas as pd
from googleapiclient.discovery import build

from derby_bet.src.utils import google_api as gapi
from derby_bet.src.utils.io_tools import find_project_root
from derby_bet.src.core.wager_validation import validate_wager_data


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
    

_STATE_ = WagerState()

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
    
    valid_wagers = validate_wager_data(wager_data)  # Wager validation
    # TODO: @PF Pass valid wagers on to other processes that include moving player bids to pending and adding to relevant pools

    save_latest_wager(wager_dir, wager_data, processed=True)

    return wager_data


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
            new_responses = all_responses[_STATE_.last_processed_row:]
            new_processed = process_wager(new_responses)
            _STATE_.update(new_responses, new_processed, len(all_responses))
            if (len(new_responses) > 0):
                output_state(_STATE_.get_all(processed=False), processed=False)
                output_state(_STATE_.get_all(processed=True), processed=True)

            print(f'Processed {len(new_processed)} new wagers. Total received: {len(all_responses)}')

        except Exception as e:
            print(f'Error polling sheets for wagers: {e}')
        
        sleep(update_time)


def start_background_polling():
    polling_thread = threading.Thread(target=poll_wagers, daemon=True)
    polling_thread.start()
    print('Background polling started')


if __name__ == '__main__':
    start_background_polling()
    sleep(120)
