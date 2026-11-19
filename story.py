"""The lantern story: relighting the four old lanterns of Lantern Lake, one season at a time.

Ms. Alder finds notes about the lanterns in the library archive and writes to you on your second morning. Each
lantern stands on the far shore, seen from one rowboat spot, and wakes up in its own season: once its three
tasks are done (and in year one, once its season has come), row out there and light it. A short cutscene plays.
When all four burn, the whole town comes down to the dock that night for the Night of Four Lanterns, which ends
year one's story.

State lives in Game.story: {'started': bool, 'lit': [ids], 'festival': bool, 'flags': [...]}.
"""
import math
import random

import pygame

import scenes
import ui as U
from art import HORIZON, add_glow, lerp_c, mul_c
from data import FISH_BY_ID, SEASONS, DAYS_PER_SEASON


def _kinds(g):
    return [f for f in g.journal if f in FISH_BY_ID]


def _rare(g):
    return [f for f in _kinds(g) if FISH_BY_ID[f]['rarity'] >= 3]


def _hearts(g, n):
    return sum(1 for v in g.friends.values() if v >= n * 10)


LANTERNS = [
    dict(id='dock', name='Dock Lantern', season=0, spot='dock', x=410,
         line='The Dock Lantern was always first. "Light it for the ones who stay close to home."',
         tasks=[('Catch 8 kinds of fish', lambda g: (len(_kinds(g)), 8)),
                ('Cook a dish with 3 stars', lambda g: (g.stats.get('perfect_dishes', 0), 1)),
                ('Reach 3 hearts with a neighbour', lambda g: (_hearts(g, 3), 1))]),
    dict(id='cove', name='Cove Lantern', season=1, spot='cove', x=360,
         line='The Cove Lantern is for summer. "Light it for everyone who ever shared a catch."',
         tasks=[('Donate 8 fish to the aquarium', lambda g: (len(g.museum), 8)),
                ('Fish at 3 different spots', lambda g: (len(g.stats.get('spots', [])), 3)),
                ('Fund a town project', lambda g: (len(g.projects), 1))]),
    dict(id='deep', name='Deep Lantern', season=2, spot='deep', x=250,
         line='The Deep Lantern burns over the old fish. "Light it for the patient ones."',
         tasks=[('Catch 3 kinds of rare fish', lambda g: (len(_rare(g)), 3)),
                ('Cook 5 different recipes', lambda g: (len(g.cook_best), 5)),
                ('Reach 5 hearts with 3 neighbours', lambda g: (_hearts(g, 5), 3))]),
    dict(id='creek', name='Creek Lantern', season=3, spot='creek', x=196,
         line='The Creek Lantern is the last, where the river comes in. "Light it, and bring everyone home."',
         tasks=[('Catch 20 kinds of fish', lambda g: (len(_kinds(g)), 20)),
                ('Build a home upgrade', lambda g: (len(g.upgrades), 1)),
                ('Cook 15 dishes', lambda g: (g.stats.get('cooked', 0), 15))]),
]
LANTERN_BY_ID = {l['id']: l for l in LANTERNS}
LANTERN_AT = {l['spot']: l for l in LANTERNS}


def new_state():
    return {'started': False, 'lit': [], 'festival': False, 'flags': []}


def clean(st):
    base = new_state()
    if not isinstance(st, dict):
        return base
    base['started'] = bool(st.get('started'))
    base['festival'] = bool(st.get('festival'))
    base['lit'] = [x for x in st.get('lit', []) if x in LANTERN_BY_ID] if isinstance(st.get('lit'), list) else []
    base['flags'] = [str(x) for x in st.get('flags', [])] if isinstance(st.get('flags'), list) else []
    return base


def year(g):
    return (g.day - 1) // (DAYS_PER_SEASON * 4)


def tasks(g, lan):
    return [(label, min(have, need), need) for label, fn in lan['tasks'] for have, need in [fn(g)]]


def tasks_done(g, lan):
    return all(h >= n for _, h, n in tasks(g, lan))


def current(g):
    """The next lantern to light, or None when all four burn."""
    for lan in LANTERNS:
        if lan['id'] not in g.story['lit']:
            return lan
    return None


def awake(g, lan):
    """In year one a lantern wakes in its own season; after that, any time."""
    return year(g) > 0 or g.season_of(g.day) >= lan['season']


def can_light(g, lan):
    """(ok, reason)"""
    if not g.story['started'] or lan['id'] in g.story['lit']:
        return False, ''
    if current(g) is not lan:
        return False, 'Light the %s first.' % current(g)['name']
    if not awake(g, lan):
        return False, 'It wakes up in %s.' % SEASONS[lan['season']]
    if not tasks_done(g, lan):
        return False, 'Finish its three tasks first.'
    if g.place != 'lake' or g.spot != lan['spot']:
        from data import SPOT_BY_ID
        return False, 'Row out to %s to light it.' % SPOT_BY_ID[lan['spot']]['name']
    return True, ''


def hud_line(g):
    st = g.story
    if not st['started'] or st['festival']:
        return None
    lan = current(g)
    if lan is None:
        return 'All four lanterns burn. Tonight...'
    if not awake(g, lan):
        return '%s wakes in %s' % (lan['name'], SEASONS[lan['season']])
    done = sum(1 for _, h, n in tasks(g, lan) if h >= n)
    if done == 3:
        return '%s is ready to light!' % lan['name']
    return '%s: %d / 3 tasks' % (lan['name'], done)


# ---------------------------------------------------------------- flow
def start(g):
    if g.story['started']:
        return
    g.story['started'] = True
    g.toast('New: the Lantern story. Press L to see the four lanterns.', (230, 170, 80))
    g.audio.play('wish', 0.5)


def morning(g):
    """Called from Game.start_day: Ms. Alder's letter on day two starts the story."""
    if not g.story['started'] and g.day >= 2:
        g.story['started'] = True
        g.queue.append(('letter', ('Dear angler,', (
            "While cataloguing the library archive I found a bundle of old notes about the four lanterns that "
            "gave Lantern Lake its name. They stand on the far shore, dark for fifty years now. The notes say each "
            "one wants proof that somebody loves the lake, and that each wakes in its own season. I have copied "
            "the notes for you (press L). Do come by the library and tell me how you get on."),
            '- Ms. Alder, Fernwick Library')))


def light(g, lan):
    ok, why = can_light(g, lan)
    if not ok:
        g.toast(why, (150, 140, 130))
        return
    g.overlay = None
    who, heard = REACTIONS[lan['id']]
    x = lan['x']
    beats = [
        ('fade', 'You row out across the still water to the far shore. The %s stands in the reeds, cold and '
                 'rusted shut.' % lan['name']),
        ('focus', (x, HORIZON - 12), 104, 3.0),               # in close: the old lantern on its post
        ('say', 'you', 'There\'s a little brass plate on the post. "%s"' % lan['line'].split('"')[1]),
        ('say', 'you', 'A twist of dry reed, a match from the tin... Steady now.'),
        ('ritual', 'light the wick'),
        ('call', lambda g, lid=lan['id']: _do_light(g, lid)),
        ('wait', 2.4),
        ('focus', (320, HORIZON + 20), 640, 3.6),             # right back out: the whole lake, and its light
        ('call', _town_wakes),
        ('wait', 3.0),
        ('say', who, heard),
        ('say', 'you', lambda g, lan=lan: _light_reply(g, lan)),
    ]
    g.scene = scenes.Cutscene(g, beats, 'lake', title=lan['name'], on_end=_after_light)
    g.scene.focus = (x, HORIZON + 10)
    g.scene.zoom_w = 448
    g.scene.fx = {'lantern': lan['id']}
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('wish', 0.35)


# who calls across the water when each lantern catches
REACTIONS = {
    'dock': ('pip', "(from the shore path) I SAW IT! I saw it from my window! Is it magic? It's magic, isn't it!"),
    'cove': ('juniper', "(rowing past) The whole cove's gone gold. The fish are all coming up to have a look."),
    'deep': ('tom', "(on the jetty, very quietly) Fifty years I've waited to see a light out on the Deep. "
                    "Don't mind me. Something in my eye."),
    'creek': ('librarian', "(from the footbridge) All four. Rosie... they're burning again. Come up to the village "
                           "tonight, dear. Everyone's coming down to the dock."),
}


def _town_wakes(g):
    """Up in Fernwick, windows light one by one and somebody rings the old bell on the hill."""
    sc = getattr(g, 'scene', None)
    if sc is not None:
        sc.fx['town'] = sc.t
    g.audio.play('townbell', 0.6)


def _light_reply(g, lan):
    n = len(g.story['lit'])
    return {1: 'One down. Grandma, I hope you can see it from wherever you are.',
            2: 'Two lanterns burning. The lake looks warmer already.',
            3: 'Three. Just the Creek Lantern left.',
            4: 'All four... The whole lake is glowing.'}.get(n, 'It burns again.')


def _do_light(g, lid):
    if lid not in g.story['lit']:
        g.story['lit'].append(lid)
    g.world.sparkles(LANTERN_BY_ID[lid]['x'], HORIZON - 15, 34, (255, 220, 140), 16)
    g.world.ripple(LANTERN_BY_ID[lid]['x'], HORIZON + 3, 10, 18, 160)
    sc = getattr(g, 'scene', None)
    if sc is not None:
        sc.fx['lit_at'] = sc.t
    g.audio.play('lantern', 0.8)
    g.shake(0.6)
    g.stats['lanterns'] = len(g.story['lit'])
    g.luck = min(3.0, g.luck + 1.0)


def _after_light(g):
    g.toast('The %s burns again. (+ luck)' % LANTERN_BY_ID[g.story['lit'][-1]]['name'], (230, 170, 80))
    g.check_badges()


def update(g, dt):
    """The Night of Four Lanterns starts on the first evening at the dock after the last lantern is lit."""
    st = g.story
    if (st['started'] and not st['festival'] and len(st['lit']) == 4 and g.overlay is None
            and g.rest_phase is None and g.place == 'lake' and g.spot == 'dock' and g.minute >= 1170
            and g.fishing.state == 'idle' and g.mode == 'play'):
        festival(g)


FOLK_ON_DOCK = [('mabel', 112), ('tom', 126), ('hazel', 140), ('juniper', 154), ('fen', 168), ('librarian', 182),
                ('pip', 196)]


def festival(g):
    g.story['festival'] = True
    g.festival_fx = {'t': 0.0, 'lanterns': [], 'fireworks': [], 'folk': True}
    beats = [
        ('fade', 'Word travels fast in Fernwick. As the sun goes down, the whole town walks down the path to your '
                 'dock, carrying paper lanterns.'),
        ('say', 'hazel', "Citizens of Fernwick! Fifty years ago this lake went dark. Tonight, thanks to one stubborn "
                         "angler and one very fluffy cat, it is lit again!"),
        ('say', 'librarian', "Rosie would have loved this. The records say she always cried at the festival. "
                             "Happy tears, of course."),
        ('say', 'tom', "Alright, alright. Everyone grab a lantern before Pip lights them all at once."),
        ('call', lambda g: g.festival_fx.update(release=True)),
        ('wait', 3.5),
        ('say', 'pip', "LOOK! They're floating! They're going all the way up!"),
        ('say', 'mabel', "I brought tarts for everybody. Rosie's recipe, naturally."),
        ('say', 'fen', "I'm not even going to try to paint this. Some things you just keep."),
        ('say', 'juniper', "Every fish in the lake is looking up right now. I'm sure of it."),
        ('wait', 2.5),
        ('say', 'you', "Thank you, everyone. For all of it."),
        ('picture', 'yearone', 'The Night of Four Lanterns'),
        ('call', _festival_reward),
    ]
    g.scene = scenes.Cutscene(g, beats, 'lake', title='The Night of Four Lanterns', on_end=_after_festival)
    g.scene.focus = (190, 252)
    g.scene.zoom_w = 448
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('wish', 0.6)


def _festival_reward(g):
    if 'lanternhat' not in g.hats:
        g.hats.append('lanternhat')
    g.coins += 1000
    for k in list(g.friends):
        g.add_friend(k, 10)


def _after_festival(g):
    g.festival_fx['folk'] = False
    g.festival_fx['release'] = True
    g.toast('Year one\'s story is complete! You got the Lantern Hat and 1,000 coins.', (230, 170, 80))
    g.audio.play('jingle5', 0.7)
    g.check_badges()


def update_fx(g, dt):
    fx = getattr(g, 'festival_fx', None)
    if not fx:
        return
    fx['t'] += dt
    rng = random
    if fx.get('release') and fx['t'] < 400 and rng.random() < dt * (9 if fx.get('folk') else 3):
        fx['lanterns'].append([rng.uniform(90, 600), rng.uniform(250, 300), rng.uniform(-3, 3), 0.0,
                               rng.choice(((255, 190, 110), (255, 160, 120), (255, 220, 140)))])
    for l in fx['lanterns']:
        l[3] += dt
        l[0] += (l[2] + math.sin(l[3] * 0.8 + l[1]) * 2) * dt
        l[1] -= (6 + l[3] * 0.4) * dt
    fx['lanterns'] = [l for l in fx['lanterns'] if l[1] > -10][-160:]
    if fx.get('folk') and fx.get('release') and rng.random() < dt * 0.9:
        fx['fireworks'].append([rng.uniform(140, 560), rng.uniform(40, 120), 0.0,
                                rng.choice(((255, 200, 120), (180, 220, 255), (255, 150, 180), (200, 255, 190)))])
    for f in fx['fireworks']:
        f[2] += dt
    fx['fireworks'] = [f for f in fx['fireworks'] if f[2] < 1.8]
    if not fx.get('folk') and fx['t'] > 40 and not fx['lanterns']:
        g.festival_fx = None


# ---------------------------------------------------------------- drawing at the lake
def draw_far(g, frame, env, world):
    """This spot's old lantern on the far shore (before the water, so the lake reflects it)."""
    st = g.story
    lan = LANTERN_AT.get(g.spot)
    if not lan or not st['started']:
        return
    x, base = lan['x'], HORIZON
    amb = lerp_c(env.amb, env.sky[2], 0.35)
    lit = lan['id'] in st['lit']

    def c(col):
        return mul_c(col, amb)
    sc = g.scene if (getattr(g, 'overlay', None) == 'scene' and getattr(g, 'scene', None)) else None
    fx = sc.fx if sc is not None and sc.fx.get('lantern') == lan['id'] else None
    _village(g, frame, world, sc)
    # the post, a little cross-arm, and the lantern: a glass box under a peaked brass cap
    frame.fill(c((70, 60, 54)), (x, base - 12, 1, 12))
    frame.fill(c((70, 60, 54)), (x - 2, base - 13, 5, 1))
    frame.fill(c((60, 56, 50)), (x - 2, base - 18, 5, 5))
    frame.fill(c((44, 40, 40)), (x - 1, base - 17, 3, 3))                 # dark glass
    frame.fill(c((110, 92, 64)), (x - 2, base - 19, 5, 1))
    frame.set_at((x, base - 20), c((110, 92, 64)))
    frame.set_at((x, base - 21), c((90, 80, 70)))                         # the ring on top
    catching = fx is not None and not lit
    if catching and sc.ritual > 0.01:
        k = sc.ritual
        frame.fill((255, 200, 120), (x, base - 16, 1, 1 + int(k * 1.5)))
        add_glow(frame, world.g_mid, (x, base - 15), 0.15 + 0.5 * k * (0.9 + 0.1 * math.sin(world.t * 23)))
    if lit:
        fl = 0.85 + 0.15 * math.sin(world.t * 7 + x)
        frame.fill((255, 236, 170), (x - 1, base - 17, 3, 3))
        frame.fill((255, 250, 220), (x, base - 16, 1, 2))
        boost = 0.0
        if fx is not None and 'lit_at' in fx:
            boost = max(0.0, 1.6 - (sc.t - fx['lit_at']) * 0.5)          # the flare as it catches
        add_glow(frame, world.g_mid, (x, base - 15), (0.35 + 0.55 * env.nf) * fl + boost)
        if boost > 0.4:
            add_glow(frame, world.g_mid, (x, base - 15), boost * 0.6)
    elif not can_light(g, lan)[0] and current(g) is lan and tasks_done(g, lan) and awake(g, lan):
        pass
    if not lit and current(g) is lan and awake(g, lan) and tasks_done(g, lan):
        # ready: a faint pulse to say "come and light me"
        k = 0.5 + 0.5 * math.sin(world.t * 3)
        add_glow(frame, world.g_mid, (x, base - 15), 0.12 + 0.15 * k)


VILLAGE = [(18 + i * 9 + (i * 7) % 5, (i * 5) % 4) for i in range(13)]


def _village(g, frame, world, sc):
    """Fernwick's windows along the far left shore, lighting one by one when a lantern catches."""
    if sc is None or 'town' not in sc.fx:
        return
    k = (sc.t - sc.fx['town']) / 2.2
    for i, (vx, dy) in enumerate(VILLAGE):
        if k * len(VILLAGE) < i + 1:
            break
        y = HORIZON - 3 - dy
        frame.fill((255, 214, 140), (vx, y, 2, 1))
        add_glow(frame, world.g_mid, (vx, y), 0.22)


def draw_near(g, near):
    """The festival: townsfolk on the dock, paper lanterns rising, fireworks."""
    fx = getattr(g, 'festival_fx', None)
    if not fx:
        return
    import town as T
    from art import DECK_Y
    if fx.get('folk') and g.spot == 'dock':
        for k, x in FOLK_ON_DOCK:
            spec = T.FOLK[k]
            T.walker(near, x, DECK_Y, 1, 0, spec['shirt'], spec['hair'], spec['hat'], g.env.season,
                     spec.get('kid'), spec.get('glasses'))
            if fx.get('release'):
                near.fill((255, 210, 140), (x + 3, DECK_Y - 18 - int(2 * math.sin(fx['t'] * 2 + x)), 3, 3))
    for x, y, vx, t, col in fx['lanterns']:
        a = int(255 * min(1.0, t / 0.6))
        near.fill((*col, a), (int(x), int(y), 2, 3))
        near.fill((255, 250, 220, a), (int(x), int(y) + 1, 2, 1))


def draw_lights(g, frame, world):
    fx = getattr(g, 'festival_fx', None)
    if not fx:
        return
    for x, y, vx, t, col in fx['lanterns']:
        add_glow(frame, world.g_mid, (int(x) + 1, int(y) + 1), 0.3)
    for x, y, t, col in fx['fireworks']:
        r = 4 + t * 26
        k = max(0.0, 1 - t / 1.8)
        for i in range(14):
            a = i / 14 * 2 * math.pi
            px, py = x + math.cos(a) * r, y + math.sin(a) * r + t * t * 6
            frame.fill(tuple(int(v * k) for v in col), (int(px), int(py), 2, 2), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------- the lanterns page (L)
def draw_map(g, s, rect, t):
    """Ms. Alder's copy of the old lantern map."""
    ui = g.ui
    s.fill((236, 220, 180), rect)
    for i in range(0, rect.h, 7):
        s.fill((230, 212, 170), (rect.x, rect.y + i, rect.w, 2))
    lake = rect.inflate(-rect.w // 4, -rect.h // 3)
    pygame.draw.ellipse(s, (150, 180, 190), lake)
    pygame.draw.ellipse(s, (110, 140, 150), lake, 3)
    for i, lan in enumerate(LANTERNS):
        a = -math.pi * 0.85 + i * math.pi * 0.56
        x = lake.centerx + math.cos(a) * (lake.w / 2 + 6)
        y = lake.centery + math.sin(a) * (lake.h / 2 + 6)
        lit = lan['id'] in g.story['lit']
        if lit:
            pygame.draw.circle(s, (255, 220, 140), (int(x), int(y)), 14)
        pygame.draw.circle(s, (90, 60, 40), (int(x), int(y)), 8)
        pygame.draw.circle(s, (250, 200, 90) if lit else (200, 180, 150), (int(x), int(y)), 5)
        ui.blit_text(s, lan['name'].split()[0], (int(x), int(y) + (18 if y > lake.centery else -30)), 'tiny',
                     (90, 60, 40), 'midtop')
    ui.blit_text(s, 'LANTERN LAKE', (rect.centerx, lake.centery - 10), 'h3', (70, 90, 100), 'center')
    pygame.draw.line(s, (150, 110, 80), (rect.x + 30, rect.bottom - 30), (rect.x + 120, rect.bottom - 30), 2)


def draw_panel(g, s):
    import legends
    ui = g.ui
    tab = getattr(g, 'lan_tab', 'lanterns')
    rect = g.big_panel(s, 'The Four Lanterns' if tab == 'lanterns' else 'Legends of the Lake')
    # two tabs: the lanterns, and the legend hunts
    tabs = [('lanterns', 'Lanterns'), ('legends', 'Legends  %d/4' % legends.done_count(g))]
    for i, (key, label) in enumerate(tabs):
        r = pygame.Rect(rect.centerx - 230 + i * 236, rect.y + 88, 224, 38)
        ui.button(s, r, label, lambda key=key: g.set_lan_tab(key), 'primary' if tab == key else 'normal',
                  font='small')
    hint = g.hint([('key', 'Tab'), 'switch'], [('pad', 'LB'), 'switch'])
    ui.rich(s, hint, (rect.right - 30 - ui.rich(s, hint, (0, 0), measure=True), rect.y + 98), U.SOFT, False)
    if tab == 'legends':
        legends.draw_page(g, s, rect)
        return
    rect = rect.move(0, 0)
    st = g.story
    if not st['started']:
        ui.blit_text(s, 'Nobody has lit the old lanterns in fifty years...', rect.center, 'body', U.SOFT, 'center')
        return
    mp = pygame.Rect(rect.x + 30, rect.y + 144, 330, 230)
    pygame.draw.rect(s, (120, 90, 60), mp.inflate(10, 10), border_radius=6)
    draw_map(g, s, mp, g.t)
    ui.blit_text(s, '%d of 4 lit' % len(st['lit']), (mp.centerx, mp.bottom + 22), 'bodyb', (170, 110, 60), 'midtop')
    lines = ui.wrap('Each lantern wakes in its own season. Finish its three tasks, then row out to its spot '
                    'and light it from this page.', 'small', mp.w)
    for i, ln in enumerate(lines):
        ui.blit_text(s, ln, (mp.x, mp.bottom + 64 + i * 24), 'small', U.SOFT)
    x0 = mp.right + 40
    cw = rect.right - 30 - x0
    for i, lan in enumerate(LANTERNS):
        r = pygame.Rect(x0, rect.y + 140 + i * 118, cw, 110)
        lit = lan['id'] in st['lit']
        cur = current(g) is lan
        ui.tile(s, r, (252, 240, 210) if lit else (250, 244, 228) if cur else (232, 226, 214),
                (220, 170, 90) if lit else (196, 170, 140))
        # a little lantern icon
        cx, cy = r.x + 34, r.y + 50
        s.fill((80, 66, 56), (cx - 2, cy, 4, 40))
        s.fill((80, 66, 56), (cx - 12, cy - 22, 24, 24))
        s.fill((255, 214, 120) if lit else (90, 84, 80), (cx - 8, cy - 18, 16, 16))
        s.fill((80, 66, 56), (cx - 14, cy - 26, 28, 5))
        ui.blit_text(s, lan['name'], (r.x + 70, r.y + 12), 'bodyb', U.INK)
        ui.blit_text(s, SEASONS[lan['season']], (r.right - 16, r.y + 14), 'small', U.SOFT, 'topright')
        if lit:
            ui.blit_text(s, 'Burning bright.', (r.x + 70, r.y + 50), 'small', (170, 110, 60))
            continue
        if not cur:
            ui.blit_text(s, 'Light the earlier lanterns first.', (r.x + 70, r.y + 50), 'small', U.SOFT)
            continue
        for j, (label, h, n) in enumerate(tasks(g, lan)):
            done = h >= n
            y = r.y + 38 + j * 22
            pygame.draw.rect(s, (120, 170, 110) if done else (200, 180, 160), (r.x + 70, y + 2, 16, 16),
                             border_radius=4)
            if done:
                pygame.draw.lines(s, (255, 255, 255), False, [(r.x + 73, y + 10), (r.x + 77, y + 14),
                                                              (r.x + 83, y + 5)], 2)
            ui.blit_text(s, '%s  (%d/%d)' % (label, h, n), (r.x + 94, y), 'small', U.INK if not done else U.SOFT,
                         maxw=r.w - 280)
        ok, why = can_light(g, lan)
        if ok:
            ui.button(s, (r.right - 176, r.bottom - 50, 160, 40), 'Light it', lambda lan=lan: light(g, lan),
                      'gold', font='small')
        else:
            for j, ln in enumerate(ui.wrap(why, 'tiny', 170)[:3]):
                ui.blit_text(s, ln, (r.right - 16, r.y + 40 + j * 20), 'tiny', U.SOFT, 'topright')
    if st['festival']:
        ui.blit_text(s, 'The Night of Four Lanterns has been held. The lake will never go dark again.',
                     (rect.centerx, rect.bottom - 34), 'small', (170, 110, 60), 'center')


def draw_yearone(g, s, rect, t):
    """The picture at the end of the festival: a summary of your first year."""
    ui = g.ui
    for i in range(rect.h):
        s.fill(lerp_c((30, 30, 70), (120, 70, 90), i / rect.h), (rect.x, rect.y + i, rect.w, 1))
    rng = random.Random(4)
    for _ in range(40):
        x, y = rect.x + rng.randrange(rect.w), rect.y + rng.randrange(rect.h)
        k = 0.5 + 0.5 * math.sin(t * 2 + x)
        s.fill((int(200 + 55 * k), int(170 + 40 * k), 110), (x, y - int((t * 12 + x) % rect.h) % rect.h // 8, 3, 4))
    ui.blit_text(s, 'Year One', (rect.centerx, rect.y + 30), 'h1', (255, 230, 170), 'midtop')
    stats = [('Kinds of fish caught', len(_kinds(g))), ('Fish in the aquarium', len(g.museum)),
             ('Dishes cooked', g.stats.get('cooked', 0)), ('Friends with 5+ hearts', _hearts(g, 5)),
             ('Town projects built', len(g.projects)), ('Lanterns lit', len(g.story['lit']))]
    for i, (label, v) in enumerate(stats):
        y = rect.y + 110 + i * 34
        ui.blit_text(s, label, (rect.x + 70, y), 'body', (240, 230, 220))
        ui.blit_text(s, str(v), (rect.right - 70, y), 'bodyb', (255, 220, 140), 'topright')


scenes.PICTURES['yearone'] = draw_yearone
