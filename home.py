"""Your cabin room: wallpaper, rugs, furniture you place yourself, mounted record fish and tank themes."""
import math

import pygame

import actors
import art
import ui as U
from data import FISH, FISH_BY_ID

RW, RH = 320, 170           # the room canvas, shown at x2
FLOOR = 122                 # where the wall meets the floor
WALL_SLOTS = [(48, 56), (102, 52), (218, 52), (272, 56)]      # centres
FLOOR_SLOTS = [40, 98, 222, 282]                              # x centres, standing on the floor line
FEET = 140
MOUNT_PRICE = 60
MOUNT_AT = 0.7              # a record: at least 70% of the way to the biggest size


def F(id, name, price, kind, desc):
    return dict(id=id, name=name, price=price, kind=kind, desc=desc)


CATALOGUE = [
    F('painting', 'Lake Painting', 120, 'wall', 'Lantern Lake at dawn, in thick oil paint.'),
    F('clock', 'Wall Clock', 90, 'wall', 'It keeps the same time as the lake.'),
    F('shelf', 'Little Shelf', 110, 'wall', 'Jars, a candle and a ship in a bottle.'),
    F('garland', 'Flower Garland', 70, 'wall', 'Dried flowers from every season.'),
    F('lakemap', 'Old Lake Map', 80, 'wall', 'Somebody marked the Deep with a tiny skull.'),
    F('armchair', 'Armchair', 180, 'floor', 'Squashy, patched, perfect.'),
    F('lamp', 'Floor Lamp', 120, 'floor', 'A warm pool of light on long evenings.'),
    F('fern', 'Potted Fern', 70, 'floor', 'Hard to kill. You have tried.'),
    F('stove', 'Wood Stove', 320, 'floor', 'Crackles all winter. Biscuit approves.'),
    F('bookcase', 'Bookcase', 220, 'floor', 'Fishing books, mostly. One mystery.'),
    F('rocker', 'Rocking Chair', 200, 'floor', 'Rocks a little on its own when it is windy.'),
    F('basket', 'Cat Basket', 120, 'floor', 'Biscuit naps here when she is home.'),
    F('yarn', 'Yarn Basket', 60, 'floor', 'A toy for Biscuit. Play with her once a day.'),
    F('scratcher', 'Scratching Post', 90, 'floor', 'A toy for Biscuit, and your chairs are saved.'),
    F('toybox', 'Feather Wand', 80, 'floor', 'A toy for Biscuit. She goes completely wild.'),
    dict(F('lens', 'Lighthouse Lens', 0, 'floor', "Rowan's old lens from Gull Point. It throws rainbows."),
         gift=True),
    F('rug_round', 'Braided Rug', 80, 'rug', 'Round and soft, in autumn colours.'),
    F('rug_stripe', 'Striped Rug', 100, 'rug', 'Blue and cream, like a lake cabin should be.'),
    F('rug_fish', 'Fish Rug', 140, 'rug', 'Shaped like a very flat trout.'),
    F('rug_star', 'Starry Rug', 160, 'rug', 'Navy wool with little gold stars.'),
    F('pine', 'Pine Planks', 0, 'paper', 'The cabin walls as you found them.'),
    F('cream', 'Cream Dots', 60, 'paper', 'Soft and sunny.'),
    F('sage', 'Sage Stripes', 70, 'paper', 'Calm green stripes.'),
    F('berry', 'Berry Diamonds', 80, 'paper', 'A bit fancy. Mabel would love it.'),
    F('sky', 'Cloud Paper', 90, 'paper', 'Little clouds all over.'),
    F('classic', 'Stone Cottage', 0, 'tank', 'The tank as it came, with a tiny stone house.'),
    F('coral', 'Coral Garden', 150, 'tank', 'Pink and orange coral, pale sand.'),
    F('moss', 'Mossy Log', 120, 'tank', 'Green water, a sunken log, plants everywhere.'),
    F('wreck', 'Sunken Rowboat', 180, 'tank', 'A little wrecked rowboat on the bottom.'),
    F('moon', 'Moonlit Tank', 220, 'tank', 'Deep blue water and plants that glow.'),
]
BY_ID = {c['id']: c for c in CATALOGUE}
KINDS = [('wall', 'Wall art'), ('floor', 'Furniture'), ('rug', 'Rugs'), ('paper', 'Wallpaper'), ('tank', 'Tank')]
FREE = ('pine', 'classic')
PAPERS = {'pine': ((150, 104, 70), (128, 86, 58)), 'cream': ((242, 228, 200), (226, 198, 160)),
          'sage': ((176, 196, 164), (156, 178, 146)), 'berry': ((196, 126, 136), (172, 100, 114)),
          'sky': ((166, 200, 222), (240, 244, 248))}


def new():
    return {'owned': [], 'wall': [None] * 4, 'floor': [None] * 4, 'rug': None, 'paper': 'pine', 'tank': 'classic'}


def clean(h):
    base = new()
    if not isinstance(h, dict):
        return base
    owned = [i for i in h.get('owned', []) if isinstance(i, str) and (i in BY_ID or mount_spec(i))]
    base['owned'] = list(dict.fromkeys(owned))
    for kind, n in (('wall', 4), ('floor', 4)):
        v = h.get(kind)
        if isinstance(v, list):
            v = (v + [None] * n)[:n]
            base[kind] = [i if i in base['owned'] and item_kind(i) == kind else None for i in v]
    if h.get('rug') in base['owned']:
        base['rug'] = h['rug']
    for k in ('paper', 'tank'):
        if h.get(k) in FREE or h.get(k) in base['owned'] and BY_ID.get(h.get(k), {}).get('kind') == k:
            base[k] = h[k]
    return base


def mount_spec(iid):
    if isinstance(iid, str) and iid.startswith('mount:'):
        return FISH_BY_ID.get(iid[6:])
    return None


def item_kind(iid):
    if mount_spec(iid):
        return 'wall'
    return BY_ID[iid]['kind'] if iid in BY_ID else None


def item_name(iid):
    sp = mount_spec(iid)
    if sp:
        return '%s Mount' % sp['name']
    return BY_ID[iid]['name']


def is_record(g, spec):
    e = g.journal.get(spec['id'])
    if not e or spec.get('junk'):
        return False
    lo, hi = spec['size']
    return e['best'] >= lo + (hi - lo) * MOUNT_AT


def mounts(g):
    """Fish mounts on offer: every record-size fish in your journal."""
    out = []
    for f in FISH:
        if is_record(g, f):
            e = g.journal[f['id']]
            out.append(dict(id='mount:' + f['id'], name='%s Mount' % f['name'], price=MOUNT_PRICE, kind='wall',
                            desc='Your record %s, %.1f cm, on a carved plaque.' % (f['name'], e['best'])))
    return out


def items(g, kind):
    its = [c for c in CATALOGUE if c['kind'] == kind and (not c.get('gift') or c['id'] in g.home['owned'])]
    if kind == 'wall':
        its += mounts(g)
    return its


def owns(g, iid):
    return iid in FREE or iid in g.home['owned']


def placed_where(g, iid):
    h = g.home
    for kind in ('wall', 'floor'):
        if iid in h[kind]:
            return kind, h[kind].index(iid)
    if h['rug'] == iid:
        return 'rug', 0
    return None


def choose(g, it):
    """Buy if needed, then put it in the selected spot (or wear it: wallpaper, rug, tank)."""
    h = g.home
    iid = it['id']
    if not owns(g, iid):
        if g.coins < it['price']:
            g.toast('Not enough coins yet.', (200, 120, 100))
            g.audio.play('nibble', 0.5)
            return False
        g.coins -= it['price']
        h['owned'].append(iid)
        g.stats['furniture'] = g.stats.get('furniture', 0) + 1
        g.audio.play('coin', 0.6)
    kind = it['kind']
    if kind in ('paper', 'tank'):
        h[kind] = iid
    elif kind == 'rug':
        h['rug'] = None if h['rug'] == iid else iid
    else:
        sk, si = g.home_sel if g.home_sel and g.home_sel[0] == kind else (kind, first_free(h, kind))
        was = placed_where(g, iid)
        if was:
            h[was[0]][was[1]] = None
        h[kind][si] = iid
        g.home_sel = (kind, si)
    g.audio.play('ui', 0.6)
    g.save()
    return True


def first_free(h, kind):
    for i, v in enumerate(h[kind]):
        if v is None:
            return i
    return 0


def take_down(g):
    sel = g.home_sel
    if sel and sel[0] in ('wall', 'floor'):
        g.home[sel[0]][sel[1]] = None
        g.audio.play('ui', 0.5)
        g.save()


# ---------------------------------------------------------------- drawing the room
class Room:
    def __init__(self):
        self.surf = pygame.Surface((RW, RH))
        self.glow = pygame.Surface((RW, RH))

    def render(self, g, t):
        s = self.surf
        h = g.home
        env = g.env
        nf = env.nf
        base, alt = PAPERS.get(h['paper'], PAPERS['pine'])
        _paper(s, h['paper'], base, alt)
        # window onto the lake
        _window(s, g, env, t)
        # beam and baseboard
        s.fill((96, 64, 44), (0, 0, RW, 7))
        s.fill((80, 52, 36), (0, 7, RW, 1))
        s.fill((104, 70, 48), (0, FLOOR - 4, RW, 5))
        s.fill((86, 58, 40), (0, FLOOR, RW, 1))
        # floor
        for y in range(FLOOR + 1, RH):
            k = (y - FLOOR) / (RH - FLOOR)
            s.fill(art.lerp_c((150, 102, 66), (180, 128, 84), k), (0, y, RW, 1))
        for i, y in enumerate(range(FLOOR + 6, RH, 9)):
            s.fill((140, 94, 60), (0, y, RW, 1))
            for x in range((i * 37) % 60, RW, 60):
                s.fill((140, 94, 60), (x, y - 8, 1, 8))
        if h['rug']:
            _rug(s, h['rug'])
        for i, iid in enumerate(h['wall']):
            if iid:
                _wall_item(s, g, iid, WALL_SLOTS[i], t)
        cat_spot = None
        for i, iid in enumerate(h['floor']):
            if iid:
                _floor_item(s, g, iid, FLOOR_SLOTS[i], t, env)
                if iid == 'basket':
                    cat_spot = ('basket', FLOOR_SLOTS[i])
                elif iid in ('yarn', 'scratcher', 'toybox') and cat_spot is None:
                    cat_spot = ('toy', FLOOR_SLOTS[i])
        _draw_home_cat(s, g, t, cat_spot)
        # evening light: dim the room and let lamps and the stove glow
        if nf > 0.05:
            dark = pygame.Surface((RW, RH), pygame.SRCALPHA)
            dark.fill((20, 20, 50, int(110 * nf)))
            s.blit(dark, (0, 0))
            gl = self.glow
            gl.fill((0, 0, 0))
            for i, iid in enumerate(h['floor']):
                x = FLOOR_SLOTS[i] if iid else None
                if iid == 'lamp':
                    _glow(gl, (x, FEET - 46), 56, (255, 210, 140), nf)
                elif iid == 'stove':
                    _glow(gl, (x, FEET - 10), 50 + math.sin(t * 9) * 2, (255, 160, 90), nf)
                elif iid == 'lens':
                    _glow(gl, (x, FEET - 30), 60, (220, 230, 255), nf)
            _glow(gl, (160, 48), 40, (200, 210, 255) if env.season is not None else (255, 255, 255), nf * 0.4)
            s.blit(gl, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return s

    def slot_at(self, lx, ly):
        for i, (cx, cy) in enumerate(WALL_SLOTS):
            if abs(lx - cx) <= 22 and abs(ly - cy) <= 22:
                return ('wall', i)
        for i, cx in enumerate(FLOOR_SLOTS):
            if abs(lx - cx) <= 24 and FEET - 64 <= ly <= FEET + 6:
                return ('floor', i)
        return None


def _glow(gl, c, r, col, k):
    """Soft light added in rings, brighter towards the middle."""
    f = 0.05 * k
    ring = tuple(int(v * f) for v in col)
    for i in range(6, 0, -1):
        rr = max(1, int(r * i / 6))
        tmp = pygame.Surface((rr * 2, rr * 2))
        tmp.fill((0, 0, 0))
        pygame.draw.circle(tmp, ring, (rr, rr), rr)
        gl.blit(tmp, (int(c[0]) - rr, int(c[1]) - rr), special_flags=pygame.BLEND_RGB_ADD)


def _paper(s, kind, base, alt):
    s.fill(base, (0, 0, RW, FLOOR))
    if kind == 'pine':
        for y in range(10, FLOOR, 9):
            s.fill(alt, (0, y, RW, 1))
        for y in range(10, FLOOR, 18):
            for x in range(20 + (y * 7) % 40, RW, 70):
                s.fill(alt, (x, y, 1, 9))
    elif kind == 'cream':
        for y in range(12, FLOOR - 4, 10):
            for x in range((y // 10 % 2) * 5 + 3, RW, 10):
                s.set_at((x, y), alt)
    elif kind == 'sage':
        for x in range(0, RW, 12):
            s.fill(alt, (x, 8, 5, FLOOR - 8))
    elif kind == 'berry':
        for y in range(14, FLOOR - 4, 14):
            for x in range((y // 14 % 2) * 8, RW, 16):
                pygame.draw.polygon(s, alt, [(x, y - 3), (x + 3, y), (x, y + 3), (x - 3, y)])
    elif kind == 'sky':
        for y in range(16, FLOOR - 6, 22):
            for x in range((y // 22 % 2) * 20 + 6, RW, 40):
                pygame.draw.ellipse(s, alt, (x, y, 12, 5))
                pygame.draw.ellipse(s, alt, (x + 4, y - 2, 7, 5))


def _window(s, g, env, t):
    r = pygame.Rect(136, 22, 48, 52)
    sky = art.lerp_c((168, 210, 236), (30, 36, 76), env.nf)
    if env.weather in ('rain', 'fog', 'snow') and env.nf < 0.6:
        sky = art.lerp_c(sky, (180, 184, 190), 0.5)
    s.fill(sky, r)
    if env.nf > 0.5:
        for i in range(6):
            s.set_at((r.x + 5 + i * 7, r.y + 5 + (i * 13) % 20), (240, 240, 210))
        pygame.draw.circle(s, (240, 236, 200), (r.right - 10, r.y + 10), 4)
    else:
        pygame.draw.circle(s, (255, 236, 170), (r.x + 12, r.y + 12), 5)
    hill = art.lerp_c((96, 140, 110), (30, 46, 50), env.nf)
    pygame.draw.polygon(s, hill, [(r.x, r.y + 34), (r.x + 18, r.y + 26), (r.x + 34, r.y + 32), (r.right, r.y + 28),
                                  (r.right, r.y + 38), (r.x, r.y + 38)])
    s.fill(art.lerp_c((110, 170, 200), (30, 50, 80), env.nf), (r.x, r.y + 38, r.w, r.h - 38))
    if env.season == 3:
        for i in range(10):
            x = r.x + (i * 11 + int(t * 8)) % r.w
            y = r.y + (i * 17 + int(t * 14)) % r.h
            s.set_at((x, y), (250, 250, 255))
    elif env.weather == 'rain':
        for i in range(10):
            x = r.x + (i * 11) % r.w
            y = r.y + (i * 17 + int(t * 60)) % r.h
            s.fill((200, 210, 230), (x, y, 1, 3))
    frame = (240, 232, 214)
    pygame.draw.rect(s, frame, r.inflate(4, 4), 2)
    s.fill(frame, (r.centerx - 1, r.y, 2, r.h))
    s.fill(frame, (r.x, r.y + 24, r.w, 2))
    s.fill((126, 90, 62), (r.x - 6, r.bottom + 2, r.w + 12, 3))
    for side in (-1, 1):                         # curtains
        cx = r.x - 6 if side < 0 else r.right + 1
        for i in range(5):
            s.fill((196, 92, 86) if i % 2 == 0 else (176, 76, 72), (cx + i, r.y - 4, 1, r.h + 6 - abs(i - 2)))
    s.fill((120, 90, 60), (r.x - 10, r.y - 6, r.w + 20, 2))


def _rug(s, iid):
    c = pygame.Rect(160 - 62, 146, 124, 20)
    if iid == 'rug_round':
        for i, col in enumerate(((176, 94, 60), (220, 160, 80), (150, 70, 52), (230, 196, 120))):
            pygame.draw.ellipse(s, col, c.inflate(-i * 18, -i * 4))
    elif iid == 'rug_stripe':
        r = pygame.Rect(160 - 58, 146, 116, 18)
        s.fill((240, 232, 214), r)
        for x in range(r.x, r.right, 10):
            s.fill((80, 120, 170), (x, r.y, 5, r.h))
        for x in range(r.x, r.right, 3):
            s.set_at((x, r.y - 1), (220, 210, 190))
            s.set_at((x, r.bottom), (220, 210, 190))
    elif iid == 'rug_fish':
        pygame.draw.ellipse(s, (120, 150, 170), (110, 146, 90, 20))
        pygame.draw.polygon(s, (120, 150, 170), [(196, 156), (214, 146), (214, 166)])
        for x in range(124, 190, 8):
            s.fill((160, 186, 200), (x, 150, 3, 12))
        s.fill((40, 50, 60), (118, 153, 3, 3))
    elif iid == 'rug_star':
        pygame.draw.ellipse(s, (44, 56, 96), c)
        pygame.draw.ellipse(s, (60, 76, 124), c, 2)
        for i in range(9):
            x = c.x + 14 + i * 12
            y = c.y + 6 + (i * 5) % 9
            s.set_at((x, y), (250, 220, 120))
            s.set_at((x + 1, y), (250, 220, 120))


def _wall_item(s, g, iid, pos, t):
    cx, cy = pos
    sp = mount_spec(iid)
    if sp:
        pygame.draw.ellipse(s, (110, 74, 48), (cx - 22, cy - 12, 44, 24))
        pygame.draw.ellipse(s, (146, 102, 66), (cx - 20, cy - 10, 40, 20))
        spr = art.fish_sprite(sp)
        k = min(36 / spr.get_width(), 16 / spr.get_height())
        spr = pygame.transform.scale(spr, (max(1, int(spr.get_width() * k)), max(1, int(spr.get_height() * k))))
        s.blit(spr, spr.get_rect(center=(cx, cy - 1)))
        s.fill((220, 186, 90), (cx - 5, cy + 9, 10, 3))
        return
    if iid == 'painting':
        r = pygame.Rect(cx - 18, cy - 13, 36, 26)
        s.fill((170, 130, 60), r.inflate(4, 4))
        s.fill((250, 200, 160), (r.x, r.y, r.w, 10))
        s.fill((240, 170, 140), (r.x, r.y + 6, r.w, 4))
        pygame.draw.circle(s, (255, 230, 170), (r.x + 26, r.y + 9), 4)
        s.fill((70, 110, 100), (r.x, r.y + 12, r.w, 4))
        s.fill((120, 170, 200), (r.x, r.y + 16, r.w, r.h - 16))
        s.fill((200, 220, 230), (r.x + 8, r.y + 19, 12, 1))
    elif iid == 'clock':
        pygame.draw.circle(s, (120, 80, 50), (cx, cy), 12)
        pygame.draw.circle(s, (246, 240, 226), (cx, cy), 10)
        m = g.minute
        for a, ln, col in (((m / 60) % 12 / 12, 5, (60, 40, 30)), ((m % 60) / 60, 8, (90, 60, 40))):
            ang = a * math.tau - math.pi / 2
            pygame.draw.line(s, col, (cx, cy), (cx + math.cos(ang) * ln, cy + math.sin(ang) * ln))
        for i in range(12):
            ang = i / 12 * math.tau
            s.set_at((int(cx + math.cos(ang) * 8), int(cy + math.sin(ang) * 8)), (150, 130, 110))
        sw = math.sin(t * 3) * 3
        pygame.draw.line(s, (200, 160, 70), (cx, cy + 12), (cx + sw, cy + 22))
        pygame.draw.circle(s, (220, 180, 80), (int(cx + sw), cy + 23), 2)
    elif iid == 'shelf':
        s.fill((120, 80, 52), (cx - 22, cy + 6, 44, 3))
        s.fill((96, 64, 42), (cx - 18, cy + 9, 2, 4))
        s.fill((96, 64, 42), (cx + 16, cy + 9, 2, 4))
        s.fill((170, 210, 200), (cx - 18, cy - 4, 7, 10))
        s.fill((230, 160, 80), (cx - 17, cy - 1, 5, 7))
        s.fill((240, 236, 220), (cx - 6, cy - 2, 4, 8))
        if g.env.nf > 0.3 or int(t * 4) % 7:
            s.fill((255, 210, 110), (cx - 5, cy - 5, 2, 3))
        pygame.draw.ellipse(s, (190, 220, 230), (cx + 2, cy - 2, 16, 8))
        s.fill((240, 240, 240), (cx + 8, cy - 6, 1, 6))
        s.fill((150, 100, 70), (cx + 6, cy + 2, 6, 2))
    elif iid == 'garland':
        cols = [(230, 150, 170), (240, 200, 90), (220, 120, 70), (160, 190, 220), (190, 140, 200)]
        pts = [(cx - 24 + i * 4, cy - 6 + int(math.sin(i / 12 * math.pi) * 8)) for i in range(13)]
        pygame.draw.lines(s, (120, 140, 90), False, pts)
        for i, p in enumerate(pts[1:-1:2]):
            pygame.draw.circle(s, cols[i % 5], (p[0], p[1] + 2), 2)
    elif iid == 'lakemap':
        r = pygame.Rect(cx - 17, cy - 13, 34, 26)
        s.fill((232, 214, 170), r)
        pygame.draw.rect(s, (190, 160, 120), r, 1)
        pygame.draw.ellipse(s, (140, 180, 196), (r.x + 4, r.y + 5, 26, 15))
        s.set_at((r.x + 20, r.y + 12), (60, 40, 40))
        s.fill((200, 70, 60), (r.x + 9, r.y + 9, 2, 2))
        pygame.draw.line(s, (120, 150, 110), (r.x + 26, r.y + 4), (r.right - 2, r.y + 2))


def _floor_item(s, g, iid, x, t, env):
    y = FEET
    if iid == 'armchair':
        s.fill((150, 70, 64), (x - 14, y - 24, 28, 20))
        s.fill((176, 90, 80), (x - 11, y - 14, 22, 8))
        s.fill((130, 60, 56), (x - 17, y - 16, 6, 14))
        s.fill((130, 60, 56), (x + 11, y - 16, 6, 14))
        s.fill((90, 60, 40), (x - 14, y - 2, 2, 3))
        s.fill((90, 60, 40), (x + 12, y - 2, 2, 3))
        s.fill((236, 220, 180), (x - 6, y - 21, 12, 6))
    elif iid == 'lamp':
        s.fill((80, 70, 60), (x - 5, y - 2, 10, 2))
        s.fill((90, 80, 70), (x, y - 40, 1, 38))
        on = env.nf > 0.3
        pygame.draw.polygon(s, (250, 220, 160) if on else (226, 200, 160),
                            [(x - 8, y - 40), (x + 9, y - 40), (x + 6, y - 52), (x - 5, y - 52)])
    elif iid == 'fern':
        pygame.draw.polygon(s, (180, 100, 70), [(x - 6, y - 10), (x + 6, y - 10), (x + 4, y), (x - 4, y)])
        for i in range(7):
            a = -math.pi / 2 + (i - 3) * 0.38 + math.sin(t * 1.2 + i) * 0.04
            ln = 14 - abs(i - 3) * 2
            pygame.draw.line(s, (70, 130, 70), (x, y - 10), (x + math.cos(a) * ln, y - 10 + math.sin(a) * ln), 2)
    elif iid == 'stove':
        s.fill((56, 56, 60), (x - 12, y - 22, 24, 22))
        s.fill((70, 70, 76), (x - 13, y - 24, 26, 3))
        s.fill((60, 60, 66), (x - 3, y - 64, 6, 40))
        fire = (255, 150 + int(math.sin(t * 11) * 40), 60)
        s.fill((30, 20, 20), (x - 7, y - 16, 14, 10))
        s.fill(fire, (x - 5, y - 12 - int(abs(math.sin(t * 7)) * 2), 10, 6))
        s.fill((255, 230, 140), (x - 2, y - 10, 4, 3))
        s.fill((40, 40, 44), (x - 11, y, 3, 1))
        s.fill((40, 40, 44), (x + 8, y, 3, 1))
    elif iid == 'bookcase':
        s.fill((110, 74, 48), (x - 16, y - 50, 32, 50))
        cols = [(170, 70, 60), (70, 110, 150), (200, 170, 90), (80, 130, 90), (140, 90, 140)]
        for row in range(3):
            yy = y - 46 + row * 15
            s.fill((86, 58, 38), (x - 14, yy + 12, 28, 2))
            for i in range(6):
                hgt = 9 + (i * 3 + row) % 3
                s.fill(cols[(i + row * 2) % 5], (x - 13 + i * 4 + (1 if i > 3 else 0), yy + 12 - hgt, 3, hgt))
    elif iid == 'rocker':
        k = math.sin(t * 1.4) * (1.5 + getattr(env, 'wind', 0) * 2)
        pygame.draw.arc(s, (120, 80, 50), (x - 16, y - 8, 32, 10), math.pi + 0.3, 2 * math.pi - 0.3, 2)
        s.fill((140, 94, 58), (x - 10, y - 12, 20, 3))
        s.fill((140, 94, 58), (x - 10 + int(k), y - 34, 3, 24))
        for i in range(3):
            s.fill((150, 104, 66), (x - 8 + int(k), y - 32 + i * 7, 2, 18 - i * 7))
        s.fill((140, 94, 58), (x + 8, y - 20, 2, 10))
    elif iid == 'basket':
        pygame.draw.ellipse(s, (180, 130, 70), (x - 14, y - 9, 28, 10))
        pygame.draw.ellipse(s, (150, 104, 56), (x - 14, y - 9, 28, 10), 1)
        pygame.draw.ellipse(s, (230, 150, 150), (x - 11, y - 9, 22, 5))
        for i in range(-10, 11, 4):
            s.fill((150, 104, 56), (x + i, y - 5, 1, 4))
    elif iid == 'yarn':
        pygame.draw.polygon(s, (170, 120, 70), [(x - 9, y - 8), (x + 9, y - 8), (x + 7, y), (x - 7, y)])
        for i, col in enumerate(((220, 90, 100), (90, 140, 200), (240, 200, 90))):
            pygame.draw.circle(s, col, (x - 5 + i * 5, y - 10), 3)
        pygame.draw.line(s, (220, 90, 100), (x - 5, y - 8), (x - 14, y + 1))
    elif iid == 'scratcher':
        s.fill((170, 130, 90), (x - 9, y - 3, 18, 3))
        s.fill((200, 170, 120), (x - 3, y - 30, 6, 27))
        for yy in range(y - 28, y - 3, 3):
            s.fill((176, 146, 100), (x - 3, yy, 6, 1))
        s.fill((170, 130, 90), (x - 6, y - 33, 12, 3))
        pygame.draw.line(s, (120, 100, 90), (x + 5, y - 32), (x + 9, y - 22))
        pygame.draw.circle(s, (230, 90, 110), (x + 9, y - 21), 2)
    elif iid == 'lens':
        s.fill((120, 86, 46), (x - 9, y - 4, 18, 4))
        s.fill((150, 110, 60), (x - 2, y - 16, 4, 12))
        pygame.draw.circle(s, (180, 140, 70), (x, y - 30), 15)
        for i in range(5, 0, -1):
            k = (math.sin(t * 2 + i) + 1) / 2
            pygame.draw.circle(s, (int(200 + 40 * k), int(220 + 30 * k), 240), (x, y - 30), i * 3)
            pygame.draw.circle(s, (160, 190, 210), (x, y - 30), i * 3, 1)
        s.set_at((x, y - 30), (255, 255, 230))
        if env.nf > 0.3:
            for j in range(3):
                a = t * 0.6 + j * 2.1
                ex, ey = x + math.cos(a) * 26, y - 30 + math.sin(a) * 10 - 10
                s.fill((250, 180, 200), (int(ex), int(ey), 2, 1))
                s.fill((180, 230, 200), (int(ex) + 2, int(ey), 2, 1))
    elif iid == 'toybox':
        s.fill((150, 110, 160), (x - 8, y - 8, 16, 8))
        s.fill((130, 90, 140), (x - 8, y - 8, 16, 1))
        a = math.sin(t * 2.5) * 0.3
        tip = (x + 4 + math.sin(a) * 18, y - 8 - math.cos(a) * 18)
        pygame.draw.line(s, (180, 150, 110), (x + 3, y - 8), tip)
        for i, col in enumerate(((90, 170, 200), (240, 180, 80), (220, 90, 120))):
            s.fill(col, (int(tip[0]) - 1 + i, int(tip[1]) - 2 + i, 2, 3))


def _draw_home_cat(s, g, t, spot):
    """Biscuit at home: asleep in her basket, batting at a toy, or curled up on the rug."""
    import biscuit
    if g.place == 'town' and biscuit.follows(g):
        return                                # she's out walking with you
    night = g.env.nf > 0.6
    playing = g.cat['excited'] > 0 or g.cat.get('trick')
    if spot and spot[0] == 'basket':
        actors.draw_cat(s, g, t, spot[1], FEET - 3, bed=False, sleep=not playing, look=0)
    elif spot and spot[0] == 'toy':
        x = spot[1] + (16 if spot[1] < 200 else -16)
        actors.draw_cat(s, g, t, x, FEET + 4, bed=False, sleep=night and not playing,
                        face=1 if x < spot[1] else -1, look=0)
    else:
        actors.draw_cat(s, g, t, 160, FEET + 12, bed=False, sleep=night and not playing, look=0)


# ---------------------------------------------------------------- the Home tab
def draw_tab(g, s, rect):
    ui = g.ui
    t = g.t
    room = g.room
    rx, ry = rect.x + 30, rect.y + 88
    surf = room.render(g, t)
    pygame.draw.rect(s, (120, 80, 54), (rx - 8, ry - 8, RW * 2 + 16, RH * 2 + 16), border_radius=10)
    s.blit(pygame.transform.scale(surf, (RW * 2, RH * 2)), (rx, ry))
    sel = g.home_sel
    # slot outlines: dashed for empty, gold for the selected one
    for kind, slots in (('wall', WALL_SLOTS), ('floor', FLOOR_SLOTS)):
        for i in range(4):
            if kind == 'wall':
                cx, cy = slots[i]
                r = pygame.Rect(rx + (cx - 22) * 2, ry + (cy - 22) * 2, 88, 88)
            else:
                cx = slots[i]
                r = pygame.Rect(rx + (cx - 24) * 2, ry + (FEET - 64) * 2, 96, 140)
            on = sel == (kind, i)
            empty = g.home[kind][i] is None
            hov = r.collidepoint(ui.mouse)
            if on or hov or empty:
                col = U.GOLD if on else (250, 244, 230) if hov else (230, 214, 190)
                _dashed(s, r, col, 3 if on else 2)
            ui.hotspot(r, lambda k=kind, i=i: _select(g, (k, i)))
    # under the room: what's selected
    iy = ry + RH * 2 + 18
    if sel and sel[0] in ('wall', 'floor'):
        iid = g.home[sel[0]][sel[1]]
        where = '%s spot %d' % ('Wall' if sel[0] == 'wall' else 'Floor', sel[1] + 1)
        ui.blit_text(s, item_name(iid) if iid else where + ': empty', (rx, iy), 'h3', U.INK)
        ui.blit_text(s, where + ('.  Pick something on the right to put here.' if not iid else
                                 '.  Pick something else to swap it.'), (rx, iy + 30), 'small', U.SOFT)
        if iid:
            ui.button(s, (rx + RW * 2 - 170, iy, 170, 44), 'Take down', lambda: take_down(g), 'rose')
    else:
        ui.blit_text(s, 'Click a spot in the room, then pick something for it.', (rx, iy + 6), 'body', U.SOFT)
    # the catalogue
    cx0 = rx + RW * 2 + 26
    cw = rect.right - 30 - cx0
    tab = g.home_tab
    for i, (k, label) in enumerate(KINDS):         # two rows: three tabs, then two
        n, row = (3, 0) if i < 3 else (2, 1)
        w = (cw + 4) // n
        ui.button(s, (cx0 + (i if i < 3 else i - 3) * w, ry - 6 + row * 38, w - 4, 34), label,
                  lambda k=k: _set_tab(g, k), 'tab_on' if tab == k else 'tab', font='smallb')
    ry += 36
    its = items(g, tab)
    per = 9
    pages = max(1, (len(its) + per - 1) // per)
    g.home_page = min(g.home_page, pages - 1)
    tw, th = (cw - 12) // 3, 98
    hover = None
    for n, it in enumerate(its[g.home_page * per:(g.home_page + 1) * per]):
        r = pygame.Rect(cx0 + (n % 3) * (tw + 6), ry + 40 + (n // 3) * (th + 6), tw, th)
        have = owns(g, it['id'])
        using = (placed_where(g, it['id']) is not None or g.home.get(tab) == it['id'] and tab in ('paper', 'tank'))
        hov = r.collidepoint(ui.mouse)
        if hov:
            hover = it
        ui.tile(s, r, (252, 248, 236) if hov else (240, 230, 210), U.GOLD if using else (186, 170, 150), using)
        ic = icon(g, it['id'])
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 36)))
        nm = it['name'] if ui.fonts['small'].size(it['name'])[0] < tw - 8 else it['name'].split(' ')[-1]
        ui.blit_text(s, nm, (r.centerx, r.bottom - 38), 'small', U.INK, 'midtop')
        ui.blit_text(s, 'In use' if using else 'Owned' if have else '%d coins' % it['price'],
                     (r.centerx, r.bottom - 18), 'small', (90, 140, 90) if using or have else U.SOFT, 'midtop')
        ui.hotspot(r, lambda it=it: choose(g, it))
    if pages > 1:
        py = ry + 40 + 3 * (th + 6)
        ui.button(s, (cx0, py, 44, 32), '<', lambda: setattr(g, 'home_page', max(0, g.home_page - 1)), 'normal',
                  enabled=g.home_page > 0, font='smallb')
        ui.blit_text(s, '%d / %d' % (g.home_page + 1, pages), (cx0 + cw // 2, py + 8), 'smallb', U.SOFT, 'midtop')
        ui.button(s, (cx0 + cw - 44, py, 44, 32), '>', lambda: setattr(g, 'home_page', g.home_page + 1),
                  'normal', enabled=g.home_page < pages - 1, font='smallb')
    dy = ry + 40 + 3 * (th + 6) + 44
    if hover:
        ui.blit_text(s, hover['name'], (cx0, dy), 'bodyb', U.INK)
        for j, line in enumerate(ui.wrap(hover['desc'], 'small', cw)[:3]):
            ui.blit_text(s, line, (cx0, dy + 26 + j * 20), 'small', U.SOFT)
    elif tab == 'wall' and not mounts(g):
        for j, line in enumerate(ui.wrap('Catch a record-size fish (near its biggest) and you can mount it here.',
                                         'small', cw)):
            ui.blit_text(s, line, (cx0, dy + j * 20), 'small', U.SOFT)
    elif tab == 'tank':
        ui.blit_text(s, 'Changes the look of your fish tank.', (cx0, dy), 'small', U.SOFT)


def _dashed(s, r, col, w):
    for x in range(r.x, r.right, 12):
        s.fill(col, (x, r.y, 6, w))
        s.fill(col, (x, r.bottom - w, 6, w))
    for y in range(r.y, r.bottom, 12):
        s.fill(col, (r.x, y, w, 6))
        s.fill(col, (r.right - w, y, w, 6))


def _select(g, sel):
    g.home_sel = sel
    if g.home_tab not in (sel[0],):
        g.home_tab = sel[0]
        g.home_page = 0
    g.audio.play('ui', 0.4)


def _set_tab(g, k):
    g.home_tab = k
    g.home_page = 0
    if k in ('wall', 'floor') and (not g.home_sel or g.home_sel[0] != k):
        g.home_sel = (k, first_free(g.home, k))


_icons = {}


def icon(g, iid):
    """A 64x64 preview of a catalogue item, drawn by the room code itself."""
    sp = mount_spec(iid)
    key = iid
    if key in _icons:
        return _icons[key]
    tmp = pygame.Surface((48, 40), pygame.SRCALPHA)
    kind = item_kind(iid)
    if sp or kind == 'wall':
        _wall_item(tmp, _IconGame, iid, (24, 20), 0.0)
    elif kind == 'floor':
        tmp2 = pygame.Surface((48, 70), pygame.SRCALPHA)
        _floor_item_at(tmp2, iid, 24, 66, _IconGame.env)
        tmp = pygame.transform.scale(tmp2, (34, 50))
        out = pygame.Surface((48, 40), pygame.SRCALPHA)
        out.blit(tmp, tmp.get_rect(midbottom=(24, 40)))
        tmp = out
    elif kind == 'rug':
        big = pygame.Surface((RW, RH), pygame.SRCALPHA)
        _rug(big, iid)
        crop = big.subsurface((92, 140, 130, 30)).copy()
        tmp.blit(pygame.transform.scale(crop, (48, 12)), (0, 16))
    elif kind == 'paper':
        sw = pygame.Surface((60, 50))
        base, alt = PAPERS[iid]
        sw.fill(base)
        _paper_swatch(sw, iid, base, alt)
        tmp.blit(pygame.transform.scale(sw, (36, 30)), (6, 5))
        pygame.draw.rect(tmp, (120, 90, 60), (6, 5, 36, 30), 1)
    elif kind == 'tank':
        img = _tank_preview().render(None, iid)
        tmp.blit(pygame.transform.scale(img, (44, 18)), (2, 11))
        pygame.draw.rect(tmp, (120, 90, 60), (1, 10, 46, 20), 1)
    out = pygame.transform.scale(tmp, (72, 60))
    _icons[key] = out
    return out


class _IconGame:
    """Stands in for the game when drawing catalogue icons: daytime, no wind."""
    minute = 600
    env = type('E', (), {'nf': 0.0, 'wind': 0.0, 'season': 0, 'weather': 'clear'})


def _floor_item_at(s, iid, x, feet, env):
    global FEET
    old = FEET
    FEET = feet
    try:
        _floor_item(s, _IconGame, iid, x, 0.0, env)
    finally:
        FEET = old


def _paper_swatch(sw, iid, base, alt):
    tmp = pygame.Surface((RW, FLOOR))
    _paper(tmp, iid, base, alt)
    sw.blit(tmp.subsurface((20, 16, 60, 50)), (0, 0))


_tank_tv = None


def _tank_preview():
    global _tank_tv
    if _tank_tv is None:
        import tank as tk
        _tank_tv = tk.Tank()
    return _tank_tv
