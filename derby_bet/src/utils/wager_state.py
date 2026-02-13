# Imports
from googleapiclient.discovery import build
import threading
from time import sleep
from datetime import datetime
import json
from utils import google_api as gapi


_BASE_DIR = next(p for p in Path(__file__).resolve().parents if p.name == 'derby_bet')
_DRB_DIR = Path(_BASE_DIR, 'src', 'drb')

class WagerState:

    def __init__(self):
        self.all_wagers = []
        self.last_processed_row = 1
        self.lock = threading.Lock()
    
    def update(self, new_wagers, total_rows):
        with self.lock:
            self.all_wagers.extend(new_wagers)
            self.last_processed_row = total_rows
    
    def get_all(self):
        with self.lock:
            return self.all_wagers.copy()
    

def process_wager(wager_data):
    print(f'Processing wager: {wager_data}')

    # Processing logic calls here

    with open(str(Path(_DRB_FP, 'wagers', 'wager_log_unprocessed.json')), 'a') as file:
        file.write(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'wager': wager_data
        }) + '\n')

    return wager_data


def poll_google_sheets():
    service = get_sheet_service()

