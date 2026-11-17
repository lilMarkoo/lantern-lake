"""Saltmarsh harbour: the little village up the steps from the pier (2.0).

A quay you walk along like Fernwick's street: Morwen's harbour office and its board of orders and tides, Nell's fish
stall, the Gull & Lantern inn, Ossian's boatyard, Sol's cottage and the dark old lighthouse, then a beach to comb.
The tide rises and falls against the quay wall while you walk, and once the lighthouse is lit its beam sweeps the
sky after dark.

Runs under Game.overlay 'harbour' with Game.aqscene (the same slot as the aquarium hall, since you can only be in
one of them), drawn and framed like the ice-fishing scene. The rules live in coast.py.
"""
import math
import random

import pygame

import actors
import art
import coast
import town as T
import ui as U
from art import W, H, HORIZON, lerp_c, darken, lighten, add_glow
from data import FISH_BY_ID, RARITY_COLORS

HB_W = 1600
FLOOR = T.GROUND                 # feet on the quay (the same height as Fernwick's pavement)
WALK = 62.0
STEPS_X = 44
BOARD_X = 318
OFFICE = (150, 290)
STALL_X = 432
INN = (526, 746)
INN_X = 636
YARD = (790, 990)
YARD_X = 870
COTTAGE = (1036, 1130)
COTTAGE_X = 1083
LIGHT_X = 1214
BEACH_X0 = 1272
INN_HOURS = (660, 1380)
HEADLESS = False                 # set by main at start-up, with its clock formatter
fmt_clock = str
HOME = {'morwen': 262, 'nell': STALL_X, 'ossian': 852, 'sol': 1182, 'kit': 1420}
BOAT_X = 872                     # Ossian's new boat, on the trestles in the shed
INN_FOLK = (dict(name='Bram', shirt=(150, 60, 56), hair=(90, 60, 40), hat='beanie'),
            dict(name='Old Tam', shirt=(70, 80, 110), hair=(206, 206, 210), hat='captain'))


def folk_here(g, k):
    m = g.minute
    if k == 'sol':
        return True                                  # the keeper is always somewhere about the lighthouse
    if k == 'kit':
        return 480 <= m < 1080
    return coast.OPEN_H <= m < coast.CLOSE_H


def enter(g):
    g.aqscene = HarbourScene(g)
    g.overlay = 'harbour'
    g.release_holds()
    g.fishing.reset()
    g.audio.play('creak', 0.4)
    st = g.coast
    st['visits'] += 1
    if st['visits'] == 1:
        g.toast('Welcome to Saltmarsh! Walk with A and D, and press E at a door or a neighbour.', (90, 140, 180))


# ---------------------------------------------------------------- static art
_STATIC = {}


def _vols():
    G = FLOOR
    v = []

    def add(poly, depth, wall, roof, tex='courses'):
        v.append(dict(poly=poly, depth=depth, wall=wall, roof=roof, tex=tex))
    add(T._rect(150, G - 70, 290, G - 4), 26, (100, 130, 160), (70, 80, 100), 'planks')
    add([(144, G - 70), (220, G - 102), (296, G - 70)], 26, (100, 130, 160), (70, 80, 100), 'tiles')
    add(T._rect(384, G - 56, 484, G - 4), 16, (222, 212, 192), (150, 140, 130), 'planks')
    add(T._rect(526, G - 108, 746, G - 4), 30, (236, 232, 220), (66, 66, 78))
    add([(520, G - 108), (636, G - 142), (752, G - 108)], 30, (236, 232, 220), (66, 66, 78), 'tiles')
    add(T._rect(700, G - 156, 714, G - 126), 8, (150, 140, 130), (120, 112, 104), 'bricks')
    add(T._rect(790, G - 84, 990, G - 4), 34, (150, 112, 80), (128, 144, 152), 'planks')
    add([(784, G - 84), (890, G - 118), (996, G - 84)], 34, (150, 112, 80), (128, 144, 152), 'ribs')
    add(T._rect(1036, G - 52, 1130, G - 4), 20, (196, 190, 180), (204, 170, 98), 'bricks')
    add([(1027, G - 52), (1077, G - 80), (1089, G - 80), (1139, G - 52)], 22, (196, 190, 180), (204, 170, 98),
        'straw')
    return T.finish_volumes(v)


VOLUMES = _vols()


def _cobbles(s, x0, x1, top, bot, col, rng):
    s.fill(col, (x0, top, x1 - x0, bot - top))
    for y in range(top + 2, bot, 4):
        off = (y // 4 % 2) * 3
        for x in range(x0 + off, x1, 6):
            s.fill(darken(col, rng.uniform(0.05, 0.16)), (x, y, 5, 3))
            s.set_at((x, y), lighten(col, 0.08))


def build(season):
    """The quay, the buildings' fronts, the lighthouse and the beach (everything that doesn't move)."""
    key = ('street', season)
    if key in _STATIC:
        return _STATIC[key]
    G = FLOOR
    snow = season == 3
    rng = random.Random(51 + season)
    s = pygame.Surface((HB_W, H), pygame.SRCALPHA)
    wins, lamps = [], []
    # the quay: cobbles, a granite edge, and the wall dropping into the water
    stone = [(176, 170, 160), (180, 174, 162), (170, 164, 156), (204, 208, 218)][season]
    _cobbles(s, 0, BEACH_X0, G - 6, G + 9, stone, rng)
    s.fill(darken(stone, 0.08), (0, G + 9, BEACH_X0, 3))
    wall = (130, 124, 116)
    s.fill(wall, (0, G + 12, BEACH_X0, H - G - 12))
    for j, y in enumerate(range(G + 12, H, 7)):
        s.fill(darken(wall, 0.18), (0, y, BEACH_X0, 1))
        for x in range((j % 2) * 9, BEACH_X0, 18):
            s.fill(darken(wall, 0.18), (x, y, 1, 7))
            s.fill(lighten(wall, rng.uniform(0.0, 0.1)), (x + 2, y + 2, rng.randrange(4, 12), 2))
    for x in range(30, BEACH_X0, 140):                       # iron mooring rings and bollards
        s.fill((60, 56, 58), (x, G - 6, 6, 7))
        s.fill((84, 80, 84), (x - 1, G - 7, 8, 2))
        pygame.draw.circle(s, (70, 66, 70), (x + 60, G + 20), 3, 1)
    # the pier steps down to your boat
    for i in range(6):
        s.fill(darken((150, 112, 80), i * 0.04), (STEPS_X - 18 + i * 2, G + 8 + i * 6, 36 - i * 4, 4))
        s.fill(darken((150, 112, 80), 0.35), (STEPS_X - 18 + i * 2, G + 12 + i * 6, 36 - i * 4, 2))
    s.fill((96, 70, 50), (STEPS_X - 22, G - 26, 3, 34))
    s.fill((96, 70, 50), (STEPS_X + 19, G - 26, 3, 34))
    s.fill((120, 90, 64), (STEPS_X - 22, G - 27, 44, 3))
    T._sign(s, STEPS_X, G - 40, 'TO THE BOATS', (236, 226, 200), (70, 60, 50), 64)
    # ---- the harbour office
    x0, x1 = OFFICE
    T._planks(s, pygame.Rect(x0, G - 70, x1 - x0, 66), (100, 130, 160), (82, 108, 136))
    T._gable(s, x0, x1, G - 70, 32, (70, 80, 100), (50, 56, 70), snow)
    T._door(s, 220, 16, 30, (60, 80, 110), (230, 226, 214))
    T._window(s, 170, G - 54, 20, 18, (230, 226, 214), wins)
    T._window(s, 252, G - 54, 20, 18, (230, 226, 214), wins)
    T._sign(s, 220, G - 66, 'HARBOURMASTER', (236, 226, 200), (40, 60, 90), 80)
    pygame.draw.circle(s, (240, 236, 220), (220, G - 84), 5)    # a round window in the gable
    pygame.draw.circle(s, (50, 56, 70), (220, G - 84), 5, 1)
    T._grounded(s, x0, x1, G - 70)
    s.fill((200, 200, 204), (300, G - 120, 2, 116))             # the flagpole
    s.fill((236, 200, 90), (299, G - 122, 4, 3))
    # the harbour board: orders and the tide table
    s.fill((96, 70, 50), (BOARD_X - 16, G - 40, 3, 36))
    s.fill((96, 70, 50), (BOARD_X + 13, G - 40, 3, 36))
    s.fill((120, 90, 64), (BOARD_X - 18, G - 48, 36, 26))
    s.fill((150, 116, 84), (BOARD_X - 16, G - 46, 32, 22))
    for i, c in enumerate(((246, 240, 220), (236, 226, 196), (246, 240, 220))):
        s.fill(c, (BOARD_X - 13 + i * 10, G - 43, 8, 9 + i % 2 * 3))
    pygame.draw.polygon(s, (60, 66, 80), [(BOARD_X - 21, G - 48), (BOARD_X, G - 56), (BOARD_X + 21, G - 48)])
    # ---- Nell's fish stall (the counter is drawn live, in front of Nell)
    T._planks(s, pygame.Rect(384, G - 56, 100, 52), (222, 212, 192), (196, 184, 162))
    s.fill((60, 70, 90), (400, G - 46, 68, 22))                 # the dark of the shed behind the counter
    for i in range(5):                                          # crates and a hanging scale
        s.fill((150, 110, 80), (402 + i * 13, G - 30, 11, 6))
    pygame.draw.line(s, (180, 180, 186), (452, G - 46), (452, G - 38))
    s.fill((200, 200, 206), (447, G - 38, 10, 3))
    T._grounded(s, 384, 484)
    # ---- the Gull & Lantern
    x0, x1 = INN
    s.fill((236, 232, 220), (x0, G - 108, x1 - x0, 104))
    for y in range(G - 104, G - 4, 6):
        s.fill((226, 222, 210), (x0, y, x1 - x0, 1))
    s.fill((60, 56, 64), (x0, G - 22, x1 - x0, 18))              # a tarred plinth
    T._gable(s, x0, x1, G - 108, 34, (66, 66, 78), (44, 44, 54), snow)
    s.fill((150, 140, 130), (700, G - 156, 14, 34))
    s.fill((120, 112, 104), (698, G - 158, 18, 3))
    for wx in (546, 588, 676, 718):
        T._window(s, wx - 8, G - 92, 16, 18, (90, 70, 56), wins, (60, 90, 110))
    for wx in (556, 716):                                       # bay windows below
        s.fill((90, 70, 56), (wx - 16, G - 56, 32, 32))
        T._window(s, wx - 13, G - 52, 26, 22, (90, 70, 56), wins)
        s.fill((66, 66, 78), (wx - 18, G - 60, 36, 4))
    T._door(s, INN_X, 20, 34, (110, 50, 46), (90, 70, 56))
    T._sign(s, INN_X, G - 70, 'GULL & LANTERN', (40, 50, 70), (240, 220, 160), 84)
    lamps.append((INN_X - 18, G - 46))
    lamps.append((INN_X + 18, G - 46))
    for lx in (INN_X - 18, INN_X + 18):
        s.fill((40, 36, 40), (lx - 2, G - 50, 5, 8))
        s.fill((250, 220, 150), (lx - 1, G - 49, 3, 5))
    for i in range(3):                                          # barrels by the door
        bx = 600 + i * 9 if i < 2 else 668
        s.fill((120, 80, 52), (bx - 4, G - 16, 9, 12))
        s.fill((90, 60, 40), (bx - 4, G - 12, 9, 1))
    T._grounded(s, x0, x1, G - 108)
    # ---- Ossian's boatyard: a big open shed, a boat on trestles and the slipway
    x0, x1 = YARD
    T._planks(s, pygame.Rect(x0, G - 84, x1 - x0, 80), (150, 112, 80), (126, 92, 64), 5)
    T._tin_roof(s, x0, x1, G - 84, 34, snow, rng)
    s.fill((44, 36, 34), (812, G - 66, 120, 62))                # the open doors and the dark inside
    s.fill((126, 92, 64), (806, G - 70, 6, 66))
    s.fill((126, 92, 64), (932, G - 70, 6, 66))
    pygame.draw.polygon(s, (120, 70, 50), [(826, G - 34), (918, G - 34), (904, G - 18), (840, G - 18)])  # a hull
    pygame.draw.line(s, (160, 100, 70), (828, G - 32), (916, G - 32), 2)
    T._sign(s, 890, G - 78, 'BOATYARD', (236, 226, 200), (90, 60, 40), 60)
    for wx in (960,):
        T._window(s, wx, G - 60, 16, 16, (100, 76, 54), wins)
    s.fill((96, 70, 50), (944, G - 22, 40, 4))                  # a sawhorse and planks
    s.fill((96, 70, 50), (948, G - 18, 2, 14))
    s.fill((96, 70, 50), (978, G - 18, 2, 14))
    T._grounded(s, x0, x1, G - 84)
    # the slipway down into the water
    pygame.draw.polygon(s, (150, 140, 128), [(996, G + 9), (1030, G + 9), (1046, H), (1004, H)])
    for y in range(G + 12, H, 5):
        pygame.draw.line(s, (120, 112, 104), (996 + (y - G) * 0.2, y), (1030 + (y - G) * 0.4, y))
    # ---- Sol's cottage
    x0, x1 = COTTAGE
    T._bricks(s, pygame.Rect(x0, G - 52, x1 - x0, 48), (196, 190, 180), (170, 164, 154), 5, 11)
    T._thatch(s, x0, x1, G - 52, 28, snow, rng)
    T._door(s, COTTAGE_X, 14, 26, (60, 110, 100), (150, 140, 130))
    T._window(s, 1048, G - 40, 14, 14, (240, 236, 226), wins)
    T._window(s, 1104, G - 40, 14, 14, (240, 236, 226), wins)
    s.fill((150, 100, 70), (1120, G - 14, 8, 10))               # lobster pots stacked by the wall
    s.fill((150, 100, 70), (1124, G - 22, 8, 8))
    for xx in range(1120, 1132, 3):
        s.fill((110, 70, 50), (xx, G - 22, 1, 18))
    T._grounded(s, x0, x1, G - 52)
    # ---- the lighthouse, on a rocky spur at the end of the quay
    for i, (rx, rw, rh) in enumerate(((1172, 30, 20), (1196, 40, 26), (1232, 30, 18), (1252, 22, 12))):
        pygame.draw.ellipse(s, (120, 114, 108), (rx, G - rh + 6, rw, rh + 12))
        pygame.draw.ellipse(s, (146, 140, 132), (rx + 3, G - rh + 7, rw - 10, rh // 2))
    top, bot = 104, G - 14
    for y in range(top, bot):
        k = (y - top) / (bot - top)
        half = 15 + 9 * k
        band = ((y - top) // 22) % 2
        col = (238, 234, 226) if not band else (196, 70, 64)
        col = lerp_c(col, darken(col, 0.25), 0.0)
        x0 = int(LIGHT_X - half)
        s.fill(col, (x0, y, LIGHT_X - x0, 1))
        s.fill(darken(col, 0.18), (LIGHT_X, y, int(half), 1))
    s.fill((60, 60, 70), (LIGHT_X - 20, top - 4, 40, 5))         # the gallery and its railing
    for xx in range(LIGHT_X - 20, LIGHT_X + 21, 4):
        s.fill((60, 60, 70), (xx, top - 12, 1, 8))
    s.fill((60, 60, 70), (LIGHT_X - 20, top - 12, 41, 1))
    s.fill((40, 44, 52), (LIGHT_X - 12, top - 30, 24, 26))       # the lamp room (glass drawn live)
    pygame.draw.polygon(s, (60, 60, 70), [(LIGHT_X - 15, top - 30), (LIGHT_X, top - 44), (LIGHT_X + 15, top - 30)])
    s.fill((60, 60, 70), (LIGHT_X - 1, top - 50, 2, 7))
    for wy in (150, 200):
        s.fill((40, 44, 52), (LIGHT_X - 4, wy, 7, 10))
    s.fill((60, 60, 70), (LIGHT_X - 9, bot - 22, 18, 22))
    s.fill((96, 70, 50), (LIGHT_X - 7, bot - 20, 14, 20))
    # ---- the beach: dunes and marram grass, a striped hut and an upturned boat
    sand = [(232, 214, 168), (238, 218, 166), (220, 200, 156), (224, 222, 220)][season]
    pygame.draw.polygon(s, sand, [(BEACH_X0 - 6, G - 6), (BEACH_X0 + 20, G - 12), (HB_W, G - 14), (HB_W, H),
                                  (BEACH_X0 - 20, H)])
    for _ in range(500):
        x, y = rng.randrange(BEACH_X0, HB_W), rng.randrange(G - 10, H)
        s.set_at((x, y), darken(sand, rng.uniform(0.03, 0.12)))
    for i in range(5):
        dx = BEACH_X0 + 40 + i * 64
        pygame.draw.ellipse(s, darken(sand, 0.06), (dx, G - 30, 70, 30))
        grass = (120, 150, 90) if season < 2 else (170, 150, 100) if season == 2 else (200, 206, 210)
        for j in range(9):
            gx = dx + 12 + j * 5
            pygame.draw.line(s, grass, (gx, G - 18), (gx + rng.randint(-4, 4), G - 30 - rng.randrange(8)), 1)
    hx = 1458
    s.fill((240, 236, 226), (hx, G - 40, 30, 34))
    for xx in range(hx, hx + 30, 6):
        s.fill((80, 140, 190), (xx, G - 40, 3, 34))
    pygame.draw.polygon(s, (200, 80, 70), [(hx - 3, G - 40), (hx + 15, G - 52), (hx + 33, G - 40)])
    s.fill((90, 70, 56), (hx + 10, G - 24, 10, 18))
    pygame.draw.ellipse(s, (70, 110, 140), (1530, G - 14, 40, 14))
    pygame.draw.ellipse(s, (90, 130, 160), (1532, G - 14, 36, 6))
    # lamp posts along the quay
    for lx in (106, 494, 772, 1010, 1160):
        s.fill((50, 50, 56), (lx - 1, G - 50, 3, 46))
        s.fill((50, 50, 56), (lx - 4, G - 6, 9, 3))
        s.fill((50, 50, 56), (lx - 4, G - 56, 9, 6))
        s.fill((236, 220, 170), (lx - 3, G - 55, 7, 4))
        lamps.append((lx, G - 53))
    _STATIC[key] = (s, wins, lamps)
    return _STATIC[key]


def build_back(season):
    """The far headland and hills, and a couple of islands out at sea (the sea itself is drawn live)."""
    key = ('back', season)
    if key in _STATIC:
        return _STATIC[key]
    bw = W + (HB_W - W) // 3
    s = pygame.Surface((bw, H), pygame.SRCALPHA)
    hill = [(130, 170, 150), (120, 164, 130), (176, 150, 120), (206, 214, 228)][season]
    pts = T._ridge(300, HORIZON + 6, [(52, 0.012), (14, 0.05)], 5)
    end = pts[-1][1]
    tail = [(300 + i * 12, end + (HORIZON + 4 - end) * (1 - math.cos(i / 10 * math.pi)) / 2) for i in range(1, 11)]
    pygame.draw.polygon(s, hill, [(0, H)] + pts + tail + [(420, H)])
    pygame.draw.polygon(s, darken(hill, 0.1), [(0, H), (0, HORIZON + 20), (90, HORIZON + 10), (200, HORIZON + 40),
                                               (260, H)])
    for i in range(10):                                         # cottages on the hillside
        hx = 30 + i * 22 + (i % 3) * 5
        hy = HORIZON + 30 + (i % 4) * 8
        s.fill((236, 230, 214), (hx, hy, 9, 6))
        pygame.draw.polygon(s, (150, 90, 80) if i % 2 else (90, 96, 116), [(hx - 1, hy), (hx + 4, hy - 4), (hx + 10, hy)])
    far_isle = lerp_c(hill, (170, 190, 210), 0.6)
    pygame.draw.ellipse(s, far_isle, (bw - 260, HORIZON - 8, 120, 18))
    pygame.draw.ellipse(s, far_isle, (bw - 120, HORIZON - 5, 60, 12))
    s.fill((0, 0, 0, 0), (bw - 270, HORIZON + 1, 240, 12))
    _STATIC[key] = s
    return s


# ---------------------------------------------------------------- shells, for the beach and Kit's collection
def shell_icon(s, sid, c, k=1):
    x, y = c
    sh = coast.SHELL_BY_ID.get(sid)
    col = sh['col'] if sh else (200, 200, 200)
    d = darken(col, 0.3)
    if sid == 'starfish':
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = (5 if i % 2 == 0 else 2) * k
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        pygame.draw.polygon(s, col, pts)
    elif sid == 'sanddollar':
        pygame.draw.circle(s, col, (x, y), 4 * k)
        for i in range(5):
            a = -math.pi / 2 + i * 2 * math.pi / 5
            s.fill(d, (int(x + math.cos(a) * 2 * k), int(y + math.sin(a) * 2 * k), max(1, k), max(1, k)))
    elif sid == 'razor':
        s.fill(col, (x - 5 * k, y - k, 10 * k, 2 * k))
        s.fill(d, (x - 5 * k, y + k, 10 * k, max(1, k // 2)))
    elif sid in ('periwinkle', 'conch'):
        pygame.draw.circle(s, col, (x, y), 3 * k)
        pygame.draw.polygon(s, col, [(x + 2 * k, y - 2 * k), (x + 6 * k, y), (x + 2 * k, y + 2 * k)])
        pygame.draw.circle(s, d, (x - k, y), k)
    elif sid == 'cowrie':
        pygame.draw.ellipse(s, col, (x - 4 * k, y - 3 * k, 8 * k, 6 * k))
        for i in range(3):
            s.fill(d, (x - 2 * k + i * 2 * k, y - 2 * k, max(1, k), max(1, k)))
        s.fill(lighten(col, 0.3), (x - 3 * k, y, 6 * k, max(1, k // 2)))
    else:                                                       # cockle and scallop: a fan
        pygame.draw.polygon(s, col, [(x - 4 * k, y + 2 * k), (x, y - 4 * k), (x + 4 * k, y + 2 * k)])
        pygame.draw.circle(s, col, (x, y + k), 4 * k, draw_top_left=False, draw_top_right=False)
        for i in (-2, 0, 2):
            pygame.draw.line(s, d, (x, y - 3 * k), (x + i * k, y + 3 * k))


# ---------------------------------------------------------------- the scene
class HarbourScene:
    kind = 'harbour'

    def __init__(self, g, rng=None):
        self.g = g
        self.rng = rng or random.Random()
        self.t = 0.0
        self.x = STEPS_X + 26.0
        self.face = 1
        self.step = 0.0
        self.target = None
        self.on_arrive = None
        self.scroll = 0.0
        self.panel = None               # None, or 'morwen', 'nell', 'inn', 'ossian', 'sol', 'kit'
        self.line = ''
        self.fx = []
        self.done = False
        self.holds = set()
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self.smoke = []
        self.kit = dict(x=float(HOME['kit']), goal=None, wait=2.0, face=1, step=0.0)
        self.gulls = [dict(x=self.rng.uniform(0, HB_W), y=self.rng.uniform(40, 140), vx=self.rng.choice((-1, 1)) *
                           self.rng.uniform(14, 26), ph=self.rng.uniform(0, 6)) for _ in range(4)]
        self.said = 0.0
        self.talk = None                # the fishermen's conversations at the inn (made when you go in)
        self.talk_t0 = 0.0
        self.glows = (art.glow(46, (255, 186, 104)), art.glow(18, (255, 186, 104)), art.glow(60, (255, 236, 170)))

    # ------------------------------------------------------------ what's in reach
    def nearest(self):
        g = self.g
        x = self.x
        if abs(x - STEPS_X) < 22:
            return ('steps', None)
        if abs(x - BOARD_X) < 16:
            return ('board', None)
        if folk_here(g, 'kit') and abs(self.kit['x'] - x) < 14:
            return ('folk', 'kit')
        for item in g.coast['beach']:
            if abs(item['x'] - x) < 9:
                return ('item', item)
        if abs(x - LIGHT_X) < 28 or abs(x - HOME['sol']) < 12:
            return ('folk', 'sol')
        if abs(x - INN_X) < 20:
            return ('inn', None)
        if abs(x - STALL_X) < 34:
            return ('folk', 'nell') if folk_here(g, 'nell') else ('closed', 'nell')
        if abs(x - YARD_X) < 50:
            return ('folk', 'ossian') if folk_here(g, 'ossian') else ('closed', 'ossian')
        if abs(x - HOME['morwen']) < 30:
            return ('folk', 'morwen') if folk_here(g, 'morwen') else ('closed', 'morwen')
        if abs(x - COTTAGE_X) < 12:
            return ('cottage', None)
        return None

    def prompt(self):
        n = self.nearest()
        if not n:
            return None
        kind, v = n
        g = self.g
        if kind == 'steps':
            return 'Back down to your boat'
        if kind == 'board':
            return 'Read the harbour board'
        if kind == 'folk':
            f = coast.FOLK[v]
            return {'nell': "Nell's Fish Stall", 'ossian': "Ossian's Boatyard",
                    'sol': 'The lighthouse  (Sol)'}.get(v, 'Talk to %s' % f['name'])
        if kind == 'item':
            return 'Pick up the %s' % ('sea glass' if v['kind'] == 'glass' else coast.SHELL_BY_ID[v['id']]['name'])
        if kind == 'inn':
            if not (INN_HOURS[0] <= g.minute < INN_HOURS[1]):
                return 'The Gull & Lantern  (opens %s)' % T.fmt_hour(INN_HOURS[0])
            return 'The Gull & Lantern'
        if kind == 'closed':
            return {'nell': "Nell's stall  (opens 7 AM)", 'ossian': 'The boatyard  (opens 7 AM)',
                    'morwen': 'The harbour office  (opens 7 AM)'}[v]
        if kind == 'cottage':
            return "Sol's cottage  (Sol is at the lighthouse)"
        return None

    def interact(self):
        n = self.nearest()
        if not n:
            return
        kind, v = n
        g = self.g
        if kind == 'steps':
            self.leave()
        elif kind == 'board':
            self.open('board')
        elif kind == 'folk':
            self.open(v)
        elif kind == 'item':
            coast.pick_up(g, v)
            for _ in range(10):
                self.fx.append([v['x'], FLOOR + 4, self.rng.uniform(-14, 14), self.rng.uniform(-30, -10), 0.7,
                                (255, 240, 200)])
            g.check_badges()
        elif kind == 'inn':
            if INN_HOURS[0] <= g.minute < INN_HOURS[1]:
                self.open('inn')
            else:
                g.toast('The Gull & Lantern is shut. A cat watches you from the window.', (110, 130, 160))
        elif kind == 'closed':
            g.toast('Closed for now. The harbour folk keep 7 AM to 8 PM.', (110, 130, 160))
        elif kind == 'cottage':
            g.toast('Nobody home. A kettle sits on the stove, waiting for Sol.', (110, 130, 160))

    def open(self, panel):
        g = self.g
        self.panel = panel
        self.line = ''
        if panel == 'inn':
            self.talk = self.inn_talk()
            self.talk_t0 = self.t
        k = 'morwen' if panel == 'board' else panel
        if k in coast.FOLK and (panel != 'board' or folk_here(g, 'morwen')):
            if panel != 'board':
                self.line = coast.chat(g, k)
        g.release_holds()
        g.audio.play('page', 0.6)

    def close_panel(self):
        self.panel = None
        self.g.audio.play('page', 0.5)

    def leave(self):
        g = self.g
        self.done = True
        g.aqscene = None
        if g.overlay == 'harbour':
            g.overlay = None
        g.release_holds()
        g.audio.play('plop', 0.4)
        g.toast('You climb back down into your boat.', (90, 140, 180))
        g.save()

    # ------------------------------------------------------------ input
    def key(self, k):
        if k == pygame.K_ESCAPE:
            if self.panel:
                self.close_panel()
            else:
                self.leave()
            return
        if self.panel:
            return
        if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_w, pygame.K_UP):
            self.interact()

    def press(self, src='mouse'):
        if self.panel:
            return
        g = self.g
        wx, wy = g.s2w(*g.ui.mouse)
        tx = max(14.0, min(HB_W - 14.0, wx + self.scroll))
        if wy > FLOOR + 10 and tx < STEPS_X + 30:
            return self.walk_to(STEPS_X, self.leave)
        for item in g.coast['beach']:
            if abs(item['x'] - tx) < 8 and wy > FLOOR - 10:
                return self.walk_to(item['x'], self.interact)
        spots = [(BOARD_X, 'board'), (STALL_X, 'nell'), (INN_X, 'inn'), (YARD_X, 'ossian'), (LIGHT_X, 'sol'),
                 (HOME['morwen'], 'morwen')]
        if folk_here(g, 'kit'):
            spots.append((self.kit['x'], 'kit'))
        for sx, _what in spots:
            if abs(sx - tx) < 14 and wy > FLOOR - 70:
                return self.walk_to(sx, self.interact)
        self.walk_to(tx, None)

    def release(self, src='mouse'):
        self.holds.discard(src)

    def walk_to(self, x, then):
        self.target = float(x)
        self.on_arrive = then

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.done:
            return
        g = self.g
        self.t += dt
        rng = self.rng
        for p in self.fx:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 40 * dt
            p[4] -= dt
        self.fx = [p for p in self.fx if p[4] > 0]
        for gl in self.gulls:
            gl['x'] += gl['vx'] * dt
            if gl['x'] < -40 or gl['x'] > HB_W + 40:
                gl['vx'] = -gl['vx']
        if rng.random() < dt * 1.2:                              # smoke from the inn chimney
            self.smoke.append([707.0 + rng.uniform(-2, 2), float(FLOOR - 158), 3.0])
        if ('bass' in g.coast['tasks'] or coast.lit(g)) and rng.random() < dt * 1.0:     # ...and Sol's
            self.smoke.append([1111.0 + rng.uniform(-1, 1), float(FLOOR - 98), 3.0])
        for p in self.smoke:
            p[0] += (6 + getattr(g.env, 'wind', 0.3) * 10) * dt
            p[1] -= 7 * dt
            p[2] -= dt
        self.smoke = [p for p in self.smoke if p[2] > 0]
        self._update_kit(dt)
        moving = 0
        if self.panel is None:
            walk = 0
            if g.typing is None and not HEADLESS:
                keys = g.keys()
                walk = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
                       (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
            if walk:
                self.target, self.on_arrive = None, None
                moving = walk
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
            self.x = max(14.0, min(HB_W - 14.0, self.x + moving * WALK * dt))
            before = self.step
            self.step += dt * 9
            if int(before / math.pi) != int(self.step / math.pi):
                g.audio.step(0.22)
        else:
            self.step = 0.0
        want = max(0.0, min(HB_W - W, self.x - W / 2))
        self.scroll += (want - self.scroll) * min(1.0, dt * 5)

    def _update_kit(self, dt):
        k = self.kit
        rng = self.rng
        if k['goal'] is None:
            k['step'] = 0.0
            k['wait'] -= dt
            if k['wait'] <= 0:
                k['goal'] = rng.uniform(BEACH_X0 + 30, HB_W - 40)
        else:
            d = k['goal'] - k['x']
            if abs(d) < 1.5:
                k['goal'] = None
                k['wait'] = rng.uniform(2, 6)
            else:
                k['face'] = 1 if d > 0 else -1
                k['x'] += k['face'] * 24 * dt
                k['step'] += dt * 8

    def audio_ctx(self):
        return {'town': True, 'sea': True}

    # ------------------------------------------------------------ work you can watch
    def _burst(self, x, y, n=24, col=(255, 236, 170)):
        rng = self.rng
        for _ in range(n):
            self.fx.append([x + rng.uniform(-8, 8), y + rng.uniform(-6, 6), rng.uniform(-26, 26),
                            rng.uniform(-44, -10), rng.uniform(0.8, 1.4), col])

    def _task(self, tid):
        """Give Sol what the lamp needs, then close the window so you can see the change."""
        if not coast.do_task(self.g, tid):
            return
        self.close_panel()
        x, y = {'glass': (LIGHT_X, 86), 'bass': (1111, FLOOR - 92), 'oil': (1146, FLOOR - 12)}[tid]
        self._burst(x, y)
        if tid == 'oil':
            self._burst(LIGHT_X, 110, 16, (220, 200, 160))     # the top of the scaffold comes down

    def _light(self):
        if coast.light_up(self.g):
            self.close_panel()
            self._burst(LIGHT_X, 86, 40, (255, 240, 180))

    def _help(self):
        if coast.help_boat(self.g):
            self.close_panel()
            self._burst(BOAT_X + (190 if self.g.coast['boat'] >= len(coast.BOAT_STAGES) - 1 else 0), FLOOR - 30)

    # ------------------------------------------------------------ for the bot: a stroll round the harbour
    def auto(self, dt, rng):
        g = self.g
        if not hasattr(self, '_plan'):
            self._plan = ['morwen', 'nell', 'inn', 'ossian', 'sol', 'beach', 'kit', 'steps']
            self._wait = 0.0
        if self.panel:
            self._wait += dt
            if self._wait < 0.8:
                return
            self._wait = 0.0
            self._bot_panel()
            self.close_panel()
            return
        if self.target is not None or not self._plan:
            return
        step = self._plan.pop(0)
        if step == 'steps':
            self.walk_to(STEPS_X, self.leave)
        elif step == 'beach':
            for item in sorted(g.coast['beach'], key=lambda b: b['x']):
                self._plan.insert(0, ('item', item))
        elif isinstance(step, tuple):
            item = step[1]
            if item in g.coast['beach']:
                self.walk_to(item['x'], self.interact)
        elif step == 'kit':
            if folk_here(g, 'kit'):
                self.walk_to(self.kit['x'], self.interact)
        elif step == 'inn':
            if INN_HOURS[0] <= g.minute < INN_HOURS[1]:
                self.walk_to(INN_X, self.interact)
        elif step == 'sol':
            self.walk_to(LIGHT_X, self.interact)
        elif folk_here(g, step):
            self.walk_to({'morwen': HOME['morwen'], 'nell': STALL_X, 'ossian': YARD_X}[step], self.interact)

    def _bot_panel(self):
        g = self.g
        p = self.panel
        if p in ('morwen', 'board'):
            for i in range(len(g.coast['orders'])):
                coast.deliver_order(g, i)
        elif p == 'nell':
            if coast.sea_basket(g):
                coast.sell_sea(g)
            if g.coins > 300 and g.baits.get('ragworm', 0) < 5:
                coast.buy_bait(g, 'ragworm')
        elif p == 'inn':
            if g.coins > 400:
                coast.buy_chowder(g)
            if g.coins > 200:
                coast.buy_round(g, self.rng)
            for _ in range(3):                    # sit and listen for a bit
                self.t += 3.2
                g.draw()
        elif p == 'ossian':
            for u in coast.UPGRADES:
                if g.coins > u['price'] + 400:
                    coast.buy_up(g, u['id'])
            self._help()
        elif p == 'kit':
            for sh in coast.SHELLS:
                coast.swap_shell(g, sh['id'])
            while coast.swap_glass(g):
                pass
        elif p == 'sol':
            for tsk in coast.LIGHT_TASKS:
                coast.do_task(g, tsk['id'])
            coast.light_up(g)

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def water_top(self):
        return FLOOR + 24 - int(coast.tide_level(self.g) * 12)

    def draw_world(self, frame):
        g = self.g
        env = g.env
        t = self.t
        season = env.season
        sc = int(self.scroll)
        w = g.world
        w._sky(frame, env)
        # the open sea out to the horizon
        far_sea = lerp_c((70, 120, 150), env.sky[2], 0.45)
        near_sea = lerp_c((40, 90, 120), env.amb, 0.25)
        for y in range(HORIZON, H, 2):
            frame.fill(lerp_c(far_sea, near_sea, (y - HORIZON) / (H - HORIZON)), (0, y, W, 2))
        for i in range(26):                                     # glints on the swell
            x = int((i * 97 + t * (6 + i % 3) - sc * 0.3) % W)
            y = HORIZON + 4 + (i * 23) % 70
            if math.sin(t * 2 + i) > 0.3:
                frame.fill(lerp_c(far_sea, (240, 246, 250), 0.45), (x, y, 3 + i % 4, 1))
        back = build_back(season).copy()
        amb = env.amb if env.fog <= 0.01 else lerp_c(env.amb, env.fog_color, env.fog * 0.5)
        back.fill((*lerp_c(amb, env.sky[2], 0.3), 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(back, (-(sc // 3), 0))
        self._sail(frame, t, sc)
        street, wins, lamps = build(season)
        near = self.near
        near.fill((0, 0, 0, 0))
        T.draw_volumes(near, sc, season, VOLUMES)
        near.blit(street, (0, 0), (sc, 0, W, H))
        self._draw_live(near, sc, t, season)
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(near, (0, 0))
        self._lights(frame, sc, t, wins, lamps)
        w._weather(frame, env)

    def _sail(self, frame, t, sc):
        x = int((t * 4 + 300) % (W + 200)) - 100 - (sc // 6) % 40
        y = HORIZON - 2
        frame.fill((90, 70, 60), (x - 6, y, 12, 2))
        pygame.draw.polygon(frame, (240, 236, 226), [(x, y - 1), (x, y - 12), (x + 6, y - 1)])

    def _draw_live(self, s, sc, t, season):
        g = self.g
        st = g.coast
        # the flag on the harbour office
        for i in range(12):
            yy = FLOOR - 120 + int(math.sin(t * 5 - i * 0.6) * (1 + i * 0.12))
            s.fill((60, 80, 140) if (i // 3) % 2 else (240, 236, 226), (302 - sc + i, yy, 1, 7))
        # the tide clock on the harbour board
        bx = BOARD_X - sc
        if -30 < bx < W + 30:
            lv = coast.tide_level(g)
            s.fill((236, 226, 196), (bx - 6, FLOOR - 32, 12, 6))
            s.fill((60, 100, 150), (bx - 6, FLOOR - 32, int(12 * lv), 6))
        # folk
        for k in ('morwen', 'nell', 'ossian', 'sol'):
            if not folk_here(g, k):
                continue
            x = HOME[k] - sc
            if -30 < x < W + 30:
                f = coast.FOLK[k]
                face = 1 if self.x > HOME[k] else -1
                if k == 'nell':
                    T.walker(s, x, FLOOR - 8, face, 0, f['shirt'], f['hair'], f['hat'], season)
                    continue
                works = k == 'ossian' or (k == 'sol' and 0 < len(st['tasks']) < 3 and not coast.lit(g))
                step = (t * 4) if works and int(t / 3) % 2 else 0
                T.ground_shadow(s, x, FLOOR, 13, 60)
                T.walker(s, x, FLOOR, face, 0, f['shirt'], f['hair'], f['hat'], season)
                if step:                                       # tap, tap, tap with the mallet
                    up = math.sin(t * 9) > 0
                    hx = x + 8 * face
                    s.fill((110, 80, 60), (hx, FLOOR - 22 - (3 if up else 0), 2, 7))
                    s.fill((90, 90, 96), (hx - 2, FLOOR - 24 - (3 if up else 0), 6, 3))
        # Nell's counter, in front of her: fish laid out on ice
        cx = STALL_X - sc
        if -70 < cx < W + 70:
            s.fill((150, 110, 80), (cx - 46, FLOOR - 22, 92, 18))
            s.fill((120, 86, 62), (cx - 46, FLOOR - 8, 92, 4))
            s.fill((226, 236, 242), (cx - 44, FLOOR - 26, 88, 5))
            for i in range(6):
                fx = cx - 38 + i * 15
                col = [(110, 146, 170), (54, 112, 120), (170, 150, 112), (220, 150, 150), (150, 166, 180),
                       (200, 70, 64)][i]
                pygame.draw.ellipse(s, col, (fx - 5, FLOOR - 28, 12, 4))
                s.set_at((fx + 5, FLOOR - 27), darken(col, 0.4))
            for i in range(10):                                 # the striped awning
                s.fill((200, 70, 66) if i % 2 else (240, 236, 226), (cx - 54 + i * 11, FLOOR - 64, 11, 10))
            for i in range(10):
                pygame.draw.circle(s, (200, 70, 66) if i % 2 else (240, 236, 226), (cx - 49 + i * 11, FLOOR - 54), 5,
                                   draw_top_left=False, draw_top_right=False)
            T._sign(s, cx, FLOOR - 76, "NELL'S FISH", (236, 226, 200), (170, 60, 56), 64)
            if st.get('catch'):
                s.fill((250, 240, 200), (cx + 30, FLOOR - 44, 14, 9))
                s.fill((200, 70, 66), (cx + 31, FLOOR - 43, 12, 2))
        # beach finds
        for item in st['beach']:
            x = item['x'] - sc
            if -10 < x < W + 10:
                if item['kind'] == 'glass':
                    col = next(gl['col'] for gl in coast.GLASS if gl['id'] == item['id'])
                    s.fill(col, (x - 2, FLOOR + 2, 4, 3))
                    if math.sin(t * 3 + item['x']) > 0.7:
                        s.fill((255, 255, 255), (x, FLOOR + 1, 1, 1))
                else:
                    shell_icon(s, item['id'], (x, FLOOR + 3), 1)
        # Kit on the beach, with a bucket and spade
        if folk_here(g, 'kit'):
            k = self.kit
            x = int(k['x'] - sc)
            if -30 < x < W + 30:
                f = coast.FOLK['kit']
                T.ground_shadow(s, x, FLOOR, 10, 50)
                T.walker(s, x, FLOOR, k['face'], k['step'], f['shirt'], f['hair'], f['hat'], season, True)
        self._draw_works(s, sc, t)
        # you
        x = int(self.x - sc)
        T.ground_shadow(s, x, FLOOR, 13, 60)
        T.walker(s, x, FLOOR, self.face, self.step, actors.SHIRT[season], (112, 72, 52), g.hat, season)
        for p in self.fx:
            s.fill(p[5], (int(p[0] - sc), int(p[1]), 2, 2))
        # smoke
        for x0, y0, life in self.smoke:
            a = int(100 * min(1.0, life / 3.0))
            pygame.draw.circle(s, (220, 220, 226, a), (int(x0 - sc), int(y0)), 2 + int((3.0 - life) * 1.3))
        # the harbour water against the quay, rising and falling with the tide
        wt = self.water_top()
        wcol = lerp_c((60, 110, 130), (40, 84, 110), 0.5)
        if season == 3:
            wcol = (80, 116, 140)
        weed = (70, 90, 60)
        qw = max(0, min(W, BEACH_X0 - 4 - sc))                       # weed and wet stone above the waterline
        s.fill(weed, (0, wt - 3, qw, 3))
        s.fill(darken((130, 124, 116), 0.25), (0, wt - 7, qw, 4))
        for y in range(wt, H):
            k = (y - wt) / max(1, H - wt)
            s.fill(lerp_c(wcol, darken(wcol, 0.3), k), (0, y, W, 1))
        for i in range(18):
            x = int((i * 53 + math.sin(t * 0.8 + i) * 10 - sc) % (W + 20)) - 10
            y = wt + 3 + (i * 7) % max(1, H - wt - 4)
            s.fill(lighten(wcol, 0.25), (x, y, 6 + i % 5, 1))
        bx = BEACH_X0 - sc                                          # foam where the water meets the sand
        if bx < W:
            for xx in range(max(0, bx), W, 3):
                yy = wt + int(math.sin(t * 2 + xx * 0.08) * 1.5)
                s.fill((236, 244, 246), (xx, yy, 3, 1))
        # boats moored along the quay, bobbing
        moored = [(STEPS_X + 4, (90, 130, 160)), (176, (200, 90, 70)), (560, (70, 110, 90)), (744, (230, 200, 120)),
                  (1120, (120, 90, 140))]
        if st['boat'] >= len(coast.BOAT_STAGES) - 1:
            moored.append((BOAT_X + 190, (70, 110, 160)))
        for i, (bx0, col) in enumerate(moored):
            x = bx0 - sc
            if -50 < x < W + 50:
                bob = math.sin(t * 1.6 + i * 1.3) * 1.5
                y = wt + 2 + bob
                hull = [(x - 20, y - 6), (x + 20, y - 6), (x + 14, y + 3), (x - 14, y + 3)]
                pygame.draw.polygon(s, col, hull)
                pygame.draw.line(s, lighten(col, 0.3), (x - 20, y - 6), (x + 20, y - 6), 2)
                s.fill(darken(col, 0.35), (x - 14, y + 1, 28, 2))
                if i == 0:
                    T.sign_text(s, 'YOURS', (x, y - 2), (250, 246, 230))
                elif i == 5:
                    s.fill((250, 250, 246), (x - 20, y - 5, 40, 1))
                    s.fill((150, 140, 130), (x - 1, y - 32, 2, 26))
                    pygame.draw.polygon(s, (240, 236, 226), [(x + 1, y - 31), (x + 1, y - 9), (x + 14, y - 9)])
                elif i % 2:
                    s.fill((150, 140, 130), (x - 1, y - 30, 2, 24))      # a mast
                    pygame.draw.line(s, (120, 110, 100), (x, y - 30), (x + 14, y - 7))
        # gulls
        for gl in self.gulls:
            x = int(gl['x'] - sc * 0.8)
            if -10 < x < W + 10:
                flap = math.sin(t * 6 + gl['ph']) * 2
                y = int(gl['y'] + math.sin(t * 0.8 + gl['ph']) * 6)
                pygame.draw.lines(s, (240, 240, 244), False, [(x - 5, y - flap), (x, y), (x + 5, y - flap)], 2)

    def _draw_works(self, s, sc, t):
        """What the lighthouse work and Ossian's boat look like today."""
        g = self.g
        st = g.coast
        tasks = st['tasks']
        lit = coast.lit(g)
        cx = 1111 - sc                                      # Sol's chimney
        if -20 < cx < W + 20:
            s.fill((150, 120, 100), (cx - 3, FLOOR - 96, 7, 16))
            s.fill((116, 92, 78), (cx - 4, FLOOR - 97, 9, 2))
        lx = LIGHT_X - sc
        if not lit and -70 < lx < W + 70:
            # the scaffold comes down a section at a time as the work gets done
            n = 3 - len(tasks)
            secs = ((96, 156), (156, 222), (222, FLOOR - 6))[3 - n:] if n else ()
            wood, dark = (156, 122, 84), (112, 86, 60)
            for a, b in secs:
                for px in (lx - 30, lx + 29):
                    s.fill(wood, (px, a, 2, b - a))
                s.fill(dark, (lx - 33, a, 66, 3))             # the walkway
                s.fill(wood, (lx - 33, a, 66, 1))
                pygame.draw.line(s, dark, (lx - 29, a + 3), (lx - 22, b - 2))
                pygame.draw.line(s, dark, (lx + 28, a + 3), (lx + 21, b - 2))
            if secs:                                         # a ladder up the side
                top = secs[0][0]
                for yy in range(top + 4, FLOOR - 6, 6):
                    s.fill(dark, (lx + 33, yy, 6, 1))
                s.fill(wood, (lx + 32, top, 1, FLOOR - 6 - top))
                s.fill(wood, (lx + 39, top, 1, FLOOR - 6 - top))
        if 'oil' in tasks or lit:                            # barrels of lamp oil and a crate of wicks
            bx = 1140 - sc
            if -20 < bx < W + 20:
                for i in range(2):
                    xx = bx + i * 9
                    s.fill((128, 84, 54), (xx - 4, FLOOR - 13, 8, 12))
                    s.fill((90, 60, 40), (xx - 4, FLOOR - 10, 8, 1))
                    s.fill((90, 60, 40), (xx - 4, FLOOR - 5, 8, 1))
                s.fill((170, 140, 96), (bx - 2, FLOOR - 20, 11, 7))
                s.fill((130, 104, 70), (bx - 2, FLOOR - 17, 11, 1))
        self._boat(s, BOAT_X - sc, FLOOR, st['boat'])

    def _boat(self, s, x, G, stage):
        """Ossian's boat on its trestles (side view): keel, ribs, planks, paint. Gone once launched."""
        if not -70 < x < W + 70:
            return
        s.fill((44, 36, 34), (x - 48, G - 42, 96, 28))       # in front of the shed's old hull
        for tx in (x - 28, x + 28):                          # the trestles
            pygame.draw.line(s, (110, 84, 60), (tx - 6, G - 4), (tx, G - 19))
            pygame.draw.line(s, (110, 84, 60), (tx + 6, G - 4), (tx, G - 19))
            s.fill((130, 98, 70), (tx - 7, G - 20, 14, 2))
        if stage >= len(coast.BOAT_STAGES) - 1:
            return
        wood = (178, 134, 92)
        if stage >= 2:
            col = (70, 110, 160) if stage >= 3 else wood
            hull = [(x - 46, G - 40), (x + 48, G - 43), (x + 38, G - 22), (x - 38, G - 22)]
            pygame.draw.polygon(s, col, hull)
            for yy in (G - 36, G - 31, G - 26):
                pygame.draw.line(s, darken(col, 0.18), (x - 42 + (G - 22 - yy) // 3, yy), (x + 42 - (G - 22 - yy) // 4, yy))
            pygame.draw.line(s, lighten(col, 0.3), (x - 46, G - 40), (x + 48, G - 43), 2)
            if stage >= 3:
                pygame.draw.line(s, (240, 240, 236), (x - 42, G - 36), (x + 44, G - 39), 1)
                T.sign_text(s, coast.BOAT_NAME.upper(), (x + 14, G - 31), (250, 246, 230))
        else:
            s.fill(wood, (x - 40, G - 24, 80, 3))            # the keel, with the stem and stern posts
            pygame.draw.line(s, wood, (x + 40, G - 23), (x + 47, G - 43), 2)
            pygame.draw.line(s, wood, (x - 40, G - 23), (x - 45, G - 40), 2)
            if stage >= 1:
                for i in range(7):
                    rx = x - 33 + i * 11
                    h = 15 - abs(i - 3)
                    pygame.draw.lines(s, (200, 160, 112), False, [(rx, G - 23), (rx - 2, G - 23 - h // 2),
                                                                   (rx - 1, G - 23 - h - 2)])

    def _lights(self, frame, sc, t, wins, lamps):
        g = self.g
        nf = g.env.nf
        big, mid, beam = self.glows
        if nf > 0.05:
            for r in wins:
                if -20 < r.x - sc < W + 20:
                    frame.fill((int(210 * nf), int(150 * nf), int(70 * nf)), r.move(-sc, 0),
                               special_flags=pygame.BLEND_ADD)
                    add_glow(frame, mid, (r.centerx - sc, r.centery), nf * 0.55)
            for lx, ly in lamps:
                if -40 < lx - sc < W + 40:
                    fl = 0.9 + 0.1 * math.sin(t * 9 + lx)
                    add_glow(frame, big, (lx - sc, ly), nf * 0.7 * fl)
        # the lighthouse lamp
        lx, ly = LIGHT_X - sc, 104 - 17
        if -200 < lx < W + 200:
            if coast.lit(g):
                on = max(0.35, nf)
                frame.fill((int(250 * on), int(220 * on), int(140 * on)), (lx - 10, ly - 10, 20, 20),
                           special_flags=pygame.BLEND_ADD)
                add_glow(frame, beam, (lx, ly), 0.5 + 0.5 * nf)
                if nf > 0.2:                                        # the beam, swinging round
                    a = math.sin(t * 0.9)
                    if abs(a) > 0.1:
                        art.draw_beam(frame, (lx, ly), (lx + a * 460, ly + 6 - abs(a) * 20), 30 * abs(a),
                                      0.34 * nf * min(1.0, abs(a) * 1.5))
            else:
                tasks = g.coast['tasks']
                if 'glass' in tasks:                                # the mended lens catches the sky
                    frame.fill((70, 104, 136), (lx - 10, ly - 10, 20, 20))
                    gx = int((t * 16) % 46) - 12
                    if -10 <= gx < 9:
                        frame.fill((236, 246, 255), (lx + gx, ly - 10, 2, 20))
                else:
                    frame.fill((22, 26, 34), (lx - 10, ly - 10, 20, 20))
                    for i in range(3):
                        frame.fill((70, 80, 96), (lx - 8 + i * 6, ly - 9, 1, 18))
                if coast.can_light(g):                             # ready: a test flicker in the lamp room
                    fl = 0.25 + 0.3 * abs(math.sin(t * 7)) * (0.6 + 0.4 * math.sin(t * 2.3))
                    frame.fill((int(220 * fl), int(160 * fl), int(70 * fl)), (lx - 8, ly - 8, 16, 16),
                               special_flags=pygame.BLEND_ADD)
                    add_glow(frame, mid, (lx, ly), fl * 0.7)
        if ('bass' in g.coast['tasks'] or coast.lit(g)) and nf < 0.45:      # supper on at Sol's cottage
            on = 0.45 - nf
            for r in wins:
                if COTTAGE[0] <= r.x <= COTTAGE[1] and -20 < r.x - sc < W + 20:
                    frame.fill((int(230 * on), int(150 * on), int(60 * on)), r.move(-sc, 0),
                               special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------ UI
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        sc = self.scroll
        st = g.coast
        ui.blit_text(s, 'Saltmarsh Harbour', (sw // 2, 26), 'h3', (255, 250, 240), 'center', (30, 30, 50))
        catch = FISH_BY_ID.get(st.get('catch'))
        info = '%s    Catch of the day: %s    %d coins' % (coast.tide_text(g), catch['name'] if catch else '-',
                                                           g.coins)
        ui.blit_text(s, info, (sw // 2, 58), 'small', (230, 240, 246), 'center', (20, 30, 40))
        ui.blit_text(s, fmt_clock(g.minute), (24, 22), 'bodyb', (255, 250, 240), 'topleft', (30, 30, 50))
        p = self.prompt() if self.panel is None and self.target is None else None
        if self.panel is None and not p:                           # names over the folk you are near
            for kk in ('morwen', 'nell', 'ossian', 'sol', 'kit'):
                if not folk_here(g, kk):
                    continue
                fx = self.kit['x'] if kk == 'kit' else HOME[kk]
                if abs(fx - self.x) < 70:
                    f = coast.FOLK[kk]
                    lift = 30 if kk == 'kit' else 44
                    ui.blit_text(s, '%s, %s' % (f['name'], f['title'].lower()), (int((fx - sc) * k),
                                 int((FLOOR - lift) * k)), 'tiny', (255, 250, 236), 'center', outline=(30, 30, 40))
        if p:
            px = int((self.x - sc) * k)
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (px, int((FLOOR - 40) * k) - 6)
            r.x = max(12, min(sw - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        if self.panel is None:
            hint = g.hint([('key', 'A'), ('key', 'D'), 'or', ('key', 'Click'), 'to walk   ', ('key', 'E'),
                           'talk, shop, pick up   ', ('key', 'Esc'), 'back to the boat'],
                          [('pad', 'STICK'), 'walk   ', ('pad', 'A'), 'talk, shop   ', ('pad', 'B'), 'back to the boat'])
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, sh - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
            return
        g.dim(s)
        {'board': self.draw_board, 'morwen': self.draw_board, 'nell': self.draw_nell, 'inn': self.draw_inn,
         'ossian': self.draw_ossian, 'sol': self.draw_sol, 'kit': self.draw_kit}[self.panel](s)

    # ------------------------------------------------------------ the windows
    def _head(self, s, rect, k):
        """A portrait, hearts and today's words down the left of a window."""
        g = self.g
        ui = g.ui
        f = coast.FOLK[k]
        tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
        T.walker(tmp, 13, 38, 1, 0, f['shirt'], f['hair'], f['hat'], g.env.season, False)
        big = pygame.transform.scale(tmp, (104, 160))
        s.blit(big, big.get_rect(center=(rect.x + 110, rect.y + 190)))
        ui.blit_text(s, f['name'], (rect.x + 110, rect.y + 278), 'bodyb', U.INK, 'center')
        ui.blit_text(s, f['title'], (rect.x + 110, rect.y + 298), 'tiny', U.SOFT, 'center')
        hx = rect.x + 110 - 2 * 22
        n = coast.hearts(g, k)
        for i in range(5):
            col = (226, 84, 104) if i < n else (214, 200, 186)
            cx, cy = hx + i * 22, rect.y + 322
            pygame.draw.circle(s, col, (cx - 4, cy), 5)
            pygame.draw.circle(s, col, (cx + 4, cy), 5)
            pygame.draw.polygon(s, col, [(cx - 9, cy + 1), (cx + 9, cy + 1), (cx, cy + 10)])
        if self.line:
            y = rect.y + 350
            for ln in ui.wrap('"%s"' % self.line, 'small', 200)[:6]:
                ui.blit_text(s, ln, (rect.x + 110, y), 'small', U.SOFT, 'midtop')
                y += 22

    def _fish_icon(self, s, f, center, w=72, h=36, known=True):
        spr = art.fish_sprite(f, 2) if known else art.silhouette(f, 2)
        kk = min(w / spr.get_width(), h / spr.get_height())
        spr = pygame.transform.scale(spr, (max(1, int(spr.get_width() * kk)), max(1, int(spr.get_height() * kk))))
        s.blit(spr, spr.get_rect(center=center))

    def draw_board(self, s):
        g = self.g
        ui = g.ui
        rect = T._panel(g, s, 1000, 600, 'The Harbour Board')
        here = folk_here(g, 'morwen')
        if here:
            self._head(s, rect, 'morwen')
        x0 = rect.x + 240
        cw = rect.right - 30 - x0
        y = rect.y + 96
        ui.blit_text(s, "Morwen's orders for today", (x0, y), 'bodyb', U.INK)
        y += 34
        basket = {b['id'] for b in g.basket}
        for i, o in enumerate(g.coast['orders']):
            f = FISH_BY_ID[o['fish']]
            r = pygame.Rect(x0, y, cw, 62)
            ui.tile(s, r, (244, 236, 218), RARITY_COLORS[f['rarity']])
            self._fish_icon(s, f, (r.x + 50, r.centery), known=f['id'] in g.journal)
            ui.blit_text(s, f['name'] if f['id'] in g.journal else '%s  (not caught yet)' % f['name'],
                         (r.x + 100, r.y + 10), 'smallb', U.INK)
            ui.blit_text(s, '%d coins.  %s' % (o['reward'], f['hint']), (r.x + 100, r.y + 34), 'tiny', U.SOFT,
                         maxw=cw - 260)
            if o['done']:
                ui.button(s, (r.right - 140, r.y + 11, 126, 40), 'Delivered', None, enabled=False, font='smallb')
            else:
                ui.button(s, (r.right - 140, r.y + 11, 126, 40), 'Deliver', lambda i=i: coast.deliver_order(g, i),
                          'primary', enabled=here and o['fish'] in basket, font='smallb', nav=True)
            y += 70
        if not here:
            ui.blit_text(s, 'The office is shut. Morwen takes deliveries from 7 AM to 8 PM.', (x0, y), 'small',
                         U.SOFT)
        y += 30
        # the tide table: a day of water level, and the next few turns
        ui.blit_text(s, 'Tides:  %s' % coast.tide_text(g), (x0, y), 'bodyb', U.INK)
        y += 34
        gr = pygame.Rect(x0, y, cw - 320, 110)
        pygame.draw.rect(s, (236, 230, 214), gr, border_radius=8)
        pts = []
        for i in range(97):
            m = g.minute + i * 15
            lv = coast.tide_level(g, m)
            pts.append((gr.x + 6 + i * (gr.w - 12) / 96, gr.bottom - 10 - lv * (gr.h - 20)))
        pygame.draw.polygon(s, (150, 196, 220), [(gr.x + 6, gr.bottom - 4)] + pts + [(gr.right - 6, gr.bottom - 4)])
        pygame.draw.lines(s, (60, 110, 150), False, pts, 2)
        for frac, label in ((0.0, 'now'), (0.5, '+12h'), (1.0, '+24h')):
            xx = gr.x + 6 + frac * (gr.w - 12)
            ui.blit_text(s, label, (xx, gr.bottom + 4), 'tiny', U.SOFT, 'midtop')
        pygame.draw.line(s, (200, 80, 70), (gr.x + 6, gr.y + 4), (gr.x + 6, gr.bottom - 4), 2)
        tx = gr.right + 20
        for i, (kind, day, m) in enumerate(coast.next_tides(g, 4)):
            when = fmt_clock(m) + ('' if day == g.day else '  tomorrow')
            ui.blit_text(s, '%s  %s' % (kind, when), (tx, y + 4 + i * 26), 'small', U.INK)
        ui.blit_text(s, 'High water brings big fish close in; low water uncovers the rock pools.',
                     (x0, gr.bottom + 30), 'tiny', U.SOFT)

    def draw_nell(self, s):
        g = self.g
        ui = g.ui
        rect = T._panel(g, s, 940, 560, "Nell's Fish Stall")
        self._head(s, rect, 'nell')
        x0 = rect.x + 240
        cw = rect.right - 30 - x0
        y = rect.y + 96
        f = FISH_BY_ID.get(g.coast.get('catch'))
        if f:
            r = pygame.Rect(x0, y, cw, 74)
            ui.tile(s, r, (250, 240, 214), U.GOLD)
            self._fish_icon(s, f, (r.x + 56, r.centery), 90, 44, f['id'] in g.journal)
            ui.blit_text(s, 'Catch of the day: %s' % f['name'], (r.x + 116, r.y + 12), 'bodyb', U.INK)
            ui.blit_text(s, 'Nell pays double for it, today only.  %s' % f['hint'], (r.x + 116, r.y + 42), 'tiny',
                         U.SOFT, maxw=cw - 130)
            y += 92
        ui.blit_text(s, 'Bait', (x0, y), 'bodyb', U.INK)
        y += 32
        for b in coast.SEA_BAITS:
            have = g.baits.get(b['id'], 0)
            r = pygame.Rect(x0, y, cw, 58)
            ui.tile(s, r, (244, 236, 218), (190, 170, 140))
            ui.blit_text(s, '%s, pack of %d   (you have %d)' % (b['name'], b['pack'], have), (r.x + 16, r.y + 8),
                         'smallb', U.INK)
            ui.blit_text(s, b['desc'], (r.x + 16, r.y + 32), 'tiny', U.SOFT, maxw=cw - 200)
            ui.button(s, (r.right - 160, r.y + 9, 146, 40), '%d coins' % b['price'],
                      lambda bid=b['id']: coast.buy_bait(g, bid), 'primary', enabled=g.coins >= b['price'],
                      font='smallb', nav=True)
            y += 66
        y += 12
        items = coast.sea_basket(g)
        ui.blit_text(s, 'Sell your sea fish', (x0, y), 'bodyb', U.INK)
        y += 32
        if items:
            total = g.quote(items)
            ui.blit_text(s, '%d sea fish in your basket.' % len(items), (x0, y + 10), 'small', U.SOFT)
            ui.button(s, (x0 + cw - 260, y, 260, 46), 'Sell all  +%d coins' % total, lambda: coast.sell_sea(g),
                      'primary', font='smallb', nav=True)
        else:
            ui.blit_text(s, 'No sea fish in your basket. Nell only buys from the sea.', (x0, y + 10), 'small',
                         U.SOFT)

    LINE_T = 3.4                     # seconds each line of talk stays up

    def inn_talk(self):
        """Today's conversations between Bram and Old Tam: the tide, the weather, the light, the boat, you."""
        g = self.g
        st = g.coast
        rng = random.Random(g.day * 31 + 7)
        convs = []
        high = next(((d, m) for k, d, m in coast.next_tides(g, 3) if k == 'High'), None)
        hi = fmt_clock(high[1]) if high else 'tonight'
        convs.append([(0, "Tide's on the turn. High water at %s." % hi),
                      (1, 'High water, big fish. Always been the way.'),
                      (0, 'You said that about my cousin.'),
                      (1, 'And was I wrong?')])
        tom = g.forecast.get(str(g.day + 1), 'clear')
        sky = {'rain': ("Rain tomorrow, the radio says.", "Good. The fish don't mind getting wet."),
               'storm': ('Storm coming tomorrow. Tie everything down.', "And the Thunderfin come up. Mark my words."),
               'fog': ('Fog tomorrow. Thick as chowder.', 'Then stay in and eat chowder.'),
               'snow': ('Snow tomorrow!', 'My knees told me that last week.')}.get(
            tom, ('Fair weather tomorrow, they reckon.', "Fair weather, fair fishing. Even you'll catch something."))
        convs.append([(1, sky[0]), (0, sky[1])])
        tasks = st['tasks']
        if coast.lit(g):
            convs.append([(1, 'Years that light was dark, and now look at it.'),
                          (0, 'I saw a grey back out by the rocks last night...'),
                          (1, 'The Mariner? Never. Not in my lifetime.'),
                          (0, "Well, your lifetime isn't over yet.")])
        elif not tasks:
            convs.append([(0, 'Old Sol was up the lighthouse again.'), (1, 'Talking to the lamp, was he?'),
                          (0, "Says it'll shine again if someone helps him."),
                          (1, 'Somebody young and foolish, then.')])
        elif len(tasks) < 3:
            convs.append([(0, 'Did you see? Part of the scaffold is down.'), (1, 'Someone is helping Sol. About time.'),
                          (0, 'The lens caught the sun this morning!' if 'glass' in tasks else
                           'Sol had a proper supper last night, smoke and all.' if 'bass' in tasks else
                           'Barrels of lamp oil on the quay, too.'),
                          (1, 'Well, I never.')])
        else:
            convs.append([(0, 'Sol has everything the lamp needs now.'), (1, 'Then why is it still dark?'),
                          (0, 'Waiting for the right person to light it, he says.')])
        bs = st['boat']
        if bs == 0:
            convs.append([(0, "Ossian's laid a new keel at the yard."), (1, 'Another boat? Who for?'),
                          (0, "Won't say. Could use a hand, though.")])
        elif bs < len(coast.BOAT_STAGES) - 1:
            convs.append([(1, "Ossian's boat is coming on."),
                          (0, {1: 'Ribs up already.', 2: 'Planked and caulked!', 3: 'Painted blue. Got a name, too.'}[bs]),
                          (1, 'Someone from the lake is helping him, I hear.')])
        else:
            convs.append([(0, 'The %s rides nicely on her mooring.' % coast.BOAT_NAME),
                          (1, "Best boat Ossian ever built. Don't tell him I said so.")])
        sea = [FISH_BY_ID[f] for f in g.journal if FISH_BY_ID.get(f, {}).get('method') == 'sea']
        if sea:
            f = max(sea, key=lambda x: x['rarity'])
            convs.append([(0, 'That angler from the lake landed a %s, you know.' % f['name']),
                          (1, "From the lake? Beginner's luck."),
                          (0, '%d kinds of sea fish, Nell says.' % len(sea)), (1, '...Pass the chowder.')])
        else:
            convs.append([(1, 'Lake folk never catch a thing in salt water.'),
                          (0, 'Give them time. The tide teaches everyone.')])
        rng.shuffle(convs)
        return convs

    def talk_now(self):
        """(speaker, text) of the line being said now, or None in the pause between conversations."""
        if not self.talk:
            return None
        el = self.t - self.talk_t0
        lines = []
        for c in self.talk:
            lines += c + [None]                       # a pause after each one
        k = int(el / self.LINE_T) % len(lines)
        return lines[k]

    def _inn_scene(self, s, sr):
        """The room: panelling, the fire, the bar, and Bram and Old Tam at their table."""
        g = self.g
        ui = g.ui
        t = self.t
        pygame.draw.rect(s, (86, 58, 42), sr, border_radius=12)
        for xx in range(sr.x + 10, sr.right - 10, 24):
            s.fill((74, 48, 34), (xx, sr.y + 20, 2, sr.h - 74))
        s.fill((58, 38, 28), (sr.x + 4, sr.y + 8, sr.w - 8, 12))                 # a beam
        fl = pygame.Rect(sr.x + 4, sr.bottom - 56, sr.w - 8, 52)
        pygame.draw.rect(s, (116, 80, 54), fl, border_bottom_left_radius=10, border_bottom_right_radius=10)
        for yy in range(fl.y + 10, fl.bottom, 12):
            s.fill((100, 68, 46), (fl.x, yy, fl.w, 2))
        # the hearth
        hx = sr.x + 96
        stone = pygame.Rect(hx - 64, sr.y + 52, 128, sr.h - 104)
        pygame.draw.rect(s, (130, 124, 116), stone, border_radius=6)
        for yy in range(stone.y + 12, stone.bottom, 16):
            for xx in range(stone.x + ((yy // 16) % 2) * 12, stone.right - 8, 24):
                pygame.draw.rect(s, (112, 106, 100), (xx, yy, 20, 12), 1, border_radius=2)
        mouth = pygame.Rect(hx - 40, stone.bottom - 76, 80, 76)
        pygame.draw.rect(s, (30, 20, 18), mouth, border_top_left_radius=30, border_top_right_radius=30)
        glow = pygame.Surface((160, 120))
        glow.fill((0, 0, 0))
        k = 0.8 + 0.2 * math.sin(t * 6) * math.sin(t * 2.7)
        pygame.draw.circle(glow, (int(110 * k), int(56 * k), int(20 * k)), (80, 80), 56)
        pygame.draw.circle(glow, (int(160 * k), int(90 * k), int(30 * k)), (80, 86), 30)
        s.blit(glow, (hx - 80, mouth.bottom - 100), special_flags=pygame.BLEND_RGB_ADD)
        for i in range(5):                                   # flames
            fx = hx - 26 + i * 13
            h = 26 + 14 * abs(math.sin(t * (5 + i) + i * 1.7))
            base = mouth.bottom - 10
            pygame.draw.polygon(s, (236, 120, 50), [(fx - 8, base), (fx + 8, base), (fx + math.sin(t * 9 + i) * 3, base - h)])
            pygame.draw.polygon(s, (252, 210, 110), [(fx - 4, base), (fx + 4, base),
                                                     (fx + math.sin(t * 11 + i) * 2, base - h * 0.55)])
        s.fill((80, 56, 40), (hx - 34, mouth.bottom - 10, 68, 6))         # the logs
        s.fill((60, 44, 32), (stone.x - 6, stone.y - 6, stone.w + 12, 8))   # the mantel
        # the bar, with bottles, and the ship in a bottle
        bx = sr.right - 190
        for j in range(2):
            s.fill((60, 40, 30), (bx, sr.y + 50 + j * 46, 170, 4))
            for i in range(7):
                col = ((90, 140, 90), (150, 70, 60), (200, 170, 90), (90, 110, 160))[(i + j) % 4]
                pygame.draw.rect(s, col, (bx + 10 + i * 22, sr.y + 26 + j * 46, 10, 24), border_radius=3)
                s.fill(lighten(col, 0.35),
                       (bx + 12 + i * 22, sr.y + 30 + j * 46, 2, 12))
        pygame.draw.ellipse(s, (210, 230, 236), (bx + 30, sr.y + 120 - 14, 110, 26), 2)
        pygame.draw.polygon(s, (120, 80, 56), [(bx + 60, sr.y + 122), (bx + 112, sr.y + 122), (bx + 104, sr.y + 128),
                                                (bx + 68, sr.y + 128)])
        pygame.draw.polygon(s, (240, 236, 226), [(bx + 86, sr.y + 108), (bx + 86, sr.y + 121), (bx + 100, sr.y + 121)])
        s.fill((96, 64, 44), (bx - 10, sr.bottom - 96, 200, 46))           # the counter
        s.fill((130, 90, 60), (bx - 14, sr.bottom - 100, 208, 8))
        # Bram and Old Tam
        say = self.talk_now()
        tx = sr.centerx - 30
        ty = sr.bottom - 44
        heads = []
        for i, fk in enumerate(INN_FOLK):
            x = tx + (-74 if i == 0 else 74)
            tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
            T.walker(tmp, 13, 38, 1 if i == 0 else -1, 0, fk['shirt'], fk['hair'], fk['hat'], g.env.season, False)
            big = pygame.transform.scale(tmp, (78, 120))
            bob = -2 if say and say[0] == i and int(t * 6) % 2 else 0
            s.blit(big, big.get_rect(midbottom=(x, ty + bob)))
            heads.append((x, ty - 82))
        # the table and two mugs in front of them
        pygame.draw.rect(s, (130, 92, 62), (tx - 60, ty - 40, 120, 10), border_radius=3)
        s.fill((100, 70, 48), (tx - 6, ty - 30, 12, 30))
        for mx in (tx - 34, tx + 22):
            pygame.draw.rect(s, (220, 214, 200), (mx, ty - 56, 14, 16), border_radius=2)
            pygame.draw.rect(s, (250, 246, 236), (mx, ty - 58, 14, 4), border_radius=2)
            pygame.draw.arc(s, (220, 214, 200), (mx + 10, ty - 54, 10, 10), -1.6, 1.6, 2)
        for i, fk in enumerate(INN_FOLK):
            ui.blit_text(s, fk['name'], (heads[i][0], ty + 6), 'tiny', (250, 236, 210), 'midtop')
        # the speech bubble
        if say:
            who, text = say
            lines = ui.wrap(text, 'small', 250)[:3]
            w = max(ui.fonts['small'].size(ln)[0] for ln in lines) + 28
            h = 14 + 22 * len(lines)
            hxp, hyp = heads[who]
            br = pygame.Rect(0, 0, w, h)
            br.midbottom = (hxp + (40 if who == 0 else -40), hyp - 16)
            br.clamp_ip(sr.inflate(-16, -16))
            pygame.draw.polygon(s, (255, 252, 242), [(hxp - 6 + (6 if who == 0 else -6), br.bottom - 2),
                                                     (hxp + 10 * (1 if who == 0 else -1), br.bottom - 2),
                                                     (hxp, hyp - 3)])
            pygame.draw.rect(s, (255, 252, 242), br, border_radius=12)
            pygame.draw.rect(s, (150, 120, 96), br, 2, border_radius=12)
            for j, ln in enumerate(lines):
                ui.blit_text(s, ln, (br.x + 14, br.y + 8 + j * 22), 'small', U.INK)

    def draw_inn(self, s):
        g = self.g
        ui = g.ui
        st = g.coast
        rect = T._panel(g, s, 960, 610, 'The Gull & Lantern')
        x0 = rect.x + 36
        cw = rect.w - 72
        y = rect.y + 92
        self._inn_scene(s, pygame.Rect(x0, y, cw, 250))
        y += 262
        r = pygame.Rect(x0, y, cw, 80)
        ui.tile(s, r, (250, 240, 214), (200, 150, 80))
        pygame.draw.ellipse(s, (240, 236, 226), (r.x + 18, r.y + 22, 64, 38))
        pygame.draw.ellipse(s, (236, 214, 160), (r.x + 24, r.y + 26, 52, 24))
        for i in range(4):
            s.fill((250, 250, 250), (r.x + 34 + i * 8, r.y + 10 - (int(self.t * 10 + i * 3) % 8), 2, 6))
        ui.blit_text(s, 'Harbour Chowder', (r.x + 104, r.y + 12), 'bodyb', U.INK)
        ui.blit_text(s, 'Rare sea fish bite more often for the rest of the day.', (r.x + 104, r.y + 46), 'small',
                     U.SOFT, maxw=cw - 300)
        had = g.buff('chowder')
        ui.button(s, (r.right - 180, r.y + 18, 166, 44), 'Eaten today' if had else '%d coins' % coast.CHOWDER,
                  lambda: coast.buy_chowder(g), 'primary', enabled=not had and g.coins >= coast.CHOWDER,
                  font='smallb', nav=True)
        y += 90
        r = pygame.Rect(x0, y, cw, 92)
        bought = st['round_day'] == g.day
        ui.tile(s, r, (250, 240, 214), (200, 150, 80))
        for i, mx in enumerate((r.x + 26, r.x + 50)):           # two mugs
            pygame.draw.rect(s, (220, 190, 120), (mx, r.y + 30, 18, 24), border_radius=3)
            pygame.draw.rect(s, (252, 248, 236), (mx, r.y + 26, 18, 7), border_radius=3)
            pygame.draw.arc(s, (200, 170, 100), (mx + 14, r.y + 34, 12, 12), -1.6, 1.6, 2)
        if bought and st.get('tip'):
            ui.blit_text(s, 'Old Tam leans in and lowers his voice:', (r.x + 104, r.y + 10), 'smallb', U.INK)
            yy = r.y + 36
            for ln in ui.wrap(st['tip'], 'small', cw - 300)[:2]:
                ui.blit_text(s, ln, (r.x + 104, yy), 'small', U.SOFT)
                yy += 22
        else:
            ui.blit_text(s, 'Buy the fishermen a round', (r.x + 104, r.y + 12), 'bodyb', U.INK)
            ui.blit_text(s, 'They might let you in on a secret, and a cheer brings a little luck.', (r.x + 104, r.y + 48),
                         'small', U.SOFT, maxw=cw - 300)
        ui.button(s, (r.right - 180, r.y + 24, 166, 44), 'Cheers!' if bought else '%d coins' % coast.ROUND,
                  lambda: coast.buy_round(g, self.rng), 'primary', enabled=not bought and g.coins >= coast.ROUND,
                  font='smallb', nav=True)

    def draw_ossian(self, s):
        g = self.g
        ui = g.ui
        rect = T._panel(g, s, 900, 600, "Ossian's Boatyard")
        self._head(s, rect, 'ossian')
        x0 = rect.x + 240
        cw = rect.right - 30 - x0
        y = rect.y + 100
        ui.blit_text(s, 'Fittings for your rowboat', (x0, y), 'bodyb', U.INK)
        y += 36
        for u in coast.UPGRADES:
            have = coast.has_up(g, u['id'])
            r = pygame.Rect(x0, y, cw, 88)
            ui.tile(s, r, (244, 236, 218), (150, 190, 160) if have else (190, 170, 140))
            ui.blit_text(s, u['name'], (r.x + 16, r.y + 12), 'bodyb', U.INK)
            ui.blit_text(s, u['desc'], (r.x + 16, r.y + 46), 'small', U.SOFT, maxw=cw - 200)
            if have:
                ui.button(s, (r.right - 160, r.y + 22, 146, 44), 'Fitted', None, enabled=False, font='smallb')
            else:
                ui.button(s, (r.right - 160, r.y + 22, 146, 44), '%d coins' % u['price'],
                          lambda uid=u['id']: coast.buy_up(g, uid), 'primary', enabled=g.coins >= u['price'],
                          font='smallb', nav=True)
            y += 100
        # the boat on the trestles
        st = g.coast
        stage = st['boat']
        last = len(coast.BOAT_STAGES) - 1
        y += 6
        ui.blit_text(s, "Ossian's new boat", (x0, y), 'bodyb', U.INK)
        y += 34
        r = pygame.Rect(x0, y, cw, 120)
        ui.tile(s, r, (244, 236, 218), (150, 190, 160) if stage >= last else (190, 170, 140))
        pic = pygame.Surface((110, 50), pygame.SRCALPHA)
        if stage >= last:
            pygame.draw.polygon(pic, (70, 110, 160), [(8, 24), (102, 21), (92, 40), (18, 40)])
            pic.fill((90, 150, 190), (0, 40, 110, 10))
        else:
            self._boat(pic, 55, 48, stage)
            pic.fill((0, 0, 0, 0), (0, 0, 6, 50))
        pic = pygame.transform.scale(pic, (220, 100))
        s.blit(pic, (r.x + 10, r.y + 10))
        tx = r.x + 244
        ui.blit_text(s, coast.BOAT_STAGES[stage] if stage < last else 'The %s is afloat!' % coast.BOAT_NAME,
                     (tx, r.y + 14), 'bodyb', U.INK, maxw=r.right - tx - 206)
        sub = ('She rides on her mooring by the slipway. Ossian beams every time he looks at her.' if stage >= last
               else 'Lend Ossian a hand once a day and watch her take shape. Day %d of %d.' % (stage + 1, last))
        y2 = r.y + 44
        for ln in ui.wrap(sub, 'small', r.right - tx - 206)[:3]:
            ui.blit_text(s, ln, (tx, y2), 'small', U.SOFT)
            y2 += 22
        if stage < last:
            ok = coast.can_help(g)
            ui.button(s, (r.right - 196, r.centery - 21, 182, 42), 'Lend a hand' if ok else 'More tomorrow',
                      self._help, 'primary', enabled=ok, font='smallb', nav=True)

    def draw_sol(self, s):
        g = self.g
        ui = g.ui
        st = g.coast
        rect = T._panel(g, s, 960, 580, 'The Saltmarsh Light')
        self._head(s, rect, 'sol')
        x0 = rect.x + 240
        cw = rect.right - 30 - x0
        y = rect.y + 100
        if coast.lit(g):
            ui.blit_text(s, 'The light is shining again.', (x0, y), 'h3', U.INK)
            y += 44
            for ln in ui.wrap('Every night the beam sweeps out over Kelp Rocks and the open sea. Sol keeps the lamp '
                              'trimmed and the lens polished, and the ships come home by it.', 'small', cw)[:3]:
                ui.blit_text(s, ln, (x0, y), 'small', U.SOFT)
                y += 24
            y += 20
            f = FISH_BY_ID['mariner']
            r = pygame.Rect(x0, y, cw, 96)
            caught = f['id'] in g.journal
            ui.tile(s, r, (236, 236, 244), RARITY_COLORS[5])
            self._fish_icon(s, f, (r.x + 70, r.centery), 110, 60, caught)
            ui.blit_text(s, f['name'] if caught else 'The Grey Mariner', (r.x + 140, r.y + 14), 'bodyb', U.INK)
            ui.blit_text(s, 'Caught! Sol tells everyone.' if caught else f['hint'], (r.x + 140, r.y + 46), 'small',
                         U.SOFT, maxw=cw - 160)
            return
        for ln in ui.wrap("The lamp has been dark for years. Sol can't light it alone: the lens is cracked, the oil "
                          "ran out, and a keeper needs a good supper for a long night.", 'small', cw)[:3]:
            ui.blit_text(s, ln, (x0, y), 'small', U.SOFT)
            y += 24
        y += 14
        basket = {b['id'] for b in g.basket}
        for tsk in coast.LIGHT_TASKS:
            done = tsk['id'] in st['tasks']
            r = pygame.Rect(x0, y, cw, 78)
            ui.tile(s, r, (226, 238, 228) if done else (244, 236, 218), (120, 180, 130) if done else (190, 170, 140))
            ui.blit_text(s, tsk['name'], (r.x + 16, r.y + 10), 'bodyb', U.INK)
            ui.blit_text(s, tsk['desc'], (r.x + 16, r.y + 42), 'tiny', U.SOFT, maxw=cw - 210)
            if done:
                ui.button(s, (r.right - 170, r.y + 17, 156, 44), 'Done', None, enabled=False, font='smallb')
            else:
                ok = {'glass': st['glass'] >= coast.GLASS_NEED, 'bass': 'seabass' in basket,
                      'oil': g.coins >= coast.OIL_COST}[tsk['id']]
                label = {'glass': 'Give glass  %d/%d' % (min(st['glass'], coast.GLASS_NEED), coast.GLASS_NEED),
                         'bass': 'Give sea bass' if ok else 'No sea bass', 'oil': 'Pay %d' % coast.OIL_COST}[tsk['id']]
                ui.button(s, (r.right - 170, r.y + 17, 156, 44), label, lambda tid=tsk['id']: self._task(tid),
                          'primary', enabled=ok, font='smallb', nav=True)
            y += 86
        y += 6
        ui.button(s, (x0, y, cw, 54), 'Light the lamp!' if coast.can_light(g) else 'Light the lamp  (%d of 3 ready)'
                  % len(st['tasks']), self._light, 'primary', enabled=coast.can_light(g), font='h3',
                  nav=True)
        y += 64
        ui.blit_text(s, 'Each thing you bring, you can watch the work happen on the lighthouse.', (x0, y), 'tiny',
                     U.SOFT, maxw=cw)

    def draw_kit(self, s):
        g = self.g
        ui = g.ui
        st = g.coast
        rect = T._panel(g, s, 940, 600, "Kit's Shell Collection")
        self._head(s, rect, 'kit')
        x0 = rect.x + 240
        cw = rect.right - 30 - x0
        y = rect.y + 96
        have = sum(1 for sh in coast.SHELLS if st['shells'].get(sh['id']))
        spare = coast.spares(g)
        ui.blit_text(s, 'Shells found: %d of %d' % (have, len(coast.SHELLS)), (x0, y), 'bodyb', U.INK)
        ui.blit_text(s, 'Spare shells to swap: %d' % spare, (x0 + cw, y + 4), 'small', U.SOFT, 'topright')
        y += 38
        tw = (cw - 3 * 10) // 4
        for i, sh in enumerate(coast.SHELLS):
            r = pygame.Rect(x0 + (i % 4) * (tw + 10), y + (i // 4) * 112, tw, 102)
            n = st['shells'].get(sh['id'], 0)
            ui.tile(s, r, (250, 244, 228) if n else (232, 226, 214), sh['col'] if n else (190, 180, 168))
            if n:
                shell_icon(s, sh['id'], (r.centerx, r.y + 36), 4)
                ui.blit_text(s, '%s  x%d' % (sh['name'], n), (r.centerx, r.bottom - 24), 'tiny', U.INK, 'center',
                             maxw=r.w - 8)
            else:
                ui.blit_text(s, '?', (r.centerx, r.y + 22), 'h3', (180, 170, 160), 'center')
                ui.blit_text(s, sh['name'], (r.centerx, r.y + 46), 'tiny', U.SOFT, 'center', maxw=r.w - 8)
                cost = coast.swap_cost(sh['id'])
                ui.button(s, (r.x + 8, r.bottom - 36, r.w - 16, 28), 'Swap %d spares' % cost,
                          lambda sid=sh['id']: coast.swap_shell(g, sid), 'primary', enabled=spare >= cost,
                          font='tiny', nav=True)
        y += 2 * 112 + 8
        if coast.needs_glass(g):
            r = pygame.Rect(x0, y, cw, 66)
            ui.tile(s, r, (236, 244, 246), (120, 170, 190))
            for j, gl in enumerate(coast.GLASS):
                pygame.draw.rect(s, gl['col'], (r.x + 16 + j * 14, r.y + 26 + (j % 2) * 6, 11, 9), border_radius=3)
            ui.blit_text(s, 'Sea glass for the lighthouse lens: %d of %d' % (st['glass'], coast.GLASS_NEED),
                         (r.x + 70, r.y + 10), 'smallb', U.INK, maxw=cw - 260)
            ui.blit_text(s, 'Kit keeps a bucket of it. %d spare shells for a piece.' % coast.GLASS_SWAP,
                         (r.x + 70, r.y + 38), 'tiny', U.SOFT, maxw=cw - 260)
            ui.button(s, (r.right - 180, r.y + 12, 166, 42), 'Swap %d spares' % coast.GLASS_SWAP,
                      lambda: coast.swap_glass(g), 'primary', enabled=spare >= coast.GLASS_SWAP, font='smallb',
                      nav=True)
            y += 76
        txt = ('Every one! The harbour paid out %d coins for the full set.' % coast.SHELL_REWARD if st['shell_done']
               else 'Find every kind and the harbour pays a %d-coin prize. New shells wash up each morning.'
               % coast.SHELL_REWARD)
        ui.blit_text(s, txt, (x0, y + 4), 'small', U.SOFT, maxw=cw)
