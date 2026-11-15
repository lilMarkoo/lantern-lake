"""Ways to fish that change with the seasons.

  Crab pot      buy one at the shop, set it off the dock in the evening (E or click it), check it the next
                morning. Crayfish, crabs, snails and the odd treasure.
  Fly casting   with the Fly Rod, casting at Willow Creek is a rhythm: tap on three beats as the line loops
                overhead. Good rhythm casts further, brings rarer fish, and only a good cast tempts the
                fly-only fish.
  Ice fishing   in winter Lily Cove freezes over. With an Ice Auger, drill a hole and jig for winter fish
                (icefish.py has the scene).
  Rare nights   a summer or autumn rain night can turn into a thunderstorm (Thunderfin rise), and a clear
                winter night can bring the northern lights (Northern Lightfish).

State on Game: pot = {'set': day or None, 'corn': bool}, sky = 'storm' / 'aurora' / None (tonight).
"""
import math
import random

import pygame

import art
import ui as U
from art import HORIZON, DECK_Y, W, H, lerp_c
from data import FISH, FISH_BY_ID, JUNK_BY_ID, ALL_BY_ID

POT_X = 152                     # where the crab pot sits on the deck
FLOAT_X, FLOAT_Y = 268, 300     # its float once it's in the water
FLY_BEAT = 0.72                 # seconds between the line's loops overhead
FLY_WIN = (0.09, 0.2)           # perfect / good timing windows


# ---------------------------------------------------------------- shared helpers
def bank_catch(g, spec, size):
    """Put a catch straight into the basket without the catch card (crab pots, Biscuit's gifts)."""
    lo, hi = spec['size']
    k = (size - lo) / max(0.01, hi - lo)
    junk = spec.get('junk')
    price = spec['price'] if junk else int(round(spec['price'] * (0.8 + 0.6 * k)))
    if not junk:
        e = g.journal.setdefault(spec['id'], {'count': 0, 'best': 0})
        e['count'] += 1
        e['best'] = max(e['best'], size)
        g.total += 1
    g.basket.append(dict(id=spec['id'], size=size, price=price))
    return price


def rand_size(spec, rng, luck=0.0):
    lo, hi = spec['size']
    return round(lo + (hi - lo) * min(1.0, rng.random() ** 1.6 + luck), 1)


def year(g):
    from data import DAYS_PER_SEASON
    return (g.day - 1) // (DAYS_PER_SEASON * 4)


# ---------------------------------------------------------------- storms and the northern lights
def roll_sky(g, slot):
    """Called as each weather slot rolls. Storms and auroras are decided at nightfall and end at dawn."""
    if slot == 'morning':
        g.sky = None
        return
    if slot != 'night':
        return
    season = g.season_of(g.day)
    r = random.random()
    if g.weather == 'rain' and season in (1, 2) and r < 0.35:
        g.sky = 'storm'
        g.toast('A thunderstorm is rolling in. Thunderfin rise in storms!', (150, 160, 210))
    elif season == 3 and g.weather in ('clear', 'snow', 'cloudy') and r < 0.3:
        g.sky = 'aurora'
        if g.weather == 'cloudy':
            g.weather = 'clear'
        g.toast('The northern lights! Northern Lightfish glow beneath them.', (140, 220, 190))
    else:
        g.sky = None


def sky_live(g, kind):
    return getattr(g, 'sky', None) == kind and g.night_now()


def update(g, dt):
    """Storm lightning, pot float bobbing and the like."""
    w = g.world
    if sky_live(g, 'storm') and g.place == 'lake':
        if g.weather != 'rain':
            g.weather = 'rain'
        w.thunder_cd = min(w.thunder_cd, 9.0)          # a real storm: lightning every few seconds
        if w.thunder_cd > 0:
            w.thunder_cd -= dt * 2.2


def draw_aurora(frame, env, world, g):
    """Curtains of green and pink light over the far hills on aurora nights."""
    if not sky_live(g, 'aurora'):
        return
    a = min(1.0, (env.nf - 0.4) * 2.5) * (1 - env.over * 0.8)
    if a <= 0.02:
        return
    t = world.t
    buf = getattr(world, '_aurora', None)
    if buf is None:
        buf = world._aurora = pygame.Surface((W, HORIZON), pygame.SRCALPHA)
    buf.fill((0, 0, 0, 0))
    for band, (col, y0, amp) in enumerate((((90, 255, 170), 70, 16), ((160, 120, 255), 52, 12),
                                           ((120, 255, 210), 92, 10))):
        for x in range(0, W, 2):
            y = y0 + math.sin(x * 0.012 + t * 0.25 + band) * amp + math.sin(x * 0.031 - t * 0.4) * 5
            h = 30 + 18 * math.sin(x * 0.02 + t * 0.3 + band * 2)
            k = 0.5 + 0.5 * math.sin(x * 0.05 + t * (0.6 + band * 0.2))
            for i in range(0, int(h), 2):
                fade = (1 - i / h) * k
                buf.fill((*col, int(70 * fade)), (x, int(y - i), 2, 2))
    buf.set_alpha(int(255 * a))
    frame.blit(buf, (0, 0), special_flags=0)


# ---------------------------------------------------------------- the crab pot
def pot_state(g):
    p = g.pot if isinstance(g.pot, dict) else {}
    return p.get('set')


def pot_ready(g):
    s = pot_state(g)
    return s is not None and (g.day > s and g.minute >= 300 or g.day > s + 1)


def pot_action(g):
    """Set the pot (evenings), or haul it in (once a night has passed)."""
    if not g.has('pot') or g.spot != 'dock' or g.place != 'lake':
        return False
    s = pot_state(g)
    if s is None:
        if 960 <= g.minute or g.minute < 120:
            corn = g.baits.get('corn', 0) > 0
            if corn:
                g.baits['corn'] -= 1
            g.pot = {'set': g.day if g.minute >= 960 else g.day - 1, 'corn': corn}
            g.world.splash(FLOAT_X, FLOAT_Y, 10, 0.8)
            g.audio.play('plop', 0.7)
            g.toast('You lower the crab pot off the dock%s. Check it in the morning!' %
                    (', baited with sweet corn' if corn else ''), (120, 150, 170))
        else:
            g.toast('Crabs come out at night. Set the pot after 4 PM.', (150, 140, 130))
        return True
    if not pot_ready(g):
        g.toast('Give it the night. Check the pot in the morning.', (150, 140, 130))
        return True
    haul(g)
    return True


def haul(g, rng=None):
    rng = rng or random
    p = g.pot
    season = g.season_of(g.day)
    n = rng.choice((1, 2, 2, 3)) + (1 if p.get('corn') else 0)
    pool = [f for f in FISH if f.get('method') == 'pot']
    got = []
    for _ in range(n):
        if rng.random() < 0.12:
            spec = JUNK_BY_ID[rng.choice(('clam', 'boot', 'can', 'driftwood', 'clam'))]
        else:
            ws = []
            for f in pool:
                w = {1: 10, 2: 4, 3: 1}[f['rarity']]
                if f['id'] == 'rivercrab' and season in (1, 2):
                    w *= 1.8
                if f['id'] == 'moonsnail' and season == 0:
                    w *= 2
                if f['id'] == 'bluecray' and p.get('corn'):
                    w *= 2.2
                ws.append(w)
            spec = rng.choices(pool, ws)[0]
        bank_catch(g, spec, rand_size(spec, rng))
        got.append(spec['name'])
    g.pot = {'set': None, 'corn': False}
    g.stats['pots'] = g.stats.get('pots', 0) + 1
    g.audio.play('splash', 0.6)
    g.world.splash(FLOAT_X, FLOAT_Y, 14, 1.0)
    names = {}
    for nm in got:
        names[nm] = names.get(nm, 0) + 1
    text = ', '.join('%s%s' % (nm, ' x%d' % c if c > 1 else '') for nm, c in names.items())
    g.toast('You haul up the crab pot: %s. Into the basket!' % text, (120, 150, 170))
    g.check_badges()
    g.save()
    return got


def pot_rect(g):
    if pot_state(g) is None:
        return pygame.Rect(POT_X - 7, DECK_Y - 12, 15, 13)
    return pygame.Rect(FLOAT_X - 6, FLOAT_Y - 8, 13, 13)


def draw_pot(s, g, t):
    """The pot on the deck, or its rope and float once it's in the water."""
    if not g.has('pot'):
        return
    wire, rope = (120, 120, 116), (196, 172, 120)
    if pot_state(g) is None:
        x, y = POT_X, DECK_Y
        pygame.draw.rect(s, (70, 64, 56), (x - 6, y - 9, 13, 9), 1)
        for i in range(-4, 6, 3):
            pygame.draw.line(s, wire, (x + i, y - 8), (x + i, y - 1))
        pygame.draw.line(s, wire, (x - 5, y - 5), (x + 5, y - 5))
        pygame.draw.circle(s, rope, (x + 7, y - 3), 2, 1)
        return
    bob = math.sin(t * 2.2) * 1.2
    fx, fy = FLOAT_X, FLOAT_Y + bob
    pygame.draw.line(s, rope, (262, DECK_Y - 1), (fx - 1, int(fy) - 2))
    pygame.draw.ellipse(s, (60, 80, 100, 110), (fx - 5, int(fy) + 2, 11, 3))
    s.fill((236, 120, 60), (fx - 3, int(fy) - 3, 7, 4))
    s.fill((250, 240, 220), (fx - 3, int(fy) - 4, 7, 1))
    if pot_ready(g) and int(t * 2) % 2:
        s.fill((255, 240, 170), (fx - 1, int(fy) - 8, 3, 2))


# ---------------------------------------------------------------- fly casting at the creek
def fly_on(g):
    return getattr(g, 'spot', 'dock') == 'creek' and g.has('flyrod')


def start_fly(f):
    f.state = 'fly'
    f.t = 0.0
    f.fly_taps = []                  # grades of each beat
    f.fly_q = 0
    f.fly_beat = 0
    f.g.audio.play('ui', 0.4)


def press_fly(f):
    """A tap during the loops: graded against the nearest beat."""
    k = f.fly_beat
    if k >= 3:
        return
    target = FLY_BEAT * (k + 1)
    d = abs(f.t - target)
    if d <= FLY_WIN[0]:
        grade = 'perfect'
    elif d <= FLY_WIN[1]:
        grade = 'good'
    else:
        grade = 'miss'
    f.fly_taps.append(grade)
    f.fly_beat += 1
    g = f.g
    g.audio.play('chime%d' % min(4, k + 1) if grade != 'miss' else 'nibble', 0.5)


def update_fly(f, dt):
    """Returns the rod angle target while the line loops overhead."""
    k = f.fly_beat
    if k < 3 and f.t > FLY_BEAT * (k + 1) + FLY_WIN[1]:
        f.fly_taps.append('miss')                # let a beat go by
        f.fly_beat += 1
    if f.fly_beat >= 3 and f.t > FLY_BEAT * 3 + 0.12:
        q = sum(2 if t_ == 'perfect' else 1 if t_ == 'good' else 0 for t_ in f.fly_taps)
        f.fly_q = q                              # 0..6
        f.g.stats['fly_casts'] = f.g.stats.get('fly_casts', 0) + 1
        if q >= 5:
            f.g.toast('A beautiful cast! The fly settles like a real mayfly.', (90, 150, 120))
        f.cast(min(1.0, 0.35 + q * 0.11))
        return -40
    ph = (f.t % FLY_BEAT) / FLY_BEAT
    return -70 - 45 * math.sin(ph * math.pi * 2)


def fly_weight(f, spec):
    """The fly casting effect on the pick weights; None means it can't bite."""
    if spec.get('method') == 'fly':
        if not getattr(f, 'fly_q', 0) or f.fly_q < 3:
            return None
        return 1.0 + (f.fly_q - 3) * 0.6
    return 1.0


def draw_fly(s, ui, f, center):
    """Three beat rings and a sweeping hand near the angler."""
    cx, cy = center
    pygame.draw.circle(s, (30, 40, 50), (cx, cy), 58)
    pygame.draw.circle(s, (230, 240, 236), (cx, cy), 54, 3)
    for k in range(3):
        a = -math.pi / 2 + (k + 1) * 2 * math.pi / 3.0
        x, y = cx + math.cos(a) * 44, cy + math.sin(a) * 44
        grade = f.fly_taps[k] if k < len(f.fly_taps) else None
        col = {'perfect': (255, 220, 110), 'good': (170, 220, 170), 'miss': (220, 120, 110)}.get(grade,
                                                                                                 (120, 130, 140))
        pygame.draw.circle(s, col, (int(x), int(y)), 10)
        pygame.draw.circle(s, (250, 250, 240), (int(x), int(y)), 10, 2)
    # the hand sweeps once per beat, so it meets beat k at the top of the circle each time... kept simple:
    tot = FLY_BEAT * 3
    a = -math.pi / 2 + min(1.0, f.t / tot) * 2 * math.pi
    pygame.draw.line(s, (255, 236, 170), (cx, cy), (cx + math.cos(a) * 40, cy + math.sin(a) * 40), 4)
    pygame.draw.circle(s, (255, 236, 170), (cx, cy), 6)
    ph = (f.t % FLY_BEAT) / FLY_BEAT
    pulse = max(0.0, 1 - min(ph, 1 - ph) * 6)
    if pulse > 0:
        pygame.draw.circle(s, (255, 250, 230), (cx, cy), int(54 + 10 * pulse), 2)
    hint = 'Tap on each beat!' if f.fly_beat < 3 else 'Here it goes...'
    ui.blit_text(s, hint, (cx, cy - 78), 'bodyb', (255, 246, 228), 'center', (30, 20, 30))


# ---------------------------------------------------------------- the frozen cove
def frozen(g):
    return getattr(g, 'spot', 'dock') == 'cove' and g.season_of(g.day) == 3 and g.place == 'lake'


def draw_ice(near, env, world, g):
    """Lily Cove under ice: a pale sheet with cracks, snow drifts and your fishing hole."""
    if not frozen(g):
        return
    ice = getattr(world, '_ice', None)
    if ice is None:
        ice = world._ice = pygame.Surface((W, H - HORIZON), pygame.SRCALPHA)
        rng = random.Random(7)
        for y in range(H - HORIZON):
            k = y / (H - HORIZON)
            ice.fill((*lerp_c((206, 220, 232), (232, 240, 248), k), 236), (0, y, W, 1))
        for _ in range(26):                                  # cracks
            x, y = rng.uniform(0, W), rng.uniform(4, H - HORIZON)
            pts = [(x, y)]
            for _ in range(5):
                x += rng.uniform(-14, 14)
                y += rng.uniform(-3, 5)
                pts.append((x, y))
            pygame.draw.lines(ice, (170, 190, 210, 200), False, pts)
        for _ in range(40):                                  # drifts of snow
            x, y = rng.uniform(0, W), rng.uniform(0, H - HORIZON)
            w = rng.uniform(8, 40) * (0.5 + y / (H - HORIZON))
            pygame.draw.ellipse(ice, (250, 252, 255, 220), (x, y, w, max(2, w * 0.18)))
    near.blit(ice, (0, HORIZON))
    hx, hy = 330, 286
    if g.ice_hole == g.day:
        pygame.draw.ellipse(near, (40, 70, 92), (hx - 9, hy - 3, 18, 6))
        pygame.draw.ellipse(near, (230, 238, 246), (hx - 11, hy - 4, 22, 8), 1)
        k = 0.5 + 0.5 * math.sin(world.t * 2)
        near.fill((110, 160, 190), (hx - 4, hy - 1 + int(k), 3, 1))


def ice_tip(g):
    if g.has('auger'):
        return 'Lily Cove is frozen solid. Press Space or click to ice fish!'
    return 'Lily Cove is frozen solid. An Ice Auger from the shop would get you through.'


def open_ice(g):
    import icefish
    if not g.has('auger'):
        g.toast(ice_tip(g), (120, 150, 190))
        return
    g.release_holds()
    g.icescene = icefish.IceScene(g, drilled=g.ice_hole == g.day)
    g.overlay = 'ice'
    g.audio.play('page', 0.5)


# ---------------------------------------------------------------- shop gear and icons
GEAR_ITEMS = [
    dict(id='pot', name='Crab Pot', price=250,
         desc='Set it off the dock in the evening (E), haul it up in the morning.'),
    dict(id='flyrod', name='Fly Rod', price=700,
         desc='At Willow Creek, cast in rhythm: tap on the beats. Some fish only take a fly.'),
    dict(id='auger', name='Ice Auger', price=300,
         desc='Drill through the ice when Lily Cove freezes in winter, and fish below.'),
]


def icon(item_id):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    d = pygame.draw
    if item_id == 'pot':
        d.rect(s, (90, 80, 70), (2, 5, 12, 9), 1)
        for x in range(4, 13, 3):
            d.line(s, (150, 150, 146), (x, 6), (x, 12))
        d.line(s, (150, 150, 146), (3, 9), (13, 9))
        d.circle(s, (210, 180, 120), (8, 3), 2, 1)
    elif item_id == 'flyrod':
        d.line(s, (90, 60, 40), (2, 14), (5, 11), 2)
        d.line(s, (120, 150, 110), (5, 11), (14, 2))
        d.arc(s, (240, 240, 220), (6, 0, 10, 12), 0.2, 2.8)
        d.rect(s, (250, 210, 90), (12, 7, 3, 2))
    elif item_id == 'auger':
        d.line(s, (120, 90, 60), (3, 3), (13, 3), 2)
        d.line(s, (150, 150, 160), (8, 3), (8, 14), 2)
        for y in range(6, 14, 2):
            d.line(s, (200, 200, 210), (6, y), (10, y + 1))
    return s


def _register():
    import data
    for it in GEAR_ITEMS:
        if all(x['id'] != it['id'] for x in data.GEAR):
            data.GEAR.append(it)
    art.EXTRA_ICONS.update({it['id']: (lambda i: lambda: icon(i))(it['id']) for it in GEAR_ITEMS})


_register()
