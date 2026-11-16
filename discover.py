"""Biscuit-led discoveries: on walks through Fernwick she sometimes notices something and trots off to it.

Follow her and she'll be pawing at a page of Grandma Rosie's diary, one of Rosie's old lures, or (once you have
found all of those) the gap in the hedge that leads to Rosie's secret. After that she still turns up little
things now and then: a coin, some bait, a feather.

g.finds (saved): {'n': story finds so far, 'day': day of the last find, 'pages': [i...], 'lures': [id...],
                  'secret': bool, 'extra': little finds}
g.disc (not saved): what she's doing right now: {'day', 'phase', 't', 'x', 'nook'}
  phase 'idle' (waiting to notice), 'notice' (ears up), 'lead' (trotting to the spot), 'wait' (pawing at it)
"""
import random

import actors
from data import BAIT_BY_ID

LEAD_SPEED = 58.0
REACH = 22                    # how close you need to be to see what she found
SECRET_X = 1758               # the gap in the hedge between the library and the lookout

NOOKS = [(392, 'under the bakery steps'), (566, 'behind the notice board'), (640, 'by the fountain'),
         (752, 'under a bench in the square'), (884, 'in the aquarium hedge'), (1130, 'by the town hall steps'),
         (1418, "behind Pip's ring toss"), (1606, "in the library's flower bed"), (1700, 'among the roots of the old oak')]

PAGES = [
    ('Spring, the year I came',
     "Bought the cabin by the lake today with every penny I had. The roof leaks over the bed and the dock wobbles, "
     "but at dawn the whole lake went pink and a heron stood right by the post like it had been waiting for me. "
     "I think I'll stay."),
    ('Summer',
     "The reeds past the dock are full of little brown birds that never stop chattering. I sat in the shallows with "
     "my trousers rolled up and one landed on my hat. Tom says I'll catch my death. Tom worries too much."),
    ('Autumn',
     "Built a landing on the far shore so I can row over for blackberries. It's crooked, but it's mine. Mabel came "
     "with a pie and we ate the whole thing on the end of it with our feet in the water."),
    ('Winter',
     "Ice on the lake this morning, thin as a window. I made my first lure by the stove tonight: a spinner cut from "
     "an old red teaspoon. If it catches nothing, at least it's pretty."),
    ('Spring again',
     "A kitten turned up on the dock in the rain, orange as a marmalade jar and furious about the weather. I gave "
     "her a bit of perch, and she has decided she lives here now. I've named her Biscuit."),
    ('Summer, with Biscuit',
     "Biscuit trots after me into Fernwick now. She found my thimble under the bakery steps and a penny behind the "
     "notice board. That cat notices everything, so I've started hiding little things around town for her to find."),
    ('Autumn, many years on',
     "My knees don't care for rowing any more, and the landing has gone back to the brambles. I don't mind. One "
     "day someone young will clear it. If you're reading this, my dear, follow the cat. She knows where I hid the "
     "best thing of all."),
]
SECRET_LETTER = ('Under the bench, in a tin',
                 "For my grandchild. This lake has been the best thing in my life: the mornings, the fish, the "
                 "friends, one very bossy cat. Now it's yours. Be patient, be kind to the water, and catch "
                 "something lovely. All my love.", '- Grandma Rosie')
LURES = [('spinner', "Rosie's Red Spinner", 'the spinner she cut from a red teaspoon'),
         ('feather', 'Jay Feather Fly', 'a fly tied with a blue jay feather and a lot of patience'),
         ('minnow', 'Carved Wooden Minnow', 'a little minnow whittled from birch, with painted eyes')]
LURE_BY_ID = {lid: (lid, name, desc) for lid, name, desc in LURES}
# the order of the story: pages and lures, then the secret
ORDER = ['p0', 'l0', 'p1', 'p2', 'l1', 'p3', 'p4', 'l2', 'p5', 'p6', 'secret']


def new():
    return {'n': 0, 'day': 0, 'pages': [], 'lures': [], 'secret': False, 'extra': 0}


def clean(f):
    base = new()
    if not isinstance(f, dict):
        return base
    try:
        base['n'] = max(0, min(len(ORDER), int(f.get('n', 0))))
        base['day'] = max(0, int(f.get('day', 0)))
        base['extra'] = max(0, int(f.get('extra', 0)))
    except (TypeError, ValueError):
        pass
    base['pages'] = sorted({i for i in f.get('pages', []) if isinstance(i, int) and 0 <= i < len(PAGES)})
    base['lures'] = [lid for lid, _, _ in LURES if lid in (f.get('lures') or [])]
    base['secret'] = bool(f.get('secret'))
    return base


def next_find(g):
    f = g.finds
    return ORDER[f['n']] if f['n'] < len(ORDER) else 'extra'


def chance(g):
    import biscuit
    return min(0.9, 0.55 + 0.1 * max(0, biscuit.level(g) - biscuit.FOLLOW_LEVEL))


# ---------------------------------------------------------------- on the street
def on_town(g, rng=random):
    """Arriving in Fernwick with Biscuit: will she notice something today?"""
    import biscuit
    d = getattr(g, 'disc', None)
    if not biscuit.follows(g) or g.finds['day'] == g.day:
        g.disc = None
        return
    if d and d.get('day') == g.day:
        if d['phase'] in ('lead', 'wait', 'notice'):
            d.update(phase='idle', t=1.5)          # she remembers where it was
        return
    if rng.random() < chance(g):
        g.disc = {'day': g.day, 'phase': 'idle', 't': rng.uniform(5, 14), 'x': None, 'nook': ''}
    else:
        g.disc = {'day': g.day, 'phase': 'none', 't': 0.0, 'x': None, 'nook': ''}


def _pick(g, px, rng):
    if next_find(g) == 'secret':
        return SECRET_X, 'a gap in the hedge'
    near = [n for n in NOOKS if 90 <= abs(n[0] - px) <= 520] or NOOKS
    return rng.choice(near)


def drive(g, tn, dt, rng=random):
    """Moves Biscuit while she's onto something. Returns True if she's busy (and not just following you)."""
    d = getattr(g, 'disc', None)
    if not d or d['phase'] in ('none', 'done'):
        return False
    cat = tn.cat
    if d['phase'] == 'idle':
        if g.overlay is None and cat.x is not None:
            d['t'] -= dt
            if d['t'] <= 0:
                d['phase'], d['t'] = 'notice', 1.3
                d['x'], d['nook'] = _pick(g, tn.x, rng)
                g.audio.play('purr', 0.5)
                g.toast("Biscuit's ears prick up. She's noticed something!", (200, 130, 80))
        return False
    if cat.x is None:
        cat.x = tn.x - 18 * tn.face
    if d['phase'] == 'notice':
        d['t'] -= dt
        cat.step = 0.0
        cat.face = 1 if d['x'] > cat.x else -1
        if d['t'] <= 0:
            d['phase'] = 'lead'
        return True
    if d['phase'] == 'lead':
        dx = d['x'] - cat.x
        if abs(dx) < 2:
            cat.x = d['x']
            d['phase'], d['t'] = 'wait', 0.0
            cat.step = 0.0
        else:
            cat.face = 1 if dx > 0 else -1
            cat.x += cat.face * min(abs(dx), LEAD_SPEED * dt)
            cat.step += dt * 12
        return True
    # waiting at the spot: look back at you now and then, and paw at it
    d['t'] += dt
    cat.step = 0.0
    cat.face = 1 if tn.x > cat.x else -1
    if d['t'] % 4.0 < 2.0:
        cat.face = 1 if d['x'] >= cat.x else -1
    return True


def waiting(g):
    d = getattr(g, 'disc', None)
    return bool(d) and d['phase'] == 'wait'


def near_find(g):
    return waiting(g) and abs(g.town.x - g.disc['x']) < REACH


def busy(g):
    d = getattr(g, 'disc', None)
    return bool(d) and d['phase'] in ('notice', 'lead', 'wait')


def hud_line(g):
    if g.place != 'town' or not busy(g):
        return None
    if g.disc['phase'] == 'wait':
        return 'Biscuit found something: go and see'
    return 'Biscuit is onto something: follow her!'


def draw_town(s, g, t, scroll, ground):
    """A little bubble over her while she's onto something."""
    if not busy(g) or g.town.cat.x is None:
        return
    x = int(g.town.cat.x - scroll)
    kind = 'bang' if g.disc['phase'] == 'notice' else 'dots' if g.disc['phase'] == 'lead' else \
        ('bang' if int(t * 1.2) % 3 == 0 else 'dots')
    actors.draw_bubble(s, x + 1, ground - 17, kind, t)


def click(g, tx, wy, ground):
    """Clicking Biscuit while she waits: walk over and look."""
    if not waiting(g) or abs(tx - g.disc['x']) > 10 or not (ground - 20 < wy < ground + 4):
        return False
    tn = g.town
    side = -10 if tn.x < g.disc['x'] else 10
    tn.walk_to(g.disc['x'] + side, lambda: reveal(g))
    return True


# ---------------------------------------------------------------- what she found
def reveal(g, rng=random):
    """A short scene: you look at what she's pawing at, and it's yours."""
    import scenes
    if not near_find(g) and not (waiting(g) and abs(g.town.x - g.disc['x']) < REACH + 12):
        return False
    d = g.disc
    nook = d['nook']
    what = next_find(g)
    d['phase'] = 'done'
    g.finds['day'] = g.day
    tn = g.town
    you_face = 1 if d['x'] > tn.x else -1
    beats = [('face', 'you', you_face), ('emote', 'you', 'bang')]
    end = None
    if what.startswith('p'):
        i = int(what[1:])
        head, body = PAGES[i]
        beats += [('say', 'you', "Biscuit is pawing at something %s... It's a page from Grandma Rosie's diary!"
                   % nook), ('call', lambda g, i=i: _got_page(g, i))]
        end = lambda g, i=i: g.open_letter(page_letter(i))
    elif what.startswith('l'):
        lid, name, desc = LURES[int(what[1:])]
        beats += [('say', 'you', "Biscuit noses something shiny out %s. It's one of Grandma's old lures: %s!"
                   % (nook, desc)),
                  ('call', lambda g, lid=lid: _got_lure(g, lid))]
    elif what == 'secret':
        beats = [('face', 'you', 1),
                 ('fade', 'Biscuit slips through a gap in the hedge, and you squeeze after her. A narrow path '
                          'winds down through the birches to the water.'),
                 ('say', 'you', "A little bench, right at the lake's edge. Someone carved an R and a fish into it."),
                 ('say', 'you', "And underneath... a tin box, with Grandma's handwriting on the lid."),
                 ('emote', 'you', 'heart'),
                 ('call', _got_secret)]
        end = lambda g: g.open_letter(SECRET_LETTER)
    else:
        kind, text = _extra(g, rng)
        beats += [('say', 'you', 'Biscuit found %s %s. Good cat!' % (text, nook)),
                  ('call', lambda g, kind=kind: _got_extra(g, kind))]
    beats += [('emote', 'you', 'note'), ('wait', 0.5)]
    g.scene = scenes.Cutscene(g, beats, 'town', on_end=end, title='Biscuit found something')
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('purr', 0.7)
    return True


def page_letter(i):
    head, body = PAGES[i]
    return ("Rosie's diary: " + head, body, '- Rosie')


def _story_step(g):
    g.finds['n'] = min(len(ORDER), g.finds['n'] + 1)
    g.stats['finds'] = g.finds['n']
    g.cat['excited'] = 1.5


def _got_page(g, i):
    if i not in g.finds['pages']:
        g.finds['pages'].append(i)
        g.finds['pages'].sort()
        _story_step(g)
        g.toast("A page of Rosie's diary (%d of %d). It's in your journal, under Letters."
                % (len(g.finds['pages']), len(PAGES)), (200, 130, 80))
        g.check_badges()


def _got_lure(g, lid):
    if lid in g.finds['lures']:
        return
    g.finds['lures'].append(lid)
    _story_step(g)
    first = 'lureboard' not in g.home['owned']
    if first:
        g.home['owned'].append('lureboard')
    g.toast("%s goes on Rosie's lure board%s." % (LURE_BY_ID[lid][1], ' (a new wall decoration in your cabin)'
                                                  if first else ''), (200, 150, 80))
    g.audio.play('jingle2', 0.6)


def _got_secret(g):
    if g.finds['secret']:
        return
    g.finds['secret'] = True
    _story_step(g)
    if 'tacklebox' not in g.home['owned']:
        g.home['owned'].append('tacklebox')
    g.baits['golden'] = g.baits.get('golden', 0) + 3
    g.luck = min(3.0, g.luck + 1.5)
    g.toast("Rosie's tackle box, with three Golden Lures inside. It's in your cabin's Home catalogue.",
            (210, 160, 60))
    g.audio.play('jingle3', 0.7)
    g.check_badges()


def _extra(g, rng):
    return rng.choice([('coins', 'a few coins'), ('bait', 'a twist of Glow Grubs'), ('feather', 'a heron feather'),
                       ('coins', 'a shiny coin')])


def _got_extra(g, kind, rng=random):
    g.finds['extra'] += 1
    if kind == 'coins':
        n = rng.randint(10, 30)
        g.coins += n
        g.toast('+%d coins. Biscuit looks very pleased with herself.' % n, (210, 160, 60))
    elif kind == 'bait':
        g.baits['glow'] = g.baits.get('glow', 0) + 3
        g.toast('+3 %s.' % BAIT_BY_ID['glow']['name'], (90, 150, 140))
    else:
        g.luck = min(3.0, g.luck + 0.5)
        g.toast('A heron feather: they say it brings a little luck.', (110, 150, 100))
