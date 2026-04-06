# Imports
import logging
import os
import threading
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

@app.route('/')
def index():
    logging.debug('LOAD: index.html')
    return render_template('index.html')

def open_browser():
    logging.debug(f'Opening browser at 127.0.0.1:{_PORT}')
    webbrowser.open_new(f'http://127.0.0.1:{_PORT}')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Timer(1.0, open_browser).start()
    app.run(port=_PORT, debug=_DEBUG)
