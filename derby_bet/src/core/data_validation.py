
def normalize_wager_fields(wager_data):
    field_map = {
        'Timestamp': 'timestamp_google', 
        'Player Name (First + Last pls)': 'player_name',
        'Player Name': 'player_name',
        'Race Number (1 - 14)': 'race_number', 
        'Race Number': 'race_number',
        'Win Post Position (1 - 20)': 'win_post',
        'Win Post': 'win_post',
        'Win Bid': 'win_bid',
        'Place Post Position (1 - 20)': 'place_post',
        'Place Post': 'place_post',
        'Place Bid': 'place_bid',
        'Show Post Position (1 - 20)': 'show_post',
        'Show Post': 'show_post',
        'Show Bid': 'show_bid'
    }

    output = {}
    for k, v in wager_data.items():
        output[field_map.get(k, k.lower().strip().replace(' ', '_'))] = v
    return output


def normalize_trsc_fields(trsc_data):
    field_map = {
        'Timestamp': 'timestamp_google', 
        'PlayerID': 'player_id',
        'Player ID': 'player_id',
        'VenmoAmount': 'amount_received',
        'Venmo Amount': 'amount_received'
    }

    output = {}
    for k, v in trsc_data.items():
        output[field_map.get(k, k.lower().strip().replace(' ', '_'))] = v
    return output


def _parse_post_bid(post_raw, bid_raw, field_name):
    """Parse a post + bid pair. Returns (post, bid, error).

    Both blank  -> (None, 0, None)   — no bet placed, not an error
    One blank   -> (None, 0, error)  — incompatible pair
    Non-integer -> (None, 0, error)  — bad value
    Both valid  -> (int, int, None)
    """
    def _clean(v):
        return str(v).strip().replace(' ', '').replace('\t', '').replace('-', '').replace('_', '')

    post_clean = _clean(post_raw)
    bid_clean = _clean(bid_raw)
    post_blank = len(post_clean) == 0
    bid_blank = len(bid_clean) == 0

    if post_blank and bid_blank:
        return None, 0, None

    if post_blank != bid_blank:
        return None, 0, 'Incompatible {} post + bid: "{}" & "{}"'.format(field_name, post_raw, bid_raw)

    try:
        post = int(post_clean)
    except ValueError:
        return None, 0, 'Invalid {} post value: "{}"'.format(field_name, post_raw)

    try:
        bid = int(bid_clean)
    except ValueError:
        return None, 0, 'Invalid {} bid value: "{}"'.format(field_name, bid_raw)

    return post, bid, None


def _safe_int(value, default=0):
    try:
        value = str(value).strip().replace(' ', '').replace('\t', '').replace('-', '').replace('_', '')
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_float(value, default=0.0):
    try:
        value = str(value).strip().replace(' ', '').replace('\t', '').replace('-', '').replace('_', '')
        return float(value)
    except (ValueError, TypeError):
        return default


def normalize_trsc_values(trsc_data):
    output = trsc_data.copy()
    output['player_id'] = _safe_int(output.get('player_id', 0))
    output['amount_received'] = _safe_float(output.get('amount_received', 0.))
    return output


def normalize_wager_values(wager_data):
    output = wager_data.copy()
    output['race_number'] = _safe_int(output.get('race_number', 0))
    output['player_id'] = _safe_int(output.get('player_id', 0))
    return output

