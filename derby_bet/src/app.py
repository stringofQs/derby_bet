# Imports
import json
import logging
import os
import queue
import threading
import datetime as dt
from flask import Flask, render_template, jsonify, request, Response
import webbrowser

from derby_bet.src.utils.log_utils import setup_logger
from derby_bet.src.core.app_manager import app_manager, start_background_polling

# Inputs --------------------------
LOG_LEVEL = logging.DEBUG
_PORT = 5050

# Setup ---------------------------
setup_logger('error_log', level=logging.ERROR, console=True, file=True, filename='error.log')
setup_logger('debug_log', level=logging.DEBUG, console=False, file=True, filename='debug.log')
_DEBUG = LOG_LEVEL == logging.DEBUG

app = Flask(__name__)

# SSE client management
_sse_clients = []
_sse_lock = threading.Lock()

def _push_sse_event(data):
    """Push an event to all connected SSE clients."""
    with _sse_lock:
        for client_queue in _sse_clients[:]:
            client_queue.put(data)

app_manager.sse_push_callback = _push_sse_event

def _base_jsonify_return(success, message):
    return {'_success': success, '_message': message}


# ============================================================================
# PAGE ROUTE
# ============================================================================

@app.route('/')
def index():
    logging.debug('LOAD: index.html')
    return render_template('index.html')


# ============================================================================
# DATA API ROUTES
# ============================================================================

@app.route('/api/race-info')
def get_race_info():
    """Returns current and previous race data. Fetched once on page load and
    updated via SSE when a race is finalized."""
    msg = []
    current_race = None
    previous_race = None
    race_schedule = None

    try:
        current_race = app_manager.race_manager.get_next_race()
    except Exception:
        msg.append('Error fetching current race data')
        logging.error('Error fetching current race data from RaceManager', exc_info=True)

    try:
        previous_race = app_manager.race_manager.get_previous_race()
    except Exception:
        msg.append('Error fetching previous race data')
        logging.error('Error fetching previous race data from RaceManager', exc_info=True)
    
    try:
        race_schedule = app_manager.race_manager.get_upcoming_races(num_races=5)
    except Exception:
        msg.append('Error fetching race schedule')
        logging.error('Error fetching race schedule from RaceManager', exc_info=True)

    ret_json = _base_jsonify_return(
        success=len(msg) == 0,
        message='; '.join(msg) if msg else 'OK'
    )
    ret_json['current_race'] = current_race
    ret_json['previous_race'] = previous_race
    ret_json['race_schedule'] = race_schedule
    return jsonify(ret_json)


@app.route('/api/players')
def get_players():
    """Returns all players with their available bid counts. Polled frequently."""
    try:
        players = app_manager.player_manager.get_all_players_sorted(lastname_alpha=True)
        lead_players = app_manager.player_manager.get_lead_players(top_n=5)
        ret_json = _base_jsonify_return(success=True, message='OK')
        ret_json['all_players'] = players
        ret_json['lead_players'] = lead_players
        return jsonify(ret_json)
    except Exception:
        logging.error('Error fetching player data from PlayerManager', exc_info=True)
        ret_json = _base_jsonify_return(success=False, message='Error fetching player data')
        ret_json['all_players'] = []
        ret_json['lead_players'] = []
        return jsonify(ret_json), 500


@app.route('/api/odds')
def get_odds():
    """Returns the current race pool odds by post position. Polled frequently."""
    try:
        current_race_pool = app_manager.get_current_race_odds()
        ret_json = _base_jsonify_return(success=True, message='OK')
        ret_json['current_race_pool'] = current_race_pool
        return jsonify(ret_json)
    except Exception:
        logging.error('Error fetching current race pool data', exc_info=True)
        ret_json = _base_jsonify_return(success=False, message='Error fetching odds data')
        ret_json['current_race_pool'] = {}
        return jsonify(ret_json), 500


# ============================================================================
# SERVER-SENT EVENTS
# ============================================================================

@app.route('/api/events')
def sse_events():
    """SSE stream. Pushes race_finalized events to connected clients when a
    race is finalized via the admin panel."""
    def generate():
        client_queue = queue.Queue()
        with _sse_lock:
            _sse_clients.append(client_queue)
        try:
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            while True:
                try:
                    data = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with _sse_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/api/admin/finalize-race', methods=['POST'])
def admin_finalize_race():
    data = request.get_json()
    if not data:
        return jsonify(_base_jsonify_return(False, 'No JSON body received')), 400

    race_num = data.get('race_number')
    win_post = data.get('win_post')
    place_post = data.get('place_post')
    show_post = data.get('show_post')

    if not all([race_num, win_post, place_post, show_post]):
        return jsonify(_base_jsonify_return(False, 'Missing required fields')), 400

    try:
        app_manager.finalize_race(race_num, win_post, place_post, show_post)

        current_race = app_manager.race_manager.get_next_race()
        previous_race = app_manager.race_manager.get_race_info(race_num)
        race_schedule = app_manager.race_manager.get_upcoming_races(num_races=5)

        _push_sse_event({
            'type': 'race_finalized',
            'current_race': current_race,
            'previous_race': previous_race,
            'race_schedule': race_schedule
        })

        return jsonify(_base_jsonify_return(True, f'Race {race_num} finalized successfully'))
    except ValueError as e:
        return jsonify(_base_jsonify_return(False, str(e))), 400
    except Exception:
        logging.error('Error finalizing race', exc_info=True)
        return jsonify(_base_jsonify_return(False, 'Internal server error')), 500


@app.route('/api/admin/add-player', methods=['POST'])
def admin_add_player():
    data = request.get_json()
    if not data:
        return jsonify(_base_jsonify_return(False, 'No JSON body received for adding new player')), 400

    player_name = data.get('player_name')

    try:
        app_manager.player_manager.add_new_player(player_name)
        return jsonify(_base_jsonify_return(True, f'New player ({player_name}) successfully added.'))
    except Exception:
        logging.error('Error adding new player', exc_info=True)
        return jsonify(_base_jsonify_return(False, 'Internal server error')), 500

# ============================================================================
# STARTUP
# ============================================================================

def open_browser():
    logging.debug(f'Opening browser at 0.0.0.0:{_PORT}')
    webbrowser.open_new(f'http://0.0.0.0:{_PORT}')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not _DEBUG:
        start_background_polling()
        threading.Timer(1.0, open_browser).start()
    app.run(host='0.0.0.0', port=_PORT, debug=_DEBUG)
