# Imports
from googleapiclient.discovery import build
import threading
from time import sleep
from datetime import datetime
import json
from utils import google_api as gapi
from utils.io_tools import find_project_root


_BASE_DIR = find_project_root()
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


def poll_google_sheets(update_time=5):
    service = get_sheet_service()

    while True:
        try:
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID,
                range=RANGE_NAME
            ).execute()

            values = result.get('values', [])

            if not values:
                continue
            
            headers = values[0]
            all_rows = values[1:]

            new_rows = all_rows[state.last_processed_row:]

            if new_rows:
                print(f'Found {len(new_rows)} new wagers')

                new_wagers = []
                for row in new_rows:
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = row[i] if i < len(row) else ''
                    
                    processed = process_wager(row_dict)
                    new_wagers.append(processed)

                state.update(new_wagers, len(all_rows))
                print(f'Processed {len(new_wagers)} new wagers. Total: {len(state.get_all())}')

        except Exception as e:
            print(f'Error polling sheets: {e}')
        
        sleep(update_time)

