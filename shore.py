"""Shoreline restoration at your home dock: the reed beds, the old landing and a wildlife hide.

Each project is a few small steps paid for with things you already gather: junk fished out of the lake, plant
food from the compost heap, coins, and photos for the Nature page. The lake changes a little with every step
(litter cleared, shoots growing day by day, brambles shrinking), and each finished project brings a new animal:
a reed warbler in the reeds, a muskrat from the landing, and a shy bittern you can only see from the hide.

g.shore = {'reeds': {'stage', 'day'}, 'landing': {'stage', 'cuts', 'day'}, 'hide': {'stage'}, 'told': bool}
"""
import math
import random

import pygame

import ui as U
from art import HORIZON, darken

JUNK = ('boot', 'can', 'driftwood')
GROW_DAYS = 3                 # reed shoots take three days to grow tall
CUT_DAYS = 3                  # the brambles take three days of clipping
HIDE_PHOTOS = 6               # animals on your Nature page before the hide is worth building

PROJECTS = [
    dict(id='reeds', name='Reed beds', where='The shallows past the dock', animal='warbler',
         desc='Litter has drifted into the shallows where the reeds used to grow. Clear it out, plant new '
              'shoots, and give them a few days.',
         done='Tall reeds rustle in the shallows, and a reed warbler sings from the tips.'),
    dict(id='landing', name='The old landing', where='The far shore', animal='muskrat',
         desc="Grandma Rosie's old landing is lost under brambles. Clip them back a little each day, then "
              "mend the planks.",
         done='The landing is clear again, with a lantern on its post. A muskrat swims over from it.'),
    dict(id='hide', name='Wildlife hide', where='In the reeds', animal='bittern',
         desc='A little wooden hut in the reeds, so shy animals stop minding you. It needs tall reeds around '
              'it, and some practice with the camera.',
         done='The hide sits snug in the reeds. Listen at dusk: something shy is booming in there.'),
]
BY_ID = {p['id']: p for p in PROJECTS}
LAST = {'reeds': 3, 'landing': 2, 'hide': 1}          # the stage each project is finished at

# where things are on the lake (world pixels, home dock only)
SHALLOWS = 296                # where the reed bed's roots are: clear of the toolbar along the bottom
REED_BED = pygame.Rect(430, SHALLOWS - 56, 134, 64)
LANDING = pygame.Rect(296, HORIZON - 10, 52, 16)
HIDE = pygame.Rect(568, SHALLOWS - 62, 40, 46)
LITTER = [('tyre', 472, 266), ('can', 506, 278), ('bottle', 446, 285), ('boot', 530, 270), ('plank', 548, 287),
          ('can', 488, 292)]
_rng = random.Random(7)
STALKS = [dict(x=430 + i * 2.6 + _rng.uniform(-1, 1), base=SHALLOWS - 8 + _rng.uniform(0, 15), h=_rng.uniform(16, 40),
               ph=_rng.uniform(0, 6), cat=_rng.random() < 0.35) for i in range(50)]
DEAD = [dict(x=436 + i * 11 + _rng.uniform(-3, 3), h=_rng.uniform(4, 9), lean=_rng.uniform(-3, 3)) for i in range(11)]
BRAMBLE = [(LANDING.x + 4 + i * 6 + _rng.uniform(-2, 2), LANDING.bottom - 3 - _rng.uniform(0, 3), _rng.uniform(4, 7))
           for i in range(8)]


def new():
    return {'reeds': {'stage': 0, 'day': 0}, 'landing': {'stage': 0, 'cuts': 0, 'day': 0}, 'hide': {'stage': 0},
            'told': False}


def clean(sh):
    base = new()
    if not isinstance(sh, dict):
        return base
    for pid, last in LAST.items():
        v = sh.get(pid)
        if isinstance(v, dict):
            for k in base[pid]:
                try:
                    base[pid][k] = max(0, int(v.get(k, base[pid][k])))
                except (TypeError, ValueError):
                    pass
            base[pid]['stage'] = min(last, base[pid]['stage'])
    base['landing']['cuts'] = min(CUT_DAYS, base['landing']['cuts'])
    base['told'] = bool(sh.get('told'))
    return base


# ---------------------------------------------------------------- what you see (your lake, or the host's)
def view(g):
    """The shore to draw: when visiting a friend, theirs (from the world message), else your own."""
    if getattr(g, 'solo', None) and isinstance(getattr(g, 'visit_shore', None), dict):
        return g.visit_shore
    return g.shore


def summary(g):
    """What a guest needs to draw your shore: stages and growth, nothing else."""
    sh = g.shore
    return {'reeds': [sh['reeds']['stage'], round(growth(g), 2)], 'landing': [sh['landing']['stage'],
                                                                              sh['landing']['cuts']],
            'hide': sh['hide']['stage']}


def from_summary(m):
    """A host's shore, for drawing while you visit. Anything odd and you just see an untouched shore."""
    out = new()
    try:
        out['reeds']['stage'] = max(0, min(3, int(m['reeds'][0])))
        out['reeds']['grow'] = max(0.0, min(1.0, float(m['reeds'][1])))
        out['landing']['stage'] = max(0, min(2, int(m['landing'][0])))
        out['landing']['cuts'] = max(0, min(CUT_DAYS, int(m['landing'][1])))
        out['hide']['stage'] = max(0, min(1, int(m['hide'])))
    except (KeyError, TypeError, ValueError, IndexError):
        return new()
    return out


def stage(g, pid, sh=None):
    return (sh or view(g))[pid]['stage']


def done(g, pid, sh=None):
    return stage(g, pid, sh) >= LAST[pid]


def unlocked(g, animal):
    """Has the project that brings this animal been finished (on the lake you are at)?"""
    for p in PROJECTS:
        if p['animal'] == animal:
            return done(g, p['id'])
    return True


def growth(g, sh=None):
    """How tall the new reeds are, 0..1 (1 once they are fully grown)."""
    sh = sh or g.shore
    r = sh['reeds']
    if r['stage'] >= 3:
        return 1.0
    if r['stage'] < 2:
        return 0.0
    if 'grow' in r:
        return r['grow']
    return max(0.0, min(1.0, (g.day - r['day'] + g.minute / 1440.0) / GROW_DAYS))


# ---------------------------------------------------------------- steps
def junk(g):
    return [b for b in g.basket if b['id'] in JUNK]


def next_step(g, pid):
    """(label, needs dict, why-not or None) for a project's next step, or None when there is nothing to do."""
    sh = g.shore
    st = sh[pid]['stage']
    if pid == 'reeds':
        if st == 0:
            return 'Clear the litter', {'junk': 4}, None
        if st == 1:
            return 'Plant reed shoots', {'food': 2, 'coins': 50}, None
        return None
    if pid == 'landing':
        if st == 0:
            if sh['landing']['day'] == g.day:
                return 'Clip the brambles', {}, "You've clipped enough for today. Come back tomorrow."
            return 'Clip the brambles', {}, None
        if st == 1:
            return 'Mend the planks', {'junk': 3, 'coins': 150}, None
        return None
    if st == 0:
        if not done(g, 'reeds', sh):
            return 'Build the hide', {'coins': 300}, 'Grow the reeds tall first.'
        if len(g.nature) < HIDE_PHOTOS:
            return 'Build the hide', {'coins': 300}, 'Photograph %d animals first (%d so far).' % (
                HIDE_PHOTOS, len(g.nature))
        return 'Build the hide', {'coins': 300}, None
    return None


def missing(g, needs):
    """What you're short of, as words, or '' when you have it all."""
    out = []
    if needs.get('junk', 0) > len(junk(g)):
        out.append('%d lake junk' % (needs['junk'] - len(junk(g))))
    if needs.get('food', 0) > g.garden['food']:
        out.append('%d plant food' % (needs['food'] - g.garden['food']))
    if needs.get('coins', 0) > g.coins:
        out.append('%d coins' % (needs['coins'] - g.coins))
    return ', '.join(out)


def cost_text(needs):
    parts = []
    if needs.get('junk'):
        parts.append('%d lake junk' % needs['junk'])
    if needs.get('food'):
        parts.append('%d plant food' % needs['food'])
    if needs.get('coins'):
        parts.append('%d coins' % needs['coins'])
    return ' + '.join(parts) if parts else 'Free: it just takes a little while'


def can_do(g, pid):
    ns = next_step(g, pid)
    return bool(ns) and ns[2] is None and not missing(g, ns[1]) and not getattr(g, 'solo', None)


def do_step(g, pid):
    """Pay for and do a project's next step. Returns True if something happened."""
    if getattr(g, 'solo', None):
        g.toast("This is your friend's lake. Your own shore waits at home.", (150, 140, 130))
        return False
    ns = next_step(g, pid)
    if not ns:
        return False
    label, needs, why = ns
    if why:
        g.toast(why, (150, 140, 130))
        return False
    short = missing(g, needs)
    if short:
        g.toast('You need %s more.' % short, (200, 120, 100))
        g.audio.play('nibble', 0.5)
        return False
    for b in junk(g)[:needs.get('junk', 0)]:
        g.basket.remove(b)
    g.garden['food'] -= needs.get('food', 0)
    g.coins -= needs.get('coins', 0)
    sh = g.shore
    p = sh[pid]
    w = g.world
    if pid == 'reeds':
        if p['stage'] == 0:
            p['stage'] = 1
            g.toast('You fish the litter out of the shallows. The water looks clearer already.', (90, 140, 120))
            w.ripple(495, SHALLOWS - 14, 10, 10, 160)
            w.sparkles(495, SHALLOWS - 18, 10, (220, 240, 255), 30)
        else:
            p['stage'], p['day'] = 2, g.day
            g.toast('You press reed shoots into the mud. Give them three days.', (90, 140, 90))
            w.splash(495, SHALLOWS - 4, 8, 0.4)
    elif pid == 'landing':
        if p['stage'] == 0:
            p['cuts'] += 1
            p['day'] = g.day
            g.advance_time(40)
            if p['cuts'] >= CUT_DAYS:
                p['stage'] = 1
                g.toast('The last of the brambles come away. There are old planks under there!', (110, 130, 80))
            else:
                g.toast('You spend a while clipping brambles on the far shore (%d of %d days).'
                        % (p['cuts'], CUT_DAYS), (110, 130, 80))
        else:
            p['stage'] = 2
            g.toast("The old landing is mended, and you hang a lantern on its post. Rosie would be pleased.",
                    (200, 150, 80))
            g.world.sparkles(LANDING.centerx, LANDING.y, 12, (255, 230, 160), 16)
            finished(g, 'landing')
    else:
        p['stage'] = 1
        g.toast('You build a little hide in the reeds. Sit quietly and see who comes.', (120, 110, 80))
        w.sparkles(HIDE.centerx, HIDE.y + 10, 12, (255, 240, 190), 18)
        finished(g, 'hide')
    g.stats['shore_steps'] = g.stats.get('shore_steps', 0) + 1
    g.audio.play('coin' if needs.get('coins') else 'page', 0.6)
    g.save()
    return True


def finished(g, pid):
    import wildlife
    sp = wildlife.SPECIES_BY_ID[BY_ID[pid]['animal']]
    g.stats['shore_done'] = sum(1 for q in PROJECTS if done(g, q['id'], g.shore))
    g.audio.play('jingle3', 0.6)
    g.toast('New visitor at the lake: watch for the %s!' % sp['name'], (110, 140, 120))
    g.check_badges()


def morning(g):
    """The reeds grow overnight, and Juniper writes once you've settled in."""
    r = g.shore['reeds']
    if r['stage'] == 2 and g.day - r['day'] >= GROW_DAYS:
        r['stage'] = 3
        g.toast('The new reeds are tall and green. Listen: a reed warbler is singing in them!', (90, 140, 90))
        finished(g, 'reeds')
    if not g.shore['told'] and g.day >= 2:
        g.shore['told'] = True
        g.queue.append(('letter', ('Dear neighbour,',
                                   "Your grandmother used to keep the shore by her dock lovely: reeds full of "
                                   "warblers, and a little landing on the far side. It's gone a bit wild since. "
                                   "If you'd like to bring it back, click the litter in the shallows past your "
                                   "dock. Junk you fish up, plant food from your compost and a few coins are all "
                                   "it takes. The animals will thank you.", '- Juniper, the aquarium')))


def hud_line(g):
    if g.place != 'lake' or getattr(g, 'solo', None) or not g.shore['told']:
        return None
    sh = g.shore
    if sh['reeds']['stage'] == 2:
        return 'New reeds growing: %d%%' % int(growth(g) * 100)
    if sh['landing']['stage'] == 0 and 0 < sh['landing']['cuts'] and sh['landing']['day'] != g.day:
        return 'The brambles at the old landing can be clipped again'
    if sh['reeds']['stage'] == 0 and len(junk(g)) >= 4:
        return 'Shore: enough junk to clear the litter (click it)'
    return None


# ---------------------------------------------------------------- the lake
def site_at(g, wx, wy):
    if g.spot != 'dock':
        return None
    if HIDE.collidepoint(wx, wy) and done(g, 'reeds'):
        return 'hide'
    if REED_BED.collidepoint(wx, wy):
        return 'reeds'
    if LANDING.inflate(10, 10).collidepoint(wx, wy):
        return 'landing'
    return None


def click(g, wx, wy):
    site = site_at(g, wx, wy)
    if not site or not g.shore['told'] or getattr(g, 'solo', None):
        return False
    if site == 'landing' and done(g, 'landing'):
        import farshore
        farshore.go(g)                     # the landing is mended: row across to the Far Shore
        return True
    open_panel(g, site)
    return True


def open_panel(g, site=None):
    g.shore_sel = site or getattr(g, 'shore_sel', 'reeds') or 'reeds'
    g.overlay = 'shore'
    g.audio.play('page', 0.6)


def _reed_col(season):
    return {0: (96, 150, 76), 1: (80, 136, 62), 2: (176, 150, 80), 3: (170, 160, 140)}.get(season, (96, 150, 76))


def draw_world(near, g, t):
    """The three sites as they are now, at the home dock."""
    sh = view(g)
    env = g.env
    wind = 1 + env.wind * 2
    # the old landing on the far shore
    L = LANDING
    st, cuts = sh['landing']['stage'], sh['landing'].get('cuts', 0)
    wood, dwood = (120, 92, 66), (84, 62, 46)
    if st >= 1:
        for i in range(0, L.w - 8, 4):
            broken = st == 1 and i in (12, 24, 36)
            if not broken:
                near.fill(wood if st == 2 else (104, 90, 76), (L.x + 4 + i, L.bottom - 6, 3, 2))
        near.fill(dwood, (L.x + 4, L.bottom - 4, L.w - 12, 1))
        for x in (L.x + 6, L.x + 22, L.right - 10):
            near.fill(dwood, (x, L.bottom - 5, 1, 5))
    else:
        for x in (L.x + 8, L.x + 26, L.right - 12):
            near.fill(dwood, (x, L.bottom - 7, 1, 7))
    keep = len(BRAMBLE) * (CUT_DAYS - cuts) // CUT_DAYS if st == 0 else 0
    for bx, by, r in BRAMBLE[:keep]:
        rr = int(r * (0.6 + 0.4 * (CUT_DAYS - cuts) / CUT_DAYS))
        pygame.draw.circle(near, (46, 70, 44), (int(bx), int(by)), rr)
        pygame.draw.circle(near, (60, 88, 52), (int(bx) - 1, int(by) - 1), max(1, rr - 2))
        near.set_at((int(bx) + 1, int(by) - rr + 1), (150, 60, 80))
    if st == 2:
        px = L.right - 10
        near.fill(dwood, (px, L.bottom - 14, 1, 9))
        near.fill(dwood, (px, L.bottom - 14, 3, 1))
        lit = env.nf > 0.3
        near.fill((255, 214, 140) if lit else (150, 130, 100), (px + 2, L.bottom - 13, 2, 3))
    # litter in the shallows
    if sh['reeds']['stage'] == 0:
        for kind, x, y in LITTER:
            bob = math.sin(t * 1.3 + x * 0.1) * 0.8
            y = int(y + bob)
            if kind == 'tyre':
                pygame.draw.ellipse(near, (34, 34, 38), (x - 7, y - 2, 14, 5))
                pygame.draw.ellipse(near, (70, 96, 110), (x - 3, y - 1, 6, 2))
            elif kind == 'can':
                near.fill((176, 70, 60), (x - 2, y - 2, 4, 3))
                near.fill((200, 200, 196), (x - 2, y - 2, 4, 1))
            elif kind == 'bottle':
                near.fill((90, 140, 100), (x - 3, y - 1, 6, 2))
                near.fill((90, 140, 100), (x + 3, y - 1, 2, 1))
            elif kind == 'boot':
                near.fill((80, 58, 40), (x - 3, y - 4, 3, 4))
                near.fill((80, 58, 40), (x - 3, y - 1, 6, 2))
            else:
                near.fill((130, 104, 76), (x - 6, y - 1, 12, 2))
            near.fill((200, 220, 230, 90), (x - 5, y + 2, 10, 1))
    # dead stalks before planting, then shoots, then a full reed bed
    rs = sh['reeds']['stage']
    if rs <= 1:
        for d in DEAD:
            x, b = int(d['x']), SHALLOWS
            pygame.draw.line(near, (120, 100, 70), (x, b), (x + d['lean'], b - d['h']))
    else:
        col = _reed_col(env.season)
        k = growth(g, sh)
        for s in STALKS:
            h = s['h'] * (0.15 + 0.85 * k)
            sway = math.sin(t * 1.2 + s['ph']) * wind * (0.4 + 0.6 * k)
            x0, b = s['x'], s['base']
            tip = (x0 + sway, b - h)
            pygame.draw.line(near, darken(col, 0.22), (x0, b), (x0 + sway * 0.5, b - h * 0.5))
            pygame.draw.line(near, col, (x0 + sway * 0.5, b - h * 0.5), tip)
            if s['cat'] and k >= 1 and env.season != 3:
                near.fill((110, 74, 50), (int(tip[0]) - 1, int(tip[1]) + 1, 2, 5))
            if env.season == 3:
                near.set_at((int(tip[0]), int(tip[1])), (240, 244, 250))
    # the hide, tucked in among the reeds (the foreground reeds are drawn over it)
    if sh['hide']['stage'] >= 1:
        hx, hy = HIDE.x + 4, HIDE.y + 8
        for x in (hx + 2, hx + 26):
            near.fill((70, 52, 38), (x, hy + 20, 2, 18))
        body = (124, 98, 64)
        near.fill(body, (hx, hy + 6, 30, 16))
        for y in range(hy + 8, hy + 22, 3):
            near.fill(darken(body, 0.15), (hx, y, 30, 1))
        near.fill((26, 22, 20), (hx + 6, hy + 11, 18, 3))
        pygame.draw.polygon(near, (96, 120, 70), [(hx - 3, hy + 7), (hx + 15, hy - 1), (hx + 33, hy + 7)])
        pygame.draw.line(near, (70, 90, 52), (hx - 3, hy + 7), (hx + 33, hy + 7))
        for i in range(5):
            near.fill((120, 150, 80), (hx + 2 + i * 6, hy + 3 - (i if i < 3 else 4 - i), 1, 3))
        if env.season == 3:
            pygame.draw.line(near, (240, 244, 250), (hx - 2, hy + 6), (hx + 15, hy - 2))


# ---------------------------------------------------------------- the Shore window
def draw_panel(g, s):
    ui = g.ui
    rect = g.big_panel(s, 'The Shore')
    sh = g.shore
    sel = getattr(g, 'shore_sel', 'reeds')
    x0 = rect.x + 34
    cw = (rect.w - 68 - 32) // 3
    for i, p in enumerate(PROJECTS):
        r = pygame.Rect(x0 + i * (cw + 16), rect.y + 90, cw, rect.h - 160)
        on = p['id'] == sel
        fin = done(g, p['id'], sh)
        ui.tile(s, r, (252, 248, 236) if on else (244, 236, 218), (150, 180, 130) if fin else
                U.GOLD if on else (186, 170, 150), on)
        ui.hotspot(r, lambda pid=p['id']: setattr(g, 'shore_sel', pid))
        _preview(g, s, pygame.Rect(r.x + 14, r.y + 14, r.w - 28, 120), p['id'])
        y = r.y + 146
        ui.blit_text(s, p['name'], (r.x + 16, y), 'h3', U.INK, maxw=r.w - 32)
        ui.blit_text(s, p['where'], (r.x + 16, y + 32), 'small', U.SOFT, maxw=r.w - 32)
        _dots(s, g, p['id'], (r.right - 18, y + 12))
        y += 62
        text = p['done'] if fin else p['desc']
        for ln in ui.wrap(text, 'small', r.w - 32)[:5]:
            ui.blit_text(s, ln, (r.x + 16, y), 'small', U.INK)
            y += 22
        by = r.bottom - 112
        if fin:
            import wildlife
            sp = wildlife.SPECIES_BY_ID[p['animal']]
            got = p['animal'] in g.nature
            ui.blit_text(s, 'Brings the %s' % sp['name'], (r.x + 16, by + 30), 'smallb', (90, 140, 90),
                         maxw=r.w - 32)
            ui.blit_text(s, 'On your Nature page!' if got else 'Not photographed yet', (r.x + 16, by + 56),
                         'small', U.SOFT, maxw=r.w - 32)
            continue
        if p['id'] == 'reeds' and sh['reeds']['stage'] == 2:
            ui.blit_text(s, 'Growing: %d%%' % int(growth(g) * 100), (r.x + 16, by + 20), 'bodyb', (90, 140, 90))
            bar = pygame.Rect(r.x + 16, by + 50, r.w - 32, 12)
            pygame.draw.rect(s, (226, 214, 196), bar, border_radius=6)
            pygame.draw.rect(s, (120, 170, 100), (bar.x, bar.y, int(bar.w * growth(g)), bar.h), border_radius=6)
            ui.blit_text(s, 'Tall in %d more day(s)' % max(1, GROW_DAYS - (g.day - sh['reeds']['day'])),
                         (r.x + 16, by + 70), 'small', U.SOFT)
            continue
        ns = next_step(g, p['id'])
        label, needs, why = ns
        by -= 24                      # leave room for a two-line hint above the button
        ui.blit_text(s, cost_text(needs), (r.x + 16, by), 'small', U.SOFT, maxw=r.w - 32)
        short = missing(g, needs)
        note = why or ('Short of %s' % short if short else '')
        if note:
            for j, ln in enumerate(ui.wrap(note, 'tiny', r.w - 32)[:2]):
                ui.blit_text(s, ln, (r.x + 16, by + 22 + j * 18), 'tiny', (176, 110, 80))
        ui.button(s, (r.x + 16, r.bottom - 62, r.w - 32, 46), label, lambda pid=p['id']: do_step(g, pid),
                  'primary', enabled=can_do(g, p['id']))
    have = 'Lake junk in your basket: %d      Plant food: %d      Animals photographed: %d' % (
        len(junk(g)), g.garden['food'], len(g.nature))
    ui.blit_text(s, have, (x0, rect.bottom - 44), 'smallb', U.SOFT)


def _dots(s, g, pid, right_mid):
    n = LAST[pid]
    st = g.shore[pid]['stage']
    x = right_mid[0] - (n - 1) * 14
    for i in range(n):
        col = (120, 170, 100) if i < st else (214, 204, 188)
        pygame.draw.circle(s, col, (x + i * 14, right_mid[1]), 5)


def _preview(g, s, r, pid):
    """A look at the site: cut straight out of the lake view when you're at your dock."""
    crop = {'reeds': pygame.Rect(402, SHALLOWS - 72, 190, 80), 'landing': pygame.Rect(250, HORIZON - 40, 142, 60),
            'hide': pygame.Rect(500, SHALLOWS - 74, 140, 59)}[pid]      # all about the card's shape
    at_home = g.place == 'lake' and g.spot == 'dock' and not getattr(g, 'solo', None)
    if at_home:
        k = min(r.w / crop.w, r.h / crop.h)
        img = pygame.transform.scale(g.frame.subsurface(crop), (int(crop.w * k), int(crop.h * k)))
        pygame.draw.rect(s, (120, 90, 60), r.inflate(6, 6), border_radius=6)
        pygame.draw.rect(s, (60, 70, 80), r)
        s.blit(img, img.get_rect(center=r.center))
    else:
        pygame.draw.rect(s, (226, 216, 196), r, border_radius=8)
        g.ui.blit_text(s, 'Row home to your dock to see it', r.center, 'small', U.SOFT, 'center')
