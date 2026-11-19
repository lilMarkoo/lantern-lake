"""Cooking at the cabin stove, as a little playable scene.

Pressing Cook in the kitchen walks you into the cabin's kitchen corner. A short cutscene plays (a longer one the
very first time), then three quick steps decide how well the dish turns out:

  chop     press as the knife passes over each mark on the fish
  heat     hold to stoke the stove, let go to let it cool: keep the heat inside the moving green band
  finish   depends on the dish: flip it while it's golden (fried dishes), take it out of the oven when the crust is
           just right (pies and tarts), or shake in the seasoning as the shaker swings over the pot (soups, stews)

The three scores make a star rating (see kitchen.finish). Harder recipes move faster with less room for error.
Everything is drawn into a 320x180 room, scaled 2x into the world frame; the camera cuts and pans between shots
of the room, and Game.draw uses cam() as its cam_rect.
"""
import math
import random

import pygame

import art
import kitchen as K
import look as looks
import town
import ui as U
from art import darken, lighten, lerp_c
from data import ALL_BY_ID

RW, RH = 320, 180
FLOOR = 150
SHOTS = {'wide': (34, 45, 240, 135), 'board': (74, 96, 104, 58.5), 'stove': (132, 92, 104, 58.5),
         'oven': (140, 104, 88, 49.5), 'table': (186, 100, 96, 54), 'pot': (158, 100, 56, 31.5)}
TIER = {'fritters': 1, 'chowder': 1, 'grilled': 2, 'stew': 2, 'clam': 2, 'fishpie': 3, 'tart': 3, 'feast': 4}
FINISH = {'plate': 'flip', 'fritters': 'flip', 'feast': 'flip', 'pie': 'oven', 'tart': 'oven', 'bowl': 'season'}
FINISH_NAME = {'flip': 'Flip', 'oven': 'Bake', 'season': 'Season'}
SPOT = {'door': 18, 'board': 97, 'stove': 152, 'table': 206}
BOARD = (103, 131)              # cutting board x range; it lies on the counter top
TOP = 137                       # counter top y
POT_X = 184
STOOL_X = 173
CAT_COUNTER = (89.0, 137.0)
CAT_CHAIR = (258.0, 140.0)
FIRST_LINES = ["Grandma Rosie's recipe book. Every page smells a little of butter.",
               '"Chop it neat, keep the pot happy, and never rush the golden part."',
               'Biscuit has already claimed the best seat in the kitchen.']
WORDS = {3: 'Perfect!', 2: 'Lovely!', 1: 'A bit rough, but edible', 0: 'Oh no... burnt to a crisp'}
WALK = 46.0                     # room pixels a second


def stars_for(score):
    for n, cut in ((3, 0.85), (2, 0.6), (1, 0.3)):
        if score >= cut:
            return n
    return 0


def grade(q):
    return 'Perfect!' if q >= 0.9 else 'Good' if q >= 0.65 else 'Wobbly' if q >= 0.3 else 'Miss'


def _clamp(v, a, b):
    return a if v < a else b if v > b else v


def sky_at(minute):
    """(window colour, darkness 0..1) for this time of day."""
    h = minute / 60.0
    day, dusk, night = (156, 204, 234), (238, 164, 120), (28, 34, 66)
    if 7 <= h < 17.5:
        return day, 0.0
    if 5 <= h < 7:
        if h < 6:
            return lerp_c(night, dusk, h - 5), 1 - (h - 5) * 0.5
        return lerp_c(dusk, day, h - 6), 0.5 - (h - 6) * 0.5
    if 17.5 <= h < 20:
        k = (h - 17.5) / 2.5
        return (lerp_c(day, dusk, k * 2) if k < 0.5 else lerp_c(dusk, night, k * 2 - 1)), k
    return night, 1.0


# ---------------------------------------------------------------- the room
SEASON_HILL = {0: (120, 176, 96), 1: (86, 150, 70), 2: (206, 132, 60), 3: (232, 238, 244)}


def build_room(season, minute, copper, g=None):
    s = pygame.Surface((RW, RH))
    rng = random.Random(7)
    sky, dark = sky_at(minute)
    # ceiling and rafters
    s.fill((92, 60, 44), (0, 0, RW, 52))
    for x in range(8, RW, 46):
        s.fill((72, 46, 34), (x, 0, 7, 52))
        s.fill((104, 70, 50), (x, 0, 1, 52))
    # plank wall
    for i, x in enumerate(range(0, RW, 12)):
        s.fill((160, 110, 76) if i % 2 else (152, 104, 72), (x, 56, 12, FLOOR - 56))
        s.fill((124, 82, 58), (x, 56, 1, FLOOR - 56))
        for _ in range(2):
            kx, ky = x + rng.randint(3, 9), rng.randint(60, 118)
            s.fill((132, 88, 60), (kx, ky, 2, 1))
    # wainscot
    s.fill((126, 84, 58), (0, 122, RW, FLOOR - 122))
    s.fill((176, 126, 88), (0, 121, RW, 2))
    for x in range(0, RW, 20):
        s.fill((106, 70, 50), (x, 123, 1, FLOOR - 123))
    # the beam
    s.fill((96, 62, 44), (0, 50, RW, 6))
    s.fill((124, 84, 60), (0, 50, RW, 1))
    s.fill((66, 42, 32), (0, 56, RW, 1))
    # floorboards
    s.fill((140, 96, 64), (0, FLOOR, RW, RH - FLOOR))
    for j, y in enumerate(range(FLOOR + 2, RH, 6)):
        s.fill((120, 80, 54), (0, y + 5, RW, 1))
        for x in range((j * 17) % 40, RW, 40):
            s.fill((112, 74, 50), (x, y, 1, 5))
    s.fill((92, 60, 44), (0, FLOOR, RW, 2))
    # the door, left
    s.fill((104, 68, 50), (4, 98, 30, FLOOR - 98))
    s.fill((170, 118, 80), (7, 101, 24, FLOOR - 101))
    for y0 in (104, 127):
        pygame.draw.rect(s, (146, 98, 66), (10, y0, 18, 19), 1)
    s.fill((236, 204, 120), (27, 126, 2, 2))
    # the window
    wx, wy, ww, wh = 49, 82, 27, 28
    s.fill(sky, (wx, wy, ww, wh))
    if dark > 0.6:
        for _ in range(7):
            s.set_at((wx + rng.randint(1, ww - 2), wy + rng.randint(1, 14)), (240, 240, 210))
        pygame.draw.circle(s, (240, 236, 210), (wx + 20, wy + 6), 3)
        pygame.draw.circle(s, sky, (wx + 21, wy + 5), 3)
    hill = SEASON_HILL[season]
    if dark > 0.3:
        hill = lerp_c(hill, (30, 40, 60), min(1.0, dark))
    pygame.draw.ellipse(s, darken(hill, 0.1), (wx - 6, wy + wh - 12, 24, 16))
    pygame.draw.ellipse(s, hill, (wx + 10, wy + wh - 10, 26, 16))
    s.fill(lerp_c((90, 140, 190), sky, 0.3), (wx, wy + wh - 4, ww, 4))
    pygame.draw.rect(s, (234, 224, 204), (wx - 2, wy - 2, ww + 4, wh + 4), 2)
    s.fill((234, 224, 204), (wx + ww // 2, wy, 2, wh))
    s.fill((234, 224, 204), (wx, wy + wh // 2, ww, 2))
    s.fill((206, 190, 168), (wx - 4, wy + wh + 2, ww + 8, 3))
    for cx in (wx - 6, wx + ww + 1):         # check curtains
        s.fill((196, 86, 74), (cx, wy - 4, 6, wh + 6))
        for yy in range(wy - 4, wy + wh + 2, 4):
            s.fill((226, 140, 120), (cx + (1 if (yy // 4) % 2 else 3), yy, 2, 2))
    s.fill((120, 84, 60), (wx - 8, wy - 6, ww + 16, 2))
    # shelves with jars over the counter
    jars = [(214, 120, 70), (236, 200, 96), (130, 170, 110), (200, 90, 100), (150, 190, 210), (226, 226, 210)]
    for row, y in enumerate((100, 114)):
        s.fill((112, 74, 52), (86, y, 64, 3))
        s.fill((140, 96, 66), (86, y, 64, 1))
        for bx in (90, 144):
            s.fill((92, 60, 44), (bx, y + 3, 2, 3))
        x = 90 + row * 3
        while x < 144:
            w, h = rng.choice(((5, 7), (6, 6), (4, 9), (7, 5)))
            c = rng.choice(jars)
            s.fill(darken(c, 0.15), (x, y - h, w, h))
            s.fill(c, (x + 1, y - h + 1, w - 2, h - 2))
            s.fill((240, 236, 224), (x, y - h - 1, w, 1))
            s.set_at((x + 1, y - h + 2), lighten(c, 0.4))
            x += w + rng.randint(1, 3)
    # utensil rail
    s.fill((150, 150, 160), (92, 120, 38, 1))
    for i, ux in enumerate(range(95, 128, 6)):
        kind = i % 3
        s.fill((120, 120, 130), (ux, 121, 1, 6))
        if kind == 0:
            pygame.draw.circle(s, (170, 170, 180), (ux, 129), 2)
        elif kind == 1:
            s.fill((150, 110, 80), (ux - 1, 127, 3, 3))
        else:
            pygame.draw.ellipse(s, (180, 180, 190), (ux - 2, 127, 4, 5), 1)
    # the counter
    s.fill((172, 122, 84), (84, TOP + 2, 76, FLOOR - TOP - 2))
    s.fill((150, 104, 70), (84, FLOOR - 2, 76, 2))
    for dx in (88, 113, 138):
        pygame.draw.rect(s, (148, 102, 70), (dx, TOP + 4, 20, FLOOR - TOP - 8), 1)
        s.fill((226, 196, 130), (dx + 17, TOP + 8, 1, 2))
    s.fill((222, 200, 168), (82, TOP, 80, 2))
    s.fill((196, 170, 136), (82, TOP + 2, 80, 1))
    # stove (pipe and body; the fire, pot and oven door are drawn each frame)
    body = (196, 120, 70) if copper else (66, 66, 74)
    trim = lighten(body, 0.25)
    s.fill((80, 80, 88), (POT_X - 2, 56, 5, 70))
    s.fill((110, 110, 118), (POT_X - 2, 56, 1, 70))
    s.fill((96, 96, 104), (POT_X - 3, 88, 7, 2))
    s.fill(darken(body, 0.2), (168, 135, 32, FLOOR - 135 - 1))
    s.fill(body, (169, 136, 30, FLOOR - 138))
    s.fill(trim, (166, 133, 36, 2))
    s.fill(darken(body, 0.4), (169, FLOOR - 1, 3, 1))
    s.fill(darken(body, 0.4), (196, FLOOR - 1, 3, 1))
    for i in range(3):                       # dials
        s.set_at((172 + i * 2, 137), (230, 220, 200))
    # table and chair
    s.fill((150, 100, 66), (214, 141, 38, 2))
    s.fill((178, 126, 86), (212, 139, 42, 2))
    for lx in (216, 247):
        s.fill((132, 88, 58), (lx, 143, 2, 9))
    s.fill((236, 230, 214), (220, 138, 26, 1))      # a cloth runner
    s.fill((140, 92, 60), (254, 142, 10, 2))
    s.fill((122, 80, 54), (262, 128, 2, 22))
    s.fill((122, 80, 54), (255, 144, 2, 6))
    # a little painting of the lake over the table (or Fen's portrait of you, once Fen has painted it)
    if g is not None and 'portrait' in g.story.get('flags', []):
        import scenes
        pygame.draw.rect(s, (150, 104, 64), (216, 80, 34, 32))
        pygame.draw.rect(s, (196, 146, 90), (216, 80, 34, 32), 1)
        r = pygame.Rect(218, 82, 30, 28)
        s.set_clip(r)
        scenes.paint_portrait(g, s, r, 1)
        s.set_clip(None)
    else:
        pygame.draw.rect(s, (120, 84, 56), (220, 92, 26, 18))
        s.fill((150, 196, 222), (222, 94, 22, 8))
        s.fill((96, 140, 90), (222, 101, 22, 2))
        s.fill((92, 140, 186), (222, 103, 22, 5))
        s.fill((240, 220, 120), (238, 96, 2, 2))
    # the rug
    pygame.draw.ellipse(s, (150, 62, 60), (96, 152, 120, 12))
    pygame.draw.ellipse(s, (190, 92, 76), (100, 153, 112, 10))
    pygame.draw.ellipse(s, (226, 186, 120), (112, 155, 88, 6), 1)
    return s


def draw_cat(s, x, fy, t, face=1, happy=False, ears_down=False, coat=None, pattern=None):
    """Biscuit sitting, in the room's pixel scale. coat is look.coat()'s colours (her ginger tabby by default),
    pattern the coat's id for the calico patches and siamese points."""
    tmp = pygame.Surface((26, 24), pygame.SRCALPHA)
    orange, white, dark, ear = coat or looks.coat(looks.DEFAULT)
    pts_c = dark if pattern == 'siamese' else orange
    cx, y = 12, 22
    sw = math.sin(t * (7.0 if happy else 2.0)) * 3
    pts = [(cx - 5, y - 2), (cx - 8, y - 3), (cx - 10 + sw * 0.3, y - 6), (cx - 10 + sw, y - 10)]
    pygame.draw.lines(tmp, pts_c, False, pts, 2)
    pygame.draw.ellipse(tmp, orange, (cx - 6, y - 9, 11, 9))
    if pattern == 'calico':
        tmp.fill(dark, (cx - 5, y - 7, 3, 3))
        tmp.fill((60, 54, 58), (cx - 2, y - 9, 3, 2))
    elif pattern != 'siamese':
        for i in (-4, -2):
            tmp.fill(dark, (cx + i, y - 8, 1, 3))
    tmp.fill(white, (cx + 1, y - 6, 3, 5))
    hx, hy = cx + 3, y - 12
    pygame.draw.circle(tmp, orange, (hx, hy), 4)
    if ears_down:
        pygame.draw.polygon(tmp, pts_c, [(hx - 4, hy - 1), (hx - 6, hy - 3), (hx - 2, hy - 3)])
        pygame.draw.polygon(tmp, pts_c, [(hx + 4, hy - 1), (hx + 6, hy - 3), (hx + 2, hy - 3)])
    else:
        pygame.draw.polygon(tmp, pts_c, [(hx - 4, hy - 2), (hx - 3, hy - 6), (hx - 1, hy - 3)])
        pygame.draw.polygon(tmp, pts_c, [(hx + 4, hy - 2), (hx + 3, hy - 6), (hx + 1, hy - 3)])
        tmp.set_at((hx - 3, hy - 4), ear)
        tmp.set_at((hx + 3, hy - 4), ear)
    if pattern == 'calico':
        tmp.fill(dark, (hx - 3, hy - 3, 3, 2))
    elif pattern == 'siamese':
        tmp.fill(lerp_c(orange, dark, 0.45), (hx - 2, hy, 5, 2))
    tmp.fill(white, (hx - 1, hy + 1, 3, 2))
    eye = (60, 40, 34) if sum(orange) > 330 else (206, 220, 104)
    if pattern == 'siamese':
        eye = (70, 130, 210)
    if happy:
        tmp.fill(eye, (hx - 2, hy - 1, 2, 1))
        tmp.fill(eye, (hx + 1, hy - 1, 2, 1))
    elif (t % 4.0) < 0.12:
        tmp.fill(eye, (hx - 2, hy, 1, 1))
        tmp.fill(eye, (hx + 2, hy, 1, 1))
    else:
        tmp.fill(eye, (hx - 2, hy - 1, 1, 2))
        tmp.fill(eye, (hx + 2, hy - 1, 1, 2))
    tmp.set_at((hx, hy + 1), (226, 130, 130))
    if face < 0:
        tmp = pygame.transform.flip(tmp, True, False)
    s.blit(tmp, (int(x) - 12, int(fy) - 22))


def heart(s, x, y, c=(236, 96, 120)):
    x, y = int(x), int(y)
    s.fill(c, (x - 2, y - 1, 2, 2))
    s.fill(c, (x + 1, y - 1, 2, 2))
    s.fill(c, (x - 1, y, 3, 2))
    s.set_at((x, y + 2), c)


# ---------------------------------------------------------------- the scene
class CookScene:
    def __init__(self, g, rid, items, first=False):
        self.g = g
        self.rid = rid
        self.r = K.RECIPE_BY_ID[rid]
        self.items = items                   # taken from the basket already; handed back if you back out
        self.first = first
        self.tier = TIER.get(rid, 2)
        self.speed = 1 + 0.15 * (self.tier - 1)
        self.tf = 1 + 0.12 * (self.tier - 1)          # tolerance shrinks by this
        self.kind = self.r['look'][0]
        self.finish_kind = FINISH.get(self.kind, 'flip')
        self.rng = random.Random()
        self.copper = g.has_up('stove')
        self.room = build_room(g.env.season, g.minute, self.copper, g)
        self.dark = sky_at(g.minute)[1]
        self.view = pygame.Surface((RW, RH))
        self.glow = art.glow(46, (255, 196, 110), 1.6)
        self.fire_glow = art.glow(18, (255, 140, 60), 1.4)
        self.t = 0.0
        self.st_t = 0.0
        self.state = 'intro'
        self.shot = 'wide'
        self.cam_f = list(SHOTS['wide'])
        self.bars = 1.0                      # letterbox, 0..1
        self.holds = set()
        self.px, self.pface, self.pstep = float(SPOT['door']), 1, 0.0
        self.ptarget = None
        self.carry = None                    # 'dish' while walking it to the table
        self.cat = list(CAT_COUNTER)
        self.cat_hop = None                  # (from, to, t) while Biscuit jumps
        self.cat_happy = 0.0
        self.parts = []
        self.floats = []                     # [text, x, y, t, colour] in room pixels
        self.scores = {}
        self.result = None
        self.stars_shown = 0
        self.cancelled = False
        self.done = False
        self.esc_hint = 0.0
        # the fish on the board: the first ingredient (an exact or rare fish if the recipe asks for one)
        main = items[0] if items else {'id': 'minnow'}
        spec = ALL_BY_ID.get(main['id']) or ALL_BY_ID['minnow']
        img = art.fish_sprite(spec, 1)
        bb = img.get_bounding_rect()
        img = img.subsurface(bb).copy() if bb.w and bb.h else img
        w = 24
        h = max(4, min(9, round(img.get_height() * w / max(1, img.get_width()))))
        self.fish_img = pygame.transform.scale(img, (w, h))
        self.fish_x0 = (BOARD[0] + BOARD[1]) // 2 - w // 2
        self.side_items = [ALL_BY_ID.get(b['id']) for b in items[1:4]]
        # chop
        n = 4 if self.tier >= 3 else 3
        self.targets = self._targets(n)
        self.ci = 0
        self.cuts = []
        self.kp, self.kdir = 0.0, 1
        self.slam = 0.0
        self.cut_t = 0.0
        self.chop_q = []
        # heat
        self.heat = 0.25
        self.heat_acc = 0.0
        self.heat_time = 0.0
        self.heat_dur = 6.0 + 0.5 * self.tier
        self.hot_warned = False
        self.smoke_t = 0.0
        # finish
        self.fin_q = []
        self.brown = 0.0
        self.flip = None                     # flip animation timer
        self.side = 0
        self.side_brown = [0.0, 0.0]
        self.oven_open = 0.0
        self.in_oven = False
        self.shake_w = 2 * math.pi / (1.7 / self.speed)
        self.shake_ph = self.rng.uniform(0, 6.28)
        self.shake_t = 0.0
        self.shaking = 0.0
        self.sprinkled = 0
        self.intro_len = 2.2 + (len(FIRST_LINES) * 2.8 if first else 0) + 1.8
        g.audio.play('creak', 0.4)

    # ------------------------------------------------------------ helpers
    def _targets(self, n):
        x0, w = self.fish_x0, self.fish_img.get_width()
        lo, hi = x0 + 4, x0 + w - 4
        for _ in range(50):
            xs = sorted(self.rng.uniform(lo, hi) for _ in range(n))
            if all(b - a >= 3.5 for a, b in zip(xs, xs[1:])):
                return xs
        return [lo + (hi - lo) * (i + 0.5) / n for i in range(n)]

    def knife_x(self):
        x0, w = self.fish_x0, self.fish_img.get_width()
        return x0 - 3 + self.kp * (w + 6)

    def band(self):
        """(centre, half width) of the green heat band right now."""
        tt = self.heat_time
        w = 2 * math.pi / (5.0 / self.speed)
        c = 0.5 + 0.2 * math.sin(w * tt - math.pi / 2)
        if self.tier >= 3:
            c += 0.07 * math.sin(2.7 * w * tt)
        return c, 0.13 / self.tf

    def zone(self):
        """The gold zone (start, end) on the browning / crust bar."""
        z = (0.17 if self.finish_kind == 'flip' else 0.14) / self.tf
        return 0.6, 0.6 + z

    def shaker_off(self):
        return 13 * math.sin(self.shake_ph + self.shake_w * self.shake_t)

    def holding(self):
        return bool(self.holds)

    def say(self, text, x, y, col=(255, 250, 230)):
        self.floats.append([text, x, y, 0.0, col])

    def puff(self, x, y, n, kind, col, spread=1.0, up=-14.0):
        for _ in range(n):
            self.parts.append([x + self.rng.uniform(-2, 2), y, self.rng.uniform(-8, 8) * spread,
                               up * self.rng.uniform(0.5, 1.2), 0.0, self.rng.uniform(0.5, 1.2), kind, col])

    def go(self, state, shot=None, walk=None):
        self.state = state
        self.st_t = 0.0
        if shot:
            self.shot = shot
        if walk is not None:
            self.ptarget = float(walk)

    def phase_names(self):
        return ['Chop', 'Heat', FINISH_NAME[self.finish_kind]]

    # ------------------------------------------------------------ input
    def press(self, src='key'):
        if src in self.holds:
            return
        self.holds.add(src)
        st = self.state
        if st == 'intro':
            self.skip_intro()
        elif st == 'chop':
            self.chop()
        elif st == 'flip':
            self.do_flip()
        elif st == 'oven':
            self.take_out()
        elif st == 'season':
            self.shake()
        elif st == 'plate' and self.result is not None:
            reveal = 0.55 + 0.45 * max(self.result['stars'], 1)
            if self.st_t < reveal:
                self.st_t = reveal
            elif self.st_t > 0.6:
                self.finish_scene()

    def release(self, src='key'):
        self.holds.discard(src)

    def key(self, k):
        if k == pygame.K_ESCAPE:
            self.escape()
        elif k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
            self.press('key' if k == pygame.K_SPACE else 'enter')
            if k != pygame.K_SPACE:
                self.release('enter')

    def escape(self):
        if self.state == 'intro' or (self.state == 'chop' and not self.cuts):
            self.cancelled = True
            self.g.basket.extend(self.items)
            self.items = []
            self.g.toast('You put the fish back in the basket.', (150, 140, 130))
            self.g.audio.play('page', 0.5)
            self.done = True
            self.g.end_cooking()
        elif self.state == 'plate' and self.result is not None:
            self.finish_scene()
        else:
            self.esc_hint = 2.5

    def skip_intro(self):
        self.px = float(SPOT['board'])
        self.pstep = 0.0
        self.cam_f = list(SHOTS['board'])
        self.start_chop()

    def start_chop(self):
        self.go('chop', 'board', SPOT['board'])
        self.g.audio.play('page', 0.4)

    # ------------------------------------------------------------ actions
    def chop(self):
        if self.slam > 0 or self.ci >= len(self.targets):
            return
        kx = self.knife_x()
        tx = self.targets[self.ci]
        d = abs(kx - tx)
        q = _clamp(1 - max(0.0, d - 0.5) / (2.8 / self.tf), 0.0, 1.0)
        self._cut(kx, q)

    def _cut(self, kx, q):
        self.chop_q.append(q)
        self.cuts.append(kx)
        self.ci += 1
        self.slam = 0.2
        self.cut_t = 0.0
        self.say(grade(q), kx, TOP - 16, (250, 230, 120) if q >= 0.9 else (255, 250, 230) if q >= 0.3
                 else (240, 140, 120))
        self.puff(kx, TOP - 3, 5, 'chip', (236, 230, 220), 1.4, -18)
        self.g.audio.play('snap' if q >= 0.3 else 'nibble', 0.45)

    def do_flip(self):
        if self.flip is not None or self.side > 1:
            return
        self._flip_score(self.brown)

    def _flip_score(self, b):
        a, z = self.zone()
        dist = 0.0 if a <= b <= z else min(abs(b - a), abs(b - z))
        q = _clamp(1 - dist / 0.12, 0, 1) if b < 1.0 else 0.0
        self.fin_q.append(q)
        self.side_brown[self.side] = b
        self.say(grade(q) if b < 1 else 'Scorched!', POT_X, 112, (250, 230, 120) if q >= 0.9 else
                 (255, 250, 230) if q >= 0.3 else (240, 140, 120))
        self.flip = 0.0
        self.g.audio.play('cast', 0.4)
        self.puff(POT_X, 128, 6, 'oil', (255, 240, 200), 1.2, -16)

    def take_out(self):
        if not self.in_oven or self.st_t < 0.8:
            return
        self._oven_score(self.brown)

    def _oven_score(self, b):
        a, z = self.zone()
        dist = 0.0 if a <= b <= z else min(abs(b - a), abs(b - z))
        q = _clamp(1 - dist / 0.12, 0, 1) if b < 1.0 else 0.0
        self.fin_q.append(q)
        self.in_oven = False
        self.side_brown[0] = b
        self.say(grade(q) if b < 1 else 'Burnt!', POT_X, 118, (250, 230, 120) if q >= 0.9 else
                 (255, 250, 230) if q >= 0.3 else (240, 140, 120))
        self.g.audio.play('creak', 0.5)
        self.st_t = 0.0
        if b >= 0.92:
            self.puff(POT_X, 140, 10, 'smoke', (70, 64, 64), 1.2, -12)

    def shake(self):
        if self.shaking > 0 or self.sprinkled >= 3 or self.ptarget is not None or self.st_t < 0.7:
            return
        self._shake_score(self.shaker_off())

    def _shake_score(self, off):
        q = _clamp(1 - max(0.0, abs(off) - 1.0) / (5.0 / self.tf), 0, 1)
        self.fin_q.append(q)
        self.sprinkled += 1
        self.shaking = 0.35
        sx = POT_X + off
        for _ in range(9):
            self.parts.append([sx + self.rng.uniform(-1.5, 1.5), 119.0, self.rng.uniform(-3, 3),
                               self.rng.uniform(10, 26), 0.0, 0.9, 'grain', self.rng.choice(
                                   ((90, 150, 70), (236, 220, 180), (120, 90, 60)))])
        self.say(grade(q), POT_X, 104, (250, 230, 120) if q >= 0.9 else (255, 250, 230) if q >= 0.3
                 else (240, 140, 120))
        self.g.audio.play('click', 0.5)
        self.shake_w *= 1.12
        self.shake_t = 0.0

    # ------------------------------------------------------------ flow
    def update(self, dt):
        if self.done:
            return
        self.t += dt
        self.st_t += dt
        # camera
        tgt = SHOTS[self.shot]
        k = 1 - math.exp(-dt * 3.2)
        for i in range(4):
            self.cam_f[i] += (tgt[i] - self.cam_f[i]) * k
        cine = self.state in ('intro', 'plate', 'move_heat', 'move_table')
        self.bars += ((1.0 if cine else 0.0) - self.bars) * (1 - math.exp(-dt * 5))
        # the player walks
        if self.ptarget is not None:
            d = self.ptarget - self.px
            if abs(d) > 0.6:
                self.pface = 1 if d > 0 else -1
                self.px += self.pface * min(abs(d), WALK * dt)
                self.pstep += dt * 11
            else:
                self.px = self.ptarget
                self.ptarget = None
                self.pstep = 0.0
        self.esc_hint = max(0.0, self.esc_hint - dt)
        self.cat_happy = max(0.0, self.cat_happy - dt)
        self._update_cat(dt)
        self._update_parts(dt)
        getattr(self, 'u_' + self.state)(dt)

    def _update_cat(self, dt):
        if self.cat_hop:
            a, b, t = self.cat_hop
            t += dt / 1.1
            if t >= 1:
                self.cat = list(b)
                self.cat_hop = None
                self.g.audio.play('purr', 0.5)
            else:
                self.cat = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - math.sin(t * math.pi) * 26]
                self.cat_hop = (a, b, t)

    def _update_parts(self, dt):
        keep = []
        for p in self.parts:
            p[4] += dt
            if p[4] >= p[5]:
                continue
            kind = p[6]
            if kind in ('chip', 'oil', 'grain'):
                p[3] += 90 * dt
            elif kind in ('steam', 'smoke'):
                p[2] *= 0.96
                p[3] *= 0.985
            elif kind == 'heart':
                p[2] = math.sin(p[4] * 5 + p[0]) * 4
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if kind == 'grain' and p[1] > 125 and abs(p[0] - POT_X) < 9:
                continue
            if kind in ('chip', 'oil', 'grain') and p[1] > (TOP if p[0] < 162 else 134):
                p[1] = TOP if p[0] < 162 else 134
                p[2] = p[3] = 0
            keep.append(p)
        self.parts = keep[-260:]
        for f in self.floats:
            f[3] += dt
            f[2] -= dt * 8
        self.floats = [f for f in self.floats if f[3] < 1.1]

    def u_intro(self, dt):
        if self.st_t > 0.3 and self.ptarget is None and self.px < SPOT['board']:
            self.ptarget = float(SPOT['board'])
        if self.first and int(self.st_t / 2.8) == 2 and not getattr(self, '_purred', False):
            self._purred = True
            self.g.audio.play('purr', 0.4)
            self.cat_happy = 1.2
        if self.st_t > self.intro_len - 1.6 and self.shot == 'wide':
            self.shot = 'board'
        if self.st_t >= self.intro_len:
            self.start_chop()

    def u_chop(self, dt):
        if self.slam > 0:
            self.slam = max(0.0, self.slam - dt)
        if self.ci < len(self.targets):
            rate = 0.85 * self.speed
            self.kp += self.kdir * dt * rate
            if self.kp > 1:
                self.kp, self.kdir = 2 - self.kp, -1
            elif self.kp < 0:
                self.kp, self.kdir = -self.kp, 1
            want = _clamp(self.knife_x() - 11, 92, 118)
            if abs(want - self.px) > 1.5:
                self.ptarget = want
            self.cut_t += dt
            if self.cut_t > 4.0:
                self.say('Too slow!', self.knife_x(), TOP - 22, (240, 140, 120))
                self._cut(self.targets[self.ci] + self.rng.choice((-3, 3)), 0.0)
        elif self.slam <= 0 and self.st_t > 0.4:
            if not hasattr(self, '_chop_end'):
                self._chop_end = self.st_t
            if self.st_t - self._chop_end > 0.7:
                self.scores['chop'] = sum(self.chop_q) / len(self.chop_q)
                self.carry = 'bowl'
                self.go('move_heat', 'stove', SPOT['stove'])

    def u_move_heat(self, dt):
        if self.ptarget is None and self.st_t > 0.9:
            self.carry = None
            self.g.audio.play('plop', 0.5)
            self.puff(POT_X, 124, 6, 'steam', (240, 240, 244), 1.0, -10)
            self.heat_time = 0.0
            self.go('heat')

    def u_heat(self, dt):
        h = self.holding()
        self.heat = _clamp(self.heat + (0.55 if h else -0.4) * dt, 0.0, 1.0)
        self.heat_time += dt
        c, bw = self.band()
        dist = abs(self.heat - c)
        if self.heat_time > 0.8:
            q = 1.0 if dist <= bw else max(0.0, 1 - (dist - bw) / 0.08)
            self.heat_acc += q * dt
        over = self.heat > c + bw + 0.08
        if over:
            self.smoke_t += dt
            if self.rng.random() < dt * 14:
                self.puff(POT_X + self.rng.uniform(-6, 6), 122, 1, 'smoke', (80, 74, 74), 0.6, -12)
            if not self.hot_warned:
                self.hot_warned = True
                self.g.audio.play('warn', 0.35)
        else:
            self.hot_warned = False
        if self.rng.random() < dt * (2 + 16 * self.heat):
            self.puff(POT_X + self.rng.uniform(-7, 7), 124, 1, 'bubble', lerp_c(self.r['look'][1], (255, 255, 255),
                                                                                   0.4), 0.3, -9)
        if self.rng.random() < dt * (1 + 6 * self.heat):
            self.puff(POT_X + self.rng.uniform(-6, 6), 120, 1, 'steam', (240, 240, 244), 0.7, -10)
        if self.heat_time >= self.heat_dur:
            self.scores['heat'] = self.heat_acc / (self.heat_dur - 0.8)
            self.holds.discard('auto')
            if self.finish_kind == 'oven':
                self.in_oven = False
                self.go('oven', 'oven', 165)
            elif self.finish_kind == 'season':
                self.go('season', None, STOOL_X)    # hop up on Grandma's step stool to reach over the pot
            else:
                self.go('flip')
            self.brown = 0.0
            self.g.audio.play('page', 0.4)

    def u_flip(self, dt):
        if self.flip is not None:
            self.flip += dt
            if self.flip >= 0.55:
                self.flip = None
                self.side += 1
                self.brown = 0.0
                if self.side > 1:
                    self.scores['finish'] = sum(self.fin_q) / len(self.fin_q)
                    self.go('to_table')
            return
        if self.side > 1:
            return
        self.brown += dt * (0.34 + 0.3 * self.brown) * self.speed
        if self.rng.random() < dt * (4 + 10 * self.brown):
            self.puff(POT_X + self.rng.uniform(-8, 8), 128, 1, 'oil', (255, 244, 210), 0.8, -14)
        if self.brown > 0.85 and self.rng.random() < dt * 10:
            self.puff(POT_X + self.rng.uniform(-6, 6), 126, 1, 'smoke', (80, 74, 74), 0.6, -10)
        if self.brown >= 1.0:
            self._flip_score(1.0)

    def u_oven(self, dt):
        if not self.in_oven and not self.fin_q:
            # slide the dish in
            self.oven_open = min(1.0, self.st_t / 0.4) if self.st_t < 0.9 else max(0.0, 1 - (self.st_t - 0.9) / 0.3)
            if self.st_t >= 1.2:
                self.in_oven = True
                self.oven_open = 0.0
                self.brown = 0.0
                self.st_t = 0.0
                self.g.audio.play('creak', 0.4)
            return
        if self.in_oven:
            rate = self.speed * (0.32 + 0.12 * math.sin(self.t * 3.1) + 0.08 * math.sin(self.t * 5.3))
            self.brown += dt * rate
            if self.brown > 0.88 and self.rng.random() < dt * 8:
                self.puff(186, 136, 1, 'smoke', (80, 74, 74), 0.5, -10)
            if self.brown >= 1.0:
                self._oven_score(1.0)
            return
        # taking it out
        self.oven_open = min(1.0, self.st_t / 0.3) if self.st_t < 0.8 else max(0.0, 1 - (self.st_t - 0.8) / 0.3)
        if self.st_t >= 1.1:
            self.oven_open = 0.0
            self.scores['finish'] = sum(self.fin_q) / len(self.fin_q)
            self.go('to_table')

    def u_season(self, dt):
        if self.ptarget is not None or self.st_t < 0.7:
            return
        self.shake_t += dt
        self.shaking = max(0.0, self.shaking - dt)
        if self.sprinkled < 3 and self.shake_t > 6.0:
            self.say('Too slow!', POT_X, 104, (240, 140, 120))
            self._shake_score(99)
        if self.rng.random() < dt * 4:
            self.puff(POT_X + self.rng.uniform(-6, 6), 122, 1, 'steam', (240, 240, 244), 0.7, -10)
        if self.sprinkled >= 3 and self.shaking <= 0:
            if not hasattr(self, '_season_end'):
                self._season_end = self.st_t
            if self.st_t - self._season_end > 0.6:
                self.scores['finish'] = sum(self.fin_q) / len(self.fin_q)
                self.go('to_table')

    def u_to_table(self, dt):
        # work out the result as the dish comes off the stove
        if self.result is None:
            sc = [self.scores.get(k, 0.0) for k in ('chop', 'heat', 'finish')]
            score = sum(sc) / 3.0
            stars = stars_for(score)
            self.result = K.finish(self.g, self.rid, stars, quiet=True)
            self.result['score'] = score
            self.items = []
        self.carry = 'dish'
        self.go('move_table', 'table', SPOT['table'] - 2)

    def u_move_table(self, dt):
        if self.ptarget is None and self.st_t > 0.6:
            self.carry = None
            self.g.audio.play('plop', 0.4)
            self.go('plate')
            self.pface = 1
            if self.result['stars'] == 0:
                self.puff(232, 134, 12, 'smoke', (70, 64, 64), 1.0, -10)
            elif self.result['stars'] == 3:
                self.cat_hop = (tuple(self.cat), CAT_CHAIR, 0.0)

    def u_plate(self, dt):
        st = self.result['stars']
        want = min(st, int((self.st_t - 0.5) / 0.45) + 1) if self.st_t > 0.5 else 0
        if want > self.stars_shown and self.stars_shown < 3:
            self.stars_shown = want
            self.g.audio.play('coin', 0.5)
        if self.st_t > 0.5 + 0.45 * max(st, 1) and not getattr(self, '_jingled', False):
            self._jingled = True
            self.stars_shown = max(self.stars_shown, st)
            self.g.audio.play('jingle3' if st == 3 else 'jingle2' if st else 'sad', 0.6)
            if st == 3:
                self.cat_happy = 3.0
        if st == 0 and self.rng.random() < dt * 6:
            self.puff(232 + self.rng.uniform(-4, 4), 134, 1, 'smoke', (70, 64, 64), 0.6, -10)
        if st == 3 and self.cat_hop is None and self.rng.random() < dt * 2.5:
            self.parts.append([self.cat[0] + self.rng.uniform(-3, 3), self.cat[1] - 18, 0.0, -10.0, 0.0, 1.4,
                               'heart', (236, 96, 120)])
        if st >= 2 and self.rng.random() < dt * 3:
            self.puff(232 + self.rng.uniform(-5, 5), 134, 1, 'steam', (250, 250, 252), 0.5, -8)

    def finish_scene(self):
        if self.done:
            return
        self.done = True
        g = self.g
        if g.net.role != 'guest':
            g.advance_time(30)
        K.finish_toast(g, self.result)
        g.end_cooking()

    # ------------------------------------------------------------ bot
    def auto(self, dt, rng, skill=0.75):
        """A stand-in player for --bot and tests. skill 1 is near perfect; lower skill adds human-like timing
        error and slower reactions."""
        err = 1.0 - skill
        st = self.state
        aim = getattr(self, '_aim', None)
        if st != getattr(self, '_aim_state', None):
            aim = None
            self._aim_state = st
        if st == 'intro':
            if self.st_t > 0.5:
                self._tap()
        elif st == 'chop':
            if self.slam <= 0 and self.ci < len(self.targets):
                if aim is None or aim[0] != self.ci:
                    aim = (self.ci, self.targets[self.ci] + rng.gauss(0, err * 3.0))
                if abs(self.knife_x() - aim[1]) < 0.7:
                    self._tap()
                    aim = None
        elif st == 'heat':
            self._react = getattr(self, '_react', 0.0) - dt
            if self._react <= 0:
                self._react = 0.06 + err * 0.3
                c, bw = self.band()
                if self.heat < c + rng.gauss(0, err * 0.12):
                    self.holds.add('auto')
                else:
                    self.holds.discard('auto')
        elif st in ('flip', 'oven'):
            if self.flip is None and (st == 'flip' or self.in_oven):
                key = (self.side, len(self.fin_q))
                if aim is None or aim[0] != key:
                    a, z = self.zone()
                    aim = (key, (a + z) / 2 + rng.gauss(0, err * 0.16))
                if self.brown >= aim[1]:
                    self._tap()
        elif st == 'season':
            if self.shaking <= 0 and self.st_t > 0.8:
                if aim is None or aim[0] != self.sprinkled:
                    aim = (self.sprinkled, rng.gauss(0, err * 7.0))
                if abs(self.shaker_off() - aim[1]) < 0.8:
                    self._tap()
        elif st == 'plate':
            if self.st_t > 2.6:
                self._tap()
        self._aim = aim

    def _tap(self):
        self.press('auto')
        self.release('auto')

    # ------------------------------------------------------------ drawing: the room
    def cam(self):
        x, y, w, _ = self.cam_f
        w2 = int(round(w * 2 / 16)) * 16
        h2 = w2 * 9 // 16
        cx, cy = (x + w / 2) * 2, (y + self.cam_f[3] / 2) * 2
        rx = int(round(_clamp(cx - w2 / 2, 0, RW * 2 - w2)))
        ry = int(round(_clamp(cy - h2 / 2, 0, RH * 2 - h2)))
        return pygame.Rect(rx, ry, w2, h2)

    def draw_world(self, frame):
        s = self.view
        s.blit(self.room, (0, 0))
        t = self.t
        self._draw_stove(s)
        self._draw_board(s)
        self._draw_table(s)
        # Biscuit
        cx, cy = self.cat
        face = 1 if self.px > cx else -1
        if self.cat_hop:
            face = 1
        draw_cat(s, cx, cy, t, face, self.cat_happy > 0, self.result is not None and self.result['stars'] == 0
                 and self.state == 'plate', coat=looks.cat_colors(self.g), pattern=looks.of(self.g)['coat'])
        self._draw_player(s)
        self._draw_parts(s)
        # light: dim the room by the time of day, then the lamp and the stove glow
        if self.dark > 0.05:
            k = 1 - 0.45 * self.dark
            v = (int(255 * k), int(255 * (k - 0.03 * self.dark)), int(255 * min(1, k + 0.05 * self.dark)))
            s.fill(v, special_flags=pygame.BLEND_MULT)
        flick = 0.85 + 0.05 * math.sin(t * 7.3) + 0.03 * math.sin(t * 13.1)
        art.add_glow(s, self.glow, (150, 86), (0.25 + 0.35 * self.dark) * flick)
        fire = self._fire_level()
        art.add_glow(s, self.fire_glow, (POT_X, 143), 0.25 + 0.5 * fire)
        # the lamp itself (drawn after the glow so it stays crisp)
        s.fill((60, 50, 44), (150, 56, 1, 20))
        pygame.draw.polygon(s, (60, 104, 84), [(144, 82), (156, 82), (153, 76), (147, 76)])
        s.fill((255, 236, 170), (148, 82, 4, 2))
        pygame.transform.scale(s, (RW * 2, RH * 2), frame)

    def _fire_level(self):
        if self.state in ('heat',):
            return self.heat
        if self.state in ('flip', 'season'):
            return 0.55
        if self.state == 'oven':
            return 0.8
        return 0.25

    def _draw_stove(self, s):
        t = self.t
        fire = self._fire_level()
        # oven window with the fire
        s.fill((34, 24, 22), (176, 140, 16, 6))
        for i in range(4):
            k = 0.5 + 0.5 * math.sin(t * (6 + i) + i * 1.7)
            hgt = int(1 + 5 * fire * (0.6 + 0.4 * k))
            col = lerp_c((230, 90, 40), (255, 220, 120), k * fire)
            s.fill(col, (178 + i * 4, 146 - hgt, 3, hgt))
        body = (196, 120, 70) if self.copper else (66, 66, 74)
        # oven door (it drops open when a pie goes in or out)
        o = self.oven_open
        top = 138 + int(9 * o)
        if o > 0.01:
            s.fill((40, 26, 22), (171, 138, 26, 11))
            s.fill((255, 150, 70), (173, 146, 22, 1))
            if self.finish_kind == 'oven' and (self.in_oven or (self.state == 'oven' and not self.fin_q)
                                               or (self.state == 'oven' and self.fin_q and self.st_t < 0.6)):
                self._draw_bake(s, 184, 145, 0.7)
        dh = 149 - top
        if dh > 0:
            pygame.draw.rect(s, darken(body, 0.3), (171, top, 26, dh), 1)
            if not o:
                s.fill((236, 220, 180), (182, 139, 4, 1))
        if o > 0.01:
            s.fill(darken(body, 0.3), (169, 149, 30, 2))
        # the pot or the pan on the cooktop
        if self.finish_kind == 'flip':
            self._draw_pan(s)
        else:
            self._draw_pot(s)
        # through the oven window: the dish baking
        if self.in_oven and o < 0.01:
            self._draw_bake(s, 184, 145, 0.5, window=True)

    def _draw_pot(self, s):
        c1, c2 = self.r['look'][1], self.r['look'][2]
        pot = (150, 156, 172)
        rattle = 0
        if self.state == 'heat':
            c, bw = self.band()
            if self.heat > c + bw + 0.08:
                rattle = int(math.sin(self.t * 40) > 0)
        y0 = 124 - rattle
        s.fill(darken(pot, 0.25), (POT_X - 9, y0 + 1, 18, 9))
        s.fill(pot, (POT_X - 9, y0 + 1, 17, 8))
        s.fill(lighten(pot, 0.3), (POT_X - 10, y0, 20, 2))
        s.fill(darken(pot, 0.35), (POT_X - 12, y0 + 2, 2, 2))
        s.fill(darken(pot, 0.35), (POT_X + 10, y0 + 2, 2, 2))
        s.fill(lighten(pot, 0.45), (POT_X - 7, y0 + 3, 1, 4))
        if self.state not in ('intro', 'chop', 'move_heat'):
            col = c1 if self.state != 'heat' or self.heat < 0.9 else darken(c1, 0.25)
            s.fill(col, (POT_X - 8, y0, 16, 1))
            s.set_at((POT_X - 4, y0), c2)
            s.set_at((POT_X + 3, y0), c2)
        # a ladle resting in it
        pygame.draw.line(s, (170, 170, 180), (POT_X + 5, y0 + 1), (POT_X + 10, y0 - 7))
        if self.state == 'season':
            off = self.shaker_off()
            sx = int(POT_X + off)
            jig = 1 if self.shaking > 0 and int(self.t * 30) % 2 else 0
            s.fill((150, 110, 80), (sx - 2, 113 + jig, 5, 6))
            s.fill((236, 226, 210), (sx - 2, 112 + jig, 5, 2))
            s.fill((240, 240, 236), (sx - 1, 119 + jig, 3, 1))
            # a faint guide under the shaker: where the pot's middle is
            s.fill((255, 240, 160), (POT_X, 118, 1, 1))

    def _draw_pan(self, s):
        c1, c2 = self.r['look'][1], self.r['look'][2]
        pan = (60, 60, 66)
        s.fill(pan, (POT_X - 12, 131, 24, 2))
        s.fill((90, 90, 98), (POT_X - 13, 130, 26, 1))
        s.fill((96, 70, 52), (POT_X - 24, 130, 11, 2))
        if self.state in ('intro', 'chop', 'move_heat'):
            return
        # the food: colour from raw to golden to burnt
        if self.state in ('flip', 'to_table', 'move_table', 'plate') and self.side <= 1:
            b = self.brown
        else:
            b = min(0.3, self.heat * 0.25) if self.state == 'heat' else 0.0
        food = self._browned(c1, b)
        fy, fx = 128.0, float(POT_X)
        ang = 0.0
        if self.flip is not None:
            k = self.flip / 0.55
            fy -= math.sin(k * math.pi) * 18
            ang = 180 * k
            food = self._browned(c1, self.side_brown[self.side] if k > 0.5 else b)
        if self.state in ('to_table', 'move_table', 'plate'):
            return
        tmp = pygame.Surface((18, 5), pygame.SRCALPHA)
        if self.kind == 'fritters':
            for i in range(3):
                pygame.draw.circle(tmp, food, (4 + i * 5, 3), 2)
        else:
            pygame.draw.ellipse(tmp, food, (1, 1, 16, 4))
            tmp.fill(lighten(food, 0.2), (4, 1, 8, 1))
            if self.kind == 'feast':
                tmp.set_at((12, 2), c2)
        if ang:
            hgt = max(1, int(round(abs(math.cos(math.radians(ang))) * 5)))
            tmp = pygame.transform.scale(tmp, (18, hgt))
        s.blit(tmp, tmp.get_rect(center=(int(fx), int(fy))))

    def _browned(self, raw, b):
        golden = (222, 164, 72)
        burnt = (70, 46, 34)
        if b < 0.65:
            return lerp_c(lighten(raw, 0.25), golden, b / 0.65)
        return lerp_c(golden, burnt, min(1.0, (b - 0.65) / 0.35))

    def _draw_bake(self, s, x, y, k, window=False):
        crust = self._browned(self.r['look'][1], self.brown)
        if window:
            s.fill(darken(crust, 0.35), (x - 6, y - 3, 12, 2))
            return
        pygame.draw.ellipse(s, crust, (x - 7, y - 4, 14, 4))
        s.fill(self.r['look'][2], (x - 3, y - 4, 6, 1))

    def _draw_board(self, s):
        x0, x1 = BOARD
        s.fill((150, 104, 66), (x0, TOP - 2, x1 - x0, 2))
        s.fill((206, 160, 110), (x0, TOP - 3, x1 - x0, 1))
        s.fill((150, 104, 66), (x1, TOP - 3, 2, 1))
        # the recipe book, open
        s.fill((120, 60, 50), (141, TOP - 2, 15, 2))
        s.fill((246, 238, 220), (142, TOP - 4, 6, 2))
        s.fill((236, 226, 206), (149, TOP - 4, 6, 2))
        s.fill((150, 140, 130), (143, TOP - 4, 4, 1))
        # a little basket of the other ingredients
        s.fill((170, 120, 70), (133, TOP - 4, 7, 4))
        for i, spec in enumerate(self.side_items):
            if spec and self.state in ('intro', 'chop'):
                s.fill(((150, 170, 190), (190, 160, 110), (140, 170, 130))[i % 3], (134 + i * 2, TOP - 6, 2, 2))
        s.fill((140, 96, 56), (133, TOP - 3, 7, 1))
        if self.state not in ('intro', 'chop') and not (self.state == 'move_heat' and self.st_t < 0.2):
            return
        # the fish, in pieces where it has been cut
        img = self.fish_img
        fw, fh = img.get_size()
        y = TOP - 3 - fh
        cuts = sorted(self.cuts)
        edges = [self.fish_x0] + [int(round(c)) for c in cuts] + [self.fish_x0 + fw]
        spread = min(1.0, (self.st_t if self.state == 'chop' else 1.0) * 3)
        for i in range(len(edges) - 1):
            a, b = edges[i], edges[i + 1]
            if b <= a:
                continue
            piece = img.subsurface((a - self.fish_x0, 0, b - a, fh))
            off = int(round((i - (len(edges) - 2) / 2) * 1.0 * spread)) if cuts else 0
            s.blit(piece, (a + off, y))
        if self.state != 'chop':
            return
        # marks to cut
        for i, tx in enumerate(self.targets):
            if i < self.ci:
                continue
            col = (255, 230, 120) if i == self.ci else (230, 220, 200)
            for yy in range(y - 2, y + fh + 1, 2):
                s.set_at((int(round(tx)), yy), col)
        # the knife
        kx = self.knife_x()
        if self.ci < len(self.targets) or self.slam > 0:
            k = self.slam / 0.2 if self.slam > 0 else 0.0
            lift = int(10 * (1 - math.sin(k * math.pi))) if self.slam > 0 else 10
            ky = TOP - 3 - fh - lift
            kxi = int(round(kx if self.slam <= 0 else self.cuts[-1]))
            s.fill((210, 214, 224), (kxi - 1, ky, 2, fh + 3))
            s.fill((246, 248, 252), (kxi - 1, ky, 1, fh + 3))
            s.fill((96, 64, 46), (kxi - 1, ky - 5, 3, 5))
            s.fill((60, 40, 30), (kxi - 1, ky - 3, 3, 1))

    def _draw_table(self, s):
        if self.state not in ('plate',):
            return
        st = self.result['stars'] if self.result else 2
        ic = self._dish_small(st == 0)
        s.blit(ic, ic.get_rect(midbottom=(232, 139)))

    def _dish_small(self, burnt):
        ic = K.dish_icon(self.rid, 1)
        ic = pygame.transform.scale(ic, (20, 16))
        if burnt:
            ic = ic.copy()
            ic.fill((70, 56, 52, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ic.fill((30, 24, 24, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return ic

    def _draw_player(self, s):
        g = self.g
        season = g.env.season
        lk = looks.of(g)
        shirt = looks.shirt(lk, season)
        x = int(round(self.px))
        face = self.pface
        fy = FLOOR
        if self.state == 'season':
            k = _clamp((self.st_t - 0.35) / 0.25, 0, 1) if self.ptarget is None else 0.0
            fy = FLOOR - int(round(5 * k + math.sin(k * math.pi) * 4))
            s.fill((150, 100, 64), (STOOL_X - 6, FLOOR - 5, 12, 2))
            s.fill((120, 80, 52), (STOOL_X - 5, FLOOR - 3, 2, 3))
            s.fill((120, 80, 52), (STOOL_X + 3, FLOOR - 3, 2, 3))
        town.walker(s, x, fy, face, self.pstep, shirt, looks.hair(lk), g.hat, season, look=lk)
        skin = looks.skin(lk)
        arm = darken(shirt, 0.2)
        sh = (x + face, fy - 13)
        hand = None
        st = self.state
        if self.carry == 'dish' or self.carry == 'bowl':
            hand = (x + 5 * face, FLOOR - 15)
            if self.carry == 'dish':
                ic = self._dish_small(self.result is not None and self.result['stars'] == 0)
                ic = pygame.transform.scale(ic, (14, 11))
                s.blit(ic, ic.get_rect(midbottom=(hand[0] + 2 * face, hand[1] + 2)))
            else:
                s.fill((200, 220, 236), (hand[0] - 3, hand[1] - 2, 7, 3))
                s.fill((236, 230, 220), (hand[0] - 2, hand[1] - 3, 5, 1))
        elif st == 'chop' and face > 0:
            if self.slam > 0 and self.cuts:
                kx = self.cuts[-1]
                k = self.slam / 0.2
                ky = TOP - 3 - self.fish_img.get_height() - int(10 * (1 - math.sin(k * math.pi))) - 4
            else:
                kx = self.knife_x()
                ky = TOP - 3 - self.fish_img.get_height() - 14
            hand = (int(kx), int(ky))
        elif st == 'heat':
            hand = (166, 138 + (1 if self.holding() else 0))
        elif st == 'flip':
            lift = int(math.sin((self.flip or 0) / 0.55 * math.pi) * 3) if self.flip is not None else 0
            hand = (POT_X - 23, 131 - lift)
        elif st == 'season':
            hand = (int(POT_X + self.shaker_off()) - 2, 114 + (1 if self.shaking > 0 and int(self.t * 30) % 2 else 0))
        elif st == 'oven' and self.oven_open > 0.2:
            hand = (174, 146)
        if hand:
            dx, dy = hand[0] - sh[0], hand[1] - sh[1]
            if math.hypot(dx, dy) > 14:          # a long reach bends at the elbow
                el = (sh[0] + dx * 0.45 - 3 * (dy < -8), sh[1] + dy * 0.45 + (4 if dy > -8 else 0))
                pygame.draw.lines(s, arm, False, [sh, el, hand], 2)
            else:
                pygame.draw.line(s, arm, sh, hand, 2)
            s.fill(skin, (hand[0] - 1, hand[1] - 1, 2, 2))

    def _draw_parts(self, s):
        for p in self.parts:
            x, y, kind, col = int(p[0]), int(p[1]), p[6], p[7]
            k = p[4] / p[5]
            if kind == 'steam':
                if k < 0.85:
                    c = lerp_c(col, (176, 134, 104), k)
                    if k < 0.4:
                        s.set_at((x, y), c)
                    else:
                        s.fill(c, (x, y, 2, 2))
            elif kind == 'smoke':
                c = lerp_c(col, (150, 124, 110), k)
                r = 1 + int(k * 2.2)
                pygame.draw.circle(s, c, (x, y), r)
            elif kind == 'bubble':
                if y > 118:
                    s.set_at((x, y), col)
            elif kind == 'heart':
                heart(s, x, y)
            else:
                s.set_at((x, y), col)

    # ------------------------------------------------------------ drawing: on screen
    def r2s(self, x, y):
        return self.g.w2s(x * 2, y * 2)

    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        SW, SH = s.get_size()
        # floating words over the action
        for text, x, y, ft, col in self.floats:
            p = self.r2s(x, y)
            ui.blit_text(s, text, p, 'h3', col, 'center', outline=(40, 26, 24), alpha=int(255 * min(1, (1.1 - ft) * 3)))
        # letterbox bars
        bh = int(round(self.bars * 64 / 2)) * 2
        if bh > 1:
            s.fill((10, 8, 12), (0, 0, SW, bh))
            s.fill((10, 8, 12), (0, SH - bh, SW, bh))
        st = self.state
        if st == 'intro':
            self._ui_intro(s, SW, SH)
        elif st == 'chop':
            self._banner(s, SW, 0, self.g.hint('Press Space or click as the knife passes over each mark',
                                               ['Press', ('pad', 'A'), 'as the knife passes over each mark']))
            n = len(self.targets)
            ui.blit_text(s, 'Cuts %d / %d' % (self.ci, n), (SW // 2, 112), 'smallb', (255, 250, 230), 'center',
                         outline=(40, 26, 24))
            self._timer_ring(s, SW // 2 + 120, 112, 1 - self.cut_t / 4.0)
        elif st == 'heat':
            self._banner(s, SW, 1, self.g.hint('Hold Space or the mouse to stoke the fire. Keep the needle in the green',
                                               ['Hold', ('pad', 'A'), 'to stoke the fire. Keep the needle in the green']))
            self._thermo(s, SW, SH)
        elif st == 'flip':
            self._banner(s, SW, 2, 'Flip it when the bar is in the gold. Two sides!')
            self._bar(s, SW, 'Side %d of 2' % min(2, self.side + 1))
        elif st == 'oven':
            self._banner(s, SW, 2, 'Take it out when the crust is golden')
            if self.in_oven:
                self._bar(s, SW, 'Crust')
        elif st == 'season':
            self._banner(s, SW, 2, 'Shake when the shaker is right over the pot. Three shakes')
            ui.blit_text(s, 'Shakes %d / 3' % self.sprinkled, (SW // 2, 112), 'smallb', (255, 250, 230), 'center',
                         outline=(40, 26, 24))
        elif st == 'plate' and self.result is not None:
            self._ui_result(s, SW, SH)
        if self.esc_hint > 0 and st not in ('plate',):
            ui.blit_text(s, "The stove is lit - finish cooking first!", (SW // 2, SH - 92), 'small',
                         (255, 230, 200), 'center', outline=(40, 26, 24))

    def _banner(self, s, SW, idx, tip):
        ui = self.g.ui
        names = self.phase_names()
        w = 132
        x0 = SW // 2 - (w * 3 + 16) // 2
        for i, n in enumerate(names):
            r = pygame.Rect(x0 + i * (w + 8), 18, w, 34)
            on = i == idx
            done = i < idx
            fill = (250, 226, 150) if on else (236, 226, 206) if not done else (200, 226, 190)
            pygame.draw.rect(s, (60, 40, 32), r.inflate(4, 4), border_radius=10)
            pygame.draw.rect(s, fill, r, border_radius=8)
            ui.blit_text(s, '%d  %s' % (i + 1, n), r.center, 'smallb', U.INK, 'center')
        if isinstance(tip, list):              # a controller hint with button pictures in it
            w = ui.rich(s, tip, (0, 0), measure=True)
            ui.rich(s, tip, (SW // 2 - w // 2, 70), (255, 250, 236), outline=(40, 26, 24))
        else:
            ui.blit_text(s, tip, (SW // 2, 70), 'small', (255, 250, 236), 'center', outline=(40, 26, 24),
                         maxw=SW - 80)
        self._difficulty(s, SW - 24 - 4 * 22, 30, 'topright')

    def _difficulty(self, s, x, y, anchor):
        ui = self.g.ui
        ui.blit_text(s, 'Difficulty', (x - 12, y), 'tiny', (255, 236, 180), 'midright', outline=(40, 26, 24))
        for i in range(4):
            on = i < self.tier
            star(s, x + i * 22 + 4, y, 9, (250, 200, 80) if on else (120, 100, 90), (60, 40, 30))

    def _timer_ring(self, s, x, y, k):
        k = _clamp(k, 0, 1)
        col = (120, 200, 120) if k > 0.4 else (240, 170, 80) if k > 0.2 else (230, 90, 80)
        pygame.draw.circle(s, (40, 30, 28), (x, y), 12)
        if k > 0:
            pts = [(x, y)]
            for i in range(int(k * 24) + 1):
                a = -math.pi / 2 + (i / 24) * 2 * math.pi
                pts.append((x + 10 * math.cos(a), y + 10 * math.sin(a)))
            if len(pts) > 2:
                pygame.draw.polygon(s, col, pts)

    def _thermo(self, s, SW, SH):
        ui = self.g.ui
        x, y, w, h = SW - 120, 150, 40, SH - 330
        c, bw = self.band()
        pygame.draw.rect(s, (50, 36, 30), (x - 6, y - 6, w + 12, h + 12), border_radius=14)
        pygame.draw.rect(s, (240, 232, 214), (x, y, w, h), border_radius=10)
        # a warm-to-hot gradient strip
        for i in range(0, h, 4):
            k = 1 - i / h
            s.fill(lerp_c((120, 170, 230), (236, 90, 60), k), (x + 4, y + i, 6, 4))
        lo, hi = _clamp(c - bw, 0, 1), _clamp(c + bw, 0, 1)
        by0, by1 = y + int((1 - hi) * h), y + int((1 - lo) * h)
        pygame.draw.rect(s, (120, 200, 110), (x + 12, by0, w - 16, max(2, by1 - by0)), border_radius=4)
        pygame.draw.rect(s, (70, 150, 70), (x + 12, by0, w - 16, max(2, by1 - by0)), 2, border_radius=4)
        ny = y + int((1 - self.heat) * h)
        inside = abs(self.heat - c) <= bw
        nc = (60, 40, 32) if inside else (220, 70, 60)
        pygame.draw.polygon(s, nc, [(x - 14, ny - 8), (x - 14, ny + 8), (x - 2, ny)])
        s.fill(nc, (x, ny - 2, w, 4))
        ui.blit_text(s, 'Heat', (x + w // 2, y + h + 14), 'smallb', (255, 250, 236), 'midtop', outline=(40, 26, 24))
        # the time left
        k = 1 - self.heat_time / self.heat_dur
        bx, bw2 = SW // 2 - 160, 320
        pygame.draw.rect(s, (40, 30, 28), (bx - 4, 96, bw2 + 8, 16), border_radius=8)
        pygame.draw.rect(s, (250, 226, 150), (bx, 100, int(bw2 * _clamp(k, 0, 1)), 8), border_radius=4)
        if self.heat > c + bw + 0.08:
            ui.blit_text(s, 'Too hot!', (x + w // 2, y - 30), 'h3', (255, 140, 110), 'center', outline=(40, 26, 24))
        elif self.heat < c - bw - 0.08 and self.heat_time > 0.8:
            ui.blit_text(s, 'Too cool', (x + w // 2, y - 30), 'h3', (170, 210, 255), 'center', outline=(40, 26, 24))

    def _bar(self, s, SW, label):
        ui = self.g.ui
        w = 420
        x, y = SW // 2 - w // 2, 110
        a, z = self.zone()
        pygame.draw.rect(s, (50, 36, 30), (x - 6, y - 6, w + 12, 36), border_radius=12)
        for i in range(0, w, 4):
            s.fill(self._browned(self.r['look'][1], i / w), (x + i, y, 4, 24))
        pygame.draw.rect(s, (255, 236, 140), (x + int(a * w), y - 2, int((z - a) * w), 28), 3, border_radius=4)
        mx = x + int(_clamp(self.brown, 0, 1) * w)
        pygame.draw.polygon(s, (255, 255, 255), [(mx - 8, y - 12), (mx + 8, y - 12), (mx, y - 2)])
        s.fill((255, 255, 255), (mx - 1, y, 3, 24))
        ui.blit_text(s, label, (SW // 2, y + 40), 'smallb', (255, 250, 236), 'midtop', outline=(40, 26, 24))

    def _ui_intro(self, s, SW, SH):
        ui = self.g.ui
        t = self.st_t
        cap = None
        if self.first:
            i = int((t - 0.6) / 2.8)
            if t > 0.6 and 0 <= i < len(FIRST_LINES):
                cap = FIRST_LINES[i]
                lt = (t - 0.6) - i * 2.8
                a = int(255 * _clamp(min(lt / 0.35, (2.8 - lt) / 0.35), 0, 1))
                ui.blit_text(s, cap, (SW // 2, SH - 32), 'body', (250, 244, 230), 'center', alpha=a, maxw=SW - 120)
        # the title card for this dish
        t0 = self.intro_len - 2.6
        if t > t0:
            k = _clamp((t - t0) / 0.4, 0, 1)
            card = pygame.Rect(0, 0, 420, 150)
            card.center = (SW // 2, 96 + 150 // 2 + 20 + int((1 - k) * -30))
            if k > 0.05:
                ui.tile(s, card, (252, 244, 226), (196, 160, 120))
                ic = K.dish_icon(self.rid, 2)
                s.blit(ic, ic.get_rect(center=(card.x + 70, card.centery)))
                ui.blit_text(s, self.r['name'], (card.x + 130, card.y + 22), 'h2', U.INK, maxw=card.w - 150)
                ui.blit_text(s, 'Difficulty', (card.x + 130, card.y + 66), 'smallb', (170, 110, 70))
                for i in range(4):
                    star(s, card.x + 260 + i * 24, card.y + 78, 10,
                         (250, 200, 80) if i < self.tier else (220, 210, 196), (150, 100, 50))
                ui.blit_text(s, '  >  '.join(self.phase_names()), (card.x + 130, card.y + 100), 'small', U.SOFT)
        parts = [('key', 'Space'), 'skip']
        w = ui.rich(s, parts, (0, 0), measure=True)
        ui.rich(s, parts, (SW - 24 - w, SH - 32), (190, 180, 170))
        if t < 0.6 and not self.first:
            pass

    def _ui_result(self, s, SW, SH):
        g = self.g
        ui = g.ui
        res = self.result
        st = res['stars']
        card = pygame.Rect(0, 0, 600, 200)
        card.midtop = (SW // 2, 72)
        ui.tile(s, card, (252, 244, 226), (196, 160, 120))
        ic = K.dish_icon(self.rid, 2)
        if st == 0:
            ic = ic.copy()
            ic.fill((80, 64, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(ic, ic.get_rect(center=(card.x + 70, card.y + 70)))
        ui.blit_text(s, self.r['name'], (card.x + 134, card.y + 18), 'h3', U.INK, maxw=card.w - 300)
        ui.blit_text(s, WORDS[st], (card.x + 134, card.y + 52), 'smallb', (170, 110, 70) if st else (170, 80, 70),
                     maxw=card.w - 300)
        # stars, stamped in one at a time
        for i in range(3):
            cx = card.right - 150 + i * 50
            cy = card.y + 46
            on = i < self.stars_shown
            pop = 1.0
            if on and i == self.stars_shown - 1:
                pop = 1 + max(0.0, 0.4 - (self.st_t - 0.5 - 0.45 * i)) * 1.2
            star(s, cx, cy, 20 * pop, (250, 210, 80) if on else (220, 210, 196), (150, 100, 50) if on else
                 (190, 176, 160))
        # how each step went
        names = self.phase_names()
        for i, key in enumerate(('chop', 'heat', 'finish')):
            q = self.scores.get(key, 0.0)
            x = card.x + 134 + i * 130
            y = card.y + 92
            ui.blit_text(s, names[i], (x, y), 'tiny', U.SOFT)
            pygame.draw.rect(s, (226, 214, 196), (x, y + 24, 110, 10), border_radius=4)
            pygame.draw.rect(s, (120, 190, 110) if q >= 0.6 else (230, 170, 80) if q >= 0.3 else (220, 100, 80),
                             (x, y + 24, max(4, int(110 * q)), 10), border_radius=4)
        msg = res['text']
        lines = ui.wrap(msg, 'tiny', card.w - 200)
        for i, ln in enumerate(lines[:2]):
            ui.blit_text(s, ln, (card.x + 24, card.bottom - 52 + i * 22), 'tiny',
                         (90, 130, 80) if st else (170, 80, 70))
        if self.st_t > 0.6:
            ui.button(s, (card.right - 150, card.bottom - 44, 130, 32), 'Continue', self.finish_scene, 'primary',
                      font='small')


def star(s, cx, cy, r, fill, edge):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(s, fill, pts)
    pygame.draw.polygon(s, edge, pts, 2)
