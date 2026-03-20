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


if __name__ == '__main__':
    start_background_polling()
    sleep(1200)
