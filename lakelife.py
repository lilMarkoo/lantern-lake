"""Little lives around your line while you fish: a fish jumping far out, rings where one rises to take a fly,
a damselfly that comes to rest on your bobber on a still summer day, the reeds rustling, a kingfisher that
comes to sit on the dock post and sometimes dives, and Biscuit pricking up at every nibble.

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
        self.kf = None           # the kingfisher: dict(state, x, y, t, ...)
        self.kf_t = 40.0         # seconds until it might come by
        self.nib_seen = False

    # ------------------------------------------------------------ update
    def update(self, g, dt):
        rng = self.rng
        env = g.env
        import seasons
        frozen = seasons.frozen(g)
        dusky = env.phase in ('dawn', 'dusk')
        rain = env.weather in ('rain', 'storm')
        w = g.world
        rise = rising(g)
        if rise and not g.stats.get('rise_told'):
            g.stats['rise_told'] = True
            g.toast('The evening rise! Fish are feeding at the surface: quicker bites, better fish.', (220, 150, 90))
        # a fish jumping clear of the water, far out
        self.jump_t -= dt * (3.0 if rise else 1.7 if dusky else 1.0)
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
        self.rise_t -= dt * (3.0 if rise else 1.5 if dusky else 1.0) * (0.6 if rain else 1.0)
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
        self._kingfisher(g, dt, frozen, rain)
        self._biscuit(g)

    def _biscuit(self, g):
        """Biscuit watches the bobber too: a nibble makes her sit up, tail going."""
        f = g.fishing
        nib = f.state == 'waiting' and f.nib_anim > 0
        if nib and not self.nib_seen and getattr(g, 'spot', 'dock') == 'dock':
            c = g.cat
            if not c.get('sleep'):
                c['excited'] = max(c['excited'], 0.9)
        self.nib_seen = nib

    PERCH = (257, 242)

    def _kingfisher(self, g, dt, frozen, rain):
        rng = self.rng
        env = g.env
        f = g.fishing
        k = self.kf
        home = getattr(g, 'spot', 'dock') == 'dock' and g.overlay in (None, 'catch')
        if k is None:
            quiet = f.state in ('idle', 'waiting')
            self.kf_t -= dt * (1.6 if f.state == 'waiting' else 1.0)
            if self.kf_t <= 0:
                self.kf_t = rng.uniform(70, 150)
                if (home and quiet and not frozen and not rain and env.nf < 0.35 and env.season != 3
                        and g.mode == 'play'):
                    side = rng.choice((1, 1, -1))
                    self.kf = dict(state='in', t=0.0, x=self.PERCH[0] + side * 170, y=HORIZON + 6, side=side,
                                   x0=self.PERCH[0] + side * 170, y0=HORIZON + 6, stay=rng.uniform(7, 14),
                                   dives=0, fish=False)
                    g.audio.play('bird%d' % rng.randrange(4), 0.35, 0.7)
            return
        k['t'] += dt
        st = k['state']
        px, py = self.PERCH
        if st != 'out' and (not home or f.state in ('fight', 'landing') or g.mode != 'play'):
            k.update(state='out', t=0.0, x0=k['x'], y0=k['y'])
            return
        if st == 'in':
            q = min(1.0, k['t'] / 2.4)
            e = q * q * (3 - 2 * q)
            k['x'] = k['x0'] + (px - k['x0']) * e
            k['y'] = k['y0'] + (py - k['y0']) * e - math.sin(math.pi * q) * 14 + math.sin(k['t'] * 9) * 1.2
            if q >= 1:
                k.update(state='perch', t=0.0, x=px, y=py)
                g.toast_few('kingfisher', 'A kingfisher has come to sit on your dock post.', (60, 120, 170), 2)
        elif st == 'perch':
            if k['t'] > k['stay']:
                if k['dives'] < 2 and rng.random() < 0.65:
                    tx = rng.uniform(270, 330)
                    ty = rng.uniform(296, 330)
                    k.update(state='dive', t=0.0, x0=px, y0=py, tx=tx, ty=ty)
                else:
                    k.update(state='out', t=0.0, x0=k['x'], y0=k['y'])
                    g.audio.play('bird%d' % rng.randrange(4), 0.3, 0.7)
        elif st == 'dive':
            q = min(1.0, k['t'] / 0.45)
            k['x'] = k['x0'] + (k['tx'] - k['x0']) * q
            k['y'] = k['y0'] + (k['ty'] - k['y0']) * q * q
            if q >= 1:
                w = g.world
                w.splash(k['tx'], k['ty'], 6, 0.6)
                w.ripple(k['tx'], k['ty'], 6, 12, 150)
                g.audio.play('plip', 0.35, k['tx'] / W)
                g.audio.play('splash_small', 0.2, k['tx'] / W)
                k.update(state='under', t=0.0, fish=rng.random() < 0.6)
                c = g.cat
                if not c.get('sleep'):
                    c['excited'] = max(c['excited'], 1.4)
        elif st == 'under':
            if k['t'] > 0.35:
                g.world.splash(k['tx'], k['ty'], 4, 0.45)
                k.update(state='up', t=0.0, x0=k['tx'], y0=k['ty'], dives=k['dives'] + 1)
        elif st == 'up':
            q = min(1.0, k['t'] / 0.9)
            k['x'] = k['x0'] + (px - k['x0']) * q
            k['y'] = k['y0'] + (py - k['y0']) * q - math.sin(math.pi * q) * 10
            if q >= 1:
                k.update(state='perch', t=0.0, x=px, y=py, stay=rng.uniform(4, 9))
        else:  # out
            k['x'] += k['side'] * 80 * dt
            k['y'] -= 26 * dt
            if k['t'] > 2.5:
                self.kf = None

    def draw_bird(self, near, t):
        """The kingfisher (drawn over the dock, so it can sit on top of the post)."""
        k = self.kf
        if not k or k['state'] == 'under':
            return
        import pygame
        x, y = int(round(k['x'])), int(round(k['y']))
        blue, blue_d, orange, white, beak = (40, 150, 210), (26, 96, 160), (236, 132, 56), (246, 240, 228), (40, 34, 36)
        st = k['state']
        if st == 'perch':
            d = -1                                   # faces out over the water
            bob = 1 if int(t * 1.5) % 4 == 0 else 0  # a little head bob now and then
            near.fill(blue_d, (x - 1, y - 2, 2, 2))            # tail down the back
            near.fill(blue, (x - 1, y - 5, 3, 3))              # back and wing
            near.fill(orange, (x - 1 + (1 if d < 0 else 0), y - 3, 2, 2))   # chest
            near.fill(blue, (x - 1, y - 7 + bob, 3, 2))        # head
            near.set_at((x + d, y - 6 + bob), white)           # cheek
            near.fill(beak, (x + 2 * d - (2 if d < 0 else 0), y - 6 + bob, 3, 1))
            if k.get('fish') and k['dives']:
                near.set_at((x + 3 * d, y - 5 + bob), (200, 210, 220))   # a minnow in its beak
            near.set_at((x, y), (170, 60, 50))                # feet
            return
        d = 1 if (st == 'out' and k['side'] > 0) or (st == 'in' and k['side'] < 0) else -1
        if st in ('dive',):
            near.fill(blue, (x - 1, y - 3, 2, 3))
            near.set_at((x, y), beak)
            near.set_at((x, y + 1), beak)
            near.set_at((x - 1, y - 4), blue_d)
            return
        flap = int(t * 16) % 2
        near.fill(blue, (x - 2, y - 1, 5, 2))
        near.fill(orange, (x - 1, y, 3, 1))
        near.fill(beak, (x + 3 * d - (1 if d < 0 else 0), y - 1, 2, 1))
        near.set_at((x - 3 * d, y - 1), blue_d)
        if flap:
            near.set_at((x, y - 2), blue_d)
            near.set_at((x - d, y - 3), blue_d)
        else:
            near.set_at((x, y + 1), blue_d)
            near.set_at((x - d, y + 2), blue_d)
        if k.get('fish') and st == 'up':
            near.set_at((x + 4 * d, y), (200, 210, 220))

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


def rising(g):
    """The evening rise: at dusk on the lake, fish come up to feed. Quicker bites, better fish, more rings."""
    env = g.env
    if env.phase != 'dusk' or g.place != 'lake' or env.weather == 'storm':
        return False
    import coast
    import seasons
    return not coast.at_coast(g) and not seasons.frozen(g)


# ---------------------------------------------------------------- the dock fills up as you fish
# (id, test, the line you get the first time)
DOCK = (
    ('bucket', lambda tot, sp: tot >= 5, 'A bait bucket of your own now sits on the dock.'),
    ('board', lambda tot, sp: tot >= 15, 'You nailed a tally board to the dock post.'),
    ('sign', lambda tot, sp: sp >= 8, 'Eight kinds of fish! You carved a little fish sign for the post.'),
    ('rope', lambda tot, sp: tot >= 30, 'A proper coil of rope and a net, drying on the dock.'),
    ('pots', lambda tot, sp: tot >= 50, 'Fifty fish! Flower pots for the dock, to celebrate.'),
    ('chime', lambda tot, sp: tot >= 80, 'A wind chime of old lures now sings on the end post.'),
)


def _species(g):
    from data import FISH_BY_ID
    return sum(1 for k in g.journal if k in FISH_BY_ID)


def dock_props(g):
    tot, sp = g.total, _species(g)
    return [d[0] for d in DOCK if d[1](tot, sp)]


def dock_progress(g):
    """After each catch: anything new for the dock gets one line, said once."""
    have = dock_props(g)
    if 'dock' not in g.stats:
        g.stats['dock'] = list(have)       # an older save: what's already earned arrives quietly
        return
    for pid, _, line in DOCK:
        if pid in have and pid not in g.stats['dock']:
            g.stats['dock'].append(pid)
            g.toast(line, (150, 120, 80))


def draw_dock(near, g, t):
    import pygame
    import math as m
    have = dock_props(g)
    if not have:
        return
    deck = 286
    if 'bucket' in have:
        x = 190
        pygame.draw.rect(near, (110, 120, 128), (x, deck - 6, 7, 6))
        pygame.draw.rect(near, (80, 88, 96), (x, deck - 6, 7, 6), 1)
        pygame.draw.line(near, (150, 160, 168), (x, deck - 6), (x + 6, deck - 6))
        pygame.draw.arc(near, (70, 76, 84), (x, deck - 10, 7, 8), 0, m.pi)
        near.set_at((x + 2, deck - 7), (200, 120, 110))           # a worm, peeking out
    if 'board' in have:
        bx, by = 106, 252
        near.fill((150, 112, 74), (bx, by, 11, 8))
        pygame.draw.rect(near, (96, 70, 48), (bx, by, 11, 8), 1)
        marks = min(g.total, 40) // 5
        for i in range(min(marks, 4)):                              # little groups of five tally marks
            for j in range(4):
                near.set_at((bx + 2 + i * 2 + (j % 2), by + 2 + j // 2 * 3 - (j // 2)), (60, 44, 30))
        if g.total >= 25:
            near.set_at((bx + 9, by + 4), (220, 180, 90))           # a gold star, for luck
    if 'sign' in have:
        sx, sy = 106, 264
        pygame.draw.line(near, (80, 64, 50), (sx, sy - 2), (sx + 3, sy))
        pygame.draw.ellipse(near, (196, 150, 96), (sx + 1, sy, 10, 5))
        pygame.draw.polygon(near, (196, 150, 96), [(sx + 10, sy + 2), (sx + 14, sy), (sx + 14, sy + 5)])
        near.set_at((sx + 3, sy + 1), (60, 44, 30))
    if 'rope' in have:
        rx = 124
        for i, w in enumerate((9, 7, 5)):
            pygame.draw.ellipse(near, (186, 156, 104) if i % 2 == 0 else (160, 130, 86),
                                (rx - w // 2, deck - 3 - i, w, 3))
        for i in range(5):                                          # a net hung over the left post
            near.set_at((101 - i % 2, 258 + i * 2), (130, 140, 120))
            near.set_at((100 - (i + 1) % 2, 259 + i * 2), (110, 120, 100))
    if 'pots' in have:
        for px, col in ((112, (230, 110, 120)), (250, (250, 200, 90))):
            pygame.draw.polygon(near, (176, 96, 66), [(px - 3, deck - 5), (px + 3, deck - 5), (px + 2, deck), (px - 2, deck)])
            pygame.draw.line(near, (110, 150, 80), (px, deck - 5), (px, deck - 8))
            near.set_at((px - 1, deck - 9), col)
            near.set_at((px + 1, deck - 9), col)
            near.set_at((px, deck - 10), col)
            near.set_at((px, deck - 9), (255, 236, 160))
    if 'chime' in have:
        cx, cy = 258, 245
        wind = getattr(g.env, 'wind', 0.3)
        pygame.draw.line(near, (110, 90, 70), (cx, cy), (cx + 5, cy))
        for i in range(3):
            sw = m.sin(t * (2.2 + i * 0.7) + i) * (0.6 + wind * 1.6)
            x0 = cx + 1 + i * 2
            x1 = x0 + sw
            pygame.draw.line(near, (150, 150, 140), (x0, cy), (x1, cy + 4 + i))
            near.set_at((int(round(x1)), cy + 5 + i), ((220, 90, 80), (90, 170, 210), (240, 200, 90))[i])


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


def draw_bird(near, g, t):
    ll = getattr(g, 'lakelife', None)
    if ll is not None and g.place != 'town':
        ll.draw_bird(near, t)
