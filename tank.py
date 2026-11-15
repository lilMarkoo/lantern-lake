"""The cabin aquarium: kept fish swim around a little pixel-art tank."""
import math
import random

import pygame

import art
from data import FISH_BY_ID

TW, TH = 320, 132          # low-res tank canvas, shown scaled x3
SAND = 112
# tank themes from the cabin Home catalogue: water top/bottom, sand, sand highlight, plant colours
THEMES = {
    'classic': ((120, 200, 214), (40, 110, 140), (214, 196, 156), (226, 210, 172),
                [(70, 140, 80), (90, 160, 90), (60, 120, 90), (120, 170, 80)]),
    'coral': ((140, 214, 226), (36, 100, 150), (240, 222, 206), (250, 236, 222),
              [(240, 120, 130), (250, 160, 90), (230, 100, 150), (250, 190, 120)]),
    'moss': ((150, 196, 150), (40, 90, 70), (120, 100, 70), (140, 120, 86),
             [(60, 130, 60), (90, 150, 60), (50, 110, 70), (110, 160, 70)]),
    'wreck': ((110, 180, 200), (30, 80, 110), (200, 186, 150), (214, 200, 166),
              [(70, 140, 100), (90, 150, 110), (60, 120, 90), (100, 160, 110)]),
    'moon': ((50, 70, 130), (12, 22, 56), (80, 90, 120), (100, 110, 140),
             [(90, 220, 220), (140, 200, 250), (120, 240, 200), (180, 160, 250)]),
}


class Tank:
    def __init__(self):
        self.rng = random.Random(21)
        self.t = 0.0
        self.swimmers = []
        self.bubbles = []
        self.surf = pygame.Surface((TW, TH))
        r = random.Random(4)
        self.plants = [dict(x=x, h=r.randint(18, 46), ph=r.random() * 6, col=r.choice(
            [(70, 140, 80), (90, 160, 90), (60, 120, 90), (120, 170, 80)])) for x in
            [12, 20, 28, 96, 104, 210, 218, 290, 298, 306]]
        self.pebbles = [(r.randint(0, TW), r.randint(SAND + 2, TH - 2), r.choice(
            [(196, 178, 140), (170, 150, 120), (220, 206, 170), (150, 140, 130)])) for _ in range(90)]
        self.sprites = {}

    def sync(self, tank):
        """Keep one swimmer per kept fish, in the same order as the save list."""
        while len(self.swimmers) > len(tank):
            self.swimmers.pop()
        for i, f in enumerate(tank):
            if i < len(self.swimmers) and self.swimmers[i]['id'] == f['id'] and self.swimmers[i]['size'] == f['size']:
                continue
            sw = dict(id=f['id'], size=f['size'], x=self.rng.uniform(30, TW - 30), y=self.rng.uniform(20, SAND - 20),
                      tx=0, ty=0, dir=self.rng.choice((-1, 1)), sp=0, ph=self.rng.random() * 6, rest=0)
            self._new_target(sw)
            if i < len(self.swimmers):
                self.swimmers[i] = sw
            else:
                self.swimmers.append(sw)

    def _new_target(self, s):
        s['tx'] = self.rng.uniform(26, TW - 26)
        s['ty'] = self.rng.uniform(16, SAND - 14)
        spec = FISH_BY_ID[s['id']]
        s['sp'] = self.rng.uniform(10, 18) * (0.6 + spec['agility'] * 0.8)

    def sprite(self, s):
        spec = FISH_BY_ID[s['id']]
        lo, hi = spec['size']
        rel = (s['size'] - lo) / max(1, hi - lo)
        base = {1: 0.55, 2: 0.65, 3: 0.75, 4: 0.85, 5: 1.0}[spec['rarity']]
        if spec['shape'] == 'small':
            base -= 0.1
        k = round((base + rel * 0.15) * 10) / 10
        key = (s['id'], k)
        spr = self.sprites.get(key)
        if spr is None:
            src = art.fish_sprite(spec)
            spr = pygame.transform.scale(src, (int(src.get_width() * k), int(src.get_height() * k)))
            self.sprites[key] = (spr, pygame.transform.flip(spr, True, False))
            spr = self.sprites[key]
        return spr

    def update(self, dt, tank):
        self.sync(tank)
        self.t += dt
        for s in self.swimmers:
            if s['rest'] > 0:
                s['rest'] -= dt
                continue
            dx, dy = s['tx'] - s['x'], s['ty'] - s['y']
            d = math.hypot(dx, dy)
            if d < 3:
                s['rest'] = self.rng.uniform(0.3, 2.5)
                self._new_target(s)
                continue
            s['x'] += dx / d * s['sp'] * dt
            s['y'] += dy / d * s['sp'] * dt * 0.6
            if abs(dx) > 2:
                s['dir'] = 1 if dx > 0 else -1
        if self.rng.random() < dt * 4:
            self.bubbles.append([62 + self.rng.uniform(-2, 2), SAND - 4, self.rng.uniform(14, 24), self.rng.random() * 6])
        for b in self.bubbles:
            b[1] -= b[2] * dt
            b[0] += math.sin(self.t * 3 + b[3]) * 0.3
        self.bubbles = [b for b in self.bubbles if b[1] > 6]

    def hit(self, lx, ly):
        """Index of the fish under a point in tank coordinates, or None."""
        for i in range(len(self.swimmers) - 1, -1, -1):
            s = self.swimmers[i]
            spr = self.sprite(s)[0]
            if abs(lx - s['x']) < spr.get_width() / 2 and abs(ly - s['y']) < spr.get_height() / 2 + 2:
                return i
        return None

    def render(self, selected=None, theme='classic'):
        s = self.surf
        t = self.t
        top, bot, sand, sand2, pcols = THEMES.get(theme, THEMES['classic'])
        # water gradient
        for y in range(TH):
            k = y / TH
            c = art.lerp_c(top, bot, k)
            pygame.draw.line(s, c, (0, y), (TW, y))
        # light rays
        rays = pygame.Surface((TW, TH), pygame.SRCALPHA)
        for i in range(5):
            x = 30 + i * 66 + math.sin(t * 0.4 + i) * 8
            pygame.draw.polygon(rays, (255, 255, 230, 22) if theme != 'moon' else (200, 220, 255, 10),
                                [(x, 0), (x + 16, 0), (x + 40, SAND), (x + 10, SAND)])
        s.blit(rays, (0, 0))
        # back plants
        for n, p in enumerate(self.plants):
            p = dict(p, col=pcols[n % len(pcols)])
            if theme == 'coral' and n % 3 == 1:
                _coral(s, p['x'], p['h'], p['col'])
                continue
            sw = math.sin(t * 1.1 + p['ph']) * 3
            pts = [(p['x'] + math.sin(t * 1.1 + p['ph'] + j * 0.5) * j * 0.12 * 3, SAND - j) for j in range(0, p['h'], 3)]
            if len(pts) > 1:
                pygame.draw.lines(s, art.darken(p['col'], 0.2), False, pts, 3)
                pygame.draw.lines(s, p['col'], False, pts, 1)
            for j in range(6, p['h'], 8):
                x = p['x'] + math.sin(t * 1.1 + p['ph'] + j * 0.5) * j * 0.12 * 3
                pygame.draw.line(s, p['col'], (x, SAND - j), (x + (4 if j % 16 else -4) + sw * 0.3, SAND - j - 3))
        _ornament(s, theme, t)
        # sand
        pygame.draw.rect(s, sand, (0, SAND, TW, TH - SAND))
        for x in range(0, TW, 2):
            pygame.draw.line(s, sand2, (x, SAND + int(math.sin(x * 0.1) * 1.5)), (x + 1, SAND))
        for (x, y, c) in self.pebbles:
            s.set_at((x % TW, y), c if theme != 'moon' else art.darken(c, 0.5))
        if theme == 'moon':                   # glowing specks drifting up
            for i in range(14):
                gx = (i * 47 + int(t * 6)) % TW
                gy = SAND - ((i * 29 + int(t * 9)) % SAND)
                s.set_at((gx, gy), (170, 250, 240))
        # bubbler
        pygame.draw.rect(s, (110, 110, 120), (58, SAND - 5, 9, 5))
        # fish
        for i, f in enumerate(self.swimmers):
            right, left = self.sprite(f)
            spr = right if f['dir'] > 0 else left
            bob = math.sin(t * 2 + f['ph']) * 1.2
            rect = spr.get_rect(center=(int(f['x']), int(f['y'] + bob)))
            # soft shadow on the sand
            sw_ = max(4, int(rect.w * 0.6))
            sh = pygame.Surface((sw_, 3), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (90, 74, 56, 40), sh.get_rect())
            s.blit(sh, (rect.centerx - sw_ // 2, SAND + 4))
            if i == selected:
                pygame.draw.ellipse(s, (255, 250, 220), rect.inflate(8, 6), 1)
            s.blit(spr, rect)
        for b in self.bubbles:
            pygame.draw.circle(s, (220, 244, 250), (int(b[0]), int(b[1])), 1)
            s.set_at((int(b[0]), int(b[1]) - 1), (255, 255, 255))
        # surface line and glass shine
        pygame.draw.line(s, (200, 236, 244), (0, 3), (TW, 3))
        pygame.draw.line(s, (170, 220, 232), (0, 4), (TW, 4))
        shine = pygame.Surface((TW, TH), pygame.SRCALPHA)
        if theme == 'moon':
            pygame.draw.circle(s, (230, 236, 255), (40, 16), 6)     # the moon seen through the water
            pygame.draw.circle(s, art.lerp_c(top, bot, 0.1), (43, 14), 5)
        pygame.draw.polygon(shine, (255, 255, 255, 18), [(TW - 70, 0), (TW - 52, 0), (TW - 100, TH), (TW - 118, TH)])
        s.blit(shine, (0, 0))
        return s


def _coral(s, x, h, col):
    """A little branching coral instead of a weed (Coral Garden theme)."""
    h = int(h * 0.6)
    pygame.draw.line(s, col, (x, SAND), (x, SAND - h), 3)
    for j, (dx, at) in enumerate(((-6, 0.4), (5, 0.6), (-4, 0.8))):
        y = SAND - int(h * at)
        pygame.draw.line(s, col, (x, y), (x + dx, y - 6), 2)
        pygame.draw.circle(s, col, (x + dx, y - 6), 2)
    pygame.draw.circle(s, col, (x, SAND - h), 2)


def _ornament(s, theme, t):
    hx = 150
    if theme == 'coral':                       # a big pink scallop shell
        pygame.draw.ellipse(s, (246, 196, 186), (hx, SAND - 14, 26, 16))
        for i in range(5):
            pygame.draw.line(s, (220, 150, 150), (hx + 13, SAND), (hx + 3 + i * 5, SAND - 12))
        s.fill((255, 250, 240), (hx + 12, SAND - 6, 3, 3))      # a pearl
    elif theme == 'moss':                      # a mossy sunken log
        pygame.draw.ellipse(s, (96, 70, 50), (hx - 20, SAND - 12, 64, 14))
        pygame.draw.ellipse(s, (130, 100, 70), (hx + 34, SAND - 12, 10, 14))
        pygame.draw.ellipse(s, (100, 76, 54), (hx + 36, SAND - 9, 6, 8))
        for i in range(0, 56, 4):
            s.fill((90, 150, 70), (hx - 16 + i, SAND - 13 + (i % 8 == 0), 3, 2))
    elif theme == 'wreck':                     # a little wrecked rowboat
        pygame.draw.polygon(s, (120, 84, 56), [(hx - 18, SAND - 12), (hx + 30, SAND - 16), (hx + 24, SAND),
                                               (hx - 12, SAND)])
        pygame.draw.polygon(s, (90, 62, 42), [(hx - 18, SAND - 12), (hx + 30, SAND - 16), (hx + 28, SAND - 13),
                                              (hx - 16, SAND - 9)])
        for i in range(3):
            s.fill((150, 110, 76), (hx - 10 + i * 12, SAND - 12, 2, 10))
        s.fill((40, 50, 60), (hx + 6, SAND - 7, 5, 4))
        pygame.draw.line(s, (130, 100, 70), (hx + 14, SAND - 14), (hx + 22, SAND - 34), 2)
    elif theme == 'moon':                      # a stone lantern with a glow inside
        s.fill((96, 104, 130), (hx + 4, SAND - 22, 14, 4))
        s.fill((80, 88, 116), (hx + 6, SAND - 18, 10, 10))
        glow = 200 + int(math.sin(t * 2) * 40)
        s.fill((glow, glow, 140), (hx + 8, SAND - 16, 6, 6))
        s.fill((80, 88, 116), (hx + 8, SAND - 8, 6, 8))
        s.fill((96, 104, 130), (hx + 2, SAND - 2, 18, 2))
    else:                                      # the little stone cottage
        pygame.draw.rect(s, (150, 140, 136), (hx, SAND - 16, 22, 16))
        pygame.draw.polygon(s, (170, 90, 80), [(hx - 3, SAND - 16), (hx + 11, SAND - 26), (hx + 25, SAND - 16)])
        pygame.draw.rect(s, (40, 60, 70), (hx + 8, SAND - 9, 6, 9))
        pygame.draw.rect(s, (230, 210, 120), (hx + 3, SAND - 13, 3, 3))
