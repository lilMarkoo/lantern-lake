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
HOLD_REEL = 0.4          # while waiting: a tap twitches the bobber, holding this long reels the line in
TWITCH_CUT = (1.1, 0.8, 0.5)     # how much each of the first twitches shortens the wait (then they spook)
_sil_cache = {}


# the bobber, row by row: (offset up from its foot, from x, to x, colour); bigger the nearer it is
BOB_RED, BOB_HI, BOB_WHITE, BOB_STICK = (222, 58, 56), (255, 140, 120), (250, 248, 240), (60, 50, 50)
BOBBER = {
    'near': [(-7, 0, 0, BOB_STICK), (-6, -1, 1, BOB_RED), (-5, -2, 2, BOB_RED), (-4, -2, 2, BOB_RED),
             (-3, -2, 2, BOB_WHITE), (-2, -1, 1, BOB_WHITE), (-1, 0, 0, BOB_WHITE)],
    'mid': [(-5, 0, 0, BOB_STICK), (-4, -1, 1, BOB_RED), (-3, -1, 1, BOB_RED), (-2, -1, 1, BOB_WHITE),
            (-1, 0, 0, BOB_WHITE)],
    'far': [(-3, 0, 0, BOB_STICK), (-2, 0, 1, BOB_RED), (-1, 0, 1, BOB_WHITE)],
}


def draw_bobber(dst, x, y, persp, water=None):
    """A red and white float with its foot at (x, y). With water given, whatever is below the waterline
    (a nibble pulling it down) is hidden."""
    rows = BOBBER['near' if persp > 0.74 else 'mid' if persp > 0.56 else 'far']
    x, y = int(x), int(round(y))
    for dy, x0, x1, col in rows:
        yy = y + dy
        if water is not None and yy >= water:
            continue
        dst.fill(col, (x + x0, yy, x1 - x0 + 1, 1))
    if persp > 0.74 and (water is None or y - 5 < water):
        dst.set_at((x - 1, y - 5), BOB_HI)


def silhouette(spec, width, flip=False):
    """A dark fish-shaped shadow for seeing a fish under the water."""
    width = max(4, int(width))
    key = (spec['id'], width, flip)
    sil = _sil_cache.get(key)
    if sil is None:
        spr = art.fish_sprite(spec)
        h = max(2, int(spr.get_height() * width / spr.get_width()))
        sil = pygame.transform.scale(spr, (width, h))
        if flip:
            sil = pygame.transform.flip(sil, True, False)
        sil.fill((12, 28, 38, 255), special_flags=pygame.BLEND_RGBA_MIN)
        if len(_sil_cache) > 400:
            _sil_cache.clear()
        _sil_cache[key] = sil
    return sil


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
        self.pressing = False
        self.hold_t = 0.0
        self.twitches = 0
        self.twitch_anim = 0.0
        self.school = False
        self.fdir = 1.0              # which way the hooked fish is swimming in the water (-1 left, 1 right)
        self.fspeed = 0.0
        self.spray_t = 0.0
        self.crank = 0.0             # the reel handle's angle (actors.py turns the angler's hand with it)
        self.rum_t = 0.0             # the pad's next rumble
        self.slowmo = 0.0            # a breath of slow motion as a catch clears the water
        self.drip_t = 0.0
        self.ring_t = 1.0            # the next little ring the resting bobber sends out
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
            self.pressing = True               # a tap twitches the bobber; holding reels in (see update)
            self.hold_t = 0.0
        elif st == 'bite':
            self.hook()
        elif st == 'fight' and self.mg:
            self.mg.press()

    def release(self):
        if self.state == 'charging':
            self.cast(self.power)
        elif self.state == 'waiting' and self.pressing:
            self.pressing = False
            if self.hold_t < HOLD_REEL:
                self.twitch()

    def twitch(self):
        """Give the bobber a little tug toward you. A few twitches draw fish in, twitching on a nibble makes
        it bite, and too many spook them."""
        g = self.g
        x, y = self.dst
        persp = 0.5 + (y - HORIZON) / 170
        if x > self.tip[0] + 30:
            x -= 2 + 2 * persp
            y = min(y + 0.8 * persp, 322)
        self.dst = (x, y)
        self.twitch_anim = 0.3
        self.twitches += 1
        g.world.ripple(x, y, 4 + 4 * persp, 14, 170)
        g.world.splash(x, y, 3, 0.3 + 0.2 * persp)
        g.audio.play('plop', 0.3, x / W)
        junk = self.catch['spec'].get('junk')
        if self.nib_anim > 0:
            # a twitch right on a nibble: it can't resist
            self.bite_at = min(self.bite_at, self.t + 0.45)
            self.nibbles = []
            if not junk and self.shadow is None:
                self._spawn_shadow()
            g.toast("A twitch on the nibble! Here it comes...", (90, 150, 190))
        elif self.twitches <= len(TWITCH_CUT):
            self.bite_at = max(self.t + 0.7, self.bite_at - TWITCH_CUT[self.twitches - 1])
        else:
            self.bite_at += 2.5
            self.nibbles = [n + 2.5 for n in self.nibbles]
            self.flee_shadow()
            g.toast('Easy! Too much twitching spooks them.', (200, 120, 100))

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
        self.school = not self.hot and w.take_school(x, y, persp)
        self.pressing = False
        self.twitches = 0
        if self.hot:
            g.toast('Right on the bubbles! Something is down there...', (90, 150, 190))
        elif self.school:
            g.toast("Into the school! They're feeding.", (90, 150, 190))
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
        elif self.school:
            base *= 0.5
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
            if getattr(self, 'school', False) and r >= 2:
                w *= 1.3
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
        g.world.ripple(x, y, 8, 10)
        g.audio.play('bloop', 0.65, x / W)
        g.audio.play('bite', 0.45, x / W)
        self._buzz(0.85, 0.5, 260)
        g.on_bite()

    def hook(self):
        g = self.g
        spec = self.catch['spec']
        g.use_bait()
        g.audio.play('hook', 0.6)
        self._buzz(0.6, 0.3, 160)
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
        self.pressing = False
        self.fdir = 1.0 if self.rng.random() < 0.5 else -1.0
        if not self.shadow or self.shadow['mode'] != 'approach':
            self._spawn_shadow()             # so the fish is always there to see in the water
        self.shadow['a'] = max(self.shadow['a'], 0.6)
        g.world.splash(self.bob[0], self.bob[1], 6 + spec['rarity'] * 2, 0.8 + spec['strength'] * 0.6)
        g.shake(1.2 + spec['strength'] * 1.6)

    def start_landing(self, pos):
        g = self.g
        self.mg = None
        self.leap_h = 0.0
        self.state = 'landing'
        self.t = 0
        self.fly_from = tuple(pos)
        self.fly_pos = list(pos)
        spec = self.catch['spec']
        r = 0 if spec.get('junk') else spec['rarity']
        self.land_dur = 0.7 if r == 0 else 0.8 + (0.25 if r >= 3 else 0.0)
        if r:
            self.slowmo = 0.14 + 0.04 * r       # the world holds its breath as it breaks the surface
            self._buzz(0.5 + 0.08 * r, 0.25, 240)
        g.world.splash(pos[0], pos[1], 14 + r * 4, 1.2 + r * 0.12)
        g.world.ripple(pos[0], pos[1], 16)
        g.world.ripple(pos[0], pos[1], 9, 10)
        if r >= 2:
            from data import RARITY_COLORS
            g.world.sparkles(pos[0], pos[1] - 6, 6 + r * 3, RARITY_COLORS[r], 10)
        if r:
            g.shake(0.8 + r * 0.4)
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
    def _buzz(self, low, high, ms):
        """A one-off rumble (the steady fight rumble waits until it's done)."""
        if self.g.rumble(low, high, ms):
            self.rum_t = ms / 1000.0

    def update(self, dt):
        g = self.g
        if self.slowmo > 0:
            self.slowmo -= dt
            dt *= 0.3
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
        elif st == 'waiting' and self.pressing and self.hold_t + dt >= HOLD_REEL:
            self.pressing = False
            g.toast('You reel in the line.', (150, 140, 130))
            self.flee_shadow()
            self.to_reel_back()
        elif st == 'waiting':
            target = -40
            if self.pressing:
                self.hold_t += dt
            if getattr(g, 'spot', 'dock') == 'creek':
                # the current carries the bobber downstream (to the right) until the line pulls tight
                self.dst = (min(self.dst[0] + CREEK_DRIFT * dt, min(628, self.drift_max)), self.dst[1])
            x, y = self.dst
            self.nib_anim = max(0, self.nib_anim - dt)
            self.twitch_anim = max(0.0, self.twitch_anim - dt)
            dip = 3.5 * math.sin(math.pi * min(1.0, self.nib_anim / 0.3)) if self.nib_anim > 0 else 0
            hop = -math.sin(math.pi * self.twitch_anim / 0.3) * 2.0 if self.twitch_anim > 0 else 0
            if self.twitch_anim > 0:
                target = -46
            self.bob = [x, y + math.sin(self.t * 2.6) * 0.7 + dip + hop]
            self.ring_t -= dt
            if self.ring_t <= 0:
                # the bobber rocking on the water sends out little rings
                self.ring_t = self.rng.uniform(1.6, 3.0)
                persp = 0.5 + (y - HORIZON) / 170
                g.world.ripple(x, y, 3 + 4 * persp, 6, 80)
            if self.nibbles and self.t >= self.nibbles[0]:
                self.nibbles.pop(0)
                self.nib_anim = 0.3
                g.world.ripple(x, y, 6, 10, 120)
                g.audio.play('nibble', 0.5, x / W)
                self._buzz(0.0, 0.35, 70)
            if not self.catch['spec'].get('junk') and self.shadow is None and self.t >= self.bite_at - 2.4:
                self._spawn_shadow()
            if self.t >= self.bite_at:
                self.bite()
        elif st == 'bite':
            target = -42
            x, y = self.dst
            self.bob = [x, y + min(9.0, self.t * 70)]       # yanked clean under
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
            dur = getattr(self, 'land_dur', 0.7)
            k = min(1.0, self.t / dur)
            if dur > 0.9:
                k = k * k * (3 - 2 * k)          # rare fish hang in the air for a moment at the top
            fx, fy = self.fly_from
            tx, ty = HAND[0] + 10, HAND[1] - 26
            self.fly_pos = [fx + (tx - fx) * k, fy + (ty - fy) * k - math.sin(math.pi * k) * (40 + dur * 14)]
            self.bob = list(self.fly_pos)
            self.drip_t -= dt
            if self.drip_t <= 0 and k < 0.9:
                # water running off it on the way in
                self.drip_t = 0.035
                px, py = self.fly_pos
                floor = fy + (ty + 8 - fy) * min(1.0, k + 0.15)
                g.world.particles.append(dict(x=px + self.rng.uniform(-3, 3), y=py + 2, vx=self.rng.uniform(-6, 6),
                                              vy=self.rng.uniform(0, 10), g=160, life=1.0, max=1.0,
                                              col=(214, 232, 244), kind='drop', floor=max(py + 4, floor)))
            target = -95
            rate = 10
            if k >= 1:
                self.state = 'caught'
                self.t = 0
                g.world.splash(tx, ty + 4, 6, 0.5)        # drips as you grab it
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
        self._feel(dt)

    def _feel(self, dt):
        """The line's own sounds, the pad's rumble and the reel handle turning, every frame."""
        g = self.g
        st = self.state
        reel = drag = hum = pitch = 0.0
        pan = self.bob[0] / W if self.bob else 0.5
        turning = False
        if st == 'casting':
            drag = 0.2                             # line peeling off the spool
        elif st in ('reel_back', 'landing'):
            reel, turning = 0.7, True
        elif st == 'waiting' and self.pressing and self.hold_t > 0.12:
            reel, turning = 0.55, True
        elif st == 'fight' and self.mg:
            mg = self.mg
            hold = g.holding
            sulk = getattr(mg, 'sulk', 0) > 0
            if not mg.leap:
                if mg.in_arc and (hold or not sulk):
                    reel, turning = (0.9 if hold else 0.5), True
                if mg.lunge > 0:
                    drag = 0.95                    # it runs, and the drag sings
                elif not mg.in_arc:
                    drag = 0.38
                elif getattr(mg, 'dive', 0) > 0:
                    drag = 0.25
            hum = clamp((mg.strain - 0.3) / 0.6) * 0.4
            pitch = clamp((mg.strain - 0.55) / 0.45)
            if self.fish_pos:
                pan = self.fish_pos[0] / W
            self.rum_t -= dt
            if self.rum_t <= 0:
                self.rum_t = 0.1
                if mg.leap:
                    g.rumble(0.05, 0.0, 150)
                else:
                    low = 0.1 + 0.45 * mg.strain + (0.4 if mg.lunge > 0 else 0.0)
                    high = max(0.0, mg.strain - 0.6) * 1.6 + (0.3 if mg.over_t > 0 else 0.0)
                    g.rumble(low, high, 150)
        if turning:
            self.crank += dt * (17 if (g.holding or st != 'fight') else 9)
        g.audio.set_line(reel, drag, hum, pitch, pan)

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
                           w=(5 + sz * 22) * persp, h=(2 + sz * 6) * persp, a=0.0, mode='approach', fx=side, sz=sz)

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
                self._buzz(1.0, 0.4, 280)
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
                g.shake(0.7)
            elif k == 'dive':
                w.splash(fx, fy, 10, 0.9)
                w.ripple(fx, fy, 12)
                w.ripple(fx, fy, 7, 10)
                g.audio.play('splash_small', 0.6, fx / W)
                g.shake(1.2)
            elif k == 'surface':
                w.splash(fx, fy, 7, 0.7)
                w.ripple(fx, fy, 10)
                g.audio.play('splash_small', 0.5, fx / W)
            elif k == 'sulk':
                w.ripple(fx, fy, 8, 8, 200)
                g.audio.play('nibble', 0.5, fx / W)
            elif k == 'unsulk':
                w.splash(fx, fy, 5, 0.6)
            elif k == 'turn':
                w.splash(fx, fy, 6, 0.7)
                w.ripple(fx, fy, 8, 18)
                g.shake(1.0)
            elif k == 'second':
                self._buzz(1.0, 0.7, 420)
                w.splash(fx, fy, 20, 1.4)
                w.ripple(fx, fy, 18)
                w.ripple(fx, fy, 11, 12)
                g.audio.play('warn', 0.8, fx / W)
                g.audio.play('splash', 0.7, fx / W)
                g.shake(3.5)
            elif k == 'stage':
                self._buzz(1.0, 0.7, 420)
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
            g.audio.play('twang', 0.7, fx / W)
            self._buzz(1.0, 1.0, 350)
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
        if getattr(mg, 'sulk', 0) > 0:
            tx, ty = fx, fy                      # dead still on the bottom
        k = min(1, dt * (14 if mg.lunge > 0 else 6))
        nx, ny = fx + (tx - fx) * k, fy + (ty - fy) * k
        vx = (nx - fx) / max(dt, 1e-3)
        self.fspeed += (abs(vx) - self.fspeed) * min(1, dt * 8)
        if abs(vx) > 2:
            self.fdir = 1.0 if vx > 0 else -1.0
        self.fish_pos = [nx, ny]
        L = mg.leap
        if L:
            lk = min(1.0, L['t'] / 1.25)
            self.leap_h = math.sin(math.pi * lk) * 30 * persp
        else:
            self.leap_h = max(0.0, self.leap_h - dt * 80)
        self.bob = [self.fish_pos[0], self.fish_pos[1] - self.leap_h]
        self.splash_t -= dt
        diving = getattr(mg, 'dive', 0) > 0
        if self.splash_t <= 0 and not L:
            busy = mg.lunge > 0 or mg.warn > 0 or getattr(mg, 'tell', 0) > 0
            self.splash_t = 0.18 if busy else 0.35 if diving else 0.5
            if diving:
                # bubbles coming up from deep down
                w.particles.append(dict(x=self.fish_pos[0] + self.rng.uniform(-3, 3) * persp, y=self.fish_pos[1],
                                        vx=0, vy=-6, g=0, life=0.5, max=0.5, col=(226, 242, 250), kind='spark'))
            else:
                w.ripple(self.fish_pos[0], self.fish_pos[1], 6 + 6 * persp, 16, 140)
            if busy and not diving:
                w.splash(self.fish_pos[0], self.fish_pos[1], 3, 0.5)
                if mg.lunge > 0:
                    w.splash(self.fish_pos[0] - self.fdir * 4 * persp, self.fish_pos[1], 3, 0.7)   # tail slap
        # a tight line flicks off water drops
        self.spray_t -= dt
        if mg.strain > 0.8 and self.spray_t <= 0:
            self.spray_t = 0.12
            tx_, ty_ = self.tip
            q = self.rng.uniform(0.35, 0.95)
            w.splash(tx_ + (self.fish_pos[0] - tx_) * q, ty_ + (self.fish_pos[1] - ty_) * q, 1, 0.25)

    # ------------------------------------------------------------ drawing
    def draw_shadow(self, frame):
        s = self.shadow
        if not s or s['a'] <= 0.02 or not self.catch:
            return
        spec = self.catch['spec']
        mg = self.mg if self.state == 'fight' else None
        w = s['w'] * 1.25
        if self.state == 'fight':
            w = (5 + s.get('sz', 0.4) * 22) * (0.5 + (s['y'] - HORIZON) / 170) * 1.25   # grows as it comes in
        alpha = 120 * s['a']
        flip = s['fx'] < 0
        x, y = s['x'], s['y']
        if mg:
            flip = self.fdir < 0
            if getattr(mg, 'dive', 0) > 0:
                w *= 0.7                      # deep down: smaller and fainter
                alpha = 45
            else:
                alpha = 150
            if mg.lunge > 0 or mg.warn > 0:
                x += math.sin(self.t * 50) * 1.2
        elif s['mode'] == 'approach':
            flip = (self.bob[0] if self.bob else x) < x
        sil = silhouette(spec, w, flip)
        if self.state == 'fight' and getattr(mg, 'sulk', 0) <= 0:
            # the tail beats: squash the shadow a little in time
            k = 1 + 0.08 * math.sin(self.t * (14 if mg and mg.lunge > 0 else 7))
            sil = pygame.transform.scale(sil, (max(2, int(sil.get_width() * k)), sil.get_height()))
        sil.set_alpha(int(alpha))
        frame.blit(sil, (int(x - sil.get_width() / 2), int(y - sil.get_height() / 2)))

    def draw_water(self, near):
        st = self.state
        if self.bob is None:
            return
        x, y = int(self.bob[0]), int(self.bob[1])
        if st in ('casting', 'waiting', 'reel_back'):
            if st == 'waiting':
                wy = int(round(self.dst[1]))
                persp = 0.5 + (wy - HORIZON) / 170
                draw_bobber(near, x, y + 1, persp, wy)
                hw = 2 + int(2 * persp)
                near.fill((230, 240, 250, 150), (x - hw, wy, hw * 2 + 1, 1))
            else:
                persp = 0.5 + (y - HORIZON) / 170 if y > HORIZON else 1.0
                draw_bobber(near, x, y, max(persp, 0.8 if st == 'casting' else persp))
        elif st == 'bite':
            # pulled under: a swirl and a boil of bubbles where it was
            wx, wy = int(self.dst[0]), int(round(self.dst[1]))
            persp = 0.5 + (wy - HORIZON) / 170
            if self.t < 0.12:
                draw_bobber(near, wx, y + 1, persp, wy)
            rw = int((4 + self.t * 10) * persp) + 2
            pygame.draw.ellipse(near, (240, 248, 255, 190), (wx - rw, wy - rw // 3, rw * 2, max(2, rw * 2 // 3)), 1)
            for i in range(4):
                a = self.t * 7 + i * 1.57
                bx = wx + int(math.cos(a) * 2 * persp)
                by = wy - int((self.t * 9 + i * 1.3) % 4)
                near.set_at((bx, by), (236, 246, 255, 230))
        elif st == 'fight':
            if self.leap_h > 1 and self.fish_pos:
                x, y = int(self.fish_pos[0]), int(self.fish_pos[1])
            persp = 0.5 + (y - HORIZON) / 170
            mg = self.mg
            diving = mg is not None and getattr(mg, 'dive', 0) > 0
            sulking = mg is not None and getattr(mg, 'sulk', 0) > 0
            r = int(3 + 3 * persp)
            if not diving:
                for i in range(4):
                    a = self.t * (4 if sulking else 9) + i * 1.6
                    near.set_at((x + int(math.cos(a) * r), y + int(math.sin(a) * r * 0.4)), (240, 248, 255, 220))
                near.fill((255, 255, 255, 180), (x - r, y, r * 2, 1))
            if mg and self.leap_h <= 1 and not diving and not sulking and self.fish_pos:
                fx, fy = self.fish_pos
                d = self.fdir
                busy = mg.lunge > 0 or mg.warn > 0
                # its back fin cuts the surface, with a wake fanning out behind
                if busy or self.fspeed > 6 or math.sin(self.t * 3.1) > 0.2:
                    fh = max(2, int((2 + 2 * persp) * (1.4 if busy else 1.0)))
                    bx = int(fx - d * 2 * persp)
                    pygame.draw.polygon(near, (40, 54, 64, 235),
                                        [(bx - d * 3 * persp, fy), (bx + d * 2 * persp, fy), (bx - d * persp, fy - fh)])
                    near.set_at((int(bx - d * persp), int(fy - fh)), (200, 216, 226, 230))
                if self.fspeed > 4 or busy:
                    ln = int((5 + min(14, self.fspeed * 0.5)) * persp)
                    for sgn in (-1, 1):
                        pygame.draw.line(near, (230, 242, 250, 150), (int(fx - d * 3 * persp), int(fy)),
                                         (int(fx - d * (3 * persp + ln)), int(fy + sgn * ln * 0.25)))

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
                k = 0.42
                small = pygame.transform.scale(spr, (int(sw * k), int(spr.get_height() * k)))
                rot = pygame.transform.rotate(small, math.sin(self.t * 25) * 35)
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
        shiver = max(0.0, strain - 0.55) * 2.4
        if st == 'fight' and self.mg and (self.mg.lunge > 0 or self.mg.warn > 0):
            shiver += 0.8
        pts = []
        for i in range(13):
            s = i / 12
            px = (1 - s) ** 2 * tx + 2 * (1 - s) * s * mx + s * s * bx
            py = (1 - s) ** 2 * ty + 2 * (1 - s) * s * my + s * s * by
            if shiver:
                py += math.sin(math.pi * s) * math.sin(self.t * 55 + s * 9) * shiver
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
