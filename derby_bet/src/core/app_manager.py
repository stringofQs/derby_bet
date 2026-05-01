# Imports
from time import sleep
from pathlib import Path
import threading
import pandas as pd
import json
import datetime as dt
import logging

from derby_bet.src.utils import google_api as gapi
from derby_bet.src.utils.io_tools import find_project_root
from derby_bet.src.core.data_validation import normalize_wager_fields, normalize_wager_values, normalize_trsc_fields, normalize_trsc_values, _parse_post_bid
from derby_bet.src.core.transaction_manager import TransactionManager
from derby_bet.src.core.race_manager import RaceManager
from derby_bet.src.core.player_manager import PlayerManager
from derby_bet.src.core.pool_manager import PoolManager
from derby_bet.src.core.wager_state import WagerState
from derby_bet.src.core.payout_calculator import PayoutCalculator

_BASE_DIR = find_project_root()
_DRB_DIR = Path(_BASE_DIR, 'drb')


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
        self.sse_push_callback = None

        # Initialize all managers
        self.transaction_manager = TransactionManager()
        self.race_manager = RaceManager()
        self.player_manager = PlayerManager()
        self.pool_manager = PoolManager()
        self.wager_state = WagerState()
        self.payout_calculator = PayoutCalculator()

        self._initialized = True

    def validate_wager_data(self, wager_data):
        logging.debug('Validating wager data.')
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
                
                win_post, win_bid, win_err = _parse_post_bid(
                    norm_wager_data.get('win_post', ''), norm_wager_data.get('win_bid', ''), 'win'
                )
                if win_err:
                    errors.append(win_err)
                norm_wager_data['win_post'] = win_post if win_post is not None else ''
                norm_wager_data['win_bid'] = win_bid

                place_post, place_bid, place_err = _parse_post_bid(
                    norm_wager_data.get('place_post', ''), norm_wager_data.get('place_bid', ''), 'place'
                )
                if place_err:
                    errors.append(place_err)
                norm_wager_data['place_post'] = place_post if place_post is not None else ''
                norm_wager_data['place_bid'] = place_bid

                show_post, show_bid, show_err = _parse_post_bid(
                    norm_wager_data.get('show_post', ''), norm_wager_data.get('show_bid', ''), 'show'
                )
                if show_err:
                    errors.append(show_err)
                norm_wager_data['show_post'] = show_post if show_post is not None else ''
                norm_wager_data['show_bid'] = show_bid

                total_bids = win_bid + place_bid + show_bid
                norm_wager_data['total_bid'] = total_bids

                if player_id == -1:
                    # Player is already invalid — don't query bids against a phantom player
                    norm_wager_data['player_has_bids'] = False
                elif self.player_manager.has_bids_available(total_bids, player_name=player_name):
                    norm_wager_data['player_has_bids'] = True
                else:
                    norm_wager_data['player_has_bids'] = False
                    errors.append('{} does not have {} bids available to fulfill wager.'.format(player_name, total_bids))
                
                if (len(errors) > 0):
                    norm_wager_data['valid'] = False
                else:
                    norm_wager_data['valid'] = True
                
                err_str = '; '.join(errors)
                norm_wager_data['errors'] = err_str

                if len(errors) > 0:
                    logging.error('Wager validation error(s): {}'.format(err_str))

                output_wagers.append(norm_wager_data)

        return output_wagers

    def validate_transaction_data(self, trsc_data):
        logging.debug('Validating transaction data.')
        output_trsc = []
        
        for trsc in trsc_data:
            errors = []
            out1 = normalize_trsc_fields(trsc)
            norm_trsc_data = normalize_trsc_values(out1)

            with self.global_lock:
                player_id = norm_trsc_data.get('player_id', 0)
                if not self.player_manager.is_valid_player(player_id=player_id):
                    errors.append('Invalid player ID received in transaction: {}'.format(player_id))
                
                amount_received = float(norm_trsc_data.get('amount_received', 0.))
                if amount_received <= 0.:
                    errors.append('Invalid transaction amount received: {}'.format(amount_received))
                    bids_received = 0
                else:
                    bids_received = amount_received / self.transaction_manager._BID_VALUE_
                
                norm_trsc_data['bids_received'] = float(bids_received)
                
                if (len(errors) > 0):
                    norm_trsc_data['valid'] = False
                else:
                    norm_trsc_data['valid'] = True
                
                err_str = '; '.join(errors)
                norm_trsc_data['errors'] = err_str

                if len(errors) > 0:
                    logging.error('Transaction validation error(s): {}'.format(err_str))

                output_trsc.append(norm_trsc_data)
        
        return output_trsc

    def place_valid_wagers(self, in_data):
        self._apply_bids_to_pool(in_data)
        self._apply_bids_to_player_data(in_data)

    def _apply_bids_to_pool(self, in_data):
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

    def _apply_bids_to_player_data(self, in_data):
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

    def receive_player_transactions(self, trsc_data):
        for trsc in trsc_data:
            if isinstance(trsc, dict) and (trsc.get('valid', False)):
                player_id = trsc.get('player_id', 0)
                bids_received = trsc.get('bids_received', 0.)

                with self.global_lock:
                    self.player_manager.purchase_bids(bids_received, player_id=str(player_id))

    def finalize_race(self, race_num, win_post, place_post, show_post):
        logging.info('Finalize Race: race_num={} | win_post={} | place_post={} | show_post={}'.format(race_num, win_post, place_post, show_post))
        with self.global_lock:
            if not self.race_manager.is_valid_race(race_num):
                logging.error('Invalid race number: {}'.format(race_num))
                raise ValueError('Received invalid race number: {}'.format(race_num))

            if self.race_manager.has_results(race_num):
                logging.error('Race results already exist for race {}'.format(race_num))
                raise ValueError('Race results already set for race {}'.format(race_num))
            
            if not all(1 <= int(h) <= 20 for h in [win_post, place_post, show_post]):
                logging.error('Invalid post values received: {}, {}, {}'.format(win_post, place_post, show_post))
                raise ValueError('Invalid posts: {}, {}, {}'.format(win_post, place_post, show_post))
            
            if len(list(set([win_post, place_post, show_post]))) != 3:
                logging.error('Non-unique post values received: {}'.format(win_post, place_post, show_post))
                raise ValueError('Expected win, place, and show posts to be unique. Received {}, {}, {}'.format(win_post, place_post, show_post))
            
            self.race_manager.set_results(race_num, win_post, place_post, show_post)
            
            result_map = {
                'win': [win_post],
                'place': [place_post, win_post],
                'show': [show_post, place_post, win_post]
            }

            for bet_type, posts in result_map.items():
                pool_dict = self.pool_manager.get_pool_info(race_num, spec_pool=bet_type)
                pool_total = self.pool_manager.total_in_bet_type(race_num, bet_type)
                wagers = self.wager_state.get_wagers_by_race(race_num)

                first_payout, last_payout = self.payout_calculator.calculate_payouts(race_num, bet_type, posts, pool_dict, wagers, pool_total)
                race_payouts = self.payout_calculator.get_payouts_between_ids(first_payout, last_payout)

                for transaction in race_payouts:
                    profit = float(transaction.get('bid_profit', 0.))
                    player_id = transaction.get('player_id', 0)
                    if (profit <= 0):
                        self.player_manager.set_losing_bid(abs(profit), player_id=player_id)
                    else:
                        self.player_manager.set_winning_bid(abs(profit), transaction.get('bid_wagered', 0), player_id=player_id)
    
    def invalidate_wager(self, wager_id):
        wager = self.wager_state.get_wager_by_id(wager_id)
        if not wager:
            raise ValueError(f'Wager {wager_id} not found')
        if not wager.get('valid', False):
            raise ValueError(f'Wager {wager_id} was not valid and cannot be invalidated')
        if wager.get('invalidated', False):
            raise ValueError(f'Wager {wager_id} is already invalidated')

        race_num = wager.get('race_number', 0)
        if self.race_manager.is_race_complete(race_num):
            raise ValueError(f'Race {race_num} is already complete; wager cannot be invalidated')

        win_post = wager.get('win_post', '')
        win_bid = wager.get('win_bid', 0)
        place_post = wager.get('place_post', '')
        place_bid = wager.get('place_bid', 0)
        show_post = wager.get('show_post', '')
        show_bid = wager.get('show_bid', 0)
        player_id = wager.get('player_id', 0)
        total = sum(int(b) for b in [win_bid, place_bid, show_bid] if len(str(b)) > 0)

        with self.global_lock:
            if len(str(win_post)) > 0:
                self.pool_manager.apply_to_win_pool(race_num, win_post, -int(win_bid))
            if len(str(place_post)) > 0:
                self.pool_manager.apply_to_place_pool(race_num, place_post, -int(place_bid))
            if len(str(show_post)) > 0:
                self.pool_manager.apply_to_show_pool(race_num, show_post, -int(show_bid))
            self.player_manager.unplace_bids(total, player_id=str(player_id))

        self.wager_state.mark_wager_invalidated(wager_id)
        logging.info(f'Wager {wager_id} invalidated successfully')

    def get_current_race_odds(self):
        cur_race = self.race_manager.get_next_race()
        if not cur_race:
            return {}
        cur_race_id = int(cur_race.get('race_id', 0))

        cur_race_pool = self.pool_manager.get_pool_info(race_num=str(cur_race_id))
        return cur_race_pool.copy()


app_manager = AppManager()


def save_latest_wager(wager_dir, wager_data, processed=False):
    if not Path(wager_dir).exists():
        Path(wager_dir).mkdir(parents=True)
    proc = 'processed' if processed else 'unprocessed'
    logging.debug('Saving {} wager data'.format(proc))
    with open(str(Path(wager_dir, f'wager_timeline_{proc}.json')), 'a') as file:
        file.write(json.dumps({
            'timestamp': dt.datetime.now().isoformat(),
            'wager': wager_data
        }) + '\n')


def save_latest_trsc(trsc_dir, trsc_data, processed=False):
    if not Path(trsc_dir).exists():
        Path(trsc_dir).mkdir(parents=True)
    proc = 'processed' if processed else 'unprocessed'
    logging.debug('Saving {} transaction data'.format(proc))
    with open(str(Path(trsc_dir, f'transaction_timeline_{proc}.json')), 'a') as file:
        file.write(json.dumps({
            'timestamp': dt.datetime.now().isoformat(),
            'transaction': trsc_data
        }) + '\n')


def process_wager(wager_data):
    logging.debug('Processing wager')
    wager_dir = Path(_DRB_DIR, 'wagers')
    save_latest_wager(wager_dir, wager_data, processed=False)
    
    valid_wagers = app_manager.validate_wager_data(wager_data)  # Wager validation
    app_manager.place_valid_wagers(valid_wagers)  # Post validated wagers to relevant pools and player data

    save_latest_wager(wager_dir, valid_wagers, processed=True)

    return valid_wagers


def process_transaction(trsc_data):
    logging.debug('Processing transaction')
    trsc_dir = Path(_DRB_DIR, 'transactions')
    save_latest_trsc(trsc_dir, trsc_data, processed=False)
    
    valid_trsc = app_manager.validate_transaction_data(trsc_data)  # Wager validation
    app_manager.receive_player_transactions(valid_trsc)

    save_latest_trsc(trsc_dir, valid_trsc, processed=True)

    return valid_trsc


def output_state_wgr(state_data, processed=False):
    wager_dir = Path(_DRB_DIR, 'wagers')
    if not Path(wager_dir).exists():
        Path(wager_dir).mkdir(parents=True)
    df = pd.DataFrame(state_data)
    proc = 'processed' if processed else 'unprocessed'
    logging.debug('Outputting {} wager state dataset'.format(proc))
    df.to_csv(str(Path(wager_dir, f'wager_state_{proc}.csv')), index=False)


def output_state_trs(state_data, processed=False):
    trsc_dir = Path(_DRB_DIR, 'transactions')
    if not Path(trsc_dir).exists():
        Path(trsc_dir).mkdir(parents=True)
    df = pd.DataFrame(state_data)
    proc = 'processed' if processed else 'unprocessed'
    logging.debug('Outputting {} transaction state dataset'.format(proc))
    df.to_csv(str(Path(trsc_dir, f'transactions_{proc}.csv')), index=False)


def poll_wagers(update_time=5):
    while True:
        try:
            all_responses = gapi.get_form_responses(gapi.WAGER_RANGE_NAME)
            new_responses = all_responses[app_manager.wager_state.last_processed_row:]
            if not new_responses:
                app_manager.wager_state.update([], [], len(all_responses))
                sleep(update_time)
                continue
            new_processed = process_wager(new_responses)
            app_manager.wager_state.update(new_responses, new_processed, len(all_responses))
            if (len(new_responses) > 0):
                output_state_wgr(app_manager.wager_state.get_all(processed=False), processed=False)
                output_state_wgr(app_manager.wager_state.get_all(processed=True), processed=True)

                if app_manager.sse_push_callback:
                    results = []
                    for w in new_processed:
                        bets = []
                        if str(w.get('win_post', '')).strip():
                            bets.append({'type': 'Win', 'post': w.get('win_post'), 'bid': w.get('win_bid', 0)})
                        if str(w.get('place_post', '')).strip():
                            bets.append({'type': 'Place', 'post': w.get('place_post'), 'bid': w.get('place_bid', 0)})
                        if str(w.get('show_post', '')).strip():
                            bets.append({'type': 'Show', 'post': w.get('show_post'), 'bid': w.get('show_bid', 0)})
                        results.append({
                            'player_name': w.get('player_name', 'Unknown'),
                            'race_number': w.get('race_number', '?'),
                            'valid': w.get('valid', False),
                            'total_bid': w.get('total_bid', 0),
                            'bets': bets,
                            'errors': w.get('errors', ''),
                            'timestamp': dt.datetime.now().isoformat()
                        })
                    app_manager.sse_push_callback({
                        'type': 'wager_processed',
                        'results': results
                    })

            logging.info(f'Processed {len(new_processed)} new wagers. Total received: {len(all_responses)}')

        except Exception as e:
            logging.error(f'Error polling sheets for wagers: {e}', exc_info=True)
        
        sleep(update_time)


def poll_transactions(update_time=10):
    while True:
        try:
            all_responses = gapi.get_form_responses(gapi.TRANSACTION_RANGE_NAME)
            new_responses = all_responses[app_manager.transaction_manager.last_processed_row:]
            if not new_responses:
                app_manager.transaction_manager.update([], [], len(all_responses))
                sleep(update_time)
                continue
            new_processed = process_transaction(new_responses)
            app_manager.transaction_manager.update(new_responses, new_processed, len(all_responses))
            if (len(new_responses) > 0):
                output_state_trs(app_manager.transaction_manager.get_all(processed=False), processed=False)
                output_state_trs(app_manager.transaction_manager.get_all(processed=True), processed=True)

                if app_manager.sse_push_callback:
                    results = []
                    for t in new_processed:
                        player_info = app_manager.player_manager.get_player_info(player_id=t.get('player_id', 0))
                        results.append({
                            'player_name': player_info.get('player_name', 'Unknown'),
                            'amount_received': t.get('amount_received', 0.),
                            'bids_received': t.get('bids_received', 0.),
                            'valid': t.get('valid', False),
                            'errors': t.get('errors', ''),
                            'timestamp': dt.datetime.now().isoformat()
                        })
                    app_manager.sse_push_callback({
                        'type': 'transaction_processed',
                        'results': results
                    })

            logging.info(f'Processed {len(new_processed)} new transactions. Total received: {len(all_responses)}')

        except Exception as e:
            logging.error(f'Error polling sheets for transactions: {e}')
        
        sleep(update_time)


def start_background_polling():
    poll_wgrs = threading.Thread(target=poll_wagers, daemon=True)
    poll_wgrs.start()
    poll_trsc = threading.Thread(target=poll_transactions, daemon=True)
    poll_trsc.start()
    logging.info('Background polling started')


if __name__ == '__main__':
    start_background_polling()
    sleep(1200)