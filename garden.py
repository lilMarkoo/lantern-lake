"""The cabin garden: six raised beds on the slope under the cabin.

Plant seeds, water the beds once a day (rain and snow do it for you) and pick what grows. Crops sell, add an extra
serving to a matching dish in the kitchen, turn into crab-pot bait (sweetcorn) or make Biscuit very happy (catnip).
Junk fished out of the lake goes on the compost heap and comes back as plant food. Nothing ever dies: a bed that
wasn't watered simply waits a day.
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
# a fresh crop that goes with a dish adds one more serving when you cook it (kitchen.py)
GARNISH = {'fritters': ('dill',), 'chowder': ('corn', 'peas'), 'grilled': ('garlic', 'dill'),
           'fishpie': ('peas', 'carrot'), 'clam': ('tomato',), 'stew': ('kale', 'carrot', 'pumpkin'),
           'tart': ('strawberry',), 'feast': ('pumpkin', 'beet', 'radish')}
CORN_BAIT = 5                          # one cob makes this much Sweet Corn bait

# the beds on the slope under the cabin, in world pixels: (x, soil y, width)
BED_SPOTS = [(6, 252, 22), (32, 252, 22), (58, 252, 20), (10, 274, 22), (36, 274, 22), (62, 274, 22)]
AREA = pygame.Rect(2, 236, 92, 50)     # click here on the lake to open the garden
VIEW = pygame.Rect(0, 230, 100, 54)    # what the Garden tab shows, scaled up


def new():
    return {'beds': [None] * BEDS, 'open': START_OPEN, 'produce': {}, 'heap': 0, 'food': 0, 'grew': 0,
            'rain': 0}


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
    """Rain and snow water the beds for you."""
    if g.garden_fx > 0:
        g.garden_fx = max(0.0, g.garden_fx - dt)
    gd = g.garden
    if not raining(g) or g.mode != 'play':
        return
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
    n = c['n'] + (1 if b['fed'] else 0)
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
    hx, hy = 2 + ox, 292 + oy
    pygame.draw.ellipse(s, (88, 66, 46), (hx, hy - 4, 12, 6))
    for k, col in enumerate(((120, 100, 60), (96, 120, 70), (140, 110, 70))):
        s.set_at((hx + 3 + k * 3, hy - 4 + k % 2), col)
    s.fill((150, 112, 74), (hx - 1, hy - 1, 14, 2))
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
    else:
        d.ellipse(s, leaf, (2, 7, 12, 8))
        d.line(s, darken(leaf, 0.3), (8, 8), (8, 14))
        d.line(s, col, (5, 2), (5, 7), 2)
        d.line(s, col, (11, 3), (11, 7), 2)
    return pygame.transform.scale(s, (16 * scale, 16 * scale))


# ---------------------------------------------------------------- the Garden tab in the cabin
def draw_tab(g, s, rect):
    ui = g.ui
    gd = g.garden
    t = g.t
    # a close-up of the real beds
    view = pygame.Rect(rect.x + 30, rect.y + 90, VIEW.w * 6, VIEW.h * 6)
    small = pygame.Surface(VIEW.size)
    sky = lerp_c((150, 190, 214), (60, 70, 100), g.env.nf * 0.7)
    small.fill(sky)
    small.blit(_dock_ground(g.env.season), (0, 0), VIEW)
    sel = g.garden_sel
    draw_beds(small, g, t, 0, -VIEW.y, None)
    pygame.draw.rect(s, (120, 80, 54), view.inflate(16, 16), border_radius=12)
    s.blit(pygame.transform.scale(small, view.size), view)
    pygame.draw.rect(s, (150, 104, 70), view.inflate(8, 8), 3, border_radius=10)
    for i, (x, y, w) in enumerate(BED_SPOTS):
        r = pygame.Rect(view.x + (x - 3) * 6, view.y + (y - 19 - VIEW.y) * 6, (w + 6) * 6, 27 * 6)
        if i == sel:
            pygame.draw.rect(s, (255, 230, 140), r, 3, border_radius=8)
        elif r.collidepoint(ui.mouse):
            pygame.draw.rect(s, (255, 250, 230), r, 2, border_radius=8)
        ui.hotspot(r, lambda i=i: _select(g, i))
    # buttons under the view
    by = view.bottom + 18
    nd = len(thirsty(g))
    ui.button(s, (view.x, by, 190, 44), 'Water the beds', lambda: water_all(g), 'primary', enabled=nd > 0)
    nr = len(ready_beds(g))
    ui.button(s, (view.x + 202, by, 170, 44), 'Pick all', lambda: harvest_all(g), 'gold', enabled=nr > 0)
    if raining(g):
        note = 'The weather is watering the beds today.'
    elif nd:
        note = '%d bed%s need%s water.' % (nd, '' if nd == 1 else 's', 's' if nd == 1 else '')
    elif any(gd['beds'][:gd['open']]):
        note = 'All watered for today.'
    else:
        note = 'Click a bed to plant seeds.'
    ui.blit_text(s, note, (view.x + 386, by + 22), 'small', U.SOFT, 'midleft', maxw=view.right - view.x - 386)
    # the produce shelf
    py = by + 62
    ui.blit_text(s, 'From the garden', (view.x, py), 'h3', U.INK)
    items = [(cid, n) for cid, n in sorted(gd['produce'].items(), key=lambda kv: list(CROP_BY_ID).index(kv[0]))]
    if not items:
        ui.blit_text(s, 'Nothing picked yet.', (view.x + 200, py + 6), 'small', U.SOFT)
    tw = 148
    for k, (cid, n) in enumerate(items[:8]):
        c = CROP_BY_ID[cid]
        tr = pygame.Rect(view.x + (k % 4) * (tw + 4), py + 32 + (k // 4) * 54, tw, 50)
        ui.tile(s, tr, (250, 244, 228), (160, 190, 120))
        ic = crop_icon(cid, 2)
        s.blit(ic, ic.get_rect(center=(tr.x + 22, tr.centery)))
        ui.blit_text(s, c['name'], (tr.x + 42, tr.y + 5), 'tiny', U.INK, maxw=tw - 48)
        ui.blit_text(s, str(n), (tr.x + 34, tr.bottom - 6), 'smallb', U.INK, 'bottomright', outline=(250, 244, 228))
        if cid == 'corn':
            ui.button(s, (tr.x + 42, tr.y + 24, 48, 22), 'Bait', lambda: corn_to_bait(g), 'normal', font='tiny')
            ui.button(s, (tr.x + 94, tr.y + 24, 48, 22), 'Sell', lambda cid=cid: sell(g, cid), 'normal', font='tiny')
        elif cid == 'catnip':
            ui.button(s, (tr.x + 42, tr.y + 24, 48, 22), 'Cat', lambda: give_catnip(g), 'rose', font='tiny',
                      enabled=not catnip_today(g))
            ui.button(s, (tr.x + 94, tr.y + 24, 48, 22), 'Sell', lambda cid=cid: sell(g, cid), 'normal', font='tiny')
        else:
            ui.button(s, (tr.x + 42, tr.y + 24, 100, 22), 'Sell  %d' % (n * c['sell']), lambda cid=cid: sell(g, cid),
                      'normal', font='tiny')
    if len(items) > 8:
        ui.blit_text(s, '+%d more' % (len(items) - 8), (view.right, py + 6), 'small', U.SOFT, 'topright')
    # the right column: the chosen bed
    x0 = view.right + 34
    cw = rect.right - 30 - x0
    y = rect.y + 92
    if sel is None or sel >= BEDS:
        ui.blit_text(s, 'Your garden', (x0, y), 'h3', U.INK)
        lines = ['Click a bed in the picture to plant,', 'feed or pick it.', '',
                 'Water once a day and every bed', 'grows a little overnight. Rain', 'and snow water them for you.', '',
                 'Fresh crops add a serving to the', 'dish they go with in the kitchen.']
        for k, ln in enumerate(lines):
            ui.blit_text(s, ln, (x0, y + 40 + k * 24), 'small', U.SOFT)
    elif sel >= gd['open']:
        price = BED_PRICES[gd['open'] - START_OPEN]
        ui.blit_text(s, 'An empty patch', (x0, y), 'h3', U.INK)
        ui.blit_text(s, 'Dig it over and edge it with boards', (x0, y + 40), 'small', U.SOFT, maxw=cw)
        ui.blit_text(s, 'to make another bed.', (x0, y + 62), 'small', U.SOFT, maxw=cw)
        if sel == gd['open']:
            ui.button(s, (x0, y + 100, 240, 46), 'Dig it: %d coins' % price, lambda: open_bed(g), 'primary',
                      enabled=g.coins >= price)
        else:
            ui.blit_text(s, 'Dig the beds in order.', (x0, y + 110), 'smallb', U.SOFT)
    else:
        b = gd['beds'][sel]
        if b is None:
            sea = g.season_of(g.day)
            ui.blit_text(s, 'Plant something', (x0, y), 'h3', U.INK)
            ui.blit_text(s, '%s seeds and herbs' % SEASON_NAMES[sea], (x0, y + 32), 'small', U.SOFT)
            for k, c in enumerate(seeds_now(g)):
                r = pygame.Rect(x0, y + 60 + k * 62, cw, 56)
                ui.tile(s, r, (250, 244, 228), (196, 170, 140))
                ic = crop_icon(c['id'], 2)
                s.blit(ic, ic.get_rect(center=(r.x + 26, r.centery)))
                ui.blit_text(s, c['name'], (r.x + 52, r.y + 6), 'smallb', U.INK, maxw=cw - 150)
                rg = ', again every %d' % c['regrow'] if c['regrow'] else ''
                ui.blit_text(s, '%d days%s' % (c['days'], rg), (r.x + 52, r.y + 30), 'tiny', U.SOFT,
                             maxw=cw - 150)
                ui.button(s, (r.right - 92, r.y + 10, 82, 36), '%d' % c['seed'], lambda c=c: plant(g, sel, c['id']),
                          'primary', enabled=g.coins >= c['seed'], font='smallb')
        else:
            c = crop(b)
            st = stage(b)
            ic = crop_icon(c['id'], 4)
            s.blit(ic, (x0, y))
            ui.blit_text(s, c['name'], (x0 + 76, y + 4), 'h3', U.INK, maxw=cw - 76)
            words = ('Just planted', 'Sprouting', 'Growing', 'Nearly there', 'Ready to pick!')[st]
            ui.blit_text(s, words, (x0 + 76, y + 36), 'smallb', (90, 140, 70) if st == 4 else U.SOFT)
            # growth bar
            bar = pygame.Rect(x0, y + 82, cw, 14)
            pygame.draw.rect(s, (226, 214, 196), bar, border_radius=7)
            pygame.draw.rect(s, (140, 190, 100), (bar.x, bar.y, int(bar.w * min(1, b['age'] / c['days'])), bar.h),
                             border_radius=7)
            ui.blit_text(s, 'Day %d of %d' % (min(b['age'], c['days']), c['days']), (x0, y + 104), 'small', U.SOFT)
            if st < 4:
                ui.blit_text(s, 'Watered today' if wet(g, b) else 'Needs water today',
                             (x0 + cw, y + 104), 'small', (90, 130, 170) if wet(g, b) else (190, 120, 90), 'topright')
            u = uses(c['id'])
            if u:
                ui.blit_text(s, u, (x0, y + 134), 'small', (90, 130, 80), maxw=cw)
            yb = y + 172
            if st == 4:
                ui.button(s, (x0, yb, 200, 46), 'Pick', lambda: harvest(g, sel), 'gold')
            else:
                ui.button(s, (x0, yb, 200, 46), 'Plant food (%d)' % gd['food'], lambda: feed(g, sel), 'normal',
                          enabled=gd['food'] > 0 and not b['fed'])
                if b['fed']:
                    ui.blit_text(s, 'Fed: one extra crop', (x0, yb + 52), 'tiny', (90, 130, 80))
            ui.button(s, (x0 + 212, yb, cw - 212, 46), 'Pull up', lambda: pull_up(g, sel), 'rose', font='smallb')
    # compost, bottom right
    cy = rect.bottom - 132
    ui.blit_text(s, 'Compost heap', (x0, cy), 'h3', U.INK)
    ui.blit_text(s, 'Junk from the lake: %d of %d for one plant food' % (gd['heap'], JUNK_PER_FOOD), (x0, cy + 32),
                 'tiny', U.SOFT, maxw=cw)
    ui.blit_text(s, 'Plant food: %d' % gd['food'], (x0, cy + 54), 'smallb', U.INK)
    nj = len(junk_in_basket(g))
    ui.button(s, (x0, cy + 80, cw, 40), 'Add junk from the basket (%d)' % nj, lambda: compost(g), 'normal',
              enabled=nj > 0, font='smallb')
    if gd['open'] < BEDS and sel is None:
        ui.blit_text(s, 'More beds: click a staked patch', (x0, cy - 34), 'tiny', U.SOFT, maxw=cw)


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
