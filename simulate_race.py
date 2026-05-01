"""
Race simulation script.
Resets state, gives players bids, generates 30-50 wagers per pool,
finalizes the race exactly as the admin would, then reports results.
"""
import sys
import json
import random
import datetime as dt
from pathlib import Path

random.seed(42)

# ── locate project root before importing anything ──────────────────────
def _find_root():
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / 'pyproject.toml').exists():
            return p
        p = p.parent
    raise RuntimeError('Could not find pyproject.toml')

BASE = _find_root()
DRB  = BASE / 'drb'
sys.path.insert(0, str(BASE))

# ── Step 0: reset all data files BEFORE importing app_manager ──────────
PLAYERS = [
    (1,"Nichole Beck"),(2,"Paul Farmer"),(3,"Matt Leonard"),
    (4,"Emily Leonard"),(5,"Brent Murphy"),(6,"Ahana Sen"),
    (7,"David Hogan"),(8,"Audrey Ahlenius"),(9,"Nick Lowe"),
    (10,"Lilly Moss"),(11,"Molly McLeod"),(12,"Brian Hanks"),
    (13,"Adam Gray"),(14,"Katie Landers"),(15,"Abigail Horton"),
    (16,"Abby White"),(17,"Lauren Riehm"),(18,"Eli Harrison"),
    (19,"Brian Mobley"),
]

player_data = {}
for pid, name in PLAYERS:
    player_data[str(pid)] = {
        "player_id": pid, "player_name": name,
        "latest_update": dt.datetime.now().isoformat(),
        "bids": {"purchased":0,"available":0,"won":0,"active_pending":0,"lost":0,"placed":0}
    }

race_times = ["11:00","11:32","12:05","12:38","13:12","13:53",
              "14:38","15:23","16:06","16:50","17:39","18:57","20:00","20:33"]
race_desc  = {11:"Old Forester Turf Classic",
              12:"Kentucky Derby presented by Woodford Reserve"}
races_data = {}
for i in range(1, 15):
    races_data[str(i)] = {
        "race_id":i, "race_description": race_desc.get(i, f"Race {i}"),
        "post_time": f"2026-05-02T{race_times[i-1]}:00",
        "win":None,"place":None,"show":None,
        "status":"next" if i==2 else "pending"
    }

(DRB/'players'/'player_data.json').write_text(json.dumps(player_data, indent=2))
(DRB/'pool'/'pool_data.json').write_text('{}')
(DRB/'payouts'/'payouts_data.json').write_text('{}')
(DRB/'races'/'races_data.json').write_text(json.dumps(races_data, indent=2))
(DRB/'wagers'/'wager_row_state.json').write_text('{"last_processed_row": 0}')
(DRB/'wagers'/'wager_timeline_processed.json').write_text('')
(DRB/'wagers'/'wager_timeline_unprocessed.json').write_text('')
(DRB/'wagers'/'wager_state_processed.csv').write_text(
    'timestamp_google,player_name,race_number,win_post,win_bid,place_post,place_bid,show_post,show_bid,player_id,total_bid,player_has_bids,valid,errors,wager_id\n')
(DRB/'wagers'/'wager_state_unprocessed.csv').write_text(
    'Timestamp,Player Name (First + Last pls),Race Number (1 - 14),Win Post Position (1 - 20),Win Bid,Place Post Position (1 - 20),Place Bid,Show Post Position (1 - 20),Show Bid\n')
(DRB/'transactions'/'transaction_row_state.json').write_text('{"last_processed_row": 0}')
(DRB/'transactions'/'transaction_timeline_processed.json').write_text('')
(DRB/'transactions'/'transaction_timeline_unprocessed.json').write_text('')
(DRB/'transactions'/'transactions_processed.csv').write_text(
    'timestamp_google,player_id,amount_received,bids_received,valid,errors\n')
(DRB/'transactions'/'transactions_unprocessed.csv').write_text(
    'Timestamp,PlayerID,VenmoAmount\n')

print("[OK] Data files reset")

# ── Step 1: import app_manager (reads clean files) ─────────────────────
from derby_bet.src.core.app_manager import (
    app_manager, process_wager, process_transaction,
    output_state_wgr, output_state_trs
)

# ── Step 2: give every player 5 000 bids ($500 Venmo) ──────────────────
BIDS_EACH   = 5000
VENMO_EACH  = int(BIDS_EACH * 0.10)   # $500

raw_trsc_all  = []
proc_trsc_all = []
for pid, name in PLAYERS:
    raw  = [{"Timestamp": dt.datetime.now().isoformat(),
             "PlayerID": str(pid), "VenmoAmount": str(VENMO_EACH)}]
    proc = process_transaction(raw)
    raw_trsc_all.extend(raw)
    proc_trsc_all.extend(proc)

app_manager.transaction_manager.update(raw_trsc_all, proc_trsc_all, len(raw_trsc_all))
output_state_trs(app_manager.transaction_manager.get_all(processed=False), processed=False)
output_state_trs(app_manager.transaction_manager.get_all(processed=True),  processed=True)
print(f"[OK] {len(PLAYERS)} players each given {BIDS_EACH} bids")

# ── Step 3: generate wagers ────────────────────────────────────────────
RACE = 1

# Horses in the field — weighted toward a handful of favourites
# Posts NOT in this list get zero bets
FIELD = {
    3:  12,   # heavy favourite
    7:  10,   # second favourite
    12:  8,   # third
    5:   5,
    9:   5,
    14:  4,
    17:  4,
    1:   2,
    6:   2,
    11:  2,
    20:  1,   # extreme longshot
    16:  1,
}
POSTS     = list(FIELD.keys())
WEIGHTS   = list(FIELD.values())

def pick_post(exclude=()):
    candidates = [p for p in POSTS if p not in exclude]
    wts        = [FIELD[p] for p in candidates]
    return random.choices(candidates, weights=wts, k=1)[0]

def pick_bid():
    # Skewed toward smaller amounts; multiples of 5
    return random.choices(range(5, 105, 5),
                          weights=[max(1, 21-i) for i in range(20)], k=1)[0]

def ts(i):
    h = 10 + i // 60
    m = (i * 37) % 60
    s = (i * 19) % 60
    return f"4/30/2026 {h:02d}:{m:02d}:{s:02d}"

player_names = [name for _, name in PLAYERS]

# Produce exactly these pool-type combos so each pool lands in [30, 50]
COMBO_PLAN = (
    ['win']          * 18 +
    ['place']        * 10 +
    ['show']         * 10 +
    ['win','place']  * 8  +    # each entry = one wager covering 2 pools
    ['win','show']   * 6  +
    ['place','show'] * 6  +
    ['win','place','show'] * 7
)
# Win bets: 18 + 8 + 6 + 7 = 39
# Place bets: 10 + 8 + 6 + 7 = 31
# Show bets:  10 + 6 + 6 + 7 = 29  → bump show-only to 12
COMBO_PLAN = (
    ['win']          * 18 +
    ['place']        * 10 +
    ['show']         * 12 +
    ['win','place']  * 8  +
    ['win','show']   * 6  +
    ['place','show'] * 6  +
    ['win','place','show'] * 7
)
# Win: 18+8+6+7=39  Place: 10+8+6+7=31  Show: 12+6+6+7=31  ✓ all in [30,50]

random.shuffle(COMBO_PLAN)

wager_submissions = []
for i, pools in enumerate(COMBO_PLAN):
    player = random.choice(player_names)
    w = {
        "Timestamp":                    ts(i),
        "Player Name (First + Last pls)": player,
        "Race Number (1 - 14)":         str(RACE),
        "Win Post Position (1 - 20)":   str(pick_post()) if 'win'   in pools else "",
        "Win Bid":                       str(pick_bid())  if 'win'   in pools else "",
        "Place Post Position (1 - 20)": str(pick_post()) if 'place' in pools else "",
        "Place Bid":                     str(pick_bid())  if 'place' in pools else "",
        "Show Post Position (1 - 20)":  str(pick_post()) if 'show'  in pools else "",
        "Show Bid":                      str(pick_bid())  if 'show'  in pools else "",
    }
    wager_submissions.append(w)

# Process wagers one at a time (matches real per-form-submission flow)
raw_wgr_all  = []
proc_wgr_all = []
for w in wager_submissions:
    proc = process_wager([w])
    raw_wgr_all.append(w)
    proc_wgr_all.extend(proc)

app_manager.wager_state.update(raw_wgr_all, proc_wgr_all, len(raw_wgr_all))
output_state_wgr(app_manager.wager_state.get_all(processed=False), processed=False)
output_state_wgr(app_manager.wager_state.get_all(processed=True),  processed=True)

valid_wgr  = [w for w in proc_wgr_all if w.get('valid')]
win_pool   = app_manager.pool_manager.get_pool_info(RACE, 'win')
place_pool = app_manager.pool_manager.get_pool_info(RACE, 'place')
show_pool  = app_manager.pool_manager.get_pool_info(RACE, 'show')

print(f"[OK] {len(wager_submissions)} wager submissions processed  "
      f"({len(valid_wgr)} valid, {len(proc_wgr_all)-len(valid_wgr)} invalid)")
print(f"  Win  pool: {len(win_pool)} posts, {sum(win_pool.values())} total bids")
print(f"  Place pool: {len(place_pool)} posts, {sum(place_pool.values())} total bids")
print(f"  Show pool: {len(show_pool)} posts, {sum(show_pool.values())} total bids")

# ── Step 4: pick results & finalize ────────────────────────────────────
# Winning post = the most-bet post in the win pool (the favourite wins)
# Place/show drawn randomly from posts that have bets in those pools
win_post = int(max(win_pool, key=lambda p: win_pool[p]))

place_candidates = [int(p) for p in place_pool if int(p) != win_post and place_pool[p] > 0]
place_post = random.choice(place_candidates) if place_candidates else (win_post % 20) + 1

show_candidates = [int(p) for p in show_pool
                   if int(p) not in (win_post, place_post) and show_pool[p] > 0]
show_post = random.choice(show_candidates) if show_candidates else ((win_post + 1) % 20) + 1

print(f"\n[OK] Race result: WIN={win_post}  PLACE={place_post}  SHOW={show_post}")
app_manager.finalize_race(RACE, win_post, place_post, show_post)
print("[OK] Race finalized\n")

# ── Step 5: report ──────────────────────────────────────────────────────
SEP = "=" * 72

def label(post):
    post = int(post)
    if post == win_post:   return "<-- WIN"
    if post == place_post: return "<-- PLACE"
    if post == show_post:  return "<-- SHOW"
    return ""

print(SEP)
print("POOL BREAKDOWN")
print(SEP)

for pool_name, pool in [("WIN", win_pool), ("PLACE", place_pool), ("SHOW", show_pool)]:
    total = sum(pool.values())
    print(f"\n  {pool_name} POOL  (total = {total} bids)")
    print(f"  {'Post':>6}  {'Bids':>6}  {'Share':>7}  {''}  ")
    print(f"  {'------':>6}  {'------':>6}  {'-------':>7}")
    for post in sorted(pool, key=lambda x: -pool[x]):
        bids  = pool[post]
        share = bids / total * 100 if total else 0
        mk    = label(post)
        print(f"  Post {int(post):2d}  {bids:>6}  {share:>6.1f}%  {mk}")

# ── payout table ────────────────────────────────────────────────────────
payouts = app_manager.payout_calculator.payouts
id_to_name = {pid: name for pid, name in PLAYERS}

print(f"\n{SEP}")
print("PAYOUT RESULTS  (win pool | place pool | show pool)")
print(SEP)

for pool_name in ['win', 'place', 'show']:
    pool_obj  = {'win': win_pool, 'place': place_pool, 'show': show_pool}[pool_name]
    pool_total = sum(pool_obj.values())
    pool_pays  = [v for v in payouts.values() if v['bet_type'] == pool_name]

    wins_label = {'win': f"post {win_post}",
                  'place': f"posts {win_post} or {place_post}",
                  'show':  f"posts {win_post}, {place_post}, or {show_post}"}[pool_name]
    print(f"\n  {pool_name.upper()} POOL  (total={pool_total}  winning={wins_label})")
    print(f"  {'Player':<20} {'Post':>5} {'Wagered':>8} {'Paid':>8} {'Profit':>8}  Result")
    print(f"  {'-'*20} {'-'*5} {'-'*8} {'-'*8} {'-'*8}  ------")

    wins = losses = pushes = 0
    for p in sorted(pool_pays, key=lambda x: x['payout_id']):
        name    = id_to_name.get(p['player_id'], f"#{p['player_id']}")
        profit  = p['bid_profit']
        outcome = "WIN " if profit > 0 else ("LOSS" if profit < 0 else "PUSH")
        if profit > 0: wins   += 1
        elif profit < 0: losses += 1
        else: pushes += 1
        print(f"  {name:<20} {p['post']:>5} {p['bids_wagered']:>8.0f} {p['bids_paid']:>8.1f} {profit:>+8.1f}  {outcome}")

    paid_total = sum(p['bids_paid'] for p in pool_pays)
    conservation = "[OK]" if abs(paid_total - pool_total) < 0.01 else "[!!MISMATCH]"
    print(f"\n  Summary: {wins} wins, {losses} losses, {pushes} pushes")
    print(f"  Bids paid out: {paid_total:.1f}  (pool total: {pool_total})  {conservation}")

# ── final standings ─────────────────────────────────────────────────────
print(f"\n{SEP}")
print("FINAL PLAYER STANDINGS  (sorted by available bids, highest first)")
print(SEP)

all_players = app_manager.player_manager.get_all_players_sorted(by_avail=True)
header = f"  {'Player':<20} {'Purchased':>10} {'Available':>10} {'Won':>7} {'Lost':>7} {'Pending':>8}"
print(f"\n{header}")
print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*7} {'-'*7} {'-'*8}")
for p in all_players:
    b = p['bids']
    print(f"  {p['player_name']:<20} {b['purchased']:>10.0f} {b['available']:>10.0f} "
          f"{b['won']:>7.0f} {b['lost']:>7.0f} {b['active_pending']:>8.0f}")

# ── sanity checks ────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("SANITY CHECKS")
print(SEP)

for pool_name, pool_obj in [('win', win_pool), ('place', place_pool), ('show', show_pool)]:
    pool_total = sum(pool_obj.values())
    paid_total = sum(p['bids_paid'] for p in payouts.values() if p['bet_type'] == pool_name)
    ok = "[OK]" if abs(paid_total - pool_total) < 0.01 else "[!!]"
    print(f"  {ok} {pool_name.upper():5} pool: deposited={pool_total}  paid_out={paid_total:.1f}")

total_purchased = sum(app_manager.player_manager.players[k]['bids']['purchased']
                      for k in app_manager.player_manager.players)
total_available = sum(app_manager.player_manager.players[k]['bids']['available']
                      for k in app_manager.player_manager.players)
total_won       = sum(app_manager.player_manager.players[k]['bids']['won']
                      for k in app_manager.player_manager.players)
total_lost      = sum(app_manager.player_manager.players[k]['bids']['lost']
                      for k in app_manager.player_manager.players)
total_pending   = sum(app_manager.player_manager.players[k]['bids']['active_pending']
                      for k in app_manager.player_manager.players)

net_won_lost = total_won - total_lost
print(f"\n  Total purchased across all players: {total_purchased:.0f}")
print(f"  Total available after race:         {total_available:.0f}")
print(f"  Total still pending:                {total_pending:.0f}")
print(f"  Total won (net):                    {total_won:.0f}")
print(f"  Total lost (net):                   {total_lost:.0f}")
print(f"  Net won - lost (should be 0):       {net_won_lost:.1f}  {'[OK]' if abs(net_won_lost) < 0.01 else '[!!]'}")
print(f"  Conservation: available + pending = {total_available + total_pending:.0f}  "
      f"vs purchased = {total_purchased:.0f}  "
      f"{'[OK]' if abs((total_available + total_pending) - total_purchased) < 0.01 else '[!!]'}")
