# Imports
from pathlib import Path
import threading
import logging
import json

from derby_bet.src.utils.io_tools import find_project_root

_BASE_DIR = find_project_root()
_STATE_FILE = Path(_BASE_DIR, 'drb', 'transactions', 'transaction_row_state.json')


class TransactionManager:

    _BID_VALUE_ = 0.1  # 1 bid = $0.10

    def __init__(self):
        logging.info('Initialized TransactionManager')
        self.all_transactions_unprocessed = []
        self.all_transactions_processed = []
        self.lock = threading.Lock()
        self.last_processed_row = self._load_last_row()

    def _load_last_row(self):
        if Path(_STATE_FILE).exists():
            try:
                with open(str(_STATE_FILE), 'r') as f:
                    return int(json.load(f).get('last_processed_row', 0))
            except Exception:
                logging.warning('Could not load transaction row state; defaulting to 0')
        return 0

    def _save_last_row(self):
        try:
            _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(str(_STATE_FILE), 'w') as f:
                json.dump({'last_processed_row': self.last_processed_row}, f)
        except Exception as e:
            logging.error(f'Failed to save transaction row state: {e}')

    def update(self, new_unp_transactions, new_proc_transactions, total_rows):
        logging.debug(f'Updating transactions to new total {total_rows}')
        with self.lock:
            self.all_transactions_unprocessed.extend(new_unp_transactions)
            self.all_transactions_processed.extend(new_proc_transactions)
            self.last_processed_row = total_rows
        self._save_last_row()
    
    def get_all(self, processed=False):
        with self.lock:
            if processed:
                return self.all_transactions_processed.copy()
            else:
                return self.all_transactions_unprocessed.copy()
    
    def get_transactions_by_player(self, player_id):
        proc_transactions = self.get_all(processed=True)
        filtered_transactions = []
        for trsc in proc_transactions:
            if int(trsc.get('player_id', 0)) == int(player_id):
                filtered_transactions.append(trsc)
        
        return filtered_transactions
