"""Derby App - Kentucky Derby party wagering system."""

__version__ = '0.1.0'

# Import key components
from derby_bet.src.core.wager_state import WagerState
from derby_bet.src.core.race_manager import RaceManager
from derby_bet.src.core.player_manager import PlayerManager
from derby_bet.src.core.payout_calculator import PayoutCalculator
from derby_bet.src.core.pool_manager import PoolManager
from derby_bet.src.core.transaction_manager import TransactionManager
from derby_bet.src.core.app_manager import AppManager, process_wager, poll_wagers, process_transaction, poll_transactions, start_background_polling
from derby_bet.src.utils.google_api import get_sheet_service, get_form_responses
from derby_bet.src.utils.io_tools import find_project_root
from derby_bet.src.utils.log_utils import setup_logger

__all__ = [
    'WagerState',
    'RaceManager',
    'PlayerManager',
    'PayoutCalculator',
    'PoolManager',
    'TransactionManager',
    'AppManager',
    'process_wager',
    'pool_wager',
    'process_transaction',
    'poll_transactions',
    'start_background_polling',
    'get_sheet_service',
    'get_form_responses',
    'find_project_root',
    'setup_logger'
]