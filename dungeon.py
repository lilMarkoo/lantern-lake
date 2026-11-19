"""The Drowned Stair: a roguelike fishing dungeon under the hill by the dock.

You go down with nothing: bare hands and a bit of string. Every floor is a flooded cave with a pool. Catch
enough of its fish and the stair down opens. Fish drop loot: pearls, gear for five slots (rod, reel, line,
lure, charm) in five tiers that get better the deeper you go, and things to use (kelp wraps, glow worms,
calm tonic, homeward shells). It all goes in a twelve-slot bag; anything that doesn't fit lies on the floor
until you go down.

Every fifth floor a boss fish guards the stair (a three-stage fight). Beat it and you reach a camp, where
you can climb out with everything you carry (sold for coins) or go deeper. A Homeward Shell gets you out
from anywhere.

A snapped line costs a heart, and so does a biter (red eyes) that gets away. Lose every heart and the water
carries you back up the stair with nothing: the whole run's loot is lost. Only your records stay.

Runs under Game.overlay 'dungeon' with Game.dungeon. Records live in Game.delve (saved).
"""
import math
import random

import pygame

import actors
import art
import look as looks
import minigame
import ui as U
from art import lerp_c, darken
from data import F

W, H = 640, 360
BAG = 12
STACK = 5
BOSS_EVERY = 5
BASE_ROD = dict(arc=46, turn=200, reel=0.8)     # bare hands: worse than the Twig Rod (70 / 250 / 1.0)
BASE_HEARTS = 3
PEARL_COINS = 1                                 # what a pearl sells for when you climb out
WATER_Y = 262                                   # the pool's surface, in world pixels
POOL_X0, POOL_X1 = 168, 588
LEDGE_X = 128                                   # where you stand
AREA = pygame.Rect(88, 298, 22, 22)             # the stone arch in the bank below the garden (world pixels)

SLOTS = ('rod', 'reel', 'line', 'lure', 'charm')
SLOT_NAMES = dict(rod='Rod', reel='Reel', line='Line', lure='Lure', charm='Charm')
TIERS = (('Worn', (178, 168, 156)), ('Sturdy', (122, 190, 112)), ('Fine', (108, 160, 238)),
         ('Gleaming', (204, 132, 234)), ('Abyssal', (250, 200, 84)))
GEAR_NAMES = dict(
    rod=('Driftwood Rod', 'Reed Rod', 'Coral Rod', 'Moonbone Rod', 'Abyssal Spine'),
    reel=('Tin Spool', 'Brass Reel', 'Shell Reel', 'Pearl Reel', 'Tide Engine'),
    line=('Frayed Twine', 'Cotton Line', 'Kelp Line', 'Spider-silk Line', 'Leviathan Sinew'),
    lure=('Bent Nail', 'Painted Spoon', 'Glow Bead', 'Siren Feather', 'Star Lure'),
    charm=('Lucky Pebble', 'Sea Glass', 'Coral Ring', 'Pearl Locket', 'Abyssal Eye'),
)
# stats by tier (rolled 85% - 115%)
GEAR_STATS = dict(
    rod=[dict(arc=a, turn=t) for a, t in ((8, 20), (16, 40), (26, 70), (38, 100), (52, 140))],
    reel=[dict(reel=r) for r in (0.12, 0.25, 0.4, 0.6, 0.85)],
    line=[dict(tough=r) for r in (0.12, 0.22, 0.34, 0.46, 0.58)],
    lure=[dict(bite=b, luck=l) for b, l in ((0.15, 0), (0.25, 1), (0.35, 1), (0.45, 2), (0.55, 3))],
)
CHARMS = [                     # by tier: the choices a charm of that tier can roll
    [dict(pearl=0.15), dict(heart=1)],
    [dict(heart=1), dict(pearl=0.3), dict(mend=0.25)],
    [dict(heart=1, pearl=0.2), dict(heart=1, mend=0.3), dict(pearl=0.5)],
    [dict(heart=2), dict(heart=1, mend=0.45), dict(heart=1, pearl=0.5)],
    [dict(heart=2, mend=0.5), dict(heart=2, pearl=0.6), dict(heart=3)],
]
GEAR_VALUE = (4, 9, 20, 45, 100)
USES = dict(
    kelp=dict(name='Kelp Wrap', desc='Wrap a sore hand: heals one heart.', value=2, col=(96, 160, 90)),
    worm=dict(name='Glow Worms', desc='Your next 3 casts bite fast, and what they drop is better.', value=3,
              col=(170, 240, 150)),
    tonic=dict(name='Calm Tonic', desc='Your next fight: the line strains half as fast.', value=4,
               col=(150, 190, 240)),
    shell=dict(name='Homeward Shell', desc='Blow it to climb out right away, keeping everything you carry.',
               value=10, col=(240, 200, 180)),
)
USE_WEIGHTS = (('kelp', 50), ('worm', 24), ('tonic', 18), ('shell', 8))

# ---------------------------------------------------------------- the deep's own fish
ZONES = [
    dict(name='Mossy Cellar', wall=(58, 70, 54), deep=(20, 28, 24), water=((52, 102, 92), (12, 30, 30)),
         glow=(170, 230, 150), decor='moss',
         fish=[F('dg_cavefry', 'Cave Fry', 1, 0, (4, 9), 'small', (196, 204, 198), (240, 240, 236),
                 pattern='scales', strength=.12, agility=.4),
               F('dg_mossloach', 'Moss Loach', 1, 0, (8, 18), 'long', (96, 130, 80), (184, 204, 144),
                 pattern='spots', pc=(64, 90, 52), strength=.18, agility=.3),
               F('dg_blindperch', 'Blind Perch', 1, 0, (12, 24), 'normal', (190, 178, 178), (236, 226, 226),
                 c3=(214, 150, 150), pattern='stripes', pc=(150, 136, 136), strength=.24, agility=.35)],
         biter=F('dg_nipper', 'Nipper Eel', 2, 0, (30, 50), 'eel', (92, 62, 62), (204, 126, 104),
                 strength=.3, agility=.5)),
    dict(name='Glowworm Grotto', wall=(40, 52, 82), deep=(12, 16, 30), water=((40, 84, 140), (8, 16, 40)),
         glow=(150, 214, 255), decor='glowworm',
         fish=[F('dg_tetra', 'Lantern Tetra', 1, 0, (4, 8), 'small', (60, 100, 164), (164, 222, 255),
                 glow=(150, 220, 255), strength=.18, agility=.55),
               F('dg_glasscarp', 'Glass Carp', 1, 0, (20, 44), 'round', (150, 190, 214), (222, 240, 250),
                 pattern='scales', strength=.4, agility=.2),
               F('dg_starbass', 'Speckled Starbass', 1, 0, (18, 36), 'normal', (40, 60, 112), (140, 170, 232),
                 pattern='spots', pc=(232, 240, 255), strength=.34, agility=.45)],
         biter=F('dg_fangpike', 'Fang Pike', 2, 0, (40, 80), 'gar', (70, 92, 82), (182, 204, 172),
                 strength=.42, agility=.55)),
    dict(name='Coral Crypt', wall=(84, 50, 74), deep=(28, 14, 26), water=((120, 70, 120), (34, 14, 40)),
         glow=(255, 170, 200), decor='coral',
         fish=[F('dg_bonecarp', 'Bone Carp', 1, 0, (24, 50), 'round', (220, 210, 190), (250, 244, 230),
                 pattern='stripes', pc=(160, 150, 130), strength=.46, agility=.22),
               F('dg_wrasse', 'Coral Wrasse', 1, 0, (14, 30), 'normal', (232, 112, 122), (255, 204, 164),
                 pattern='stripes', pc=(184, 72, 96), strength=.38, agility=.58),
               F('dg_gravecat', 'Grave Catfish', 1, 0, (40, 90), 'catfish', (92, 80, 112), (172, 152, 192),
                 strength=.55, agility=.25)],
         biter=F('dg_grinner', 'Grinning Gar', 2, 0, (50, 100), 'gar', (152, 62, 82), (242, 172, 172),
                 strength=.5, agility=.6)),
    dict(name='Abyssal Steps', wall=(30, 34, 46), deep=(4, 6, 12), water=((24, 60, 70), (2, 8, 14)),
         glow=(120, 255, 220), decor='abyss',
         fish=[F('dg_angler', 'Deep Angler', 1, 0, (30, 70), 'catfish', (34, 44, 54), (84, 104, 114),
                 glow=(120, 255, 220), strength=.6, agility=.3),
               F('dg_voideel', 'Void Eel', 1, 0, (60, 120), 'eel', (22, 26, 44), (92, 102, 164),
                 glow=(150, 130, 255), strength=.55, agility=.62),
               F('dg_pearlfish', 'Pearlfish', 1, 0, (10, 22), 'round', (220, 230, 240), (255, 255, 255),
                 glow=(255, 250, 230), strength=.4, agility=.6)],
         biter=F('dg_maw', 'Hollow Maw', 2, 0, (80, 150), 'sturgeon', (42, 40, 52), (122, 112, 132),
                 strength=.66, agility=.5)),
]
BOSSES = [
    (F('dg_mossjaw', 'Old Mossjaw', 5, 0, (120, 160), 'catfish', (70, 96, 58), (170, 196, 120),
       pattern='spots', pc=(40, 60, 34), strength=.55, agility=.4),
     ('Old Mossjaw stirs!', 'It churns up the mud!', 'Last stand!')),
    (F('dg_matriarch', 'The Lantern Matriarch', 5, 0, (90, 130), 'normal', (40, 64, 130), (170, 210, 255),
       glow=(170, 230, 255), pattern='spots', pc=(230, 245, 255), strength=.62, agility=.55),
     ('The Matriarch lights up!', 'Her glow blinds the water!', 'Last stand!')),
    (F('dg_tyrant', 'The Coral Tyrant', 5, 0, (140, 200), 'gar', (170, 60, 84), (255, 190, 170),
       pattern='stripes', pc=(120, 30, 60), strength=.7, agility=.6),
     ('The Tyrant bares its teeth!', 'It thrashes through the coral!', 'Last stand!')),
    (F('dg_drowned', 'The Drowned King', 5, 0, (200, 300), 'sturgeon', (30, 40, 60), (120, 160, 170),
       glow=(120, 255, 220), strength=.8, agility=.55),
     ('The Drowned King wakes!', 'The whole pool heaves!', 'Last stand!')),
]
CHEST = F('dg_chest', 'Sunken Chest', 2, 0, (30, 40), 'normal', (120, 84, 50), (200, 160, 90),
          strength=.3, agility=.1, behavior='sulker')


def _chest_sprite():
    s = pygame.Surface((art.FW, art.FH), pygame.SRCALPHA)
    pygame.draw.rect(s, (96, 64, 38), (12, 6, 24, 15))
    pygame.draw.rect(s, (130, 90, 54), (12, 6, 24, 6))
    pygame.draw.rect(s, (60, 40, 26), (12, 6, 24, 15), 1)
    for x in (16, 31):
        pygame.draw.rect(s, (214, 170, 80), (x, 6, 2, 15))
    pygame.draw.rect(s, (240, 210, 110), (22, 11, 4, 4))
    pygame.draw.rect(s, (40, 30, 20), (23, 13, 2, 1))
    return s


art._sprite_cache[('dg_chest', 1)] = _chest_sprite()


def zone_of(floor):
    return ((floor - 1) // BOSS_EVERY) % len(ZONES)


def is_boss(floor):
    return floor % BOSS_EVERY == 0


def need_of(floor):
    return 2 if floor <= 2 else 3 if floor <= 9 else 4


def scaled(base, floor, biter=False):
    """A pool fish as it fights this deep: stronger, quicker, and a rarer-looking ring."""
    r = min(4, 1 + floor // 4 + (1 if biter else 0))
    return dict(base, rarity=r, strength=min(1.1, base['strength'] + 0.022 * floor),
                agility=min(1.0, base['agility'] + 0.012 * floor))


def boss_spec(floor):
    k = floor // BOSS_EVERY - 1
    base, lines = BOSSES[k % len(BOSSES)]
    loop = k // len(BOSSES)                    # past the Drowned King they come back, harder
    spec = dict(base, strength=min(1.15, base['strength'] + 0.1 * loop), agility=min(1.0, base['agility'] + 0.06 * loop))
    if loop:
        spec['name'] = base['name'] + ' (again)'
    return spec, lines


# ---------------------------------------------------------------- records (saved)
def new_rec():
    return dict(best=0, runs=0, climbs=0, lost=0, bosses=0, coins=0, haul=0, seen=False)


def clean_rec(d):
    out = new_rec()
    if isinstance(d, dict):
        for k, v in out.items():
            if k in d and isinstance(d[k], type(v)):
                out[k] = d[k]
    return out


def open_stair(g):
    """Go down the stair from the dock."""
    if g.overlay is not None or g.rest_phase is not None or g.mode != 'play':
        return
    if g.fishing.state not in ('idle', 'waiting'):
        g.toast('Finish what is on the line first.')
        return
    g.fishing.reset()
    g.release_holds()
    g.dungeon = Dungeon(g)
    g.overlay = 'dungeon'
    g.audio.play('page', 0.5)


# ---------------------------------------------------------------- gear
def gear_desc(it):
    """The short lines that say what an item does."""
    if it['kind'] == 'use':
        return [USES[it['id']]['desc']]
    st = it['stats']
    sl = it['slot']
    if sl == 'rod':
        return ['Reeling arc +%d' % st['arc'], 'Swing speed +%d' % st['turn']]
    if sl == 'reel':
        return ['Reels in %d%% faster' % round(st['reel'] * 100 / BASE_ROD['reel'])]
    if sl == 'line':
        return ['Line strains %d%% slower' % round(st['tough'] * 100)]
    if sl == 'lure':
        out = ['Bites come %d%% sooner' % round(st['bite'] * 100)]
        if st.get('luck'):
            out.append('Better loot (luck +%d)' % st['luck'])
        return out
    out = []
    if st.get('heart'):
        out.append('+%d heart%s' % (st['heart'], 's' if st['heart'] > 1 else ''))
    if st.get('pearl'):
        out.append('+%d%% pearls' % round(st['pearl'] * 100))
    if st.get('mend'):
        out.append('%d%% chance to mend a heart each floor' % round(st['mend'] * 100))
    return out


def short_desc(it):
    return ',  '.join(gear_desc(it)) if it['kind'] == 'gear' else USES[it['id']]['desc']


def item_name(it):
    return USES[it['id']]['name'] if it['kind'] == 'use' else it['name']


def item_col(it):
    return USES[it['id']]['col'] if it['kind'] == 'use' else TIERS[it['tier']][1]


def item_value(it):
    if it['kind'] == 'use':
        return USES[it['id']]['value'] * it['n']
    return it['value']


# ---------------------------------------------------------------- icons (16x16, drawn here)
_icons = {}


def icon(kind, col, scale=3, dim=False):
    key = (kind, col, scale, dim)
    out = _icons.get(key)
    if out is not None:
        return out
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    dk = darken(col, 0.45)
    lt = lerp_c(col, (255, 255, 255), 0.45)
    if kind == 'rod':
        pygame.draw.line(s, dk, (3, 14), (13, 2), 3)
        pygame.draw.line(s, col, (3, 13), (13, 2), 1)
        pygame.draw.line(s, (110, 76, 50), (2, 15), (5, 12), 3)
        s.fill(lt, (6, 10, 2, 2))
        pygame.draw.line(s, (230, 230, 230), (13, 2), (14, 9))
        s.fill((220, 80, 60), (13, 9, 2, 2))
    elif kind == 'reel':
        pygame.draw.circle(s, dk, (8, 8), 7)
        pygame.draw.circle(s, col, (8, 8), 6)
        pygame.draw.circle(s, dk, (8, 8), 2)
        for a in range(0, 360, 90):
            x, y = 8 + math.cos(math.radians(a + 45)) * 4, 8 + math.sin(math.radians(a + 45)) * 4
            s.fill(lt, (int(x), int(y), 1, 1))
        pygame.draw.line(s, dk, (13, 8), (15, 12), 2)
    elif kind == 'line':
        pygame.draw.rect(s, (130, 96, 64), (3, 3, 10, 10))
        pygame.draw.rect(s, col, (4, 5, 8, 6))
        for y in (6, 8, 10):
            pygame.draw.line(s, dk, (4, y), (11, y))
        pygame.draw.line(s, lt, (12, 7), (15, 2))
    elif kind == 'lure':
        pygame.draw.ellipse(s, dk, (4, 2, 8, 10))
        pygame.draw.ellipse(s, col, (5, 3, 6, 8))
        s.fill(lt, (6, 4, 2, 2))
        pygame.draw.line(s, (200, 200, 200), (8, 12), (8, 14))
        pygame.draw.arc(s, (200, 200, 200), (5, 11, 6, 5), math.pi, 2 * math.pi, 1)
    elif kind == 'charm':
        pygame.draw.lines(s, (200, 180, 140), False, [(3, 1), (8, 6), (13, 1)])
        pygame.draw.polygon(s, dk, [(8, 5), (13, 10), (8, 15), (3, 10)])
        pygame.draw.polygon(s, col, [(8, 6), (12, 10), (8, 14), (4, 10)])
        s.fill(lt, (6, 8, 2, 2))
    elif kind == 'kelp':
        pygame.draw.ellipse(s, (50, 96, 50), (3, 3, 10, 11))
        pygame.draw.ellipse(s, col, (4, 4, 8, 9))
        pygame.draw.line(s, (60, 110, 60), (5, 6), (11, 10))
        pygame.draw.line(s, (60, 110, 60), (5, 10), (11, 6))
    elif kind == 'worm':
        pygame.draw.rect(s, (200, 214, 220), (3, 3, 10, 12), 1)
        s.fill((180, 150, 110), (4, 2, 8, 2))
        for i, (x, y) in enumerate(((5, 12), (7, 10), (9, 11), (10, 8), (8, 6))):
            s.fill(col, (x, y, 2, 2))
    elif kind == 'tonic':
        pygame.draw.rect(s, (200, 214, 220), (6, 1, 4, 4))
        pygame.draw.ellipse(s, (200, 214, 220), (2, 4, 12, 11))
        pygame.draw.ellipse(s, col, (3, 7, 10, 7))
        s.fill(lt, (5, 8, 2, 2))
        s.fill((140, 100, 70), (6, 0, 4, 2))
    elif kind == 'shell':
        pygame.draw.polygon(s, dk, [(2, 12), (8, 2), (14, 12), (8, 14)])
        pygame.draw.polygon(s, col, [(3, 12), (8, 3), (13, 12), (8, 13)])
        for y in (6, 9, 11):
            pygame.draw.line(s, dk, (8 - (y - 3) // 2, y), (8 + (y - 3) // 2, y))
    elif kind == 'pearl':
        pygame.draw.circle(s, (170, 170, 190), (8, 8), 6)
        pygame.draw.circle(s, (240, 240, 250), (8, 8), 5)
        s.fill((255, 255, 255), (5, 5, 3, 3))
    if dim:
        s.fill((120, 110, 100, 90), special_flags=pygame.BLEND_RGBA_MULT)
    out = pygame.transform.scale(s, (16 * scale, 16 * scale))
    _icons[key] = out
    return out


def item_icon(it, scale=3):
    if it['kind'] == 'use':
        return icon(it['id'], USES[it['id']]['col'], scale)
    return icon(it['slot'], TIERS[it['tier']][1], scale)


def heart(s, x, y, full, r=6):
    c = (226, 82, 92) if full else (90, 70, 74)
    pygame.draw.circle(s, c, (x - r // 2, y), r // 2 + 1)
    pygame.draw.circle(s, c, (x + r // 2, y), r // 2 + 1)
    pygame.draw.polygon(s, c, [(x - r - 1, y + 1), (x + r + 1, y + 1), (x, y + r + 3)])
    if full:
        s.fill((255, 190, 190), (x - r // 2 - 1, y - 2, 2, 2))


class _Tough:
    """The line's toughness: strain builds slower by this factor."""
    tough = 1.0

    def update(self, dt, holding, aim=None, steer=0):
        s0 = self.strain
        super().update(dt, holding, aim, steer)
        d = self.strain - s0
        if d > 0:
            self.strain = s0 + d * self.tough


class DReel(_Tough, minigame.ReelGame):
    pass


class DBoss(_Tough, minigame.LegendGame):
    pass


# ---------------------------------------------------------------- the run
class Dungeon:
    def __init__(self, g, seed=None):
        self.g = g
        self.rng = random.Random(seed)
        self.t = 0.0
        self.st = 0.0
        self.done = False
        self.holds = set()
        self.floor = 0
        self.eq = {k: None for k in SLOTS}
        self.bag = []
        self.ground = []
        self.pearls = 0
        self.hearts = BASE_HEARTS
        self.uid = 0
        self.worms = 0
        self.tonic = False
        self.caught = 0
        self.taken = 0                 # fish landed this run
        self.pool = []
        self.state = 'enter'
        self.panel = None if g.delve.get('seen') else 'rules'
        self.sel = None
        self.popups = []
        self.loot = None               # what the last catch dropped, for the card
        self.mg = None
        self.fish = None               # the pool fish on the line / coming to the lure
        self.bob = None                # the bobber's x, while it's in the water
        self.drops = []
        self.rings = []
        self.summary = None
        self.bot_goal = None
        self._bg = None
        self._dim = {}
        self.next_floor()

    # ------------------------------------------------------------ derived stats
    def stat(self, slot, key, default=0):
        it = self.eq.get(slot)
        return it['stats'].get(key, default) if it else default

    def rod(self):
        return dict(arc=BASE_ROD['arc'] + self.stat('rod', 'arc'), turn=BASE_ROD['turn'] + self.stat('rod', 'turn'),
                    reel=BASE_ROD['reel'] + self.stat('reel', 'reel'))

    def max_hearts(self):
        return BASE_HEARTS + self.stat('charm', 'heart')

    def tough(self):
        return 1 - self.stat('line', 'tough')

    def luck(self):
        return self.stat('lure', 'luck')

    # ------------------------------------------------------------ floors
    def next_floor(self):
        g = self.g
        self.floor += 1
        f = self.floor
        rec = g.delve
        if f > rec['best'] and self.panel != 'rules':
            rec['best'] = f
        rng = self.rng
        mended = False
        if f > 1:
            mend = self.stat('charm', 'mend')
            if mend and self.hearts < self.max_hearts() and rng.random() < mend:
                self.hearts += 1
                mended = True
        self.ground = []
        self.caught = 0
        self.pool = []
        self.popups = []
        self.bob = None
        self.fish = None
        self.mg = None
        self.zone = ZONES[zone_of(f)]
        self._bg = None
        if mended:
            self.pop('Your charm mends a heart.', (255, 190, 200))
        if is_boss(f):
            spec, lines = boss_spec(f)
            self.pool.append(self._swimmer(spec, 'boss'))
            self.boss_lines = lines
            self.need = 1
        else:
            self.need = need_of(f)
            z = self.zone
            for i in range(self.need + 2):
                self.pool.append(self._swimmer(scaled(rng.choice(z['fish']), f), 'fish'))
            nb = 0 if f == 1 else 1 if f <= 6 else 2 if f <= 14 else 3
            for i in range(nb):
                self.pool.append(self._swimmer(scaled(z['biter'], f, True), 'biter'))
            if f > 1 and rng.random() < 0.35:
                self.pool.append(self._swimmer(dict(CHEST, strength=0.3 + 0.015 * f), 'chest'))
        self.state, self.st = 'enter', 0.0

    def _swimmer(self, spec, kind):
        rng = self.rng
        y = rng.uniform(WATER_Y + 16, H - 22 if kind != 'chest' else H - 14)
        if kind == 'boss':
            y = WATER_Y + 52
        return dict(spec=spec, kind=kind, x=rng.uniform(POOL_X0 + 30, POOL_X1 - 30), y=y,
                    vx=rng.choice((-1, 1)) * rng.uniform(10, 24) * (0 if kind == 'chest' else 1),
                    ph=rng.uniform(0, 6.3), mode='swim')

    def stair_open(self):
        return not is_boss(self.floor) and self.caught >= self.need

    def fish_left(self):
        return [p for p in self.pool if p['mode'] != 'gone']

    # ------------------------------------------------------------ loot
    def new_gear(self, tier, slot=None):
        rng = self.rng
        tier = max(0, min(4, tier))
        if slot is None:
            w = [(s, 3 if self.eq[s] is None else 1) for s in SLOTS]
            slot = rng.choices([s for s, _ in w], [k for _, k in w])[0]
        q = rng.uniform(0.85, 1.15)
        if slot == 'charm':
            st = dict(rng.choice(CHARMS[tier]))
            if st.get('pearl'):
                st['pearl'] = round(st['pearl'] * q, 2)
            if st.get('mend'):
                st['mend'] = round(min(0.8, st['mend'] * q), 2)
        else:
            st = {}
            for k, v in GEAR_STATS[slot][tier].items():
                st[k] = v if k == 'luck' else (round(v * q, 2) if isinstance(v, float) else int(round(v * q)))
        self.uid += 1
        return dict(uid=self.uid, kind='gear', slot=slot, tier=tier, name=GEAR_NAMES[slot][tier], stats=st,
                    power=tier + (q - 0.85) / 0.3 * 0.9, value=int(GEAR_VALUE[tier] * q))

    def new_use(self, kind=None):
        if kind is None:
            kind = self.rng.choices([k for k, _ in USE_WEIGHTS], [w for _, w in USE_WEIGHTS])[0]
        self.uid += 1
        return dict(uid=self.uid, kind='use', id=kind, n=1)

    def roll_tier(self, bonus=0.0):
        base = self.floor / 5.0 + self.luck() * 0.35 + bonus + (0.6 if self.worms_on else 0)
        return max(0, min(4, int(base + self.rng.gauss(0, 0.7))))

    def drop_loot(self, kind):
        """What a landed fish (or chest, or boss) drops. Returns a list of items (pearls are an int entry)."""
        rng = self.rng
        f = self.floor
        mult = 1 + self.stat('charm', 'pearl')
        out = []
        if kind == 'boss':
            out.append(int((14 + f * 1.6) * mult))
            t = min(4, f // BOSS_EVERY + 1)
            out.append(self.new_gear(t))
            out.append(self.new_gear(self.roll_tier(1.0)))
            out.append(self.new_use('kelp'))
            return out
        p = rng.randint(1, 3) + f // 2
        if kind == 'biter':
            p *= 2
        if kind == 'chest':
            p += 4 + f
        out.append(max(1, int(p * mult)))
        gear = {'fish': 0.4, 'biter': 0.75, 'chest': 1.0}[kind]
        if f == 1 and self.taken == 0:
            gear = 1.0                         # the very first fish always gives you something to hold
        if rng.random() < gear:
            out.append(self.new_gear(self.roll_tier({'fish': 0, 'biter': 0.5, 'chest': 1.0}[kind])))
        if rng.random() < (0.6 if kind == 'chest' else 0.2):
            out.append(self.new_use())
        return out

    @property
    def worms_on(self):
        return self.worms > 0

    def add(self, it):
        """Into the bag (stacking), else onto the floor. A gear slot that is empty gets it straight away."""
        if it['kind'] == 'gear' and self.eq[it['slot']] is None:
            self.eq[it['slot']] = it
            self._on_equip(it)
            return 'equipped'
        if it['kind'] == 'use':
            for b in self.bag:
                if b['kind'] == 'use' and b['id'] == it['id'] and b['n'] < STACK:
                    b['n'] += it['n']
                    return 'bag'
        if len(self.bag) < BAG:
            self.bag.append(it)
            return 'bag'
        self.ground.append(it)
        return 'ground'

    def _on_equip(self, it):
        h = it['stats'].get('heart', 0) if it['slot'] == 'charm' else 0
        if h and not it.get('filled'):
            it['filled'] = True
            self.hearts += h                     # a new charm's hearts come full, once
        self.hearts = min(self.hearts, self.max_hearts())

    def equip(self, i):
        it = self.bag[i]
        if it['kind'] != 'gear':
            return
        old = self.eq[it['slot']]
        self.eq[it['slot']] = it
        if old:
            self.bag[i] = old
        else:
            self.bag.pop(i)
        self._on_equip(it)
        self.sel = ('eq', it['slot'])
        self.g.audio.play('click', 0.5)

    def unequip(self, slot):
        it = self.eq[slot]
        if not it or len(self.bag) >= BAG:
            return
        self.eq[slot] = None
        self.bag.append(it)
        self.hearts = min(self.hearts, self.max_hearts())
        self.sel = ('bag', len(self.bag) - 1)
        self.g.audio.play('click', 0.5)

    def use(self, i):
        it = self.bag[i]
        if it['kind'] != 'use':
            return
        k = it['id']
        g = self.g
        if k == 'kelp':
            if self.hearts >= self.max_hearts():
                self.pop('Your hands are fine for now.', (220, 220, 210))
                return
            self.hearts += 1
            self.pop('+1 heart', (255, 190, 200))
        elif k == 'worm':
            self.worms += 3
            self.pop('Glow worms on the hook: 3 quick casts', (190, 250, 170))
        elif k == 'tonic':
            if self.tonic:
                return
            self.tonic = True
            self.pop('Calm tonic: the next fight is gentler on the line', (180, 210, 250))
        elif k == 'shell':
            self._take(i)
            g.audio.play('wish', 0.7)
            self.climb_out('You blow the Homeward Shell. The water lifts you gently up the stair.')
            return
        g.audio.play('chime1', 0.6)
        self._take(i)

    def _take(self, i):
        it = self.bag[i]
        it['n'] -= 1
        if it['n'] <= 0:
            self.bag.pop(i)
            if self.sel == ('bag', i) or (self.sel and self.sel[0] == 'bag' and self.sel[1] >= len(self.bag)):
                self.sel = None

    def drop(self, i):
        self.ground.append(self.bag.pop(i))
        self.sel = ('ground', len(self.ground) - 1)
        self.g.audio.play('plop', 0.4)

    def pick(self, j):
        if len(self.bag) >= BAG:
            self.pop('Your bag is full. Drop something first.', (240, 190, 170))
            return
        it = self.ground.pop(j)
        r = self.add(it)
        self.sel = ('eq', it['slot']) if r == 'equipped' else ('bag', len(self.bag) - 1) if r == 'bag' and \
            it['kind'] == 'gear' else None
        self.g.audio.play('click', 0.5)

    def carried(self):
        return [it for it in self.eq.values() if it] + list(self.bag)

    def haul_value(self):
        return self.pearls * PEARL_COINS + sum(item_value(it) for it in self.carried())

    # ------------------------------------------------------------ input
    def press(self, src='key'):
        if src in self.holds:
            return
        self.holds.add(src)
        if self.panel or self.done:
            return
        st = self.state
        if st == 'enter':
            if self.st > 0.3:
                self.state, self.st = ('boss_wait' if is_boss(self.floor) else 'cast'), 0.0
        elif st == 'cast':
            self.cast()
        elif st in ('wait', 'come'):
            self.reel_in('You reel the lure back in.')
        elif st == 'bite':
            self.hook()
        elif st == 'fight':
            if self.mg:
                self.mg.press()
        elif st == 'land' and self.st > 0.5:
            self.after_land()
        elif st == 'boss_wait' and self.st > 0.4:
            self.hook(self.pool[0])

    def release(self, src='key'):
        self.holds.discard(src)

    def holding(self):
        return bool(self.holds)

    def key(self, k):
        if k == pygame.K_ESCAPE:
            if self.panel == 'bag':
                self.close_bag()
            elif self.panel == 'rules':
                self.close()
            elif self.panel == 'quit':
                self.panel = None
            elif self.state in ('lost', 'out'):
                self.close()
            elif self.state == 'fight':
                self.panel = 'quit'
            else:
                self.panel = 'quit'
            return
        if k in (pygame.K_i, pygame.K_TAB, pygame.K_b):
            if self.panel == 'bag':
                self.close_bag()
            else:
                self.open_bag()
            return
        if self.panel:
            if self.panel == 'rules' and k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
                self.begin()
            return
        if self.state in ('lost', 'out'):
            if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e) and self.st > 0.8:
                self.close()
            return
        if k in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER) and self.state == 'cast' and self.stair_open():
            self.descend()
            return
        if self.state == 'camp':
            if k in (pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.descend()
            return
        if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
            self.press('key' if k == pygame.K_SPACE else 'enter')
            if k != pygame.K_SPACE:
                self.release('enter')

    def begin(self):
        rec = self.g.delve
        rec['seen'] = True
        rec['best'] = max(rec['best'], self.floor)
        self.panel = None
        self.st = 0.0
        self.g.audio.play('page', 0.5)

    def open_bag(self):
        if self.state == 'fight' or self.state in ('lost', 'out') or self.panel == 'rules':
            return
        if self.state in ('wait', 'come', 'bite'):
            self.reel_in(None)
        self.panel = 'bag'
        if self.sel is None:
            self.sel = ('bag', 0) if self.bag else None
        self.g.audio.play('page', 0.5)

    def close_bag(self):
        self.panel = None
        self.g.audio.play('page', 0.4)

    # ------------------------------------------------------------ fishing the pool
    def cast(self):
        left = [p for p in self.pool if p['mode'] == 'swim']
        if not left:
            self.pop('The pool is empty. Take the stair down.' if self.stair_open() else 'Nothing left here.',
                     (220, 220, 210))
            return
        rng = self.rng
        self.bob = rng.uniform(POOL_X0 + 70, POOL_X1 - 40)
        k = 1 - self.stat('lure', 'bite')
        if self.worms_on:
            k *= 0.4
        self.wait = rng.uniform(1.4, 3.4) * k
        self.state, self.st = 'wait', 0.0
        self.rings.append([self.bob, WATER_Y, 2.0, 0.0])
        self.g.audio.play('plop', 0.6)

    def reel_in(self, text):
        if self.fish and self.fish['mode'] in ('come', 'bite'):
            self.fish['mode'] = 'swim'
        self.fish = None
        self.bob = None
        self.state, self.st = 'cast', 0.0
        if text:
            self.pop(text, (220, 226, 230))

    def _choose(self):
        left = [p for p in self.pool if p['mode'] == 'swim']
        w = [3 if p['kind'] == 'fish' else 2 if p['kind'] == 'biter' else 1 for p in left]
        return self.rng.choices(left, w)[0]

    def hook(self, fish=None):
        fish = fish or self.fish
        if fish is None:
            return
        g = self.g
        self.fish = fish
        fish['mode'] = 'hooked'
        spec = fish['spec']
        rod = self.rod()
        boss = fish['kind'] == 'boss'
        if boss:
            self.mg = DBoss(spec, rod, g.assist(), self.rng, self.rng.random(), lines=self.boss_lines)
            self.bob = (POOL_X0 + POOL_X1) / 2
        else:
            self.mg = DReel(spec, rod, g.assist(), self.rng, self.rng.random())
        self.mg.tough = self.tough() * (0.5 if self.tonic else 1.0)
        self.mg.morph = None
        self.tonic = False
        if self.worms > 0:
            self.worms -= 1
            self.worm_fight = True
        else:
            self.worm_fight = False
        self.state, self.st = 'fight', 0.0
        g.audio.play('hook', 0.7)
        if boss:
            g.audio.play('warn', 0.8)

    def fight(self, dt):
        g = self.g
        mg = self.mg
        aim, steer = g.reel_input()
        mg.update(dt, self.holding(), aim, steer)
        fx, fy = self.fish_xy()
        for ev in mg.events:
            k = ev[0]
            if k in ('lunge', 'dive', 'turn', 'surface'):
                self.splash(fx, WATER_Y, 6)
                g.audio.play('splash_small', 0.5)
            elif k == 'warn':
                self.rings.append([fx, WATER_Y, 2.0, 0.0])
                g.audio.play('warn', 0.6)
            elif k in ('leap', 'splashdown', 'second', 'stage'):
                self.splash(fx, WATER_Y, 14)
                self.rings.append([fx, WATER_Y, 4.0, 0.0])
                g.audio.play('splash', 0.7)
                g.shake(2.5 if k != 'stage' else 4.0)
                if k == 'stage':
                    g.audio.play('jingle1', 0.5)
            elif k == 'perfect':
                g.audio.play('chime%d' % self.rng.randrange(5), 0.8)
            elif k == 'nice':
                g.audio.play('chime0', 0.6)
            elif k == 'miss':
                g.audio.play('nibble', 0.6)
            elif k == 'glimmer':
                n = max(1, ev[1] // 4)
                self.pearls += n
                self.pop('+%d pearl%s' % (n, 's' if n > 1 else ''), (240, 240, 255))
                g.audio.play('coin', 0.6)
            elif k == 'click':
                g.audio.play('click', 0.3)
            elif k == 'creak':
                g.audio.play('creak', 0.6)
                g.shake(0.7)
        mg.events.clear()
        if mg.result == 'caught':
            self.landed()
        elif mg.result in ('snap', 'escape'):
            self.lost_fish(mg.result)

    def landed(self):
        g = self.g
        fish = self.fish
        kind = fish['kind']
        fish['mode'] = 'gone'
        self.pool = [p for p in self.pool if p is not fish]
        spec = fish['spec']
        lo, hi = spec['size']
        size = round(lo + (hi - lo) * self.rng.random(), 1)
        items = self.drop_loot(kind)
        if self.worm_fight and kind != 'boss' and self.rng.random() < 0.5:
            items.append(self.new_gear(self.roll_tier(0.3)))
        lines = []
        for it in items:
            if isinstance(it, int):
                self.pearls += it
                lines.append(('pearl', it))
            else:
                lines.append((it, self.add(it)))
        if kind != 'chest':
            self.taken += 1
        if kind in ('fish', 'biter'):
            self.caught += 1
        self.loot = dict(spec=spec, size=size, kind=kind, lines=lines,
                         opened=kind in ('fish', 'biter') and self.caught == self.need)
        self.mg = None
        self.bob = None
        self.fish = None
        self.state, self.st = 'land', 0.0
        self.splash(LEDGE_X + 30, WATER_Y, 10)
        g.audio.play('splash', 0.6)
        g.audio.play('jingle2' if kind != 'boss' else 'jingle3', 0.6)
        if kind == 'boss':
            g.delve['bosses'] += 1
            g.shake(3.0)

    def after_land(self):
        kind = self.loot['kind'] if self.loot else 'fish'
        if self.loot and self.loot.get('opened'):
            self.pop('The stone door grinds open: the stair goes on down.', (200, 236, 220))
            self.g.audio.play('creak', 0.7)
        self.loot = None
        if kind == 'boss':
            self.hearts = min(self.max_hearts(), self.hearts + 1)
            self.state, self.st = 'camp', 0.0
            self.g.audio.play('page', 0.5)
        else:
            self.state, self.st = 'cast', 0.0

    def lost_fish(self, result):
        g = self.g
        fish = self.fish
        kind = fish['kind']
        name = fish['spec']['name']
        self.mg = None
        self.bob = None
        hurt = 0
        if result == 'snap':
            hurt = 1
            self.pop('Snap! The line breaks and whips your hand.  -1 heart', (250, 160, 150))
            g.audio.play('snap', 0.7)
        elif kind in ('biter', 'boss'):
            hurt = 1
            self.pop(('%s bites you as it breaks free!  -1 heart' % name) if kind == 'biter' else
                     '%s drags you to the edge!  -1 heart' % name, (250, 160, 150))
            g.audio.play('splash', 0.7)
        else:
            self.pop('It got away.', (230, 210, 200))
        fish['mode'] = 'swim'
        self.fish = None
        if hurt:
            g.shake(3.0)
            self.hearts -= hurt
            if self.hearts <= 0:
                self.fail()
                return
        self.state, self.st = ('boss_wait' if kind == 'boss' else 'cast'), 0.0

    def descend(self):
        if self.state not in ('cast', 'camp') or (self.state == 'cast' and not self.stair_open()):
            return
        self.g.audio.play('page', 0.6)
        self.next_floor()

    # ------------------------------------------------------------ the end of a run
    def fail(self):
        g = self.g
        lost = self.carried()
        self.summary = dict(floor=self.floor, pearls=self.pearls, items=lost, value=self.haul_value())
        g.delve['runs'] += 1
        g.delve['lost'] += 1
        g.stats['delve_lost'] = g.stats.get('delve_lost', 0) + 1
        self.eq = {k: None for k in SLOTS}
        self.bag, self.ground, self.pearls = [], [], 0
        self.state, self.st = 'lost', 0.0
        self.panel = None
        g.audio.play('snap', 0.5)
        g.audio.play('splash', 0.8)

    def climb_out(self, text=None):
        g = self.g
        coins = self.haul_value()
        self.summary = dict(floor=self.floor, pearls=self.pearls, items=self.carried(), value=coins, text=text)
        g.coins += coins
        rec = g.delve
        rec['runs'] += 1
        rec['climbs'] += 1
        rec['coins'] += coins
        rec['haul'] = max(rec['haul'], coins)
        g.stats['delve_coins'] = g.stats.get('delve_coins', 0) + coins
        self.state, self.st = 'out', 0.0
        self.panel = None
        g.audio.play('coin', 0.7)
        g.audio.play('jingle3', 0.6)

    def give_up(self):
        self.panel = None
        self.pop('You let go and the water carries you up.', (230, 200, 190))
        self.fail()

    def close(self):
        g = self.g
        if self.state not in ('lost', 'out') and self.panel != 'rules':
            self.fail()
        self.done = True
        g.dungeon = None
        if g.overlay == 'dungeon':
            g.overlay = None
        g.release_holds()
        g.bot_aim = None
        s = self.summary
        if s and self.state == 'out':
            g.toast('Back at the dock with your haul from the Drowned Stair: +%d coins.' % s['value'], (200, 160, 70))
        elif s:
            g.toast('Back at the dock, soaked and empty-handed. The Drowned Stair keeps what you found.',
                    (110, 120, 150))
        g.check_badges()
        g.save()

    def pop(self, text, col):
        self.popups.append([text, col, 0.0])

    # ------------------------------------------------------------ update
    def fish_xy(self):
        if self.fish is not None and self.mg is not None:
            mg = self.mg
            bx = self.bob if self.bob is not None else (POOL_X0 + POOL_X1) / 2
            x = bx + (LEDGE_X + 50 - bx) * mg.progress + math.sin(math.radians(mg.fa)) * 26
            y = WATER_Y + 10 + (1 + math.cos(math.radians(mg.fa))) * 14 + (18 if mg.dive > 0 else 0)
            return x, y
        if self.fish is not None:
            return self.fish['x'], self.fish['y']
        return (POOL_X0 + POOL_X1) / 2, WATER_Y + 20

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        self.st += dt
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < 2.6]
        for d in self.drops:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
            d[3] += 300 * dt
            d[4] -= dt
        self.drops = [d for d in self.drops if d[4] > 0 and d[1] <= WATER_Y + 2]
        for r in self.rings:
            r[3] += dt
        self.rings = [r for r in self.rings if r[3] < 1.0]
        self._swim(dt)
        if self.panel:
            return
        st = self.state
        if st == 'enter' and self.st > 1.8:
            self.state, self.st = ('boss_wait' if is_boss(self.floor) else 'cast'), 0.0
        elif st == 'wait':
            self.wait -= dt
            if self.wait <= 0:
                self.fish = self._choose()
                self.fish['mode'] = 'come'
                self.state, self.st = 'come', 0.0
                if self.fish['kind'] == 'biter':
                    self.pop('Red eyes in the water: a %s! Reel in to dodge it.' % self.fish['spec']['name'],
                             (250, 170, 160))
                    self.g.audio.play('warn', 0.4)
        elif st == 'come':
            f = self.fish
            if self.st > 8:
                self.reel_in(None)                 # it lost interest
            elif abs(f['x'] - self.bob) < 4 and abs(f['y'] - (WATER_Y + 8)) < 4:
                f['mode'] = 'bite'
                self.state, self.st = 'bite', 0.0
                self.window = 0.75 + (0.35 if self.g.assist() else 0)
                self.rings.append([self.bob, WATER_Y, 2.0, 0.0])
                self.g.audio.play('hook', 0.4)
        elif st == 'bite':
            if self.st > self.window:
                self.fish['mode'] = 'swim'
                self.fish['vx'] = self.rng.choice((-1, 1)) * 30
                self.fish = None
                self.wait = self.rng.uniform(1.0, 2.6)
                self.state, self.st = 'wait', 0.0
                self.pop('Too slow: it swam off with a nibble.', (230, 210, 200))
        elif st == 'fight':
            self.fight(dt)
        elif st == 'land' and self.st > 4.0:
            self.after_land()

    def _swim(self, dt):
        rng = self.rng
        for f in self.pool:
            m = f['mode']
            if m == 'gone' or m == 'hooked':
                continue
            if m in ('come', 'bite') and self.bob is not None:
                tx, ty = self.bob, WATER_Y + 8
                if m == 'bite':
                    tx += math.sin(self.t * 30) * 1.5
                dx, dy = tx - f['x'], ty - f['y']
                d = math.hypot(dx, dy)
                sp = (46 if f['kind'] != 'chest' else 70) * dt   # a chest: you drag the lure to it
                if d <= sp:
                    f['x'], f['y'] = tx, ty
                else:
                    f['x'] += dx / d * sp
                    f['y'] += dy / d * sp
                f['vx'] = math.copysign(max(10, abs(f['vx'])), dx if abs(dx) > 1 else f['vx'])
                continue
            if f['kind'] == 'chest':
                continue
            boss = f['kind'] == 'boss'
            f['x'] += f['vx'] * dt * (0.7 if boss else 1)
            f['ph'] += dt
            lo, hi = POOL_X0 + (60 if boss else 20), POOL_X1 - (60 if boss else 20)
            if f['x'] < lo or f['x'] > hi:
                f['x'] = max(lo, min(hi, f['x']))
                f['vx'] = -f['vx']
            if rng.random() < dt * 0.25:
                f['vx'] = math.copysign(rng.uniform(10, 26), rng.choice((-1, 1)))
            f['y'] += math.sin(f['ph'] * 0.9) * 4 * dt

    def splash(self, x, y, n):
        rng = self.rng
        for _ in range(n):
            self.drops.append([x + rng.uniform(-4, 4), y - 1, rng.uniform(-50, 50), rng.uniform(-150, -60), 0.9])

    # ------------------------------------------------------------ the bot
    def auto(self, dt, rng, skill=0.8):
        g = self.g
        if self.bot_goal is None:
            self.bot_goal = rng.choice((5, 5, 10, 10, 15, 20))
        if self.panel == 'rules':
            self.begin()
            return
        if self.panel == 'bag':
            self.close_bag()
            return
        if self.panel == 'quit':
            self.panel = None
            return
        st = self.state
        if st in ('lost', 'out'):
            if self.st > 1.0:
                self.close()
            return
        if st not in ('fight',):
            self.bot_gear()
        if st == 'enter':
            return
        if st == 'cast':
            low = self.hearts <= 1
            if self.stair_open() and (not [p for p in self.pool if p['mode'] == 'swim'] or rng.random() < 0.7
                                      or low):
                self.descend()
                return
            if rng.random() < dt * 3:
                self.press('bot')
                self.release('bot')
        elif st == 'come':
            if self.fish['kind'] == 'biter' and self.hearts <= 2 and rng.random() < dt * 4:
                self.press('bot')
                self.release('bot')
        elif st == 'bite':
            if self.st > 0.15 + rng.random() * 0.3 * (1.2 - skill):
                self.press('bot')
                self.release('bot')
        elif st == 'fight':
            mg = self.mg
            g.bot_aim = (mg.fa + rng.uniform(-15, 15) * (1.4 - skill)) % 360
            if mg.strain < 0.6 and mg.warn <= 0 and mg.lunge <= 0:
                self.holds.add('bot')
            else:
                self.holds.discard('bot')
            L = mg.leap
            if L and not L['done'] and abs(L['r'] - minigame.TARGET) < 8 and L['t'] > 0.2:
                mg.press()
        elif st == 'land':
            self.holds.discard('bot')
            if self.st > 0.8:
                self.press('bot')
                self.release('bot')
        elif st == 'boss_wait':
            self.holds.discard('bot')
            if self.st > 0.8:
                self.press('bot')
                self.release('bot')
        elif st == 'camp':
            if self.st > 0.8:
                if self.floor >= self.bot_goal or self.hearts <= 1:
                    self.climb_out()
                else:
                    self.descend()

    def bot_gear(self):
        """Wear the best of everything, eat kelp when hurt, and leave the junk behind."""
        for i in range(len(self.bag) - 1, -1, -1):
            it = self.bag[i]
            if it['kind'] == 'gear':
                cur = self.eq[it['slot']]
                if cur is None or it['power'] > cur['power']:
                    self.equip(i)
                    return
            elif it['id'] == 'kelp' and self.hearts < self.max_hearts():
                self.use(i)
                return
            elif it['id'] in ('worm', 'tonic') and self.state == 'cast' and not self.worms and not self.tonic:
                self.use(i)
                return
            elif it['id'] == 'shell' and self.hearts <= 1 and self.state == 'cast':
                self.use(i)
                return
        for j in range(len(self.ground) - 1, -1, -1):
            it = self.ground[j]
            if len(self.bag) >= BAG:
                worst = min((i for i, b in enumerate(self.bag) if b['kind'] == 'gear'),
                            key=lambda i: self.bag[i]['value'], default=None)
                if worst is None or it['kind'] != 'gear' or self.bag[worst]['value'] >= it['value']:
                    continue
                self.drop(worst)
            self.pick(self.ground.index(it))
            return

    # ------------------------------------------------------------ drawing: the cave
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def _background(self):
        key = (self.floor, self.g.env.nf > 0.5)
        if self._bg and self._bg[0] == key:
            return self._bg[1]
        z = self.zone
        rng = random.Random(self.floor * 7919 + 3)
        bg = pygame.Surface((W, H))
        wall, deep = z['wall'], z['deep']
        for y in range(H):
            bg.fill(lerp_c(deep, wall, math.sin(math.pi * min(1.0, y / (WATER_Y + 10))) * 0.9), (0, y, W, 1))
        # rough stone blocks and cracks on the back wall
        for _ in range(70):
            x, y = rng.randrange(0, W), rng.randrange(30, WATER_Y - 6)
            w, h = rng.randint(14, 40), rng.randint(6, 14)
            c = lerp_c(wall, deep, rng.uniform(0.15, 0.45))
            pygame.draw.rect(bg, c, (x, y, w, h), 1)
        for _ in range(16):
            x, y = rng.randrange(0, W), rng.randrange(40, WATER_Y - 20)
            pts = [(x, y)]
            for _ in range(4):
                x += rng.randint(-6, 6)
                y += rng.randint(3, 8)
                pts.append((x, y))
            pygame.draw.lines(bg, darken(wall, 0.4), False, pts)
        # the ceiling and its stalactites
        pygame.draw.rect(bg, deep, (0, 0, W, 18))
        x = 0
        while x < W:
            w = rng.randint(8, 22)
            h = rng.randint(10, 48)
            col = lerp_c(deep, wall, rng.uniform(0.1, 0.4))
            pygame.draw.polygon(bg, col, [(x, 16), (x + w, 16), (x + w // 2 + rng.randint(-2, 2), 16 + h)])
            x += w + rng.randint(-4, 6)
        # the stair you came down, on the left
        rock = lerp_c(wall, (120, 120, 116), 0.25)
        for i in range(8):
            sx = i * 14
            sy = 150 + i * 14
            pygame.draw.rect(bg, darken(rock, 0.15), (sx, sy, 16, H - sy))
            pygame.draw.rect(bg, lerp_c(rock, (230, 230, 220), 0.2), (sx, sy, 16, 2))
        pygame.draw.rect(bg, darken(rock, 0.1), (0, WATER_Y, POOL_X0 + 4, H - WATER_Y))
        pygame.draw.rect(bg, lerp_c(rock, (230, 230, 220), 0.25), (0, WATER_Y, POOL_X0 + 4, 2))
        for _ in range(30):
            x, y = rng.randrange(0, POOL_X0), rng.randrange(WATER_Y + 4, H)
            bg.fill(darken(rock, rng.uniform(0.2, 0.4)), (x, y, rng.randint(2, 6), 2))
        # the far ledge on the right, and the door down
        pygame.draw.rect(bg, darken(rock, 0.1), (POOL_X1 - 4, WATER_Y, W - POOL_X1 + 4, H - WATER_Y))
        pygame.draw.rect(bg, lerp_c(rock, (230, 230, 220), 0.25), (POOL_X1 - 4, WATER_Y, W - POOL_X1 + 4, 2))
        dx, dy = 600, WATER_Y
        pygame.draw.rect(bg, darken(rock, 0.3), (dx - 18, dy - 54, 36, 54))
        pygame.draw.circle(bg, darken(rock, 0.3), (dx, dy - 54), 18)
        pygame.draw.rect(bg, deep, (dx - 13, dy - 50, 26, 50))
        pygame.draw.circle(bg, deep, (dx, dy - 50), 13)
        # zone decorations
        dec = z['decor']
        glow = z['glow']
        if dec == 'moss':
            for _ in range(40):
                x = rng.randrange(0, W)
                y = rng.choice((rng.randrange(14, 30), rng.randrange(WATER_Y - 4, WATER_Y + 1)))
                pygame.draw.ellipse(bg, lerp_c((70, 120, 60), wall, rng.uniform(0, 0.4)),
                                    (x, y, rng.randint(6, 18), rng.randint(3, 6)))
            for _ in range(12):
                x = rng.randrange(0, W)
                h = rng.randint(8, 30)
                pygame.draw.line(bg, (70, 112, 60), (x, 16), (x + rng.randint(-2, 2), 16 + h))
        elif dec == 'glowworm':
            for _ in range(46):
                x = rng.randrange(4, W - 4)
                h = rng.randint(6, 60)
                pygame.draw.line(bg, lerp_c(deep, glow, 0.25), (x, 16), (x, 16 + h))
        elif dec == 'coral':
            for _ in range(14):
                x = rng.randrange(0, W)
                y = rng.randrange(40, WATER_Y - 30)
                pygame.draw.circle(bg, lerp_c(wall, (230, 220, 200), 0.35), (x, y), 3)
                bg.fill(deep, (x - 2, y - 1, 1, 1))
                bg.fill(deep, (x + 1, y - 1, 1, 1))
        elif dec == 'abyss':
            for _ in range(30):
                x, y = rng.randrange(0, W), rng.randrange(20, WATER_Y)
                bg.fill(lerp_c(deep, glow, 0.35), (x, y, 1, 1))
        if is_boss(self.floor):
            # bones and old broken rods round the boss's pool
            for _ in range(6):
                x = rng.choice((rng.randrange(10, POOL_X0 - 10), rng.randrange(POOL_X1 + 4, W - 40)))
                pygame.draw.line(bg, (210, 200, 180), (x, WATER_Y - 2), (x + 8, WATER_Y - 4), 2)
        self._bg = (key, bg)
        return bg

    def _water(self):
        key = ('water', self.floor)
        if self._dim.get(key) is None:
            top, bot = self.zone['water']
            s = pygame.Surface((POOL_X1 - POOL_X0, H - WATER_Y), pygame.SRCALPHA)
            for y in range(s.get_height()):
                k = y / s.get_height()
                c = lerp_c(top, bot, k)
                s.fill((*c, int(150 + 90 * k)), (0, y, s.get_width(), 1))
            self._dim = {key: s}
        return self._dim[key]

    def _fish_img(self, spec, left, scale=1, kind='fish'):
        key = (spec['id'], left, scale, kind, self.floor)
        out = self._dim.get(key)
        if out is None:
            spr = art.fish_sprite(spec, scale)
            if left:
                spr = pygame.transform.flip(spr, True, False)
            out = spr.copy()
            top = self.zone['water'][0]
            if kind == 'boss':
                sh = lerp_c(top, (40, 40, 50), 0.35)
                out.fill((*lerp_c(sh, (255, 255, 255), 0.25), 220), special_flags=pygame.BLEND_RGBA_MULT)
            elif kind != 'chest':
                tint = lerp_c((255, 255, 255), top, 0.35)
                out.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._dim[key] = out
        return out

    def draw_world(self, frame):
        g = self.g
        t = self.t
        z = self.zone
        frame.blit(self._background(), (0, 0))
        glow = z['glow']
        # glowworms and drips that move
        if z['decor'] == 'glowworm':
            rng = random.Random(self.floor)
            for i in range(60):
                x, y = rng.randrange(4, W - 4), rng.randrange(18, 80)
                k = 0.5 + 0.5 * math.sin(t * rng.uniform(0.8, 2.2) + i)
                frame.fill(lerp_c(z['deep'], glow, 0.4 + 0.6 * k), (x, y, 1 + (k > 0.8), 1 + (k > 0.8)))
        elif z['decor'] == 'abyss':
            rng = random.Random(self.floor + 9)
            for i in range(20):
                x, y = rng.randrange(POOL_X0, POOL_X1), rng.randrange(WATER_Y + 10, H)
                k = 0.5 + 0.5 * math.sin(t * 1.3 + i * 1.7)
                frame.fill(lerp_c(z['water'][1], glow, 0.3 * k), (x, y, 1, 1))
        for i in range(18):
            mx = (i * 97 + t * (4 + i % 5)) % W
            my = 40 + (i * 53 % 200) + math.sin(t * 0.6 + i) * 8
            k = 0.5 + 0.5 * math.sin(t * 1.1 + i * 2.3)
            frame.fill(lerp_c(z['wall'], glow, 0.25 + 0.45 * k), (int(mx), int(my), 1, 1))
        for i in range(4):
            dx = 200 + i * 110 + (self.floor * 37 % 50)
            ph = (t * 0.8 + i * 0.37) % 1.0
            frame.fill(lerp_c(z['deep'], glow, 0.5), (dx, int(18 + ph * (WATER_Y - 18)), 1, 3))
        # the door down: shut, or open with a light on the steps below
        dx, dy = 600, WATER_Y
        if self.stair_open() or self.state == 'camp':
            for i in range(5):
                c = lerp_c(z['deep'], glow, 0.15 + i * 0.12)
                pygame.draw.rect(frame, c, (dx - 11 + i, dy - 6 - i * 8, 22 - i * 2, 3))
            lvl = int((0.5 + 0.5 * math.sin(t * 2)) * 2.99)
            halo = self._dim.get(('door', lvl))
            if halo is None:
                halo = pygame.Surface((60, 60))
                for i in range(10, 0, -1):
                    k = (0.1 + 0.04 * lvl) * ((11 - i) / 10) ** 1.5
                    pygame.draw.circle(halo, tuple(int(c * k) for c in glow), (30, 30), i * 3)
                self._dim[('door', lvl)] = halo
            frame.blit(halo, (dx - 30, dy - 52), special_flags=pygame.BLEND_RGB_ADD)
        else:
            slab = lerp_c(z['wall'], (150, 150, 146), 0.4)
            pygame.draw.rect(frame, slab, (dx - 13, dy - 50, 26, 50))
            pygame.draw.circle(frame, slab, (dx, dy - 50), 13)
            k = 0.4 + 0.3 * math.sin(t * 1.5)
            pygame.draw.circle(frame, lerp_c(slab, glow, k), (dx, dy - 34), 5, 1)
            frame.fill(lerp_c(slab, glow, k), (dx - 1, dy - 26, 2, 14))
            n = min(self.caught, self.need)
            for i in range(self.need):
                c = glow if i < n else darken(slab, 0.3)
                frame.fill(c, (dx - 8 + i * 6 - (self.need - 3) * 3, dy - 8, 4, 3))
        # fish in the pool (behind the water's tint)
        for f in self.pool:
            if f['mode'] in ('gone', 'hooked'):
                continue
            kind = f['kind']
            left = f['vx'] < 0
            if f is self.fish and f['mode'] in ('come', 'bite'):
                img = art.fish_sprite(f['spec'], 1)          # the one after your lure: in full colour
                img = pygame.transform.flip(img, True, False) if left else img
            else:
                img = self._fish_img(f['spec'], left, 3 if kind == 'boss' else 1, kind)
            x, y = f['x'], f['y']
            if kind == 'boss':
                y += math.sin(t * 0.7) * 4
            frame.blit(img, img.get_rect(center=(int(x), int(y))))
            if kind in ('biter', 'boss'):
                ex = int(x + (-1 if left else 1) * (14 if kind == 'biter' else 46))
                ey = int(y - (2 if kind == 'biter' else 8))
                c = (255, 70, 60) if kind == 'biter' else (255, 230, 120)
                frame.fill(c, (ex, ey, 2 if kind == 'biter' else 4, 2 if kind == 'biter' else 3))
            if kind == 'chest' and int(t * 2) % 3 == 0:
                frame.fill((255, 240, 170), (int(x) + 2, int(y) - 6, 1, 1))
        # the water itself
        frame.blit(self._water(), (POOL_X0, WATER_Y))
        top = z['water'][0]
        frame.fill(lerp_c(top, (255, 255, 255), 0.45), (POOL_X0, WATER_Y, POOL_X1 - POOL_X0, 1))
        for i in range(10):
            x = POOL_X0 + ((i * 53 + t * 9) % (POOL_X1 - POOL_X0 - 12))
            frame.fill(lerp_c(top, (255, 255, 255), 0.3), (int(x), WATER_Y + 3 + (i % 3) * 5, 6, 1))
        # the hooked fish, near the surface where it fights
        if self.state == 'fight' and self.fish is not None and self.mg is not None:
            fx, fy = self.fish_xy()
            boss = self.fish['kind'] == 'boss'
            img = art.fish_sprite(self.fish['spec'], 2 if boss else 1)
            ang = 20 * math.sin(t * 9)
            if math.sin(math.radians(self.mg.fa)) < 0:
                img = pygame.transform.flip(img, True, False)
            img = pygame.transform.rotate(img, ang)
            frame.blit(img, img.get_rect(center=(int(fx), int(fy))))
        # rings and drops
        for x, y, sp, a in self.rings:
            r = int(3 + a * 14 * sp / 2)
            c = lerp_c(top, (255, 255, 255), 0.6 * (1 - a))
            pygame.draw.ellipse(frame, c, (int(x) - r, int(y) - r // 4, r * 2, max(2, r // 2)), 1)
        for d in self.drops:
            frame.fill(lerp_c(top, (255, 255, 255), 0.7), (int(d[0]), int(d[1]), 1, 2))
        # you, on the ledge, with a lantern
        lk = looks.of(g)
        season = g.env.season
        shirt = looks.shirt(lk, season)
        breathe = 1 if math.sin(t * 1.6) > 0.6 else 0
        actors.draw_person(frame, LEDGE_X, WATER_Y, shirt, looks.hair(lk), getattr(g, 'hat', 'straw'), season,
                           breathe, cheer=self.state == 'land' and self.st < 1.2, look=lk)
        lx, ly = LEDGE_X - 26, WATER_Y - 12
        pygame.draw.rect(frame, (60, 50, 40), (lx - 3, ly, 7, 10))
        flick = 0.5 + 0.5 * math.sin(t * 11) * math.sin(t * 7.3)
        frame.fill((255, 214, 120), (lx - 1, ly + 3, 3, 4))
        lvl = 2 if flick > 0.7 else 1 if flick > 0.35 else 0
        halo = self._dim.get(('lantern', lvl))
        if halo is None:
            halo = pygame.Surface((130, 130))
            k0 = (0.82, 0.91, 1.0)[lvl]
            for i in range(13, 0, -1):
                k = k0 * 0.17 * ((14 - i) / 13) ** 1.6
                pygame.draw.circle(halo, (int(255 * k), int(180 * k), int(100 * k)), (65, 65), i * 5)
            self._dim[('lantern', lvl)] = halo
        frame.blit(halo, (lx - 65, ly - 60), special_flags=pygame.BLEND_RGB_ADD)
        # rod and line
        fighting = self.state == 'fight'
        bend = 0
        if fighting and self.mg:
            bend = int(6 * min(1.0, self.mg.strain + (0.4 if self.holding() else 0)))
        has_rod = self.eq['rod'] is not None
        tip = (LEDGE_X + (26 if has_rod else 12), WATER_Y - (30 if has_rod else 16) + bend)
        hand = (LEDGE_X + 4, WATER_Y - 12)
        if has_rod:
            pygame.draw.line(frame, TIERS[self.eq['rod']['tier']][1], hand, tip, 2)
        else:
            pygame.draw.line(frame, shirt, (LEDGE_X + 1, WATER_Y - 14), hand)
        target = None
        if fighting and self.fish:
            target = self.fish_xy()
        elif self.bob is not None:
            dip = 2 if self.state == 'bite' and int(t * 10) % 2 else 0
            target = (self.bob, WATER_Y - 1 + dip)
            pygame.draw.circle(frame, (230, 80, 70), (int(self.bob), WATER_Y - 2 + dip), 2)
            frame.fill((250, 250, 245), (int(self.bob) - 1, WATER_Y - 5 + dip, 3, 2))
        if target:
            pygame.draw.line(frame, (226, 230, 236), tip, (int(target[0]), int(target[1])))
        # a boss's last fish card: the trophy held up
        if self.state == 'land' and self.loot:
            spr = art.fish_sprite(self.loot['spec'], 1)
            k = min(1.0, self.st / 0.5)
            y = WATER_Y - 30 - math.sin(math.pi * k) * 18
            frame.blit(spr, spr.get_rect(center=(LEDGE_X + 18, int(y))))

    # ------------------------------------------------------------ drawing: the interface
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        z = self.zone
        # the run's readout, top left
        r = ui.panel(s, pygame.Rect(16, 16, 360, 108), radius=16)
        boss = is_boss(self.floor)
        ui.blit_text(s, 'Floor %d   %s' % (self.floor, z['name']), (r.x + 18, r.y + 12), 'bodyb', U.INK, maxw=326)
        mh = self.max_hearts()
        for i in range(mh):
            heart(s, r.x + 28 + i * 26, r.y + 50, i < self.hearts, 7)
        px = r.x + 30 + mh * 26
        s.blit(icon('pearl', (255, 255, 255), 2), (px, r.y + 38))
        ui.blit_text(s, '%d' % self.pearls, (px + 38, r.y + 54), 'bodyb', U.INK, 'midleft')
        if self.state == 'camp':
            line = 'Boss beaten! Rest at the camp'
        elif boss:
            line = 'A boss guards this floor'
        elif self.stair_open():
            line = 'The stair is open: E to go down'
        else:
            line = 'Catch %d more to open the stair' % (self.need - self.caught)
        ui.blit_text(s, line, (r.x + 18, r.y + 76), 'small', U.SOFT, maxw=326)
        # your gear, top right, and the bag button
        bx = sw - 16 - 5 * 54 - 120
        for i, sl in enumerate(SLOTS):
            it = self.eq[sl]
            rr = pygame.Rect(bx + i * 54, 20, 48, 48)
            pygame.draw.rect(s, (40, 34, 30), rr, border_radius=8)
            pygame.draw.rect(s, item_col(it) if it else (110, 96, 84), rr, 2, border_radius=8)
            s.blit(icon(sl, item_col(it), 2) if it else icon(sl, (150, 140, 130), 2, True), (rr.x + 8, rr.y + 8))
        ui.button(s, (sw - 16 - 110, 20, 110, 48), 'Bag', self.open_bag, 'normal', font='bodyb',
                  enabled=self.state not in ('fight', 'lost', 'out'))
        ui.blit_text(s, '%d / %d' % (len(self.bag), BAG), (sw - 16 - 55, 82), 'small', (240, 236, 226), 'center',
                     (30, 24, 20))
        extras = []
        if self.worms:
            extras.append('Glow worms x%d' % self.worms)
        if self.tonic:
            extras.append('Calm tonic ready')
        if self.ground:
            extras.append('%d on the floor' % len(self.ground))
        for i, e in enumerate(extras):
            ui.blit_text(s, e, (sw - 16, 100 + i * 22), 'smallb', (236, 240, 230), 'topright', (30, 24, 20))
        st = self.state
        hint = None
        if st == 'enter':
            self._banner(s, sw, 'Floor %d' % self.floor, ('Boss: ' + self.pool[0]['spec']['name']) if boss
                         else z['name'], min(1.0, self.st / 0.3, max(0.0, (1.8 - self.st) / 0.4)))
        elif st == 'cast':
            if self.stair_open():
                hint = g.hint([('key', 'Space'), 'cast again for loot   ', ('key', 'E'), 'go down the stair   ',
                               ('key', 'I'), 'bag   ', ('key', 'Esc'), 'give up'],
                              [('pad', 'A'), 'cast   ', ('pad', 'B'), 'menu'])
                ui.button(s, (sw // 2 - 110, sh - 120, 220, 50), 'Go down the stair', self.descend, 'primary',
                          nav=True)
            else:
                hint = g.hint([('key', 'Space'), 'or', ('key', 'Click'), 'cast into the pool   ', ('key', 'I'),
                               'bag   ', ('key', 'Esc'), 'give up'],
                              [('pad', 'A'), 'cast into the pool   ', ('pad', 'B'), 'menu'])
        elif st in ('wait', 'come'):
            hint = g.hint([('key', 'Space'), 'reel in   ', 'wait for the bobber to dip'],
                          [('pad', 'A'), 'reel in   ', 'wait for the bobber to dip'])
        elif st == 'bite':
            k = self.fish['kind']
            ui.blit_text(s, 'Bite!  Hook it!' if k != 'biter' else 'A biter bites! Hook it, or let it go',
                         (sw // 2, 150), 'h2', (255, 236, 200) if k != 'biter' else (255, 180, 160), 'center',
                         (40, 20, 20))
            hint = g.hint([('key', 'Space'), 'or', ('key', 'Click'), 'hook it'], [('pad', 'A'), 'hook it'])
        elif st == 'fight' and self.mg:
            spec = self.fish['spec']
            title = spec['name'] + ('  (biter!)' if self.fish['kind'] == 'biter' else '')
            minigame.draw(s, ui, self.mg, self.t, title, teach=self.g.delve['runs'] < 2)
        elif st == 'land' and self.loot:
            self._loot_card(s, sw, sh)
        elif st == 'boss_wait':
            spec = self.pool[0]['spec']
            ui.blit_text(s, spec['name'], (sw // 2, 140), 'h2', (255, 236, 190), 'center', (40, 20, 20))
            ui.blit_text(s, 'A huge shadow circles the pool.', (sw // 2, 180), 'bodyb', (236, 230, 220), 'center',
                         (30, 20, 20))
            hint = g.hint([('key', 'Space'), 'or', ('key', 'Click'), 'cast to the boss   ', ('key', 'I'), 'bag'],
                          [('pad', 'A'), 'cast to the boss'])
        elif st == 'camp':
            self._camp(s, sw, sh)
        elif st in ('lost', 'out'):
            self._summary(s, sw, sh)
        # popups
        for i, (text, col, pt) in enumerate(self.popups[-4:] if st != 'land' else ()):
            a = min(1.0, (2.6 - pt) / 0.6)
            ui.blit_text(s, text, (sw // 2, 230 + i * 34 - int(pt * 8)), 'bodyb', col, 'center', (20, 16, 24),
                         alpha=255 * max(0.0, a))
        if self.panel == 'bag':
            self._bag(s, sw, sh)
        elif self.panel == 'quit':
            self._quit(s, sw, sh)
        elif self.panel == 'rules':
            self._rules(s, sw, sh)
        if hint and not self.panel:
            w = ui.rich(s, hint, (0, 0), measure=True)
            ui.rich(s, hint, (sw // 2 - w // 2, sh - 40), (230, 236, 244), outline=(20, 30, 40))

    def _banner(self, s, sw, big, small, a):
        ui = self.g.ui
        a = max(0.0, a)
        rib = self._dim.get(('rib', sw))
        if rib is None:
            rib = pygame.Surface((sw, 110), pygame.SRCALPHA)
            for i in range(110):
                rib.fill((10, 8, 16, int(170 * math.sin(math.pi * i / 109))), (0, i, sw, 1))
            self._dim[('rib', sw)] = rib
        rib.set_alpha(int(255 * a))
        s.blit(rib, (0, 150))
        ui.blit_text(s, big, (sw // 2, 190), 'h1', (255, 240, 210), 'center', (30, 20, 20), alpha=255 * a)
        ui.blit_text(s, small, (sw // 2, 236), 'bodyb', self.zone['glow'], 'center', (20, 16, 20), alpha=255 * a)

    def _loot_card(self, s, sw, sh):
        ui = self.g.ui
        L = self.loot
        n = len(L['lines'])
        w, h = 460, 150 + n * 44
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, 120, w, h), radius=20)
        spr = art.fish_sprite(L['spec'], 2)
        s.blit(spr, spr.get_rect(center=(r.x + 70, r.y + 50)))
        col = U.INK
        if L['kind'] == 'biter':
            col = (170, 60, 50)
        ui.blit_text(s, L['spec']['name'], (r.x + 130, r.y + 22), 'h3', col, maxw=w - 150)
        sub = ('%.1f cm' % L['size']) if L['kind'] != 'chest' else 'Pried open!'
        if L['kind'] == 'boss':
            sub = 'Boss beaten!  %.1f cm' % L['size']
        ui.blit_text(s, sub, (r.x + 130, r.y + 56), 'small', U.SOFT)
        y = r.y + 96
        for it, where in L['lines']:
            if it == 'pearl':
                s.blit(icon('pearl', (255, 255, 255), 2), (r.x + 30, y))
                ui.blit_text(s, '+%d pearl%s' % (where, '' if where == 1 else 's'), (r.x + 76, y + 16), 'bodyb', U.INK, 'midleft')
            else:
                s.blit(item_icon(it, 2), (r.x + 30, y))
                ui.blit_text(s, item_name(it), (r.x + 76, y + 6), 'smallb', darken(item_col(it), 0.35)
                             if it['kind'] == 'gear' else U.INK, maxw=220)
                tag = {'equipped': 'Equipped!', 'bag': 'Into the bag', 'ground': 'Bag full: left on the floor'}[where]
                if it['kind'] == 'gear':
                    tag = TIERS[it['tier']][0] + '.  ' + tag
                ui.blit_text(s, tag, (r.x + 76, y + 26), 'small', U.SOFT, maxw=w - 100)
            y += 44
        if self.st > 0.5:
            ui.blit_text(s, 'Space to go on', (r.centerx, r.bottom - 22), 'small', U.SOFT, 'center')

    def _camp(self, s, sw, sh):
        ui = self.g.ui
        w, h = 560, 300
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2 - 20, w, h), radius=22)
        ui.blit_text(s, 'A quiet camp by the stair', (r.centerx, r.y + 32), 'h3', U.INK, 'center')
        lines = ui.wrap('The boss is beaten and the water is still. You could climb out now with everything you '
                        'carry, or go on down where the gear is better and the fish are meaner.', 'small', w - 60)
        y = r.y + 64
        for ln in lines:
            ui.blit_text(s, ln, (r.centerx, y), 'small', U.SOFT, 'midtop')
            y += 22
        ui.blit_text(s, 'Your haul is worth %d coins' % self.haul_value(), (r.centerx, y + 12), 'bodyb',
                     (150, 110, 40), 'midtop')
        bw = 236
        ui.button(s, (r.x + 30, r.bottom - 76, bw, 52), 'Climb out', lambda: self.climb_out(), 'gold', nav=True)
        ui.button(s, (r.right - 30 - bw, r.bottom - 76, bw, 52), 'Go deeper (floor %d)' % (self.floor + 1),
                  self.descend, 'primary', nav=True)
        ui.button(s, (r.centerx - 50, r.bottom + 12, 100, 40), 'Bag', self.open_bag, 'normal', font='smallb',
                  nav=True)

    def _summary(self, s, sw, sh):
        ui = self.g.ui
        S = self.summary
        a = min(1.0, self.st / 0.4)
        if a < 1:
            fade = pygame.Surface((sw, sh), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(140 * a)))
            s.blit(fade, (0, 0))
        else:
            fade = self._dim.get(('fade', sw, sh))
            if fade is None:
                fade = pygame.Surface((sw, sh), pygame.SRCALPHA)
                fade.fill((0, 0, 0, 140))
                self._dim[('fade', sw, sh)] = fade
            s.blit(fade, (0, 0))
        lost = self.state == 'lost'
        items = S['items']
        rows = (len(items) + 7) // 8
        w, h = 640, 270 + rows * 60
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2, w, h), radius=22)
        ui.blit_text(s, 'Swept away...' if lost else 'Out in the fresh air!', (r.centerx, r.y + 34), 'h2',
                     (150, 60, 60) if lost else (90, 120, 70), 'center')
        if lost:
            text = ('The water closes over you and carries you back up the stair. Everything you found is gone: '
                    'the deep keeps it.')
        else:
            text = S.get('text') or 'You climb the stair with your haul and sell the lot on the dock.'
        y = r.y + 70
        for ln in ui.wrap(text, 'small', w - 70):
            ui.blit_text(s, ln, (r.centerx, y), 'small', U.SOFT, 'midtop')
            y += 22
        ui.blit_text(s, 'Deepest this run: floor %d      Your record: floor %d' % (S['floor'], self.g.delve['best']),
                     (r.centerx, y + 8), 'smallb', U.INK, 'midtop')
        y += 44
        x0 = r.centerx - min(8, len(items) + 1) * 64 // 2
        cells = [('pearl', S['pearls'])] + [(it, None) for it in items]
        for i, (it, n) in enumerate(cells[:16]):
            cx = x0 + (i % 8) * 64
            cy = y + (i // 8) * 60
            box = pygame.Rect(cx, cy, 56, 56)
            pygame.draw.rect(s, (60, 50, 44), box, border_radius=8)
            if it == 'pearl':
                s.blit(icon('pearl', (255, 255, 255), 3, lost), (cx + 4, cy + 4))
                ui.blit_text(s, str(n), (box.right - 4, box.bottom - 4), 'smallb', (255, 255, 255), 'bottomright',
                             (20, 16, 20))
            else:
                img = item_icon(it, 3)
                if lost:
                    img = img.copy()
                    img.fill((110, 100, 100, 120), special_flags=pygame.BLEND_RGBA_MULT)
                s.blit(img, (cx + 4, cy + 4))
                if it['kind'] == 'use' and it['n'] > 1:
                    ui.blit_text(s, str(it['n']), (box.right - 4, box.bottom - 4), 'smallb', (255, 255, 255),
                                 'bottomright', (20, 16, 20))
            if lost:
                pygame.draw.line(s, (220, 90, 80), (cx + 8, cy + 8), (cx + 48, cy + 48), 3)
        y += min(2, (len(cells) + 7) // 8) * 60 + 6
        if lost:
            ui.blit_text(s, 'Lost: %d coins worth of loot' % S['value'], (r.centerx, y), 'bodyb', (170, 70, 60),
                         'midtop')
        else:
            ui.blit_text(s, 'Sold for %d coins' % S['value'], (r.centerx, y), 'bodyb', (150, 110, 40), 'midtop')
        if self.st > 0.8:
            ui.button(s, (r.centerx - 120, r.bottom - 64, 240, 48), 'Back to the dock', self.close, 'primary',
                      nav=True)

    def _quit(self, s, sw, sh):
        ui = self.g.ui
        has_shell = any(it['kind'] == 'use' and it['id'] == 'shell' for it in self.bag)
        w, h = 560, 250 + (60 if has_shell else 0)
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2, w, h), radius=22)
        ui.blit_text(s, 'Give up the run?', (r.centerx, r.y + 34), 'h3', U.INK, 'center')
        y = r.y + 66
        for ln in ui.wrap('The only safe ways out are the camp after a boss, or a Homeward Shell. Give up now and '
                          'the water takes everything you carry (worth %d coins).' % self.haul_value(), 'small',
                          w - 60):
            ui.blit_text(s, ln, (r.centerx, y), 'small', U.SOFT, 'midtop')
            y += 22
        by = r.bottom - 72
        if has_shell:
            i = next(i for i, it in enumerate(self.bag) if it['kind'] == 'use' and it['id'] == 'shell')
            ui.button(s, (r.centerx - 150, by - 62, 300, 50), 'Blow the Homeward Shell',
                      lambda i=i: (setattr(self, 'panel', None), self.use(i)), 'gold', nav=True)
        ui.button(s, (r.x + 30, by, 236, 50), 'Keep going', lambda: setattr(self, 'panel', None), 'primary', nav=True)
        ui.button(s, (r.right - 266, by, 236, 50), 'Give up (lose it all)', self.give_up, 'rose', nav=True)

    def _rules(self, s, sw, sh):
        ui = self.g.ui
        w, h = 700, 470
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2, w, h), radius=22)
        ui.blit_text(s, 'The Drowned Stair', (r.centerx, r.y + 36), 'h2', U.INK, 'center')
        y = r.y + 76
        for text in ('Old steps under the hill lead down into flooded caves. You go down with nothing: no rod, no '
                     'reel, just your hands and a bit of string.',
                     'Catch fish in each floor\'s pool to open the stair down. They drop pearls and gear for five '
                     'slots: rod, reel, line, lure and charm. The deeper you go, the better the gear.',
                     'A snapped line costs a heart. So does a biter (red eyes) that gets away. Every fifth floor a '
                     'boss guards the stair; beat it to reach a camp where you can climb out with your haul.',
                     'Lose every heart and the water carries you back up with nothing. All your loot is lost.'):
            for ln in ui.wrap(text, 'small', w - 70):
                ui.blit_text(s, ln, (r.x + 35, y), 'small', U.INK if text.startswith('Lose') else U.SOFT)
                y += 22
            y += 10
        ui.button(s, (r.x + 40, r.bottom - 74, 280, 52), 'Not today', self.close, 'normal', nav=True)
        ui.button(s, (r.right - 320, r.bottom - 74, 280, 52), 'Go down the stair', self.begin, 'primary', nav=True)

    # ------------------------------------------------------------ the bag
    def _bag(self, s, sw, sh):
        g = self.g
        ui = g.ui
        w, h = min(960, sw - 40), min(560, sh - 40)
        r = ui.panel(s, pygame.Rect(sw // 2 - w // 2, sh // 2 - h // 2, w, h), radius=22)
        ui.blit_text(s, 'Your bag', (r.x + 28, r.y + 20), 'h3', U.INK)
        mh = self.max_hearts()
        for i in range(mh):
            heart(s, r.x + 200 + i * 24, r.y + 34, i < self.hearts, 6)
        px = r.x + 210 + mh * 24
        s.blit(icon('pearl', (255, 255, 255), 2), (px, r.y + 18))
        ui.blit_text(s, '%d pearls   (haul worth %d coins)' % (self.pearls, self.haul_value()), (px + 38, r.y + 34),
                     'smallb', U.INK, 'midleft')
        ui.button(s, (r.right - 62, r.y + 16, 44, 44), 'X', self.close_bag, 'normal', font='h3')
        sel = self.sel
        # equipped, left
        x0, y0 = r.x + 26, r.y + 76
        ui.blit_text(s, 'Wearing', (x0, y0 - 6), 'smallb', U.SOFT)
        for i, sl in enumerate(SLOTS):
            it = self.eq[sl]
            box = pygame.Rect(x0, y0 + 18 + i * 66, 58, 58)
            on = sel == ('eq', sl)
            ui.button(s, box, '', (lambda sl=sl: self._select(('eq', sl))), 'tab_on' if on else 'tab', nav=True)
            s.blit(icon(sl, item_col(it), 3) if it else icon(sl, (150, 140, 130), 3, True), (box.x + 5, box.y + 3))
            if it:
                ui.blit_text(s, it['name'], (box.right + 12, box.y + 6), 'smallb', darken(item_col(it), 0.4), maxw=210)
                ui.blit_text(s, gear_desc(it)[0], (box.right + 12, box.y + 30), 'small', U.SOFT, maxw=210)
            else:
                ui.blit_text(s, 'No %s' % SLOT_NAMES[sl].lower(), (box.right + 12, box.y + 18), 'small', U.SOFT)
        rod = self.rod()
        y = y0 + 18 + 5 * 66 + 8
        for ln in ('Arc %d   Swing %d   Reel x%.2f' % (rod['arc'], rod['turn'], rod['reel']),
                   'Line strain %d%%   Bites %d%%' % (round(self.tough() * 100),
                                                       round((1 - self.stat('lure', 'bite')) * 100))):
            ui.blit_text(s, ln, (x0, y), 'small', U.INK, maxw=290)
            y += 22
        # bag grid, middle
        gx, gy = r.x + 330, r.y + 76
        ui.blit_text(s, 'Bag  %d / %d' % (len(self.bag), BAG), (gx, gy - 6), 'smallb', U.SOFT)
        for i in range(BAG):
            c, rr = i % 4, i // 4
            box = pygame.Rect(gx + c * 66, gy + 18 + rr * 66, 58, 58)
            if i < len(self.bag):
                it = self.bag[i]
                on = sel == ('bag', i)
                ui.button(s, box, '', (lambda i=i: self._select(('bag', i))), 'tab_on' if on else 'tab', nav=True)
                s.blit(item_icon(it, 3), (box.x + 5, box.y + 3))
                if it['kind'] == 'gear':
                    pygame.draw.rect(s, item_col(it), (box.x + 4, box.bottom - 9, box.w - 8, 3))
                    cur = self.eq[it['slot']]
                    if cur is None or it['power'] > cur['power'] + 0.05:
                        ui.blit_text(s, '^', (box.right - 5, box.y + 2), 'smallb', (90, 170, 80), 'topright')
                elif it['n'] > 1:
                    ui.blit_text(s, str(it['n']), (box.right - 5, box.bottom - 4), 'smallb', U.INK, 'bottomright')
            else:
                pygame.draw.rect(s, (226, 212, 186), box, border_radius=8)
                pygame.draw.rect(s, (200, 184, 158), box, 2, border_radius=8)
        # what lies on the floor
        fy = gy + 18 + 3 * 66 + 10
        ui.blit_text(s, 'On the floor here', (gx, fy), 'smallb', U.SOFT, maxw=270)
        for j, it in enumerate(self.ground[:8]):
            c, rr = j % 4, j // 4
            box = pygame.Rect(gx + c * 66, fy + 26 + rr * 66, 58, 58)
            on = sel == ('ground', j)
            ui.button(s, box, '', (lambda j=j: self._select(('ground', j))), 'tab_on' if on else 'tab', nav=True)
            s.blit(item_icon(it, 3), (box.x + 5, box.y + 3))
        if not self.ground:
            ui.blit_text(s, 'Nothing.', (gx, fy + 30), 'small', (180, 164, 146))
        # details, right
        dx, dy = r.x + 630, r.y + 76
        dw = r.right - 26 - dx
        it = self._sel_item()
        if it is None:
            for ln in ui.wrap('Pick something to see what it does. Gear goes on with Equip; the green ^ marks an '
                              'upgrade.', 'small', dw):
                ui.blit_text(s, ln, (dx, dy), 'small', U.SOFT)
                dy += 22
            return
        s.blit(item_icon(it, 5), (dx, dy))
        ui.blit_text(s, item_name(it), (dx + 92, dy + 8), 'bodyb', darken(item_col(it), 0.4) if it['kind'] == 'gear'
                     else U.INK, maxw=dw - 92)
        sub = ('%s %s' % (TIERS[it['tier']][0], SLOT_NAMES[it['slot']].lower())) if it['kind'] == 'gear' else \
            ('x%d' % it['n'])
        ui.blit_text(s, sub, (dx + 92, dy + 36), 'small', U.SOFT)
        y = dy + 96
        for ln in gear_desc(it):
            for l2 in ui.wrap(ln, 'small', dw):
                ui.blit_text(s, l2, (dx, y), 'small', U.INK)
                y += 22
        if it['kind'] == 'gear' and sel[0] != 'eq':
            cur = self.eq[it['slot']]
            y += 8
            if cur is None:
                ui.blit_text(s, 'Your %s slot is empty.' % SLOT_NAMES[it['slot']].lower(), (dx, y), 'small',
                             (90, 150, 80), maxw=dw)
            else:
                better = it['power'] > cur['power']
                ui.blit_text(s, ('Better than' if better else 'Not as good as') + ' your ' + cur['name'],
                             (dx, y), 'small', (90, 150, 80) if better else (170, 90, 70), maxw=dw)
            y += 24
        if it['kind'] == 'gear':
            ui.blit_text(s, 'Sells for %d coins' % it['value'], (dx, y + 4), 'small', U.SOFT)
        bw = (dw - 10) // 2
        by = r.bottom - 70
        kind, i = sel
        if kind == 'bag':
            if it['kind'] == 'gear':
                ui.button(s, (dx, by, bw, 46), 'Equip', lambda i=i: self.equip(i), 'primary', nav=True, font='smallb')
            else:
                ui.button(s, (dx, by, bw, 46), 'Use', lambda i=i: self.use(i), 'primary', nav=True, font='smallb')
            ui.button(s, (dx + bw + 10, by, bw, 46), 'Drop', lambda i=i: self.drop(i), 'normal', nav=True,
                      font='smallb')
        elif kind == 'eq':
            ui.button(s, (dx, by, dw, 46), 'Take off', lambda sl=i: self.unequip(sl), 'normal', nav=True,
                      font='smallb', enabled=len(self.bag) < BAG)
        else:
            ui.button(s, (dx, by, dw, 46), 'Pick up', lambda j=i: self.pick(j), 'primary', nav=True, font='smallb',
                      enabled=len(self.bag) < BAG or (it['kind'] == 'gear' and self.eq[it['slot']] is None))

    def _select(self, sel):
        self.sel = sel
        self.g.audio.play('ui', 0.3)

    def _sel_item(self):
        sel = self.sel
        if not sel:
            return None
        kind, i = sel
        if kind == 'eq':
            return self.eq.get(i)
        lst = self.bag if kind == 'bag' else self.ground
        return lst[i] if 0 <= i < len(lst) else None


# ---------------------------------------------------------------- the arch on the dock bank
def draw_world(near, g, t):
    """The old stone arch in the bank below the garden, steps going down into the dark."""
    x, y = AREA.x + 1, AREA.y
    stone = (126, 122, 112)
    dark = (78, 74, 70)
    pygame.draw.rect(near, dark, (x, y + 6, 20, 16))
    pygame.draw.circle(near, dark, (x + 10, y + 7), 10)
    pygame.draw.rect(near, (16, 18, 22), (x + 4, y + 8, 12, 14))
    pygame.draw.circle(near, (16, 18, 22), (x + 10, y + 8), 6)
    for i in range(3):
        c = lerp_c((16, 18, 22), (90, 92, 96), 0.55 - i * 0.18)
        near.fill(c, (x + 5 + i, y + 18 - i * 3, 10 - i * 2, 2))
    k = 0.5 + 0.5 * math.sin(t * 1.6)
    near.fill(lerp_c((30, 50, 60), (110, 220, 210), k * 0.7), (x + 9, y + 9, 2, 2))
    for sx, sy in ((0, 12), (0, 17), (16, 12), (16, 17), (2, 5), (14, 5), (7, 0), (11, 0)):
        near.fill(stone, (x + sx, y + sy, 4, 3))
        near.fill((150, 146, 136), (x + sx, y + sy, 4, 1))
    for mx in (1, 5, 13, 17):
        near.fill((86, 132, 70), (x + mx, y + 2 + (mx % 3), 3, 2))
