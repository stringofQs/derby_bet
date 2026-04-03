# Imports
from pathlib import Path
import threading


class TransactionManager:

    def __init__(self):
        self.all_transactions_unprocessed = []
        self.all_transactions_processed = []
        self.last_processed_row = 0
        self.lock = threading.Lock()
    
    def update(self, new_unp_transactions, new_proc_transactions, total_rows):
        with self.lock:
            self.all_transactions_unprocessed.extend(new_unp_transactions)
            self.all_transactions_processed.extend(new_proc_transactions)
            self.last_processed_row = total_rows
    
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
