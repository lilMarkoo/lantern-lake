"""Grandma Rosie's pickup truck (0.5.5): the roads out of Lantern Lake.

The truck has sat in Rosie's shed by the cabin for years. Old Tom writes about it on your fourth day; fix it up
(a battery, tyres and a tune-up) in the Garage and it opens four roads, each to a new place to fish (areas.py):
the Hill Road up to Pinecrest Reservoir, the River Road to Copper Falls, the Coast Road to Gull Point (and on to
Saltmarsh's harbour) and the Quarry Track to the Old Quarry.

Driving is a side-on scenic drive (drive.py): gas and brake over the hills, through rain, snow and the dark. Along
each road there are viewpoints to photograph, people to give a lift, animals to wait for and the odd lost thing to
bring home. Neighbours up the roads order fish from the lake: pack them in the cooler and drive gently, because a
bumpy ride spills them and a long one warms them. Once you have driven a road you can fast-travel it from the map.

Saved state is Game.truck. The truck window (overlay 'truck') has three tabs: the region map, the garage and
the orders board.
"""
import math
import random

import pygame

import ui as U

ROUTES = {
    'hill': dict(id='hill', name='The Hill Road', to='reservoir', length=4300, minutes=45, theme='hill',
                 amp=(70, 34, 12), freq=(0.0016, 0.0047, 0.013), desc='Up through the pines, with hairpins and '
                 'a long climb to the dam. Snow on the tops in winter.'),
    'river': dict(id='river', name='The River Road', to='falls', length=3900, minutes=35, theme='river',
                  amp=(26, 16, 8), freq=(0.0021, 0.0063, 0.017), desc='Along the river past the old mill and over '
                  'Copper Bridge. Gentle, rolling and green.'),
    'coast': dict(id='coast', name='The Coast Road', to='gullpoint', length=4800, minutes=55, theme='coast',
                  amp=(44, 22, 10), freq=(0.0018, 0.0055, 0.015), desc='Over the downs to the clifftops, with '
                  'the sea opening out on your right. Saltmarsh is a short walk from the end.'),
    'quarry': dict(id='quarry', name='The Quarry Track', to='quarry', length=3100, minutes=25, theme='quarry',
                   amp=(30, 18, 6), freq=(0.0024, 0.0071, 0.021), rough=True, desc='A rutted gravel track '
                   'out to the old stone quarry. Bumpy: mind the cooler.'),
}
ROUTE_OF = {r['to']: r['id'] for r in ROUTES.values()}
# things along each road: (kind, id, where along it 0..1, name)
VIEWS = [
    ('hill', 'hairpin', 0.34, 'Hairpin Lookout'), ('hill', 'dam', 0.86, 'The Dam Overlook'),
    ('river', 'mill', 0.28, 'The Old Mill'), ('river', 'bridge', 0.7, 'Copper Bridge'),
    ('coast', 'cliffs', 0.42, 'Gull Cliffs'), ('coast', 'light', 0.8, 'Saltmarsh Light'),
    ('quarry', 'starfield', 0.3, "Stargazer's Field"), ('quarry', 'rim', 0.62, 'The Quarry Rim'),
]
VIEW_BY_ID = {v[1]: v for v in VIEWS}
LOST = {   # route -> (id, thing, owner, where along it, thank-you letter)
    'hill': ('kite', "Pip's kite", 'pip', 0.55, "You found my kite!! It blew all the way up the hill road. Mum says "
             "I can't fly it near the pines any more. Here's my best marble for you."),
    'river': ('notebook', "Juniper's field notebook", 'juniper', 0.47, 'My field notebook! Two years of notes on '
              'the river birds were in there. Thank you so much. Please take this for your trouble.'),
    'coast': ('sketchbook', "Fen's sketchbook", 'fen', 0.6, "My sketchbook! I lost it painting the cliffs and I've "
              'been sulking ever since. There is a little drawing of your truck in it now. A thank-you is enclosed.'),
    'quarry': ('lure', "Old Tom's lucky lure", 'tom', 0.45, 'Well I never. My lucky lure! I dropped it out there '
               'forty years ago, chasing a carp with your grandmother. Here, a little something.'),
}
ANIMALS = {'hill': 'deer', 'river': 'ducks', 'coast': 'sheep', 'quarry': 'hedgehog'}
HIKERS = [
    ('Wanda, walking the hills', (150, 120, 170), (120, 90, 70), 'beanie'),
    ('Ned with his fishing rod', (110, 140, 100), (90, 70, 50), 'bucket'),
    ('Priya, a birdwatcher', (200, 170, 100), (40, 30, 30), 'none'),
    ('Arlo the postman', (180, 70, 70), (60, 50, 40), 'beret'),
    ('Elsie and her dog', (120, 150, 190), (220, 220, 214), 'flower'),
    ('Tobias, lost again', (160, 160, 120), (170, 120, 70), 'bowler'),
]
HIKER_LINES = ['Thanks for the lift! My feet were done for.', "Lovely truck. My gran had one just like it.",
               'Is that a cat in the front? Hello, puss!', 'You saved me an hour of walking. Here, for petrol.',
               'I was starting to think nobody drove this road any more.']
PARTS = [
    dict(id='battery', name='A new battery', need='250 coins', cost=250,
         say="Rosie's old battery is as flat as a pancake. Wren can get you a new one."),
    dict(id='tyres', name='Four good tyres', need='200 coins', cost=200,
         say='The old tyres have perished. You could see daylight through them.'),
    dict(id='tuneup', name="A tune-up from Old Tom", need='3 fish from your basket', fish=3,
         say="Old Tom knows engines. He'll do it for a few fish for his supper."),
]
UPGRADES = [
    dict(id='snow', name='Snow Tyres', cost=300, desc='Grip on snowy hills. Without them, winter climbs are a '
         'slippery struggle.'),
    dict(id='cooler', name='Big Cooler', cost=350, desc='Orders stay cold twice as long and take more bumps '
         'before anything spills.'),
    dict(id='rack', name='Roof Rack', cost=450, desc='Takes your rowboat along. Row out at Pinecrest Reservoir and '
         'the Old Quarry for the fish in the deep water.', boat=True),
]
UP_BY_ID = {u['id']: u for u in UPGRADES}
PAINTS = [('rose', 'Rosie Red', (190, 74, 76)), ('sage', 'Sage', (128, 160, 118)), ('sky', 'Sky Blue', (110, 160, 200)),
          ('butter', 'Buttercup', (230, 196, 90)), ('plum', 'Plum', (126, 84, 128)), ('cream', 'Cream', (232, 222, 196))]
PAINT_BY_ID = {p[0]: p for p in PAINTS}
PAINT_COST = 60
CLIENTS = {'reservoir': 'Ranger Ida', 'falls': 'Hal at the Falls Lodge', 'gullpoint': "Morag's Clifftop Cafe",
           'quarry': 'Bertram, the quarry watchman'}
AREA_NAMES = {'reservoir': 'Pinecrest Reservoir', 'falls': 'Copper Falls', 'gullpoint': 'Gull Point',
              'quarry': 'The Old Quarry'}
TELL_DAY = 4
COURIER = 10


# ---------------------------------------------------------------- state
def new():
    return dict(told=False, parts=[], fixed=False, ups=[], paint='rose', paints=['rose'], km=0.0, drives=0,
                driven=[], visits={}, photos=[], lifts=0, kind=0, found=[], returned=[], caught={}, spilled=0,
                delivered=0, order=None, offers=[], offers_day=0)


def clean(d):
    base = new()
    if not isinstance(d, dict):
        return base
    for k, v in base.items():
        if k in d and (type(d[k]) is type(v) or (isinstance(v, float) and isinstance(d[k], int))):
            base[k] = d[k]
    base['km'] = float(base['km'])
    base['parts'] = [p for p in base['parts'] if p in {x['id'] for x in PARTS}]
    base['ups'] = [u for u in base['ups'] if u in UP_BY_ID]
    base['paints'] = [p for p in base['paints'] if p in PAINT_BY_ID] or ['rose']
    if base['paint'] not in base['paints']:
        base['paint'] = base['paints'][0]
    base['driven'] = [r for r in base['driven'] if r in ROUTES]
    base['photos'] = [p for p in base['photos'] if p in VIEW_BY_ID]
    ids = {v[0] for v in LOST.values()}
    base['found'] = [x for x in base['found'] if x in ids]
    base['returned'] = [x for x in base['returned'] if x in ids]
    base['visits'] = {k: int(v) for k, v in base['visits'].items() if k in AREA_NAMES}
    base['offers'] = [o for o in base['offers'] if _order_ok(o)][:3]
    if base['order'] is not None and not _order_ok(base['order']):
        base['order'] = None
    return base


def _order_ok(o):
    from data import FISH_BY_ID
    return (isinstance(o, dict) and o.get('to') in AREA_NAMES and o.get('fish') in FISH_BY_ID
            and isinstance(o.get('n'), int) and isinstance(o.get('reward'), int))


def has(g, uid):
    return uid in g.truck['ups']


def paint_col(g):
    return PAINT_BY_ID[g.truck['paint']][2]


def unlocked(g):
    return g.truck['fixed']


def solo(g):
    return not getattr(g, 'solo', None) and not g.net.online


def at_home(g):
    return g.place == 'lake' and g.spot == 'dock'


# ---------------------------------------------------------------- the clock
def tick(g, before):
    st = g.truck
    if not st['told'] and g.day >= TELL_DAY and g.minute >= 7 * 60 and g.mode == 'play':
        st['told'] = True
        g.post([("Rosie's truck", "Your grandmother's old pickup is still in the shed behind the cabin, you know. "
                 "She drove it all over these hills: up to the reservoir, out to the falls, along the coast. It needs "
                 "a battery, some tyres and a bit of fettling, and I can help with the last part.\n\nPress V, or "
                 "choose Rosie's truck from the menu, to have a look at it.", '- Old Tom')])
    o = st['order']
    if o and (g.day > o['day'] or g.minute >= 21 * 60 and before < 21 * 60):
        st['order'] = None
        g.toast("%s's order went past its time. Never mind: there'll be others." % CLIENTS[o['to']], (150, 130, 110))


def morning(g):
    """A new day: fresh orders on the board, and thank-you letters for lost things you found."""
    st = g.truck
    if st['fixed'] and st['offers_day'] != g.day:
        st['offers_day'] = g.day
        st['offers'] = _make_offers(g)
    for rid, (lid, thing, who, _, letter) in LOST.items():
        if lid in st['found'] and lid not in st['returned']:
            st['returned'].append(lid)
            import town
            g.coins += 100
            g.add_friend(who, 10)
            g.post([('You found it!', letter + '\n\n(+100 coins)', '- %s' % town.FOLK[who]['name'])])


def _make_offers(g):
    from data import FISH
    rng = random.Random(g.day * 4447 + 11)
    pool = [f for f in FISH if 1 <= f['rarity'] <= 3 and not f.get('method') and not f.get('event')
            and f['id'] in g.journal]
    if not pool:
        return []
    out = []
    areas = [a for a in AREA_NAMES if a != 'quarry' or rng.random() < 0.5]
    rng.shuffle(areas)
    for a in areas[:2]:
        f = rng.choice(pool)
        n = rng.choice((2, 2, 3)) if f['rarity'] == 1 else rng.choice((1, 2)) if f['rarity'] == 2 else 1
        reward = int(round(f['price'] * n * 2.2 + 40))
        out.append(dict(to=a, fish=f['id'], n=n, reward=reward, day=g.day))
    return out


def take_order(g, i):
    st = g.truck
    if st['order'] or i >= len(st['offers']):
        return
    st['order'] = dict(st['offers'].pop(i), day=g.day)
    g.audio.play('page', 0.5)
    g.toast('Order taken: pack the fish and drive them over before 9 PM.', (110, 140, 170))


def drop_order(g):
    g.truck['order'] = None
    g.audio.play('page', 0.4)


def order_fish(g, o):
    """The fish in your basket that would fill this order (best first)."""
    return sorted([b for b in g.basket if b.get('id') == o['fish']], key=lambda b: -b['price'])


def day_note(g):
    st = g.truck
    o = st['order']
    if o:
        from data import FISH_BY_ID
        have = len(order_fish(g, o))
        return '%s wants %d %s by 9 PM (%d packed)' % (CLIENTS[o['to']], o['n'], FISH_BY_ID[o['fish']]['name'],
                                                     min(have, o['n']))
    if st['told'] and not st['fixed']:
        return "Rosie's truck is waiting in the shed (V)"
    return None


def badge_cond(g):
    from data import ROAD_FISH
    st = g.truck
    return {'roadtrip': all(st['visits'].get(a) for a in AREA_NAMES), 'courier': st['delivered'] >= COURIER,
            'sightseer': len(st['photos']) >= len(VIEWS),
            'backroads': all(f['id'] in g.journal for f in ROAD_FISH)}


# ---------------------------------------------------------------- the garage
def part_ready(g, p):
    st = g.truck
    if p['id'] in st['parts']:
        return False
    if p.get('cost'):
        return g.coins >= p['cost']
    return len(_spare_fish(g)) >= p['fish']


def _spare_fish(g):
    from data import ALL_BY_ID
    return sorted([b for b in g.basket if not ALL_BY_ID[b['id']].get('junk')], key=lambda b: b['price'])


def fit_part(g, pid):
    st = g.truck
    p = next(x for x in PARTS if x['id'] == pid)
    if not part_ready(g, p):
        return False
    if p.get('cost'):
        g.coins -= p['cost']
    else:
        for b in _spare_fish(g)[:p['fish']]:
            g.basket.remove(b)
    st['parts'].append(pid)
    g.audio.play('coin', 0.5)
    if len(st['parts']) == len(PARTS):
        st['fixed'] = True
        st['offers_day'] = g.day
        st['offers'] = _make_offers(g)
        g.audio.play('jingle3', 0.6)
        g.audio.play('horn', 0.6)
        g.toast("Rosie's truck coughs, splutters and roars into life! The roads are open.", (200, 150, 80))
    else:
        g.toast('%s: done.' % p['name'], (150, 130, 100))
    g.save()
    return True


def buy(g, uid):
    st = g.truck
    u = UP_BY_ID[uid]
    if uid in st['ups'] or g.coins < u['cost'] or (u.get('boat') and not g.has_boat()):
        return False
    g.coins -= u['cost']
    st['ups'].append(uid)
    g.audio.play('jingle2', 0.6)
    g.toast('%s fitted to the truck!' % u['name'], (200, 150, 80))
    g.save()
    return True


def paint(g, pid):
    st = g.truck
    if pid not in st['paints']:
        if g.coins < PAINT_COST:
            return False
        g.coins -= PAINT_COST
        st['paints'].append(pid)
        g.audio.play('coin', 0.5)
    st['paint'] = pid
    g.audio.play('click', 0.4)
    g.save()
    return True


# ---------------------------------------------------------------- going places
def can_leave(g, quiet=False):
    def no(msg):
        if not quiet:
            g.toast(msg, (130, 120, 110))
        return False
    if not unlocked(g):
        return no("Rosie's truck needs fixing first.")
    if not solo(g):
        return no('The roads are a quiet trip. Take the truck out when you are playing on your own.')
    if not at_home(g):
        return no('Row home to your dock first: the truck is in the shed by the cabin.')
    if g.fishing.state not in ('idle', 'waiting', 'charging'):
        return no('Finish what is on the line first.')
    if g.rest_phase is not None:
        return False
    return True


def open_(g, tab=None):
    st = g.truck
    if not st['told']:
        g.toast('Just the old shed. Something big is under a dust sheet in there.', (150, 140, 130))
        return
    if g.place != 'lake':
        g.toast("Rosie's truck is in the shed by the cabin.", (150, 140, 130))
        return
    g.truck_tab = tab or ('map' if st['fixed'] else 'garage')
    if st['fixed'] and st['offers_day'] != g.day:
        morning(g)
    g.truck_sel = getattr(g, 'truck_sel', None) or 'reservoir'
    g.overlay = 'truck'
    g.release_holds()
    g.audio.play('door', 0.5)


def depart(g, area, fast=False):
    """Set off from the cabin for an area: a drive (or, on a road you know, a fast trip)."""
    if not can_leave(g):
        return False
    rid = ROUTE_OF[area]
    if fast and rid not in g.truck['driven']:
        return False
    import drive
    g.fishing.reset()
    g.release_holds()
    cooler = _pack(g, area)
    if fast:
        return arrive(g, rid, area, cooler, fast=True)
    g.aqscene = drive.Drive(g, rid, back=False, cooler=cooler)
    g.overlay = 'drive'
    g.audio.play('door', 0.6)
    return True


def head_home(g, area, fast=False):
    """From an area back to the cabin."""
    rid = ROUTE_OF[area]
    import drive
    g.release_holds()
    if fast:
        return arrive(g, rid, 'home', None, fast=True)
    g.aqscene = drive.Drive(g, rid, back=True, cooler=None)
    g.overlay = 'drive'
    g.audio.play('door', 0.6)
    return True


def _pack(g, area):
    """Pack an order's fish into the cooler if you're heading its way."""
    o = g.truck['order']
    if not o or o['to'] != area:
        return None
    fish = order_fish(g, o)[:o['n']]
    if len(fish) < o['n']:
        from data import FISH_BY_ID
        g.toast('Not enough %s for the order yet (%d of %d). Off you go anyway.'
                % (FISH_BY_ID[o['fish']]['name'], len(fish), o['n']), (150, 130, 110))
        return None
    for b in fish:
        g.basket.remove(b)
    return dict(fish=fish, ice=1.0, jostle=0.0, spilled=0)


def arrive(g, rid, dest, cooler, fast=False, extra=None):
    """The end of a drive (or a fast trip): into the area, or home to the dock."""
    st = g.truck
    r = ROUTES[rid]
    if fast:
        g.advance_time(r['minutes'])
        if cooler:
            cooler['ice'] = max(0.0, cooler['ice'] - r['minutes'] / ice_minutes(g))
    else:
        if rid not in st['driven']:
            st['driven'].append(rid)
    st['drives'] += 1
    st['km'] += r['length'] / 100.0
    g.audio.engine(0)
    g.fade, g.fade_dir = 1.0, -1
    if dest == 'home':
        g.aqscene = None
        g.overlay = None
        g.place, g.spot = 'lake', 'dock'
        g.toast('Home again. Biscuit is first out of the cab.' if not fast else
                'You drive home to the cabin. (%d minutes)' % r['minutes'], (200, 150, 80))
        g.save()
        return True
    import areas
    st['visits'][dest] = st['visits'].get(dest, 0) + 1
    areas.enter(g, dest)
    if cooler:
        deliver(g, dest, cooler)
    if extra:
        for f in extra:
            f()
    g.check_badges()
    g.save()
    return True


def ice_minutes(g):
    return 150.0 if has(g, 'cooler') else 75.0


def deliver(g, area, cooler):
    st = g.truck
    o = st['order']
    if not o or o['to'] != area:
        g.basket.extend(cooler['fish'])
        return
    got = len(cooler['fish'])
    warm = cooler['ice'] <= 0
    pay = int(round(o['reward'] * got / o['n'] * (0.5 if warm else 1.0)))
    st['order'] = None
    who = CLIENTS[area]
    if got == 0:
        g.toast('The cooler is empty: every fish bounced out on the way. %s laughs it off.' % who, (150, 130, 110))
        return
    g.coins += pay
    st['delivered'] += 1
    g.audio.play('coin', 0.6)
    if got < o['n']:
        g.toast('%s takes the %d fish that are left: +%d coins.' % (who, got, pay), (200, 150, 80))
    elif warm:
        g.toast("%s: 'A bit warm, these.' Half pay: +%d coins." % (who, pay), (200, 150, 80))
    else:
        g.toast('%s is delighted: cold and perfect! +%d coins.' % (who, pay), (200, 150, 80))
    g.check_badges()


def in_cooler(g):
    """Fish packed in the cooler on a drive right now: saved as still in the basket, so quitting mid-drive
    never loses them."""
    sc = g.aqscene if g.overlay == 'drive' else None
    c = getattr(sc, 'cooler', None)
    return list(c['fish']) if c and not getattr(sc, 'done', False) else []


def update(g, dt):
    """Every frame: keep the engine quiet unless you're driving."""
    if g.overlay != 'drive':
        g.audio.engine(0)


# ---------------------------------------------------------------- drawing the truck
_tcache = {}


def truck_sprite(col, rack=False, cooler=False, boat=False, night=False, people=(), cat=False, wheel=0.0):
    """Rosie's pickup, side on, facing right: 52 x 28 pixels, wheels at y=24. people: shirt colours in the cab."""
    s = pygame.Surface((56, 30), pygame.SRCALPHA)
    dark = tuple(max(0, int(c * 0.72)) for c in col)
    light = tuple(min(255, int(c * 1.15 + 12)) for c in col)
    # bed and cab
    pygame.draw.rect(s, dark, (3, 13, 26, 9), border_radius=1)
    pygame.draw.rect(s, col, (4, 13, 24, 7))
    s.fill(light, (4, 13, 24, 1))
    pygame.draw.polygon(s, col, [(28, 22), (28, 6), (39, 6), (44, 13), (52, 14), (53, 22)])
    pygame.draw.polygon(s, dark, [(28, 22), (53, 22), (53, 19), (28, 19)])
    s.fill(light, (28, 6, 11, 1))
    # windows: you and whoever rides with you
    win = (34, 46, 60) if night else (170, 206, 222)
    pygame.draw.polygon(s, win, [(30, 8), (38, 8), (42, 13), (30, 13)])
    for i, shirt in enumerate(people[:2]):
        px = 37 - i * 5
        s.fill((236, 200, 170), (px, 9, 3, 3))
        s.fill(shirt, (px - 1, 12, 5, 1))
    if cat:
        s.fill((226, 150, 80), (31, 10, 3, 3))
        s.set_at((31, 9), (226, 150, 80))
        s.set_at((33, 9), (226, 150, 80))
    # bumpers, lights, mirror, door line, handle
    s.fill((200, 200, 204), (51, 19, 4, 2))
    s.fill((200, 200, 204), (1, 18, 3, 2))
    s.fill((255, 240, 180) if night else (240, 236, 220), (51, 15, 2, 2))
    s.fill((220, 70, 60), (2, 14, 2, 2))
    s.fill(dark, (40, 9, 1, 3))
    s.fill(dark, (39, 13, 1, 8))
    s.fill((60, 50, 50), (35, 15, 3, 1))
    if cooler:
        s.fill((90, 150, 200), (10, 9, 9, 5))
        s.fill((240, 240, 240), (10, 9, 9, 1))
    if rack or boat:
        s.fill((80, 80, 86), (27, 4, 14, 1))
        s.fill((80, 80, 86), (29, 4, 1, 2))
        s.fill((80, 80, 86), (38, 4, 1, 2))
    if boat:
        pygame.draw.polygon(s, (130, 86, 58), [(18, 4), (50, 4), (46, 0), (22, 0)])
        s.fill((160, 110, 76), (22, 0, 24, 1))
    # wheels with turning hub caps
    for wx in (12, 44):
        pygame.draw.circle(s, (34, 30, 32), (wx, 23), 5)
        pygame.draw.circle(s, (150, 150, 156), (wx, 23), 2)
        a = wheel
        s.set_at((wx + int(round(math.cos(a) * 3)), 23 + int(round(math.sin(a) * 3))), (90, 90, 96))
        s.set_at((wx + int(round(math.cos(a + math.pi) * 3)), 23 + int(round(math.sin(a + math.pi) * 3))),
                 (90, 90, 96))
    return s


# ---------------------------------------------------------------- the truck window
def draw(g, s):
    ui = g.ui
    sw, sh = s.get_size()
    rect = pygame.Rect(sw // 2 - 520, sh // 2 - 318, 1040, 636)
    ui.panel(s, rect, radius=24)
    g.panel_header(s, rect, "Rosie's Truck")
    ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', lambda: close(g), 'normal', font='h3')
    st = g.truck
    tab = getattr(g, 'truck_tab', 'map')
    tabs = [('map', 'Map'), ('garage', 'Garage'), ('orders', 'Orders')] if st['fixed'] else [('garage', 'Garage')]
    for i, (key, label) in enumerate(tabs):
        ui.button(s, (rect.x + 400 + i * 140, rect.y + 24, 130, 40), label,
                  lambda k=key: setattr(g, 'truck_tab', k), 'tab_on' if tab == key else 'tab')
    if tab == 'map' and st['fixed']:
        return _draw_map(g, s, rect)
    if tab == 'orders' and st['fixed']:
        return _draw_orders(g, s, rect)
    return _draw_garage(g, s, rect)


def close(g):
    g.overlay = None
    g.audio.play('page', 0.5)


# where things sit on the region map, in a 600 x 470 box
MAP_PTS = {'home': (262, 214), 'fernwick': (150, 176), 'farshore': (356, 300), 'saltmarsh': (540, 402),
           'reservoir': (300, 62), 'falls': (528, 150), 'gullpoint': (420, 428), 'quarry': (70, 330)}
ROAD_PTS = {'hill': [(262, 214), (250, 170), (286, 140), (262, 108), (300, 62)],
            'river': [(262, 214), (330, 200), (400, 160), (470, 170), (528, 150)],
            'coast': [(262, 214), (220, 280), (260, 360), (340, 400), (420, 428)],
            'quarry': [(262, 214), (190, 236), (130, 300), (70, 330)]}


def _draw_map(g, s, rect):
    ui = g.ui
    st = g.truck
    season = g.env.season
    m = pygame.Rect(rect.x + 30, rect.y + 90, 600, 470)
    land = [(150, 186, 120), (130, 176, 104), (192, 170, 110), (226, 230, 236)][season]
    pygame.draw.rect(s, land, m, border_radius=16)
    ox, oy = m.x, m.y
    P = lambda p: (ox + p[0], oy + p[1])
    # the sea, bottom right
    pygame.draw.polygon(s, (110, 160, 196), [P((600, 300)), P((600, 470)), P((330, 470)), P((380, 445)), P((470, 420)),
                                            P((560, 360))])
    # hills and mountains at the top
    for k, x in enumerate(range(150, 470, 44)):
        h = 30 + (k * 37) % 26
        pygame.draw.polygon(s, (120, 130, 140), [P((x - 30, 70)), P((x, 70 - h)), P((x + 30, 70))])
        if season != 1:
            pygame.draw.polygon(s, (240, 244, 250), [P((x - 8, 70 - h + 8)), P((x, 70 - h)), P((x + 8, 70 - h + 8))])
    # the reservoir, the lake, the river to the sea
    pygame.draw.ellipse(s, (96, 150, 186), (ox + 270, oy + 40, 70, 34))
    pygame.draw.ellipse(s, (96, 150, 186), (ox + 230, oy + 210, 170, 96))
    river = [(392, 262), (430, 290), (470, 330), (520, 380), (560, 410)]
    pygame.draw.lines(s, (96, 150, 186), False, [P(p) for p in river], 8)
    pygame.draw.lines(s, (96, 150, 186), False, [P(p) for p in ((400, 250), (460, 210), (528, 160), (580, 120))], 6)
    # the quarry pit
    pygame.draw.ellipse(s, (150, 146, 140), (ox + 34, oy + 312, 70, 40))
    pygame.draw.ellipse(s, (70, 110, 100), (ox + 48, oy + 322, 42, 22))
    # roads
    for rid, pts in ROAD_PTS.items():
        known = rid in st['driven']
        pygame.draw.lines(s, (130, 100, 70), False, [P(p) for p in pts], 6)
        pygame.draw.lines(s, (226, 206, 160) if known else (196, 176, 136), False, [P(p) for p in pts], 2)
    # places you can't drive to, for reference
    for key, label in (('fernwick', 'Fernwick'), ('farshore', 'Far Shore'), ('saltmarsh', 'Saltmarsh')):
        x, y = P(MAP_PTS[key])
        U.house(s, (x, y)) if key != 'farshore' else pygame.draw.circle(s, (80, 120, 70), (x, y), 8)
        ui.blit_text(s, label, (x, y + 14), 'tiny', U.INK, 'midtop', outline=(250, 246, 232))
    hx, hy = P(MAP_PTS['home'])
    pygame.draw.rect(s, (150, 90, 70), (hx - 8, hy - 6, 16, 12))
    pygame.draw.polygon(s, (110, 60, 50), [(hx - 10, hy - 6), (hx, hy - 14), (hx + 10, hy - 6)])
    ui.blit_text(s, 'Your cabin', (hx, hy + 10), 'tiny', U.INK, 'midtop', outline=(250, 246, 232))
    sel = getattr(g, 'truck_sel', 'reservoir')
    for area, name in AREA_NAMES.items():
        x, y = P(MAP_PTS[area])
        on = area == sel
        hov = math.hypot(ui.mouse[0] - x, ui.mouse[1] - y) < 22
        pygame.draw.circle(s, (60, 46, 40), (x, y + 2), 14)
        pygame.draw.circle(s, (250, 220, 120) if on else (252, 246, 230) if hov else (236, 226, 204), (x, y), 13)
        if st['visits'].get(area):
            U.star(s, (x, y), 7, (200, 150, 60))
        else:
            pygame.draw.circle(s, (170, 140, 110), (x, y), 4)
        ui.blit_text(s, name, (x, y - 18), 'smallb' if on else 'tiny', U.INK, 'midbottom', outline=(250, 246, 232))
        ui.hotspot(pygame.Rect(x - 22, y - 22, 44, 44), lambda a=area: setattr(g, 'truck_sel', a))
    # the card for the place you picked
    import areas
    a = areas.AREAS[sel]
    r = ROUTES[ROUTE_OF[sel]]
    c = pygame.Rect(rect.x + 650, rect.y + 90, 360, 470)
    ui.tile(s, c, (252, 246, 232), (196, 170, 130))
    ui.blit_text(s, a['name'], (c.x + 20, c.y + 16), 'h3', U.INK, maxw=c.w - 40)
    y = c.y + 58
    for ln in ui.wrap(a['desc'], 'small', c.w - 40)[:5]:
        ui.blit_text(s, ln, (c.x + 20, y), 'small', U.INK)
        y += 22
    y += 8
    ui.blit_text(s, '%s  -  %d minutes' % (r['name'], r['minutes']), (c.x + 20, y), 'smallb', U.SOFT)
    y += 26
    for ln in ui.wrap(r['desc'], 'tiny', c.w - 40)[:3]:
        ui.blit_text(s, ln, (c.x + 20, y), 'tiny', U.SOFT)
        y += 18
    y += 6
    from data import ROAD_FISH
    fish = [f for f in ROAD_FISH if f['spot'] == sel]
    got = sum(1 for f in fish if f['id'] in g.journal)
    ui.blit_text(s, 'Fish found here: %d of %d' % (got, len(fish)), (c.x + 20, y), 'tiny', U.SOFT)
    y += 20
    views = [v for v in VIEWS if v[0] == ROUTE_OF[sel]]
    ui.blit_text(s, 'Viewpoints photographed: %d of %d' % (sum(1 for v in views if v[1] in st['photos']), len(views)),
                 (c.x + 20, y), 'tiny', U.SOFT)
    y += 20
    o = st['order']
    if o and o['to'] == sel:
        from data import FISH_BY_ID
        have = len(order_fish(g, o))
        ui.blit_text(s, 'Order: %d %s (you have %d)' % (o['n'], FISH_BY_ID[o['fish']]['name'], have),
                     (c.x + 20, y), 'smallb', (90, 110, 160), maxw=c.w - 40)
    note = areas.note_for(g, sel)
    if note:
        ui.blit_text(s, note, (c.x + 20, c.bottom - 140), 'tiny', (170, 110, 60), maxw=c.w - 40)
    ok = can_leave(g, quiet=True)
    ui.button(s, (c.x + 20, c.bottom - 112, c.w - 40, 50), 'Drive there', lambda: depart(g, sel), 'primary', ok,
              font='bodyb', nav=True)
    known = r['id'] in st['driven']
    ui.button(s, (c.x + 20, c.bottom - 56, c.w - 40, 42),
              'Fast travel  (%d min)' % r['minutes'] if known else 'Drive it once to fast-travel',
              lambda: depart(g, sel, fast=True), 'normal', ok and known, font='smallb')
    if not ok and not at_home(g):
        ui.blit_text(s, 'Row home to the dock to set off.', (c.centerx, c.bottom - 124), 'tiny', (170, 90, 80),
                     'midbottom')


def _draw_orders(g, s, rect):
    ui = g.ui
    st = g.truck
    from data import FISH_BY_ID
    import art
    x0, y0 = rect.x + 40, rect.y + 96
    ui.blit_text(s, 'Neighbours up the roads would like fish from your lake. Take one order at a time, pack the '
                    'fish in the cooler and drive them over before 9 PM. Drive gently: bumps spill them.',
                 (x0, y0), 'small', U.SOFT, maxw=rect.w - 80)
    y = y0 + 64
    o = st['order']
    if o:
        box = pygame.Rect(x0, y, rect.w - 80, 150)
        ui.tile(s, box, (240, 246, 252), (130, 160, 200))
        f = FISH_BY_ID[o['fish']]
        spr = art.fish_sprite(f, 2)
        s.blit(spr, spr.get_rect(center=(box.x + 80, box.centery)))
        ui.blit_text(s, 'Your order: %d %s for %s' % (o['n'], f['name'], CLIENTS[o['to']]), (box.x + 160, box.y + 20),
                     'bodyb', U.INK, maxw=box.w - 200)
        have = len(order_fish(g, o))
        ui.blit_text(s, 'In your basket: %d of %d.   Pays %d coins.   Due by 9 PM today.' % (have, o['n'],
                     o['reward']), (box.x + 160, box.y + 58), 'small', U.SOFT)
        ui.blit_text(s, 'Drive (or fast-travel) to %s with them.' % AREA_NAMES[o['to']], (box.x + 160, box.y + 86),
                     'small', U.SOFT)
        ui.button(s, (box.right - 170, box.bottom - 56, 150, 42), 'Cancel it', lambda: drop_order(g), 'normal',
                  font='smallb')
        y = box.bottom + 24
    ui.blit_text(s, "Today's board", (x0, y), 'bodyb', U.INK)
    y += 34
    if not st['offers']:
        ui.blit_text(s, 'No more orders today. New ones go up every morning.', (x0, y), 'small', U.SOFT)
    for i, off in enumerate(st['offers']):
        f = FISH_BY_ID[off['fish']]
        row = pygame.Rect(x0, y, rect.w - 80, 92)
        ui.tile(s, row, (252, 246, 232), (196, 170, 130))
        spr = art.fish_sprite(f, 2)
        s.blit(spr, spr.get_rect(center=(row.x + 70, row.centery)))
        ui.blit_text(s, '%d %s for %s' % (off['n'], f['name'], CLIENTS[off['to']]), (row.x + 140, row.y + 16),
                     'smallb', U.INK, maxw=row.w - 340)
        ui.blit_text(s, '%s.  You have %d.  Pays %d coins.' % (AREA_NAMES[off['to']], len(order_fish(g, off)),
                     off['reward']), (row.x + 140, row.y + 48), 'small', U.SOFT, maxw=row.w - 340)
        ui.button(s, (row.right - 170, row.centery - 22, 150, 44), 'Take it', lambda i=i: take_order(g, i), 'gold',
                  st['order'] is None, font='smallb')
        y += 104


def _draw_garage(g, s, rect):
    ui = g.ui
    st = g.truck
    x0, y0 = rect.x + 40, rect.y + 96
    # the truck, big, in the shed
    pic = pygame.Rect(x0, y0, 400, 230)
    pygame.draw.rect(s, (90, 70, 56), pic.inflate(10, 10), border_radius=12)
    pygame.draw.rect(s, (150, 126, 100), pic, border_radius=8)
    for k in range(pic.x + 10, pic.right, 26):
        pygame.draw.line(s, (136, 112, 88), (k, pic.y + 4), (k, pic.bottom - 30))
    s.fill((120, 110, 100), (pic.x, pic.bottom - 30, pic.w, 30))
    spr = truck_sprite(paint_col(g) if st['fixed'] or st['parts'] else (150, 130, 120), rack=has(g, 'rack'),
                       boat=has(g, 'rack'), cooler=st['order'] is not None, cat=False)
    big = pygame.transform.scale(spr, (spr.get_width() * 6, spr.get_height() * 6))
    s.blit(big, big.get_rect(midbottom=(pic.centerx, pic.bottom - 4)))
    if not st['fixed']:
        dusty = big.copy()
        k = 70 - 20 * len(st['parts'])
        dusty.fill((k, k, k), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(dusty, big.get_rect(midbottom=(pic.centerx, pic.bottom - 4)))
    y = pic.bottom + 22
    if st['fixed']:
        for label, v in (('Trips', st['drives']), ('Distance', '%.1f km' % st['km']), ('Orders delivered',
                         st['delivered']), ('Viewpoints', '%d of %d' % (len(st['photos']), len(VIEWS))),
                         ('Lifts given', st['lifts']), ('Lost things found', '%d of %d' % (len(st['found']),
                                                                                          len(LOST)))):
            ui.blit_text(s, label, (x0, y), 'small', U.SOFT)
            ui.blit_text(s, str(v), (x0 + 400, y), 'smallb', U.INK, 'topright')
            y += 26
    else:
        for j, ln in enumerate(ui.wrap('Grandma Rosie drove it everywhere, from the hills to the sea. It just '
                                       'needs a little love.', 'small', 400)):
            ui.blit_text(s, ln, (x0, y + j * 24), 'small', U.SOFT)
    ux = rect.x + 480
    if not st['fixed']:
        ui.blit_text(s, 'Getting it going', (ux, y0), 'bodyb', U.INK)
        yy = y0 + 40
        for p in PARTS:
            got = p['id'] in st['parts']
            row = pygame.Rect(ux, yy, 520, 108)
            ui.tile(s, row, (236, 244, 226) if got else (252, 246, 232), (150, 180, 130) if got else (196, 170, 130))
            ui.blit_text(s, p['name'], (row.x + 18, row.y + 12), 'smallb', U.INK)
            ui.blit_text(s, 'Needs %s' % p['need'], (row.x + 18, row.y + 38), 'small', U.SOFT)
            for j, ln in enumerate(ui.wrap(p['say'], 'tiny', row.w - 180)[:2]):
                ui.blit_text(s, ln, (row.x + 18, row.y + 62 + j * 18), 'tiny', U.SOFT)
            if got:
                ui.blit_text(s, 'Done', (row.right - 60, row.centery), 'smallb', (90, 140, 80), 'center')
            else:
                ui.button(s, (row.right - 150, row.centery - 22, 132, 44), 'Fix it', lambda i=p['id']: fit_part(g, i),
                          'gold', part_ready(g, p), font='smallb')
            yy += 120
        return
    ui.blit_text(s, 'Upgrades', (ux, y0), 'bodyb', U.INK)
    yy = y0 + 36
    for u in UPGRADES:
        own = has(g, u['id'])
        row = pygame.Rect(ux, yy, 520, 84)
        ui.tile(s, row, (236, 244, 226) if own else (252, 246, 232), (150, 180, 130) if own else (196, 170, 130))
        ui.blit_text(s, u['name'], (row.x + 18, row.y + 10), 'smallb', U.INK)
        ui.blit_text(s, u['desc'], (row.x + 18, row.y + 36), 'tiny', U.SOFT, maxw=row.w - 200)
        if own:
            ui.blit_text(s, 'Fitted', (row.right - 80, row.centery), 'smallb', (90, 140, 80), 'center')
        elif u.get('boat') and not g.has_boat():
            ui.blit_text(s, 'Needs a rowboat', (row.right - 90, row.centery), 'tiny', U.SOFT, 'center')
        else:
            g.price_button(s, (row.right - 160, row.y + 18, 142, 46), u['cost'], lambda i=u['id']: buy(g, i))
        yy += 94
    ui.blit_text(s, 'Paint  (%d coins each, then free to switch)' % PAINT_COST, (ux, yy + 6), 'smallb', U.INK)
    yy += 38
    for i, (pid, name, col) in enumerate(PAINTS):
        r = pygame.Rect(ux + i * 86, yy, 76, 64)
        on = st['paint'] == pid
        ui.tile(s, r, (252, 246, 232), (200, 150, 70) if on else (196, 170, 130), on)
        pygame.draw.rect(s, col, (r.x + 14, r.y + 10, r.w - 28, 22), border_radius=6)
        ui.blit_text(s, name if pid in st['paints'] else '%d' % PAINT_COST, (r.centerx, r.bottom - 16), 'tiny',
                     U.INK if pid in st['paints'] else U.SOFT, 'center', maxw=r.w - 6)
        ui.hotspot(r, lambda p=pid: paint(g, p))


# ---------------------------------------------------------------- the bot
def bot_garage(g):
    st = g.truck
    for p in PARTS:
        fit_part(g, p['id'])
    if st['fixed']:
        for u in UPGRADES:
            if g.coins > u['cost'] + 600:
                buy(g, u['id'])


def bot_trip(g, rng):
    """Pick somewhere to go (the quarry at night), maybe take an order for it, and set off."""
    st = g.truck
    if not st['fixed'] or not can_leave(g, quiet=True):
        return False
    if st['offers_day'] != g.day:
        morning(g)
    night = g.minute >= 19 * 60 or g.minute < 4 * 60
    choices = ['quarry'] if night else [a for a in AREA_NAMES if a != 'quarry']
    for i, o in enumerate(st['offers']):
        if st['order'] is None and o['to'] in choices and len(order_fish(g, o)) >= o['n']:
            take_order(g, i)
            break
    o = st['order']
    area = o['to'] if o and o['to'] in choices else rng.choice(choices)
    fast = ROUTE_OF[area] in st['driven'] and rng.random() < 0.3
    return depart(g, area, fast=fast)
