"""The bigger moments out on the lake, the ones you look up for: a heron wading the shallows, a canoe gliding past,
a big fish leaping clear of the water, a breeze you can watch sweep across the whole lake, and in spring, blossom
petals drifting down onto the water.

One happens every minute or so, picked to suit the spot, the season and the hour. None of it changes what bites."""
import math
import random

import pygame

from art import W, H, HORIZON, lerp_c, darken, lighten

GAP = (35.0, 70.0)          # seconds between the big moments
FIRST = 14.0                # the first one comes along quite soon


def persp(y):
    return 0.5 + (y - HORIZON) / 170


class LakeShow:
    def __init__(self):
        self.rng = random.Random()
        self.cd = FIRST
        self.ev = None           # the moment happening now: dict(kind, t, ...)
        self.petals = []         # spring blossom drifting down and floating on the water
        self.breeze = None       # a cat's paw of wind sweeping across the whole lake: dict(x, spd, w)
        self.last = None


def state(g):
    s = getattr(g, '_lakeshow', None)
    if s is None:
        s = g._lakeshow = LakeShow()
    return s


def _choices(g):
    env = g.env
    import seasons
    frozen = seasons.frozen(g)
    spot = g.spot
    night = env.nf > 0.45
    out = []
    if not frozen and not night and spot in ('dock', 'cove', 'creek') and env.rain < 0.6:
        out.append(('heron', 3))
    if not frozen and env.rain < 0.5:
        out.append(('canoe', 2 if not night else 1))
    if not frozen:
        out.append(('leap', 3))
    if not frozen and env.season != 3 or env.wind > 0.3:
        out.append(('breeze', 2))
    return out


def start(g, kind=None):
    """Begin one of the big moments (kind=None picks one that suits the moment)."""
    s = state(g)
    rng = s.rng
    if kind is None:
        opts = [o for o in _choices(g) if o[0] != s.last] or _choices(g)
        if not opts:
            return
        tot = sum(w for _, w in opts)
        r = rng.uniform(0, tot)
        for kind, w in opts:
            r -= w
            if r <= 0:
                break
    s.last = kind
    # what's in the shot right now, so things start just off its edge and come into view
    z, fx = max(1.0, g.cam[0]), g.cam[1]
    if z < 1.6:                          # mid-move (or casting wide): plan for the usual resting shot
        z = getattr(g, 'HOME_Z', 2.0)
        fx = 238 + W / z * 0.17
    half = W / z / 2
    left, right = max(0.0, fx - half), min(float(W), fx + half)
    if kind == 'heron':
        d = -1 if g.spot == 'dock' else rng.choice((-1, 1))      # at home it keeps clear of the dock
        y = rng.uniform(306, 322)
        s.ev = dict(kind='heron', t=0.0, x=right + 8 if d < 0 else left - 8, y=y, d=d, step=2.5, pause=0.0,
                    strike=0.0, fly=None, walked=0.0, far=(right - left) * 0.55)
    elif kind == 'canoe':
        d = rng.choice((-1, 1))
        y = rng.uniform(226, 246)
        s.ev = dict(kind='canoe', t=0.0, x=left - 24 if d > 0 else right + 24, y=y, d=d,
                    shirt=rng.choice([(70, 120, 180), (190, 90, 80), (90, 150, 100), (210, 170, 70)]),
                    hull=rng.choice([(176, 70, 52), (60, 110, 150), (200, 160, 80)]), drip=0.0)
    elif kind == 'leap':
        x = rng.uniform(max(260.0, left + (right - left) * 0.45), max(300.0, right - 50))
        y = rng.uniform(262, 300)
        s.ev = dict(kind='leap', t=0.0, x=x, y=y, d=rng.choice((-1, 1)), n=rng.randint(1, 3), i=0,
                    sz=rng.uniform(1.0, 1.4), **{'in': True}, col=rng.choice([(176, 186, 170), (200, 170, 120), (150, 170, 190)]))
        _leap_in(g, s.ev)
    elif kind == 'breeze':
        s.breeze = dict(x=-120.0, spd=rng.uniform(70, 100), w=rng.uniform(90, 150))
        s.ev = dict(kind='breeze', t=0.0)
        g.world.sway = max(g.world.sway, 0.8)
        g.audio.play('rustle', 0.45)


def _leap_in(g, e):
    p = persp(e['y'])
    g.world.splash(e['x'], e['y'], 10, 1.1 * p * e['sz'])
    g.world.ripple(e['x'], e['y'], 12 * p + 4)
    g.audio.play('splash_small', 0.5, e['x'] / W)


def update(g, dt):
    if g.place != 'lake' or g.mode != 'play':
        return
    s = state(g)
    rng = s.rng
    env = g.env
    w = g.world
    # spring petals: a few always drifting down on a spring day, a flurry when the breeze comes through
    if env.season == 0 and env.nf < 0.5 and g.spot != 'deep':
        rate = 0.9 + (6 if s.breeze else 0) + env.wind * 2
        if len(s.petals) < 60 and rng.random() < dt * rate:
            s.petals.append(dict(x=rng.uniform(120, 520), y=rng.uniform(150, 175), vy=rng.uniform(5, 9),
                                 ph=rng.uniform(0, 6.28), land=rng.uniform(250, 350), float=0.0,
                                 col=rng.choice([(255, 206, 222), (255, 226, 236), (246, 186, 206)])))
    for p in s.petals:
        if p['float'] > 0:
            p['float'] += dt
            p['x'] += (2 + env.wind * 4) * dt
        else:
            p['y'] += p['vy'] * dt
            p['x'] += (math.sin(g.t * 1.6 + p['ph']) * 10 + 6 + env.wind * 14 + (20 if s.breeze else 0)) * dt
            if p['y'] >= p['land']:
                p['float'] = 0.01
                if rng.random() < 0.3:
                    w.ripple(p['x'], p['y'], 3, 6, 90)
    s.petals = [p for p in s.petals if p['float'] < 14 and p['x'] < W + 10]
    if s.breeze:
        b = s.breeze
        b['x'] += b['spd'] * dt
        w.sway = max(w.sway, 0.7)
        if b['x'] - b['w'] > W + 40:
            s.breeze = None
    e = s.ev
    if e is None:
        if g.rest_phase is not None or g.overlay not in (None, 'catch'):
            return
        s.cd -= dt
        if s.cd <= 0:
            s.cd = rng.uniform(*GAP)
            start(g)
        return
    e['t'] += dt
    k = e['kind']
    if k == 'heron':
        _heron(g, s, e, dt)
    elif k == 'canoe':
        e['x'] += e['d'] * 17 * dt
        e['drip'] -= dt
        if e['drip'] <= 0:
            e['drip'] = 0.55
            w.ripple(e['x'] - e['d'] * 4, e['y'] + 1, 4, 7, 110)
        if e['x'] < -40 or e['x'] > W + 40:
            s.ev = None
    elif k == 'leap':
        dur = 0.95 * e['sz']
        if e['t'] >= dur:
            p = persp(e['y'])
            ex = e['x'] + e['d'] * 30 * p * e['sz']
            w.splash(ex, e['y'], 14, 1.3 * p * e['sz'])
            w.ripple(ex, e['y'], 16 * p + 5)
            w.ripple(ex, e['y'], 9 * p + 3, 10)
            g.audio.play('splash', 0.45, ex / W)
            g.cat['excited'] = max(g.cat['excited'], 1.6)
            e['i'] += 1
            if e['i'] >= e['n']:
                s.ev = None
            else:
                e['x'] = ex + e['d'] * rng.uniform(6, 16)
                e['t'] = -rng.uniform(0.4, 1.0)             # under for a moment, then up again
                e['sz'] *= 0.92
        elif e['t'] >= 0 and not e.get('in'):
            e['in'] = True
            _leap_in(g, e)
        if e['t'] < 0:
            e['in'] = False
    elif k == 'breeze':
        if s.breeze is None:
            s.ev = None


def _heron(g, s, e, dt):
    w = g.world
    rng = s.rng
    if e['fly'] is not None:
        f = e['fly']
        f['t'] += dt
        e['x'] += e['d'] * 34 * dt
        e['y'] -= (14 + f['t'] * 10) * dt
        if e['y'] < 120 or e['x'] < -40 or e['x'] > W + 40:
            s.ev = None
        return
    if e['strike'] > 0:
        e['strike'] -= dt
        if e['strike'] <= 0.25 and not e.get('splashed'):
            e['splashed'] = True
            w.splash(e['x'] + e['d'] * 14, e['y'] - 1, 6, 0.6)
            w.ripple(e['x'] + e['d'] * 14, e['y'], 6)
        return
    if e['pause'] > 0:
        e['pause'] -= dt
        if e['pause'] <= 0:
            e['step'] = rng.uniform(1.4, 2.8)
        return
    e['step'] -= dt
    e['x'] += e['d'] * 9 * dt
    e['walked'] += 9 * dt
    if int(e['t'] * 1.4) != int((e['t'] - dt) * 1.4):
        w.ripple(e['x'] + rng.uniform(-3, 3), e['y'] + 1, 4, 6, 110)
    if e['step'] <= 0:
        e['pause'] = rng.uniform(1.0, 3.0)
        e.pop('splashed', None)
        if rng.random() < 0.35:
            e['strike'] = 0.7
    if e['walked'] > e.get('far', 170) or g.fishing.state == 'fight':
        e['fly'] = dict(t=0.0)             # off it goes, slow wingbeats, low over the water
        w.splash(e['x'], e['y'], 4, 0.5)


def scare(g):
    """A fight or a splash nearby: the heron takes off."""
    s = state(g)
    e = s.ev
    if e and e['kind'] == 'heron' and e['fly'] is None:
        e['fly'] = dict(t=0.0)


# ------------------------------------------------------------ drawing
def draw_water(frame, g, t):
    """The breeze darkening and ruffling the water as it sweeps across (drawn on the lake itself)."""
    s = state(g)
    b = s.breeze
    if not b:
        return
    env = g.env
    surf = getattr(s, '_bz', None)
    if surf is None:
        surf = s._bz = pygame.Surface((W, H - HORIZON), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    dark = (20, 40, 56)
    glint = lerp_c((230, 240, 246), env.sky[2], 0.3)
    rng = random.Random(int(b['x'] / 6))
    for i in range(240):
        yy = rng.uniform(2, H - HORIZON - 2)
        p = 0.5 + yy / 170
        # the front of the gust leans: it reaches the near water a little later than the far
        cx = b['x'] - (1 - p) * 40
        x = cx - rng.uniform(0, b['w'])
        edge = min(1.0, (cx - x) / 30, (x - (cx - b['w'])) / 40)
        if edge <= 0 or x < 0 or x >= W:
            continue
        ln = int(2 + 5 * p)
        a = int(90 * edge)
        col = (*glint, a + 40) if i % 6 == 0 else (*dark, a)
        pygame.draw.line(surf, col, (x, yy), (x + ln, yy))
    frame.blit(surf, (0, HORIZON))


def draw(near, g, t):
    s = state(g)
    env = g.env
    for p in s.petals:
        x, y = int(p['x']), int(p['y'])
        if p['float'] > 0:
            a = int(255 * min(1.0, (14 - p['float']) / 3))
            near.fill((*p['col'], a), (x, y, 2, 1))
        else:
            flip = math.sin(t * 6 + p['ph']) > 0
            near.fill(p['col'], (x, y, 2 if flip else 1, 1 if flip else 2))
    e = s.ev
    if not e:
        return
    k = e['kind']
    if k == 'heron':
        _draw_heron(near, e, t, env)
    elif k == 'canoe':
        _draw_canoe(near, e, t, env)
    elif k == 'leap' and e['t'] >= 0:
        _draw_leap(near, e)


def _draw_heron(near, e, t, env):
    x, y, d = e['x'], e['y'], e['d']
    grey = (150, 158, 166)
    dk = (70, 74, 84)
    beak = (226, 190, 80)
    if e['fly'] is not None:
        ft = e['fly']['t']
        flap = math.sin(ft * 5)
        # neck tucked in, legs trailing, big slow wings
        pygame.draw.ellipse(near, grey, (x - 9, y - 22, 18, 7))
        near.fill(dk, (int(x + d * 8), int(y - 22), 4, 4))
        pygame.draw.line(near, beak, (x + d * 10, y - 20), (x + d * 16, y - 19), 2)
        pygame.draw.line(near, dk, (x - d * 8, y - 18), (x - d * 18, y - 16), 1)
        tip = y - 19 - flap * 12
        pygame.draw.polygon(near, darken(grey, 0.1), [(x - 6, y - 19), (x + 6, y - 19), (x + d * 2, tip),
                                                      (x - d * 10, tip + 2)])
        return
    strike = e['strike'] > 0
    # legs into the water, standing on its reflection
    lift = 2 if e['pause'] <= 0 and e['step'] > 0 and int(t * 3) % 2 else 0
    pygame.draw.line(near, dk, (x - 2, y), (x - 1, y - 12), 1)
    pygame.draw.line(near, dk, (x + 2, y - lift), (x + 1, y - 12), 1)
    pygame.draw.line(near, (40, 70, 90, 120), (x - 4, y + 1), (x + 4, y + 1))
    # body, wing and tail
    body = pygame.Rect(0, 0, 18, 9)
    body.center = (int(x), int(y - 16))
    pygame.draw.ellipse(near, grey, body)
    pygame.draw.ellipse(near, darken(grey, 0.15), body.inflate(-6, -4).move(-d * 2, 1))
    near.fill(dk, (int(x - d * 9 - (1 if d > 0 else 0)), int(y - 15), 3, 2))
    # the S-curved neck, and the beak: forward and down when it strikes
    if strike:
        k = min(1.0, (0.7 - e['strike']) / 0.3)
        hx, hy = x + d * (8 + 8 * k), y - 18 + 14 * k
    else:
        hx, hy = x + d * 4, y - 34 + math.sin(t * 0.7) * 0.8
    pygame.draw.lines(near, lighten(grey, 0.15), False, [(x + d * 5, y - 18), (x + d * 1, y - 24),
                                                         (x + d * 5, y - 29), (hx, hy)], 3)
    pygame.draw.circle(near, lighten(grey, 0.25), (int(hx), int(hy)), 3)
    near.fill(dk, (int(hx - d * 4 - (2 if d < 0 else 0)), int(hy - 3), 5, 1))     # the black crest
    near.set_at((int(hx + d), int(hy - 1)), (240, 220, 120))
    pygame.draw.line(near, beak, (hx + d * 2, hy), (hx + d * 10, hy + (5 if strike else 1)), 2)


def _draw_canoe(near, e, t, env):
    x, y, d = e['x'], e['y'] + math.sin(t * 1.6) * 0.5, e['d']
    p = persp(e['y'])
    s = 1.45 * p
    hw = 17 * s
    hull = [(x - hw, y - 2 * s), (x + hw, y - 2 * s), (x + hw * 0.7, y + 1.5 * s), (x - hw * 0.7, y + 1.5 * s)]
    pygame.draw.polygon(near, e['hull'], hull)
    pygame.draw.line(near, lighten(e['hull'], 0.3), hull[0], hull[1])
    pygame.draw.line(near, (230, 240, 246, 120), (x - d * hw, y + 2 * s), (x - d * (hw + 12 * s), y + 2 * s))
    # a paddler kneeling, the paddle switching sides with each stroke
    px = x - d * 4 * s
    top = y - 2 * s
    near.fill(e['shirt'], (int(px - 2 * s), int(top - 7 * s), int(4 * s) + 1, int(7 * s)))
    near.fill((232, 196, 166), (int(px - 1.5 * s), int(top - 10 * s), int(3 * s) + 1, int(3 * s)))
    ph = t * 2.4
    side = 1 if math.sin(ph * 0.5) > 0 else -1
    sw = math.cos(ph)
    bx = px - d * sw * 8 * s
    by = y + 2 * s + side
    pygame.draw.line(near, (120, 90, 60), (px + d * 2 * s, top - 6 * s), (bx, by), max(1, int(s)))
    near.fill((150, 110, 70), (int(bx) - 1, int(by) - 1, 3, 3))
    if env.nf > 0.35:
        # a lantern at the bow after dark
        lx, ly = int(x + d * hw * 0.8), int(y - 6 * s)
        near.fill((255, 220, 140), (lx - 1, ly - 2, 3, 3))


def _draw_leap(near, e):
    p = persp(e['y'])
    sz = e['sz'] * p
    dur = 0.95 * e['sz']
    k = max(0.0, min(1.0, e['t'] / dur))
    x = e['x'] + e['d'] * 30 * sz * k
    y = e['y'] - math.sin(math.pi * k) * 44 * sz
    ln = 9 * sz
    ang = math.cos(math.pi * k) * 0.9
    dx = math.cos(ang) * ln * e['d']
    dy = -math.sin(ang) * ln
    col = e['col']
    # a proper fish shape: fat in the middle, a forked tail, a pale belly
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux
    th = 2.6 * sz
    body = [(x + dx, y + dy), (x + dx * 0.3 + nx * th, y + dy * 0.3 + ny * th),
            (x - dx * 0.7 + nx * th * 0.5, y - dy * 0.7 + ny * th * 0.5), (x - dx, y - dy),
            (x - dx * 0.7 - nx * th * 0.5, y - dy * 0.7 - ny * th * 0.5), (x + dx * 0.3 - nx * th, y + dy * 0.3 - ny * th)]
    pygame.draw.polygon(near, darken(col, 0.25), body)
    pygame.draw.polygon(near, col, body[:4])
    tx, ty = x - dx, y - dy
    pygame.draw.polygon(near, darken(col, 0.3), [(tx, ty), (tx - ux * 4 * sz + nx * 3 * sz, ty - uy * 4 * sz + ny * 3 * sz),
                                                 (tx - ux * 4 * sz - nx * 3 * sz, ty - uy * 4 * sz - ny * 3 * sz)])
    near.set_at((int(x + dx * 0.7), int(y + dy * 0.7)), (30, 30, 34))
    for i in range(4):
        q = (k * 3 + i * 0.27) % 1.0
        near.set_at((int(x - dx * (1.2 + q)), int(y - dy * (1.2 + q) + q * 8)), (230, 244, 252, int(220 * (1 - q))))
