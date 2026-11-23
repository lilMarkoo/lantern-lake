"""Your market stall (0.5.0): every Leafday morning, 9 AM to 1 PM, a pitch at the top of the lake path in Fernwick.

Set it up first: fill up to four crates (six with the Second Table) from your basket, your pantry and your garden
basket, and chalk a price on each. Then open up, and the morning goes by while folk stop at the stall. Neighbours
look for their favourite fish and dish, visitors drift in from the farms (and, once you're known, from Saltmarsh),
and everyone has their own idea of a fair price: under it they buy (two, if it's a real bargain), a little over and
they haggle, too far over and they walk on. Selling cheap to a neighbour warms them to you. Now and then a neighbour
orders a fish for next Leafday, and pays double for it.

Nothing leaves your basket, pantry or garden basket until it is sold, so packing up (or quitting the game) mid-morning
never loses anything. Reputation grows with every sale and brings more people by; five stall upgrades from the
'Your stall' tab add to it. State that lasts is Game.stall (saved); the morning itself is Game.stallrun.
"""
import math
import random

import pygame

import ui as U

STALL_DAY = 3                       # Leafday
OPEN, CLOSE = 9 * 60, 13 * 60
SPEED = 1.0                         # the clock runs as usual while you sell
STREET_X = 100                      # where the stall stands on Fernwick's street (town.py), at the top of the lake path
CRATE_MAX = 6                       # things to a crate
STEPS = (0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0)
DEFAULT_STEP = 4                    # 1.2: a little over what Old Tom pays
UPGRADES = [
    dict(id='awning', name='Striped Awning', cost=200, desc='Rain no longer keeps people away.'),
    dict(id='bell', name='Brass Bell', cost=250, desc='More people stop by, and you can ring it.'),
    dict(id='scale', name='Weighing Scale', cost=300, desc='People pay more for fish they see weighed.'),
    dict(id='board', name='Chalkboard', cost=350, desc='Chalk up a special to draw a crowd.'),
    dict(id='table', name='Second Table', cost=600, desc='Room for six crates instead of four.'),
]
UP_BY_ID = {u['id']: u for u in UPGRADES}
REP = [0, 12, 35, 70, 120, 190]     # reputation for each level
REP_NAMES = ['A new stall', 'Known on the street', 'A Leafday favourite', 'The talk of Fernwick',
             'Famous downriver', 'A market legend']
REP_PERKS = ['', 'A few more people stop by.', 'People pay a little more.', 'Saltmarsh folk come up the river to buy.',
             'Even more people stop by.', 'People pay more again, and come from all around.']
BADGE_SOLD = 60                     # the Stallholder badge
# people who aren't neighbours: (name, shirt, hair, hat, kid)
VISITORS = [
    ('Ada, out walking', (150, 170, 110), (90, 60, 44), 'none', False),
    ('Bertie from the farm', (176, 120, 80), (60, 50, 44), 'bucket', False),
    ('Clem the carter', (110, 120, 150), (180, 170, 160), 'beanie', False),
    ('Dot, on her bicycle', (220, 150, 160), (220, 190, 120), 'flower', False),
    ('Ezra, a hiker', (90, 140, 120), (40, 34, 30), 'beanie', False),
    ('Flo and her basket', (200, 170, 110), (150, 80, 60), 'none', False),
    ('Gus, aged eight', (230, 120, 90), (110, 70, 40), 'none', True),
    ('Hattie from the mill', (160, 130, 190), (230, 226, 220), 'bowler', False),
]
SEA_VISITORS = [
    ('Nell from Saltmarsh', (90, 120, 160), (200, 120, 70), 'beanie', False),
    ('Bram from Saltmarsh', (120, 90, 80), (120, 120, 120), 'bucket', False),
    ('Kit from Saltmarsh', (240, 200, 110), (60, 40, 34), 'none', True),
    ('Ossian from Saltmarsh', (150, 110, 80), (170, 110, 70), 'beret', False),
]
BUY = ["Lovely. I'll take one.", 'Just what I was after!', 'Wrap it up for me, would you?',
       "Smells like the lake. In a good way.", "That'll do nicely for supper."]
FAV = ['{x}! My favourite. Yes please!', "Oh, {x}. You know me too well."]
TWO = ['At that price? I\'ll take two!', 'Two, please. My lucky day!']
DEAR = ['Ooh, a bit dear for me.', 'Not at that price, love.', 'Hmm. Maybe next week.']
LOOK = ['Just looking, thanks!', 'Lovely stall!', 'What a nice spread.']
DECLINE = ['Fair enough. Maybe next week!', 'No harm in asking!']


# ---------------------------------------------------------------- state
def new():
    return dict(told=False, rep=0, ups=[], days=0, sold=0, coins=0, best=0, orders=[], last=0, held=0)


def clean(d):
    base = new()
    if not isinstance(d, dict):
        return base
    for k, v in base.items():
        if k in d and type(d[k]) is type(v):
            base[k] = d[k]
    base['ups'] = [u for u in base['ups'] if u in UP_BY_ID]
    from data import FISH_BY_ID
    import town
    base['orders'] = [o for o in base['orders'] if isinstance(o, dict) and o.get('who') in town.FOLK
                      and o.get('fish') in FISH_BY_ID and isinstance(o.get('due'), int)][:2]
    return base


def has(g, uid):
    return uid in g.stall['ups']


def level(g):
    r = g.stall['rep']
    return max(i for i, v in enumerate(REP) if r >= v)


def is_day(g, day=None):
    import almanac
    return almanac.dow(g.day if day is None else day) == STALL_DAY


def run(g):
    """Today's market morning (or None)."""
    r = getattr(g, 'stallrun', None)
    return r if r is not None and r['day'] == g.day else None


def done_today(g):
    r = run(g)
    return r is not None and r['phase'] in ('summary', 'done')


def market_open(g):
    """Can you still have your market morning today?"""
    st = g.stall
    return (st['told'] and is_day(g) and g.minute < CLOSE - 10 and not done_today(g)
            and (st['held'] != g.day or run(g) is not None))     # (once a day, even if you quit mid-morning)


def running(g):
    r = run(g)
    return g.overlay == 'stall' and r is not None and r['phase'] == 'open'


def crate_cap(g):
    return 6 if has(g, 'table') else 4


# ---------------------------------------------------------------- goods
def a_(name):
    return ('an ' if name[:1].lower() in 'aeiou' else 'a ') + name


def _goods_name(kind, gid):
    from data import ALL_BY_ID
    import kitchen
    import garden
    if kind == 'fish':
        return ALL_BY_ID[gid]['name']
    if kind == 'dish':
        return kitchen.RECIPE_BY_ID[gid]['name']
    return garden.CROP_BY_ID[gid]['name']


def sellable_fish(b):
    from data import ALL_BY_ID
    spec = ALL_BY_ID.get(b.get('id'))
    return spec is not None and not spec.get('junk') and not b.get('v')


def fair(g, c, b=None):
    """What one thing from this crate is worth: what Old Tom pays on a quiet day."""
    import kitchen
    import garden
    if c['kind'] == 'fish':
        items = [x for x in c['items'] if _in_basket(g, x)]
        if b is None:
            if not items:
                return 0
            return int(round(sum(g.sale_price(x, 0) for x in items) / len(items)))
        return g.sale_price(b, 0)
    if c['kind'] == 'dish':
        return kitchen.RECIPE_BY_ID[c['id']]['price']
    return garden.CROP_BY_ID[c['id']]['sell']


def _in_basket(g, b):
    return any(x is b for x in g.basket)


def stock(g, c):
    if c is None:
        return 0
    if c['kind'] == 'fish':
        return sum(1 for x in c['items'] if _in_basket(g, x))
    have = g.pantry.get(c['id'], 0) if c['kind'] == 'dish' else g.garden['produce'].get(c['id'], 0)
    return min(c['n'], have)


def available(g, kind, gid):
    """How many more of this could go in a crate."""
    r = run(g)
    crates = [c for c in (r['crates'] if r else []) if c and c['kind'] == kind and c['id'] == gid]
    if kind == 'fish':
        used = {id(x) for c in crates for x in c['items']}
        return sum(1 for b in g.basket if b.get('id') == gid and sellable_fish(b) and id(b) not in used)
    have = g.pantry.get(gid, 0) if kind == 'dish' else g.garden['produce'].get(gid, 0)
    return max(0, have - sum(c['n'] for c in crates))


def goods(g, kind):
    """Everything of this kind you could put out: [(id, how many)]."""
    import kitchen
    import garden
    from data import ALL_BY_ID
    if kind == 'fish':
        ids = []
        for b in sorted(g.basket, key=lambda b: -b['price']):
            if sellable_fish(b) and b['id'] not in ids:
                ids.append(b['id'])
        out = [(i, available(g, 'fish', i)) for i in ids]
        return sorted(out, key=lambda e: (-ALL_BY_ID[e[0]].get('rarity', 0), ALL_BY_ID[e[0]]['name']))
    if kind == 'dish':
        return [(r['id'], available(g, 'dish', r['id'])) for r in kitchen.RECIPES if g.pantry.get(r['id'], 0) > 0]
    order = list(garden.CROP_BY_ID)
    return sorted([(cid, available(g, 'crop', cid)) for cid, n in g.garden['produce'].items() if n > 0],
                  key=lambda e: order.index(e[0]))


def add(g, kind, gid):
    """Put one more of something out: on its own crate if it has one, else on the next empty crate."""
    r = run(g)
    if r is None or r['phase'] != 'setup' or available(g, kind, gid) <= 0:
        return False
    crates = r['crates']
    c = next((c for c in crates if c and c['kind'] == kind and c['id'] == gid and _count(c) < CRATE_MAX), None)
    if c is None:
        if None not in crates:
            g.toast('Your crates are all full. Clear one first, or buy the Second Table.', (170, 120, 90))
            return False
        i = crates.index(None)
        c = crates[i] = dict(kind=kind, id=gid, items=[], n=0, step=DEFAULT_STEP, special=False)
    if kind == 'fish':
        used = {id(x) for cc in crates if cc and cc['kind'] == 'fish' for x in cc['items']}
        pick = max((b for b in g.basket if b.get('id') == gid and sellable_fish(b) and id(b) not in used),
                   key=lambda b: b['price'])
        c['items'].append(pick)
    else:
        c['n'] += 1
    g.audio.play('click', 0.4)
    return True


def _count(c):
    return len(c['items']) if c['kind'] == 'fish' else c['n']


def take_back(g, i):
    """One thing off crate i (the crate empties when it's the last one)."""
    r = run(g)
    c = r['crates'][i] if r else None
    if c is None or r['phase'] != 'setup':
        return
    if c['kind'] == 'fish':
        if c['items']:
            c['items'].pop()
    else:
        c['n'] -= 1
    if _count(c) <= 0:
        r['crates'][i] = None
    g.audio.play('click', 0.3)


def clear(g, i):
    r = run(g)
    if r and r['phase'] == 'setup':
        r['crates'][i] = None
        g.audio.play('page', 0.3)


def set_step(g, i, d):
    r = run(g)
    c = r['crates'][i] if r else None
    if c is not None:
        c['step'] = max(0, min(len(STEPS) - 1, c['step'] + d))
        g.audio.play('click', 0.3)


def set_special(g, i):
    r = run(g)
    if r is None or not has(g, 'board'):
        return
    for j, c in enumerate(r['crates']):
        if c:
            c['special'] = j == i and not c['special']
    g.audio.play('click', 0.3)


def fill_all(g):
    """Set out a bit of everything: the best fish first, then dishes, then the garden basket."""
    r = run(g)
    if r is None or r['phase'] != 'setup':
        return
    for kind in ('fish', 'dish', 'crop'):
        for gid, n in goods(g, kind):
            for _ in range(min(n, CRATE_MAX)):
                if None not in r['crates'] and not any(c and c['kind'] == kind and c['id'] == gid
                                                       and _count(c) < CRATE_MAX for c in r['crates']):
                    return
                if not add(g, kind, gid):
                    break


def price_tag(g, c):
    return int(round(fair(g, c) * STEPS[c['step']]))


def price_word(step):
    m = STEPS[step]
    return 'Bargain' if m < 0.95 else 'Fair' if m < 1.15 else 'Pricey' if m < 1.4 else 'Steep'


# ---------------------------------------------------------------- the morning
def open_(g):
    """Walk up to the stall: set up on a market morning, or look after it any other day."""
    st = g.stall
    if not st['told']:
        g.toast('A canvas stall, folded under a tarp. Someone has chalked RESERVED on it.', (150, 140, 130))
        return
    r = run(g)
    if r is None and market_open(g):
        g.stallrun = r = dict(day=g.day, phase='setup', crates=[None] * crate_cap(g), cust=[], next_m=0.0,
                              takings=0, sold=0, rep0=st['rep'], per={}, dear=0, came=[], bell_m=-999.0,
                              t=0.0, said=None, ordered=False, orders_done=0, lvl0=level(g))
    g.stall_tab = 'setup' if r is not None and r['phase'] in ('setup', 'open', 'summary') else 'stall'
    g.overlay = 'stall'
    g.release_holds()
    g.audio.play('page', 0.5)


def open_up(g):
    """Take the covers off and start selling."""
    r = run(g)
    if r is None or r['phase'] != 'setup' or not any(r['crates']):
        return
    if g.minute < OPEN:
        g.advance_time(OPEN - g.minute)          # wait for nine o'clock
    if g.minute >= CLOSE:
        return
    r['phase'] = 'open'
    r['next_m'] = g.minute + 3
    st = g.stall
    st['days'] += 1
    st['held'] = g.day
    g.audio.play('townbell' if has(g, 'bell') else 'page', 0.5)
    g.toast('Your stall is open until 1 PM!', (120, 150, 100))


def ring_bell(g):
    r = run(g)
    if r is None or r['phase'] != 'open' or not has(g, 'bell') or g.minute - r['bell_m'] < 60:
        return
    r['bell_m'] = g.minute
    r['next_m'] = min(r['next_m'], g.minute + 1)
    r['crowd'] = 2                               # the next two come along quickly
    r['ring_t'] = r['t']
    g.audio.play('townbell', 0.6)


def pack_up(g):
    r = run(g)
    if r is None or r['phase'] != 'open':
        return
    r['phase'] = 'summary'
    r['cust'] = []
    st = g.stall
    st['best'] = max(st['best'], r['takings'])
    st['last'] = r['takings']
    g.stats['stall_days'] = st['days']
    g.audio.play('jingle2', 0.6)
    g.check_badges()
    g.save()


def close(g):
    """The X (or Esc): pack up first if you're open, then put the window away."""
    r = run(g)
    if r is not None and r['phase'] == 'open':
        return pack_up(g)
    if r is not None and r['phase'] == 'summary':
        r['phase'] = 'done'
    g.overlay = None
    g.audio.play('page', 0.5)


def _rng(g, r):
    return random.Random(int(g.day * 7919 + r['sold'] * 131 + len(r['came']) * 17 + r['t'] * 10))


def _spawn(g, r):
    """Someone wanders up to the stall."""
    import town
    rng = _rng(g, r)
    lvl = level(g)
    slots = [c['slot'] for c in r['cust'] if c['state'] != 'out']
    free = [s for s in ('L', 'R') if s not in slots]
    if not free:
        return False
    slot = free[0] if len(free) == 1 else rng.choice(free)
    st = g.stall
    due = [o for o in st['orders'] if o['due'] == g.day and g.minute >= o['at'] and o['who'] not in r['came']]
    who = name = None
    look = None
    order = None
    if due:
        order = due[0]
        who = order['who']
    else:
        near = [k for k in town.FOLK_ORDER if k not in r['came'] and g.town.folk_here(k, g.minute)]
        if near and rng.random() < 0.55:
            who = rng.choice(near)
    if who:
        f = town.FOLK[who]
        name = f['name']
        look = (f['shirt'], f['hair'], f['hat'], bool(f.get('kid')), bool(f.get('glasses')))
        r['came'].append(who)
    else:
        pool = VISITORS + (SEA_VISITORS if lvl >= 3 else [])
        name, shirt, hair, hat, kid = rng.choice(pool)
        look = (shirt, hair, hat, kid, False)
    side = -1 if slot == 'L' else 1
    r['cust'].append(dict(who=who, name=name, look=look, slot=slot, x=-14.0 if side < 0 else SCN_W + 14.0,
                          state='in', t=0.0, crate=None, offer=0, line='', order=order, seen=0.0,
                          visitor=who is None, sea=name in [v[0] for v in SEA_VISITORS]))
    if has(g, 'bell'):
        r['ring_t'] = r['t'] if r.get('crowd') else r.get('ring_t', -9)
    return True


def _interval(g):
    lvl = level(g)
    base = 15.0 * (1 - 0.06 * lvl) * (0.78 if has(g, 'bell') else 1.0)
    if g.env.rain > 0.3 and not has(g, 'awning'):
        base *= 1.7
    return base


def _fav(c, cust):
    import town
    import kitchen
    k = cust['who']
    if not k or c is None:
        return False
    if c['kind'] == 'fish':
        return town.FOLK[k].get('loves') == c['id']
    if c['kind'] == 'dish':
        return kitchen.FAVOURITE_DISH.get(k) == c['id']
    return False


def _decide(g, r, cust):
    """At the stall: what do they want, and what will they pay?"""
    rng = _rng(g, r)
    lvl = level(g)
    crates = [(i, c) for i, c in enumerate(r['crates']) if c and stock(g, c) > 0]
    if cust['order']:
        o = cust['order']
        g.stall['orders'] = [x for x in g.stall['orders'] if x is not o]
        hit = next(((i, c) for i, c in crates if c['kind'] == 'fish' and c['id'] == o['fish']), None)
        from data import ALL_BY_ID
        if hit:
            i, c = hit
            pay = 2 * fair(g, c, _first(g, c))
            _sell(g, r, cust, i, 1, pay=pay)
            r['orders_done'] += 1
            g.stall['rep'] += 3
            g.add_friend(cust['who'], 5)
            cust['line'] = 'You remembered my %s! Double, as promised.' % ALL_BY_ID[o['fish']]['name']
        else:
            cust['line'] = 'No %s this week? Never mind, dear.' % ALL_BY_ID[o['fish']]['name']
        cust['state'], cust['t'] = 'talk', 0.0
        return
    if not crates:
        cust['line'] = 'All sold out? I\'ll come earlier next week!'
        cust['state'], cust['t'] = 'talk', 0.0
        return
    weights = []
    for i, c in crates:
        w = 1.0
        if _fav(c, cust):
            w *= 7
        if c.get('special'):
            w *= 2.2
        if c['kind'] == 'fish':
            from data import ALL_BY_ID
            w *= 1 + 0.15 * ALL_BY_ID[c['id']].get('rarity', 0)
        weights.append(w)
    i, c = rng.choices(crates, weights=weights)[0]
    fav = _fav(c, cust)
    if not fav and not c.get('special') and rng.random() < 0.18:
        cust['line'] = rng.choice(LOOK)
        cust['state'], cust['t'] = 'talk', 0.0
        _maybe_order(g, r, cust, rng)
        return
    hearts = g.friends.get(cust['who'], 0) / 10.0 if cust['who'] else 0.0
    wtp = (0.95 + rng.uniform(0, 0.4) + 0.04 * lvl + (0.05 if lvl >= 2 else 0) + (0.05 if lvl >= 5 else 0)
           + (0.4 if fav else 0) + (0.1 if c['kind'] == 'fish' and has(g, 'scale') else 0)
           + (0.12 if cust['visitor'] else 0) + (0.1 if cust['sea'] else 0) + 0.015 * hearts)
    m = STEPS[c['step']]
    cust['crate'] = i
    if m <= wtp:
        n = 2 if m < 0.95 and stock(g, c) >= 2 and rng.random() < 0.5 else 1
        _sell(g, r, cust, i, n)
        name = _goods_name(c['kind'], c['id'])
        cust['line'] = (rng.choice(TWO) if n == 2 else rng.choice(FAV).format(x=name) if fav else rng.choice(BUY))
        cust['state'], cust['t'] = 'talk', 0.0
        _maybe_order(g, r, cust, rng)
    elif m <= wtp + 0.35:
        cust['offer'] = max(1, int(fair(g, c) * wtp))
        cust['line'] = 'Hmm. Would you take %d for it?' % cust['offer'] if rng.random() < 0.5 else \
            'Tell you what: %d, and it\'s a deal?' % cust['offer']
        cust['state'], cust['t'] = 'haggle', 0.0
        g.audio.play('chat1', 0.4)
    else:
        r['dear'] += 1
        cust['line'] = rng.choice(DEAR)
        cust['state'], cust['t'] = 'talk', 0.0


def _first(g, c):
    if c['kind'] != 'fish':
        return None
    return next((x for x in c['items'] if _in_basket(g, x)), None)


def _sell(g, r, cust, i, n, pay=None):
    """Hand it over and take the coins. pay: the whole price, if it isn't the price on the tag."""
    c = r['crates'][i]
    total = 0
    for _ in range(n):
        if stock(g, c) <= 0:
            break
        if c['kind'] == 'fish':
            b = _first(g, c)
            each = pay if pay is not None else int(round(fair(g, c, b) * STEPS[c['step']]))
            g.basket = [x for x in g.basket if x is not b]
            c['items'] = [x for x in c['items'] if x is not b]
        else:
            each = pay if pay is not None else int(round(fair(g, c) * STEPS[c['step']]))
            if c['kind'] == 'dish':
                g.pantry[c['id']] -= 1
                if g.pantry[c['id']] <= 0:
                    del g.pantry[c['id']]
            else:
                pr = g.garden['produce']
                pr[c['id']] -= 1
                if pr[c['id']] <= 0:
                    del pr[c['id']]
            c['n'] -= 1
        total += each
        r['sold'] += 1
        key = (c['kind'], c['id'])
        r['per'][key] = r['per'].get(key, 0) + 1
    if not total:
        return 0
    g.coins += total
    r['takings'] += total
    st = g.stall
    lv = level(g)
    fav = _fav(c, cust)
    st['rep'] += n + (1 if fav else 0)
    st['sold'] += n
    st['coins'] += total
    g.stats['stall_sold'] = st['sold']
    if cust['who']:
        pts = 2 + (3 if STEPS[c['step']] < 1.0 and pay is None else 0) + (2 if fav else 0)
        g.add_friend(cust['who'], pts)
    r['coin_t'] = r['t']
    r['coin_slot'] = cust['slot']
    g.audio.play('coin', 0.6)
    if level(g) > lv:
        g.audio.play('jingle3', 0.6)
        g.toast('Your stall is now %s! %s' % (REP_NAMES[level(g)].lower(), REP_PERKS[level(g)]), (200, 150, 80))
    return total


def _maybe_order(g, r, cust, rng):
    """A neighbour asks you to bring something next week."""
    from data import FISH_BY_ID, FISH
    import town
    k = cust['who']
    st = g.stall
    if (not k or r['ordered'] or len(st['orders']) >= 2 or any(o['who'] == k for o in st['orders'])
            or rng.random() > 0.35):
        return
    want = town.FOLK[k].get('loves')
    if want not in FISH_BY_ID or want not in g.journal or FISH_BY_ID[want]['rarity'] >= 4 or rng.random() < 0.3:
        pool = [f for f in FISH if 1 <= f['rarity'] <= 2 and not f.get('method') and not f.get('event')
                and f['id'] in g.journal]
        if not pool:
            return
        want = rng.choice(pool)['id']
    r['ordered'] = True
    st['orders'].append(dict(who=k, fish=want, due=g.day + 7, at=rng.randrange(600, 720, 10)))
    cust['line'] += '  Oh, and could you save me %s next Leafday? I\'ll pay double.' % a_(FISH_BY_ID[want]['name'])
    cust['t'] = -1.5                                 # a longer chat


def accept(g):
    r = run(g)
    cust = next((c for c in (r['cust'] if r else []) if c['state'] == 'haggle'), None)
    if cust is None:
        return
    c = r['crates'][cust['crate']]
    if c and stock(g, c) > 0:
        _sell(g, r, cust, cust['crate'], 1, pay=cust['offer'])
        cust['line'] = 'Deal! Pleasure doing business.'
        _maybe_order(g, r, cust, _rng(g, r))
    else:
        cust['line'] = 'Oh, it\'s gone? Never mind.'
    cust['state'], cust['t'] = 'talk', 0.0


def decline(g):
    r = run(g)
    cust = next((c for c in (r['cust'] if r else []) if c['state'] == 'haggle'), None)
    if cust is None:
        return
    cust['line'] = random.choice(DECLINE)
    cust['state'], cust['t'] = 'talk', 0.0


def update(g, dt):
    r = run(g)
    if r is None:
        return
    r['t'] += dt
    if r['phase'] != 'open':
        return
    if g.minute >= CLOSE:
        g.toast("One o'clock: the market's over for today.", (150, 130, 100))
        return pack_up(g)
    if not any(stock(g, c) for c in r['crates'] if c) and not any(c['state'] != 'out' for c in r['cust']):
        g.toast('Sold out! Time to pack up.', (120, 150, 100))
        return pack_up(g)
    if g.minute >= r['next_m'] and _spawn(g, r):
        rng = _rng(g, r)
        if r.get('crowd'):
            r['crowd'] -= 1
            r['next_m'] = g.minute + rng.uniform(1.5, 3)
        else:
            r['next_m'] = g.minute + _interval(g) * rng.uniform(0.6, 1.4)
    for cust in r['cust']:
        cust['t'] += dt
        home = SLOT_X[cust['slot']]
        if cust['state'] == 'in':
            d = home - cust['x']
            if abs(d) < 1.0:
                cust['x'] = home
                cust['state'], cust['t'] = 'look', 0.0
            else:
                cust['x'] += math.copysign(min(abs(d), 34 * dt), d)
        elif cust['state'] == 'look' and cust['t'] > 1.2:
            _decide(g, r, cust)
        elif cust['state'] == 'haggle' and cust['t'] > 8.0:
            cust['line'] = 'Never mind, then!'
            cust['state'], cust['t'] = 'talk', 0.0
        elif cust['state'] == 'talk' and cust['t'] > 2.6:
            cust['state'], cust['t'] = 'out', 0.0
        elif cust['state'] == 'out':
            away = -20.0 if cust['slot'] == 'L' else SCN_W + 20.0
            cust['x'] += math.copysign(34 * dt, away - cust['x'])
    r['cust'] = [c for c in r['cust'] if not (c['state'] == 'out' and (c['x'] < -16 or c['x'] > SCN_W + 16))]


def tick(g, before):
    """As the clock moves: Hazel's letter about the market, and orders that went past their day."""
    st = g.stall
    if not st['told'] and g.day >= 2 and g.minute >= 7 * 60 and g.mode == 'play':
        st['told'] = True
        g.post([('Leafday market', "Fernwick has a market every Leafday morning, from 9 until 1, and I've kept a "
                 "pitch for you at the top of the lake path, right by Old Tom's. Bring whatever you've caught, cooked "
                 "or grown, chalk up your prices and see who comes by.\n\nA tip from an old market hand: folk pay "
                 "more for their favourites, and they never forget a bargain.", '- Mayor Hazel')])
    if st['orders']:
        st['orders'] = [o for o in st['orders'] if o['due'] > g.day or o['due'] == g.day and g.minute < CLOSE]


def day_note(g):
    """A note for the HUD: market morning, or an order to bring."""
    st = g.stall
    if not st['told']:
        return None
    if market_open(g):
        r = run(g)
        if r is not None and r['phase'] == 'open':
            return 'Your stall is open until 1 PM'
        return 'Market day: your stall in Fernwick, 9 AM to 1 PM'
    o = next((o for o in st['orders']), None)
    if o:
        import town
        from data import FISH_BY_ID
        return '%s wants %s for Leafday' % (town.FOLK[o['who']]['name'], a_(FISH_BY_ID[o['fish']]['name']))
    return None


def badge_cond(g):
    return {'stallholder': g.stall['sold'] >= BADGE_SOLD}


# ---------------------------------------------------------------- the bot
def auto(g, dt, rng):
    """For the soak test: set out everything, open, take any fair offer, pack up at the end."""
    r = run(g)
    if r is None:
        g.overlay = None
        return
    if r['phase'] == 'setup':
        for u in UPGRADES:
            if not has(g, u['id']) and g.coins > u['cost'] + 400:
                buy(g, u)
        fill_all(g)
        if has(g, 'board') and r['crates'][0]:
            r['crates'][0]['special'] = True
        for c in r['crates']:
            if c:
                c['step'] = rng.choice((3, 4, 4, 5, 6))
        if any(r['crates']):
            open_up(g)
        else:
            r['phase'] = 'done'
            g.overlay = None
    elif r['phase'] == 'open':
        cust = next((c for c in r['cust'] if c['state'] == 'haggle'), None)
        if cust and cust['t'] > 1.0:
            cr = r['crates'][cust['crate']]
            (accept if cr and cust['offer'] >= 0.95 * fair(g, cr) else decline)(g)
        if has(g, 'bell') and g.minute - r['bell_m'] >= 60:
            ring_bell(g)
    else:
        close(g)


def buy(g, u):
    st = g.stall
    if u['id'] in st['ups'] or g.coins < u['cost']:
        return
    g.coins -= u['cost']
    st['ups'].append(u['id'])
    r = run(g)
    if u['id'] == 'table' and r is not None and r['phase'] == 'setup':
        r['crates'] += [None] * (crate_cap(g) - len(r['crates']))
    g.audio.play('jingle2', 0.6)
    g.toast('%s for your stall!' % u['name'], (200, 150, 80))
    g.save()


# ---------------------------------------------------------------- drawing: the stall in close-up
SCN_W, SCN_H = 236, 66
SCN_K = 4
SLOT_X = {'L': 62.0, 'R': 174.0}
COUNTER = pygame.Rect(78, 40, 80, 20)
_icons = {}


def goods_icon(kind, gid, box):
    """An icon for a crate or a tile, as big as fits in box (w, h) in whole steps."""
    key = (kind, gid, box)
    if key in _icons:
        return _icons[key]
    import art
    import kitchen
    import garden
    from data import ALL_BY_ID
    if kind == 'fish':
        src = art.fish_sprite(ALL_BY_ID[gid], 1)
    elif kind == 'dish':
        src = kitchen.dish_icon(gid, 1)
    else:
        src = garden.crop_icon(gid, 1)
    w, h = src.get_size()
    k = max(1, min(box[0] // max(1, w), box[1] // max(1, h)))
    if w * k > box[0] or h * k > box[1]:
        s = min(box[0] / w, box[1] / h)
        out = pygame.transform.smoothscale(src, (max(1, int(w * s)), max(1, int(h * s))))
    else:
        out = pygame.transform.scale(src, (w * k, h * k))
    _icons[key] = out
    return out


def _awning(s, x0, x1, y, striped, t, wind):
    if striped:
        for i, x in enumerate(range(x0, x1, 6)):
            col = (200, 84, 90) if i % 2 == 0 else (250, 242, 228)
            s.fill(col, (x, y, 6, 8))
            sway = int(math.sin(t * 2.2 + i * 0.7) * wind * 1.5)
            pygame.draw.polygon(s, col, [(x, y + 8), (x + 6, y + 8), (x + 3 + sway, y + 11)])
        s.fill((150, 64, 70), (x0, y, x1 - x0, 1))
    else:
        pts = [(x0, y + 2)]
        for x in range(x0, x1 + 1, 4):
            pts.append((x, y + 1 + int(1.5 * math.sin((x - x0) / (x1 - x0) * math.pi))))
        pts += [(x1, y + 9), (x0, y + 9)]
        pygame.draw.polygon(s, (214, 196, 160), pts)
        s.fill((180, 160, 124), (x0, y + 8, x1 - x0, 1))
        for x in range(x0 + 3, x1, 8):
            s.fill((196, 176, 140), (x, y + 3, 1, 5))


def draw_scene(g, t):
    """The stall from across the street: you behind the counter, your crates on it, and whoever's buying."""
    import town
    import look as looks
    import actors
    import biscuit
    from art import lerp_c, darken, lighten
    r = run(g)
    st = g.stall
    env = g.env
    season = env.season
    s = pygame.Surface((SCN_W, SCN_H))
    sky = lerp_c((170, 206, 226), (120, 130, 150), min(1.0, env.rain))
    s.fill(sky)
    # far side of the street: Old Tom's blue planks on the right, the hedge and the lake path on the left
    hedge = [(96, 150, 86), (82, 136, 70), (170, 120, 64), (214, 222, 232)][season]
    for x in range(0, 120, 3):
        h = 16 + int(5 * math.sin(x * 0.31)) + int(3 * math.sin(x * 0.11))
        s.fill(darken(hedge, 0.12 if x % 2 else 0.0), (x, 40 - h, 3, h))
    s.fill((120, 88, 60), (20, 18, 2, 24))
    pygame.draw.polygon(s, (170, 128, 84), [(10, 18), (36, 18), (40, 21), (36, 24), (10, 24)])
    planks = (92, 128, 140)
    s.fill(planks, (128, 2, SCN_W - 128, 40))
    for y in range(4, 42, 4):
        s.fill((78, 110, 122), (128, y, SCN_W - 128, 1))
    s.fill((230, 224, 210), (196, 10, 20, 16))
    s.fill((140, 180, 200), (198, 12, 16, 12))
    s.fill((230, 224, 210), (205, 12, 2, 12))
    if season == 3:
        s.fill((246, 248, 255), (128, 0, SCN_W - 128, 3))
    # the pavement and the road
    pave = town.PAVE[season]
    s.fill(pave, (0, 40, SCN_W, 8))
    s.fill(lighten(pave, 0.08), (0, 40, SCN_W, 1))
    road = (128, 120, 116) if season != 3 else (176, 180, 192)
    s.fill(darken(pave, 0.25), (0, 48, SCN_W, 1))
    s.fill(road, (0, 49, SCN_W, SCN_H - 49))
    rng = random.Random(9)
    for y in range(51, SCN_H, 5):
        off = rng.randrange(0, 9)
        for x in range(-off, SCN_W, 11):
            c = lerp_c(road, (150, 144, 138) if season != 3 else (220, 224, 236), rng.uniform(0.1, 0.5))
            pygame.draw.rect(s, c, (x + 1, y, 9, 3), border_radius=1)
    # the stall: two posts, the awning, a bit of bunting
    wood, dark = (150, 104, 70), (104, 72, 50)
    for px in (80, 154):
        s.fill(wood, (px, 10, 3, 32))
        s.fill(dark, (px + 2, 10, 1, 32))
    _awning(s, 72, 166, 4, has(g, 'awning'), t, getattr(env, 'wind', 0.3))
    if season == 3:
        s.fill((246, 248, 255), (72, 3, 94, 2))
    if has(g, 'bell'):
        ring = r.get('ring_t', -9) if r else -9
        sw = math.sin((t - ring) * 18) * max(0.0, 1 - (t - ring) / 1.2) * 3 if r else 0
        s.fill(dark, (78, 14, 6, 1))
        bx = 76 + int(sw)
        pygame.draw.polygon(s, (214, 170, 70), [(bx, 21), (bx + 2, 16), (bx + 4, 21)])
        s.fill((240, 210, 120), (bx + 1, 17, 1, 3))
    if has(g, 'scale'):
        s.fill(dark, (156, 15, 6, 1))
        s.fill((170, 170, 176), (158, 16, 1, 8))
        pygame.draw.arc(s, (190, 190, 196), (153, 22, 11, 6), math.pi, 2 * math.pi, 1)
    # you, behind the counter, turned toward whoever is talking to you
    talk = None
    if r:
        talk = next((c for c in r['cust'] if c['state'] in ('look', 'haggle', 'talk')), None)
    face = (-1 if talk['slot'] == 'L' else 1) if talk else 1
    rain = env.rain > 0.3
    town.walker(s, 118, 43, face, 0, *looks.player_colors(g, season), g.hat, season, look=looks.of(g))
    # the counter, the crates on it
    s.fill((166, 116, 76), COUNTER)
    s.fill((196, 146, 98), (COUNTER.x - 2, COUNTER.y - 2, COUNTER.w + 4, 3))
    for x in range(COUNTER.x + 4, COUNTER.right - 4, 19):
        pygame.draw.rect(s, (140, 96, 62), (x, COUNTER.y + 4, 16, 12), 1)
    crates = r['crates'] if r else [None] * crate_cap(g)
    n = len(crates)
    cw = (COUNTER.w - 4) // n
    for i, c in enumerate(crates):
        x = COUNTER.x + 2 + i * cw
        s.fill((176, 132, 84), (x + 1, COUNTER.y - 8, cw - 2, 7))
        s.fill((140, 100, 64), (x + 1, COUNTER.y - 8, cw - 2, 1))
        s.fill((140, 100, 64), (x + 1, COUNTER.y - 4, cw - 2, 1))
        k = stock(g, c) if c else 0
        if k:
            ic = goods_icon(c['kind'], c['id'], (cw - 2, 9))
            for j in range(min(k, 3)):
                s.blit(ic, ic.get_rect(midbottom=(x + cw // 2 + (j - 1) * 2 * (k > 1), COUNTER.y - 6 - (j % 2))))
            if c.get('special'):
                s.fill((250, 230, 120), (x + cw // 2 - 1, COUNTER.y - 16, 3, 3))
    if has(g, 'board'):
        s.fill(dark, (30, 54, 1, 9))
        s.fill(dark, (40, 54, 1, 9))
        s.fill((60, 56, 60), (28, 40, 15, 14))
        s.fill(dark, (27, 39, 17, 1))
        for i in range(3):
            s.fill((236, 230, 220), (30, 43 + i * 3, 6 + (i * 5) % 9, 1))
    # Biscuit keeps you company
    if biscuit.follows(g) or g.cat_follow:
        actors.draw_cat(s, g, t, 198, 60, bed=False, sleep=False, face=-1, trick=False, look=0)
    # customers
    if r:
        for c in r['cust']:
            shirt, hair, hat, kid, glasses = c['look']
            fc = 1 if c['state'] == 'in' and c['slot'] == 'L' or c['state'] in ('look', 'haggle', 'talk') and \
                c['slot'] == 'L' else -1
            if c['state'] == 'out':
                fc = -1 if c['slot'] == 'L' else 1
            step = r['t'] * 9 if c['state'] in ('in', 'out') else 0
            pygame.draw.ellipse(s, darken(road, 0.3), (int(c['x']) - 6, 62, 12, 3))
            town.walker(s, int(c['x']), 63, fc, step, shirt, hair, hat, season, kid, glasses,
                        umbrella=(180, 110, 120) if rain and not has(g, 'awning') else None)
    # coins for a sale
    if r and r.get('coin_t') is not None and r['t'] - r['coin_t'] < 0.8:
        k = (r['t'] - r['coin_t']) / 0.8
        x0 = SLOT_X[r.get('coin_slot', 'L')]
        for j in range(3):
            px = int(x0 + (118 - x0) * k + j * 3)
            py = int(30 - math.sin(k * math.pi) * 14 + j)
            s.fill((246, 206, 80), (px, py, 2, 2))
    if rain:
        rr = random.Random(int(t * 12))
        for _ in range(40):
            x, y = rr.randrange(SCN_W), rr.randrange(SCN_H)
            if has(g, 'awning') and 72 <= x <= 166 and y < 40:
                continue
            s.fill((200, 214, 232), (x, y, 1, 3))
    return s


# ---------------------------------------------------------------- the window
def draw(g, s):
    ui = g.ui
    sw, sh = s.get_size()
    rect = pygame.Rect(sw // 2 - 520, sh // 2 - 318, 1040, 636)
    ui.panel(s, rect, radius=24)
    g.panel_header(s, rect, 'Your Market Stall')
    ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', lambda: close(g), 'normal', font='h3')
    r = run(g)
    tab = getattr(g, 'stall_tab', 'setup')
    if r is None or r['phase'] in ('setup', 'done'):
        for i, (key, label) in enumerate((('setup', 'Set up'), ('stall', 'Your stall'))):
            ui.button(s, (rect.x + 470 + i * 150, rect.y + 24, 140, 40), label,
                      lambda k=key: setattr(g, 'stall_tab', k), 'tab_on' if tab == key else 'tab')
    if r is not None and r['phase'] == 'open':
        return _draw_open(g, s, rect, r)
    if r is not None and r['phase'] == 'summary':
        return _draw_summary(g, s, rect, r)
    if tab == 'stall' or r is None or r['phase'] == 'done':
        return _draw_stall_tab(g, s, rect, r)
    return _draw_setup(g, s, rect, r)


def _crate_card(g, s, rc, i, c, live):
    """One crate: what's in it, how many, and its price tag (with arrows to change it)."""
    ui = g.ui
    if c is None:
        ui.tile(s, rc, (240, 232, 214), (206, 190, 166))
        ui.blit_text(s, 'Empty crate', (rc.centerx, rc.centery - 10), 'smallb', (176, 160, 140), 'center')
        if not live:
            ui.blit_text(s, 'Click something on the left', (rc.centerx, rc.centery + 14), 'tiny', (176, 160, 140),
                         'center', maxw=rc.w - 16)
        return
    k = stock(g, c)
    sp = c.get('special')
    ui.tile(s, rc, (252, 246, 228) if k or not live else (236, 228, 214), (200, 160, 80) if sp else (190, 160, 124), sp)
    iw = min(56, rc.w // 3)
    ic = goods_icon(c['kind'], c['id'], (iw, 34))
    s.blit(ic, ic.get_rect(center=(rc.x + 10 + iw // 2, rc.y + 30)))
    nx = rc.x + 18 + iw
    name = _goods_name(c['kind'], c['id'])
    ui.blit_text(s, name, (nx, rc.y + 12), 'smallb', U.INK, maxw=rc.right - nx - (34 if not live else 8))
    word = price_word(c['step'])
    col = {'Bargain': (80, 140, 80), 'Fair': (110, 110, 120), 'Pricey': (190, 130, 60), 'Steep': (190, 80, 70)}[word]
    ui.blit_text(s, ('%d left' % k) if live else ('x%d' % _count(c)), (nx, rc.y + 38), 'small',
                 U.SOFT if k else (190, 90, 80))
    if rc.w >= 180:
        ui.blit_text(s, word, (rc.right - 12, rc.y + 40), 'tiny', col, 'topright')
    if sp:
        U.star(s, (rc.x + 14, rc.y + 14), 8, (236, 190, 70))
    elif not live and has(g, 'board'):
        U.star(s, (rc.x + 14, rc.y + 14), 7, (220, 210, 190))
    if not live:
        ui.button(s, (rc.right - 30, rc.y + 8, 22, 22), 'x', lambda: take_back(g, i), 'normal', font='tiny')
        if has(g, 'board'):
            ui.hotspot(pygame.Rect(rc.x + 4, rc.y + 4, iw + 12, 50), lambda: set_special(g, i))
    # the price tag
    py = rc.bottom - 40
    if live and not k:
        ui.blit_text(s, 'Sold out!', (rc.centerx, py + 16), 'smallb', (120, 150, 100), 'center')
        return
    ui.button(s, (rc.x + 8, py, 30, 32), '<', lambda: set_step(g, i, -1), 'normal', c['step'] > 0, font='smallb')
    ui.button(s, (rc.right - 38, py, 30, 32), '>', lambda: set_step(g, i, 1), 'normal',
              c['step'] < len(STEPS) - 1, font='smallb')
    tag = pygame.Rect(rc.x + 42, py, rc.w - 84, 32)
    pygame.draw.rect(s, (250, 244, 226), tag, border_radius=8)
    pygame.draw.rect(s, col if rc.w < 180 else (190, 160, 124), tag, 2, border_radius=8)
    txt = '%d' % price_tag(g, c)
    tw = ui.fonts['smallb'].size(txt)[0] + 20
    U.coin(s, (tag.centerx - tw // 2 + 7, tag.centery), 7)
    ui.blit_text(s, txt, (tag.centerx - tw // 2 + 20, tag.centery), 'smallb', U.INK, 'midleft')


def _draw_setup(g, s, rect, r):
    ui = g.ui
    tab = getattr(g, 'stall_goods', 'fish')
    gx, gy, gw = rect.x + 30, rect.y + 88, 476
    for i, (key, label) in enumerate((('fish', 'Fish'), ('dish', 'Dishes'), ('crop', 'Garden & wild'))):
        n = sum(1 for _, k in goods(g, key) if k > 0)
        ui.button(s, (gx + i * 162, gy, 154, 38), '%s  %d' % (label, n), lambda k=key: _goods_tab(g, k),
                  'tab_on' if tab == key else 'tab', font='smallb')
    items = goods(g, tab)
    page = getattr(g, 'stall_page', 0)
    per = 12
    pages = max(1, -(-len(items) // per))
    page = min(page, pages - 1)
    tw, th = (gw - 3 * 10) // 4, 96
    for j, (gid, n) in enumerate(items[page * per:(page + 1) * per]):
        tr = pygame.Rect(gx + (j % 4) * (tw + 10), gy + 52 + (j // 4) * (th + 10), tw, th)
        hov = tr.collidepoint(ui.mouse) and n > 0
        ui.tile(s, tr, (252, 248, 236) if hov else (244, 236, 218) if n else (232, 226, 214), (196, 170, 140))
        ic = goods_icon(tab, gid, (tw - 24, 40))
        s.blit(ic, ic.get_rect(center=(tr.centerx, tr.y + 30)))
        ui.blit_text(s, _goods_name(tab, gid), (tr.centerx, tr.y + 56), 'tiny', U.INK if n else U.SOFT, 'midtop',
                     maxw=tw - 10)
        ui.blit_text(s, 'x%d' % n if n else 'all out', (tr.centerx, tr.y + 76), 'tiny', U.SOFT, 'midtop')
        if n:
            ui.hotspot(tr, lambda gid=gid: add(g, tab, gid))
    if not items:
        ui.blit_text(s, {'fish': 'No fish in your basket. Catch some first!',
                         'dish': 'Nothing in your pantry. Cook something in the cabin kitchen.',
                         'crop': 'Your garden basket is empty. Pick crops, or forage on the Far Shore.'}[tab],
                     (gx + gw // 2, gy + 160), 'small', U.SOFT, 'center', maxw=gw - 20)
    if pages > 1:
        ui.button(s, (gx, gy + 380, 44, 36), '<', lambda: setattr(g, 'stall_page', max(0, page - 1)), 'normal',
                  page > 0, font='smallb')
        ui.button(s, (gx + gw - 44, gy + 380, 44, 36), '>', lambda: setattr(g, 'stall_page', page + 1), 'normal',
                  page < pages - 1, font='smallb')
        ui.blit_text(s, '%d / %d' % (page + 1, pages), (gx + gw // 2, gy + 398), 'small', U.SOFT, 'center')
    # the crates
    cx0, cy0 = rect.x + 530, rect.y + 88
    cw, ch = 234, 120
    for i, c in enumerate(r['crates']):
        rc = pygame.Rect(cx0 + (i % 2) * (cw + 12), cy0 + (i // 2) * (ch + 12), cw, ch)
        _crate_card(g, s, rc, i, c, False)
    if not has(g, 'table'):
        rc = pygame.Rect(cx0, cy0 + 2 * (ch + 12), cw * 2 + 12, ch)
        pygame.draw.rect(s, (236, 226, 206), rc, border_radius=14)
        pygame.draw.rect(s, (214, 198, 172), rc, 2, border_radius=14)
        ui.blit_text(s, 'Two more crates with the Second Table', (rc.centerx, rc.centery), 'small', U.SOFT, 'center')
    # the bottom: orders, set out everything, open up
    by = rect.bottom - 82
    due = [o for o in g.stall['orders'] if o['due'] == g.day]
    if due:
        import town
        from data import FISH_BY_ID
        txt = 'Orders today: ' + ', '.join('%s for %s' % (FISH_BY_ID[o['fish']]['name'], town.FOLK[o['who']]['name'])
                                           for o in due)
        ui.blit_text(s, txt, (gx, by - 26), 'small', (90, 110, 160), maxw=560)
    ui.button(s, (gx, by, 200, 52), 'Set out all', lambda: fill_all(g), 'normal', font='smallb')
    tip = 'Click something to set it out. < > changes a price.' + (
        "  Click a crate's star to make it the special." if has(g, 'board') else '')
    for j, ln in enumerate(ui.wrap(tip, 'tiny', 300)[:3]):
        ui.blit_text(s, ln, (gx + 216, by + 6 + j * 18), 'tiny', U.SOFT)
    ok = any(r['crates']) and g.minute < CLOSE
    label = 'Open at 9 AM' if g.minute < OPEN else 'Open the stall'
    ui.button(s, (rect.right - 260, by - 4, 230, 60), label, lambda: open_up(g), 'primary', ok, font='h3', nav=True)


def _goods_tab(g, k):
    g.stall_goods = k
    g.stall_page = 0


def _bubble(g, s, text, x, y, maxw=360, head=None):
    ui = g.ui
    lines = ui.wrap(text, 'small', maxw - 30)[:3]
    w = max(ui.fonts['small'].size(ln)[0] for ln in lines) + 30
    if head:
        w = max(w, ui.fonts['tiny'].size(head)[0] + 30)
    h = 18 + 22 * len(lines) + (18 if head else 0)
    sw = s.get_width()
    bx = int(max(8, min(sw - 8 - w, x - w // 2)))
    bub = pygame.Rect(bx, y - h, w, h)
    pygame.draw.rect(s, (255, 252, 244), bub, border_radius=12)
    pygame.draw.rect(s, (150, 120, 96), bub, 2, border_radius=12)
    tx = max(bub.x + 14, min(bub.right - 14, x))
    pygame.draw.polygon(s, (255, 252, 244), [(tx - 8, bub.bottom - 2), (tx + 8, bub.bottom - 2), (tx, bub.bottom + 10)])
    yy = bub.y + 9
    if head:
        ui.blit_text(s, head, (bub.x + 15, yy), 'tiny', (130, 100, 80))
        yy += 18
    for ln in lines:
        ui.blit_text(s, ln, (bub.x + 15, yy), 'small', U.INK)
        yy += 22
    return bub


def _draw_open(g, s, rect, r):
    ui = g.ui
    sr = pygame.Rect(rect.x + 48, rect.y + 82, SCN_W * SCN_K, SCN_H * SCN_K)
    pygame.draw.rect(s, (120, 80, 54), sr.inflate(12, 12), border_radius=10)
    s.blit(pygame.transform.scale(draw_scene(g, r['t']), sr.size), sr)
    # what they're saying
    for c in r['cust']:
        if c['state'] in ('haggle', 'talk') and c['line']:
            x = sr.x + int(c['x'] * SCN_K)
            bub = _bubble(g, s, c['line'], x, sr.y + (63 - 34) * SCN_K, 400, c['name'])
            if c['state'] == 'haggle':
                bw = 120
                y = bub.bottom + 16
                bx = max(sr.x + 8, min(sr.right - 2 * bw - 18, bub.centerx - bw - 5))
                ui.button(s, (bx, y, bw, 44), 'Deal', lambda: accept(g), 'primary', font='smallb', nav=True)
                ui.button(s, (bx + bw + 10, y, bw, 44), 'No thanks', lambda: decline(g), 'normal', font='smallb',
                          nav=True)
    # the crates, prices still changeable
    n = len(r['crates'])
    cw = (sr.w - (n - 1) * 10) // n
    for i, c in enumerate(r['crates']):
        rc = pygame.Rect(sr.x + i * (cw + 10), sr.bottom + 18, cw, 124)
        _crate_card(g, s, rc, i, c, True)
    # the bottom line
    import main as _m
    by = rect.bottom - 66
    ui.blit_text(s, _m.fmt_clock(g.minute), (rect.x + 48, by + 6), 'h3', U.INK)
    ui.blit_text(s, 'until 1 PM', (rect.x + 48, by + 34), 'tiny', U.SOFT)
    U.coin(s, (rect.x + 200, by + 20), 10)
    ui.blit_text(s, '%d' % r['takings'], (rect.x + 216, by + 20), 'h3', (150, 110, 40), 'midleft')
    ui.blit_text(s, '%d sold' % r['sold'], (rect.x + 300, by + 20), 'small', U.SOFT, 'midleft')
    _rep_bar(g, s, pygame.Rect(rect.x + 390, by + 8, 200, 30))
    if has(g, 'bell'):
        ok = g.minute - r['bell_m'] >= 60
        ui.button(s, (rect.right - 410, by - 4, 170, 52), 'Ring the bell' if ok else 'Bell rung', lambda: ring_bell(g),
                  'gold', ok, font='smallb')
    ui.button(s, (rect.right - 228, by - 4, 180, 52), 'Pack up', lambda: pack_up(g), 'normal', font='bodyb')


def _rep_bar(g, s, rc, big=False):
    ui = g.ui
    st = g.stall
    lv = level(g)
    ui.blit_text(s, REP_NAMES[lv], (rc.x, rc.y), 'smallb' if big else 'tiny', U.INK)
    bar = pygame.Rect(rc.x, rc.y + (28 if big else 20), rc.w, 8)
    pygame.draw.rect(s, (222, 206, 180), bar, border_radius=4)
    if lv < len(REP) - 1:
        k = (st['rep'] - REP[lv]) / float(REP[lv + 1] - REP[lv])
    else:
        k = 1.0
    pygame.draw.rect(s, (200, 150, 70), (bar.x, bar.y, max(6, int(bar.w * k)), bar.h), border_radius=4)


def _draw_summary(g, s, rect, r):
    ui = g.ui
    st = g.stall
    card = pygame.Rect(rect.centerx - 330, rect.y + 96, 660, 440)
    ui.panel(s, card, fill=(252, 246, 232), radius=18, shadow=False)
    ui.blit_text(s, 'Market morning done!', (card.centerx, card.y + 26), 'h2', U.INK, 'midtop')
    tw = ui.fonts['h1'].size('%d' % r['takings'])[0] + 48
    U.coin(s, (card.centerx - tw // 2 + 18, card.y + 104), 18)
    ui.blit_text(s, '%d' % r['takings'], (card.centerx - tw // 2 + 48, card.y + 104), 'h1', (150, 110, 40),
                 'midleft')
    y = card.y + 160
    lines = ['You sold %d thing%s.' % (r['sold'], '' if r['sold'] == 1 else 's')]
    if r['per']:
        (kind, gid), n = max(r['per'].items(), key=lambda kv: kv[1])
        lines.append('Best seller: %s (%d).' % (_goods_name(kind, gid), n))
    if r['orders_done']:
        lines.append('%d order%s delivered, at double the price.' % (r['orders_done'], '' if r['orders_done'] == 1
                                                                    else 's'))
    gained = st['rep'] - r['rep0']
    lines.append('Reputation +%d: %s.' % (gained, REP_NAMES[level(g)].lower()))
    if r['takings'] and r['takings'] >= st['best']:
        lines.append('Your best market morning yet!')
    if r['dear'] >= 3:
        lines.append('%d people walked away at your prices. A little lower might sell more.' % r['dear'])
    for ln in lines:
        ui.blit_text(s, ln, (card.centerx, y), 'body', U.INK, 'midtop', maxw=card.w - 60)
        y += 36
    o = next((o for o in st['orders'] if o['due'] > g.day), None)
    if o:
        import town
        from data import FISH_BY_ID
        ui.blit_text(s, 'Next Leafday: %s for %s.' % (a_(FISH_BY_ID[o['fish']]['name']), town.FOLK[o['who']]['name']),
                     (card.centerx, y + 8), 'small', (90, 110, 160), 'midtop', maxw=card.w - 60)
    ui.button(s, (card.centerx - 100, card.bottom - 76, 200, 56), 'Lovely!', lambda: close(g), 'primary', font='h3',
              nav=True)


def _draw_stall_tab(g, s, rect, r):
    ui = g.ui
    st = g.stall
    x0, y0 = rect.x + 40, rect.y + 96
    # a little picture of the stall as it stands, and how it's known
    pic = draw_scene(g, g.t).subsurface((60, 0, 120, SCN_H))
    pr = pygame.Rect(x0, y0, 120 * 3, SCN_H * 3)
    pygame.draw.rect(s, (120, 80, 54), pr.inflate(10, 10), border_radius=10)
    s.blit(pygame.transform.scale(pic, pr.size), pr)
    _rep_bar(g, s, pygame.Rect(x0, pr.bottom + 22, pr.w, 40), big=True)
    lv = level(g)
    if lv < len(REP) - 1:
        ui.blit_text(s, 'Next: %s' % REP_PERKS[lv + 1], (x0, pr.bottom + 70), 'tiny', U.SOFT, maxw=pr.w)
    y = pr.bottom + 104
    for label, v in (('Market mornings', st['days']), ('Things sold', st['sold']), ('Coins taken', st['coins']),
                     ('Best morning', st['best'])):
        ui.blit_text(s, label, (x0, y), 'small', U.SOFT)
        ui.blit_text(s, '{:,}'.format(v), (x0 + pr.w, y), 'smallb', U.INK, 'topright')
        y += 26
    if is_day(g) and done_today(g):
        when = "You've had your market morning. See you next Leafday!"
    elif market_open(g):
        when = 'It\'s market day! Set up and open before 1 PM.'
    else:
        import almanac
        d = g.day + 1
        while almanac.dow(d) != STALL_DAY:
            d += 1
        when = 'Next market: Leafday%s, 9 AM to 1 PM.' % (' (tomorrow)' if d == g.day + 1 else '')
    ui.blit_text(s, when, (x0, rect.bottom - 52), 'small', (90, 110, 160), maxw=pr.w + 40)
    # upgrades
    ux = rect.x + 460
    ui.blit_text(s, 'Stall upgrades', (ux, y0), 'bodyb', U.INK)
    for i, u in enumerate(UPGRADES):
        rc = pygame.Rect(ux, y0 + 36 + i * 82, 540, 74)
        own = has(g, u['id'])
        ui.tile(s, rc, (238, 244, 228) if own else (246, 236, 216), (150, 180, 130) if own else (196, 170, 140))
        ui.blit_text(s, u['name'], (rc.x + 18, rc.y + 12), 'smallb', U.INK)
        ui.blit_text(s, u['desc'], (rc.x + 18, rc.y + 40), 'tiny', U.SOFT, maxw=rc.w - 200)
        if own:
            ui.blit_text(s, 'Yours', (rc.right - 80, rc.centery), 'smallb', (80, 130, 70), 'center')
        else:
            g.price_button(s, (rc.right - 160, rc.y + 14, 142, 46), u['cost'], lambda u=u: buy(g, u))
    if st['orders']:
        import town
        from data import FISH_BY_ID
        o = st['orders'][0]
        ui.blit_text(s, 'Order: %s for %s, on Leafday.' % (a_(FISH_BY_ID[o['fish']]['name']),
                                                             town.FOLK[o['who']]['name']),
                     (ux, rect.bottom - 52), 'small', (90, 110, 160), maxw=540)


# ---------------------------------------------------------------- on the street (town.py)
def street_state(g):
    """'folded' under its tarp, 'set' for market morning, 'busy' while you're selling."""
    r = run(g)
    if r is not None and r['phase'] == 'open':
        return 'busy'
    if g.stall['told'] and is_day(g) and OPEN - 60 <= g.minute < CLOSE and not done_today(g):
        return 'set'
    return 'folded'


def draw_street(s, g, sc, ground, t):
    """The stall on Fernwick's street, at the top of the lake path."""
    cx = int(STREET_X - sc)
    if not -40 < cx < s.get_width() + 40:
        return
    state = street_state(g)
    season = g.env.season
    wood, dark = (150, 104, 70), (104, 72, 50)
    sh = pygame.Surface((44, 6), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (24, 20, 32, 70), sh.get_rect())
    s.blit(sh, (cx - 22, ground - 4))
    s.fill((166, 116, 76), (cx - 18, ground - 16, 36, 14))
    s.fill((196, 146, 98), (cx - 19, ground - 17, 38, 2))
    for lx in (cx - 16, cx + 14):
        s.fill(dark, (lx, ground - 3, 2, 3))
    if state == 'folded':
        pygame.draw.polygon(s, (170, 160, 140), [(cx - 19, ground - 16), (cx - 14, ground - 24), (cx + 14, ground - 24),
                                                 (cx + 19, ground - 16)])
        for i in range(-10, 12, 6):
            s.fill((150, 140, 124), (cx + i, ground - 23, 2, 8))
        if season == 3:
            s.fill((246, 248, 255), (cx - 14, ground - 26, 28, 2))
        return
    for px in (cx - 18, cx + 16):
        s.fill(wood, (px, ground - 42, 2, 26))
    _awning(s, cx - 22, cx + 22, ground - 48, has(g, 'awning'), t, getattr(g.env, 'wind', 0.3))
    r = run(g)
    crates = r['crates'] if r else [None] * crate_cap(g)
    n = len(crates)
    w = 34 // n
    for i, c in enumerate(crates):
        x = cx - 17 + i * w
        s.fill((176, 132, 84), (x, ground - 21, w - 1, 5))
        if c and stock(g, c):
            ic = goods_icon(c['kind'], c['id'], (w - 1, 5))
            s.blit(ic, ic.get_rect(midbottom=(x + w // 2, ground - 20)))
    if has(g, 'board'):
        s.fill((60, 56, 60), (cx - 32, ground - 14, 8, 10))
        s.fill(dark, (cx - 29, ground - 4, 2, 4))
        s.fill((236, 230, 220), (cx - 31, ground - 12, 6, 1))
    if has(g, 'bell'):
        pygame.draw.polygon(s, (214, 170, 70), [(cx - 21, ground - 34), (cx - 19, ground - 38), (cx - 17, ground - 34)])
