"""Colour morphs: now and then a fish bites in colours it doesn't usually wear.

Six morphs, each a recolouring of the species' own sprite (so every fish in the game has all six): Golden, Ghost,
Shadow, Koi, Starry (only bites at night) and Prism (only in the rain). A catch is a morph about one time in fifty.
Morphs don't go in the basket, so cooking, requests and the market can't spend them by accident: they go to the
hatchery pond by the cabin (hatchery.py), the tank, or back into the lake.
"""
import math
import random
import zlib

import numpy as np
import pygame

# ramp: the colours the sprite's light-to-dark is mapped onto (dark first). mult: what it sells for.
MORPHS = [
    dict(id='golden', name='Golden', w=1, mult=5, col=(214, 160, 36),
         ramp=((88, 50, 16), (168, 106, 28), (228, 172, 48), (252, 222, 112), (255, 250, 214)),
         desc='Scales like a coin in the sun. The rarest of them all.'),
    dict(id='ghost', name='Ghost', w=3, mult=3, col=(176, 160, 184),
         ramp=((148, 118, 128), (208, 190, 196), (236, 228, 228), (248, 244, 240), (255, 255, 255)),
         desc='Pale as morning mist, with a blush of pink.'),
    dict(id='shadow', name='Shadow', w=3, mult=3, col=(62, 74, 104),
         ramp=((12, 14, 24), (28, 34, 52), (46, 58, 84), (74, 94, 126), (128, 158, 194)),
         desc='Dark as deep water, with a blue sheen when it turns.'),
    dict(id='koi', name='Koi', w=2, mult=3, col=(222, 110, 56),
         ramp=((112, 92, 84), (200, 180, 162), (238, 226, 208), (250, 242, 230), (255, 255, 250)),
         desc='Patched in cream, orange and ink, never twice the same way.'),
    dict(id='starry', name='Starry', w=2, mult=4, col=(70, 82, 164), when='night',
         ramp=((10, 12, 38), (24, 30, 76), (42, 54, 118), (70, 88, 162), (118, 138, 208)),
         desc='Night-blue and freckled with stars. Only bites after dark.'),
    dict(id='prism', name='Prism', w=2, mult=4, col=(150, 108, 196), when='rain',
         ramp=None, desc='Bands of colour like oil on a puddle. Only bites in the rain.'),
]
MORPH_BY_ID = {m['id']: m for m in MORPHS}
IDS = [m['id'] for m in MORPHS]

WILD = 0.02           # a catch's chance of being a morph
STOCKED = 0.10        # extra chance for a species you've released young of that colour into
NO_SHAPES = ('crab', 'crayfish', 'snail', 'spirit')


def can_morph(spec):
    """Real fish only: not junk, crabs, snails, the lake spirit or the legends."""
    return bool(spec) and not spec.get('junk') and spec.get('shape') not in NO_SHAPES and spec['rarity'] < 5 \
        and spec.get('spot') != 'pot'


def biting(g):
    """The morphs that can bite right now."""
    out = []
    for m in MORPHS:
        if m.get('when') == 'night' and g.env.nf < 0.5:
            continue
        if m.get('when') == 'rain' and g.weather != 'rain':
            continue
        out.append(m)
    return out


def roll(g, spec, rng, hot=False):
    """None, or the id of the morph this catch turned out to be."""
    if not can_morph(spec):
        return None
    now = biting(g)
    if not now:
        return None
    stock = g.hatch['stock'].get(spec['id']) if hasattr(g, 'hatch') else None
    if stock and stock['until'] >= g.day and any(m['id'] == stock['v'] for m in now):
        if rng.random() < STOCKED:
            return stock['v']
    p = WILD * (1.5 if hot else 1.0) * (1 + 0.1 * getattr(g, 'luck', 0.0))
    if rng.random() >= p:
        return None
    total = sum(m['w'] for m in now)
    x = rng.uniform(0, total)
    for m in now:
        x -= m['w']
        if x <= 0:
            return m['id']
    return now[-1]['id']


def name(spec, v):
    return '%s %s' % (MORPH_BY_ID[v]['name'], spec['name']) if v in MORPH_BY_ID else spec['name']


def mult(v):
    return MORPH_BY_ID[v]['mult'] if v in MORPH_BY_ID else 1


# ---------------------------------------------------------------- the sprites
def _seed(*parts):
    return zlib.crc32('|'.join(str(p) for p in parts).encode())


def recolor(src, v, sid):
    """src (a fish sprite) in morph v's colours. sid seeds the patches and stars, so a species always wears
    the same pattern."""
    m = MORPH_BY_ID[v]
    rgb = pygame.surfarray.array3d(src).astype(np.float32)
    alpha = pygame.surfarray.array_alpha(src)
    on = alpha > 0
    if not on.any():
        return src.copy()
    lum = rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11
    vals = lum[on]
    lo, hi = float(np.percentile(vals, 3)), float(vals.max())
    t = np.clip((lum - lo) / max(1.0, hi - lo), 0.0, 1.0)
    w, h = t.shape
    if m['ramp'] is not None:
        ramp = np.array(m['ramp'], dtype=np.float32)
        pos = t * (len(ramp) - 1)
        i0 = np.clip(pos.astype(int), 0, len(ramp) - 2)
        f = (pos - i0)[..., None]
        out = ramp[i0] * (1 - f) + ramp[i0 + 1] * f
    else:
        # prism: hue runs along the body in soft bands, brightness from the sprite
        xs = np.arange(w, dtype=np.float32)[:, None] / w
        ys = np.arange(h, dtype=np.float32)[None, :] / h
        hue = (xs * 1.6 + ys * 0.4) % 1.0
        out = np.empty((w, h, 3), np.float32)
        for c, off in enumerate((0.0, 1 / 3, 2 / 3)):
            out[..., c] = 0.5 + 0.5 * np.cos(2 * math.pi * (hue - off))
        val = 0.25 + 0.75 * t
        out = (out * 0.55 + 0.45) * val[..., None] * 255
    rng = random.Random(_seed(sid, v))
    inner = on & (t > 0.28)
    if v == 'koi':
        xs = np.arange(w)[:, None]
        ys = np.arange(h)[None, :]
        cols = np.argwhere(inner)
        if len(cols):
            for k in range(rng.choice((3, 4, 4, 5))):
                cx, cy = cols[rng.randrange(len(cols))]
                r = rng.uniform(2.5, 5.5)
                blob = inner & ((xs - cx) ** 2 + ((ys - cy) * 1.4) ** 2 < r * r)
                pc = np.array((232, 112, 44) if k % 3 != 2 else (40, 32, 36), np.float32)
                out[blob] = pc * (0.72 + 0.28 * t[blob][:, None])
    elif v == 'starry':
        cols = np.argwhere(inner)
        for _ in range(max(3, len(cols) // 14)):
            x, y = cols[rng.randrange(len(cols))]
            out[x, y] = (244, 246, 255) if rng.random() < 0.75 else (255, 232, 160)
    elif v == 'golden':
        cols = np.argwhere(on & (t > 0.55))
        for _ in range(min(4, len(cols))):
            x, y = cols[rng.randrange(len(cols))]
            out[x, y] = (255, 255, 240)
    res = src.copy()
    pygame.surfarray.pixels3d(res)[...] = np.clip(out, 0, 255).astype(np.uint8)
    return res


def sprite(spec, v, scale=1):
    """Like art.fish_sprite, in morph v's colours (v None: the usual sprite)."""
    import art
    if v not in MORPH_BY_ID or not can_morph(spec):
        return art.fish_sprite(spec, scale)
    cache = art._sprite_cache
    key = ('morph', spec['id'], v, scale)
    out = cache.get(key)
    if out is None:
        base = cache.get(('morph', spec['id'], v, 1))
        if base is None:
            base = cache[('morph', spec['id'], v, 1)] = recolor(art.fish_sprite(spec, 1), v, spec['id'])
        out = base if scale == 1 else pygame.transform.scale(base, (base.get_width() * scale,
                                                                     base.get_height() * scale))
        cache[key] = out
    return out


def badge(s, ui, v, center, font='tiny'):
    """A little pill with the morph's name, centred on center. Returns its rect."""
    m = MORPH_BY_ID[v]
    tw = ui.fonts[font].size(m['name'])[0]
    r = pygame.Rect(0, 0, tw + 20, 22 if font == 'tiny' else 28)
    r.center = center
    pygame.draw.rect(s, m['col'], r, border_radius=r.h // 2)
    pygame.draw.rect(s, tuple(max(0, c - 50) for c in m['col']), r, 2, border_radius=r.h // 2)
    ui.blit_text(s, m['name'], r.center, font, (255, 255, 250), 'center')
    return r
