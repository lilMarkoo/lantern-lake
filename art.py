"""Procedural pixel art: glows, clouds, moon, treeline, foreground, fish and item sprites."""
import math
import random

import numpy as np
import pygame

W, H = 640, 360
HORIZON = 190
DECK_Y = 286


# ---------------------------------------------------------------- colour helpers
def lerp_c(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def mul_c(a, b):
    return (a[0] * b[0] // 255, a[1] * b[1] // 255, a[2] * b[2] // 255)


def darken(c, k):
    return (int(c[0] * (1 - k)), int(c[1] * (1 - k)), int(c[2] * (1 - k)))


def lighten(c, k):
    return (int(c[0] + (255 - c[0]) * k), int(c[1] + (255 - c[1]) * k), int(c[2] + (255 - c[2]) * k))


def seed_of(text):
    v = 7
    for ch in text:
        v = (v * 131 + ord(ch)) % 1000003
    return v


# ---------------------------------------------------------------- glows (additive sprites)
def glow(r, color, power=2.0, ry=None):
    ry = ry or r
    w, h = r * 2, ry * 2
    s = pygame.Surface((w, h))
    xx, yy = np.mgrid[0:w, 0:h]
    d = np.sqrt(((xx - r + 0.5) / r) ** 2 + ((yy - ry + 0.5) / ry) ** 2)
    f = np.clip(1 - d, 0, 1) ** power
    arr = np.empty((w, h, 3), dtype=np.uint8)
    for i in range(3):
        arr[..., i] = (f * color[i]).astype(np.uint8)
    pygame.surfarray.blit_array(s, arr)
    return s


_glow_cache = {}


def add_glow(dst, g, pos, k):
    """Additively blit glow sprite g centred on pos at intensity k (0..1)."""
    if k <= 0.02:
        return
    lvl = min(24, int(k * 24 + 0.5))
    key = (id(g), lvl)
    s = _glow_cache.get(key)
    if s is None:
        s = g.copy()
        v = int(255 * lvl / 24)
        s.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        _glow_cache[key] = s
    dst.blit(s, (int(pos[0]) - s.get_width() // 2, int(pos[1]) - s.get_height() // 2),
             special_flags=pygame.BLEND_ADD)


def soft_blob(w, h, color=(255, 255, 255), power=1.5):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*color, 0))
    xx, yy = np.mgrid[0:w, 0:h]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = (np.clip(1 - d, 0, 1) ** power * 255).astype(np.uint8)
    pa = pygame.surfarray.pixels_alpha(s)
    pa[:] = a
    del pa
    return s


def vignette(w, h, strength=120):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((20, 10, 30, 0))
    xx, yy = np.mgrid[0:w, 0:h]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = (np.clip((d - 0.62) / 0.6, 0, 1) ** 1.6 * strength).astype(np.uint8)
    pa = pygame.surfarray.pixels_alpha(s)
    pa[:] = a
    del pa
    return s


def vertical_alpha_gradient(w, h, color, a0, a1):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*color, 0))
    pa = pygame.surfarray.pixels_alpha(s)
    col = np.linspace(a0, a1, h).astype(np.uint8)
    pa[:] = col[None, :]
    del pa
    return s


# ---------------------------------------------------------------- sky things
def make_cloud(rng):
    w = rng.randint(60, 120)
    h = rng.randint(22, 34)
    s = pygame.Surface((w, h + 6), pygame.SRCALPHA)
    blobs = []
    n = rng.randint(5, 8)
    for i in range(n):
        cx = int(w * (0.15 + 0.7 * i / (n - 1)) + rng.randint(-4, 4))
        r = rng.randint(h // 4, h // 2)
        # taller in the middle
        mid = 1 - abs(i / (n - 1) - 0.5) * 1.4
        r = int(r * (0.6 + 0.6 * mid))
        cy = h - r // 2 - 2
        blobs.append((cx, cy, r))
    for cx, cy, r in blobs:
        pygame.draw.circle(s, (200, 206, 224), (cx, cy + 3), r)
    for cx, cy, r in blobs:
        pygame.draw.circle(s, (255, 255, 255), (cx, cy), r)
    # flatten the bottom
    pygame.draw.rect(s, (0, 0, 0, 0), (0, h + 2, w, 6))
    return s


def make_moon(phase_idx):
    r = 7
    s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (240, 238, 220), (r + 1, r + 1), r)
    for (x, y) in ((r - 2, r - 1), (r + 3, r + 3), (r, r + 4), (r + 4, r - 2)):
        s.set_at((x, y), (214, 212, 196))
    offsets = [99, 11, 8, 5, -5, -8, -11, 99]
    off = offsets[phase_idx % 8]
    if abs(off) < 50:
        pygame.draw.circle(s, (0, 0, 0, 0), (r + 1 + off, r), r)
    return s


# ---------------------------------------------------------------- treeline (far shore)
TREE_PAL = {
    0: dict(pine=[(38, 82, 62), (50, 98, 72)], round=[(98, 152, 86), (122, 172, 98)], accent=(244, 178, 198)),
    1: dict(pine=[(32, 76, 54), (42, 90, 62)], round=[(60, 126, 62), (76, 142, 72)], accent=None),
    2: dict(pine=[(38, 78, 58), (46, 88, 64)], round=[(208, 114, 54), (224, 164, 66), (178, 76, 54)], accent=None),
    3: dict(pine=[(44, 72, 66), (54, 82, 74)], round=[(122, 110, 106), (134, 122, 116)], accent=None),
}
GROUND = {0: (70, 112, 64), 1: (58, 100, 56), 2: (124, 100, 60), 3: (226, 232, 240)}


TREE_SPOT = {  # seed, tree height factor, gap in the front row (for a house or the river mouth), house x
    'dock': (5, 1.0, (456, 488), 466),
    'cove': (17, 1.2, None, None),
    'deep': (29, 0.55, (48, 80), 56),
    'creek': (41, 1.05, (290, 350), None),
}


def make_treeline(season, spot='dock'):
    if spot in COAST_LAMP:
        return _coast_skyline(season, spot)
    seed, hf, gap, house = TREE_SPOT[spot]
    rng = random.Random(seed)
    h = 64
    s = pygame.Surface((W, h), pygame.SRCALPHA)
    pal = TREE_PAL[season]
    snow = season == 3

    def pine(x, th, col):
        base = h - 1
        dark = darken(col, 0.18)
        for i in range(3):
            top = base - th + int(i * th * 0.27)
            bot = top + int(th * 0.48)
            wd = th * (0.22 + 0.11 * i)
            pygame.draw.polygon(s, col, [(x, top), (x - wd, bot), (x + wd, bot)])
            pygame.draw.polygon(s, dark, [(x, top), (x + 1, top + 1), (x + wd, bot), (x + 1, bot)])
            if snow:
                pygame.draw.line(s, (236, 240, 248), (x - 1, top + 2), (x + 1, top + 2))
                s.set_at((x, top + 1), (246, 248, 252))
        pygame.draw.line(s, (60, 46, 40), (x, base - 2), (x, base))

    def roundtree(x, th, cols, accent):
        base = h - 1
        pygame.draw.line(s, (72, 56, 46), (x, base), (x, base - int(th * 0.45)))
        if snow:
            for k in (-1, 1):
                pygame.draw.line(s, (100, 86, 80), (x, base - int(th * 0.4)),
                                 (x + k * int(th * 0.3), base - int(th * 0.8)))
            pygame.draw.line(s, (100, 86, 80), (x, base - int(th * 0.4)), (x, base - th))
            s.set_at((x, base - th), (240, 244, 250))
            return
        r = max(3, int(th * 0.32))
        cy = base - int(th * 0.62)
        c = cols[rng.randrange(len(cols))]
        pygame.draw.circle(s, darken(c, 0.15), (x + 1, cy + 1), r)
        pygame.draw.circle(s, c, (x, cy), r)
        pygame.draw.circle(s, c, (x - r // 2, cy + r // 3), r * 2 // 3)
        pygame.draw.circle(s, lighten(c, 0.12), (x - 1, cy - r // 3), r // 2)
        if accent:
            for _ in range(r):
                s.set_at((x + rng.randint(-r + 1, r - 1), cy + rng.randint(-r + 1, r - 1)), accent)

    # back row
    x = -6
    while x < W + 6:
        th = int((rng.randint(9, 18) + int(5 * math.sin(x * 0.021) + 5)) * hf)
        if spot == 'creek' and 300 <= x <= 340:
            th = max(4, th // 3)
        if rng.random() < 0.6:
            pine(x, th, darken(pal['pine'][0], 0.12))
        else:
            roundtree(x, th, [darken(c, 0.12) for c in pal['round']], pal['accent'])
        x += rng.randint(3, 7)
    # front row
    x = -4
    while x < W + 6:
        if gap and gap[0] <= x <= gap[1]:
            x += 6
            continue
        th = int((rng.randint(12, 24) + int(8 * math.sin(x * 0.013 + 2) + 4)) * hf)
        if rng.random() < 0.55:
            pine(x, th, pal['pine'][rng.randrange(2)])
        else:
            roundtree(x, th, pal['round'], pal['accent'])
        x += rng.randint(6, 14)
    if spot == 'creek':
        # a little footbridge over the river mouth
        base = h - 3
        wood = (120, 88, 62) if not snow else (150, 136, 126)
        for i in range(0, 64):
            x = 288 + i
            y = base - 9 + int(4 * ((i - 32) / 32) ** 2)
            s.set_at((x, y), wood)
            s.set_at((x, y + 1), darken(wood, 0.25))
            if i % 8 == 0:
                pygame.draw.line(s, darken(wood, 0.3), (x, y + 2), (x, base))
            if i % 4 == 0:
                s.set_at((x, y - 3), wood)
        pygame.draw.line(s, wood, (288, base - 12), (351, base - 12))
    if house is None:
        pygame.draw.rect(s, GROUND[season], (0, h - 2, W, 2))
        return s
    # little far house (from the Deep, it is your own cabin)
    hx, base = house, h - 2
    pygame.draw.rect(s, (156, 126, 104), (hx, base - 7, 12, 8))
    pygame.draw.polygon(s, (128, 62, 56), [(hx - 2, base - 7), (hx + 6, base - 13), (hx + 14, base - 7)])
    if snow:
        pygame.draw.line(s, (240, 244, 250), (hx - 1, base - 8), (hx + 6, base - 13))
        pygame.draw.line(s, (240, 244, 250), (hx + 6, base - 13), (hx + 13, base - 8))
    pygame.draw.rect(s, (60, 54, 60), (hx + 7, base - 5, 3, 3))
    # shore line
    pygame.draw.rect(s, GROUND[season], (0, h - 2, W, 2))
    return s


# ---------------------------------------------------------------- foreground (bank, cabin, dock)
BANK = [(0, 226), (40, 228), (70, 236), (92, 252), (108, 276), (116, 290), (124, 312), (130, 340), (134, 360),
        (0, 360)]
GRASS = {0: (120, 172, 86), 1: (98, 154, 72), 2: (172, 148, 76), 3: (234, 238, 244)}
GRASS_D = {0: (86, 134, 64), 1: (72, 120, 54), 2: (140, 112, 60), 3: (198, 208, 222)}
CABIN_WINDOW = pygame.Rect(32, 206, 14, 11)
CABIN_DOOR = pygame.Rect(12, 212, 11, 20)
POLES = (104, 258)


def bank_top(x):
    pts = BANK[:-1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / max(1, x1 - x0)
    return 360


# ---------------------------------------------------------------- the home slope: terraces under the cabin
SLOPE_LAMPS = ((5, 268), (93, 271), (27, 215))     # (x, y) of each little lamp's glass: path, steps, porch
WALL_Y = 282                                       # top of the stone wall under the garden terrace
FACE_X = 84                                        # right of this (below the wall) is the stone face with the arch


def _lawn_px(season, rng, x, y, base, dark, light):
    """One pixel of lawn: soft noise with little dark blades and lighter tips."""
    r = rng.random() * (2.5 if season == 3 else 1.0)       # snow lies smoother than grass grows
    if r < 0.10:
        return dark
    if r < 0.17:
        return light
    if (x * 7 + y * 3) % 11 == 0:
        return lerp_c(base, dark, 0.5)
    return base


def _stone(s, x, y, w, h, col, season, moss=None):
    """One fieldstone: a rounded block with a lit top edge and a dark seam under it."""
    pygame.draw.rect(s, darken(col, 0.35), (x, y, w, h), border_radius=1)
    pygame.draw.rect(s, col, (x, y, w - 1, h - 1), border_radius=1)
    pygame.draw.line(s, lighten(col, 0.22), (x + 1, y), (x + w - 3, y))
    if season == 3:
        pygame.draw.line(s, (240, 244, 250), (x + 1, y), (x + w - 3, y))
    elif moss and (x * 13 + y) % 5 == 0:
        s.set_at((x + 1, y + h - 2), moss)
        s.set_at((x + 2, y + h - 2), moss)


def _lamp(s, x, y, post=12):
    """A little lamp on a post: (x, y) is the glass."""
    s.fill((70, 60, 54), (x, y + 2, 1, post))
    s.fill((60, 52, 48), (x - 1, y - 2, 3, 1))
    s.fill((60, 52, 48), (x - 1, y + 2, 3, 1))
    s.fill((236, 210, 150), (x - 1, y - 1, 3, 3))
    s.set_at((x, y), (255, 240, 200))


def _dock_slope(s, season, rng):
    """Turns the bare bank under the cabin into a lawn on two terraces: the garden up top, a stone wall, the pond
    terrace below it, and a mossy stone face around the old arch. Everything that's clicked keeps its place."""
    grass = GRASS[season]
    g_dark, g_light = darken(grass, 0.14), lighten(grass, 0.1)
    if season == 3:
        g_dark, g_light = (214, 222, 234), (250, 252, 255)
    stone = ((150, 144, 132), (146, 140, 128), (152, 140, 122), (160, 162, 170))[season]
    moss = ((96, 140, 70), (84, 128, 62), (130, 120, 60), None)[season]
    flowers = {0: [(250, 236, 120), (250, 186, 210), (255, 255, 255), (186, 170, 250)],
               1: [(250, 140, 90), (250, 220, 90), (230, 110, 150), (255, 255, 255)],
               2: [(220, 120, 50), (200, 70, 50), (240, 190, 80)], 3: []}[season]
    # ---- the lawns: the garden terrace (to the wall) and the pond terrace (to the stone face)
    for x in range(0, 136):
        top = int(bank_top(x)) + 5
        bottom = 318 if x < FACE_X else WALL_Y
        for y in range(top, bottom):
            if not s.get_at((x, y))[3]:
                continue
            k = 0.0 if y < WALL_Y else 0.06                       # the lower lawn sits a touch in shadow
            base = darken(grass, k)
            s.set_at((x, y), _lawn_px(season, rng, x, y, base, darken(g_dark, k), g_light))
    # ---- below the lawns: a cool earth bank with boulders, roots and a grassy lip, and stones ringing the arch
    rx = random.Random(17)
    earth_hi, earth_lo = (104, 80, 60), (58, 46, 42)
    if season == 3:
        earth_hi, earth_lo = (112, 98, 92), (64, 58, 60)
    for x in range(0, 140):
        top = max(int(bank_top(x)) + 5, 318 if x < FACE_X else WALL_Y + 1)
        for y in range(top, 360):
            if not s.get_at((x, y))[3]:
                continue
            k = min(1.0, (y - 300) / 60)
            c = lerp_c(earth_hi, earth_lo, k)
            if rx.random() < 0.08:
                c = darken(c, 0.15)
            s.set_at((x, y), c)
    for _ in range(22):                                       # boulders, half sunk in the bank
        x, y = rx.randint(0, 132), rx.randint(320, 352)
        if FACE_X - 2 < x < FACE_X + 28 and y < 324:
            continue
        if not s.get_at((x, y))[3] or bank_top(x + 8) > y:
            continue
        w, h = rx.randint(5, 10), rx.randint(3, 6)
        c = lerp_c(stone, darken(stone, 0.4), rx.random() * 0.6 + (y - 320) / 80)
        pygame.draw.ellipse(s, darken(c, 0.35), (x, y + 1, w, h))
        pygame.draw.ellipse(s, c, (x, y, w - 1, h - 1))
        s.fill(lighten(c, 0.2), (x + 2, y, max(1, w - 5), 1))
        if moss and rx.random() < 0.5:
            s.fill(moss, (x + 1, y, 2, 1))
    for _ in range(9):                                        # roots hanging out of the bank
        x = rx.randint(4, 80)
        y = 319
        pts = [(x, y)]
        for _ in range(rx.randint(3, 6)):
            x += rx.randint(-1, 1)
            y += rx.randint(2, 3)
            pts.append((x, y))
        pygame.draw.lines(s, (88, 66, 50), False, pts)
    # the lawn's lip: tufts hanging over the edge
    for x in range(0, FACE_X):
        if s.get_at((x, 318))[3]:
            s.set_at((x, 318), darken(grass, 0.3))
            if rx.random() < 0.4:
                s.set_at((x, 319), darken(grass, 0.15) if season != 3 else (236, 240, 248))
                if rx.random() < 0.4:
                    s.set_at((x, 320), darken(grass, 0.3) if season != 3 else (220, 226, 236))
    # the bank under the garden terrace, right of the wall, where the arch is cut in
    ax, ay = 99, 308
    for k in range(26):
        a = math.pi * (0.95 + k / 25 * 1.1)                  # a ring of stones over the top half of the arch
        rr = 14 + (k % 2)
        x, y = ax + math.cos(a) * rr, ay + math.sin(a) * rr * 0.9
        if y > 322:
            continue
        c = lerp_c(stone, darken(stone, 0.25), rx.random())
        _stone(s, int(x) - 2, int(y) - 2, 5, 4, c, season, moss)
    for x in range(FACE_X - 2, FACE_X + 30, 6):              # a stone sill along the foot of the arch
        if s.get_at((min(W - 1, x + 2), 321))[3] and bank_top(x + 6) < 318:
            _stone(s, x, 321, 6, 3, lerp_c(stone, darken(stone, 0.2), rx.random()), season)
    # ---- the retaining wall under the garden: two courses of fieldstone, moss and a flower border on top
    x = 0
    while x < FACE_X - 2:
        w = rng.randint(7, 11)
        w = min(w, FACE_X - 2 - x)
        if w >= 3:
            c = lerp_c(stone, darken(stone, 0.2), rng.random() * 0.8)
            _stone(s, x, WALL_Y, w, 4, c, season, moss)
        x += w
    x = -4
    while x < FACE_X - 2:
        w = rng.randint(8, 12)
        w = min(w, FACE_X - 2 - x)
        if w >= 3:
            c = lerp_c(stone, darken(stone, 0.28), rng.random() * 0.8)
            _stone(s, max(0, x), WALL_Y + 4, w if x >= 0 else w + x, 4, c, season, moss)
        x += w
    pygame.draw.line(s, darken(grass, 0.35), (0, WALL_Y + 8), (FACE_X - 3, WALL_Y + 8))      # its shadow
    for x in range(0, FACE_X - 2):
        if moss and rng.random() < 0.18:                                                  # ivy over the top
            for k in range(rng.randint(1, 4)):
                s.set_at((x, WALL_Y + k), moss if k % 2 == 0 else darken(moss, 0.2))
        if flowers and rng.random() < 0.3:
            s.set_at((x, WALL_Y - 2), rng.choice(flowers))
            s.set_at((x, WALL_Y - 1), darken(grass, 0.2))
        elif season == 3 and rng.random() < 0.6:
            s.set_at((x, WALL_Y - 1), (250, 252, 255))
    # ---- steps from the garden down to the arch, at the right end of the wall
    for k in range(4):
        sx, sy = FACE_X - 6 + k * 2, WALL_Y - 2 + k * 3
        c = lighten(stone, 0.05 - k * 0.04)
        s.fill(darken(c, 0.35), (sx, sy + 2, 9, 2))
        s.fill(c, (sx, sy, 9, 2))
        if season == 3:
            s.fill((244, 246, 252), (sx, sy, 9, 1))
    # a gravel apron in front of the arch
    for _ in range(40):
        gx, gy = rng.randint(FACE_X + 2, FACE_X + 26), rng.randint(318, 323)
        if s.get_at((gx, gy))[3]:
            s.set_at((gx, gy), rng.choice([(150, 140, 126), (128, 120, 110), (170, 160, 146)]))
    # ---- stepping stones from the cabin door, a porch slab, and a few around the pond terrace
    for sx, sy, w in ((10, 233, 15), (30, 236, 6), (42, 238, 5), (54, 237, 6), (66, 239, 5)):
        c = lighten(stone, 0.08)
        pygame.draw.ellipse(s, darken(c, 0.3), (sx, sy, w, 3))
        pygame.draw.ellipse(s, c, (sx, sy - 1, w, 3))
    for sx, sy in ((6, 313), (66, 314), (78, 316)):
        pygame.draw.ellipse(s, darken(stone, 0.3), (sx, sy, 7, 3))
        pygame.draw.ellipse(s, lighten(stone, 0.06), (sx, sy - 1, 7, 3))
    # ---- shrubs and flower clumps on the lower lawn
    bush = {0: (82, 140, 72), 1: (64, 126, 58), 2: (190, 106, 52), 3: (210, 220, 232)}[season]
    for bx, by, r in ((84, 296, 4), (10, 318, 4)):
        pygame.draw.circle(s, darken(bush, 0.25), (bx, by + 1), r)
        pygame.draw.circle(s, bush, (bx, by), r - 1)
        s.set_at((bx - 1, by - r + 2), lighten(bush, 0.2))
        if flowers:
            for _ in range(3):
                s.set_at((bx + rng.randint(-2, 2), by + rng.randint(-2, 1)), rng.choice(flowers))
    for cx, cy in ((14, 289), (62, 289), (40, 314)):
        for _ in range(6):
            fx, fy = cx + rng.randint(-3, 3), cy + rng.randint(-1, 1)
            s.set_at((fx, fy), darken(grass, 0.25))
            if flowers:
                s.set_at((fx, fy - 1), rng.choice(flowers))
    # ---- the lamps (glass glows at night: world._lights)
    _lamp(s, *SLOPE_LAMPS[0], post=12)
    _lamp(s, *SLOPE_LAMPS[1], post=10)


def _cabin_extras(s, season, rng):
    """A stone footing, a lamp by the door, a woodpile under the eave and shingles that catch the light."""
    stone = ((150, 144, 132), (146, 140, 128), (152, 140, 122), (160, 162, 170))[season]
    x = 6
    while x < 64:
        w = rng.randint(4, 7)
        w = min(w, 64 - x)
        if not (CABIN_DOOR.x - 1 <= x + w // 2 <= CABIN_DOOR.right):
            c = lerp_c(stone, darken(stone, 0.25), rng.random())
            s.fill(darken(c, 0.3), (x, 229, w, 3))
            s.fill(c, (x, 229, w - 1, 2))
        x += w
    # the porch lamp, right of the door
    lx, ly = SLOPE_LAMPS[2]
    s.fill((70, 60, 54), (lx - 2, ly + 1, 2, 1))
    s.fill((60, 52, 48), (lx - 1, ly - 3, 3, 1))
    s.fill((236, 210, 150), (lx - 1, ly - 2, 3, 3))
    s.set_at((lx, ly - 1), (255, 240, 200))
    s.fill((60, 52, 48), (lx - 1, ly + 1, 3, 1))
    # a woodpile under the left eave
    for row, (y, n) in enumerate(((229, 3), (226, 2), (223, 1))):
        for k in range(n):
            cx = 1 + k * 2 + row
            pygame.draw.circle(s, (120, 84, 56), (cx + 1, y + 1), 1)
            s.set_at((cx + 1, y + 1), (196, 160, 110))
    # shingles: a light lip on every other course
    for i in range(1, 6, 2):
        y = 178 + i * 4 + 1
        half = 35 * (i * 4 + 1) / 23
        for xx in range(int(35 - half) + 1, int(35 + half) - 1, 3):
            s.set_at((xx, y), (156, 84, 68) if season != 3 else (250, 252, 255))


def make_foreground(season, spot='dock'):
    if spot == 'pier':
        return _pier_fg(season)
    if spot == 'rocks':
        return _rocks_fg(season)
    rng = random.Random(3)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    if spot == 'deep':
        _island(s, season)
        return s
    grass, grass_d = GRASS[season], GRASS_D[season]
    dirt, dirt_d = (112, 84, 60), (86, 64, 48)
    pygame.draw.polygon(s, dirt, BANK)
    # soil gets darker and cooler with depth, with little pebbles and roots
    for x in range(0, 136):
        top = int(bank_top(x))
        for y in range(top + 6, 360):
            if not s.get_at((x, y))[3]:
                continue
            k = min(1.0, (y - top) / 120)
            c = lerp_c(dirt, (70, 54, 48), k * 0.8)
            if rng.random() < 0.05:
                c = darken(c, 0.12)
            s.set_at((x, y), c)
    for _ in range(140):
        x = rng.randint(0, 128)
        y = rng.randint(int(bank_top(x)) + 6, 359)
        if x < 130 and s.get_at((x, y))[3]:
            s.set_at((x, y), dirt_d)
    for _ in range(18):
        x = rng.randint(4, 110)
        y = rng.randint(int(bank_top(x)) + 14, 352)
        if s.get_at((x, y))[3]:
            pygame.draw.ellipse(s, rng.choice([(132, 122, 112), (150, 140, 128)]), (x, y, rng.randint(3, 6), 3))
    for _ in range(7):
        x = rng.randint(6, 100)
        y = int(bank_top(x)) + 8
        pts = [(x, y)]
        for i in range(rng.randint(3, 6)):
            x += rng.randint(-2, 2)
            y += rng.randint(2, 4)
            pts.append((x, y))
        pygame.draw.lines(s, (96, 72, 54), False, pts)
    # ferns and tall grass spilling down the slope edge
    tuft = {0: (110, 160, 80), 1: (90, 146, 66), 2: (176, 140, 70), 3: (220, 226, 234)}[season]
    for y in range(256, 356, 5):
        ex = 0
        for xx in range(0, 140):
            if bank_top(xx) >= y:
                ex = xx
                break
        for i in range(rng.randint(1, 3)):
            bx = ex - rng.randint(2, 10)
            h = rng.randint(3, 7)
            lean = rng.randint(-2, 3)
            pygame.draw.line(s, tuft if i % 2 == 0 else darken(tuft, 0.2), (bx, y), (bx + lean, y - h))
    # stones at the water edge
    for _ in range(12):
        y = rng.randint(280, 352)
        x = 0
        for xx in range(0, 140):
            if bank_top(xx) > y:
                x = xx
                break
        x = int(x) + rng.randint(-6, 2)
        c = rng.choice([(126, 124, 120), (146, 142, 136), (110, 106, 104)])
        pygame.draw.ellipse(s, c, (x, y, rng.randint(5, 9), rng.randint(3, 5)))
    # grass cap
    for x in range(0, 136):
        top = bank_top(x)
        if top >= 359:
            continue
        top = int(top)
        thick = 5 if x < 104 else 3
        pygame.draw.line(s, grass, (x, top), (x, top + thick))
        pygame.draw.line(s, grass_d, (x, top + thick + 1), (x, top + thick + 1))
        if rng.random() < 0.35 and x < 112:
            s.set_at((x, top - 1), grass)
            if rng.random() < 0.4:
                s.set_at((x, top - 2), grass_d if season != 3 else (250, 252, 255))
    # flowers on the bank
    if season in (0, 1):
        for _ in range(16):
            x = rng.randint(2, 100)
            y = int(bank_top(x)) + rng.randint(0, 3)
            s.set_at((x, y - 1), rng.choice([(250, 240, 120), (250, 190, 210), (255, 255, 255), (190, 170, 250)]))

    # bushes behind cabin edge
    bush = {0: (82, 140, 72), 1: (64, 126, 58), 2: (190, 106, 52), 3: (210, 220, 232)}[season]
    for bx, by, r in ((72, 236, 6), (80, 239, 5), (2, 230, 6)):
        pygame.draw.circle(s, darken(bush, 0.15), (bx, by + 1), r)
        pygame.draw.circle(s, bush, (bx, by), r - 1)
        if season in (0, 1):
            for _ in range(3):
                s.set_at((bx + rng.randint(-3, 3), by + rng.randint(-3, 2)), (250, 200, 220))
    if spot == 'cove':
        _cove_bank(s, season, rng)
        return s
    if spot == 'creek':
        _willow(s, season, 46)
        _right_bank(s, season, rng)
        return s

    _dock_slope(s, season, rng)
    # ---- cabin
    log, log_d = (156, 104, 68), (122, 80, 52)
    pygame.draw.rect(s, log, (6, 198, 58, 34))
    for y in range(200, 232, 4):
        pygame.draw.line(s, log_d, (6, y), (63, y))
    for x in (6, 63):
        pygame.draw.line(s, (96, 64, 44), (x, 198), (x, 231))
    # chimney
    pygame.draw.rect(s, (130, 126, 122), (48, 176, 7, 18))
    for y in range(178, 194, 3):
        pygame.draw.line(s, (108, 104, 100), (48, y), (54, y))
    # roof
    roof, roof_d = (132, 66, 54), (104, 50, 44)
    pygame.draw.polygon(s, roof, [(0, 201), (35, 178), (70, 201)])
    for i in range(1, 6):
        y = 178 + i * 4
        half = 35 * i * 4 / 23
        pygame.draw.line(s, roof_d, (35 - half, y), (35 + half, y))
    pygame.draw.line(s, (88, 44, 38), (0, 201), (70, 201))
    if season == 3:
        pygame.draw.polygon(s, (240, 244, 250), [(1, 199), (35, 177), (69, 199), (60, 196), (35, 181), (10, 197)])
        pygame.draw.rect(s, (240, 244, 250), (48, 175, 7, 2))
    # door
    pygame.draw.rect(s, (92, 60, 42), CABIN_DOOR)
    pygame.draw.rect(s, (70, 46, 34), CABIN_DOOR, 1)
    s.set_at((CABIN_DOOR.right - 3, CABIN_DOOR.y + 10), (220, 190, 110))
    # window frame (glass drawn dynamically)
    pygame.draw.rect(s, (230, 214, 180), CABIN_WINDOW.inflate(2, 2), 1)
    pygame.draw.rect(s, (66, 74, 84), CABIN_WINDOW)
    pygame.draw.line(s, (230, 214, 180), (CABIN_WINDOW.centerx, CABIN_WINDOW.y), (CABIN_WINDOW.centerx, CABIN_WINDOW.bottom - 1))
    pygame.draw.line(s, (230, 214, 180), (CABIN_WINDOW.x, CABIN_WINDOW.centery), (CABIN_WINDOW.right - 1, CABIN_WINDOW.centery))
    # window box with flowers
    pygame.draw.rect(s, (110, 74, 50), (CABIN_WINDOW.x - 1, CABIN_WINDOW.bottom + 1, CABIN_WINDOW.w + 2, 3))
    if season != 3:
        for i in range(0, CABIN_WINDOW.w + 2, 2):
            s.set_at((CABIN_WINDOW.x + i, CABIN_WINDOW.bottom), (240, 120, 120) if i % 4 else (250, 220, 110))
    _cabin_extras(s, season, rng)

    # ---- dock
    wood, wood_d, wood_dd = (164, 118, 78), (134, 94, 62), (100, 70, 48)
    x0, x1 = 96, 264
    # posts (under deck) with submerged part translucent
    for px in (110, 150, 190, 230, 260):
        pygame.draw.rect(s, wood_dd, (px, DECK_Y + 6, 4, 14))
        sub = pygame.Surface((4, 18), pygame.SRCALPHA)
        sub.fill((60, 50, 44, 120))
        s.blit(sub, (px, DECK_Y + 20))
    pygame.draw.rect(s, wood, (x0, DECK_Y, x1 - x0, 5))
    for x in range(x0, x1, 7):
        pygame.draw.line(s, wood_d, (x, DECK_Y), (x, DECK_Y + 4))
    pygame.draw.line(s, lighten(wood, 0.2), (x0, DECK_Y), (x1 - 1, DECK_Y))
    pygame.draw.rect(s, wood_dd, (x0, DECK_Y + 5, x1 - x0, 2))
    if season == 3:
        for x in range(x0, x1, 2):
            if rng.random() < 0.7:
                s.set_at((x, DECK_Y - 1), (240, 244, 250))
    # tall poles
    for px in POLES:
        pygame.draw.rect(s, wood_d, (px - 1, 244, 3, DECK_Y - 244))
        pygame.draw.line(s, lighten(wood_d, 0.2), (px - 1, 244), (px - 1, DECK_Y - 1))
        pygame.draw.rect(s, wood_dd, (px - 2, 243, 5, 2))
    return s


def _island(s, season):
    """A tiny far island with one pine, out in the middle of the lake."""
    gx, gy = 452, HORIZON + 22
    ground = GROUND[season]
    pygame.draw.ellipse(s, darken(ground, 0.25), (gx - 26, gy - 3, 52, 8))
    pygame.draw.ellipse(s, ground, (gx - 24, gy - 5, 48, 7))
    col = TREE_PAL[season]['pine'][0]
    for i in range(3):
        top = gy - 26 + i * 6
        wd = 4 + i * 2
        pygame.draw.polygon(s, col, [(gx, top), (gx - wd, top + 10), (gx + wd, top + 10)])
        if season == 3:
            pygame.draw.line(s, (236, 240, 248), (gx - 1, top + 2), (gx + 1, top + 2))
    pygame.draw.line(s, (70, 52, 42), (gx, gy - 4), (gx, gy - 1))
    s.fill((150, 146, 140), (gx + 10, gy - 4, 4, 2))


def _willow(s, season, x):
    """A big weeping willow on the left bank."""
    top = int(bank_top(x))
    trunk, trunk_d = (104, 80, 62), (80, 60, 48)
    pygame.draw.polygon(s, trunk, [(x - 4, top), (x + 4, top), (x + 2, top - 46), (x - 1, top - 46)])
    pygame.draw.line(s, trunk_d, (x + 2, top - 1), (x + 1, top - 44))
    for dx, dy in ((-14, -54), (16, -58), (-4, -64)):
        pygame.draw.line(s, trunk, (x, top - 40), (x + dx, top + dy), 2)
    leaf = {0: (150, 196, 96), 1: (104, 160, 72), 2: (214, 176, 70), 3: None}[season]
    rng = random.Random(9)
    if leaf is None:
        for i in range(26):
            fx = x - 40 + i * 3 + rng.randint(-1, 1)
            fy = top - 62 + abs(fx - x) // 3
            pygame.draw.line(s, (120, 100, 90), (fx, fy), (fx + rng.randint(-1, 1), fy + 12 + rng.randint(0, 10)))
            s.set_at((fx, fy), (240, 244, 250))
        return
    dark, light = darken(leaf, 0.22), lighten(leaf, 0.15)
    pygame.draw.ellipse(s, dark, (x - 34, top - 74, 70, 30))
    pygame.draw.ellipse(s, leaf, (x - 30, top - 76, 62, 24))
    for i in range(40):
        fx = x - 44 + i * 2 + rng.randint(-1, 1)
        fy = top - 66 + abs(fx - x) // 4 + rng.randint(-2, 2)
        ln = 20 + rng.randint(0, 22) - abs(fx - x) // 3
        c = (dark, leaf, light)[i % 3]
        pygame.draw.line(s, c, (fx, fy), (fx + rng.randint(-1, 1), fy + max(8, ln)))
    for _ in range(30):
        s.set_at((x - 30 + rng.randint(0, 60), top - 74 + rng.randint(0, 18)), light)


def _cove_bank(s, season, rng):
    """Lily Cove: flowering shrubs, a stone lantern and a log dipping into the water."""
    flower = {0: (240, 170, 200), 1: (150, 170, 240), 2: (230, 150, 80), 3: None}[season]
    bush = {0: (82, 140, 72), 1: (64, 126, 58), 2: (170, 110, 56), 3: (210, 220, 232)}[season]
    for bx, by, r in ((22, 222, 10), (40, 218, 12), (60, 224, 9), (104, 262, 7)):
        pygame.draw.circle(s, darken(bush, 0.2), (bx + 1, by + 2), r)
        pygame.draw.circle(s, bush, (bx, by), r)
        pygame.draw.circle(s, lighten(bush, 0.12), (bx - r // 3, by - r // 3), r // 2)
        if flower:
            for _ in range(r * 2):
                s.set_at((bx + rng.randint(-r + 2, r - 2), by + rng.randint(-r + 2, r - 3)), flower)
    # stone lantern
    lx = 84
    ly = int(bank_top(lx))
    st, st_d = (150, 146, 138), (112, 108, 104)
    s.fill(st_d, (lx - 3, ly - 3, 7, 3))
    s.fill(st, (lx - 1, ly - 10, 3, 7))
    s.fill(st, (lx - 4, ly - 12, 9, 2))
    s.fill((60, 56, 54), (lx - 2, ly - 16, 5, 4))
    s.fill(st, (lx - 3, ly - 17, 7, 1))
    pygame.draw.polygon(s, st, [(lx - 5, ly - 17), (lx + 5, ly - 17), (lx, ly - 21)])
    if season == 3:
        s.fill((240, 244, 250), (lx - 4, ly - 18, 9, 1))
    # mossy log into the water
    pygame.draw.line(s, (96, 70, 52), (96, 300), (156, 318), 5)
    pygame.draw.line(s, (124, 92, 66), (96, 298), (156, 316), 1)
    pygame.draw.ellipse(s, (150, 120, 88), (152, 313, 7, 8))
    if season != 3:
        for i in range(0, 50, 3):
            s.set_at((100 + i, 297 + i * 18 // 60), (110, 150, 80))


def _right_bank(s, season, rng):
    """Willow Creek: the far bank comes in at the bottom right, with river stones."""
    pts = [(530, 360), (546, 334), (568, 316), (600, 306), (640, 300), (640, 360)]
    dirt = (112, 84, 60)
    pygame.draw.polygon(s, dirt, pts)
    for _ in range(90):
        x, y = rng.randint(540, 639), rng.randint(310, 359)
        if s.get_at((x, y))[3]:
            s.set_at((x, y), darken(dirt, rng.uniform(0.05, 0.25)))
    grass, grass_d = GRASS[season], GRASS_D[season]
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        pygame.draw.line(s, grass, (x0, y0), (x1, y1), 4)
        pygame.draw.line(s, grass_d, (x0, y0 + 3), (x1, y1 + 3), 1)
    for _ in range(9):
        x = rng.randint(520, 600)
        y = rng.randint(330, 356)
        c = rng.choice([(126, 124, 120), (146, 142, 136), (110, 106, 104)])
        pygame.draw.ellipse(s, c, (x, y, rng.randint(6, 11), rng.randint(3, 5)))


# ---------------------------------------------------------------- 2.0: the coast at Saltmarsh
# where the Saltmarsh lighthouse lamp sits, seen from each coast spot: (x, lamp y, tower height)
COAST_LAMP = {'pier': (508, HORIZON - 48, 34), 'rocks': (548, HORIZON - 92, 58)}
COAST_WINS = {}            # lit windows in the harbour skyline, filled in when it is drawn


def _coast_skyline(season, spot):
    """The far side of the water at the coast: Saltmarsh's houses and hill from the pier, a headland from the rocks."""
    h = 64
    s = pygame.Surface((W, h), pygame.SRCALPHA)
    rng = random.Random(61 if spot == 'pier' else 67)
    pal = TREE_PAL[season]
    hill = darken(GROUND[season], 0.1) if season != 3 else (214, 222, 234)
    wins = []
    if spot == 'pier':
        pts = [(0, 18), (60, 12), (130, 16), (210, 26), (300, 34), (380, 44), (440, 56), (460, h)]
        pygame.draw.polygon(s, hill, [(0, h)] + pts)
        for _ in range(30):                                  # trees and hedges on the hill
            x = rng.randrange(0, 420)
            y = 20 + int(x * 0.07) + rng.randrange(0, 12)
            pygame.draw.circle(s, darken(pal['round'][0] if season != 3 else (190, 200, 210), 0.15), (x, y), 3)
        x = 6
        cols = [(236, 226, 206), (200, 214, 230), (240, 214, 190), (214, 230, 214), (236, 236, 236), (230, 196, 196)]
        while x < 420:
            w = rng.randrange(14, 24)
            hh = rng.randrange(14, 26)
            col = cols[rng.randrange(len(cols))]
            base = h - 5
            s.fill(col, (x, base - hh, w, hh))
            s.fill(darken(col, 0.18), (x + w - 3, base - hh, 3, hh))
            roof = rng.choice([(90, 96, 116), (150, 86, 76), (70, 70, 80)])
            pygame.draw.polygon(s, roof, [(x - 1, base - hh), (x + w // 2, base - hh - 7), (x + w + 1, base - hh)])
            if season == 3:
                pygame.draw.line(s, (246, 248, 255), (x, base - hh - 1), (x + w // 2, base - hh - 7))
            for wx in range(x + 3, x + w - 3, 6):
                for wy in (base - hh + 4, base - hh + 11):
                    if wy < base - 3:
                        s.fill((70, 80, 96), (wx, wy, 2, 3))
                        wins.append((wx + 1, HORIZON - h + wy + 1))
            x += w + rng.randrange(1, 5)
        s.fill((150, 144, 136), (0, h - 5, 440, 5))         # the quay wall
        s.fill((120, 114, 108), (0, h - 2, 440, 2))
        for mx in (64, 138, 236, 318):                        # masts in the harbour
            pygame.draw.line(s, (120, 100, 80), (mx, h - 4), (mx, h - 26))
            pygame.draw.line(s, (150, 130, 110), (mx, h - 24), (mx + 7, h - 8))
        lx = COAST_LAMP['pier'][0]
        for rx, rw in ((lx - 26, 22), (lx - 10, 26), (lx + 10, 18)):
            pygame.draw.ellipse(s, (120, 114, 108), (rx, h - 10, rw, 14))
    else:                                                    # the headland runs out to the lighthouse, right
        pts = [(W, 6), (W - 40, 8), (W - 90, 18), (W - 150, 24), (W - 200, 40), (W - 240, 54), (W - 260, h)]
        pygame.draw.polygon(s, hill, [(W, h)] + pts)
        rock = (110, 106, 102)
        pygame.draw.polygon(s, rock, [(W - 250, h), (W - 214, 44), (W - 150, 30), (W - 70, 30), (W - 40, 46),
                                      (W - 20, h)])
        for _ in range(40):
            x, y = rng.randrange(W - 240, W - 30), rng.randrange(34, h)
            s.fill(lighten(rock, rng.uniform(0.05, 0.2)), (x, y, rng.randrange(2, 6), 1))
        grass = GRASS[season]
        for x in range(W - 200, W, 2):
            y = int(6 + (W - x) * 0.12 + 2 * math.sin(x * 0.2))
            s.fill(grass, (x, y, 2, 3))
        pygame.draw.ellipse(s, darken(hill, 0.2), (150, h - 9, 70, 10))      # a far island with a cottage
        s.fill((236, 230, 214), (178, h - 15, 8, 6))
        pygame.draw.polygon(s, (150, 86, 76), [(177, h - 15), (182, h - 19), (187, h - 15)])
    COAST_WINS[(season, spot)] = wins
    return s


def draw_beam(frame, src, end, spread, k):
    """A soft lighthouse beam, added onto the frame: brightest along the middle, fading at the edges."""
    if k <= 0.01:
        return
    x0, y0 = src
    x1, y1 = end
    bx, by = int(min(x0, x1)) - 2, int(min(y0, y1) - spread) - 2
    bw, bh = int(abs(x1 - x0)) + 4, int(abs(y1 - y0) + spread * 2) + 4
    if bw < 2 or bh < 2:
        return
    img = pygame.Surface((bw, bh))
    for w, a in ((1.0, 0.25), (0.62, 0.5), (0.3, 0.8)):
        c = (int(255 * k * a), int(236 * k * a), int(180 * k * a))
        pygame.draw.polygon(img, c, [(x0 - bx, y0 - by - 1), (x0 - bx, y0 - by + 1),
                                     (x1 - bx, y1 - by + spread * w), (x1 - bx, y1 - by - spread * w)])
    frame.blit(img, (bx, by), special_flags=pygame.BLEND_ADD)


def draw_coast_lighthouse(frame, spot, amb, lit, nf):
    """The Saltmarsh lighthouse on its rocks, seen across the water (lamp dark until Sol lights it)."""
    x, ly, th = COAST_LAMP[spot]
    base = ly + th + 8

    def c(col):
        return mul_c(col, amb)
    half_b = 7 if spot == 'pier' else 10
    for i in range(th):
        y = base - i
        half = half_b - (half_b * 0.35) * i / th
        col = (200, 70, 64) if (i // max(4, th // 7)) % 2 else (240, 236, 226)
        frame.fill(c(col), (int(x - half), y, int(half * 2) + 1, 1))
        frame.fill(c(darken(col, 0.2)), (x + 1, y, int(half), 1))
    top = base - th
    frame.fill(c((60, 60, 70)), (x - 6, top - 1, 13, 2))
    frame.fill(c((40, 44, 52)), (x - 4, top - 8, 9, 7))
    pygame.draw.polygon(frame, c((60, 60, 70)), [(x - 6, top - 8), (x, top - 13), (x + 6, top - 8)])
    if lit:
        k = max(0.45, nf)
        frame.fill((int(255 * k), int(236 * k), int(160 * k)), (x - 3, top - 7, 7, 5))


def _pier_fg(season):
    """Saltmarsh Pier: the wooden pier comes out from the quay on the left, on tall barnacled legs."""
    rng = random.Random(71)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    wood, wood_d, wood_dd = (150, 112, 80), (120, 88, 62), (84, 62, 46)
    deck = 226
    # the quay wall at the far left
    wall = (140, 134, 126)
    s.fill(wall, (0, deck - 18, 36, H - deck + 18))
    for j, y in enumerate(range(deck - 18, H, 7)):
        s.fill(darken(wall, 0.2), (0, y, 36, 1))
        for x in range((j % 2) * 8, 36, 16):
            s.fill(darken(wall, 0.2), (x, y, 1, 7))
    s.fill((96, 110, 70), (0, 296, 36, 10))                   # weed at the tide line
    # legs, with weed and barnacles where the tide reaches
    for px in (46, 84, 122, 160):
        s.fill(wood_dd, (px, deck + 4, 6, 70))
        s.fill(darken(wood_dd, 0.2), (px + 4, deck + 4, 2, 70))
        s.fill((80, 100, 64), (px, deck + 62, 6, 10))
        for _ in range(5):
            s.set_at((px + rng.randrange(6), deck + 50 + rng.randrange(20)), (210, 206, 196))
        sub = pygame.Surface((6, 60), pygame.SRCALPHA)
        sub.fill((40, 50, 50, 110))
        s.blit(sub, (px, deck + 74))
    for px0, px1 in ((46, 84), (84, 122), (122, 160)):       # cross braces
        pygame.draw.line(s, wood_d, (px0 + 3, deck + 8), (px1 + 3, deck + 44), 2)
    # the deck and its railing
    s.fill(wood, (0, deck, 176, 6))
    for x in range(0, 176, 6):
        s.fill(wood_d, (x, deck, 1, 6))
    s.fill(lighten(wood, 0.2), (0, deck, 176, 1))
    s.fill(wood_dd, (0, deck + 6, 176, 2))
    for x in range(4, 176, 22):
        s.fill(wood_d, (x, deck - 16, 3, 16))
    s.fill(wood, (0, deck - 17, 176, 3))
    if season == 3:
        s.fill((240, 244, 250), (0, deck - 1, 176, 2))
        s.fill((240, 244, 250), (0, deck - 18, 176, 1))
    # a ladder down to your boat
    lx = 168
    for xx in (lx, lx + 10):
        s.fill(wood_dd, (xx, deck + 6, 2, 56))
    for y in range(deck + 12, deck + 60, 7):
        s.fill(wood_d, (lx, y, 12, 2))
    # things on the pier: a lamp post, a coil of rope, a lobster pot and a gull on a post
    s.fill((50, 50, 56), (96, deck - 46, 3, 46))
    s.fill((50, 50, 56), (93, deck - 52, 9, 6))
    s.fill((236, 220, 170), (94, deck - 51, 7, 4))
    pygame.draw.ellipse(s, (190, 170, 120), (20, deck - 6, 18, 6))
    pygame.draw.ellipse(s, (160, 140, 100), (24, deck - 5, 10, 3))
    s.fill((150, 100, 70), (128, deck - 12, 18, 12))
    for xx in range(128, 146, 3):
        s.fill((110, 70, 50), (xx, deck - 12, 1, 12))
    gx, gy = 158, deck - 18
    s.fill((240, 240, 244), (gx - 3, gy - 6, 8, 5))
    s.fill((150, 156, 166), (gx - 2, gy - 6, 6, 2))
    s.fill((240, 240, 244), (gx + 3, gy - 9, 3, 3))
    s.set_at((gx + 6, gy - 8), (240, 180, 60))
    return s


def _rocks_fg(season):
    """Kelp Rocks: big weedy rocks on the left, and a few more breaking the water to the right."""
    rng = random.Random(73)
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rock, rock_l, rock_d = (104, 100, 98), (136, 132, 126), (74, 70, 70)
    pts = [(0, 196), (30, 192), (62, 204), (92, 222), (120, 250), (138, 284), (150, 320), (156, 360), (0, 360)]
    pygame.draw.polygon(s, rock, pts)
    for _ in range(26):
        x = rng.randrange(0, 140)
        y = rng.randrange(206, 356)
        if s.get_at((x, y))[3]:
            pygame.draw.ellipse(s, rng.choice([rock_l, rock_d, darken(rock, 0.1)]), (x, y, rng.randrange(8, 22),
                                                                                       rng.randrange(4, 9)))
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        pygame.draw.line(s, rock_l, (x0, y0), (x1, y1), 2)
    pygame.draw.ellipse(s, (70, 120, 140), (22, 200, 30, 7))         # a rock pool, with a starfish
    pygame.draw.ellipse(s, (110, 160, 176), (26, 201, 22, 4))
    s.fill((240, 140, 80), (38, 202, 3, 1))
    s.fill((240, 140, 80), (39, 201, 1, 3))
    weed = (88, 104, 56) if season != 3 else (96, 106, 80)
    for i in range(40):                                               # bladderwrack down at the waterline
        x = 70 + i * 2 + rng.randrange(-2, 3)
        y = 230 + int((x - 70) * 1.1) + rng.randrange(-4, 4)
        if y < 356:
            pygame.draw.line(s, weed if i % 2 else darken(weed, 0.2), (x, y), (x + rng.randrange(-3, 4), y + 8), 2)
    for _ in range(30):
        x = rng.randrange(0, 120)
        y = rng.randrange(208, 300)
        if s.get_at((x, y))[3]:
            s.set_at((x, y), (220, 216, 206))                           # barnacles
    if season == 3:
        for (x0, y0), (x1, y1) in zip(pts[:4], pts[1:5]):
            pygame.draw.line(s, (240, 244, 250), (x0, y0 - 1), (x1, y1 - 1), 2)
    for gx, gy in ((34, 192),):
        s.fill((240, 240, 244), (gx - 3, gy - 6, 8, 5))
        s.fill((150, 156, 166), (gx - 2, gy - 6, 6, 2))
        s.fill((240, 240, 244), (gx + 3, gy - 9, 3, 3))
        s.set_at((gx + 6, gy - 8), (240, 180, 60))
    return s


def make_map(season):
    """The lake map for the rowboat, 300x220 art pixels."""
    w, h = 300, 220
    rng = random.Random(21)
    s = pygame.Surface((w, h))
    land = {0: (128, 176, 96), 1: (110, 162, 82), 2: (186, 160, 92), 3: (228, 234, 242)}[season]
    s.fill(land)
    for _ in range(900):
        s.set_at((rng.randrange(w), rng.randrange(h)), darken(land, rng.uniform(0.04, 0.12)))
    # trees on land (painted first; the water is drawn over them)
    tree = TREE_PAL[season]['pine'][1]
    rt = TREE_PAL[season]['round'][0]
    lake_mask = pygame.Rect(26, 24, 248, 168)
    for _ in range(230):
        x, y = rng.randrange(4, w - 4), rng.randrange(6, h - 2)
        dx, dy = (x - lake_mask.centerx) / (lake_mask.w / 2), (y - lake_mask.centery) / (lake_mask.h / 2)
        if dx * dx + dy * dy < 1.0 or math.hypot(x - 98, y - 182) < 40 or (x > 240 and y < 60 and abs((300 - x) - (y - 6) * 1.1) < 14):
            continue
        if rng.random() < 0.6:
            pygame.draw.polygon(s, darken(tree, 0.1), [(x, y - 5), (x - 3, y + 1), (x + 3, y + 1)])
            s.set_at((x, y - 5), lighten(tree, 0.2) if season != 3 else (240, 244, 250))
        else:
            pygame.draw.circle(s, darken(rt, 0.12), (x + 1, y), 3)
            pygame.draw.circle(s, rt, (x, y - 1), 3)
    water = (92, 150, 180) if season != 3 else (150, 190, 214)
    edge = lighten(water, 0.18)
    lake = pygame.Rect(32, 30, 236, 156)
    pygame.draw.ellipse(s, edge, lake.inflate(6, 6))
    pygame.draw.circle(s, edge, (98, 182), 33)
    pygame.draw.ellipse(s, water, lake)
    pygame.draw.circle(s, water, (98, 182), 30)
    # the creek coming in from the top right
    pts = [(300, 6), (288, 14), (276, 24), (266, 36), (252, 50)]
    pygame.draw.lines(s, edge, False, pts, 11)
    pygame.draw.lines(s, water, False, pts, 7)
    # the deep water
    deep = darken(water, 0.22)
    pygame.draw.ellipse(s, darken(water, 0.1), (118, 72, 96, 58))
    pygame.draw.ellipse(s, deep, (132, 82, 68, 38))
    pygame.draw.ellipse(s, darken(deep, 0.15), (146, 92, 40, 18))
    # little waves
    for _ in range(60):
        x, y = rng.randrange(40, 262), rng.randrange(38, 210)
        if s.get_at((x, y))[:3] == water:
            s.fill(lighten(water, 0.25), (x, y, 3, 1))
    # lily pads in the cove
    if season != 3:
        for _ in range(16):
            x, y = 98 + rng.randint(-22, 22), 184 + rng.randint(-14, 16)
            if s.get_at((x, y))[:3] in (water, lighten(water, 0.25)):
                pygame.draw.circle(s, (86, 140, 72), (x, y), 2)
                if rng.random() < 0.4:
                    s.set_at((x, y - 1), (250, 200, 220))
    # the willow at the creek mouth
    wl = {0: (150, 196, 96), 1: (104, 160, 72), 2: (214, 176, 70), 3: (170, 160, 150)}[season]
    pygame.draw.circle(s, darken(wl, 0.2), (263, 66), 7)
    pygame.draw.circle(s, wl, (262, 64), 6)
    for i in range(-5, 6, 2):
        pygame.draw.line(s, darken(wl, 0.1), (262 + i, 64), (262 + i, 70))
    # the cabin and the dock
    s.fill((150, 104, 70), (14, 102, 12, 8))
    pygame.draw.polygon(s, (132, 66, 54), [(12, 103), (20, 96), (28, 103)])
    s.fill((255, 214, 140), (22, 105, 2, 2))
    pygame.draw.line(s, (164, 118, 78), (28, 108), (44, 108), 2)
    return s


# ---------------------------------------------------------------- fish sprites
FW, FH = 48, 24
SHAPES = {'normal': (28, 11, 8, 5), 'round': (25, 15, 8, 7), 'small': (20, 7, 6, 4), 'long': (34, 8, 7, 5),
          'gar': (28, 8, 6, 5), 'eel': (38, 6, 0, 0), 'catfish': (30, 11, 8, 6), 'sturgeon': (32, 10, 8, 6),
          'spirit': (27, 11, 11, 8)}


def _outline(s, col):
    m = pygame.mask.from_surface(s, 1)
    w, h = s.get_size()
    pts = []
    for y in range(h):
        for x in range(w):
            if m.get_at((x, y)):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and m.get_at((nx, ny)):
                    pts.append((x, y))
                    break
    for p in pts:
        s.set_at(p, col)


def _fish(spec):
    shape = spec['shape']
    bl, bh, tl, th = SHAPES[shape]
    s = pygame.Surface((FW, FH), pygame.SRCALPHA)
    cy = FH // 2
    x0 = (FW - (bl + tl)) // 2 + tl
    if shape == 'gar':
        x0 -= 4
    c1, c2, c3 = spec['c1'], spec['c2'], spec['c3']
    pc = spec['pc'] or darken(c1, 0.3)
    seed = seed_of(spec['id'])
    # tail
    if tl:
        if shape in ('normal', 'small', 'long', 'sturgeon', 'gar'):
            pts = [(x0 + 2, cy), (x0 - tl, cy - th), (x0 - tl + 3, cy), (x0 - tl, cy + th)]
        elif shape == 'spirit':
            pts = [(x0 + 2, cy), (x0 - tl, cy - th - 2), (x0 - tl + 5, cy - 1), (x0 - tl - 1, cy + 1),
                   (x0 - tl + 4, cy + 3), (x0 - tl, cy + th + 2)]
        else:
            pts = [(x0 + 2, cy), (x0 - tl, cy - th), (x0 - tl - 1, cy), (x0 - tl, cy + th)]
        pygame.draw.polygon(s, c3, pts)
    top = cy - bh // 2
    mx = x0 + bl // 2
    if shape == 'eel':
        pygame.draw.rect(s, c3, (x0 + 4, cy - bh // 2 - 1, bl - 12, bh + 2))
        pygame.draw.polygon(s, c3, [(x0 - 3, cy), (x0 + 6, cy - 4), (x0 + 6, cy + 4)])
    else:
        dh = 5 if shape in ('round', 'spirit') else 4
        pygame.draw.polygon(s, c3, [(mx - 7, top + 2), (mx - 3, top - dh), (mx + 4, top + 1)])
        pygame.draw.polygon(s, c3, [(mx - 3, cy + bh // 2 - 1), (mx - 1, cy + bh // 2 + 3), (mx + 3, cy + bh // 2 - 1)])
        if shape == 'spirit':
            pygame.draw.polygon(s, c3, [(mx - 9, top + 2), (mx - 12, top - 4), (mx - 4, top)])
    body = pygame.Surface((FW, FH), pygame.SRCALPHA)
    white = (255, 255, 255)
    if shape == 'eel':
        pygame.draw.ellipse(body, white, (x0 - 2, cy - bh // 2, bl + 2, bh))
    else:
        pygame.draw.ellipse(body, white, (x0, cy - bh // 2, bl, bh))
    if shape == 'gar':
        pygame.draw.rect(body, white, (x0 + bl - 3, cy - 1, 10, 3))
    if shape == 'sturgeon':
        pygame.draw.polygon(body, white, [(x0 + bl - 4, cy - 3), (x0 + bl + 5, cy + 1), (x0 + bl - 4, cy + 3)])
    if shape == 'catfish':
        pygame.draw.rect(body, white, (x0 + bl - 11, cy - bh // 2 + 2, 10, bh - 3), border_radius=3)
    mask = pygame.mask.from_surface(body)
    bt = cy - bh / 2
    for y in range(FH):
        for x in range(FW):
            if not mask.get_at((x, y)):
                continue
            t = (y - bt) / max(1, bh)
            col = c1 if t < 0.5 else c2
            if 0.42 <= t < 0.58:
                col = lerp_c(c1, c2, 0.5)
            if t < 0.2:
                col = lighten(col, 0.14)
            h_ = ((x * 7349 + y * 3571 + seed) * 2654435761 >> 7) % 100
            p = spec['pattern']
            if p == 'stripes':
                if t < 0.8 and x0 + 4 < x < x0 + bl - 9 and (x - x0) % 6 in (0, 1):
                    col = pc
            elif p == 'spots':
                if t < 0.82 and h_ < 13:
                    col = pc
            elif p == 'scales':
                if t < 0.85 and y % 2 == 0 and (x + (y // 2) * 2) % 4 == 0:
                    col = darken(col, 0.13)
            elif p == 'rainbow':
                if 0.36 <= t < 0.56:
                    col = pc
                elif t < 0.36 and h_ < 10:
                    col = darken(c1, 0.35)
            elif p == 'glow':
                if t < 0.32 and x % 4 == 0:
                    col = pc
                elif t > 0.6:
                    col = lighten(col, 0.15)
            elif p == 'koi':
                v = math.sin(x * 0.42 + seed % 7) + math.sin(y * 0.8 + x * 0.21 + seed % 5)
                if v > 0.45:
                    col = pc
            elif p == 'scutes':
                if t < 0.24 and x % 3 == 0:
                    col = pc
            s.set_at((x, y), col)
    # gill line
    gx = x0 + bl - (7 if shape == 'eel' else 10)
    if shape == 'gar':
        gx = x0 + bl - 7
    for y in range(cy - 3, cy + 3):
        if 0 <= y < FH and mask.get_at((gx, y)):
            s.set_at((gx, y), darken(s.get_at((gx, y))[:3], 0.25))
    # pectoral fin
    if shape != 'eel':
        pygame.draw.polygon(s, c3, [(gx - 1, cy + 1), (gx - 6, cy + 4), (gx - 1, cy + 3)])
    # eye
    ex = x0 + bl - (4 if shape in ('gar', 'eel', 'catfish') else 5)
    ey = cy - (1 if shape in ('eel', 'small', 'long', 'gar') else 2)
    s.set_at((ex, ey), (24, 24, 34))
    s.set_at((ex, ey - 1), (250, 250, 240))
    if shape not in ('small', 'eel'):
        s.set_at((ex - 1, ey), (24, 24, 34))
    if shape == 'catfish':
        dk = darken(c1, 0.5)
        pygame.draw.line(s, dk, (x0 + bl - 1, cy + 1), (x0 + bl + 5, cy + 5))
        pygame.draw.line(s, dk, (x0 + bl - 3, cy + 2), (x0 + bl + 2, cy + 7))
        pygame.draw.line(s, dk, (x0 + bl - 1, cy - 1), (x0 + bl + 5, cy - 4))
    _outline(s, darken(c1, 0.55))
    if shape == 'spirit':
        s.set_alpha(215)
    return s


def _critter(spec):
    """Crab pot catches: crayfish, crabs and snails."""
    s = pygame.Surface((FW, FH), pygame.SRCALPHA)
    c1, c2, c3 = spec['c1'], spec['c2'], spec['c3']
    d = pygame.draw
    shape = spec['shape']
    if shape == 'crab':
        for i in range(3):                                        # legs
            d.line(s, darken(c1, 0.2), (17 + i * 4, 15), (13 + i * 3, 21))
            d.line(s, darken(c1, 0.2), (27 + i * 3, 15), (33 + i * 3, 21))
        d.ellipse(s, c1, (15, 8, 20, 11))
        d.ellipse(s, c2, (18, 9, 14, 6))
        for cx, cy in ((11, 9), (38, 9)):                         # claws
            d.circle(s, c1, (cx, cy), 4)
            d.line(s, (30, 20, 20), (cx - 2, cy - 1), (cx + 2, cy - 1))
        d.line(s, c1, (15, 12), (12, 10), 2)
        d.line(s, c1, (34, 12), (37, 10), 2)
        for ex in (22, 28):
            d.line(s, c1, (ex, 9), (ex, 6))
            s.set_at((ex, 5), (20, 20, 20))
    elif shape == 'crayfish':
        d.ellipse(s, c1, (6, 10, 10, 6))                          # tail fan
        for i in range(4):
            d.ellipse(s, c1 if i % 2 else c2, (12 + i * 4, 9, 6, 8))
        d.ellipse(s, c1, (26, 8, 12, 9))
        d.line(s, c1, (36, 10), (42, 5), 2)
        d.line(s, c1, (36, 14), (42, 18), 2)
        d.circle(s, c1, (43, 4), 3)
        d.circle(s, c1, (43, 19), 3)
        d.line(s, darken(c1, 0.3), (37, 9), (46, 2))
        s.set_at((35, 10), (20, 20, 20))
        for i in range(3):
            d.line(s, darken(c1, 0.2), (27 + i * 3, 16), (26 + i * 3, 20))
    else:                                                         # snail
        d.ellipse(s, c2, (10, 15, 26, 5))
        d.circle(s, c1, (22, 11), 8)
        d.circle(s, c3, (22, 11), 5, 1)
        d.circle(s, c3, (23, 11), 2, 1)
        d.line(s, c2, (33, 15), (37, 9))
        d.line(s, c2, (35, 15), (40, 10))
        s.set_at((37, 8), (30, 30, 30))
        s.set_at((40, 9), (30, 30, 30))
    _outline(s, darken(c1, 0.5))
    return s


def _axolotl(spec):
    s = pygame.Surface((FW, FH), pygame.SRCALPHA)
    c1, c2, c3 = spec['c1'], spec['c2'], spec['c3']
    pygame.draw.ellipse(s, c2, (3, 9, 16, 6))
    pygame.draw.ellipse(s, c1, (12, 9, 22, 8))
    for lx in (16, 27):
        pygame.draw.rect(s, darken(c1, 0.12), (lx, 15, 2, 3))
    pygame.draw.ellipse(s, c1, (29, 6, 13, 11))
    for (a, b) in (((31, 8), (28, 3)), ((33, 7), (32, 2)), ((35, 7), (36, 2)),
                   ((31, 15), (28, 19)), ((33, 16), (32, 21))):
        pygame.draw.line(s, c3, a, b)
    s.set_at((38, 10), (30, 24, 34))
    s.set_at((38, 9), (255, 255, 255))
    s.set_at((40, 14), (180, 80, 110))
    s.set_at((39, 14), (180, 80, 110))
    _outline(s, darken(c1, 0.5))
    return s


def _junk(kind):
    s = pygame.Surface((FW, FH), pygame.SRCALPHA)
    if kind == 'boot':
        c = (110, 78, 52)
        pygame.draw.rect(s, c, (16, 3, 9, 13))
        pygame.draw.rect(s, c, (16, 12, 18, 6), border_radius=2)
        pygame.draw.rect(s, (60, 44, 34), (15, 18, 20, 2))
        for y in range(5, 12, 3):
            pygame.draw.line(s, (220, 210, 180), (18, y), (23, y))
        _outline(s, (60, 40, 28))
    elif kind == 'can':
        pygame.draw.rect(s, (170, 176, 180), (18, 4, 12, 16))
        pygame.draw.rect(s, (196, 80, 70), (18, 8, 12, 7))
        pygame.draw.line(s, (240, 230, 200), (20, 11), (27, 11))
        pygame.draw.line(s, (220, 226, 230), (19, 5), (19, 19))
        s.set_at((26, 17), (150, 100, 60))
        s.set_at((27, 18), (150, 100, 60))
        _outline(s, (80, 84, 90))
    elif kind == 'driftwood':
        pygame.draw.polygon(s, (186, 160, 128), [(4, 13), (12, 9), (30, 8), (44, 11), (40, 15), (24, 16), (8, 16)])
        pygame.draw.line(s, (220, 200, 170), (10, 11), (36, 10))
        pygame.draw.line(s, (186, 160, 128), (28, 9), (33, 4))
        pygame.draw.circle(s, (150, 126, 100), (20, 13), 2)
        _outline(s, (110, 90, 70))
    elif kind == 'bottle':
        g = (110, 170, 130)
        pygame.draw.rect(s, g, (12, 8, 20, 9), border_radius=4)
        pygame.draw.rect(s, g, (31, 10, 7, 5))
        pygame.draw.rect(s, (170, 130, 90), (38, 10, 3, 5))
        pygame.draw.rect(s, (240, 230, 200), (16, 10, 12, 5))
        pygame.draw.line(s, (200, 240, 210), (14, 9), (28, 9))
        _outline(s, (60, 100, 76))
    elif kind == 'clam':
        pygame.draw.ellipse(s, (232, 200, 196), (14, 6, 20, 12))
        for i in range(4):
            pygame.draw.line(s, (206, 170, 168), (24, 17), (16 + i * 5, 7))
        pygame.draw.ellipse(s, (210, 176, 172), (14, 13, 20, 6))
        pygame.draw.circle(s, (250, 250, 255), (24, 14), 2)
        s.set_at((23, 13), (255, 255, 255))
        _outline(s, (150, 110, 110))
    return s


_sprite_cache = {}


def fish_sprite(spec, scale=1):
    key = (spec['id'], scale)
    if key in _sprite_cache:
        return _sprite_cache[key]
    base = _sprite_cache.get((spec['id'], 1))
    if base is None:
        if spec.get('junk'):
            base = _junk(spec['shape'])
        elif spec['shape'] == 'axolotl':
            base = _axolotl(spec)
        elif spec['shape'] in ('crab', 'crayfish', 'snail'):
            base = _critter(spec)
        else:
            base = _fish(spec)
        _sprite_cache[(spec['id'], 1)] = base
    if scale == 1:
        return base
    out = pygame.transform.scale(base, (FW * scale, FH * scale))
    if spec.get('shape') == 'spirit':
        out.set_alpha(215)
    _sprite_cache[key] = out
    return out


def silhouette(spec, scale):
    key = ('sil', spec['id'], scale)
    if key in _sprite_cache:
        return _sprite_cache[key]
    src = fish_sprite(spec, scale)
    m = pygame.mask.from_surface(src, 1)
    out = m.to_surface(setcolor=(96, 84, 74, 255), unsetcolor=(0, 0, 0, 0))
    _sprite_cache[key] = out
    return out


# ---------------------------------------------------------------- item icons (16x16 pixel art)
EXTRA_ICONS = {}       # item id -> function returning a 16x16 icon (gear from seasons.py, furniture...)


def item_icon(item_id, scale=3, color=None):
    key = ('icon', item_id, scale)
    if key in _sprite_cache:
        return _sprite_cache[key]
    if item_id in EXTRA_ICONS:
        s = EXTRA_ICONS[item_id]()
        if scale != 1:
            s = pygame.transform.scale(s, (16 * scale, 16 * scale))
        _sprite_cache[key] = s
        return s
    if item_id.startswith('lure_'):
        import legends
        s = legends.lure_icon(item_id)
        if scale != 1:
            s = pygame.transform.scale(s, (16 * scale, 16 * scale))
        _sprite_cache[key] = s
        return s
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    d = pygame.draw
    if item_id in ('twig', 'bamboo', 'willow', 'starlight'):
        col = color or (160, 120, 80)
        d.line(s, (90, 60, 40), (2, 14), (5, 11), 2)
        d.line(s, col, (5, 11), (14, 2))
        d.circle(s, (120, 120, 130), (6, 12), 2)
        d.line(s, (230, 230, 220), (14, 2), (14, 9))
        d.rect(s, (220, 60, 60), (13, 9, 3, 2))
        d.rect(s, (250, 250, 250), (13, 11, 3, 1))
        if item_id == 'starlight':
            for p in ((10, 3), (3, 6), (12, 13)):
                s.set_at(p, (255, 255, 200))
        if item_id == 'bamboo':
            for p in ((8, 8), (11, 5)):
                s.set_at(p, (130, 120, 60))
    elif item_id == 'lantern':
        d.line(s, (60, 60, 60), (8, 1), (8, 3))
        d.rect(s, (70, 64, 60), (5, 3, 7, 2))
        d.rect(s, (255, 200, 110), (5, 5, 7, 7))
        d.rect(s, (255, 240, 190), (7, 7, 3, 3))
        d.rect(s, (70, 64, 60), (5, 5, 7, 7), 1)
        d.rect(s, (70, 64, 60), (4, 12, 9, 2))
    elif item_id == 'worm':
        for i in range(10):
            s.set_at((3 + i, 8 + int(2 * math.sin(i * 0.9))), (226, 130, 140))
            s.set_at((3 + i, 9 + int(2 * math.sin(i * 0.9))), (196, 100, 112))
    elif item_id == 'corn':
        d.ellipse(s, (250, 210, 80), (4, 2, 8, 12))
        for y in range(4, 13, 2):
            d.line(s, (220, 170, 50), (5, y), (10, y))
        d.polygon(s, (120, 170, 80), [(4, 14), (2, 6), (7, 12)])
        d.polygon(s, (120, 170, 80), [(12, 14), (14, 6), (9, 12)])
    elif item_id == 'glow':
        d.circle(s, (100, 160, 60), (8, 8), 6)
        d.ellipse(s, (210, 255, 140), (4, 5, 9, 6))
        d.ellipse(s, (250, 255, 210), (6, 6, 4, 3))
    elif item_id == 'golden':
        d.ellipse(s, (240, 190, 60), (3, 5, 9, 6))
        d.polygon(s, (220, 160, 40), [(3, 8), (0, 5), (0, 11)])
        s.set_at((9, 7), (40, 30, 20))
        d.line(s, (190, 190, 200), (12, 8), (14, 8))
        d.arc(s, (190, 190, 200), (11, 8, 5, 6), 3.1, 6.3)
        s.set_at((6, 6), (255, 250, 200))
    elif item_id == 'flowers':
        d.polygon(s, (190, 100, 70), [(4, 9), (12, 9), (11, 15), (5, 15)])
        d.line(s, (90, 150, 70), (8, 9), (8, 4))
        d.line(s, (90, 150, 70), (6, 9), (5, 5))
        d.circle(s, (240, 120, 150), (8, 3), 2)
        d.circle(s, (250, 220, 100), (5, 4), 2)
        d.circle(s, (200, 160, 250), (11, 5), 2)
    elif item_id == 'teaset':
        d.ellipse(s, (120, 150, 170), (2, 6, 10, 8))
        d.line(s, (120, 150, 170), (11, 9), (14, 6))
        d.arc(s, (90, 110, 130), (1, 4, 6, 6), 1.5, 4.5)
        d.rect(s, (90, 110, 130), (5, 5, 4, 2))
        d.line(s, (230, 230, 240), (7, 2), (8, 0))
    elif item_id == 'catbed':
        d.ellipse(s, (200, 80, 80), (1, 7, 14, 7))
        d.ellipse(s, (230, 120, 110), (3, 8, 10, 4))
        d.ellipse(s, (240, 160, 90), (4, 5, 8, 5))
        s.set_at((10, 5), (240, 160, 90))
        s.set_at((11, 4), (240, 160, 90))
    elif item_id == 'chimes':
        d.line(s, (120, 90, 60), (2, 2), (14, 2))
        for i, ln in enumerate((7, 10, 8, 11)):
            x = 4 + i * 3
            d.line(s, (200, 200, 210), (x, 2), (x, 2 + ln))
            s.set_at((x, 2 + ln), (240, 240, 250))
    elif item_id == 'feeder':
        d.line(s, (110, 80, 60), (8, 8), (8, 15))
        d.polygon(s, (170, 70, 60), [(2, 5), (8, 1), (14, 5)])
        d.rect(s, (200, 160, 110), (4, 5, 9, 4))
        d.rect(s, (230, 200, 120), (5, 8, 7, 1))
    elif item_id == 'lights':
        pts = [(1, 4), (5, 8), (8, 9), (11, 8), (15, 4)]
        d.lines(s, (80, 70, 60), False, pts)
        for p, c in zip(pts[1:4], ((255, 210, 120), (255, 150, 140), (200, 240, 150))):
            d.circle(s, c, (p[0], p[1] + 2), 2)
    elif item_id == 'lanterns':
        d.ellipse(s, (240, 110, 80), (3, 3, 10, 10))
        d.ellipse(s, (255, 190, 120), (5, 5, 6, 6))
        d.line(s, (120, 60, 40), (3, 8), (12, 8))
        d.rect(s, (90, 50, 40), (6, 13, 4, 2))
    elif item_id == 'moon':
        d.circle(s, (250, 236, 170), (8, 8), 6)
        d.circle(s, (0, 0, 0, 0), (11, 6), 5)
        d.line(s, (190, 190, 200), (8, 1), (8, 3))
        s.set_at((13, 12), (255, 255, 220))
        s.set_at((3, 3), (255, 255, 220))
    elif item_id == 'storm':
        d.ellipse(s, (90, 120, 100), (5, 6, 6, 7))
        d.polygon(s, (170, 200, 230), [(8, 7), (1, 3), (3, 9)])
        d.polygon(s, (170, 200, 230), [(8, 7), (15, 3), (13, 9)])
        d.polygon(s, (250, 220, 90), [(9, 9), (7, 12), (9, 12), (7, 15)])
    elif item_id.startswith('hat_'):
        h = item_id[4:]
        if h == 'straw':
            d.rect(s, (232, 204, 124), (1, 9, 14, 3))
            d.rect(s, (232, 204, 124), (4, 4, 8, 6))
            d.rect(s, (196, 82, 72), (4, 8, 8, 2))
        elif h == 'bucket':
            d.polygon(s, (100, 134, 94), [(1, 12), (15, 12), (13, 9), (3, 9)])
            d.rect(s, (122, 156, 112), (4, 3, 8, 7))
        elif h == 'beret':
            d.ellipse(s, (184, 62, 74), (2, 5, 13, 7))
            d.rect(s, (140, 40, 54), (3, 10, 10, 2))
            d.line(s, (140, 40, 54), (8, 5), (8, 3))
        elif h == 'flower':
            d.arc(s, (110, 170, 90), (1, 4, 14, 10), 0, 3.14, 2)
            for p, c in (((3, 8), (250, 160, 190)), ((6, 5), (255, 236, 120)), ((10, 5), (255, 255, 255)),
                         ((13, 8), (230, 140, 220))):
                d.circle(s, c, p, 2)
        elif h == 'captain':
            d.rect(s, (244, 244, 240), (3, 3, 10, 7))
            d.rect(s, (40, 44, 60), (3, 9, 10, 2))
            d.rect(s, (40, 44, 60), (9, 11, 6, 2))
            d.rect(s, (240, 196, 70), (7, 5, 2, 2))
        elif h == 'frog':
            d.ellipse(s, (112, 184, 92), (2, 5, 12, 9))
            for ex in (4, 11):
                d.circle(s, (255, 255, 250), (ex, 5), 2)
                s.set_at((ex, 5), (30, 30, 30))
        elif h == 'beanie':
            d.ellipse(s, (90, 122, 200), (2, 4, 12, 10))
            d.rect(s, (150, 176, 230), (2, 10, 12, 3))
            d.circle(s, (250, 250, 250), (8, 3), 2)
        elif h == 'party':
            d.polygon(s, (236, 110, 150), [(3, 14), (13, 14), (8, 2)])
            d.line(s, (110, 190, 220), (5, 10), (11, 10), 2)
            d.line(s, (110, 190, 220), (7, 6), (9, 6), 1)
            d.circle(s, (255, 230, 120), (8, 2), 2)
        elif h == 'lanternhat':
            d.rect(s, (70, 56, 50), (2, 12, 12, 2))
            d.rect(s, (70, 56, 50), (4, 4, 8, 9))
            d.rect(s, (255, 210, 120), (5, 5, 6, 6))
            d.rect(s, (255, 246, 200), (7, 6, 2, 3))
            d.rect(s, (70, 56, 50), (6, 1, 4, 3))
        elif h == 'tophat':
            d.rect(s, (40, 36, 46), (1, 12, 14, 2))
            d.rect(s, (40, 36, 46), (4, 2, 8, 11))
            d.rect(s, (190, 60, 70), (4, 9, 8, 2))
            d.line(s, (80, 74, 92), (5, 3), (5, 8))
    elif item_id.startswith('cat_'):
        c = item_id[4:]
        if c == 'none':
            d.circle(s, (232, 150, 78), (8, 9), 5)
            d.polygon(s, (232, 150, 78), [(3, 7), (4, 2), (7, 5)])
            d.polygon(s, (232, 150, 78), [(13, 7), (12, 2), (9, 5)])
            s.set_at((6, 9), (60, 70, 40))
            s.set_at((10, 9), (60, 70, 40))
        elif c == 'bell':
            d.arc(s, (200, 60, 60), (1, 1, 14, 10), 3.4, 6.0, 2)
            d.circle(s, (246, 200, 70), (8, 11), 4)
            s.set_at((8, 13), (120, 90, 30))
        elif c == 'scarf':
            d.rect(s, (86, 150, 200), (1, 5, 14, 4))
            d.rect(s, (86, 150, 200), (3, 8, 4, 7))
            for x in range(2, 15, 3):
                s.set_at((x, 6), (240, 240, 240))
        elif c == 'crown':
            d.polygon(s, (246, 204, 70), [(2, 13), (2, 5), (5, 9), (8, 3), (11, 9), (14, 5), (14, 13)])
            d.circle(s, (220, 80, 90), (8, 10), 1)
        elif c == 'bow':
            d.polygon(s, (236, 120, 170), [(8, 8), (2, 3), (2, 13)])
            d.polygon(s, (236, 120, 170), [(8, 8), (14, 3), (14, 13)])
            d.circle(s, (200, 80, 130), (8, 8), 2)
    elif item_id == 'pinwheel':
        d.line(s, (206, 196, 176), (8, 8), (8, 15))
        for i, c in enumerate(((240, 100, 100), (250, 210, 90), (110, 170, 230), (130, 200, 120))):
            a = i * math.pi / 2 + 0.3
            d.polygon(s, c, [(8, 7), (8 + math.cos(a) * 7, 7 + math.sin(a) * 7),
                             (8 + math.cos(a + 0.9) * 4, 7 + math.sin(a + 0.9) * 4)])
    elif item_id == 'telescope':
        d.line(s, (196, 160, 80), (2, 10), (14, 3), 3)
        d.line(s, (92, 70, 54), (8, 7), (5, 15))
        d.line(s, (92, 70, 54), (8, 7), (11, 15))
    elif item_id == 'bench':
        d.rect(s, (150, 100, 66), (1, 5, 14, 2))
        d.rect(s, (150, 100, 66), (1, 9, 14, 2))
        d.rect(s, (112, 74, 50), (2, 5, 1, 10))
        d.rect(s, (112, 74, 50), (13, 5, 1, 10))
    elif item_id == 'rowboat':
        d.polygon(s, (92, 130, 150), [(0, 7), (16, 7), (13, 12), (3, 12)])
        d.line(s, (236, 230, 214), (0, 7), (15, 7))
        d.line(s, (120, 88, 60), (5, 8), (1, 14))
    elif item_id == 'gnome':
        d.polygon(s, (210, 70, 70), [(4, 7), (12, 7), (8, 0)])
        d.rect(s, (240, 214, 190), (5, 7, 6, 3))
        d.rect(s, (250, 250, 250), (4, 9, 8, 3))
        d.rect(s, (80, 110, 170), (4, 11, 8, 4))
    elif item_id == 'sell':
        d.circle(s, (240, 190, 70), (8, 8), 6)
        d.circle(s, (210, 150, 40), (8, 8), 4, 1)
    out = pygame.transform.scale(s, (16 * scale, 16 * scale))
    _sprite_cache[key] = out
    return out
