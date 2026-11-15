"""The angler, Biscuit the cat and the dock decorations."""
import math

import pygame

from art import DECK_Y, POLES, lerp_c, darken, lighten, bank_top
from fishing import PLAYER_X, HAND

CAT_X = 214
SHIRT = {0: (214, 128, 112), 1: (236, 196, 96), 2: (196, 98, 66), 3: (122, 144, 196)}


def light_bulbs():
    (x0, x1), y = POLES, 248
    out = []
    cols = [(255, 206, 120), (255, 150, 136), (196, 236, 150), (150, 200, 255)]
    n = 16
    for i in range(1, n):
        k = i / n
        x = x0 + (x1 - x0) * k
        sag = math.sin(math.pi * k) * 12
        out.append((int(x), int(y + sag), cols[i % 4]))
    return out


def draw_person(s, x, fy, shirt, hair, hat, season, breathe, cheer=False):
    """An angler standing with their feet on y=fy. Returns the y their body is drawn from (for arms, hats)."""
    boot, pants = (84, 58, 42), (72, 92, 140)
    skin = (240, 202, 172)
    by = fy - breathe
    # legs
    s.fill(pants, (x - 3, fy - 7, 2, 6))
    s.fill(pants, (x + 1, fy - 7, 2, 6))
    s.fill(boot, (x - 4, fy - 2, 3, 2))
    s.fill(boot, (x + 1, fy - 2, 3, 2))
    # body
    s.fill(shirt, (x - 4, by - 15, 8, 9))
    s.fill(pants, (x - 3, by - 9, 6, 3))
    s.fill(darken(pants, 0.15), (x - 3, by - 14, 1, 6))
    s.fill(darken(pants, 0.15), (x + 2, by - 14, 1, 6))
    if season == 3:
        s.fill((200, 70, 70), (x - 4, by - 16, 9, 2))
        s.fill((200, 70, 70), (x - 5, by - 15, 2, 4))
    # head
    s.fill(skin, (x - 3, by - 21, 7, 6))
    s.fill(hair, (x - 4, by - 21, 3, 5))
    s.set_at((x + 2, by - 19), (50, 40, 40))
    if cheer:
        s.set_at((x + 1, by - 16), (180, 90, 80))
        s.set_at((x + 2, by - 16), (180, 90, 80))
    s.fill((236, 160, 150), (x + 1, by - 17, 2, 1))
    draw_hat(s, hat, x, by, season, hair)
    return by


def rod_points(hand, angle, bend, length, target):
    """The nine points of a rod held at `hand`, bent toward `target` (same maths as Fishing._rod_geometry)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    hx, hy = hand
    straight = (hx + ux * length, hy + uy * length)
    bx = by = 0.0
    if bend > 0.02 and target:
        vx, vy = target[0] - straight[0], target[1] - straight[1]
        n = math.hypot(vx, vy) or 1
        bx, by = vx / n * length * 0.4 * bend, vy / n * length * 0.4 * bend
    return [(hx + ux * i / 8 * length + bx * (i / 8) ** 2, hy + uy * i / 8 * length + by * (i / 8) ** 2)
            for i in range(9)]


def draw_rod(s, pts, col):
    pygame.draw.line(s, (80, 54, 40), pts[0], pts[1], 2)
    pygame.draw.lines(s, col, False, pts[1:5], 2)
    pygame.draw.lines(s, lighten(col, 0.15), False, pts[4:], 1)
    reel = pts[1]
    s.fill((140, 140, 150), (int(reel[0]) - 1, int(reel[1]), 3, 2))


def draw_held_fish(s, spec, hx, hy):
    import art
    spr = art.fish_sprite(spec)
    k = 0.4
    sm = pygame.transform.scale(spr, (int(spr.get_width() * k), int(spr.get_height() * k)))
    sm = pygame.transform.rotate(sm, 70)
    s.blit(sm, (hx + 4 - sm.get_width() // 2, hy - 30))


def draw_player(s, g, t):
    f = g.fishing
    st = f.state
    x, fy = PLAYER_X, DECK_Y
    season = g.env.season
    breathe = 1 if math.sin(t * 1.6) > 0.6 else 0
    if st == 'caught':
        breathe = -1 if math.sin(t * 10) > 0 else 0
    shirt = SHIRT[season]
    by = draw_person(s, x, fy, shirt, (112, 72, 52), getattr(g, 'hat', 'straw'), season, breathe, st == 'caught')
    # arm reaching for the rod handle
    hx, hy = HAND
    pygame.draw.line(s, shirt, (x + 1, by - 13), (hx - 1, hy + breathe))
    s.fill((240, 202, 172), (hx - 1, hy - 1 + breathe, 2, 2))
    if f.rod_pts:
        draw_rod(s, f.rod_pts, g.rod_spec()['color'])
    # fish held up
    if st == 'caught' and f.catch:
        draw_held_fish(s, f.catch['spec'], hx, hy)


def draw_hat(s, hat, x, by, season, hair):
    if hat == 'none':
        s.fill(hair, (x - 3, by - 22, 7, 2))
        return
    if hat == 'chef':
        s.fill((250, 250, 246), (x - 3, by - 24, 7, 3))
        s.fill((250, 250, 246), (x - 4, by - 28, 9, 4))
        s.fill((226, 226, 222), (x - 3, by - 22, 7, 1))
        return
    if hat == 'bowler':
        c = (60, 52, 64)
        s.fill(c, (x - 5, by - 22, 11, 1))
        s.fill(c, (x - 3, by - 25, 7, 3))
        s.fill((150, 70, 90), (x - 3, by - 23, 7, 1))
        return
    if hat == 'party':
        for i in range(6):
            w = max(1, 7 - i * 2 + (i // 2))
            s.fill((236, 110, 150) if i % 2 == 0 else (110, 190, 220), (x - w // 2, by - 22 - i, w, 1))
        s.fill((255, 230, 120), (x, by - 29, 2, 2))
        return
    if hat == 'lanternhat':
        s.fill((70, 56, 50), (x - 4, by - 22, 9, 1))
        s.fill((70, 56, 50), (x - 3, by - 28, 7, 6))
        s.fill((255, 210, 120), (x - 2, by - 27, 5, 4))
        s.fill((255, 246, 200), (x, by - 26, 1, 2))
        s.fill((70, 56, 50), (x - 1, by - 30, 3, 2))
        return
    if hat == 'tophat':
        c = (40, 36, 46)
        s.fill(c, (x - 5, by - 22, 11, 1))
        s.fill(c, (x - 3, by - 30, 7, 8))
        s.fill((190, 60, 70), (x - 3, by - 24, 7, 1))
        s.fill((70, 64, 80), (x - 2, by - 29, 1, 4))
        return
    if hat == 'bucket':
        c = (122, 156, 112)
        s.fill(darken(c, 0.15), (x - 5, by - 22, 11, 2))
        s.set_at((x - 6, by - 21), darken(c, 0.15))
        s.set_at((x + 6, by - 21), darken(c, 0.15))
        s.fill(c, (x - 3, by - 26, 7, 4))
        s.fill(lighten(c, 0.2), (x - 2, by - 26, 5, 1))
    elif hat == 'beret':
        c = (184, 62, 74)
        s.fill(c, (x - 4, by - 24, 9, 3))
        s.fill(c, (x + 3, by - 25, 3, 1))
        s.fill(darken(c, 0.25), (x - 4, by - 22, 9, 1))
        s.set_at((x, by - 25), darken(c, 0.3))
    elif hat == 'flower':
        s.fill(hair, (x - 3, by - 23, 7, 2))
        for i, (dx, dy, c) in enumerate(((-3, -23, (250, 160, 190)), (-1, -24, (255, 236, 120)),
                                         (1, -23, (255, 255, 255)), (3, -24, (230, 140, 220)))):
            s.set_at((x + dx, by + dy), c)
            s.set_at((x + dx + 1, by + dy + (1 if i % 2 else 0)), (110, 170, 90))
    elif hat == 'captain':
        s.fill((244, 244, 240), (x - 3, by - 26, 7, 4))
        s.fill((40, 44, 60), (x - 3, by - 23, 7, 1))
        s.fill((40, 44, 60), (x + 2, by - 22, 4, 1))
        s.set_at((x, by - 25), (240, 196, 70))
    elif hat == 'frog':
        c = (112, 184, 92)
        s.fill(c, (x - 4, by - 25, 9, 4))
        s.fill(darken(c, 0.2), (x - 4, by - 22, 9, 1))
        for ex in (x - 3, x + 3):
            s.fill((255, 255, 250), (ex - 1, by - 27, 2, 2))
            s.set_at((ex, by - 26), (30, 30, 30))
        s.fill((230, 120, 130), (x + 1, by - 23, 2, 1))
    elif hat == 'beanie' or (hat == 'straw' and season == 3):
        c = (90, 122, 200) if hat == 'beanie' else (170, 80, 80)
        s.fill(c, (x - 4, by - 25, 9, 4))
        for i in range(-4, 5, 2):
            s.set_at((x + i, by - 24), darken(c, 0.15))
        s.fill((240, 240, 240) if hat == 'straw' else lighten(c, 0.3), (x - 4, by - 22, 9, 1))
        s.fill((250, 250, 250), (x, by - 27, 2, 2))
    else:
        hat_c = (232, 204, 124)
        s.fill(hat_c, (x - 6, by - 22, 13, 2))
        s.fill(hat_c, (x - 3, by - 25, 7, 3))
        s.fill((196, 82, 72), (x - 3, by - 23, 7, 1))


def draw_cat_item(s, item, hx, hy, sleeping):
    """Biscuit's accessory. (hx, hy) is the centre of her head."""
    if item == 'bell':
        s.fill((200, 60, 60), (hx - 3, hy + 3, 5, 1))
        s.fill((246, 200, 70), (hx - 1, hy + 4, 2, 2))
    elif item == 'scarf':
        s.fill((86, 150, 200), (hx - 3, hy + 3, 6, 2))
        s.fill((86, 150, 200), (hx - 3 if not sleeping else hx - 5, hy + 4, 2, 3))
        s.set_at((hx - 1, hy + 3), (240, 240, 240))
        s.set_at((hx + 1, hy + 4), (240, 240, 240))
    elif item == 'crown':
        c = (246, 204, 70)
        s.fill(c, (hx - 2, hy - 6, 5, 2))
        for dx in (-2, 0, 2):
            s.set_at((hx + dx, hy - 7), c)
        s.set_at((hx, hy - 6), (220, 80, 90))
    elif item == 'bow':
        c = (236, 120, 170)
        bx, by = hx + 2, hy - 5
        for dx, dy in ((-1, 0), (1, 0), (-1, 1), (1, 1)):
            s.set_at((bx + dx, by + dy), c)
        s.set_at((bx, by), darken(c, 0.25))


TRICK_TIME = 1.6


def draw_cat(s, g, t, x=CAT_X, fy=DECK_Y, bed=None, sleep=None, face=1, walk=0.0, trick=True, look=None):
    """Biscuit. By default she sits on the dock; the cabin room and Fernwick pass their own spot."""
    cat = g.cat
    orange, white, dark = (232, 150, 78), (250, 240, 228), (192, 110, 56)
    sleeping = cat['sleep'] if sleep is None else sleep
    if bed is None:
        bed = g.has('catbed')
    tr = cat.get('trick') if trick else None
    if (tr and tr[1] > 0 and not sleeping) or face != 1:
        tmp = pygame.Surface((48, 44), pygame.SRCALPHA)
        draw_cat(tmp, g, t, 24, 30, bed=False, sleep=sleeping, walk=walk, trick=False, look=look)
        dx = dy = 0
        if tr and tr[1] > 0 and not sleeping:
            p = 1 - tr[1] / TRICK_TIME
            kind = tr[0]
            if kind == 'spin':
                if int(p * 10) % 2:
                    tmp = pygame.transform.flip(tmp, True, False)
                dy = -int(abs(math.sin(p * math.pi * 5)) * 2)
            elif kind == 'roll':
                tmp = pygame.transform.rotate(tmp, -int(p * 4) * 90 % 360 if p < 0.9 else 0)
                dx = int(math.sin(p * math.pi) * 6)
            elif kind == 'flip':
                dy = -int(math.sin(p * math.pi) * 16)
                tmp = pygame.transform.rotate(tmp, int(p * 360) // 30 * 30 % 360)
            elif kind == 'beg':
                tmp = pygame.transform.rotate(tmp, int(math.sin(p * math.pi) * 3) * 8)
                dy = -int(math.sin(p * math.pi) * 3)
            elif kind == 'paw':
                up = int(math.sin(min(1.0, p * 1.6) * math.pi / 2) * 5)
                tmp.fill(orange, (29, 18 - up, 2, 5))
                tmp.fill(white, (29, 18 - up, 2, 1))
        if face != 1:
            tmp = pygame.transform.flip(tmp, True, False)
        if bed:
            _cat_bed(s, x, fy)
            fy -= 2
        r = tmp.get_rect(center=(x + dx, fy - 8 + dy))     # she turns about her middle
        s.blit(tmp, r)
        return
    if bed:
        _cat_bed(s, x, fy)
        fy -= 2
    if sleeping:
        pygame.draw.ellipse(s, orange, (x - 7, fy - 6, 14, 6))
        pygame.draw.ellipse(s, dark, (x - 5, fy - 6, 4, 2))
        pygame.draw.circle(s, orange, (x + 4, fy - 4), 3)
        s.fill(orange, (x + 3, fy - 8, 2, 2))
        s.fill(orange, (x + 6, fy - 8, 1, 2))
        s.fill((80, 50, 40), (x + 4, fy - 4, 2, 1))
        pygame.draw.line(s, orange, (x - 7, fy - 1), (x + 2, fy - 1))
        draw_cat_item(s, getattr(g, 'cat_item', 'none'), x + 4, fy - 5, True)
        return
    bounce = 0
    if cat['excited'] > 0:
        bounce = -int(abs(math.sin(t * 12)) * 2)
    if walk:
        bounce = -int(abs(math.sin(walk)) * 2)
    y = fy + bounce
    # tail
    sw = math.sin(t * (2.0 if cat['excited'] <= 0 else 7.0)) * 3
    pts = [(x - 5, y - 2), (x - 8, y - 3), (x - 10 + sw * 0.3, y - 6), (x - 10 + sw, y - 10)]
    pygame.draw.lines(s, orange, False, pts, 2)
    s.set_at((int(x - 10 + sw), y - 11), dark)
    # body
    pygame.draw.ellipse(s, orange, (x - 6, y - 9, 11, 9))
    for i in (-4, -2):
        s.fill(dark, (x + i, y - 8, 1, 3))
    s.fill(white, (x + 1, y - 6, 3, 5))
    s.fill(white, (x + 1, y - 1, 2, 1))
    s.fill(white, (x + 3, y - 1, 2, 1))
    # head
    if look is None:
        look = 1 if g.fishing.state in ('waiting', 'bite', 'fight') and g.place == 'lake' else 0
    hx, hy = x + 3 + look, y - 12
    pygame.draw.circle(s, orange, (hx, hy), 4)
    pygame.draw.polygon(s, orange, [(hx - 4, hy - 2), (hx - 3, hy - 6), (hx - 1, hy - 3)])
    pygame.draw.polygon(s, orange, [(hx + 4, hy - 2), (hx + 3, hy - 6), (hx + 1, hy - 3)])
    s.set_at((hx - 3, hy - 4), (240, 170, 160))
    s.set_at((hx + 3, hy - 4), (240, 170, 160))
    s.fill(white, (hx - 1, hy + 1, 3, 2))
    blink = (t % 4.0) < 0.15 or cat['pet'] > 0
    eye = (60, 70, 40)
    if blink:
        s.fill(eye, (hx - 2, hy, 2, 1))
        s.fill(eye, (hx + 1, hy, 2, 1))
    else:
        s.fill(eye, (hx - 2, hy - 1, 1, 2))
        s.fill(eye, (hx + 2, hy - 1, 1, 2))
    s.set_at((hx, hy + 1), (220, 120, 120))
    draw_cat_item(s, getattr(g, 'cat_item', 'none'), hx, hy, False)


def _cat_bed(s, x, fy):
    pygame.draw.ellipse(s, (170, 60, 64), (x - 9, fy - 4, 18, 5))
    pygame.draw.ellipse(s, (210, 96, 92), (x - 8, fy - 5, 16, 4))
    for i in range(-6, 7, 3):
        s.set_at((x + i, fy - 3), (240, 200, 190))


def draw_decor(s, g, t):
    env = g.env
    season = env.season
    if g.has('flowers'):
        petals = {0: [(250, 160, 190), (255, 230, 120)], 1: [(250, 120, 110), (250, 220, 90)],
                  2: [(230, 140, 60), (200, 90, 70)], 3: [(220, 40, 50), (240, 240, 240)]}[season]
        for i, px in enumerate((114, 178)):
            pygame.draw.polygon(s, (190, 100, 70), [(px - 3, DECK_Y - 5), (px + 3, DECK_Y - 5), (px + 2, DECK_Y), (px - 2, DECK_Y)])
            s.fill((160, 80, 56), (px - 3, DECK_Y - 5, 7, 1))
            stem = (80, 140, 70) if season != 3 else (40, 100, 60)
            for j, (dx, h) in enumerate(((-2, 5), (0, 8), (2, 6))):
                sway = int(math.sin(t * 1.5 + j + i) * 0.8)
                pygame.draw.line(s, stem, (px + dx, DECK_Y - 5), (px + dx + sway, DECK_Y - 5 - h))
                s.fill(petals[(i + j) % 2], (px + dx + sway - 1, DECK_Y - 6 - h, 2 if season != 3 else 1, 2))
    if g.has('teaset'):
        kx = 132
        s.fill((126, 90, 60), (kx - 5, DECK_Y - 6, 11, 6))
        s.fill((100, 70, 48), (kx - 5, DECK_Y - 6, 11, 1))
        pygame.draw.ellipse(s, (116, 150, 172), (kx - 3, DECK_Y - 11, 7, 5))
        s.fill((96, 126, 146), (kx - 1, DECK_Y - 12, 3, 1))
        pygame.draw.line(s, (116, 150, 172), (kx + 3, DECK_Y - 8), (kx + 6, DECK_Y - 11))
        s.fill((244, 236, 222), (kx + 7, DECK_Y - 3, 3, 3))
        if g.world.rng.random() < 0.06:
            g.world.steam(kx + 6, DECK_Y - 12)
    if g.has('chimes'):
        px = POLES[0]
        pygame.draw.line(s, (110, 80, 56), (px, 250), (px + 8, 250))
        for i, ln in enumerate((6, 9, 7, 10)):
            sw = math.sin(t * 2.2 + i * 0.9) * env.wind * 2
            cx = px + 2 + i * 2
            pygame.draw.line(s, (206, 210, 220), (cx, 251), (cx + sw, 251 + ln))
    if g.has('lights'):
        bulbs = light_bulbs()
        prev = (POLES[0], 248)
        for (x, y, c) in bulbs:
            pygame.draw.line(s, (70, 62, 56), prev, (x, y))
            prev = (x, y)
        pygame.draw.line(s, (70, 62, 56), prev, (POLES[1], 248))
        for (x, y, c) in bulbs:
            s.fill(lerp_c(darken(c, 0.35), c, env.nf), (x, y + 1, 1, 2))
    if g.has('lantern'):
        px = POLES[1]
        pygame.draw.line(s, (90, 70, 56), (px, 249), (px + 7, 249))
        sw = int(math.sin(t * 1.4) * env.wind)
        lx = px + 7 + sw
        pygame.draw.line(s, (60, 56, 56), (px + 7, 249), (lx, 252))
        s.fill((70, 64, 60), (lx - 2, 252, 5, 1))
        s.fill(lerp_c((180, 160, 120), (255, 222, 150), env.nf), (lx - 2, 253, 5, 6))
        s.fill((70, 64, 60), (lx - 2, 253, 1, 6))
        s.fill((70, 64, 60), (lx + 2, 253, 1, 6))
        s.fill((70, 64, 60), (lx - 3, 259, 7, 1))


def draw_extras(s, g, t):
    """Newer decorations: pinwheel, telescope and the birthday gifts."""
    env = g.env
    if g.has('rowboat') or g.has('boat'):
        bob = math.sin(t * 1.2) * 0.6
        x0, y0 = 156, 309 + bob
        hull = [(x0, y0), (x0 + 28, y0), (x0 + 24, y0 + 5), (x0 + 4, y0 + 5)]
        pygame.draw.polygon(s, (92, 130, 150), hull)
        pygame.draw.line(s, (236, 230, 214), hull[0], hull[1])
        s.fill((150, 106, 70), (x0 + 9, int(y0) - 1, 3, 2))
        s.fill((150, 106, 70), (x0 + 18, int(y0) - 1, 3, 2))
        pygame.draw.line(s, (120, 88, 60), (x0 + 6, y0 + 1), (x0 - 4, y0 + 7))
        pygame.draw.line(s, (200, 190, 170), (x0 + 1, y0), (150, DECK_Y + 6))
    if g.has('bench'):
        bx = 146
        c, cd = (150, 100, 66), (112, 74, 50)
        s.fill(c, (bx, DECK_Y - 6, 20, 2))
        s.fill(c, (bx, DECK_Y - 11, 20, 2))
        s.fill(cd, (bx + 1, DECK_Y - 11, 1, 11))
        s.fill(cd, (bx + 18, DECK_Y - 11, 1, 11))
        s.fill(cd, (bx + 3, DECK_Y - 4, 1, 4))
        s.fill(cd, (bx + 16, DECK_Y - 4, 1, 4))
        s.fill(lighten(c, 0.2), (bx, DECK_Y - 11, 20, 1))
    if g.has('pinwheel'):
        px, py = 197, DECK_Y - 12
        pygame.draw.line(s, (206, 196, 176), (px, DECK_Y), (px, py))
        a0 = t * (2 + env.wind * 10)
        for i, c in enumerate(((240, 100, 100), (250, 210, 90), (110, 170, 230), (130, 200, 120))):
            a = a0 + i * math.pi / 2
            tip = (px + math.cos(a) * 4, py + math.sin(a) * 4)
            side = (px + math.cos(a + 0.9) * 2.5, py + math.sin(a + 0.9) * 2.5)
            pygame.draw.polygon(s, c, [(px, py), tip, side])
        s.set_at((px, py), (250, 250, 240))
    if g.has('telescope'):
        tx = 89
        ty = int(bank_top(tx))
        leg = (92, 70, 54)
        pygame.draw.line(s, leg, (tx, ty - 8), (tx - 3, ty))
        pygame.draw.line(s, leg, (tx, ty - 8), (tx + 3, ty))
        pygame.draw.line(s, leg, (tx, ty - 8), (tx, ty))
        pygame.draw.line(s, (196, 160, 80), (tx - 4, ty - 6), (tx + 6, ty - 13), 2)
        pygame.draw.line(s, (230, 200, 120), (tx - 4, ty - 7), (tx + 6, ty - 14))
        s.fill((80, 70, 60), (tx + 6, ty - 15, 2, 2))
    if g.has('gnome'):
        gx = 63
        gy = int(bank_top(gx))
        s.fill((80, 110, 170), (gx - 2, gy - 4, 5, 4))
        s.fill((240, 214, 190), (gx - 1, gy - 6, 3, 2))
        s.fill((250, 250, 250), (gx - 2, gy - 5, 5, 2))
        pygame.draw.polygon(s, (210, 70, 70), [(gx - 2, gy - 6), (gx + 3, gy - 6), (gx, gy - 12)])
        s.fill((60, 50, 40), (gx - 2, gy, 2, 1))
        s.fill((60, 50, 40), (gx + 1, gy, 2, 1))


BOAT_X0, BOAT_X1 = 186, 286          # the rowboat you fish from away from the dock


def draw_boat_back(s, g, t):
    """The far side of the rowboat, drawn behind Biscuit and the angler."""
    y = DECK_Y
    s.fill((96, 66, 46), (BOAT_X0 + 4, y - 6, BOAT_X1 - BOAT_X0 - 8, 3))
    s.fill((120, 84, 58), (BOAT_X0 + 4, y - 7, BOAT_X1 - BOAT_X0 - 8, 1))
    # a little seat plank
    s.fill((150, 108, 72), (BOAT_X0 + 30, y - 5, 14, 2))


def draw_boat_front(s, g, t):
    """The near side of the hull, with oars and (if you own one) a lantern on a pole."""
    env = g.env
    y = DECK_Y
    wood, wood_d, paint = (150, 104, 70), (112, 76, 52), (84, 126, 150)
    hull = [(BOAT_X0 - 4, y - 5), (BOAT_X1 + 4, y - 7), (BOAT_X1 - 4, y + 5), (BOAT_X0 + 6, y + 5)]
    pygame.draw.polygon(s, wood, hull)
    pygame.draw.line(s, lighten(wood, 0.25), hull[0], hull[1])
    pygame.draw.line(s, paint, (BOAT_X0 - 1, y - 2), (BOAT_X1 + 1, y - 3), 2)
    pygame.draw.line(s, wood_d, (BOAT_X0 + 5, y + 4), (BOAT_X1 - 5, y + 4))
    for x in range(BOAT_X0 + 14, BOAT_X1 - 6, 16):
        s.set_at((x, y + 1), wood_d)
    # the hull sits in the water: a soft waterline
    pygame.draw.line(s, (40, 60, 80, 120), (BOAT_X0 + 6, y + 6), (BOAT_X1 - 4, y + 6))
    # oar resting in the rowlock, blade in the water
    sway = math.sin(t * 1.1) * 0.6
    pygame.draw.line(s, (176, 134, 90), (BOAT_X0 + 18, y - 6), (BOAT_X0 - 14, y + 10 + sway))
    pygame.draw.ellipse(s, (160, 118, 80), (BOAT_X0 - 20, int(y + 8 + sway), 9, 4))
    if g.has('lantern'):
        px = BOAT_X0 + 10
        pygame.draw.line(s, (90, 70, 56), (px, y - 4), (px, y - 22))
        s.fill((60, 56, 50), (px - 2, y - 22, 5, 1))
        s.fill(lerp_c((180, 160, 120), (255, 222, 150), env.nf), (px - 2, y - 21, 5, 6))
        s.fill((70, 64, 60), (px - 2, y - 21, 1, 6))
        s.fill((70, 64, 60), (px + 2, y - 21, 1, 6))
        s.fill((70, 64, 60), (px - 3, y - 15, 7, 1))


# ---------------------------------------------------------------- friends (online co-op)
PEER_COLORS = [(236, 150, 92), (110, 168, 214), (150, 196, 110), (196, 132, 204)]
PEER_HAIR = [(112, 72, 52), (58, 44, 42), (206, 158, 86), (150, 72, 52)]
DOCK_SLOTS = (194, 168, 142)           # where friends stand on your dock, nearest first
BOAT_SLOTS = ((440, 256, 0.9), (534, 247, 0.8), (372, 266, 1.0))   # their rowboats out on the water
LINE_C = (236, 236, 226, 190)

ICONS = {
    'heart': ((228, 84, 104), ['.##.##.', '#######', '#######', '.#####.', '..###..', '...#...']),
    'note': ((84, 92, 150), ['...###', '...#.#', '...#..', '.###..', '####..', '.##...']),
    'bang': ((220, 80, 70), ['#', '#', '#', '#', '.', '#']),
    'fish': ((74, 140, 196), ['..###..#', '.######.', '########', '.######.', '..###..#']),
    'dots': ((120, 110, 120), ['.......', '.......', '#.#.#..', '.......']),
}
EMOTES = ('heart', 'note', 'bang', 'fish')


def draw_bubble(s, x, y, kind, t=0.0):
    """A little speech bubble with a pixel icon, its tail pointing down at (x, y)."""
    col, rows = ICONS.get(kind, ICONS['dots'])
    w = max(len(r) for r in rows) + 4
    h = len(rows) + 4
    bx, by = x - w // 2, y - h - 3 + int(math.sin(t * 3) * 0.6)
    ink = (64, 52, 62)
    s.fill(ink, (bx + 1, by, w - 2, h))
    s.fill(ink, (bx, by + 1, w, h - 2))
    s.fill((252, 250, 244), (bx + 1, by + 1, w - 2, h - 2))
    s.fill(ink, (x - 1, by + h, 3, 1))
    s.set_at((x, by + h + 1), ink)
    s.fill((252, 250, 244), (x, by + h - 1, 1, 1))
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == '#':
                s.set_at((bx + 2 + i, by + 2 + j), col)


def peer_places(g):
    """Friends fishing at the same spot as you: [(id, view, kind, x, y, scale)], kind 'dock' or 'boat'."""
    net = getattr(g, 'net', None)
    if net is None or not net.online:
        return []
    if getattr(g, 'place', 'lake') != 'lake':
        return []
    here = [(pid, p['v']) for pid, p in sorted(net.peers.items())
            if p.get('v') and p['v']['spot'] == g.spot and p['v'].get('place', 'lake') == 'lake']
    out = []
    for i, (pid, v) in enumerate(here[:3]):
        if g.spot == 'dock':
            out.append((pid, v, 'dock', DOCK_SLOTS[i], DECK_Y, 1.0))
        else:
            bx, by, k = BOAT_SLOTS[i]
            out.append((pid, v, 'boat', bx, by, k))
    return out


def _line(s, tip, end, sag, col=LINE_C):
    tx, ty = tip
    bx, by = end
    mx, my = (tx + bx) / 2, (ty + by) / 2 + sag
    pts = []
    for i in range(13):
        k = i / 12
        pts.append(((1 - k) ** 2 * tx + 2 * (1 - k) * k * mx + k * k * bx,
                    (1 - k) ** 2 * ty + 2 * (1 - k) * k * my + k * k * by))
    pygame.draw.lines(s, col, False, pts)


def _water_mark(s, fs, x, y, t):
    x, y = int(x), int(y)
    if fs in ('casting', 'waiting', 'reel_back'):
        s.fill((250, 250, 245), (x, y - 1, 2, 1))
        s.fill((220, 60, 60), (x, y - 2, 2, 1))
    elif fs == 'bite':
        s.fill((220, 60, 60), (x - 1, y - 2, 3, 1))
        s.fill((255, 255, 255, 200), (x - 3, y - 1, 7, 1))
    elif fs == 'fight':
        for i in range(4):
            a = t * 9 + i * 1.6
            s.set_at((x + int(math.cos(a) * 5), y + int(math.sin(a) * 2)), (240, 248, 255, 220))
        s.fill((255, 255, 255, 180), (x - 5, y, 10, 1))


def draw_peer_dock(s, g, t, pid, v, x):
    from data import ROD_BY_ID, ALL_BY_ID
    fs = v['fs']
    breathe = 1 if math.sin(t * 1.6 + pid * 1.7) > 0.6 else 0
    if fs == 'caught':
        breathe = -1 if math.sin(t * 10) > 0 else 0
    shirt = PEER_COLORS[pid % 4]
    by = draw_person(s, x, DECK_Y, shirt, PEER_HAIR[pid % 4], v['hat'], g.env.season, breathe, fs == 'caught')
    hand = (x + HAND[0] - PLAYER_X, HAND[1] + breathe)
    pygame.draw.line(s, shirt, (x + 1, by - 13), (hand[0] - 1, hand[1]))
    s.fill((240, 202, 172), (hand[0] - 1, hand[1] - 1, 2, 2))
    rod = ROD_BY_ID[v['rod']]
    bob = v['bob']
    pts = rod_points(hand, v['ang'], v['bend'], rod['length'], bob)
    draw_rod(s, pts, rod['color'])
    if bob and fs in ('casting', 'waiting', 'bite', 'fight', 'reel_back'):
        _line(s, pts[-1], bob, 2 if fs in ('casting', 'fight') else 9)
        _water_mark(s, fs, bob[0], bob[1], t)
    if fs == 'caught' and v['held'] in ALL_BY_ID:
        draw_held_fish(s, ALL_BY_ID[v['held']], hand[0], hand[1])


def draw_peer_boat(s, g, t, pid, v, x, y, k):
    """A friend in their own rowboat, out on the water at this spot."""
    bob = math.sin(t * 1.2 + pid) * 0.6
    y = int(y + bob)
    w = int(15 * k)
    wood = (150, 104, 70)
    hull = [(x - w, y - 2), (x + w, y - 3), (x + w - 4, y + 3), (x - w + 4, y + 3)]
    pygame.draw.polygon(s, wood, hull)
    pygame.draw.line(s, lighten(wood, 0.25), hull[0], hull[1])
    pygame.draw.line(s, (84, 126, 150), (x - w + 2, y), (x + w - 2, y - 1))
    s.fill((40, 60, 80, 110), (x - w + 4, y + 4, 2 * w - 8, 1))
    # the angler, small with distance
    shirt = PEER_COLORS[pid % 4]
    fs = v['fs']
    hop = -1 if fs == 'caught' and math.sin(t * 10) > 0 else 0
    s.fill(shirt, (x - 2, y - 8 + hop, 4, 6))
    s.fill((240, 202, 172), (x - 1, y - 11 + hop, 3, 3))
    s.fill(PEER_HAIR[pid % 4], (x - 2, y - 11 + hop, 1, 3))
    s.fill((232, 204, 124) if v['hat'] == 'straw' else (120, 100, 90), (x - 2, y - 12 + hop, 5, 1))
    tip = (x + int(9 * k), y - int(15 * k))
    pygame.draw.line(s, (120, 88, 60), (x + 1, y - 6), tip)
    if fs in ('waiting', 'bite', 'fight', 'reel_back', 'casting'):
        end = (x + int(26 * k), y + 3)
        _line(s, tip, end, 1 if fs == 'fight' else 4)
        _water_mark(s, fs, end[0], end[1], t)
    if fs == 'caught' and v['held']:
        s.fill((236, 200, 120), (x + 3, y - 16, 2, 5))
        s.set_at((x + 3, y - 17), (255, 250, 220))


def draw_peers(s, g, t, kind):
    for pid, v, k, x, y, sc in peer_places(g):
        if k != kind:
            continue
        if k == 'dock':
            draw_peer_dock(s, g, t, pid, v, x)
        else:
            draw_peer_boat(s, g, t, pid, v, x, y, sc)


def draw_bubbles(s, g, t):
    em = getattr(g, 'emote', None)
    if em:
        draw_bubble(s, PLAYER_X + 1, DECK_Y - 29, em[0], t)
    for pid, v, k, x, y, sc in peer_places(g):
        kind = v['em'] or ('dots' if v['away'] else None)
        if kind:
            draw_bubble(s, x + 1, y - (29 if k == 'dock' else int(14 * sc) + 2), kind, t + pid)


def draw_all(s, g, t):
    if getattr(g, 'spot', 'dock') == 'dock':
        draw_decor(s, g, t)
        draw_extras(s, g, t)
        draw_peers(s, g, t, 'dock')
        draw_cat(s, g, t)
        draw_player(s, g, t)
    else:
        draw_peers(s, g, t, 'boat')
        draw_boat_back(s, g, t)
        draw_cat(s, g, t)
        draw_player(s, g, t)
        draw_boat_front(s, g, t)
    draw_bubbles(s, g, t)
