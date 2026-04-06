# Imports
import logging
import os
import threading
import datetime as dt
from flask import Flask, render_template, jsonify, request
import webbrowser

from derby_bet.src.utils.log_utils import setup_logger
from derby_bet.src.core.app_manager import app_manager

# Inputs --------------------------
LOG_LEVEL = logging.DEBUG
_PORT = 5050

# Setup ---------------------------
setup_logger('error_log', level=logging.ERROR, console=True, file=True, filename='error.log')
setup_logger('debug_log', level=logging.DEBUG, console=False, file=True, filename='debug.log')
_DEBUG = LOG_LEVEL == logging.DEBUG

app = Flask(__name__)

def _base_jsonify_return(success, message):
    return {'_success': success, '_message': message}

@app.route('/')
def index():
    logging.debug('LOAD: index.html')
    return render_template('index.html')

@app.route('/api/dashboard-data')
def get_dashboard_data():
    msg = []
    players = None
    current_race_pool = None
    previous_race = None

    try:
        players = app_manager.player_manager.get_all_players_sorted(lastname_alpha=True)
    except _:
        msg.append('Error fetching player data from PlayerManager')
        logging.error('Error fetching player data from PlayerManager', exc_info=True)
    
    try:
        current_race_pool = app_manager.get_current_race_odds()
    except _:
        msg.append('Error fetching current race pool data from AppManager (via PoolManager)')
        logging.error('Error fetching current race pool data from AppManager (via PoolManager)', exc_info=True)

    try:
        previous_race = app_manager.race_manager.get_previous_race()
    except _:
        msg.append('Error fetching previous race data from RaceManager')
        logging.error('Error fetching prevous race data from RaceManager', exc_info=True)
    

    success = (len(msg) == 0)
    if len(msg) > 0:
        message = '; '.join(msg)
    else:
        message = 'Successfully fetched data'

    ret_json = _base_jsonify_return(success=success, message=message)
    ret_json['players'] = players
    ret_json['current_race_pool'] = current_race_pool
    ret_json['previous_race'] = previous_race
    ret_json['timestamp'] = dt.datetime.now().isoformat()
    return jsonify(ret_json)

def open_browser():
    logging.debug(f'Opening browser at 127.0.0.1:{_PORT}')
    webbrowser.open_new(f'http://127.0.0.1:{_PORT}')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Timer(1.0, open_browser).start()
    app.run(port=_PORT, debug=_DEBUG)
