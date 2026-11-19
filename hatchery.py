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
    """The pond on the slope: a ring of stones, still water, the fish as little coloured shapes."""
    env = g.env
    r = POND_RECT
    sky = env.sky[2]
    water = lerp_c((56, 104, 118), sky, 0.25)
    water = lerp_c(water, (20, 26, 44), env.nf * 0.6)
    pygame.draw.ellipse(near, (92, 74, 58), r.inflate(6, 4))
    pygame.draw.ellipse(near, water, r)
    pygame.draw.ellipse(near, lighten(water, 0.18), (r.x + 4, r.y + 2, r.w - 8, 4))
    rng = random.Random(41)
    for k in range(18):
        a = k / 18 * math.tau
        x = r.centerx + math.cos(a) * (r.w / 2 + 2)
        y = r.centery + math.sin(a) * (r.h / 2 + 1.5)
        c = lerp_c((150, 146, 140), (118, 112, 106), rng.random())
        if env.season == 3:
            c = lerp_c(c, (236, 240, 248), 0.5)
        pygame.draw.rect(near, c, (int(x) - 1, int(y) - 1, 3, 2))
    # reeds at the back left, eggs under them
    for k, dx in enumerate((3, 6, 8)):
        top = r.y - 6 - k * 2
        pygame.draw.line(near, (92, 134, 70) if env.season != 3 else (150, 140, 110), (r.x + dx, r.y + 4),
                         (r.x + dx + 1, top))
    for c in g.hatch['clutches']:
        st = stage(g, c)
        if st == 0:
            for k in range(5):
                near.set_at((r.x + 6 + k % 3, r.y + 6 + k // 3), (240, 236, 214))
        else:
            for k in range(4):
                x = r.x + 10 + (k * 7 + int(t * 10 + k * 3)) % 26
                y = r.y + 6 + int(math.sin(t * 3 + k) * 2)
                near.set_at((x, y), (220, 220, 200) if st == 1 else (240, 200, 120))
    # the fish: a two-pixel streak in their colour
    from data import FISH_BY_ID
    for f, (x, y, right) in zip(g.hatch['pond'], _pond_fish(g, t, r.w - 10, r.h - 8, r.x + 5, r.y + 4)):
        spec = FISH_BY_ID[f['id']]
        col = morphs.MORPH_BY_ID[f['v']]['col'] if f['v'] else spec['c1']
        xi, yi = int(x), int(y)
        near.fill(col, (xi - 2, yi, 4, 1))
        near.set_at((xi + (2 if right else -3), yi), darken(col, 0.3))
    # a lily pad, and a tiny sign
    if env.season != 3:
        pygame.draw.ellipse(near, (86, 140, 76), (r.right - 16, r.y + 8, 7, 3))
    pygame.draw.line(near, (110, 80, 56), (r.right + 4, r.y - 2), (r.right + 4, r.y + 6))
    pygame.draw.rect(near, (176, 136, 92), (r.right + 1, r.y - 6, 8, 5))
    pygame.draw.line(near, (120, 90, 60), (r.right + 2, r.y - 4), (r.right + 7, r.y - 4))
    if ready(g):
        bob = int(math.sin(t * 4) * 1.5)
        pygame.draw.polygon(near, (255, 220, 120), [(r.centerx - 3, r.y - 12 + bob), (r.centerx + 3, r.y - 12 + bob),
                                                    (r.centerx, r.y - 8 + bob)])


def _closeup(g, t, w, h):
    """The pond close up, for the tab: real fish sprites gliding about."""
    from data import FISH_BY_ID
    env = g.env
    s = pygame.Surface((w, h))
    grass = lerp_c((116, 150, 84), (60, 70, 74), env.nf * 0.6)
    if env.season == 3:
        grass = lerp_c((222, 228, 236), (90, 96, 120), env.nf * 0.6)
    elif env.season == 2:
        grass = lerp_c((150, 136, 78), (64, 62, 66), env.nf * 0.6)
    s.fill(grass)
    rng = random.Random(7)
    for _ in range(140):
        x, y = rng.randrange(w), rng.randrange(h)
        s.set_at((x, y), darken(grass, 0.12) if rng.random() < 0.6 else lighten(grass, 0.1))
    pond = pygame.Rect(10, 10, w - 20, h - 18)
    water = lerp_c((58, 112, 128), (22, 30, 52), env.nf * 0.7)
    pygame.draw.ellipse(s, (96, 80, 64), pond.inflate(8, 8))
    pygame.draw.ellipse(s, water, pond)
    deep = darken(water, 0.18)
    pygame.draw.ellipse(s, deep, pond.inflate(-40, -26))
    for k in range(40):
        a = k / 40 * math.tau
        x = pond.centerx + math.cos(a) * (pond.w / 2 + 3)
        y = pond.centery + math.sin(a) * (pond.h / 2 + 3)
        c = lerp_c((158, 152, 146), (116, 110, 104), rng.random())
        pygame.draw.ellipse(s, c, (int(x) - 3, int(y) - 2, 6, 4))
    # eggs and fry among the reeds on the left
    for j, c in enumerate(g.hatch['clutches']):
        ex, ey = pond.x + 24 + j * 30, pond.bottom - 22
        for k in range(4):
            pygame.draw.line(s, (86, 128, 66), (ex - 6 + k * 4, ey + 6), (ex - 7 + k * 4, ey - 14 - k % 2 * 4))
        st = stage(g, c)
        if st == 0:
            for k in range(9):
                pygame.draw.circle(s, (244, 240, 218), (ex - 4 + (k % 3) * 4, ey - 2 + (k // 3) * 3), 1)
        else:
            for k in range(c['n'] * 2):
                x = ex + int(math.sin(t * 1.4 + k * 1.9) * 16)
                y = ey - 4 + int(math.cos(t * 1.1 + k * 2.3) * 5)
                col = (230, 226, 206) if st == 1 else (238, 196, 120)
                s.fill(col, (x, y, 3 if st == 1 else 4, 1))
    # the fish
    for f, (x, y, right) in zip(g.hatch['pond'], _pond_fish(g, t, pond.w - 60, pond.h - 30, pond.x + 30,
                                                             pond.y + 12)):
        spec = FISH_BY_ID[f['id']]
        spr = morphs.sprite(spec, f['v'], 1)
        if not right:
            spr = pygame.transform.flip(spr, True, False)
        sh = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
        sh.blit(spr, (0, 0))
        sh.fill((0, 0, 0, 70), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(sh, sh.get_rect(center=(int(x) + 2, int(y) + 4)))
        s.blit(spr, spr.get_rect(center=(int(x), int(y))))
    # lily pads and glints on top
    for (x, y) in ((pond.right - 40, pond.y + 16), (pond.right - 26, pond.bottom - 18), (pond.x + 60, pond.y + 10)):
        if env.season != 3:
            pygame.draw.ellipse(s, (88, 148, 80), (x, y, 14, 7))
            pygame.draw.line(s, water, (x + 7, y + 3), (x + 13, y + 3))
    for k in range(6):
        x = pond.x + 20 + (k * 37 + int(t * 6)) % (pond.w - 40)
        y = pond.y + 8 + (k * 13) % (pond.h - 16)
        if math.sin(t * 2 + k) > 0.3:
            s.fill(lighten(water, 0.5), (x, y, 3, 1))
    return s


def draw_tab(g, s, rect):
    from data import FISH_BY_ID, RARITY_COLORS
    ui = g.ui
    hd = g.hatch
    t = g.t
    # the pond, close up
    view = pygame.Rect(rect.x + 30, rect.y + 90, 480, 260)
    small = _closeup(g, t, view.w // 2, view.h // 2)
    pygame.draw.rect(s, (120, 80, 54), view.inflate(16, 16), border_radius=12)
    s.blit(pygame.transform.scale(small, view.size), view)
    pygame.draw.rect(s, (150, 104, 70), view.inflate(8, 8), 3, border_radius=10)
    if not hd['pond'] and not hd['clutches']:
        ui.blit_text(s, 'The pond is empty. Coloured catches come here,', (view.centerx, view.centery - 14),
                     'smallb', (250, 250, 240), 'center', (30, 60, 70))
        ui.blit_text(s, 'or bring a pair from the basket.', (view.centerx, view.centery + 12),
                     'smallb', (250, 250, 240), 'center', (30, 60, 70))
    # the clutches under it
    y = view.bottom + 18
    ui.blit_text(s, 'Clutches', (view.x, y), 'h3', U.INK)
    if not hd['clutches']:
        pr = pairs(g)
        if pr:
            txt = 'A pair of %s will lay eggs at dawn.' % FISH_BY_ID[pr[0]]['name']
        else:
            txt = 'Two fish of a kind lay eggs after a night together.'
        ui.blit_text(s, txt, (view.x + 130, y + 6), 'small', U.SOFT, maxw=view.w - 130)
    for i, c in enumerate(hd['clutches']):
        spec = FISH_BY_ID[c['id']]
        r = pygame.Rect(view.x, y + 34 + i * 54, view.w, 48)
        ui.tile(s, r, (250, 244, 228), (150, 186, 200))
        ic = morphs.sprite(spec, next((v for v in c['pv'] if v), None), 1)
        s.blit(ic, ic.get_rect(center=(r.x + 32, r.centery)))
        st = stage(g, c)
        age = g.day - c['day']
        words = ('Eggs: they hatch in %d day%s' % (HATCH_DAY - age, '' if HATCH_DAY - age == 1 else 's'),
                 'Fry: ready in %d day%s' % (GROWN_DAY - age, '' if GROWN_DAY - age == 1 else 's'),
                 '%d young, ready!' % c['n'])[st]
        ui.blit_text(s, spec['name'], (r.x + 64, r.y + 4), 'smallb', U.INK, maxw=r.w - 200)
        ui.blit_text(s, words, (r.x + 64, r.y + 26), 'tiny', (90, 140, 70) if st == 2 else U.SOFT,
                     maxw=r.w - 180)
        # the parents' colours, after the name
        vx = r.x + 64 + min(r.w - 200, ui.fonts['smallb'].size(spec['name'])[0]) + 12
        for v in dict.fromkeys(x for x in c['pv'] if x):
            bw = ui.fonts['tiny'].size(morphs.MORPH_BY_ID[v]['name'])[0] + 20
            br = morphs.badge(s, ui, v, (vx + bw // 2, r.y + 15))
            vx = br.right + 6
        if st == 2:
            ui.button(s, (r.right - 106, r.y + 8, 96, 32), 'Collect', lambda i=i: collect(g, i), 'gold',
                      font='smallb')
    # right column: the fish in the pond
    x0 = view.right + 34
    cw = rect.right - 30 - x0
    y = rect.y + 88
    ui.blit_text(s, 'In the pond  %d / %d' % (len(hd['pond']), POND), (x0, y), 'h3', U.INK)
    sel = g.hatch_sel
    for i, f in enumerate(hd['pond']):
        spec = FISH_BY_ID[f['id']]
        r = pygame.Rect(x0 + (i % 2) * (cw // 2 + 4), y + 36 + (i // 2) * 52, cw // 2 - 4, 48)
        on = i == sel
        ui.tile(s, r, (255, 246, 214) if on else (250, 244, 228),
                morphs.MORPH_BY_ID[f['v']]['col'] if f['v'] else RARITY_COLORS[spec['rarity']])
        ic = morphs.sprite(spec, f['v'], 1)
        s.blit(ic, ic.get_rect(center=(r.x + 30, r.centery)))
        ui.blit_text(s, spec['name'], (r.x + 58, r.y + 4), 'tiny', U.INK, maxw=r.w - 62)
        ui.blit_text(s, (morphs.MORPH_BY_ID[f['v']]['name'] + '  ' if f['v'] else '') + '%.1f cm' % f['size'],
                     (r.x + 58, r.y + 24), 'tiny', morphs.MORPH_BY_ID[f['v']]['col'] if f['v'] else U.SOFT,
                     maxw=r.w - 62)
        if on:
            pygame.draw.rect(s, (230, 180, 70), r, 3, border_radius=8)
        ui.hotspot(r, lambda i=i: _select(g, i))
    ay = y + 36 + 3 * 52 + 6
    if sel is not None and sel < len(hd['pond']):
        f = hd['pond'][sel]
        full = len(g.tank) >= g.tank_size()
        bw = (cw - 12) // 3
        ui.button(s, (x0, ay, bw, 40), 'Sell %d' % f['price'], lambda: sell(g, sel), 'gold', font='smallb')
        ui.button(s, (x0 + bw + 6, ay, bw, 40), 'Tank full' if full else 'To tank', lambda: to_tank(g, sel),
                  'normal', enabled=not full, font='smallb')
        ui.button(s, (x0 + 2 * (bw + 6), ay, bw, 40), 'Release', lambda: release(g, sel), 'rose', font='smallb')
        if not f['v']:
            ui.button(s, (x0, ay + 46, cw, 30), 'Back to the basket', lambda: to_basket(g, sel), 'normal',
                      font='tiny')
        elif f['v']:
            ui.blit_text(s, 'Releasing it stocks the lake with %s %s for a week.'
                         % (morphs.MORPH_BY_ID[f['v']]['name'].lower(), spec_name(f)),
                         (x0, ay + 50), 'tiny', U.SOFT, maxw=cw)
    else:
        ui.blit_text(s, 'Click a fish to sell it, move it to the tank or', (x0, ay + 4), 'tiny', U.SOFT, maxw=cw)
        ui.blit_text(s, 'let it go. Coloured ones stock the lake.', (x0, ay + 24), 'tiny', U.SOFT, maxw=cw)
    # from the basket
    by = ay + 88
    kinds = basket_kinds(g)
    ui.blit_text(s, 'Add from the basket', (x0, by), 'smallb', U.INK)
    if not kinds:
        ui.blit_text(s, 'No pond fish in the basket right now.', (x0, by + 30), 'tiny', U.SOFT)
    for k, (sid, n) in enumerate(kinds[:6]):
        spec = FISH_BY_ID[sid]
        r = pygame.Rect(x0 + k * ((cw + 6) // 6), by + 26, (cw + 6) // 6 - 6, 44)
        ok = room(g) > 0
        hov = ok and r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 248, 236) if hov else (244, 236, 218), RARITY_COLORS[spec['rarity']])
        ic = morphs.sprite(spec, None, 1)
        ic = pygame.transform.scale(ic, (ic.get_width() * 3 // 4, ic.get_height() * 3 // 4))
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 18)))
        ui.blit_text(s, 'x%d' % n, (r.right - 4, r.bottom - 2), 'tiny', U.INK, 'bottomright')
        if ok:
            ui.hotspot(r, lambda sid=sid: from_basket(g, sid))
    # the variants found, along the bottom
    vy = rect.bottom - 86
    ui.blit_text(s, 'Colours found', (x0, vy), 'smallb', U.INK)
    ui.blit_text(s, '%d kinds' % kinds_found(g), (x0 + cw, vy), 'tiny', U.SOFT, 'topright')
    mw = (cw + 6) // 6
    for k, m in enumerate(morphs.MORPHS):
        n = len(hd['found'].get(m['id'], []))
        r = pygame.Rect(x0 + k * mw, vy + 24, mw - 6, 46)
        ui.tile(s, r, (250, 244, 228) if n else (232, 224, 210), m['col'] if n else (200, 190, 176))
        pygame.draw.circle(s, m['col'] if n else (200, 192, 182), (r.centerx, r.y + 14), 8)
        ui.blit_text(s, m['name'] if n else '?', (r.centerx, r.y + 26), 'tiny', U.INK if n else U.SOFT, 'midtop',
                     maxw=r.w - 4)
        if r.collidepoint(ui.mouse):
            g.hatch_tip = m
    tip = getattr(g, 'hatch_tip', None)
    g.hatch_tip = None
    if tip:
        n = len(hd['found'].get(tip['id'], []))
        ui.blit_text(s, tip['desc'] if n else 'Not found yet. ' + {'night': 'It only bites after dark.',
                                                                  'rain': 'It only bites in the rain.'}.get(
            tip.get('when'), 'Keep fishing!'), (x0, vy - 22), 'tiny', U.SOFT, maxw=cw)


def spec_name(f):
    from data import FISH_BY_ID
    return FISH_BY_ID[f['id']]['name']


def _select(g, i):
    g.hatch_sel = None if g.hatch_sel == i else i
    g.audio.play('ui', 0.4)
