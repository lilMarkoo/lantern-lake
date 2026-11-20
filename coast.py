"""Saltmarsh, the coast at the end of the river (2.0).

Once you own the rowboat, Harbourmaster Morwen writes to say the river is open. Row down it (about an hour,
less with a sail) to two new places to fish, Saltmarsh Pier and Kelp Rocks, where the tide comes and goes twice
a day and decides what bites. Up the steps from the pier is the harbour village (harbour.py): Morwen's daily
orders, Nell's fish stall, the Gull & Lantern inn, Ossian's boatyard, the dark old lighthouse and a beach to
comb. Light the lighthouse again and the Grey Mariner comes home.

Everything saved lives in g.coast (see new()). This module is rules and data; harbour.py draws the village.
"""
import math
import random

import pygame

from art import darken, lighten
from data import FISH_BY_ID, SEA_FISH, COAST_IDS, BAITS, BAIT_BY_ID

RIVER_MIN = 60                  # game minutes to row down (or back up) the river
SAIL_MIN = 20
OPEN_H, CLOSE_H = 420, 1200     # the harbour folk keep 7 AM to 8 PM (Sol never sleeps)

# the harbour folk: their own little friendships (0..50 points, 10 to a heart)
FOLK = {
    'morwen': dict(name='Morwen', title='Harbourmaster', shirt=(54, 76, 116), hair=(170, 170, 176), hat='captain',
                   gift=('coins', 300), gift_line="Here, a bonus from the harbour fund. Don't tell the gulls."),
    'nell': dict(name='Nell', title='Fishmonger', shirt=(176, 70, 66), hair=(120, 70, 44), hat='none',
                 gift=('bait', 'squid', 5), gift_line='Squid strips, on the house. The big ones love them.'),
    'ossian': dict(name='Ossian', title='Shipwright', shirt=(120, 96, 66), hair=(70, 50, 40), hat='beanie',
                   gift=('coins', 250), gift_line='Found this in an old hull. Coins! Yours now.'),
    'sol': dict(name='Sol', title='Lighthouse keeper', shirt=(70, 90, 80), hair=(232, 232, 236), hat='bowler',
                gift=('luck', 1.0), gift_line='An old keeper\'s blessing. Fair winds and full nets.'),
    'kit': dict(name='Kit', title='Beachcomber', shirt=(236, 180, 70), hair=(180, 110, 60), hat='bucket', kid=True,
                gift=('shell', 'cowrie'), gift_line="It's my lucky shell. You can have it. Really!"),
}
FOLK_ORDER = ('morwen', 'nell', 'ossian', 'sol', 'kit')

LINES = {
    'morwen': ["The tide waits for no one. Not even me, and I've asked nicely.",
               'Two high tides a day, a little later each day. Check the table on my board.',
               'High water brings the big fish in close. Low water shows you the rock pools.'],
    'nell': ['Fresh this morning! Well. Fresh-ish.',
             'If you bring me the catch of the day, I pay double. That is the rule.',
             'Ragworm for quick bites, squid for the fancy fish. Nothing fancier than squid.'],
    'ossian': ['Every boat on this harbour has passed through my hands. Some twice.',
               'A sail on that rowboat of yours and the river is a short hop.',
               'Mind the slipway. It is slipperier than it looks, and it looks slippery.'],
    'sol': ["Forty years I kept that lamp. Then the lens cracked and the oil ran dry.",
            'On a high tide at night, the old ones come in close to the rocks.',
            'My grandmother said the Grey Mariner follows the light home.'],
    'kit': ['I found a starfish this big! Well, this big. Maybe.',
            'The best shells wash up overnight. Come early!',
            'Sea glass is just old bottles that the sea polished. Isn\'t that amazing?'],
}

# beachcombing: shells for Kit's collection, and sea glass for the lighthouse lens
SHELLS = [
    dict(id='cockle', name='Cockle', col=(226, 200, 170), w=10),
    dict(id='scallop', name='Scallop', col=(240, 170, 130), w=8),
    dict(id='razor', name='Razor Shell', col=(200, 186, 160), w=8),
    dict(id='periwinkle', name='Periwinkle', col=(110, 90, 80), w=8),
    dict(id='starfish', name='Starfish', col=(240, 140, 80), w=5),
    dict(id='sanddollar', name='Sand Dollar', col=(236, 230, 214), w=4),
    dict(id='conch', name='Pink Conch', col=(250, 190, 190), w=2),
    dict(id='cowrie', name='Tiger Cowrie', col=(200, 140, 90), w=1),
]
SHELL_BY_ID = {s['id']: s for s in SHELLS}
GLASS = [dict(id='green', col=(120, 200, 150), w=6), dict(id='blue', col=(120, 170, 230), w=4),
         dict(id='amber', col=(240, 180, 80), w=1)]
SHELL_REWARD = 600
GLASS_NEED = 6
GLASS_SWAP = 2                  # spare shells Kit takes for one piece of sea glass
SHELL_SWAP = {'conch': 3, 'cowrie': 4}      # ...and for a shell you are missing (2 for the common ones)

# the lighthouse: three things Sol needs before the lamp can be lit
LIGHT_TASKS = [
    dict(id='glass', name='Sea glass for the lens', desc='Six pieces of sea glass from the beach, to mend the lens.'),
    dict(id='bass', name='Supper for the lamp room', desc='A Silver Sea Bass, for a long night at the lamp.'),
    dict(id='oil', name='Lamp oil and a new wick', desc='600 coins to Ossian for oil, a wick and polish.'),
]
OIL_COST = 600

# Ossian's boatyard
UPGRADES = [
    dict(id='sail', name='Little Sail', price=900,
         desc='A sail for the rowboat. The river trip takes 20 minutes instead of an hour.'),
    dict(id='boatlamp', name='Bow Lamp', price=650,
         desc='A lamp on the bow. Sea fish bite sooner at night.'),
]
UP_BY_ID = {u['id']: u for u in UPGRADES}

CHOWDER = 45
ROUND = 30                      # a round for the fishermen at the Gull & Lantern: they tell you a secret

# the boat Ossian is building: lend a hand once a day and watch it grow on the trestles
BOAT_STAGES = ('Just a keel on the trestles', 'Ribs going up', 'Planked and caulked', 'Painted and named',
               'Launched!')
BOAT_NAME = 'Kittiwake'
BOAT_PAY = 25
BOAT_PRIZE = 250

SEA_BAITS = [
    dict(id='ragworm', name='Ragworm', price=30, pack=10, merchant=True, sea=True,
         desc='Sea fish bite much sooner. Sold at Nell\'s stall in Saltmarsh.'),
    dict(id='squid', name='Squid Strips', price=150, pack=5, merchant=True, sea=True,
         desc='Rare sea fish come twice as often. Sold at Nell\'s stall in Saltmarsh.'),
]
for _b in SEA_BAITS:
    if _b['id'] not in BAIT_BY_ID:
        BAITS.append(_b)
        BAIT_BY_ID[_b['id']] = _b


# ---------------------------------------------------------------- state
def new():
    return dict(open=False, friends={}, chat={}, gifts=[], orders=[], orders_day=0, beach=[], beach_day=0,
                shells={}, glass=0, shell_done=False, light='dark', tasks=[], ups=[], catch=None, catch_day=0,
                mrest=0, visits=0, chowder=0, seen_rocks=False, told_light=False, boat=0, boat_day=0,
                round_day=0, tip='')


def clean(st):
    base = new()
    if not isinstance(st, dict):
        return base
    for k, v in base.items():
        if k != 'catch' and not isinstance(st.get(k), type(v)):
            st[k] = v
    st['friends'] = {k: max(0, min(50, int(v))) for k, v in st['friends'].items() if k in FOLK}
    st['chat'] = {k: int(v) for k, v in st['chat'].items() if k in FOLK}
    st['gifts'] = [k for k in st['gifts'] if k in FOLK]
    st['orders'] = [o for o in st['orders'] if isinstance(o, dict) and o.get('fish') in FISH_BY_ID]
    glass = {gl['id'] for gl in GLASS}
    st['beach'] = [b for b in st['beach'] if isinstance(b, dict) and isinstance(b.get('x'), (int, float)) and
                   (b.get('kind') == 'shell' and b.get('id') in SHELL_BY_ID or
                    b.get('kind') == 'glass' and b.get('id') in glass)]
    st['shells'] = {k: int(v) for k, v in st['shells'].items() if k in SHELL_BY_ID}
    st['tasks'] = [t for t in st['tasks'] if t in ('glass', 'bass', 'oil')]
    st['ups'] = [u for u in st['ups'] if u in UP_BY_ID]
    if st['light'] not in ('dark', 'lit'):
        st['light'] = 'dark'
    st['boat'] = max(0, min(len(BOAT_STAGES) - 1, st['boat']))
    if st.get('catch') not in FISH_BY_ID:
        st['catch'] = None
    return st


def is_open(g):
    return bool(g.coast.get('open'))


def at_coast(g):
    return getattr(g, 'spot', 'dock') in COAST_IDS and getattr(g, 'place', 'lake') == 'lake'


def has_up(g, uid):
    return uid in g.coast['ups']


def lit(g):
    return g.coast.get('light') == 'lit'


def river_minutes(g):
    return SAIL_MIN if has_up(g, 'sail') else RIVER_MIN


def region(spot):
    return 'coast' if spot in COAST_IDS else 'lake'


def reachable(g):
    """Spots the bot (or the map) can row to from here."""
    from data import SPOTS
    out = [s['id'] for s in SPOTS if s.get('region') != 'coast']
    if is_open(g):
        out += list(COAST_IDS)
    return out


# ---------------------------------------------------------------- tides
TIDE_PERIOD = 745.0             # minutes between high tides (a little over twelve hours)


def tide_level(g, minute=None, day=None):
    """0 (low water) .. 1 (high water). Two highs a day, each day about 50 minutes later."""
    m = g.minute if minute is None else minute
    d = g.day if day is None else day
    return 0.5 + 0.5 * math.cos((d * 1440 + m) / TIDE_PERIOD * 2 * math.pi)


def tide(g, minute=None):
    lv = tide_level(g, minute)
    return 'high' if lv > 0.62 else 'low' if lv < 0.38 else 'mid'


def rising(g):
    return tide_level(g, g.minute + 6) > tide_level(g)


def tide_text(g):
    t = tide(g)
    if t == 'high':
        return 'High tide'
    if t == 'low':
        return 'Low tide'
    return 'Tide coming in' if rising(g) else 'Tide going out'


def next_tides(g, n=4):
    """The next few high and low waters from now: [(kind, day, minute)]."""
    out = []
    prev = tide_level(g, g.minute)
    prev_d = tide_level(g, g.minute + 1) - prev
    for k in range(1, 1500):
        m = g.minute + k
        lv = tide_level(g, m)
        d = lv - prev
        if prev_d > 0 >= d:
            out.append(('High', g.day + m // 1440, m % 1440))
        elif prev_d < 0 <= d:
            out.append(('Low', g.day + m // 1440, m % 1440))
        prev, prev_d = lv, d
        if len(out) >= n:
            break
    return out


def fish_ok(g, f):
    """The tide filter for the bite picker."""
    return not f.get('tide') or tide(g) in f['tide']


# ---------------------------------------------------------------- the day
def morning(g):
    st = g.coast
    if not st['open'] and g.owns_boat():
        st['open'] = True
        g.queue.append(('letter', ('Dear angler,', (
            "The spring floods have cleared the old river channel, and a rowboat can get all the way down to the sea "
            "again. It is about an hour's row from your dock. Open your map (B) and look for Saltmarsh.\n"
            "We have a pier, a harbour, a lighthouse that has been dark for years, and fish you have never seen. "
            "Mind the tide: it decides everything here."), '- Harbourmaster Morwen of Saltmarsh')))
    if not st['open']:
        return
    rng = random.Random(g.day * 7919 + 11)
    sea = g.env.season if hasattr(g, 'env') else 0
    pool = [f for f in SEA_FISH if f['rarity'] <= 3 and (f['seasons'] is None or sea in f['seasons'])]
    if st['orders_day'] != g.day:
        st['orders_day'] = g.day
        picks = rng.sample(pool, min(3, len(pool)))
        st['orders'] = [dict(fish=f['id'], reward=int(f['price'] * 2.5) + 20, done=False) for f in picks]
    if st['catch_day'] != g.day:
        st['catch_day'] = g.day
        st['catch'] = rng.choice(pool)['id']
    if st['beach_day'] != g.day:
        st['beach_day'] = g.day
        st['beach'] = []
        for i in range(rng.randint(4, 6)):
            x = 1290 + i * 44 + rng.randint(-12, 12)
            if rng.random() < 0.3:
                k = _weighted(rng, GLASS)
                st['beach'].append(dict(x=x, kind='glass', id=k['id']))
            else:
                k = _weighted(rng, SHELLS)
                st['beach'].append(dict(x=x, kind='shell', id=k['id']))
        if needs_glass(g) and not any(b['kind'] == 'glass' for b in st['beach']):
            b = st['beach'][rng.randrange(len(st['beach']))]
            b['kind'], b['id'] = 'glass', _weighted(rng, GLASS)['id']
    if st['light'] == 'lit' and 'mariner_letter' not in g.town_day:
        g.town_day['mariner_letter'] = g.day
        g.queue.append(('letter', ('Dear friend,', (
            "Last night, from the lamp room, I saw it: a great grey back rolling off Kelp Rocks, right where the "
            "beam touched the water. The Grey Mariner has come home.\n"
            "Fish the rocks on a high tide at night, and hold on tight."), '- Sol, keeper of the Saltmarsh light')))


def needs_glass(g):
    st = g.coast
    return st['light'] != 'lit' and 'glass' not in st['tasks'] and st['glass'] < GLASS_NEED


def _weighted(rng, items):
    x = rng.uniform(0, sum(i['w'] for i in items))
    for i in items:
        x -= i['w']
        if x <= 0:
            return i
    return items[-1]


def price_mult(g, fid):
    """Nell's catch of the day sells for double."""
    st = getattr(g, 'coast', None)
    if st and st.get('catch') == fid and st.get('catch_day') == g.day:
        return 2.0
    return 1.0


# ---------------------------------------------------------------- fishing at the coast
def bite_mult(g):
    """How much sooner bites come at the coast."""
    k = 1.0
    if not at_coast(g):
        return k
    if g.bait == 'ragworm':
        k *= 0.6
    if has_up(g, 'boatlamp') and g.env.phase in ('night', 'dusk'):
        k *= 0.8
    return k


def weight_mult(g, f):
    """Extra pick weight for sea fish: squid, chowder, the light."""
    k = 1.0
    if f.get('method') != 'sea':
        return k
    r = f['rarity']
    if g.bait == 'squid' and r >= 3:
        k *= 2.0
    if r >= 3 and g.buff('chowder'):
        k *= 1.5
    if r >= 3 and lit(g) and g.env.phase in ('night', 'dusk'):
        k *= 1.3
    return k


def legend_can_bite(g, fid):
    """The Grey Mariner: only after the light is lit, and not again on a day it got away."""
    return fid == 'mariner' and lit(g) and g.coast.get('mrest') != g.day


MARINER_LINES = ('The Grey Mariner rolls and dives!', 'It runs for the open sea!', 'The last pull, against the tide!')


def on_escape(g, fid):
    if fid != 'mariner':
        return None
    g.coast['mrest'] = g.day
    g.save()
    return 'The Grey Mariner slips back into the dark water. It will be back tomorrow night.'


# ---------------------------------------------------------------- friendship
def hearts(g, k):
    return g.coast['friends'].get(k, 0) // 10


def add_friend(g, k, pts):
    st = g.coast
    old = st['friends'].get(k, 0)
    new = max(0, min(50, old + pts))
    st['friends'][k] = new
    if new >= 50 and k not in st['gifts']:
        st['gifts'].append(k)
        give_gift(g, k)


def give_gift(g, k):
    f = FOLK[k]
    kind = f['gift'][0]
    if kind == 'coins':
        g.coins += f['gift'][1]
    elif kind == 'bait':
        g.baits[f['gift'][1]] = g.baits.get(f['gift'][1], 0) + f['gift'][2]
    elif kind == 'luck':
        g.luck = min(3.0, g.luck + f['gift'][1])
    elif kind == 'shell':
        sid = f['gift'][1]
        g.coast['shells'][sid] = g.coast['shells'].get(sid, 0) + 1
        check_shells(g)
    g.audio.play('jingle4', 0.6)
    g.toast('%s: %s' % (f['name'], f['gift_line']), (90, 140, 180))


def chat(g, k):
    """Talk once a day for a little friendship. Returns what they say."""
    st = g.coast
    first = st['chat'].get(k) != g.day
    if first:
        st['chat'][k] = g.day
        add_friend(g, k, 5)
    lines = LINES[k]
    if k == 'sol' and not lit(g):
        line = lines[0] if first else lines[g.day % len(lines)]
    else:
        line = lines[(g.day + (0 if first else 1)) % len(lines)]
    if k == 'morwen':
        line = '%s Right now: %s.' % (line, tide_text(g).lower())
    return line


# ---------------------------------------------------------------- the harbour's jobs
def deliver_order(g, i):
    o = g.coast['orders'][i]
    if o['done']:
        return False
    items = [b for b in g.basket if b['id'] == o['fish']]
    if not items:
        return False
    g.basket.remove(min(items, key=lambda b: b['price']))
    o['done'] = True
    g.coins += o['reward']
    add_friend(g, 'morwen', 3)
    g.stats['coast_orders'] = g.stats.get('coast_orders', 0) + 1
    g.audio.play('coins', 0.7)
    g.toast('Morwen ticks off the order: %s. +%d coins' % (FISH_BY_ID[o['fish']]['name'], o['reward']),
            (90, 140, 180))
    g.save()
    return True


def buy_bait(g, bid):
    b = BAIT_BY_ID[bid]
    if g.coins < b['price']:
        g.toast('Not enough coins.', (200, 120, 100))
        return False
    g.coins -= b['price']
    g.baits[bid] = g.baits.get(bid, 0) + b['pack']
    g.audio.play('coins', 0.6)
    g.toast('Nell wraps up %d %s.' % (b['pack'], b['name']), (90, 140, 180))
    g.save()
    return True


def sea_basket(g):
    return [b for b in g.basket if FISH_BY_ID.get(b['id'], {}).get('method') == 'sea']


def sell_sea(g):
    items = sea_basket(g)
    if not items:
        return 0
    total = g.sell_fish(items)
    add_friend(g, 'nell', 2)
    g.audio.play('coins', 0.7)
    g.toast('Nell buys your sea fish for %d coins.' % total, (90, 140, 180))
    g.save()
    return total


def buy_chowder(g):
    if g.buff('chowder'):
        return False
    if g.coins < CHOWDER:
        g.toast('Not enough coins.', (200, 120, 100))
        return False
    g.coins -= CHOWDER
    g.buffs['chowder'] = g.day
    g.coast['chowder'] += 1
    g.audio.play('jingle2', 0.6)
    g.toast('A steaming bowl of harbour chowder. Rare sea fish will come more often today.', (200, 150, 80))
    g.save()
    return True


def buy_up(g, uid):
    u = UP_BY_ID[uid]
    if has_up(g, uid) or g.coins < u['price']:
        return False
    g.coins -= u['price']
    g.coast['ups'].append(uid)
    add_friend(g, 'ossian', 4)
    g.audio.play('jingle4', 0.6)
    g.toast('Ossian fits the %s. "She\'ll fly now."' % u['name'], (90, 140, 180))
    g.save()
    return True


def pick_up(g, item):
    """Beachcombing: pick up a shell or a piece of sea glass."""
    st = g.coast
    if item not in st['beach']:
        return
    st['beach'].remove(item)
    if item['kind'] == 'glass':
        st['glass'] += 1
        g.toast('A piece of %s sea glass, smooth as a sweet. (%d)' % (item['id'], st['glass']), (110, 170, 190))
    else:
        sid = item['id']
        st['shells'][sid] = st['shells'].get(sid, 0) + 1
        sh = SHELL_BY_ID[sid]
        new = st['shells'][sid] == 1
        g.toast('%s%s' % (sh['name'], '! A new one for the collection.' if new else '.'), (200, 160, 110))
        check_shells(g)
    g.stats['combed'] = g.stats.get('combed', 0) + 1
    g.audio.play('pop', 0.5)


def check_shells(g):
    st = g.coast
    if not st['shell_done'] and all(st['shells'].get(s['id'], 0) for s in SHELLS):
        st['shell_done'] = True
        g.coins += SHELL_REWARD
        add_friend(g, 'kit', 10)
        g.audio.play('jingle4', 0.7)
        g.toast('Every kind of shell! Kit is beside themself, and the harbour pays a %d-coin prize.' % SHELL_REWARD,
                (200, 160, 110))


def do_task(g, tid):
    st = g.coast
    if tid in st['tasks'] or st['light'] == 'lit':
        return False
    if tid == 'glass':
        if st['glass'] < GLASS_NEED:
            return False
        st['glass'] -= GLASS_NEED
    elif tid == 'bass':
        items = [b for b in g.basket if b['id'] == 'seabass']
        if not items:
            return False
        g.basket.remove(items[0])
    elif tid == 'oil':
        if g.coins < OIL_COST:
            return False
        g.coins -= OIL_COST
    st['tasks'].append(tid)
    add_friend(g, 'sol', 5)
    g.audio.play('jingle2', 0.6)
    g.toast({'glass': 'Sol fits the glass into the lens. Up top, it catches the sun already!',
             'bass': 'Sol takes the sea bass home. Smoke curls from the cottage chimney: supper is on.',
             'oil': 'Ossian rolls the oil barrels down the quay, and the top of the scaffold comes down.'}[tid],
            (90, 140, 180))
    g.save()
    return True


def can_light(g):
    return g.coast['light'] == 'dark' and len(g.coast['tasks']) == 3


def light_up(g):
    if not can_light(g):
        return False
    g.coast['light'] = 'lit'
    add_friend(g, 'sol', 10)
    g.audio.play('jingle4', 0.8)
    g.toast('The Saltmarsh light shines again, sweeping out across the sea!', (250, 220, 140))
    g.check_badges()
    g.save()
    return True


# ---------------------------------------------------------------- swapping with Kit
def spares(g):
    """Shells you have more than one of."""
    return sum(max(0, n - 1) for n in g.coast['shells'].values())


def swap_cost(sid):
    return SHELL_SWAP.get(sid, 2)


def _spend_spares(g, n):
    sh = g.coast['shells']
    took = {}
    for _ in range(n):
        # the one you have most of goes first; on a tie, one you haven't given yet, so the cost is spread out
        sid = max(sh, key=lambda k: (sh[k], -took.get(k, 0)))
        sh[sid] -= 1
        took[sid] = took.get(sid, 0) + 1


def swap_glass(g):
    if not needs_glass(g) or spares(g) < GLASS_SWAP:
        return False
    _spend_spares(g, GLASS_SWAP)
    g.coast['glass'] += 1
    add_friend(g, 'kit', 2)
    g.audio.play('jingle1', 0.5)
    g.toast('Kit trades you a piece of sea glass from the bucket. (%d/%d)' % (g.coast['glass'], GLASS_NEED),
            (110, 170, 190))
    g.save()
    return True


def swap_shell(g, sid):
    st = g.coast
    cost = swap_cost(sid)
    if st['shells'].get(sid) or spares(g) < cost:
        return False
    _spend_spares(g, cost)
    st['shells'][sid] = 1
    add_friend(g, 'kit', 2)
    g.audio.play('jingle2', 0.5)
    g.toast('Kit swaps you a %s for %d spares. "Deal! Look after it."' % (SHELL_BY_ID[sid]['name'], cost),
            (200, 160, 110))
    check_shells(g)
    g.save()
    return True


# ---------------------------------------------------------------- the boatyard and the inn
def can_help(g):
    st = g.coast
    return st['boat'] < len(BOAT_STAGES) - 1 and st['boat_day'] != g.day


def help_boat(g):
    st = g.coast
    if not can_help(g):
        return False
    st['boat'] += 1
    st['boat_day'] = g.day
    add_friend(g, 'ossian', 4)
    if st['boat'] == len(BOAT_STAGES) - 1:
        g.coins += BOAT_PRIZE
        g.audio.play('jingle4', 0.7)
        g.toast('Down the slipway she goes! The %s floats, and Ossian presses %d coins on you.'
                % (BOAT_NAME, BOAT_PRIZE), (90, 140, 180))
    else:
        g.coins += BOAT_PAY
        g.audio.play('jingle2', 0.55)
        g.toast({1: 'You hold the ribs while Ossian pegs them to the keel. +%d coins',
                 2: 'Plank after plank, hammered and caulked. The hull is closed! +%d coins',
                 3: 'Blue paint, a white stripe and her name on the bow. +%d coins'}[st['boat']] % BOAT_PAY,
                (90, 140, 180))
    g.stats['boat_help'] = g.stats.get('boat_help', 0) + 1
    g.save()
    return True


def buy_round(g, rng=random):
    """A round for the fishermen: they tell you about a fish (or a secret of the harbour)."""
    st = g.coast
    if st['round_day'] == g.day or g.coins < ROUND:
        return False
    g.coins -= ROUND
    st['round_day'] = g.day
    unknown = [f for f in SEA_FISH if f['id'] not in g.journal and (f['id'] != 'mariner' or lit(g))]
    if unknown:
        f = rng.choice(unknown)
        st['tip'] = '"Want to know a secret? There\'s a %s about. %s"' % (f['name'], f['hint'])
    elif not lit(g):
        st['tip'] = '"Help old Sol with that lamp. When it\'s lit, something big comes in to the rocks at night."'
    else:
        st['tip'] = '"Nothing left in the sea you haven\'t caught! Well. Have you tried the lake in winter?"'
    g.luck = min(3.0, g.luck + 0.5)
    g.audio.play('jingle1', 0.5)
    g.toast('The fishermen raise their mugs to you. A little luck, and a tip!', (200, 150, 80))
    g.save()
    return True


# ---------------------------------------------------------------- the HUD and the map
def day_lines(g):
    out = []
    if at_coast(g):
        out.append(('spot', '%s%s' % (tide_text(g), '  (big fish close in)' if tide(g) == 'high' else
                                      '  (rock pools out)' if tide(g) == 'low' else '')))
        if g.buff('chowder'):
            out.append(('snack', 'Harbour Chowder: rare sea fish'))
    return out


def sea_known(g):
    return sum(1 for f in SEA_FISH if f['id'] in g.journal)


_MAP = {}
COAST_PINS = {'pier': (96, 128), 'rocks': (214, 74), 'dock': (30, 18)}


def make_map(season):
    """The coast map, 300x220 art pixels: the river coming down from the lake, the harbour and the rocks."""
    if season in _MAP:
        return _MAP[season]
    w, h = 300, 220
    rng = random.Random(33)
    s = pygame.Surface((w, h))
    land = {0: (140, 178, 104), 1: (126, 166, 90), 2: (186, 164, 100), 3: (226, 232, 240)}[season]
    sea = (70, 132, 170) if season != 3 else (110, 150, 180)
    s.fill(land)
    for _ in range(700):
        s.set_at((rng.randrange(w), rng.randrange(h)), darken(land, rng.uniform(0.04, 0.12)))
    # the sea along the bottom and right, with a sandy edge
    pts = [(0, 160), (40, 150), (80, 146), (120, 150), (150, 140), (180, 118), (200, 96), (230, 84), (262, 60),
           (300, 50), (300, 220), (0, 220)]
    sand = (236, 220, 170)
    pygame.draw.polygon(s, sand, [(x, y - 5) for x, y in pts[:10]] + [(300, 220), (0, 220)])
    pygame.draw.polygon(s, sea, pts)
    for _ in range(70):
        x, y = rng.randrange(0, w), rng.randrange(60, h)
        if s.get_at((x, y))[:3] == sea:
            s.fill(lighten(sea, 0.2), (x, y, 3, 1))
    # the river from the lake (top left) down to the harbour
    river = [(0, 6), (18, 18), (34, 40), (52, 66), (70, 92), (86, 118), (94, 140)]
    pygame.draw.lines(s, lighten(sea, 0.15), False, river, 9)
    pygame.draw.lines(s, sea, False, river, 5)
    # the harbour: a quay and the pier
    s.fill((150, 130, 110), (70, 128, 60, 8))
    for i in range(6):
        s.fill(darken((150, 130, 110), 0.2), (72 + i * 10, 128, 6, 3))
    s.fill((130, 96, 64), (94, 136, 4, 22))
    for hx, col in ((74, (200, 110, 90)), (88, (110, 140, 190)), (104, (230, 200, 120)), (118, (200, 110, 90))):
        s.fill(col, (hx, 118, 9, 8))
        s.fill(darken(col, 0.3), (hx - 1, 115, 11, 3))
    # the headland, Kelp Rocks and the lighthouse
    for x, y, r in ((214, 82, 9), (226, 76, 7), (204, 90, 6), (236, 70, 6)):
        pygame.draw.circle(s, (120, 116, 110), (x, y), r)
        pygame.draw.circle(s, (146, 142, 134), (x - 2, y - 2), r - 3)
    s.fill((240, 236, 226), (244, 44, 6, 16))
    s.fill((200, 60, 60), (244, 48, 6, 3))
    s.fill((60, 60, 70), (243, 40, 8, 4))
    s.fill((250, 220, 120), (245, 41, 4, 2))
    _MAP[season] = s
    return s
