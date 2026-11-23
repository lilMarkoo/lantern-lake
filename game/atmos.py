"""Light and air over the lake: sunbeams slanting through the haze, a soft glow around everything bright,
mist drifting on the water at dawn and dusk, cloud shadows sliding across the lake, sun and moon glints
twinkling on the ripples, the Milky Way (and its reflection) on clear nights, and glinting spray when a
fish breaks the surface.

Everything is drawn on the world's own 640x360 pixel grid, so it keeps the game's look. The soft light
(the glow and the beams) is worked out at a quarter of that size and laid over the top in one go, which
keeps it cheap. Settings > Display > Light effects turns it down to 'Simple' (no glow, beams or mist)."""
import math
import random

import numpy as np
import pygame

import art
from art import W, H, HORIZON, lerp_c

QW, QH = W // 4, H // 4                 # the light buffer: one pixel per 4x4 of the world
EW, EH = QW // 4, QH // 4               # ...and a smaller one again for the wide, soft part of the glow


def _smooth(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def _bump(x, a, b, c, d):
    """0 before a, rising to 1 at b, holding to c, falling to 0 at d."""
    if x <= a or x >= d:
        return 0.0
    if x < b:
        return _smooth((x - a) / (b - a))
    if x <= c:
        return 1.0
    return _smooth((d - x) / (d - c))


def _noise(w, h, cw, ch, seed):
    """Smooth value noise in 0..1, as a (w, h) array."""
    rng = np.random.default_rng(seed)
    small = pygame.Surface((cw, ch))
    v = (rng.random((cw, ch)) * 255).astype(np.uint8)
    pygame.surfarray.blit_array(small, np.dstack([v, v, v]))
    big = pygame.transform.smoothscale(small, (w, h))
    return pygame.surfarray.array3d(big)[..., 0].astype(np.float32) / 255.0


def mist_amount(env):
    """How much mist lies on the water: thick at first light, a haze at dusk, and all through a foggy day."""
    m = env.minute
    k = 0.95 * _bump(m, 285, 345, 430, 590) + 0.5 * _bump(m, 1110, 1190, 1250, 1330)
    k *= (1.0, 0.75, 1.2, 0.85)[env.season]
    k *= 1 - env.rain * 0.7
    return max(k, env.fog * 0.85)


class Atmos:
    def __init__(self):
        rng = random.Random(23)
        self.rng = rng
        self.t = 0.0
        self.light = pygame.Surface((QW, QH))
        self.wide = pygame.Surface((EW, EH))
        self.wide_up = pygame.Surface((QW, QH))
        self.beam = self._make_beam()
        self._beam_rot = {}
        self.big = pygame.Surface((W, H))
        # mist: long low wisps, bigger nearer the shore you stand on
        self.mist_spr = [art.soft_blob(w, h, power=1.4) for w, h in ((150, 12), (110, 9), (200, 15), (90, 8))]
        self.mist = []
        for i in range(16):
            d = rng.random() ** 1.3
            self.mist.append(dict(x=rng.uniform(-120, W), d=d, spr=i % 4, spd=rng.uniform(0.6, 1.4),
                                  ph=rng.uniform(0, 6.3), a=rng.uniform(0.5, 1.0)))
        self.mist_layer = pygame.Surface((W, H - HORIZON + 24), pygame.SRCALPHA)
        # cloud shadows: soft dark patches sliding over the water
        self.shadows = [dict(x=rng.uniform(-200, W), y=rng.uniform(HORIZON + 20, H - 30),
                             w=rng.randint(200, 320), spd=rng.uniform(0.7, 1.3)) for _ in range(3)]
        self._shadow_cache = {}
        # sun / moon glints: each one twinkles, then turns up somewhere else on the glitter path
        self.glints = [(rng.random(), rng.uniform(1.5, 3.2), rng.uniform(0, 6.3)) for _ in range(46)]
        self.bursts = []
        # sheets of rain sweeping across in the wind
        self.veil = art.soft_blob(150, 360, power=1.2)
        self.veils = [dict(x=rng.uniform(-150, W), spd=rng.uniform(0.7, 1.3), ph=rng.uniform(0, 6.3))
                      for _ in range(3)]
        self._veil_cache = {}
        self._milky = None
        self._milky_lv = {}

    # ------------------------------------------------------------------ update
    def update(self, dt, env):
        self.t += dt
        wind = env.wind
        for m in self.mist:
            persp = 0.45 + m['d'] * 0.9
            m['x'] += (3 + wind * 12) * m['spd'] * persp * dt
            if m['x'] > W + 20:
                m['x'] = -self.mist_spr[m['spr']].get_width() * (0.8 + m['d']) - self.rng.uniform(0, 80)
                m['d'] = self.rng.random() ** 1.3
        for s in self.shadows:
            s['x'] += (5 + wind * 16) * s['spd'] * dt
            if s['x'] > W + 40:
                s['x'] = -s['w'] - self.rng.uniform(0, 160)
                s['y'] = self.rng.uniform(HORIZON + 20, H - 30)
        for v in self.veils:
            v['x'] += (18 + wind * 50) * v['spd'] * dt
            if v['x'] > W + 40:
                v['x'] = -200 - self.rng.uniform(0, 200)
        for b in self.bursts:
            b['t'] += dt
        self.bursts = [b for b in self.bursts if b['t'] < 0.9]

    def burst(self, x, y, power):
        """A fish breaking the surface: a flash of white water and a foam ring."""
        self.bursts.append(dict(x=x, y=y, p=power, t=0.0))

    # ------------------------------------------------------------------ sky
    def _milky_way(self):
        if self._milky is None:
            w, h = W, HORIZON
            xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
            cy = 18 + xx * 0.24 + np.sin(xx * 0.008) * 16          # a gentle diagonal arc
            d = np.abs(yy - cy)
            n1 = _noise(w, h, 40, 12, 3)
            n2 = _noise(w, h, 90, 26, 4)
            f = np.exp(-(d / 26.0) ** 2) * (0.45 + 0.75 * n1)
            f *= 1 - 0.75 * np.exp(-((yy - cy - 3 + n2 * 6) / 5.0) ** 2) * n2     # the dark dust lane
            f *= np.clip((h - yy) / 50.0, 0, 1)                    # fades into the haze at the horizon
            f = np.clip(f, 0, 1)
            rng = np.random.default_rng(7)
            stars = (rng.random((w, h)) < f * 0.05) * rng.uniform(0.4, 1.0, (w, h))
            arr = np.zeros((w, h, 3), np.float32)
            for i, (c0, c1) in enumerate(zip((92, 96, 128), (190, 170, 150))):
                arr[..., i] = f * (c0 + (c1 - c0) * n2 * f) * 0.5 + stars * 170
            s = pygame.Surface((w, h))
            pygame.surfarray.blit_array(s, np.clip(arr, 0, 255).astype(np.uint8))
            self._milky = s
        return self._milky

    def draw_sky(self, frame, env, g):
        """The Milky Way, on clear dark nights (the water reflects it, since it's drawn with the sky)."""
        k = _smooth((env.nf - 0.7) / 0.3) * (1 - env.over * 1.4) * (1 - env.fog)
        k *= 0.55 * (1 - 0.5 * env.moon_vis * env.full_moon)
        if k < 0.05 or env.season == 3 and env.snow > 0.3:
            return
        lv = min(10, int(k * 10 + 0.5))
        s = self._milky_lv.get(lv)
        if s is None:
            s = self._milky_way().copy()
            v = int(255 * lv / 10)
            s.fill((v, v, v), special_flags=pygame.BLEND_MULT)
            self._milky_lv[lv] = s
        frame.blit(s, (0, 0), special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------------ on the water
    def draw_water(self, frame, env, g):
        """Mist on the water and glints on the ripples (drawn before the dock and everything near you)."""
        self._glints(frame, env)
        self._bursts(frame, env)
        if env.rain > 0.1:
            self._crowns(frame, env, getattr(g, 'world', None))
        if self.full(g):
            self._mist(frame, env)

    def _glints(self, frame, env):
        t = self.t
        if env.sun_vis and env.over < 0.7 and env.fog < 0.6:
            src, k = env.sun[0], (1 - env.over / 0.7) * (1 - env.fog) * (1 - env.nf * 0.8)
            low = _smooth((env.sun[1] - 60) / 120)
            col = lerp_c((255, 250, 226), (255, 196, 120), low)
            n = len(self.glints)
        elif env.moon_vis and env.nf > 0.5 and env.over < 0.6:
            src, k = env.moon[0], env.nf * (1 - env.over / 0.6) * (0.6 + 0.4 * env.full_moon)
            col = (200, 214, 255)
            n = len(self.glints) // 2
        else:
            return
        if k < 0.05:
            return
        for i in range(n):
            v, spd, ph = self.glints[i]
            a = t * spd + ph
            cyc = int(a / (2 * math.pi))
            tw = math.sin(a)
            if tw < 0.55:
                continue
            # a fresh spot on the glitter path each time it twinkles
            h1 = math.sin(cyc * 12.9898 + i * 78.233) * 43758.5453
            h2 = math.sin(cyc * 39.346 + i * 11.135) * 24634.6345
            u, vv = (h1 % 1.0) * 2 - 1, (h2 % 1.0 + v) % 1.0
            y = HORIZON + 3 + vv ** 1.25 * (H - HORIZON - 6)
            spread = 6 + (y - HORIZON) * 0.38
            x = src + u * abs(u) * spread * 1.6
            if not (0 <= x < W):
                continue
            b = (tw - 0.55) / 0.45 * k
            c = tuple(int(ch * b) for ch in col)
            arm = 1 + int(b * (1 + (y - HORIZON) / 80))
            ix, iy = int(x), int(y)
            frame.fill(c, (ix, iy, 1, 1), special_flags=pygame.BLEND_ADD)
            frame.fill(c, (ix, iy, 1, 1), special_flags=pygame.BLEND_ADD)
            dim = tuple(ch // 2 for ch in c)
            frame.fill(dim, (ix - arm, iy, arm * 2 + 1, 1), special_flags=pygame.BLEND_ADD)
            if arm > 1:
                frame.fill(dim, (ix, iy - 1, 1, 3), special_flags=pygame.BLEND_ADD)

    def _bursts(self, frame, env):
        for b in self.bursts:
            k = b['t'] / 0.9
            p = b['p']
            persp = 0.5 + (b['y'] - HORIZON) / 170
            r = (3 + k * 16 * p) * persp
            ry = max(1, int(r * 0.3))
            fade = (1 - k) ** 1.5
            c = tuple(int(v * fade) for v in (150, 170, 175))
            rect = pygame.Rect(int(b['x'] - r), int(b['y'] - ry), int(r * 2), ry * 2)
            if rect.w > 2 and 0 <= b['x'] < W and HORIZON < b['y'] < H:
                under = frame.get_at((int(b['x']), int(b['y'])))[:3]
                pygame.draw.ellipse(frame, lerp_c(under, (236, 246, 250), fade * 0.85), rect, 1)
            if k < 0.35:
                # the white water where it broke the surface
                w = max(3, int((4 + 10 * p) * persp * (0.6 + k)))
                hh = max(2, int((6 * p) * persp * (1 - k / 0.35)))
                crown = pygame.Surface((w, hh + 2))
                crown.fill((0, 0, 0))
                pygame.draw.ellipse(crown, c, (0, hh - 1, w, 3))              # the white water at its foot
                dim = tuple(v * 2 // 3 for v in c)
                for j in range(1, w - 1, 2):                                   # the crown's spikes
                    sh = int(hh * (0.45 + 0.55 * abs(math.sin(j * 1.7 + b['x']))))
                    crown.fill(dim if j % 4 else c, (j, hh - sh, 1, sh))
                frame.blit(crown, (int(b['x'] - w / 2), int(b['y'] - hh)), special_flags=pygame.BLEND_ADD)

    def _crowns(self, frame, env, world):
        """Each raindrop that lands kicks up a tiny crown of water before its ring spreads."""
        if world is None:
            return
        c = (70, 74, 80)
        for (x, y, r, rmax, sp, a) in world.ripples:
            if r > 1.6 or rmax > 9:
                continue
            ix, iy = int(x), int(y)
            if not (1 <= ix < W - 1 and HORIZON < iy < H - 3):
                continue
            hgt = 1 + int((iy - HORIZON) / 70)
            frame.fill(c, (ix, iy - hgt, 1, hgt), special_flags=pygame.BLEND_ADD)
            frame.fill(c, (ix - 1, iy - hgt - 1, 1, 1), special_flags=pygame.BLEND_ADD)
            frame.fill(c, (ix + 1, iy - hgt - 1, 1, 1), special_flags=pygame.BLEND_ADD)

    def _mist(self, frame, env):
        k = mist_amount(env)
        if k < 0.04:
            return
        layer = self.mist_layer
        layer.fill((0, 0, 0, 0))
        t = self.t
        y0 = HORIZON - 14
        for m in self.mist:
            d = m['d']
            spr = self.mist_spr[m['spr']]
            sc = 0.55 + d * 1.1
            w, h = int(spr.get_width() * sc), max(3, int(spr.get_height() * sc))
            y = HORIZON - 4 + d ** 1.4 * (H - HORIZON - 30)
            a = k * m['a'] * (0.55 + 0.45 * math.sin(t * 0.25 + m['ph'])) * (1.0 - d * 0.35)
            if a < 0.03:
                continue
            s = pygame.transform.scale(spr, (w, h))
            s.set_alpha(int(min(1.0, a) * 200))
            layer.blit(s, (int(m['x']), int(y - y0 - h / 2)))
        # a low band of haze right along the far shore
        band = self.mist_spr[2]
        bs = pygame.transform.scale(band, (W + 200, 18))
        bs.set_alpha(int(min(1.0, k) * 150))
        layer.blit(bs, (-100, 14 - 9))
        # lit by the sky, warmer on the side the sun is on
        top, mid, bot = env.sky
        col = lerp_c(bot, (255, 255, 255), 0.35 - env.nf * 0.25)
        col = lerp_c(col, env.amb, 0.3)
        layer.fill((*col, 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(layer, (0, y0))

    # ------------------------------------------------------------------ over everything
    def draw_air(self, frame, env, g):
        """Cloud shadows sliding over the lake and the dock, and sheets of rain sweeping past (drawn after
        everything near you)."""
        if not self.full(g):
            return
        if env.rain > 0.1:
            lv = min(6, int(env.rain * 6 + 0.5))
            for i, v in enumerate(self.veils):
                k = lv * (0.6 + 0.4 * math.sin(self.t * 0.4 + v['ph']))
                spr = self._veil(i, max(1, int(k)), env.wind)
                frame.blit(spr, (int(v['x']), 0), special_flags=pygame.BLEND_ADD)
        if not env.sun_vis or env.nf > 0.6:
            return
        k = (1 - env.nf / 0.6) * _smooth((env.cloud - 0.15) / 0.3) * (1 - env.over) * (1 - env.fog)
        if env.cloud > 0.95:
            k *= max(0.0, (1.05 - env.cloud) / 0.1)
        if k < 0.05:
            return
        lv = min(6, int(k * 6 + 0.5))
        for i, s in enumerate(self.shadows):
            spr = self._shadow(i, s['w'], lv)
            frame.blit(spr, (int(s['x']), int(s['y'] - spr.get_height() / 2)), special_flags=pygame.BLEND_MULT)

    def _veil(self, i, lv, wind):
        slant = int(4 + wind * 10)
        key = (i, lv, slant)
        s = self._veil_cache.get(key)
        if s is None:
            if len(self._veil_cache) > 60:
                self._veil_cache.clear()
            src = pygame.transform.scale(self.veil, (150 + i * 40, H))
            base = pygame.Surface(src.get_size())
            v = 4 * lv
            base.fill((v, v, v + 3))
            base.blit(src, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            # mask by the blob's alpha: multiply colour by alpha
            arr = pygame.surfarray.pixels_alpha(src).astype(np.float32) / 255.0
            rgb = pygame.surfarray.array3d(base).astype(np.float32)
            rgb[...] = np.array([v, v, v + 3], np.float32)[None, None, :] * arr[..., None]
            s = pygame.Surface(src.get_size())
            pygame.surfarray.blit_array(s, rgb.astype(np.uint8))
            s = pygame.transform.rotate(s, slant)
            self._veil_cache[key] = s
        return s

    def _shadow(self, i, w, lv):
        key = (i, lv)
        s = self._shadow_cache.get(key)
        if s is None:
            h = w // 5
            xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
            n = _noise(w, h, 7, 3, 40 + i)
            d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
            f = np.clip((1 - d) * 1.6 + (n - 0.5) * 0.9, 0, 1) ** 1.3
            depth = 0.16 * lv / 6
            arr = np.empty((w, h, 3), np.float32)
            for c, tint in enumerate((1.0, 0.96, 0.86)):
                arr[..., c] = 255 * (1 - f * depth * tint)
            s = pygame.Surface((w, h))
            pygame.surfarray.blit_array(s, arr.astype(np.uint8))
            self._shadow_cache[key] = s
        return s

    # ------------------------------------------------------------------ glow and sunbeams
    def full(self, g):
        try:
            fx = g.settings.get('fx', 'full')
            return fx == 'full' or (fx == 'auto' and not getattr(g, 'fx_low', False))
        except AttributeError:
            return True

    def post(self, frame, env, g):
        """The soft light: everything bright glows a little, and low sun throws beams through the haze."""
        if not self.full(g):
            return
        light = self.light
        pygame.transform.smoothscale(frame, (QW, QH), light)
        nf = env.nf
        thr = int(218 - 100 * nf)                   # at night even a lantern blooms; by day only the sun does
        light.fill((thr, thr, thr), special_flags=pygame.BLEND_SUB)
        gain = int(120 + 80 * nf)
        light.fill((gain, gain, gain), special_flags=pygame.BLEND_MULT)
        light.blit(light.copy(), (0, 0), special_flags=pygame.BLEND_ADD)     # x2: the bright core
        # the wide, soft halo
        pygame.transform.smoothscale(light, (EW, EH), self.wide)
        pygame.transform.smoothscale(self.wide, (QW, QH), self.wide_up)
        light.blit(self.wide_up, (0, 0), special_flags=pygame.BLEND_ADD)
        light.blit(self.wide_up, (0, 0), special_flags=pygame.BLEND_ADD)
        self._rays(light, env)
        pygame.transform.smoothscale(light, (W, H), self.big)
        frame.blit(self.big, (0, 0), special_flags=pygame.BLEND_ADD)

    def ray_amount(self, env):
        if not env.sun_vis:
            return 0.0
        sy = env.sun[1]
        low = _smooth((sy - 70) / 100)                      # long beams when the sun is low
        clear = max(0.0, 1 - env.over * 1.5)
        k = 0.85 * low * clear + 0.38 * env.fog * (1 - env.rain)
        k += 0.3 * clear * _smooth((env.cloud - 0.3) / 0.4) * (1 - low)      # through broken cloud by day
        return min(1.0, k) * (1 - env.nf)

    @staticmethod
    def _make_beam():
        """One soft beam of light, pointing right from the middle of the picture: it widens and fades along
        its length, with soft edges. (The left half is empty so it turns about the sun.)"""
        L, hh = 90, 9
        w, h = L * 2, hh * 2 + 1
        xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
        x = (xx - L) / L
        spread = 0.12 + 0.88 * np.clip(x, 0, 1)
        across = np.exp(-((yy - hh) / (hh * spread + 0.6)) ** 2 * 2.2)
        along = np.clip(x, 0, 1)
        f = np.where(x > 0, (1 - along) ** 1.3 * np.clip(x * 12, 0, 1), 0) * across
        s = pygame.Surface((w, h))
        v = (f * 255).astype(np.uint8)
        pygame.surfarray.blit_array(s, np.dstack([v, v, v]))
        return s

    def _rays(self, light, env):
        k = self.ray_amount(env)
        if k < 0.04:
            return
        t = self.t
        sx, sy = env.sun
        ox, oy = sx / 4, sy / 4
        low = _smooth((sy - 60) / 120)
        col = lerp_c((255, 236, 196), (255, 172, 100), low)
        aim = math.atan2(H * 0.8 - sy, W * 0.5 - sx)
        n = 8
        span = 2.3 if abs(sx - W / 2) < W * 0.3 else 1.4
        for i in range(n):
            q = (i + 0.5) / n - 0.5
            ang = aim + q * span + 0.04 * math.sin(t * 0.09 + i * 1.7)
            br = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(t * (0.15 + 0.025 * i) + i * 2.3)) ** 2
            br *= (1 - abs(q) * 1.1) * k * 0.85
            if br < 0.02:
                continue
            deg = int(round(-math.degrees(ang))) % 360
            zoom = 0.8 + 0.4 * (0.5 + 0.5 * math.sin(i * 2.9))
            key = (deg, round(zoom, 1))
            spr = self._beam_rot.get(key)
            if spr is None:
                spr = pygame.transform.rotozoom(self.beam, deg, key[1])
                if len(self._beam_rot) > 600:
                    self._beam_rot.clear()
                self._beam_rot[key] = spr
            c = tuple(int(v * br) for v in col)
            b = spr.copy()
            b.fill(c, special_flags=pygame.BLEND_MULT)
            light.blit(b, (int(ox - b.get_width() / 2), int(oy - b.get_height() / 2)),
                       special_flags=pygame.BLEND_ADD)
