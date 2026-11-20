"""The cabin garden: six raised beds on the slope under the cabin.

Plant seeds, water the beds once a day (rain and snow do it for you) and pick what grows. Crops sell, add an extra
serving to a matching dish in the kitchen, turn into crab-pot bait (sweetcorn) or make Biscuit very happy (catnip).
Junk fished out of the lake goes on the compost heap and comes back as plant food. Nothing ever dies: a bed that
wasn't watered simply waits a day.

A sunflower in bloom brings bees: the beds beside it (and the one across the path) give one more crop. A rain barrel
catches the rain and waters dry beds by itself on the next mornings without any.
"""
import math
import random

import pygame

import ui as U
from art import darken, lighten, lerp_c

BEDS = 6
START_OPEN = 3
BED_PRICES = (150, 300, 500)          # the 4th, 5th and 6th beds
JUNK_PER_FOOD = 3
SEASON_NAMES = ('Spring', 'Summer', 'Autumn', 'Winter')

# look: how it's drawn. n: crops per harvest. regrow: days until the next picking (None: the bed empties)
CROPS = [
    dict(id='radish', name='Radish', season=0, days=3, seed=10, sell=24, n=2, regrow=None, look='root',
         col=(226, 70, 96), leaf=(104, 170, 78)),
    dict(id='peas', name='Snap Peas', season=0, days=4, seed=15, sell=12, n=3, regrow=2, look='vine',
         col=(156, 214, 110), leaf=(84, 156, 70)),
    dict(id='strawberry', name='Strawberries', season=0, days=5, seed=25, sell=16, n=3, regrow=3, look='berry',
         col=(232, 58, 70), leaf=(78, 150, 70)),
    dict(id='corn', name='Sweetcorn', season=1, days=5, seed=20, sell=26, n=2, regrow=None, look='tall',
         col=(246, 214, 90), leaf=(110, 170, 70)),
    dict(id='tomato', name='Tomatoes', season=1, days=4, seed=20, sell=14, n=3, regrow=2, look='vine',
         col=(228, 72, 56), leaf=(86, 150, 66)),
    dict(id='sunflower', name='Sunflower', season=1, days=6, seed=30, sell=75, n=1, regrow=None, look='flower',
         col=(250, 200, 60), leaf=(96, 156, 66)),
    dict(id='pumpkin', name='Pumpkin', season=2, days=6, seed=35, sell=90, n=1, regrow=None, look='gourd',
         col=(232, 130, 50), leaf=(96, 150, 70)),
    dict(id='carrot', name='Carrots', season=2, days=3, seed=10, sell=22, n=2, regrow=None, look='root',
         col=(240, 140, 50), leaf=(110, 176, 80)),
    dict(id='beet', name='Beetroot', season=2, days=4, seed=15, sell=30, n=2, regrow=None, look='root',
         col=(150, 40, 84), leaf=(120, 150, 80)),
    dict(id='kale', name='Winter Kale', season=3, days=4, seed=15, sell=30, n=2, regrow=None, look='leafy',
         col=(96, 136, 124), leaf=(80, 120, 110)),
    dict(id='garlic', name='Garlic', season=3, days=5, seed=20, sell=22, n=3, regrow=None, look='root',
         col=(240, 236, 220), leaf=(130, 170, 110)),
    dict(id='dill', name='Dill', season=None, days=3, seed=10, sell=10, n=2, regrow=2, look='herb',
         col=(220, 214, 90), leaf=(130, 180, 80)),
    dict(id='catnip', name='Catnip', season=None, days=4, seed=20, sell=8, n=2, regrow=3, look='mint',
         col=(180, 150, 220), leaf=(110, 170, 110)),
]
CROP_BY_ID = {c['id']: c for c in CROPS}
# wild finds from the Far Shore trail (farshore.py). They are never planted, but they sit in the same basket as
# your crops: they sell, show in the garden's Picked row and go with dishes just like a fresh crop
FORAGE = [
    dict(id='morel', name='Morels', season=0, sell=30, look='mushroom', col=(176, 140, 96), leaf=(226, 214, 186)),
    dict(id='ramsons', name='Wild Garlic', season=0, sell=12, look='herb', col=(250, 250, 240), leaf=(90, 160, 80)),
    dict(id='violet', name='Sweet Violets', season=0, sell=12, look='flower', col=(150, 110, 210),
         leaf=(90, 150, 80)),
    dict(id='bilberry', name='Bilberries', season=1, sell=14, look='cluster', col=(70, 80, 150),
         leaf=(80, 140, 70)),
    dict(id='chamomile', name='Chamomile', season=1, sell=12, look='flower', col=(250, 250, 244),
         leaf=(110, 160, 80)),
    dict(id='sorrel', name='Wood Sorrel', season=1, sell=10, look='leafy', col=(120, 190, 90), leaf=(90, 150, 70)),
    dict(id='chanterelle', name='Chanterelles', season=2, sell=28, look='mushroom', col=(240, 170, 60),
         leaf=(250, 210, 120)),
    dict(id='hazelnut', name='Hazelnuts', season=2, sell=14, look='nut', col=(170, 116, 70), leaf=(120, 150, 70)),
    dict(id='blackberry', name='Blackberries', season=2, sell=16, look='cluster', col=(60, 40, 70),
         leaf=(90, 130, 60)),
    dict(id='rosehip', name='Rosehips', season=3, sell=16, look='cluster', col=(220, 70, 50), leaf=(110, 90, 60)),
    dict(id='pinetip', name='Pine Tips', season=3, sell=12, look='herb', col=(110, 170, 110), leaf=(60, 110, 70)),
    dict(id='oyster', name='Oyster Mushrooms', season=3, sell=24, look='mushroom', col=(200, 200, 196),
         leaf=(236, 232, 224)),
]
for _f in FORAGE:
    _f.update(forage=True, days=0, seed=0, n=1, regrow=None)
    CROP_BY_ID[_f['id']] = _f
FORAGE_BY_ID = {f['id']: f for f in FORAGE}
# a fresh crop that goes with a dish adds one more serving when you cook it (kitchen.py)
GARNISH = {'fritters': ('dill', 'ramsons', 'sorrel'), 'chowder': ('corn', 'peas', 'oyster'),
           'grilled': ('garlic', 'dill', 'ramsons', 'pinetip'), 'fishpie': ('peas', 'carrot', 'morel', 'chanterelle'),
           'clam': ('tomato',), 'stew': ('kale', 'carrot', 'pumpkin', 'chanterelle', 'morel', 'oyster'),
           'tart': ('strawberry', 'bilberry', 'blackberry', 'rosehip'), 'feast': ('pumpkin', 'beet', 'radish',
                                                                              'hazelnut')}
CORN_BAIT = 5                          # one cob makes this much Sweet Corn bait
BARREL_PRICE = 250
BARREL_HOLDS = 3                       # dry mornings a full barrel can water

# the beds on the slope under the cabin, in world pixels: (x, soil y, width)
BED_SPOTS = [(6, 252, 22), (32, 252, 22), (58, 252, 20), (10, 274, 22), (36, 274, 22), (62, 274, 22)]
AREA = pygame.Rect(2, 236, 92, 50)     # click here on the lake to open the garden
VIEW = pygame.Rect(0, 230, 100, 54)    # what the Garden tab shows, scaled up


def new():
    return {'beds': [None] * BEDS, 'open': START_OPEN, 'produce': {}, 'heap': 0, 'food': 0, 'grew': 0,
            'rain': 0, 'barrel': False, 'water': 0, 'poured': 0}


def clean(gd):
    out = new()
    if not isinstance(gd, dict):
        return out
    try:
        out['open'] = max(START_OPEN, min(BEDS, int(gd.get('open', START_OPEN))))
        out['heap'] = max(0, int(gd.get('heap', 0)))
        out['food'] = max(0, int(gd.get('food', 0)))
        out['grew'] = int(gd.get('grew', 0))
        out['rain'] = int(gd.get('rain', 0))
        out['barrel'] = bool(gd.get('barrel', False))
        out['water'] = max(0, min(BARREL_HOLDS, int(gd.get('water', 0))))
        out['poured'] = int(gd.get('poured', 0))
    except (TypeError, ValueError):
        pass
    pr = gd.get('produce')
    if isinstance(pr, dict):
        for k, v in pr.items():
            if k in CROP_BY_ID and isinstance(v, int) and v > 0:
                out['produce'][k] = v
    beds = gd.get('beds')
    if isinstance(beds, list):
        for i, b in enumerate(beds[:BEDS]):
            if isinstance(b, dict) and b.get('crop') in CROP_BY_ID:
                try:
                    out['beds'][i] = {'crop': b['crop'], 'age': max(0, int(b.get('age', 0))),
                                      'wet': int(b.get('wet', 0)), 'fed': bool(b.get('fed'))}
                except (TypeError, ValueError):
                    pass
    return out


# ---------------------------------------------------------------- state
def crop(b):
    return CROP_BY_ID[b['crop']]


def ready(b):
    return b is not None and b['age'] >= crop(b)['days']


def stage(b):
    """0 seed, 1 sprout, 2 young, 3 grown, 4 ready to pick."""
    if ready(b):
        return 4
    k = b['age'] / crop(b)['days']
    return 0 if k <= 0 else 1 if k < 0.34 else 2 if k < 0.67 else 3


def wet(g, b):
    return b is not None and b['wet'] == g.day


def thirsty(g):
    """Beds that would grow tonight if they were watered."""
    gd = g.garden
    return [i for i, b in enumerate(gd['beds'][:gd['open']]) if b and not ready(b) and not wet(g, b)]


def ready_beds(g):
    gd = g.garden
    return [i for i, b in enumerate(gd['beds'][:gd['open']]) if ready(b)]


def neighbours(i):
    """The beds beside bed i in its row, and the one across the path."""
    row, col = divmod(i, 3)
    return [row * 3 + c for c in (col - 1, col + 1) if 0 <= c < 3] + [(1 - row) * 3 + col]


def bees(g, i):
    """True when a sunflower in bloom next to bed i brings it bees."""
    gd = g.garden
    for j in neighbours(i):
        b = gd['beds'][j] if j < gd['open'] else None
        if b and b['crop'] == 'sunflower' and stage(b) >= 3:
            return True
    return False


def seeds_now(g):
    sea = g.season_of(g.day)
    return [c for c in CROPS if c['season'] is None or c['season'] == sea]


def raining(g):
    return g.weather in ('rain', 'snow')


def morning(g):
    """Overnight, every bed that was watered yesterday grows a day."""
    gd = g.garden
    if gd['grew'] == g.day:
        return
    gd['grew'] = g.day
    grown = 0
    for b in gd['beds']:
        if b and not ready(b) and b['wet'] == g.day - 1:
            b['age'] += 1
            grown += 1
            if ready(b):
                g.stats['crops_ready'] = g.stats.get('crops_ready', 0) + 1
    n = len(ready_beds(g))
    if n:
        g.toast('Something in the garden is ready to pick!' if n == 1 else
                '%d garden beds are ready to pick!' % n, (110, 150, 80))


def update(g, dt):
    """Rain and snow water the beds for you (and fill the barrel); the barrel waters them on dry mornings."""
    if g.garden_fx > 0:
        g.garden_fx = max(0.0, g.garden_fx - dt)
    gd = g.garden
    if g.mode != 'play':
        return
    if not raining(g):
        if gd['barrel'] and gd['water'] > 0 and gd['poured'] != g.day and g.minute >= 360:
            gd['poured'] = g.day
            beds = thirsty(g)
            if beds:
                for i in beds:
                    gd['beds'][i]['wet'] = g.day
                gd['water'] -= 1
                g.garden_fx = 1.0
                if g.place == 'lake':
                    g.toast('The rain barrel watered the garden.', (100, 130, 170))
        return
    if gd['barrel'] and gd['water'] < BARREL_HOLDS:
        gd['water'] = BARREL_HOLDS
    dry = [b for b in gd['beds'][:gd['open']] if b and not ready(b) and b['wet'] != g.day]
    for b in dry:
        b['wet'] = g.day
    if dry and gd['rain'] != g.day:
        gd['rain'] = g.day
        if g.place == 'lake':
            g.toast('The %s is watering your garden.' % ('rain' if g.weather == 'rain' else 'melting snow'),
                    (100, 130, 170))


# ---------------------------------------------------------------- things you do
def plant(g, i, cid):
    gd = g.garden
    c = CROP_BY_ID[cid]
    if i >= gd['open'] or gd['beds'][i] is not None or g.coins < c['seed'] or c not in seeds_now(g):
        return False
    g.coins -= c['seed']
    gd['beds'][i] = {'crop': cid, 'age': 0, 'wet': g.day if raining(g) else 0, 'fed': False}
    g.stats['planted'] = g.stats.get('planted', 0) + 1
    g.audio.play('plop', 0.4)
    g.save()
    return True


def water_all(g):
    gd = g.garden
    beds = thirsty(g)
    for i in beds:
        gd['beds'][i]['wet'] = g.day
    if beds:
        g.audio.play('water', 0.7)
        g.garden_fx = 1.0
        g.stats['waterings'] = g.stats.get('waterings', 0) + 1
        g.save()
    return len(beds)


def harvest(g, i, quiet=False):
    gd = g.garden
    b = gd['beds'][i]
    if not ready(b):
        return 0
    c = crop(b)
    n = c['n'] + (1 if b['fed'] else 0) + (1 if c['id'] != 'sunflower' and bees(g, i) else 0)
    gd['produce'][c['id']] = gd['produce'].get(c['id'], 0) + n
    g.stats['harvested'] = g.stats.get('harvested', 0) + n
    if c['regrow']:
        gd['beds'][i] = {'crop': c['id'], 'age': c['days'] - c['regrow'], 'wet': b['wet'], 'fed': False}
    else:
        gd['beds'][i] = None
    if not quiet:
        g.audio.play('jingle1', 0.5)
        g.toast('Picked %d %s.' % (n, c['name']), (110, 150, 80))
        if g.place == 'lake' and g.spot == 'dock':
            x, y, w = BED_SPOTS[i]
            g.world.sparkles(x + w // 2, y - 4, 10, (250, 236, 150), 8)
        g.check_badges()
        g.save()
    return n


def harvest_all(g):
    total = sum(harvest(g, i, quiet=True) for i in ready_beds(g))
    if total:
        g.audio.play('jingle2', 0.5)
        g.toast('Picked %d things from the garden.' % total, (110, 150, 80))
        g.check_badges()
        g.save()
    return total


def pull_up(g, i):
    if g.garden['beds'][i] is not None:
        g.garden['beds'][i] = None
        g.audio.play('page', 0.4)


def feed(g, i):
    gd = g.garden
    b = gd['beds'][i]
    if b is None or b['fed'] or gd['food'] <= 0:
        return False
    gd['food'] -= 1
    b['fed'] = True
    b['age'] = min(crop(b)['days'], b['age'] + 1)
    g.audio.play('chime2', 0.4)
    g.save()
    return True


COMPOST = ('boot', 'can', 'driftwood')    # not the pearl clams (chowder) or the bottles (letters)


def junk_in_basket(g):
    return [b for b in g.basket if b['id'] in COMPOST]


def compost(g):
    gd = g.garden
    junk = junk_in_basket(g)
    for b in junk:
        g.basket.remove(b)
    gd['heap'] += len(junk)
    made = gd['heap'] // JUNK_PER_FOOD
    gd['heap'] %= JUNK_PER_FOOD
    gd['food'] += made
    if junk:
        g.audio.play('page', 0.5)
        g.toast('%d bits of junk on the compost heap.%s' % (
            len(junk), ' It made %d plant food!' % made if made else ''), (130, 110, 80))
        g.save()
    return made


def open_bed(g):
    gd = g.garden
    if gd['open'] >= BEDS:
        return False
    price = BED_PRICES[gd['open'] - START_OPEN]
    if g.coins < price:
        return False
    g.coins -= price
    gd['open'] += 1
    g.audio.play('coin', 0.6)
    g.toast('A new garden bed, dug and edged.', (110, 150, 80))
    g.save()
    return True


def buy_barrel(g):
    gd = g.garden
    if gd['barrel'] or g.coins < BARREL_PRICE:
        return False
    g.coins -= BARREL_PRICE
    gd['barrel'] = True
    gd['water'] = BARREL_HOLDS
    g.audio.play('coin', 0.6)
    g.toast('A rain barrel by the beds, full to the brim.', (100, 130, 170))
    g.save()
    return True


def plant_all(g, cid):
    """The same seed in every empty bed you can pay for. How many were planted."""
    gd = g.garden
    n = 0
    for i in range(gd['open']):
        if gd['beds'][i] is None and plant(g, i, cid):
            n += 1
    return n


def produce_value(g):
    return sum(n * CROP_BY_ID[cid]['sell'] for cid, n in g.garden['produce'].items())


def sell_all(g):
    gd = g.garden
    total = produce_value(g)
    if not total:
        return 0
    n = sum(gd['produce'].values())
    gd['produce'] = {}
    g.coins += total
    g.stats['sold'] = g.stats.get('sold', 0) + n
    g.audio.play('coin', 0.7)
    g.toast('Sold %d things from the garden for %d coins.' % (n, total), (200, 160, 70))
    g.save()
    return total


def sell(g, cid):
    gd = g.garden
    n = gd['produce'].get(cid, 0)
    if n <= 0:
        return 0
    c = CROP_BY_ID[cid]
    del gd['produce'][cid]
    g.coins += n * c['sell']
    g.stats['sold'] = g.stats.get('sold', 0) + n
    g.audio.play('coin', 0.6)
    g.toast('Sold %d %s for %d coins.' % (n, c['name'], n * c['sell']), (200, 160, 70))
    g.save()
    return n * c['sell']


def corn_to_bait(g):
    gd = g.garden
    if gd['produce'].get('corn', 0) <= 0:
        return False
    _take(gd, 'corn')
    g.baits['corn'] = g.baits.get('corn', 0) + CORN_BAIT
    g.audio.play('ui', 0.5)
    g.toast('One cob makes %d Sweet Corn bait.' % CORN_BAIT, (200, 170, 80))
    return True


def catnip_today(g):
    import biscuit
    return biscuit.done_today(g, 'nip')


def give_catnip(g):
    import actors
    import biscuit
    gd = g.garden
    if gd['produce'].get('catnip', 0) <= 0 or catnip_today(g):
        return False
    _take(gd, 'catnip')
    biscuit.gain(g, 'nip')
    g.cat['trick'] = ['spin', actors.TRICK_TIME * 2]
    g.cat['sleep'] = False
    g.audio.play('purr', 0.9)
    g.toast('Biscuit rolls in the catnip, then chases her tail like a kitten.', (200, 130, 80))
    return True


def _take(gd, cid, n=1):
    gd['produce'][cid] -= n
    if gd['produce'][cid] <= 0:
        del gd['produce'][cid]


def garnish_for(g, rid):
    pr = g.garden['produce']
    for cid in GARNISH.get(rid, ()):
        if pr.get(cid, 0) > 0:
            return cid
    return None


def use_garnish(g, rid):
    cid = garnish_for(g, rid)
    if cid:
        _take(g.garden, cid)
    return cid


def uses(cid):
    """What a crop is good for, in a few words."""
    from kitchen import RECIPE_BY_ID
    dishes = [RECIPE_BY_ID[r]['name'].split(' ')[-1] for r, cs in GARNISH.items() if cid in cs]
    extra = {'corn': 'or crab-pot bait', 'catnip': 'Biscuit loves it', 'sunflower': 'Sells well'}.get(cid)
    out = ('+1 %s' % ' / '.join(dishes)) if dishes else ''
    if extra:
        out = (out + ', ' + extra) if out else extra
    return out


def hud_line(g):
    if g.place != 'lake' or g.mode != 'play':
        return None
    n = len(ready_beds(g))
    if n:
        return 'Garden: ready to pick'
    if thirsty(g) and 300 <= g.minute < 1320 and not raining(g):
        return 'Garden: the beds are dry'
    return None


# ---------------------------------------------------------------- drawing (world pixels)
def _plant(s, c, st, x, y, t):
    """One plant, growing up from the soil at (x, y)."""
    leaf, col = c['leaf'], c['col']
    dk = darken(leaf, 0.3)
    put = s.set_at
    if st == 0:
        put((x - 1, y), (70, 50, 38))
        put((x + 1, y - 1), (70, 50, 38))
        return
    if st == 1:
        s.fill(leaf, (x, y - 2, 1, 3))
        put((x - 1, y - 3), leaf)
        put((x + 1, y - 3), lighten(leaf, 0.2))
        return
    sw = int(round(math.sin(t * 1.6 + x * 0.7) * 0.6))       # a little breeze at the tips
    look = c['look']
    if look == 'root':
        h = 3 if st == 2 else 5
        thin = c['id'] == 'garlic'
        stem = (170, 70, 90) if c['id'] == 'beet' else leaf
        pygame.draw.line(s, stem, (x, y), (x - 2 + sw, y - h))
        pygame.draw.line(s, leaf, (x, y), (x + sw, y - h - (2 if thin else 1)))
        pygame.draw.line(s, dk, (x, y), (x + 2 + sw, y - h + (0 if thin else 1)))
        if not thin:
            put((x - 3 + sw, y - h), leaf)
            put((x + 3 + sw, y - h + 1), lighten(leaf, 0.15))
        if st == 4:
            s.fill(col, (x - 2, y - 1, 5, 2))
            put((x - 1, y - 2), lighten(col, 0.25))
            put((x + 2, y), darken(col, 0.25))
    elif look == 'vine':
        h = 5 if st == 2 else 9
        pygame.draw.line(s, (150, 112, 74), (x + 2, y), (x + 2, y - 10))
        for k in range(h):
            xx = x + (1 if (k // 2) % 2 else 0) + (sw if k > h - 3 else 0)
            put((xx, y - k), leaf if k % 3 else dk)
            if k % 3 == 1:
                put((xx - 1, y - k), lighten(leaf, 0.15))
        if st == 4:
            for k, (dx, dy) in enumerate(((-1, 3), (1, 6), (-1, 8))):
                if c['id'] == 'peas':
                    s.fill(col, (x + dx, y - dy, 1, 2))
                else:
                    s.fill(col, (x + dx - 1, y - dy, 2, 2))
                    put((x + dx - 1, y - dy), lighten(col, 0.3))
    elif look == 'berry':
        w = 5 if st == 2 else 7
        pygame.draw.ellipse(s, dk, (x - w // 2, y - 3, w, 4))
        pygame.draw.ellipse(s, leaf, (x - w // 2, y - 4, w, 3))
        if st == 3:
            put((x - 1, y - 4), (250, 250, 240))
            put((x + 2, y - 3), (250, 250, 240))
        if st == 4:
            for dx, dy in ((-2, -2), (1, -3), (3, -1)):
                s.fill(col, (x + dx, y + dy, 2, 2))
                put((x + dx, y + dy), lighten(col, 0.35))
    elif look == 'tall':
        h = {2: 6, 3: 11, 4: 14}[st]
        top = (x + sw, y - h)
        pygame.draw.line(s, leaf, (x, y), top)
        for k in range(2, h - 1, 3):
            d = -1 if k % 2 else 1
            pygame.draw.line(s, dk if d < 0 else leaf, (x, y - k), (x + 3 * d, y - k + 2))
        if st >= 3:
            s.fill((210, 180, 110), (top[0] - 1, top[1] - 1, 3, 1))
            put((top[0], top[1] - 2), (220, 196, 130))
        if st == 4:
            s.fill(col, (x + 1, y - 9, 2, 4))
            s.fill(darken(leaf, 0.1), (x + 1, y - 5, 2, 1))
    elif look == 'flower':
        h = {2: 6, 3: 12, 4: 16}[st]
        top = (x + sw, y - h)
        pygame.draw.line(s, leaf, (x, y), top)
        for k in (4, 8, 12):
            if k < h - 1:
                s.fill(leaf, (x - 2 if k % 8 else x + 1, y - k, 2, 1))
        if st == 3:
            pygame.draw.circle(s, dk, top, 1)
        elif st == 4:
            pygame.draw.circle(s, col, top, 3)
            pygame.draw.circle(s, (110, 70, 40), top, 1)
            put((top[0] - 1, top[1] - 1), (90, 60, 34))
    elif look == 'gourd':
        w = 6 if st == 2 else 10
        pygame.draw.line(s, dk, (x - w // 2, y), (x + w // 2, y - 1))
        for k in range(-w // 2, w // 2 + 1, 3):
            pygame.draw.ellipse(s, leaf, (x + k - 1, y - 3, 3, 2))
        if st == 4:
            r = pygame.Rect(x - 3, y - 4, 7, 5)
            pygame.draw.ellipse(s, col, r)
            put((x - 1, y - 3), lighten(col, 0.25))
            s.fill(darken(col, 0.2), (x, y - 4, 1, 5))
            s.fill((110, 120, 60), (x, y - 5, 1, 2))
    elif look == 'leafy':
        w = {2: 4, 3: 6, 4: 8}[st]
        pygame.draw.ellipse(s, dk, (x - w // 2, y - w // 2 - 1, w, w // 2 + 2))
        pygame.draw.ellipse(s, col if st == 4 else leaf, (x - w // 2 + 1, y - w // 2 - 2, w - 2, w // 2 + 1))
        for k in range(-w // 2 + 1, w // 2, 2):
            put((x + k, y - w // 2 - 2), lighten(leaf, 0.2))
    elif look == 'herb':
        h = 4 if st == 2 else 7
        for dx in (-2, 0, 2):
            pygame.draw.line(s, leaf if dx else dk, (x + dx // 2, y), (x + dx + sw, y - h + abs(dx) // 2))
        if st == 4:
            for dx in (-2, 0, 2):
                s.fill(col, (x + dx + sw - 1, y - h - 1 + abs(dx) // 2, 3, 1))
    else:   # mint
        w = 5 if st == 2 else 7
        pygame.draw.ellipse(s, dk, (x - w // 2, y - 3, w, 4))
        pygame.draw.ellipse(s, leaf, (x - w // 2, y - 4, w - 1, 3))
        if st == 4:
            for dx in (-2, 1):
                s.fill(col, (x + dx + sw, y - 7, 1, 3))
                put((x + dx + sw, y - 8), lighten(col, 0.3))


def draw_beds(s, g, t, ox=0, oy=0, sel=None):
    """The garden as it stands, at world scale. ox, oy shift it (the Garden tab draws it on its own)."""
    gd = g.garden
    sea = g.env.season
    wood, wood_d = (158, 110, 70), (118, 80, 52)
    for i, (x, y, w) in enumerate(BED_SPOTS):
        x += ox
        y += oy
        if i >= gd['open']:
            # a patch still waiting to be dug: a stake and a few weeds
            s.fill((96, 72, 54), (x + 1, y - 1, w - 2, 3))
            s.fill((150, 112, 74), (x + w - 4, y - 7, 1, 7))
            s.fill((236, 226, 200), (x + w - 6, y - 8, 5, 3))
            for k in (3, 9, 14):
                if k < w - 6:
                    s.set_at((x + k, y - 2), (110, 150, 80) if sea != 3 else (220, 228, 236))
                    s.set_at((x + k + 1, y - 3), (90, 130, 70) if sea != 3 else (200, 210, 224))
            continue
        b = gd['beds'][i]
        soil = (74, 54, 42) if wet(g, b) else (118, 88, 62)
        s.fill(soil, (x, y - 2, w, 4))
        for k in range(1, w - 1, 3):
            s.set_at((x + k, y - 1), darken(soil, 0.18))
        if wet(g, b):
            for k in range(2, w - 2, 5):
                s.set_at((x + k, y - 2), (110, 130, 150))
        # the board along the front
        s.fill(wood, (x - 1, y + 2, w + 2, 3))
        s.fill(lighten(wood, 0.18), (x - 1, y + 2, w + 2, 1))
        s.fill(wood_d, (x - 1, y + 5, w + 2, 1))
        s.fill(wood_d, (x - 1, y - 2, 1, 7))
        s.fill(wood_d, (x + w, y - 2, 1, 7))
        if sea == 3:
            s.fill((236, 240, 248), (x - 1, y + 1, w + 2, 1))
        if b:
            c = crop(b)
            st = stage(b)
            for k in range(3):
                _plant(s, c, st, x + int(w * (k + 0.5) / 3), y - 1, t + k)
            if st == 4 and int(t * 2 + i) % 4 == 0:
                s.set_at((x + w // 2, y - 15 if c['look'] in ('tall', 'flower') else y - 9), (255, 250, 210))
        if sel == i:
            pygame.draw.rect(s, (255, 236, 150), (x - 3, y - 18, w + 6, 26), 1)
    # a watering can and the compost heap
    cx, cy = 86 + ox, 266 + oy
    can = (120, 150, 170)
    s.fill(can, (cx, cy - 4, 5, 4))
    s.fill(lighten(can, 0.25), (cx, cy - 4, 5, 1))
    pygame.draw.line(s, can, (cx + 5, cy - 3), (cx + 8, cy - 6))
    pygame.draw.line(s, darken(can, 0.3), (cx + 1, cy - 6), (cx + 3, cy - 6))
    if gd['barrel']:
        bx, by = 90 + ox, 258 + oy
        oak = (128, 88, 58)
        s.fill(darken(oak, 0.2), (bx, by, 7, 9))
        s.fill(oak, (bx + 1, by, 5, 9))
        s.fill((96, 100, 108), (bx, by + 2, 7, 1))
        s.fill((96, 100, 108), (bx, by + 6, 7, 1))
        s.fill((80, 110, 140) if gd['water'] else (70, 52, 40), (bx + 1, by, 5, 1))
    # the compost bin: a slatted box on the lower lawn, with the heap showing over the top
    hx, hy = 2 + ox, 306 + oy
    slat, slat_d = (150, 108, 70), (104, 74, 50)
    heap = gd['heap'] + min(3, gd['food'])
    if heap:
        pygame.draw.ellipse(s, (96, 72, 50), (hx + 1, hy - 10 - min(3, heap), 9, 5 + min(3, heap)))
        for k, col in enumerate(((120, 100, 60), (96, 128, 70), (150, 116, 70))):
            s.set_at((hx + 3 + k * 2, hy - 9 - min(3, heap) + k % 2), col)
    s.fill(slat_d, (hx, hy - 8, 11, 8))
    for k in range(3):
        s.fill(slat, (hx, hy - 8 + k * 3, 11, 2))
    s.fill(slat_d, (hx, hy - 9, 1, 9))
    s.fill(slat_d, (hx + 10, hy - 9, 1, 9))
    fx = getattr(g, 'garden_fx', 0)
    if fx > 0:
        rng = random.Random(int(t * 20))
        for _ in range(14):
            i = rng.randrange(len(BED_SPOTS))
            x, y, w = BED_SPOTS[i]
            if i < gd['open']:
                s.set_at((x + ox + rng.randrange(w), y + oy - 3 - rng.randrange(10)), (170, 210, 240))


def draw_world(near, g, t):
    draw_beds(near, g, t)


def crop_icon(cid, scale=3):
    """A crop on its own, for lists: drawn at 16x16 and scaled up in whole steps."""
    c = CROP_BY_ID[cid]
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    col, leaf = c['col'], c['leaf']
    d = pygame.draw
    look = c['look']
    if look == 'root':
        if cid == 'garlic':
            d.ellipse(s, col, (4, 7, 8, 7))
            d.line(s, darken(col, 0.2), (8, 8), (8, 13))
            d.line(s, leaf, (8, 7), (8, 2))
        else:
            long_ = cid == 'carrot'
            if long_:
                d.polygon(s, col, [(5, 6), (11, 6), (8, 15)])
            else:
                d.ellipse(s, col, (4, 6, 8, 8))
                s.set_at((8, 14), darken(col, 0.3))
            s.set_at((6, 8), lighten(col, 0.35))
            for dx in (-2, 0, 2):
                d.line(s, (170, 70, 90) if cid == 'beet' and dx else leaf, (8, 6), (8 + dx, 1))
    elif look == 'vine':
        if cid == 'peas':
            d.ellipse(s, col, (2, 6, 12, 5))
            for k in range(3):
                s.set_at((5 + k * 3, 8), darken(col, 0.25))
            d.line(s, leaf, (13, 7), (15, 4))
        else:
            d.circle(s, col, (8, 9), 5)
            s.set_at((6, 7), lighten(col, 0.4))
            d.line(s, leaf, (6, 4), (10, 4))
            s.set_at((8, 3), leaf)
    elif look == 'berry':
        d.polygon(s, col, [(3, 6), (13, 6), (8, 15)])
        for p in ((6, 8), (9, 9), (7, 11), (10, 7)):
            s.set_at(p, (255, 230, 150))
        d.line(s, leaf, (4, 5), (12, 5), 2)
    elif look == 'tall':
        d.ellipse(s, col, (5, 2, 6, 12))
        for k in range(3, 13, 2):
            d.line(s, darken(col, 0.15), (6, k), (10, k))
        d.polygon(s, leaf, [(4, 14), (6, 6), (7, 14)])
        d.polygon(s, leaf, [(12, 14), (10, 6), (9, 14)])
    elif look == 'flower':
        for a in range(10):
            ang = a * math.pi / 5
            d.circle(s, col, (8 + int(5 * math.cos(ang)), 8 + int(5 * math.sin(ang))), 2)
        d.circle(s, (110, 70, 40), (8, 8), 3)
    elif look == 'gourd':
        d.ellipse(s, col, (1, 5, 14, 10))
        d.line(s, darken(col, 0.2), (8, 5), (8, 14))
        d.line(s, darken(col, 0.15), (4, 6), (4, 13))
        d.line(s, darken(col, 0.15), (12, 6), (12, 13))
        d.line(s, (110, 120, 60), (8, 5), (9, 2), 2)
    elif look == 'leafy':
        d.ellipse(s, darken(col, 0.2), (2, 4, 12, 11))
        d.ellipse(s, col, (3, 3, 10, 9))
        for k in range(4, 13, 2):
            s.set_at((k, 3), lighten(col, 0.3))
        d.line(s, lighten(col, 0.25), (8, 5), (8, 13))
    elif look == 'herb':
        for dx in (-4, 0, 4):
            d.line(s, leaf, (8, 15), (8 + dx, 4))
            d.line(s, col, (8 + dx - 2, 4), (8 + dx + 2, 4))
    elif look == 'mushroom':
        for k, (mx, my, r) in enumerate(((5, 7, 4), (11, 9, 3))):
            d.rect(s, leaf, (mx - 1, my, 3, 15 - my))
            d.ellipse(s, darken(col, 0.25), (mx - r, my - r + 1, r * 2, r + 2))
            d.ellipse(s, col, (mx - r, my - r, r * 2, r + 1))
            s.set_at((mx - 1, my - r + 1), lighten(col, 0.4))
    elif look == 'cluster':
        for p in ((6, 8), (10, 8), (8, 11), (5, 12), (11, 12), (8, 6)):
            d.circle(s, col, p, 2)
            s.set_at((p[0] - 1, p[1] - 1), lighten(col, 0.45))
        d.line(s, leaf, (8, 5), (8, 1))
        d.line(s, leaf, (8, 2), (12, 1))
    elif look == 'nut':
        for mx, my in ((5, 10), (11, 11)):
            d.ellipse(s, darken(col, 0.25), (mx - 4, my - 3, 8, 7))
            d.ellipse(s, col, (mx - 4, my - 4, 8, 7))
            s.set_at((mx - 2, my - 2), lighten(col, 0.4))
            d.line(s, leaf, (mx - 3, my - 4), (mx + 3, my - 4), 2)
    else:
        d.ellipse(s, leaf, (2, 7, 12, 8))
        d.line(s, darken(leaf, 0.3), (8, 8), (8, 14))
        d.line(s, col, (5, 2), (5, 7), 2)
        d.line(s, col, (11, 3), (11, 7), 2)
    return pygame.transform.scale(s, (16 * scale, 16 * scale))


# ---------------------------------------------------------------- the Garden tab in the cabin
CARD = (47, 39)          # one bed's picture, in art pixels
CARD_K = 4               # drawn at this zoom
_CARD_BG = {}


def _card_bg(season, night):
    """Grass behind a bed: cached per season and light."""
    key = (season, night)
    if key not in _CARD_BG:
        w, h = CARD
        nf = night / 10
        s = pygame.Surface((w, h))
        top = lerp_c(((206, 226, 178), (200, 222, 160), (226, 210, 160), (226, 232, 240))[season], (70, 80, 100), nf * 0.6)
        bot = lerp_c(((128, 168, 92), (118, 160, 82), (164, 146, 84), (210, 218, 228))[season], (50, 60, 70), nf * 0.6)
        for y in range(h):
            s.fill(lerp_c(top, bot, y / (h - 1)), (0, y, w, 1))
        rng = random.Random(season)
        for _ in range(60):
            x, y = rng.randrange(w), rng.randrange(h // 3, h)
            c = s.get_at((x, y))
            s.set_at((x, y), darken(c, 0.1) if rng.random() < 0.6 else lighten(c, 0.08))
        _CARD_BG[key] = s
    return _CARD_BG[key]


def _bee(s, x, y, t):
    x, y = int(x), int(y)
    s.set_at((x, y), (250, 210, 70))
    s.set_at((x + 1, y), (40, 34, 30))
    s.set_at((x + 2, y), (250, 210, 70))
    if int(t * 16) % 2:
        s.set_at((x + 1, y - 1), (240, 248, 255))


def _bed_card(g, i, t):
    """Bed i as a little picture: the raised bed, its plants, the soil wet or dry."""
    gd = g.garden
    w, h = CARD
    s = _card_bg(g.env.season, int(round(g.env.nf * 10))).copy()
    sea = g.env.season
    soil_y = 29
    x0, x1 = 4, w - 4
    if i >= gd['open']:
        # an unused patch: rough ground, two stakes and a string
        s.fill((112, 86, 62), (x0, soil_y - 1, x1 - x0, 6))
        for k in range(x0 + 2, x1 - 2, 4):
            s.set_at((k, soil_y - 2), (90, 130, 70) if sea != 3 else (220, 228, 236))
            s.set_at((k + 1, soil_y - 3), (110, 150, 80) if sea != 3 else (236, 240, 246))
        for sx in (x0 + 1, x1 - 2):
            s.fill((150, 112, 74), (sx, soil_y - 10, 2, 11))
        pygame.draw.line(s, (236, 226, 200), (x0 + 2, soil_y - 8), (x1 - 2, soil_y - 8))
        return s
    b = gd['beds'][i]
    is_wet = wet(g, b)
    soil = (76, 56, 44) if is_wet else (128, 96, 68)
    wood, wood_d = (164, 114, 72), (116, 78, 50)
    s.fill(darken(soil, 0.15), (x0, soil_y - 3, x1 - x0, 9))
    s.fill(soil, (x0, soil_y - 3, x1 - x0, 6))
    for k in range(x0 + 1, x1 - 1, 3):
        s.set_at((k, soil_y), darken(soil, 0.2))
        s.set_at((k + 1, soil_y + 2), darken(soil, 0.12))
    if is_wet:
        for k in range(x0 + 3, x1 - 3, 7):
            s.set_at((k, soil_y - 2), (120, 140, 160))
    elif b and not ready(b):
        for k in range(x0 + 6, x1 - 6, 13):                # little cracks in dry soil
            s.set_at((k, soil_y - 1), darken(soil, 0.35))
            s.set_at((k + 1, soil_y), darken(soil, 0.35))
    # the boards: front, ends
    s.fill(wood, (x0 - 2, soil_y + 3, x1 - x0 + 4, 5))
    s.fill(lighten(wood, 0.2), (x0 - 2, soil_y + 3, x1 - x0 + 4, 1))
    s.fill(wood_d, (x0 - 2, soil_y + 8, x1 - x0 + 4, 1))
    for k in range(x0 + 10, x1, 14):
        s.fill(wood_d, (k, soil_y + 4, 1, 4))
    s.fill(wood_d, (x0 - 2, soil_y - 4, 2, 12))
    s.fill(wood_d, (x1, soil_y - 4, 2, 12))
    if sea == 3:
        s.fill((240, 244, 250), (x0 - 2, soil_y + 2, x1 - x0 + 4, 1))
    if b:
        c = crop(b)
        st = stage(b)
        for k in range(3):
            px = x0 + int((x1 - x0) * (k + 0.5) / 3)
            _plant(s, c, st, px, soil_y - 2, t + k * 0.7)
        if st == 4:
            for k in range(3):                                # it twinkles when it's ready
                ph = (t * 1.3 + k * 0.37 + i * 0.21) % 1
                if ph < 0.25:
                    sx = x0 + 5 + (k * 13 + i * 7) % (x1 - x0 - 10)
                    sy = soil_y - 10 - (k * 5) % 7
                    s.set_at((sx, sy), (255, 250, 210))
                    if ph < 0.12:
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            s.set_at((sx + dx, sy + dy), (250, 230, 150))
    if bees(g, i) or (b and b['crop'] == 'sunflower' and stage(b) >= 3):
        for k in range(2):
            a = t * (1.6 + k * 0.4) + i + k * 2
            _bee(s, w / 2 + math.cos(a) * (10 + k * 5), 13 + math.sin(a * 2) * 4, t + k)
    if getattr(g, 'garden_fx', 0) > 0:                         # drops from the watering can
        rng = random.Random(int(t * 20) + i)
        for _ in range(8):
            s.set_at((rng.randrange(x0, x1), rng.randrange(6, soil_y)), (170, 210, 240))
    return s


def _drop(s, c, r, col=(96, 150, 210)):
    x, y = c
    pygame.draw.circle(s, col, (x, y + r // 3), r)
    pygame.draw.polygon(s, col, [(x - r + 1, y + r // 3 - 1), (x + r - 1, y + r // 3 - 1), (x, y - r - 2)])
    pygame.draw.circle(s, lighten(col, 0.5), (x - r // 3, y), max(1, r // 4))


def _sel_key(g):
    sel = g.garden_sel
    if isinstance(sel, int) and not 0 <= sel < BEDS:
        return None
    if isinstance(sel, str) and sel.startswith('p:') and g.garden['produce'].get(sel[2:], 0) <= 0:
        return None
    return sel


def draw_tab(g, s, rect):
    ui = g.ui
    gd = g.garden
    t = g.t
    sel = g.garden_sel = _sel_key(g)
    # ---- the six beds, as cards
    cw, ch = CARD[0] * CARD_K, CARD[1] * CARD_K
    gx, gy = rect.x + 30, rect.y + 92
    for i in range(BEDS):
        r = pygame.Rect(gx + (i % 3) * (cw + 14), gy + (i // 3) * (ch + 14), cw, ch)
        pic = pygame.transform.scale(_bed_card(g, i, t), r.size)
        on = sel == i
        hov = r.collidepoint(ui.mouse)
        s.blit(ui._frame(r.w + 8, r.h + 8, (120, 86, 60), (230, 180, 70) if on else (84, 58, 42), 2),
               r.inflate(8, 8))
        s.blit(pic, r)
        if hov and not on:
            pygame.draw.rect(s, (255, 250, 230), r, 2)
        ui.hotspot(r, lambda i=i: _select(g, i))
        if i >= gd['open']:
            label = 'Dig a new bed' if i == gd['open'] else 'Unused patch'
            ui.blit_text(s, label, (r.x + 10, r.y + 8), 'smallb', U.INK, outline=(250, 244, 228))
            if i == gd['open']:
                price = BED_PRICES[gd['open'] - START_OPEN]
                U.coin(s, (r.x + 18, r.y + 46), 8)
                ui.blit_text(s, str(price), (r.x + 30, r.y + 46), 'smallb', U.INK, 'midleft', outline=(250, 244, 228))
            continue
        b = gd['beds'][i]
        if b is None:
            ui.blit_text(s, 'Empty', (r.x + 10, r.y + 8), 'smallb', U.INK, outline=(250, 244, 228))
            ui.blit_text(s, '+ plant', (r.centerx, r.y + 64), 'smallb', (90, 120, 70), 'center',
                         outline=(250, 244, 228))
            continue
        c = crop(b)
        st = stage(b)
        ui.blit_text(s, c['name'], (r.x + 10, r.y + 8), 'smallb', U.INK, outline=(250, 244, 228), maxw=r.w - 50)
        if st == 4:
            chip = pygame.Rect(r.right - 62, r.y + 8, 54, 26)
            pygame.draw.rect(s, (246, 210, 110), chip, border_radius=12)
            pygame.draw.rect(s, (170, 120, 50), chip, 2, border_radius=12)
            ui.blit_text(s, 'Pick', chip.center, 'smallb', U.INK, 'center')
        elif not wet(g, b):
            k = 9 + int(math.sin(t * 4 + i) * 1.5)
            _drop(s, (r.right - 22, r.y + 22), k)
        # days grown, as pips along the bottom board
        n = c['days']
        for k in range(n):
            px = r.centerx - (n - 1) * 8 + k * 16
            done = k < b['age']
            pygame.draw.circle(s, (126, 186, 100) if done else (90, 64, 44), (px, r.bottom - 10), 5)
            pygame.draw.circle(s, (60, 44, 32), (px, r.bottom - 10), 5, 1)
        if b['fed']:
            ui.blit_text(s, 'fed', (r.x + 10, r.bottom - 10), 'tiny', (250, 244, 228), 'midleft',
                         outline=(70, 50, 36))
    # ---- the basket of things picked
    py = gy + 2 * ch + 14 + 26
    ui.blit_text(s, 'Picked', (gx, py), 'h3', U.INK)
    items = sorted(gd['produce'].items(), key=lambda kv: list(CROP_BY_ID).index(kv[0]))
    if not items:
        ui.blit_text(s, 'Nothing picked yet. Ready beds twinkle.', (gx + 110, py + 6), 'small', U.SOFT)
    full_w = 3 * cw + 28
    tw = 64
    for k, (cid, n) in enumerate(items[:7]):
        tr = pygame.Rect(gx + k * (tw + 8), py + 34, tw, 60)
        on = sel == 'p:' + cid
        ui.tile(s, tr, (255, 246, 214) if on else (250, 244, 228), (230, 180, 70) if on else (160, 190, 120))
        ic = crop_icon(cid, 2)
        s.blit(ic, ic.get_rect(center=(tr.centerx, tr.y + 24)))
        ui.blit_text(s, str(n), (tr.right - 6, tr.bottom - 4), 'smallb', U.INK, 'bottomright', outline=(250, 244, 228))
        ui.hotspot(tr, lambda cid=cid: _select(g, 'p:' + cid))
    if items:
        v = produce_value(g)
        ui.button(s, (gx + full_w - 168, py + 40, 168, 48), 'Sell all  %d' % v, lambda: sell_all(g), 'gold',
                  font='smallb')
    # ---- the right-hand column
    x0 = gx + full_w + 30
    pw = rect.right - 30 - x0
    pane = pygame.Rect(x0, gy - 4, pw, rect.bottom - 20 - (gy - 4))
    ui.tile(s, pane, (252, 247, 234), (196, 172, 140))
    x, y, w = pane.x + 18, pane.y + 16, pane.w - 36
    if isinstance(sel, int) and sel >= gd['open']:
        _pane_patch(g, s, x, y, w, pane, sel)
    elif isinstance(sel, int) and gd['beds'][sel] is None:
        _pane_seeds(g, s, x, y, w, pane, sel)
    elif isinstance(sel, int):
        _pane_bed(g, s, x, y, w, pane, sel)
    elif isinstance(sel, str):
        _pane_produce(g, s, x, y, w, pane, sel[2:])
    else:
        _pane_today(g, s, x, y, w, pane)


def _back(g, s, pane):
    g.ui.button(s, (pane.right - 92, pane.y + 12, 78, 32), 'Back', lambda: setattr(g, 'garden_sel', None), 'normal',
                font='tiny')


def _pane_today(g, s, x, y, w, pane):
    ui = g.ui
    gd = g.garden
    ui.blit_text(s, 'Today', (x, y), 'h3', U.INK)
    nd, nr = len(thirsty(g)), len(ready_beds(g))
    if raining(g):
        note = 'The weather is watering the beds.'
    elif nd:
        note = '%d bed%s could use water.' % (nd, '' if nd == 1 else 's')
    elif any(gd['beds'][:gd['open']]):
        note = 'All watered for today.'
    else:
        note = 'Click an empty bed to plant.'
    ui.blit_text(s, note, (x, y + 34), 'small', U.SOFT, maxw=w)
    ui.button(s, (x, y + 66, w, 46), 'Water the beds' + ('  (%d)' % nd if nd else ''), lambda: water_all(g), 'primary',
              enabled=nd > 0)
    ui.button(s, (x, y + 120, w, 46), 'Pick everything' + ('  (%d)' % nr if nr else ''), lambda: harvest_all(g),
              'gold', enabled=nr > 0)
    # the rain barrel
    y += 186
    pygame.draw.line(s, (226, 212, 186), (x, y - 8), (x + w, y - 8), 2)
    bic = pygame.Surface((10, 12), pygame.SRCALPHA)
    oak = (128, 88, 58)
    bic.fill(darken(oak, 0.2), (1, 1, 8, 11))
    bic.fill(oak, (2, 1, 6, 11))
    bic.fill((96, 100, 108), (1, 3, 8, 1))
    bic.fill((96, 100, 108), (1, 8, 8, 1))
    bic.fill((80, 120, 160) if gd['water'] else (70, 52, 40), (2, 1, 6, 1))
    s.blit(pygame.transform.scale(bic, (30, 36)), (x, y))
    ui.blit_text(s, 'Rain barrel', (x + 42, y), 'smallb', U.INK)
    if gd['barrel']:
        for k in range(BARREL_HOLDS):
            _drop(s, (x + 52 + k * 22, y + 30), 6, (96, 150, 210) if k < gd['water'] else (214, 204, 188))
        ui.blit_text(s, 'Waters dry beds on its own,', (x + 42, y + 46), 'tiny', U.SOFT, maxw=w - 42)
        ui.blit_text(s, 'and the rain fills it again.', (x + 42, y + 64), 'tiny', U.SOFT, maxw=w - 42)
    else:
        ui.blit_text(s, 'Catches the rain, then waters', (x + 42, y + 24), 'tiny', U.SOFT, maxw=w - 42)
        ui.blit_text(s, 'dry beds for you, %d mornings a fill.' % BARREL_HOLDS, (x + 42, y + 42), 'tiny', U.SOFT,
                     maxw=w - 42)
        g.price_button(s, (x + 42, y + 64, 140, 38), BARREL_PRICE, lambda: buy_barrel(g))
    # the compost heap
    y += 120
    pygame.draw.line(s, (226, 212, 186), (x, y - 8), (x + w, y - 8), 2)
    ui.blit_text(s, 'Compost heap', (x, y), 'smallb', U.INK)
    ui.blit_text(s, 'Plant food: %d' % gd['food'], (x + w, y), 'smallb', (96, 140, 80), 'topright')
    for k in range(JUNK_PER_FOOD):
        r = pygame.Rect(x + k * 26, y + 30, 20, 14)
        pygame.draw.rect(s, (150, 118, 80) if k < gd['heap'] else (226, 214, 196), r, border_radius=5)
    ui.blit_text(s, 'junk from the lake makes food', (x + JUNK_PER_FOOD * 26 + 6, y + 37), 'tiny', U.SOFT, 'midleft',
                 maxw=w - JUNK_PER_FOOD * 26 - 6)
    nj = len(junk_in_basket(g))
    ui.button(s, (x, y + 56, w, 38), 'Add junk from the basket' + ('  (%d)' % nj if nj else ''), lambda: compost(g),
              'normal', enabled=nj > 0, font='smallb')
    for k, line in enumerate(ui.wrap('Tip: a sunflower in bloom brings bees, and the beds beside it give one '
                                     'more crop.', 'tiny', w)[:3]):
        ui.blit_text(s, line, (x, pane.bottom - 70 + k * 20), 'tiny', (110, 140, 80))


def _pane_patch(g, s, x, y, w, pane, sel):
    ui = g.ui
    gd = g.garden
    _back(g, s, pane)
    ui.blit_text(s, 'An unused patch', (x, y), 'h3', U.INK, maxw=w - 90)
    for k, line in enumerate(ui.wrap('Dig it over and edge it with boards to make another raised bed.', 'small', w)):
        ui.blit_text(s, line, (x, y + 40 + k * 24), 'small', U.SOFT)
    if sel == gd['open']:
        price = BED_PRICES[gd['open'] - START_OPEN]
        ui.blit_text(s, 'Dig it for:', (x, y + 92), 'smallb', U.INK)
        g.price_button(s, (x, y + 110, w, 48), price, lambda: open_bed(g))
    else:
        ui.blit_text(s, 'Dig the beds in order.', (x, y + 116), 'smallb', U.SOFT)


def _pane_seeds(g, s, x, y, w, pane, sel):
    ui = g.ui
    gd = g.garden
    _back(g, s, pane)
    sea = g.season_of(g.day)
    ui.blit_text(s, 'Plant something', (x, y), 'h3', U.INK, maxw=w - 90)
    ui.blit_text(s, '%s seeds and herbs' % SEASON_NAMES[sea], (x, y + 32), 'small', U.SOFT)
    empty = [i for i in range(gd['open']) if gd['beds'][i] is None]
    fill = getattr(g, 'garden_fill', False) and len(empty) > 1
    seeds = seeds_now(g)
    rh = min(58, (pane.bottom - 70 - (y + 62)) // max(1, len(seeds)))
    for k, c in enumerate(seeds):
        r = pygame.Rect(x, y + 62 + k * rh, w, rh - 6)
        cost = c['seed'] * (len(empty) if fill else 1)
        ok = g.coins >= c['seed']
        hov = ok and r.collidepoint(ui.mouse)
        ui.tile(s, r, (255, 250, 236) if hov else (246, 238, 220), (196, 170, 140))
        ic = crop_icon(c['id'], 2)
        s.blit(ic, ic.get_rect(center=(r.x + 24, r.centery)))
        ui.blit_text(s, c['name'], (r.x + 48, r.y + 4), 'smallb', U.INK, maxw=w - 140)
        rg = ', again every %d' % c['regrow'] if c['regrow'] else ''
        ui.blit_text(s, '%d days%s' % (c['days'], rg), (r.x + 48, r.y + 26), 'tiny', U.SOFT, maxw=w - 140)
        U.coin(s, (r.right - 64, r.centery), 8)
        ui.blit_text(s, '%d' % cost, (r.right - 52, r.centery), 'smallb', U.INK if g.coins >= cost else (190, 120, 100),
                     'midleft')
        if ok:
            act = (lambda c=c: plant_all(g, c['id'])) if fill else (lambda c=c: plant(g, sel, c['id']))
            ui.hotspot(r, act)
    if len(empty) > 1:
        ui.button(s, (x, pane.bottom - 58, w, 40),
                  ('Plant in: all %d empty beds' % len(empty)) if fill else 'Plant in: just this bed',
                  lambda: setattr(g, 'garden_fill', not getattr(g, 'garden_fill', False)),
                  'tab_on' if fill else 'normal', font='smallb')


def _pane_bed(g, s, x, y, w, pane, sel):
    ui = g.ui
    gd = g.garden
    b = gd['beds'][sel]
    c = crop(b)
    st = stage(b)
    _back(g, s, pane)
    ic = crop_icon(c['id'], 4)
    s.blit(ic, (x, y))
    ui.blit_text(s, c['name'], (x + 76, y + 4), 'h3', U.INK, maxw=w - 76 - 90)
    words = ('Just planted', 'Sprouting', 'Growing', 'Nearly there', 'Ready to pick!')[st]
    ui.blit_text(s, words, (x + 76, y + 36), 'smallb', (90, 140, 70) if st == 4 else U.SOFT)
    y += 84
    bar = pygame.Rect(x, y, w, 14)
    pygame.draw.rect(s, (226, 214, 196), bar, border_radius=7)
    pygame.draw.rect(s, (140, 190, 100), (bar.x, bar.y, max(14, int(bar.w * min(1, b['age'] / c['days']))), bar.h),
                     border_radius=7)
    ui.blit_text(s, 'Day %d of %d' % (min(b['age'], c['days']), c['days']), (x, y + 22), 'small', U.SOFT)
    if st < 4:
        ui.blit_text(s, 'Watered today' if wet(g, b) else 'Needs water today', (x + w, y + 22), 'small',
                     (90, 130, 170) if wet(g, b) else (190, 120, 90), 'topright')
    y += 56
    extra = []
    n = c['n'] + (1 if b['fed'] else 0) + (1 if c['id'] != 'sunflower' and bees(g, sel) else 0)
    extra.append('Each picking gives %d.' % n)
    if b['fed']:
        extra.append('Fed with plant food: one extra.')
    if c['id'] != 'sunflower' and bees(g, sel):
        extra.append('Bees from the sunflower: one extra.')
    if c['id'] == 'sunflower':
        extra.append('In bloom it brings bees to the beds beside it.')
    if c['regrow']:
        extra.append('Grows back %d days after picking.' % c['regrow'])
    u = uses(c['id'])
    if u:
        extra.append(u)
    for line in extra[:5]:
        ui.blit_text(s, line, (x, y), 'small', (90, 120, 80) if 'extra' in line or 'bees' in line else U.SOFT, maxw=w)
        y += 24
    by = pane.bottom - 70
    if st == 4:
        ui.button(s, (x, by, w - 120, 48), 'Pick', lambda: harvest(g, sel), 'gold')
    else:
        ui.button(s, (x, by, w - 120, 48), 'Plant food (%d)' % gd['food'], lambda: feed(g, sel), 'normal',
                  enabled=gd['food'] > 0 and not b['fed'], font='smallb')
    ui.button(s, (x + w - 110, by, 110, 48), 'Pull up', lambda: pull_up(g, sel), 'rose', font='smallb')


def _pane_produce(g, s, x, y, w, pane, cid):
    ui = g.ui
    gd = g.garden
    c = CROP_BY_ID[cid]
    n = gd['produce'].get(cid, 0)
    _back(g, s, pane)
    ic = crop_icon(cid, 4)
    s.blit(ic, (x, y))
    ui.blit_text(s, c['name'], (x + 76, y + 4), 'h3', U.INK, maxw=w - 76 - 90)
    ui.blit_text(s, '%d in the basket' % n, (x + 76, y + 36), 'smallb', U.SOFT)
    y += 92
    u = uses(cid)
    lines = ['Each one sells for %d.' % c['sell']]
    if u:
        lines.append(u)
    lines.append('Fresh crops add a serving to the dish they go with when you cook.')
    for line in lines:
        for ln in ui.wrap(line, 'small', w):
            ui.blit_text(s, ln, (x, y), 'small', U.SOFT)
            y += 24
        y += 4
    by = pane.bottom - 70
    ui.button(s, (x, by, w, 48), 'Sell %d  for %d' % (n, n * c['sell']), lambda: sell(g, cid), 'gold', font='smallb')
    if cid == 'corn':
        ui.button(s, (x, by - 56, w, 46), 'Make %d Sweet Corn bait' % CORN_BAIT, lambda: corn_to_bait(g), 'normal',
                  font='smallb')
    elif cid == 'catnip':
        ui.button(s, (x, by - 56, w, 46), 'Give some to Biscuit' if not catnip_today(g) else 'Biscuit had some today',
                  lambda: give_catnip(g), 'rose', enabled=not catnip_today(g), font='smallb')


_GROUND = {}


def _dock_ground(season):
    """The slope under the cabin (the dock's foreground), whichever spot you are at."""
    if season not in _GROUND:
        import art
        _GROUND[season] = art.make_foreground(season, 'dock')
    return _GROUND[season]


def _select(g, i):
    g.garden_sel = None if g.garden_sel == i else i
    g.audio.play('ui', 0.4)
