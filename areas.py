"""The places Rosie's truck reaches (0.5.5): Pinecrest Reservoir, Copper Falls, Gull Point and the Old Quarry.

Each is a short walk like the Far Shore: the truck parked at the left end (drive home from it), someone who lives
there to chat to (and who takes your cooler orders), and water with three fish of its own. Pinecrest has a rowboat
landing for the deep water (with the roof rack, your boat comes along), Copper Falls has its waterfall pool, Gull
Point has rock pools on the beach and a cliff path down to Saltmarsh's harbour, and the Old Quarry's pool only wakes
up after dark.

Runs under Game.overlay 'area' with Game.aqscene. The state for the roads lives in Game.truck (truck.py).
"""
import math
import random

import pygame

import art
import look as looks
import minigame
import town as T
import truck as TR
import ui as U
from art import W, H, lerp_c, darken, lighten, add_glow
from data import FISH_BY_ID, JUNK_BY_ID, phase_of

HEADLESS = False
fmt_clock = str

AW = 1200
FLOOR = T.GROUND
WALK = 62.0
TRUCK_X = 70

AREAS = {
    'reservoir': dict(
        name='Pinecrest Reservoir', npc=dict(name='Ranger Ida', role='reservoir ranger', shirt=(110, 120, 80),
                                             hair=(120, 80, 50), hat='beanie', x=330),
        water=(470, 1110), spot=446, boat=476, deep=920, fish=('cutthroat', 'kokanee', 'goldtrout'),
        desc='A cold, clear lake held back by an old stone dam, high in the pines. Ranger Ida keeps the fire tower.',
        lines=['The water up here is snowmelt. Clean enough to drink, cold enough to make you yelp.',
               'Golden trout keep to the deep water by the dam. You need a boat to reach them.',
               'Kokanee turn red in autumn. Like the maples, but wetter.',
               'From the tower you can see all the way down to your lake on a clear day.']),
    'falls': dict(
        name='Copper Falls', npc=dict(name='Hal', role='keeps the Falls Lodge', shirt=(160, 90, 70),
                                      hair=(60, 50, 44), hat='bucket', x=300),
        water=(560, 1160), spot=536, fish=('darter', 'steelhead', 'copperjaw'), fall=960,
        desc='The river tumbles down a copper-coloured cliff into a deep pool. Hal runs the little lodge.',
        lines=['They say the Copperjaw comes up the falls in autumn, at first light and last light.',
               'Steelhead run in the cold months. Fight like they are still at sea.',
               'Darters hide under the stones in the rapids. Tiny, but bright as sweets.',
               'Sit on the porch a while. The falls do the talking up here.']),
    'gullpoint': dict(
        name='Gull Point', npc=dict(name='Morag', role='runs the Clifftop Cafe', shirt=(90, 120, 160),
                                    hair=(200, 120, 80), hat='none', x=290),
        water=(640, 1200), spot=616, fish=('blenny', 'sandeel', 'seatrout'), pools=(450, 540), path=180,
        desc="Wind, gulls and a beach of rock pools under the cliffs. Morag's cafe does the best scones on the coast.",
        lines=['Sea trout come into the bay at dusk. Bring a lantern.',
               "The rock pools are full of blennies. They'll nibble your fingers if you let them.",
               'Saltmarsh is just down the cliff steps by the cafe. Mind them when it is wet.',
               'A gull stole a whole scone off a lady yesterday. Plate and all.']),
    'quarry': dict(
        name='The Old Quarry', npc=dict(name='Bertram', role='quarry watchman', shirt=(90, 96, 110),
                                        hair=(220, 220, 214), hat='bowler', x=310),
        water=(470, 1120), spot=446, boat=476, deep=900, fish=('cavefish', 'ironcarp', 'glowscale'),
        desc='A flooded stone quarry, deep and green and very still. Its fish only stir after dark. Bertram keeps watch.',
        lines=['Nothing bites in the daytime here. Come back when the stars are out.',
               'Glowscales like a clear sky. Something about seeing the stars.',
               'The iron carp are as old as the machinery. Possibly older.',
               'Seventy feet deep, that pool. Nobody has seen the bottom.']),
}
WEIGHTS = {'cutthroat': 50, 'kokanee': 40, 'goldtrout': 14, 'darter': 50, 'steelhead': 34, 'copperjaw': 8,
           'blenny': 50, 'sandeel': 36, 'seatrout': 26, 'cavefish': 50, 'ironcarp': 30, 'glowscale': 12}
POOL_FINDS = ['A little green crab waves a claw at you.', 'A starfish, orange as a sunset.',
              'Anemones close up as your shadow falls on them.', 'A shrimp, see-through and twitchy.',
              'A periwinkle trundles across a stone.']


def available(g, f, deep=False):
    """Can this fish bite now?"""
    if f['seasons'] is not None and g.env.season not in f['seasons']:
        return False
    if f['phases'] is not None and phase_of(g.minute) not in f['phases']:
        return False
    if f['id'] == 'goldtrout' and not deep:
        return False
    if f['id'] == 'glowscale' and g.weather not in ('clear', 'sunny', 'fair'):
        return False
    return True


def bite_odds(g, area, deep=False):
    out = []
    for fid in AREAS[area]['fish']:
        f = FISH_BY_ID[fid]
        if available(g, f, deep):
            w = WEIGHTS[fid] * (3 if deep and f['rarity'] >= 3 else 1)
            out.append((f, w))
    return out


def note_for(g, area):
    """A line for the region map: what's biting there now."""
    if area == 'quarry' and phase_of(g.minute) != 'night':
        return 'The quarry fish only bite after dark.'
    if not bite_odds(g, area, deep=True):
        return 'Nothing much is biting there right now.'
    return None


def enter(g, area):
    g.aqscene = Area(g, area)
    g.overlay = 'area'
    g.release_holds()
    g.fishing.reset()
    a = AREAS[area]
    if g.truck['visits'].get(area, 0) <= 1 and not getattr(g, '_area_seen', {}).get(area):
        g._area_seen = dict(getattr(g, '_area_seen', {}), **{area: True})
        g.toast('%s! Walk with A and D, press E to fish or talk. The truck takes you home.' % a['name'],
                (110, 150, 120))


def register(g, spec, size, area):
    import goals as goalmod
    lo, hi = spec['size']
    k = (size - lo) / max(0.01, hi - lo)
    price = int(round(spec['price'] * (0.8 + 0.6 * k)))
    entry = g.journal.get(spec['id'])
    new = entry is None
    record = entry is not None and size > entry.get('best', 0)
    if entry is None:
        entry = g.journal[spec['id']] = {'count': 0, 'best': 0}
    entry['count'] += 1
    entry['best'] = max(entry['best'], size)
    g.total += 1
    g.note('catch', fish=spec['id'], new=new, record=record)
    g.stats['caught_day'] = g.day
    if phase_of(g.minute) == 'night':
        g.stats['night'] += 1
    goalmod.on_catch(g, spec)
    st = g.truck
    st['caught'][spec['id']] = st['caught'].get(spec['id'], 0) + 1
    g.basket.append(dict(id=spec['id'], size=size, price=price))
    g.check_badges()
    g.save()
    return dict(spec=spec, size=size, price=price, new=new, record=record)


# ---------------------------------------------------------------- static art
_BACK = {}


def build(area, season):
    """The whole area's backdrop (sky not included): hills, the area's landmark, the ground and the water's bed."""
    key = (area, season)
    if key in _BACK:
        return _BACK[key]
    a = AREAS[area]
    s = pygame.Surface((AW, H), pygame.SRCALPHA)
    rng = random.Random(hash(key) & 0xffff)
    grass = art.GRASS[season]
    gd = art.GRASS_D[season]
    snowy = season == 3
    w0, w1 = a['water']
    if area == 'reservoir':
        rock = (126, 132, 146) if not snowy else (180, 190, 206)
        for k in range(8):
            cx = k * 170 + rng.randint(-30, 30)
            ht = rng.randint(80, 130)
            pygame.draw.polygon(s, rock, [(cx - 140, 230), (cx, 230 - ht), (cx + 140, 230)])
            if season != 1:
                pygame.draw.polygon(s, (240, 244, 250), [(cx - 26, 230 - ht + 18), (cx, 230 - ht),
                                                         (cx + 26, 230 - ht + 18)])
        pine = {0: (56, 100, 74), 1: (48, 92, 66), 2: (60, 96, 72), 3: (70, 100, 90)}[season]
        s.fill(darken(pine, 0.15), (0, 226, AW, FLOOR - 226))
        s.fill(lerp_c(darken(pine, 0.1), grass, 0.4), (0, 276, AW, FLOOR - 276))
        for x in range(-10, AW + 10, 11):
            h = rng.randint(34, 60)
            _pine(s, x, 262 + rng.randint(-4, 4), h, lighten(pine, rng.uniform(-0.06, 0.08)), snowy)
        # the dam at the far end
        dx = 1080
        s.fill((150, 146, 140), (dx, 200, 120, 100))
        for j in range(5):
            s.fill((130, 126, 120), (dx, 210 + j * 18, 120, 1))
        for j in range(6):
            s.fill((130, 126, 120), (dx + 10 + j * 20, 200, 1, 100))
        s.fill((170, 166, 160), (dx - 4, 196, 128, 6))
        # the fire tower behind Ida's spot
        tx = a['npc']['x'] - 60
        for k in (-10, 10):
            pygame.draw.line(s, (110, 84, 62), (tx + k, FLOOR), (tx + k // 3, FLOOR - 110), 2)
        for y in range(FLOOR - 100, FLOOR, 22):
            pygame.draw.line(s, (110, 84, 62), (tx - 9, y), (tx + 9, y))
        s.fill((150, 100, 70), (tx - 12, FLOOR - 128, 24, 18))
        s.fill((200, 220, 230), (tx - 9, FLOOR - 124, 18, 7))
        pygame.draw.polygon(s, (120, 70, 56), [(tx - 15, FLOOR - 128), (tx, FLOOR - 140), (tx + 15, FLOOR - 128)])
    elif area == 'falls':
        hill = {0: (126, 164, 120), 1: (104, 150, 100), 2: (170, 140, 96), 3: (200, 208, 220)}[season]
        for x in range(AW):
            y = 190 + int(16 * math.sin(x * 0.009) + 8 * math.sin(x * 0.027 + 1))
            s.fill(hill, (x, y, 1, H - y))
        # the copper cliff and the falls
        cx = a['fall']
        cliff = (176, 110, 70) if not snowy else (190, 150, 130)
        pygame.draw.polygon(s, cliff, [(cx - 90, FLOOR + 10), (cx - 70, 120), (cx + 160, 100), (AW, 110),
                                       (AW, FLOOR + 10)])
        for j in range(8):
            y = 130 + j * 20
            s.fill(darken(cliff, 0.12), (cx - 60 + j * 3, y, 200, 2))
        cols = [(110, 164, 90), (88, 144, 76), (124, 172, 98)] if season != 2 else \
            [(204, 150, 70), (180, 110, 60), (150, 150, 70)]
        for x in range(-10, cx - 90, 30):
            _tree(s, x + rng.randint(-8, 8), 262, rng.randint(10, 16), rng.choice(cols), season)
        # Hal's lodge
        lx = a['npc']['x'] + 40
        s.fill((150, 104, 70), (lx, FLOOR - 56, 90, 56))
        for j in range(7):
            s.fill((130, 88, 60), (lx, FLOOR - 52 + j * 8, 90, 1))
        pygame.draw.polygon(s, (110, 70, 56), [(lx - 8, FLOOR - 56), (lx + 45, FLOOR - 84), (lx + 98, FLOOR - 56)])
        s.fill((250, 220, 140), (lx + 14, FLOOR - 40, 14, 12))
        s.fill((250, 220, 140), (lx + 62, FLOOR - 40, 14, 12))
        s.fill((90, 60, 44), (lx + 38, FLOOR - 30, 14, 30))
        s.fill((120, 80, 56), (lx - 10, FLOOR - 20, 110, 3))
    elif area == 'gullpoint':
        sea = (96, 150, 186) if not snowy else (120, 156, 180)
        s.fill(sea, (0, 212, AW, H - 212))
        for x in range(0, AW, 31):
            s.fill(lighten(sea, 0.2), (x + (x // 31 % 3) * 5, 218 + (x // 31 % 5) * 6, 9, 1))
        # cliffs at the left, the beach below
        cliff = (190, 176, 150) if not snowy else (214, 214, 220)
        pygame.draw.polygon(s, cliff, [(0, 140), (200, 150), (340, 190), (400, FLOOR + 10), (0, FLOOR + 10)])
        top = (140, 180, 118) if not snowy else (236, 240, 246)
        pygame.draw.polygon(s, top, [(0, 136), (200, 146), (340, 186), (340, 192), (200, 154), (0, 144)])
        for j in range(6):
            s.fill(darken(cliff, 0.1), (20 + j * 20, 170 + j * 18, 200 - j * 12, 2))
        # the lighthouse on the point
        lx = 1020
        s.fill((120, 110, 100), (lx - 26, 206, 60, 10))
        s.fill((240, 236, 228), (lx - 6, 150, 14, 58))
        s.fill((200, 80, 70), (lx - 6, 166, 14, 8))
        s.fill((200, 80, 70), (lx - 6, 186, 14, 8))
        s.fill((60, 60, 60), (lx - 8, 142, 18, 8))
        # Morag's cafe on the cliff edge, at the top of the steps
        cx = a['npc']['x'] - 10
        s.fill((236, 230, 214), (cx - 40, FLOOR - 48, 80, 48))
        pygame.draw.polygon(s, (90, 120, 160), [(cx - 48, FLOOR - 48), (cx, FLOOR - 72), (cx + 48, FLOOR - 48)])
        for k in range(5):
            s.fill((220, 90, 80) if k % 2 == 0 else (250, 250, 250), (cx - 40 + k * 16, FLOOR - 48, 16, 6))
        s.fill((250, 220, 140), (cx - 30, FLOOR - 34, 16, 12))
        s.fill((90, 70, 60), (cx + 8, FLOOR - 30, 14, 30))
    else:   # quarry
        rock = {0: (176, 160, 134), 1: (186, 166, 130), 2: (170, 146, 116), 3: (206, 206, 214)}[season]
        pygame.draw.polygon(s, rock, [(0, 120), (AW, 100), (AW, FLOOR + 10), (0, FLOOR + 10)])
        for j in range(9):
            y = 112 + j * 20
            s.fill(darken(rock, 0.1 + 0.02 * (j % 3)), (0, y, AW, 2))
            for x in range(0, AW, 90):
                s.fill(darken(rock, 0.14), (x + (j % 2) * 45, y, 1, 20))
        top = gd if not snowy else (236, 240, 246)
        s.fill(top, (0, 96, AW, 14))
        for x in range(0, AW, 5):
            s.fill(top, (x, 106, 2, rng.randint(3, 8)))
        # the old crane and Bertram's hut
        cx = 1000
        s.fill((130, 90, 60), (cx, 120, 5, FLOOR - 120))
        pygame.draw.line(s, (130, 90, 60), (cx + 2, 124), (cx - 140, 150), 3)
        pygame.draw.line(s, (90, 90, 90), (cx - 134, 150), (cx - 134, 210))
        s.fill((80, 80, 84), (cx - 140, 210, 12, 8))
        hx = a['npc']['x'] + 40
        s.fill((120, 110, 100), (hx, FLOOR - 44, 64, 44))
        s.fill((90, 80, 70), (hx - 4, FLOOR - 48, 72, 6))
        s.fill((250, 220, 140), (hx + 10, FLOOR - 34, 12, 10))
        s.fill((70, 60, 54), (hx + 36, FLOOR - 30, 14, 30))
    # the ground and the bank
    for x in range(0, AW, 2):
        if w0 <= x < w1:
            continue
        s.fill(grass if area != 'gullpoint' else (226, 206, 160), (x, FLOOR - 2, 2, 5))
        s.fill(gd if area != 'gullpoint' else (206, 184, 140), (x, FLOOR + 3, 2, H - FLOOR - 3))
    for x in range(0, AW, 9):
        if not (w0 <= x < w1) and area != 'gullpoint':
            s.fill(darken(gd, 0.1), (x, FLOOR - 4, 1, 3))
    _BACK[key] = s
    return s


def _pine(s, x, base, h, col, snow=False):
    for k in range(4):
        w = int(h * 0.26 * (1 - k * 0.2)) + 2
        y = base - int(h * (0.25 + k * 0.2))
        pygame.draw.polygon(s, col, [(x - w, y + int(h * 0.22)), (x, y - 4), (x + w, y + int(h * 0.22))])
        if snow:
            s.fill((240, 244, 250), (x - w // 2, y + 2, w, 1))
    s.fill(darken(col, 0.3), (x - 1, base - int(h * 0.2), 2, int(h * 0.2)))


def _tree(s, x, base, r, col, season):
    s.fill((96, 70, 50), (x - 1, base - r, 3, r))
    if season == 3:
        for k in (-1, 1):
            pygame.draw.line(s, (110, 90, 74), (x, base - r), (x + k * r // 2, base - r - r // 2))
        return
    pygame.draw.circle(s, darken(col, 0.12), (x, base - r - r // 3), r)
    pygame.draw.circle(s, col, (x - 1, base - r - r // 3 - 1), r - 1)


# ---------------------------------------------------------------- the scene
class Area:
    kind = 'area'

    def __init__(self, g, area, rng=None):
        self.g = g
        self.area = area
        self.a = AREAS[area]
        self.rng = rng or random.Random()
        self.t = 0.0
        self.x = TRUCK_X + 40.0
        self.face = 1
        self.step = 0.0
        self.target = None
        self.on_arrive = None
        self.scroll = 0.0
        self.panel = None               # None, 'npc', 'truck'
        self.line = ''
        self.fx = []
        self.done = False
        self.holds = set()
        self.fs = None
        self.rowing = False             # out in the rowboat on the deep water
        self.peeked = set()
        self.mist = []
        self.near = pygame.Surface((W, H), pygame.SRCALPHA)
        self.glows = (art.glow(30, (255, 220, 150)), art.glow(12, (150, 255, 230)))

    # ------------------------------------------------------------ what's in reach
    def nearest(self):
        a = self.a
        x = self.x
        if self.rowing:
            return ('boat', None)
        if abs(x - TRUCK_X) < 34:
            return ('truck', None)
        if abs(x - a['npc']['x']) < 16:
            return ('npc', None)
        if a.get('boat') and abs(x - a['boat']) < 13 and TR.has(self.g, 'rack'):
            return ('boat', None)
        for px in a.get('pools', ()):
            if abs(x - px) < 18:
                return ('pool', px)
        if a.get('path') and abs(x - a['path']) < 26:
            return ('path', None)
        if abs(x - a['spot']) < 50:
            return ('fish', None)
        return None

    def prompt(self):
        n = self.nearest()
        if not n or self.fs:
            return None
        kind, v = n
        g = self.g
        if kind == 'truck':
            return "Rosie's truck (drive home)"
        if kind == 'npc':
            return 'Talk to %s' % self.a['npc']['name']
        if kind == 'boat':
            return 'Fish the deep water' if self.rowing else 'Row out to the deep water'
        if kind == 'pool':
            return 'Peer into the rock pool'
        if kind == 'path':
            return 'Take the cliff steps down to Saltmarsh'
        if kind == 'fish':
            if self.area == 'quarry' and phase_of(g.minute) != 'night':
                return 'The quarry pool  (fish stir after dark)'
            return 'Fish here'
        return None

    def interact(self):
        n = self.nearest()
        if not n:
            return
        kind, v = n
        g = self.g
        if kind == 'truck':
            self.open('truck')
        elif kind == 'npc':
            self.open('npc')
        elif kind == 'boat':
            if self.rowing:
                self.start_fishing(deep=True)
            else:
                self.rowing = True
                self.x = float(self.a['deep'])
                g.audio.play('plop', 0.5)
                g.toast('You row out into the deep water. Press E to fish, Esc to row back.', (90, 140, 180))
        elif kind == 'pool':
            self.peek(v)
        elif kind == 'path':
            self.to_saltmarsh()
        elif kind == 'fish':
            self.start_fishing()

    def peek(self, px):
        g = self.g
        if px in self.peeked:
            g.toast('Just the blennies, minding their own business.', (110, 140, 150))
            return
        self.peeked.add(px)
        if self.rng.random() < 0.3:
            c = JUNK_BY_ID['clam']
            g.basket.append(dict(id='clam', size=round(self.rng.uniform(*c['size']), 1), price=c['price']))
            g.audio.play('jingle2', 0.5)
            g.toast('A Pearl Clam, tucked under the weed! Into the basket.', (200, 150, 80))
        else:
            g.toast(self.rng.choice(POOL_FINDS), (110, 140, 150))
            g.audio.play('plip', 0.5)

    def to_saltmarsh(self):
        g = self.g
        import harbour
        self.done = True
        g.road_trip = self.area
        g.advance_time(10)
        harbour.enter(g)
        g.fade, g.fade_dir = 1.0, -1
        g.toast('Down the cliff steps to Saltmarsh. Leave the harbour to climb back up.', (90, 140, 180))

    def open(self, panel):
        g = self.g
        self.panel = panel
        if panel == 'npc':
            rng = random.Random(g.day * 31 + int(g.minute // 60) + len(self.area))
            lines = list(self.a['lines'])
            o = g.truck['order']
            if o and o['to'] == self.area:
                lines = ['Is that my order coming? I could eat a horse. Or a %s.' % FISH_BY_ID[o['fish']]['name'],
                         ] + lines[:1]
            self.line = rng.choice(lines)
        g.release_holds()
        g.audio.play('page', 0.6)

    def close_panel(self):
        self.panel = None
        self.g.audio.play('page', 0.5)

    def drive_home(self, fast=False):
        g = self.g
        self.done = True
        self.panel = None
        if self.fs:
            self.fs = None
            g.bot_aim = None
        TR.head_home(g, self.area, fast=fast)

    # ------------------------------------------------------------ fishing
    def start_fishing(self, deep=False):
        g = self.g
        if self.area == 'quarry' and phase_of(g.minute) != 'night':
            g.toast('The quarry pool lies still as glass. Its fish only stir after dark.', (110, 130, 150))
            return False
        if not bite_odds(g, self.area, deep):
            g.toast('Nothing is biting here right now. Try another time of day, or another season.', (110, 130, 150))
            return False
        if not deep:
            self.x, self.face = float(self.a['spot']), 1
        w0, w1 = self.a['water']
        bx = self.x + self.rng.uniform(50, 110)
        bx = max(w0 + 20, min(w1 - 20, bx))
        wait = self.rng.uniform(4.0, 9.0) * g.boost('bite')
        self.fs = dict(state='wait', t=0.0, wait=wait, bx=bx, by=FLOOR + 22 + self.rng.uniform(-4, 6), deep=deep)
        g.audio.play('cast', 0.5)
        return True

    def hook(self):
        g = self.g
        fs = self.fs
        if not fs or fs['state'] != 'bite':
            return False
        pool = bite_odds(g, self.area, fs['deep'])
        if not pool:
            self.fs = None
            return False
        spec = self.rng.choices([p for p, _ in pool], [w for _, w in pool])[0]
        lo, hi = spec['size']
        k = min(1.0, self.rng.random() ** 1.6 + g.luck * 0.03 + g.boost('size'))
        fs.update(state='fight', t=0.0, spec=spec, size=round(lo + (hi - lo) * k, 1),
                  mg=minigame.ReelGame(spec, g.rod_spec(), g.assist(), self.rng, k))
        g.use_bait()
        g.audio.play('hook', 0.7)
        return True

    def _fish_update(self, dt):
        g = self.g
        fs = self.fs
        fs['t'] += dt
        st = fs['state']
        if st == 'wait':
            if fs['t'] >= fs['wait']:
                fs['state'], fs['t'] = 'bite', 0.0
                g.audio.play('bite', 0.7)
                self.rings_at(fs['bx'], fs['by'])
            elif self.rng.random() < dt * 0.4:
                self.rings_at(fs['bx'], fs['by'], small=True)
        elif st == 'bite':
            if fs['t'] > (1.8 if g.assist() else 1.2):
                self.pop('Too slow. It let go.')
                fs.update(state='wait', t=0.0, wait=self.rng.uniform(3.0, 7.0))
        elif st == 'fight':
            mg = fs['mg']
            aim, steer = g.reel_input()
            mg.update(dt, bool(self.holds), aim, steer)
            for ev in mg.events:
                if ev[0] in ('lunge', 'leap', 'splashdown'):
                    self.rings_at(fs['bx'], fs['by'])
                    g.audio.play('splash_small', 0.5) if 'splash_small' in g.audio.sounds else None
                elif ev[0] == 'warn':
                    g.audio.play('warn', 0.5)
            mg.events.clear()
            if mg.result == 'caught':
                fs['card'] = register(g, fs['spec'], fs['size'], self.area)
                fs['state'], fs['t'] = 'landed', 0.0
                g.audio.play('jingle%d' % max(1, min(5, fs['spec']['rarity'])), 0.6)
                self._burst(fs['bx'], fs['by'], 18, (220, 240, 255))
                self.holds.clear()
                g.bot_aim = None
            elif mg.result in ('snap', 'escape'):
                self.pop('Snap! The line broke.' if mg.result == 'snap' else 'It got away.')
                self.fs = None
                self.holds.clear()
                g.bot_aim = None
        elif st == 'landed' and fs['t'] > 3.2:
            self.fs = None

    def rings_at(self, x, y, small=False):
        self.fx.append([x, y, 0.0, 0.0, 0.9 if not small else 0.5, 'ring'])

    def pop(self, text):
        self.fx.append([self.x, FLOOR - 50, 0.0, -12.0, 1.6, text])

    def _burst(self, x, y, n=24, col=(255, 236, 170)):
        rng = self.rng
        for _ in range(n):
            self.fx.append([x + rng.uniform(-8, 8), y + rng.uniform(-6, 6), rng.uniform(-26, 26),
                            rng.uniform(-44, -10), rng.uniform(0.8, 1.4), col])

    # ------------------------------------------------------------ input
    def key(self, k):
        g = self.g
        if self.panel == 'truck':
            if k == pygame.K_ESCAPE:
                self.close_panel()
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE):
                self.drive_home()
            elif k == pygame.K_f and self.can_fast():
                self.drive_home(fast=True)
            return
        if k == pygame.K_ESCAPE:
            if self.panel:
                self.close_panel()
            elif self.fs and self.fs['state'] != 'landed':
                self.fs = None
                self.holds.clear()
                g.bot_aim = None
                g.audio.play('plop', 0.4)
            elif self.rowing:
                self.row_back()
            else:
                self.open('truck')
            return
        if self.panel:
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e, pygame.K_SPACE):
                self.close_panel()
            return
        if self.fs:
            if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.press('key')
            return
        if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_w, pygame.K_UP):
            self.interact()
        elif k == pygame.K_v:
            self.open('truck')

    def row_back(self):
        self.rowing = False
        self.x = float(self.a['boat'])
        self.g.audio.play('plop', 0.4)

    def can_fast(self):
        return TR.ROUTE_OF[self.area] in self.g.truck['driven']

    def press(self, src='mouse'):
        if self.panel:
            return
        g = self.g
        fs = self.fs
        if fs:
            if fs['state'] == 'bite':
                self.hook()
            elif fs['state'] == 'fight':
                self.holds.add(src)
                fs['mg'].press()
            elif fs['state'] == 'landed' and fs['t'] > 0.6:
                self.fs = None
            return
        if src != 'mouse' or self.rowing:
            if self.rowing and src == 'mouse':
                self.start_fishing(deep=True)
            return
        wx, wy = g.s2w(*g.ui.mouse)
        tx = max(14.0, min(AW - 14.0, wx + self.scroll))
        a = self.a
        if tx < TRUCK_X + 30:
            return self.walk_to(TRUCK_X, self.interact)
        w0, w1 = a['water']
        if w0 <= tx <= w1 and wy > FLOOR:
            return self.walk_to(a['spot'], self.interact)
        spots = [a['npc']['x']] + list(a.get('pools', ())) + ([a['path']] if a.get('path') else []) + \
            ([a['boat']] if a.get('boat') and TR.has(g, 'rack') else [])
        for sx in spots:
            if abs(sx - tx) < 14 and wy > FLOOR - 60:
                return self.walk_to(sx, self.interact)
        self.walk_to(min(tx, w0 - 4.0) if tx > w0 else tx, None)

    def release(self, src='mouse'):
        self.holds.discard(src)

    def walk_to(self, x, then):
        self.target = max(14.0, min(float(x), self.a['water'][0] - 4.0))   # the bank's edge at most
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
            if p[5] != 'ring' and not isinstance(p[5], str):
                p[3] += 40 * dt
            p[4] -= dt
        self.fx = [p for p in self.fx if p[4] > 0]
        if self.a.get('fall') and self.rng.random() < dt * 14:
            self.mist.append([self.a['fall'] + self.rng.uniform(-30, 30), FLOOR + 12, self.rng.uniform(-8, 8), 1.4])
        for p in self.mist:
            p[0] += p[2] * dt
            p[1] -= 12 * dt
            p[3] -= dt
        self.mist = [p for p in self.mist if p[3] > 0]
        if self.fs:
            self._fish_update(dt)
            self.step = 0.0
            return
        moving = 0
        w0 = self.a['water'][0]
        if self.panel is None and not self.rowing:
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
            hi = w0 - 4.0
            self.x = max(14.0, min(hi, self.x + moving * WALK * dt))
            before = self.step
            self.step += dt * 9
            if int(before / math.pi) != int(self.step / math.pi):
                g.audio.step(0.22)
        else:
            self.step = 0.0
        want = max(0.0, min(AW - W, self.x - W / 2))
        self.scroll += (want - self.scroll) * min(1.0, dt * 5)

    def audio_ctx(self):
        return {'feeder': False, 'chimes': False}

    # ------------------------------------------------------------ the bot
    def auto(self, dt, rng):
        g = self.g
        if not hasattr(self, '_plan'):
            self._plan = ['npc'] + ['pool'] * len(self.a.get('pools', ())) + ['fish', 'fish'] + \
                (['boat', 'deep'] if self.a.get('boat') and TR.has(g, 'rack') else []) + ['home']
            self._wait = 0.0
        fs = self.fs
        if fs:
            if fs['state'] == 'bite':
                self.hook()
            elif fs['state'] == 'fight':
                mg = fs['mg']
                g.bot_aim = (mg.fa + rng.uniform(-12, 12)) % 360
                if mg.leap and not mg.leap['done'] and abs(mg.leap['r'] - minigame.TARGET) < 4:
                    mg.press()
                if mg.strain < 0.7:
                    self.holds.add('bot')
                else:
                    self.holds.discard('bot')
            elif fs['state'] == 'landed':
                self.fs = None
            return
        if self.panel:
            self._wait += dt
            if self._wait < 0.6:
                return
            self._wait = 0.0
            if self.panel == 'truck':
                self.drive_home(fast=self.can_fast() and rng.random() < 0.4)
            else:
                self.close_panel()
            return
        if self.target is not None or not self._plan:
            return
        step = self._plan.pop(0)
        a = self.a
        if step == 'npc':
            self.walk_to(a['npc']['x'], self.interact)
        elif step == 'pool':
            left = [p for p in a.get('pools', ()) if p not in self.peeked]
            if left:
                self.walk_to(left[0], self.interact)
        elif step == 'fish':
            if self.rowing:
                self.start_fishing(deep=True)
            else:
                self.walk_to(a['spot'], self.interact)
        elif step == 'boat':
            self.walk_to(a['boat'], self.interact)
        elif step == 'deep':
            self.start_fishing(deep=True)
        elif step == 'home':
            if self.rowing:
                self.row_back()
            self.walk_to(TRUCK_X, self.interact)

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def draw_world(self, frame):
        g = self.g
        env = g.env
        t = self.t
        season = env.season
        sc = int(self.scroll)
        frame.fill(env.sky[2])
        g.world._sky(frame, env)
        near = self.near
        near.fill((0, 0, 0, 0))
        back = build(self.area, season)
        near.blit(back, (0, 0), (sc, 0, W, H))
        self._water(near, sc, t, env)
        self._draw_live(near, sc, t, season)
        na = env.near_amb
        near.fill((na[0], na[1], na[2], 255), special_flags=pygame.BLEND_RGBA_MULT)
        frame.blit(near, (0, 0))
        self._lights(frame, sc, t)
        g.world._weather(frame, env)

    def _water(self, s, sc, t, env):
        a = self.a
        w0, w1 = a['water']
        base = {'reservoir': (70, 120, 150), 'falls': (70, 130, 130), 'gullpoint': (80, 140, 176),
                'quarry': (50, 110, 100)}[self.area]
        water = lerp_c(base, env.sky[2], 0.25)
        water = lerp_c(water, (16, 22, 40), env.nf * 0.55)
        x0, x1 = w0 - sc, w1 - sc
        if x1 < 0 or x0 > W:
            return
        r = pygame.Rect(x0, FLOOR - 2, x1 - x0, H - FLOOR + 2)
        s.fill(darken(water, 0.1), r)
        s.fill(water, (r.x, r.y, r.w, 3))
        s.fill(lighten(water, 0.15), (r.x, r.y, r.w, 1))
        for kx in range(6):
            for ky in range(4):
                gx = r.x + 12 + (kx * 97 + ky * 41 + int(t * (4 + ky))) % max(1, r.w - 30)
                if (t * 0.6 + kx * 0.3 + ky * 0.17) % 1 < 0.6:
                    s.fill(lighten(water, 0.3), (gx, r.y + 8 + ky * 12, 4 + ky, 1))
        if env.season == 3 and self.area == 'reservoir':
            s.fill((220, 232, 240), (r.x, r.y, min(r.w, 90), 4))
        if env.nf > 0.3:
            s.fill(lerp_c(water, (240, 240, 220), 0.5 * env.nf), (r.x + r.w // 2, r.y + 14, 8, 2))
        if a.get('fall'):                      # the falls pouring into the pool
            fx = a['fall'] - sc
            for k in range(10):
                x = fx + k * 4
                for y in range(120, FLOOR, 6):
                    c = (230, 240, 246) if (y // 6 + k + int(t * 12)) % 3 else (190, 216, 230)
                    s.fill(c, (x, y + int(t * 40) % 6, 3, 4))
            pygame.draw.ellipse(s, (236, 244, 248), (fx - 14, FLOOR - 8, 66, 14))
            for p in self.mist:
                al = max(0.0, min(1.0, p[3]))
                s.fill(lerp_c((200, 220, 230), (250, 252, 252), al), (int(p[0] - sc), int(p[1]), 3, 2))
        for px in a.get('pools', ()):
            x = px - sc
            pygame.draw.ellipse(s, (120, 110, 100), (x - 16, FLOOR + 2, 32, 12))
            pygame.draw.ellipse(s, lerp_c((90, 150, 170), (16, 22, 40), env.nf * 0.5), (x - 13, FLOOR + 4, 26, 8))
            s.fill((220, 120, 100), (x - 6, FLOOR + 7, 2, 2))
        if a.get('boat') and TR.has(self.g, 'rack'):
            bx = (a['deep'] if self.rowing else a['boat']) - sc
            bob = int(math.sin(t * 1.6) * 1)
            y = FLOOR + 6 if self.rowing else FLOOR + 2
            pygame.draw.polygon(s, (120, 76, 52), [(bx - 18, y + bob), (bx + 20, y + bob), (bx + 14, y + 7 + bob),
                                                  (bx - 12, y + 7 + bob)])
            s.fill((160, 110, 76), (bx - 17, y + bob, 36, 2))

    def _draw_live(self, s, sc, t, season):
        g = self.g
        a = self.a
        # Rosie's truck, parked
        x = TRUCK_X - sc
        if -60 < x < W + 60:
            spr = TR.truck_sprite(TR.paint_col(g), rack=TR.has(g, 'rack'), boat=False, night=g.env.nf > 0.35)
            T.ground_shadow(s, x, FLOOR, 26, 60)
            s.blit(spr, spr.get_rect(midbottom=(x, FLOOR + 1)))
            # Biscuit dozing on the bonnet
            bx, by = x + 14, FLOOR - 17
            s.fill((226, 150, 80), (bx, by, 6, 3))
            s.set_at((bx + 5, by - 1), (226, 150, 80))
        # the path sign to Saltmarsh
        if a.get('path'):
            px = a['path'] - sc
            s.fill((110, 80, 56), (px, FLOOR - 26, 2, 26))
            s.fill((236, 226, 200), (px - 2, FLOOR - 26, 22, 8))
            pygame.draw.polygon(s, (236, 226, 200), [(px + 20, FLOOR - 26), (px + 25, FLOOR - 22), (px + 20, FLOOR - 18)])
        # the person who lives here
        n = a['npc']
        nx = n['x'] - sc
        if -30 < nx < W + 30:
            T.ground_shadow(s, nx, FLOOR, 13, 60)
            T.walker(s, nx, FLOOR, 1 if self.x > n['x'] else -1, 0, n['shirt'], n['hair'], n['hat'], season)
        # you, standing on the bank or sitting in the boat
        x = int(self.x - sc)
        fy = FLOOR + 4 if self.rowing else FLOOR
        if not self.rowing:
            T.ground_shadow(s, x, FLOOR, 13, 60)
        T.walker(s, x, fy, self.face, self.step, *looks.player_colors(g, season), g.hat, season, look=looks.of(g))
        fs = self.fs
        if fs:
            tip = (x + 22, fy - 40)
            pygame.draw.line(s, (110, 80, 56), (x + 6, fy - 22), tip, 1)
            bx_, by_ = int(fs['bx'] - sc), int(fs['by'])
            if fs['state'] == 'fight':
                mg = fs['mg']
                bx_ += int(math.cos(math.radians(mg.fa)) * 10)
                by_ += int(math.sin(math.radians(mg.fa)) * 3)
            pygame.draw.line(s, (230, 230, 220), tip, (bx_, by_ - 1))
            if fs['state'] in ('wait', 'bite'):
                dip = 2 if fs['state'] == 'bite' and math.sin(t * 30) > 0 else int(math.sin(t * 2) * 0.6)
                s.fill((240, 70, 60), (bx_ - 1, by_ - 2 + dip, 3, 2))
                s.fill((250, 250, 250), (bx_ - 1, by_ + dip, 3, 1))
                if fs['state'] == 'bite':
                    s.fill((255, 230, 120), (x - 1, fy - 52, 3, 6))
                    s.fill((255, 230, 120), (x - 1, fy - 44, 3, 2))
        for p in self.fx:
            px, py = int(p[0] - sc), int(p[1])
            if p[5] == 'ring':
                rw = int(4 + (1 - p[4]) * 14)
                pygame.draw.ellipse(s, (200, 220, 230), (px - rw // 2, py - 1, rw, 3), 1)
            elif not isinstance(p[5], str):
                s.fill(p[5], (px, py, 2, 2))

    def _lights(self, frame, sc, t):
        g = self.g
        nf = g.env.nf
        if nf < 0.05:
            return
        warm, glow = self.glows
        a = self.a
        # windows and lamps glow after dark
        lamps = {'reservoir': [(a['npc']['x'] - 60, FLOOR - 120)], 'falls': [(a['npc']['x'] + 61, FLOOR - 34),
                                                                              (a['npc']['x'] + 109, FLOOR - 34)],
                 'gullpoint': [(a['npc']['x'] - 32, FLOOR - 28), (1022, 146)],
                 'quarry': [(a['npc']['x'] + 56, FLOOR - 29), (a['spot'] - 60, FLOOR - 30)]}[self.area]
        for lx, ly in lamps:
            x = lx - sc
            if -40 < x < W + 40:
                add_glow(frame, warm, (x, ly), nf * (0.8 + 0.1 * math.sin(t * 3 + lx)))
        if self.area == 'quarry':                          # the quarry lamp on its post, and the glowscales
            x = a['spot'] - 60 - sc
            frame.fill((int(200 * nf), int(150 * nf), int(70 * nf)), (x - 1, FLOOR - 32, 3, 3),
                       special_flags=pygame.BLEND_ADD)
            if g.weather in ('clear', 'sunny', 'fair'):
                for k in range(5):
                    gx = a['water'][0] + 60 + (k * 131 + int(t * 6)) % (a['water'][1] - a['water'][0] - 120) - sc
                    gy = FLOOR + 16 + (k * 7) % 22
                    kk = 0.5 + 0.5 * math.sin(t * 1.3 + k * 2)
                    if kk > 0.4:
                        add_glow(frame, glow, (gx, gy), kk * nf * 0.7)
        if TR.has(g, 'rack') or True:                       # the truck's sidelights
            x = TRUCK_X - sc + 26
            frame.fill((int(160 * nf), int(150 * nf), int(100 * nf)), (x, FLOOR - 13, 2, 2),
                       special_flags=pygame.BLEND_ADD)

    # ------------------------------------------------------------ UI
    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        sc = self.scroll
        fs = self.fs
        a = self.a
        if fs and fs['state'] == 'fight':
            minigame.draw(s, ui, fs['mg'], self.t, fs['spec']['name'] if fs['spec']['id'] in g.journal else
                          'Something on the line...', teach=False)
            return
        ui.blit_text(s, a['name'], (sw // 2, 26), 'h3', (255, 250, 240), 'center', (30, 30, 50))
        o = g.truck['order']
        if o and o['to'] == self.area:
            info = 'Order for %s: %d %s' % (a['npc']['name'], o['n'], FISH_BY_ID[o['fish']]['name'])
        else:
            from data import ROAD_FISH
            fish = [f for f in ROAD_FISH if f['spot'] == self.area]
            info = 'Fish found here: %d of %d' % (sum(1 for f in fish if f['id'] in g.journal), len(fish))
            nt = note_for(g, self.area)
            if nt:
                info += '   -   ' + nt
        ui.blit_text(s, info, (sw // 2, 58), 'small', (236, 244, 230), 'center', (20, 30, 24))
        ui.blit_text(s, fmt_clock(g.minute), (24, 22), 'bodyb', (255, 250, 240), 'topleft', (30, 30, 50))
        for p in self.fx:
            if isinstance(p[5], str) and p[5] != 'ring':
                ui.blit_text(s, p[5], (int((p[0] - sc) * k), int(p[1] * k)), 'bodyb', (255, 246, 226), 'center',
                             (30, 26, 30), alpha=int(255 * min(1.0, p[4])))
        if fs and fs['state'] == 'landed':
            self._card(s, fs['card'])
            return
        p = self.prompt() if self.panel is None and self.target is None else None
        if self.panel is None and not p and abs(a['npc']['x'] - self.x) < 80:
            ui.blit_text(s, '%s, %s' % (a['npc']['name'], a['npc']['role']),
                         (int((a['npc']['x'] - sc) * k), int((FLOOR - 44) * k)), 'tiny', (255, 250, 236), 'center',
                         outline=(30, 30, 40))
        if p:
            px = int((self.x - sc) * k)
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (px, int((FLOOR - 40) * k) - 6)
            r.x = max(12, min(sw - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        if fs and fs['state'] in ('wait', 'bite'):
            text = 'Strike! Press E or click!' if fs['state'] == 'bite' else 'Waiting for a bite...   Esc: reel in'
            ui.blit_text(s, text, (sw // 2, sh - 120), 'h3' if fs['state'] == 'bite' else 'bodyb',
                         (255, 240, 200), 'center', (30, 26, 30))
        if self.panel is None:
            if self.rowing:
                hint = g.hint([('key', 'E'), 'or', ('key', 'Click'), 'fish the deep water   ', ('key', 'Esc'),
                               'row back'], [('pad', 'A'), 'fish   ', ('pad', 'B'), 'row back'])
            else:
                hint = g.hint([('key', 'A'), ('key', 'D'), 'or', ('key', 'Click'), 'to walk   ', ('key', 'E'),
                               'fish, talk   ', ('key', 'Esc'), 'the truck'],
                              [('pad', 'STICK'), 'walk   ', ('pad', 'A'), 'fish, talk   ', ('pad', 'B'), 'the truck'])
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, sh - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
            return
        g.dim(s)
        if self.panel == 'npc':
            self._draw_npc(s)
        else:
            self._draw_truck(s)

    def _card(self, s, c):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        spec = c['spec']
        r = pygame.Rect(sw // 2 - 230, sh // 2 - 150, 460, 250)
        ui.panel(s, r, radius=22)
        col = (240, 214, 130) if spec['rarity'] >= 3 else (220, 230, 210)
        pygame.draw.rect(s, col, (r.x + 20, r.y + 20, r.w - 40, 120), border_radius=16)
        spr = art.fish_sprite(spec, 3)
        s.blit(spr, spr.get_rect(center=(r.centerx, r.y + 80)))
        ui.blit_text(s, spec['name'], (r.centerx, r.y + 160), 'h3', U.INK, 'center')
        tag = 'New!  ' if c['new'] else 'Record!  ' if c['record'] else ''
        ui.blit_text(s, '%s%.1f cm   worth %d' % (tag, c['size'], c['price']), (r.centerx, r.y + 196), 'smallb',
                     U.SOFT, 'center')
        ui.blit_text(s, 'Into the basket. Click to cast again.', (r.centerx, r.y + 224), 'tiny', U.SOFT, 'center')

    def _window(self, s, title, h=420):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        rect = pygame.Rect(sw // 2 - 400, sh // 2 - h // 2, 800, h)
        ui.panel(s, rect, radius=24)
        g.panel_header(s, rect, title)
        ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', self.close_panel, 'normal', font='h3')
        return rect

    def _draw_npc(self, s):
        g = self.g
        ui = g.ui
        n = self.a['npc']
        rect = self._window(s, n['name'])
        tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
        T.walker(tmp, 13, 38, 1, 0, n['shirt'], n['hair'], n['hat'], g.env.season)
        big = pygame.transform.scale(tmp, (104, 160))
        s.blit(big, big.get_rect(center=(rect.x + 110, rect.y + 200)))
        ui.blit_text(s, n['role'].capitalize(), (rect.x + 110, rect.y + 294), 'tiny', U.SOFT, 'center')
        y = rect.y + 110
        for ln in ui.wrap('"%s"' % self.line, 'body', rect.w - 280):
            ui.blit_text(s, ln, (rect.x + 230, y), 'body', U.INK)
            y += 32
        ui.blit_text(s, self.a['desc'], (rect.x + 230, rect.bottom - 110), 'tiny', U.SOFT, maxw=rect.w - 270)
        ui.button(s, (rect.right - 200, rect.bottom - 64, 170, 44), 'Bye for now', self.close_panel, 'normal',
                  font='smallb', nav=True)

    def _draw_truck(self, s):
        g = self.g
        ui = g.ui
        rect = self._window(s, "Rosie's truck")
        r = TR.ROUTES[TR.ROUTE_OF[self.area]]
        spr = TR.truck_sprite(TR.paint_col(g), rack=TR.has(g, 'rack'), boat=TR.has(g, 'rack'), cat=True)
        big = pygame.transform.scale(spr, (spr.get_width() * 4, spr.get_height() * 4))
        s.blit(big, big.get_rect(center=(rect.x + 170, rect.y + 190)))
        ui.blit_text(s, 'Home to the cabin along %s.' % r['name'], (rect.x + 340, rect.y + 110), 'body', U.INK,
                     maxw=rect.w - 380)
        ui.blit_text(s, 'About %d minutes. Biscuit is already on the seat.' % r['minutes'], (rect.x + 340, rect.y + 150),
                     'small', U.SOFT, maxw=rect.w - 380)
        ui.button(s, (rect.x + 340, rect.y + 210, rect.w - 380, 52), 'Drive home', self.drive_home, 'primary',
                  font='bodyb', nav=True)
        ui.button(s, (rect.x + 340, rect.y + 272, rect.w - 380, 44), 'Fast travel home  (F)',
                  lambda: self.drive_home(fast=True), 'normal', self.can_fast(), font='smallb', nav=True)
        ui.button(s, (rect.x + 340, rect.y + 326, rect.w - 380, 40), 'Stay a while', self.close_panel, 'normal',
                  font='smallb', nav=True)
