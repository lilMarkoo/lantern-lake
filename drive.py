"""Driving Rosie's truck (0.5.5): a side-on scenic drive along one of the four roads (truck.ROUTES).

Hold gas and brake over the hills; the truck tilts with the road and its springs bounce over the bumps. In rain the
road is slick, in winter it is snowy (snow tyres help on the climbs), and after dark the headlights come on. Things
along the way: viewpoints to stop at and photograph, people with a thumb out for a lift, animals on the road (wait,
or a toot of the horn hurries them), and the odd lost thing in the verge. If you're carrying an order the cooler sits
in the back: big bumps at speed spill a fish, and the ice melts as the minutes go by.

Runs under Game.overlay 'drive' with Game.aqscene, like the walk scenes. The clock is paused by main while you
drive; the drive itself moves it on by the route's minutes as you cover the road.
"""
import math
import random

import pygame

import art
import town as T
import truck as TR
import ui as U
from art import W, H, lerp_c, darken, lighten, add_glow

HEADLESS = False
fmt_clock = str

BASE = 286                 # where the road sits on screen, more or less
TX = 196                   # the truck's x on screen
RAMP = 260                 # flat-ish road at each end
GAS, BRAKE, GRAV = 96.0, 180.0, 150.0
ANIMAL_LOOK = {'deer': (150, 104, 70), 'ducks': (120, 110, 90), 'sheep': (238, 236, 228), 'hedgehog': (120, 96, 70)}


def road_fn(r):
    """h(x): the road's height (y, down is +) along route r, flattened at both ends."""
    a1, a2, a3 = r['amp']
    f1, f2, f3 = r['freq']
    L = float(r['length'])
    rng = random.Random(hash(r['id']) & 0xffff)
    p1, p2, p3 = rng.uniform(0, 6), rng.uniform(0, 6), rng.uniform(0, 6)
    climb = -70.0 if r['id'] == 'hill' else (-26.0 if r['id'] == 'coast' else 0.0)

    def h(x):
        x = max(0.0, min(L, x))
        e = min(1.0, x / RAMP, (L - x) / RAMP)
        e = e * e * (3 - 2 * e)
        k = x / L
        trend = climb * (k * k * (3 - 2 * k))
        return BASE + trend + e * (a1 * math.sin(x * f1 + p1) + a2 * math.sin(x * f2 + p2) +
                                  a3 * math.sin(x * f3 + p3))
    return h


# ---------------------------------------------------------------- scenery layers (tileable, 1280 wide)
_LAYERS = {}
LW = 1280


def _wrap_poly(s, pts, col):
    for off in (-LW, 0, LW):
        pygame.draw.polygon(s, col, [(x + off, y) for x, y in pts])


def _pine(s, x, base, h, col, snow=False):
    for k in range(4):
        w = int(h * 0.26 * (1 - k * 0.2)) + 2
        y = base - int(h * (0.25 + k * 0.2))
        pygame.draw.polygon(s, col, [(x - w, y + int(h * 0.22)), (x, y - 4), (x + w, y + int(h * 0.22))])
        if snow:
            s.fill((240, 244, 250), (x - w // 2, y + 2, w, 1))
    s.fill(darken(col, 0.3), (x - 1, base - int(h * 0.2), 2, int(h * 0.2)))


def _tree(s, x, base, r, col, season):
    s.fill((96, 70, 50), (x - 1, base - r, 3, r))
    if season == 3:
        for k in (-1, 1):
            pygame.draw.line(s, (110, 90, 74), (x, base - r), (x + k * r // 2, base - r - r // 2))
        return
    pygame.draw.circle(s, darken(col, 0.12), (x, base - r - r // 3), r)
    pygame.draw.circle(s, col, (x - 1, base - r - r // 3 - 1), r - 1)
    pygame.draw.circle(s, lighten(col, 0.08), (x - r // 3, base - r - r // 2 - 1), r // 2)


def build_layers(theme, season):
    key = (theme, season)
    if key in _LAYERS:
        return _LAYERS[key]
    rng = random.Random(hash(key) & 0xffff)
    far = pygame.Surface((LW, H), pygame.SRCALPHA)
    mid = pygame.Surface((LW, H), pygame.SRCALPHA)
    grass = art.GRASS[season]
    gd = art.GRASS_D[season]
    snowy = season == 3
    if theme == 'hill':
        rock = (126, 132, 146) if not snowy else (176, 186, 204)
        for k in range(9):
            cx = k * LW // 9 + rng.randint(-30, 30)
            ht = rng.randint(90, 150)
            wd = rng.randint(110, 170)
            pts = [(cx - wd, 230), (cx - wd // 3, 230 - ht * 2 // 3), (cx, 230 - ht), (cx + wd // 4, 230 - ht * 3 // 4),
                   (cx + wd, 230)]
            _wrap_poly(far, pts, rock)
            cap = [(cx - wd // 4, 230 - ht * 3 // 4), (cx, 230 - ht), (cx + wd // 6, 230 - ht * 4 // 5)]
            if season != 1:
                _wrap_poly(far, cap, (240, 244, 250))
        far.fill(darken(rock, 0.08), (0, 228, LW, H - 228))
        pine = {0: (56, 100, 74), 1: (48, 92, 66), 2: (60, 96, 72), 3: (70, 100, 90)}[season]
        mid.fill(darken(pine, 0.1), (0, 236, LW, H - 236))
        for x in range(0, LW, 9):
            hgt = rng.randint(30, 52)
            _pine(mid, x, 240 + rng.randint(-3, 3), hgt, lighten(pine, rng.uniform(-0.05, 0.08)), snowy)
    elif theme == 'river':
        hill = {0: (126, 164, 120), 1: (104, 150, 100), 2: (170, 140, 96), 3: (200, 208, 220)}[season]
        for x in range(LW):
            y = 172 + int(10 * math.sin(x * 2 * math.pi * 3 / LW) + 6 * math.sin(x * 2 * math.pi * 7 / LW + 1))
            far.fill(hill, (x, y, 1, H - y))
        water = (110, 160, 190) if not snowy else (170, 196, 214)
        mid.fill(water, (0, 246, LW, 14))
        for x in range(0, LW, 23):
            mid.fill(lighten(water, 0.25), (x, 249 + (x // 23) % 3 * 3, 8, 1))
        mid.fill(darken(grass, 0.06), (0, 258, LW, H - 258))
        cols = [(110, 160, 84), (92, 146, 72), (204, 150, 70), (180, 110, 60)] if season == 2 else \
            [(110, 164, 90), (88, 144, 76), (124, 172, 98)]
        for x in range(0, LW, 28):
            xx = x + rng.randint(-8, 8)
            _tree(mid, xx, 246, rng.randint(9, 14), rng.choice(cols), season)
        # the old mill and its wheel, once along the bank
        mx = 840
        mid.fill((170, 150, 126), (mx, 212, 40, 34))
        pygame.draw.polygon(mid, (120, 74, 60), [(mx - 4, 213), (mx + 20, 196), (mx + 44, 213)])
        pygame.draw.circle(mid, (110, 84, 60), (mx + 46, 236), 13, 3)
        for k in range(6):
            a = k * math.pi / 3
            pygame.draw.line(mid, (110, 84, 60), (mx + 46, 236), (mx + 46 + int(13 * math.cos(a)),
                                                                  236 + int(13 * math.sin(a))))
    elif theme == 'coast':
        downs = {0: (140, 180, 118), 1: (120, 166, 100), 2: (176, 160, 104), 3: (204, 212, 222)}[season]
        sea = (96, 150, 186) if not snowy else (120, 156, 180)
        far.fill(lighten(sea, 0.12), (0, 186, LW, 3))
        far.fill(sea, (0, 189, LW, H - 189))
        for x in range(0, LW, 37):
            far.fill(lighten(sea, 0.2), (x + (x // 37 % 3) * 7, 196 + (x // 37 % 4) * 7, 10, 1))
        # the lighthouse far out on its rock
        lx = 980
        far.fill((120, 110, 100), (lx - 8, 200, 18, 6))
        far.fill((240, 236, 228), (lx - 3, 176, 7, 26))
        far.fill((200, 80, 70), (lx - 3, 184, 7, 4))
        far.fill((200, 80, 70), (lx - 3, 194, 7, 4))
        far.fill((60, 60, 60), (lx - 4, 172, 9, 4))
        for x in range(LW):
            y = 224 + int(10 * math.sin(x * 2 * math.pi * 2 / LW) + 6 * math.sin(x * 2 * math.pi * 5 / LW))
            mid.fill(downs, (x, y, 1, H - y))
        def dy(x):
            return 224 + int(10 * math.sin(x * 2 * math.pi * 2 / LW) + 6 * math.sin(x * 2 * math.pi * 5 / LW))
        for x in range(40, LW - 40, 70):
            xx = x + rng.randint(-20, 20)
            gy = dy(xx) + 3
            if rng.random() < 0.4:
                pygame.draw.line(mid, (96, 76, 60), (xx, gy), (xx + 4, gy - 12), 2)
                crown = darken(downs, 0.22)
                pygame.draw.ellipse(mid, crown, (xx - 2, gy - 20, 18, 9))
                pygame.draw.ellipse(mid, lighten(crown, 0.08), (xx + 2, gy - 21, 10, 5))
            elif season != 3:
                for k in range(rng.randint(1, 3)):
                    sx = xx + k * 7
                    sy = dy(sx) + 4
                    pygame.draw.ellipse(mid, (240, 238, 230), (sx, sy - 4, 6, 4))
                    mid.fill((50, 50, 50), (sx + 5, sy - 3, 2, 2))
    else:   # quarry
        rock = {0: (176, 160, 134), 1: (186, 166, 130), 2: (170, 146, 116), 3: (206, 206, 214)}[season]
        for x in range(LW):
            y = 186 + int(6 * math.sin(x * 2 * math.pi * 4 / LW) + 3 * math.sin(x * 2 * math.pi * 11 / LW))
            far.fill(lerp_c(rock, (150, 160, 180), 0.35), (x, y, 1, H - y))
        for k in range(7):
            cx = k * LW // 7 + rng.randint(-40, 40)
            wd, ht = rng.randint(80, 130), rng.randint(30, 60)
            _wrap_poly(far, [(cx - wd, 236), (cx - wd + 20, 236 - ht), (cx + wd - 20, 236 - ht), (cx + wd, 236)],
                       darken(rock, 0.1))
            for j in range(3):
                far.fill(darken(rock, 0.2), (cx - wd + 26, 236 - ht + 10 + j * 9, 2 * wd - 52, 1))
        far.fill(darken(rock, 0.06), (0, 234, LW, H - 234))
        mid.fill(lerp_c(gd, rock, 0.5), (0, 250, LW, H - 250))
        for x in range(0, LW, 16):
            xx = x + rng.randint(-5, 5)
            if rng.random() < 0.3:
                pygame.draw.ellipse(mid, darken(rock, 0.15), (xx, 242, rng.randint(8, 16), 10))
            else:
                c = gd if season != 3 else (214, 220, 230)
                for j in range(4):
                    mid.fill(c, (xx + j * 2, 250 - rng.randint(2, 7), 1, 7))
        # an old crane over the pit
        cx = 520
        mid.fill((130, 90, 60), (cx, 170, 4, 80))
        pygame.draw.line(mid, (130, 90, 60), (cx + 2, 172), (cx + 70, 190), 3)
        pygame.draw.line(mid, (90, 90, 90), (cx + 66, 190), (cx + 66, 214))
    _LAYERS[key] = (far, mid)
    return far, mid


def _animal(s, kind, x, y, t, k=1.0):
    """Draw a little crowd of the road's animal standing at road height y."""
    c = ANIMAL_LOOK[kind]
    bob = int(math.sin(t * 6) * 1)
    if kind == 'deer':
        s.fill(c, (x - 9, y - 14 + bob, 16, 7))
        for lx in (x - 8, x - 5, x + 3, x + 5):
            s.fill(darken(c, 0.2), (lx, y - 8 + bob, 1, 8 - bob))
        s.fill(c, (x + 5, y - 20 + bob, 3, 7))
        s.fill(c, (x + 6, y - 21 + bob, 6, 4))
        s.fill((60, 40, 30), (x + 11, y - 20 + bob, 1, 1))
        s.fill((236, 230, 220), (x - 10, y - 14 + bob, 2, 3))
        pygame.draw.line(s, (110, 80, 56), (x + 7, y - 21 + bob), (x + 5, y - 26 + bob))
        pygame.draw.line(s, (110, 80, 56), (x + 9, y - 21 + bob), (x + 11, y - 26 + bob))
    elif kind == 'ducks':
        for i in range(3):
            dx = x - 12 + i * 10
            b = int(math.sin(t * 9 + i * 2) * 1)
            pygame.draw.ellipse(s, c, (dx - 4, y - 6 + b, 9, 5))
            s.fill((60, 120, 80), (dx + 3, y - 9 + b, 3, 3))
            s.fill((240, 170, 60), (dx + 6, y - 8 + b, 2, 1))
            s.fill((240, 170, 60), (dx, y - 1, 1, 1))
    elif kind == 'sheep':
        for i in range(2):
            dx = x - 8 + i * 14
            b = int(math.sin(t * 5 + i * 3) * 1)
            pygame.draw.ellipse(s, c, (dx - 6, y - 12 + b, 12, 8))
            s.fill((50, 46, 46), (dx + 5, y - 11 + b, 3, 4))
            for lx in (dx - 4, dx + 3):
                s.fill((50, 46, 46), (lx, y - 5 + b, 1, 5 - b))
    else:
        pygame.draw.ellipse(s, c, (x - 6, y - 6, 11, 6))
        for k2 in range(5):
            s.set_at((x - 5 + k2 * 2, y - 6), darken(c, 0.3))
        s.fill((220, 190, 160), (x + 4, y - 3, 3, 2))
        s.set_at((x + 7, y - 3), (30, 20, 20))


def _lost_icon(s, lid, x, y, t):
    if lid == 'kite':
        pygame.draw.polygon(s, (230, 90, 90), [(x, y - 12), (x + 6, y - 6), (x, y), (x - 6, y - 6)])
        pygame.draw.line(s, (250, 220, 100), (x, y - 12), (x, y))
        pygame.draw.line(s, (240, 240, 240), (x, y), (x - 4 + int(math.sin(t * 3) * 2), y + 4))
    elif lid in ('notebook', 'sketchbook'):
        col = (90, 120, 80) if lid == 'notebook' else (170, 80, 70)
        s.fill(darken(col, 0.3), (x - 5, y - 4, 10, 4))
        s.fill(col, (x - 5, y - 5, 10, 3))
        s.fill((240, 232, 210), (x - 4, y - 2, 8, 1))
    else:
        s.fill((210, 170, 60), (x - 3, y - 3, 6, 2))
        s.fill((200, 60, 50), (x + 2, y - 3, 2, 2))
        s.set_at((x - 4, y - 2), (200, 200, 210))


# ---------------------------------------------------------------- the drive
class Drive:
    kind = 'drive'

    def __init__(self, g, rid, back=False, cooler=None, rng=None):
        self.g = g
        self.r = TR.ROUTES[rid]
        self.rid = rid
        self.back = back
        self.cooler = cooler
        self.rng = rng or random.Random()
        self.L = float(self.r['length'])
        fwd = road_fn(self.r)
        self.h = (lambda x: fwd(self.L - x)) if back else fwd
        self.x = 30.0
        self.v = 0.0
        self.t = 0.0
        self.cam_y = self.h(self.x) - BASE
        self.bounce = 0.0
        self.bounce_v = 0.0
        self.wheel = 0.0
        self.panel = None               # None or 'pause'
        self.done = False
        self.tacc = 0.0
        self.mins = 0.0
        self.horn_t = 0.0
        self.fx = []                    # [x, y, vx, vy, life, colour or text]
        self.puffs = []
        self.rider = None               # a hitchhiker in the cab: (name, shirt, hair, hat)
        self.flash = 0.0
        self.snap = None                # the last photo, shown as a postcard
        self.snap_t = 0.0
        self.want_snap = None
        self.spin = 0.0                 # wheels spinning in the snow
        self.bot = (0.0, 0.0)
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self.glows = (art.glow(60, (255, 236, 170)), art.glow(10, (255, 240, 190)))
        self._tint = {}
        self.events = self._make_events()
        self.dest = 'home' if back else self.r['to']
        self.said_snow = False

    def _along(self, p):
        return (1.0 - p if self.back else p) * self.L

    def _make_events(self):
        g = self.g
        st = g.truck
        rng = random.Random(g.day * 977 + hash(self.rid) % 1000 + (7 if self.back else 0))
        ev = []
        for rid, vid, p, name in TR.VIEWS:
            if rid == self.rid:
                ev.append(dict(kind='view', id=vid, name=name, x=self._along(p), done=False))
        lid, thing, who, p, _ = TR.LOST[self.rid]
        if lid not in st['found'] and not self.back:
            ev.append(dict(kind='lost', id=lid, name=thing, x=self._along(p), done=False))
        if rng.random() < 0.5:
            look = rng.choice(TR.HIKERS)
            ev.append(dict(kind='hiker', look=look, x=self.L * rng.uniform(0.18, 0.4), done=False))
        if rng.random() < 0.65:
            ev.append(dict(kind='animal', id=TR.ANIMALS[self.rid], x=self.L * rng.uniform(0.5, 0.75), state='wait',
                           t=0.0, done=False))
        n = 16 if self.r.get('rough') else 6
        self.bumps = sorted(rng.uniform(RAMP, self.L - RAMP) for _ in range(n))
        self.bumped = set()
        ev.sort(key=lambda e: e['x'])
        return ev

    # ------------------------------------------------------------ road facts
    def slope(self, x):
        return (self.h(x + 3) - self.h(x - 3)) / 6.0

    def curve(self, x):
        return (self.h(x + 6) - 2 * self.h(x) + self.h(x - 6)) / 36.0

    def grip(self):
        g = self.g
        if g.weather == 'snow' or g.env.season == 3:
            return 0.95 if TR.has(g, 'snow') else 0.55
        if g.weather in ('rain', 'storm'):
            return 0.82
        return 1.0

    def night(self):
        return self.g.env.nf > 0.35

    def nearest(self):
        """Something you've stopped beside: (event) or None."""
        if self.v > 12:
            return None
        for e in self.events:
            if e['done'] or e['kind'] == 'animal':
                continue
            reach = 60 if e['kind'] == 'view' else 34
            if abs(e['x'] - self.x) < reach:
                if e['kind'] == 'hiker' and self.rider:
                    continue
                return e
        return None

    def prompt(self):
        e = self.nearest()
        if not e:
            return None
        if e['kind'] == 'view':
            return 'Take a photo of %s' % e['name'] if e['id'] not in self.g.truck['photos'] else \
                'Another photo of %s' % e['name']
        if e['kind'] == 'lost':
            return 'Pick up %s' % e['name']
        if e['kind'] == 'hiker':
            return 'Offer %s a lift' % e['look'][0].split(',')[0].split(' with')[0].split(' and')[0]
        return None

    # ------------------------------------------------------------ doing things
    def interact(self):
        e = self.nearest()
        if not e:
            return
        g = self.g
        st = g.truck
        if e['kind'] == 'view':
            new = e['id'] not in st['photos']
            if new:
                st['photos'].append(e['id'])
                g.coins += 25
            self.flash = 1.0
            self.want_snap = e['name']
            g.audio.play('shutter', 0.7)
            g.toast(('Photo: %s (%d of %d viewpoints). +25 coins' % (e['name'], len(st['photos']), len(TR.VIEWS)))
                    if new else 'Another lovely photo of %s.' % e['name'], (110, 130, 170))
            e['done'] = True
            g.check_badges()
        elif e['kind'] == 'lost':
            st['found'].append(e['id'])
            e['done'] = True
            g.audio.play('jingle2', 0.6)
            g.toast('%s! You put it safe on the seat to give back.' % e['name'], (200, 150, 80))
            self._burst(e['x'], self.h(e['x']) - 6)
        elif e['kind'] == 'hiker':
            self.rider = e['look']
            e['done'] = True
            g.audio.play('door', 0.6)
            self.pop('Hop in!')

    def honk(self):
        g = self.g
        if self.horn_t > 0:
            return
        self.horn_t = 0.6
        g.audio.play('horn', 0.6)
        for e in self.events:
            if e['kind'] == 'animal' and e['state'] == 'cross' and 0 < e['x'] - self.x < 240:
                e['t'] = min(e['t'], 0.8)

    def pop(self, text):
        self.fx.append([self.x + 10, self.h(self.x) - 50, 0.0, -12.0, 1.8, text])

    def _burst(self, x, y, n=18, col=(255, 236, 170)):
        rng = self.rng
        for _ in range(n):
            self.fx.append([x + rng.uniform(-6, 6), y + rng.uniform(-4, 4), rng.uniform(-24, 24),
                            rng.uniform(-40, -10), rng.uniform(0.7, 1.2), col])

    def turn_round(self):
        """Give up on this drive and go back where you came from."""
        g = self.g
        self.done = True
        self.panel = None
        g.audio.engine(0)
        if self.back:
            import areas
            areas.enter(g, self.r['to'])
        else:
            if self.cooler:
                g.basket.extend(self.cooler['fish'])
            g.aqscene = None
            g.overlay = None
            g.place, g.spot = 'lake', 'dock'
            g.toast('You turn the truck round and head home.', (150, 130, 110))
        g.fade, g.fade_dir = 1.0, -1
        g.save()

    def finish(self):
        g = self.g
        self.done = True
        g.audio.engine(0)
        g.audio.play('door', 0.6)
        if self.rider:
            pay = 30 + (sum(map(ord, self.rider[0])) % 4) * 10
            g.coins += pay
            g.truck['lifts'] += 1
            g.toast("%s: '%s' (+%d coins)" % (self.rider[0].split(',')[0], TR.HIKER_LINES[g.day % len(TR.HIKER_LINES)],
                                              pay), (110, 140, 120))
        if self.cooler:
            self.cooler['ice'] = max(0.0, self.cooler['ice'])
        TR.arrive(g, self.rid, self.dest, self.cooler)

    # ------------------------------------------------------------ input
    def key(self, k):
        g = self.g
        if self.panel == 'pause':
            if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_e):
                self.close_panel()
            elif k == pygame.K_t:
                self.turn_round()
            return
        if k == pygame.K_ESCAPE:
            self.panel = 'pause'
            g.release_holds()
            g.audio.play('page', 0.5)
            return
        if k in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.interact()
        elif k == pygame.K_h:
            self.honk()

    def press(self, src='mouse'):
        if self.panel or src != 'mouse':
            return
        g = self.g
        if self.nearest() and g.ui.mouse[1] < 600:
            self.interact()

    def release(self, src='mouse'):
        pass

    def close_panel(self):
        self.panel = None
        self.g.audio.play('page', 0.5)

    def controls(self):
        """(gas 0..1, brake 0..1) from the keys, the pad (via held keys) or the bot."""
        g = self.g
        if HEADLESS or getattr(g, 'bot_drive', False):
            return self.bot
        if g.typing is not None:
            return 0.0, 0.0
        keys = g.keys()
        mb = pygame.mouse.get_pressed()[0] if not HEADLESS else False
        gas = 1.0 if (keys[pygame.K_d] or keys[pygame.K_RIGHT] or keys[pygame.K_w] or keys[pygame.K_UP]) else 0.0
        brk = 1.0 if (keys[pygame.K_a] or keys[pygame.K_LEFT] or keys[pygame.K_s] or keys[pygame.K_DOWN]) else 0.0
        if not gas and not brk and mb and g.ui.mouse[1] < 600:
            gas = 1.0 if g.ui.mouse[0] > 640 else 0.0
            brk = 1.0 if g.ui.mouse[0] <= 640 else 0.0
        return gas, brk

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.done:
            return
        g = self.g
        self.t += dt
        dt = min(dt, 0.05)
        self.horn_t = max(0.0, self.horn_t - dt)
        self.flash = max(0.0, self.flash - dt * 3)
        if self.snap:
            self.snap_t += dt
            if self.snap_t > 3.2:
                self.snap = None
        for p in self.fx:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if not isinstance(p[5], str):
                p[3] += 50 * dt
            p[4] -= dt
        self.fx = [p for p in self.fx if p[4] > 0]
        for p in self.puffs:
            p[0] += p[2] * dt
            p[1] -= 6 * dt
            p[3] -= dt
        self.puffs = [p for p in self.puffs if p[3] > 0]
        if self.panel:
            g.audio.engine(0.0)
            return
        gas, brk = self.controls()
        grip = self.grip()
        sl = self.slope(self.x)
        a = GRAV * sl / math.sqrt(1 + sl * sl)              # downhill (h grows) pulls you on
        a += GAS * gas * grip
        if brk and self.v > 0:
            a -= BRAKE * brk * (0.55 + 0.45 * grip)
        a -= 0.34 * self.v + 0.0018 * self.v * self.v
        self.spin = 0.0
        if gas and a < 14 and self.v < 30:
            # can't quite make the climb: crawl up it with the wheels spinning
            if grip < 0.9:
                self.spin = 1.0
                if not self.said_snow and not TR.has(g, 'snow'):
                    self.said_snow = True
                    g.toast('The wheels spin on the snow. Snow tyres would help on these climbs.', (130, 150, 180))
            a = 14.0
        # animals on the road: ease to a stop behind them
        block = None
        for e in self.events:
            if e['kind'] != 'animal' or e['state'] == 'gone':
                continue
            gap = e['x'] - self.x
            if e['state'] == 'wait' and gap < 190:
                e['state'], e['t'] = 'cross', self.rng.uniform(4.5, 7.0)
            if e['state'] == 'cross':
                e['t'] -= dt
                if e['t'] <= 0:
                    e['state'], e['t'] = 'gone', 1.0
                elif 0 < gap < 120:
                    block = gap
            break
        self.v = max(0.0, self.v + a * dt)
        if block is not None:
            stop = max(0.0, (block - 48) * 2.2)
            if self.v > stop:
                self.v = max(stop, self.v - 260 * dt)
        if not gas and not brk and self.v < 3 and abs(sl) < 0.5:
            self.v = 0.0          # the handbrake
        dx = self.v * dt
        self.x = min(self.L, self.x + dx)
        self.wheel += dx / 5.0 + self.spin * dt * 20
        # the clock and the cooler
        per = self.r['minutes'] / self.L
        self.tacc += dx * per
        while self.tacc >= 1.0:
            self.tacc -= 1.0
            self.mins += 1
            g.advance_time(1)
            if self.cooler:
                self.cooler['ice'] -= 1.0 / TR.ice_minutes(g)
        # bumps, crests and dips: the springs, and the cooler
        cap = 1.6 if TR.has(g, 'cooler') else 1.0
        jolt = 0.0
        for b in self.bumps:
            if b not in self.bumped and self.x >= b:
                self.bumped.add(b)
                self.bounce_v -= 10 + self.v * 0.35
                if self.v > 60:
                    jolt += ((self.v - 60) / 90.0) ** 2 * 0.6
                g.audio.play('creak', min(0.6, 0.1 + self.v / 300))
        va = self.v * self.v * self.curve(self.x)
        self.bounce_v += -va * 0.08 * dt * 10
        if abs(va) > 40:
            jolt += (abs(va) - 40) * 0.004 * dt
        self.bounce_v += (-self.bounce * 90 - self.bounce_v * 9) * dt
        self.bounce += self.bounce_v * dt
        self.bounce = max(-6.0, min(6.0, self.bounce))
        if self.cooler:
            c = self.cooler
            c['jostle'] = max(0.0, c['jostle'] + jolt - 0.04 * dt)
            if c['jostle'] >= cap and c['fish']:
                c['fish'].pop()
                c['spilled'] += 1
                g.truck['spilled'] += 1
                c['jostle'] = 0.25
                self.pop('A fish bounced out!')
                g.audio.play('plop', 0.6)
                self._burst(self.x - 20, self.h(self.x) - 20, 10, (180, 210, 230))
        # exhaust and dust
        if self.rng.random() < dt * (3 + gas * 8):
            self.puffs.append([self.x - 24, self.h(self.x) - 6 + self.bounce, -6 - self.v * 0.1, 1.2])
        if (self.r.get('rough') or g.env.season == 2) and self.v > 40 and self.rng.random() < dt * self.v * 0.06:
            self.fx.append([self.x - 14, self.h(self.x) - 2, -self.v * 0.2, -8.0, 0.6, (190, 170, 140)])
        cy = self.h(self.x) - BASE
        self.cam_y += (cy - self.cam_y) * min(1.0, dt * 3)
        g.audio.engine(0.15 + 0.55 * min(1.0, self.v / 150) + 0.3 * gas)
        if self.x >= self.L - 1:
            self.finish()

    def audio_ctx(self):
        return {'feeder': False, 'chimes': False}

    # ------------------------------------------------------------ the bot: drive along, stop for everything
    def auto(self, dt, rng):
        if self.panel:
            self.close_panel()
            return
        e = self.nearest()
        if e:
            self.bot = (0.0, 1.0)
            self.interact()
            return
        target = None
        for ev in self.events:
            if not ev['done'] and ev['kind'] in ('view', 'lost', 'hiker') and ev['x'] > self.x - 10:
                if ev['kind'] == 'hiker' and self.rider:
                    continue
                target = ev
                break
        for ev in self.events:
            if ev['kind'] == 'animal' and ev['state'] == 'cross' and 0 < ev['x'] - self.x < 160:
                self.honk()
        cruise = 95.0 if self.cooler else 140.0
        if target and target['x'] - self.x < 160:
            want = max(0.0, (target['x'] - self.x) * 0.8)
            self.bot = (1.0 if self.v < want else 0.0, 1.0 if self.v > want + 6 else 0.0)
        else:
            self.bot = (1.0 if self.v < cruise else 0.0, 1.0 if self.v > cruise + 20 else 0.0)

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def _tinted(self, surf, key, amb):
        k = (key, tuple(c // 6 for c in amb))
        out = self._tint.get(k)
        if out is None:
            if len(self._tint) > 12:
                self._tint.clear()
            out = surf.copy()
            out.fill((*amb, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._tint[k] = out
        return out

    def draw_world(self, frame):
        g = self.g
        env = g.env
        t = self.t
        season = env.season
        frame.fill(env.sky[2])
        g.world._sky(frame, env)
        far, mid = build_layers(self.r['theme'], season)
        amb = env.amb if env.fog <= 0.01 else lerp_c(env.amb, env.fog_color, env.fog * 0.5)
        camx = self.x - TX
        vy = int(self.cam_y * 0.25)
        fa = self._tinted(far, 'far', lerp_c(amb, env.sky[2], 0.4))
        ox = -int(camx * 0.12) % LW
        frame.blit(fa, (ox - LW, -vy))
        frame.blit(fa, (ox, -vy))
        ma = self._tinted(mid, 'mid', lerp_c(amb, env.sky[2], 0.15))
        ox = -int(camx * 0.38) % LW
        vy2 = int(self.cam_y * 0.55)
        frame.blit(ma, (ox - LW, 10 - vy2))
        frame.blit(ma, (ox, 10 - vy2))
        near = self.near
        near.fill((0, 0, 0, 0))
        self._draw_road(near, camx, t, season)
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(near, (0, 0))
        self._lights(frame, camx, t)
        g.world._weather(frame, env)
        if self.want_snap:
            self.snap = (frame.copy(), self.want_snap)
            self.snap_t = 0.0
            self.want_snap = None
        if self.flash > 0:
            frame.fill((int(255 * self.flash),) * 3, special_flags=pygame.BLEND_ADD)

    def sy(self, wx):
        return int(self.h(wx) - self.cam_y)

    def _draw_road(self, s, camx, t, season):
        g = self.g
        theme = self.r['theme']
        grass = art.GRASS[season]
        gd = art.GRASS_D[season]
        soil = {'quarry': (150, 128, 100), 'coast': (150, 120, 90)}.get(theme, (122, 92, 66))
        if season == 3:
            soil = lerp_c(soil, (210, 216, 228), 0.5)
        tar = (150, 138, 120) if theme == 'quarry' else (88, 86, 92)
        if g.weather in ('rain', 'storm'):
            tar = darken(tar, 0.15)
        ix = int(camx)
        # posts, poles and wires behind the road
        poles = []
        for wx in range((ix // 40) * 40, ix + W + 40, 40):
            x = wx - ix
            y = self.sy(wx)
            if wx % 200 == 0:
                s.fill((110, 84, 62), (x, y - 58, 3, 58))
                s.fill((110, 84, 62), (x - 6, y - 54, 15, 2))
                poles.append((x + 1, y - 53))
            elif theme in ('river', 'coast') and season != 3 or theme == 'hill':
                s.fill((140, 110, 80), (x, y - 11, 2, 9))
                if theme != 'hill':
                    s.fill((150, 120, 90), (x - 20, y - 9, 40, 1))
        for (x1, y1), (x2, y2) in zip(poles, poles[1:]):
            mx, my = (x1 + x2) // 2, max(y1, y2) + 8
            pygame.draw.lines(s, (60, 56, 56), False, [(x1, y1), (mx, my), (x2, y2)])
        # roadside things
        for e in self.events:
            x = int(e['x'] - ix)
            if not -40 < x < W + 40:
                continue
            y = self.sy(e['x'])
            if e['kind'] == 'view':
                s.fill((110, 80, 56), (x - 1, y - 20, 2, 18))
                s.fill((240, 232, 210), (x - 9, y - 26, 18, 9))
                s.fill((70, 60, 60), (x - 4, y - 24, 8, 5))
                s.fill((150, 190, 220), (x - 1, y - 23, 3, 3))
                s.fill((130, 96, 66), (x + 12, y - 7, 16, 2))
                s.fill((110, 80, 56), (x + 13, y - 5, 1, 4))
                s.fill((110, 80, 56), (x + 26, y - 5, 1, 4))
                if not e['done'] and e['id'] not in g.truck['photos'] and math.sin(t * 4) > 0:
                    s.fill((255, 230, 120), (x - 1, y - 36, 3, 6))
                    s.fill((255, 230, 120), (x - 1, y - 28, 3, 1))
            elif e['kind'] == 'lost' and not e['done']:
                _lost_icon(s, e['id'], x, y - 3, t)
            elif e['kind'] == 'hiker' and not e['done']:
                name, shirt, hair, hat = e['look']
                T.ground_shadow(s, x, y - 2, 12, 50)
                T.walker(s, x, y - 2, -1, 0, shirt, hair, hat, season)
                s.fill((236, 200, 170), (x - 8, y - 22 + int(math.sin(t * 3) > 0), 3, 2))
        # the road itself, column by column
        for x in range(0, W, 2):
            wx = ix + x
            y = self.sy(wx)
            if y >= H:
                continue
            s.fill(tar, (x, y, 2, 6))
            s.fill(lighten(tar, 0.12), (x, y, 2, 1))
            if theme != 'quarry' and (wx // 18) % 2 == 0:
                s.fill((232, 226, 196), (x, y + 2, 2, 1))
            s.fill(grass, (x, y + 6, 2, 3))
            s.fill(gd, (x, y + 9, 2, 2))
            s.fill(soil, (x, y + 11, 2, H - y - 11))
            s.fill(darken(soil, 0.08), (x, y + 30, 2, H - y - 30))
            s.fill(darken(soil, 0.16), (x, y + 56, 2, max(0, H - y - 56)))
            hsh = (wx // 2 * 2654435761) & 0xffff
            if hsh % 29 == 0:
                sy = y + 16 + hsh % 50
                s.fill(lighten(soil, 0.18), (x, sy, 4, 2))
                s.fill(darken(soil, 0.25), (x, sy + 2, 4, 1))
            elif hsh % 41 == 0 and season != 3 and theme != 'quarry':
                s.fill(gd, (x, y + 4, 1, 3))
                s.fill((240, 220, 120) if hsh % 3 else (230, 140, 170), (x, y + 3, 1, 1))
            if theme == 'quarry' and (wx * 7) % 13 == 0:
                s.fill(darken(tar, 0.2), (x, y + 1, 1, 1))
        for b in self.bumps:
            x = int(b - ix)
            if -4 < x < W + 4:
                y = self.sy(b)
                s.fill(darken(tar, 0.35), (x - 2, y, 5, 2))
        # the start and end signs
        for wx, label in ((60, None), (self.L - 70, self.dest)):
            x = int(wx - ix)
            if -60 < x < W + 60:
                y = self.sy(wx)
                s.fill((110, 80, 56), (x, y - 26, 2, 24))
                s.fill((90, 130, 90), (x - 18, y - 34, 38, 12))
                s.fill((240, 240, 230), (x - 16, y - 32, 34, 1))
        # animals
        for e in self.events:
            if e['kind'] != 'animal' or (e['state'] == 'gone' and e['t'] <= 0):
                continue
            x = int(e['x'] - ix)
            if not -40 < x < W + 40:
                continue
            if e['state'] == 'gone':
                e['t'] -= 1 / 60.0
                if e['t'] <= 0:
                    continue
                x += int((1 - e['t']) * 30)
            _animal(s, e['id'], x, self.sy(e['x']) + 3, t + (2 if e['state'] == 'gone' else 0))
        # the truck
        self._draw_truck(s, ix, t, season)
        for p in self.puffs:
            a = max(0.0, min(1.0, p[3]))
            c = lerp_c((120, 120, 124), (220, 220, 224), 1 - a)
            s.fill(c, (int(p[0] - ix), int(p[1] - self.cam_y), 2 + int((1 - a) * 3), 2))
        for p in self.fx:
            if not isinstance(p[5], str):
                s.fill(p[5], (int(p[0] - ix), int(p[1] - self.cam_y), 2, 2))

    def _draw_truck(self, s, ix, t, season):
        g = self.g
        people = [(110, 140, 180)]
        try:
            import look as looks
            people = [looks.player_colors(g, season)[0]]
        except Exception:
            pass
        if self.rider:
            people.append(self.rider[1])
        spr = TR.truck_sprite(TR.paint_col(g), rack=TR.has(g, 'rack'), cooler=self.cooler is not None,
                              boat=TR.has(g, 'rack'), night=self.night(), people=people, cat=True, wheel=self.wheel)
        sl = self.slope(self.x)
        ang = -math.degrees(math.atan(sl))
        rot = pygame.transform.rotate(spr, ang)
        cx = TX
        cy = self.h(self.x) - self.cam_y
        a = math.radians(-ang)
        oy = -13 + self.bounce * 0.5
        px = cx + (-oy) * math.sin(a) * -1
        py = cy + oy * math.cos(a)
        T.ground_shadow(s, cx, int(cy) + 1, 26, 60)
        s.blit(rot, rot.get_rect(center=(int(px), int(py))))
        if self.spin:
            for k in range(2):
                s.fill((240, 244, 250), (cx - 18 - self.rng.randint(0, 6), int(cy) - self.rng.randint(1, 5), 2, 2))

    def _lights(self, frame, camx, t):
        if not self.night():
            return
        nf = self.g.env.nf
        big, small = self.glows
        sl = self.slope(self.x)
        a = math.atan(sl)
        cy = self.h(self.x) - self.cam_y - 11 + self.bounce * 0.5
        fx, fy = TX + 26 * math.cos(a), cy + 26 * math.sin(a)
        beam = self._beam()
        b = pygame.transform.rotate(beam, -math.degrees(a))
        b.fill((int(255 * nf),) * 3, special_flags=pygame.BLEND_MULT)
        ca, sa = math.cos(a), math.sin(a)
        mid_x, mid_y = fx + ca * beam.get_width() / 2, fy + sa * beam.get_width() / 2 + 3
        frame.blit(b, b.get_rect(center=(int(mid_x), int(mid_y))), special_flags=pygame.BLEND_ADD)
        add_glow(frame, small, (fx, fy), nf)
        add_glow(frame, big, (fx + 70 * math.cos(a), fy + 70 * math.sin(a) + 6), nf * 0.5)
        bx = TX - 26 * math.cos(a)
        frame.fill((int(120 * nf), 10, 10), (int(bx) - 1, int(cy + 2 - 26 * math.sin(a)), 2, 2),
                   special_flags=pygame.BLEND_ADD)

    _BEAM = None

    def _beam(self):
        """A soft cone of light, pointing right from its left middle: brightest near the lamp, fading out."""
        if Drive._BEAM is None:
            L, hh = 170, 64
            b = pygame.Surface((L, hh))
            b.fill((0, 0, 0))
            for x in range(L):
                k = x / L
                half = 2 + k * (hh / 2 - 6)
                fade = (1 - k) ** 1.4 * min(1.0, x / 6.0)
                for y in range(hh):
                    d = abs(y - hh / 2 + k * 6) / max(1.0, half)
                    if d < 1:
                        v = fade * (1 - d * d) * 0.42
                        b.set_at((x, y), (int(255 * v), int(246 * v), int(200 * v)))
            Drive._BEAM = b
        return Drive._BEAM

    # ------------------------------------------------------------ UI
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        st = g.truck
        dest = TR.AREA_NAMES.get(self.dest, 'your cabin')
        ui.blit_text(s, '%s  -  to %s' % (self.r['name'], dest), (sw // 2, 22), 'h3', (255, 250, 240), 'midtop',
                     (30, 30, 50))
        ui.blit_text(s, fmt_clock(g.minute), (24, 22), 'bodyb', (255, 250, 240), 'topleft', (30, 30, 50))
        # the trip bar
        bar = pygame.Rect(sw // 2 - 260, 66, 520, 10)
        pygame.draw.rect(s, (40, 36, 44), bar.inflate(4, 4), border_radius=7)
        pygame.draw.rect(s, (90, 84, 90), bar, border_radius=5)
        f = self.x / self.L
        pygame.draw.rect(s, (240, 200, 110), (bar.x, bar.y, int(bar.w * f), bar.h), border_radius=5)
        for e in self.events:
            ex = bar.x + int(bar.w * e['x'] / self.L)
            if e['kind'] == 'view':
                col = (150, 200, 240) if e['id'] in st['photos'] else (255, 255, 255)
                pygame.draw.rect(s, col, (ex - 5, bar.y - 12, 10, 7), border_radius=2)
                pygame.draw.circle(s, (40, 40, 50), (ex, bar.y - 9), 2)
            elif e['kind'] == 'lost' and not e['done']:
                U.star(s, (ex, bar.y - 9), 5, (250, 210, 100))
        tx = bar.x + int(bar.w * f)
        pygame.draw.rect(s, TR.paint_col(g), (tx - 7, bar.y - 2, 14, 8), border_radius=3)
        # speed and the cooler
        panel = pygame.Rect(sw - 250, sh - 150, 230, 130 if self.cooler else 62)
        panel.bottom = sh - 20
        ui.glass(s, panel, 150, 16)
        ui.blit_text(s, '%d km/h' % int(self.v * 0.45), (panel.x + 18, panel.y + 12), 'bodyb', (255, 250, 240))
        if self.spin:
            ui.blit_text(s, 'slipping!', (panel.right - 18, panel.y + 16), 'smallb', (190, 220, 250), 'topright')
        elif self.rider:
            ui.blit_text(s, 'with %s' % self.rider[0].split(',')[0].split(' with')[0].split(' and')[0],
                         (panel.right - 18, panel.y + 16), 'tiny', (230, 230, 220), 'topright')
        if self.cooler:
            c = self.cooler
            from data import FISH_BY_ID
            o = st['order']
            name = FISH_BY_ID[o['fish']]['name'] if o else 'fish'
            ui.blit_text(s, 'Cooler: %d %s' % (len(c['fish']), name), (panel.x + 18, panel.y + 46), 'small',
                         (236, 244, 250), maxw=panel.w - 30)
            cap = 1.6 if TR.has(g, 'cooler') else 1.0
            for i, (label, v, col) in enumerate((('Ice', max(0.0, c['ice']), (140, 200, 240)),
                                                 ('Bumps', min(1.0, c['jostle'] / cap), (240, 140, 110)))):
                y = panel.y + 80 + i * 22
                ui.blit_text(s, label, (panel.x + 18, y - 2), 'tiny', (230, 230, 220))
                r = pygame.Rect(panel.x + 80, y, panel.w - 100, 10)
                pygame.draw.rect(s, (50, 50, 60), r, border_radius=5)
                pygame.draw.rect(s, col, (r.x, r.y, int(r.w * v), r.h), border_radius=5)
        # words
        sc = self.x - TX
        for p in self.fx:
            if isinstance(p[5], str):
                ui.blit_text(s, p[5], (int((p[0] - sc) * k), int((p[1] - self.cam_y) * k)), 'bodyb',
                             (255, 246, 226), 'center', (30, 26, 30), alpha=int(255 * min(1.0, p[4])))
        # the postcard after a photo
        if self.snap:
            img, name = self.snap
            a = min(1.0, self.snap_t * 4, (3.2 - self.snap_t) * 3)
            pc = pygame.Rect(0, 0, 360, 240)
            pc.topright = (sw - 30, 100 + int((1 - a) * -40))
            ui.panel(s, pc, fill=(250, 246, 236), radius=6)
            pic = pygame.transform.smoothscale(img, (pc.w - 24, int((pc.w - 24) * H / W)))
            s.blit(pic, (pc.x + 12, pc.y + 12))
            ui.blit_text(s, name, (pc.centerx, pc.bottom - 22), 'smallb', U.INK, 'center')
        p = self.prompt() if self.panel is None else None
        if p:
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (int(TX * k), int((self.h(self.x) - self.cam_y - 60) * k))
            r.x = max(12, min(sw - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        elif self.panel is None:
            nxt = next((e for e in self.events if not e['done'] and e['kind'] in ('view', 'lost', 'hiker')
                        and 0 < e['x'] - self.x < 260), None)
            if nxt and self.v > 12:
                what = {'view': 'A viewpoint ahead: stop to take a photo', 'lost': 'Something in the verge ahead...',
                        'hiker': 'Someone ahead with a thumb out'}[nxt['kind']]
                ui.blit_text(s, what, (sw // 2, 100), 'smallb', (255, 244, 220), 'midtop', (30, 26, 30))
            blk = next((e for e in self.events if e['kind'] == 'animal' and e['state'] == 'cross'
                        and 0 < e['x'] - self.x < 200), None)
            if blk:
                nm = {'deer': 'Deer on the road!', 'ducks': 'Ducks crossing!', 'sheep': 'Sheep on the road!',
                      'hedgehog': 'A hedgehog!'}[blk['id']]
                ui.blit_text(s, nm + '  Wait, or toot the horn.', (sw // 2, 130), 'bodyb', (255, 236, 200), 'midtop',
                             (30, 26, 30))
        if self.panel is None:
            hint = g.hint([('key', 'D'), 'gas   ', ('key', 'A'), 'brake   ', ('key', 'E'), 'stop and look   ',
                           ('key', 'H'), 'horn   ', ('key', 'Esc'), 'pause'],
                          [('pad', 'RT'), 'gas   ', ('pad', 'LT'), 'brake   ', ('pad', 'A'), 'look   ',
                           ('pad', 'X'), 'horn   ', ('pad', 'B'), 'pause'])
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, sh - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
            return
        g.dim(s)
        rect = pygame.Rect(sw // 2 - 300, sh // 2 - 150, 600, 300)
        ui.panel(s, rect, radius=24)
        ui.blit_text(s, 'Pull over', (rect.centerx, rect.y + 30), 'h2', U.INK, 'midtop')
        ui.blit_text(s, '%s, %d%% of the way to %s.' % (self.r['name'], int(100 * self.x / self.L), dest),
                     (rect.centerx, rect.y + 90), 'small', U.SOFT, 'midtop')
        ui.button(s, (rect.x + 40, rect.bottom - 120, rect.w - 80, 50), 'Keep driving', self.close_panel, 'primary',
                  font='bodyb', nav=True)
        back = 'Turn round and go home' if not self.back else 'Turn round, back to %s' % TR.AREA_NAMES[self.r['to']]
        ui.button(s, (rect.x + 40, rect.bottom - 62, rect.w - 80, 44), back + '  (T)', self.turn_round, 'normal',
                  font='smallb', nav=True)
