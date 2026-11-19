"""Inside the Fernwick Aquarium: a hall you can walk through, with your donated fish swimming in themed exhibits.

Every fish in the game belongs to one exhibit (exhibit_of). The fish you have donated swim in it; the rest of the
exhibit waits, with an empty name card. There are benches to sit on, a few neighbours looking at the tanks, and
Juniper's desk by the door, where you donate. Finishing an exhibit earns a reward once.

Runs under Game.overlay 'aquarium' with Game.aqscene, drawn and framed like the ice-fishing scene.
"""
import math
import random

import pygame

import actors
import art
import look as looks
import ui as U
from art import lerp_c, darken, add_glow
from data import FISH, FISH_BY_ID, RARITY_COLORS

W, H = 640, 360
FLOOR = 304                  # where feet touch the floor
WALL_BOT = 262               # the back wall meets the floor here
WALK = 62.0
DOOR_X = 40
DESK_X = 128
OPEN, CLOSE = 540, 1020      # the same hours as the door on the street
HEADLESS = False             # set by main at start-up, with its clock formatter
fmt_clock = str

EXHIBITS = [
    dict(id='home', name='Lantern Lake', w=190, style='lake', reward=300, bench=True,
         blurb='The fish you meet from the dock: an everyday crowd, and never boring.'),
    dict(id='cove', name='Lily Cove', w=110, style='cove', reward=150,
         blurb='Warm, weedy and full of lily pads. The fish here like to hide.'),
    dict(id='creek', name='Willow Creek', w=120, style='creek', reward=200,
         blurb='A tank with a current running through it, for fish that like moving water.'),
    dict(id='deep', name='The Deep', w=120, style='deep', reward=250, bench=True,
         blurb='Kept dark and cold, like the middle of the lake. Give your eyes a moment.'),
    dict(id='legends', name='Legends of the Lake', w=170, style='legend', reward=600, bench=True,
         blurb="Fish most people only hear about in stories. Juniper still can't quite believe it."),
    dict(id='ice', name='Under the Ice', w=110, style='ice', reward=200,
         blurb='Cold-water fish from the winter holes at Lily Cove.'),
    dict(id='pots', name='Crab Pot Corner', w=120, style='pots', reward=150,
         blurb='Crayfish, crabs and a snail, clicking about on the rocks.'),
    dict(id='warm', name='Spring & Summer', w=110, style='warm', reward=200, bench=True,
         blurb='Fish of the warm months, among reeds and sunlight.'),
    dict(id='cold', name='Autumn & Winter', w=110, style='cold', reward=200,
         blurb='Fish of the cold months, among fallen leaves and bare twigs.'),
    dict(id='wonders', name='Weather & Wonders', w=130, style='wonders', reward=400,
         blurb='Storm fish, festival fish, and fish that fell with the stars.'),
    dict(id='harbour', name='Harbour Waters', w=140, style='harbour', reward=350, bench=True,
         blurb='Sea fish from under Saltmarsh Pier, in a tank of real salt water. Nell brings it up in buckets.'),
    dict(id='kelp', name='Kelp Forest', w=120, style='kelp', reward=350,
         blurb='Tall kelp and rock pools from Kelp Rocks, and everything that hides in them.'),
]
EX_BY_ID = {e['id']: e for e in EXHIBITS}
CURATOR = 5                  # exhibits to finish for the Curator badge
_x = 200
for _e in EXHIBITS:          # tanks along the back wall, left to right
    _top, _h = {'deep': (74, 150), 'pots': (150, 70), 'legend': (82, 140)}.get(_e['style'], (96, 118))
    _e['rect'] = pygame.Rect(_x, _top, _e['w'], _h)
    _e['cx'] = _x + _e['w'] // 2
    _x += _e['w'] + 40
AQ_W = _x + 70               # the far wall
BENCHES = [e['cx'] for e in EXHIBITS if e.get('bench')]

WATER = {'lake': ((74, 136, 150), (28, 70, 86)), 'cove': ((84, 146, 112), (34, 80, 58)),
         'creek': ((116, 176, 192), (48, 100, 120)), 'deep': ((26, 44, 76), (6, 12, 28)),
         'legend': ((64, 112, 152), (14, 30, 58)), 'ice': ((172, 210, 230), (66, 116, 148)),
         'pots': ((96, 126, 124), (50, 70, 70)), 'warm': ((116, 176, 152), (48, 108, 88)),
         'cold': ((96, 124, 154), (40, 58, 90)), 'wonders': ((44, 42, 96), (10, 10, 40)),
         'harbour': ((70, 130, 160), (20, 56, 86)), 'kelp': ((80, 140, 130), (24, 60, 60))}
LINES = ["{fish}! I didn't know they got that big.", 'Look at the {fish}. Did you really catch it yourself?',
         'I could watch the {fish} all day.', 'The {fish} keeps looking at me. I think it likes me.',
         "Juniper says the {fish} came from you. Well done!"]
LEGEND_LINES = ['My grandmother told stories about the {fish}. I thought she made it up!',
                "The {fish}... I've waited my whole life to see one."]
EMPTY_LINES = ['{ex} is still empty. I wonder what will live here one day.',
               "Nothing in {ex} yet. You'll fix that, won't you?"]


def exhibit_of(f):
    """Which exhibit a fish belongs in (every fish has exactly one)."""
    if f['rarity'] == 5:
        return 'legends'
    if f.get('method') == 'sea':
        return 'harbour' if f.get('spot') == 'pier' else 'kelp'
    if f.get('event') or f.get('method') in ('storm', 'aurora'):
        return 'wonders'
    sp = f.get('spot')
    if sp in ('cove', 'deep', 'creek', 'ice'):
        return sp
    if sp == 'pot':
        return 'pots'
    if f.get('year'):
        return 'deep'                       # the year-two fish arrive in the Deep
    if f['seasons'] is not None:
        return 'warm' if min(f['seasons']) <= 1 else 'cold'
    return 'home'


MEMBERS = {e['id']: [f for f in FISH if exhibit_of(f) == e['id']] for e in EXHIBITS}


def shown(g, ex):
    return [f for f in MEMBERS[ex] if f['id'] in g.museum]


def complete(g, ex):
    return len(shown(g, ex)) == len(MEMBERS[ex])


def finished(g):
    return list(g.stats.get('exhibits', []))


def is_open(g):
    return OPEN <= g.minute < CLOSE


# ---------------------------------------------------------------- entering and donating
def enter(g):
    g.aqscene = AquariumScene(g)
    g.overlay = 'aquarium'
    g.release_holds()
    g.audio.play('creak', 0.4)
    catch_up(g)


def catch_up(g):
    """Exhibits you filled before the new hall opened (older saves) pay out the first time you walk in."""
    done = g.stats.setdefault('exhibits', [])
    new = [e for e in EXHIBITS if e['id'] not in done and complete(g, e['id'])]
    if not new:
        return 0
    total = sum(e['reward'] for e in new)
    done.extend(e['id'] for e in new)
    g.coins += total
    g.audio.play('jingle4', 0.6)
    many = 'One of them is' if len(new) == 1 else '%d of them are' % len(new)
    g.toast('Juniper has set out the new exhibits. %s already complete, thanks to you! She gives you %d coins.'
            % (many, total), (90, 140, 180))
    g.check_badges()
    return total


def on_donate(g, fid):
    """Called by Game.donate: the fish joins its tank, and a finished exhibit pays out once."""
    f = FISH_BY_ID[fid]
    ex = exhibit_of(f)
    sc = getattr(g, 'aqscene', None)
    if sc is not None:
        sc.add_fish(f, splash=True)
    done = g.stats.setdefault('exhibits', [])
    if complete(g, ex) and ex not in done:
        done.append(ex)
        e = EX_BY_ID[ex]
        g.coins += e['reward']
        g.audio.play('jingle4', 0.6)
        g.toast('The %s exhibit is complete! Juniper gives you %d coins.' % (e['name'], e['reward']), (90, 140, 180))
        if sc is not None:
            sc.sparkle(e)
        g.check_badges()


# ---------------------------------------------------------------- static art
_STATIC = {}


def _gravel(s, r, rng, col):
    for _ in range(r.w // 2):
        x = rng.randrange(r.x, r.right - 2)
        y = rng.randrange(r.bottom - 8, r.bottom - 1)
        s.fill(lerp_c(col, (220, 210, 190), rng.uniform(0, 0.5)), (x, y, rng.choice((1, 2, 2, 3)), 2))


def _tank_back(s, e, rng):
    """Water, bottom and the fixed decorations of one tank."""
    r = e['rect']
    st = e['style']
    top, bot = WATER[st]
    if st == 'legend':
        cx, cy, rad = r.centerx, r.centery, r.w // 2 - 2
        for y in range(r.y, r.bottom):
            k = (y - r.y) / r.h
            half = int(math.sqrt(max(0, rad * rad - (y - cy) ** 2)))
            if half:
                s.fill(lerp_c(top, bot, k), (cx - half, y, half * 2, 1))
        pygame.draw.circle(s, (176, 140, 70), (cx, cy), rad + 3, 4)          # a brass porthole frame
        pygame.draw.circle(s, (226, 192, 110), (cx, cy), rad + 3, 1)
        for a in range(0, 360, 30):
            px, py = cx + math.cos(math.radians(a)) * (rad + 3), cy + math.sin(math.radians(a)) * (rad + 3)
            s.fill((240, 214, 140), (int(px) - 1, int(py) - 1, 2, 2))
        band = cy + rad - 12                       # sand and rocks along the bottom, inside the porthole
        for y in range(band, cy + rad):
            hw = int(math.sqrt(max(0, rad * rad - (y - cy) ** 2)))
            s.fill((150, 140, 116), (cx - hw, y, hw * 2, 1))
        half = int(math.sqrt(rad * rad - (band - 4 - cy) ** 2)) - 7
        for i in range(8):
            x = cx - half + i * (half * 2) // 7
            hgt = rng.randrange(6, 11)
            pygame.draw.ellipse(s, lerp_c((70, 76, 90), (96, 100, 110), i % 2), (x - 6, band - hgt // 2, 12, hgt))
        return
    for y in range(r.y, r.bottom):
        s.fill(lerp_c(top, bot, (y - r.y) / r.h), (r.x, y, r.w, 1))
    sand = {'deep': (60, 60, 70), 'ice': (150, 160, 170), 'pots': (120, 110, 96), 'wonders': (40, 40, 70),
            'cold': (120, 100, 80)}.get(st, (176, 160, 120))
    s.fill(sand, (r.x, r.bottom - 8, r.w, 8))
    _gravel(s, r, rng, sand)
    if st == 'cove':                       # lily pads on the surface, with their shadows below
        for i in range(4):
            x = r.x + 10 + i * (r.w - 20) // 3
            pygame.draw.ellipse(s, (60, 120, 70), (x - 9, r.y, 18, 5))
            pygame.draw.ellipse(s, darken(top, 0.18), (x - 7, r.y + 12, 14, 4))
        pygame.draw.circle(s, (240, 200, 210), (r.x + 30, r.y + 1), 2)
    elif st == 'ice':                      # the ice ceiling
        s.fill((236, 244, 250), (r.x, r.y, r.w, 9))
        s.fill((200, 224, 238), (r.x, r.y + 9, r.w, 3))
        for i in range(5):
            s.fill((210, 230, 244), (r.x + 8 + i * 22, r.y + 12, 2, 4 + i % 3 * 2))
    elif st == 'pots':                     # rocks to clamber over
        for i in range(6):
            x = r.x + 6 + i * (r.w - 12) // 5
            pygame.draw.ellipse(s, lerp_c((110, 104, 96), (80, 76, 70), i % 2), (x - 10, r.bottom - 22, 22, 18))
        s.fill((150, 110, 70), (r.right - 30, r.bottom - 30, 20, 16))              # a little crab pot
        for x in range(r.right - 30, r.right - 10, 4):
            s.fill((96, 70, 46), (x, r.bottom - 30, 1, 16))
    elif st == 'wonders':                  # a starry back wall
        for _ in range(26):
            s.fill((220, 220, 255), (rng.randrange(r.x, r.right), rng.randrange(r.y, r.bottom - 12), 1, 1))
    elif st == 'warm':
        for i in range(3):
            x = r.x + 18 + i * 34
            pygame.draw.circle(s, (240, 220, 120), (x, r.y + 14), 3)
    elif st == 'harbour':                  # an old pier leg with barnacles, and a sunken lobster pot
        px = r.x + r.w - 34
        s.fill((84, 62, 46), (px, r.y, 10, r.h - 8))
        s.fill((70, 96, 64), (px, r.y + 30, 10, 8))
        for i in range(8):
            s.set_at((px + 1 + i % 8, r.y + 44 + (i * 7) % 40), (210, 206, 196))
        s.fill((150, 100, 70), (r.x + 12, r.bottom - 24, 22, 16))
        for x in range(r.x + 12, r.x + 34, 4):
            s.fill((110, 70, 50), (x, r.bottom - 24, 1, 16))
    elif st == 'kelp':                     # rocks along the bottom (the kelp itself sways, drawn live)
        for i in range(5):
            x = r.x + 4 + i * (r.w - 8) // 4
            pygame.draw.ellipse(s, lerp_c((90, 90, 96), (70, 70, 76), i % 2), (x - 12, r.bottom - 24, 26, 20))
        s.fill((240, 140, 80), (r.x + 40, r.bottom - 16, 5, 1))
        s.fill((240, 140, 80), (r.x + 42, r.bottom - 18, 1, 5))
    elif st == 'cold':
        for i in range(9):
            x, y = rng.randrange(r.x + 4, r.right - 4), rng.randrange(r.bottom - 10, r.bottom - 3)
            s.fill(rng.choice([(200, 110, 50), (180, 80, 50), (220, 160, 60)]), (x, y, 3, 2))
        pygame.draw.lines(s, (90, 70, 60), False, [(r.x + 16, r.bottom - 8), (r.x + 22, r.bottom - 30),
                                                    (r.x + 30, r.bottom - 40)], 2)
    # the tank's wooden frame and lip
    pygame.draw.rect(s, (92, 66, 50), r.inflate(8, 8), 4, border_radius=2)
    pygame.draw.rect(s, (130, 96, 70), r.inflate(8, 8), 1, border_radius=2)
    s.fill((92, 66, 50), (r.x - 6, r.bottom + 4, r.w + 12, 4))


def _build_static():
    if 'hall' in _STATIC:
        return _STATIC['hall']
    s = pygame.Surface((AQ_W, H))
    rng = random.Random(21)
    wall, wall2 = (92, 132, 140), (82, 120, 130)
    for y in range(0, WALL_BOT):
        s.fill(lerp_c((60, 88, 100), wall, min(1.0, y / 120.0)), (0, y, AQ_W, 1))
    for x in range(0, AQ_W, 26):                   # plaster panels
        s.fill(wall2, (x, 40, 1, WALL_BOT - 90))
    # the ceiling: beams and a cornice
    s.fill((48, 40, 44), (0, 0, AQ_W, 26))
    for x in range(0, AQ_W, 60):
        s.fill((70, 56, 50), (x, 0, 10, 30))
    s.fill((200, 196, 180), (0, 26, AQ_W, 4))
    s.fill((150, 146, 132), (0, 30, AQ_W, 2))
    # wainscot below the tanks
    s.fill((112, 80, 60), (0, WALL_BOT - 40, AQ_W, 40))
    for x in range(0, AQ_W, 22):
        pygame.draw.rect(s, (96, 68, 50), (x + 3, WALL_BOT - 36, 16, 30), 1)
    s.fill((140, 104, 76), (0, WALL_BOT - 42, AQ_W, 3))
    # the floor: checkered tiles, darker towards you
    for y in range(WALL_BOT, H):
        k = (y - WALL_BOT) / (H - WALL_BOT)
        s.fill(lerp_c((176, 168, 150), (130, 120, 104), k), (0, y, AQ_W, 1))
    for row, y in enumerate(range(WALL_BOT, H, 10)):
        for x in range(-(row % 2) * 12, AQ_W, 24):
            s.fill(lerp_c((150, 140, 124), (112, 102, 88), (y - WALL_BOT) / (H - WALL_BOT)), (x, y, 12, 10))
    s.fill((60, 46, 40), (0, WALL_BOT, AQ_W, 2))
    # the entrance: a door to the street with daylight, a coat stand, a rope line and Juniper's desk
    s.fill((60, 46, 40), (DOOR_X - 18, 168, 36, WALL_BOT - 168))
    s.fill((214, 226, 220), (DOOR_X - 14, 174, 28, WALL_BOT - 174))
    s.fill((180, 200, 190), (DOOR_X - 14, 230, 28, WALL_BOT - 230))
    s.fill((60, 46, 40), (DOOR_X - 1, 174, 2, WALL_BOT - 174))
    pygame.draw.arc(s, (60, 46, 40), (DOOR_X - 18, 152, 36, 34), 0, math.pi, 4)
    s.fill((80, 60, 46), (86, 210, 2, FLOOR - 210))                     # coat stand
    for dy in (0, 8):
        pygame.draw.line(s, (80, 60, 46), (80, 212 + dy), (94, 212 + dy), 1)
    s.fill((170, 80, 70), (90, 214, 6, 14))
    # a lake map mural at the far end
    mx = AQ_W - 60
    s.fill((236, 226, 200), (mx - 34, 80, 68, 90))
    pygame.draw.rect(s, (110, 80, 60), (mx - 36, 78, 72, 94), 3)
    pygame.draw.ellipse(s, (120, 170, 200), (mx - 26, 100, 52, 44))
    pygame.draw.ellipse(s, (90, 140, 90), (mx - 30, 90, 60, 64), 2)
    for px, py in ((mx - 16, 108), (mx + 12, 130), (mx + 2, 116)):
        s.fill((200, 70, 70), (px, py, 2, 2))
    # potted ferns in the gaps between tanks
    for i, e in enumerate(EXHIBITS[:-1]):
        if i % 2:
            continue
        px = e['rect'].right + 20
        s.fill((170, 110, 80), (px - 6, FLOOR - 14, 12, 12))
        s.fill((140, 90, 64), (px - 7, FLOOR - 15, 14, 3))
        for j in range(7):
            ang = -math.pi / 2 + (j - 3) * 0.32
            pygame.draw.line(s, (70, 130, 80), (px, FLOOR - 14), (px + math.cos(ang) * 12, FLOOR - 14 + math.sin(ang) * 14), 2)
    for e in EXHIBITS:
        _tank_back(s, e, rng)
        r = e['rect']
        py = (r.bottom if e['style'] != 'legend' else r.bottom + 4) + 14   # the brass name plate
        if e['style'] == 'pots':
            s.fill((150, 140, 130), (r.x - 6, r.bottom + 8, r.w + 12, WALL_BOT - 40 - r.bottom - 8))  # stone plinth
            for y in range(r.bottom + 14, WALL_BOT - 40, 6):
                s.fill((130, 120, 112), (r.x - 6, y, r.w + 12, 1))
            py = r.bottom + 12
        w = max(60, min(r.w - 10, len(e['name']) * 5 + 14))
        s.fill((120, 92, 50), (r.centerx - w // 2 - 1, py - 1, w + 2, 12))
        s.fill((214, 182, 108), (r.centerx - w // 2, py, w, 10))
        _sign(s, e['name'].upper(), (r.centerx, py + 5), (70, 50, 30))
    _STATIC['hall'] = s
    return s


def _sign(s, text, center, col):
    import town
    town.sign_text(s, text, center, col)


def _glass():
    if 'glass' not in _STATIC:
        gl = {}
        for e in EXHIBITS:
            r = e['rect']
            surf = pygame.Surface(r.size, pygame.SRCALPHA)
            for i in range(3):
                x0 = 8 + i * 9
                pygame.draw.line(surf, (255, 255, 255, 34 - i * 8), (x0, r.h - 1), (x0 + r.h // 2, 0), 3 - i)
            if e['style'] == 'legend':
                m = pygame.Surface(r.size, pygame.SRCALPHA)
                pygame.draw.circle(m, (255, 255, 255, 255), (r.w // 2, r.h // 2), r.w // 2 - 2)
                surf.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            gl[e['id']] = surf
        _STATIC['glass'] = gl
        _STATIC['tankglow'] = art.glow(40, (120, 200, 230))
        _STATIC['lampglow'] = art.glow(22, (255, 214, 150))
    return _STATIC['glass']


# ---------------------------------------------------------------- the scene
class AquariumScene:
    def __init__(self, g, rng=None):
        self.g = g
        self.rng = rng or random.Random()
        self.t = 0.0
        self.x = DOOR_X + 26.0
        self.face = 1
        self.step = 0.0
        self.target = None
        self.on_arrive = None
        self.scroll = 0.0
        self.panel = None               # None, 'donate' or 'exhibit'
        self.sel = None                 # the exhibit the 'exhibit' panel shows
        self.sitting = None             # the bench x you're sitting on
        self.sit_t = 0.0
        self.fish = []
        self.fx = []                    # sparkles and splashes: [x, y, vx, vy, life, colour]
        self.done = False
        self.closing = None
        self.holds = set()
        self.said = {}
        for f in FISH:
            if f['id'] in g.museum:
                self.add_fish(f)
        self.visitors = self._visitors()
        _build_static()
        _glass()

    # ------------------------------------------------------------ fish
    def add_fish(self, f, splash=False):
        e = EX_BY_ID[exhibit_of(f)]
        r = self._swim_rect(e)
        rng = self.rng
        big = f['rarity'] >= 4
        k = 1.0 if big else 0.75
        spr = art.fish_sprite(f, 1)
        spr = pygame.transform.scale(spr, (int(spr.get_width() * k), int(spr.get_height() * k)))
        crawl = e['style'] == 'pots'
        fish = dict(spec=f, ex=e['id'], spr=spr, flip=pygame.transform.flip(spr, True, False),
                    x=rng.uniform(r.x, r.right), y=(r.bottom - 6) if crawl else rng.uniform(r.y, r.bottom),
                    vx=rng.choice((-1, 1)) * (rng.uniform(4, 9) if crawl else rng.uniform(8, 18) * (0.6 if big else 1)),
                    ty=rng.uniform(r.y, r.bottom), wait=0.0, crawl=crawl, ph=rng.uniform(0, 6))
        if splash:
            fish['y'] = r.y
            for _ in range(14):
                self.fx.append([fish['x'], e['rect'].y + 4, rng.uniform(-20, 20), rng.uniform(-30, 5), 0.8,
                                (220, 240, 255)])
            self.g.audio.play('plop', 0.5)
        self.fish.append(fish)

    def _swim_rect(self, e):
        r = e['rect']
        if e['style'] == 'legend':
            return pygame.Rect(r.centerx - 44, r.centery - 34, 88, 64)
        top = r.y + (16 if e['style'] == 'ice' else 10)
        return pygame.Rect(r.x + 14, top, r.w - 28, r.bottom - 14 - top)

    def _update_fish(self, dt):
        rng = self.rng
        for f in self.fish:
            r = self._swim_rect(EX_BY_ID[f['ex']])
            if f['wait'] > 0:
                f['wait'] -= dt
                continue
            f['x'] += f['vx'] * dt
            if f['x'] < r.x or f['x'] > r.right:
                f['x'] = max(r.x, min(r.right, f['x']))
                f['vx'] = -f['vx']
                if rng.random() < 0.4:
                    f['wait'] = rng.uniform(0.5, 2.0)
            if f['crawl']:
                f['y'] = r.bottom + 4
                if rng.random() < dt * 0.3:
                    f['wait'] = rng.uniform(1.0, 3.0)
                continue
            if rng.random() < dt * 0.25:
                f['ty'] = rng.uniform(r.y, r.bottom)
            f['y'] += (f['ty'] - f['y']) * min(1.0, dt * 0.6)
            if rng.random() < dt * 0.05:
                f['vx'] = -f['vx']

    def sparkle(self, e):
        r = e['rect']
        for _ in range(40):
            self.fx.append([self.rng.uniform(r.x, r.right), self.rng.uniform(r.y, r.bottom), self.rng.uniform(-10, 10),
                            self.rng.uniform(-30, -6), 1.6, (255, 230, 140)])

    # ------------------------------------------------------------ neighbours looking at the tanks
    def _visitors(self):
        import town
        g = self.g
        year = (g.day - 1) // 28
        rng = random.Random(g.day * 31 + 7)
        pool = [k for k in town.FOLK_ORDER if k != 'juniper' and town.FOLK[k].get('new_in_year', 0) <= year]
        out = []
        for k in rng.sample(pool, 2):
            out.append(dict(k=k, x=float(rng.choice(EXHIBITS)['cx'] + rng.uniform(-20, 20)), face=1, step=0.0,
                            goal=None, wait=rng.uniform(1, 4), ex=None, em=None, em_t=0.0, line=None))
        return out

    def _ex_at(self, x):
        return min(EXHIBITS, key=lambda e: abs(e['cx'] - x))

    def _update_visitors(self, dt):
        rng = self.rng
        for v in self.visitors:
            v['em_t'] = max(0.0, v['em_t'] - dt)
            if v['goal'] is None:
                v['wait'] -= dt
                v['step'] = 0.0
                e = self._ex_at(v['x'])
                if v['ex'] != e['id']:
                    v['ex'] = e['id']
                    v['line'] = self._line(v, e)
                if v['wait'] <= 0:
                    if rng.random() < 0.5:
                        v['goal'] = rng.choice(EXHIBITS)['cx'] + rng.uniform(-24, 24)
                    else:
                        v['em'], v['em_t'], v['wait'] = rng.choice(('heart', 'note', 'bang')), 2.0, rng.uniform(3, 7)
            else:
                d = v['goal'] - v['x']
                if abs(d) < 1.5:
                    v['goal'] = None
                    v['wait'] = rng.uniform(4, 10)
                    v['face'] = rng.choice((-1, 1))
                else:
                    v['face'] = 1 if d > 0 else -1
                    v['x'] += v['face'] * 20 * dt
                    v['step'] += dt * 7

    def _line(self, v, e):
        rng = random.Random(hash((v['k'], e['id'], self.g.day)) & 0xffff)
        have = shown(self.g, e['id'])
        if not have:
            return rng.choice(EMPTY_LINES).format(ex=e['name'])
        f = rng.choice(have)
        pool = LEGEND_LINES if e['id'] == 'legends' else LINES
        return rng.choice(pool).format(fish=f['name'])

    # ------------------------------------------------------------ what's in reach
    def nearest(self):
        x = self.x
        if abs(x - DOOR_X) < 22:
            return ('door', None)
        if abs(x - DESK_X) < 24:
            return ('desk', None)
        for v in self.visitors:
            if abs(v['x'] - x) < 12:
                return ('folk', v)
        for bx in BENCHES:
            if abs(bx - x) < 12:
                return ('bench', bx)
        for e in EXHIBITS:
            if abs(e['cx'] - x) < e['w'] // 2 + 8:
                return ('exhibit', e)
        return None

    def prompt(self):
        if self.sitting is not None:
            return 'Stand up'
        n = self.nearest()
        if not n:
            return None
        kind, v = n
        import town
        if kind == 'door':
            return 'Back out to the street'
        if kind == 'desk':
            can = sum(1 for b in self.g.basket if b['id'] in FISH_BY_ID and b['id'] not in self.g.museum)
            return 'Donate fish  (%d new in your basket)' % can if can else 'Talk to Juniper'
        if kind == 'folk':
            return 'Chat with %s' % town.FOLK[v['k']]['name']
        if kind == 'bench':
            return 'Sit and watch the fish'
        return 'Look at %s  (%d/%d)' % (v['name'], len(shown(self.g, v['id'])), len(MEMBERS[v['id']]))

    def interact(self):
        g = self.g
        if self.sitting is not None:
            self.stand()
            return
        n = self.nearest()
        if not n:
            return
        kind, v = n
        if kind == 'door':
            self.leave()
        elif kind == 'desk':
            self.panel = 'donate'
            g.audio.play('page', 0.6)
        elif kind == 'folk':
            self._chat(v)
        elif kind == 'bench':
            self.sit(v)
        else:
            self.sel = v['id']
            self.panel = 'exhibit'
            g.audio.play('page', 0.6)

    def _chat(self, v):
        import town
        g = self.g
        v['em'], v['em_t'] = 'heart', 2.0
        v['face'] = 1 if self.x > v['x'] else -1
        self.said[v['k']] = 4.0
        key = 'aq_' + v['k']
        if g.town_day.get(key) != g.day:
            g.town_day[key] = g.day
            g.add_friend(v['k'], 2)
        g.audio.play('chime%d' % (town.FOLK_ORDER.index(v['k']) % 5), 0.3)

    def sit(self, bx):
        g = self.g
        self.sitting = bx
        self.sit_t = 0.0
        self.x = float(bx)
        self.target = None
        if g.town_day.get('aq_sit') != g.day:
            g.town_day['aq_sit'] = g.day
            g.luck = min(3.0, g.luck + 0.3)
            g.toast('You sit a while and watch the fish drift by. It is very calming.', (90, 140, 170))

    def stand(self):
        self.sitting = None

    def leave(self):
        g = self.g
        self.done = True
        g.aqscene = None
        if g.overlay == 'aquarium':
            g.overlay = None
        import town
        g.town.x = float(town.PLACE_BY_ID['museum']['door'])
        g.town.target = None
        g.release_holds()
        g.audio.play('creak', 0.4)

    # ------------------------------------------------------------ input
    def key(self, k):
        if k == pygame.K_ESCAPE:
            if self.panel:
                self.close_panel()
            elif self.sitting is not None:
                self.stand()
            else:
                self.leave()
            return
        if self.panel:
            if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and self.panel == 'exhibit':
                self.close_panel()
            return
        if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_w, pygame.K_UP):
            self.interact()
        elif k in (pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT) and self.sitting is not None:
            self.stand()

    def close_panel(self):
        self.panel = None
        self.g.audio.play('page', 0.5)

    def press(self, src='mouse'):
        """A click in the hall: walk there, and use whatever is there."""
        if self.panel:
            return
        if self.sitting is not None:
            self.stand()
            return
        wx, wy = self.g.s2w(*self.g.ui.mouse)
        tx = max(14.0, min(AQ_W - 14.0, wx + self.scroll))
        for v in self.visitors:
            if abs(v['x'] - tx) < 8 and FLOOR - 34 < wy < FLOOR + 2:
                return self.walk_to(v['x'] - 10 * (1 if v['x'] > self.x else -1), lambda v=v: self._chat(v))
        for bx in BENCHES:
            if abs(bx - tx) < 16 and FLOOR - 20 < wy < FLOOR + 4:
                return self.walk_to(bx, lambda bx=bx: self.sit(bx))
        if abs(tx - DESK_X) < 20 and wy > 220:
            return self.walk_to(DESK_X + 14, self.interact)
        if abs(tx - DOOR_X) < 18 and wy > 150:
            return self.walk_to(DOOR_X, self.leave)
        for e in EXHIBITS:
            if e['rect'].inflate(8, 8).collidepoint(tx, wy):
                return self.walk_to(e['cx'], lambda e=e: (setattr(self, 'sel', e['id']), setattr(self, 'panel', 'exhibit')))
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
        for p in self.fx:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 30 * dt
            p[4] -= dt
        self.fx = [p for p in self.fx if p[4] > 0]
        for k in list(self.said):
            self.said[k] -= dt
            if self.said[k] <= 0:
                del self.said[k]
        self._update_fish(dt)
        self._update_visitors(dt)
        if not is_open(g):
            if self.closing is None:
                self.closing = 2.5
                self.panel = None
                g.toast("Juniper: We're closing up for the night! Come back tomorrow.", (90, 140, 180))
            self.closing -= dt
            if self.closing <= 0:
                self.leave()
                return
        moving = 0
        if self.panel is None and self.sitting is None:
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
            self.x = max(14.0, min(AQ_W - 14.0, self.x + moving * WALK * dt))
            before = self.step
            self.step += dt * 9
            if int(before / math.pi) != int(self.step / math.pi):
                g.audio.step(0.22)
        else:
            self.step = 0.0
        if self.sitting is not None:
            self.sit_t += dt
        want = max(0.0, min(AQ_W - W, self.x - W / 2))
        self.scroll += (want - self.scroll) * min(1.0, dt * 5)

    def audio_ctx(self):
        return {'town': True}

    # ------------------------------------------------------------ for the bot: a little tour
    def auto(self, dt, rng):
        g = self.g
        if not hasattr(self, '_plan'):
            self._plan = ['desk'] + [e['cx'] for e in rng.sample(EXHIBITS, 3)] + ['bench', 'door']
            self._sat = 0.0
        if self.panel == 'donate':
            for fid in sorted({b['id'] for b in g.basket}):
                if fid in FISH_BY_ID and fid not in g.museum:
                    g.donate(fid)
            self.close_panel()
            return
        if self.panel:
            self.close_panel()
            return
        if self.sitting is not None:
            self._sat += dt
            if self._sat > 3.0:
                self.stand()
            return
        if self.target is not None or not self._plan:
            return
        step = self._plan.pop(0)
        if step == 'desk':
            self.walk_to(DESK_X + 10, self.interact)
        elif step == 'bench':
            bx = rng.choice(BENCHES)
            self.walk_to(bx, lambda: self.sit(bx))
        elif step == 'door':
            self.walk_to(DOOR_X, self.leave)
        else:
            self.walk_to(step, lambda: (setattr(self, 'sel', self._ex_at(self.x)['id']),
                                        setattr(self, 'panel', 'exhibit')))

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def draw_world(self, frame):
        g = self.g
        t = self.t
        sc = int(self.scroll)
        hall = _build_static()
        frame.blit(hall, (0, 0), (sc, 0, W, H))
        glass = _glass()
        tg, lg = _STATIC['tankglow'], _STATIC['lampglow']
        for e in EXHIBITS:
            r = e['rect'].move(-sc, 0)
            if r.right < -40 or r.x > W + 40:
                continue
            self._draw_tank_live(frame, e, r, t)
            frame.blit(glass[e['id']], r)
            # light from the tank on the floor in front of it
            for i in range(3):
                y = WALL_BOT + 10 + i * 9
                wob = math.sin(t * 1.4 + i * 1.7 + e['cx']) * 6
                ln = int(r.w * (0.45 - i * 0.1))
                c = lerp_c(hall.get_at((max(0, min(AQ_W - 1, e['cx'])), y))[:3], (170, 220, 230), 0.14 - i * 0.03)
                frame.fill(c, (int(r.centerx - ln / 2 + wob), y, ln, 1))
            add_glow(frame, tg, (r.centerx, r.centery), 0.18)
        for i in range(0, AQ_W, 120):                  # hanging lamps
            lx = 60 + i - sc
            if -30 < lx < W + 30:
                pygame.draw.line(frame, (40, 34, 34), (lx, 26), (lx, 44))
                pygame.draw.polygon(frame, (60, 80, 70), [(lx - 6, 50), (lx + 6, 50), (lx + 3, 44), (lx - 3, 44)])
                frame.fill((255, 226, 160), (lx - 3, 50, 6, 2))
                add_glow(frame, lg, (lx, 54), 0.35)
        for bx in BENCHES:
            self._bench(frame, bx - sc, back=True)
        # Juniper behind her desk
        import town
        season = g.env.season
        jx = DESK_X - sc
        if -40 < jx < W + 40:
            spec = town.FOLK['juniper']
            town.walker(frame, jx, FLOOR - 6, 1 if self.x > DESK_X else -1, 0, spec['shirt'], spec['hair'],
                        spec['hat'], season)
            frame.fill((120, 86, 62), (jx - 26, FLOOR - 18, 52, 16))
            frame.fill((150, 110, 80), (jx - 28, FLOOR - 20, 56, 3))
            frame.fill((96, 68, 50), (jx - 26, FLOOR - 3, 52, 2))
            frame.fill((236, 230, 214), (jx - 23, FLOOR - 15, 46, 9))
            _sign(frame, 'DONATE', (jx, FLOOR - 10), (60, 90, 120))
            frame.fill((200, 220, 230), (jx + 16, FLOOR - 26, 9, 6))          # a little fishbowl
            frame.fill((240, 150, 60), (jx + 19, FLOOR - 24, 3, 2))
        for v in self.visitors:
            spec = town.FOLK[v['k']]
            x = int(v['x'] - sc)
            if -30 < x < W + 30:
                town.ground_shadow(frame, x, FLOOR, 13, 60)
                town.walker(frame, x, FLOOR, v['face'], v['step'], spec['shirt'], spec['hair'], spec['hat'], season,
                            spec.get('kid'), spec.get('glasses'))
                if v['em_t'] > 0 and v['em']:
                    actors.draw_bubble(frame, x + 1, FLOOR - 32, v['em'], t)
        x = int(self.x - sc)
        if self.sitting is not None:
            town.walker(frame, x, FLOOR - 6, self.face, 0, *looks.player_colors(g, season), g.hat, season, look=looks.of(g))
            self._bench(frame, self.sitting - sc, back=False)
        else:
            town.ground_shadow(frame, x, FLOOR, 13, 60)
            town.walker(frame, x, FLOOR, self.face, self.step, *looks.player_colors(g, season), g.hat, season, look=looks.of(g))
        for p in self.fx:
            frame.fill(p[5], (int(p[0] - sc), int(p[1]), 2, 2))

    def _bench(self, s, x, back=True):
        x = int(x)
        if back:
            s.fill((96, 66, 46), (x - 16, FLOOR - 18, 32, 2))
            s.fill((96, 66, 46), (x - 14, FLOOR - 18, 2, 8))
            s.fill((96, 66, 46), (x + 12, FLOOR - 18, 2, 8))
        s.fill((140, 98, 66), (x - 16, FLOOR - 10, 32, 3))
        s.fill((96, 66, 46), (x - 14, FLOOR - 7, 2, 7))
        s.fill((96, 66, 46), (x + 12, FLOOR - 7, 2, 7))

    def _draw_tank_live(self, frame, e, r, t):
        st = e['style']
        rng = random.Random(e['cx'])
        clip = frame.get_clip()
        frame.set_clip(r)
        # weeds swaying
        if st in ('lake', 'cove', 'creek', 'warm', 'legend', 'kelp', 'harbour'):
            col = {'warm': (90, 160, 90), 'creek': (80, 140, 90), 'kelp': (100, 110, 50),
                   'harbour': (70, 110, 70)}.get(st, (60, 120, 80))
            for i in range(5 if st != 'legend' else 4):
                bx = r.x + 10 + rng.randrange(max(1, r.w - 20))
                h = rng.randrange(18, 40) if st != 'kelp' else rng.randrange(60, r.h - 14)
                sw = math.sin(t * 1.1 + i) * 3 + (math.sin(t * 3) * 2 if st == 'creek' else 0)
                base = r.bottom - 6 if st != 'legend' else r.bottom - 22
                pygame.draw.lines(frame, col, False, [(bx, base), (bx + sw * 0.5, base - h / 2), (bx + sw, base - h)], 2)
        # the fish
        for f in self.fish:
            if f['ex'] != e['id']:
                continue
            spr = f['spr'] if f['vx'] > 0 else f['flip']
            y = f['y'] + math.sin(t * 1.5 + f['ph']) * 1.5
            frame.blit(spr, spr.get_rect(center=(int(f['x'] - (e['rect'].x - r.x)), int(y))))
        # the tanks' own little residents, so no tank is ever just empty water: a school of fry turning
        # together, and a snail making its slow way along the glass
        if st not in ('legend',):
            n = 7 if st != 'pots' else 0
            cx = r.x + r.w / 2 + math.sin(t * 0.23 + e['cx']) * (r.w / 2 - 22)
            cy = r.y + r.h * 0.45 + math.sin(t * 0.41 + e['cx'] * 0.7) * (r.h * 0.22)
            dirn = 1 if math.cos(t * 0.23 + e['cx']) > 0 else -1
            fry = lerp_c(WATER.get(st, WATER['lake'])[0], (246, 236, 200), 0.75)
            for i in range(n):
                fx = cx + math.sin(i * 2.1 + t * 0.9) * 6 + (i % 3) * 3 * dirn
                fy = cy + math.cos(i * 1.7 + t * 1.1) * 3 + (i // 3) * 2
                frame.fill(fry, (int(fx), int(fy), 3, 2))
                frame.set_at((int(fx) + (2 if dirn > 0 else -1), int(fy)), lerp_c(fry, (40, 40, 40), 0.5))
            sx = r.x + 6 + int((t * 1.2 + e['cx']) % max(1, r.w - 12))
            sy = r.bottom - 9
            frame.fill((150, 110, 80), (sx, sy - 2, 3, 3))
            frame.fill((200, 170, 120), (sx + 1, sy - 1, 1, 1))
            frame.fill((120, 130, 110), (sx + 3, sy, 2, 1))
            if st == 'pots':                                          # a hermit crab, sidling about
                hx = r.x + 16 + int((math.sin(t * 0.3) * 0.5 + 0.5) * (r.w - 32))
                frame.fill((210, 110, 80), (hx - 2, r.bottom - 10, 5, 3))
                frame.fill((230, 210, 170), (hx - 3, r.bottom - 13, 4, 3))
                frame.set_at((hx + 3, r.bottom - 11), (210, 110, 80))
        # moving water details
        if st == 'creek':
            for i in range(6):
                y = r.y + 12 + i * (r.h - 24) // 5
                x = r.x + int((t * 40 + i * 37) % (r.w + 30)) - 15
                frame.fill(lerp_c(WATER[st][0], (230, 246, 255), 0.4), (x, y, 10, 1))
        elif st in ('deep', 'wonders'):
            for i in range(12):
                x = r.x + int((i * 37 + t * (3 + i % 3)) % r.w)
                y = r.y + int((i * 53 + math.sin(t * 0.7 + i) * 8) % r.h)
                on = 0.5 + 0.5 * math.sin(t * 2 + i)
                c = (120, 200, 255) if st == 'deep' else (255, 240, 180)
                frame.fill(lerp_c(WATER[st][1], c, on), (x, y, 1, 1))
            if st == 'wonders' and (t % 7) < 0.12:                 # a flicker of storm light
                frame.fill((40, 40, 60), r, special_flags=pygame.BLEND_ADD)
        elif st in ('ice', 'legend', 'warm'):
            for i in range(3):                                      # soft light shafts
                x = r.x + 20 + i * (r.w - 40) // 2 + int(math.sin(t * 0.5 + i) * 6)
                for y in range(r.y, r.bottom, 2):
                    if (y // 2) % 3 == 0:
                        c = frame.get_at((max(0, min(W - 1, x)), y))
                        frame.fill(lerp_c(c[:3], (230, 246, 255), 0.18), (x, y, 4, 2))
        # bubbles
        bx = r.x + r.w - 14
        for i in range(5):
            y = r.bottom - ((t * 22 + i * 19) % (r.h - 4))
            frame.fill((210, 236, 250), (bx + int(math.sin(t * 3 + i) * 2), int(y), 2, 2))
        frame.set_clip(clip)

    # ------------------------------------------------------------ UI
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        sc = self.scroll
        ui.blit_text(s, 'Fernwick Aquarium', (sw // 2, 26), 'h3', (255, 250, 240), 'center', (30, 30, 50))
        done = finished(g)
        n_on = len(set(g.museum))
        head = ('The tanks are ready for your first fish.    Closes 5 PM' if not n_on else
                '%d of %d fish on display    Exhibits complete %d / %d    Closes 5 PM'
                % (n_on, len(FISH), len(done), len(EXHIBITS)))
        ui.blit_text(s, head, (sw // 2, 58), 'small', (230, 240, 246), 'center', (20, 30, 40))
        ui.blit_text(s, fmt_clock(g.minute), (24, 22), 'bodyb', (255, 250, 240), 'topleft', (30, 30, 50))
        # what neighbours say when you're near
        import town
        p = self.prompt() if self.panel is None and self.target is None else None
        for v in self.visitors:
            if abs(v['x'] - self.x) < 40 or v['k'] in self.said:
                text = '%s: %s' % (town.FOLK[v['k']]['name'], v['line'] or '')
                up = 66 if p and abs(v['x'] - self.x) < 70 else 46          # keep clear of the E prompt
                self._bubble(s, text, int((v['x'] - sc) * k), int((FLOOR - up) * k))
        if abs(self.x - DESK_X) < 50:
            n = len(set(g.museum))
            text = ("Juniper: Welcome in! Bring me any fish you catch and it gets a tank of its own." if not n else
                    'Juniper: Welcome in! %d of %d fish on display.' % (n, len(FISH)) if n < len(FISH) else
                    'Juniper: Every fish in the lake, under one roof. Thank you.')
            self._bubble(s, text, int((DESK_X - sc) * k), int((FLOOR - (66 if p else 54)) * k))
        if self.sitting is not None:
            e = self._ex_at(self.sitting)
            have = shown(g, e['id'])
            if have:
                f = have[int(self.sit_t / 6) % len(have)]
                text = '%s: %s' % (f['name'], f['desc'])
            else:
                text = '%s. %s' % (e['name'], e['blurb'])
            w = min(sw - 120, 900)
            r = ui.glass(s, (sw // 2 - w // 2, sh - 150, w, 70), 170, 18)
            for i, ln in enumerate(ui.wrap(text, 'small', w - 40)[:2]):
                ui.blit_text(s, ln, (r.x + 20, r.y + 14 + i * 24), 'small', (240, 246, 250))
        if p:
            px = int((self.x - sc) * k)
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (px, int((FLOOR - 40) * k) - 6)
            r.x = max(12, min(sw - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        hint = g.hint([('key', 'A'), ('key', 'D'), 'or', ('key', 'Click'), 'to walk   ', ('key', 'E'), 'look, sit, talk   ',
                       ('key', 'Esc'), 'leave'],
                      [('pad', 'STICK'), 'walk   ', ('pad', 'A'), 'look, sit, talk   ', ('pad', 'B'), 'leave'])
        if self.panel is None:
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, sh - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
        if self.panel == 'donate':
            g.dim(s)
            town.draw_museum(g, s)
        elif self.panel == 'exhibit' and self.sel:
            g.dim(s)
            self.draw_exhibit(s, EX_BY_ID[self.sel])

    def _bubble(self, s, text, x, y):
        ui = self.g.ui
        w = min(520, ui.fonts['small'].size(text)[0] + 28)
        lines = ui.wrap(text, 'small', w - 28)[:3]
        h = 14 + 22 * len(lines)
        r = pygame.Rect(0, 0, w, h)
        r.midbottom = (x, y)
        r.x = max(12, min(s.get_width() - 12 - w, r.x))
        r = ui.panel(s, r, fill=(255, 252, 244), radius=12)
        for i, ln in enumerate(lines):
            ui.blit_text(s, ln, (r.x + 14, r.y + 8 + i * 22), 'small', U.INK)

    def draw_exhibit(self, s, e):
        import town
        g = self.g
        ui = g.ui
        mem = MEMBERS[e['id']]
        cols = min(6, len(mem))
        rows = math.ceil(len(mem) / cols)
        tw, th, gap = 118, 112, 10
        w = max(620, cols * (tw + gap) + 60)
        h = 230 + rows * (th + gap)
        rect = town._panel(g, s, w, h, e['name'])
        ui.blit_text(s, e['blurb'], (rect.x + 30, rect.y + 90), 'small', U.SOFT, maxw=rect.w - 60)
        have = {f['id'] for f in shown(g, e['id'])}
        basket = {b['id'] for b in g.basket}
        x0 = rect.centerx - (cols * (tw + gap) - gap) // 2
        tip = None
        for i, f in enumerate(mem):
            r = pygame.Rect(x0 + (i % cols) * (tw + gap), rect.y + 124 + (i // cols) * (th + gap), tw, th)
            on = f['id'] in have
            can = not on and f['id'] in basket
            hov = r.collidepoint(ui.mouse)
            ui.tile(s, r, (226, 238, 244) if on else (252, 246, 228) if can else (232, 226, 214),
                    RARITY_COLORS[f['rarity']] if on or can else (190, 180, 168), hov and can)
            spr = art.fish_sprite(f, 2)
            if spr.get_width() > tw - 10:
                kk = (tw - 10) / spr.get_width()
                spr = pygame.transform.scale(spr, (int(spr.get_width() * kk), int(spr.get_height() * kk)))
            if not on:
                spr = pygame.mask.from_surface(spr, 1).to_surface(
                    setcolor=(150, 140, 130, 255) if can else (200, 192, 180, 255), unsetcolor=(0, 0, 0, 0))
            s.blit(spr, spr.get_rect(center=(r.centerx, r.y + th * 0.42)))
            if on:
                ui.blit_text(s, f['name'], (r.centerx, r.bottom - 22), 'tiny', U.INK, 'center', maxw=r.w - 8)
            elif can:
                ui.blit_text(s, 'Donate', (r.centerx, r.bottom - 22), 'smallb', (60, 120, 80), 'center')
                ui.hotspot(r, lambda fid=f['id']: g.donate(fid))
            else:
                ui.blit_text(s, '?', (r.centerx, r.bottom - 22), 'smallb', (170, 160, 150), 'center')
            if hov:
                tip = f
        foot = rect.bottom - 44
        if tip and (tip['id'] in have or tip['id'] in g.journal):
            text = tip['name'] + ': ' + (tip['desc'] if tip['id'] in have else town.fish_hint(tip))
        elif tip:
            text = 'Not yet found. ' + town.fish_hint(tip)
        elif e['id'] in finished(g):
            text = 'Exhibit complete! A little brass star shines on the name plate.'
        else:
            text = '%d of %d on display. Finishing this exhibit earns %d coins.' % (len(have), len(mem), e['reward'])
        ui.blit_text(s, text, (rect.centerx, foot), 'small', U.INK if tip else U.SOFT, 'center', maxw=rect.w - 60)
