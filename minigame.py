"""The reeling minigame.

The hooked fish swims around a ring. You steer a golden arc (mouse or A/D) to stay on top of it:
while the fish is inside the arc the line comes in, outside it the fish gets away. Holding the button
reels faster but builds line strain, and the line snaps if you hold through a lunge. Fish warn you
before they lunge, leap out of the water for a timing challenge, and golden glimmers on the ring
are worth a few coins if you can swing over to them.
"""
import math
import random

import pygame

import art
import ui as U
from data import RARITY_COLORS

CX, CY, R = 196, 424, 104          # ring position on the 1280x720 interface layer
TARGET = 40                        # leap timing: the radius the shrinking ring has to meet
PERFECT, NICE = 9, 22              # leap timing windows in pixels
LEAPS = {1: 0, 2: 1, 3: 2, 4: 2, 5: 3}


def angdiff(a, b):
    """Signed smallest difference a - b in degrees."""
    return (a - b + 180) % 360 - 180


def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


class ReelGame:
    def __init__(self, spec, rod, assist=False, rng=None, size_k=0.5):
        self.spec = spec
        self.rng = rng or random.Random()
        rng = self.rng
        self.s, self.a = spec['strength'], spec['agility']
        self.r = max(1, spec['rarity'])
        self.assist = assist
        self.arc = rod['arc'] + (24 if assist else 0)
        self.turn = rod['turn'] * (1.1 if assist else 1.0)
        self.rate = 0.11 * rod['reel'] / (1 + 1.4 * self.s) / (1 + 0.38 * (self.r - 1))
        self.base = 35 + self.a * 110 + (self.r - 1) * 7                # how fast the fish swims around the ring (deg/s)
        self.behavior = spec.get('behavior') or 'runner'
        self.t = 0.0
        self.progress = 0.3
        self.strain = 0.0
        self.over_t = 0.0
        self.fa = rng.uniform(0, 360)                # fish angle
        self.pa = (self.fa + rng.choice((-1, 1)) * rng.uniform(25, 50)) % 360   # arc centre
        self.fv = 0.0
        self.tv = 0.0
        self.acc = 4.0
        self.mode = 'swim'
        self.mode_t = 0.0
        self.zig = rng.random() * 6
        self.warn = 0.0
        self.lunge = 0.0
        self.lunge_dir = 1
        self.lunge_speed = 0.0
        self.lunge_cd = rng.uniform(2.0, 3.4)
        n = LEAPS.get(self.r, 0)
        if self.r == 1 and size_k > 0.6:
            n = 1
        self.leap_marks = [0.35 + (i + 1) * 0.55 / (n + 1) for i in range(n)]
        self.all_marks = list(self.leap_marks)
        self.leap = None
        self.glim = None
        self.glim_cd = rng.uniform(3.0, 5.0)
        self.coins = 0
        self.events = []
        self.popups = []
        self.result = None
        self.in_arc = False
        self.spin = 0.0
        self.click_t = 0.0
        self.creak_t = 0.0
        self.perfects = 0
        self.lunges = 0
        self.tired = False

    # ------------------------------------------------------------ input
    def press(self):
        """A click / Space press. Only matters during a leap."""
        L = self.leap
        if not L or L['done'] or L['t'] < 0.18:
            return False
        d = abs(L['r'] - TARGET)
        self._grade('perfect' if d <= PERFECT else 'nice' if d <= NICE else 'miss')
        return True

    # ------------------------------------------------------------ update
    def update(self, dt, holding, aim=None, steer=0):
        if self.result:
            return
        self.t += dt
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < 1.1]
        if steer:
            self.pa = (self.pa + steer * self.turn * dt) % 360
        elif aim is not None:
            d = angdiff(aim, self.pa)
            step = self.turn * dt
            self.pa = (self.pa + max(-step, min(step, d))) % 360
        if self.leap:
            self._leap(dt)
            self.strain = max(0.0, self.strain - 0.6 * dt)
            return
        self._fish(dt)
        s = self.s
        self.in_arc = abs(angdiff(self.fa, self.pa)) <= self.arc / 2
        if self.in_arc:
            gain = self.rate * (1.7 if holding else 1.0)
            self.progress += gain * dt
            self.spin += gain * dt * 60
        else:
            self.progress -= (0.04 + 0.05 * s) * (1.3 if self.lunge > 0 else 1.0) * dt
            self.spin -= dt * 2
        if holding:
            if self.lunge > 0:
                k = 1.5
            elif self.in_arc:
                k = 0.2 * (0.6 + s)
            else:
                k = 0.45 * (0.6 + s)
            self.strain += k * dt
            self.click_t -= dt
            if self.click_t <= 0 and self.in_arc:
                self.click_t = 0.075
                self.events.append(('click',))
        else:
            self.strain -= 0.6 * dt
        self.strain = clamp(self.strain, 0, 1.05)
        if self.strain >= 1.0:
            self.over_t += dt
            self.creak_t -= dt
            if self.creak_t <= 0:
                self.creak_t = 0.3
                self.events.append(('creak',))
            if self.over_t > (0.8 if self.assist else 0.4):
                self.result = 'snap'
                return
        else:
            self.over_t = max(0.0, self.over_t - dt * 2)
        self._glimmer(dt)
        if self.leap_marks and self.progress >= self.leap_marks[0]:
            self.leap_marks.pop(0)
            self._start_leap()
        if self.progress >= 1.0:
            self.progress = 1.0
            self.result = 'caught'
        elif self.progress <= 0.0:
            self.progress = 0.0
            self.result = 'escape'

    def tire(self):
        """Long fights wear the fish out, so nobody is stuck reeling forever."""
        return clamp(1 - (self.t - 18) * 0.025, 0.5, 1.0)

    def _fish(self, dt):
        rng = self.rng
        if not self.tired and self.t > 18:
            self.tired = True
            self.popups.append(['It is getting tired...', (200, 226, 250), 0.0])
        if self.lunge > 0:
            self.lunge -= dt
            self.fv = self.lunge_dir * self.lunge_speed
        elif self.warn > 0:
            self.warn -= dt
            self.fv *= 1 - min(1.0, dt * 6)          # it tenses up before the dash
            if self.warn <= 0:
                self.lunge = 0.35 + 0.25 * self.a
                self.lunge_speed = (150 + 200 * self.s) * self.tire()
                d = angdiff(self.fa, self.pa)
                self.lunge_dir = 1 if d >= 0 else -1  # away from the arc...
                if rng.random() < 0.25:
                    self.lunge_dir *= -1              # ...or sometimes straight through it
                self.lunges += 1
                self.events.append(('lunge',))
        else:
            self.lunge_cd -= dt
            if self.lunge_cd <= 0:
                self.warn = 0.9 if self.assist else 0.6
                self.lunge_cd = max(1.8, rng.uniform(2.4, 5.6 - 2.4 * self.s) + (2.0 if self.s < 0.2 else 0))
                self.lunge_cd /= self.tire()
                self.events.append(('warn',))
            self._behave(dt)
            self.fv += (self.tv - self.fv) * min(1.0, dt * self.acc)
        self.fa = (self.fa + self.fv * dt) % 360

    def _behave(self, dt):
        rng, b = self.rng, self.base * self.tire()
        self.mode_t -= dt
        beh = self.behavior
        if beh == 'calm':
            self.acc = 2.0
            if self.mode_t <= 0:
                self.mode_t = rng.uniform(1.4, 3.0)
                self.tv = rng.choice((-1, 1)) * rng.uniform(0.4, 1.0) * b
        elif beh == 'darter':
            self.acc = 12.0
            if self.mode_t <= 0:
                if self.mode == 'dart':
                    self.mode, self.mode_t = 'rest', rng.uniform(0.35, 0.9)
                    self.tv = rng.uniform(-0.15, 0.15) * b
                else:
                    self.mode, self.mode_t = 'dart', rng.uniform(0.25, 0.45)
                    self.tv = rng.choice((-1, 1)) * 2.3 * b
        elif beh == 'zigzag':
            self.acc = 6.0
            self.zig += dt * (1.4 + self.a * 1.5)
            self.tv = math.sin(self.zig) * 1.5 * b + math.sin(self.zig * 0.31) * 0.4 * b
        else:                                         # runner
            self.acc = 3.5
            if self.mode_t <= 0:
                if self.mode == 'run':
                    self.mode, self.mode_t, self.tv = 'turn', rng.uniform(0.3, 0.6), 0.0
                else:
                    self.mode, self.mode_t = 'run', rng.uniform(1.4, 2.8)
                    self.tv = rng.choice((-1, 1)) * rng.uniform(1.0, 1.4) * b

    def _glimmer(self, dt):
        rng = self.rng
        g = self.glim
        if g is None:
            self.glim_cd -= dt
            if self.glim_cd <= 0:
                self.glim = dict(a=(self.fa + rng.uniform(110, 250)) % 360, life=3.2, max=3.2, fill=0.0)
            return
        g['life'] -= dt
        if abs(angdiff(g['a'], self.pa)) <= self.arc / 2:
            g['fill'] += dt / 0.35
            if g['fill'] >= 1:
                c = 2 + self.r * 2 + rng.randint(0, 3)
                self.coins += c
                self.events.append(('glimmer', c))
                self.popups.append(['+%d coins' % c, (250, 210, 100), 0.0])
                self.glim = None
                self.glim_cd = rng.uniform(4.0, 7.0)
                return
        if g['life'] <= 0:
            self.glim = None
            self.glim_cd = rng.uniform(3.0, 6.0)

    def _start_leap(self):
        speed = (150 + self.a * 70) * (0.8 if self.assist else 1.0)
        self.leap = dict(r=150.0, speed=speed, t=0.0, done=None, hold=0.0)
        self.warn = 0.0
        self.lunge = 0.0
        self.events.append(('leap',))

    def _leap(self, dt):
        L = self.leap
        L['t'] += dt
        if L['done']:
            L['hold'] += dt
            if L['hold'] > 0.55:
                self.leap = None
                self.events.append(('splashdown',))
            return
        L['r'] -= L['speed'] * dt
        if L['r'] < TARGET - NICE:
            self._grade('miss')

    def _grade(self, grade):
        L = self.leap
        L['done'] = grade
        if grade == 'perfect':
            self.progress = min(0.99, self.progress + 0.12)
            self.perfects += 1
            self.popups.append(['Perfect!', (255, 226, 120), 0.0])
        elif grade == 'nice':
            self.progress = min(0.99, self.progress + 0.05)
            self.popups.append(['Nice', (200, 236, 200), 0.0])
        else:
            self.progress -= 0.10
            self.strain = min(1.0, self.strain + 0.15)
            self.popups.append(['Missed!', (250, 170, 150), 0.0])
            if self.progress <= 0:
                self.progress = 0.0
                self.result = 'escape'
        self.events.append((grade,))


class LegendGame(ReelGame):
    """A legend fights in three stages. Each stage it changes how it swims and fights harder; reaching a new
    stage sets a checkpoint, so it can only escape by holding you at the checkpoint for a few seconds."""
    STAGE_AT = (0.3, 0.53, 0.76)
    STYLES = ('runner', 'zigzag', 'darter')
    HOLD = 4.0                       # seconds pinned at a checkpoint before it breaks away

    def __init__(self, spec, rod, assist=False, rng=None, size_k=0.5, lines=None):
        super().__init__(spec, rod, assist, rng, size_k)
        self.lines = lines or ('It fights!', 'It fights harder!', 'Last stand!')
        self.stage = 1
        self.floor = 0.0
        self.floor_t = 0.0
        self.st = 0.0
        self.tired = True            # legends tire per stage instead (see tire)
        self.stage_tired = False
        self.behavior = self.STYLES[0]
        self.leap_marks = [0.45, 0.68, 0.9]                  # one leap in every stage
        self.all_marks = list(self.leap_marks)
        self.banner = [self.lines[0], 0.0]
        self.rate *= 0.8                 # a long fight, even for a perfect angler

    def tire(self):
        return clamp(1 - (self.st - 14) * 0.03, 0.6, 1.0)

    def update(self, dt, holding, aim=None, steer=0):
        if self.result:
            return
        self.st += dt
        if self.banner:
            self.banner[1] += dt
            if self.banner[1] > 2.8:
                self.banner = None
        if not self.stage_tired and self.st > 14:
            self.stage_tired = True
            self.popups.append(['It is tiring...', (200, 226, 250), 0.0])
        super().update(dt, holding, aim, steer)
        if self.result == 'escape' and self.floor > 0:
            self.result = None                       # the checkpoint holds it; see below
        if self.result is None and self.floor > 0:
            if self.progress <= self.floor + 0.002:
                self.progress = self.floor
                if self.floor_t == 0:
                    self.popups.append(['Hold on! Win it back!', (250, 190, 150), 0.0])
                    self.events.append(('warn',))
                self.floor_t += dt
                if self.floor_t >= self.HOLD:
                    self.result = 'escape'
                    return
            else:
                self.floor_t = max(0.0, self.floor_t - dt * 2)
        if self.result is None and self.stage < 3 and self.progress >= self.STAGE_AT[self.stage]:
            self._next_stage()

    def _next_stage(self):
        self.stage += 1
        self.floor = self.STAGE_AT[self.stage - 1] - 0.05
        self.floor_t = 0.0
        self.st = 0.0
        self.stage_tired = False
        self.behavior = self.STYLES[self.stage - 1]
        self.base *= 1.12
        self.s = min(1.2, self.s + 0.05)
        self.warn, self.lunge = 0.0, 0.0
        self.lunge_cd = 0.9                          # it comes at you straight away
        self.strain = max(0.0, self.strain - 0.3)
        self.banner = [self.lines[self.stage - 1], 0.0]
        self.events.append(('stage', self.stage))


# ---------------------------------------------------------------- drawing
_cache = {}


def _pt(a, r):
    rad = math.radians(a)
    return (CX + math.cos(rad) * r, CY + math.sin(rad) * r)


def band(dst, color, r0, r1, a0, a1, step=4):
    """A thick ring segment from angle a0 to a1 (degrees, clockwise on screen)."""
    if a1 < a0:
        a0, a1 = a1, a0
    n = max(2, int((a1 - a0) / step) + 1)
    outer = [_pt(a0 + (a1 - a0) * i / (n - 1), r1) for i in range(n)]
    inner = [_pt(a1 - (a1 - a0) * i / (n - 1), r0) for i in range(n)]
    pygame.draw.polygon(dst, color, outer + inner)


def _backdrop():
    s = _cache.get('bg')
    if s is None:
        size = (R + 52) * 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size // 2
        for i in range(24):
            r = R + 52 - i
            pygame.draw.circle(s, (22, 30, 46, min(190, 18 + i * 8)), (c, c), r)
        _cache['bg'] = s
    return s


def draw(s, ui, mg, t, title):
    """Draw the ring minigame on the interface layer."""
    spec = mg.spec
    stage = getattr(mg, 'stage', 0)
    bg = _backdrop()
    shake = 0
    if mg.warn > 0 or mg.over_t > 0:
        shake = int(math.sin(t * 60) * 2)
    s.blit(bg, (CX - bg.get_width() // 2 + shake, CY - bg.get_height() // 2))
    # title above the ring
    if mg.leap and not mg.leap['done']:
        title = 'It leaps! Click as the rings meet'
    ui.blit_text(s, title, (CX, CY - R - 38), 'h3', (255, 246, 228), 'center', (30, 20, 30))
    if stage:
        for i in range(3):
            px = CX - 30 + i * 30
            on = i < stage
            pygame.draw.circle(s, (60, 40, 30), (px, CY - R - 62), 9)
            pygame.draw.circle(s, (255, 214, 100) if on else (110, 100, 90), (px, CY - R - 62), 7)
            if i == stage - 1:
                pygame.draw.circle(s, (255, 250, 230), (px, CY - R - 62), 11, 2)
        if mg.banner:
            text, bt = mg.banner
            a = min(1.0, bt / 0.25, max(0.0, (2.8 - bt) / 0.5))
            sw = s.get_width()
            y = 204 - int((1 - min(1.0, bt / 0.3)) * 20)
            rib = _cache.get(('ribbon', sw))
            if rib is None:
                rib = pygame.Surface((sw, 84), pygame.SRCALPHA)
                for i in range(84):
                    rib.fill((20, 14, 24, int(150 * math.sin(math.pi * i / 83))), (0, i, sw, 1))
                _cache[('ribbon', sw)] = rib
            rib.set_alpha(int(255 * a))
            s.blit(rib, (0, y - 58))
            ui.blit_text(s, 'Stage %d' % stage, (sw // 2, y - 34), 'bodyb', (255, 226, 140), 'center', (40, 24, 20),
                         alpha=255 * a)
            ui.blit_text(s, text, (sw // 2, y), 'h2', (255, 248, 230), 'center', (40, 24, 20), alpha=255 * a)
    # water ring with drifting sparkles
    pygame.draw.circle(s, (44, 86, 112), (CX, CY), R + 14)
    pygame.draw.circle(s, (30, 58, 80), (CX, CY), R - 14)
    pygame.draw.circle(s, (88, 140, 166), (CX, CY), R + 14, 2)
    pygame.draw.circle(s, (70, 110, 136), (CX, CY), R - 14, 2)
    for i in range(18):
        a = i * 20 + t * 14 * (1 if i % 2 else -1)
        x, y = _pt(a, R + math.sin(t * 2 + i) * 6)
        s.fill((140, 196, 216), (int(x), int(y), 2, 2))
    # progress track inside the ring, with stars where the fish will leap
    pr = R - 30
    band(s, (58, 66, 84), pr - 5, pr + 5, -90, 270, 6)
    if mg.progress > 0.005:
        band(s, (130, 206, 176), pr - 5, pr + 5, -90, -90 + 360 * mg.progress, 4)
        hx, hy = _pt(-90 + 360 * mg.progress, pr)
        pygame.draw.circle(s, (240, 252, 244), (int(hx), int(hy)), 6)
        pygame.draw.circle(s, (60, 110, 96), (int(hx), int(hy)), 6, 2)
    if stage:
        for i, at in enumerate(mg.STAGE_AT[1:]):
            a = -90 + 360 * at
            p0, p1 = _pt(a, pr - 10), _pt(a, pr + 10)
            pygame.draw.line(s, (255, 236, 170) if stage > i + 1 else (150, 140, 120), p0, p1, 3)
        if mg.floor > 0 and mg.floor_t > 0 and int(t * 8) % 2:
            band(s, (240, 120, 100), pr - 7, pr + 7, -90 + 360 * mg.floor - 4, -90 + 360 * mg.floor + 4, 2)
    for m in mg.all_marks:
        x, y = _pt(-90 + 360 * m, pr)
        done = m not in mg.leap_marks
        U.star(s, (int(x), int(y)), 7, (200, 190, 170) if done else (255, 226, 120))
    # glimmer
    g = mg.glim
    if g:
        x, y = _pt(g['a'], R)
        tw = 0.7 + 0.3 * math.sin(t * 12)
        fade = min(1.0, g['life'] / 0.6)
        if fade > 0.3 or int(t * 10) % 2:
            U.star(s, (int(x), int(y)), int(9 * tw + 2), (255, 222, 110))
            pygame.draw.circle(s, (255, 244, 200), (int(x), int(y)), 3)
        if g['fill'] > 0:
            pygame.draw.arc(s, (255, 250, 220), (int(x) - 15, int(y) - 15, 30, 30), math.pi / 2,
                            math.pi / 2 + g['fill'] * 2 * math.pi, 3)
    # the golden player arc; brackets at both ends so it reads without colour
    a0, a1 = mg.pa - mg.arc / 2, mg.pa + mg.arc / 2
    on = mg.in_arc and not mg.leap
    glow = 0.5 + 0.5 * math.sin(t * 10) if on else 0
    col = art.lerp_c((206, 160, 70), (255, 226, 130), 0.5 + 0.5 * glow) if on else (190, 150, 80)
    band(s, art.darken(col, 0.35), R - 18, R + 18, a0 - 1, a1 + 1)
    band(s, col, R - 16, R + 16, a0, a1)
    band(s, art.lerp_c(col, (255, 250, 230), 0.5), R + 10, R + 15, a0 + 2, a1 - 2)
    for a, d in ((a0, 1), (a1, -1)):
        p0, p1 = _pt(a, R - 22), _pt(a, R + 22)
        pygame.draw.line(s, (72, 46, 32), p0, p1, 4)
        pygame.draw.line(s, (72, 46, 32), p1, _pt(a + 6 * d, R + 22), 4)
        pygame.draw.line(s, (72, 46, 32), p0, _pt(a + 6 * d, R - 22), 4)
    # the fish
    fx, fy = _pt(mg.fa, R)
    if mg.warn > 0:
        fx += math.sin(t * 70) * 3
    rc = RARITY_COLORS[spec['rarity']] if spec['rarity'] else (200, 200, 200)
    halo = _cache.get(('halo', rc))
    if halo is None:
        halo = pygame.Surface((64, 64), pygame.SRCALPHA)
        for i in range(8, 0, -1):
            pygame.draw.circle(halo, (*rc, 16 + (8 - i) * 10), (32, 32), i * 4)
        _cache[('halo', rc)] = halo
    s.blit(halo, (int(fx) - 32, int(fy) - 32))
    cw = mg.fv >= 0
    heading = mg.fa + (90 if cw else -90)              # direction of travel on screen
    key = ('fm', spec['id'], int(round(heading / 15)) % 24)
    spr = _cache.get(key)
    if spr is None:
        base = art.fish_sprite(spec, 1)
        base = pygame.transform.scale(base, (int(base.get_width() * 1.4), int(base.get_height() * 1.4)))
        h = int(round(heading / 15)) * 15
        if 90 < h % 360 < 270:                          # keep the fish upright when it swims left
            base = pygame.transform.flip(base, False, True)
        spr = pygame.transform.rotate(base, -h)
        _cache[key] = spr
    s.blit(spr, spr.get_rect(center=(int(fx), int(fy))))
    if mg.lunge > 0:
        for i in range(1, 5):
            tx, ty = _pt(mg.fa - mg.lunge_dir * i * 7, R)
            pygame.draw.circle(s, (220, 240, 250), (int(tx), int(ty)), 4 - i // 2)
    if mg.warn > 0:
        bx, by = int(fx), int(fy) - 34 - int(abs(math.sin(t * 14)) * 5)
        pygame.draw.circle(s, (250, 160, 70), (bx, by), 15)
        pygame.draw.circle(s, (130, 70, 30), (bx, by), 15, 2)
        ui.blit_text(s, '!', (bx, by), 'h2', (255, 255, 245), 'center')
    # centre: the reel, or the leap timing rings
    L = mg.leap
    if L:
        pygame.draw.circle(s, (250, 240, 214), (CX, CY), 62)
        pygame.draw.circle(s, (120, 82, 58), (CX, CY), 62, 3)
        pygame.draw.circle(s, (240, 214, 150), (CX, CY), TARGET + PERFECT, 0)
        pygame.draw.circle(s, (250, 240, 214), (CX, CY), TARGET - PERFECT, 0)
        pygame.draw.circle(s, (200, 140, 50), (CX, CY), TARGET, 4)
        if not L['done']:
            r = max(2, int(L['r']))
            pygame.draw.circle(s, (255, 255, 255), (CX, CY), r, 4)
            pygame.draw.circle(s, (90, 60, 40), (CX, CY), r + 2, 1)
        else:
            word = {'perfect': 'Perfect!', 'nice': 'Nice!', 'miss': 'Missed'}[L['done']]
            ui.blit_text(s, word, (CX, CY), 'h3', U.INK, 'center')
    else:
        pygame.draw.circle(s, (120, 82, 58), (CX, CY), 36)
        pygame.draw.circle(s, (232, 214, 182), (CX, CY), 32)
        for i in range(6):
            a = mg.spin + i * math.pi / 3
            pygame.draw.line(s, (150, 112, 82), (CX, CY), (CX + math.cos(a) * 28, CY + math.sin(a) * 28), 3)
        pygame.draw.circle(s, (120, 82, 58), (CX, CY), 8)
        hx, hy = CX + math.cos(mg.spin) * 26, CY + math.sin(mg.spin) * 26
        pygame.draw.circle(s, (210, 120, 90), (int(hx), int(hy)), 7)
        pygame.draw.circle(s, (120, 60, 50), (int(hx), int(hy)), 7, 2)
    # popups float up from the centre
    for text, col, pt in mg.popups:
        a = 1 - pt / 1.1
        y = CY - 80 - pt * 40
        ui.blit_text(s, text, (CX, y), 'bodyb', col, 'center', (30, 20, 30), alpha=255 * min(1, a * 2))
    # line strain: hatched danger end so it reads without colour
    bw, bh = 236, 16
    bx, by = CX - bw // 2, CY + R + 34
    ui.blit_text(s, 'Line strain', (bx, by - 22), 'smallb', (250, 244, 232), 'topleft', (30, 20, 30))
    if mg.coins:
        U.coin(s, (bx + bw - 54, by - 13), 8)
        ui.blit_text(s, '+%d' % mg.coins, (bx + bw - 42, by - 13), 'smallb', (255, 230, 150), 'midleft', (30, 20, 30))
    bar = pygame.Rect(bx, by, bw, bh)
    pygame.draw.rect(s, (226, 214, 192), bar, border_radius=8)
    danger = pygame.Rect(bx + int(bw * 0.8), by, bw - int(bw * 0.8), bh)
    s.set_clip(danger)
    pygame.draw.rect(s, (236, 168, 150), danger)
    for x in range(danger.x - bh, danger.right, 7):
        pygame.draw.line(s, (150, 70, 60), (x, danger.bottom), (x + bh, danger.top), 1)
        pygame.draw.line(s, (150, 70, 60), (x, danger.top), (x + bh, danger.bottom), 1)
    s.set_clip(None)
    fw = int(bw * min(1, mg.strain))
    if fw > 2:
        c = art.lerp_c((150, 200, 160), (240, 170, 80), mg.strain)
        if mg.strain > 0.8:
            c = art.lerp_c(c, (230, 90, 70), (mg.strain - 0.8) * 5)
        pygame.draw.rect(s, c, (bx, by, fw, bh), border_radius=8)
    flash = mg.over_t > 0 and int(t * 16) % 2
    pygame.draw.rect(s, (255, 250, 240) if flash else U.BROWN_D, bar, 2, border_radius=8)
    if ui.pad_layout:
        lines = ('Steer with the left stick', 'Hold %s to reel faster, let go when it lunges' % ui.pad_label('A'))
    else:
        lines = ('Steer with the mouse or A / D', 'Hold to reel faster, let go when it lunges')
    for i, line in enumerate(lines):
        ui.blit_text(s, line, (CX, by + bh + 12 + i * 20), 'small', (240, 232, 220), 'midtop', (30, 20, 30))
