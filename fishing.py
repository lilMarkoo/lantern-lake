"""Casting, bites, the reel-in fight (see minigame.py) and everything drawn on the line."""
import math
import random

import pygame

import art
from art import W, H, HORIZON, DECK_Y, lerp_c, add_glow
from data import FISH, JUNK, RARITY_WEIGHT, SPOT_FISH
from minigame import ReelGame, LegendGame
import coast
import legends
import seasons

PLAYER_X = 238
HAND = (243, 273)
REEL_END = (274, 316)


def cast_point(d, aim=0.33):
    """Where a cast lands. d is distance (0..1), aim swings it left (-1) or right (+1) across the lake."""
    return (min(628, 275 + d * (130 + (aim + 1) * 150)), 318 - d * 118)


def aim_for(d, wx):
    """The aim that makes a cast of distance d land at world x (clamped)."""
    return clamp(((wx - 275) / max(0.05, d) - 130) / 150 - 1, -1.0, 1.0)


def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def spot_depth(spot, d):
    """How deep a cast of distance d reaches at each spot (the cove is shallow, the Deep is deep everywhere)."""
    if spot == 'cove':
        return d * 0.6
    if spot == 'deep':
        return 0.45 + d * 0.55
    if spot == 'creek':
        return 0.15 + d * 0.7
    if spot == 'rocks':
        return 0.1 + d * 0.9          # the water drops away fast off the rocks
    return d


# how long bites take at each spot, and how fast the creek carries the bobber (pixels per second)
SPOT_WAIT = {'dock': 1.0, 'cove': 0.8, 'deep': 1.35, 'creek': 0.9, 'pier': 0.9, 'rocks': 1.1}
CREEK_DRIFT = 6.0


class Fishing:
    def __init__(self, g):
        self.g = g
        self.rng = random.Random()
        self.reset()

    def reset(self):
        self.state = 'idle'
        self.t = 0.0
        self.power = 0.0
        self.pdir = 1
        self.angle = -55.0
        self.bend = 0.0
        self.tip = (HAND[0] + 15, HAND[1] - 21)
        self.rod_pts = []
        self.bob = None
        self.catch = None
        self.shadow = None
        self.nibbles = []
        self.nib_anim = 0.0
        self.bite_at = 99
        self.mg = None
        self.hot = False
        self.fish_pos = None
        self.fly_pos = None
        self.leap_h = 0.0
        self.message = ''
        if not hasattr(self, 'aim'):
            self.aim = 0.33

    # ------------------------------------------------------------ input
    def press(self):
        st = self.state
        g = self.g
        if st == 'idle':
            if seasons.frozen(g):
                seasons.open_ice(g)              # winter: Lily Cove is ice fishing
                return
            if seasons.fly_on(g):
                seasons.start_fly(self)          # the creek with a fly rod: cast in rhythm
                return
            self.fly_q = 0
            self.state = 'charging'
            self.t = 0
            self.power = 0.0
            self.pdir = 1
        elif st == 'fly':
            seasons.press_fly(self)
        elif st == 'waiting':
            if self.nib_anim > 0:
                g.toast('Too eager! It was only a nibble.', (200, 120, 100))
            else:
                g.toast('You reel in the line.', (150, 140, 130))
            self.flee_shadow()
            self.to_reel_back()
        elif st == 'bite':
            self.hook()
        elif st == 'fight' and self.mg:
            self.mg.press()

    def release(self):
        if self.state == 'charging':
            self.cast(self.power)

    # ------------------------------------------------------------ transitions
    def cast(self, power):
        rod = self.g.rod_spec()
        self.d = 0.1 + power * (rod['range'] - 0.1)
        self.src = self.tip
        self.dst = cast_point(self.d, self.aim)
        self.dur = 0.45 + self.d * 0.4
        self.state = 'casting'
        self.t = 0
        self.bob = list(self.src)
        self.g.audio.play('cast', 0.7)

    def land(self):
        g = self.g
        w = g.world
        self.bob = list(self.dst)
        x, y = self.dst
        self.drift_max = x + 46
        persp = 0.5 + (y - HORIZON) / 170
        w.ripple(x, y, 9 * persp + 3)
        w.ripple(x, y, 5 * persp + 2, 10)
        w.splash(x, y, 6, 0.6 * persp)
        g.audio.play('plop', 0.6, x / W)
        self.hot = w.take_spot(x, y, persp)
        if self.hot:
            g.toast('Right on the bubbles! Something is down there...', (90, 150, 190))
        self.catch = self.pick(self.d)
        spec = self.catch['spec']
        base = self.rng.uniform(2.5, 7.5)
        env = g.env
        night = env.phase in ('night', 'dusk')
        if g.bait == 'corn':
            base *= 0.55
        if night and g.has('lantern'):
            base *= 0.8
        if g.bait == 'glow' and night:
            base *= 0.7
        if env.weather == 'rain':
            base *= 0.6 if g.bait == 'storm' else 0.85
        base += spec['rarity'] * 0.6
        base *= SPOT_WAIT.get(getattr(g, 'spot', 'dock'), 1.0)
        base *= coast.bite_mult(g)        # ragworm and the bow lamp, down at the sea
        base *= g.boost('bite')           # bakery tea and cooked meals
        base *= 1 - 0.06 * getattr(self, 'fly_q', 0)
        if self.hot:
            base *= 0.45
        self.bite_at = base
        self.nibbles = []
        if base > 1.8:
            for _ in range(self.rng.choice((0, 1, 1, 2, 2, 3))):
                self.nibbles.append(self.rng.uniform(0.8, base - 0.8))
            self.nibbles.sort()
        self.nib_anim = 0
        self.shadow = None
        self.state = 'waiting'
        self.t = 0

    def pick(self, d):
        g = self.g
        env = g.env
        phase, season, weather = env.phase, env.season, env.weather
        rod = g.rod
        cands = []
        run = g.run_fish(g.day)
        spot = getattr(g, 'spot', 'dock')
        d = spot_depth(spot, d)
        legend = None
        for f in FISH:
            if spot == 'dock':
                if f['spot']:
                    continue
            elif f['spot'] != spot and f['id'] not in SPOT_FISH[spot]:
                continue
            if f.get('event') and not g.event_active(f['event']):
                continue
            if f['rarity'] == 5 and not legends.can_bite(g, f['id']):
                continue                   # legends only ever bite on their own lure...
            if f.get('tide') and not coast.fish_ok(g, f):
                continue                   # at the sea, some fish come and go with the tide
            if f.get('year') and seasons.year(g) < f['year']:
                continue                   # new arrivals in year two
            fw = seasons.fly_weight(self, f)
            if fw is None:
                continue                   # fly-only fish want a good fly cast
            if spot == 'creek' and f['id'] in ('salmon', 'riverking') and season == 2:
                pass                       # the autumn run: salmon swim up the creek at any hour
            elif f['phases'] and phase not in f['phases']:
                continue
            if f['rarity'] == 5:
                pass                       # ...and with it, whatever the season or the weather
            elif f['seasons'] is not None and season not in f['seasons']:
                continue
            elif f['weather'] and weather not in f['weather']:
                continue
            lo, hi = f['depth']
            if d < lo or d > hi + 0.05:
                continue
            if f['needs'] and rod != f['needs']:
                continue
            r = f['rarity']
            w = RARITY_WEIGHT[r]
            if g.bait == 'golden' and r >= 3:
                w *= 2.5
            if g.bait == 'glow' and f['phases'] and 'night' in f['phases'] and phase in ('night', 'dusk'):
                w *= 2.5
            if r >= 2:
                w *= 1 + g.luck * 0.25 * (r - 1)
            if r >= 3:
                w *= g.boost('rare')      # a Star Cookie or a cooked meal
                if phase in ('night', 'dusk') and 'lighthouse' in g.projects:
                    w *= 1.4
            if f['phases'] and 'night' in f['phases'] and phase in ('night', 'dusk'):
                w *= g.boost('night')
            if f['id'] == 'sturgeon' and env.full_moon:
                w *= 3
            if rod == 'starlight' and r == 5:
                w *= 1.5
            if f['id'] not in g.journal:
                w *= 1.3
            if f.get('event'):
                w *= 4
            if f['id'] == run:
                w *= 4
            if g.bait == 'moon' and r >= 4 and phase in ('night', 'dusk'):
                w *= 3
            if g.bait == 'storm' and f['weather'] and 'rain' in f['weather'] and weather == 'rain':
                w *= 3
            if self.hot and r >= 2:
                w *= 1.8
            if spot == 'deep':
                w *= 1.6 if r >= 3 else 0.45 if r == 1 else 1.0     # few small fish out in the deep water
            elif spot == 'cove' and r == 1:
                w *= 1.2
            if f['spot'] == spot and r >= 2:
                w *= 1.5                  # the locals are the easiest to find in their own water
            if spot == 'creek' and season == 2 and f['id'] in ('salmon', 'riverking'):
                w *= 3
            w *= fw
            w *= coast.weight_mult(g, f)   # squid strips, harbour chowder and the lighthouse
            q = getattr(self, 'fly_q', 0)
            if q and r >= 2:
                w *= 1 + 0.1 * q           # a lovely fly cast brings up the better fish
            if f['rarity'] == 5:
                legend = f
                continue
            cands.append((f, w))
        for j in JUNK:
            w = j['weight']
            if j['id'] == 'bottle' and len(g.letters) >= 10:
                w = 0.5
            if spot == 'deep':
                w *= 2.5 if j['id'] == 'clam' else 0.4
            elif spot == 'creek' and j['id'] == 'driftwood':
                w *= 2
            elif spot in ('pier', 'rocks'):
                w *= {'clam': 1.6, 'can': 0.5, 'driftwood': 1.4}.get(j['id'], 1.0)
            cands.append((j, w))
        if legend:
            cands.append((legend, sum(w for _, w in cands)))     # in its time and place, a coin flip
        total = sum(w for _, w in cands)
        x = self.rng.uniform(0, total)
        spec = cands[-1][0]
        for f, w in cands:
            x -= w
            if x <= 0:
                spec = f
                break
        lo, hi = spec['size']
        r = min(1.0, self.rng.random() ** 1.7 + g.luck * 0.03 + (0.12 if spot == 'deep' else 0)
                + g.boost('size'))
        size = round(lo + (hi - lo) * r, 1)
        return dict(spec=spec, size=size)

    def bite(self):
        g = self.g
        self.state = 'bite'
        self.t = 0
        spec = self.catch['spec']
        self.window = 0.8 + g.rod_spec()['window'] + (0.2 if spec.get('junk') else 0)
        x, y = self.bob
        g.world.splash(x, y, 10, 0.9)
        g.world.ripple(x, y, 14)
        g.audio.play('bite', 0.8, x / W)
        g.on_bite()

    def hook(self):
        g = self.g
        spec = self.catch['spec']
        g.use_bait()
        g.audio.play('hook', 0.6)
        if spec.get('junk'):
            self.start_landing(self.bob)
            return
        self.state = 'fight'
        self.t = 0
        self.splash_t = 0.3
        self.start = tuple(self.bob)
        self.fish_pos = list(self.bob)
        lo, hi = spec['size']
        size_k = (self.catch['size'] - lo) / max(0.01, hi - lo)
        if spec['rarity'] == 5 and (legends.HUNT_BY_FISH.get(spec['id']) or spec['id'] == 'mariner'):
            self.mg = LegendGame(spec, g.rod_spec(), g.assist(), self.rng, size_k, legends.fight_lines(spec['id']))
            g.audio.play('warn', 0.8)
        else:
            self.mg = ReelGame(spec, g.rod_spec(), g.assist(), self.rng, size_k)
        g.shake(1.5)

    def start_landing(self, pos):
        g = self.g
        self.mg = None
        self.leap_h = 0.0
        self.state = 'landing'
        self.t = 0
        self.fly_from = tuple(pos)
        self.fly_pos = list(pos)
        g.world.splash(pos[0], pos[1], 14, 1.2)
        g.world.ripple(pos[0], pos[1], 16)
        g.audio.play('splash', 0.7, pos[0] / W)
        self.shadow = None

    def to_reel_back(self):
        self.state = 'reel_back'
        self.t = 0
        if self.bob is None:
            self.state = 'idle'

    def flee_shadow(self):
        if self.shadow:
            s = self.shadow
            s['mode'] = 'flee'
            dx = s['x'] - (self.bob[0] if self.bob else s['x'])
            s['fx'] = 1 if dx >= 0 else -1

    def fail(self, text, sound='sad'):
        g = self.g
        g.toast(text, (200, 120, 100))
        g.audio.play(sound, 0.6)
        self.flee_shadow()
        if self.fish_pos:
            self.bob = list(self.fish_pos)
        self.fish_pos = None
        self.mg = None
        self.leap_h = 0.0
        self.to_reel_back()

    def finish(self):
        """Called when the catch card is closed."""
        self.state = 'idle'
        self.catch = None
        self.bob = None
        self.fly_pos = None
        self.t = 0

    # ------------------------------------------------------------ update
    def update(self, dt):
        g = self.g
        self.t += dt
        st = self.state
        target = -55.0
        rate = 8.0
        self.bend += (0 - self.bend) * min(1, dt * 6)
        if self.shadow:
            self._update_shadow(dt)
        if st == 'fly':
            g.aim_cast(dt)
            target = seasons.update_fly(self, dt)
            rate = 14
        elif st == 'charging':
            g.aim_cast(dt)
            self.power += self.pdir * dt * 0.85
            if self.power >= 1:
                self.power, self.pdir = 1.0, -1
            elif self.power <= 0:
                self.power, self.pdir = 0.0, 1
            target = -62 - self.power * 58
            rate = 12
        elif st == 'casting':
            k = min(1.0, self.t / self.dur)
            sx, sy = self.src
            dx, dy = self.dst
            e = 1 - (1 - k) ** 1.6
            self.bob = [sx + (dx - sx) * e, sy + (dy - sy) * e - math.sin(math.pi * k) * (36 + self.d * 46)]
            target = -32
            rate = 22
            if k >= 1:
                self.land()
        elif st == 'waiting':
            target = -40
            if getattr(g, 'spot', 'dock') == 'creek':
                # the current carries the bobber downstream (to the right) until the line pulls tight
                self.dst = (min(self.dst[0] + CREEK_DRIFT * dt, min(628, self.drift_max)), self.dst[1])
            x, y = self.dst
            self.nib_anim = max(0, self.nib_anim - dt)
            dip = 1.5 if self.nib_anim > 0 else 0
            self.bob = [x, y + math.sin(self.t * 2.6) * 0.6 + dip]
            if self.nibbles and self.t >= self.nibbles[0]:
                self.nibbles.pop(0)
                self.nib_anim = 0.3
                g.world.ripple(x, y, 6, 10, 120)
                g.audio.play('nibble', 0.5, x / W)
            if not self.catch['spec'].get('junk') and self.shadow is None and self.t >= self.bite_at - 2.4:
                self._spawn_shadow()
            if self.t >= self.bite_at:
                self.bite()
        elif st == 'bite':
            target = -42
            x, y = self.dst
            self.bob = [x, y + 3]
            if self.t > self.window:
                self.fail('It got away... bites are quick!')
        elif st == 'fight':
            self._fight(dt)
            if self.state == 'fight':
                mg = self.mg
                target = -38 + mg.strain * 22
                self.bend = 0.25 + mg.strain * 0.75
                rate = 10
                if mg.warn > 0 or mg.lunge > 0:
                    target += math.sin(self.t * 48) * (5 if mg.warn > 0 else 3)
                    self.bend += 0.15 * math.sin(self.t * 37)
                    rate = 30
        elif st == 'landing':
            k = min(1.0, self.t / 0.7)
            fx, fy = self.fly_from
            tx, ty = HAND[0] + 10, HAND[1] - 26
            self.fly_pos = [fx + (tx - fx) * k, fy + (ty - fy) * k - math.sin(math.pi * k) * 40]
            self.bob = list(self.fly_pos)
            target = -95
            rate = 10
            if k >= 1:
                self.state = 'caught'
                self.t = 0
                g.on_catch(self.catch)
        elif st == 'caught':
            target = -95
        elif st == 'reel_back':
            target = -60
            if self.bob is None:
                self.state = 'idle'
            else:
                bx, by = self.bob
                tx, ty = self.tip
                k = min(1, dt * 6)
                self.bob = [bx + (tx - bx) * k, by + (ty - by) * k - dt * 20]
                if abs(bx - tx) + abs(by - ty) < 6 or self.t > 1.2:
                    self.bob = None
                    self.state = 'idle'
                    self.shadow = None
        self.angle += (target - self.angle) * min(1, dt * rate)
        self._rod_geometry()

    def _rod_geometry(self):
        rod = self.g.rod_spec()
        L = rod['length']
        a = math.radians(self.angle)
        ux, uy = math.cos(a), math.sin(a)
        hx, hy = HAND
        straight = (hx + ux * L, hy + uy * L)
        bx = by = 0.0
        if self.bend > 0.02:
            target = self.fish_pos or self.bob
            if target:
                vx, vy = target[0] - straight[0], target[1] - straight[1]
                n = math.hypot(vx, vy) or 1
                bx, by = vx / n * L * 0.4 * self.bend, vy / n * L * 0.4 * self.bend
        pts = []
        for i in range(9):
            s = i / 8
            pts.append((hx + ux * s * L + bx * s * s, hy + uy * s * L + by * s * s))
        self.rod_pts = pts
        self.tip = pts[-1]

    def _spawn_shadow(self):
        x, y = self.dst
        spec = self.catch['spec']
        lo, hi = spec['size']
        sz = clamp(math.log(1 + self.catch['size']) / math.log(240))
        persp = 0.5 + (y - HORIZON) / 170
        side = self.rng.choice((-1, 1))
        self.shadow = dict(x=x + side * self.rng.uniform(26, 40) * persp, y=y + self.rng.uniform(-6, 8) * persp,
                           w=(5 + sz * 22) * persp, h=(2 + sz * 6) * persp, a=0.0, mode='approach', fx=side)

    def _update_shadow(self, dt):
        s = self.shadow
        if s['mode'] == 'approach':
            s['a'] = min(1, s['a'] + dt * 0.8)
            if self.bob:
                tx, ty = self.bob[0], self.bob[1] + 2
                s['x'] += (tx - s['x']) * min(1, dt * 0.9)
                s['y'] += (ty - s['y']) * min(1, dt * 0.9)
            if self.state == 'fight' and self.fish_pos:
                s['x'], s['y'] = self.fish_pos[0], self.fish_pos[1] + 2
        else:
            s['x'] += s['fx'] * 90 * dt
            s['a'] -= dt * 1.5
            if s['a'] <= 0:
                self.shadow = None

    def _fight(self, dt):
        g = self.g
        mg = self.mg
        aim, steer = g.reel_input()
        mg.update(dt, g.holding, aim, steer)
        fx, fy = self.fish_pos
        w = g.world
        for ev in mg.events:
            k = ev[0]
            if k == 'warn':
                w.ripple(fx, fy, 10, 26, 220)
                w.ripple(fx, fy, 6, 18, 200)
                g.audio.play('warn', 0.7, fx / W)
            elif k == 'lunge':
                w.splash(fx, fy, 8, 0.8)
                g.audio.play('splash_small', 0.5, fx / W)
                g.shake(2.0)
            elif k == 'leap':
                w.splash(fx, fy, 14, 1.1)
                w.ripple(fx, fy, 14)
                g.audio.play('splash', 0.6, fx / W)
            elif k == 'splashdown':
                w.splash(fx, fy, 16, 1.2)
                w.ripple(fx, fy, 16)
                w.ripple(fx, fy, 9, 10)
                g.audio.play('splash', 0.5, fx / W)
                g.shake(2.5)
            elif k == 'perfect':
                g.audio.play('chime%d' % self.rng.randrange(5), 0.8)
                w.sparkles(fx, fy - 20, 14, (255, 236, 160), 12)
                g.shake(1.5)
            elif k == 'nice':
                g.audio.play('chime0', 0.6)
            elif k == 'miss':
                g.audio.play('nibble', 0.6)
            elif k == 'glimmer':
                g.coins += ev[1]
                g.audio.play('coin', 0.6)
            elif k == 'click':
                g.audio.play('click', 0.3)
            elif k == 'creak':
                g.audio.play('creak', 0.6)
            elif k == 'stage':
                w.splash(fx, fy, 22, 1.5)
                w.ripple(fx, fy, 20)
                w.ripple(fx, fy, 12, 14)
                g.audio.play('splash', 0.8, fx / W)
                g.audio.play('jingle1', 0.5)
                g.shake(4.0)
        mg.events.clear()
        if mg.result == 'caught':
            self.start_landing(self.fish_pos)
            return
        legend = getattr(mg, 'stage', 0)
        if mg.result == 'snap':
            g.shake(3)
            self.fail(legends.on_escape(g, mg.spec['id']) if legend else
                      'Snap! The line broke. Let go when the fish lunges!', 'snap')
            return
        if mg.result == 'escape':
            self.fail(legends.on_escape(g, mg.spec['id']) if legend else
                      'It got away. Keep the golden arc on the fish!')
            return
        # the fish in the water follows its spot on the ring and comes closer as you reel
        sx, sy = self.start
        ex, ey = REEL_END
        p = clamp((mg.progress - 0.3) / 0.7, -0.25, 1.0)
        bx, by = sx + (ex - sx) * p, sy + (ey - sy) * p
        persp = 0.5 + (by - HORIZON) / 170
        ang = math.radians(mg.fa)
        tx = bx + math.cos(ang) * 16 * persp * (1 - max(0, p) * 0.5)
        ty = by + math.sin(ang) * 5 * persp
        k = min(1, dt * (14 if mg.lunge > 0 else 6))
        self.fish_pos = [fx + (tx - fx) * k, fy + (ty - fy) * k]
        L = mg.leap
        if L:
            lk = min(1.0, L['t'] / 1.25)
            self.leap_h = math.sin(math.pi * lk) * 30 * persp
        else:
            self.leap_h = max(0.0, self.leap_h - dt * 80)
        self.bob = [self.fish_pos[0], self.fish_pos[1] - self.leap_h]
        self.splash_t -= dt
        if self.splash_t <= 0 and not L:
            busy = mg.lunge > 0 or mg.warn > 0
            self.splash_t = 0.18 if busy else 0.5
            w.ripple(self.fish_pos[0], self.fish_pos[1], 6 + 6 * persp, 16, 140)
            if busy:
                w.splash(self.fish_pos[0], self.fish_pos[1], 3, 0.5)

    # ------------------------------------------------------------ drawing
    def draw_shadow(self, frame):
        s = self.shadow
        if not s or s['a'] <= 0.02:
            return
        w, h = max(3, int(s['w'])), max(2, int(s['h']))
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (10, 26, 36, int(110 * s['a'])), (0, 0, w, h))
        frame.blit(surf, (int(s['x'] - w / 2), int(s['y'] - h / 2)))

    def draw_water(self, near):
        st = self.state
        if self.bob is None:
            return
        x, y = int(self.bob[0]), int(self.bob[1])
        if st in ('casting', 'waiting', 'reel_back'):
            # red and white bobber
            persp = 0.5 + (y - HORIZON) / 170
            if persp > 0.75 or st == 'casting':
                near.fill((250, 250, 245), (x - 1, y - 1, 3, 2))
                near.fill((220, 60, 60), (x - 1, y - 3, 3, 2))
                near.set_at((x, y - 4), (60, 50, 50))
            else:
                near.fill((250, 250, 245), (x, y - 1, 2, 1))
                near.fill((220, 60, 60), (x, y - 2, 2, 1))
            if st == 'waiting':
                near.fill((230, 240, 250, 140), (x - 2, y + 1, 5, 1))
        elif st == 'bite':
            near.fill((220, 60, 60), (x - 1, y - 2, 3, 1))
            near.fill((255, 255, 255, 200), (x - 3, y - 1, 7, 1))
        elif st == 'fight':
            if self.leap_h > 1 and self.fish_pos:
                x, y = int(self.fish_pos[0]), int(self.fish_pos[1])
            persp = 0.5 + (y - HORIZON) / 170
            r = int(3 + 3 * persp)
            for i in range(4):
                a = self.t * 9 + i * 1.6
                near.set_at((x + int(math.cos(a) * r), y + int(math.sin(a) * r * 0.4)), (240, 248, 255, 220))
            near.fill((255, 255, 255, 180), (x - r, y, r * 2, 1))

    def draw_line(self, near):
        st = self.state
        if self.bob is None or st == 'idle' or st == 'charging':
            return
        tx, ty = self.tip
        bx, by = self.bob
        if st == 'fight' and self.leap_h > 1:
            # the fish jumps clear of the water
            spr = art.fish_sprite(self.catch['spec'])
            persp = 0.5 + (self.fish_pos[1] - HORIZON) / 170
            k = 0.3 + 0.12 * persp
            small = pygame.transform.scale(spr, (int(spr.get_width() * k), int(spr.get_height() * k)))
            L = self.mg.leap if self.mg else None
            tilt = 50 - 100 * min(1.0, L['t'] / 1.25) if L else -40
            if self.mg and self.mg.fv < 0:
                small = pygame.transform.flip(small, True, False)
                tilt = -tilt
            rot = pygame.transform.rotate(small, tilt)
            near.blit(rot, (int(bx - rot.get_width() / 2), int(by - rot.get_height() / 2)))
        if st == 'landing' or st == 'caught':
            spr = art.fish_sprite(self.catch['spec'])
            sw = spr.get_width()
            if st == 'landing':
                k = 0.35
                small = pygame.transform.scale(spr, (int(sw * k), int(spr.get_height() * k)))
                rot = pygame.transform.rotate(small, math.sin(self.t * 25) * 30)
                near.blit(rot, (int(bx - rot.get_width() / 2), int(by - rot.get_height() / 2)))
            return
        strain = self.mg.strain if (st == 'fight' and self.mg) else 0
        if st == 'fight':
            sag = (1 - min(1, 0.25 + strain)) * 16
        elif st == 'casting':
            sag = 2
        else:
            sag = 9
        mx, my = (tx + bx) / 2, (ty + by) / 2 + sag
        pts = []
        for i in range(13):
            s = i / 12
            px = (1 - s) ** 2 * tx + 2 * (1 - s) * s * mx + s * s * bx
            py = (1 - s) ** 2 * ty + 2 * (1 - s) * s * my + s * s * by
            pts.append((px, py))
        col = (236, 236, 226, 190)
        if st == 'fight' and strain > 0.75:
            col = lerp_c((236, 236, 226), (255, 110, 90), min(1, (strain - 0.75) / 0.3)) + (230,)
        pygame.draw.lines(near, col, False, pts)

    def draw_lights(self, frame, nf):
        g = self.g
        w = g.world
        rod = g.rod_spec()
        if rod.get('glow'):
            add_glow(frame, w.g_cool, self.tip, 0.35 + nf * 0.4)
        if g.bait == 'glow' and self.bob and self.state in ('waiting', 'bite'):
            add_glow(frame, w.g_tiny, self.bob, 0.6 + nf * 0.6)
        if self.state == 'fight' and self.catch and self.catch['spec'].get('glow') and self.fish_pos:
            add_glow(frame, w.g_cool, (self.fish_pos[0], self.fish_pos[1] + 3), 0.4 + nf * 0.5)
