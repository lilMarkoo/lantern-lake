"""Goals: the welcome quest for a brand new game, and the goal tracker.

The welcome quest ('Settling in') gives a new game a quick payoff: catch two fish and Grandma's radishes are
ready to pick, pick them and a yarn basket arrives for Biscuit, play with Biscuit and she finds the old tool
box, and with it you mend the loose plank on the dock.

The tracker lists every goal you have going (Q opens it). Pin one and the HUD card follows it, with its next
step, where to go and when.
"""
import math

import pygame

import ui as U
import almanac
import biscuit
import coast
import legends
import story
import garden as gardenmod
import shore as shoremod
from data import FISH_BY_ID, SPOT_BY_ID, SEASONS, spots_of

STEPS = [
    dict(id='fish', title='Catch two fish', where='Cast from your dock', icon='spot'),
    dict(id='pick', title="Pick Grandma's radishes", where='Click the garden by the cabin', icon='garden'),
    dict(id='play', title='Play with Biscuit', where='Cabin (C), then the Biscuit tab', icon='birthday'),
    dict(id='plank', title='Mend the loose dock plank', where='Click the plank sticking up', icon='town'),
]
DONE = len(STEPS)
PLANK = pygame.Rect(166, 286, 7, 5)          # the loose plank (world pixels, on the deck)
PLANK_CLICK = pygame.Rect(158, 274, 24, 18)
PLANK_COINS = 50


def fmt_clock(m):                             # main swaps in its own (12 or 24 hour)
    m = int(m) % 1440
    return '%d:%02d' % (m // 60, m % 60)


def new():
    return {'step': 0, 'fish': 0, 'bed': -1, 'pinned': None, 't': 0.0}


def clean(st, fresh=False):
    """fresh=False: an older save without goals has long since settled in."""
    base = new()
    if not isinstance(st, dict):
        if not fresh:
            base['step'] = DONE
        return base
    for k, v in base.items():
        if k == 'pinned':
            continue
        if not isinstance(st.get(k), type(v)):
            st[k] = v
    st['step'] = max(0, min(DONE, int(st['step'])))
    if not isinstance(st.get('pinned'), str):
        st['pinned'] = None
    return st


def active(g):
    return g.goals['step'] < DONE and not getattr(g, 'solo', None)


# ---------------------------------------------------------------- the welcome quest
def _advance(g):
    st = g.goals
    st['step'] += 1
    st['t'] = 0.0
    g.audio.play('jingle2', 0.55)
    if st['step'] >= DONE:
        g.toast("Settled in! Press Q any time to choose what to do next.", (110, 150, 100))
    g.save()


def on_catch(g, spec):
    st = g.goals
    if st['step'] != 0 or spec.get('junk') or not active(g):
        return
    st['fish'] += 1
    if st['fish'] < 2:
        return
    # Grandma planted radishes before you came: they are ready right now
    gd = g.garden
    beds = gd['beds']
    i = next((j for j in range(gd['open']) if beds[j] is None), -1)
    if i >= 0:
        days = gardenmod.CROP_BY_ID['radish']['days']
        beds[i] = {'crop': 'radish', 'age': days, 'wet': 0, 'fed': False}
        st['bed'] = i
        if g.place == 'lake' and g.spot == 'dock':
            x, y, w = gardenmod.BED_SPOTS[i]
            g.world.sparkles(x + w // 2, y - 4, 14, (250, 236, 150), 10)
    else:
        gd['produce']['radish'] = gd['produce'].get('radish', 0) + 2
    g.toast("Grandma's radishes have popped up in the garden! Go and pick them.", (110, 150, 80))
    _advance(g)


def update(g, dt):
    st = g.goals
    if not active(g) or g.mode != 'play':
        return
    st['t'] += dt
    step = st['step']
    if step == 1:
        i = st['bed']
        b = g.garden['beds'][i] if 0 <= i < len(g.garden['beds']) else None
        if i < 0 or not (b and b['crop'] == 'radish' and gardenmod.ready(b)):
            _give_yarn(g)
            _advance(g)
    elif step == 2 and biscuit.done_today(g, 'play'):
        g.toast('Biscuit chases the yarn under the dock... and comes back with Grandma\'s old tool box!',
                (200, 130, 80))
        _advance(g)


def _give_yarn(g):
    h = g.home
    if 'yarn' not in h['owned']:
        h['owned'].append('yarn')
    if 'yarn' not in h['floor'] and None in h['floor']:
        h['floor'][h['floor'].index(None)] = 'yarn'
    g.toast('A parcel on the step: a yarn basket for Biscuit! Play with her from the Cabin.', (200, 130, 80))


def mend_plank(g):
    st = g.goals
    if st['step'] != 3:
        return False
    if g.place != 'lake' or g.spot != 'dock':
        g.toast('The loose plank is on your home dock.', (150, 140, 130))
        return False
    g.coins += PLANK_COINS
    g.world.sparkles(PLANK.centerx, PLANK.y - 2, 16, (255, 236, 170), 10)
    g.audio.play('creak', 0.6)
    g.audio.play('click', 0.5)
    g.toast('Tap, tap: the dock is whole again. Grandma left %d coins in the tool box, too!' % PLANK_COINS,
            (180, 140, 90))
    _advance(g)
    return True


def welcome_line(g):
    st = g.goals
    step = st['step']
    return STEPS[step]['title'], (st['fish'], 2) if step == 0 else None


def welcome_act(g):
    step = g.goals['step']
    if step == 1:
        return lambda: g.open_cabin_tab('garden')
    if step == 2:
        return lambda: g.open_cabin_tab('biscuit')
    if step == 3:
        return lambda: mend_plank(g)
    return None


# ---------------------------------------------------------------- where and when a fish bites
_WHERE = {}
_TIDES = {}
SHORT ={'dock': 'Your dock', 'pier': 'Saltmarsh Pier'}


def fish_where(g, f):
    """(where, when): the spots it swims at, and the hours, seasons, weather and tide it wants."""
    fid = f['id']
    if fid not in _WHERE:
        sp = spots_of(fid)
        if f.get('spot') == 'pot':
            where = 'In the crab pot'
        elif f.get('spot') == 'ice':
            where = 'Through the ice'
        elif not sp:
            where = 'Somewhere special'
        elif len(sp) >= 4:
            where = 'Anywhere on the lake'
        else:
            where = ', '.join(SHORT.get(s, SPOT_BY_ID[s]['name']) for s in sp)
        _WHERE[fid] = where
    bits = []
    if f.get('phases'):
        bits.append(' & '.join(p for p in ('dawn', 'day', 'dusk', 'night') if p in f['phases']))
    if f.get('seasons') is not None and len(f['seasons']) < 4:
        bits.append(' & '.join(SEASONS[x] for x in sorted(f['seasons'])))
    if f.get('weather'):
        bits.append(' or '.join(sorted(f['weather'])))
    if f.get('tide'):
        want = '/'.join(f['tide'])
        bits.append('%s tide' % want)
        if coast.tide(g) not in f['tide']:
            key = (g.day, int(g.minute) // 5)
            if _TIDES.get('key') != key:                  # worked out a few times a game hour, not every frame
                _TIDES['key'], _TIDES['list'] = key, coast.next_tides(g, 4)
            nxt = next(((k, d, m) for k, d, m in _TIDES['list'] if k.lower() in f['tide']), None)
            if nxt:
                bits.append('next %s %s' % (nxt[0].lower(), fmt_clock(nxt[2])))
        else:
            bits.append('now!')
    return _WHERE[fid], ', '.join(bits) if bits else 'any time'


def _missing_shells(g):
    return [s for s in coast.SHELLS if not g.coast['shells'].get(s['id'])]


def spares(g):
    return sum(max(0, n - 1) for n in g.coast['shells'].values())


# ---------------------------------------------------------------- every goal
TITLES = {'welcome': 'Settling in', 'request': 'A letter', 'festival': 'Festival', 'expedition': 'Outing',
          'light': 'Relight the lighthouse', 'shells': "Kit's shells", 'orders': "Morwen's orders",
          'lantern': 'The lanterns', 'legend': 'Legend hunt', 'garden': 'The garden', 'shore': 'The shore'}


def info(g, gid):
    """A goal's card: dict(id, title, icon, next, where, when, prog, act) or None if it isn't going."""
    st = g.coast
    out = dict(id=gid, title=TITLES.get(gid, gid), icon='spot', next='', where='', when='', prog=None, act=None,
               pill=None)
    if gid == 'welcome':
        if not active(g):
            return None
        out['next'], out['pill'] = welcome_line(g)
        step = g.goals['step']
        out['prog'] = (step, DONE)
        out['icon'] = STEPS[step]['icon']
        out['where'], out['when'] = STEPS[step]['where'], 'Settling in: step %d of %d' % (step + 1, DONE)
        out['act'] = welcome_act(g)
        return out
    if gid == 'request':
        req = g.request
        if not req or req.get('done'):
            return None
        f = FISH_BY_ID[req['fish']]
        who = req['who'].split(' (')[0]
        out['title'] = ("%s's birthday" % who) if req.get('birthday') else "%s's letter" % who
        out['icon'] = 'birthday' if req.get('birthday') else 'town'
        out['next'] = '%s needs a %s' % (who, f['name'])
        out['where'], out['when'] = fish_where(g, f)
        out['prog'] = out['pill'] = (req['have'], req['need'])
        out['act'] = g.read_request
        out['fish'] = f
        return out
    if gid == 'festival':
        fest = g.festival
        if not (g.festival_today() and not fest.get('done')):
            return None
        out['title'] = fest['name']
        out['icon'] = 'festival'
        out['next'] = ('Starts at %s' % fmt_clock(fest['start']) if g.minute < fest['start'] else
                       'Ends at %s: catch your best' % fmt_clock(fest['end']))
        out['where'], out['when'] = 'Your home dock', 'today'
        return out
    if gid in ('light', 'shells', 'orders') and not coast.is_open(g):
        return None
    if gid == 'light':
        if coast.lit(g):
            return None
        out['icon'] = 'meteor'
        tasks = st['tasks']
        out['prog'] = (len(tasks), 3)
        out['where'] = 'Saltmarsh, the lighthouse'
        if 'glass' not in tasks and st['glass'] < coast.GLASS_NEED:
            out['next'] = 'Sea glass for the lens'
            out['pill'] = (st['glass'], coast.GLASS_NEED)
            out['where'] = 'The beach, or swap shells with Kit'
            out['when'] = 'New glass washes up every morning'
        elif 'bass' not in tasks and not any(b['id'] == 'seabass' for b in g.basket):
            f = FISH_BY_ID['seabass']
            out['next'] = 'A %s for Sol' % f['name']
            out['where'], out['when'] = fish_where(g, f)
            out['fish'] = f
        elif 'oil' not in tasks and g.coins < coast.OIL_COST:
            out['next'] = 'Lamp oil: %d coins' % coast.OIL_COST
            out['pill'] = (g.coins, coast.OIL_COST)
            out['where'] = 'Pay Sol at the lighthouse'
            out['when'] = 'Fish and sell to save up'
        elif len(tasks) < 3:
            out['next'] = 'Bring it all to Sol at the lighthouse'
            out['when'] = 'Sol is there day and night'
        else:
            out['next'] = 'Light the lamp with Sol!'
            out['when'] = 'any time'
        return out
    if gid == 'shells':
        if st['shell_done']:
            return None
        miss = _missing_shells(g)
        have = len(coast.SHELLS) - len(miss)
        out['icon'] = 'critter'
        out['prog'] = (have, len(coast.SHELLS))
        out['pill'] = out['prog']
        n = spares(g)
        out['next'] = "Kit's shell collection"
        out['where'] = 'Missing: %s' % ', '.join(s['name'] for s in miss)
        out['when'] = ('Kit swaps your %d spare shells' % n if n >= 2 else
                       'Saltmarsh beach, early: they wash up overnight')
        return out
    if gid == 'orders':
        todo = [o for o in st['orders'] if not o['done']]
        if not todo or st['orders_day'] != g.day:
            return None
        out['icon'] = 'run'
        out['prog'] = (len(st['orders']) - len(todo), len(st['orders']))
        f = FISH_BY_ID[todo[0]['fish']]
        out['pill'] = out['prog']
        out['next'] = "Morwen's orders"
        out['where'] = 'Deliver: %s' % ', '.join(FISH_BY_ID[o['fish']]['name'] for o in todo)
        w, wh = fish_where(g, f)
        out['when'] = '%s: %s, %s' % (f['name'], w, wh)
        out['fish'] = f
        return out
    if gid == 'lantern':
        line = story.hud_line(g)
        if not line:
            return None
        out['icon'] = 'lantern'
        out['next'] = line
        lan = story.current(g)
        if lan and lan.get('spot') in SPOT_BY_ID:
            out['where'] = SPOT_BY_ID[lan['spot']]['name']
        out['when'] = 'press L for the tasks'
        out['act'] = g.open_lanterns
        return out
    if gid == 'legend':
        line = legends.hud_line(g)
        if not line:
            return None
        out['icon'] = 'festival'
        out['next'] = line
        out['when'] = 'press L, Legends tab'
        out['act'] = lambda: (g.set_lan_tab('legends'), g.open_lanterns())
        return out
    if gid == 'garden':
        line = gardenmod.hud_line(g)
        if not line:
            return None
        out['icon'] = 'garden'
        out['next'] = line
        out['where'], out['when'] = 'Your home dock', 'water the beds each day'
        out['act'] = lambda: g.open_cabin_tab('garden')
        return out
    if gid == 'shore':
        line = shoremod.hud_line(g)
        if not line:
            return None
        out['icon'] = 'reeds'
        out['next'] = line
        out['where'] = 'The shore by your dock'
        out['act'] = lambda: shoremod.open_panel(g)
        return out
    return None


ORDER = ('welcome', 'request', 'festival', 'light', 'orders', 'shells', 'lantern', 'legend', 'garden', 'shore')
COAST_GOALS = ('light', 'orders', 'shells')


def all_goals(g):
    return [x for x in (info(g, gid) for gid in ORDER) if x]


def pin(g, gid):
    st = g.goals
    st['pinned'] = None if st['pinned'] == gid else gid
    g.tracked = st['pinned']
    g.audio.play('ui', 0.6)


def catchable_here(g, f):
    return g.spot in spots_of(f['id'])


# ---------------------------------------------------------------- the Goals window (Q)
def draw_panel(g, s):
    ui = g.ui
    rect = g.big_panel(s, 'Goals')
    goals = all_goals(g)
    pinned = g.goals['pinned']
    x0, y0 = rect.x + 30, rect.y + 92
    if not goals:
        ui.blit_text(s, 'Nothing on the go right now. Fish, explore, and something will turn up.',
                     (rect.centerx, rect.centery), 'bodyb', U.SOFT, 'center')
        return
    ui.blit_text(s, 'Pin a goal and the card in the corner follows it, with where to go and when.',
                 (x0, y0 - 6), 'small', U.SOFT)
    y0 += 26
    cw = (rect.w - 60 - 16) // 2
    th = 96
    for i, gl in enumerate(goals[:10]):
        col, row = i % 2, i // 2
        r = pygame.Rect(x0 + col * (cw + 16), y0 + row * (th + 8), cw, th)
        on = gl['id'] == pinned
        ui.tile(s, r, (250, 242, 222) if on else (244, 236, 218), U.GOLD if on else (196, 170, 140))
        almanac.event_icon(s, gl['icon'], (r.x + 28, r.y + 28), 1.0)
        bw = 104
        tw = r.w - 70 - bw - 14
        ui.blit_text(s, gl['title'], (r.x + 56, r.y + 8), 'smallb', U.INK, maxw=tw)
        ui.blit_text(s, gl['next'], (r.x + 56, r.y + 34), 'small', U.INK, maxw=tw)
        wh = '  -  '.join(x for x in (gl['where'], gl['when']) if x)
        ui.blit_text(s, wh, (r.x + 56, r.y + 62), 'tiny', U.SOFT, maxw=r.w - 70)
        if gl['prog']:
            a, b = gl['prog']
            ui.blit_text(s, '%d/%d' % (a, b), (r.x + 28, r.y + 62), 'tiny', U.SOFT, 'midtop')
        ui.button(s, (r.right - bw - 10, r.y + 10, bw, 38), 'Pinned' if on else 'Pin',
                  lambda gid=gl['id']: pin(g, gid), 'gold' if on else 'primary', font='smallb', nav=True)
        if on:
            draw_pin(s, (r.right - 8, r.y + 6))


def draw_pin(s, c):
    """A little red drawing pin."""
    x, y = c
    pygame.draw.line(s, (120, 120, 130), (x - 2, y + 4), (x - 7, y + 11), 2)
    pygame.draw.circle(s, (200, 70, 66), (x, y), 6)
    pygame.draw.circle(s, (240, 140, 130), (x - 2, y - 2), 2)


# ---------------------------------------------------------------- the dock (world pixels)
def draw_dock(near, g, t):
    """The loose plank until it is mended, then a fresh one and a little pennant on the end post."""
    p = PLANK
    if g.goals['step'] < DONE:
        near.fill((54, 40, 32), p)                                   # the gap
        near.fill((30, 24, 20), (p.x, p.y + 3, p.w, 2))
        if True:
            # the plank itself, kicked up at an angle beside the hole
            wob = math.sin(t * 3) * 0.6 if g.goals['step'] == 3 else 0
            pts = [(p.x - 1, p.y + 1), (p.x + 6, p.y - 5 + wob), (p.x + 8, p.y - 3 + wob), (p.x + 1, p.y + 3)]
            pygame.draw.polygon(near, (176, 128, 86), pts)
            pygame.draw.polygon(near, (120, 86, 58), pts, 1)
            if g.goals['step'] == 3 and int(t * 2) % 2 == 0:       # a twinkle: click me
                near.set_at((p.x + 6, p.y - 8), (255, 246, 200))
                near.set_at((p.x + 5, p.y - 7), (255, 236, 170))
                near.set_at((p.x + 7, p.y - 7), (255, 236, 170))
        return
    near.fill((196, 152, 104), p)                                    # the new plank, still pale
    pygame.draw.line(near, (226, 190, 140), (p.x, p.y), (p.right - 1, p.y))
    near.set_at((p.x + 1, p.y + 2), (90, 80, 80))
    near.set_at((p.right - 2, p.y + 2), (90, 80, 80))
    # a pennant on the end of the dock
    fx, fy = 262, 286
    pygame.draw.line(near, (110, 80, 56), (fx, fy), (fx, fy - 20))
    flap = math.sin(t * 4) * 1.5
    pygame.draw.polygon(near, (220, 90, 80), [(fx + 1, fy - 20), (fx + 10, fy - 17 + flap), (fx + 1, fy - 14)])
    pygame.draw.line(near, (250, 220, 120), (fx + 1, fy - 17), (fx + 6, fy - 17 + flap * 0.5))
