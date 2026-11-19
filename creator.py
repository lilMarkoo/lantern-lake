"""The character creator: make your angler (and choose Biscuit's coat) on a little living diorama of the lake.

Opened before a new game starts, and from the cabin wardrobe ("Change your look"). Everything you pick shows at
once on the dock: at dawn, noon, dusk or night, in any season, with the water reflecting it all.
"""
import math
import random

import pygame

import actors
import cookscene
import look as looks
import ui as U
from art import lerp_c, darken, lighten

SEASON_NAMES = ('Spring', 'Summer', 'Autumn', 'Winter')
TABS = (('face', 'Face'), ('hair', 'Hair'), ('clothes', 'Clothes'), ('keep', 'Keepsake'), ('cat', 'Biscuit'))
TODS = (('dawn', 'Dawn'), ('noon', 'Noon'), ('dusk', 'Dusk'), ('night', 'Night'))
DW, DH, WL = 80, 64, 45          # the diorama, in world pixels, and its waterline
ZOOM = 6
ROLL_TIME = 0.9

# sky top, sky bottom, far hills, water, light on the figures
LIGHT = {
    'dawn': ((118, 132, 198), (252, 196, 166), (112, 108, 150), (120, 128, 178), (246, 222, 222)),
    'noon': ((104, 166, 232), (196, 224, 244), (120, 160, 150), (84, 148, 190), (255, 255, 255)),
    'dusk': ((72, 58, 122), (252, 150, 108), (96, 70, 108), (104, 82, 126), (246, 198, 186)),
    'night': ((12, 16, 42), (40, 52, 96), (30, 38, 66), (20, 30, 62), (122, 134, 186)),
}
TREES = {0: (88, 150, 92), 1: (54, 120, 70), 2: (196, 110, 54), 3: (210, 220, 232)}
STARS = [(random.Random(i).randrange(DW), random.Random(i * 7 + 1).randrange(30)) for i in range(26)]


# ---------------------------------------------------------------- opening and closing
def open_(g, mode):
    """mode 'new' (before a new game) or 'edit' (from the wardrobe)."""
    cur = looks.of(g) if mode == 'edit' else looks.DEFAULT
    night = g.night_now() if mode == 'edit' else False
    g.cre = dict(mode=mode, look=dict(cur), start=dict(cur), tab='face', season=g.env.season if mode == 'edit' else 0,
                 tod='night' if night else 'dusk', hat=True, roll=0.0, tick=0.0, final=None, cheer=0.0,
                 last=g.t, fx=[], back=g.overlay)
    g.overlay = 'creator'
    g.audio.play('page', 0.5)


def cancel(g):
    c = g.cre
    g.typing = None
    g.save_settings()
    g.overlay = c['back'] if c['mode'] == 'edit' else None
    g.audio.play('page', 0.5)


def confirm(g):
    c = g.cre
    g.typing = None
    g.save_settings()
    lk = looks.clean(c['look'])
    if c['mode'] == 'new':
        g.overlay = None
        g.start_game(False, look=lk)
    else:
        g.look = lk
        g.overlay = c['back']
        g.audio.play('chime2', 0.5)
        g.save()


def surprise(g):
    c = g.cre
    if c['roll'] > 0:
        return
    c['roll'] = ROLL_TIME
    c['tick'] = 0.0
    c['final'] = looks.random_look()
    g.audio.play('ui', 0.5)


def set_opt(g, field, oid):
    c = g.cre
    c['look'][field] = oid
    if field in ('hstyle', 'hair'):
        c['hat'] = False                 # take the hat off so you can see it
    if field == 'coat':
        c['cheer'] = 0.6
    g.audio.play('ui', 0.4)


def _update(g):
    c = g.cre
    dt = max(0.0, min(0.1, g.t - c['last']))
    c['last'] = g.t
    c['cheer'] = max(0.0, c['cheer'] - dt)
    if c['roll'] > 0:
        c['roll'] -= dt
        c['tick'] -= dt
        if c['roll'] <= 0:
            c['look'] = c['final']
            c['cheer'] = 1.4
            g.audio.play('chime2', 0.6)
            _burst(c)
        elif c['tick'] <= 0:
            c['tick'] = 0.075
            c['look'] = looks.random_look()
            g.audio.play('ui', 0.15)
    for p in c['fx']:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[3] += 260 * dt
        p[4] -= dt
    c['fx'] = [p for p in c['fx'] if p[4] > 0]


def _burst(c):
    rng = random.Random()
    cols = [(255, 214, 110), (236, 120, 150), (120, 200, 230), (160, 220, 120), (250, 250, 240)]
    for _ in range(46):
        a = rng.uniform(0, math.tau)
        sp = rng.uniform(80, 320)
        c['fx'].append([0.0, 0.0, math.cos(a) * sp, math.sin(a) * sp - 140, rng.uniform(0.6, 1.3), rng.choice(cols)])


# ---------------------------------------------------------------- little renders of you
_CACHE = {}


def _cached(key, make):
    if key not in _CACHE:
        if len(_CACHE) > 600:
            _CACHE.clear()
        _CACHE[key] = make()
    return _CACHE[key]


def figure(lk, season, hat, pose='', cheer=False):
    """You standing on a 26x40 surface, feet at (13, 38)."""
    def make():
        tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
        actors.draw_person(tmp, 13, 38, looks.shirt(lk, season), looks.hair(lk), hat, season, 0, cheer, look=lk,
                           pose=pose)
        return tmp
    return _cached(('fig', looks.encode(lk), season, hat, pose, cheer), make)


def outlined(surf, k, col=(96, 70, 54)):
    """surf scaled up k times, with a one-pixel (k wide) outline so pale colours stand out on the tiles."""
    big = pygame.transform.scale(surf, (surf.get_width() * k, surf.get_height() * k))
    out = pygame.Surface((big.get_width() + 2 * k, big.get_height() + 2 * k), pygame.SRCALPHA)
    sil = pygame.mask.from_surface(big, 60).to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (k + dx * k, k + dy * k))
    out.blit(big, (k, k))
    return out


def head_icon(lk, k):
    """Your head and shoulders, k times the size."""
    def make():
        return outlined(figure(lk, 1, 'none').subsurface((4, 11, 15, 14)), k)
    return _cached(('head', looks.encode(lk), k), make)


def body_icon(lk, season, k):
    def make():
        return outlined(figure(lk, season, 'none').subsurface((5, 20, 16, 19)), k)
    return _cached(('body', looks.encode(lk), season, k), make)


def cat_icon(coat_id, k, t=0.0):
    tmp = pygame.Surface((26, 24), pygame.SRCALPHA)
    cookscene.draw_cat(tmp, 12, 22, t, 1, False, coat=looks.coat(dict(looks.DEFAULT, coat=coat_id)), pattern=coat_id)
    return outlined(tmp.subsurface((1, 5, 22, 18)), k)


def mood_icon(mood, t):
    s = pygame.Surface((16, 14), pygame.SRCALPHA)
    if mood == 'hummer':
        actors._note(s, 3, 3 + int(math.sin(t * 4) * 1.5), (110, 96, 160))
        actors._note(s, 9, 6 - int(math.sin(t * 4 + 1) * 1.5), (190, 110, 120))
    elif mood == 'stargazer':
        c = (230, 180, 60)
        s.fill(c, (6, 3, 3, 7))
        s.fill(c, (4, 5, 7, 3))
        if int(t * 3) % 2:
            s.set_at((13, 2), c)
            s.set_at((2, 11), c)
    elif mood == 'fidget':
        up = 1 if math.sin(t * 10) > 0 else 0
        s.fill((72, 92, 140), (4, 2, 3, 6))
        s.fill((72, 92, 140), (9, 2 - up, 3, 6))
        s.fill((84, 58, 42), (3, 8, 5, 3))
        s.fill((84, 58, 42), (9, 8 - up, 5, 3))
    elif mood == 'dozy':
        actors._zed(s, 2, 7, (100, 110, 170))
        actors._zed(s, 8, 2 + int(math.sin(t * 2)), (100, 110, 170))
    elif mood == 'chatty':
        actors.draw_bubble(s, 8, 13, 'dots', t)
    else:
        s.fill((236, 236, 230), (6, 6, 4, 2))
        s.fill((220, 64, 64), (6, 4, 4, 2))
        pygame.draw.line(s, (90, 140, 190), (1, 10), (14, 10))
    return s


# ---------------------------------------------------------------- the diorama
def render_diorama(g, t):
    c = g.cre
    lk = c['look']
    tod, season = c['tod'], c['season']
    top_c, bot_c, hill_c, water_c, light = LIGHT[tod]
    night = tod == 'night'
    s = pygame.Surface((DW, DH))
    for y in range(WL):
        s.fill(lerp_c(top_c, bot_c, (y / WL) ** 1.3), (0, y, DW, 1))
    # stars, sun, moon, clouds
    if tod in ('night', 'dusk'):
        for i, (sx, sy) in enumerate(STARS):
            tw = 0.5 + 0.5 * math.sin(t * (1.2 + i % 3) + i)
            if tod == 'dusk' and (sy > 14 or i % 2):
                continue
            if tw > 0.25:
                s.set_at((sx, sy), lerp_c(top_c, (255, 250, 220), tw))
    if tod == 'night':
        pygame.draw.circle(s, (250, 246, 220), (64, 9), 4)
        pygame.draw.circle(s, top_c, (66, 8), 3)
    elif tod == 'noon':
        pygame.draw.circle(s, (255, 250, 214), (62, 9), 4)
        pygame.draw.circle(s, (255, 236, 170), (62, 9), 3)
    elif tod == 'dusk':
        pygame.draw.circle(s, (255, 196, 120), (58, 36), 7)
        pygame.draw.circle(s, (255, 226, 160), (58, 36), 5)
    else:
        pygame.draw.circle(s, (255, 226, 190), (16, 37), 6)
    if tod in ('noon', 'dawn'):
        for i in range(2):
            cx = (t * (2.4 + i) + i * 47) % (DW + 30) - 15
            cy = 7 + i * 9
            cc = (255, 255, 255) if tod == 'noon' else (255, 222, 214)
            pygame.draw.ellipse(s, cc, (int(cx), cy, 14, 4))
            pygame.draw.ellipse(s, cc, (int(cx) + 4, cy - 2, 8, 4))
    # far hills and the treeline
    for x in range(DW):
        hy = 31 + math.sin(x * 0.08 + 1.3) * 3 + math.sin(x * 0.21) * 1.2
        s.fill(hill_c, (x, int(hy), 1, WL - int(hy)))
    k = {'dawn': 0.45, 'noon': 0.0, 'dusk': 0.55, 'night': 0.8}[tod]
    tree = lerp_c(TREES[season], darken(hill_c, 0.3), k)
    for i, tx in enumerate(range(-2, DW + 4, 5)):
        h = 7 + (i * 5) % 6
        base = WL - 1
        pygame.draw.polygon(s, tree, [(tx - 3, base), (tx + 3, base), (tx, base - h)])
        if season == 3 and tod != 'night':
            s.set_at((tx, base - h), (250, 252, 255))
            s.set_at((tx - 1, base - h + 2), (240, 244, 250))
        elif season == 0 and i % 3 == 0:
            s.set_at((tx + 1, base - h + 3), lerp_c((250, 190, 210), tree, k))
    # the water
    for y in range(WL, DH):
        s.fill(lerp_c(water_c, darken(water_c, 0.35), (y - WL) / (DH - WL)), (0, y, DW, 1))
    # the dock, Biscuit and you, on their own layer so the light of the hour falls on them
    mid = pygame.Surface((DW, DH), pygame.SRCALPHA)
    wood = (150, 104, 70)
    for px in (9, 31, 53):
        mid.fill(darken(wood, 0.3), (px, 42, 2, 12))
    mid.fill(wood, (2, 40, 60, 3))
    mid.fill(lighten(wood, 0.2), (2, 40, 60, 1))
    for px in range(6, 62, 7):
        mid.set_at((px, 41), darken(wood, 0.2))
    mid.fill((96, 76, 60), (5, 27, 1, 13))                       # the lantern post
    mid.fill((96, 76, 60), (4, 26, 4, 1))
    mid.fill((70, 56, 50), (3, 27, 3, 4))
    lit = (255, 214, 120) if tod in ('dusk', 'night') else (214, 190, 150)
    mid.fill(lit, (4, 28, 1, 2))
    cheer = c['cheer'] > 0
    hop = int(abs(math.sin(c['cheer'] * 9)) * 2) if cheer else 0
    cookscene.draw_cat(mid, 18, 40 - hop, t, 1, cheer, coat=looks.coat(lk), pattern=lk['coat'])
    nib = (t % 7.0) > 5.6 and c['roll'] <= 0                     # a fish nibbling, now and then
    pose = '' if cheer else actors.idle_pose(lk['mood'], t, night)
    x, fy = 36, 40
    breathe = 1 if math.sin(t * 1.6) > 0.6 else 0
    shirt = looks.shirt(lk, season)
    hat = (getattr(g, 'hat', 'straw') if c['mode'] == 'edit' else 'straw') if c['hat'] else 'none'
    by = actors.draw_person(mid, x, fy - hop, shirt, looks.hair(lk), hat, season, breathe, cheer, look=lk, pose=pose)
    hand = (x + 6, by - 10)
    pygame.draw.line(mid, shirt, (x + 1, by - 13), (hand[0] - 1, hand[1]))
    mid.fill(looks.skin(lk), (hand[0] - 1, hand[1] - 1, 2, 2))
    bob = (72, WL + 6 + (2 if nib and int(t * 8) % 2 else 0))
    pts = actors.rod_points(hand, -60, 0.35 if nib else 0.12, 24, bob)
    try:
        rod_c = g.rod_spec()['color']
    except (AttributeError, KeyError):
        rod_c = (150, 110, 70)
    actors.draw_rod(mid, pts, rod_c)
    actors._line(mid, pts[-1], bob, 3 if nib else 6, (236, 236, 226, 170))
    if light != (255, 255, 255):
        mid.fill(light + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(mid, (0, 0))
    # the bobber and its rings (in the water, so after the light)
    s.fill((250, 250, 245), (bob[0], bob[1] - 1, 2, 1))
    s.fill((220, 60, 60), (bob[0], bob[1] - 2, 2, 1))
    for i in range(2):
        p = ((t * 0.7 + i * 0.5) % 1.0)
        r = int(2 + p * 7)
        rc = lerp_c(lighten(water_c, 0.4), water_c, p)
        pygame.draw.ellipse(s, rc, (bob[0] + 1 - r, bob[1] - 1, r * 2, 3), 1)
    # glows: the dock lantern, your keepsake, fireflies
    if tod in ('dusk', 'night'):
        s.blit(actors._glow(12, (255, 190, 110)), (4 - 12, 29 - 12))
    actors.draw_charm(s, lk['charm'], pts[3], t, 1.0 if nib else (0.6 if cheer else 0.0), night)
    if not cheer and c['roll'] <= 0:
        actors.draw_mood(s, lk['mood'], x, by, t, night)
    if tod in ('dusk', 'night'):
        for i in range(5):
            fx = 10 + (i * 17 + math.sin(t * 0.6 + i * 2.1) * 8) % 60
            fy2 = 26 + math.sin(t * 0.9 + i * 1.7) * 9
            if math.sin(t * 2.3 + i * 3) > -0.2:
                s.set_at((int(fx), int(fy2)), (240, 255, 170))
    # the reflection, wobbling
    above = s.copy()
    above.set_alpha(96 if tod != 'night' else 120)
    for y in range(WL, DH):
        sy = 2 * WL - y - 1
        if sy < 0:
            break
        d = y - WL
        dx = int(round(math.sin(y * 1.3 + t * 2.4) * (0.4 + d * 0.06)))
        s.blit(above, (dx, y), area=pygame.Rect(0, sy, DW, 1))
    # glints on the water
    gl = lighten(water_c, 0.5)
    for i in range(7):
        gx = int((i * 23 + t * (4 + i % 3)) % (DW + 10)) - 5
        gy = WL + 2 + (i * 5) % (DH - WL - 3)
        if math.sin(t * 1.7 + i) > 0:
            s.fill(gl, (gx, gy, 2 + i % 3, 1))
    # the posts stand in the water, over their reflections
    for px in (9, 31, 53):
        s.fill(lerp_c(darken(wood, 0.45), light, 0.15), (px, WL, 2, 8))
    return s


# ---------------------------------------------------------------- the screen
def _pick(ui, s, rect, action, selected, fill=(240, 230, 210)):
    """A tile you can click or reach with the keys / a pad. Returns (rect, hover)."""
    rect = pygame.Rect(rect)
    idx = len(ui.nav)
    ui.nav.append((rect, action))
    hov = rect.collidepoint(ui.mouse)
    if hov and ui.mouse_moved:
        ui.focus = idx
    focused = ui.focus == idx
    ui.tile(s, rect, lighten(fill, 0.08) if (hov or focused) else fill, U.GOLD if selected else (186, 170, 150),
            selected)
    if focused:
        fr = rect.inflate(8, 8)
        pygame.draw.rect(s, (90, 60, 30), fr.inflate(4, 4), 2)
        pygame.draw.rect(s, (255, 214, 110), fr, 2)
    ui.hot.append((rect, action))
    return rect, hov or focused


def _swatch(ui, s, rect, col, selected, action):
    r, _ = _pick(ui, s, rect, action, selected)
    inner = r.inflate(-14, -14)
    pygame.draw.rect(s, darken(col, 0.3), inner, border_radius=6)
    pygame.draw.rect(s, col, inner.inflate(-4, -4), border_radius=5)
    pygame.draw.rect(s, lighten(col, 0.3), (inner.x + 4, inner.y + 4, inner.w - 8, 3), border_radius=2)
    if selected:
        pygame.draw.circle(s, (255, 255, 250), r.center, 5)
        pygame.draw.circle(s, darken(col, 0.4), r.center, 5, 2)


def _title(ui, s, text, pos):
    ui.blit_text(s, text, pos, 'h3', U.INK)


def draw(g, s):
    _update(g)
    c = g.cre
    c.pop('hover', None)
    ui = g.ui
    lk = c['look']
    t = g.t
    rect = pygame.Rect(U.LOGICAL[0] // 2 - 610, U.LOGICAL[1] // 2 - 340, 1220, 680)
    ui.panel(s, rect, radius=24)
    head = 'Make your angler' if c['mode'] == 'new' else 'Change your look'
    ui.blit_text(s, head, (rect.x + 40, rect.y + 22), 'h1', U.INK)
    ui.blit_text(s, 'Everything you choose shows on the dock straight away.', (rect.x + 44, rect.y + 70), 'small',
                 U.SOFT)
    # ---- the diorama
    dio = pygame.Rect(rect.x + 36, rect.y + 104, DW * ZOOM, DH * ZOOM)
    pygame.draw.rect(s, (110, 74, 50), dio.inflate(20, 20), border_radius=14)
    pygame.draw.rect(s, (150, 104, 70), dio.inflate(10, 10), 3, border_radius=10)
    s.blit(pygame.transform.scale(render_diorama(g, t), dio.size), dio)
    for p in c['fx']:
        a = max(0.0, min(1.0, p[4] * 1.5))
        if a > 0.05:
            s.fill(p[5], (int(dio.x + 36 * ZOOM + p[0]), int(dio.y + 22 * ZOOM + p[1]), 6, 6))
    ui.button(s, (dio.right - 132, dio.y + 10, 122, 36), 'Hat: on' if c['hat'] else 'Hat: off',
              lambda: c.__setitem__('hat', not c['hat']), 'normal', font='smallb', nav=True)
    # ---- time of day
    ty = dio.bottom + 18
    tw = (dio.w - 18) // 4
    for i, (tid, tl) in enumerate(TODS):
        ui.button(s, (dio.x + i * (tw + 6), ty, tw, 38), tl, lambda v=tid: c.__setitem__('tod', v),
                  'tab_on' if c['tod'] == tid else 'tab', font='smallb', nav=True)
    # ---- the four seasons in your colours
    sy = ty + 50
    sw = (dio.w - 18) // 4
    for i in range(4):
        r = pygame.Rect(dio.x + i * (sw + 6), sy, sw, rect.bottom - 24 - sy)
        r, hov = _pick(ui, s, r, lambda v=i: c.__setitem__('season', v), c['season'] == i,
                       (236, 226, 206))
        fig = figure(lk, i, 'none' if not c['hat'] else (getattr(g, 'hat', 'straw') if c['mode'] == 'edit'
                                                          else 'straw'))
        big = outlined(fig.subsurface((4, 8, 18, 31)), 2)
        s.blit(big, big.get_rect(midtop=(r.centerx, r.y + 4)))
        ui.blit_text(s, SEASON_NAMES[i], (r.centerx, r.bottom - 22), 'tiny',
                     U.INK if c['season'] == i else U.SOFT, 'midtop')
    # ---- the right-hand side
    x0 = dio.right + 50
    rw = rect.right - 36 - x0
    ui.blit_text(s, 'Your name', (x0, rect.y + 120), 'bodyb', U.INK, 'midleft')
    g.text_field(s, (x0 + 130, rect.y + 96, rw - 130, 48), 'mp_name', 'Angler')
    tby = rect.y + 160
    tw = (rw - 4 * 8) // 5
    for i, (tid, tl) in enumerate(TABS):
        ui.button(s, (x0 + i * (tw + 8), tby, tw, 42), tl, lambda v=tid: _tab(g, v),
                  'tab_on' if c['tab'] == tid else 'tab', font='smallb', nav=True)
    y0 = tby + 62
    {'face': _tab_face, 'hair': _tab_hair, 'clothes': _tab_clothes, 'keep': _tab_keep,
     'cat': _tab_cat}[c['tab']](g, s, x0, y0, rw, t)
    # ---- bottom row
    by = rect.bottom - 74
    dice = _dice_icon(t if c['roll'] > 0 else 0.0)
    ui.button(s, (x0, by, 210, 54), 'Surprise me', lambda: surprise(g), 'gold', font='bodyb', icon=dice, nav=True)
    ui.button(s, (x0 + 220, by, 110, 54), 'Reset', lambda: _reset(g), 'normal', font='smallb', nav=True)
    if c['mode'] == 'new':
        ui.button(s, (rect.right - 36 - 250, by, 250, 54), 'Start fishing', lambda: confirm(g), 'primary', font='h3',
                  nav=True)
    else:
        ui.button(s, (rect.right - 36 - 150, by, 150, 54), 'Done', lambda: confirm(g), 'primary', font='h3',
                  nav=True)
        ui.button(s, (rect.right - 36 - 280, by, 120, 54), 'Cancel', lambda: cancel(g), 'normal', font='bodyb',
                  nav=True)
    if c['mode'] == 'new':
        close = pygame.Rect(rect.right - 62, rect.y + 18, 44, 44)
        ui.button(s, close, 'X', lambda: cancel(g), 'normal', font='h3')


def _tab(g, v):
    g.cre['tab'] = v
    if v in ('hair', 'face'):
        g.cre['hat'] = False
    g.audio.play('ui', 0.4)


def _reset(g):
    g.cre['look'] = dict(g.cre['start'] if g.cre['mode'] == 'edit' and g.cre['look'] != g.cre['start']
                         else looks.DEFAULT)
    g.audio.play('page', 0.5)


def _dice_icon(t):
    s = pygame.Surface((26, 26), pygame.SRCALPHA)
    pygame.draw.rect(s, (84, 56, 28), (1, 1, 24, 24), border_radius=6)
    pygame.draw.rect(s, (255, 250, 236), (3, 3, 20, 20), border_radius=5)
    face = int(t * 14) % 6 + 1 if t else 5
    spots = {1: [(13, 13)], 2: [(8, 8), (18, 18)], 3: [(8, 8), (13, 13), (18, 18)],
             4: [(8, 8), (18, 8), (8, 18), (18, 18)], 5: [(8, 8), (18, 8), (13, 13), (8, 18), (18, 18)],
             6: [(8, 7), (18, 7), (8, 13), (18, 13), (8, 19), (18, 19)]}[face]
    for p in spots:
        pygame.draw.circle(s, (200, 70, 70), p, 2)
    return s


def _variant(lk, field, oid):
    v = dict(lk)
    v[field] = oid
    return v


def _style_row(g, s, field, x0, y, w, h, gap, render, label=True):
    """A row of tiles, one per option of `field`, each showing you with that option."""
    c = g.cre
    ui = g.ui
    for i, oid in enumerate(looks.options(field)):
        r = pygame.Rect(x0 + i * (w + gap), y, w, h)
        r, hov = _pick(ui, s, r, lambda o=oid: set_opt(g, field, o), c['look'][field] == oid)
        icon = render(_variant(c['look'], field, oid), r)
        s.blit(icon, icon.get_rect(center=(r.centerx, r.y + (h - (18 if label else 0)) // 2 + 2)))
        if label:
            ui.blit_text(s, looks.label(field, oid), (r.centerx, r.bottom - 20), 'tiny',
                         U.INK if c['look'][field] == oid else U.SOFT, 'midtop', maxw=w - 6)
        if hov:
            c['hover'] = (field, oid)


def _swatch_row(g, s, field, x0, y, size, gap, color_of):
    c = g.cre
    for i, oid in enumerate(looks.options(field)):
        col = color_of(_variant(c['look'], field, oid))
        _swatch(g.ui, s, (x0 + i * (size + gap), y, size, size), col, c['look'][field] == oid,
                lambda o=oid: set_opt(g, field, o))


def _tab_face(g, s, x0, y, rw, t):
    ui = g.ui
    c = g.cre
    _title(ui, s, 'Skin', (x0, y))
    _swatch_row(g, s, 'skin', x0, y + 32, 58, 8, looks.skin)
    y += 108
    _title(ui, s, 'Eyes', (x0, y))
    _style_row(g, s, 'eyes', x0, y + 32, 96, 96, 9, lambda v, r: head_icon(v, 4))
    y += 144
    _title(ui, s, 'Beard', (x0, y))
    _style_row(g, s, 'beard', x0, y + 32, 82, 96, 8, lambda v, r: head_icon(v, 4))
    bx = x0 + 4 * 90 + 20
    _title(ui, s, 'Cheeks', (bx, y))
    for i, (key, lab) in enumerate((('freckles', 'Freckles'), ('blush', 'Rosy'))):
        on = c['look'][key]
        ui.button(s, (bx, y + 32 + i * 52, rw - (bx - x0), 44), lab + (': on' if on else ': off'),
                  lambda k=key: _toggle(g, k), 'tab_on' if on else 'tab', font='smallb', nav=True)


def _toggle(g, key):
    g.cre['look'][key] = not g.cre['look'][key]
    g.audio.play('ui', 0.4)


def _tab_hair(g, s, x0, y, rw, t):
    ui = g.ui
    _title(ui, s, 'Colour', (x0, y))
    _swatch_row(g, s, 'hair', x0, y + 32, 52, 7, looks.hair)
    y += 100
    _title(ui, s, 'Style', (x0, y))
    w = (rw - 3 * 10) // 4
    for row in range(2):
        ids = looks.options('hstyle')[row * 4:row * 4 + 4]
        for i, oid in enumerate(ids):
            r = pygame.Rect(x0 + i * (w + 10), y + 32 + row * 114, w, 106)
            sel = g.cre['look']['hstyle'] == oid
            r, _ = _pick(ui, s, r, lambda o=oid: set_opt(g, 'hstyle', o), sel)
            icon = head_icon(_variant(g.cre['look'], 'hstyle', oid), 5)
            s.blit(icon, icon.get_rect(midtop=(r.centerx, r.y + 4)).clip(r.inflate(-6, -6)),
                   area=pygame.Rect(0, 0, icon.get_width(), 76))
            ui.blit_text(s, looks.label('hstyle', oid), (r.centerx, r.bottom - 24), 'smallb',
                         U.INK if sel else U.SOFT, 'midtop')


def _tab_clothes(g, s, x0, y, rw, t):
    ui = g.ui
    c = g.cre
    season = c['season']
    _title(ui, s, 'Top', (x0, y))
    w = (rw - 4 * 8) // 5
    _style_row(g, s, 'top', x0, y + 32, w, 104, 8, lambda v, r: body_icon(v, season, 4))
    y += 150
    _title(ui, s, 'Colours', (x0, y))
    ui.blit_text(s, 'one shade for each season', (x0 + 100, y + 4), 'small', U.SOFT)
    w2 = (rw - 7 * 6) // 8
    for i, oid in enumerate(looks.options('theme')):
        r = pygame.Rect(x0 + i * (w2 + 6), y + 32, w2, 74)
        sel = c['look']['theme'] == oid
        r, _ = _pick(ui, s, r, lambda o=oid: set_opt(g, 'theme', o), sel)
        v = _variant(c['look'], 'theme', oid)
        sw = (r.w - 20) // 4
        for k in range(4):
            col = looks.shirt(v, k)
            pygame.draw.rect(s, col, (r.x + 10 + k * sw, r.y + 10, sw, 30))
            if k == season:
                pygame.draw.rect(s, (255, 255, 250), (r.x + 10 + k * sw, r.y + 40, sw, 3))
        pygame.draw.rect(s, darken(looks.shirt(v, 0), 0.4), (r.x + 9, r.y + 9, sw * 4 + 2, 32), 1)
        ui.blit_text(s, looks.label('theme', oid), (r.centerx, r.bottom - 22), 'tiny', U.INK if sel else U.SOFT,
                     'midtop', maxw=r.w - 4)
    y += 122
    half = (rw - 20) // 2
    _title(ui, s, 'Trousers', (x0, y))
    _swatch_row(g, s, 'pants', x0, y + 32, (half - 5 * 6) // 6, 6, looks.pants)
    bx = x0 + half + 20
    _title(ui, s, 'Boots', (bx, y))
    _swatch_row(g, s, 'boots', bx, y + 32, (half - 5 * 6) // 6, 6, looks.boots)
    hov = c.pop('hover', None)
    if hov and hov[0] == 'boots':
        ui.blit_text(s, looks.label('boots', hov[1]), (bx, y + 110), 'small', U.SOFT)


def _tab_keep(g, s, x0, y, rw, t):
    ui = g.ui
    c = g.cre
    lk = c['look']
    _title(ui, s, 'Rod charm', (x0, y))
    ui.blit_text(s, 'hangs from your rod and sways', (x0 + 126, y + 4), 'small', U.SOFT)
    w = (rw - 7 * 6) // 8
    for i, oid in enumerate(looks.options('charm')):
        r = pygame.Rect(x0 + i * (w + 6), y + 32, w, 92)
        sel = lk['charm'] == oid
        r, hov = _pick(ui, s, r, lambda o=oid: set_opt(g, 'charm', o), sel)
        ic = pygame.Surface((10, 11), pygame.SRCALPHA)
        if oid == 'none':
            pygame.draw.line(ic, (190, 170, 150), (2, 2), (7, 7))
            pygame.draw.line(ic, (190, 170, 150), (7, 2), (2, 7))
        else:
            a = actors.charm_swing(t + i, 0.0)
            ex = 5 + int(round(math.sin(a) * 2))
            pygame.draw.line(ic, (150, 140, 130), (5, 0), (ex, 2))
            actors.draw_charm_icon(ic, oid, ex, 3, t, 0.0, False)
        ic = pygame.transform.scale(ic, (60, 66))
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 38)))
        ui.blit_text(s, looks.label('charm', oid).split(' ')[-1].capitalize(), (r.centerx, r.bottom - 22), 'tiny',
                     U.INK if sel else U.SOFT, 'midtop', maxw=r.w - 4)
        if hov:
            c['hover'] = ('charm', oid)
    hov = c.get('hover')
    show = hov[1] if hov and hov[0] == 'charm' else lk['charm']
    ui.blit_text(s, looks.label('charm', show) + ':  ' + looks.blurb('charm', show), (x0, y + 136), 'small',
                 U.INK, maxw=rw)
    y += 178
    _title(ui, s, 'While you wait', (x0, y))
    ui.blit_text(s, 'how you pass the time until a bite', (x0 + 160, y + 4), 'small', U.SOFT)
    w = (rw - 5 * 8) // 6
    for i, oid in enumerate(looks.options('mood')):
        r = pygame.Rect(x0 + i * (w + 8), y + 32, w, 92)
        sel = lk['mood'] == oid
        r, hov = _pick(ui, s, r, lambda o=oid: set_opt(g, 'mood', o), sel)
        ic = pygame.transform.scale(mood_icon(oid, t + i * 0.3), (64, 56))
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 36)))
        ui.blit_text(s, looks.label('mood', oid), (r.centerx, r.bottom - 22), 'tiny', U.INK if sel else U.SOFT,
                     'midtop', maxw=r.w - 4)
        if hov:
            c['hover'] = ('mood', oid)
    hov = c.pop('hover', None)
    show = hov[1] if hov and hov[0] == 'mood' else lk['mood']
    ui.blit_text(s, looks.label('mood', show) + ':  ' + looks.blurb('mood', show), (x0, y + 136), 'small',
                 U.INK, maxw=rw)


def _tab_cat(g, s, x0, y, rw, t):
    ui = g.ui
    c = g.cre
    _title(ui, s, "Biscuit's coat", (x0, y))
    ui.blit_text(s, 'your cat, who keeps you company on the dock', (x0 + 172, y + 4), 'small', U.SOFT)
    w = (rw - 3 * 10) // 4
    for i, oid in enumerate(looks.options('coat')):
        r = pygame.Rect(x0 + (i % 4) * (w + 10), y + 32 + (i // 4) * 142, w, 132)
        sel = c['look']['coat'] == oid
        r, _ = _pick(ui, s, r, lambda o=oid: set_opt(g, 'coat', o), sel)
        ic = cat_icon(oid, 4, t + i * 0.7 if sel else 0.5)
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 52)))
        ui.blit_text(s, looks.label('coat', oid), (r.centerx, r.bottom - 26), 'smallb', U.INK if sel else U.SOFT,
                     'midtop', maxw=r.w - 6)
    ui.blit_text(s, 'She wears it everywhere: on the dock, in the cabin and around the village.',
                 (x0, y + 32 + 2 * 142 + 4), 'small', U.SOFT, maxw=rw)
