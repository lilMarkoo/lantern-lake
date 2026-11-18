"""Little lives around your line while you fish: a fish jumping far out, rings where one rises to take a fly,
a damselfly that comes to rest on your bobber on a still summer day, the reeds rustling.

Nothing here changes what bites. It's only there so the lake feels alive while you wait."""
import math
import random

from art import W, HORIZON

JUMP = (9.0, 22.0)       # seconds between fish jumping far out
RISE = (5.0, 12.0)       # ...and fish rising
RUSTLE = (7.0, 16.0)


def persp(y):
    return 0.5 + (y - HORIZON) / 170


class LakeLife:
    def __init__(self):
        self.rng = random.Random()
        self.jumps = []
        self.jump_t = 6.0
        self.rise_t = 3.0
        self.rustle_t = 8.0
        self.fly = None          # the damselfly: dict(state, x, y, t, side)
        self.fly_cast = None     # the cast it already decided about (one roll per cast)

    # ------------------------------------------------------------ update
    def update(self, g, dt):
        rng = self.rng
        env = g.env
        import seasons
        frozen = seasons.frozen(g)
        dusky = env.phase in ('dawn', 'dusk')
        rain = env.weather in ('rain', 'storm')
        w = g.world
        # a fish jumping clear of the water, far out
        self.jump_t -= dt * (1.7 if dusky else 1.0)
        if self.jump_t <= 0:
            self.jump_t = rng.uniform(*JUMP)
            if not frozen:
                y = rng.uniform(HORIZON + 10, HORIZON + 70)
                x = rng.uniform(320, W - 20)
                p = persp(y)
                self.jumps.append(dict(x=x, y=y, t=0.0, dur=0.45 + 0.2 * p, h=(6 + 10 * p), d=rng.choice((-1, 1)),
                                       p=p))
                w.splash(x, y, 3, 0.35 * p)
                w.ripple(x, y, 5 * p + 2, 8, 120)
                g.audio.play('splash_small', 0.08 + 0.12 * p, x / W)
        for j in self.jumps:
            j['t'] += dt
            if j['t'] >= j['dur'] and not j.get('down'):
                j['down'] = True
                x = j['x'] + j['d'] * 8 * j['p']
                w.splash(x, j['y'], 4, 0.4 * j['p'])
                w.ripple(x, j['y'], 7 * j['p'] + 3, 9, 140)
                w.ripple(x, j['y'], 4 * j['p'] + 2, 6, 110)
                g.audio.play('splash_small', 0.1 + 0.15 * j['p'], x / W)
        self.jumps = [j for j in self.jumps if j['t'] < j['dur'] + 0.1]
        # rings where a fish rises (more of them on a calm evening, none under ice)
        self.rise_t -= dt * (1.5 if dusky else 1.0) * (0.6 if rain else 1.0)
        if self.rise_t <= 0:
            self.rise_t = rng.uniform(*RISE)
            if not frozen:
                y = rng.uniform(HORIZON + 14, 330)
                x = rng.uniform(290, W - 10)
                p = persp(y)
                w.ripple(x, y, 5 * p + 2, 6, 130)
                w.ripple(x, y, 3 * p + 1, 4, 100)
                g.audio.play('plip', 0.12 + 0.2 * p, x / W)
        # the reeds stirring
        self.rustle_t -= dt * (1 + env.wind)
        if self.rustle_t <= 0:
            self.rustle_t = rng.uniform(*RUSTLE)
            if not frozen:
                g.audio.play('rustle', 0.2 + 0.2 * min(1.0, env.wind), rng.uniform(0.6, 0.95))
        self._damselfly(g, dt)

    def _damselfly(self, g, dt):
        f = g.fishing
        env = g.env
        fl = self.fly
        waiting = f.state == 'waiting' and f.bob is not None
        if fl is None:
            # one roll per cast: on a fine spring or summer day, a damselfly may come and sit on the bobber
            if waiting and f.t > 3.5 and self.fly_cast is not f.catch:
                self.fly_cast = f.catch
                fine = env.season in (0, 1) and env.nf < 0.3 and env.weather in ('clear', 'cloudy')
                if fine and self.rng.random() < 0.4 and getattr(g, 'spot', 'dock') in ('dock', 'cove', 'creek'):
                    side = self.rng.choice((-1, 1))
                    self.fly = dict(state='in', x=f.bob[0] + side * 60, y=f.bob[1] - 30, t=0.0, side=side)
            return
        fl['t'] += dt
        spooked = (not waiting or f.twitch_anim > 0 or f.nib_anim > 0 or f.shadow is not None)
        if fl['state'] != 'out' and (spooked or (fl['state'] == 'sit' and fl['t'] > 7)):
            fl['state'], fl['t'] = 'out', 0.0
        if fl['state'] in ('in', 'sit'):
            p = persp(f.dst[1]) if waiting else 1.0
            tx, ty = f.bob[0] + 1, f.bob[1] - (8 if p > 0.74 else 6 if p > 0.56 else 4)
            if fl['state'] == 'in':
                tx += math.sin(fl['t'] * 5) * 3
                ty += math.sin(fl['t'] * 7) * 2 - 2
                k = min(1.0, dt * 2.5)
                fl['x'] += (tx - fl['x']) * k
                fl['y'] += (ty - fl['y']) * k
                if fl['t'] > 2.2 and abs(tx - fl['x']) + abs(ty - fl['y']) < 3:
                    fl['state'], fl['t'] = 'sit', 0.0
            else:
                fl['x'], fl['y'] = tx, ty
        else:
            fl['x'] += fl['side'] * 70 * dt
            fl['y'] -= 30 * dt
            if fl['t'] > 1.5:
                self.fly = None

    # ------------------------------------------------------------ draw (on the world's near layer)
    def draw(self, near, t):
        for j in self.jumps:
            k = min(1.0, j['t'] / j['dur'])
            p = j['p']
            x = j['x'] + j['d'] * 8 * p * k
            y = j['y'] - math.sin(math.pi * k) * j['h']
            ln = 2 if p < 0.7 else 3
            tilt = int(round((0.5 - k) * 2))
            col = (196, 206, 214)
            for i in range(ln):
                near.set_at((int(x - j['d'] * i), int(y + tilt * (i if j['d'] > 0 else -i) * 0.5)), col)
            near.set_at((int(x - j['d'] * ln), int(y - 1)), (150, 160, 170))
        fl = self.fly
        if fl:
            x, y = int(fl['x']), int(fl['y'])
            body, head = (40, 170, 190), (30, 120, 150)
            wing = (230, 245, 255, 170)
            d = -1 if fl['state'] == 'out' and fl['side'] < 0 else 1
            near.fill(body, (x - 2 if d > 0 else x - 1, y, 4, 1))
            near.set_at((x + 2 * d, y), head)
            if fl['state'] == 'sit' and int(t * 2) % 5:
                near.fill(wing, (x - 1, y - 1, 3, 1))           # wings folded back
            elif int(t * 30) % 2:
                near.set_at((x, y - 1), wing)
                near.set_at((x + d, y - 2), wing)
            else:
                near.set_at((x, y + 1), wing)
                near.set_at((x + d, y + 1), wing)


def get(g):
    ll = getattr(g, 'lakelife', None)
    if ll is None:
        ll = g.lakelife = LakeLife()
    return ll


def update(g, dt):
    if g.place == 'town':
        return
    get(g).update(g, dt)


def draw(near, g, t):
    ll = getattr(g, 'lakelife', None)
    if ll is not None and g.place != 'town':
        ll.draw(near, t)
