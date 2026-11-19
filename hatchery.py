"""The hatchery pond: a little stone-ringed pool on the slope under the garden.

Colour morphs you catch (morphs.py) come here, and you can bring ordinary fish from the basket too. Two fish of the
same kind that have spent a night in the pond lay a clutch of eggs at dawn. The eggs hatch into fry two days later,
and three days after that the young are big enough to collect. Young can take after their parents' colours, and
now and then one turns up in a colour neither parent had.

Releasing a coloured fish into the lake (from the pond, the tank or a catch card) stocks it: for a week, that kind
bites in that colour far more often.
"""
import math
import random

import pygame

import morphs
import ui as U
from art import lerp_c, darken, lighten

POND = 6                    # fish the pond holds
CLUTCHES = 2                # clutches of eggs it can raise at once
HATCH_DAY = 2               # eggs hatch into fry this many days after they're laid
GROWN_DAY = 5               # and the young are ready to collect on this day
STOCK_DAYS = 7
SAME_KEEP = 0.85            # both parents the same morph: chance each young one is too
ONE_KEEP = 0.45             # one parent a morph (or two different ones): chance a young one takes after it
SPONTANEOUS = 0.05          # chance a young one comes out in a colour neither parent had

AREA = pygame.Rect(12, 288, 72, 26)          # click here on the lake to open the hatchery
POND_RECT = pygame.Rect(18, 293, 60, 16)     # the water, in world pixels


def new():
    return {'pond': [], 'clutches': [], 'stock': {}, 'found': {}, 'raised': 0, 'laid': 0, 'last': None}


def clean(hd):
    from data import FISH_BY_ID
    out = new()
    if not isinstance(hd, dict):
        return out
    try:
        for f in hd.get('pond', [])[:POND]:
            if isinstance(f, dict) and f.get('id') in FISH_BY_ID:
                v = f.get('v') if f.get('v') in morphs.MORPH_BY_ID else None
                out['pond'].append(dict(id=f['id'], size=float(f.get('size', 1.0)), v=v,
                                        day=int(f.get('day', 0)), price=max(1, int(f.get('price', 1)))))
        for c in hd.get('clutches', [])[:CLUTCHES]:
            if isinstance(c, dict) and c.get('id') in FISH_BY_ID:
                pv = [v if v in morphs.MORPH_BY_ID else None for v in list(c.get('pv', []))[:2]]
                out['clutches'].append(dict(id=c['id'], pv=pv, day=int(c.get('day', 0)),
                                            n=max(1, min(5, int(c.get('n', 3))))))
        for sid, st in dict(hd.get('stock', {})).items():
            if sid in FISH_BY_ID and isinstance(st, dict) and st.get('v') in morphs.MORPH_BY_ID:
                out['stock'][sid] = {'v': st['v'], 'until': int(st.get('until', 0))}
        for v, ids in dict(hd.get('found', {})).items():
            if v in morphs.MORPH_BY_ID:
                out['found'][v] = [i for i in ids if i in FISH_BY_ID]
        out['raised'] = max(0, int(hd.get('raised', 0)))
        out['laid'] = int(hd.get('laid', 0))
    except (TypeError, ValueError, AttributeError):
        pass
    return out


# ---------------------------------------------------------------- what's in the pond
def can_live(spec):
    """Freshwater fish that can morph (no sea fish, crabs or legends)."""
    return morphs.can_morph(spec) and spec.get('spot') not in ('pier', 'rocks')


def room(g):
    return POND - len(g.hatch['pond'])


def stage(g, c):
    """0 eggs, 1 fry, 2 ready to collect."""
    age = g.day - c['day']
    return 2 if age >= GROWN_DAY else 1 if age >= HATCH_DAY else 0


def ready(g):
    return [c for c in g.hatch['clutches'] if stage(g, c) == 2]


def pairs(g):
    """Kinds with two fish that have spent a night in the pond, and no clutch of their own yet."""
    hd = g.hatch
    busy = {c['id'] for c in hd['clutches']}
    count = {}
    for f in hd['pond']:
        if f['day'] < g.day:
            count[f['id']] = count.get(f['id'], 0) + 1
    return [sid for sid, n in count.items() if n >= 2 and sid not in busy]


def price_of(spec, size, v):
    lo, hi = spec['size']
    k = (size - lo) / max(0.01, hi - lo)
    return max(1, int(round(spec['price'] * (0.8 + 0.6 * k)))) * morphs.mult(v)


def note_found(g, sid, v):
    """Remember a kind seen in a morph. True when it's a new one for the Variants page."""
    if v not in morphs.MORPH_BY_ID:
        return False
    seen = g.hatch['found'].setdefault(v, [])
    if sid in seen:
        return False
    seen.append(sid)
    return True


def kinds_found(g):
    return sum(len(v) for v in g.hatch['found'].values())


# ---------------------------------------------------------------- the day
def morning(g):
    """At dawn: pairs lay eggs, and the pond tells you when young are ready."""
    from data import FISH_BY_ID
    hd = g.hatch
    if hd['laid'] == g.day:
        return
    hd['laid'] = g.day
    rng = random.Random(g.day * 7919 + len(hd['pond']))
    for sid in pairs(g):
        if len(hd['clutches']) >= CLUTCHES:
            break
        mates = [f for f in hd['pond'] if f['id'] == sid and f['day'] < g.day]
        mates.sort(key=lambda f: f['v'] is None)          # colourful parents first
        pv = [mates[0]['v'], mates[1]['v']]
        hd['clutches'].append(dict(id=sid, pv=pv, day=g.day, n=rng.choice((2, 3, 3, 4))))
        g.toast('A pair of %s laid eggs in the hatchery pond!' % FISH_BY_ID[sid]['name'], (90, 140, 170))
    n = len(ready(g))
    if n:
        g.toast('Young fish are ready in the hatchery pond.' if n == 1 else
                '%d clutches of young fish are ready in the hatchery pond.' % n, (90, 140, 170))


def inherit(pv, rng):
    vs = [v for v in pv if v]
    if len(vs) == 2 and vs[0] == vs[1]:
        if rng.random() < SAME_KEEP:
            return vs[0]
    elif vs:
        if rng.random() < ONE_KEEP:
            return rng.choice(vs)
    if rng.random() < SPONTANEOUS:
        return rng.choice(morphs.IDS)
    return None


# ---------------------------------------------------------------- things you do
def add_catch(g, spec, size, v, price):
    """A catch (usually a morph) goes into the pond. False when there's no room."""
    if room(g) <= 0 or not can_live(spec):
        return False
    g.hatch['pond'].append(dict(id=spec['id'], size=size, v=v, day=g.day, price=price))
    return True


def from_basket(g, sid):
    """Move one fish of this kind from the basket into the pond (the biggest one)."""
    from data import FISH_BY_ID
    spec = FISH_BY_ID.get(sid)
    if room(g) <= 0 or not spec or not can_live(spec):
        return False
    items = [b for b in g.basket if b['id'] == sid]
    if not items:
        return False
    b = max(items, key=lambda b: b['size'])
    g.basket.remove(b)
    g.hatch['pond'].append(dict(id=sid, size=b['size'], v=None, day=g.day, price=b['price']))
    g.audio.play('splash_small', 0.5)
    g.save()
    return True


def basket_kinds(g):
    """Kinds in the basket that could go into the pond, most of them first."""
    from data import FISH_BY_ID
    count = {}
    for b in g.basket:
        spec = FISH_BY_ID.get(b['id'])
        if spec and can_live(spec):
            count[b['id']] = count.get(b['id'], 0) + 1
    return sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))


def collect(g, i):
    """Collect a ready clutch: the young go into the pond, and any that don't fit are let into the lake."""
    from data import FISH_BY_ID
    hd = g.hatch
    if not 0 <= i < len(hd['clutches']) or stage(g, hd['clutches'][i]) != 2:
        return None
    c = hd['clutches'].pop(i)
    spec = FISH_BY_ID[c['id']]
    rng = random.Random()
    lo, hi = spec['size']
    young = []
    for _ in range(c['n']):
        v = inherit(c['pv'], rng)
        size = round(lo + (hi - lo) * rng.uniform(0.05, 0.35), 1)
        young.append(dict(id=c['id'], size=size, v=v, day=g.day, price=price_of(spec, size, v)))
    young.sort(key=lambda f: (f['v'] is None, -morphs.mult(f['v'])))     # the colourful ones get the room
    kept = freed = 0
    new_kinds = []
    for f in young:
        if note_found(g, f['id'], f['v']):
            new_kinds.append(f['v'])
        if room(g) > 0:
            hd['pond'].append(f)
            kept += 1
        else:
            stock(g, f)
            freed += 1
    hd['raised'] += len(young)
    g.stats['raised'] = g.stats.get('raised', 0) + len(young)
    colours = [morphs.MORPH_BY_ID[f['v']]['name'] for f in young if f['v']]
    hd['last'] = dict(id=c['id'], n=len(young), colours=colours, kept=kept, freed=freed)
    msg = '%d young %s' % (len(young), spec['name'])
    if colours:
        msg += ': ' + ', '.join(colours) + '!'
    if freed:
        msg += '  (%d swam off into the lake: the pond was full)' % freed
    g.toast(msg, (90, 140, 170))
    g.audio.play('jingle3' if colours else 'jingle1', 0.6)
    g.world.sparkles(48, 296, 10, (220, 244, 255))
    g.check_badges()
    g.save()
    return young


def stock(g, f):
    """A fish let into the lake. A coloured one stocks the lake with its colour for a week."""
    if f.get('v') in morphs.MORPH_BY_ID:
        g.hatch['stock'][f['id']] = {'v': f['v'], 'until': g.day + STOCK_DAYS}


def release(g, i):
    from data import FISH_BY_ID
    hd = g.hatch
    if not 0 <= i < len(hd['pond']):
        return
    f = hd['pond'].pop(i)
    stock(g, f)
    g.luck = min(3.0, g.luck + 0.3)
    g.stats['released'] += 1
    spec = FISH_BY_ID[f['id']]
    if f.get('v'):
        g.toast('The %s swims off. For a week, %s bite in %s more often.'
                % (morphs.name(spec, f['v']), spec['name'], morphs.MORPH_BY_ID[f['v']]['name'].lower()),
                (110, 150, 100))
    else:
        g.toast('You let the %s go. You feel a little luckier.' % spec['name'], (110, 150, 100))
    g.audio.play('splash_small', 0.6)
    g.hatch_sel = None
    g.check_badges()
    g.save()


def sell(g, i):
    from data import FISH_BY_ID
    hd = g.hatch
    if not 0 <= i < len(hd['pond']):
        return
    f = hd['pond'].pop(i)
    g.coins += f['price']
    g.stats['sold'] = g.stats.get('sold', 0) + 1
    g.note('sell', coins=f['price'])
    g.toast('A collector paid %d coins for the %s.' % (f['price'], morphs.name(FISH_BY_ID[f['id']], f['v'])),
            (200, 160, 70))
    g.audio.play('coin', 0.8)
    g.hatch_sel = None
    g.save()


def to_tank(g, i):
    from data import FISH_BY_ID
    hd = g.hatch
    if not 0 <= i < len(hd['pond']) or len(g.tank) >= g.tank_size():
        return
    f = hd['pond'].pop(i)
    g.tank.append(dict(id=f['id'], size=f['size'], v=f['v']))
    g.toast('%s is settling into the cabin tank.' % morphs.name(FISH_BY_ID[f['id']], f['v']), (90, 140, 190))
    g.audio.play('splash_small', 0.6)
    g.hatch_sel = None
    g.check_badges()
    g.save()


def to_basket(g, i):
    """Plain fish can go back in the basket (coloured ones stay out of it, so they're never cooked or sold by
    accident)."""
    hd = g.hatch
    if not 0 <= i < len(hd['pond']) or hd['pond'][i].get('v'):
        return
    f = hd['pond'].pop(i)
    g.basket.append(dict(id=f['id'], size=f['size'], price=f['price']))
    g.audio.play('ui', 0.5)
    g.hatch_sel = None
    g.save()


def hud_line(g):
    n = len(ready(g))
    if n:
        return 'Young fish are ready in the hatchery'
    return None


# ---------------------------------------------------------------- drawing
def _pond_fish(g, t, w, h, ox, oy):
    """Where each pond fish is now: slow loops around the water. (x, y, facing right)."""
    out = []
    for i, f in enumerate(g.hatch['pond']):
        ph = i * 2.1 + (hash(f['id']) % 100) * 0.05
        sp = 0.22 + 0.04 * (i % 3)
        a = t * sp + ph
        x = ox + w / 2 + math.cos(a) * (w * 0.36)
        y = oy + h / 2 + math.sin(a * 1.3) * (h * 0.22) + math.sin(t * 0.7 + i) * 0.6
        out.append((x, y, -math.sin(a) < 0))
    return out


def draw_world(near, g, t):
    """The pond on the lower lawn: a ring of fieldstones, water with a deep middle and the sky in it, lily pads,
    reeds, and the fish as little coloured shapes that flick their tails."""
    env = g.env
    r = POND_RECT
    sky = env.sky[2]
    water = lerp_c((60, 112, 124), sky, 0.22)
    water = lerp_c(water, (20, 26, 44), env.nf * 0.6)
    edge = darken(water, 0.28)
    winter = env.season == 3
    # the bank: a dark rim of wet earth under the stones
    pygame.draw.ellipse(near, (78, 66, 54), r.inflate(6, 4))
    pygame.draw.ellipse(near, edge, r)
    pygame.draw.ellipse(near, water, r.inflate(-6, -4))
    pygame.draw.ellipse(near, lighten(water, 0.08), r.inflate(-22, -9))
    # the sky in the water: a soft band, and glints that come and go
    band = lighten(water, 0.22 if not winter else 0.4)
    near.fill(band, (r.x + 10, r.y + 3, r.w - 26, 1))
    near.fill(lighten(water, 0.12), (r.x + 16, r.y + 4, r.w - 36, 1))
    for k in range(4):
        ph = (t * 0.6 + k * 0.29) % 1
        if ph < 0.5:
            gx = r.x + 10 + (k * 13 + int(t * 2)) % (r.w - 20)
            near.fill(lighten(water, 0.45), (gx, r.y + 5 + (k * 3) % 7, 2, 1))
    if winter:
        # thin ice at the edges, with a few white streaks
        pygame.draw.ellipse(near, (214, 228, 238), r, 2)
        for k in range(5):
            x = r.x + 8 + k * 10
            near.fill((236, 244, 250), (x, r.y + 4 + (k * 5) % 8, 4, 1))
    # the fish: a short body in their colour, a darker back, and a tail that flicks
    from data import FISH_BY_ID
    for i, (f, (x, y, right)) in enumerate(zip(g.hatch['pond'], _pond_fish(g, t, r.w - 14, r.h - 8, r.x + 7, r.y + 4))):
        spec = FISH_BY_ID[f['id']]
        col = morphs.MORPH_BY_ID[f['v']]['col'] if f['v'] else spec['c1']
        if not winter:
            col = lerp_c(col, water, 0.15)
        else:
            col = lerp_c(col, (214, 228, 238), 0.55)
        xi, yi = int(x), int(y)
        d = 1 if right else -1
        near.fill(col, (xi - 2, yi, 5, 1))
        near.fill(darken(col, 0.25), (xi - 1, yi - 1, 3, 1))
        flick = 1 if math.sin(t * 6 + i * 1.7) > 0 else 0
        near.set_at((xi - 3 * d, yi - flick), darken(col, 0.3))
        near.set_at((xi + 2 * d, yi), (30, 30, 40))
        # now and then one comes up and leaves a ring
        ph = (t * 0.23 + i * 0.41) % 1
        if ph < 0.12 and not winter:
            rw = 3 + int(ph / 0.12 * 8)
            pygame.draw.ellipse(near, lighten(water, 0.35), (xi - rw // 2, yi - 1, rw, 3), 1)
    # eggs among the reeds, or the fry darting about
    for c in g.hatch['clutches']:
        st = stage(g, c)
        if st == 0:
            for k in range(5):
                near.set_at((r.x + 6 + k % 3, r.y + 7 + k // 3), (240, 236, 214))
        else:
            for k in range(4):
                x = r.x + 10 + (k * 7 + int(t * 10 + k * 3)) % 26
                y = r.y + 7 + int(math.sin(t * 3 + k) * 2)
                near.set_at((x, y), (220, 220, 200) if st == 1 else (240, 200, 120))
    # lily pads (one in flower), reeds at the back left, and the stone ring on top
    if not winter:
        for k, (px, py) in enumerate(((r.right - 16, r.y + 9), (r.x + 22, r.bottom - 5))):
            py += int(math.sin(t * 0.8 + k * 2) * 0.6)
            pad = (82, 142, 76)
            pygame.draw.ellipse(near, darken(pad, 0.2), (px, py + 1, 7, 3))
            pygame.draw.ellipse(near, pad, (px, py, 7, 3))
            near.set_at((px + 5, py + 1), water)
            if k == 0 and env.season in (0, 1):
                near.fill((246, 170, 196), (px + 2, py - 1, 2, 1))
                near.set_at((px + 2, py - 2), (255, 236, 244))
    reed = (92, 134, 70) if not winter else (150, 140, 110)
    for k, dx in enumerate((2, 4, 6, 8)):
        sway = int(round(math.sin(t * 1.1 + k) * 0.6))
        top = r.y - 7 - (k * 3) % 5
        pygame.draw.line(near, reed if k % 2 else darken(reed, 0.15), (r.x + dx, r.y + 5), (r.x + dx + sway, top))
        if env.season in (1, 2) and k % 2 == 0:
            near.fill((116, 80, 54), (r.x + dx + sway, top - 1, 1, 3))
    rng = random.Random(41)
    stone = (150, 146, 140) if not winter else (210, 216, 226)
    for k in range(22):
        a = k / 22 * math.tau
        x = r.centerx + math.cos(a) * (r.w / 2 + 2)
        y = r.centery + math.sin(a) * (r.h / 2 + 1.5)
        c = lerp_c(stone, darken(stone, 0.3), rng.random())
        xi, yi = int(x) - 1, int(y) - 1
        near.fill(darken(c, 0.3), (xi, yi + 1, 4, 2))
        near.fill(c, (xi, yi, 3, 2))
        near.set_at((xi, yi), lighten(c, 0.25))
    # a tiny sign
    pygame.draw.line(near, (110, 80, 56), (r.right + 5, r.y - 2), (r.right + 5, r.y + 6))
    pygame.draw.rect(near, (176, 136, 92), (r.right + 2, r.y - 6, 8, 5))
    pygame.draw.line(near, (120, 90, 60), (r.right + 3, r.y - 4), (r.right + 8, r.y - 4))
    if ready(g):
        bob = int(math.sin(t * 4) * 1.5)
        pygame.draw.polygon(near, (255, 220, 120), [(r.centerx - 3, r.y - 12 + bob), (r.centerx + 3, r.y - 12 + bob),
                                                    (r.centerx, r.y - 8 + bob)])


# ---------------------------------------------------------------- the Hatchery tab: a pond you can watch
BANNER = (490, 120)          # the pond close-up, in art pixels (drawn at 2x)
_BG = {}


def _blobs(w, h):
    """The pond's outline: three overlapping ovals make a soft kidney shape."""
    return [pygame.Rect(18, 16, int(w * 0.56), h - 34), pygame.Rect(int(w * 0.36), 12, int(w * 0.44), h - 26),
            pygame.Rect(int(w * 0.7), 22, int(w * 0.26), h - 42)]


def _background(season, night, w, h):
    """Grass, the stone rim and the water's depths: everything that doesn't move. Cached."""
    key = (season, night, w, h)
    if key in _BG:
        return _BG[key]
    nf = night / 10
    rng = random.Random(11)
    s = pygame.Surface((w, h))
    grass = ((116, 156, 84), (128, 160, 80), (156, 140, 78), (220, 226, 234))[season]
    grass = lerp_c(grass, (52, 62, 72), nf * 0.65)
    s.fill(grass)
    for _ in range(w * h // 40):
        x, y = rng.randrange(w), rng.randrange(h)
        s.set_at((x, y), darken(grass, 0.1) if rng.random() < 0.6 else lighten(grass, 0.08))
    for _ in range(40):                                  # grass tufts and a few flowers
        x, y = rng.randrange(w), rng.randrange(h)
        d = darken(grass, 0.2)
        s.set_at((x, y), d)
        s.set_at((x - 1, y - 1), d)
        s.set_at((x + 1, y - 1), d)
        if season in (0, 1) and rng.random() < 0.35:
            s.set_at((x, y - 2), lerp_c(rng.choice(((250, 236, 120), (250, 250, 244), (236, 150, 190))),
                                        (60, 60, 90), nf * 0.6))
    blobs = _blobs(w, h)
    water_m = pygame.Surface((w, h), pygame.SRCALPHA)
    for b in blobs:
        pygame.draw.ellipse(water_m, (255, 255, 255, 255), b)
    mask = pygame.mask.from_surface(water_m)
    # the muddy bank, then the water in three depths
    bank = lerp_c((104, 84, 64), (40, 38, 46), nf * 0.6)
    for b in blobs:
        pygame.draw.ellipse(s, bank, b.inflate(10, 8))
    shallow = lerp_c((92, 148, 150), (24, 40, 60), nf * 0.7)
    mid = lerp_c((64, 118, 132), (20, 32, 54), nf * 0.7)
    deep = lerp_c((44, 90, 112), (14, 24, 44), nf * 0.7)
    if season == 3:
        shallow, mid, deep = (lerp_c(c, (190, 210, 222), 0.25 * (1 - nf)) for c in (shallow, mid, deep))
    # depth from how far a spot is from the shore (a blurred copy of the outline), in dithered pixel bands
    import numpy as np
    m = (pygame.surfarray.array_alpha(water_m) > 0).astype(np.float32)
    b = m
    for _ in range(2):
        for r_, ax in ((30, 0), (16, 1)):
            k = np.ones(2 * r_ + 1, np.float32) / (2 * r_ + 1)
            b = np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), ax, b)
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.5
    v = b + np.tile(bayer, (w // 4 + 1, h // 4 + 1))[:w, :h] * 0.08
    rgb = pygame.surfarray.array3d(s)
    edge = lighten(shallow, 0.12)
    for col, lo in ((edge, 0.0), (shallow, 0.3), (mid, 0.5), (deep, 0.7)):
        sel_ = (m > 0) & (v >= lo)
        rgb[sel_] = col
    pygame.surfarray.blit_array(s, rgb)
    # pebbles on the bottom of the shallows
    for _ in range(70):
        x, y = rng.randrange(w), rng.randrange(h)
        if mask.get_at((x, y)) and not all(mask.get_at((min(w - 1, x + dx), y)) for dx in (-12, 12)):
            s.set_at((x, y), lerp_c(shallow, (170, 160, 130), 0.35))
    # stones all round the rim, only where they sit on dry ground
    stone = lerp_c((164, 158, 148), (70, 70, 82), nf * 0.6)
    for b in blobs:
        n = int((b.w + b.h) / 5)
        for k in range(n):
            a = k / n * math.tau + rng.random() * 0.1
            x = b.centerx + math.cos(a) * (b.w / 2 + 3)
            y = b.centery + math.sin(a) * (b.h / 2 + 2.5)
            xi, yi = int(x), int(y)
            if 0 <= xi < w and 0 <= yi < h and mask.get_at((xi, yi)):
                continue
            c = lerp_c(stone, darken(stone, 0.25), rng.random())
            if season == 3:
                c = lerp_c(c, (236, 240, 248), 0.4 * (1 - nf))
            sw = rng.choice((4, 5, 6))
            pygame.draw.ellipse(s, darken(c, 0.3), (xi - sw // 2, yi - 1, sw, 4))
            pygame.draw.ellipse(s, c, (xi - sw // 2, yi - 2, sw, 4))
            s.set_at((xi - 1, yi - 2), lighten(c, 0.25))
    _BG[key] = (s, mask, (shallow, mid, deep))
    if len(_BG) > 12:
        _BG.pop(next(iter(_BG)))
    return _BG[key]


def _inside(mask, x, y, mx=16, my=5):
    w, h = mask.get_size()
    for px, py in ((x, y), (x - mx, y), (x + mx, y), (x, y - my), (x, y + my)):
        px, py = int(px), int(py)
        if not (0 <= px < w and 0 <= py < h) or not mask.get_at((px, py)):
            return False
    return True


def _spot(mask, rng):
    w, h = mask.get_size()
    for _ in range(200):
        x, y = rng.uniform(20, w - 20), rng.uniform(14, h - 14)
        if _inside(mask, x, y, 20, 7):
            return x, y
    return w / 2, h / 2


def _keys(g):
    seen, out = {}, []
    for f in g.hatch['pond']:
        k = (f['id'], f['v'], f['day'], round(f['size'], 1))
        seen[k] = seen.get(k, 0) + 1
        out.append(k + (seen[k],))
    return out


def _sim(g, t, mask):
    """Moves the pond fish: each one wanders to a spot, sometimes rests there, and keeps clear of the others."""
    sim = g.__dict__.get('_pond_sim')
    if sim is None or sim['size'] != mask.get_size():
        sim = g._pond_sim = {'fish': {}, 't': t, 'rings': [], 'rng': random.Random(5), 'size': mask.get_size()}
    dt = max(0.0, min(0.1, t - sim['t']))
    sim['t'] = t
    rng = sim['rng']
    keys = _keys(g)
    agents = sim['fish']
    for k in list(agents):
        if k not in keys:
            del agents[k]
    for k in keys:
        if k not in agents:
            x, y = _spot(mask, rng)
            agents[k] = dict(x=x, y=y, vx=0.0, vy=0.0, tx=x, ty=y, wait=rng.uniform(0, 1.5),
                             face=rng.choice((-1, 1)), ph=rng.random() * 6, depth=rng.random(),
                             dz=rng.random(), top=rng.uniform(9, 15))
    for k in keys:
        a = agents[k]
        dx, dy = a['tx'] - a['x'], a['ty'] - a['y']
        d = math.hypot(dx, dy)
        wx = wy = 0.0
        if a['wait'] > 0:
            a['wait'] -= dt
        elif d < 4:
            a['tx'], a['ty'] = _spot(mask, rng)
            a['wait'] = rng.uniform(0.6, 3.0) if rng.random() < 0.5 else 0.0
            a['top'] = rng.uniform(10, 22)
            a['dz'] = rng.random()
        else:
            sp = a['top'] * min(1.0, d / 26 + 0.15)
            wx, wy = dx / d * sp, dy / d * sp * 0.7
        for b in agents.values():                       # keep a little room between fish
            if b is a:
                continue
            ex, ey = a['x'] - b['x'], (a['y'] - b['y']) * 2.2
            e = math.hypot(ex, ey)
            if 0 < e < 30:
                push = (30 - e) / 30 * 9
                wx += ex / e * push
                wy += ey / e * push * 0.4
        kk = min(1.0, dt * 1.4)
        a['vx'] += (wx - a['vx']) * kk
        a['vy'] += (wy - a['vy']) * kk
        nx, ny = a['x'] + a['vx'] * dt, a['y'] + a['vy'] * dt
        if _inside(mask, nx, ny):
            a['x'], a['y'] = nx, ny
        else:
            a['vx'] *= -0.4
            a['vy'] *= -0.4
            a['tx'], a['ty'] = _spot(mask, rng)
        if a['vx'] > 1.2:
            a['face'] = 1
        elif a['vx'] < -1.2:
            a['face'] = -1
        spd = math.hypot(a['vx'], a['vy'])
        a['ph'] += dt * (3.0 + spd * 0.7)
        a['depth'] += (a['dz'] - a['depth']) * min(1.0, dt * 0.4)
        if rng.random() < dt * 0.05 and a['depth'] < 0.35:     # now and then one noses the surface
            sim['rings'].append([a['x'] + a['face'] * 10, a['y'], t])
    sim['rings'] = [r for r in sim['rings'] if t - r[2] < 1.6][-8:]
    return [agents[k] for k in keys], sim


def _wag(spr, ph, amp):
    """The back of the fish (its tail end, on the left of the sprite) sways up and down."""
    w, h = spr.get_size()
    out = pygame.Surface((w, h + 2), pygame.SRCALPHA)
    out.blit(spr, (0, 1))
    if amp <= 0:
        return out
    tail = int(w * 0.45)
    out.fill((0, 0, 0, 0), (0, 0, tail, h + 2))
    for x in range(tail):
        k = 1 - x / tail
        off = int(round(math.sin(ph - x * 0.22) * amp * k))
        out.blit(spr, (x, 1 + off), (x, 0, 1, h))
    return out


def _tint(spr, col, k):
    """spr seen through k of the water above it."""
    if k <= 0.02:
        return spr
    out = spr.copy()
    m = int(255 * (1 - k))
    out.fill((m, m, m, 255), special_flags=pygame.BLEND_RGBA_MULT)
    out.fill((int(col[0] * k), int(col[1] * k), int(col[2] * k), 0), special_flags=pygame.BLEND_RGB_ADD)
    return out


def _reeds(s, x, y, t, season, n=5):
    col = (92, 138, 70) if season != 3 else (160, 150, 120)
    for k in range(n):
        h = 10 + (k * 7) % 6
        bx = x - n + k * 2
        sway = math.sin(t * 1.1 + k * 0.9) * 1.2
        pygame.draw.line(s, darken(col, 0.15 * (k % 2)), (bx, y), (int(bx + sway), y - h))
        if k % 2 == 0 and season in (1, 2):
            s.fill((120, 82, 56), (int(bx + sway), y - h - 2, 1, 3))


def _closeup(g, t, w, h, sel=None):
    """The pond, alive: returns the picture and where each fish is (art pixels)."""
    from data import FISH_BY_ID
    env = g.env
    bg, mask, (shallow, mid, deep) = _background(env.season, int(round(env.nf * 10)), w, h)
    s = bg.copy()
    fish, sim = _sim(g, t, mask)
    blobs = _blobs(w, h)
    # glints drifting across the water
    if env.nf < 0.7:
        for k in range(14):
            x = int((k * 53 + t * (3 + k % 3)) % w)
            y = int(14 + (k * 29) % (h - 28) + math.sin(t * 0.7 + k) * 2)
            if mask.get_at((x, y)) and math.sin(t * 1.3 + k * 1.7) > 0.2:
                s.fill(lighten(shallow, 0.45), (x, y, 2 + k % 3, 1))
    # the fish: shadows on the bottom first, deep ones first
    order = sorted(range(len(fish)), key=lambda i: -fish[i]['depth'])
    sprites = []
    for i in order:
        a = fish[i]
        f = g.hatch['pond'][i]
        spr = morphs.sprite(FISH_BY_ID[f['id']], f['v'], 1)
        moving = math.hypot(a['vx'], a['vy'])
        spr = _wag(spr, a['ph'], 1.0 if moving > 1 else 0.5)
        if a['face'] < 0:
            spr = pygame.transform.flip(spr, True, False)
        sprites.append((i, a, spr))
    for i, a, spr in sprites:
        sh = spr.copy()
        sh.fill((0, 0, 0, 60), special_flags=pygame.BLEND_RGBA_MULT)
        off = 3 + int((1 - a['depth']) * 4)
        s.blit(sh, sh.get_rect(center=(int(a['x']) + 2, int(a['y']) + off)))
    for i, a, spr in sprites:
        spr = _tint(spr, deep, 0.15 + a['depth'] * 0.4)
        s.blit(spr, spr.get_rect(center=(int(a['x']), int(a['y']))))
        if sel == i:
            bob = int(math.sin(t * 5) * 1.5)
            x, y = int(a['x']), int(a['y']) - 12 + bob
            pts = [(x - 5, y - 5), (x + 5, y - 5), (x, y)]
            pygame.draw.polygon(s, (255, 226, 120), pts)
            pygame.draw.polygon(s, (120, 80, 30), pts, 1)
    # rings where a fish touched the surface
    ring = pygame.Surface((w, h), pygame.SRCALPHA)
    for x, y, t0 in sim['rings']:
        k = (t - t0) / 1.6
        rw = int(4 + k * 18)
        pygame.draw.ellipse(ring, lighten(shallow, 0.5) + (int(170 * (1 - k)),),
                            (int(x) - rw // 2, int(y) - rw // 4, rw, max(2, rw // 2)), 1)
    s.blit(ring, (0, 0))
    # reeds at each end, with eggs or fry tucked in them
    ends = [(blobs[0].x + 16, blobs[0].centery + 10), (blobs[2].right - 14, blobs[2].centery + 8)]
    for j, c in enumerate(g.hatch['clutches'][:2]):
        ex, ey = ends[j]
        st = stage(g, c)
        if st == 0:
            for k in range(9):
                px = ex - 5 + (k % 3) * 3 + (k // 3) % 2
                py = ey - 2 + (k // 3) * 2 + int(math.sin(t * 1.2 + k) * 0.6)
                s.set_at((px, py), (246, 242, 222))
                s.set_at((px + 1, py), (214, 206, 176))
        else:
            spec = FISH_BY_ID[c['id']]
            col = (230, 226, 206) if st == 1 else spec['c1']
            n = c['n'] * 2 if st == 1 else c['n']
            cx = ex + (24 if j == 0 else -24) + math.sin(t * 0.5 + j) * 16
            cy = ey - 4 + math.cos(t * 0.37 + j) * 5
            for k in range(n):
                lag = k * 0.35
                px = cx + math.sin(t * 0.5 - lag + j) * 16 * (1 - k * 0.04) + math.sin(k * 2.4) * 5
                py = cy + math.cos(t * 0.37 - lag) * 5 + math.cos(k * 1.7) * 3
                right = math.cos(t * 0.5 - lag + j) > 0
                if st == 1:
                    s.fill(col, (int(px), int(py), 3, 1))
                    s.set_at((int(px) + (2 if right else 0), int(py)), (40, 40, 50))
                else:
                    s.fill(col, (int(px), int(py), 5, 2))
                    s.set_at((int(px) + (4 if right else 0), int(py)), (30, 30, 40))
                    s.set_at((int(px) + (0 if right else 4), int(py) + 1), darken(col, 0.3))
    for j, (ex, ey) in enumerate(ends):
        _reeds(s, ex, ey + 4, t + j * 3, env.season, 6)
    # lily pads, riding the water
    if env.season != 3:
        pads = [(blobs[1].centerx + 40, blobs[1].y + 18), (blobs[0].x + 70, blobs[0].bottom - 16),
                (blobs[2].centerx, blobs[2].y + 12)]
        for k, (x, y) in enumerate(pads):
            y += int(math.sin(t * 0.8 + k * 2) * 0.7)
            pc = lerp_c((86, 146, 78), (30, 50, 50), env.nf * 0.6)
            pygame.draw.ellipse(s, darken(pc, 0.25), (x - 6, y - 2, 13, 6))
            pygame.draw.ellipse(s, pc, (x - 6, y - 3, 13, 6))
            pygame.draw.line(s, mid, (x, y), (x + 6, y - 1))
            if k == 0 and env.season in (0, 1):
                s.fill((246, 170, 196), (x - 2, y - 4, 3, 2))
                s.set_at((x - 1, y - 5), (255, 236, 244))
    # fireflies after dark
    if env.nf > 0.5 and env.season in (0, 1, 2):
        for k in range(7):
            x = int((k * 71 + math.sin(t * 0.4 + k) * 20) % w)
            y = int(10 + (k * 37) % (h - 20) + math.sin(t * 0.9 + k * 2) * 6)
            if math.sin(t * 2.1 + k * 1.3) > 0.1:
                s.set_at((x, y), (250, 240, 140))
                if math.sin(t * 2.1 + k * 1.3) > 0.7:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        s.set_at((x + dx, y + dy), (190, 180, 90))
    return s, fish


def draw_tab(g, s, rect):
    from data import FISH_BY_ID, RARITY_COLORS
    ui = g.ui
    hd = g.hatch
    t = g.t
    sel = g.hatch_sel if g.hatch_sel is not None and g.hatch_sel < len(hd['pond']) else None
    # the pond across the top
    view = pygame.Rect(rect.x + 30, rect.y + 90, BANNER[0] * 2, BANNER[1] * 2)
    small, fish = _closeup(g, t, BANNER[0], BANNER[1], sel)
    s.blit(ui._frame(view.w + 16, view.h + 16, (120, 86, 60), (84, 58, 42), 2), view.inflate(16, 16))
    s.blit(pygame.transform.scale(small, view.size), view)
    for i, a in enumerate(fish):
        hit = pygame.Rect(view.x + int(a['x']) * 2 - 34, view.y + int(a['y']) * 2 - 18, 68, 36)
        ui.hotspot(hit, lambda i=i: _select(g, i))
    if not hd['pond'] and not hd['clutches']:
        ui.blit_text(s, 'The pond is empty. Coloured catches come here, or bring a pair from the basket.',
                     (view.centerx, view.centery), 'smallb', (250, 250, 240), 'center', outline=(30, 60, 70))
    y0 = view.bottom + 22
    c1 = pygame.Rect(view.x, y0, 330, rect.bottom - 20 - y0)
    c2 = pygame.Rect(c1.right + 22, y0, 300, c1.h)
    c3 = pygame.Rect(c2.right + 22, y0, view.right - c2.right - 22, c1.h)
    # ---- the fish in the pond
    ui.blit_text(s, 'In the pond', (c1.x, c1.y), 'h3', U.INK)
    ui.blit_text(s, '%d / %d' % (len(hd['pond']), POND), (c1.right, c1.y + 4), 'smallb', U.SOFT, 'topright')
    tw = (c1.w - 8) // 2
    for i in range(POND):
        r = pygame.Rect(c1.x + (i % 2) * (tw + 8), c1.y + 34 + (i // 2) * 50, tw, 44)
        if i >= len(hd['pond']):
            pygame.draw.rect(s, (236, 226, 206), r, 2, border_radius=8)
            continue
        f = hd['pond'][i]
        spec = FISH_BY_ID[f['id']]
        on = i == sel
        rim = morphs.MORPH_BY_ID[f['v']]['col'] if f['v'] else RARITY_COLORS[spec['rarity']]
        ui.tile(s, r, (255, 246, 214) if on else (250, 244, 228), rim)
        ic = morphs.sprite(spec, f['v'], 1)
        s.blit(ic, ic.get_rect(center=(r.x + 28, r.centery)))
        ui.blit_text(s, spec['name'], (r.x + 54, r.y + 4), 'tiny', U.INK, maxw=r.w - 58)
        ui.blit_text(s, (morphs.MORPH_BY_ID[f['v']]['name'] + '  ' if f['v'] else '') + '%d cm' % round(f['size']),
                     (r.x + 54, r.y + 22), 'tiny', darken(rim, 0.2) if f['v'] else U.SOFT, maxw=r.w - 58)
        if on:
            pygame.draw.rect(s, (230, 180, 70), r, 3, border_radius=8)
        ui.hotspot(r, lambda i=i: _select(g, i))
    ay = c1.y + 34 + 3 * 50 + 4
    if sel is not None:
        f = hd['pond'][sel]
        full = len(g.tank) >= g.tank_size()
        bw = (c1.w - 12) // 3
        ui.button(s, (c1.x, ay, bw, 38), 'Sell %d' % f['price'], lambda: sell(g, sel), 'gold', font='smallb')
        ui.button(s, (c1.x + bw + 6, ay, bw, 38), 'Tank full' if full else 'To tank', lambda: to_tank(g, sel),
                  'normal', enabled=not full, font='smallb')
        ui.button(s, (c1.x + 2 * (bw + 6), ay, bw, 38), 'Release', lambda: release(g, sel), 'rose', font='smallb')
        if not f['v']:
            ui.button(s, (c1.x, ay + 44, c1.w, 28), 'Back to the basket', lambda: to_basket(g, sel), 'normal',
                      font='tiny')
        else:
            ui.blit_text(s, 'Releasing it stocks the lake with %s %s for a week.'
                         % (morphs.MORPH_BY_ID[f['v']]['name'].lower(), spec_name(f)),
                         (c1.x, ay + 46), 'tiny', U.SOFT, maxw=c1.w)
    elif hd['pond']:
        ui.blit_text(s, 'Pick a fish (here or in the pond) to sell it,', (c1.x, ay + 6), 'tiny', U.SOFT, maxw=c1.w)
        ui.blit_text(s, 'move it to the tank or let it go.', (c1.x, ay + 26), 'tiny', U.SOFT, maxw=c1.w)
    # ---- the clutches
    ui.blit_text(s, 'Clutches', (c2.x, c2.y), 'h3', U.INK)
    if not hd['clutches']:
        pr = pairs(g)
        txt = ('A pair of %s will lay eggs at dawn.' % FISH_BY_ID[pr[0]]['name'] if pr else
               'Two fish of a kind lay eggs after a night together in the pond.')
        for k, line in enumerate(ui.wrap(txt, 'small', c2.w)[:3]):
            ui.blit_text(s, line, (c2.x, c2.y + 40 + k * 24), 'small', U.SOFT)
    for i, c in enumerate(hd['clutches']):
        spec = FISH_BY_ID[c['id']]
        r = pygame.Rect(c2.x, c2.y + 34 + i * 96, c2.w, 88)
        st = stage(g, c)
        ui.tile(s, r, (250, 244, 228), (120, 176, 120) if st == 2 else (150, 186, 200))
        ic = morphs.sprite(spec, next((v for v in c['pv'] if v), None), 1)
        s.blit(ic, ic.get_rect(center=(r.x + 30, r.y + 26)))
        ui.blit_text(s, spec['name'], (r.x + 58, r.y + 8), 'smallb', U.INK, maxw=r.w - 66)
        vx = r.x + 58
        for v in dict.fromkeys(x for x in c['pv'] if x):
            bw = ui.fonts['tiny'].size(morphs.MORPH_BY_ID[v]['name'])[0] + 20
            br = morphs.badge(s, ui, v, (vx + bw // 2, r.y + 40))
            vx = br.right + 6
        # eggs, fry, ready: three steps along the bottom
        age = g.day - c['day']
        for k, word in enumerate(('Eggs', 'Fry', 'Ready')):
            px = r.x + 18 + k * 64
            done = st >= k
            pygame.draw.circle(s, (126, 176, 112) if done else (222, 212, 194), (px, r.bottom - 18), 6)
            ui.blit_text(s, word, (px + 10, r.bottom - 18), 'tiny', U.INK if st == k else U.SOFT, 'midleft')
        if st == 2:
            ui.button(s, (r.right - 102, r.bottom - 38, 92, 30), 'Collect', lambda i=i: collect(g, i), 'gold',
                      font='smallb')
        else:
            left = (HATCH_DAY if st == 0 else GROWN_DAY) - age
            ui.blit_text(s, '%d day%s' % (left, '' if left == 1 else 's'), (r.right - 12, r.bottom - 18), 'tiny',
                         U.SOFT, 'midright')
    # ---- from the basket, and the colours found
    ui.blit_text(s, 'Add from the basket', (c3.x, c3.y + 4), 'smallb', U.INK)
    kinds = basket_kinds(g)
    if not kinds:
        ui.blit_text(s, 'No pond fish in the basket.', (c3.x, c3.y + 40), 'tiny', U.SOFT)
    tw = (c3.w - 12) // 3
    for k, (sid, n) in enumerate(kinds[:6]):
        spec = FISH_BY_ID[sid]
        r = pygame.Rect(c3.x + (k % 3) * (tw + 6), c3.y + 32 + (k // 3) * 50, tw, 44)
        ok = room(g) > 0
        hov = ok and r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 248, 236) if hov else (244, 236, 218), RARITY_COLORS[spec['rarity']])
        ic = morphs.sprite(spec, None, 1)
        s.blit(ic, ic.get_rect(center=(r.centerx - 8, r.centery)))
        ui.blit_text(s, 'x%d' % n, (r.right - 6, r.bottom - 4), 'tiny', U.INK, 'bottomright')
        if ok:
            ui.hotspot(r, lambda sid=sid: from_basket(g, sid))
    vy = c3.y + 140
    ui.blit_text(s, 'Colours found', (c3.x, vy), 'smallb', U.INK)
    ui.blit_text(s, '%d kinds' % kinds_found(g), (c3.right, vy + 2), 'tiny', U.SOFT, 'topright')
    mw = (c3.w + 6) // len(morphs.MORPHS)
    tip = None
    for k, m in enumerate(morphs.MORPHS):
        n = len(hd['found'].get(m['id'], []))
        r = pygame.Rect(c3.x + k * mw, vy + 28, mw - 6, 36)
        ui.tile(s, r, (250, 244, 228) if n else (232, 224, 210), m['col'] if n else (200, 190, 176))
        pygame.draw.circle(s, m['col'] if n else (206, 198, 186), r.center, 9)
        if n:
            pygame.draw.circle(s, lighten(m['col'], 0.4), (r.centerx - 3, r.centery - 3), 2)
        else:
            ui.blit_text(s, '?', r.center, 'tiny', U.SOFT, 'center')
        if r.collidepoint(ui.mouse):
            tip = (m, n)
    if tip:
        m, n = tip
        txt = (m['name'] + ': ' + m['desc']) if n else 'Not found yet. ' + {
            'night': 'It only bites after dark.', 'rain': 'It only bites in the rain.'}.get(m.get('when'), 'Keep fishing!')
        for k, line in enumerate(ui.wrap(txt, 'tiny', c3.w)[:3]):
            ui.blit_text(s, line, (c3.x, vy + 72 + k * 20), 'tiny', U.SOFT)
    else:
        ui.blit_text(s, 'Point at a colour to read about it.', (c3.x, vy + 72), 'tiny', U.SOFT, maxw=c3.w)


def spec_name(f):
    from data import FISH_BY_ID
    return FISH_BY_ID[f['id']]['name']


def _select(g, i):
    g.hatch_sel = None if g.hatch_sel == i else i
    g.audio.play('ui', 0.4)
