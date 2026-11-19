"""Fernwick, the little village up the path from the lake.

A street you walk along (A / D, or click where to go), with shops to step into, townsfolk going about their day,
and plenty to do: Mabel's bakery snacks, a museum to fill with fish, the notice board's odd jobs, a wishing
fountain, Pip's ring toss stall, the library's fish notes, town projects at the hall, and friendships to grow.

Everything here is drawn in code like the rest of the game. Town state that should last lives on the Game
(saved with everything else); this module keeps only what is on screen right now.
"""
import math
import random

import pygame

import actors
import art
import dialogue
import kitchen
import pixfont
import ui as U
from art import W, H, HORIZON, lerp_c, darken, lighten, add_glow
from data import (FISH, FISH_BY_ID, ALL_BY_ID, RARITY_COLORS, BAIT_BY_ID, BIRTHDAYS,
                  SEASONS)

TOWN_W = 1920          # the street is three screens long
GROUND = 302           # where feet touch the pavement
WALK = 62.0            # your walking speed, world pixels per second
PANELS = ('bakery', 'museum', 'board', 'hall', 'ringtoss', 'library', 'talk', 'cocoa')

# ---------------------------------------------------------------- the townsfolk
FOLK = {
    'mabel': dict(name='Mabel', shirt=(236, 172, 182), hair=(150, 96, 70), hat='chef', home=404, work=(360, 1080),
                  loves='perch', req='Mabel from the bakery', lines=[
                      "Fresh buns at six sharp. The early angler gets the warm ones.",
                      "Flour on my nose again? It's a baker's freckle, dear.",
                      "A Lakeside Tea before fishing, and the fish practically queue up.",
                      "I tried a fish pie once. Biscuit ate the whole crust.",
                      "My mother ran this bakery, and her mother before that. Same oven!"]),
    'tom': dict(name='Old Tom', shirt=(100, 124, 92), hair=(214, 214, 210), hat='bucket', home=226,
                work=(420, 1140), loves='catfish', req='Old Tom', lines=[
                    "Catfish like it murky and late. Like me.",
                    "Sixty years of fishing and that Muskie still laughs at me.",
                    "Don't yank the line, coax it. Like asking a cat to come inside.",
                    "A good knot is worth more than a good rod. Mostly.",
                    "The lake talks if you listen. Mostly it says 'not today'.",
                    "My gnome moved again last night. I'm not saying anything. I'm just saying."]),
    'juniper': dict(name='Juniper', shirt=(126, 176, 150), hair=(86, 56, 44), hat='flower', home=972,
                    work=(540, 1020), loves='sunfish', req='Juniper', lines=[
                        "Every fish you bring to the museum gets its own little tank and a name card.",
                        "Did you know some fish only come out under a full moon? I think about that a lot.",
                        "I'm writing a guide to the lake. Chapter one is 'Be Patient'. It's the whole chapter.",
                        "The aquarium hums at night. The fish seem to like it.",
                        "Honey Sunfish glow in summer light. I could watch them for hours.",
                        "If you find a fish I've never seen, come find me right away!"]),
    'pip': dict(name='Pip', shirt=(236, 196, 92), hair=(176, 104, 60), hat='frog', home=1352, work=(720, 1260),
                loves='bluegill', req='Pip (age 9)', kid=True, lines=[
                    "Ring toss! Ring toss! Win a hat that makes you look fancy!",
                    "I can do a perfect throw with my eyes closed. Well, nearly.",
                    "Bluegills are the best fish. They look like they're smiling.",
                    "Mayor Hazel says I'm the youngest business owner in Fernwick.",
                    "I saw a frog bigger than my head at the cove. I'm not lying!",
                    "Can your cat do tricks? Biscuit can sleep standing up, I bet."]),
    'hazel': dict(name='Mayor Hazel', shirt=(120, 104, 168), hair=(70, 60, 72), hat='bowler', home=1192,
                  work=(540, 1020), loves='pike', req='Mayor Hazel', lines=[
                      "Every coin for a town project goes straight into Fernwick. Mostly into flowers.",
                      "The festival committee meets Tuesdays. The festival committee is me.",
                      "Fernwick has been here as long as the lake has. Well, nearly as long.",
                      "A town is just neighbours who agreed to share a street.",
                      "I was a champion angler once. The trophy is in my office. Polished daily.",
                      "If you see Pip running a 'raffle', it's not an official raffle."]),
    'fen': dict(name='Fen', shirt=(204, 120, 96), hair=(60, 46, 40), hat='beret', home=1702, work=(480, 1200),
                loves='trout', req='Fen the painter', lines=[
                    "The light on the lake at dusk is the hardest colour to mix. I keep trying.",
                    "I'm painting the street today. Hold still. No, keep walking. That's better.",
                    "A trout's back has eleven colours on it. I counted.",
                    "My old boat is yours now, I hear? Treat her kindly, she leaks on the left.",
                    "Rainy days are for painting indoors and pretending I'm not hungry.",
                    "Someday I'll paint every fish in the lake. I'm on fish number three."]),
    'librarian': dict(name='Ms. Alder', shirt=(150, 120, 96), hair=(196, 196, 204), hat='none', home=1512,
                      work=(540, 1200), loves='char', req='The librarian', glasses=True, lines=[
                          "Shh. Oh, it's you. You may speak normally, the books are asleep.",
                          "The fish notes are on the second shelf. Read them before you go out.",
                          "Arctic Char like the cold and the deep. So do I, frankly.",
                          "Someone returned a book about knots, all tied up. Very funny.",
                          "Every bottled letter you find is a story someone wanted told.",
                          "A quiet street is a happy street. Except during the festival."]),
    # moves into the cream cottage in year two (yeartwo.py)
    'rowan': dict(name='Rowan', shirt=(64, 84, 124), hair=(230, 228, 222), hat='beanie', home=1651,
                  work=(480, 1140), loves='burbot', req='Rowan at the cottage', new_in_year=1, lines=[
                      "Forty years of foghorns. Do you know how quiet a lake is? I keep waking up to check it.",
                      "A lighthouse keeper's job is mostly polishing. I've polished every spoon in the cottage.",
                      "Burbot bite best on cold dark nights. Like most good things.",
                      "Fen wants to paint me. I said only if I can hold a fish.",
                      "Pip asked if I've seen a mermaid. I said only on Tuesdays.",
                      "Your Grandma Rosie wrote to the lighthouse once, did you know? Asked about the stars."]),
}
FOLK_ORDER = ['mabel', 'tom', 'juniper', 'pip', 'hazel', 'fen', 'librarian', 'rowan']
REQ_TO_FOLK = {f['req']: k for k, f in FOLK.items()}

# ---------------------------------------------------------------- buildings and places along the street
# id: name, left and right edge, door x, opening hours (minutes) and who runs it
PLACES = [
    dict(id='lake', name='Path to Lantern Lake', x0=0, x1=96, door=44, hours=None),
    dict(id='tackle', name="Old Tom's Tackle", x0=132, x1=318, door=226, hours=(420, 1140), keeper='tom'),
    dict(id='bakery', name="Mabel's Bakery", x0=338, x1=474, door=404, hours=(360, 1080), keeper='mabel'),
    dict(id='board', name='Notice board', x0=520, x1=576, door=548, hours=None),
    dict(id='fountain', name='Wishing fountain', x0=616, x1=690, door=652, hours=None),
    dict(id='cocoa', name="Mabel's Cocoa Cart", x0=694, x1=724, door=709, hours=(1230, 1440), keeper='mabel'),
    dict(id='museum', name='Fernwick Aquarium', x0=862, x1=1084, door=972, hours=(540, 1020), keeper='juniper'),
    dict(id='hall', name='Town Hall', x0=1108, x1=1276, door=1192, hours=(540, 1020), keeper='hazel'),
    dict(id='ringtoss', name="Pip's Ring Toss", x0=1300, x1=1404, door=1352, hours=(720, 1260), keeper='pip'),
    dict(id='library', name='Library', x0=1430, x1=1594, door=1512, hours=(540, 1200), keeper='librarian'),
    dict(id='lookout', name='Lookout bench', x0=1790, x1=1910, door=1846, hours=None),
]
PLACE_BY_ID = {p['id']: p for p in PLACES}
LAKE_VIEW = (1764, GROUND - 34)  # where the lake opens up behind the lookout (x, the far shore's y)
BENCH_X = 1846                   # the lookout bench: you sit here, Biscuit curls up just to your right
BENCH_SEAT = GROUND - 10
TOWN_Z = 1.75                    # how close the camera sits in the village
# things along the front of the street, in front of everyone who walks past
FRONT = [(168, 'barrel'), (300, 'crates'), (560, 'bike'), (938, 'churns'), (1012, 'crates'), (1236, 'barrel'),
         (1478, 'bike'), (1664, 'churns')]
PIGEON_SPOTS = (618, 690, 1004, 1460)

SNACKS = [
    dict(id='bun', name='Honey Bun', price=30, desc='Sticky and warm. A little luck for today.'),
    dict(id='tea', name='Lakeside Tea', price=45, desc='Fish bite sooner for the rest of the day.'),
    dict(id='pie', name='Blueberry Pie', price=60, desc='Fish run a little bigger for the rest of the day.'),
    dict(id='cookie', name='Star Cookie', price=80, desc='Rare fish come out more often for the rest of the day.'),
]
# Mabel wheels a cart out to the square after dark. These last the night, not the day.
NIGHT_SNACKS = [
    dict(id='cocoa', name='Hot Cocoa', price=35, desc='Warm hands. Night fish bite sooner until dawn.', night=True),
    dict(id='mooncake', name='Moon Cake', price=50, desc='Night-time fish come out more until dawn.', night=True),
]
SNACK_BY_ID = {s['id']: s for s in SNACKS + NIGHT_SNACKS}
CONSTELLATIONS = ['The Heron', 'The Leaping Trout', 'The Lantern Keeper', 'The Sleeping Bear']
PROJECTS = [
    dict(id='flowers', name='Flower Beds', cost=300, desc='Planters bloom all along the high street.'),
    dict(id='lamps', name='Street Lanterns', cost=600, desc='Warm lanterns light the street after dark.'),
    dict(id='bandstand', name='Bandstand', cost=1000,
         desc='Musicians play in the square every evening, and the town comes out.'),
    dict(id='lighthouse', name='Lighthouse', cost=6000,
         desc='A lighthouse on the far shore of the lake. By its light, rare fish come out more at night.'),
]
UPGRADES = [
    dict(id='stove', name='Copper Stove', cost=900, desc='Every recipe you cook makes two servings.'),
    dict(id='tank', name='Bigger Fish Tank', cost=1200, desc='Your cabin tank holds 12 fish instead of 8.'),
    dict(id='icebox', name='Ice Chest', cost=1500, desc='Fish stay fresh in your basket and sell for 15% more.'),
    dict(id='shed', name='Bait Shed', cost=2000, desc='Every morning there is fresh Sweet Corn and Glow Grubs inside.'),
    dict(id='loft', name='Cozy Loft', cost=2500, desc='You sleep so well up there that you wake with a little luck.'),
]
PRIZES = [
    dict(id='storm', name='Storm Flies x3', tickets=8),
    dict(id='moon', name='Moon Lures x2', tickets=12),
    dict(id='coins', name='Pouch of 150 coins', tickets=25),
    dict(id='party', name='Party Hat', tickets=20, hat=True),
    dict(id='tophat', name='Top Hat', tickets=40, hat=True),
]
MUSEUM_REWARDS = [(5, 'coins', 150), (10, 'coins', 300), (20, 'golden', 4), (30, 'coins', 800), (len(FISH), 'coins', 2000)]
HEART_GIFTS = [(3, 'coins', 100), (6, 'golden', 3), (10, 'coins', 500)]
TOSS_COST = 15


def fmt_hour(m):
    h = int(m) // 60 % 24
    return '%d %s' % (h % 12 or 12, 'AM' if h < 12 else 'PM')


# ---------------------------------------------------------------- drawing helpers
_font = None


def sign_text(s, text, center, color):
    """Tiny pixel letters for shop signs, drawn straight onto the 640x360 world."""
    global _font
    if _font is None:
        _font = pixfont.PixelFont(1, False)
    img = _font.render(text, False, color)
    s.blit(img, img.get_rect(center=center))


def walker(s, x, fy, face, step, shirt, hair, hat, season, kid=False, glasses=False, umbrella=None):
    """A person walking (step is a running phase, 0 when standing). face is 1 for right, -1 for left."""
    tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
    cx, base = 13, 38
    bob = 1 if step and math.sin(step * 2) > 0 else 0
    actors.draw_person(tmp, cx, base, shirt, hair, hat, season, bob)
    if glasses:
        tmp.fill((60, 50, 50), (cx + 1, base - 20 - bob, 3, 1))
        tmp.set_at((cx + 2, base - 19 - bob), (60, 50, 50))
    if step:
        pants, boot = (72, 92, 140), (84, 58, 42)
        tmp.fill((0, 0, 0, 0), (cx - 6, base - 6, 12, 6))
        a = math.sin(step)
        o = int(round(a * 2))
        tmp.fill(pants, (cx - 3 + o, base - 6, 2, 5))
        tmp.fill(boot, (cx - 4 + o, base - 2, 3, 2))
        tmp.fill(darken(pants, 0.2), (cx + 1 - o, base - 6, 2, 5))
        tmp.fill(boot, (cx + 1 - o, base - 2, 3, 2))
    if face < 0:
        tmp = pygame.transform.flip(tmp, True, False)
    if kid:
        tmp = pygame.transform.scale(tmp, (21, 32))
        s.blit(tmp, (x - 10, fy - 31))
        top = fy - 26
    else:
        s.blit(tmp, (x - 13, fy - 38))
        top = fy - 31
    if umbrella:
        pygame.draw.line(s, (80, 64, 56), (x + 2 * face, top + 4), (x + 2 * face, top - 6))
        pygame.draw.ellipse(s, umbrella, (x - 9 + 2 * face, top - 11, 19, 9))
        s.fill((0, 0, 0, 0), (x - 9 + 2 * face, top - 6, 19, 4))
        pygame.draw.line(s, darken(umbrella, 0.3), (x - 9 + 2 * face, top - 7), (x + 9 + 2 * face, top - 7))


def sitter(s, x, seat, shirt, hair, hat, season, breathe=0):
    """You on the lookout bench, seen from behind: looking out over the lake."""
    pants = (72, 92, 140)
    by = seat + 3 - breathe
    s.fill(pants, (x - 4, seat - 3, 8, 3))                         # sitting on the plank
    s.fill(shirt, (x - 4, by - 15, 8, 10))                          # your back
    s.fill(darken(shirt, 0.18), (x - 4, by - 15, 1, 10))
    s.fill(darken(pants, 0.15), (x - 3, by - 15, 1, 7))            # braces
    s.fill(darken(pants, 0.15), (x + 2, by - 15, 1, 7))
    if season == 3:
        s.fill((200, 70, 70), (x - 4, by - 16, 9, 2))
    s.fill((240, 202, 172), (x - 4, by - 19, 1, 2))                # ears
    s.fill((240, 202, 172), (x + 3, by - 19, 1, 2))
    s.fill(hair, (x - 3, by - 21, 7, 6))                            # the back of your head
    s.fill(darken(hair, 0.15), (x - 3, by - 16, 7, 1))
    actors.draw_hat(s, hat, x, by, season, hair)
    s.fill((236, 186, 156), (x + 4, by - 9, 3, 2))                  # a hand resting by Biscuit


def draw_front(s, sc, season, t):
    """Barrels, crates, bikes and milk churns along the front of the street (drawn over everyone's feet)."""
    y = GROUND + 7
    for x0, kind in FRONT:
        x = x0 - sc
        if not -30 < x < W + 30:
            continue
        ground_shadow(s, x, y - 1, 16, 60)
        if kind == 'barrel':
            s.fill((128, 84, 54), (x - 6, y - 11, 12, 11))
            s.fill((96, 62, 40), (x - 6, y - 8, 12, 1))
            s.fill((96, 62, 40), (x - 6, y - 3, 12, 1))
            s.fill((150, 102, 66), (x - 5, y - 11, 2, 11))
            cols = [(250, 160, 190), (250, 120, 110), (230, 140, 60), (230, 236, 244)][season]
            for j in range(6):
                s.fill((80, 140, 70) if season != 3 else (60, 100, 70), (x - 5 + j * 2, y - 14, 1, 3))
                s.fill(cols, (x - 6 + j * 2, y - 16 + (j % 2), 2, 2))
        elif kind == 'crates':
            for dx, dy, fruit in ((-9, 0, (210, 70, 60)), (1, 0, (240, 180, 60)), (-4, -8, (120, 170, 70))):
                s.fill((176, 136, 90), (x + dx, y - 8 + dy, 9, 8))
                s.fill((136, 100, 64), (x + dx, y - 5 + dy, 9, 1))
                s.fill((136, 100, 64), (x + dx, y - 8 + dy, 1, 8))
                for j in range(4):
                    s.fill(fruit, (x + dx + 1 + j * 2, y - 10 + dy, 2, 2))
        elif kind == 'bike':
            fr = (70, 120, 150)
            for wx in (x - 7, x + 7):
                pygame.draw.circle(s, (50, 46, 50), (wx, y - 5), 5, 1)
                s.set_at((wx, y - 5), (120, 120, 120))
            pygame.draw.line(s, fr, (x - 7, y - 5), (x - 1, y - 11))
            pygame.draw.line(s, fr, (x - 1, y - 11), (x + 5, y - 11))
            pygame.draw.line(s, fr, (x + 5, y - 11), (x + 7, y - 5))
            pygame.draw.line(s, fr, (x - 1, y - 11), (x + 1, y - 5))
            pygame.draw.line(s, fr, (x + 1, y - 5), (x - 7, y - 5))
            s.fill((60, 50, 44), (x - 3, y - 13, 4, 1))              # saddle
            s.fill((150, 110, 70), (x + 4, y - 16, 6, 4))             # a basket of bread on the handlebars
            s.fill((220, 170, 100), (x + 5, y - 17, 4, 2))
        elif kind == 'churns':
            for dx in (-5, 3):
                s.fill((186, 192, 198), (x + dx - 3, y - 12, 7, 12))
                s.fill((150, 156, 164), (x + dx - 2, y - 15, 5, 3))
                s.fill((220, 226, 230), (x + dx - 2, y - 11, 1, 10))
                s.fill((130, 136, 144), (x + dx - 3, y - 6, 7, 1))


def _ridge(w, base, amps, seed):
    rng = random.Random(seed)
    phases = [rng.uniform(0, 6.28) for _ in amps]
    pts = []
    for x in range(0, w + 8, 6):
        y = base
        for i, (a, f) in enumerate(amps):
            y -= a * (0.5 + 0.5 * math.sin(x * f + phases[i]))
        pts.append((x, y))
    return pts


def _bricks(s, rect, col, mortar, h=4, w=9):
    s.fill(col, rect)
    for j, y in enumerate(range(rect.y, rect.bottom, h)):
        pygame.draw.line(s, mortar, (rect.x, y), (rect.right - 1, y))
        off = (j % 2) * (w // 2)
        for x in range(rect.x + off, rect.right, w):
            pygame.draw.line(s, mortar, (x, y), (x, min(rect.bottom - 1, y + h - 1)))


def _planks(s, rect, col, line, step=4):
    s.fill(col, rect)
    for y in range(rect.y + step, rect.bottom, step):
        pygame.draw.line(s, line, (rect.x, y), (rect.right - 1, y))


def _gable(s, x0, x1, y, h, col, edge, snow=False):
    pts = [(x0 - 6, y), ((x0 + x1) // 2, y - h), (x1 + 6, y)]
    pygame.draw.polygon(s, col, pts)
    for i in range(1, h // 4):
        yy = y - i * 4
        k = (yy - (y - h)) / h
        half = (x1 - x0 + 12) / 2 * k
        cx = (x0 + x1) / 2
        pygame.draw.line(s, darken(col, 0.12), (cx - half + 2, yy), (cx + half - 2, yy))
    pygame.draw.lines(s, edge, False, pts, 2)
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(x0 - 6, y - 1), ((x0 + x1) // 2, y - h - 1), (x1 + 6, y - 1)],
                          3)


def _window(s, x, y, w, h, frame_c, wins, shutters=None):
    s.fill(frame_c, (x - 1, y - 1, w + 2, h + 2))
    s.fill((70, 92, 120), (x, y, w, h))
    s.fill((112, 140, 170), (x, y, w, max(1, h // 3)))
    s.fill(frame_c, (x + w // 2, y, 1, h))
    s.fill(frame_c, (x, y + h // 2, w, 1))
    s.fill(darken(frame_c, 0.2), (x - 2, y + h + 1, w + 4, 2))
    if shutters:
        s.fill(shutters, (x - 4, y - 1, 3, h + 2))
        s.fill(shutters, (x + w + 1, y - 1, 3, h + 2))
    wins.append(pygame.Rect(x, y, w, h))


def _door(s, x, w, h, col, frame_c):
    y = GROUND - 4 - h
    s.fill(frame_c, (x - w // 2 - 2, y - 2, w + 4, h + 2))
    s.fill(col, (x - w // 2, y, w, h))
    s.fill(darken(col, 0.18), (x - w // 2 + 2, y + 2, w // 2 - 3, h - 4))
    s.fill(darken(col, 0.18), (x + 1, y + 2, w // 2 - 3, h - 4))
    s.set_at((x + w // 2 - 3, y + h // 2), (236, 206, 120))
    s.fill((150, 140, 132), (x - w // 2 - 3, GROUND - 4, w + 6, 2))


def _sign(s, cx, y, text, bg, fg, w=None):
    w = w or len(text) * 5 + 10
    s.fill(darken(bg, 0.35), (cx - w // 2 - 1, y - 1, w + 2, 11))
    s.fill(bg, (cx - w // 2, y, w, 9))
    sign_text(s, text, (cx, y + 5), fg)


# ---------------------------------------------------------------- 1.9.0: details that make each shop its own
_SHADOWS = {}
SHADE = (24, 20, 32)


def ground_shadow(s, x, y, w=14, a=72):
    """A soft oval where someone (or something) meets the ground."""
    img = _SHADOWS.get((w, a))
    if img is None:
        img = pygame.Surface((w + 4, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(img, (*SHADE, a // 2), img.get_rect())
        pygame.draw.ellipse(img, (*SHADE, a), (2, 1, w, 3))
        _SHADOWS[(w, a)] = img
    s.blit(img, (int(x) - w // 2 - 2, int(y) - 3))


def _shade(s, rect, a0, a1):
    """A vertical gradient of shadow (alpha a0 at the top to a1 at the bottom), blended over what's there."""
    rect = pygame.Rect(rect)
    img = pygame.Surface(rect.size, pygame.SRCALPHA)
    for i in range(rect.h):
        k = i / max(1, rect.h - 1)
        img.fill((*SHADE, int(a0 + (a1 - a0) * k)), (0, i, rect.w, 1))
    s.blit(img, rect)


def _grounded(s, x0, x1, eave=None):
    """Contact shadows for a building: on the pavement in front, where the wall meets it, and under the eaves."""
    _shade(s, (x0 - 3, GROUND - 4, x1 - x0 + 6, 6), 78, 0)
    _shade(s, (x0, GROUND - 9, x1 - x0, 5), 0, 46)
    if eave is not None:
        _shade(s, (x0, eave, x1 - x0, 6), 70, 0)


def _span(xl, xr, peak_x, base_y, h, y):
    """Left and right edges of a triangular roof at height y."""
    k = (y - (base_y - h)) / h
    return peak_x + (xl - peak_x) * k, peak_x + (xr - peak_x) * k


def _tin_roof(s, x0, x1, y, h, snow, rng):
    """Corrugated tin, a bit rusty: Old Tom's roof."""
    col = (128, 144, 152)
    xl, xr, px = x0 - 6, x1 + 6, (x0 + x1) // 2
    pygame.draw.polygon(s, col, [(xl, y), (px, y - h), (xr, y)])
    for yy in range(y - h + 2, y):
        a, b = _span(xl, xr, px, y, h, yy)
        for x in range(int(a) + 1, int(b), 3):
            s.set_at((x, yy), darken(col, 0.2))
            if x + 1 < b:
                s.set_at((x + 1, yy), lighten(col, 0.12))
    for _ in range(14):                                       # rust streaks
        yy = rng.randrange(y - h + 8, y - 2)
        a, b = _span(xl, xr, px, y, h, yy)
        x = rng.randrange(int(a) + 2, int(b) - 2)
        s.fill(rng.choice([(168, 104, 70), (150, 92, 64), (180, 120, 80)]), (x, yy, 1, rng.randrange(2, 5)))
    pygame.draw.lines(s, (86, 98, 108), False, [(xl, y), (px, y - h), (xr, y)], 2)
    s.fill((96, 108, 116), (xl, y, xr - xl, 2))
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(xl, y - 1), (px, y - h - 1), (xr, y - 1)], 3)


def _shingles(s, xl, xr, px, y, h, col, step=4, scallop=True):
    """Rows of shingles (scalloped, or straight with staggered joints) over a triangular roof."""
    line = darken(col, 0.22)
    for j, yy in enumerate(range(y - h + step, y, step)):
        a, b = _span(xl, xr, px, y, h, yy)
        pygame.draw.line(s, line, (int(a) + 2, yy), (int(b) - 2, yy))
        off = (j % 2) * 3
        for x in range(int(a) + 3 + off, int(b) - 3, 6):
            if scallop:
                s.set_at((x, yy - 1), line)
                s.set_at((x + 5, yy - 1), line)
                s.fill(lighten(col, 0.08), (x + 1, yy - step + 1, 4, 1))
            else:
                s.fill(line, (x, yy - step + 1, 1, step - 1))


def _thatch(s, x0, x1, y, h, snow, rng):
    """A thick, round-shouldered straw roof with a combed fringe."""
    col = (204, 170, 98)
    xl, xr, px = x0 - 9, x1 + 9, (x0 + x1) // 2
    pygame.draw.polygon(s, col, [(xl, y), (px - 6, y - h), (px + 6, y - h), (xr, y)])
    pygame.draw.ellipse(s, col, (px - 12, y - h - 3, 24, 8))
    for _ in range(120):
        yy = rng.randrange(y - h + 1, y)
        a, b = _span(xl, xr, px, y, h, yy)
        x = rng.randrange(int(a) + 1, max(int(a) + 2, int(b) - 1))
        s.fill(rng.choice([darken(col, 0.18), lighten(col, 0.1), darken(col, 0.1)]), (x, yy, 1, rng.randrange(2, 5)))
    for x in range(xl + 1, xr - 1, 2):                        # the combed edge
        s.fill(darken(col, 0.3), (x, y, 1, rng.randrange(1, 4)))
    s.fill(darken(col, 0.28), (px - 10, y - h - 1, 20, 2))     # ridge
    if snow:
        pygame.draw.ellipse(s, (246, 248, 255), (px - 14, y - h - 4, 28, 7))
        pygame.draw.lines(s, (246, 248, 255), False, [(xl + 2, y - 2), (px - 8, y - h), (px + 8, y - h), (xr - 2, y - 2)],
                          2)


def _saltbox(s, x0, x1, y, col, edge, snow):
    """An off-centre roof: short and steep at the front, long at the back."""
    xl, xr, px, h = x0 - 6, x1 + 6, x0 + (x1 - x0) // 3, 26
    pygame.draw.polygon(s, col, [(xl, y), (px, y - h), (xr, y)])
    _shingles(s, xl, xr, px, y, h, col, 4, False)
    pygame.draw.lines(s, edge, False, [(xl, y), (px, y - h), (xr, y)], 2)
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(xl, y - 1), (px, y - h - 1), (xr, y - 1)], 3)


def _pot(s, x, season, urn=False, rng=None):
    """A doorstep planter that changes with the season."""
    rng = rng or random.Random(x)
    base = GROUND - 4
    if urn:                                                   # stone urns for the aquarium steps
        s.fill((196, 190, 180), (x - 5, base - 7, 10, 7))
        s.fill((214, 208, 198), (x - 6, base - 8, 12, 2))
        s.fill((176, 170, 160), (x - 3, base - 2, 6, 2))
    else:
        s.fill((178, 100, 70), (x - 4, base - 6, 8, 6))
        s.fill((150, 82, 58), (x - 5, base - 7, 10, 2))
        s.fill((140, 76, 54), (x - 4, base - 1, 8, 1))
    top = base - 8
    if season == 0:                                           # tulips
        for i, c in enumerate(((236, 96, 110), (250, 214, 90), (240, 150, 190))):
            sx = x - 3 + i * 3
            s.fill((96, 156, 76), (sx, top - 5 - i % 2, 1, 5 + i % 2))
            s.fill(c, (sx - 1, top - 8 - i % 2, 3, 3))
        s.fill((110, 170, 84), (x - 4, top - 2, 2, 2))
        s.fill((110, 170, 84), (x + 3, top - 3, 2, 3))
    elif season == 1:                                         # a geranium bush in full bloom
        pygame.draw.ellipse(s, (70, 132, 70), (x - 6, top - 7, 12, 9))
        pygame.draw.ellipse(s, (96, 156, 80), (x - 4, top - 7, 7, 5))
        for _ in range(6):
            s.fill(rng.choice([(226, 62, 72), (250, 110, 120)]), (x - 5 + rng.randrange(10), top - 7 + rng.randrange(6),
                                                                  2, 2))
    elif season == 2:                                         # mums, and a pumpkin
        pygame.draw.ellipse(s, (90, 110, 60), (x - 6, top - 7, 12, 9))
        for _ in range(8):
            s.fill(rng.choice([(232, 140, 50), (214, 100, 44), (240, 190, 70)]),
                   (x - 5 + rng.randrange(10), top - 7 + rng.randrange(6), 2, 2))
        pumpkin(s, x + (8 if x % 2 else -8), base, rng.randrange(5, 8))
    else:                                                     # a little evergreen with holly berries and snow
        pygame.draw.polygon(s, (46, 100, 74), [(x - 5, top + 1), (x, top - 12), (x + 5, top + 1)])
        pygame.draw.polygon(s, (60, 120, 86), [(x - 3, top - 4), (x, top - 12), (x + 3, top - 4)])
        s.fill((246, 248, 255), (x - 2, top - 11, 4, 2))
        s.fill((246, 248, 255), (x - 4, top - 3, 3, 1))
        for dx, dy in ((-2, -2), (2, -6), (1, 0)):
            s.set_at((x + dx, top + dy), (210, 40, 50))


def pumpkin(s, x, base, r):
    pygame.draw.ellipse(s, (226, 120, 40), (x - r, base - r, r * 2, r + 1))
    pygame.draw.line(s, (190, 92, 30), (x, base - r + 1), (x, base - 1))
    pygame.draw.line(s, (190, 92, 30), (x - r // 2, base - r + 2), (x - r // 2, base - 1))
    s.fill((96, 110, 50), (x, base - r - 2, 2, 3))


def _window_box(s, x, w, y, season, rng):
    s.fill((120, 84, 58), (x - 1, y, w + 2, 4))
    s.fill((96, 66, 46), (x - 1, y + 3, w + 2, 1))
    for i in range(1, w, 3):
        if season == 3:
            s.fill((60, 110, 80), (x + i - 1, y - 2, 3, 2))
            s.fill((246, 248, 255), (x + i - 1, y - 2, 2, 1))
            continue
        s.fill((84, 146, 72) if season < 2 else (110, 120, 60), (x + i, y - 2, 2, 2))
        pal = [[(250, 170, 200), (250, 230, 120), (200, 160, 240)], [(230, 60, 70), (250, 240, 240), (250, 150, 60)],
               [(230, 130, 50), (200, 80, 50), (240, 190, 70)]][season]
        s.fill(rng.choice(pal), (x + i, y - 4 + rng.randrange(2), 2, 2))


def _festoon(s, x0, x1, y, season, lights, sag=5):
    """A swag hung under the eaves: bunting in spring and summer, a leaf garland in autumn, lights in winter."""
    n = max(2, (x1 - x0) // 4)
    pts = [(x0 + (x1 - x0) * i / n, y + sag * math.sin(math.pi * i / n)) for i in range(n + 1)]
    rope = [(150, 140, 130), (150, 140, 130), (110, 80, 52), (40, 80, 56)][season]
    pygame.draw.lines(s, rope, False, [(int(px), int(py)) for px, py in pts], 1 if season < 3 else 2)
    if season in (0, 1):
        pal = [[(250, 176, 200), (176, 226, 200), (250, 236, 150), (200, 180, 240)],
               [(226, 70, 74), (250, 210, 70), (80, 140, 210), (250, 248, 240)]][season]
        for i, (px, py) in enumerate(pts[1:-1:2]):
            px, py = int(px), int(py)
            pygame.draw.polygon(s, pal[i % 4], [(px - 3, py), (px + 3, py), (px, py + 5)])
    elif season == 2:
        for i, (px, py) in enumerate(pts[1:-1]):
            px, py = int(px), int(py)
            c = [(220, 110, 44), (190, 64, 44), (236, 176, 60), (160, 100, 50)][i % 4]
            s.fill(c, (px - 1, py + (i % 2), 3, 2))
            if i % 3 == 0:
                s.set_at((px, py + 3), (140, 96, 60))           # a dangling acorn
    else:
        for i, (px, py) in enumerate(pts[1:-1]):
            px, py = int(px), int(py)
            s.fill((50, 96, 66), (px - 1, py - 1, 3, 3))
            if i % 2 == 0:
                c = [(250, 90, 80), (250, 210, 90), (110, 190, 250), (140, 230, 140)][(i // 2) % 4]
                s.fill(c, (px, py + 2, 2, 2))
                lights.append((px, py + 2, c))


def _wreath(s, x, y):
    pygame.draw.circle(s, (40, 96, 64), (x, y), 5, 3)
    pygame.draw.circle(s, (60, 120, 80), (x, y), 5, 1)
    for a in range(0, 360, 72):
        s.set_at((x + int(math.cos(math.radians(a)) * 4), y + int(math.sin(math.radians(a)) * 4)), (220, 50, 60))
    s.fill((210, 40, 50), (x - 2, y + 4, 5, 2))


def _decorate_door(s, x, w, h, season, rng, urn=False):
    """Plants either side of a door, and a wreath on it in winter."""
    _pot(s, x - w // 2 - 7, season, urn, rng)
    _pot(s, x + w // 2 + 7, season, urn, rng)
    if season == 3:
        _wreath(s, x, GROUND - 4 - h + 8)


_SIGNS = {}
# hanging signs: (wall x, side it sticks out to, icon)
HANGING = ((132, -1, 'fish'), (474, 1, 'cupcake'), (862, -1, 'bowl'), (1594, 1, 'book'), (1108, -1, 'bell'))


def _hanging_sign(icon):
    img = _SIGNS.get(icon)
    if img is not None:
        return img
    img = pygame.Surface((14, 12), pygame.SRCALPHA)
    bg = {'fish': (230, 216, 186), 'cupcake': (250, 232, 226), 'bowl': (214, 230, 236), 'book': (226, 232, 206),
          'bell': (236, 226, 206)}[icon]
    img.fill((96, 66, 46))
    img.fill(bg, (1, 1, 12, 10))
    if icon == 'fish':
        pygame.draw.polygon(img, (70, 120, 150), [(3, 6), (7, 3), (10, 6), (7, 8)])
        pygame.draw.polygon(img, (70, 120, 150), [(10, 6), (12, 4), (12, 8)])
        img.set_at((5, 5), (250, 250, 250))
    elif icon == 'cupcake':
        img.fill((214, 150, 90), (4, 6, 6, 4))
        for x in range(4, 10, 2):
            img.set_at((x, 7), (176, 110, 64))
        pygame.draw.ellipse(img, (246, 160, 190), (3, 2, 8, 6))
        img.set_at((7, 2), (220, 40, 60))
    elif icon == 'bowl':
        pygame.draw.circle(img, (150, 200, 226), (7, 6), 4)
        img.fill((214, 230, 236), (2, 2, 10, 2))
        img.fill((240, 140, 50), (6, 6, 3, 2))
        img.set_at((9, 6), (240, 140, 50))
    elif icon == 'book':
        img.fill((176, 76, 70), (3, 3, 4, 6))
        img.fill((70, 110, 150), (7, 3, 4, 6))
        img.fill((250, 244, 230), (4, 4, 2, 4))
        img.fill((250, 244, 230), (8, 4, 2, 4))
    elif icon == 'bell':
        pygame.draw.polygon(img, (214, 170, 70), [(4, 9), (5, 4), (7, 2), (9, 4), (10, 9)])
        img.set_at((7, 10), (150, 110, 50))
    _SIGNS[icon] = img
    return img


def draw_hanging_signs(s, sc, t, wind):
    """Shop signs on iron brackets, swinging a little in the breeze."""
    iron = (56, 52, 58)
    for wx, side, icon in HANGING:
        px = wx + side * 10 - sc
        if not -20 < px < W + 20:
            continue
        ay = GROUND - 66
        s.fill(iron, (min(wx - sc, wx - sc + side * 14), ay, 15, 1))
        pygame.draw.line(s, iron, (wx - sc, ay + 7), (wx - sc + side * 8, ay))
        s.fill(iron, (wx - sc + side * 14, ay - 1, 1, 2))
        a = math.sin(t * 1.6 + wx) * (0.04 + 0.16 * wind) + math.sin(t * 3.7 + wx * 0.3) * 0.02 * wind
        ca, sa = math.cos(a), math.sin(a)
        for dx in (-5, 5):                                    # the chains
            cx, cy = dx * ca + 3 * sa, -dx * sa + 3 * ca
            pygame.draw.line(s, iron, (px + dx, ay), (int(px + cx), int(ay + cy)))
        img = pygame.transform.rotate(_hanging_sign(icon), math.degrees(a))
        s.blit(img, img.get_rect(center=(int(px + 9 * sa), int(ay + 9 * ca))))


def draw_weathervane(s, x, y, t, wind):
    """A brass fish on Old Tom's roof that swings round to face the wind."""
    s.fill((70, 64, 60), (x, y - 14, 1, 14))
    s.fill((150, 120, 60), (x - 4, y - 6, 9, 1))
    turn = math.cos(t * (0.15 + 0.3 * wind) + math.sin(t * 1.1) * 0.6 * wind)
    half = max(1, int(6 * abs(turn)))
    d = 1 if turn >= 0 else -1
    fy = y - 15
    col = (214, 170, 70) if abs(turn) > 0.35 else (176, 136, 56)
    pygame.draw.polygon(s, col, [(x - half * d, fy), (x, fy - 2), (x + half * d, fy), (x, fy + 2)])
    pygame.draw.polygon(s, col, [(x - half * d, fy), (x - (half + 3) * d, fy - 2), (x - (half + 3) * d, fy + 2)])


def _bakery_display(s, season):
    """Mabel changes her window with the seasons."""
    s.fill((236, 224, 206), (352, GROUND - 36, 34, 3))      # the shelf
    s.fill((214, 196, 176), (352, GROUND - 34, 34, 1))
    base = GROUND - 36
    if season == 0:                                           # a pink layer cake and buns
        s.fill((200, 196, 200), (364, base - 2, 10, 2))
        s.fill((250, 214, 226), (365, base - 9, 8, 7))
        s.fill((236, 150, 180), (365, base - 6, 8, 1))
        s.fill((250, 240, 244), (365, base - 10, 8, 2))
        s.set_at((369, base - 11), (220, 40, 60))
        for bx in (355, 378):
            pygame.draw.ellipse(s, (214, 154, 84), (bx, base - 4, 6, 4))
    elif season == 1:                                         # berry tarts and a lemon loaf
        for i, bx in enumerate((354, 362, 377)):
            s.fill((220, 170, 96), (bx, base - 3, 7, 3))
            c = [(200, 40, 70), (70, 80, 180), (200, 40, 70)][i]
            for j in range(3):
                s.fill(c, (bx + 1 + j * 2, base - 4, 1, 1))
        s.fill((250, 226, 120), (368, base - 6, 8, 6))
        s.fill((250, 250, 230), (368, base - 7, 8, 2))
    elif season == 2:                                         # pumpkin pie and apple turnovers
        pygame.draw.ellipse(s, (196, 140, 80), (362, base - 4, 14, 5))
        pygame.draw.ellipse(s, (224, 132, 52), (364, base - 4, 10, 3))
        for bx in (354, 379):
            pygame.draw.polygon(s, (226, 176, 104), [(bx, base), (bx + 3, base - 4), (bx + 6, base)])
        pumpkin(s, 383, base, 3)
    else:                                                     # a gingerbread house and candy canes
        s.fill((170, 104, 60), (362, base - 7, 12, 7))
        pygame.draw.polygon(s, (250, 250, 250), [(360, base - 7), (368, base - 13), (376, base - 7)])
        pygame.draw.polygon(s, (150, 90, 50), [(362, base - 8), (368, base - 12), (374, base - 8)])
        s.fill((250, 220, 120), (366, base - 4, 3, 4))
        for bx in (355, 380):
            s.fill((250, 250, 250), (bx, base - 8, 1, 8))
            s.fill((250, 250, 250), (bx + 1, base - 9, 2, 1))
            for yy in range(base - 8, base, 2):
                s.set_at((bx, yy), (220, 40, 50))
    # the right-hand window: a tiered stand of buns
    s.fill((236, 224, 206), (432, GROUND - 36, 26, 3))
    s.fill((210, 206, 210), (444, GROUND - 48, 2, 12))
    for ty, tw in ((GROUND - 39, 18), (GROUND - 46, 12)):
        s.fill((226, 222, 226), (445 - tw // 2, ty, tw, 1))
        for i in range(tw // 6):
            pygame.draw.ellipse(s, [(214, 154, 84), (236, 190, 120), (196, 120, 70), (240, 206, 226)][(season + i) % 4],
                                (445 - tw // 2 + i * 6, ty - 3, 5, 3))


def _a_board(s, x):
    """A chalkboard on the pavement outside the bakery."""
    pygame.draw.line(s, (120, 86, 60), (x - 6, GROUND - 4), (x - 2, GROUND - 22))
    pygame.draw.line(s, (120, 86, 60), (x + 6, GROUND - 4), (x + 2, GROUND - 22))
    s.fill((120, 86, 60), (x - 6, GROUND - 22, 13, 15))
    s.fill((46, 58, 54), (x - 5, GROUND - 21, 11, 13))
    s.fill((230, 230, 220), (x - 3, GROUND - 19, 7, 1))
    s.fill((230, 230, 220), (x - 3, GROUND - 17, 5, 1))
    pygame.draw.ellipse(s, (240, 190, 210), (x - 2, GROUND - 15, 5, 3))     # a chalk cupcake
    s.fill((230, 230, 220), (x - 1, GROUND - 12, 3, 2))


# ---------------------------------------------------------------- depth: buildings with sides and roofs
# Every building is a front face (drawn once into the street) pushed back into the screen. The back edges head
# towards a vanishing point above the middle of the screen, so you see a little of each roof from above and the
# side walls turn as you walk past.
VP_Y = -100
DEPTH_K = 1 / 600.0
SIDE_BIAS = 0.32         # a steady three-quarter view: the shaded right-hand walls always show a little
SIDE_SWING = 1.5         # and the sides turn as you walk past


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _volumes():
    G = GROUND
    v = []

    def add(poly, depth, wall, roof, tex='courses'):
        v.append(dict(poly=poly, depth=depth, wall=wall, roof=roof, tex=tex))
    # Old Tom's: plank walls, tin roof
    add(_rect(132, G - 74, 318, G - 4), 30, (92, 128, 140), (128, 144, 152), 'planks')
    add([(126, G - 74), (225, G - 108), (324, G - 74)], 30, (92, 128, 140), (128, 144, 152), 'ribs')
    # Mabel's: cream walls, rosy mansard, chimney
    add(_rect(338, G - 82, 474, G - 4), 24, (244, 226, 200), (186, 98, 100))
    add([(333, G - 82), (345, G - 106), (467, G - 106), (479, G - 82)], 24, (244, 226, 200), (186, 98, 100), 'tiles')
    add(_rect(436, G - 120, 448, G - 102), 8, (150, 130, 124), (126, 108, 104), 'bricks')
    # the aquarium: stone, a lead roof behind the pediment
    add(_rect(862, G - 90, 1084, G - 4), 34, (196, 190, 178), (150, 152, 160), 'bricks')
    add([(854, G - 90), (973, G - 118), (1092, G - 90)], 34, (196, 190, 178), (150, 152, 160), 'tiles')
    # the town hall and its clock tower
    add(_rect(1108, G - 80, 1276, G - 4), 28, (170, 92, 76), (90, 92, 110), 'bricks')
    add([(1102, G - 80), (1192, G - 102), (1282, G - 80)], 28, (170, 92, 76), (90, 92, 110), 'tiles')
    add(_rect(1174, G - 140, 1210, G - 80), 22, (170, 92, 76), (90, 92, 110), 'bricks')
    add([(1170, G - 140), (1192, G - 166), (1214, G - 140)], 22, (170, 92, 76), (90, 92, 110), 'tiles')
    # Pip's counter
    add(_rect(1306, G - 26, 1398, G - 4), 12, (214, 170, 110), (180, 140, 90), 'planks')
    # the library, slate roof and chimney
    add(_rect(1430, G - 80, 1594, G - 4), 26, (120, 150, 112), (88, 98, 122), 'planks')
    add([(1424, G - 80), (1512, G - 110), (1600, G - 80)], 26, (120, 150, 112), (88, 98, 122), 'tiles')
    add(_rect(1556, G - 120, 1566, G - 90), 8, (140, 150, 150), (120, 128, 130), 'bricks')
    # the cottages: thatch and a saltbox
    add(_rect(1622, G - 54, 1680, G - 4), 20, (230, 210, 170), (204, 170, 98))
    add([(1613, G - 54), (1645, G - 78), (1657, G - 78), (1689, G - 54)], 22, (230, 210, 170), (204, 170, 98),
        'straw')
    add(_rect(1700, G - 54, 1758, G - 4), 20, (200, 214, 230), (90, 110, 140))
    add([(1694, G - 54), (1719, G - 80), (1764, G - 54)], 20, (200, 214, 230), (90, 110, 140), 'tiles')
    return finish_volumes(v)


def finish_volumes(v):
    """Work out each volume's winding and extent (so other streets, like Saltmarsh's quay, can use them too)."""
    for p in v:
        pts = p['poly']
        p['area'] = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                        for i in range(len(pts)))
        p['x0'], p['x1'] = min(q[0] for q in pts), max(q[0] for q in pts)
    return v


VOLUMES = _volumes()
PAVE = [(198, 190, 176), (204, 196, 180), (190, 186, 178), (210, 214, 222)]
SNOWY = (236, 240, 250)


def draw_volumes(s, sc, season, vols=None):
    """The sides and roofs of every building on screen, behind their fronts."""
    vx = W / 2
    for p in (VOLUMES if vols is None else vols):
        if p['x1'] - sc < -60 or p['x0'] - sc > W + 60:
            continue
        k = p['depth'] * DEPTH_K
        pts = [(x - sc, y) for x, y in p['poly']]
        bias = p['depth'] * SIDE_BIAS
        back = [(x + bias + (vx - x) * k * SIDE_SWING, y + (VP_Y - y) * k) for x, y in pts]
        n = len(pts)
        cx = sum(q[0] for q in pts) / n
        cy = sum(q[1] for q in pts) / n
        shx, shy = bias + (vx - cx) * k * SIDE_SWING, (VP_Y - cy) * k
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            ba, bb = back[i], back[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            nx, ny = (dy, -dx) if p['area'] > 0 else (-dy, dx)
            if nx * shx + ny * shy <= 0.01:
                continue
            ln = math.hypot(nx, ny) or 1.0
            nx, ny = nx / ln, ny / ln
            quad = [a, b, bb, ba]
            if abs(ny) < 0.35:                                   # a side wall, in the shade away from the sun
                col = darken(p['wall'], 0.34 if nx > 0 else 0.18)
                pygame.draw.polygon(s, col, quad)
                step = 4 if p['tex'] == 'planks' else 5
                line = darken(col, 0.12)
                y0, y1 = min(a[1], b[1]), max(a[1], b[1])
                for yy in range(int(y0) + step, int(y1), step):
                    t = (yy - a[1]) / (b[1] - a[1]) if b[1] != a[1] else 0
                    pygame.draw.line(s, line, (a[0], yy), (ba[0] + (bb[0] - ba[0]) * t, ba[1] + (bb[1] - ba[1]) * t))
                # a back corner, lit a little, so the wall reads as a solid block
                pygame.draw.line(s, darken(col, 0.18), ba, bb)
            elif ny < 0:                                         # a roof (or top) plane, catching the sky
                col = p['roof'] if season != 3 else lerp_c(p['roof'], SNOWY, 0.75)
                col = lighten(col, 0.1) if nx < -0.2 else darken(col, 0.08) if nx > 0.2 else col
                pygame.draw.polygon(s, col, quad)
                line = darken(col, 0.14)
                rows = 4 if p['tex'] in ('tiles', 'straw') else 2
                for j in range(1, rows):
                    u = j / rows
                    pygame.draw.line(s, line, (a[0] + (ba[0] - a[0]) * u, a[1] + (ba[1] - a[1]) * u),
                                     (b[0] + (bb[0] - b[0]) * u, b[1] + (bb[1] - b[1]) * u))
                if p['tex'] == 'ribs':                           # tin ribs running back
                    for j in range(1, 12):
                        u = j / 12
                        pygame.draw.line(s, line, (a[0] + dx * u, a[1] + dy * u),
                                         (ba[0] + (bb[0] - ba[0]) * u, ba[1] + (bb[1] - ba[1]) * u))
                pygame.draw.line(s, darken(col, 0.3), ba, bb)            # the far ridge
            else:                                                # the underside of an overhang
                pygame.draw.polygon(s, darken(p['wall'], 0.5), quad)


FORE_K = 1.35            # the near verge slides past faster than the street
FORE_H = 46


def build_fore(season):
    """The near side of the road: a grass verge with hedges, a picket fence and flower barrels."""
    w = int(TOWN_W * FORE_K) + W
    s = pygame.Surface((w, FORE_H), pygame.SRCALPHA)
    rng = random.Random(23)
    grass = [(76, 128, 70), (70, 120, 58), (140, 104, 58), (214, 220, 232)][season]
    leaf = [(64, 116, 66), (56, 110, 54), (150, 90, 46), (52, 92, 70)][season]
    snow = season == 3
    base = FORE_H - 6
    s.fill(darken(grass, 0.15), (0, base, w, 6))
    for x in range(0, w, 2):
        s.fill(darken(grass, rng.uniform(0.0, 0.3)), (x, base - rng.randrange(1, 4), 1, 3))
    x = rng.randrange(20, 60)
    while x < w:
        kind = rng.choice(['hedge', 'hedge', 'fence', 'barrel', 'post'])
        if kind == 'hedge':
            hw = rng.randrange(30, 56)
            for i in range(6):
                bx = x + rng.randrange(0, hw - 14)
                bh = rng.randrange(20, 34)
                pygame.draw.ellipse(s, darken(leaf, rng.uniform(0.0, 0.2)), (bx, base - bh, 18, bh + 4))
            for _ in range(10):
                s.fill(lighten(leaf, 0.15), (x + rng.randrange(hw - 4), base - rng.randrange(6, 20), 2, 2))
            if season in (0, 1):
                for _ in range(5):
                    s.fill(rng.choice([(250, 220, 230), (250, 240, 200)]), (x + rng.randrange(hw - 4),
                                                                            base - rng.randrange(6, 20), 2, 2))
            if snow:
                for i in range(0, hw - 6, 4):
                    s.fill((246, 248, 255), (x + i + 2, base - rng.randrange(24, 32), 5, 2))
            x += hw
        elif kind == 'fence':
            fw = rng.randrange(40, 90)
            wood = (236, 228, 214) if season != 2 else (222, 210, 190)
            s.fill(darken(wood, 0.2), (x, base - 12, fw, 2))
            s.fill(darken(wood, 0.2), (x, base - 5, fw, 2))
            for px in range(x, x + fw, 6):
                s.fill(wood, (px, base - 18, 4, 18))
                s.set_at((px + 1, base - 19), wood)
                s.set_at((px + 2, base - 19), wood)
                s.fill(darken(wood, 0.15), (px + 3, base - 18, 1, 18))
                if snow:
                    s.fill((250, 250, 255), (px, base - 20, 4, 2))
            x += fw
        elif kind == 'barrel':
            s.fill((120, 80, 52), (x, base - 14, 16, 14))
            s.fill((90, 60, 40), (x, base - 11, 16, 1))
            s.fill((90, 60, 40), (x, base - 4, 16, 1))
            pygame.draw.ellipse(s, darken(leaf, 0.05) if not snow else (50, 90, 66), (x - 2, base - 22, 20, 11))
            if season < 3:
                for _ in range(6):
                    s.fill(rng.choice([(236, 90, 100), (250, 214, 90), (250, 150, 190), (230, 130, 50)]),
                           (x + rng.randrange(14), base - 21 + rng.randrange(6), 2, 2))
            else:
                s.fill((246, 248, 255), (x, base - 22, 16, 3))
            x += 16
        else:
            s.fill((70, 66, 72), (x, base - 12, 4, 12))
            s.fill((96, 92, 100), (x, base - 13, 4, 2))
            x += 4
        x += rng.randrange(50, 150)
    return s


def draw_paving(s, sc, pave_line):
    """Paving joints that run back towards the buildings, in the same perspective as their sides."""
    vx = W / 2
    top, bot = GROUND - 4, GROUND + 5
    k = (bot - top) / (bot - VP_Y)
    for x in range(-(sc % 12), W + 12, 12):
        pygame.draw.line(s, pave_line, (x, bot), (int(x + 2 + (vx - x) * k * SIDE_SWING), top))


# ---------------------------------------------------------------- the street, drawn once per season
def build_street(season, projects):
    s = pygame.Surface((TOWN_W, H), pygame.SRCALPHA)
    wins = []
    snow = season == 3
    lamps = []
    lights = []                     # winter string lights that glow after dark
    deco = random.Random(19 + season)
    # pavement and street, on their own layer (the paving joints are drawn live, in perspective)
    street = s
    s = ground = pygame.Surface((TOWN_W, H), pygame.SRCALPHA)
    pave = PAVE[season]
    s.fill(pave, (0, GROUND - 4, TOWN_W, 10))
    s.fill(lighten(pave, 0.08), (0, GROUND - 4, TOWN_W, 1))
    pygame.draw.line(s, darken(pave, 0.25), (0, GROUND + 6), (TOWN_W, GROUND + 6), 2)
    s.fill(lighten(pave, 0.1), (0, GROUND + 5, TOWN_W, 1))                       # the kerb's lit edge
    road = (128, 120, 116) if not snow else (176, 180, 192)
    s.fill(road, (0, GROUND + 8, TOWN_W, H - GROUND - 8))
    s.fill(darken(road, 0.25), (0, GROUND + 8, TOWN_W, 2))                       # shade under the kerb
    rng = random.Random(4)
    y = GROUND + 10
    while y < H:                     # cobbles grow as the road comes towards you
        d = (y - GROUND) / (H - GROUND)
        ch, cw = 3 + int(d * 4), 7 + int(d * 8)
        off = rng.randrange(0, cw)
        for x in range(-off, TOWN_W, cw + 2):
            c = lerp_c(road, (150, 144, 138) if not snow else (220, 224, 236), rng.uniform(0.1, 0.5))
            pygame.draw.rect(s, c, (x + 1, y, cw, ch), border_radius=1)
            s.fill(lighten(c, 0.12), (x + 2, y, cw - 2, 1))
        y += ch + 2
    if snow:
        for _ in range(500):
            x, y = rng.randrange(TOWN_W), rng.randrange(GROUND + 8, H)
            s.fill((244, 246, 252), (x, y, rng.randrange(3, 12), 2))
    if season == 2:
        for _ in range(260):
            x, y = rng.randrange(TOWN_W), rng.randrange(GROUND - 3, H)
            s.fill(rng.choice([(214, 110, 50), (230, 170, 60), (180, 70, 50)]), (x, y, 2, 1))
    s.fill(lerp_c(pave, (230, 220, 200), 0.3), (500, GROUND - 4, 340, 6))       # the square's paving
    s = street
    # --- west end: the path down to the lake
    for x in range(0, 110, 3):
        hgt = 10 + int(6 * math.sin(x * 0.3))
        col = [(96, 150, 86), (90, 140, 72), (170, 120, 64), (220, 226, 236)][season]
        pygame.draw.line(s, col, (x, GROUND - 4), (x, GROUND - 4 - hgt), 3)
    s.fill((120, 88, 60), (42, GROUND - 30, 3, 28))
    pygame.draw.polygon(s, (170, 128, 84), [(26, GROUND - 30), (62, GROUND - 30), (68, GROUND - 26), (62, GROUND - 22),
                                            (26, GROUND - 22)])
    sign_text(s, 'Lantern Lake', (46, GROUND - 26), (70, 48, 34))
    # --- Old Tom's Tackle: weathered blue planks, a big wooden fish
    x0, x1 = 132, 318
    _planks(s, pygame.Rect(x0, GROUND - 74, x1 - x0, 70), (92, 128, 140), (78, 110, 122))
    _grounded(s, x0, x1, GROUND - 72)
    _tin_roof(s, x0, x1, GROUND - 74, 34, snow, deco)
    _door(s, 226, 16, 28, (120, 86, 60), (70, 52, 40))
    for wx in (156, 268):
        _window(s, wx, GROUND - 56, 18, 16, (230, 224, 210), wins)
        _window_box(s, wx, 18, GROUND - 37, season, deco)
    _festoon(s, x0 + 2, x1 - 2, GROUND - 71, season, lights, 4)
    _decorate_door(s, 226, 16, 28, season, deco)
    _sign(s, 226, GROUND - 92, "OLD TOM'S TACKLE", (238, 226, 196), (60, 44, 36))
    fish = [(176, GROUND - 66), (200, GROUND - 72), (222, GROUND - 66), (200, GROUND - 60)]
    pygame.draw.polygon(s, (226, 170, 80), [(246, GROUND - 74), (266, GROUND - 80), (284, GROUND - 74), (266, GROUND - 68)])
    pygame.draw.polygon(s, (206, 140, 60), [(284, GROUND - 74), (292, GROUND - 80), (292, GROUND - 68)])
    s.set_at((252, GROUND - 75), (40, 30, 30))
    del fish
    for bx in (140, 300):
        s.fill((140, 100, 66), (bx, GROUND - 16, 12, 12))
        s.fill((110, 78, 52), (bx, GROUND - 16, 12, 2))
        s.fill((110, 78, 52), (bx, GROUND - 10, 12, 1))
    pygame.draw.line(s, (150, 110, 70), (186, GROUND - 4), (194, GROUND - 32), 2)    # rods leaning on the wall
    pygame.draw.line(s, (120, 90, 60), (190, GROUND - 4), (202, GROUND - 30), 2)
    # --- Mabel's Bakery: cream walls, striped awning, bread in the window
    x0, x1 = 338, 474
    s.fill((244, 226, 200), (x0, GROUND - 82, x1 - x0, 78))
    for y in range(GROUND - 80, GROUND - 4, 6):
        pygame.draw.line(s, (232, 210, 182), (x0, y), (x1 - 1, y))
    # a mansard roof of rosy scalloped tiles, with a dormer and a tall chimney
    s.fill((150, 130, 124), (436, GROUND - 120, 12, 18))     # chimney
    s.fill((126, 108, 104), (434, GROUND - 122, 16, 3))
    roof = (186, 98, 100)
    pygame.draw.polygon(s, roof, [(x0 - 5, GROUND - 82), (x0 + 7, GROUND - 106), (x1 - 7, GROUND - 106),
                                  (x1 + 5, GROUND - 82)])
    for j, yy in enumerate(range(GROUND - 102, GROUND - 82, 4)):
        k = (yy - (GROUND - 106)) / 24
        a, b = x0 + 7 - 12 * k, x1 - 7 + 12 * k
        for x in range(int(a) + 1 + (j % 2) * 3, int(b) - 5, 6):
            pygame.draw.arc(s, darken(roof, 0.25), (x, yy - 3, 6, 6), math.pi, 2 * math.pi)
            s.fill(lighten(roof, 0.1), (x + 2, yy - 2, 2, 1))
    s.fill(darken(roof, 0.3), (x0 + 5, GROUND - 108, x1 - x0 - 10, 3))
    s.fill((250, 240, 226), (x0 - 6, GROUND - 84, x1 - x0 + 12, 3))      # cream trim
    if snow:
        s.fill((246, 248, 255), (x0 + 5, GROUND - 110, x1 - x0 - 10, 3))
        s.fill((246, 248, 255), (434, GROUND - 124, 16, 2))
    s.fill((244, 226, 200), (396, GROUND - 102, 20, 16))      # the dormer
    _window(s, 401, GROUND - 99, 10, 9, (150, 100, 80), wins)
    _gable(s, 396, 416, GROUND - 102, 7, darken(roof, 0.1), darken(roof, 0.35), snow)
    _grounded(s, x0, x1, GROUND - 82)
    _window(s, 352, GROUND - 52, 34, 20, (150, 100, 80), wins)
    _door(s, 404, 16, 30, (176, 96, 88), (120, 70, 60))
    _window(s, 432, GROUND - 52, 26, 20, (150, 100, 80), wins)
    _bakery_display(s, season)
    _decorate_door(s, 404, 16, 30, season, deco)
    _a_board(s, 466)
    for i in range(0, x1 - x0 + 8, 8):
        c = (226, 104, 110) if (i // 8) % 2 == 0 else (250, 244, 236)
        pygame.draw.polygon(s, c, [(x0 - 4 + i, GROUND - 64), (x0 + 4 + i, GROUND - 64), (x0 + 4 + i, GROUND - 58),
                                   (x0 + i, GROUND - 55), (x0 - 4 + i, GROUND - 58)])
    _sign(s, 406, GROUND - 78, "MABEL'S BAKERY", (250, 236, 220), (160, 70, 70))
    # --- the square: notice board, fountain base, benches
    ground_shadow(s, 548, GROUND - 3, 58, 60)
    ground_shadow(s, 653, GROUND - 1, 88, 70)
    for bx in (601, 737):
        ground_shadow(s, bx, GROUND - 3, 26, 56)
    s.fill((120, 86, 60), (526, GROUND - 40, 3, 36))
    s.fill((120, 86, 60), (567, GROUND - 40, 3, 36))
    s.fill((150, 108, 72), (520, GROUND - 48, 56, 30))
    s.fill((112, 80, 56), (518, GROUND - 50, 60, 3))
    for i, (px, py, c) in enumerate(((524, GROUND - 44, (250, 246, 230)), (540, GROUND - 42, (236, 226, 170)),
                                     (556, GROUND - 45, (220, 236, 246)))):
        s.fill(c, (px, py, 13, 15))
        s.fill(darken(c, 0.25), (px + 2, py + 3, 9, 1))
        s.fill(darken(c, 0.25), (px + 2, py + 6, 7, 1))
        s.fill((200, 70, 70), (px + 6, py, 2, 2))
    _sign(s, 548, GROUND - 60, 'NOTICES', (238, 226, 196), (60, 44, 36))
    # fountain basin (the water is drawn live)
    pygame.draw.ellipse(s, (170, 168, 172), (612, GROUND - 16, 82, 18))
    pygame.draw.ellipse(s, (130, 128, 136), (612, GROUND - 16, 82, 18), 2)
    s.fill((170, 168, 172), (612, GROUND - 8, 82, 6))
    s.fill((150, 148, 156), (646, GROUND - 40, 12, 30))
    pygame.draw.ellipse(s, (170, 168, 172), (634, GROUND - 44, 36, 8))
    # benches
    for bx in (590, 726):
        s.fill((150, 100, 66), (bx, GROUND - 10, 22, 2))
        s.fill((150, 100, 66), (bx, GROUND - 16, 22, 2))
        s.fill((100, 70, 50), (bx + 2, GROUND - 10, 1, 6))
        s.fill((100, 70, 50), (bx + 19, GROUND - 10, 1, 6))
    if 'bandstand' in projects:
        bx = 758
        s.fill((236, 230, 220), (bx, GROUND - 10, 66, 6))
        for px in (bx + 2, bx + 31, bx + 61):
            s.fill((236, 230, 220), (px, GROUND - 44, 3, 34))
        pygame.draw.polygon(s, (196, 96, 92), [(bx - 6, GROUND - 44), (bx + 33, GROUND - 62), (bx + 72, GROUND - 44)])
        for i in range(0, 78, 8):
            pygame.draw.line(s, (240, 236, 226), (bx - 6 + i, GROUND - 44), (bx + 33, GROUND - 62))
        pygame.draw.line(s, (150, 70, 70), (bx - 6, GROUND - 44), (bx + 72, GROUND - 44), 2)
    # --- Fernwick Aquarium: stone, columns, round windows with fish
    x0, x1 = 862, 1084
    _bricks(s, pygame.Rect(x0, GROUND - 90, x1 - x0, 86), (196, 190, 178), (176, 168, 156), 5, 12)
    _grounded(s, x0, x1, GROUND - 88)
    # a copper cupola with a fish on top, gone green with age
    cx = (x0 + x1) // 2
    dome = (104, 166, 150)
    pygame.draw.ellipse(s, dome, (cx - 12, GROUND - 144, 24, 26))
    for dx in (-6, 0, 6):
        pygame.draw.line(s, darken(dome, 0.2), (cx + dx // 2, GROUND - 143), (cx + dx, GROUND - 131))
    s.fill(lighten(dome, 0.25), (cx - 7, GROUND - 139, 2, 4))
    if snow:
        pygame.draw.arc(s, (246, 248, 255), (cx - 12, GROUND - 144, 24, 26), 0.5, 2.6, 3)
    s.fill((214, 208, 196), (cx - 11, GROUND - 131, 22, 12))
    s.fill((176, 168, 156), (cx - 11, GROUND - 131, 22, 1))
    for dx in (-6, 2):
        s.fill((60, 100, 130), (cx + dx, GROUND - 128, 4, 7))
        s.fill((90, 140, 176), (cx + dx, GROUND - 128, 4, 2))
    s.fill((230, 226, 216), (cx - 13, GROUND - 120, 26, 3))
    s.fill((200, 160, 70), (cx, GROUND - 152, 1, 8))
    pygame.draw.polygon(s, (220, 180, 80), [(cx - 4, GROUND - 153), (cx + 2, GROUND - 155), (cx + 4, GROUND - 153),
                                            (cx + 2, GROUND - 151)])
    pygame.draw.polygon(s, (220, 180, 80), [(cx - 4, GROUND - 153), (cx - 6, GROUND - 155), (cx - 6, GROUND - 151)])
    pygame.draw.polygon(s, (214, 208, 196), [(x0 - 8, GROUND - 90), ((x0 + x1) // 2, GROUND - 118),
                                             (x1 + 8, GROUND - 90)])
    pygame.draw.polygon(s, (176, 168, 156), [(x0 - 8, GROUND - 90), ((x0 + x1) // 2, GROUND - 118),
                                             (x1 + 8, GROUND - 90)], 2)
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(x0 - 8, GROUND - 91), ((x0 + x1) // 2, GROUND - 119),
                                                       (x1 + 8, GROUND - 91)], 3)
    pygame.draw.circle(s, (110, 160, 190), ((x0 + x1) // 2, GROUND - 100), 7)
    pygame.draw.circle(s, (176, 168, 156), ((x0 + x1) // 2, GROUND - 100), 7, 2)
    s.fill((214, 208, 196), (x0 - 4, GROUND - 92, x1 - x0 + 8, 4))
    for cx in (884, 920, 1024, 1060):
        s.fill((232, 228, 220), (cx - 4, GROUND - 86, 8, 80))
        s.fill((204, 198, 188), (cx + 2, GROUND - 86, 2, 80))
        s.fill((214, 208, 196), (cx - 6, GROUND - 88, 12, 4))
    for wx in (902, 1042):
        pygame.draw.circle(s, (210, 204, 192), (wx, GROUND - 50), 11)
        pygame.draw.circle(s, (60, 110, 150), (wx, GROUND - 50), 9)
        pygame.draw.circle(s, (90, 150, 190), (wx - 2, GROUND - 52), 5)
        wins.append(pygame.Rect(wx - 7, GROUND - 57, 14, 14))
    _door(s, 972, 24, 36, (100, 82, 70), (176, 168, 156))
    for i in range(3):
        s.fill((214, 208, 196), (950 - i * 4, GROUND - 4 - (3 - i) * 2, 44 + i * 8, 2))
    _pot(s, 937, season, True, deco)
    _pot(s, 1007, season, True, deco)
    if season == 3:
        _wreath(s, 972, GROUND - 32)
    for a, b in ((x0 + 2, 916), (928, 1016), (1028, x1 - 2)):
        _festoon(s, a, b, GROUND - 87, season, lights, 3)
    _sign(s, 972, GROUND - 78, 'AQUARIUM & MUSEUM', (236, 232, 222), (60, 90, 120))
    # --- Town Hall: brick, a clock tower (the hands are drawn live), a flag
    x0, x1 = 1108, 1276
    _bricks(s, pygame.Rect(x0, GROUND - 80, x1 - x0, 76), (170, 92, 76), (146, 78, 66))
    _grounded(s, x0, x1, GROUND - 78)
    _gable(s, x0, x1, GROUND - 80, 22, (90, 92, 110), (60, 62, 80), snow)
    s.fill((170, 92, 76), (1174, GROUND - 140, 36, 70))
    _bricks(s, pygame.Rect(1174, GROUND - 140, 36, 60), (170, 92, 76), (146, 78, 66))
    pygame.draw.polygon(s, (90, 92, 110), [(1170, GROUND - 140), (1192, GROUND - 166), (1214, GROUND - 140)])
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(1170, GROUND - 141), (1192, GROUND - 167), (1214, GROUND - 141)], 3)
    pygame.draw.circle(s, (244, 238, 220), (1192, GROUND - 118), 11)
    pygame.draw.circle(s, (90, 70, 60), (1192, GROUND - 118), 11, 2)
    s.fill((90, 70, 60), (1191, GROUND - 190, 2, 26))
    for wx in (1124, 1150, 1222, 1248):
        _window(s, wx, GROUND - 60, 12, 20, (236, 226, 206), wins)
        _window_box(s, wx, 12, GROUND - 37, season, deco)
    _door(s, 1192, 22, 34, (90, 70, 60), (236, 226, 206))
    _decorate_door(s, 1192, 22, 34, season, deco)
    for a, b in ((x0 + 2, 1170), (1214, x1 - 2)):
        _festoon(s, a, b, GROUND - 77, season, lights, 4)
    _sign(s, 1192, GROUND - 76, 'TOWN HALL', (236, 226, 206), (110, 50, 44))
    # --- Pip's Ring Toss: a striped tent stall with bottles
    x0, x1 = 1300, 1404
    _shade(s, (x0 + 3, GROUND - 4, x1 - x0 - 6, 5), 70, 0)
    s.fill((214, 170, 110), (x0 + 6, GROUND - 26, x1 - x0 - 12, 22))
    s.fill((180, 140, 90), (x0 + 6, GROUND - 26, x1 - x0 - 12, 3))
    for i in range(6):
        s.fill([(110, 180, 120), (110, 160, 210), (230, 200, 90), (110, 180, 120), (220, 120, 120), (110, 160, 210)][i],
               (x0 + 22 + i * 12, GROUND - 38, 4, 12))
        s.fill((236, 236, 220), (x0 + 23 + i * 12, GROUND - 42, 2, 4))
    for px in (x0 + 4, x1 - 6):
        s.fill((150, 110, 76), (px, GROUND - 62, 3, 58))
    for i in range(0, x1 - x0 + 12, 10):
        c = (220, 90, 100) if (i // 10) % 2 == 0 else (250, 244, 232)
        pygame.draw.polygon(s, c, [(x0 - 6 + i, GROUND - 62), (x0 + 4 + i, GROUND - 62), (x0 + 4 + i, GROUND - 76),
                                   (x0 - 6 + i, GROUND - 70)])
    _sign(s, 1352, GROUND - 56, 'RING TOSS', (250, 236, 150), (150, 60, 60))
    # --- Library: green walls, tall windows, a book sign
    x0, x1 = 1430, 1594
    _planks(s, pygame.Rect(x0, GROUND - 80, x1 - x0, 76), (120, 150, 112), (104, 132, 98), 5)
    _grounded(s, x0, x1, GROUND - 78)
    slate = (88, 98, 122)
    _gable(s, x0, x1, GROUND - 80, 30, slate, (60, 66, 86))
    _shingles(s, x0 - 6, x1 + 6, (x0 + x1) // 2, GROUND - 80, 30, slate, 4, True)
    if snow:
        pygame.draw.lines(s, (246, 248, 255), False, [(x0 - 6, GROUND - 81), ((x0 + x1) // 2, GROUND - 111),
                                                       (x1 + 6, GROUND - 81)], 3)
    for wx in (1446, 1476, 1540, 1570):
        _window(s, wx, GROUND - 66, 12, 26, (240, 232, 214), wins)
    _door(s, 1512, 18, 32, (110, 80, 60), (240, 232, 214))
    _decorate_door(s, 1512, 18, 32, season, deco)
    _festoon(s, x0 + 2, x1 - 2, GROUND - 77, season, lights, 5)
    s.fill((140, 150, 150), (1556, GROUND - 120, 10, 30))     # chimney, down to the slates
    s.fill((120, 128, 130), (1554, GROUND - 122, 14, 3))
    pygame.draw.rect(s, (176, 76, 70), (1500, GROUND - 106, 24, 16))
    s.fill((250, 244, 230), (1502, GROUND - 104, 9, 12))
    s.fill((250, 244, 230), (1513, GROUND - 104, 9, 12))
    _sign(s, 1512, GROUND - 82, 'LIBRARY', (240, 232, 214), (60, 80, 60))
    # --- a cottage row and gardens between the library and the lookout
    for i, (hx, col, rc) in enumerate(((1622, (230, 210, 170), (150, 90, 70)), (1700, (200, 214, 230), (90, 110, 140)))):
        s.fill(col, (hx, GROUND - 54, 58, 50))
        _grounded(s, hx, hx + 58, GROUND - 52)
        if i == 0:
            _thatch(s, hx, hx + 58, GROUND - 54, 24, snow, deco)
        else:
            _saltbox(s, hx, hx + 58, GROUND - 54, rc, darken(rc, 0.3), snow)
        _window(s, hx + 8, GROUND - 40, 12, 12, (250, 246, 236), wins, (110, 140, 100))
        _window(s, hx + 38, GROUND - 40, 12, 12, (250, 246, 236), wins, (110, 140, 100))
        for wx in (hx + 8, hx + 38):
            _window_box(s, wx, 12, GROUND - 26, season, deco)
        s.fill(darken(col, 0.4), (hx + 25, GROUND - 26, 10, 22))
        s.fill(darken(col, 0.5), (hx + 25, GROUND - 26, 10, 1))
        s.set_at((hx + 33, GROUND - 15), (220, 190, 110))
        _pot(s, hx + 18, season, False, deco)
        if season == 3:
            _wreath(s, hx + 30, GROUND - 19)
        _festoon(s, hx + 2, hx + 56, GROUND - 52, season, lights, 3)
    # --- east end: a grassy lookout over the lake, with a bench
    # the lake it looks out on: a far shore, then water all the way down to the grass
    wat_hi = [(150, 190, 206), (136, 182, 204), (156, 168, 170), (206, 220, 232)][season]
    wat_lo = [(84, 134, 160), (74, 126, 156), (96, 118, 128), (170, 190, 210)][season]
    shore = [(84, 124, 84), (70, 112, 66), (156, 108, 62), (214, 222, 232)][season]
    pine = [(56, 92, 68), (48, 84, 58), (78, 92, 62), (120, 140, 150)][season]
    for x in range(LAKE_VIEW[0], TOWN_W):
        k = min(1.0, (x - LAKE_VIEW[0]) / 26.0)                 # the hedge thins out into open water
        top = GROUND - 34 + int(round((1 - k) * 22))
        for y in range(top, GROUND + 2):
            c = lerp_c(wat_hi, wat_lo, (y - (GROUND - 34)) / 36.0)
            s.set_at((x, y), c)
        s.fill(shore, (x, top - 2, 1, 2))
        if k >= 1 and (x * 7) % 11 < 4:
            h = 3 + (x * 13) % 5
            s.fill(pine, (x, top - 2 - h, 1, h))                   # a far treeline on the other side
    for x in range(LAKE_VIEW[0] - 4, LAKE_VIEW[0] + 30, 2):          # the hedge the view opens out of
        h = 30 - (x - LAKE_VIEW[0] + 4)
        if h > 0:
            s.fill(darken(shore, 0.2), (x, GROUND - h, 3, h))
    for x in range(1774, TOWN_W, 3):
        hgt = 8 + int(5 * math.sin(x * 0.27))
        col = [(96, 150, 86), (90, 140, 72), (170, 120, 64), (220, 226, 236)][season]
        pygame.draw.line(s, col, (x, GROUND + 6), (x, GROUND - hgt), 3)
    s.fill((150, 100, 66), (1832, GROUND - 10, 28, 2))
    s.fill((150, 100, 66), (1832, GROUND - 17, 28, 2))
    s.fill((100, 70, 50), (1834, GROUND - 10, 1, 8))
    s.fill((100, 70, 50), (1857, GROUND - 10, 1, 8))
    s.fill((140, 110, 80), (1786, GROUND - 22, 30, 3))
    for px in (1790, 1812):
        s.fill((140, 110, 80), (px, GROUND - 22, 2, 18))
    # --- planters (Flower Beds project) and lamp posts
    if 'flowers' in projects:
        cols = {0: [(250, 160, 190), (255, 230, 120)], 1: [(250, 120, 110), (250, 220, 90)],
                2: [(230, 140, 60), (200, 90, 70)], 3: [(220, 40, 50), (240, 240, 240)]}[season]
        for px in (122, 326, 490, 600, 850, 1096, 1290, 1420, 1606, 1770):
            s.fill((150, 96, 70), (px - 7, GROUND - 10, 14, 6))
            s.fill((120, 76, 56), (px - 7, GROUND - 10, 14, 1))
            for j in range(5):
                stem = (80, 140, 70) if season != 3 else (40, 100, 60)
                s.fill(stem, (px - 5 + j * 2, GROUND - 14, 1, 4))
                s.fill(cols[j % 2], (px - 6 + j * 2, GROUND - 16 - (j % 2), 2, 2))
    lamp_x = (110, 500, 840, 1416, 1780) if 'lamps' not in projects else \
        (110, 324, 500, 600, 840, 1098, 1288, 1416, 1600, 1780)
    for lx in lamp_x:
        ground_shadow(s, lx + 1, GROUND - 3, 9, 70)
        s.fill((60, 58, 64), (lx, GROUND - 40, 2, 36))
        s.fill((60, 58, 64), (lx - 2, GROUND - 6, 6, 2))
        s.fill((60, 58, 64), (lx - 3, GROUND - 44, 8, 2))
        s.fill((230, 210, 160), (lx - 2, GROUND - 42, 6, 5))
        lamps.append((lx + 1, GROUND - 40))
    return s, wins, lamps, lights, ground


def build_back(season):
    """Hills and a far treeline/rooftop layer that scroll slower than the street."""
    far_w = W + (TOWN_W - W) // 4
    mid_w = W + (TOWN_W - W) // 2
    far = pygame.Surface((far_w, H), pygame.SRCALPHA)
    mid = pygame.Surface((mid_w, H), pygame.SRCALPHA)
    hill = [(140, 170, 190), (130, 170, 160), (180, 150, 140), (200, 210, 226)][season]
    pts = _ridge(far_w, 214, [(40, 0.006), (16, 0.021), (6, 0.07)], 3)
    pygame.draw.polygon(far, hill, [(0, H)] + pts + [(far_w, H)])
    # the lake glimpsed beyond the east end of the street
    lake_x = far_w - 150
    pygame.draw.ellipse(far, (120, 160, 196), (lake_x, 204, 220, 30))
    green = [(92, 140, 92), (78, 126, 74), (176, 120, 66), (200, 214, 228)][season]
    pts = _ridge(mid_w, 252, [(22, 0.012), (8, 0.05)], 8)
    pygame.draw.polygon(mid, darken(green, 0.15), [(0, H)] + pts + [(mid_w, H)])
    rng = random.Random(11)
    for x in range(-10, mid_w, 9):
        top = 238 - rng.randrange(0, 28)
        c = darken(green, rng.uniform(0.0, 0.25))
        if rng.random() < 0.6:
            pygame.draw.polygon(mid, c, [(x, 262), (x + 6, top), (x + 12, 262)])
        else:
            pygame.draw.circle(mid, c, (x + 6, top + 10), 8)
    # a few far-off rooftops
    for i in range(14):
        hx = rng.randrange(0, mid_w - 40)
        roof = [(176, 96, 82), (110, 116, 140), (150, 110, 80)][i % 3]
        mid.fill(lerp_c((220, 210, 190), green, 0.3), (hx, 244, 22, 18))
        pygame.draw.polygon(mid, roof, [(hx - 3, 244), (hx + 11, 234), (hx + 25, 244)])
    if season == 3:
        for (x, y) in pts[::2]:
            mid.fill((240, 244, 252), (int(x), int(y), 6, 2))
    return far, mid


# ---------------------------------------------------------------- the town
class Town:
    def __init__(self):
        self.x = 60.0
        self.face = 1
        self.step = 0.0
        self.target = None          # walk here (and maybe do something on arrival)
        self.on_arrive = None
        self.scroll = 0.0
        self.built = None
        self.street = None
        self.wins = []
        self.lamps = []
        self.lights = []
        self.t = 0.0
        self.smoke = []
        self.notes = []
        self.coins_fx = []
        self.folk = {k: dict(x=float(f['home']) + random.uniform(-30, 30), face=1, step=0.0, goal=None, wait=0.0)
                     for k, f in FOLK.items()}
        self.talk_to = None
        self.scene_folk = set()     # neighbours a cutscene is moving about
        self.gift_mode = False
        self.reply = ''
        self.lib_page = 0
        self.year = 0                   # which year it is (kept up to date in update)
        self.bake_tab = 'treats'
        self.bake_anim = None           # Mabel fetching what you bought: dict(id, t0)
        self.bake_say = None            # (what she's saying, when she started)
        self.hall_tab = 'town'
        self.rt = dict(rings=0, t=0.0, fly=None, marks=[], won=0, msg='', speed=1.6)
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self._fx = None
        import biscuit
        self.cat = biscuit.Follower()   # Biscuit, when she comes along
        self.sitting = None             # on the lookout bench: dict(t, cat) where cat is 'walk', 'hop' or 'curl'
        self.pigeons = []
        for i, px in enumerate(PIGEON_SPOTS):
            for j in range(2 + i % 2):
                self.pigeons.append(dict(home=px, x=px + j * 7 - 5.0, y=0.0, vx=0.0, vy=0.0, fly=False,
                                         face=1 if j % 2 else -1, ph=random.uniform(0, 6), away=0.0))

    # ------------------------------------------------------------ helpers
    def to_screen_x(self, x):
        return x - self.scroll

    def folk_here(self, k, minute):
        if FOLK[k].get('new_in_year', 0) > self.year:
            return False                    # hasn't moved to Fernwick yet
        return (330 <= minute < 1290 or k == 'fen' and (minute >= 1290 or minute < 60)
                or k == 'mabel' and minute >= 1290)

    def audio_ctx(self, g):
        """What Fernwick sounds like where you are standing."""
        m = g.minute
        ctx = {'town': True}
        if g.env.season != 3:                            # the fountain freezes over in winter
            ctx['fountain'] = max(0.0, 1 - abs(self.x - 652) / 240.0)
        if 'bandstand' in g.projects and 1020 <= m < 1260 and g.env.rain < 0.5:
            ctx['band'] = max(0.15, 1 - abs(self.x - 790) / 520.0)
        if g.overlay in (None, 'scene'):
            near = [f['x'] - self.x for k, f in self.folk.items()
                    if self.folk_here(k, m) and abs(f['x'] - self.x) < 150 and k != self.talk_to]
            if near:
                d = min(near, key=abs)
                ctx['chatter'] = (1 - abs(d) / 170.0, 0.5 + max(-0.35, min(0.35, d / 300.0)))
        return ctx

    def nearest(self, g):
        """The closest thing you could talk to or step into: ('folk', id) or ('place', id), or None."""
        import discover
        if discover.near_find(g):
            return ('cat', None)                  # Biscuit is waiting by what she found
        best, bd = None, 9999
        for k, f in self.folk.items():
            if self.folk_here(k, g.minute):
                d = abs(f['x'] - self.x)
                if d < 16 and d + 8 < bd:            # standing right at a door, the door wins
                    best, bd = ('folk', k), d + 8
        for p in PLACES:
            d = abs(p['door'] - self.x)
            reach = 30 if p['id'] in ('lake', 'lookout', 'fountain') else 14 if p['id'] == 'cocoa' else 22
            if d < reach and d < bd:
                best, bd = ('place', p['id']), d
        return best

    def prompt(self, g):
        if self.sitting is not None:
            return 'Stand up'
        n = self.nearest(g)
        if not n:
            return None
        kind, key = n
        if kind == 'cat':
            return 'See what Biscuit found'
        if kind == 'folk':
            return 'Talk to %s' % FOLK[key]['name']
        p = PLACE_BY_ID[key]
        if key == 'cocoa' and not (p['hours'][0] <= g.minute < p['hours'][1]):
            return "Mabel's Cocoa Cart  (after dark)"
        if p['hours'] and not (p['hours'][0] <= g.minute < p['hours'][1]):
            return '%s  (opens %s)' % (p['name'], fmt_hour(p['hours'][0]))
        if key == 'lookout' and self.can_stargaze(g):
            return 'Lie back and look at the stars'
        return {'lake': 'Walk back to the lake', 'board': 'Read the notices', 'museum': 'Go into the aquarium', 'fountain': 'Make a wish (10 coins)',
                'lookout': 'Sit and watch the lake'}.get(key, 'Go into %s' % p['name'])

    # ------------------------------------------------------------ update
    def update(self, dt, g, keys_walk):
        import seasons
        self.year = seasons.year(g)
        self.t += dt
        moving = 0
        if g.overlay != 'talk':
            self.talk_to = None
        if g.overlay is not None or g.rest_phase is not None:
            keys_walk = 0
            if self.target is not None and g.rest_phase is not None:
                self.target, self.on_arrive = None, None
        if self.sitting is not None and (keys_walk or self.target is not None or g.overlay not in (None,)):
            self.stand_up(g)
        if g.overlay is not None:
            pass
        elif self.sitting is not None:
            self.sitting['t'] += dt
        elif keys_walk:
            self.target, self.on_arrive = None, None
            moving = keys_walk
        elif self.target is not None:
            d = self.target - self.x
            if abs(d) < 2:
                self.x = self.target
                self.target = None
                act, self.on_arrive = self.on_arrive, None
                if act:
                    act()
            else:
                moving = 1 if d > 0 else -1
        if moving:
            self.face = moving
            self.x = max(14.0, min(TOWN_W - 14.0, self.x + moving * WALK * dt))
            before = self.step
            self.step += dt * 9
            if int(before / math.pi) != int(self.step / math.pi):
                g.audio.step(0.22 if g.env.season == 3 else 0.3)
        elif g.overlay != 'scene':
            self.step = 0.0
        want = self.x - W / 2
        self.scroll += (max(0.0, min(TOWN_W - W, want)) - self.scroll) * min(1.0, dt * 6)
        import biscuit
        import discover
        st = self.sitting
        if st is not None and biscuit.follows(g):
            # Biscuit trots over, hops up beside you and curls up
            cat = self.cat
            spot = BENCH_X + 9
            if cat.x is None:
                cat.x = spot - 20
            if st['cat'] == 'walk':
                d = spot - cat.x
                if abs(d) > 1.5:
                    cat.x += math.copysign(min(abs(d) * 4, 60.0) * dt, d)
                    cat.face = 1 if d > 0 else -1
                    cat.step += dt * 12
                else:
                    cat.x, cat.step = float(spot), 0.0
                    st['cat'], st['ct'] = 'hop', 0.0
            elif st['cat'] == 'hop':
                st['ct'] += dt
                if st['ct'] > 0.35:
                    st['cat'] = 'curl'
                    g.audio.play('purr', 0.3)
        elif biscuit.follows(g) and not discover.drive(g, self, dt):
            self.cat.update(dt, self.x, self.face)
        self._pigeons(dt, g)
        # townsfolk
        m = g.minute
        band = 'bandstand' in g.projects and 1020 <= m < 1260
        for k, f in self.folk.items():
            spec = FOLK[k]
            if not self.folk_here(k, m) or k in self.scene_folk:
                continue
            if f['goal'] is None:
                f['wait'] -= dt
                if f['wait'] <= 0:
                    if band and k not in ('pip',):
                        f['goal'] = random.uniform(700, 860)
                    elif spec['work'][0] <= m < spec['work'][1]:
                        f['goal'] = spec['home'] + random.uniform(-36, 36)
                    elif k == 'mabel' and m >= 1230:
                        f['goal'] = 709 + random.uniform(-4, 4)      # minding the cocoa cart
                    elif k == 'fen' and (m >= 1290 or m < 60):
                        f['goal'] = random.uniform(1800, 1880)
                    elif k == 'rowan':
                        f['goal'] = random.uniform(1786, 1880)        # watching the lake go dark
                    else:
                        f['goal'] = random.uniform(520, 820)
                    if self.talk_to == k:
                        f['goal'] = None
                        f['wait'] = 1.0
            else:
                d = f['goal'] - f['x']
                if abs(d) < 1.5 or self.talk_to == k:
                    f['goal'] = None
                    f['wait'] = random.uniform(2, 7)
                    f['step'] = 0.0
                else:
                    f['face'] = 1 if d > 0 else -1
                    f['x'] += f['face'] * 22 * dt
                    f['step'] += dt * 7
        if self.talk_to:
            f = self.folk[self.talk_to]
            f['face'] = 1 if self.x > f['x'] else -1
            f['step'] = 0.0
        # chimney smoke, music notes, coin sparkles
        if random.random() < dt * 2.5:
            for cx, cy in ((442, GROUND - 124), (1561, GROUND - 120)):
                self.smoke.append([cx + random.uniform(-1, 1), cy, random.uniform(2, 5), 3.0])
        for p in self.smoke:
            p[0] += (4 + g.env.wind * 10) * dt
            p[1] -= p[2] * dt
            p[3] -= dt
        self.smoke = [p for p in self.smoke if p[3] > 0][-60:]
        if band and random.random() < dt * 3:
            self.notes.append([random.uniform(770, 812), GROUND - 40, 2.0])
        for n in self.notes:
            n[1] -= 10 * dt
            n[2] -= dt
        self.notes = [n for n in self.notes if n[2] > 0]
        for c in self.coins_fx:
            c[1] += c[2] * dt
            c[2] += 120 * dt
            c[3] -= dt
        self.coins_fx = [c for c in self.coins_fx if c[3] > 0]
        self._passing(dt, g)
        rt = self.rt
        if rt['rings'] > 0 or rt['fly']:
            rt['t'] += dt
        if rt['fly']:
            rt['fly'][1] += dt / 0.55
            if rt['fly'][1] >= 1:
                self._ring_lands(g)

    def _passing(self, dt, g):
        """Walk past a neighbour and they say a word or two in a speech bubble (no window, you keep walking)."""
        say = getattr(self, 'says', None)
        if say is None:
            say = self.says = {}            # k -> [text, seconds left]
            self.say_cd = {}
        for k in list(say):
            say[k][1] -= dt
            if say[k][1] <= 0:
                del say[k]
        for k in list(self.say_cd):
            self.say_cd[k] -= dt
            if self.say_cd[k] <= 0:
                del self.say_cd[k]
        if g.overlay is not None or g.rest_phase is not None or self.sitting is not None or say:
            return
        for k, f in self.folk.items():
            if k in self.say_cd or k in self.scene_folk or not self.folk_here(k, g.minute):
                continue
            d = abs(f['x'] - self.x)
            if 18 < d < 70:
                say[k] = [dialogue.passing(g, k, random.Random()), 3.2]
                self.say_cd[k] = 45.0
                g.audio.chat(0.3)
                break

    # ------------------------------------------------------------ input
    def click(self, g, wx, wy):
        tx = wx + self.scroll
        import discover
        if discover.click(g, tx, wy, GROUND):
            return
        for k, f in self.folk.items():
            if self.folk_here(k, g.minute) and abs(f['x'] - tx) < 8 and GROUND - 34 < wy < GROUND + 2:
                self.walk_to(f['x'] - 12 * (1 if f['x'] > self.x else -1), lambda k=k: self.open_talk(g, k))
                return
        for p in PLACES:
            top = GROUND - {'museum': 130, 'hall': 180, 'lookout': 60, 'lake': 50, 'board': 64,
                            'fountain': 56, 'cocoa': 44}.get(p['id'], 100)
            if p['x0'] <= tx <= p['x1'] and top < wy < GROUND + 4:
                self.walk_to(p['door'], lambda pid=p['id']: self.use_place(g, pid))
                return
        self.walk_to(max(14, min(TOWN_W - 14, tx)), None)

    def walk_to(self, x, then):
        self.target = float(x)
        self.on_arrive = then

    def _pigeons(self, dt, g):
        """Pigeons pecking on the pavement; they clatter up when you walk right through them."""
        for p in self.pigeons:
            if p['fly']:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += 18 * dt
                p['away'] += dt
                if p['away'] > 14 and abs(self.x - p['home']) > 120:
                    p.update(fly=False, x=p['home'] + random.uniform(-8, 8), y=0.0, away=0.0)   # back again
            else:
                p['ph'] += dt
                if self.sitting is None and abs(self.x - p['x']) < 16 and self.step:
                    side = 1 if p['x'] >= self.x else -1
                    p.update(fly=True, vx=side * random.uniform(40, 70), vy=-random.uniform(50, 80), face=side,
                             away=0.0)
                    g.audio.play('rustle', 0.2, max(0.0, min(1.0, (p['x'] - self.scroll) / W)))
                elif random.random() < dt * 0.3:
                    p['face'] = -p['face']

    def draw_pigeons(self, s, sc, t):
        for p in self.pigeons:
            x = int(p['x'] - sc)
            if not -10 < x < W + 10:
                continue
            body, dark = (150, 154, 168), (110, 112, 128)
            d = p['face']
            if p['fly']:
                y = int(GROUND - 2 + p['y'])
                if y < -10:
                    continue
                s.fill(body, (x - 2, y - 2, 4, 2))
                up = int(t * 18 + p['ph']) % 2
                s.fill(dark, (x - 4, y - 3 - up * 2, 3, 1))
                s.fill(dark, (x + 1, y - 3 - up * 2, 3, 1))
            else:
                peck = 1 if math.sin(p['ph'] * 3) > 0.7 else 0
                y = GROUND + 2
                s.fill(body, (x - 2, y - 3, 5, 3))
                s.fill(dark, (x - 2 - d, y - 3, 2, 2))            # tail
                s.fill((120, 140, 150), (x + 2 * d, y - 5 + peck * 2, 2, 2))   # head, bobbing down to peck
                s.set_at((x + 3 * d, y - 4 + peck * 2), (230, 160, 80))
                s.set_at((x, y), (200, 110, 100))

    def stand_up(self, g):
        if self.sitting is None:
            return
        self.sitting = None
        self.cat.sit = 0.0
        self.face = 1

    def interact(self, g):
        if self.sitting is not None:
            self.stand_up(g)
            return
        n = self.nearest(g)
        if not n:
            g.toast('Nothing here. Walk up to a door or a neighbour.', (150, 140, 130))
            return
        if n[0] == 'cat':
            import discover
            discover.reveal(g)
        elif n[0] == 'folk':
            self.open_talk(g, n[1])
        else:
            self.use_place(g, n[1])

    def use_place(self, g, pid):
        p = PLACE_BY_ID[pid]
        if p['hours'] and not (p['hours'][0] <= g.minute < p['hours'][1]):
            g.toast('%s is closed. It opens at %s.' % (p['name'], fmt_hour(p['hours'][0])), (150, 140, 130))
            return
        g.audio.play('page', 0.6)
        if pid == 'lake':
            g.go_place('lake')
        elif pid == 'tackle':
            g.shop_tab = 'sell'
            g.overlay = 'shop'
        elif pid == 'fountain':
            self.wish(g)
        elif pid == 'lookout':
            self.sit(g)
        elif pid == 'ringtoss':
            self.rt.update(msg='', won=0, marks=[])
            g.overlay = 'ringtoss'
        elif pid == 'museum':
            import aquarium
            aquarium.enter(g)            # walk in and look around (Juniper's desk is just inside)
        else:
            if pid == 'library':
                self.lib_page = 0
            g.overlay = pid
        g.release_holds()

    # ------------------------------------------------------------ activities
    def wish(self, g):
        if g.town_day.get('wish') == g.day:
            g.toast('You already made a wish today. The fountain needs time to think.', (110, 140, 170))
            return
        if g.coins < 10:
            g.toast('A wish costs 10 coins.', (200, 120, 100))
            return
        g.coins -= 10
        g.town_day['wish'] = g.day
        g.luck = min(3.0, g.luck + 0.5)
        for _ in range(8):
            self.coins_fx.append([652 + random.uniform(-4, 4), GROUND - 30, -random.uniform(40, 80), 0.6])
        g.audio.play('splash_small', 0.6)
        r = random.random()
        if r < 0.2:
            g.coins += 40
            g.toast('Plink! A frog hops out and spits up 40 coins. Lucky you!', (110, 150, 100))
        elif r < 0.35:
            g.baits['golden'] = g.baits.get('golden', 0) + 1
            g.toast('Something glints at the bottom: a Golden Lure!', (210, 160, 60))
        else:
            g.toast('Plink. You make a wish and feel a little luckier.', (110, 150, 100))
        g.stats['wishes'] = g.stats.get('wishes', 0) + 1
        g.save()

    def can_stargaze(self, g):
        m = g.minute
        return ((m >= 1230 or m < 300) and g.env.weather == 'clear' and g.env.season is not None
                and g.town_day.get('stars') != g.night_id())

    def stargaze(self, g):
        import scenes
        g.town_day['stars'] = g.night_id()
        self.x = 1846.0
        self.target, self.on_arrive = None, None
        name = CONSTELLATIONS[g.env.season % 4]
        beats = [('face', 'you', -1),
                 ('fade', 'You lie back on the lookout bench. Fernwick goes quiet, and the sky fills up with stars.'),
                 ('picture', 'stars', name)]
        fen = self.folk['fen']
        if self.folk_here('fen', g.minute) and abs(fen['x'] - 1846) < 90:
            beats += [('walk', 'fen', ('by', 'you', 14)), ('sync',), ('face', 'fen', 'you'), ('face', 'you', 'fen'),
                      ('say', 'fen', "You found my favourite spot. Can you see %s? Grandma Rosie showed me that "
                                     "one when I was small." % name),
                      ('say', 'you', "She showed me too. She said it keeps watch over the lake while we sleep."),
                      ('emote', 'fen', 'heart'),
                      ('call', lambda g: g.add_friend('fen', 3))]
        else:
            beats += [('say', 'you', "There's %s, right where Grandma said it would be. Goodnight, lake." % name)]
        beats += [('emote', 'you', 'note'), ('call', _stargaze_reward), ('wait', 0.8)]
        g.scene = scenes.Cutscene(g, beats, 'town', title='Stargazing')
        g.overlay = 'scene'
        g.release_holds()
        g.audio.play('wish', 0.5)

    def sit(self, g):
        if self.can_stargaze(g):
            self.stargaze(g)
            return
        if abs(self.x - BENCH_X) > 1:
            self.walk_to(BENCH_X, lambda: self.sit_down(g))
        else:
            self.sit_down(g)

    def sit_down(self, g):
        """Sit on the lookout bench, facing the lake; Biscuit comes and curls up beside you."""
        self.x = float(BENCH_X)
        self.target, self.on_arrive = None, None
        self.step = 0.0
        self.sitting = dict(t=0.0, cat='walk', ct=0.0)
        g.audio.play('creak', 0.35)
        if g.town_day.get('sit') != g.day:
            g.town_day['sit'] = g.day
            g.luck = min(3.0, g.luck + 0.3)
            g.toast('A quiet moment by the lake. Luck +', (110, 150, 100))

    def open_talk(self, g, k):
        import scenes
        if g.friends.get(k, 0) >= scenes.HEART_SCENE_AT and k not in g.heart_seen and g.overlay is None:
            scenes.start_heart(g, k)        # a little scene with them, once, at 5 hearts
            return
        import legends
        if legends.on_talk(g, k):           # a legend's tale, once its letter has come
            return
        import yeartwo
        if yeartwo.on_talk(g, k):           # meeting the new neighbour
            return
        self.talk_to = k
        self.gift_mode = False
        spec = FOLK[k]
        rng = random.Random()                 # a new pick every time you stop to talk
        line = dialogue.talk_line(g, k, spec['lines'], rng)
        env = g.env
        b = BIRTHDAYS.get((env.season, (g.day - 1) % 7 + 1))
        if b and b['fish'] == spec['loves']:
            line = "It's my birthday today! Don't tell anyone. Well, you can tell a few people."
        clue = legends.clue_line(g, k)
        if clue:
            line = clue                     # they know something about a legend you're hunting
        self.reply = line
        talked = g.town_day.setdefault('talked', {})
        if talked.get(k) != g.day:
            talked[k] = g.day
            g.add_friend(k, int(round(2 * g.boost('friend'))))
        g.overlay = 'talk'
        g.release_holds()
        g.audio.chat(0.55)

    def give(self, g, fid):
        k = self.talk_to
        if k is None:
            return
        gifts = g.town_day.setdefault('gifted', {})
        if gifts.get(k) == g.day:
            self.reply = "You already gave me something today. You're too kind!"
            return
        item = next((b for b in sorted(g.basket, key=lambda b: b['price']) if b['id'] == fid), None)
        if not item:
            return
        g.basket.remove(item)
        gifts[k] = g.day
        spec = ALL_BY_ID[fid]
        name = FOLK[k]['name']
        if fid == FOLK[k]['loves']:
            pts, self.reply = 25, "A %s! It's my absolute favourite! How did you know?" % spec['name']
        elif spec.get('junk'):
            pts, self.reply = -3, "Oh. A %s. Thank you... I think?" % spec['name'].lower()
        elif spec['rarity'] >= 3:
            pts, self.reply = 15, "A %s? That's a treasure. I'll never forget this." % spec['name']
        elif spec['rarity'] == 2:
            pts, self.reply = 10, 'What a lovely %s. Thank you so much!' % spec['name']
        else:
            pts, self.reply = 6, 'A %s for me? That is very sweet of you.' % spec['name']
        g.add_friend(k, int(round(pts * g.boost('friend'))) if pts > 0 else pts)
        self.gift_mode = False
        g.audio.play('jingle1' if pts > 0 else 'ui', 0.6)
        g.toast('%s %s' % (name, 'loved it!' if pts >= 15 else 'liked that.' if pts > 0 else 'looks puzzled.'),
                (220, 120, 140))
        g.save()

    def give_dish(self, g, rid):
        k = self.talk_to
        if k is None:
            return
        gifts = g.town_day.setdefault('gifted', {})
        if gifts.get(k) == g.day:
            self.reply = "You already gave me something today. You're too kind!"
            return
        if g.pantry.get(rid, 0) <= 0:
            return
        g.pantry[rid] -= 1
        if not g.pantry[rid]:
            del g.pantry[rid]
        gifts[k] = g.day
        r = kitchen.RECIPE_BY_ID[rid]
        if kitchen.FAVOURITE_DISH.get(k) == rid:
            pts, self.reply = 30, "%s! You cooked this yourself? It's my very favourite. Oh, I could cry." % r['name']
        elif rid == 'feast':
            pts, self.reply = 35, 'A whole Lakeside Feast, just for me? I am inviting you to dinner, no arguments.'
        else:
            pts, self.reply = 15, 'Homemade %s! It smells wonderful. Thank you, truly.' % r['name']
        g.add_friend(k, int(round(pts * g.boost('friend'))))
        g.stats['dish_gifts'] = g.stats.get('dish_gifts', 0) + 1
        self.gift_mode = False
        g.audio.play('jingle1', 0.6)
        g.toast('%s %s' % (FOLK[k]['name'], 'loved it!' if pts >= 30 else 'was delighted.'), (220, 120, 140))
        g.save()

    def throw(self, g):
        rt = self.rt
        if rt['rings'] <= 0 or rt['fly']:
            return
        rt['rings'] -= 1
        rt['fly'] = [self.marker_x(), 0.0]
        g.audio.play('ui', 0.5)

    def marker_x(self):
        rt = self.rt
        return math.sin(rt['t'] * rt['speed']) * 1.0

    def _ring_lands(self, g):
        rt = self.rt
        x = rt['fly'][0]
        rt['fly'] = None
        # five bottles at -0.8 .. 0.8; the middle one is gold and worth three tickets
        best = min(range(5), key=lambda i: abs(x - (-0.8 + i * 0.4)))
        off = abs(x - (-0.8 + best * 0.4))
        if off < 0.07:
            won = 3 if best == 2 else 1
            rt['won'] += won
            rt['marks'].append((x, True))
            g.tickets += won
            rt['msg'] = 'Ringer! +%d ticket%s' % (won, 's' if won > 1 else '')
            g.audio.play('coin', 0.6)
        else:
            rt['marks'].append((x, False))
            rt['msg'] = 'Clink! So close.' if off < 0.12 else 'It bounces away.'
            g.audio.play('splash_small', 0.3)
        rt['speed'] += 0.25
        if rt['rings'] == 0:
            rt['msg'] = 'All done! You won %d ticket%s.' % (rt['won'], '' if rt['won'] == 1 else 's')
            g.stats['tosses'] = g.stats.get('tosses', 0) + 1
            g.save()

    def start_toss(self, g):
        if g.coins < TOSS_COST:
            self.rt['msg'] = 'A game costs %d coins.' % TOSS_COST
            return
        g.coins -= TOSS_COST
        self.rt.update(rings=5, t=random.uniform(0, 6), fly=None, marks=[], won=0, msg='Space or click to throw!',
                       speed=1.6)
        g.audio.play('coin', 0.5)

    def redeem(self, g, prize):
        if g.tickets < prize['tickets']:
            return
        pid = prize['id']
        if prize.get('hat'):
            if pid in g.hats:
                return
            g.hats.append(pid)
            g.toast('You won the %s! Try it on in the cabin wardrobe.' % prize['name'], (210, 160, 60))
        elif pid == 'coins':
            g.coins += 150
            g.toast('150 coins, straight into your pocket.', (210, 160, 60))
        else:
            n = 3 if pid == 'storm' else 2
            g.baits[pid] = g.baits.get(pid, 0) + n
            g.toast('%s x%d added to your tackle box.' % (BAIT_BY_ID[pid]['name'], n), (210, 160, 60))
        g.tickets -= prize['tickets']
        g.audio.play('jingle2', 0.6)
        g.check_badges()
        g.save()

    # ------------------------------------------------------------ drawing the street
    def ensure_built(self, g):
        key = (g.env.season, tuple(sorted(g.projects)))
        if self.built != key:
            self.street, self.wins, self.lamps, self.lights, self.ground = build_street(g.env.season, g.projects)
            self.far, self.mid = build_back(g.env.season)
            self.fore = build_fore(g.env.season)
            self.built = key

    def draw(self, frame, env, g):
        self.ensure_built(g)
        w = g.world
        w._sky(frame, env)
        frame.fill(env.sky[2], (0, HORIZON, W, H - HORIZON))
        sc = int(self.scroll)
        amb = env.amb
        if env.fog > 0.01:
            amb = lerp_c(amb, env.fog_color, env.fog * 0.5)
        far = self.far.subsurface((sc // 4, 0, W, H)).copy()
        far.fill((*lerp_c(amb, env.sky[2], 0.35), 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(far, (0, 0))
        mid = self.mid.subsurface((sc // 2, 0, W, H)).copy()
        mid.fill((*lerp_c(amb, env.sky[2], 0.15), 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(mid, (0, 0))
        near = self.near
        near.fill((0, 0, 0, 0))
        near.blit(self.ground, (0, 0), (sc, 0, W, H))
        draw_paving(near, sc, darken(PAVE[env.season], 0.12))
        draw_volumes(near, sc, env.season)
        near.blit(self.street, (0, 0), (sc, 0, W, H))
        self._draw_live(near, env, g, sc)
        near.blit(self.fore, (0, H - FORE_H), (int(sc * FORE_K), 0, W, FORE_H))
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(near, (0, 0))
        nf = env.nf
        if nf > 0.05:
            for r in self.wins:
                if -20 < r.x - sc < W + 20:
                    frame.fill((int(210 * nf), int(150 * nf), int(70 * nf)), r.move(-sc, 0),
                               special_flags=pygame.BLEND_ADD)
                    add_glow(frame, w.g_mid, (r.centerx - sc, r.centery), nf * 0.55)
            for i, (lx, ly, c) in enumerate(self.lights):          # winter string lights, twinkling
                x = lx - sc
                if -8 < x < W + 8 and (int(self.t * 1.5) + i) % 7:
                    frame.fill((int(c[0] * nf), int(c[1] * nf), int(c[2] * nf)), (x, ly, 2, 2),
                               special_flags=pygame.BLEND_ADD)
                    add_glow(frame, w.g_small, (x + 1, ly + 1), nf * 0.5)
            for (lx, ly) in self.lamps:
                if -40 < lx - sc < W + 40:
                    fl = 0.9 + 0.1 * math.sin(self.t * 9 + lx)
                    add_glow(frame, w.g_big, (lx - sc, ly), nf * 0.75 * fl)
                    frame.fill((int(230 * nf), int(190 * nf), int(110 * nf)), (lx - 3 - sc, ly - 2, 6, 5),
                               special_flags=pygame.BLEND_ADD)
            if g.minute >= 1230 and -40 < 709 - sc < W + 40:
                fl = 0.9 + 0.1 * math.sin(self.t * 7)
                add_glow(frame, w.g_big, (709 - sc - 10, GROUND - 40), nf * 0.8 * fl)
                frame.fill((int(240 * nf), int(180 * nf), int(90 * nf)), (709 - sc - 12, GROUND - 42, 4, 5),
                           special_flags=pygame.BLEND_ADD)
        w._weather(frame, env)

    def _draw_live(self, s, env, g, sc):
        t = self.t
        season = env.season
        # fountain water
        fx = 652 - sc
        if -60 < fx < W + 60:
            water = (120, 170, 210) if season != 3 else (200, 220, 236)
            pygame.draw.ellipse(s, water, (fx - 36, GROUND - 14, 72, 10))
            if season != 3:
                for i in range(10):
                    a = (t * 1.8 + i * 0.37) % 1.0
                    side = -1 if i % 2 else 1
                    px = fx + side * a * 22
                    py = GROUND - 46 - math.sin(a * math.pi) * 10 + a * 34
                    s.fill((210, 236, 255), (int(px), int(py), 1, 2))
                s.fill((200, 230, 250), (fx - 1, GROUND - 52, 2, 8))
            for c in self.coins_fx:
                s.fill((246, 206, 80), (int(c[0] - sc), int(c[1]), 2, 2))
        import yeartwo
        yeartwo.draw_cottage(s, g, sc, GROUND, t)
        # Mabel's cocoa cart
        cx = 709 - sc
        if -40 < cx < W + 40:
            draw_cocoa_cart(s, cx, g.minute >= 1230, t, season)
        # town hall clock shows the real time of day
        cx, cy = 1192 - sc, GROUND - 118
        if -20 < cx < W + 20:
            m = g.minute
            for ang, ln, col in (((m / 720.0) * 2 * math.pi, 6, (60, 40, 40)), ((m % 60) / 60.0 * 2 * math.pi, 9,
                                                                                  (90, 70, 60))):
                pygame.draw.line(s, col, (cx, cy), (cx + math.sin(ang) * ln, cy - math.cos(ang) * ln))
            # a flag on the tower
            for i in range(10):
                yy = GROUND - 190 + int(math.sin(t * 5 - i * 0.6) * (1 + i * 0.12))
                s.fill((200, 70, 70) if i % 4 < 2 else (240, 230, 200), (cx + 1 + i, yy, 1, 6))
        wind = getattr(env, 'wind', 0.3)
        if -20 < 225 - sc < W + 20:
            draw_weathervane(s, 225 - sc, GROUND - 108, t, wind)
        draw_hanging_signs(s, sc, t, wind)
        # smoke
        for x, y, v, life in self.smoke:
            a = int(110 * min(1.0, life / 3.0))
            pygame.draw.circle(s, (220, 220, 226, a), (int(x - sc), int(y)), 2 + int((3.0 - life) * 1.3))
        # music notes over the bandstand
        for x, y, life in self.notes:
            c = (250, 240, 200, int(255 * min(1.0, life)))
            px, py = int(x - sc), int(y)
            s.fill(c, (px, py, 2, 2))
            s.fill(c, (px + 1, py - 5, 1, 5))
            s.fill(c, (px + 2, py - 5, 2, 1))
        # bandstand musicians
        m = g.minute
        rain = env.rain > 0.3
        if 'bandstand' in g.projects and 1020 <= m < 1260 and -80 < 790 - sc < W + 80:
            for bx in (776, 806):
                ground_shadow(s, bx - sc, GROUND - 10, 12, 60)
            walker(s, 776 - sc, GROUND - 10, 1, 0, (90, 110, 170), (60, 44, 40), 'tophat', season)
            walker(s, 806 - sc, GROUND - 10, -1, 0, (170, 120, 90), (196, 150, 90), 'none', season)
            pygame.draw.line(s, (176, 120, 70), (778 - sc, GROUND - 22), (786 - sc, GROUND - 28), 2)
        # townsfolk, then friends, then you (you are always in front)
        for k in FOLK_ORDER:
            f = self.folk[k]
            if not self.folk_here(k, m):
                continue
            x = int(f['x'] - sc)
            if -30 < x < W + 30:
                spec = FOLK[k]
                ground_shadow(s, x, GROUND, 10 if spec.get('kid') else 13)
                walker(s, x, GROUND, f['face'], f['step'], spec['shirt'], spec['hair'], spec['hat'], season,
                       spec.get('kid'), spec.get('glasses'), umbrella=(180, 90, 100) if rain else None)
                if k == 'fen' and abs(f['x'] - 1702) < 40 and not f['goal'] and 480 <= m < 1200:
                    ex = int(1680 - sc)
                    pygame.draw.line(s, (120, 90, 60), (ex, GROUND), (ex + 4, GROUND - 24), 1)
                    pygame.draw.line(s, (120, 90, 60), (ex + 8, GROUND), (ex + 4, GROUND - 24), 1)
                    s.fill((250, 246, 236), (ex - 2, GROUND - 22, 12, 10))
                    s.fill((120, 160, 200), (ex, GROUND - 18, 8, 3))
                    s.fill((90, 140, 90), (ex, GROUND - 15, 8, 2))
        for pid, v in self.town_peers(g):
            x = int(v['tx'] - sc)
            if -30 < x < W + 30:
                ground_shadow(s, x, GROUND, 13)
                walker(s, x, GROUND, v['face'], self.t * 9 + pid if v['walk'] else 0, actors.PEER_COLORS[pid % 4],
                       actors.PEER_HAIR[pid % 4], v['hat'], season, umbrella=(110, 140, 190) if rain else None)
                if v['em']:
                    actors.draw_bubble(s, x + 1, GROUND - 32, v['em'], t + pid)
        # the lake below the lookout glitters
        lx0 = LAKE_VIEW[0] + 26 - sc
        if lx0 < W + 10:
            for i in range(14):
                a = (t * 0.12 + i * 0.37) % 1.0
                px = lx0 + (i * 53 + int(t * 3)) % (TOWN_W - LAKE_VIEW[0] - 30)
                py = GROUND - 30 + (i * 11) % 22
                if math.sin(t * 2.4 + i * 1.7) > 0.2 and -4 < px < W + 4:
                    s.fill(lighten(lerp_c((150, 190, 206), (240, 246, 250), 0.6), 0.1) + (int(200 * a),),
                           (int(px), py, 2 + (i % 3), 1))
        self.draw_pigeons(s, sc, t)
        import biscuit
        st = self.sitting
        if biscuit.follows(g):
            if st is not None and st['cat'] in ('hop', 'curl'):
                k = min(1.0, st['ct'] / 0.35) if st['cat'] == 'hop' else 1.0
                cx = int(BENCH_X + 9 - sc)
                cy = int(GROUND - (GROUND - BENCH_SEAT) * k - math.sin(math.pi * k) * 6)
                actors.draw_cat(s, g, t, cx, cy + 1, bed=False, sleep=False, face=1, trick=False, look=0)
            else:
                if self.cat.x is not None:
                    ground_shadow(s, self.cat.x - sc, GROUND, 14, 60)
                self.cat.draw(s, g, t, sc, GROUND)
                import discover
                discover.draw_town(s, g, t, sc, GROUND)
        x = int(self.x - sc)
        if st is not None:
            breathe = 1 if math.sin(st['t'] * 1.6) > 0.6 else 0
            sitter(s, x, BENCH_SEAT, actors.SHIRT[season], (112, 72, 52), g.hat, season, breathe)
            # the bench's back rail is between us and you now
            s.fill((150, 100, 66), (BENCH_X - 14 - sc, GROUND - 17, 28, 2))
            s.fill((120, 80, 56), (BENCH_X - 14 - sc, GROUND - 15, 28, 1))
        else:
            ground_shadow(s, x, GROUND, 13)
            walker(s, x, GROUND, self.face, self.step, actors.SHIRT[season], (112, 72, 52), g.hat, season,
                   umbrella=(90, 130, 110) if rain else None)
        if g.emote:
            actors.draw_bubble(s, x + 1, GROUND - 32, g.emote[0], t)
        draw_front(s, sc, season, t)

    def town_peers(self, g):
        n = getattr(g, 'net', None)
        if n is None or not n.online:
            return []
        return [(pid, p['v']) for pid, p in sorted(n.peers.items()) if p.get('v') and p['v']['place'] == 'town']


# ---------------------------------------------------------------- the windows you open in town
def _panel(g, s, w, h, title):
    ui = g.ui
    rect = pygame.Rect(g_sw(g) // 2 - w // 2, g_sh(g) // 2 - h // 2, w, h)
    ui.panel(s, rect, radius=24)
    g.panel_header(s, rect, title)
    ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', g.close_overlay, 'normal', font='h3')
    return rect


def g_sw(g):
    return g.canvas.get_width()


def g_sh(g):
    return g.canvas.get_height()


def hearts(s, x, y, n, size=1):
    for i in range(10):
        cx = x + i * 22
        col = (226, 84, 104) if i < n else (214, 200, 186)
        pygame.draw.circle(s, col, (cx - 4, y), 5)
        pygame.draw.circle(s, col, (cx + 4, y), 5)
        pygame.draw.polygon(s, col, [(cx - 9, y + 1), (cx + 9, y + 1), (cx, y + 10)])


def portrait(g, s, k, center, scale=4):
    spec = FOLK[k]
    tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
    walker(tmp, 13, 38, 1, 0, spec['shirt'], spec['hair'], spec['hat'], g.env.season, False, spec.get('glasses'))
    big = pygame.transform.scale(tmp, (26 * scale, 40 * scale))
    s.blit(big, big.get_rect(center=center))


def snack_icon(s, sid, c):
    x, y = c
    if sid == 'bun':
        pygame.draw.ellipse(s, (214, 150, 80), (x - 16, y - 8, 32, 18))
        pygame.draw.ellipse(s, (236, 190, 110), (x - 12, y - 7, 22, 8))
        pygame.draw.arc(s, (170, 110, 60), (x - 8, y - 4, 16, 10), 0.2, 2.9, 2)
    elif sid == 'tea':
        pygame.draw.rect(s, (240, 236, 226), (x - 12, y - 8, 20, 18), border_radius=4)
        pygame.draw.rect(s, (160, 110, 70), (x - 10, y - 6, 16, 5))
        pygame.draw.circle(s, (240, 236, 226), (x + 10, y), 5, 2)
        for i in (-6, 0):
            pygame.draw.line(s, (200, 200, 210), (x + i, y - 12), (x + i + 2, y - 18), 2)
    elif sid == 'pie':
        pygame.draw.ellipse(s, (210, 160, 100), (x - 18, y - 6, 36, 16))
        pygame.draw.ellipse(s, (100, 80, 160), (x - 14, y - 6, 28, 10))
        for i in range(-12, 13, 6):
            pygame.draw.line(s, (230, 190, 120), (x + i, y - 6), (x + i + 3, y + 4), 2)
    elif sid == 'cocoa':
        pygame.draw.rect(s, (200, 110, 100), (x - 12, y - 8, 20, 18), border_radius=4)
        pygame.draw.rect(s, (110, 70, 50), (x - 10, y - 6, 16, 4))
        pygame.draw.circle(s, (240, 236, 230), (x - 6, y - 7), 2)
        pygame.draw.circle(s, (240, 236, 230), (x - 1, y - 8), 2)
        pygame.draw.circle(s, (200, 110, 100), (x + 10, y), 5, 2)
        for i in (-6, 0):
            pygame.draw.line(s, (200, 200, 210), (x + i, y - 12), (x + i + 2, y - 18), 2)
    elif sid == 'mooncake':
        pygame.draw.circle(s, (210, 160, 90), (x, y), 15)
        pygame.draw.circle(s, (236, 196, 120), (x, y), 11)
        pygame.draw.circle(s, (250, 240, 200), (x + 3, y - 2), 6)
        pygame.draw.circle(s, (236, 196, 120), (x + 6, y - 4), 5)
    else:
        U.star(s, (x, y), 15, (236, 190, 100))
        U.star(s, (x, y), 8, (250, 226, 150))


def _stargaze_reward(g):
    g.luck = min(3.0, g.luck + 1.0)
    g.stats['stargazed'] = g.stats.get('stargazed', 0) + 1
    g.toast('The stars make you feel lucky. Luck +1.', (120, 130, 200))
    g.save()


def draw_cocoa_cart(s, cx, open_, t, season):
    wood, dark = (150, 96, 62), (100, 64, 44)
    # wheels and body
    for wx in (cx - 9, cx + 9):
        pygame.draw.circle(s, (70, 50, 40), (wx, GROUND - 4), 5)
        pygame.draw.circle(s, (130, 100, 70), (wx, GROUND - 4), 2)
    s.fill(wood, (cx - 14, GROUND - 22, 28, 14))
    s.fill(dark, (cx - 14, GROUND - 22, 28, 2))
    s.fill((176, 120, 80), (cx - 12, GROUND - 18, 24, 1))
    s.fill(dark, (cx + 14, GROUND - 18, 6, 2))                  # the handle
    if not open_:
        # folded up for the day under a striped tarp
        pygame.draw.polygon(s, (180, 170, 150), [(cx - 15, GROUND - 22), (cx - 10, GROUND - 32), (cx + 10, GROUND - 32),
                                                 (cx + 15, GROUND - 22)])
        for i in range(-8, 10, 6):
            s.fill((150, 140, 124), (cx + i, GROUND - 31, 2, 9))
        if season == 3:
            s.fill((246, 248, 255), (cx - 10, GROUND - 34, 20, 2))
        return
    # poles, striped awning, a hanging lantern
    s.fill(dark, (cx - 13, GROUND - 44, 2, 22))
    s.fill(dark, (cx + 11, GROUND - 44, 2, 22))
    for i in range(8):
        col = (196, 90, 86) if i % 2 == 0 else (246, 236, 220)
        s.fill(col, (cx - 16 + i * 4, GROUND - 48, 4, 5))
        pygame.draw.polygon(s, col, [(cx - 16 + i * 4, GROUND - 43), (cx - 12 + i * 4, GROUND - 43),
                                     (cx - 14 + i * 4, GROUND - 41)])
    s.fill((60, 50, 40), (cx - 11, GROUND - 43, 1, 2))
    s.fill((250, 210, 120), (cx - 12, GROUND - 41, 3, 4))
    # a pot of cocoa with steam, and mugs on the counter
    s.fill((120, 120, 128), (cx - 2, GROUND - 28, 9, 6))
    s.fill((150, 150, 160), (cx - 3, GROUND - 29, 11, 1))
    for i in range(3):
        a = (t * 0.6 + i / 3.0) % 1.0
        px = cx + 2 + int(math.sin(t * 2 + i * 2) * 2)
        s.fill((236, 236, 240, int(200 * (1 - a))), (px, GROUND - 31 - int(a * 12), 1, 2))
    for i, col in enumerate(((240, 236, 226), (200, 120, 110), (140, 170, 200))):
        s.fill(col, (cx - 11 + i * 4, GROUND - 26, 3, 4))
    # a little chalk sign
    s.fill((60, 56, 60), (cx - 24, GROUND - 14, 8, 10))
    s.fill(dark, (cx - 21, GROUND - 4, 2, 4))
    s.fill((236, 230, 220), (cx - 23, GROUND - 12, 6, 1))
    s.fill((236, 230, 220), (cx - 23, GROUND - 9, 4, 1))


def draw_cocoa(g, s):
    ui = g.ui
    rect = _panel(g, s, 760, 370, "Mabel's Cocoa Cart")
    ui.blit_text(s, '"Can\'t sleep either? Something warm for the night fish, dear."', (rect.x + 36, rect.y + 92),
                 'small', U.SOFT, maxw=rect.w - 72)
    for i, sn in enumerate(NIGHT_SNACKS):
        r = pygame.Rect(rect.x + 30, rect.y + 128 + i * 92, rect.w - 60, 82)
        ui.tile(s, r, (238, 232, 246), (170, 160, 196))
        ic = pygame.Surface((48, 40), pygame.SRCALPHA)
        snack_icon(ic, sn['id'], (24, 22))
        ic = pygame.transform.scale(ic, (96, 80))
        s.blit(ic, ic.get_rect(center=(r.x + 50, r.centery)))
        ui.blit_text(s, sn['name'], (r.x + 100, r.y + 14), 'bodyb', U.INK)
        ui.blit_text(s, sn['desc'], (r.x + 100, r.y + 46), 'small', U.SOFT, maxw=r.w - 300)
        if g.buff(sn['id']):
            ui.blit_text(s, 'Had one tonight', (r.right - 110, r.centery), 'smallb', (90, 90, 150), 'center')
        else:
            g.price_button(s, (r.right - 180, r.y + 18, 150, 46), sn['price'], lambda sn=sn: g.buy_snack(sn),
                           g.coins >= sn['price'])
    ui.blit_text(s, 'Night treats last until dawn. The cart is out from 8:30pm till midnight.',
                 (rect.centerx, rect.bottom - 34), 'small', U.SOFT, 'center')


def draw_panel(g, s, ov):
    {'cocoa': draw_cocoa, 'bakery': draw_bakery, 'museum': draw_museum, 'board': draw_board, 'hall': draw_hall, 'ringtoss': draw_ringtoss,
     'library': draw_library, 'talk': draw_talk}[ov](g, s)


# ---------------------------------------------------------------- the bakery: Mabel behind her counter
BAKE_W, BAKE_H = 200, 64                     # the little shop scene
BAKE_VIEW, BAKE_K = (20, 8, 160, 52), 5      # the part of it you see, drawn at 5x
BAKE_SHELF = {'bun': 40, 'tea': 172, 'pie': 62, 'cookie': 150}     # where each treat sits behind her
BAKE_SERVE = {'bun': 'Still warm from the oven, dear. Mind your fingers!',
              'tea': "Steeped just right. The fish won't know what hit them.",
              'pie': 'Blueberries from the hill, picked this very morning.',
              'cookie': 'Make a wish on the star before the first bite.'}
BAKE_HOVER = {'bun': 'Honey buns are my mother\'s recipe. Sticky, sweet and lucky.',
              'tea': 'A pot of Lakeside Tea, and the fish practically queue up.',
              'pie': 'The pie? Big fish can smell it from the dock, I swear.',
              'cookie': 'Star cookies bring the rare ones up. Old Tom swears by them.'}


def _mabel_line(g):
    m = g.minute
    return ("Morning, dear! The buns are still warm." if m < 600 else
            "Back for more? I saved you the good ones." if g.stats.get('snacks_bought', 0) >= 3 else
            "Afternoon, love. What'll it be?" if m < 960 else "Nearly closing time. Last of the day's baking!")


def bakery_scene(g, t, hover=None):
    """Mabel's shop, 200x64 pixels: shelves of bread, the counter, the oven, and Mabel herself.
    When you buy something she fetches it from the shelf and sets it down on the counter for you."""
    tn = g.town
    s = pygame.Surface((BAKE_W, BAKE_H))
    s.fill((238, 222, 196))
    for x in range(0, BAKE_W, 8):                                    # striped wallpaper
        s.fill((230, 210, 182), (x, 0, 4, 40))
    s.fill((196, 150, 104), (0, 38, BAKE_W, 2))                       # dado rail
    # a window onto the street, and a hanging lamp
    s.fill((150, 112, 80), (84, 4, 32, 22))
    s.fill(lerp_c((150, 196, 226), (40, 50, 90), g.env.nf), (86, 6, 28, 18))
    s.fill((150, 112, 80), (99, 6, 2, 18))
    s.fill((226, 120, 130), (84, 4, 32, 3))
    pygame.draw.line(s, (90, 70, 60), (100, 0), (100, 2))
    # shelves of baking on both sides
    for sx0, sx1 in ((6, 78), (122, 194)):
        for sy in (14, 30):
            s.fill((150, 104, 70), (sx0, sy, sx1 - sx0, 2))
            s.fill((120, 82, 56), (sx0, sy + 2, sx1 - sx0, 1))
        for i, x in enumerate(range(sx0 + 3, sx1 - 6, 9)):
            kind = (i + sx0) % 3
            if kind == 0:
                pygame.draw.ellipse(s, (206, 146, 80), (x, 9, 8, 5))          # loaves
                s.fill((236, 190, 120), (x + 2, 10, 4, 1))
            elif kind == 1:
                s.fill((196, 176, 150), (x + 1, 7, 6, 7))                    # jars
                s.fill((200, 80, 80) if i % 2 else (230, 170, 60), (x + 1, 9, 6, 4))
                s.fill((150, 110, 80), (x + 1, 6, 6, 1))
            else:
                s.fill((220, 160, 90), (x, 11, 9, 3))                         # baguettes
            if i % 2 == 0:
                pygame.draw.ellipse(s, (226, 176, 100), (x, 25, 7, 5))      # buns
            else:
                s.fill((240, 232, 220), (x + 1, 24, 6, 6))                   # little cakes
                s.fill((240, 150, 170), (x + 1, 24, 6, 2))
    # the oven, glowing
    s.fill((110, 100, 104), (176, 32, 22, 22))
    s.fill((60, 52, 56), (180, 40, 14, 8))
    glow = 0.6 + 0.4 * math.sin(t * 3)
    s.fill(lerp_c((180, 80, 40), (255, 170, 80), glow), (182, 42, 10, 4))
    # Mabel
    an = tn.bake_anim
    mx, face, carry, reach = 100.0, 1, None, False
    if an:
        k = t - an['t0']
        shelf = BAKE_SHELF.get(an['id'], 60)
        if k < 0.6:                                   # off to the shelf
            mx = 100 + (shelf - 100) * (k / 0.6)
            face = 1 if shelf > 100 else -1
        elif k < 1.0:                                 # reaching up for it
            mx, face, reach = shelf, (1 if shelf > 100 else -1), True
            carry = an['id'] if k > 0.8 else None
        elif k < 1.6:                                 # and back to the counter
            mx = shelf + (100 - shelf) * ((k - 1.0) / 0.6)
            face = -1 if shelf > 100 else 1
            carry = an['id']
        else:
            face = 1
    elif hover:
        face = 1 if BAKE_SHELF.get(hover, 100) > 100 else -1                   # she looks toward it
    step = 0.0 if (not an or t - an['t0'] >= 1.6 or 0.6 <= t - an['t0'] < 1.0) else t * 9
    sp = FOLK['mabel']
    walker(s, int(mx), 47, face, step, sp['shirt'], sp['hair'], sp['hat'], g.env.season)
    if reach:
        pygame.draw.line(s, (240, 202, 172), (int(mx) + 2 * face, 33), (int(mx) + 5 * face, 24))
    if carry:
        ic = pygame.Surface((48, 40), pygame.SRCALPHA)
        snack_icon(ic, carry, (24, 22))
        ic = pygame.transform.smoothscale(ic, (16, 13))
        hy = 23 if reach else 34
        s.blit(ic, (int(mx) + 4 * face - 8, hy - 7))
    # the counter, in front of her
    s.fill((166, 116, 76), (20, 44, 160, 20))
    s.fill((196, 146, 98), (18, 42, 164, 3))
    for x in range(26, 176, 26):
        pygame.draw.rect(s, (140, 96, 62), (x, 48, 20, 12), 1)
    # a cake under glass, and the till
    s.fill((240, 232, 220), (30, 35, 12, 7))
    s.fill((240, 150, 170), (30, 35, 12, 2))
    s.fill((250, 70, 80), (35, 33, 2, 2))
    pygame.draw.arc(s, (214, 230, 236), (27, 28, 18, 18), 0, math.pi)
    s.fill((150, 140, 140), (152, 34, 14, 8))
    s.fill((110, 100, 100), (154, 31, 10, 3))
    s.fill((240, 220, 120), (156, 36, 6, 2))
    # what she just served, steaming on the counter
    if an and t - an['t0'] >= 1.6:
        ic = pygame.Surface((48, 40), pygame.SRCALPHA)
        snack_icon(ic, an['id'], (24, 22))
        ic = pygame.transform.smoothscale(ic, (20, 17))
        drop = max(0.0, 1 - (t - an['t0'] - 1.6) / 0.15) * 4
        s.blit(ic, (100 - 10, int(43 - 15 - drop)))
        for i in range(3):
            a = (t * 0.7 + i * 0.33) % 1.0
            s.fill((246, 240, 236), (96 + i * 4 + int(math.sin(a * 6 + i) * 1.5), int(28 - a * 12), 1, 2))
    return s


def buy_at_bakery(g, sn):
    if g.coins < sn['price'] or g.buff(sn['id']):
        return
    g.buy_snack(sn, quiet=True)
    if g.buff(sn['id']):
        g.town.bake_anim = dict(id=sn['id'], t0=g.t)
        g.town.bake_say = (BAKE_SERVE[sn['id']], g.t)
        g.stats['snacks_bought'] = g.stats.get('snacks_bought', 0) + 1


def draw_bakery(g, s):
    ui = g.ui
    tn = g.town
    rect = _panel(g, s, 860, 640, "Mabel's Bakery")
    for i, (key, label) in enumerate((('treats', 'Treats'), ('recipes', 'Recipes'))):
        ui.button(s, (rect.x + 420 + i * 140, rect.y + 24, 130, 40), label, lambda k=key: setattr(tn, 'bake_tab', k),
                  'tab_on' if tn.bake_tab == key else 'tab')
    if tn.bake_tab == 'recipes':
        return draw_recipe_cards(g, s, rect)
    t = g.t
    # which card the pointer (or the pad's focus) is on: Mabel turns toward it and talks about it
    cards = []
    cw = (rect.w - 60 - 3 * 12) // 4
    for i, sn in enumerate(SNACKS):
        cards.append((pygame.Rect(rect.x + 30 + i * (cw + 12), rect.y + 368, cw, 222), sn))
    hover = next((sn['id'] for r, sn in cards if r.collidepoint(ui.mouse)), None)
    # the shop itself
    scene = bakery_scene(g, t, hover).subsurface(BAKE_VIEW)        # in close on Mabel and her counter
    sr = pygame.Rect(rect.x + 30, rect.y + 84, BAKE_VIEW[2] * BAKE_K, BAKE_VIEW[3] * BAKE_K)
    pygame.draw.rect(s, (120, 80, 54), sr.inflate(12, 12), border_radius=10)
    s.blit(pygame.transform.scale(scene, sr.size), sr)
    # what Mabel is saying
    said = tn.bake_say
    if said and t - said[1] < 5.0:
        line = said[0]
    elif hover:
        line = BAKE_HOVER[hover]
    else:
        line = _mabel_line(g)
    bw = min(sr.w - 60, ui.fonts['small'].size(line)[0] + 40)
    bub = pygame.Rect(sr.centerx - bw // 2, sr.y + 14, bw, 40)
    pygame.draw.rect(s, (255, 252, 244), bub, border_radius=12)
    pygame.draw.rect(s, (150, 120, 96), bub, 2, border_radius=12)
    pygame.draw.polygon(s, (255, 252, 244), [(bub.centerx - 8, bub.bottom - 2), (bub.centerx + 8, bub.bottom - 2),
                                             (bub.centerx, bub.bottom + 10)])
    ui.blit_text(s, line, bub.center, 'small', U.INK, 'center')
    # the treats, on cards under the counter
    for r, sn in cards:
        hov = r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 246, 232) if hov else (246, 236, 216), (196, 170, 140))
        ic = pygame.Surface((48, 40), pygame.SRCALPHA)
        snack_icon(ic, sn['id'], (24, 22))
        ic = pygame.transform.scale(ic, (96, 80))
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 40)))
        ui.blit_text(s, sn['name'], (r.centerx, r.y + 74), 'bodyb', U.INK, 'midtop')
        for j, ln in enumerate(ui.wrap(sn['desc'], 'tiny', r.w - 20)[:3]):
            ui.blit_text(s, ln, (r.centerx, r.y + 104 + j * 18), 'tiny', U.SOFT, 'midtop')
        if g.buff(sn['id']):
            ui.blit_text(s, 'Eaten today', (r.centerx, r.bottom - 34), 'smallb', (80, 130, 70), 'center')
        else:
            g.price_button(s, (r.centerx - 70, r.bottom - 56, 140, 44), sn['price'],
                           lambda sn=sn: buy_at_bakery(g, sn), g.coins >= sn['price'])
    ui.blit_text(s, 'One treat of each kind a day. They last until bedtime.', (rect.centerx, rect.bottom - 28),
                 'small', U.SOFT, 'center')


def draw_recipe_cards(g, s, rect):
    ui = g.ui
    ui.blit_text(s, '"My mother\'s recipe cards. Cook them on your cabin stove, dear."', (rect.x + 36, rect.y + 92),
                 'small', U.SOFT, maxw=rect.w - 72)
    cards = [r for r in kitchen.RECIPES if r['card']]
    for i, r in enumerate(cards):
        row = pygame.Rect(rect.x + 30, rect.y + 126 + i * 72, rect.w - 60, 66)
        kn = r['id'] in g.recipes
        ui.tile(s, row, (226, 238, 220) if kn else (246, 236, 216), (150, 180, 130) if kn else (196, 170, 140))
        ic = kitchen.dish_icon(r['id'], 1)
        s.blit(ic, ic.get_rect(center=(row.x + 40, row.centery)))
        ui.blit_text(s, r['name'], (row.x + 80, row.y + 8), 'smallb', U.INK)
        needs = ',  '.join(kitchen.need_text(n) for n in r['needs'])
        ui.blit_text(s, '%s.   %s' % (r['effect'], needs), (row.x + 80, row.y + 36), 'tiny', U.SOFT,
                     maxw=row.w - 280)
        if kn:
            ui.blit_text(s, 'In your book', (row.right - 100, row.centery), 'smallb', (80, 130, 70), 'center')
        else:
            g.price_button(s, (row.right - 170, row.y + 12, 150, 42), r['card'], lambda r=r: g.learn_recipe(r),
                           g.coins >= r['card'])
    ui.blit_text(s, 'Minnow Fritters and Perch Chowder are already written in your cupboard.',
                 (rect.centerx, rect.bottom - 26), 'small', U.SOFT, 'center')


def draw_museum(g, s):
    ui = g.ui
    rect = g.big_panel(s, 'Fernwick Aquarium')
    have = set(g.museum)
    basket = {b['id'] for b in g.basket}
    nxt = next(((n, kind, v) for n, kind, v in MUSEUM_REWARDS if len(have) < n), None)
    info = '%d of %d fish on display.' % (len(have), len(FISH))
    if nxt:
        reward = '%d coins' % nxt[2] if nxt[1] == 'coins' else '%d Golden Lures' % nxt[2]
        info += '   At %d, Juniper gives you %s.' % (nxt[0], reward)
    ui.blit_text(s, info, (rect.x + 34, rect.y + 90), 'small', U.SOFT, maxw=rect.w - 68)
    if len(FISH) <= 36:
        tw, th, gap, cols = 100, 104, 8, 9
    else:                                   # more fish than fit: smaller tiles, five rows
        gap = 6
        cols = math.ceil(len(FISH) / 5)
        tw, th = (rect.w - 60) // cols - gap, 84
    x0 = rect.centerx - (cols * (tw + gap) - gap) // 2
    tip = None
    for i, f in enumerate(FISH):
        r = pygame.Rect(x0 + (i % cols) * (tw + gap), rect.y + 122 + (i // cols) * (th + gap), tw, th)
        shown = f['id'] in have
        can = not shown and f['id'] in basket
        hov = r.collidepoint(ui.mouse)
        ui.tile(s, r, (226, 238, 244) if shown else (252, 246, 228) if can else (232, 226, 214),
                RARITY_COLORS[f['rarity']] if shown or can else (190, 180, 168), hov and can)
        spr = art.fish_sprite(f, 2)
        if spr.get_width() > tw - 10:
            k = (tw - 10) / spr.get_width()
            spr = pygame.transform.scale(spr, (int(spr.get_width() * k), int(spr.get_height() * k)))
        if not shown:
            spr = pygame.mask.from_surface(spr, 1).to_surface(
                setcolor=(150, 140, 130, 255) if can else (200, 192, 180, 255), unsetcolor=(0, 0, 0, 0))
        s.blit(spr, spr.get_rect(center=(r.centerx, r.y + th * 0.42)))
        if shown:
            ui.blit_text(s, f['name'], (r.centerx, r.bottom - 22), 'tiny', U.INK, 'center', maxw=r.w - 8)
        elif can:
            ui.blit_text(s, 'Donate', (r.centerx, r.bottom - 22), 'smallb', (60, 120, 80), 'center')
            ui.hotspot(r, lambda fid=f['id']: g.donate(fid))
        else:
            ui.blit_text(s, '?', (r.centerx, r.bottom - 22), 'smallb', (170, 160, 150), 'center')
        if hov:
            tip = f
    if tip:
        ui.blit_text(s, tip['name'] if (tip['id'] in have or tip['id'] in basket or tip['id'] in g.journal)
                     else 'Not yet found', (rect.centerx, rect.bottom - 34), 'smallb', U.INK, 'center')
    else:
        ui.blit_text(s, 'Fish from your basket can be donated. The museum keeps one of each.',
                     (rect.centerx, rect.bottom - 34), 'small', U.SOFT, 'center')


def draw_board(g, s):
    ui = g.ui
    rect = _panel(g, s, 980, 540, 'Notice board')
    jobs = g.town_jobs()
    ui.blit_text(s, 'Odd jobs for the day. New notices go up every morning.', (rect.x + 36, rect.y + 92), 'small',
                 U.SOFT)
    for i, job in enumerate(jobs):
        r = pygame.Rect(rect.x + 30 + i * 312, rect.y + 130, 296, 370)
        tilt = (-1, 1, 0)[i]
        paper = (250, 246, 230) if not job['done'] else (226, 236, 220)
        ui.tile(s, r.move(0, tilt * 4), paper, (196, 170, 140))
        pygame.draw.circle(s, (200, 70, 70), (r.centerx, r.y + 16 + tilt * 4), 7)
        who = FOLK[job['who']]['name']
        y = r.y + 40 + tilt * 4
        ui.blit_text(s, 'From %s' % who, (r.x + 20, y), 'smallb', U.SOFT)
        y += 34
        for line in ui.wrap(job['text'], 'body', r.w - 40):
            ui.blit_text(s, line, (r.x + 20, y), 'body', U.INK)
            y += 28
        ui.blit_text(s, 'Reward: %d coins' % job['reward'], (r.x + 20, r.bottom - 112 + tilt * 4), 'smallb',
                     (150, 110, 40))
        if job['done']:
            ui.blit_text(s, 'Done. Thank you!', (r.centerx, r.bottom - 54 + tilt * 4), 'bodyb', (80, 130, 70), 'center')
        else:
            ok = g.job_ready(job) is not None
            ui.button(s, (r.x + 30, r.bottom - 76 + tilt * 4, r.w - 60, 48), 'Hand in' if ok else 'Not in your basket',
                      lambda j=job: g.hand_in(j), 'primary' if ok else 'normal', enabled=ok)


def draw_hall(g, s):
    ui = g.ui
    tn = g.town
    rect = g.big_panel(s, 'Town Hall')
    for i, (key, label) in enumerate((('town', 'Town projects'), ('home', 'Home upgrades'))):
        ui.button(s, (rect.x + 330 + i * 190, rect.y + 26, 180, 40), label, lambda k=key: setattr(tn, 'hall_tab', k),
                  'tab_on' if tn.hall_tab == key else 'tab')
    home = tn.hall_tab == 'home'
    items = UPGRADES if home else PROJECTS
    owned = g.upgrades if home else g.projects
    rh = 92 if home else 104
    for i, pr in enumerate(items):
        r = pygame.Rect(rect.x + 30, rect.y + 92 + i * (rh + 8), rect.w - 60, rh)
        done = pr['id'] in owned
        ui.tile(s, r, (226, 238, 220) if done else (246, 236, 216), (150, 180, 130) if done else (196, 170, 140))
        ui.blit_text(s, pr['name'], (r.x + 24, r.y + 14), 'bodyb', U.INK)
        ui.blit_text(s, pr['desc'], (r.x + 24, r.y + 48), 'small', U.SOFT, maxw=r.w - 250)
        if done:
            ui.blit_text(s, 'Built!', (r.right - 110, r.centery), 'bodyb', (80, 130, 70), 'center')
        else:
            act = (lambda pr=pr: g.fund_upgrade(pr)) if home else (lambda pr=pr: g.fund_project(pr))
            g.price_button(s, (r.right - 200, r.centery - 24, 170, 48), pr['cost'], act, g.coins >= pr['cost'])
    note = ('"My cousin Birch builds everything in Fernwick. He will have it done by tomorrow, he says."'
            if home else '"Fernwick runs on kindness and the odd coin. The whole street will thank you."')
    ui.blit_text(s, note + '  - Mayor Hazel', (rect.centerx, rect.bottom - 26), 'small', U.SOFT, 'center',
                 maxw=rect.w - 60)


def draw_ringtoss(g, s):
    ui = g.ui
    tn = g.town
    rt = tn.rt
    rect = _panel(g, s, 980, 560, "Pip's Ring Toss")
    # the game, left
    gr = pygame.Rect(rect.x + 30, rect.y + 90, 600, 440)
    pygame.draw.rect(s, (60, 70, 96), gr, border_radius=16)
    pygame.draw.rect(s, (220, 90, 100), (gr.x, gr.y + 300, gr.w, 30))
    for i in range(0, gr.w, 40):
        pygame.draw.rect(s, (250, 240, 230), (gr.x + i, gr.y + 300, 20, 30))
    cx, span = gr.centerx, 240
    by = gr.y + 290
    for i in range(5):
        bx = cx + int((-0.8 + i * 0.4) * span)
        col = (240, 196, 70) if i == 2 else [(110, 180, 120), (110, 160, 210), None, (220, 120, 120), (180, 140, 210)][i]
        pygame.draw.rect(s, col, (bx - 14, by - 60, 28, 60), border_radius=6)
        pygame.draw.rect(s, col, (bx - 5, by - 92, 10, 34))
        pygame.draw.rect(s, (250, 250, 240), (bx - 6, by - 96, 12, 6))
        pygame.draw.rect(s, lighten(col, 0.3), (bx - 9, by - 52, 6, 30))
    for x, hit in rt['marks']:
        mx = cx + int(x * span)
        if hit:
            pygame.draw.ellipse(s, (255, 230, 120), (mx - 13, by - 82, 26, 10), 3)
        else:
            pygame.draw.ellipse(s, (200, 190, 200), (mx - 13, by - 6, 26, 10), 3)
    if rt['fly']:
        x, k = rt['fly']
        mx = cx + int(x * span)
        y0 = gr.bottom - 30
        my = int(y0 + (by - 80 - y0) * k - math.sin(k * math.pi) * 90)
        w = int(34 - 8 * k)
        pygame.draw.ellipse(s, (255, 230, 120), (mx - w // 2, my - 6, w, 12), 4)
    if rt['rings'] > 0 and not rt['fly']:
        mx = cx + int(tn.marker_x() * span)
        ay = by + 48
        pygame.draw.polygon(s, (255, 250, 230), [(mx, ay), (mx - 12, ay + 20), (mx + 12, ay + 20)])
        for yy in range(by - 100, ay - 4, 10):
            pygame.draw.line(s, (200, 200, 220), (mx, yy), (mx, yy + 4), 2)
        for i in range(rt['rings']):
            pygame.draw.ellipse(s, (255, 230, 120), (gr.x + 24 + i * 38, gr.bottom - 34, 28, 12), 3)
        ui.button(s, (gr.right - 170, gr.bottom - 60, 150, 46), 'Throw!', lambda: tn.throw(g), 'gold', font='h3')
    elif not rt['fly']:
        ui.button(s, (gr.centerx - 150, gr.bottom - 66, 300, 52), 'Play  (%d coins, 5 rings)' % TOSS_COST,
                  lambda: tn.start_toss(g), 'primary', enabled=g.coins >= TOSS_COST)
    if rt['msg']:
        msg = rt['msg']
        if ui.pad_layout and msg.startswith('Space or click'):
            msg = '%s to throw!' % ui.pad_label('A')
        ui.blit_text(s, msg, (gr.centerx, gr.y + 40), 'h3', (255, 246, 220), 'center', outline=(40, 30, 40))
    ui.blit_text(s, 'Ring the gold bottle for 3 tickets', (gr.centerx, gr.y + 76), 'small', (220, 220, 236), 'center')
    # prizes, right
    px = rect.x + 660
    ui.blit_text(s, 'Prize counter', (px, rect.y + 96), 'h3', U.INK)
    ui.blit_text(s, 'Your tickets: %d' % g.tickets, (px, rect.y + 130), 'smallb', (150, 110, 40))
    for i, pr in enumerate(PRIZES):
        r = pygame.Rect(px, rect.y + 166 + i * 74, rect.right - 30 - px, 64)
        owned = pr.get('hat') and pr['id'] in g.hats
        ui.tile(s, r, (246, 236, 216), (196, 170, 140))
        if pr.get('hat'):
            ic = art.item_icon('hat_' + pr['id'], 2)
            s.blit(ic, ic.get_rect(center=(r.x + 26, r.centery)))
        ui.blit_text(s, pr['name'], (r.x + 50, r.y + 10), 'smallb', U.INK, maxw=r.w - 60)
        if owned:
            ui.blit_text(s, 'Yours!', (r.x + 50, r.y + 38), 'small', (80, 130, 70))
        else:
            ui.button(s, (r.x + 50, r.y + 32, r.w - 64, 26), '%d tickets' % pr['tickets'], lambda pr=pr: tn.redeem(g, pr),
                      'gold' if g.tickets >= pr['tickets'] else 'normal', enabled=g.tickets >= pr['tickets'],
                      font='small')


def fish_hint(f):
    bits = []
    if f['seasons'] is not None:
        bits.append(' and '.join(SEASONS[x] for x in sorted(f['seasons'])))
    if f['phases']:
        bits.append(', '.join(sorted(f['phases'])))
    if f['weather']:
        bits.append('in %s weather' % ' or '.join(sorted(f['weather'])))
    if f.get('spot'):
        bits.append({'cove': 'Lily Cove', 'deep': 'The Deep', 'creek': 'Willow Creek', 'pot': 'crab pot',
                     'ice': 'through the ice'}.get(f['spot'], f['spot']))
    return f['hint'] + ('  (' + '; '.join(bits) + ')' if bits else '')


def draw_library(g, s):
    ui = g.ui
    tn = g.town
    rect = g.big_panel(s, 'Library: fish notes')
    todo = [f for f in FISH if f['id'] not in g.journal]
    if not todo:
        ui.blit_text(s, "You've caught every fish in the lake. Ms. Alder is writing a book about you.",
                     (rect.centerx, rect.centery), 'bodyb', U.INK, 'center')
        return
    ui.blit_text(s, 'Fish you have not caught yet, and what the old notes say about them.', (rect.x + 34, rect.y + 90),
                 'small', U.SOFT)
    per = 6
    pages = (len(todo) + per - 1) // per
    tn.lib_page = min(tn.lib_page, pages - 1)
    for i, f in enumerate(todo[tn.lib_page * per:(tn.lib_page + 1) * per]):
        r = pygame.Rect(rect.x + 30 + (i % 2) * 496, rect.y + 124 + (i // 2) * 146, 480, 136)
        ui.tile(s, r, (246, 238, 220), RARITY_COLORS[f['rarity']])
        spr = art.fish_sprite(f, 2)
        spr = pygame.mask.from_surface(spr, 1).to_surface(setcolor=(120, 110, 100, 255), unsetcolor=(0, 0, 0, 0))
        if spr.get_width() > 110:
            k = 110 / spr.get_width()
            spr = pygame.transform.scale(spr, (110, int(spr.get_height() * k)))
        s.blit(spr, spr.get_rect(center=(r.x + 66, r.centery)))
        ui.blit_text(s, f['name'], (r.x + 132, r.y + 14), 'bodyb', U.INK, maxw=r.w - 150)
        y = r.y + 46
        for line in ui.wrap(fish_hint(f), 'small', r.w - 150)[:4]:
            ui.blit_text(s, line, (r.x + 132, y), 'small', U.SOFT)
            y += 22
    ui.button(s, (rect.centerx - 200, rect.bottom - 64, 100, 44), '<', lambda: setattr(tn, 'lib_page', tn.lib_page - 1),
              enabled=tn.lib_page > 0, font='h3')
    ui.blit_text(s, 'Page %d of %d' % (tn.lib_page + 1, pages), (rect.centerx, rect.bottom - 42), 'smallb', U.INK,
                 'center')
    ui.button(s, (rect.centerx + 100, rect.bottom - 64, 100, 44), '>', lambda: setattr(tn, 'lib_page', tn.lib_page + 1),
              enabled=tn.lib_page < pages - 1, font='h3')


def draw_talk(g, s):
    ui = g.ui
    tn = g.town
    k = tn.talk_to
    if k is None:
        g.overlay = None
        return
    spec = FOLK[k]
    rect = _panel(g, s, 820, 480, spec['name'])
    pv = pygame.Rect(rect.x + 30, rect.y + 86, 200, 230)
    pygame.draw.rect(s, (226, 236, 240), pv, border_radius=14)
    pygame.draw.rect(s, (196, 170, 140), pv, 3, border_radius=14)
    portrait(g, s, k, (pv.centerx, pv.centery + 10), 4)
    pts = g.friends.get(k, 0)
    hearts(s, rect.x + 270, rect.y + 104, pts // 10)
    ui.blit_text(s, 'Friendship', (rect.x + 260, rect.y + 120), 'tiny', U.SOFT)
    if not tn.gift_mode:
        y = rect.y + 160
        for line in ui.wrap('"%s"' % tn.reply, 'body', rect.w - 300):
            ui.blit_text(s, line, (rect.x + 260, y), 'body', U.INK)
            y += 30
        dish = kitchen.RECIPE_BY_ID[kitchen.FAVOURITE_DISH[k]]
        ui.blit_text(s, 'Loves: %s     Favourite dish: %s' % (
            FISH_BY_ID[spec['loves']]['name'] if spec['loves'] in g.journal else '???',
            dish['name'] if kitchen.known(g, dish) else '???'),
            (rect.x + 260, rect.bottom - 128), 'small', U.SOFT, maxw=rect.w - 290)
        gave = g.town_day.get('gifted', {}).get(k) == g.day
        has = bool(g.basket) or any(n > 0 for n in g.pantry.values())
        ui.button(s, (rect.x + 260, rect.bottom - 90, 240, 52), 'Gave a gift today' if gave else 'Give a gift',
                  lambda: setattr(tn, 'gift_mode', True), 'primary', enabled=has and not gave, nav=True)
        ui.button(s, (rect.right - 220, rect.bottom - 90, 190, 52), 'Goodbye', g.close_overlay, nav=True)
        if not has and not gave:
            ui.blit_text(s, 'Your basket is empty.', (rect.x + 380, rect.bottom - 26), 'small', U.SOFT, 'center')
        return
    ui.blit_text(s, 'What would you like to give?', (rect.x + 260, rect.y + 150), 'bodyb', U.INK)
    stacks = {}
    for b in g.basket:
        stacks[b['id']] = stacks.get(b['id'], 0) + 1
    tw, th = 120, 100
    dishes = [(rid, n) for rid, n in sorted(g.pantry.items()) if n > 0 and rid in kitchen.RECIPE_BY_ID]
    for i, (rid, n) in enumerate(dishes[:4]):
        r = pygame.Rect(rect.x + 260 + (i % 4) * (tw + 8), rect.y + 186, tw, th)
        hov = r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 248, 236) if hov else (246, 236, 216), (220, 150, 120), hov)
        ic = kitchen.dish_icon(rid, 2)
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 38)))
        ui.blit_text(s, kitchen.RECIPE_BY_ID[rid]['name'], (r.centerx, r.bottom - 22), 'tiny', U.INK, 'center',
                     maxw=r.w - 8)
        if n > 1:
            ui.blit_text(s, 'x%d' % n, (r.right - 8, r.y + 6), 'smallb', U.SOFT, 'topright')
        ui.hotspot(r, lambda rid=rid: tn.give_dish(g, rid))
    skip = 4 if dishes else 0
    for i, (fid, n) in enumerate(list(stacks.items())[:8 - skip]):
        i += skip
        r = pygame.Rect(rect.x + 260 + (i % 4) * (tw + 8), rect.y + 186 + (i // 4) * (th + 8), tw, th)
        hov = r.collidepoint(ui.mouse)
        spec_f = ALL_BY_ID[fid]
        ui.tile(s, r, (252, 248, 236) if hov else (240, 230, 210), RARITY_COLORS[spec_f['rarity']], hov)
        spr = art.fish_sprite(spec_f, 2)
        if spr.get_width() > tw - 14:
            kk = (tw - 14) / spr.get_width()
            spr = pygame.transform.scale(spr, (int(spr.get_width() * kk), int(spr.get_height() * kk)))
        s.blit(spr, spr.get_rect(center=(r.centerx, r.y + 38)))
        ui.blit_text(s, spec_f['name'], (r.centerx, r.bottom - 22), 'tiny', U.INK, 'center', maxw=r.w - 8)
        if n > 1:
            ui.blit_text(s, 'x%d' % n, (r.right - 8, r.y + 6), 'smallb', U.SOFT, 'topright')
        ui.hotspot(r, lambda fid=fid: tn.give(g, fid))
    ui.button(s, (rect.right - 220, rect.bottom - 70, 190, 46), 'Never mind', lambda: setattr(tn, 'gift_mode', False))


# ---------------------------------------------------------------- the notice board's odd jobs
JOB_TEXT = {
    'species': ["Could somebody bring me a {fish}? I'd like to sketch one up close.",
                "Looking for one {fish}, any size at all. It's for a family recipe.",
                "I promised to show a {fish} to the children at school. Help!"],
    'big': ["Wanted: a {fish} of at least {min} cm. There is a friendly bet riding on it.",
            "Seeking a proper big {fish}, {min} cm or more, for the aquarium's measuring wall."],
    'any': ["Any {n} fish, please! The market stall is looking very empty today.",
            "The cats of Fernwick are hungry. {n} fish of any kind would do nicely."],
    'junk': ["Help keep the lake tidy! Bring in an old boot, a tin can or some driftwood.",
             "I'm building a junk sculpture for the square. One boot, can or bit of driftwood, please!"],
}
JUNK_JOB = ('boot', 'can', 'driftwood')


def make_jobs(g):
    rng = random.Random(g.day * 7919 + 17)
    season = g.season_of(g.day)
    pool = [f for f in FISH if f['rarity'] <= 2 and not f.get('event') and not f.get('method')
            and (f['seasons'] is None or season in f['seasons'])
            and (f['spot'] is None or f['spot'] in g.visited)]
    kinds = ['species', 'big', 'any', 'junk']
    rng.shuffle(kinds)
    import seasons
    who = rng.sample([k for k in FOLK_ORDER if FOLK[k].get('new_in_year', 0) <= seasons.year(g)], 3)
    out = []
    for kind, k in zip(kinds[:3], who):
        job = dict(kind=kind, who=k, done=False)
        if kind in ('species', 'big'):
            f = rng.choice(pool)
            job['fish'] = f['id']
            lo, hi = f['size']
            job['min'] = int(lo + (hi - lo) * 0.6)
            job['reward'] = int(round((f['price'] * (3 if kind == 'big' else 2) + (40 if kind == 'big' else 20))
                                      / 5.0)) * 5
            job['text'] = rng.choice(JOB_TEXT[kind]).format(fish=f['name'], min=job['min'])
        elif kind == 'any':
            job['n'] = rng.randint(3, 5)
            job['reward'] = job['n'] * 18
            job['text'] = rng.choice(JOB_TEXT[kind]).format(n=job['n'])
        else:
            job['reward'] = 35
            job['text'] = rng.choice(JOB_TEXT[kind])
        out.append(job)
    return out


def job_items(g, job):
    """The basket items a notice would take, or None if you don't have them yet."""
    b = g.basket
    kind = job['kind']
    if kind == 'species':
        c = [x for x in b if x['id'] == job['fish']]
        return [min(c, key=lambda x: x['price'])] if c else None
    if kind == 'big':
        c = [x for x in b if x['id'] == job['fish'] and x['size'] >= job['min']]
        return [min(c, key=lambda x: x['size'])] if c else None
    if kind == 'any':
        c = sorted((x for x in b if not ALL_BY_ID[x['id']].get('junk')), key=lambda x: x['price'])
        return c[:job['n']] if len(c) >= job['n'] else None
    c = [x for x in b if x['id'] in JUNK_JOB]
    return c[:1] or None


def signpost_icon(s, c, back=False):
    """Toolbar icon: a little wooden signpost (arrows flipped for the way home)."""
    x, y = c
    pygame.draw.rect(s, (120, 86, 60), (x - 2, y - 14, 4, 30))
    d = -1 if back else 1
    for dy, dd, col in ((-12, d, (206, 160, 104)), (2, -d, (186, 136, 90))):
        x0, x1 = x - 14, x + 14
        if dd > 0:
            pts = [(x0, y + dy), (x1 - 6, y + dy), (x1, y + dy + 5), (x1 - 6, y + dy + 10), (x0, y + dy + 10)]
        else:
            pts = [(x1, y + dy), (x0 + 6, y + dy), (x0, y + dy + 5), (x0 + 6, y + dy + 10), (x1, y + dy + 10)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.polygon(s, (110, 76, 50), pts, 2)
