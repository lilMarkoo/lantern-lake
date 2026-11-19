"""The Cozy Cabin window: a wooden rail down the left with a tab for each room, and the room itself on the right.

The rail holds the cabin's name, the seven tabs (each with a little pixel icon and a dot when something there wants
you), and at the bottom a real window looking out on the lake: the sky, weather and time of day as they are now.
Each tab's page is drawn by its own module in the 1040x636 area to the right, exactly as it always was.

At the biggest interface size there isn't room for the rail, so the window falls back to tabs along the top.
"""
import math
import random

import pygame

import ui as U
from art import lerp_c, darken, lighten

RAIL = 160                  # the rail's width, in canvas pixels
PAGE_W, PAGE_H = 1040, 636  # the page area each tab draws into
WOOD = (132, 90, 60)
WOOD_D = (104, 70, 48)
WOOD_L = (156, 112, 78)

_cache = {}


def fits(sw):
    return sw >= PAGE_W + RAIL + 12


# ---------------------------------------------------------------- pixel bits (drawn at art scale, doubled)
def _rail_bg(h):
    key = ('rail', h)
    if key in _cache:
        return _cache[key]
    w, hh = RAIL // 2, h // 2
    s = pygame.Surface((w, hh), pygame.SRCALPHA)
    s.fill(WOOD)
    rng = random.Random(12)
    y = 0
    while y < hh:
        ph = rng.choice((9, 10, 11))
        s.fill(lighten(WOOD, 0.04) if (y // 10) % 2 else WOOD, (0, y, w, ph))
        pygame.draw.line(s, WOOD_D, (0, y + ph - 1), (w, y + ph - 1))
        pygame.draw.line(s, WOOD_L, (0, y), (w, y))
        # end joints, staggered
        jx = rng.randrange(18, w - 18)
        pygame.draw.line(s, WOOD_D, (jx, y + 1), (jx, y + ph - 2))
        for _ in range(3):
            gx = rng.randrange(w)
            pygame.draw.line(s, darken(WOOD, 0.08), (gx, y + 3), (gx + rng.randrange(4, 12), y + 3))
        if rng.random() < 0.3:
            kx, ky = rng.randrange(4, w - 4), y + ph // 2
            pygame.draw.ellipse(s, WOOD_D, (kx - 2, ky - 1, 4, 3))
        y += ph
    out = pygame.transform.scale(s, (RAIL, hh * 2))
    _cache[key] = out
    return out


def _icon(kind):
    key = ('icon', kind)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    d = pygame.draw
    ink = (60, 42, 34)
    if kind == 'tank':
        d.circle(s, (176, 220, 236), (8, 9), 6)
        d.rect(s, (72, 140, 172), (3, 9, 11, 5))
        d.circle(s, ink, (8, 9), 6, 1)
        d.line(s, ink, (4, 3), (12, 3))
        d.rect(s, (238, 140, 70), (6, 10, 4, 2))
        s.set_at((5, 10), (238, 140, 70))
        s.set_at((5, 11), (238, 140, 70))
        s.set_at((11, 6), (240, 250, 255))
    elif kind == 'kitchen':
        for i, x in enumerate((5, 8, 11)):
            s.set_at((x, 2 + i % 2), (236, 236, 236))
            s.set_at((x - 1, 4 - i % 2), (236, 236, 236))
        d.rect(s, (88, 92, 104), (2, 7, 12, 7), border_radius=2)
        d.rect(s, (120, 126, 140), (3, 8, 10, 2))
        d.rect(s, ink, (2, 7, 12, 7), 1, border_radius=2)
        d.line(s, ink, (0, 9), (2, 9))
        d.line(s, ink, (14, 9), (15, 9))
        d.line(s, ink, (4, 6), (11, 6))
    elif kind == 'garden':
        d.ellipse(s, (120, 82, 52), (1, 11, 14, 5))
        d.line(s, (84, 140, 64), (8, 12), (8, 6))
        d.ellipse(s, (110, 176, 84), (2, 4, 6, 4))
        d.ellipse(s, (110, 176, 84), (8, 2, 6, 4))
        s.set_at((4, 5), (160, 210, 120))
        s.set_at((11, 3), (160, 210, 120))
        d.circle(s, (228, 70, 90), (12, 12), 1)
    elif kind == 'hatchery':
        d.ellipse(s, (82, 150, 176), (1, 7, 14, 8))
        d.ellipse(s, ink, (1, 7, 14, 8), 1)
        for x, y in ((4, 4), (7, 3), (6, 6)):
            d.circle(s, (248, 240, 214), (x, y), 2)
            s.set_at((x - 1, y - 1), (255, 255, 255))
        d.rect(s, (232, 178, 52), (8, 10, 4, 2))
        s.set_at((12, 10), (232, 178, 52))
        s.set_at((12, 11), (232, 178, 52))
        s.set_at((7, 10), (232, 178, 52))
    elif kind == 'home':
        d.polygon(s, (196, 82, 70), [(1, 8), (8, 2), (15, 8)])
        d.rect(s, (232, 206, 160), (3, 8, 10, 7))
        d.rect(s, (120, 80, 54), (7, 10, 3, 5))
        d.rect(s, (255, 216, 120), (4, 9, 2, 2))
        d.rect(s, ink, (3, 8, 10, 7), 1)
        d.line(s, ink, (1, 8), (8, 1))
        d.line(s, ink, (8, 1), (15, 8))
    elif kind == 'biscuit':
        o = (232, 150, 78)
        d.polygon(s, o, [(2, 2), (6, 6), (2, 8)])
        d.polygon(s, o, [(14, 2), (10, 6), (14, 8)])
        d.ellipse(s, o, (2, 5, 12, 10))
        d.ellipse(s, (250, 238, 222), (5, 10, 6, 5))
        s.set_at((5, 8), ink)
        s.set_at((10, 8), ink)
        s.set_at((7, 11), (230, 140, 150))
        s.set_at((8, 11), (230, 140, 150))
        d.line(s, (196, 112, 58), (8, 5), (8, 7))
    elif kind == 'wardrobe':
        d.ellipse(s, (226, 196, 120), (1, 8, 14, 5))
        d.ellipse(s, (236, 210, 140), (4, 3, 8, 8))
        d.rect(s, (196, 82, 70), (4, 8, 8, 2))
        d.ellipse(s, ink, (1, 8, 14, 5), 1)
        s.set_at((6, 5), (250, 230, 170))
    out = pygame.transform.scale(s, (32, 32))
    _cache[key] = out
    return out


def _outside(g, w, h):
    """The view out of the cabin window: sky, the far shore and the lake, weather and all."""
    env = g.env
    s = pygame.Surface((w, h))
    top, mid, bot = env.sky
    hor = int(h * 0.58)
    for y in range(hor):
        k = y / max(1, hor - 1)
        s.fill(lerp_c(top, mid, k / 0.6) if k < 0.6 else lerp_c(mid, bot, (k - 0.6) / 0.4), (0, y, w, 1))
    rng = random.Random(3)
    if env.nf > 0.4 and env.over < 0.7:
        for _ in range(10):
            x, y = rng.randrange(w), rng.randrange(hor - 6)
            if math.sin(g.t * 2 + x) > -0.3:
                s.set_at((x, y), lerp_c(top, (255, 250, 230), env.nf))
    if env.moon_vis and env.nf > 0.3:
        pygame.draw.circle(s, (240, 240, 220), (w - 12, 7), 3)
    elif env.sun_vis and env.nf < 0.5:
        pygame.draw.circle(s, lerp_c((255, 246, 214), (255, 170, 104), max(0, min(1, (env.sun[1] - 60) / 120))),
                           (12, max(5, min(hor - 4, int(env.sun[1] / 190 * hor)))), 3)
    trees = lerp_c((52, 86, 70), (16, 22, 34), env.nf * 0.8)
    if env.season == 3:
        trees = lerp_c((150, 160, 176), (40, 46, 64), env.nf * 0.8)
    elif env.season == 2:
        trees = lerp_c((150, 96, 56), (30, 26, 34), env.nf * 0.8)
    for x in range(w):
        th = 3 + int(2 * math.sin(x * 0.9) + 2 * math.sin(x * 0.37 + 1))
        s.fill(trees, (x, hor - th, 1, th))
    water = lerp_c(lerp_c((60, 110, 130), bot, 0.3), (18, 24, 40), env.nf * 0.7)
    s.fill(water, (0, hor, w, h - hor))
    for k in range(5):
        x = (k * 11 + int(g.t * 3)) % w
        y = hor + 3 + (k * 5) % (h - hor - 3)
        s.fill(lighten(water, 0.25), (x, y, 3, 1))
    if g.weather == 'rain':
        for k in range(14):
            x = (k * 7 + int(g.t * 40)) % w
            y = (k * 13 + int(g.t * 90)) % h
            pygame.draw.line(s, lerp_c(mid, (220, 230, 240), 0.5), (x, y), (x - 1, y + 3))
    elif g.weather == 'snow':
        for k in range(12):
            x = (k * 9 + int(math.sin(g.t + k) * 3)) % w
            y = (k * 11 + int(g.t * 12)) % h
            s.set_at((x, y), (250, 250, 255))
    elif g.weather == 'fog':
        fog = pygame.Surface((w, h), pygame.SRCALPHA)
        fog.fill((220, 224, 228, 110))
        s.blit(fog, (0, 0))
    return s


def _window(g, w, h):
    """The whole little window at art scale: frame, panes, curtains, and a candle on the sill after dark."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    gx, gy, gw, gh = 8, 5, w - 16, h - 16
    s.blit(_outside(g, gw, gh), (gx, gy))
    frame = (226, 214, 190)
    pygame.draw.rect(s, frame, (gx - 3, gy - 3, gw + 6, gh + 6), 3)
    pygame.draw.line(s, frame, (gx + gw // 2, gy), (gx + gw // 2, gy + gh - 1), 2)
    pygame.draw.line(s, frame, (gx, gy + gh // 2), (gx + gw - 1, gy + gh // 2), 2)
    pygame.draw.rect(s, darken(frame, 0.35), (gx - 3, gy - 3, gw + 6, gh + 6), 1)
    # curtains, gathered at the sides
    cur = (196, 96, 84)
    for side in (0, 1):
        for k in range(6):
            x = gx - 5 + k if side == 0 else gx + gw + 4 - k
            ww = max(1, 6 - k)
            col = cur if k % 2 == 0 else darken(cur, 0.15)
            for y in range(gy - 4, gy + gh + 2):
                bulge = int(2 * math.sin((y - gy) / gh * math.pi))
                xx = x + (bulge if side == 0 else -bulge)
                if 0 <= xx < w:
                    s.set_at((xx, y), col)
            del ww
    pygame.draw.line(s, (120, 84, 56), (2, gy - 5), (w - 3, gy - 5), 2)
    # the sill, with a plant, and a candle once the light goes
    sill_y = gy + gh + 3
    pygame.draw.rect(s, (176, 130, 88), (2, sill_y, w - 4, 4))
    pygame.draw.line(s, (120, 84, 56), (2, sill_y + 4), (w - 3, sill_y + 4))
    pygame.draw.rect(s, (186, 100, 70), (8, sill_y - 4, 5, 4))
    for dx, dy in ((-1, -7), (2, -8), (4, -6), (0, -5)):
        pygame.draw.line(s, (96, 150, 80), (10, sill_y - 4), (10 + dx, sill_y + dy))
    if g.env.nf > 0.3:
        cx = w - 14
        pygame.draw.rect(s, (244, 236, 214), (cx, sill_y - 6, 3, 6))
        fl = 1 if math.sin(g.t * 9) > 0 else 0
        s.set_at((cx + 1, sill_y - 7 - fl), (255, 220, 120))
        s.set_at((cx + 1, sill_y - 8 - fl), (255, 246, 200))
    return s


# ---------------------------------------------------------------- the window
def summary(g, key):
    """One line under the tab's name: how things stand in that room."""
    import garden
    import hatchery
    if key == 'tank':
        return 'Your favourite catches, swimming at home'
    if key == 'kitchen':
        return 'Cook what you catch, and share it with the town'
    if key == 'garden':
        n = len(garden.ready_beds(g))
        d = len(garden.thirsty(g))
        if n:
            return '%d bed%s ready to pick' % (n, '' if n == 1 else 's')
        return '%d bed%s need water today' % (d, '' if d == 1 else 's') if d else 'All the beds are happy'
    if key == 'hatchery':
        n = len(hatchery.ready(g))
        txt = 'Pond %d / %d' % (len(g.hatch['pond']), hatchery.POND)
        if n:
            txt += '   Young fish ready!'
        elif g.hatch['clutches']:
            txt += '   %d clutch%s growing' % (len(g.hatch['clutches']), '' if len(g.hatch['clutches']) == 1 else 'es')
        return txt
    if key == 'home':
        return 'Furnish your room and hang your trophies'
    if key == 'biscuit':
        import biscuit
        return "Biscuit's bond: level %d" % biscuit.level(g)
    if key == 'wardrobe':
        return 'Hats and outfits for you, and for Biscuit'
    return ''


def wants(g, key):
    """True when something in this room needs you (a dot on its tab)."""
    import garden
    import hatchery
    if key == 'garden':
        return bool(garden.ready_beds(g)) or bool(garden.thirsty(g))
    if key == 'hatchery':
        return bool(hatchery.ready(g))
    return False


def frame(g, s, tabs, current, sw, sh):
    """Draws the window and its rail. Returns the page rect for the current tab."""
    ui = g.ui
    win = pygame.Rect(sw // 2 - (PAGE_W + RAIL) // 2, sh // 2 - PAGE_H // 2, PAGE_W + RAIL, PAGE_H)
    ui.panel(s, win, radius=24)
    page = pygame.Rect(win.x + RAIL, win.y, PAGE_W, PAGE_H)
    # the rail
    rail = pygame.Rect(win.x + 4, win.y + 4, RAIL - 4, win.h - 8)
    bg = _rail_bg(rail.h)
    s.blit(bg, rail, (0, 0, rail.w, rail.h))
    pygame.draw.line(s, U.BROWN_D, (rail.right, rail.y), (rail.right, rail.bottom - 1), 2)
    ui.blit_text(s, 'Cozy', (rail.centerx, rail.y + 12), 'h2', (250, 236, 210), 'midtop', outline=(70, 46, 32))
    ui.blit_text(s, 'Cabin', (rail.centerx, rail.y + 42), 'h2', (250, 236, 210), 'midtop', outline=(70, 46, 32))
    ty = rail.y + 90
    for key, label in tabs:
        on = key == current
        r = pygame.Rect(rail.x + 10, ty, rail.w - 10 + (6 if on else -10), 52)
        if on:
            pygame.draw.rect(s, U.CREAM, r, border_top_left_radius=12, border_bottom_left_radius=12)
            pygame.draw.rect(s, U.BROWN, r, 3, border_top_left_radius=12, border_bottom_left_radius=12)
            pygame.draw.rect(s, U.CREAM, (rail.right - 2, r.y + 3, 10, r.h - 6))
        else:
            hov = r.collidepoint(ui.mouse)
            ui.tile(s, r, lighten(WOOD, 0.22 if hov else 0.12), WOOD_D)
        ic = _icon(key)
        s.blit(ic, ic.get_rect(midleft=(r.x + 8, r.centery)))
        ui.blit_text(s, label, (r.x + 48, r.centery), 'smallb', U.INK if on else (250, 238, 214), 'midleft',
                     outline=None if on else (70, 46, 32), maxw=r.w - 54)
        if wants(g, key):
            pygame.draw.circle(s, U.ROSE, (r.x + 34, r.y + 10), 6)
            pygame.draw.circle(s, darken(U.ROSE, 0.3), (r.x + 34, r.y + 10), 6, 2)
        ui.hotspot(r, lambda k=key: _pick(g, k))
        ty += 58
    # the window onto the lake, at the bottom of the rail
    left = rail.bottom - ty - 8
    if left >= 90:
        aw = (rail.w - 20) // 2
        ah = min(60, (left - 8) // 2)
        img = pygame.transform.scale(_window(g, aw, ah), (aw * 2, ah * 2))
        s.blit(img, img.get_rect(midbottom=(rail.centerx, rail.bottom - 8)))
    # the page's own header
    title = dict(tabs).get(current, '')
    band = pygame.Rect(page.x + 4, page.y + 4, page.w - 8, 72)
    pygame.draw.rect(s, (240, 227, 202), band, border_top_right_radius=20)
    pygame.draw.line(s, (216, 196, 164), (page.x + 4, band.bottom), (page.right - 5, band.bottom), 2)
    ic = _icon(current)
    s.blit(ic, (page.x + 28, page.y + 22))
    ui.blit_text(s, title, (page.x + 72, page.y + 12), 'h2', U.INK)
    ui.blit_text(s, summary(g, current), (page.x + 72, page.y + 46), 'small', U.SOFT, maxw=page.w - 200)
    ui.button(s, (page.right - 62, page.y + 18, 44, 44), 'X', g.close_overlay, 'normal', font='h3')
    return page


def _pick(g, key):
    if g.cabin_tab != key:
        g.cabin_tab = key
        g.audio.play('ui', 0.4)
