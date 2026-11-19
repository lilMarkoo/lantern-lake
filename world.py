"""The lake: time of day, weather, sky, water, foreground, lights and ambient life."""
import math
import random

import pygame

import art
from art import W, H, HORIZON, DECK_Y, lerp_c, mul_c, darken, lighten, add_glow
from data import phase_of
from fishing import cast_point

WAGON_RECT = pygame.Rect(524, 200, 50, 34)     # Wren's houseboat, clickable on wagon days
FW_COLORS = [(255, 120, 120), (255, 210, 110), (140, 220, 255), (180, 255, 150), (230, 150, 255), (255, 255, 230)]

# minute, sky top, sky mid, sky bottom, ambient light
SKY_KEYS = [
    (0, (8, 10, 32), (22, 26, 64), (44, 44, 86), (78, 88, 150)),
    (290, (18, 20, 52), (52, 46, 92), (110, 76, 112), (96, 96, 150)),
    (360, (74, 96, 166), (232, 152, 140), (255, 196, 146), (236, 190, 176)),
    (450, (92, 152, 222), (152, 202, 240), (222, 236, 246), (255, 248, 238)),
    (720, (80, 150, 230), (140, 200, 246), (212, 236, 250), (255, 255, 255)),
    (1020, (92, 142, 216), (172, 192, 232), (242, 222, 202), (255, 244, 228)),
    (1110, (84, 84, 162), (234, 134, 124), (255, 182, 112), (255, 194, 156)),
    (1200, (42, 42, 102), (124, 72, 122), (204, 112, 102), (160, 126, 166)),
    (1290, (12, 14, 42), (30, 30, 72), (60, 50, 92), (80, 90, 152)),
    (1440, (8, 10, 32), (22, 26, 64), (44, 44, 86), (78, 88, 150)),
]


def sample_sky(minute):
    for a, b in zip(SKY_KEYS, SKY_KEYS[1:]):
        if a[0] <= minute <= b[0]:
            t = (minute - a[0]) / (b[0] - a[0])
            t = t * t * (3 - 2 * t)
            return tuple(lerp_c(a[i], b[i], t) for i in range(1, 5))
    return SKY_KEYS[0][1:]


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def grayish(c, k=1.0):
    l = lum(c)
    return (int(l * 0.86 + 22 * k), int(l * 0.88 + 24 * k), int(l * 0.94 + 30 * k))


WEATHER_TARGETS = {
    'clear': dict(cloud=0.22, rain=0, snow=0, fog=0, wind=0.25),
    'cloudy': dict(cloud=0.85, rain=0, snow=0, fog=0, wind=0.45),
    'rain': dict(cloud=1.0, rain=1, snow=0, fog=0, wind=0.7),
    'fog': dict(cloud=0.5, rain=0, snow=0, fog=1, wind=0.1),
    'snow': dict(cloud=0.9, rain=0, snow=1, fog=0, wind=0.35),
}


class Env:
    def __init__(self):
        self.minute = 360.0
        self.day = 1
        self.season = 0
        self.weather = 'clear'
        self.cloud = 0.22
        self.rain = 0.0
        self.snow = 0.0
        self.fog = 0.0
        self.wind = 0.25
        self.compute()

    def settle(self):
        for k, v in WEATHER_TARGETS[self.weather].items():
            setattr(self, k, v)
        self.compute()

    def step(self, dt):
        tg = WEATHER_TARGETS[self.weather]
        for k, v in tg.items():
            cur = getattr(self, k)
            setattr(self, k, cur + (v - cur) * min(1, dt * 0.12))
        self.compute()

    def compute(self):
        top, mid, bot, amb = sample_sky(self.minute)
        base_lum = lum(amb)
        self.nf = max(0.0, min(1.0, (205 - base_lum) / 115))
        over = max(self.cloud * 0.3, self.rain * 0.75, self.snow * 0.62)
        top, mid, bot = (lerp_c(c, grayish(c), over) for c in (top, mid, bot))
        amb = lerp_c(amb, mul_c(amb, (206, 210, 222)), over)
        if self.season == 3:
            amb = mul_c(amb, (236, 242, 255))
        if self.fog > 0.01:
            fogc = mul_c((214, 218, 224), lerp_c(amb, (255, 255, 255), 0.25))
            top = lerp_c(top, fogc, self.fog * 0.45)
            mid = lerp_c(mid, fogc, self.fog * 0.65)
            bot = lerp_c(bot, fogc, self.fog * 0.8)
            self.fog_color = fogc
        else:
            self.fog_color = (214, 218, 224)
        self.sky = (top, mid, bot)
        self.amb = amb
        # foreground stays a little readable at night
        self.near_amb = (max(amb[0], 92), max(amb[1], 98), max(amb[2], 150)) if self.nf > 0 else amb
        self.phase = phase_of(self.minute)
        self.over = over
        # sun: 05:30 -> 19:00
        m = self.minute
        st = (m - 330) / (1140 - 330)
        self.sun_vis = 0 <= st <= 1
        self.sun_t = st
        self.sun = (30 + st * 580, HORIZON + 8 - math.sin(math.pi * max(0, min(1, st))) * 165)
        mt = ((m - 1150) % 1440) / 620.0
        self.moon_vis = mt <= 1
        self.moon = (40 + mt * 560, HORIZON + 8 - math.sin(math.pi * min(1, mt)) * 150)
        self.moon_phase = self.day % 8
        self.full_moon = self.moon_phase in (0, 7)


class World:
    def __init__(self):
        rng = random.Random(11)
        self.rng = random.Random()
        self.t = 0.0

        def ridge(base, amps, step=6, seed=0.0):
            pts = []
            for x in range(-8, W + 16, step):
                y = base
                for i, (a, f) in enumerate(amps):
                    y -= a * math.sin(x * f + seed + i * 1.7)
                pts.append((x, y))
            return pts
        self.mtn_far = ridge(146, [(20, 0.009), (10, 0.023), (4, 0.061)], 6, 1.3)
        self.mtn_near = ridge(168, [(12, 0.013), (6, 0.034), (3, 0.08)], 5, 4.1)
        self.stars = [(rng.randrange(W), rng.randrange(HORIZON - 30), rng.random(), rng.random() * 6.28)
                      for _ in range(150)]
        self.cloud_sprites = [art.make_cloud(rng) for _ in range(8)]
        self.clouds = [dict(x=rng.uniform(-120, W), y=rng.uniform(10, 105), spd=rng.uniform(2, 5),
                            spr=i % 8, th=rng.random(), par=rng.uniform(0.6, 1.0)) for i in range(14)]
        self.gusts = []              # wind ruffling across the water (darker, broken patches drifting by)
        self.gust_t = 2.0
        self.sway = 0.0              # how hard the trees are swaying right now (0..1)
        self.shimmers = [dict(x=rng.uniform(0, W), y=rng.uniform(HORIZON + 2, H), ph=rng.random() * 6.28,
                              spd=rng.uniform(0.5, 1.5)) for _ in range(70)]
        self.lilies = []
        for _ in range(9):
            y = rng.uniform(298, 352)
            self.lilies.append(dict(x=rng.uniform(300, 630), y=y, r=4 + (y - 290) / 12, flower=rng.random() < 0.4,
                                    rot=rng.random(), ph=rng.random() * 6))
        for _ in range(5):
            y = rng.uniform(232, 262)
            self.lilies.append(dict(x=rng.uniform(320, 620), y=y, r=2 + (y - 220) / 20, flower=False,
                                    rot=rng.random(), ph=rng.random() * 6))
        self.reeds = [dict(x=x, h=rng.randint(14, 30), ph=rng.random() * 6, cat=rng.random() < 0.35)
                      for x in list(range(560, 646, 5)) + list(range(126, 150, 4))]
        # the other spots you can row to
        cove_lilies = []
        for _ in range(30):
            y = rng.uniform(226, 354)
            cove_lilies.append(dict(x=rng.uniform(280, 636), y=y, r=2.5 + (y - 214) / 13, flower=rng.random() < 0.55,
                                    rot=rng.random(), ph=rng.random() * 6))
        cove_reeds = [dict(x=x, h=rng.randint(18, 38), ph=rng.random() * 6, cat=rng.random() < 0.6)
                      for x in list(range(540, 646, 4)) + list(range(120, 160, 3)) + list(range(300, 336, 4))]
        creek_reeds = [dict(x=x, h=rng.randint(12, 24), ph=rng.random() * 6, cat=rng.random() < 0.3)
                       for x in list(range(124, 152, 4))]
        self.spot_sets = {'dock': (self.lilies, self.reeds), 'cove': (cove_lilies, cove_reeds),
                          'deep': ([], []), 'creek': ([], creek_reeds), 'pier': ([], []), 'rocks': ([], [])}
        # the sea at Saltmarsh: rocks that the tide covers and uncovers, kelp, and gulls overhead
        self.sea_rocks = [(330, 226, 5), (452, 246, 9), (586, 290, 14), (250, 318, 8)]
        self.gulls = [dict(x=rng.uniform(0, W), y=rng.uniform(40, 150), vx=rng.choice((-1, 1)) * rng.uniform(10, 22),
                           ph=rng.uniform(0, 6)) for _ in range(4)]
        self.seal = dict(t=rng.uniform(8, 20), x=0.0, y=0.0, up=0.0)
        self.frogs = [dict(i=i, puff=0.0, cd=rng.uniform(2, 8)) for i in (3, 11, 19)]
        self.current = [dict(x=rng.uniform(0, W), y=rng.uniform(HORIZON + 6, H - 4), ln=rng.uniform(3, 9),
                             spd=rng.uniform(0.7, 1.3)) for _ in range(34)]
        self.creek_rocks = [(196, 334, 9), (420, 300, 6), (520, 262, 5), (340, 236, 4), (600, 286, 5)]
        self.spot = 'dock'
        self.moons = [art.make_moon(i) for i in range(8)]
        self.ripples = []
        self.particles = []
        self.rain = [[rng.uniform(-40, W + 40), rng.uniform(-H, H), rng.uniform(0.8, 1.2)] for _ in range(170)]
        self.snow = [[rng.uniform(0, W), rng.uniform(-H, H), rng.uniform(0.5, 1.5), rng.random() * 6] for _ in range(130)]
        self.drift = [[rng.uniform(0, W), rng.uniform(0, H), rng.random() * 6, rng.uniform(0.6, 1.4)] for _ in range(32)]
        self.fireflies = [dict(x=rng.uniform(0, W), y=rng.uniform(200, 330), ph=rng.random() * 6.28,
                               vx=0, vy=0) for _ in range(26)]
        self.fl_lanterns = [dict(x=rng.uniform(300, 620), y=rng.uniform(220, 345), ph=rng.random() * 6) for _ in range(7)]
        self.fog_blobs = [dict(x=rng.uniform(-200, W), y=rng.uniform(150, 330), spd=rng.uniform(3, 8),
                               w=rng.randint(180, 320)) for _ in range(9)]
        self.fog_sprite = art.soft_blob(300, 40, (255, 255, 255), 1.3)
        self.fog_grad = art.vertical_alpha_gradient(W, H, (255, 255, 255), 0, 0)
        # alpha profile peaking around the horizon
        import numpy as np
        pa = pygame.surfarray.pixels_alpha(self.fog_grad)
        ys = np.arange(H)
        prof = np.clip(1 - np.abs(ys - HORIZON) / 170.0, 0, 1) ** 1.2 * 150
        pa[:] = prof.astype(np.uint8)[None, :]
        del pa
        self.shooting = None
        self.shoot_cd = 25
        self.birds = None
        self.bird_cd = 12
        self.ducks = None
        self.duck_cd = 20
        self.jump = None
        self.jump_cd = 7
        self.flash = 0.0
        self.thunder_cd = 20
        self.pending_thunder = None
        self.feeder_birds = []
        self.spots = []                 # bubbling hotspots: cast into them for quicker, rarer bites
        self.spot_cd = 8.0
        self.schools = []               # feeding schools dimpling the surface: cast into one for quick bites
        self.school_cd = 14.0
        self.streaks = []               # extra meteors during a meteor shower
        self.rockets = []
        self.fw_cd = 1.0
        self.fw_glow = []
        self.smoke_t = 0
        self.season_built = None
        self.treeline = None
        self.fg = None
        self.g_big = art.glow(46, (255, 186, 104))
        self.g_mid = art.glow(18, (255, 186, 104))
        self.g_small = art.glow(7, (255, 206, 140))
        self.g_tiny = art.glow(5, (210, 255, 120))
        self.g_sun = art.glow(60, (255, 214, 160), 2.2)
        self.g_moon = art.glow(38, (150, 170, 230), 2.4)
        self.g_streak = art.glow(9, (255, 176, 96), 1.6, ry=34)
        self.g_cool = art.glow(16, (130, 220, 255))
        self.g_star = art.glow(12, (200, 220, 255))
        self.vig = art.vignette(W, H)
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self.fx = pygame.Surface((W, H), pygame.SRCALPHA)
        self.sky_strip = pygame.Surface((1, HORIZON))
        self.water_strip = pygame.Surface((1, H - HORIZON), pygame.SRCALPHA)

    # ------------------------------------------------------------ effects api
    def ripple(self, x, y, r=10, speed=14, alpha=170):
        self.ripples.append([x, y, 0.5, r, speed, alpha])

    def splash(self, x, y, n=10, power=1.0, color=(220, 236, 244)):
        for _ in range(n):
            a = self.rng.uniform(-math.pi * 0.9, -math.pi * 0.1)
            sp = self.rng.uniform(15, 45) * power
            self.particles.append(dict(x=x, y=y, vx=math.cos(a) * sp, vy=math.sin(a) * sp * 1.4, g=110, life=0.7,
                                       max=0.7, col=color, kind='drop', floor=y + 1))

    def hearts(self, x, y, n=3):
        for i in range(n):
            self.particles.append(dict(x=x + self.rng.uniform(-6, 6), y=y, vx=self.rng.uniform(-4, 4),
                                       vy=-self.rng.uniform(10, 18), g=0, life=1.4 + i * 0.2, max=1.6,
                                       col=(240, 110, 130), kind='heart'))

    def sparkles(self, x, y, n=12, col=(255, 240, 170), spread=20):
        for _ in range(n):
            self.particles.append(dict(x=x + self.rng.uniform(-spread, spread), y=y + self.rng.uniform(-spread, spread / 2),
                                       vx=self.rng.uniform(-6, 6), vy=-self.rng.uniform(4, 16), g=0,
                                       life=self.rng.uniform(0.6, 1.4), max=1.4, col=col, kind='spark'))

    def zzz(self, x, y):
        self.particles.append(dict(x=x, y=y, vx=4, vy=-6, g=0, life=2.2, max=2.2, col=(230, 230, 250), kind='z'))

    def take_spot(self, x, y, persp):
        """True (and the spot is used up) if a bobber landed on a bubbling hotspot."""
        for sp in self.spots:
            if math.hypot(x - sp['x'], (y - sp['y']) * 2) < 7 + 7 * persp:
                self.spots.remove(sp)
                return True
        return False

    def take_school(self, x, y, persp):
        """True if a bobber landed in a feeding school (each school gives a couple of quick bites)."""
        for sc in self.schools:
            if sc['left'] > 0 and math.hypot(x - sc['x'], (y - sc['y']) * 2.2) < 12 + 12 * persp:
                sc['left'] -= 1
                if sc['left'] <= 0:
                    sc['life'] = min(sc['life'], 2.0)       # they've had enough: the school drifts off
                return True
        return False

    def steam(self, x, y):
        self.particles.append(dict(x=x, y=y, vx=self.rng.uniform(-1, 1), vy=-self.rng.uniform(5, 9), g=0,
                                   life=2.0, max=2.0, col=(240, 240, 245), kind='smoke', r=1))

    # ------------------------------------------------------------ update
    def update(self, dt, env, g):
        self.t += dt
        rng = self.rng
        spot = getattr(g, 'spot', 'dock')
        if self.season_built != (env.season, spot):
            self.treeline = art.make_treeline(env.season, spot)
            self.fg = art.make_foreground(env.season, spot)
            self.season_built = (env.season, spot)
            self.lilies, self.reeds = self.spot_sets[spot]
            self.spot = spot
            self.spots = []
            self.schools = []
            self.ripples = []
        if spot == 'creek':
            for c in self.current:
                persp = 0.5 + (c['y'] - HORIZON) / 170
                c['x'] += 26 * c['spd'] * persp * dt
                if c['x'] > W + 10:
                    c['x'] = rng.uniform(-30, -5)
                    c['y'] = rng.uniform(HORIZON + 6, H - 4)
        elif spot in art.COAST_LAMP:
            for gl in self.gulls:
                gl['x'] += gl['vx'] * dt
                if gl['x'] < -30 or gl['x'] > W + 30:
                    gl['vx'] = -gl['vx']
            se = self.seal
            if se['up'] > 0:
                se['up'] -= dt * 0.5
                if se['up'] <= 0:
                    se['t'] = rng.uniform(15, 40)
            else:
                se['t'] -= dt
                if se['t'] <= 0:
                    se['up'] = 4.0
                    se['x'], se['y'] = rng.uniform(300, 600), rng.uniform(220, 300)
        elif spot == 'cove':
            for fr in self.frogs:
                fr['cd'] -= dt
                fr['puff'] = max(0.0, fr['puff'] - dt)
                if fr['cd'] <= 0:
                    fr['cd'] = rng.uniform(3, 9)
                    fr['puff'] = 0.6
                    g.audio.play('nibble', 0.25, self.lilies[fr['i']]['x'] / W)
        # gusts of wind ruffle across the lake, left to right, and set the far trees swaying as they pass
        self.gust_t -= dt * (0.5 + env.wind * 1.5)
        if self.gust_t <= 0:
            self.gust_t = rng.uniform(5, 11)
            if env.season != 3 and spot not in art.COAST_LAMP:
                y = rng.uniform(HORIZON + 14, H - 30)
                p = 0.5 + (y - HORIZON) / 170
                self.gusts.append(dict(x=-90.0, y=y, w=rng.uniform(70, 150) * p, h=rng.uniform(8, 16) * p,
                                       vx=rng.uniform(16, 28) * (0.7 + env.wind), seed=rng.random() * 100))
        for gu in self.gusts:
            gu['x'] += gu['vx'] * dt
        self.gusts = [gu for gu in self.gusts if gu['x'] - gu['w'] < W + 20]
        want = min(1.0, sum(1 for gu in self.gusts if -40 < gu['x'] < W + 40) * 0.7) + env.wind * 0.3
        self.sway += (want - self.sway) * min(1.0, dt * 0.8)
        for c in self.clouds:
            c['x'] += c['spd'] * dt * (0.5 + env.wind) * c['par']
            if c['x'] > W + 20:
                c['x'] = -130
                c['y'] = rng.uniform(10, 105)
        for r in self.ripples:
            r[2] += r[4] * dt
        self.ripples = [r for r in self.ripples if r[2] < r[3]]
        for p in self.particles:
            p['life'] -= dt
            p['vy'] += p['g'] * dt
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            if p['kind'] == 'drop' and p['y'] > p['floor'] and p['vy'] > 0:
                p['life'] = 0
            if p['kind'] == 'smoke':
                p['vx'] += env.wind * 6 * dt
                p['r'] = min(5, p.get('r', 1) + dt * 1.6)
        self.particles = [p for p in self.particles if p['life'] > 0]
        if len(self.particles) > 700:
            self.particles = self.particles[-700:]

        # chimney smoke in cold or evening
        self.smoke_t -= dt
        if self.smoke_t <= 0:
            self.smoke_t = 0.45
            if (env.season == 3 or env.nf > 0.3 or env.rain > 0.5) and self.spot == 'dock':
                self.particles.append(dict(x=51, y=175, vx=0, vy=-7, g=0, life=4, max=4, col=(200, 200, 205),
                                           kind='smoke', r=1.5))

        # weather particles
        if env.rain > 0.02:
            n = int(len(self.rain) * env.rain)
            for d in self.rain[:n]:
                d[1] += 340 * d[2] * dt
                d[0] -= env.wind * 60 * dt
                land = HORIZON + (d[2] - 0.8) / 0.4 * (H - HORIZON)
                if d[1] > land:
                    if rng.random() < 0.5:
                        self.ripples.append([d[0], d[1], 0.5, 3 + (d[1] - HORIZON) / 50, 9, 120])
                    d[1] = rng.uniform(-60, -5)
                    d[0] = rng.uniform(-20, W + 60)
        if env.snow > 0.02:
            for f in self.snow:
                f[1] += 18 * f[2] * dt
                f[0] += math.sin(self.t * 1.3 + f[3]) * 8 * dt - env.wind * 10 * dt
                if f[1] > HORIZON + (f[2] - 0.5) * (H - HORIZON):
                    f[1] = rng.uniform(-30, -2)
                    f[0] = rng.uniform(0, W + 40)
        if env.season in (0, 2):
            for d in self.drift:
                d[1] += 12 * d[3] * dt
                d[0] += (math.sin(self.t * 1.7 + d[2]) * 14 - 8 - env.wind * 20) * dt
                if d[1] > H or d[0] < -10:
                    d[1] = rng.uniform(-40, 0)
                    d[0] = rng.uniform(0, W + 80)
        for f in self.fog_blobs:
            f['x'] += f['spd'] * dt
            if f['x'] > W + 50:
                f['x'] = -f['w'] - 20
        # fireflies
        for f in self.fireflies:
            f['vx'] += rng.uniform(-30, 30) * dt
            f['vy'] += rng.uniform(-30, 30) * dt
            f['vx'] *= 0.97
            f['vy'] *= 0.97
            f['x'] = (f['x'] + f['vx'] * dt) % W
            f['y'] = max(196, min(340, f['y'] + f['vy'] * dt))
        for l in self.fl_lanterns:
            l['x'] += (3 + env.wind * 4) * dt * (0.5 + 0.5 * math.sin(l['ph']))
            if l['x'] > W + 10:
                l['x'] = 290
        # bubbling hotspots
        self.spot_cd -= dt
        if self.spot_cd <= 0:
            self.spot_cd = rng.uniform(10, 20)
            if len(self.spots) < 2:
                d = rng.uniform(0.15, g.rod_spec()['range'])
                x, y = cast_point(d, rng.uniform(-1, 1))
                if not (g.wagon_here() and WAGON_RECT.inflate(16, 16).collidepoint(x, y)):
                    self.spots.append(dict(x=x, y=y, life=rng.uniform(30, 45), seed=rng.random() * 6, rip=0.0))
        for sp in self.spots:
            sp['life'] -= dt
            sp['rip'] -= dt
            if sp['rip'] <= 0:
                sp['rip'] = rng.uniform(0.7, 1.3)
                persp = 0.5 + (sp['y'] - HORIZON) / 170
                self.ripple(sp['x'] + rng.uniform(-3, 3) * persp, sp['y'], 4 + 5 * persp, 8, 150)
        self.spots = [sp for sp in self.spots if sp['life'] > 0]
        # feeding schools: little fins and dimples drifting slowly across the water
        self.school_cd -= dt
        if self.school_cd <= 0:
            self.school_cd = rng.uniform(22, 40)
            if not self.schools and getattr(g, 'place', 'lake') == 'lake':
                d = rng.uniform(0.3, max(0.35, g.rod_spec()['range']))
                x, y = cast_point(d, rng.uniform(-0.9, 0.9))
                if not (g.wagon_here() and WAGON_RECT.inflate(30, 16).collidepoint(x, y)):
                    self.schools.append(dict(x=x, y=y, vx=rng.choice((-1, 1)) * rng.uniform(1.5, 3.5),
                                             life=rng.uniform(28, 42), n=rng.randint(5, 8), seed=rng.random() * 6,
                                             left=2, jump=rng.uniform(1.0, 2.5)))
        for sc in self.schools:
            sc['life'] -= dt
            sc['x'] += sc['vx'] * dt
            if sc['x'] < 300 or sc['x'] > 618:
                sc['vx'] = -sc['vx']
                sc['x'] = min(618, max(300, sc['x']))
            sc['jump'] -= dt
            sc['rip'] = sc.get('rip', 0.0) - dt
            if sc['rip'] <= 0 and sc['life'] > 2:
                sc['rip'] = rng.uniform(0.25, 0.6)
                persp = 0.5 + (sc['y'] - HORIZON) / 170
                self.ripple(sc['x'] + rng.uniform(-12, 12) * persp, sc['y'] + rng.uniform(-2, 2) * persp,
                            3 + 3 * persp, 9, 160)
            if sc['jump'] <= 0 and sc['life'] > 2:
                sc['jump'] = rng.uniform(1.2, 3.0)
                persp = 0.5 + (sc['y'] - HORIZON) / 170
                jx = sc['x'] + rng.uniform(-9, 9) * persp
                self.splash(jx, sc['y'], 3, 0.35 + 0.2 * persp)
                self.ripple(jx, sc['y'], 4 + 4 * persp, 10, 150)
        self.schools = [sc for sc in self.schools if sc['life'] > 0]
        # festival fireworks on Lantern Night
        if g.lantern_night():
            self.fw_cd -= dt
            if self.fw_cd <= 0:
                self.fw_cd = rng.uniform(0.5, 1.5)
                self.rockets.append(dict(x=rng.uniform(300, 620), y=HORIZON - 2, ty=rng.uniform(26, 96),
                                         vy=-rng.uniform(95, 130), col=rng.choice(FW_COLORS)))
        for r in self.rockets:
            r['y'] += r['vy'] * dt
            r['x'] += math.sin(self.t * 9 + r['ty']) * 4 * dt
            if r['y'] <= r['ty']:
                r['done'] = True
                n = rng.randint(28, 44)
                for i in range(n):
                    a = i / n * math.tau + rng.uniform(-0.1, 0.1)
                    sp = rng.uniform(14, 32)
                    col = r['col'] if rng.random() < 0.8 else (255, 255, 240)
                    self.particles.append(dict(x=r['x'], y=r['y'], vx=math.cos(a) * sp, vy=math.sin(a) * sp, g=12,
                                               life=rng.uniform(1.3, 2.2), max=2.2, col=col, kind='fw'))
                self.fw_glow.append([r['x'], r['y'], 0.6, r['col']])
                g.audio.play('plop', 0.35, r['x'] / W)
        self.rockets = [r for r in self.rockets if not r.get('done')]
        for f in self.fw_glow:
            f[2] -= dt
        self.fw_glow = [f for f in self.fw_glow if f[2] > 0]
        # meteor shower streaks (just for looking at; the clickable star is self.shooting)
        if g.meteor_live() and env.nf > 0.6:
            if rng.random() < dt * 4.5:
                self.streaks.append(dict(x=rng.uniform(80, 660), y=rng.uniform(4, 90), vx=-rng.uniform(170, 280),
                                         vy=rng.uniform(60, 120), life=rng.uniform(0.5, 0.9), max=0.9))
        for st in self.streaks:
            st['life'] -= dt
            st['x'] += st['vx'] * dt
            st['y'] += st['vy'] * dt
        self.streaks = [st for st in self.streaks if st['life'] > 0]
        # thunder
        if env.rain > 0.7:
            self.thunder_cd -= dt
            if self.thunder_cd <= 0:
                self.thunder_cd = rng.uniform(18, 50)
                self.flash = 1.0
                self.pending_thunder = rng.uniform(0.6, 2.0)
        if self.pending_thunder is not None:
            self.pending_thunder -= dt
            if self.pending_thunder <= 0:
                self.pending_thunder = None
                g.audio.play('thunder', 0.8)
        self.flash = max(0, self.flash - dt * 2.5)
        # shooting stars
        if env.nf > 0.7 and env.over < 0.5:
            self.shoot_cd -= dt
            if self.shoot_cd <= 0 and self.shooting is None:
                if g.meteor_live():
                    self.shoot_cd = rng.uniform(1.5, 4.0)
                else:
                    self.shoot_cd = rng.uniform(25, 60) * (0.6 if g.has('telescope') else 1.0)
                x = rng.uniform(150, 560)
                self.shooting = dict(x=x, y=rng.uniform(15, 70), vx=-rng.uniform(110, 160), vy=rng.uniform(40, 70),
                                     life=1.1, caught=False)
        if self.shooting:
            s = self.shooting
            s['life'] -= dt
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            if s['life'] <= 0:
                self.shooting = None
        # bird flock across the sky
        self.bird_cd -= dt
        if self.bird_cd <= 0 and self.birds is None:
            self.bird_cd = rng.uniform(25, 60)
            if env.nf < 0.4 and env.rain < 0.3:
                self.birds = dict(x=-20, y=rng.uniform(30, 90), n=rng.randint(3, 6), spd=rng.uniform(25, 40))
        if self.birds:
            self.birds['x'] += self.birds['spd'] * dt
            if self.birds['x'] > W + 60:
                self.birds = None
        # ducks
        self.duck_cd -= dt
        if self.duck_cd <= 0 and self.ducks is None:
            self.duck_cd = rng.uniform(50, 110)
            if env.nf < 0.3 and env.rain < 0.5 and env.season in (0, 1, 2):
                self.ducks = dict(x=W + 20, y=rng.uniform(232, 256), n=rng.randint(2, 4), wake=0)
        if self.ducks:
            d = self.ducks
            d['x'] -= 9 * dt
            d['wake'] -= dt
            if d['wake'] <= 0:
                d['wake'] = 0.9
                self.ripple(d['x'] + 2, d['y'] + 1, 5, 6, 90)
            if d['x'] < 140:
                self.ducks = None
        # jumping fish
        self.jump_cd -= dt
        if self.jump_cd <= 0 and self.jump is None:
            self.jump_cd = rng.uniform(8, 22)
            y = rng.uniform(215, 340)
            x = rng.uniform(320, 620)
            self.jump = dict(x=x, y=y, t=0, dir=rng.choice((-1, 1)), sz=0.5 + (y - HORIZON) / 170)
            self.splash(x, y, 4, 0.5 * self.jump['sz'])
            self.ripple(x, y, 8 * self.jump['sz'] + 3)
        if self.jump:
            j = self.jump
            j['t'] += dt
            if j['t'] >= 0.7:
                ex = j['x'] + j['dir'] * 12 * j['sz']
                self.splash(ex, j['y'], 6, 0.6 * j['sz'])
                self.ripple(ex, j['y'], 10 * j['sz'] + 3)
                g.audio.play('splash_small', 0.25 * j['sz'], j['x'] / W)
                self.jump = None
        # feeder birds
        if g.has('feeder'):
            if env.nf < 0.3 and env.rain < 0.5 and len(self.feeder_birds) < 2 and rng.random() < dt * 0.08:
                self.feeder_birds.append(dict(t=0, side=rng.choice((-1, 1)), stay=rng.uniform(4, 10),
                                              col=rng.choice([(200, 90, 70), (90, 120, 200), (150, 120, 90)])))
            for b in self.feeder_birds:
                b['t'] += dt
            self.feeder_birds = [b for b in self.feeder_birds if b['t'] < b['stay'] + 1.2]

    # ------------------------------------------------------------ drawing
    def draw(self, frame, env, g):
        t = self.t
        nf = env.nf
        self._sky(frame, env)
        import seasons
        seasons.draw_aurora(frame, env, self, g)
        self._far(frame, env)
        if self.spot in art.COAST_LAMP:
            import coast
            art.draw_coast_lighthouse(frame, self.spot, lerp_c(env.amb, env.sky[2], 0.3), coast.lit(g), env.nf)
        elif 'lighthouse' in getattr(g, 'projects', ()):
            self._lighthouse(frame, env)
        import story
        if hasattr(g, 'story'):
            story.draw_far(g, frame, env, self)
        self._water(frame, env)
        g.fishing.draw_shadow(frame)
        near = self.near
        near.fill((0, 0, 0, 0))
        self._water_things(near, env, g)
        self._spot_things(near, env, g)
        seasons.draw_ice(near, env, self, g)
        g.fishing.draw_water(near)
        import lakelife
        lakelife.draw(near, g, t)
        near.blit(self.fg, (0, 0))
        import wildlife
        if self.spot == 'dock':
            self._dock_dynamic(near, env, g)
            lakelife.draw_dock(near, g, t)
            import goals
            goals.draw_dock(near, g, t)
            seasons.draw_pot(near, g, t)
            import biscuit
            biscuit.draw_gift(near, g, t)
            import garden
            garden.draw_world(near, g, t)
            if hasattr(g, 'shore'):
                import shore
                shore.draw_world(near, g, t)
        wildlife.draw(near, g, t)
        g.draw_actors(near)
        if hasattr(g, 'story'):
            story.draw_near(g, near)
        g.fishing.draw_line(near)
        self._particles(near, lit=True)
        self._reeds(near, env)
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        # wobbly reflection of the dock end, cat and angler
        src = near.subsurface((136, 236, 134, 52))
        refl = pygame.transform.flip(src, False, True)
        refl.set_alpha(70)
        for row in range(0, 52, 2):
            off = int(math.sin(row * 0.5 - t * 2.2) * (1 + row * 0.04))
            frame.blit(refl, (136 + off, DECK_Y + 8 + row), (0, row, 134, 2))
        frame.blit(near, (0, 0))
        self._lights(frame, env, g)
        wildlife.draw_lights(frame, g, env)
        if hasattr(g, 'story'):
            story.draw_lights(g, frame, self)
        self._particles(frame, lit=False)
        self._weather(frame, env)
        if self.flash > 0:
            v = int(self.flash * 120)
            frame.fill((v, v, v + 10), special_flags=pygame.BLEND_ADD)
        frame.blit(self.vig, (0, 0))

    def _sky(self, frame, env):
        top, mid, bot = env.sky
        strip = self.sky_strip
        for y in range(HORIZON):
            k = y / (HORIZON - 1)
            if k < 0.55:
                c = lerp_c(top, mid, k / 0.55)
            else:
                c = lerp_c(mid, bot, (k - 0.55) / 0.45)
            strip.set_at((0, y), c)
        pygame.transform.scale(strip, (W, HORIZON), frame.subsurface((0, 0, W, HORIZON)))
        t = self.t
        nf = env.nf
        vis = nf * (1 - env.over) * (1 - env.fog * 0.8)
        if vis > 0.03:
            for (x, y, b, ph) in self.stars:
                tw = 0.6 + 0.4 * math.sin(t * (1.5 + b * 2) + ph)
                a = vis * tw * (0.4 + 0.6 * b)
                c = lerp_c(top, (255, 250, 230), a)
                frame.set_at((x, y), c)
                if b > 0.9 and a > 0.5:
                    frame.set_at((x + 1, y), lerp_c(top, c, 0.5))
                    frame.set_at((x - 1, y), lerp_c(top, c, 0.5))
                    frame.set_at((x, y + 1), lerp_c(top, c, 0.5))
                    frame.set_at((x, y - 1), lerp_c(top, c, 0.5))
        # sun
        if env.sun_vis:
            sx, sy = env.sun
            low = max(0, min(1, (sy - 60) / 120))
            vis_sun = max(0.0, 1 - env.over * 1.6) * (1 - env.fog * 0.5)
            add_glow(frame, self.g_sun, (sx, sy), 0.25 + 0.45 * vis_sun)
            col = lerp_c((255, 246, 214), (255, 168, 102), low)
            if vis_sun > 0.05:
                disc = pygame.Surface((22, 22), pygame.SRCALPHA)
                pygame.draw.circle(disc, col, (11, 11), 9)
                pygame.draw.circle(disc, lighten(col, 0.5), (9, 9), 4)
                disc.set_alpha(int(255 * vis_sun))
                frame.blit(disc, (int(sx) - 11, int(sy) - 11))
        # moon
        if env.moon_vis and nf > 0.1:
            mx, my = env.moon
            add_glow(frame, self.g_moon, (mx, my), nf * 0.7 * (1 - env.over * 0.7))
            m = self.moons[env.moon_phase]
            m.set_alpha(int(255 * min(1, nf * 1.3) * (1 - env.over * 0.6)))
            frame.blit(m, (int(mx) - 8, int(my) - 8))
        # meteor shower and firework rockets (drawn in the sky so the lake reflects them)
        for st in self.streaks:
            k = min(1.0, st['life'] * 3)
            n = 18
            for i in range(n):
                q = i / n
                c = lerp_c((255, 250, 230), top, min(1.0, q * 1.1 + (1 - k)))
                frame.set_at((int(st['x'] - st['vx'] * q * 0.12), int(st['y'] - st['vy'] * q * 0.12)), c)
            add_glow(frame, self.g_star, (st['x'], st['y']), 0.45 * k)
        for r in self.rockets:
            for i in range(4):
                frame.set_at((int(r['x']), int(r['y']) + i), lerp_c((255, 240, 200), top, i / 4))
        # shooting star
        if self.shooting:
            s = self.shooting
            for i in range(14):
                k = i / 14
                x = s['x'] - s['vx'] * k * 0.12
                y = s['y'] - s['vy'] * k * 0.12
                frame.set_at((int(x), int(y)), lerp_c((255, 255, 240), top, k))
            add_glow(frame, self.g_star, (s['x'], s['y']), 0.8 * min(1, s['life'] * 2))
        # clouds
        cloud_col = lerp_c((255, 255, 255), mid, 0.3)
        cloud_col = lerp_c(cloud_col, grayish(cloud_col, 0.6), env.rain * 0.6)
        cloud_col = lerp_c(cloud_col, lerp_c(top, (60, 62, 86), 0.5), nf * 0.92)
        if env.minute < 420 or 1050 < env.minute < 1230:
            cloud_col = lerp_c(cloud_col, (255, 176, 156), 0.35 * (1 - nf))
        cover = env.cloud
        for c in self.clouds:
            a = max(0.0, min(1.0, (cover - c['th']) * 3 + 0.3)) if cover > c['th'] - 0.1 else 0
            if a <= 0.02:
                continue
            spr = self.cloud_sprites[c['spr']].copy()
            spr.fill((*cloud_col, 255), special_flags=pygame.BLEND_RGBA_MULT)
            spr.set_alpha(int(225 * a))
            frame.blit(spr, (int(c['x']), int(c['y'])))
        # bird flock
        if self.birds:
            b = self.birds
            col = darken(mid, 0.6)
            for i in range(b['n']):
                bx = b['x'] - (i % 2) * 8 - i * 6
                by = b['y'] + (i % 2) * 5 + i * 2
                flap = 1 if math.sin(t * 9 + i) > 0 else 0
                frame.set_at((int(bx), int(by)), col)
                frame.set_at((int(bx) - 1, int(by) - flap), col)
                frame.set_at((int(bx) + 1, int(by) - flap), col)
                frame.set_at((int(bx) - 2, int(by) - 1 + flap), col)
                frame.set_at((int(bx) + 2, int(by) - 1 + flap), col)

    def _far(self, frame, env):
        top, mid, bot = env.sky
        amb = env.amb
        far = lerp_c(bot, mul_c((86, 96, 136), amb), 0.4)
        if env.season == 3:
            far = lerp_c(far, (226, 232, 244), 0.35 * (1 - env.nf * 0.7))
        near = lerp_c(bot, mul_c((50, 74, 86), amb), 0.62)
        if env.fog > 0.01:
            far = lerp_c(far, env.fog_color, env.fog * 0.75)
            near = lerp_c(near, env.fog_color, env.fog * 0.55)
        if self.spot in art.COAST_LAMP:                  # the open sea: no mountains, just the far side of the bay
            pygame.draw.polygon(frame, far, [(-8, HORIZON), (-8, HORIZON - 34), (90, HORIZON - 40), (200, HORIZON - 22),
                                             (300, HORIZON - 8), (360, HORIZON)])
            tl = self.treeline.copy()
            tl.fill((*env.amb, 255), special_flags=pygame.BLEND_RGBA_MULT)
            frame.blit(tl, (0, HORIZON - 64))
            if env.fog > 0.01:
                fogl = pygame.Surface((W, 40), pygame.SRCALPHA)
                fogl.fill((*env.fog_color, int(env.fog * 150)))
                frame.blit(fogl, (0, HORIZON - 40))
            return
        pygame.draw.polygon(frame, far, [(-8, HORIZON)] + self.mtn_far + [(W + 16, HORIZON)])
        if env.season == 3:
            cap = lighten(far, 0.35)
            for (x, y) in self.mtn_far:
                if y < 134:
                    pygame.draw.line(frame, cap, (x - 3, y + 1), (x + 3, y + 1), 2)
        pygame.draw.polygon(frame, near, [(-8, HORIZON)] + self.mtn_near + [(W + 16, HORIZON)])
        tl = self.treeline.copy()
        tint = env.amb
        if env.fog > 0.01:
            tint = lerp_c(tint, (255, 255, 255), env.fog * 0.2)
        tl.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._trees(frame, tl)
        if env.fog > 0.01:
            fogl = pygame.Surface((W, 40), pygame.SRCALPHA)
            fogl.fill((*env.fog_color, int(env.fog * 150)))
            frame.blit(fogl, (0, HORIZON - 40))

    def _trees(self, frame, tl):
        """The far treeline, its tops swaying a pixel or two as the wind passes (tiles overlap, so no seams)."""
        amp = 0.35 + self.sway * 1.9
        if amp < 0.5:
            frame.blit(tl, (0, HORIZON - 64))
            return
        t = self.t
        th = tl.get_height()
        for x0 in range(0, W, 32):
            ph = t * 1.7 - x0 / 70
            for row in range(0, th, 4):
                off = int(round(math.sin(ph + row * 0.04) * amp * (1 - row / th) ** 1.5))
                sx = max(0, x0 - 1)
                frame.blit(tl, (sx + off, HORIZON - 64 + row), (sx, row, 34, 4))

    def _lighthouse(self, frame, env):
        """Fernwick's lighthouse on the far shore (drawn before the water, so the lake reflects it)."""
        x, base = 598, HORIZON
        amb = lerp_c(env.amb, env.sky[2], 0.35)
        if env.fog > 0.01:
            amb = lerp_c(amb, env.fog_color, env.fog * 0.6)

        def c(col):
            return mul_c(col, amb)
        pygame.draw.polygon(frame, c((120, 116, 110)), [(x - 14, base), (x - 8, base - 5), (x + 9, base - 5),
                                                        (x + 15, base)])
        for i in range(24):
            y = base - 5 - i
            half = 4 - i // 8
            col = (230, 70, 64) if (i // 4) % 2 else (244, 240, 230)
            frame.fill(c(col), (x - half, y, half * 2 + 1, 1))
        frame.fill(c((60, 60, 70)), (x - 4, base - 30, 9, 1))
        frame.fill(c((250, 236, 170)), (x - 2, base - 34, 5, 4))
        frame.fill(c((60, 60, 70)), (x - 3, base - 35, 7, 1))
        pygame.draw.polygon(frame, c((200, 70, 64)), [(x - 4, base - 35), (x, base - 39), (x + 4, base - 35)])
        nf = env.nf
        if nf > 0.1:
            lx, ly = x, base - 32
            frame.fill((255, 240, 170), (lx - 2, ly - 2, 5, 4))
            add_glow(frame, self.g_big, (lx, ly), nf * 0.6)
            a = self.t * 0.9
            sweep = math.cos(a)
            if abs(sweep) > 0.15:
                beam = getattr(self, '_beam', None)
                if beam is None:
                    beam = self._beam = pygame.Surface((W, HORIZON), pygame.SRCALPHA)
                beam.fill((0, 0, 0, 0))
                end = lx + sweep * 260
                k = int(70 * nf * min(1.0, abs(sweep)))
                pygame.draw.polygon(beam, (255, 240, 190, k), [(lx, ly - 1), (end, ly - 14 * abs(sweep)),
                                                               (end, ly + 10 * abs(sweep))])
                frame.blit(beam, (0, 0))

    def _water(self, frame, env):
        t = self.t
        top_region = frame.subsurface((0, 0, W, HORIZON)).copy()
        refl = pygame.transform.flip(top_region, False, True)
        frame.fill(env.sky[2], (0, HORIZON, W, H - HORIZON))
        amp_k = 1 + env.wind * 0.8 + env.rain * 1.2
        for dy in range(H - HORIZON):
            sy = min(HORIZON - 1, int(dy * 0.95))
            amp = (0.3 + dy * 0.03) * amp_k
            off = int(math.sin(dy * 0.42 - t * 2.1 + math.sin(dy * 0.07 + t * 0.4) * 2) * amp)
            frame.blit(refl, (off, HORIZON + dy), (0, sy, W, 1))
        # depth tint
        wc = mul_c((40, 98, 112), lerp_c(env.amb, (255, 255, 255), 0.15))
        if env.season == 3:
            wc = lerp_c(wc, (90, 110, 130), 0.4)
        wc = lerp_c(wc, grayish(wc, 0.3), env.rain * 0.5)
        if env.fog > 0.01:
            wc = lerp_c(wc, env.fog_color, env.fog * 0.4)
        strip = self.water_strip
        n = H - HORIZON
        for y in range(n):
            k = y / (n - 1)
            strip.set_at((0, y), (*wc, int(60 + 150 * k ** 0.8)))
        frame.blit(pygame.transform.scale(strip, (W, n)), (0, HORIZON))
        # shore line glint
        pygame.draw.line(frame, lerp_c(env.sky[2], (255, 255, 255), 0.25), (0, HORIZON), (W, HORIZON))
        # shimmer dashes
        hl = lerp_c(lighten(wc, 0.5), (255, 250, 236), 0.4 * (1 - env.nf))
        for s in self.shimmers:
            v = math.sin(t * s['spd'] + s['ph'])
            if v < 0.3:
                continue
            s['x'] = (s['x'] + 3 * env.wind * 0.016) % W
            persp = (s['y'] - HORIZON) / (H - HORIZON)
            ln = int(2 + 8 * persp * v)
            c = lerp_c(wc, hl, (v - 0.3) * (0.8 - env.rain * 0.5))
            pygame.draw.line(frame, c, (s['x'], s['y']), (s['x'] + ln, s['y']))
        # wind ruffling the water: a patch of broken, darker little waves drifting across
        ruff = darken(wc, 0.18)
        glint = lerp_c(wc, hl, 0.6)
        for gu in self.gusts:
            gx, gy, gw, gh = gu['x'], gu['y'], gu['w'], gu['h']
            p = 0.5 + (gy - HORIZON) / 170
            sd = gu['seed']
            for i in range(int(gw * gh / 9)):
                u = (math.sin(i * 12.9898 + sd) * 43758.5453) % 1.0
                v = (math.sin(i * 78.233 + sd * 1.7) * 12543.17) % 1.0
                dx, dy = u * 2 - 1, v * 2 - 1
                if dx * dx + dy * dy > 1:
                    continue
                if math.sin(t * 5 + i * 1.3) < -0.4:
                    continue
                x = gx + dx * gw / 2 + math.sin(t * 2 + i) * 1.5
                y = int(gy + dy * gh / 2)
                if y <= HORIZON + 1 or x < 0 or x >= W:
                    continue
                ln = 1 + int(2.5 * p * (1 - abs(dx)))
                pygame.draw.line(frame, glint if i % 7 == 0 else ruff, (x, y), (x + ln, y))
        # sun / moon glitter path
        rng = self.rng
        if env.sun_vis and env.over < 0.85:
            sx = env.sun[0]
            k = (1 - env.over) * (1 - env.fog * 0.6)
            gc = lerp_c((255, 246, 210), (255, 180, 110), max(0, min(1, (env.sun[1] - 60) / 120)))
            for _ in range(int(40 * k)):
                y = rng.uniform(HORIZON + 1, H)
                spread = 6 + (y - HORIZON) * 0.35
                x = sx + rng.gauss(0, spread * 0.5)
                ln = 1 + int((y - HORIZON) / 50)
                pygame.draw.line(frame, gc, (x, y), (x + ln, y))
        if env.moon_vis and env.nf > 0.4 and env.over < 0.7:
            mx = env.moon[0]
            for _ in range(int(22 * env.nf * (1 - env.over))):
                y = rng.uniform(HORIZON + 1, H)
                spread = 4 + (y - HORIZON) * 0.25
                x = mx + rng.gauss(0, spread * 0.5)
                pygame.draw.line(frame, (206, 214, 236), (x, y), (x + 1 + int((y - HORIZON) / 60), y))

    def _water_things(self, near, env, g):
        t = self.t
        # lily pads
        if env.season != 3:
            leaf = {0: (92, 150, 82), 1: (78, 140, 70), 2: (150, 140, 70)}[env.season]
            for l in self.lilies:
                r = l['r']
                bob = math.sin(t * 0.8 + l['ph']) * 0.4
                rect = pygame.Rect(0, 0, int(r * 2), max(2, int(r * 0.7)))
                rect.center = (int(l['x']), int(l['y'] + bob))
                pygame.draw.ellipse(near, darken(leaf, 0.25), rect.move(0, 1))
                pygame.draw.ellipse(near, leaf, rect)
                cx, cy = rect.center
                pygame.draw.line(near, darken(leaf, 0.3), (cx, cy), (cx + int(r * 0.9), cy - 1))
                if l['flower'] and env.season in (0, 1):
                    pygame.draw.circle(near, (250, 200, 220), (cx - 1, cy - 2), max(1, int(r / 3)))
                    near.set_at((cx - 1, cy - 2), (255, 236, 150))
        else:
            # ice floes
            for l in self.lilies[:6]:
                r = l['r'] * 1.6
                rect = pygame.Rect(0, 0, int(r * 2), max(2, int(r * 0.6)))
                rect.center = (int(l['x']), int(l['y']))
                pygame.draw.ellipse(near, (226, 236, 246, 200), rect)
                pygame.draw.line(near, (255, 255, 255), rect.midtop, (rect.right - 2, rect.top + 1))
        # ripples
        for (x, y, r, rmax, sp, a) in self.ripples:
            k = r / rmax
            alpha = int(a * (1 - k))
            if alpha < 8:
                continue
            ry = max(1, int(r * 0.32))
            rect = pygame.Rect(int(x - r), int(y - ry), int(r * 2), ry * 2)
            if rect.w >= 2:
                pygame.draw.ellipse(near, (230, 242, 250, alpha), rect, 1)
        # ducks
        if self.ducks:
            d = self.ducks
            for i in range(d['n'] + 1):
                x = int(d['x'] + i * 10)
                y = int(d['y'] + math.sin(t * 3 + i) * 0.5)
                if i == 0:
                    pygame.draw.ellipse(near, (120, 92, 64), (x - 4, y - 3, 9, 4))
                    pygame.draw.rect(near, (40, 110, 70), (x - 5, y - 6, 3, 3))
                    near.set_at((x - 6, y - 5), (240, 170, 60))
                    near.set_at((x + 4, y - 3), (90, 70, 50))
                else:
                    pygame.draw.ellipse(near, (246, 214, 100), (x - 2, y - 2, 5, 3))
                    near.set_at((x - 2, y - 3), (246, 214, 100))
                    near.set_at((x - 3, y - 3), (240, 150, 60))
        # jumping fish
        if self.jump:
            j = self.jump
            k = j['t'] / 0.7
            x = j['x'] + j['dir'] * 12 * j['sz'] * k
            y = j['y'] - math.sin(math.pi * k) * 14 * j['sz']
            ln = max(2, int(5 * j['sz']))
            ang = math.cos(math.pi * k) * 0.9
            dx = math.cos(ang) * ln * j['dir']
            dy = -math.sin(ang) * ln
            pygame.draw.line(near, (190, 200, 206), (x - dx, y - dy), (x + dx, y + dy), 2 if j['sz'] > 0.9 else 1)
        # bubbling hotspots
        for sp in self.spots:
            persp = 0.5 + (sp['y'] - HORIZON) / 170
            fade = min(1.0, sp['life'] / 3, 1)
            pw, ph_ = max(4, int(14 * persp)), max(2, int(4 * persp))
            pygame.draw.ellipse(near, (226, 242, 250, int(70 * fade)), (int(sp['x'] - pw / 2), int(sp['y'] - ph_ / 2), pw, ph_))
            for i in range(7):
                ph = (t * 1.3 + i * 0.21 + sp['seed']) % 1.0
                bx = sp['x'] + math.sin(i * 2.3 + sp['seed']) * 4 * persp
                by = sp['y'] - ph * 4 * persp
                a = int(220 * fade * (1 - ph))
                if persp > 0.8 and i % 2:
                    pygame.draw.circle(near, (236, 248, 255, a), (int(bx), int(by)), 1)
                else:
                    near.set_at((int(bx), int(by)), (236, 248, 255, a))
        # Wren's Wagon, a little houseboat shop
        if g.wagon_here() and self.spot == 'dock':
            self._wagon(near, env)
        # rival anglers in rowboats during the festival
        if g.festival_live() and self.spot == 'dock':
            for i, (bx, by, shirt) in enumerate(((392, 236, (90, 120, 190)), (528, 258, (200, 100, 90)),
                                                 (610, 226, (120, 160, 90)))):
                s = 0.55 + (by - HORIZON) / 120
                yb = by + math.sin(t * 1.3 + i * 2) * 0.8
                hw = int(9 * s)
                hull = [(bx - hw, yb - 2 * s), (bx + hw, yb - 2 * s), (bx + hw - 2 * s, yb + s), (bx - hw + 2 * s, yb + s)]
                pygame.draw.polygon(near, (130, 86, 58), hull)
                pygame.draw.line(near, (170, 120, 80), hull[0], hull[1])
                px, py = int(bx - 2 * s), int(yb - 2 * s)
                pygame.draw.rect(near, shirt, (px - 1, py - int(5 * s), max(2, int(3 * s)), int(5 * s)))
                near.fill((236, 200, 170), (px - 1, py - int(7 * s), max(2, int(3 * s)), max(1, int(2 * s))))
                near.fill((220, 196, 120), (px - 2, py - int(8 * s), max(3, int(5 * s)), 1))
                tip = (px + int(10 * s), py - int(10 * s))
                pygame.draw.line(near, (120, 90, 60), (px + 1, py - int(3 * s)), tip)
                pygame.draw.line(near, (230, 230, 220, 150), tip, (tip[0] + int(6 * s), yb + 3))
                if int(t * 2 + i) % 7 == 0:
                    near.set_at((tip[0] + int(6 * s), int(yb + 3)), (220, 60, 60))
        # floating paper lanterns (bodies)
        if ((g.has('lanterns') and self.spot == 'dock') or g.lantern_night()) and env.nf > 0.15:
            a = int(min(1, (env.nf - 0.15) * 3) * 255)
            for l in self.fl_lanterns:
                s = 0.5 + (l['y'] - HORIZON) / 170
                x, y = int(l['x']), int(l['y'] + math.sin(t + l['ph']) * 0.6)
                w_ = max(2, int(5 * s))
                pygame.draw.rect(near, (230, 110, 80, a), (x - w_ // 2, y - w_, w_, w_))
                pygame.draw.line(near, (255, 200, 140, a), (x - w_ // 2, y - w_ // 2), (x + w_ // 2 - 1, y - w_ // 2))

    def _schools(self, near):
        t = self.t
        for sc in self.schools:
            persp = 0.5 + (sc['y'] - HORIZON) / 170
            fade = max(0.0, min(1.0, sc['life'] / 2.0, (40 - sc['life']) / 2.0 + 1))
            # a darker patch of water under them
            pw, ph = max(8, int(38 * persp)), max(3, int(8 * persp))
            pygame.draw.ellipse(near, (24, 44, 58, int(80 * fade)), (int(sc['x'] - pw / 2), int(sc['y'] - ph / 2), pw, ph))
            pygame.draw.ellipse(near, (230, 242, 250, int(40 * fade)), (int(sc['x'] - pw / 2), int(sc['y'] - ph / 2), pw, ph), 1)
            for i in range(sc['n']):
                ph_ = t * (1.1 + 0.13 * i) + i * 1.9 + sc['seed']
                fx = sc['x'] + math.sin(ph_) * 11 * persp + (i - sc['n'] / 2) * 2.2 * persp
                fy = sc['y'] + math.cos(ph_ * 0.7) * 2.2 * persp
                up = math.sin(ph_ * 2.3)
                if up > 0.0:
                    # a fin or a back breaking the surface, flashing silver as it rolls
                    fw = 3 if persp > 0.8 else 2
                    near.fill((34, 48, 58, int(240 * fade)), (int(fx), int(fy) - 1, fw, 1))
                    near.set_at((int(fx) + fw // 2, int(fy) - 2), (34, 48, 58, int(240 * fade)))
                    if up > 0.75:
                        near.fill((235, 244, 250, int(240 * fade)), (int(fx), int(fy) - 1, fw, 1))
                elif up < -0.7:
                    near.set_at((int(fx), int(fy)), (226, 240, 248, int(150 * fade)))

    def _spot_things(self, near, env, g):
        """Little touches that belong to each rowboat spot."""
        t = self.t
        spot = self.spot
        if self.schools:
            self._schools(near)
        if spot in art.COAST_LAMP:
            self._sea_things(near, env, g)
            return
        if spot == 'creek':
            # current lines drifting downstream
            hl = (226, 240, 248)
            for c in self.current:
                persp = 0.5 + (c['y'] - HORIZON) / 170
                ln = int(c['ln'] * persp)
                a = int(70 + 50 * math.sin(t * 2 + c['x'] * 0.05))
                pygame.draw.line(near, (*hl, a), (int(c['x']), int(c['y'])), (int(c['x']) + ln, int(c['y'])))
            # river stones with foam on the upstream side
            for x, y, r in self.creek_rocks:
                persp = 0.5 + (y - HORIZON) / 170
                rr = max(2, int(r * persp))
                pygame.draw.ellipse(near, (96, 96, 98), (x - rr, y - rr // 2, rr * 2, rr))
                pygame.draw.ellipse(near, (128, 126, 122), (x - rr, y - rr // 2 - 1, rr * 2 - 1, max(1, rr - 1)))
                if env.season == 3:
                    near.fill((240, 244, 250), (x - rr + 1, y - rr // 2 - 1, rr, 1))
                for i in range(3):
                    ph = (t * 1.6 + i * 0.33) % 1.0
                    fx = x - rr - 1 - int(ph * 3 * persp)
                    near.set_at((fx, y + i - 1), (240, 248, 255, int(220 * (1 - ph))))
            # the little waterfall where the river comes in under the footbridge
            for i in range(24):
                x = 306 + i
                for j in range(3):
                    y = HORIZON - 7 + int(((t * 18 + i * 3.7 + j * 4) % 10))
                    near.set_at((x, y), (236, 246, 255, 200 if (i + j) % 2 else 140))
            pygame.draw.line(near, (240, 248, 255, 180), (302, HORIZON + 3), (336, HORIZON + 3))
        elif spot == 'cove' and env.season != 3:
            for fr in self.frogs:
                l = self.lilies[fr['i']]
                x, y = int(l['x']), int(l['y'] + math.sin(t * 0.8 + l['ph']) * 0.4) - 2
                body = (96, 156, 76)
                near.fill(darken(body, 0.25), (x - 3, y, 7, 2))
                near.fill(body, (x - 3, y - 2, 6, 3))
                eye = body if int(t * 3 + fr['i']) % 9 == 0 else (30, 34, 30)     # an occasional blink
                near.set_at((x - 2, y - 3), eye)
                near.set_at((x + 1, y - 3), eye)
                if fr['puff'] > 0:
                    r = 1 + int(2 * math.sin(math.pi * fr['puff'] / 0.6))
                    pygame.draw.circle(near, (236, 230, 190), (x + 3, y), r)
        elif spot == 'deep':
            # a red and white buoy marking the deep water
            bx, by = 404, 238 + math.sin(t * 1.4) * 1.2
            pygame.draw.ellipse(near, (60, 80, 100, 120), (bx - 6, int(by) + 3, 13, 3))
            near.fill((224, 70, 60), (bx - 2, int(by) - 7, 5, 4))
            near.fill((244, 240, 230), (bx - 2, int(by) - 3, 5, 3))
            near.fill((224, 70, 60), (bx - 3, int(by), 7, 3))
            near.fill((90, 80, 70), (bx, int(by) - 11, 1, 4))
            if env.nf > 0.3 and int(t * 1.5) % 3 == 0:
                near.fill((255, 230, 150), (bx - 1, int(by) - 12, 3, 2))

    def _sea_things(self, near, env, g):
        """The coast: a long swell, rocks the tide covers and uncovers, a buoy, a curious seal and the gulls."""
        import coast
        t = self.t
        lv = coast.tide_level(g)
        hl = (226, 240, 248)
        for i, c in enumerate(self.current):                       # the swell rolling in
            persp = 0.5 + (c['y'] - HORIZON) / 170
            ln = int(c['ln'] * 1.6 * persp)
            x = int((c['x'] + math.sin(t * 0.6 + i) * 6) % W)
            y = int(c['y'] + math.sin(t * 1.1 + c['x'] * 0.02) * 1.5 * persp)
            a = int(50 + 50 * math.sin(t * 1.3 + i))
            pygame.draw.line(near, (*hl, max(0, a)), (x, y), (x + ln, y))
        if self.spot == 'rocks':
            for x, y, r in self.sea_rocks:
                persp = 0.5 + (y - HORIZON) / 170
                rr = max(2, int(r * persp))
                show = 1.25 - lv                                       # more rock shows at low water
                hh = max(1, int(rr * show))
                pygame.draw.ellipse(near, (84, 82, 80), (x - rr, y - hh, rr * 2, hh + 2))
                pygame.draw.ellipse(near, (120, 116, 110), (x - rr + 1, y - hh, rr * 2 - 3, max(1, hh // 2)))
                if show > 0.6:
                    near.fill((88, 104, 56), (x - rr, y, rr * 2, 1))   # weed showing at low tide
                for i in range(6):
                    a = i / 6 * math.pi * 2 + t * 0.7
                    fx = x + math.cos(a) * (rr + 2 + math.sin(t * 2 + i) * 1.2)
                    near.set_at((int(fx), int(y + 1 + math.sin(a) * 1.2)), (240, 248, 255, 200))
            for i in range(7):                                       # kelp fronds swaying near the rocks
                bx = 150 + i * 9
                by = 300 + i * 6
                sw = math.sin(t * 0.9 + i) * 3
                pygame.draw.lines(near, (70, 96, 50, 200), False, [(bx, by), (bx + sw, by - 6), (bx + sw * 1.4, by - 12)], 2)
        else:
            bx, by = 470, 236 + math.sin(t * 1.3) * 1.4              # a red can buoy with a bell
            pygame.draw.ellipse(near, (40, 60, 80, 110), (bx - 7, int(by) + 4, 15, 3))
            near.fill((200, 60, 56), (bx - 4, int(by) - 6, 9, 10))
            near.fill((150, 40, 40), (bx + 2, int(by) - 6, 3, 10))
            near.fill((60, 60, 66), (bx - 1, int(by) - 14, 3, 8))
            near.fill((220, 190, 90), (bx - 2, int(by) - 12, 5, 3))
        # a seal pops up now and then, has a look at you, and goes again
        se = self.seal
        if se['up'] > 0:
            x, y = int(se['x']), int(se['y'])
            k = min(1.0, se['up'], 4.0 - se['up'] if se['up'] < 4.0 else 1.0)
            hh = int(6 * min(1.0, k * 2))
            if hh > 0:
                pygame.draw.ellipse(near, (96, 92, 96), (x - 4, y - hh, 9, hh + 2))
                near.fill((30, 30, 34), (x + 1, y - hh + 2, 1, 1))
                near.fill((30, 30, 34), (x + 3, y - hh + 2, 1, 1))
                pygame.draw.line(near, (230, 240, 250, 160), (x - 7, y + 1), (x + 8, y + 1))
        # gulls wheeling overhead
        for gl in self.gulls:
            x = int(gl['x'])
            y = int(gl['y'] + math.sin(t * 0.7 + gl['ph']) * 8)
            flap = math.sin(t * 6 + gl['ph']) * 2
            pygame.draw.lines(near, (240, 240, 244), False, [(x - 5, y - flap), (x, y), (x + 5, y - flap)], 2)

    def _wagon(self, near, env):
        t = self.t
        r = WAGON_RECT
        bob = math.sin(t * 1.1) * 0.7
        x0, y0 = r.x + 2, r.bottom - 6 + bob
        hull = [(x0, y0), (x0 + 46, y0), (x0 + 41, y0 + 5), (x0 + 5, y0 + 5)]
        pygame.draw.polygon(near, (120, 78, 54), hull)
        pygame.draw.line(near, (160, 110, 74), hull[0], hull[1])
        pygame.draw.line(near, (90, 60, 44), (x0 + 5, y0 + 3), (x0 + 41, y0 + 3))
        # cabin with a striped awning and a round window
        cx, cy = x0 + 8, y0 - 14
        pygame.draw.rect(near, (232, 214, 176), (cx, cy, 26, 14))
        pygame.draw.rect(near, (190, 160, 120), (cx, cy, 26, 14), 1)
        win = lerp_c((120, 150, 170), (255, 210, 130), env.nf)
        pygame.draw.circle(near, win, (cx + 7, cy + 7), 3)
        pygame.draw.rect(near, (130, 90, 60), (cx + 15, cy + 5, 6, 9))
        pygame.draw.polygon(near, (70, 140, 150), [(cx - 3, cy), (cx + 29, cy), (cx + 25, cy - 6), (cx + 1, cy - 6)])
        for i in range(0, 32, 4):
            near.fill((240, 236, 220), (cx - 3 + i, cy, 2, 2))
        # crates and a little flag
        near.fill((176, 130, 84), (x0 + 36, y0 - 6, 6, 6))
        near.fill((150, 106, 70), (x0 + 36, y0 - 6, 6, 1))
        pygame.draw.line(near, (90, 70, 56), (x0 + 3, y0), (x0 + 3, y0 - 22))
        wave = int(math.sin(t * 4) * 1.5)
        pygame.draw.polygon(near, (230, 110, 90), [(x0 + 4, y0 - 22), (x0 + 12, y0 - 20 + wave), (x0 + 4, y0 - 17)])
        # lantern on a hook
        near.fill((60, 56, 50), (x0 + 37, y0 - 15, 1, 4))
        near.fill(lerp_c((180, 160, 120), (255, 222, 150), env.nf), (x0 + 36, y0 - 11, 3, 4))

    def _dock_dynamic(self, near, env, g):
        t = self.t
        # mailbox with flag
        mx, my = 80, 241
        pygame.draw.line(near, (110, 80, 56), (mx, my), (mx, my - 10), 2)
        pygame.draw.rect(near, (90, 120, 150), (mx - 4, my - 16, 9, 6), border_radius=2)
        pygame.draw.rect(near, (60, 80, 100), (mx - 4, my - 16, 9, 6), 1, border_radius=2)
        if g.request_flag():
            pygame.draw.line(near, (60, 60, 60), (mx + 5, my - 12), (mx + 5, my - 19))
            pygame.draw.rect(near, (220, 70, 60), (mx + 5, my - 19, 4, 3))
        # festival bunting over the dock and from the cabin roof
        if g.festival_today():
            cols = [(230, 96, 96), (250, 200, 90), (110, 170, 220), (140, 196, 120), (220, 150, 210)]
            for (x0, y0), (x1, y1), sag in (((104, 245), (258, 245), 9), ((40, 182), (104, 245), 6)):
                n = int(abs(x1 - x0) / 7)
                prev = (x0, y0)
                for i in range(1, n + 1):
                    k = i / n
                    x = x0 + (x1 - x0) * k
                    y = y0 + (y1 - y0) * k + math.sin(math.pi * k) * sag
                    pygame.draw.line(near, (90, 70, 60), prev, (x, y))
                    if i < n:
                        sw = math.sin(t * 2 + i) * 0.8
                        pygame.draw.polygon(near, cols[i % len(cols)], [(x - 2, y), (x + 2, y), (x + sw, y + 5)])
                    prev = (x, y)
        # cabin window glass (warm at night)
        win = art.CABIN_WINDOW
        glass = lerp_c((90, 110, 130), (255, 206, 130), env.nf)
        for q in ((win.x, win.y, 7, 5), (win.x + 8, win.y, 6, 5), (win.x, win.y + 6, 7, 5), (win.x + 8, win.y + 6, 6, 5)):
            pygame.draw.rect(near, glass, q)
        if env.nf < 0.5:
            near.set_at((win.x + 1, win.y + 1), (220, 236, 246))
        # feeder
        if g.has('feeder'):
            fx, fy = 44, 228
            pygame.draw.line(near, (110, 80, 56), (fx, fy), (fx, fy - 16), 2)
            pygame.draw.polygon(near, (170, 70, 60), [(fx - 6, fy - 18), (fx, fy - 23), (fx + 6, fy - 18)])
            pygame.draw.rect(near, (200, 160, 110), (fx - 4, fy - 18, 9, 4))
            pygame.draw.rect(near, (230, 200, 120), (fx - 4, fy - 15, 9, 1))
            for b in self.feeder_birds:
                k = min(1, b['t'] / 1.0)
                if b['t'] > b['stay']:
                    k = max(0, 1 - (b['t'] - b['stay']) / 1.0)
                bx = fx + b['side'] * (5 + (1 - k) * 40)
                by = fy - 16 - (1 - k) * 30
                hop = 1 if (k >= 1 and math.sin(t * 5 + b['side']) > 0.8) else 0
                pygame.draw.rect(near, b['col'], (int(bx) - 2, int(by) - 3 - hop, 4, 3))
                near.set_at((int(bx) + (2 if b['side'] < 0 else -3), int(by) - 3 - hop), b['col'])
                near.set_at((int(bx) + (3 if b['side'] < 0 else -4), int(by) - 3 - hop), (240, 180, 60))

    def _reeds(self, near, env):
        t = self.t
        col = {0: (96, 150, 76), 1: (80, 136, 62), 2: (176, 150, 80), 3: (170, 160, 140)}[env.season]
        for r in self.reeds:
            sway = math.sin(t * 1.2 + r['ph']) * (1 + env.wind * 2)
            base_y = H
            if r['x'] < 160:
                base_y = 336
            x0 = r['x']
            tip = (x0 + sway, base_y - r['h'])
            pygame.draw.line(near, darken(col, 0.2), (x0, base_y), (x0 + sway * 0.5, base_y - r['h'] * 0.5))
            pygame.draw.line(near, col, (x0 + sway * 0.5, base_y - r['h'] * 0.5), tip)
            if r['cat'] and env.season != 3:
                pygame.draw.rect(near, (110, 74, 50), (int(tip[0]) - 1, int(tip[1]) + 1, 2, 5))
            if env.season == 3:
                near.set_at((int(tip[0]), int(tip[1])), (240, 244, 250))

    def _particles(self, surf, lit):
        for p in self.particles:
            k = p['kind']
            unlit = k in ('heart', 'spark', 'z', 'fw')
            if unlit == lit:
                continue
            a = max(0.0, min(1.0, p['life'] / p['max']))
            x, y = int(p['x']), int(p['y'])
            c = p['col']
            if k == 'drop':
                surf.set_at((x, y), (*c, 230) if lit else c)
            elif k == 'smoke':
                r = int(p.get('r', 1))
                pygame.draw.circle(surf, (*c, int(120 * a)), (x, y), max(1, r))
            elif k == 'heart':
                col = lerp_c((255, 255, 255), c, 0.7 + 0.3 * a) if a > 0.3 else c
                for (dx, dy) in ((-1, 0), (1, 0), (-2, -1), (-1, -1), (1, -1), (2, -1), (-2, 0), (0, 0), (2, 0),
                                 (-1, 1), (0, 1), (1, 1), (0, 2)):
                    if a > 0.15 or (dx + dy) % 2 == 0:
                        surf.set_at((x + dx, y + dy), col)
            elif k == 'spark':
                col = lerp_c((80, 80, 80), c, a)
                surf.fill(col, (x, y, 1, 1), special_flags=pygame.BLEND_ADD)
                if a > 0.5:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        surf.fill(darken(col, 0.4), (x + dx, y + dy, 1, 1), special_flags=pygame.BLEND_ADD)
            elif k == 'fw':
                col = lerp_c((0, 0, 0), c, min(1.0, a * 1.3))
                surf.fill(col, (x, y, 2, 2), special_flags=pygame.BLEND_ADD)
                for q, kk in ((0.05, 0.5), (0.1, 0.3), (0.15, 0.15)):
                    surf.fill(lerp_c((0, 0, 0), c, a * kk), (int(x - p['vx'] * q), int(y - p['vy'] * q), 1, 1),
                              special_flags=pygame.BLEND_ADD)
            elif k == 'z':
                col = lerp_c((40, 40, 60), c, a)
                for (dx, dy) in ((0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)):
                    surf.set_at((x + dx, y + dy), col)

    def _sea_lights(self, frame, env, g):
        """Windows across the harbour, and the lighthouse beam once Sol has it burning again."""
        import coast
        nf = env.nf
        for (x, y) in art.COAST_WINS.get((env.season, self.spot), ()):
            frame.fill((int(220 * nf), int(160 * nf), int(80 * nf)), (x - 1, y - 1, 2, 3), special_flags=pygame.BLEND_ADD)
            add_glow(frame, self.g_small, (x, y), nf * 0.5)
        if not coast.lit(g):
            return
        lx, ly, th = art.COAST_LAMP[self.spot]
        top = ly + 8 - 5
        add_glow(frame, self.g_big, (lx, top), nf * 0.9)
        sweep = math.cos(self.t * 0.9)
        if abs(sweep) > 0.12:
            end = (lx + sweep * 380, top - 4 * abs(sweep))
            art.draw_beam(frame, (lx, top), end, 18 * abs(sweep), 0.32 * nf * min(1.0, abs(sweep) * 1.5))

    def _lights(self, frame, env, g):
        nf = env.nf
        t = self.t
        if nf <= 0.02:
            return
        home = self.spot == 'dock'
        if home:
            win = art.CABIN_WINDOW
            add_glow(frame, self.g_mid, win.center, nf * 0.8)
        far = {'dock': 472, 'deep': 62}.get(self.spot)
        if self.spot in art.COAST_LAMP:
            self._sea_lights(frame, env, g)
        if far:
            add_glow(frame, self.g_small, (far, HORIZON - 5), nf * 0.7)
            frame.fill((int(200 * nf), int(150 * nf), int(80 * nf)), (far, HORIZON - 5, 2, 2),
                       special_flags=pygame.BLEND_ADD)
        if g.has('lantern'):
            fl = 0.92 + 0.08 * math.sin(t * 13) * math.sin(t * 7.3)
            lx, ly = (265, 258) if home else (196, DECK_Y - 17)
            add_glow(frame, self.g_big, (lx, ly), nf * fl)
            add_glow(frame, self.g_streak, (lx + 3, ly + 64), nf * 0.55 * fl)
        if g.has('lights') and home:
            for i, (x, y, c) in enumerate(g.light_bulbs()):
                fl = 0.8 + 0.2 * math.sin(t * 2 + i * 1.7)
                add_glow(frame, self.g_small, (x, y + 1), nf * 0.75 * fl)
                frame.fill(mul_c(c, (int(255 * nf),) * 3), (x, y, 1, 2), special_flags=pygame.BLEND_ADD)
        if g.wagon_here() and home:
            add_glow(frame, self.g_small, (WAGON_RECT.x + 39, WAGON_RECT.bottom - 15), nf * 0.9)
            add_glow(frame, self.g_small, (WAGON_RECT.x + 17, WAGON_RECT.bottom - 13), nf * 0.6)
        for x, y, life, col in self.fw_glow:
            add_glow(frame, self.g_mid, (x, y), life * 1.2)
        if ((g.has('lanterns') and home) or g.lantern_night()) and nf > 0.15:
            k = min(1, (nf - 0.15) * 3)
            for l in self.fl_lanterns:
                s = 0.5 + (l['y'] - HORIZON) / 170
                add_glow(frame, self.g_mid, (l['x'], l['y'] - 3 * s), k * 0.65)
                add_glow(frame, self.g_streak, (l['x'], l['y'] + 14 * s), k * 0.25)
        if env.season == 1 and env.rain < 0.4 and (env.phase in ('dusk', 'night')):
            for f in self.fireflies:
                b = math.sin(t * 2.2 + f['ph'])
                if b > 0.2:
                    add_glow(frame, self.g_tiny, (f['x'], f['y']), (b - 0.2) * nf * 1.2)
                    frame.fill((int(200 * b), int(240 * b), int(110 * b)), (int(f['x']), int(f['y']), 1, 1),
                               special_flags=pygame.BLEND_ADD)
        g.fishing.draw_lights(frame, nf)

    def _weather(self, frame, env):
        fx = self.fx
        drew = False
        if env.rain > 0.02:
            fx.fill((0, 0, 0, 0))
            drew = True
            n = int(len(self.rain) * env.rain)
            c = (200, 210, 230, 110)
            for d in self.rain[:n]:
                ln = 5 + d[2] * 5
                pygame.draw.line(fx, c, (d[0], d[1]), (d[0] - env.wind * 2 - 1, d[1] + ln))
        if env.snow > 0.02:
            if not drew:
                fx.fill((0, 0, 0, 0))
                drew = True
            n = int(len(self.snow) * env.snow)
            for f in self.snow[:n]:
                a = 230
                sz = 2 if f[2] > 1.2 else 1
                fx.fill((248, 250, 255, a), (int(f[0]), int(f[1]), sz, sz))
        if env.season in (0, 2) and env.rain < 0.5:
            if not drew:
                fx.fill((0, 0, 0, 0))
                drew = True
            for i, d in enumerate(self.drift):
                if env.season == 0:
                    c = (250, 196, 214, 230) if i % 3 else (255, 230, 236, 230)
                    fx.fill(c, (int(d[0]), int(d[1]), 2, 1))
                else:
                    c = [(214, 110, 50, 240), (230, 170, 60, 240), (180, 70, 50, 240)][i % 3]
                    flip = math.sin(self.t * 4 + d[2]) > 0
                    fx.fill(c, (int(d[0]), int(d[1]), 2 if flip else 1, 1 if flip else 2))
        if drew:
            amb = env.near_amb
            fx.fill((*amb, 255), special_flags=pygame.BLEND_RGBA_MULT)
            frame.blit(fx, (0, 0))
        if env.fog > 0.02:
            fogc = env.fog_color
            grad = self.fog_grad.copy()
            grad.fill((*fogc, 255), special_flags=pygame.BLEND_RGBA_MULT)
            grad.set_alpha(int(env.fog * 255))
            frame.blit(grad, (0, 0))
            spr = self.fog_sprite.copy()
            spr.fill((*fogc, 255), special_flags=pygame.BLEND_RGBA_MULT)
            for f in self.fog_blobs:
                s = pygame.transform.scale(spr, (f['w'], 40))
                s.set_alpha(int(env.fog * 150))
                frame.blit(s, (int(f['x']), int(f['y'])))
