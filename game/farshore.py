"""The Far Shore (0.4.0): the woods behind the old landing across the lake.

Once the landing by the dock is restored (shore.py), clicking it rows you across. Walk the trail like the harbour
quay: wild finds to gather (they go in the garden basket, sell, and add a serving to the dishes they suit), the
ranger Bramwell's hut with a favour a day, a campsite with a tent to sleep in and a fire to cook at, and the Hollow
Pool, where fish of its own rise after dark. Bramwell's old Hollow Lantern hangs dark in the great oak at the end of
the trail; mend it with him and light it, and the Hollow King starts to bite.

Runs under Game.overlay 'farshore' with Game.aqscene, like the harbour. State is Game.far (saved).
"""
import math
import random

import pygame

import art
import look as looks
import minigame
import town as T
import ui as U
from art import W, H, lerp_c, darken, lighten, add_glow
from data import FISH_BY_ID, HOLLOW_FISH

FS_W = 1600
FLOOR = T.GROUND
WALK = 62.0
JETTY_X = 30
HUT = (360, 460)
BRAM_HOME = 486
TENT_X = 700
FIRE_X = 790
POOL = pygame.Rect(984, 314, 236, 40)
POOL_X = 1100
OAK_X = 1440
LANTERN_XY = (1508, FLOOR - 116)
ZONES = ((110, 330), (520, 650), (880, 960), (1250, 1400), (1540, 1585))
NIGHT = (19 * 60 + 30, 5 * 60)              # the Hollow Pool's fish rise from 7:30 PM to 5 AM
HEADLESS = False                             # set by main at start-up, with its clock formatter
fmt_clock = str
BRAM = dict(name='Bramwell', title='Ranger of the Far Shore', shirt=(92, 112, 70), hair=(206, 202, 194),
            hat='bucket')
LANTERN_TASKS = [
    dict(id='frame', name='Mend the frame', need='6 wild finds', forage=6,
         say='Six good finds from the trail. I weave the frame from the stems, you see.'),
    dict(id='wick', name='A new wick', need='a Mossback Tench', fish='mossback',
         say='The old wick came from a mossback\'s whisker. Odd, but it burned for forty years.'),
    dict(id='glow', name='Something that glows', need='a Wisp Eel', fish='wispeel',
         say='A wisp eel, to hold the light while the wick catches. Bring it on a dry night.'),
]
LEAFMOULD = 'leafmould'


# ---------------------------------------------------------------- state
def new():
    return dict(told=False, visits=0, finds=[], finds_day=0, picked=0, camp=0, camped=0, supper=0, tea=0,
                bram=0, met=False, req=None, lantern=[], lit=False, caught={})


def clean(d):
    base = new()
    if not isinstance(d, dict):
        return base
    for k, v in base.items():
        if k not in d or type(d[k]) is not type(v) and not (v is None and isinstance(d[k], dict)):
            continue
        base[k] = d[k]
    import garden
    base['finds'] = [f for f in base['finds'] if isinstance(f, dict) and isinstance(f.get('x'), (int, float))
                     and (f.get('id') in garden.FORAGE_BY_ID or f.get('id') == LEAFMOULD)]
    base['lantern'] = [t for t in base['lantern'] if t in {x['id'] for x in LANTERN_TASKS}]
    base['caught'] = {k: int(v) for k, v in base['caught'].items() if k in FISH_BY_ID}
    r = base['req']
    if not (isinstance(r, dict) and r.get('kind') in ('forage', 'fish') and isinstance(r.get('n'), int)):
        base['req'] = None
    return base


def unlocked(g):
    import shore
    return shore.done(g, 'landing')


def night(g):
    m = g.minute
    return m >= NIGHT[0] or m < NIGHT[1]


def bram_where(g):
    """'hut' by day, 'fire' in the evening, None while he sleeps."""
    m = g.minute
    if 7 * 60 <= m < 21 * 60:
        return 'hut'
    if m >= 21 * 60 or m < 60:
        return 'fire'
    return None


def bram_x(g):
    return {'hut': BRAM_HOME, 'fire': FIRE_X + 26}.get(bram_where(g))


def hearts(g):
    return min(5, g.far['bram'] // 20)


def fire_lit(g):
    m = g.minute
    return m >= 17 * 60 or m < 3 * 60 or g.far['supper'] == g.day and m >= 12 * 60


def supper_now(g):
    return g.far['supper'] == g.day or (g.far['supper'] == g.day - 1 and g.minute < NIGHT[1])


# ---------------------------------------------------------------- the morning
def _spawn(g, extra=0):
    import garden
    st = g.far
    rng = random.Random(g.day * 4513 + 7)
    sea = g.season_of(g.day)
    pool = [f['id'] for f in garden.FORAGE if f['season'] == sea]
    finds = []
    for i in range(rng.randint(5, 7) + extra):
        a, b = ZONES[i % len(ZONES)]
        x = rng.randint(a, b)
        if any(abs(x - f['x']) < 14 for f in finds):
            continue
        finds.append(dict(x=x, id=LEAFMOULD if rng.random() < 0.18 else rng.choice(pool)))
    st['finds'] = finds
    st['finds_day'] = g.day


def _new_request(g):
    import garden
    st = g.far
    rng = random.Random(g.day * 911 + 3)
    sea = g.season_of(g.day)
    if rng.random() < 0.5:
        fid = rng.choice([f['id'] for f in garden.FORAGE if f['season'] == sea])
        st['req'] = dict(day=g.day, kind='forage', id=fid, n=rng.randint(2, 3), reward=rng.randrange(50, 110, 10),
                         done=False)
    else:
        pool = ['mothfin', 'moonperch'] + (['mossback'] if st['bram'] >= 30 else [])
        st['req'] = dict(day=g.day, kind='fish', id=rng.choice(pool), n=1, reward=rng.randrange(90, 160, 10),
                         done=False)


def morning(g):
    if not unlocked(g):
        return
    st = g.far
    if not st['told']:
        st['told'] = True
        g.queue.append(('letter', ('Hello over there,', (
            "I've been watching you mend the old landing from my side of the water. Nobody has tied a boat up "
            "there since my knees gave out.\n"
            "There's a trail through the woods, a fire that's always laid, and a pool in the hollow where strange "
            "fish come up after dark. Click the landing by your dock and row on over. I'll put the kettle on."),
            '- Bramwell, ranger of the Far Shore')))
    camped = st['camp'] == g.day - 1
    _spawn(g, 2 if camped else 0)
    _new_request(g)
    if camped:
        g.luck = min(3.0, g.luck + 0.8)
        g.toast('You wake in the tent to birdsong and row home at first light. You feel lucky.', (110, 150, 100))


# ---------------------------------------------------------------- doing things
def go(g):
    """Row across from the dock to the Far Shore."""
    if not unlocked(g):
        return False
    if getattr(g, 'solo', None) or g.net.online:
        g.toast('The Far Shore is a quiet place. Row over when you are playing on your own.', (110, 130, 120))
        return False
    if g.place != 'lake' or g.spot != 'dock':
        g.toast('Row back to your dock first: the landing is just across from it.', (110, 130, 120))
        return False
    if g.fishing.state not in ('idle', 'waiting', 'charging'):
        g.toast('Finish what is on the line first.')
        return False
    g.minute = min(1439.0, g.minute + 15)
    enter(g)
    g.fade, g.fade_dir = 1.0, -1
    return True


def enter(g):
    st = g.far
    if st['finds_day'] != g.day:
        _spawn(g)
    if not st['req'] or st['req'].get('day') != g.day:
        _new_request(g)
    g.aqscene = FarShore(g)
    g.overlay = 'farshore'
    g.release_holds()
    g.fishing.reset()
    g.audio.play('creak', 0.4)
    st['visits'] += 1
    if st['visits'] == 1:
        g.toast('The Far Shore. Walk with A and D, and press E to pick things up or talk.', (110, 150, 100))


def pick(g, item):
    import garden
    st = g.far
    if item not in st['finds']:
        return False
    st['finds'].remove(item)
    st['picked'] += 1
    if item['id'] == LEAFMOULD:
        g.garden['food'] += 1
        g.toast('A sack of leaf mould: +1 plant food for the garden.', (120, 100, 70))
    else:
        f = garden.FORAGE_BY_ID[item['id']]
        g.garden['produce'][f['id']] = g.garden['produce'].get(f['id'], 0) + 1
        use = garden.uses(f['id'])
        g.toast('%s for the basket.%s' % (f['name'], ('  (' + use + ')') if use else ''), (110, 150, 100))
    g.audio.play('plip', 0.5)
    g.check_badges()
    return True


def wild_count(g):
    import garden
    return sum(n for k, n in g.garden['produce'].items() if k in garden.FORAGE_BY_ID)


def _take_wild(g, n, only=None):
    """Use n wild finds from the basket (the ones you have most of first)."""
    import garden
    pr = g.garden['produce']
    for _ in range(n):
        ids = [k for k in pr if k in garden.FORAGE_BY_ID and pr[k] > 0 and (only is None or k in only)]
        if not ids:
            return False
        k = max(ids, key=lambda k: pr[k])
        pr[k] -= 1
        if pr[k] <= 0:
            del pr[k]
    return True


def _basket_fish(g, fid):
    for b in g.basket:
        if b['id'] == fid:
            return b
    return None


def can_give(g):
    r = g.far['req']
    if not r or r['done']:
        return False
    if r['kind'] == 'forage':
        return g.garden['produce'].get(r['id'], 0) >= r['n']
    return _basket_fish(g, r['id']) is not None


def give_req(g):
    st = g.far
    r = st['req']
    if not can_give(g):
        return False
    if r['kind'] == 'forage':
        _take_wild(g, r['n'], (r['id'],))
    else:
        g.basket.remove(_basket_fish(g, r['id']))
    r['done'] = True
    g.coins += r['reward']
    st['bram'] += 8
    g.stats['requests'] = g.stats.get('requests', 0) + 1
    g.audio.play('coin', 0.6)
    g.toast('Bramwell is delighted. +%d coins' % r['reward'], (200, 160, 70))
    g.save()
    return True


def task_ready(g, tid):
    st = g.far
    if tid in st['lantern'] or not st['met']:
        return False
    t = next(x for x in LANTERN_TASKS if x['id'] == tid)
    if t.get('forage'):
        return wild_count(g) >= t['forage']
    return _basket_fish(g, t['fish']) is not None


def give_task(g, tid):
    st = g.far
    if not task_ready(g, tid):
        return False
    t = next(x for x in LANTERN_TASKS if x['id'] == tid)
    if t.get('forage'):
        _take_wild(g, t['forage'])
    else:
        g.basket.remove(_basket_fish(g, t['fish']))
    st['lantern'].append(tid)
    st['bram'] += 10
    g.audio.play('jingle2', 0.6)
    left = len(LANTERN_TASKS) - len(st['lantern'])
    g.toast('%s: done!%s' % (t['name'], '  %d to go.' % left if left else
                              '  Light the lantern in the old oak after dark.'), (220, 180, 90))
    g.save()
    return True


def can_light(g):
    st = g.far
    return not st['lit'] and len(st['lantern']) == len(LANTERN_TASKS) and night(g)


def light_it(g):
    st = g.far
    if not can_light(g):
        return False
    st['lit'] = True
    st['bram'] += 20
    g.audio.play('jingle4', 0.8)
    g.toast('The Hollow Lantern glows again, and the fireflies come to it from all over the woods.', (240, 210, 120))
    g.queue.append(('letter', ('My dear friend,', (
        "Forty years that lantern hung dark, and tonight I sat by the fire and watched it shine. Thank you.\n"
        "Now listen: something big turned over in the pool when the light came on. Whiskers like mine and eyes "
        "like two lamps. The Hollow King has come back to see what all the fuss is about. Good luck with him."),
        '- Bramwell')))
    g.check_badges()
    g.save()
    return True


def cook_supper(g):
    """At the campfire: a fish from your basket and a wild find, roasted. Tonight's bites come quicker."""
    st = g.far
    fish = next((b for b in g.basket if not FISH_BY_ID[b['id']].get('junk')), None)
    if st['supper'] == g.day or fish is None or wild_count(g) < 1:
        return False
    g.basket.remove(fish)
    _take_wild(g, 1)
    st['supper'] = g.day
    g.audio.play('sizzle', 0.6) if 'sizzle' in getattr(g.audio, 'sounds', {}) else g.audio.play('plop', 0.5)
    g.toast('You roast the %s over the fire with something wild. Delicious. The pool feels lively tonight.'
            % FISH_BY_ID[fish['id']]['name'], (230, 150, 90))
    g.save()
    return True


TEA = ('violet', 'chamomile', 'ramsons', 'pinetip', 'sorrel')


def brew_tea(g):
    import garden
    st = g.far
    have = sum(g.garden['produce'].get(k, 0) for k in TEA)
    if st['tea'] == g.day or have < 2:
        return False
    _take_wild(g, 2, TEA)
    st['tea'] = g.day
    g.luck = min(3.0, g.luck + 0.5)
    g.audio.play('jingle1', 0.5)
    g.toast("Forager's tea in a tin cup, steam curling into the trees. You feel a little luckier.", (150, 170, 110))
    g.save()
    return True


def camp_sleep(g):
    m = g.minute
    if not (m >= 18 * 60 or m < 300):
        g.toast('Too early for bed. The tent is for after 6 PM.')
        return False
    st = g.far
    st['camp'] = g.day if m >= 300 else g.day - 1
    st['camped'] += 1
    g.check_badges()
    g.rest_phase = 'out'
    g.fishing.reset()
    g.release_holds()
    return True


def badge_cond(g):
    st = g.far
    return {'forager': st['picked'] >= 30, 'camper': st['camped'] >= 1, 'hollowlight': st['lit']}


def register(g, spec, size):
    """A fish from the Hollow Pool: into the journal and the basket (the catch card is drawn in the scene)."""
    import goals as goalmod
    lo, hi = spec['size']
    k = (size - lo) / max(0.01, hi - lo)
    price = int(round(spec['price'] * (0.8 + 0.6 * k)))
    entry = g.journal.get(spec['id'])
    new = entry is None
    record = entry is not None and size > entry.get('best', 0)
    if entry is None:
        entry = g.journal[spec['id']] = {'count': 0, 'best': 0}
    entry['count'] += 1
    entry['best'] = max(entry['best'], size)
    g.total += 1
    g.note('catch', fish=spec['id'], new=new, record=record)
    g.stats['caught_day'] = g.day
    g.stats['night'] += 1
    goalmod.on_catch(g, spec)
    st = g.far
    st['caught'][spec['id']] = st['caught'].get(spec['id'], 0) + 1
    g.basket.append(dict(id=spec['id'], size=size, price=price))
    g.check_badges()
    g.save()
    return dict(spec=spec, size=size, price=price, new=new, record=record)


def bite_odds(g):
    rain = g.weather in ('rain', 'snow', 'storm')
    w = {'mothfin': 40, 'moonperch': 30, 'mossback': 15, 'wispeel': 0 if rain else 12,
         'hollowking': 7 if g.far['lit'] else 0}
    return [(FISH_BY_ID[k], v) for k, v in w.items() if v > 0]


def chat(g):
    st = g.far
    rng = random.Random(g.day * 31 + int(g.minute // 90))
    if not st['met']:
        return ("You came! I'm Bramwell. See the lantern up in the old oak? Dark for forty years. "
                "Help me mend it?")
    sea = g.season_of(g.day)
    lines = [
        ['The wild garlic is up. You can smell it from the landing.', 'Morels hide under the ash trees. Look low.'],
        ['Bilberries stain your fingers for a week. Worth it.', 'Hot one. The pool stays cool though.'],
        ['Chanterelles! Golden as a lantern, and twice as tasty.', 'The hazels drop their nuts on my roof at night. '
         'Like being shot at by squirrels.'],
        ['Rosehips after the frost are the sweetest.', 'Pine tips make a fine tea when your toes are cold.'],
    ][sea] + ['The fish in the pool only come up after dark. Something about the stars.',
              'Sleep in the tent sometime. Best sleep you will ever have.',
              'A supper cooked over the fire puts the fish in a good mood. Or so I tell myself.']
    if st['lit']:
        lines.append('I sit by the fire and look at that lantern every night. Thank you again.')
    if bram_where(g) == 'fire':
        lines.append('Pull up a log. The fire is the best part of the day.')
    return rng.choice(lines)


# ---------------------------------------------------------------- static art
_STATIC = {}
_BACK = {}

CANOPY = {0: [(110, 168, 88), (130, 184, 98), (92, 150, 76)], 1: [(70, 128, 60), (84, 142, 66), (60, 112, 54)],
          2: [(206, 120, 52), (226, 168, 64), (176, 76, 44), (150, 130, 60)], 3: [(120, 110, 100), (110, 100, 92)]}
PINE = {0: (52, 96, 72), 1: (46, 88, 64), 2: (52, 90, 70), 3: (60, 92, 80)}


def _broadleaf(s, x, top, season, rng):
    trunk = (92, 70, 54)
    s.fill(darken(trunk, 0.25), (x - 3, top + 30, 7, FLOOR - top - 28))
    s.fill(trunk, (x - 3, top + 30, 5, FLOOR - top - 28))
    for k in range(3):                                     # roots
        s.fill(trunk, (x - 5 + k * 4, FLOOR - 4, 2, 4))
    cols = CANOPY[season]
    if season == 3:                                        # bare branches with snow on them
        for k in range(7):
            a = -math.pi / 2 + (k - 3) * 0.32
            L = rng.randint(18, 30)
            ex, ey = x + math.cos(a) * L, top + 34 + math.sin(a) * L
            pygame.draw.line(s, trunk, (x, top + 36), (ex, ey), 2)
            pygame.draw.line(s, (240, 244, 250), (ex - 2, ey - 1), (ex + 2, ey - 1))
        return
    for k in range(9):
        cx = x + rng.randint(-22, 22)
        cy = top + rng.randint(4, 34)
        r = rng.randint(10, 16)
        c = rng.choice(cols)
        pygame.draw.circle(s, darken(c, 0.18), (cx, cy + 2), r)
        pygame.draw.circle(s, c, (cx, cy), r)
        pygame.draw.circle(s, lighten(c, 0.12), (cx - r // 3, cy - r // 3), r // 2)
    if season == 0:
        for _ in range(26):                                # blossom
            s.set_at((x + rng.randint(-26, 26), top + rng.randint(-6, 40)), rng.choice([(250, 210, 226),
                                                                                       (255, 244, 250)]))


def _pine(s, x, top, season, rng):
    c = PINE[season]
    s.fill((80, 60, 48), (x - 2, FLOOR - 26, 4, 26))
    h = FLOOR - 20 - top
    for k in range(5):
        y = top + k * h // 5
        w = 8 + k * 6
        pygame.draw.polygon(s, darken(c, 0.15 + 0.03 * k), [(x, y - 4), (x - w, y + h // 4 + 2), (x + w, y + h // 4 + 2)])
        pygame.draw.polygon(s, c, [(x, y - 4), (x - w + 2, y + h // 4), (x + w - 4, y + h // 4)])
        if season == 3:
            pygame.draw.line(s, (244, 248, 252), (x - w + 2, y + h // 4), (x + w - 4, y + h // 4))


def build_back(season):
    if season in _BACK:
        return _BACK[season]
    w = W + FS_W // 3 + 10
    s = pygame.Surface((w, H), pygame.SRCALPHA)
    rng = random.Random(51 + season)
    far = {0: (120, 150, 130), 1: (100, 136, 110), 2: (150, 130, 100), 3: (196, 204, 216)}[season]
    near = {0: (92, 130, 96), 1: (76, 116, 82), 2: (140, 104, 70), 3: (170, 180, 194)}[season]
    for x in range(w):                                       # two rows of wooded hills
        y1 = 170 + int(16 * math.sin(x * 0.011) + 9 * math.sin(x * 0.031 + 1))
        s.fill(far, (x, y1, 1, H - y1))
        if rng.random() < 0.3:
            s.fill(darken(far, 0.08), (x, y1 - 2, 1, 2))
    for x in range(0, w, 7):                                # treetops along the nearer ridge
        y2 = 200 + int(14 * math.sin(x * 0.017 + 2) + 6 * math.sin(x * 0.05))
        r = rng.randint(6, 10)
        pygame.draw.circle(s, near, (x, y2), r)
        s.fill(near, (x - r, y2, r * 2, H - y2))
    _BACK[season] = s
    return s


def build(season):
    """The near layer: trees behind the trail, the trail, the hut, the camp, the pool's banks and the old oak."""
    if season in _STATIC:
        return _STATIC[season]
    s = pygame.Surface((FS_W, H), pygame.SRCALPHA)
    rng = random.Random(97 + season)
    # the woods behind the trail
    for x in range(-10, FS_W + 20, 46):
        xx = x + rng.randint(-10, 10)
        if HUT[0] - 30 < xx < HUT[1] + 30 or OAK_X - 70 < xx < OAK_X + 110:
            continue
        top = FLOOR - rng.randint(120, 170)
        (_pine if rng.random() < 0.35 else _broadleaf)(s, xx, top, season, rng)
    grass = art.GRASS[season]
    gd = art.GRASS_D[season]
    # undergrowth along the back of the trail
    for x in range(0, FS_W, 3):
        h = rng.randint(3, 9)
        c = lerp_c(gd, grass, rng.random())
        s.fill(c, (x, FLOOR - h - 2, 3, h + 2))
        if season in (0, 1) and rng.random() < 0.05:
            s.set_at((x + 1, FLOOR - h - 3), rng.choice([(250, 240, 120), (250, 180, 200), (255, 255, 255)]))
    # the ground: grass to the bottom, the trail across it
    for y in range(FLOOR - 2, H):
        for x in range(0, FS_W, 2):
            r = rng.random()
            c = gd if r < 0.12 else lighten(grass, 0.06) if r < 0.2 else grass
            s.fill(c, (x, y, 2, 1))
    path = {0: (170, 140, 104), 1: (180, 150, 108), 2: (160, 126, 92), 3: (226, 228, 236)}[season]
    for x in range(0, FS_W):
        top = FLOOR - 3 + int(1.5 * math.sin(x * 0.05))
        bot = FLOOR + 7 + int(2 * math.sin(x * 0.03 + 1))
        for y in range(top, bot):
            s.set_at((x, y), path if rng.random() > 0.08 else darken(path, 0.12))
    # the lake on the left, under the old landing
    for y in range(FLOOR + 6, H):
        for x in range(0, 58 + (y - FLOOR) // 3):
            s.set_at((x, y), lerp_c((70, 120, 140), (50, 96, 118), (y - FLOOR) / 60))
    wood, dwood = (120, 92, 66), (84, 62, 46)
    s.fill(dwood, (0, FLOOR + 2, 64, 4))                      # the landing's planks and posts
    for x in range(0, 64, 6):
        s.fill(wood, (x, FLOOR + 1, 5, 3))
    for px in (6, 30, 56):
        s.fill(dwood, (px, FLOOR + 5, 3, 18))
    # the ranger's hut: logs, a porch, a lantern hook and a chimney
    hx0, hx1 = HUT
    log = (138, 100, 70)
    for y in range(FLOOR - 50, FLOOR, 5):
        s.fill(darken(log, 0.2), (hx0, y + 3, hx1 - hx0, 2))
        s.fill(log, (hx0, y, hx1 - hx0, 3))
        pygame.draw.circle(s, (170, 130, 92), (hx0, y + 2), 2)
        pygame.draw.circle(s, (170, 130, 92), (hx1, y + 2), 2)
    roof = (96, 74, 64) if season != 3 else (240, 244, 250)
    pygame.draw.polygon(s, darken(roof, 0.2), [(hx0 - 12, FLOOR - 48), ((hx0 + hx1) // 2, FLOOR - 86),
                                               (hx1 + 12, FLOOR - 48)])
    pygame.draw.polygon(s, roof, [(hx0 - 10, FLOOR - 50), ((hx0 + hx1) // 2, FLOOR - 84), (hx1 + 10, FLOOR - 50)])
    s.fill((110, 100, 96), (hx1 - 26, FLOOR - 92, 10, 26))
    s.fill((84, 60, 46), (hx0 + 18, FLOOR - 34, 14, 34))       # door
    s.set_at((hx0 + 29, FLOOR - 18), (230, 200, 120))
    s.fill((60, 46, 40), (hx0 + 50, FLOOR - 38, 18, 14))       # window (lit at night: _lights)
    s.fill((150, 120, 90), (hx0 + 58, FLOOR - 38, 2, 14))
    s.fill((150, 120, 90), (hx0 + 50, FLOOR - 32, 18, 2))
    s.fill((120, 90, 64), (hx1 + 4, FLOOR - 14, 22, 3))        # a bench
    s.fill((96, 72, 54), (hx1 + 6, FLOOR - 11, 2, 11))
    s.fill((96, 72, 54), (hx1 + 22, FLOOR - 11, 2, 11))
    T._sign(s, hx0 - 22, FLOOR - 30, 'RANGER', (236, 226, 200), (90, 112, 70), 40)
    # the campsite: a canvas tent and logs round a ring of stones
    tc = (196, 170, 120) if season != 3 else (206, 186, 140)
    pygame.draw.polygon(s, darken(tc, 0.25), [(TENT_X - 30, FLOOR), (TENT_X, FLOOR - 40), (TENT_X + 30, FLOOR)])
    pygame.draw.polygon(s, tc, [(TENT_X - 28, FLOOR), (TENT_X, FLOOR - 38), (TENT_X + 18, FLOOR)])
    pygame.draw.polygon(s, (70, 56, 44), [(TENT_X - 8, FLOOR), (TENT_X, FLOOR - 22), (TENT_X + 8, FLOOR)])
    pygame.draw.line(s, (90, 70, 50), (TENT_X, FLOOR - 40), (TENT_X, FLOOR - 46))
    if season == 3:
        pygame.draw.line(s, (250, 252, 255), (TENT_X - 26, FLOOR - 2), (TENT_X - 1, FLOOR - 37))
    for lx in (FIRE_X - 34, FIRE_X + 22):
        s.fill((110, 80, 58), (lx, FLOOR - 4, 14, 5))
        pygame.draw.circle(s, (170, 130, 90), (lx, FLOOR - 2), 2)
    for k in range(8):
        a = k / 8 * math.tau
        x = FIRE_X + int(math.cos(a) * 9)
        y = FLOOR + 1 + int(math.sin(a) * 3)
        s.fill((140, 134, 126), (x - 1, y - 1, 3, 2))
    # the pool's banks: stones and reeds round a hole the water is drawn into
    pygame.draw.ellipse(s, (0, 0, 0, 0), POOL)
    pygame.draw.ellipse(s, (96, 82, 66, 255), POOL.inflate(8, 6), 3)
    for k in range(30):
        a = k / 30 * math.tau
        x = POOL.centerx + int(math.cos(a) * (POOL.w / 2 + 3))
        y = POOL.centery + int(math.sin(a) * (POOL.h / 2 + 2))
        c = lerp_c((150, 146, 140), (110, 106, 100), rng.random())
        s.fill(darken(c, 0.3), (x - 2, y, 5, 2))
        s.fill(c, (x - 2, y - 1, 4, 2))
    reed = (92, 134, 70) if season != 3 else (170, 160, 130)
    for k in range(18):
        x = POOL.x + 6 + k * 3 if k < 9 else POOL.right - 30 + (k - 9) * 3
        y = POOL.y + (8 if k < 9 else 10)
        top = y - rng.randint(10, 18)
        pygame.draw.line(s, reed if k % 2 else darken(reed, 0.15), (x, y), (x + rng.randint(-1, 1), top))
        if season in (1, 2) and k % 3 == 0:
            s.fill((116, 80, 54), (x, top - 1, 1, 3))
    s.fill((150, 140, 130), (POOL_X - 6, FLOOR + 6, 14, 3))     # a flat stone to fish from
    # the great oak and its branch, with the hook the lantern hangs from
    bark = (84, 66, 54)
    for y in range(FLOOR - 150, FLOOR + 2):
        w = 18 + max(0, y - (FLOOR - 30)) // 2
        s.fill(darken(bark, 0.2), (OAK_X - w // 2, y, w, 1))
        s.fill(bark, (OAK_X - w // 2 + 2, y, w - 6, 1))
    for k in range(6):
        s.fill(darken(bark, 0.3), (OAK_X - 6 + k * 3, FLOOR - 140 + k * 17, 1, 12))
    pygame.draw.line(s, bark, (OAK_X + 4, FLOOR - 130), (LANTERN_XY[0] + 8, LANTERN_XY[1] - 16), 5)
    pygame.draw.line(s, bark, (OAK_X - 6, FLOOR - 140), (OAK_X - 60, FLOOR - 180), 5)
    cols = CANOPY[season]
    if season != 3:
        for k in range(16):
            cx = OAK_X + rng.randint(-60, 80)
            cy = FLOOR - 170 + rng.randint(-26, 22)
            r = rng.randint(14, 22)
            c = rng.choice(cols)
            pygame.draw.circle(s, darken(c, 0.2), (cx, cy + 3), r)
            pygame.draw.circle(s, c, (cx, cy), r)
    else:
        for k in range(10):
            a = -math.pi / 2 + (k - 5) * 0.28
            ex, ey = OAK_X + math.cos(a) * 60, FLOOR - 150 + math.sin(a) * 50
            pygame.draw.line(s, bark, (OAK_X, FLOOR - 150), (ex, ey), 3)
            pygame.draw.line(s, (244, 248, 252), (ex - 3, ey - 1), (ex + 3, ey - 1))
    pygame.draw.line(s, (60, 50, 44), (LANTERN_XY[0], LANTERN_XY[1] - 16), (LANTERN_XY[0], LANTERN_XY[1] - 8))
    _STATIC[season] = s
    return s


def find_icon(s, fid, x, y, t):
    """A wild find lying by the trail, at art scale (x, y is where it sits)."""
    import garden
    # a pale patch of trampled grass under it, and now and then a twinkle, so it catches your eye
    pygame.draw.ellipse(s, (226, 220, 186), (x - 6, y - 1, 13, 4))
    ph = (t * 0.45 + x * 0.013) % 1
    if ph < 0.18:
        k = 1 if ph < 0.06 or ph > 0.12 else 2
        c = (255, 250, 214)
        s.fill(c, (x - k, y - 11, k * 2 + 1, 1))
        s.fill(c, (x, y - 11 - k, 1, k * 2 + 1))
    if fid == LEAFMOULD:
        s.fill((110, 84, 60), (x - 3, y - 5, 7, 6))
        s.fill((140, 110, 80), (x - 2, y - 6, 5, 2))
        s.fill((80, 60, 44), (x - 3, y, 7, 1))
        return
    f = garden.FORAGE_BY_ID[fid]
    c, leaf = f['col'], f['leaf']
    look = f['look']
    if look == 'mushroom':
        s.fill(leaf, (x - 1, y - 3, 2, 3))
        s.fill(c, (x - 3, y - 5, 6, 2))
        s.set_at((x - 2, y - 6), lighten(c, 0.3))
        s.fill(c, (x + 3, y - 3, 3, 1))
        s.set_at((x + 4, y - 2), leaf)
    elif look == 'cluster':
        s.fill(leaf, (x - 4, y - 3, 8, 3))
        for dx, dy in ((-2, -4), (1, -4), (-1, -6), (2, -2)):
            s.set_at((x + dx, y + dy), c)
    elif look == 'nut':
        s.fill(leaf, (x - 3, y - 2, 6, 2))
        for dx in (-2, 1):
            s.fill(c, (x + dx, y - 4, 2, 2))
    elif look == 'flower':
        s.fill(leaf, (x, y - 4, 1, 4))
        s.fill(c, (x - 1, y - 6, 3, 2))
        s.fill(leaf, (x + 3, y - 3, 1, 3))
        s.set_at((x + 3, y - 4), c)
    else:                                                       # herbs and leaves
        for dx in (-2, 0, 2):
            s.fill(leaf, (x + dx, y - 4 + abs(dx) // 2, 1, 4 - abs(dx) // 2))
        s.set_at((x, y - 5), c)


# ---------------------------------------------------------------- the scene
class FarShore:
    kind = 'farshore'

    def __init__(self, g, rng=None):
        self.g = g
        self.rng = rng or random.Random()
        self.t = 0.0
        self.x = JETTY_X + 30.0
        self.face = 1
        self.step = 0.0
        self.target = None
        self.on_arrive = None
        self.scroll = 0.0
        self.panel = None               # None, or 'bram', 'fire', 'tent'
        self.line = ''
        self.fx = []
        self.done = False
        self.holds = set()
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self.smoke = []
        self.flies = []
        self.fs = None                  # fishing at the pool: dict(state, t, bx, by, spec, size, mg, card)
        self.glows = (art.glow(40, (255, 170, 90)), art.glow(14, (255, 210, 130)), art.glow(56, (255, 220, 150)),
                      art.glow(5, (220, 255, 150)))

    # ------------------------------------------------------------ what's in reach
    def nearest(self):
        g = self.g
        x = self.x
        if abs(x - JETTY_X) < 24:
            return ('jetty', None)
        for item in g.far['finds']:
            if abs(item['x'] - x) < 9:
                return ('item', item)
        bx = bram_x(g)
        if bx is not None and abs(bx - x) < 16:
            return ('bram', None)
        if abs(x - TENT_X) < 18:
            return ('tent', None)
        if abs(x - FIRE_X) < 20:
            return ('fire', None)
        if abs(x - POOL_X) < 40:
            return ('pool', None)
        if abs(x - OAK_X) < 30 or abs(x - LANTERN_XY[0]) < 16:
            return ('oak', None)
        if abs(x - (HUT[0] + 25)) < 14:
            return ('hut', None)
        return None

    def prompt(self):
        n = self.nearest()
        if not n or self.fs:
            return None
        kind, v = n
        g = self.g
        import garden
        if kind == 'jetty':
            return 'Row home to the dock'
        if kind == 'item':
            return 'Pick up the %s' % ('leaf mould' if v['id'] == LEAFMOULD else
                                       garden.FORAGE_BY_ID[v['id']]['name'].lower())
        if kind == 'bram':
            return 'Talk to Bramwell'
        if kind == 'tent':
            return 'Sleep in the tent' if (g.minute >= 18 * 60 or g.minute < 300) else 'The tent  (sleep after 6 PM)'
        if kind == 'fire':
            return 'The campfire'
        if kind == 'pool':
            return 'Fish the Hollow Pool' if night(g) else 'The Hollow Pool  (fish rise after 7:30 PM)'
        if kind == 'oak':
            st = g.far
            if st['lit']:
                return 'The Hollow Lantern'
            return 'Light the Hollow Lantern' if can_light(g) else 'A dark old lantern in the oak'
        if kind == 'hut':
            return "Bramwell's hut" + ('' if bram_where(g) == 'hut' else '  (he is out)')
        return None

    def interact(self):
        n = self.nearest()
        if not n:
            return
        kind, v = n
        g = self.g
        if kind == 'jetty':
            self.leave()
        elif kind == 'item':
            if pick(g, v):
                for _ in range(8):
                    self.fx.append([v['x'], FLOOR + 2, self.rng.uniform(-14, 14), self.rng.uniform(-30, -10), 0.7,
                                    (255, 240, 200)])
        elif kind == 'bram':
            self.open('bram')
        elif kind == 'tent':
            if g.minute >= 18 * 60 or g.minute < 300:
                self.open('tent')
            else:
                g.toast('A snug canvas tent with a bedroll inside. You can sleep here after 6 PM.', (150, 140, 110))
        elif kind == 'fire':
            self.open('fire')
        elif kind == 'pool':
            self.start_fishing()
        elif kind == 'oak':
            if light_it(g):
                self._burst(LANTERN_XY[0], LANTERN_XY[1], 40, (255, 236, 160))
            elif g.far['lit']:
                g.toast('The Hollow Lantern sways in the oak, and the fireflies keep it company.', (220, 190, 110))
            elif len(g.far['lantern']) == len(LANTERN_TASKS):
                g.toast('It is mended and ready. Come back after dark to light it.', (220, 190, 110))
            else:
                g.toast('An old iron lantern, cracked and cold. Bramwell will know its story.', (150, 140, 120))
        elif kind == 'hut':
            g.toast('A warm little hut that smells of pine smoke and old books.' if bram_where(g) == 'hut' else
                    'The door is on the latch. Bramwell is out.', (150, 140, 110))

    def open(self, panel):
        g = self.g
        self.panel = panel
        self.line = ''
        if panel == 'bram':
            self.line = chat(g)
            if not g.far['met']:
                g.far['met'] = True
                g.far['bram'] += 4
                g.save()
        g.release_holds()
        g.audio.play('page', 0.6)

    def close_panel(self):
        self.panel = None
        self.g.audio.play('page', 0.5)

    def leave(self):
        g = self.g
        if self.fs:
            self.fs = None
            g.bot_aim = None
        self.done = True
        g.aqscene = None
        if g.overlay == 'farshore':
            g.overlay = None
        g.minute = min(1439.0, g.minute + 15)
        g.release_holds()
        g.audio.play('plop', 0.4)
        g.fade, g.fade_dir = 1.0, -1
        g.toast('You row back across the lake to your dock.', (90, 140, 180))
        g.save()

    # ------------------------------------------------------------ fishing at the pool
    def start_fishing(self):
        g = self.g
        if not night(g):
            g.toast('The pool lies still and dark. Its fish only come up after 7:30 PM.', (110, 130, 150))
            return False
        self.x, self.face = float(POOL_X), 1
        bx = self.rng.uniform(POOL.x + 40, POOL.right - 40)
        wait = self.rng.uniform(4.0, 9.0) * g.boost('bite') * (0.6 if supper_now(g) else 1.0)
        self.fs = dict(state='wait', t=0.0, wait=wait, bx=bx, by=POOL.centery + self.rng.uniform(-6, 6))
        g.audio.play('cast', 0.5) if 'cast' in getattr(g.audio, 'sounds', {}) else g.audio.play('plop', 0.5)
        return True

    def hook(self):
        g = self.g
        fs = self.fs
        if not fs or fs['state'] != 'bite':
            return False
        pool = bite_odds(g)
        spec = self.rng.choices([p for p, _ in pool], [w for _, w in pool])[0]
        lo, hi = spec['size']
        k = min(1.0, self.rng.random() ** 1.6 + g.luck * 0.03 + g.boost('size') + (0.1 if supper_now(g) else 0))
        fs.update(state='fight', t=0.0, spec=spec, size=round(lo + (hi - lo) * k, 1),
                  mg=minigame.ReelGame(spec, g.rod_spec(), g.assist(), self.rng, k))
        g.use_bait()
        g.audio.play('hook', 0.7)
        return True

    def _fish_update(self, dt):
        g = self.g
        fs = self.fs
        fs['t'] += dt
        st = fs['state']
        if st == 'wait':
            if fs['t'] >= fs['wait']:
                fs['state'], fs['t'] = 'bite', 0.0
                g.audio.play('bite', 0.7) if 'bite' in getattr(g.audio, 'sounds', {}) else g.audio.play('warn', 0.5)
                self.rings_at(fs['bx'], fs['by'])
            elif self.rng.random() < dt * 0.4:
                self.rings_at(fs['bx'], fs['by'], small=True)
        elif st == 'bite':
            if fs['t'] > (1.8 if g.assist() else 1.2):
                self.pop('Too slow. It let go.')
                fs.update(state='wait', t=0.0, wait=self.rng.uniform(3.0, 7.0))
        elif st == 'fight':
            mg = fs['mg']
            aim, steer = g.reel_input()
            mg.update(dt, bool(self.holds), aim, steer)
            for ev in mg.events:
                if ev[0] in ('lunge', 'leap', 'splashdown'):
                    self.rings_at(fs['bx'], fs['by'])
                    g.audio.play('splash_small', 0.5)
                elif ev[0] == 'warn':
                    g.audio.play('warn', 0.5)
            mg.events.clear()
            if mg.result == 'caught':
                fs['card'] = register(g, fs['spec'], fs['size'])
                fs['state'], fs['t'] = 'landed', 0.0
                g.audio.play('splash', 0.7)
                g.audio.play('jingle%d' % max(1, min(5, fs['spec']['rarity'])), 0.6)
                self._burst(fs['bx'], fs['by'], 18, (220, 240, 255))
                self.holds.clear()
                g.bot_aim = None
            elif mg.result in ('snap', 'escape'):
                self.pop('Snap! The line broke.' if mg.result == 'snap' else 'It slipped away into the dark.')
                self.fs = None
                self.holds.clear()
                g.bot_aim = None
        elif st == 'landed' and fs['t'] > 3.2:
            self.fs = None

    def rings_at(self, x, y, small=False):
        self.fx.append([x, y, 0.0, 0.0, 0.9 if not small else 0.5, 'ring'])

    def pop(self, text):
        self.fx.append([self.x, FLOOR - 50, 0.0, -12.0, 1.6, text])

    def _burst(self, x, y, n=24, col=(255, 236, 170)):
        rng = self.rng
        for _ in range(n):
            self.fx.append([x + rng.uniform(-8, 8), y + rng.uniform(-6, 6), rng.uniform(-26, 26),
                            rng.uniform(-44, -10), rng.uniform(0.8, 1.4), col])

    # ------------------------------------------------------------ input
    def key(self, k):
        if k == pygame.K_ESCAPE:
            if self.panel:
                self.close_panel()
            elif self.fs and self.fs['state'] != 'landed':
                self.fs = None
                self.holds.clear()
                self.g.bot_aim = None
                self.g.audio.play('plop', 0.4)
            else:
                self.leave()
            return
        if self.panel:
            return
        if self.fs:
            if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.press('key')
            return
        if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_w, pygame.K_UP):
            self.interact()

    def press(self, src='mouse'):
        if self.panel:
            return
        g = self.g
        fs = self.fs
        if fs:
            if fs['state'] == 'bite':
                self.hook()
            elif fs['state'] == 'fight':
                self.holds.add(src)
                fs['mg'].press()
            elif fs['state'] == 'landed' and fs['t'] > 0.6:
                self.fs = None
            return
        if src != 'mouse':
            return
        wx, wy = g.s2w(*g.ui.mouse)
        tx = max(14.0, min(FS_W - 14.0, wx + self.scroll))
        if tx < JETTY_X + 26:
            return self.walk_to(JETTY_X, self.leave)
        for item in g.far['finds']:
            if abs(item['x'] - tx) < 8 and wy > FLOOR - 16:
                return self.walk_to(item['x'], self.interact)
        if POOL.inflate(10, 10).collidepoint(tx, wy):
            return self.walk_to(POOL_X, self.interact)
        spots = [(TENT_X, 'tent'), (FIRE_X, 'fire'), (OAK_X, 'oak'), (LANTERN_XY[0], 'oak')]
        bx = bram_x(g)
        if bx is not None:
            spots.append((bx, 'bram'))
        for sx, _what in spots:
            if abs(sx - tx) < 14 and wy > FLOOR - 130:
                return self.walk_to(sx, self.interact)
        self.walk_to(tx, None)

    def release(self, src='mouse'):
        self.holds.discard(src)

    def walk_to(self, x, then):
        self.target = float(x)
        self.on_arrive = then

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.done:
            return
        g = self.g
        self.t += dt
        rng = self.rng
        for p in self.fx:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if p[5] != 'ring' and not isinstance(p[5], str):
                p[3] += 40 * dt
            p[4] -= dt
        self.fx = [p for p in self.fx if p[4] > 0]
        if rng.random() < dt * 1.0:                              # smoke from the hut chimney
            self.smoke.append([float(HUT[1] - 21) + rng.uniform(-1, 1), float(FLOOR - 94), 3.0])
        if fire_lit(g) and rng.random() < dt * 2.0:              # ...and sparks and smoke off the fire
            self.smoke.append([FIRE_X + rng.uniform(-3, 3), float(FLOOR - 10), 2.2])
        for p in self.smoke:
            p[0] += (5 + getattr(g.env, 'wind', 0.3) * 10) * dt
            p[1] -= 8 * dt
            p[2] -= dt
        self.smoke = [p for p in self.smoke if p[2] > 0]
        # fireflies: summer nights by the pool, and always round the lantern once it is lit
        nf = g.env.nf
        want = (14 if g.env.season == 1 else 4) * nf + (18 if g.far['lit'] else 0) * nf
        if len(self.flies) < want and rng.random() < dt * 6:
            home = (LANTERN_XY[0], LANTERN_XY[1] + 10) if g.far['lit'] and rng.random() < 0.6 else \
                (POOL.centerx + rng.uniform(-100, 100), POOL.y - 6)
            self.flies.append(dict(hx=home[0], hy=home[1], ph=rng.uniform(0, 6), sp=rng.uniform(0.5, 1.2),
                                   r=rng.uniform(10, 34), life=rng.uniform(6, 14)))
        for f in self.flies:
            f['ph'] += dt * f['sp']
            f['life'] -= dt
        self.flies = [f for f in self.flies if f['life'] > 0 and nf > 0.2]
        if self.fs:
            self._fish_update(dt)
            self.step = 0.0
            return
        moving = 0
        if self.panel is None:
            walk = 0
            if g.typing is None and not HEADLESS:
                keys = g.keys()
                walk = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
                       (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
            if walk:
                self.target, self.on_arrive = None, None
                moving = walk
            elif self.target is not None:
                d = self.target - self.x
                if abs(d) < 2:
                    self.x = self.target
                    self.target = None
                    act, self.on_arrive = self.on_arrive, None
                    if act:
                        act()
                else:
                    moving = 1 if d > 0 else -1
        if moving:
            self.face = moving
            self.x = max(14.0, min(FS_W - 14.0, self.x + moving * WALK * dt))
            before = self.step
            self.step += dt * 9
            if int(before / math.pi) != int(self.step / math.pi):
                g.audio.step(0.22)
        else:
            self.step = 0.0
        want = max(0.0, min(FS_W - W, self.x - W / 2))
        self.scroll += (want - self.scroll) * min(1.0, dt * 5)

    def audio_ctx(self):
        return {'feeder': False, 'chimes': False}

    # ------------------------------------------------------------ for the bot: an evening on the Far Shore
    def auto(self, dt, rng):
        g = self.g
        if not hasattr(self, '_plan'):
            self._plan = ['finds', 'bram', 'fire', 'pool', 'oak', 'jetty']
            self._wait = 0.0
            self._caught = 0
        fs = self.fs
        if fs:
            if fs['state'] == 'bite':
                self.hook()
            elif fs['state'] == 'fight':
                mg = fs['mg']
                g.bot_aim = (mg.fa + rng.uniform(-12, 12)) % 360
                if mg.leap and not mg.leap['done'] and abs(mg.leap['r'] - minigame.TARGET) < 4:
                    mg.press()
                if mg.strain < 0.7:
                    self.holds.add('bot')
                else:
                    self.holds.discard('bot')
            elif fs['state'] == 'landed':
                self._caught += 1
                self.fs = None
                if self._caught < 2 and night(g):
                    self._plan.insert(0, 'pool')
            return
        if self.panel:
            self._wait += dt
            if self._wait < 0.6:
                return
            self._wait = 0.0
            p = self.panel
            if p == 'bram':
                give_req(g)
                for tk in LANTERN_TASKS:
                    give_task(g, tk['id'])
            elif p == 'fire':
                cook_supper(g)
                brew_tea(g)
            self.close_panel()
            return
        if self.target is not None or not self._plan:
            return
        step = self._plan.pop(0)
        if step == 'finds':
            for item in sorted(g.far['finds'], key=lambda b: b['x']):
                self._plan.insert(0, ('item', item))
        elif isinstance(step, tuple):
            if step[1] in g.far['finds']:
                self.walk_to(step[1]['x'], self.interact)
        elif step == 'bram':
            bx = bram_x(g)
            if bx is not None:
                self.walk_to(bx, self.interact)
        elif step == 'fire':
            self.walk_to(FIRE_X, self.interact)
        elif step == 'pool':
            if night(g):
                self.walk_to(POOL_X, self.start_fishing)
        elif step == 'oak':
            if can_light(g):
                self.walk_to(OAK_X, self.interact)
        elif step == 'jetty':
            self.walk_to(JETTY_X, self.leave)

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def draw_world(self, frame):
        g = self.g
        env = g.env
        t = self.t
        season = env.season
        sc = int(self.scroll)
        w = g.world
        w._sky(frame, env)
        back = build_back(season).copy()
        amb = env.amb if env.fog <= 0.01 else lerp_c(env.amb, env.fog_color, env.fog * 0.5)
        back.fill((*lerp_c(amb, env.sky[2], 0.35), 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(back, (-(sc // 3), 0))
        near = self.near
        near.fill((0, 0, 0, 0))
        self._pool(near, sc, t, env)
        near.blit(build(season), (0, 0), (sc, 0, W, H))
        self._draw_live(near, sc, t, season)
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(near, (0, 0))
        self._lights(frame, sc, t)
        w._weather(frame, env)

    def _pool(self, s, sc, t, env):
        r = POOL.move(-sc, 0)
        if r.right < -10 or r.x > W + 10:
            return
        water = lerp_c((50, 92, 100), env.sky[2], 0.25)
        water = lerp_c(water, (16, 22, 40), env.nf * 0.55)
        if env.season == 3:
            water = lerp_c(water, (200, 214, 226), 0.3)
        pygame.draw.ellipse(s, darken(water, 0.3), r)
        pygame.draw.ellipse(s, water, r.inflate(-8, -6))
        pygame.draw.ellipse(s, lighten(water, 0.07), r.inflate(-60, -20))
        s.fill(lighten(water, 0.2), (r.x + 30, r.y + 6, r.w - 70, 1))
        for k in range(6):
            if (t * 0.5 + k * 0.23) % 1 < 0.5:
                gx = r.x + 20 + (k * 37 + int(t * 3)) % (r.w - 40)
                s.fill(lighten(water, 0.4), (gx, r.y + 8 + (k * 5) % (r.h - 14), 3, 1))
        if env.nf > 0.3:                                       # the moon and stars in the water
            s.fill(lerp_c(water, (240, 240, 220), 0.6 * env.nf), (r.centerx + 40, r.y + 12, 6, 2))
            for k in range(5):
                s.set_at((r.x + 30 + k * 37, r.y + 10 + (k * 7) % 18), lerp_c(water, (230, 230, 250), env.nf))
        for k, (px, py) in enumerate(((r.x + 34, r.bottom - 12), (r.right - 50, r.y + 10), (r.x + 120, r.y + 24))):
            if env.season == 3:
                break
            py += int(math.sin(t * 0.8 + k * 2) * 0.6)
            pad = (82, 142, 76)
            pygame.draw.ellipse(s, darken(pad, 0.2), (px, py + 1, 9, 4))
            pygame.draw.ellipse(s, pad, (px, py, 9, 4))
            if k == 1 and env.season in (0, 1):
                s.fill((246, 240, 250), (px + 3, py - 1, 3, 1))

    def _draw_live(self, s, sc, t, season):
        g = self.g
        st = g.far
        # your boat, tied up at the landing
        bx = 18 - sc
        if bx > -60:
            bob = int(math.sin(t * 1.6) * 1)
            pygame.draw.polygon(s, (120, 76, 52), [(bx - 16, FLOOR + 12 + bob), (bx + 22, FLOOR + 12 + bob),
                                                  (bx + 16, FLOOR + 19 + bob), (bx - 12, FLOOR + 19 + bob)])
            s.fill((160, 110, 76), (bx - 15, FLOOR + 12 + bob, 36, 2))
            pygame.draw.line(s, (200, 190, 160), (bx + 20, FLOOR + 12 + bob), (bx + 30, FLOOR + 4))
        # wild finds
        for item in st['finds']:
            x = item['x'] - sc
            if -10 < x < W + 10:
                find_icon(s, item['id'], x, FLOOR + 4, t)
        # the campfire: flames in the evening, a curl of smoke from the embers by day
        fx = FIRE_X - sc
        if -30 < fx < W + 30:
            s.fill((90, 64, 46), (fx - 6, FLOOR - 2, 12, 3))
            s.fill((120, 86, 58), (fx - 4, FLOOR - 3, 3, 2))
            if fire_lit(g):
                for k in range(5):
                    h = 6 + int(5 * abs(math.sin(t * (7 + k) + k * 1.3)))
                    x = fx - 5 + k * 2 + int(math.sin(t * 9 + k) * 1)
                    pygame.draw.polygon(s, (250, 150, 60), [(x - 2, FLOOR - 2), (x, FLOOR - 2 - h), (x + 2, FLOOR - 2)])
                    pygame.draw.polygon(s, (255, 226, 130), [(x - 1, FLOOR - 2), (x, FLOOR - 2 - h // 2),
                                                             (x + 1, FLOOR - 2)])
            else:
                s.fill((200, 90, 50), (fx - 2, FLOOR - 2, 1, 1))
                s.fill((170, 70, 40), (fx + 2, FLOOR - 3, 1, 1))
        # the Hollow Lantern
        lx, ly = LANTERN_XY[0] - sc, LANTERN_XY[1]
        if -20 < lx < W + 20:
            sway = int(math.sin(t * 1.3) * 1)
            frame_c = (60, 54, 50) if not st['lit'] else (90, 76, 60)
            s.fill(frame_c, (lx - 5 + sway, ly - 8, 11, 2))
            s.fill(frame_c, (lx - 5 + sway, ly + 8, 11, 2))
            glass = (40, 46, 52) if not st['lit'] else (255, 226, 140)
            done = len(st['lantern'])
            if not st['lit'] and done:
                glass = lerp_c((40, 46, 52), (120, 110, 80), done / len(LANTERN_TASKS))
            s.fill(glass, (lx - 4 + sway, ly - 6, 9, 14))
            for k in (-4, 0, 4):
                s.fill(frame_c, (lx + k + sway, ly - 6, 1, 14))
            if not st['lit'] and 'frame' not in st['lantern']:
                pygame.draw.line(s, (20, 20, 24), (lx - 3 + sway, ly - 4), (lx + 2 + sway, ly + 5))
        # Bramwell
        where = bram_where(g)
        if where:
            x = int(bram_x(g) - sc)
            if -30 < x < W + 30:
                face = -1 if where == 'fire' else (1 if self.x > bram_x(g) else -1)
                T.ground_shadow(s, x, FLOOR, 13, 60)
                T.walker(s, x, FLOOR, face, 0, BRAM['shirt'], BRAM['hair'], BRAM['hat'], season)
                if where == 'hut' and not st['met'] and math.sin(t * 3) > 0:
                    s.fill((255, 230, 120), (x - 1, FLOOR - 50, 3, 6))
                    s.fill((255, 230, 120), (x - 1, FLOOR - 42, 3, 2))
        # you (with a rod at the pool)
        x = int(self.x - sc)
        T.ground_shadow(s, x, FLOOR, 13, 60)
        T.walker(s, x, FLOOR, self.face, self.step, *looks.player_colors(g, season), g.hat, season, look=looks.of(g))
        fs = self.fs
        if fs:
            hx, hy = x + 6, FLOOR - 22
            tip = (x + 22, FLOOR - 40)
            pygame.draw.line(s, (110, 80, 56), (hx, hy), tip, 1)
            bx_, by_ = int(fs['bx'] - sc), int(fs['by'])
            if fs['state'] == 'fight':
                mg = fs['mg']
                bx_ += int(math.cos(math.radians(mg.fa)) * 10)
                by_ += int(math.sin(math.radians(mg.fa)) * 3)
            pygame.draw.line(s, (230, 230, 220), tip, (bx_, by_ - 1))
            if fs['state'] in ('wait', 'bite'):
                dip = 2 if fs['state'] == 'bite' and math.sin(t * 30) > 0 else int(math.sin(t * 2) * 0.6)
                s.fill((240, 70, 60), (bx_ - 1, by_ - 2 + dip, 3, 2))
                s.fill((250, 250, 250), (bx_ - 1, by_ + dip, 3, 1))
                if fs['state'] == 'bite':
                    s.fill((255, 230, 120), (x - 1, FLOOR - 52, 3, 6))
                    s.fill((255, 230, 120), (x - 1, FLOOR - 44, 3, 2))
        # sparks, rings and words
        for p in self.fx:
            px, py = int(p[0] - sc), int(p[1])
            if p[5] == 'ring':
                rw = int(4 + (1 - p[4]) * 14)
                pygame.draw.ellipse(s, (200, 220, 230), (px - rw // 2, py - 1, rw, 3), 1)
            elif not isinstance(p[5], str):
                s.fill(p[5], (px, py, 2, 2))
        for p in self.smoke:
            a = max(0.0, min(1.0, p[2] / 3))
            c = lerp_c((150, 150, 150), (210, 210, 214), 1 - a)
            s.fill(c, (int(p[0] - sc), int(p[1]), 2 + int((1 - a) * 3), 2))

    def _lights(self, frame, sc, t):
        g = self.g
        nf = g.env.nf
        big, mid, beam, fly = self.glows
        st = g.far
        if fire_lit(g):
            fl = 0.85 + 0.15 * math.sin(t * 11) * math.sin(t * 7.3)
            k = max(0.25, nf) * fl
            add_glow(frame, big, (FIRE_X - sc, FLOOR - 6), k * 0.9)
            add_glow(frame, mid, (FIRE_X - sc, FLOOR - 6), k)
        if nf > 0.05 and bram_where(g) == 'hut' or (nf > 0.05 and 19 * 60 <= g.minute < 23 * 60):
            wx = HUT[0] + 59 - sc
            if -20 < wx < W + 20:
                frame.fill((int(200 * nf), int(140 * nf), int(60 * nf)), (wx - 8, FLOOR - 37, 17, 12),
                           special_flags=pygame.BLEND_ADD)
                add_glow(frame, mid, (wx, FLOOR - 31), nf * 0.6)
        if st['lit']:
            lx, ly = LANTERN_XY[0] - sc + int(math.sin(t * 1.3)), LANTERN_XY[1]
            on = max(0.4, nf)
            add_glow(frame, beam, (lx, ly), on * (0.8 + 0.1 * math.sin(t * 5)))
            add_glow(frame, mid, (lx, ly), on)
        for f in self.flies:
            x = f['hx'] + math.cos(f['ph']) * f['r'] - sc
            y = f['hy'] + math.sin(f['ph'] * 1.7) * f['r'] * 0.4
            k = 0.5 + 0.5 * math.sin(f['ph'] * 5)
            if -10 < x < W + 10 and k > 0.2:
                frame.fill((int(220 * k), int(255 * k), int(140 * k)), (int(x), int(y), 1, 1),
                           special_flags=pygame.BLEND_ADD)
                add_glow(frame, fly, (x, y), k * nf)

    # ------------------------------------------------------------ UI
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        sc = self.scroll
        fs = self.fs
        if fs and fs['state'] == 'fight':
            minigame.draw(s, ui, fs['mg'], self.t, fs['spec']['name'] if fs['spec']['id'] in g.journal else
                          'Something in the dark...', teach=False)
            return
        ui.blit_text(s, 'The Far Shore', (sw // 2, 26), 'h3', (255, 250, 240), 'center', (30, 30, 50))
        r = g.far['req']
        if r and not r['done']:
            what = (FISH_BY_ID[r['id']]['name'] if r['kind'] == 'fish' else
                    '%d %s' % (r['n'], __import__('garden').FORAGE_BY_ID[r['id']]['name']))
            info = "Bramwell's favour: %s  (+%d)" % (what, r['reward'])
        else:
            info = 'Fish rise in the pool after 7:30 PM' if not night(g) else 'The pool is stirring...'
        ui.blit_text(s, info, (sw // 2, 58), 'small', (236, 244, 230), 'center', (20, 30, 24))
        ui.blit_text(s, fmt_clock(g.minute), (24, 22), 'bodyb', (255, 250, 240), 'topleft', (30, 30, 50))
        for p in self.fx:
            if isinstance(p[5], str) and p[5] != 'ring':
                ui.blit_text(s, p[5], (int((p[0] - sc) * k), int(p[1] * k)), 'bodyb', (255, 246, 226), 'center',
                             (30, 26, 30), alpha=int(255 * min(1.0, p[4])))
        if fs and fs['state'] == 'landed':
            self._card(s, fs['card'])
            return
        p = self.prompt() if self.panel is None and self.target is None else None
        if self.panel is None and not p and bram_where(g) and abs(bram_x(g) - self.x) < 70:
            ui.blit_text(s, 'Bramwell, ranger', (int((bram_x(g) - sc) * k), int((FLOOR - 44) * k)), 'tiny',
                         (255, 250, 236), 'center', outline=(30, 30, 40))
        if p:
            px = int((self.x - sc) * k)
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (px, int((FLOOR - 40) * k) - 6)
            r.x = max(12, min(sw - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        if fs and fs['state'] in ('wait', 'bite'):
            text = 'Strike! Press E or click!' if fs['state'] == 'bite' else 'Waiting for a bite...   Esc: reel in'
            ui.blit_text(s, text, (sw // 2, sh - 120), 'h3' if fs['state'] == 'bite' else 'bodyb',
                         (255, 240, 200), 'center', (30, 26, 30))
        if self.panel is None:
            hint = g.hint([('key', 'A'), ('key', 'D'), 'or', ('key', 'Click'), 'to walk   ', ('key', 'E'),
                           'pick up, talk, fish   ', ('key', 'Esc'), 'row home'],
                          [('pad', 'STICK'), 'walk   ', ('pad', 'A'), 'pick up, talk   ', ('pad', 'B'), 'row home'])
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, sh - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
            return
        g.dim(s)
        {'bram': self.draw_bram, 'fire': self.draw_fire, 'tent': self.draw_tent}[self.panel](s)

    def _card(self, s, c):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        spec = c['spec']
        r = pygame.Rect(sw // 2 - 230, sh // 2 - 150, 460, 250)
        ui.panel(s, r, radius=22)
        col = (240, 214, 130) if spec['rarity'] >= 3 else (220, 230, 210)
        pygame.draw.rect(s, col, (r.x + 20, r.y + 20, r.w - 40, 120), border_radius=16)
        spr = art.fish_sprite(spec, 3)
        s.blit(spr, spr.get_rect(center=(r.centerx, r.y + 80)))
        ui.blit_text(s, spec['name'], (r.centerx, r.y + 160), 'h3', U.INK, 'center')
        tag = 'New!  ' if c['new'] else 'Record!  ' if c['record'] else ''
        ui.blit_text(s, '%s%.1f cm   worth %d' % (tag, c['size'], c['price']), (r.centerx, r.y + 196), 'smallb',
                     U.SOFT, 'center')
        ui.blit_text(s, 'Into the basket. Click to cast again.', (r.centerx, r.y + 224), 'tiny', U.SOFT, 'center')

    # ------------------------------------------------------------ the windows
    def _window(self, s, title, h=520):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        rect = pygame.Rect(sw // 2 - 430, sh // 2 - h // 2, 860, h)
        ui.panel(s, rect, radius=24)
        g.panel_header(s, rect, title)
        ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', self.close_panel, 'normal', font='h3')
        return rect

    def draw_bram(self, s):
        g = self.g
        ui = g.ui
        st = g.far
        rect = self._window(s, 'Bramwell')
        tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
        T.walker(tmp, 13, 38, 1, 0, BRAM['shirt'], BRAM['hair'], BRAM['hat'], g.env.season, False)
        big = pygame.transform.scale(tmp, (104, 160))
        s.blit(big, big.get_rect(center=(rect.x + 110, rect.y + 180)))
        ui.blit_text(s, 'Forest ranger', (rect.x + 110, rect.y + 274), 'tiny', U.SOFT, 'center')
        n = hearts(g)
        hx = rect.x + 110 - 2 * 22
        for i in range(5):
            col = (226, 84, 104) if i < n else (214, 200, 186)
            cx, cy = hx + i * 22, rect.y + 300
            pygame.draw.circle(s, col, (cx - 4, cy), 5)
            pygame.draw.circle(s, col, (cx + 4, cy), 5)
            pygame.draw.polygon(s, col, [(cx - 9, cy + 1), (cx + 9, cy + 1), (cx, cy + 10)])
        y = rect.y + 326
        for ln in ui.wrap('"%s"' % self.line, 'small', 200)[:8]:
            ui.blit_text(s, ln, (rect.x + 110, y), 'small', U.SOFT, 'midtop')
            y += 22
        # today's favour
        x0, w = rect.x + 240, rect.w - 270
        box = pygame.Rect(x0, rect.y + 90, w, 120)
        ui.tile(s, box, (250, 244, 228), (196, 170, 130))
        ui.blit_text(s, "Today's favour", (box.x + 18, box.y + 14), 'bodyb', U.INK)
        r = st['req']
        import garden
        if r:
            if r['kind'] == 'forage':
                f = garden.FORAGE_BY_ID[r['id']]
                s.blit(garden.crop_icon(f['id'], 3), (box.x + 18, box.y + 50))
                what = '%d %s  (you have %d)' % (r['n'], f['name'], g.garden['produce'].get(r['id'], 0))
            else:
                f = FISH_BY_ID[r['id']]
                spr = art.fish_sprite(f, 1) if f['id'] in g.journal else art.silhouette(f, 1)
                s.blit(spr, spr.get_rect(center=(box.x + 42, box.y + 74)))
                what = 'A %s from the Hollow Pool' % f['name'] if f['id'] in g.journal else \
                    'A fish from the Hollow Pool at night'
            ui.blit_text(s, what, (box.x + 80, box.y + 56), 'small', U.INK, maxw=w - 260)
            ui.blit_text(s, 'Reward: %d coins and a smile' % r['reward'], (box.x + 80, box.y + 82), 'small', U.SOFT)
            if r['done']:
                ui.blit_text(s, 'Done for today!', (box.right - 20, box.centery), 'smallb', (110, 150, 90),
                             'midright')
            else:
                ui.button(s, (box.right - 150, box.centery - 22, 130, 44), 'Give', lambda: give_req(g), 'gold',
                          enabled=can_give(g), font='smallb')
        # the Hollow Lantern
        box2 = pygame.Rect(x0, box.bottom + 14, w, rect.bottom - box.bottom - 34)
        ui.tile(s, box2, (246, 240, 226), (196, 170, 130))
        ui.blit_text(s, 'The Hollow Lantern', (box2.x + 18, box2.y + 14), 'bodyb', U.INK)
        if st['lit']:
            ui.blit_text(s, 'It shines in the old oak every night. The Hollow King has been seen in the pool.',
                         (box2.x + 18, box2.y + 52), 'small', U.SOFT, maxw=w - 36)
            return
        yy = box2.y + 50
        for tk in LANTERN_TASKS:
            got = tk['id'] in st['lantern']
            row = pygame.Rect(box2.x + 14, yy, w - 28, 52)
            pygame.draw.rect(s, (236, 244, 226) if got else (252, 248, 238), row, border_radius=12)
            ui.blit_text(s, tk['name'], (row.x + 14, row.y + 6), 'smallb', U.INK)
            ui.blit_text(s, 'Needs %s' % tk['need'], (row.x + 14, row.y + 28), 'tiny', U.SOFT)
            if got:
                ui.blit_text(s, 'Done', (row.right - 18, row.centery), 'smallb', (110, 150, 90), 'midright')
            else:
                ui.button(s, (row.right - 120, row.y + 8, 106, 36), 'Give', lambda i=tk['id']: give_task(g, i),
                          'normal', enabled=task_ready(g, tk['id']), font='smallb')
            yy += 58
        if len(st['lantern']) == len(LANTERN_TASKS):
            ui.blit_text(s, 'All mended! Light it at the old oak after dark.', (box2.x + 18, yy + 6), 'smallb',
                         (170, 120, 50))

    def draw_fire(self, s):
        g = self.g
        ui = g.ui
        st = g.far
        import garden
        rect = self._window(s, 'The Campfire', 420)
        fish = next((b for b in g.basket if not FISH_BY_ID[b['id']].get('junk')), None)
        tea_have = sum(g.garden['produce'].get(k, 0) for k in TEA)
        cards = [
            ('Campfire Supper', 'A fish from your basket and any wild find, roasted on a stick.',
             'Tonight the Hollow Pool bites quicker, and the fish run a little bigger.',
             'Fish: %s.  Wild finds: %d' % (FISH_BY_ID[fish['id']]['name'] if fish else 'none', wild_count(g)),
             st['supper'] == g.day, fish is not None and wild_count(g) >= 1, lambda: cook_supper(g)),
            ("Forager's Tea", 'Two flowers or herbs (violets, chamomile, wild garlic, sorrel or pine tips).',
             'A little luck for the rest of the day.', 'You have %d' % tea_have, st['tea'] == g.day, tea_have >= 2,
             lambda: brew_tea(g)),
        ]
        for i, (name, need, gives, have, done, ok, act) in enumerate(cards):
            c = pygame.Rect(rect.x + 30 + i * 406, rect.y + 96, 394, rect.h - 130)
            ui.tile(s, c, (252, 246, 232), (200, 150, 100))
            ui.blit_text(s, name, (c.x + 20, c.y + 16), 'h3', U.INK)
            y = c.y + 60
            for line, col in ((need, U.INK), (gives, U.SOFT), (have, U.SOFT)):
                for ln in ui.wrap(line, 'small', c.w - 40):
                    ui.blit_text(s, ln, (c.x + 20, y), 'small', col)
                    y += 24
                y += 8
            if done:
                ui.blit_text(s, 'Had one today', (c.centerx, c.bottom - 40), 'smallb', (110, 150, 90), 'center')
            else:
                ui.button(s, (c.centerx - 90, c.bottom - 62, 180, 44), 'Make it', act, 'primary', enabled=ok,
                          font='smallb')

    def draw_tent(self, s):
        g = self.g
        ui = g.ui
        rect = self._window(s, 'The Tent', 300)
        ui.blit_text(s, 'Sleep under the stars? You will wake to birdsong, row home at first light with a little',
                     (rect.centerx, rect.y + 110), 'small', U.INK, 'center')
        ui.blit_text(s, 'extra luck, and find a few more things along the trail tomorrow.',
                     (rect.centerx, rect.y + 136), 'small', U.INK, 'center')
        ui.button(s, (rect.centerx - 200, rect.bottom - 90, 190, 50), 'Sleep here', lambda: camp_sleep(g), 'primary')
        ui.button(s, (rect.centerx + 10, rect.bottom - 90, 190, 50), 'Not yet', self.close_panel, 'normal')
