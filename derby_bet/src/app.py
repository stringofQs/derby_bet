# Imports
import logging
import os
import threading
from flask import Flask, render_template, jsonify, request
import webbrowser

from derby_bet.utils import log_utils as lu

# Inputs --------------------------
LOG_LEVEL = logging.DEBUG
_PORT = 5050

# Setup ---------------------------
_LOGGER = lu.setup_logger(__name__, console=True, file=True, filename='log/app.log')
_DEBUG = LOG_LEVEL == logging.DEBUG
app = Flask(__name__)

@app.route('/')
def index():
    _LOGGER.debug('LOAD: index.html')
    return render_template('index.html')

def open_browser():
    _LOGGER.debug(f'Opening browser at 127.0.0.1:{_PORT}')
    webbrowser.open_new(f'http://127.0.0.1:{_PORT}')

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        threading.Timer(1.0, open_browser).start()
    app.run(port=_PORT, debug=_DEBUG)
