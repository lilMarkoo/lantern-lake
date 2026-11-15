"""Wildlife at the lake, and the camera.

Animals come and go by spot, season, time of day and weather: herons fishing in the shallows, a kingfisher
diving from the dock pole, otters cracking clams on their bellies, deer drinking on the far shore, an owl on the
pole at night, loons calling at dusk. In photo mode (P), Space or a click takes a picture. A moving animal makes a
one-star photo, a settled one two, and catching its special moment (the heron's strike, the loon's call) three.
The best photo of each animal goes on the Nature page of the journal.
"""
import math
import os
import random

import pygame

import ui as U
from art import W, H, HORIZON, darken, lighten

NIGHT = ((1200, 1440), (0, 300))
DAWN_DUSK = ((300, 600), (1020, 1200))
# spots, seasons (None: all), hours (minute ranges), weather it avoids or needs, weight
SPECIES = [
    dict(id='mallard', name='Mallard Family', ambient=True,
         where='Anywhere on the lake by day, spring to autumn.',
         desc='A mother and her ducklings, out for a paddle. They never hurry.'),
    dict(id='frog', name='Green Frog', ambient=True,
         where='The lily pads of Lily Cove, spring to autumn.',
         desc='Sits very still on a lily pad, then puffs out its throat and sings.'),
    dict(id='heron', name='Grey Heron', spots=('dock', 'cove', 'creek'), seasons=(0, 1, 2), hours=DAWN_DUSK,
         avoid=('snow',), w=1.0, where='Shallow water at dawn and dusk, spring to autumn.',
         desc='Stands like a statue for ages, then strikes faster than you can blink.'),
    dict(id='kingfisher', name='Kingfisher', spots=('dock', 'cove', 'creek'), seasons=(0, 1), hours=((420, 1080),),
         avoid=('rain', 'snow', 'fog'), w=0.9, where='Perched over the water on fine spring and summer days.',
         desc='A flash of blue. Hovers over the water, then dives for a minnow.'),
    dict(id='dragonfly', name='Azure Dragonfly', spots=('dock', 'cove'), seasons=(1,), hours=((600, 1080),),
         need=('clear', 'cloudy'), w=1.0, where='Over the dock on warm summer days.',
         desc='Darts about over the water, and sometimes rests on the dock pole.'),
    dict(id='turtle', name='Painted Turtle', spots=('cove', 'creek'), seasons=(0, 1), hours=((600, 1000),),
         need=('clear', 'cloudy'), w=0.9, where='Basking in the sun at Lily Cove or Willow Creek.',
         desc='Climbs out to warm its shell, and stretches its neck when it feels sunny.'),
    dict(id='otter', name='River Otter', spots=('dock', 'cove', 'deep', 'creek'), seasons=(0, 2, 3),
         hours=DAWN_DUSK, w=0.8, where='Early or late in the day, any season but summer.',
         desc='Floats on its back and cracks clams on its tummy. Very pleased with itself.'),
    dict(id='deer', name='White-tailed Deer', spots=('dock', 'cove', 'deep'), seasons=(0, 2), hours=DAWN_DUSK,
         avoid=('rain',), w=0.9, where='On the far shore at dawn or dusk, spring and autumn.',
         desc='Comes down to the water to drink, and looks up when it hears you.'),
    dict(id='fox', name='Red Fox', spots=('dock', 'creek', 'cove'), seasons=(3,), hours=((360, 660), (960, 1140)),
         avoid=('rain',), w=0.9, where='Along the far shore on winter mornings and afternoons.',
         desc='Listens to the snow, then leaps head first after a mouse underneath.'),
    dict(id='owl', name='Barred Owl', spots=('dock', 'cove', 'creek'), seasons=(0, 2, 3), hours=NIGHT,
         avoid=('rain',), w=0.9, where='On a post at night, except in summer.',
         desc='Silent in flight. Turns its head right round to hoot at you.'),
    dict(id='loon', name='Common Loon', spots=('dock', 'deep'), seasons=(0, 1), hours=((1140, 1380), (240, 420)),
         w=0.9, where='Open water at dusk or first light, spring and summer.',
         desc='Dives for ages and pops up somewhere else. Its call carries across the whole lake.'),
    dict(id='beaver', name='Beaver', spots=('cove', 'creek'), seasons=(0, 2), hours=((1080, 1320),), w=0.8,
         where='Lily Cove or Willow Creek in the evening, spring and autumn.',
         desc='Busy with a branch. Slaps its tail on the water when it has had enough of you.'),
    dict(id='swans', name='Mute Swans', spots=('deep', 'cove'), seasons=(0, 2, 3), hours=((480, 1080),), w=0.8,
         where='Gliding about the Deep or Lily Cove by day.',
         desc='A pair, always together. When they face each other, their necks make a heart.'),
    dict(id='bats', name='Little Brown Bats', spots=('dock', 'cove', 'creek'), seasons=(1, 2),
         hours=((1170, 1320),), need=('clear', 'cloudy'), w=1.0, where='Summer and autumn dusk, on dry evenings.',
         desc='Flutter after midges at dusk, and dip down to sip from the lake.'),
    dict(id='moose', name='Moose', spots=('creek',), seasons=(2, 3), hours=((300, 600),),
         need=('fog', 'snow', 'cloudy'), w=0.7, where='Willow Creek on grey autumn or winter mornings.',
         desc='Wades in up to its knees and comes up with a mouthful of water weeds.'),
    dict(id='stag', name='The White Stag', spots=('dock', 'deep'), seasons=(3,), hours=((300, 480),),
         need=('fog', 'snow'), w=0.35, where='Said to walk the far shore on snowy or foggy winter dawns.',
         desc='Nobody in Fernwick quite believes in it. It bows its head, then it is gone.'),
]
SPECIES_BY_ID = {s['id']: s for s in SPECIES}
SPAWNED = [s for s in SPECIES if not s.get('ambient')]
POSE_STARS = {'move': 1, 'still': 2, 'special': 3}
NEW_REWARD = 25          # coins for a new animal on the Nature page, and again for its first 3-star photo

# where things happen, per spot (world pixels)
PERCH = {'dock': (258, 243), 'cove': (84, 227), 'creek': (420, 296)}
WATER_BELOW = {'dock': 262, 'cove': 252, 'creek': 304}
HERON_AT = {'dock': (300, 318), 'cove': (290, 322), 'creek': (162, 322)}
SHORE_X = {'dock': (300, 600), 'cove': (330, 610), 'deep': (220, 400), 'creek': (380, 620)}
LANES = {'dock': (226, 262), 'cove': (232, 266), 'deep': (224, 276), 'creek': (240, 290)}

WHITE = (244, 244, 240)


def persp(y):
    return 0.5 + (y - HORIZON) / 170


def in_hours(minute, hours):
    return any(a <= minute < b for a, b in hours)


def eligible(sp, g):
    if g.spot not in sp['spots']:
        return False
    if sp['seasons'] is not None and g.env.season not in sp['seasons']:
        return False
    if not in_hours(g.minute, sp['hours']):
        return False
    if g.weather in sp.get('avoid', ()):
        return False
    if sp.get('need') and g.weather not in sp['need']:
        return False
    if sp['id'] == 'heron' and g.spot == 'dock' and g.festival_live():
        return False
    return True


# ---------------------------------------------------------------- one visiting animal
class Critter:
    SIZE = {'heron': (30, 30, 15, 28), 'kingfisher': (16, 16, 8, 12), 'dragonfly': (12, 8, 6, 4),
            'turtle': (16, 10, 8, 8), 'otter': (20, 10, 10, 7), 'deer': (14, 12, 7, 11), 'fox': (16, 12, 8, 10),
            'owl': (14, 16, 7, 15), 'loon': (18, 12, 9, 9), 'beaver': (22, 12, 11, 8), 'swans': (34, 16, 8, 12),
            'bats': (8, 6, 4, 3), 'moose': (26, 22, 13, 21), 'stag': (16, 18, 8, 17)}

    def __init__(self, sp, g, rng):
        self.sp = sp
        self.id = sp['id']
        self.spot = g.spot
        self.rng = rng
        self.t = 0.0
        self.st = 0.0
        self.state = 'in'
        self.face = -1
        self.pose = 'move'
        self.gone = False
        self.hidden = False
        self.alpha = 255
        self.n = 0
        self.life = rng.uniform(40, 60)
        self.eyes = []
        self.sound = None
        getattr(self, 'init_' + self.id)(g)

    # helpers
    def go(self, state, pose=None):
        self.state = state
        self.st = 0.0
        if pose:
            self.pose = pose

    def toward(self, tx, ty, speed, dt):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d <= speed * dt or d < 0.5:
            self.x, self.y = tx, ty
            return True
        self.x += dx / d * speed * dt
        self.y += dy / d * speed * dt
        if abs(dx) > 1:
            self.face = 1 if dx > 0 else -1
        return False

    def enter_side(self, y):
        side = self.rng.choice((-1, 1))
        self.x = -24 if side < 0 else W + 24
        self.y = y
        self.face = -side

    def leave(self, speed, dt, dy=0.0):
        self.x += self.face * speed * dt
        self.y += dy * dt
        if self.x < -40 or self.x > W + 40 or self.y < -30:
            self.gone = True

    def update(self, dt, g):
        self.t += dt
        self.st += dt
        self.life -= dt
        getattr(self, 'upd_' + self.id)(dt, g)

    def rect(self):
        w, h, ax, ay = self.SIZE[self.id]
        if self.id == 'bats':
            xs = [b[0] for b in self.bats]
            ys = [b[1] for b in self.bats]
            return pygame.Rect(min(xs) - 4, min(ys) - 3, max(xs) - min(xs) + 8, max(ys) - min(ys) + 6)
        if self.id == 'swans':
            return pygame.Rect(int(self.x) - 8, int(self.y) - 12, 32, 13)
        return pygame.Rect(int(self.x) - ax, int(self.y) - ay, w, h)

    # ------------------------------------------------ heron
    def init_heron(self, g):
        self.tx, self.ty = HERON_AT[g.spot]
        self.enter_side(100)

    def upd_heron(self, dt, g):
        s = self.state
        if s == 'in':
            if self.toward(self.tx, self.ty, 46, dt):
                self.go('stand', 'still')
                self.wait = self.rng.uniform(3, 5)
                g.world.ripple(self.x, self.y + 1, 6, 8, 120)
        elif s == 'stand':
            if self.st > self.wait:
                self.n += 1
                self.go('strike', 'move')
        elif s == 'strike':
            if self.st > 0.35 and self.pose == 'move' and self.st < 1.7:
                self.pose = 'special'
                g.world.ripple(self.x + 12 * self.face, self.y + 1, 7, 10, 160)
                g.world.splash(self.x + 12 * self.face, self.y, 5, 0.4)
                self.sound = ('splash_small', 0.35)
            if self.st > 1.9:
                if self.life <= 0 or self.n >= 3:
                    self.face = self.rng.choice((-1, 1))
                    self.go('out', 'move')
                else:
                    self.go('stand', 'still')
                    self.wait = self.rng.uniform(4, 7)
        else:
            self.leave(48, dt, -26)

    def draw_heron(self, s, t):
        grey, dgrey, wh, blk = (150, 156, 166), (108, 114, 126), (226, 228, 232), (40, 40, 46)
        beak, leg = (226, 190, 80), (86, 80, 74)
        if self.state in ('in', 'out'):
            f = math.sin(t * 7)
            pygame.draw.line(s, leg, (19, 14), (28, 15))
            pygame.draw.ellipse(s, grey, (8, 11, 13, 5))
            s.fill(wh, (5, 10, 4, 3))
            s.fill(blk, (7, 10, 3, 1))
            s.fill(beak, (1, 11, 4, 1))
            tip = int(10 * f)
            pygame.draw.polygon(s, dgrey, [(10, 13), (19, 13), (17, 13 - tip), (11, 13 - tip)])
            pygame.draw.line(s, darken(dgrey, 0.3), (11, 13 - tip), (17, 13 - tip))
            return
        s.fill(leg, (15, 20, 1, 8))
        s.fill(leg, (17, 20, 1, 8))
        pygame.draw.ellipse(s, grey, (11, 13, 11, 8))
        s.fill(dgrey, (13, 14, 8, 2))
        s.fill(dgrey, (21, 17, 2, 3))
        if self.state == 'strike' and 0.3 < self.st < 1.75:
            pygame.draw.line(s, wh, (12, 14), (6, 22), 2)
            s.fill(wh, (3, 22, 4, 2))
            s.fill(blk, (5, 21, 3, 1))
            if self.st < 1.0:
                s.fill(beak, (0, 24, 3, 1))
            else:
                s.fill(beak, (0, 23, 4, 1))
                s.fill((200, 214, 226), (0, 24, 3, 1))
            return
        s.fill(wh, (11, 16, 3, 3))
        for x, y in ((12, 12), (11, 11), (11, 10), (12, 9), (12, 8), (11, 7)):
            s.fill(wh, (x, y, 2, 1))
        s.fill(wh, (9, 5, 4, 3))
        s.set_at((10, 6), blk)
        s.fill(blk, (12, 5, 4, 1))
        s.set_at((15, 6), blk)
        s.fill(beak, (5, 6, 4, 1))

    # ------------------------------------------------ kingfisher
    def init_kingfisher(self, g):
        self.px, self.py = PERCH[g.spot]
        self.enter_side(self.py - 30)
        self.water = WATER_BELOW[g.spot]

    def upd_kingfisher(self, dt, g):
        s = self.state
        if s == 'in':
            if self.toward(self.px, self.py, 90, dt):
                self.go('perch', 'still')
                self.wait = self.rng.uniform(3, 5)
        elif s == 'perch':
            if self.st > self.wait:
                if self.life <= 0 or self.n >= 2:
                    self.face = self.rng.choice((-1, 1))
                    self.go('out', 'move')
                else:
                    self.hx = max(20, min(W - 20, self.px + self.rng.choice((-1, 1)) * self.rng.uniform(24, 46)))
                    self.go('hover', 'move')
        elif s == 'hover':
            self.toward(self.hx, self.water - 14, 60, dt)
            if self.st > 2.0:
                self.go('dive', 'special')
        elif s == 'dive':
            self.y = min(self.water, self.y + 70 * dt)
            if self.y >= self.water and self.st < 5:
                g.world.splash(self.x, self.water, 6, 0.5)
                g.world.ripple(self.x, self.water + 1, 6, 9, 150)
                self.sound = ('splash_small', 0.3)
                self.n += 1
                self.go('up', 'special')
        elif s == 'up':
            if self.toward(self.px, self.py, 50, dt):
                self.go('perch', 'still')
                self.wait = self.rng.uniform(3, 5)
            elif self.st > 1.0:
                self.pose = 'move'
        else:
            self.leave(90, dt, -10)

    def draw_kingfisher(self, s, t):
        blue, bl2, ora, wh, dk = (40, 112, 196), (90, 170, 230), (232, 124, 52), (240, 240, 236), (36, 34, 40)
        if self.state == 'dive':
            s.fill(blue, (7, 2, 3, 7))
            s.fill(ora, (8, 5, 2, 3))
            s.fill(dk, (8, 9, 1, 3))
            return
        if self.state in ('in', 'out', 'hover') or (self.state == 'up' and self.st < 1.6):
            s.fill(blue, (4, 6, 8, 3))
            s.fill(blue, (3, 4, 4, 3))
            s.fill(ora, (5, 8, 5, 1))
            s.fill(dk, (0, 5, 3, 1))
            if int(t * 22) % 2:
                s.fill(bl2, (6, 2, 4, 4))
            else:
                s.fill(bl2, (6, 9, 4, 3))
            if self.state == 'up':
                s.fill((200, 214, 226), (0, 6, 3, 1))
            return
        bob = 1 if int(t * 1.3) % 5 == 0 else 0
        s.fill(blue, (6, 6, 5, 4))
        s.fill(blue, (4, 3 + bob, 5, 4))
        s.set_at((8, 2 + bob), blue)
        s.fill(ora, (6, 9, 4, 2))
        s.fill(wh, (4, 7, 2, 1))
        s.fill(dk, (1, 5 + bob, 3, 1))
        s.fill(darken(blue, 0.2), (10, 9, 3, 2))
        s.set_at((5, 4 + bob), dk)
        s.fill(dk, (7, 11, 2, 1))

    # ------------------------------------------------ dragonfly
    def init_dragonfly(self, g):
        self.enter_side(250)
        self.px, self.py = PERCH[g.spot] if g.spot in PERCH else (258, 243)
        self.py -= 1
        self.pick()

    def pick(self):
        self.tx = self.rng.uniform(170, 420)
        self.ty = self.rng.uniform(236, 292)

    def upd_dragonfly(self, dt, g):
        s = self.state
        if s in ('in', 'dart'):
            if self.toward(self.tx, self.ty, 85, dt):
                self.n += 1
                if self.n % 4 == 0 and self.life > 0:
                    self.go('to_perch', 'move')
                else:
                    self.go('hover', 'still')
                    self.wait = self.rng.uniform(0.6, 1.6)
        elif s == 'hover':
            self.y += math.sin(self.t * 9) * 3 * dt
            if self.st > self.wait:
                if self.life <= 0:
                    self.face = self.rng.choice((-1, 1))
                    self.go('out', 'move')
                else:
                    self.pick()
                    self.go('dart', 'move')
        elif s == 'to_perch':
            if self.toward(self.px, self.py, 70, dt):
                self.go('perch', 'special')
        elif s == 'perch':
            if self.st > 3.5:
                self.pick()
                self.go('dart', 'move')
        else:
            self.leave(90, dt)

    def draw_dragonfly(self, s, t):
        body, head = (60, 150, 230), (40, 110, 190)
        wing = (230, 240, 255, 150)
        s.fill(body, (2, 4, 8, 1))
        s.fill(head, (1, 3, 2, 2))
        s.set_at((1, 3), (120, 220, 140))
        if self.state == 'perch':
            s.fill(wing, (3, 3, 6, 1))
            s.fill(wing, (3, 5, 6, 1))
        elif int(t * 30) % 2:
            s.fill(wing, (4, 1, 2, 3))
            s.fill(wing, (7, 1, 2, 3))
        else:
            s.fill(wing, (4, 5, 2, 2))
            s.fill(wing, (7, 5, 2, 2))

    # ------------------------------------------------ turtle
    def init_turtle(self, g):
        w = g.world
        if g.spot == 'cove' and w.lilies:
            l = max(w.lilies, key=lambda l: (l['r'] if l['y'] < 300 else 0))
            self.bx, self.by = l['x'], l['y'] - 1
        else:
            self.bx, self.by = 420, 297
        self.x, self.y = self.bx - 16, self.by + 6
        self.face = 1
        self.go('surface', 'move')

    def upd_turtle(self, dt, g):
        s = self.state
        if s == 'surface':
            if self.st > 2.2:
                self.go('climb', 'move')
        elif s == 'climb':
            if self.toward(self.bx, self.by, 9, dt):
                self.face = self.rng.choice((-1, 1))
                self.go('bask', 'still')
                self.wait = self.rng.uniform(4, 6)
        elif s == 'bask':
            if self.st > self.wait:
                if self.life <= 0:
                    self.go('slide', 'move')
                else:
                    self.go('stretch', 'special')
        elif s == 'stretch':
            if self.st > 2.6:
                self.go('bask', 'still')
                self.wait = self.rng.uniform(4, 7)
        else:
            self.x += self.face * 10 * dt
            self.y += 5 * dt
            if self.st > 1.4:
                g.world.ripple(self.x, self.y, 5, 8, 140)
                self.gone = True

    def draw_turtle(self, s, t):
        shell, rim, skin = (62, 84, 50), (220, 180, 60), (82, 112, 60)
        if self.state == 'surface':
            s.fill(skin, (6, 6, 3, 2))
            s.set_at((6, 6), (230, 200, 70))
            return
        pygame.draw.ellipse(s, shell, (3, 3, 10, 5))
        s.set_at((7, 4), lighten(shell, 0.3))
        s.set_at((10, 5), lighten(shell, 0.3))
        s.set_at((5, 5), lighten(shell, 0.25))
        s.fill(rim, (3, 7, 10, 1))
        s.set_at((6, 7), (200, 70, 50))
        s.set_at((10, 7), (200, 70, 50))
        if self.state == 'stretch':
            s.fill(skin, (2, 5, 2, 1))
            s.fill(skin, (0, 3, 3, 2))
            s.set_at((1, 3), (230, 200, 70))
            s.set_at((2, 8), skin)
            s.set_at((13, 8), skin)
            s.set_at((14, 7), skin)
        else:
            s.fill(skin, (1, 5, 3, 2))
            s.set_at((1, 5), (230, 200, 70))
            s.set_at((4, 8), skin)
            s.set_at((11, 8), skin)

    # ------------------------------------------------ otter
    def init_otter(self, g):
        lo, hi = LANES[g.spot]
        self.enter_side(self.rng.uniform(lo, hi))
        self.tx = self.rng.uniform(220, 460)
        self.wake = 0.0

    def upd_otter(self, dt, g):
        s = self.state
        self.wake -= dt
        if s in ('in', 'swim'):
            if self.wake <= 0 and not self.hidden:
                self.wake = 0.7
                g.world.ripple(self.x - self.face * 4, self.y + 1, 5, 6, 90)
            if self.state == 'in':
                if self.toward(self.tx, self.y, 22, dt):
                    self.go('float', 'still')
                    self.wait = self.rng.uniform(4, 6)
            else:
                self.leave(26, dt)
        elif s == 'float':
            self.x += self.face * 2 * dt
            if self.st > self.wait:
                self.go('clam', 'special')
        elif s == 'clam':
            if int(self.st * 4) != int((self.st - dt) * 4):
                self.sound = ('click', 0.3)
            if self.st > 2.6:
                self.go('dive', 'move')
                self.hidden = True
                g.world.ripple(self.x, self.y + 1, 6, 9, 150)
                self.sound = ('plop', 0.3)
        elif s == 'dive':
            if self.st > 2.2:
                self.hidden = False
                self.x = max(30, min(W - 30, self.x + self.face * 40))
                g.world.ripple(self.x, self.y + 1, 6, 9, 150)
                if self.life <= 0:
                    self.go('swim', 'move')
                else:
                    self.go('float', 'still')
                    self.wait = self.rng.uniform(3, 5)

    def draw_otter(self, s, t):
        br, lt, dk = (110, 80, 56), (176, 146, 116), (60, 44, 34)
        if self.state in ('in', 'swim'):
            s.fill(br, (3, 3, 4, 4))
            s.set_at((2, 4), dk)
            s.set_at((5, 2), br)
            s.set_at((4, 4), (20, 20, 20))
            s.fill(br, (9, 5, 6, 2))
            s.fill(br, (16, 6, 3, 1))
            s.fill((200, 220, 230, 140), (1, 7, 6, 1))
            return
        pygame.draw.ellipse(s, br, (4, 4, 12, 4))
        s.fill(lt, (7, 4, 6, 2))
        s.fill(br, (1, 3, 4, 4))
        s.fill(lt, (1, 5, 2, 1))
        s.set_at((0, 4), dk)
        s.set_at((2, 3), (20, 20, 20))
        s.set_at((16, 3), br)
        s.set_at((17, 2), br)
        tap = self.state == 'clam' and int(self.st * 8) % 2
        s.set_at((8, 2 + tap), dk)
        s.set_at((10, 2 + tap), dk)
        if self.state == 'clam':
            s.fill((236, 230, 220), (9, 3, 2, 1))
        s.fill((200, 220, 230, 140), (3, 8, 14, 1))

    # ------------------------------------------------ deer
    def init_deer(self, g):
        lo, hi = SHORE_X[g.spot]
        self.tx = self.rng.uniform(lo, hi)
        self.face = self.rng.choice((-1, 1))
        self.x, self.y = self.tx - self.face * 24, HORIZON + 1
        self.alpha = 0

    def upd_deer(self, dt, g):
        s = self.state
        if s == 'in':
            self.alpha = min(255, self.alpha + 120 * dt)
            if self.toward(self.tx, self.y, 8, dt):
                self.go('drink', 'still')
                self.wait = self.rng.uniform(4, 6)
        elif s == 'drink':
            if self.st > self.wait:
                self.go('look', 'special')
        elif s == 'look':
            if self.st > 2.8:
                self.n += 1
                if self.life <= 0 or self.n >= 3:
                    self.face = -self.face
                    self.go('out', 'move')
                else:
                    self.go('drink', 'still')
                    self.wait = self.rng.uniform(4, 6)
        else:
            self.x += self.face * 8 * dt
            self.alpha = max(0, self.alpha - 90 * dt)
            if self.alpha <= 0:
                self.gone = True

    def draw_deer(self, s, t):
        br, lt, dk, wh = (150, 104, 64), (186, 140, 96), (96, 66, 44), (246, 244, 236)
        walk = self.state in ('in', 'out') and int(t * 6) % 2
        s.fill(br, (5, 5, 6, 3))
        s.fill(lt, (6, 7, 4, 1))
        for i, lx in enumerate((5, 6, 9, 10)):
            s.fill(dk, (lx + (1 if walk and i % 2 else 0), 8, 1, 3))
        if self.state == 'drink':
            s.fill(br, (3, 6, 2, 2))
            s.fill(br, (1, 8, 3, 2))
            s.set_at((3, 7), dk)
            s.set_at((11, 5), wh)
        elif self.state == 'look':
            s.fill(br, (4, 2, 2, 4))
            s.fill(br, (2, 1, 3, 2))
            s.set_at((1, 2), dk)
            s.set_at((3, 0), br)
            s.set_at((5, 0), br)
            s.fill(wh, (11, 3, 1, 3) if int(self.st * 3) % 2 else (11, 4, 2, 1))
        else:
            s.fill(br, (4, 3, 2, 3))
            s.fill(br, (2, 2, 3, 2))
            s.set_at((1, 3), dk)
            s.set_at((4, 1), br)
            s.set_at((11, 5), wh)

    # ------------------------------------------------ fox
    def init_fox(self, g):
        lo, hi = SHORE_X[g.spot]
        self.face = self.rng.choice((-1, 1))
        self.x = lo - 20 if self.face > 0 else hi + 20
        self.y = HORIZON + 1
        self.alpha = 0
        self.tx = self.x + self.face * self.rng.uniform(50, 90)

    def upd_fox(self, dt, g):
        s = self.state
        if s in ('in', 'trot'):
            self.alpha = min(255, self.alpha + 150 * dt)
            if self.toward(self.tx, self.y, 16, dt):
                self.go('listen', 'still')
                self.wait = self.rng.uniform(2, 3.5)
        elif s == 'listen':
            if self.st > self.wait:
                self.go('pounce', 'special')
                self.x0 = self.x
        elif s == 'pounce':
            k = min(1.0, self.st / 0.9)
            self.x = self.x0 + self.face * 12 * k
            self.hop = math.sin(math.pi * k) * 7
            if k >= 1 and not getattr(self, 'landed', False):
                self.landed = True
                g.world.sparkles(self.x + self.face * 4, self.y, 10, (240, 244, 250), 5)
                self.sound = ('splash_small', 0.15)
            if self.st > 1.8:
                self.landed = False
                self.hop = 0
                self.n += 1
                if self.life <= 0 or self.n >= 3:
                    self.go('out', 'move')
                else:
                    self.tx = max(20, min(W - 20, self.x + self.face * self.rng.uniform(30, 60)))
                    self.go('trot', 'move')
        else:
            self.leave(18, dt)
            self.alpha = max(0, self.alpha - 60 * dt)
            if self.alpha <= 0:
                self.gone = True

    def draw_fox(self, s, t):
        ora, wh, dk = (214, 110, 46), (246, 240, 230), (50, 36, 30)
        hop = int(getattr(self, 'hop', 0)) if self.state == 'pounce' else 0
        y = 2 - min(2, hop // 3)
        if self.state == 'pounce' and self.st > 0.45:
            # head first into the snow
            s.fill(ora, (5, y + 4, 6, 2))
            s.fill(ora, (2, y + 6, 3, 3))
            s.fill(ora, (10, y + 2, 4, 2))
            s.set_at((14, y + 1), wh)
            return
        walk = self.state in ('in', 'trot', 'out') and int(t * 8) % 2
        s.fill(ora, (4, y + 4, 7, 2))
        s.fill(wh, (4, y + 5, 2, 1))
        for i, lx in enumerate((4, 5, 9, 10)):
            s.fill(dk, (lx + (1 if walk and i % 2 else 0), y + 6, 1, 3))
        s.fill(ora, (2, y + 2, 3, 3))
        s.set_at((1, y + 4), dk)
        s.set_at((2, y + 1), ora)
        s.set_at((4, y + 1), ora)
        s.fill(ora, (11, y + 3, 3, 2))
        s.set_at((14, y + 3), wh)

    # ------------------------------------------------ owl
    def init_owl(self, g):
        self.px, self.py = PERCH[g.spot]
        self.enter_side(self.py - 50)

    def upd_owl(self, dt, g):
        s = self.state
        if s == 'in':
            if self.toward(self.px, self.py, 40, dt):
                self.go('perch', 'still')
                self.wait = self.rng.uniform(4, 6)
        elif s == 'perch':
            if self.st > self.wait:
                if self.life <= 0 or self.n >= 3:
                    self.face = self.rng.choice((-1, 1))
                    self.go('out', 'move')
                else:
                    self.n += 1
                    self.go('hoot', 'special')
                    self.sound = ('hoot', 0.6)
        elif s == 'hoot':
            if self.st > 2.6:
                self.go('perch', 'still')
                self.wait = self.rng.uniform(5, 8)
        else:
            self.leave(40, dt, -20)

    def draw_owl(self, s, t):
        br, face, eye, dk = (120, 94, 70), (196, 172, 138), (250, 210, 80), (70, 54, 42)
        self.eyes = []
        if self.state in ('in', 'out'):
            f = math.sin(t * 5)
            pygame.draw.ellipse(s, br, (4, 7, 7, 5))
            s.fill(face, (2, 7, 3, 3))
            tip = int(5 * f)
            pygame.draw.polygon(s, br, [(5, 8), (10, 8), (13, 8 - tip), (2, 8 - tip)])
            return
        pygame.draw.ellipse(s, br, (3, 5, 8, 10))
        for p in ((5, 10), (7, 11), (6, 13), (8, 9)):
            s.set_at(p, face)
        turn = 1 if self.state == 'hoot' and 0.4 < self.st < 2.2 else 0
        s.fill(face, (3 + turn, 5, 6, 4))
        s.set_at((3 + turn, 4), br)
        s.set_at((8 + turn, 4), br)
        blink = int(t * 2.3) % 9 == 0
        for ex in (4 + turn, 7 + turn):
            s.set_at((ex, 6), dk if blink else eye)
            if not blink:
                self.eyes.append((ex, 6))
        s.set_at((5 + turn, 8), (220, 190, 90))
        if self.state == 'hoot':
            s.fill(br, (2, 9, 1, 3))
            s.fill(br, (11, 9, 1, 3))
        s.fill((150, 140, 110), (4, 14, 2, 1))
        s.fill((150, 140, 110), (8, 14, 2, 1))

    # ------------------------------------------------ loon
    def init_loon(self, g):
        lo, hi = LANES[g.spot]
        self.x, self.y = self.rng.uniform(260, 520), self.rng.uniform(lo, hi)
        self.face = self.rng.choice((-1, 1))
        self.go('swim', 'still')
        self.wait = self.rng.uniform(5, 8)
        self.called = False
        g.world.ripple(self.x, self.y + 1, 6, 9, 150)

    def upd_loon(self, dt, g):
        s = self.state
        if s == 'swim':
            self.x += self.face * 5 * dt
            if self.st > self.wait:
                if not self.called or self.rng.random() < 0.4:
                    self.go('call', 'special')
                    self.called = True
                    self.sound = ('loon', 0.7)
                else:
                    self.go('dive', 'move')
                    self.hidden = True
                    g.world.ripple(self.x, self.y + 1, 6, 9, 150)
        elif s == 'call':
            if self.st > 2.8:
                self.go('swim', 'still')
                self.wait = self.rng.uniform(4, 6)
        elif s == 'dive':
            if self.st > 3.2:
                if self.life <= 0:
                    self.gone = True
                    return
                self.hidden = False
                self.x = max(30, min(W - 30, self.x + self.rng.uniform(-50, 50)))
                g.world.ripple(self.x, self.y + 1, 6, 9, 150)
                self.go('swim', 'still')
                self.wait = self.rng.uniform(4, 7)

    def draw_loon(self, s, t):
        blk, wh, grn, red = (24, 26, 30), (232, 234, 238), (24, 44, 38), (200, 40, 40)
        y = 2
        if self.state == 'call' and 0.3 < self.st < 2.5:
            s.fill(blk, (6, y + 3, 7, 4))
            for p in ((7, y + 4), (9, y + 5), (11, y + 4)):
                s.set_at(p, wh)
            s.fill(blk, (11, y - 2, 6, 2))
            s.fill(blk, (0, y - 2, 6, 2))
            s.set_at((13, y - 2), wh)
            s.set_at((3, y - 2), wh)
            s.fill(grn, (5, y - 2, 2, 5))
            s.fill(grn, (4, y - 2, 3, 2))
            s.fill(blk, (2, y - 2, 2, 1))
            s.set_at((4, y - 2), red)
        else:
            s.fill(blk, (6, y + 4, 9, 3))
            for p in ((7, y + 4), (9, y + 5), (11, y + 4), (13, y + 5)):
                s.set_at(p, wh)
            s.fill(grn, (4, y + 3, 2, 2))
            s.set_at((4, y + 3), wh)
            s.fill(grn, (2, y + 1, 3, 3))
            s.fill(blk, (0, y + 2, 2, 1))
            s.set_at((3, y + 2), red)
            s.set_at((15, y + 5), blk)
        s.fill((200, 220, 230, 130), (3, y + 7, 13, 1))

    # ------------------------------------------------ beaver
    def init_beaver(self, g):
        lo, hi = LANES[g.spot]
        self.enter_side(self.rng.uniform(lo, hi))
        self.tx = self.rng.uniform(220, 440)
        self.wake = 0.0

    def upd_beaver(self, dt, g):
        s = self.state
        self.wake -= dt
        if self.wake <= 0 and s in ('in', 'swim'):
            self.wake = 0.8
            g.world.ripple(self.x - self.face * 5, self.y + 1, 5, 6, 90)
        if s == 'in':
            if self.toward(self.tx, self.y, 13, dt):
                self.go('gnaw', 'still')
        elif s == 'gnaw':
            if self.st > 4:
                self.go('swim', 'move')
        elif s == 'swim':
            self.x += self.face * 13 * dt
            if self.st > 4 or self.x < 20 or self.x > W - 20:
                self.go('slap', 'special')
        elif s == 'slap':
            if self.st > 0.4 and not getattr(self, 'slapped', False):
                self.slapped = True
                g.world.splash(self.x - self.face * 8, self.y, 12, 0.8)
                g.world.ripple(self.x - self.face * 8, self.y + 1, 8, 12, 180)
                self.sound = ('splash_small', 0.5)
            if self.st > 1.0:
                self.go('gone', 'move')
                self.hidden = True
        else:
            if self.st > 1.5:
                self.gone = True

    def draw_beaver(self, s, t):
        br, dk, tail = (110, 76, 50), (60, 42, 30), (70, 54, 46)
        y = 3
        s.fill(br, (4, y + 1, 5, 3))
        s.set_at((3, y + 2), dk)
        s.set_at((7, y), br)
        s.set_at((5, y + 1), (20, 20, 20))
        s.fill(br, (9, y + 3, 6, 2))
        if self.state == 'slap':
            s.fill(tail, (15, y - 1, 3, 4))
        else:
            s.fill(tail, (15, y + 4, 4, 1))
        if self.state != 'slap':
            pygame.draw.line(s, (100, 78, 54), (0, y + 1), (8, y + 3))
            for p in ((0, y), (1, y + 2), (2, y)):
                s.set_at(p, (110, 160, 80))
            if self.state == 'gnaw' and int(t * 6) % 2:
                s.set_at((4, y + 3), (240, 230, 200))
        s.fill((200, 220, 230, 130), (3, y + 5, 14, 1))

    # ------------------------------------------------ swans
    def init_swans(self, g):
        lo, hi = LANES[g.spot]
        self.enter_side(self.rng.uniform(lo, hi))
        self.tx = self.rng.uniform(160, 260) if self.x < 0 else self.rng.uniform(380, 480)

    def upd_swans(self, dt, g):
        s = self.state
        if s == 'in':
            if self.toward(self.tx, self.y, 13, dt):
                self.go('drift', 'still')
                self.wait = self.rng.uniform(4, 6)
        elif s == 'drift':
            self.x += self.face * 1.5 * dt
            if self.st > self.wait:
                if self.life <= 0 and self.n:
                    self.go('out', 'move')
                else:
                    self.n += 1
                    self.go('heart', 'special')
        elif s == 'heart':
            if self.st > 3.2:
                self.go('drift', 'still')
                self.wait = self.rng.uniform(5, 7)
        else:
            self.leave(9, dt)

    @staticmethod
    def _swan(s, ox, flip, bow, t):
        tmp = pygame.Surface((16, 16), pygame.SRCALPHA)
        sh, beak = (206, 212, 218), (230, 120, 50)
        pygame.draw.ellipse(tmp, WHITE, (4, 8, 10, 5))
        tmp.fill(sh, (7, 9, 6, 1))
        tmp.set_at((14, 8), WHITE)
        tmp.set_at((13, 7), WHITE)
        if bow:
            for x, y in ((5, 8), (4, 7), (4, 6), (5, 5), (6, 5)):
                tmp.fill(WHITE, (x, y, 1, 1))
            tmp.fill(WHITE, (6, 5, 2, 2))
            tmp.fill(beak, (8, 7, 1, 1))
            tmp.set_at((7, 5), (30, 30, 30))
        else:
            for x, y in ((5, 8), (4, 7), (4, 6), (5, 5), (5, 4), (5, 3)):
                tmp.fill(WHITE, (x, y, 2, 1))
            tmp.fill(WHITE, (3, 2, 3, 2))
            tmp.fill(beak, (1, 3, 2, 1))
            tmp.set_at((3, 3), (30, 30, 30))
        tmp.fill((200, 220, 230, 120), (3, 13, 12, 1))
        if flip:
            tmp = pygame.transform.flip(tmp, True, False)
        s.blit(tmp, (ox, 0))

    def draw_swans(self, s, t):
        if self.state == 'heart' and 0.3 < self.st < 3.0:
            self._swan(s, 2, True, True, t)
            self._swan(s, 14, False, True, t)
        else:
            self._swan(s, 0, False, False, t)
            self._swan(s, 15, False, False, t + 1)

    # ------------------------------------------------ bats
    def init_bats(self, g):
        self.cx = -30 if self.rng.random() < 0.5 else W + 30
        self.vx = 14 if self.cx < 0 else -14
        self.bats = [(self.cx, 150)] * 3
        self.ph = [self.rng.uniform(0, 6) for _ in range(3)]
        self.swoop = -1
        self.go('fly', 'move')
        self.next = self.rng.uniform(3, 5)

    def upd_bats(self, dt, g):
        if self.life > 0:
            target = W * 0.5
            self.cx += max(-14, min(14, (target - self.cx) * 0.3)) * dt
        else:
            self.cx += self.vx * 2 * dt
            if self.cx < -60 or self.cx > W + 60:
                self.gone = True
        self.next -= dt
        if self.swoop < 0 and self.next <= 0:
            self.swoop = self.rng.randrange(3)
            self.sw_t = 0.0
            self.next = self.rng.uniform(4, 6)
        out = []
        for i, ph in enumerate(self.ph):
            x = self.cx + math.sin(self.t * (1.1 + i * 0.3) + ph) * 120 + math.sin(self.t * 3.1 + ph) * 18
            y = 150 + math.sin(self.t * (1.7 + i * 0.2) + ph * 2) * 26 + math.sin(self.t * 5 + ph) * 6
            if i == self.swoop:
                self.sw_t += dt
                k = min(1.0, self.sw_t / 1.4)
                y += math.sin(math.pi * k) * (HORIZON + 34 - y)
                if 0.45 < k < 0.55 and not getattr(self, 'dipped', False):
                    self.dipped = True
                    g.world.ripple(x, HORIZON + 34, 4, 6, 140)
                if k >= 1:
                    self.swoop = -1
                    self.dipped = False
            out.append((x, y))
        self.bats = out
        self.x, self.y = sum(b[0] for b in out) / 3, sum(b[1] for b in out) / 3
        self.pose = 'special' if self.swoop >= 0 else 'move'

    def draw_bats(self, s, t):
        pass   # drawn bat by bat in draw()

    # ------------------------------------------------ moose
    def init_moose(self, g):
        self.face = -1
        self.x, self.y = W + 20, 214
        self.tx = self.rng.uniform(440, 520)

    def upd_moose(self, dt, g):
        s = self.state
        if s == 'in':
            if self.toward(self.tx, self.y, 9, dt):
                self.go('drink', 'still')
                self.wait = self.rng.uniform(4, 6)
                g.world.ripple(self.x, self.y + 1, 8, 10, 120)
        elif s == 'drink':
            if self.st > self.wait:
                self.go('lift', 'special')
        elif s == 'lift':
            if self.st > 3.0:
                self.n += 1
                if self.life <= 0 or self.n >= 3:
                    self.face = 1
                    self.go('out', 'move')
                else:
                    self.go('drink', 'still')
                    self.wait = self.rng.uniform(4, 6)
        else:
            self.leave(9, dt)

    def draw_moose(self, s, t):
        dk, lg, ant, weed = (74, 56, 42), (110, 90, 70), (196, 176, 136), (90, 150, 74)
        walk = self.state in ('in', 'out') and int(t * 4) % 2
        s.fill(dk, (8, 7, 12, 7))
        s.fill(dk, (9, 6, 5, 1))
        for i, lx in enumerate((9, 11, 16, 18)):
            s.fill(lg, (lx + (1 if walk and i % 2 else 0), 14, 2, 5))
        if self.state == 'drink':
            s.fill(dk, (4, 10, 5, 4))
            s.fill(dk, (1, 13, 5, 4))
            s.fill(ant, (4, 9, 4, 1))
            s.set_at((4, 8), ant)
            s.set_at((7, 8), ant)
        else:
            s.fill(dk, (5, 6, 4, 5))
            s.fill(dk, (1, 7, 5, 4))
            s.fill(dk, (0, 9, 2, 3))
            s.set_at((5, 12), dk)
            s.fill(ant, (3, 4, 6, 2))
            for p in ((3, 3), (5, 3), (7, 3), (9, 4)):
                s.set_at(p, ant)
            s.set_at((3, 8), (20, 20, 20))
            if self.state == 'lift':
                for k, (wx, wy) in enumerate(((0, 12), (1, 13), (2, 12), (1, 14))):
                    s.set_at((wx, wy + (int(self.st * 6 + k) % 3 if k == 3 else 0)), weed)
        s.fill((200, 220, 230, 150), (6, 19, 16, 1))

    # ------------------------------------------------ the white stag
    def init_stag(self, g):
        lo, hi = SHORE_X[g.spot]
        self.x, self.y = self.rng.uniform(lo + 40, hi - 40), HORIZON + 1
        self.face = self.rng.choice((-1, 1))
        self.alpha = 0
        self.go('in', 'still')

    def upd_stag(self, dt, g):
        s = self.state
        if s == 'in':
            self.alpha = min(255, self.alpha + 70 * dt)
            if self.alpha >= 255:
                self.go('stand', 'still')
        elif s == 'stand':
            if self.st > 4:
                if self.n:
                    self.go('out', 'still')
                else:
                    self.n = 1
                    self.go('bow', 'special')
                    self.sound = ('wish', 0.4)
        elif s == 'bow':
            if int(self.st * 3) != int((self.st - dt) * 3):
                g.world.sparkles(self.x, self.y - 8, 6, (230, 236, 255), 8)
            if self.st > 3.4:
                self.go('stand', 'still')
        else:
            self.alpha = max(0, self.alpha - 60 * dt)
            if self.alpha <= 0:
                self.gone = True

    def draw_stag(self, s, t):
        sh, ant = (204, 212, 228), (240, 222, 164)
        s.fill(WHITE, (5, 8, 7, 3))
        s.fill(sh, (6, 10, 5, 1))
        for lx in (5, 6, 10, 11):
            s.fill(sh, (lx, 11, 1, 5))
        if self.state == 'bow':
            s.fill(WHITE, (3, 9, 2, 2))
            s.fill(WHITE, (1, 11, 3, 2))
            pygame.draw.line(s, ant, (3, 10), (1, 7))
            pygame.draw.line(s, ant, (4, 10), (6, 6))
        else:
            s.fill(WHITE, (4, 5, 2, 4))
            s.fill(WHITE, (2, 4, 3, 2))
            s.set_at((1, 5), sh)
            for (a, b) in (((4, 4), (4, 0)), ((4, 2), (2, 1)), ((5, 4), (7, 0)), ((6, 2), (8, 1))):
                pygame.draw.line(s, ant, a, b)
        s.set_at((12, 8), WHITE)

    # ------------------------------------------------ drawing
    def draw(self, near, t):
        if self.hidden or self.alpha <= 0:
            return
        if self.id == 'bats':
            for i, (bx, by) in enumerate(self.bats):
                up = int(t * 14 + i) % 2
                x, y = int(bx), int(by)
                c = (48, 40, 52)
                near.fill(c, (x - 1, y - 1, 2, 3))
                if up:
                    pygame.draw.line(near, c, (x - 4, y - 3), (x - 1, y))
                    pygame.draw.line(near, c, (x + 3, y - 3), (x, y))
                else:
                    pygame.draw.line(near, c, (x - 4, y + 1), (x - 1, y))
                    pygame.draw.line(near, c, (x + 3, y + 1), (x, y))
            return
        w, h, ax, ay = self.SIZE[self.id]
        tmp = pygame.Surface((w, h), pygame.SRCALPHA)
        getattr(self, 'draw_' + self.id)(tmp, t)
        if self.face > 0:
            tmp = pygame.transform.flip(tmp, True, False)
            ax = w - ax
            self.eyes = [(w - 1 - ex, ey) for ex, ey in self.eyes]
        if self.alpha < 255:
            tmp.set_alpha(int(self.alpha))
        x, y = int(self.x) - ax, int(self.y) - ay
        near.blit(tmp, (x, y))
        self.eyes = [(x + ex, y + ey) for ex, ey in self.eyes]
        if self.id in ('deer', 'fox', 'stag', 'moose'):
            # a faint reflection in the still water below
            r = pygame.transform.flip(tmp, False, True)
            r.set_alpha(int(50 * self.alpha / 255))
            near.blit(r, (x, y + h - 1))


# ---------------------------------------------------------------- the lake's wildlife, all together
def update(g, dt):
    if g.snap_flash > 0:
        g.snap_flash = max(0.0, g.snap_flash - dt)
    if g.snap_card:
        g.snap_card['t'] -= dt
        if g.snap_card['t'] <= 0:
            g.snap_card = None
    c = g.critter
    if g.mode != 'play' or g.place != 'lake':
        g.critter = None
        return
    if c and (c.spot != g.spot or g.rest_phase is not None):
        g.critter = c = None
    if c:
        c.update(dt, g)
        if c.sound:
            g.audio.play(c.sound[0], c.sound[1], max(0.0, min(1.0, c.x / W)))
            c.sound = None
        if c.gone:
            g.critter = None
            g.critter_cd = g.critter_rng.uniform(20, 40)
        return
    if g.rest_phase is not None or g.overlay in ('scene', 'cooking', 'ice'):
        return
    g.critter_cd -= dt
    if g.critter_cd > 0:
        return
    rng = g.critter_rng
    g.critter_cd = rng.uniform(12, 28)
    pool = [sp for sp in SPAWNED if eligible(sp, g)]
    if not pool or rng.random() > 0.6:
        return
    weights = [sp['w'] * (3.0 if sp['id'] not in g.nature else 1.0) for sp in pool]
    sp = rng.choices(pool, weights)[0]
    spawn(g, sp['id'])


def spawn(g, cid):
    sp = SPECIES_BY_ID[cid]
    g.critter = Critter(sp, g, g.critter_rng)
    day_key = '%s:%d' % (cid, g.day)
    if g.nature.get(cid, {}).get('stars', 0) < 3 and g.critter_told != day_key:
        g.critter_told = day_key
        g.toast('%s nearby. Press %s for photo mode.' % (sp['name'] if cid in g.nature else 'Something is moving',
                                                        photo_key(g)), (110, 140, 120))
    return g.critter


def photo_key(g):
    import binds
    return binds.key_label(g.binds().key_of('photo'))


def draw(near, g, t):
    c = g.critter
    if c and g.place == 'lake':
        c.draw(near, t)


def draw_lights(frame, g, env):
    """Owl eyes catch the light at night; the white stag has a faint glow of its own."""
    c = g.critter
    if not c or c.hidden or g.place != 'lake':
        return
    if c.id == 'owl' and env.nf > 0.3:
        for ex, ey in c.eyes:
            frame.set_at((ex, ey), (255, 226, 120))
    elif c.id == 'stag':
        a = 34 * c.alpha / 255
        if a > 2:
            glow = pygame.Surface((30, 30))
            for i, r in enumerate(range(14, 1, -3)):
                v = a * (i + 1) / 5
                pygame.draw.circle(glow, (int(v * 0.8), int(v * 0.86), int(v)), (15, 15), r)
            frame.blit(glow, (int(c.x) - 15, int(c.y) - 22), special_flags=pygame.BLEND_RGB_ADD)


def hud_line(g):
    c = g.critter
    if not c or c.hidden or g.hide_ui or not on_screen(c.rect()):
        return None
    sp = c.sp
    if g.nature.get(c.id, {}).get('stars', 0) >= 3:
        return None
    return '%s nearby: %s for a photo' % (sp['name'] if c.id in g.nature else 'An animal', photo_key(g))


# ---------------------------------------------------------------- the camera
def on_screen(r):
    if r.w <= 0 or r.h <= 0:
        return False
    c = r.clip(pygame.Rect(0, 0, W, H))
    return c.w * c.h >= 0.6 * r.w * r.h


def candidates(g):
    """What's in the picture right now: (stars, species, world rect)."""
    out = []
    if g.place != 'lake':
        return out
    c = g.critter
    if c and not c.hidden and c.alpha > 140:
        r = c.rect()
        if on_screen(r):
            out.append((POSE_STARS[c.pose], c.sp, r))
    w = g.world
    d = w.ducks
    if d:
        r = pygame.Rect(int(d['x']) - 7, int(d['y']) - 7, d['n'] * 10 + 13, 9)
        if on_screen(r):
            whole = r.left >= W * 0.12 and r.right <= W * 0.88
            out.append((3 if whole else 2, SPECIES_BY_ID['mallard'], r))
    if g.spot == 'cove' and g.env.season != 3 and w.spot == 'cove':
        best = None
        for fr in w.frogs:
            if fr['i'] >= len(w.lilies):
                continue
            l = w.lilies[fr['i']]
            r = pygame.Rect(int(l['x']) - 5, int(l['y']) - 6, 11, 8)
            st = 3 if fr['puff'] > 0 else 2
            if on_screen(r) and (best is None or st > best[0]):
                best = (st, SPECIES_BY_ID['frog'], r)
        if best:
            out.append(best)
    return out


def best_candidate(g):
    cands = candidates(g)
    return max(cands, key=lambda c: c[0]) if cands else None


def snap(g):
    g.snap_flash = 0.45
    g.audio.play('shutter', 0.8)
    g.stats['snaps'] = g.stats.get('snaps', 0) + 1
    best = best_candidate(g)
    if best is None:
        g.snap_card = {'surf': g.frame.subsurface(_crop(W // 2, H // 2)).copy(), 'name': 'The lake', 'stars': 0,
                       'new': False, 'better': False, 't': 2.6}
        return None
    stars, sp, r = best
    surf = g.frame.subsurface(_crop(*r.center)).copy()
    rec = g.nature.get(sp['id'])
    new = rec is None
    better = new or stars > rec['stars']
    reward = 0
    if new:
        reward += NEW_REWARD
    if stars == 3 and (new or rec['stars'] < 3):
        reward += NEW_REWARD
    g.nature[sp['id']] = {'stars': max(stars, rec['stars'] if rec else 0),
                          'day': g.day if better else rec['day'], 'n': (rec['n'] if rec else 0) + 1}
    if better:
        g.photos[sp['id']] = surf
        d = g.photo_dir()
        if d:
            try:
                os.makedirs(d, exist_ok=True)
                pygame.image.save(pygame.transform.scale(surf, (320, 180)), os.path.join(d, sp['id'] + '.png'))
            except (OSError, pygame.error) as e:
                print('photo save failed', e)
    if reward:
        g.coins += reward
        g.audio.play('jingle3' if new else 'jingle2', 0.5)
    g.snap_card = {'surf': surf, 'name': sp['name'], 'stars': stars, 'new': new, 'better': better and not new,
                   'reward': reward, 't': 3.4}
    g.check_badges()
    g.save()
    return stars


def _crop(cx, cy):
    r = pygame.Rect(0, 0, 160, 90)
    r.center = (int(cx), int(cy))
    r.clamp_ip(pygame.Rect(0, 0, W, H))
    return r


def photo(g, cid):
    """The best photo of an animal: from this session, or from the photos folder."""
    if cid in g.photos:
        return g.photos[cid]
    d = g.photo_dir()
    surf = None
    if d and cid in g.nature:
        p = os.path.join(d, cid + '.png')
        if os.path.exists(p):
            try:
                surf = pygame.transform.scale(pygame.image.load(p), (160, 90))
            except pygame.error:
                surf = None
    g.photos[cid] = surf
    return surf


def portrait(cid, t=0.0):
    """The animal drawn on a little water background, for when there's no photo file to show."""
    surf = pygame.Surface((160, 90))
    surf.fill((150, 186, 204))
    surf.fill((110, 150, 170), (0, 50, 160, 40))
    sp = SPECIES_BY_ID[cid]
    big = pygame.Surface((40, 22), pygame.SRCALPHA)
    if cid in ('mallard', 'frog'):
        if cid == 'mallard':
            pygame.draw.ellipse(big, (120, 92, 64), (8, 12, 9, 4))
            big.fill((40, 110, 70), (7, 9, 3, 3))
            big.set_at((6, 10), (240, 170, 60))
            for i in range(3):
                pygame.draw.ellipse(big, (246, 214, 100), (18 + i * 6, 13, 5, 3))
        else:
            big.fill((70, 120, 60), (14, 14, 9, 2))
            big.fill((96, 156, 76), (15, 12, 7, 3))
            big.set_at((16, 11), (30, 34, 30))
            big.set_at((20, 11), (30, 34, 30))
    else:
        rng = random.Random(3)
        c = Critter.__new__(Critter)
        c.sp, c.id, c.rng, c.t, c.st, c.face, c.n, c.eyes = sp, cid, rng, t, 0.0, -1, 0, []
        c.alpha, c.hidden = 255, False
        c.state = {'heron': 'stand', 'kingfisher': 'perch', 'dragonfly': 'perch', 'turtle': 'bask',
                   'otter': 'float', 'deer': 'look', 'fox': 'listen', 'owl': 'perch', 'loon': 'swim',
                   'beaver': 'gnaw', 'swans': 'heart', 'bats': 'fly', 'moose': 'lift', 'stag': 'stand'}[cid]
        c.st = 1.0
        if cid == 'bats':
            c.bats = [(12, 6), (22, 10), (30, 5)]
            c.draw(big, t)
        else:
            w, h, ax, ay = Critter.SIZE[cid]
            c.x, c.y = (40 - w) // 2 + ax, (22 - h) // 2 + ay
            c.draw(big, t)
    s2 = pygame.transform.scale(big, (160, 88))
    surf.blit(s2, (0, 0))
    return surf


# ---------------------------------------------------------------- photo mode on screen
def draw_viewfinder(g, s):
    ui = g.ui
    sw, sh = s.get_size()
    col, dk = (250, 246, 236), (30, 24, 34)
    m, ln = 36, 46
    for (x, y, dx, dy) in ((m, m, 1, 1), (sw - m, m, -1, 1), (m, sh - m, 1, -1), (sw - m, sh - m, -1, -1)):
        for c, wdt in ((dk, 8), (col, 4)):
            pygame.draw.line(s, c, (x, y), (x + dx * ln, y), wdt)
            pygame.draw.line(s, c, (x, y), (x, y + dy * ln), wdt)
    # what the camera is looking at
    best = best_candidate(g) if g.mode == 'play' else None
    if best:
        stars, sp, r = best
        x0, y0 = g.w2s(r.x, r.y)
        x1, y1 = g.w2s(r.right, r.bottom)
        box = pygame.Rect(x0 - 10, y0 - 10, x1 - x0 + 20, y1 - y0 + 20)
        fc = (255, 214, 90) if stars == 3 else (250, 246, 236) if stars == 2 else (190, 186, 180)
        k = 12
        for (x, y, dx, dy) in ((box.x, box.y, 1, 1), (box.right, box.y, -1, 1), (box.x, box.bottom, 1, -1),
                               (box.right, box.bottom, -1, -1)):
            pygame.draw.line(s, fc, (x, y), (x + dx * k, y), 3)
            pygame.draw.line(s, fc, (x, y), (x, y + dy * k), 3)
        name = sp['name'] if sp['id'] in g.nature else '???'
        ui.blit_text(s, name, (box.centerx, box.y - 30), 'smallb', fc, 'center', outline=dk)
        for i in range(3):
            U.star(s, (box.centerx - 16 + i * 16, box.bottom + 16), 6, (255, 214, 90) if i < stars else (90, 84, 96))
    if ui.pad_layout:
        hint = [('pad', 'A'), 'take a photo     ', ('pad', 'X'), 'save the screen     ', ('pad', 'B'), 'done']
    else:
        hint = [('key', 'Space'), 'or', ('key', 'Click'), 'take a photo     ', ('key', 'P'), 'done     ',
                ('key', 'F12'), 'save the screen']
    hw = ui.rich(s, hint, (0, 0), measure=True)
    ui.rich(s, hint, (sw // 2 - hw // 2, sh - m - 30), col, outline=dk)
    n = len(g.nature)
    ui.blit_text(s, 'Nature page  %d / %d' % (n, len(SPECIES)), (sw // 2, m + 12), 'smallb', col, 'center',
                 outline=dk)
    # the flash, then the photo you just took
    if g.snap_flash > 0:
        fl = pygame.Surface((sw, sh), pygame.SRCALPHA)
        fl.fill((255, 255, 255, int(255 * min(1.0, g.snap_flash / 0.45) ** 2)))
        s.blit(fl, (0, 0))
    card = g.snap_card
    if card:
        k = min(1.0, (3.4 - card['t']) * 4) if card['t'] > 0.4 else card['t'] / 0.4
        r = pygame.Rect(0, 0, 360, 264)
        r.bottomright = (sw - m - 20, sh - m - 60 + int((1 - k) * 300))
        pygame.draw.rect(s, (40, 30, 40), r.move(4, 6), border_radius=6)
        pygame.draw.rect(s, (252, 250, 244), r, border_radius=6)
        s.blit(pygame.transform.scale(card['surf'], (320, 180)), (r.x + 20, r.y + 18))
        ui.blit_text(s, card['name'], (r.x + 20, r.y + 210), 'smallb', U.INK, maxw=220)
        for i in range(3):
            U.star(s, (r.right - 66 + i * 20, r.y + 220), 8, (240, 190, 60) if i < card['stars'] else (214, 206, 196))
        sub = ('New on your Nature page!' if card['new'] else 'A better photo!' if card['better'] else
               'Nothing in the frame, but a lovely view.' if not card['stars'] else 'Your best one is still better.')
        if card.get('reward'):
            sub += '  +%d coins' % card['reward']
        ui.blit_text(s, sub, (r.x + 20, r.y + 236), 'tiny', U.SOFT, maxw=320)


# ---------------------------------------------------------------- the Nature page of the journal
def draw_page(g, s, rect):
    ui = g.ui
    gx, gy = rect.x + 28, rect.y + 90
    tw, th = 172, 110
    hover = None
    for n, sp in enumerate(SPECIES):
        col, row = n % 4, n // 4
        tr = pygame.Rect(gx + col * (tw + 6), gy + row * (th + 6), tw, th)
        rec = g.nature.get(sp['id'])
        hov = tr.collidepoint(ui.mouse)
        if hov:
            hover = n
        sel = n == g.n_sel
        ui.tile(s, tr, (252, 248, 236) if hov or sel else (240, 230, 210),
                (240, 190, 60) if rec and rec['stars'] >= 3 else (150, 180, 130) if rec else (186, 170, 150), sel)
        pr = pygame.Rect(tr.x + 22, tr.y + 8, 128, 72)
        if rec:
            ph = photo(g, sp['id']) or _portrait_cached(g, sp['id'])
            s.blit(pygame.transform.scale(ph, pr.size), pr)
            pygame.draw.rect(s, (252, 250, 244), pr, 2)
        else:
            pygame.draw.rect(s, (214, 202, 184), pr, border_radius=6)
            ui.blit_text(s, '?', pr.center, 'h2', (186, 172, 154), 'center')
        nm = sp['name'] if rec else '???'
        ui.blit_text(s, nm, (tr.centerx, tr.bottom - 20), 'tiny', U.INK if rec else U.SOFT, 'center', maxw=tw - 50)
        if rec:
            for k in range(3):
                U.star(s, (tr.right - 38 + k * 12, tr.y + 14), 5, U.GOLD if k < rec['stars'] else (214, 204, 190))
        ui.hotspot(tr, lambda n=n: setattr(g, 'n_sel', n))
    sp = SPECIES[hover if hover is not None else g.n_sel]
    rec = g.nature.get(sp['id'])
    dr = pygame.Rect(rect.x + 740, rect.y + 90, 272, 470)
    pygame.draw.rect(s, (244, 234, 214), dr, border_radius=16)
    pygame.draw.rect(s, (214, 196, 170), dr, 2, border_radius=16)
    pr = pygame.Rect(dr.x + 16, dr.y + 16, 240, 135)
    if rec:
        ph = photo(g, sp['id']) or _portrait_cached(g, sp['id'])
        pygame.draw.rect(s, (252, 250, 244), pr.inflate(10, 10))
        s.blit(pygame.transform.scale(ph, pr.size), pr)
    else:
        pygame.draw.rect(s, (220, 208, 190), pr, border_radius=8)
        ui.blit_text(s, 'No photo yet', pr.center, 'smallb', (170, 156, 140), 'center')
    y = pr.bottom + 16
    ui.blit_text(s, sp['name'] if rec else '???', (dr.x + 16, y), 'h3', U.INK, maxw=dr.w - 32)
    y += 36
    if rec:
        for k in range(3):
            U.star(s, (dr.x + 24 + k * 22, y + 8), 8, U.GOLD if k < rec['stars'] else (214, 204, 190))
        ui.blit_text(s, 'Photos: %d' % rec['n'], (dr.right - 16, y), 'small', U.SOFT, 'topright')
        y += 30
        for line in ui.wrap(sp['desc'], 'small', dr.w - 32):
            ui.blit_text(s, line, (dr.x + 16, y), 'small', U.INK)
            y += 22
        y += 8
        if rec['stars'] < 3:
            for line in ui.wrap('For three stars, wait for its special moment.', 'tiny', dr.w - 32):
                ui.blit_text(s, line, (dr.x + 16, y), 'tiny', (150, 120, 80))
                y += 20
    ui.blit_text(s, 'Where to look', (dr.x + 16, dr.bottom - 96), 'smallb', U.SOFT)
    yy = dr.bottom - 72
    for line in ui.wrap(sp['where'], 'small', dr.w - 32)[:3]:
        ui.blit_text(s, line, (dr.x + 16, yy), 'small', U.INK)
        yy += 22
    three = sum(1 for r in g.nature.values() if r['stars'] >= 3)
    ui.blit_text(s, 'Animals  %d / %d      Three-star photos  %d      Photo mode: %s'
                 % (len(g.nature), len(SPECIES), three, photo_key(g)), (rect.x + 34, rect.bottom - 40), 'smallb',
                 U.SOFT)


def _portrait_cached(g, cid):
    key = ('portrait', cid)
    if key not in g.photos:
        g.photos[key] = portrait(cid)
    return g.photos[key]
