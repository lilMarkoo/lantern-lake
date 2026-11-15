"""Legend hunts: one legendary fish a season, each with a tale, clues around town, a crafted lure and a
three-stage fight.

  Spring   Old Whiskers      told by Mabel       clues from Pip and Mayor Hazel
  Summer   Sunpetal Koi      told by Fen         clues from Juniper and Mabel
  Autumn   Mossback Muskie   told by Old Tom     clues from Mayor Hazel and Juniper
  Winter   Lake Spirit       told by Ms. Alder   clues from Fen and Pip

How a hunt goes:
  1. 'letter'  the season comes and the teller writes to you. Talk to them in Fernwick to hear the tale.
  2. 'clues'   two neighbours each know a piece of it. Talk to them.
  3. 'craft'   make the hunt's lure on the Legends page (press L): coins plus a few fish from your basket.
  4. 'hunt'    with the lure on your line, the legend bites at its own time and place, whatever the weather.
               If it gets away, your lure is safe and the legend comes back tomorrow.
  5. 'done'    a victory scene, a trophy, a keepsake that helps from then on. The lure can be made again any
               time for a rematch.
Legendary fish only ever bite on their own lure.

State: Game.hunts = {hunt id: {'stage': ..., 'clues': [folk ids], 'rest': day, 'day': day, 'size': cm}}
"""
import math

import pygame

import art
import scenes
import ui as U
from data import FISH_BY_ID, SEASONS, DAYS_PER_SEASON

STAGES = ('letter', 'clues', 'craft', 'hunt', 'done')

HUNTS = [
    dict(id='whiskers', fish='whiskers', season=0, teller='mabel', lure='lure_whiskers', lure_name='Honeycomb Bob',
         lure_desc="Mabel's honey-and-catfish bob. Old Whiskers can smell it across the lake.",
         coins=300, needs=[('catfish', 2), ('carp', 2)], reward=300,
         keepsake=("Whiskers' Bell", 'Night fish come a little more often.'),
         when='Night, at the very end of a long cast: off the dock or out in the Deep.',
         letter=('Dear angler,', (
             "The rain is back, and every spring rain my father used to stand at the bakery window and mutter "
             "about Old Whiskers. He swore that catfish stole his best hat in 1961. Come by the bakery and I'll "
             "tell you the whole silly story. There will be buns."), '- Mabel, Fernwick Bakery'),
         tale=[
             "Sit, sit. Have a bun. Now. Old Whiskers.",
             "My father was a baker, not a fisherman, but he loved that lake. One night he rowed out with a "
             "basket of honey buns and a borrowed rod.",
             "Something grabbed the line and pulled the whole boat in a circle. Three times! Then up came a face "
             "with whiskers like a walrus, and it took his hat right off his head.",
             "He drew it the next morning. He was a much better baker than an artist.",
             ("picture", 'sketch_whiskers', "Father's drawing, still pinned behind the ovens"),
             ("you", "It ate his hat?"),
             "Wore it, he said. Anyway. If anyone can catch that old thief, it's Rosie's grandchild. Ask Pip, "
             "that child sees everything. And Mayor Hazel keeps the town ledgers. Then come back to me for the "
             "honey."],
         clues={
             'pip': ("Old Whiskers? I SAW it! Only ever at night, way way out where your bobber is a tiny dot. Its "
                     "whiskers were longer than my arm. Okay, my arm is short. But still!",
                     'Pip: only at night, at the very end of a long cast.'),
             'hazel': ("Ah, the ledger. 1961: 'Baker's hat lost to catfish.' 1974: 'Whiskers taken briefly on a bob of "
                       "honey and catfish roe, line broke.' Two catfish and two carp for the roe, I'd say.",
                       'Hazel: a honey bob made with 2 catfish and 2 carp.')},
         fight=('Old Whiskers rolls into the mud!', 'It drags the line under the dock!', 'One last thrash! Hold on!'),
         win=("You caught HIM! Look at those whiskers! Father, if you can see this...",
              "I looked everywhere. No hat.",
              "Ha! He must have eaten it after all. Here, the bakery's whole jar of tips. You've earned every coin.")),
    dict(id='sunpetal', fish='sunpetal', season=1, teller='fen', lure='lure_sunpetal', lure_name='Dawnpetal Fly',
         lure_desc='A fly tied with sunfish scales and a koi fin. It flashes like a sunrise.',
         coins=450, needs=[('sunfish', 2), ('koi', 1)], reward=350,
         keepsake=('Sunpetal Scale', 'Fish run a little bigger.'),
         when='Dawn, very far out from the dock.',
         letter=('Hello!', (
             "Summer light is the best light. I'm painting the lake at sunrise every morning this week, and I keep "
             "seeing something gold under the water, just for a moment. Come to the lookout. I want to show you "
             "a painting nobody believes."), '- Fen'),
         tale=[
             "Every summer, the first clear sunrise, I sit here and paint. Same view. Different light.",
             "Six summers ago the lake turned gold for one breath. A koi the size of a cello rose and touched the "
             "surface. Then nothing. I painted it from memory before it faded.",
             ("picture", 'sketch_sunpetal', "Fen's painting: 'Sunrise, with Koi'"),
             "Everyone says it's a reflection. Reflections don't have fins.",
             ("you", "So it only comes up at dawn?"),
             "Only at dawn. Juniper at the aquarium knows koi better than anyone. And Mabel is up before the sun "
             "every day, baking. She might have seen it too."],
         clues={
             'juniper': ("Koi follow flashes of gold. In the old books, anglers tied flies from Honey Sunfish scales "
                         "and a real koi fin. Two sunfish and one koi should make a good fly!",
                         'Juniper: a fly of 2 Honey Sunfish and 1 Koi.'),
             'mabel': ("Oh, I've seen something! At dawn, when I open the bakery window, there's a glint way out on "
                       "the lake, far past where anyone casts. Gone by the time the buns are out.",
                       'Mabel: only at dawn, far out past the dock.')},
         fight=('A flash of gold! It circles wide!', 'It sweeps back and forth like a brushstroke!',
                'The sun is up. It gives everything it has!'),
         win=("It's real. It's REAL. Hold it up to the light... look at the colours. I'll never get them right.",
              "You'll have to paint it. You were the first one to see it.",
              "Then I will. And you get the first print, and the commission money. Thank you, truly.")),
    dict(id='muskie', fish='muskie', season=2, teller='tom', lure='lure_muskie', lure_name='Mossback Spoon',
         lure_desc="Tom's old spoon, polished up with salmon and cisco. It wobbles just like a wounded fish.",
         coins=600, needs=[('salmon', 1), ('cisco', 2)], reward=400,
         keepsake=("Tom's Lucky Spoon", 'Rare fish come a little more often.'),
         when='Dusk, in the Deep, at the very end of a long cast. You will need the rowboat.',
         letter=('Kid,', (
             "The leaves are turning. Forty-some autumns ago I lost the Mossback Muskie at the side of my boat. "
             "Every autumn since, I swear I can feel it out there, waiting. Come by the shop. I've got something "
             "for you, and a story you've only heard half of."), '- Old Tom'),
         tale=[
             "You've heard about the fight. You haven't heard about the spoon.",
             "I made a lure for it, the summer before. Polished brass spoon, wrapped in salmon skin and cisco "
             "scales. Had it on when I hooked the old devil.",
             ("picture", 'photo', 'Tom keeps this photo behind the counter'),
             "Snapped the line, took the hook, left me the spoon. It's been in a drawer forty years.",
             ("you", "Do you want me to try?"),
             "I want you to land it. My hands shake too much now. Ask Hazel what the ledgers say about where it "
             "feeds, and ask Juniper what it eats these days. Then fix up the spoon."],
         clues={
             'hazel': ("Every Muskie sighting in the ledger is in the Deep, at dusk, and always 'at the far end of "
                       "a cast'. You'll want the rowboat, and a strong arm.",
                       'Hazel: the Deep, at dusk, at the far end of a long cast. Take the rowboat.'),
             'juniper': ("Muskies are fussy! Ours in the old tank only ate fresh salmon and cisco. One salmon and two "
                         "cisco wrapped on a spoon should drive it wild.",
                         'Juniper: wrap the spoon with 1 Salmon and 2 Cisco.')},
         fight=('It runs for the deep water!', "It's thrashing at the surface! Watch the line!",
                'It won\'t give up. Neither will you!'),
         win=("Forty years. FORTY YEARS. Let me look at you, you old devil.",
              "It winked at me. I swear it winked.",
              "Ha! Then it knows it's been beaten fair. Take this, kid. And the spoon's yours now. For keeps.")),
    dict(id='spirit', fish='spirit', season=3, teller='librarian', lure='lure_spirit', lure_name='Starglass Lure',
         lure_desc='A sliver of glass that holds a little starlight. It glows the colour of the aurora.',
         coins=800, needs=[('aurora', 1), ('eel', 2)], reward=500,
         keepsake=('Spirit Lantern Glass', 'Every fish bites a little sooner.'),
         when='Night, at the very end of a long cast, with the Starlight Rod.',
         letter=('Dear angler,', (
             "Winter is when the archive tells its strangest stories. I have found three separate accounts of "
             "something called the Lake Spirit, written a hundred years apart, all describing the same thing. "
             "Please come to the library. I would like a second opinion, and a cup of tea."),
             '- Ms. Alder, Fernwick Library'),
         tale=[
             "Three accounts. 1823, 1921, and one in your grandmother's handwriting from 1974.",
             "All three describe a fish made of light, deep under the winter ice. All three say it can only be "
             "reached with a rod that holds starlight.",
             ("picture", 'sketch_spirit', "Rosie's notebook, page 41"),
             "Your grandmother wrote: 'Not caught. Met. It looked at me and the lake felt warmer.'",
             ("you", "Grandma saw it..."),
             "She did. The notes mention a lure of 'aurora and eel'. Fen paints the night sky; she'll know the "
             "aurora fish. And Pip has been sneaking down to the lake at night. Ask them both."],
         clues={
             'fen': ("The Aurora Fish? It glows green and pink, only on winter nights. If you catch one, wrap it with "
                     "two eels so the light lasts. That's what the old painters did for their lamps!",
                     'Fen: 1 Aurora Fish and 2 Eels for the glass.'),
             'pip': ("Don't tell Mum! I sneak out to look at the stars. Sometimes the lake glows, way out, right in the "
                     "middle of the night. Only when someone has a sparkly rod, I bet!",
                     'Pip: deep in the night, far out. It wants the Starlight Rod.')},
         fight=('The water lights up around the line!', 'It flickers left and right like a candle!',
                'The whole lake is glowing! Last stand!'),
         win=("Oh my. Oh, my dear. It's exactly as she described it.",
              "It's warm. Grandma was right. The lake feels warmer.",
              "Let it shine a moment, then let us write this down properly. A fourth account. Yours.")),
]
HUNT_BY_ID = {h['id']: h for h in HUNTS}
HUNT_BY_FISH = {h['fish']: h for h in HUNTS}
HUNT_BY_LURE = {h['lure']: h for h in HUNTS}
# each hunt's three stages: where on the reel track each one starts, and the checkpoint below it
STAGE_AT = (0.3, 0.53, 0.76)


def lure_baits():
    """Bait entries for data.BAITS: never sold, never used up by a bite."""
    return [dict(id=h['lure'], name=h['lure_name'], price=0, pack=0, merchant=True, legend=True,
                 desc=h['lure_desc']) for h in HUNTS]


def clean(st):
    out = {}
    if not isinstance(st, dict):
        return out
    for hid, v in st.items():
        if hid in HUNT_BY_ID and isinstance(v, dict) and v.get('stage') in STAGES:
            v = dict(v)
            v['clues'] = [k for k in v.get('clues', []) if k in HUNT_BY_ID[hid]['clues']] \
                if isinstance(v.get('clues'), list) else []
            out[hid] = v
    return out


def state(g, hid):
    return g.hunts.get(hid)


def stage(g, hid):
    st = g.hunts.get(hid)
    return st['stage'] if st else None


def folk_name(k):
    import town
    return town.FOLK[k]['name']


def fish_name(h):
    return FISH_BY_ID[h['fish']]['name']


def done_count(g):
    return sum(1 for h in HUNTS if (g.hunts.get(h['id']) or {}).get('day'))


# ---------------------------------------------------------------- perks from landed legends
def perk(g, kind):
    """Keepsakes from landed legends. 'size' adds; everything else multiplies."""
    landed = lambda hid: bool((g.hunts.get(hid) or {}).get('day'))
    if kind == 'size':
        return 0.04 if landed('sunpetal') else 0.0
    v = 1.0
    if kind == 'night' and landed('whiskers'):
        v *= 1.15
    elif kind == 'rare' and landed('muskie'):
        v *= 1.15
    elif kind == 'bite' and landed('spirit'):
        v *= 0.9
    return v


# ---------------------------------------------------------------- the flow
def morning(g):
    """A season's hunt opens with a letter from its teller (one new letter a morning at most)."""
    if not g.story.get('started') or g.day < 3:
        return
    year = (g.day - 1) // (DAYS_PER_SEASON * 4)
    season = g.season_of(g.day)
    for h in HUNTS:
        if h['id'] in g.hunts:
            continue
        if year == 0 and season < h['season']:
            break
        g.hunts[h['id']] = {'stage': 'letter', 'clues': []}
        g.queue.append(('letter', h['letter']))
        g.toast('A legend stirs: %s. (L to see the Legends page)' % fish_name(h), (228, 178, 40))
        break


def on_talk(g, k):
    """Talking to a hunt's teller after their letter plays the tale. True if a scene started."""
    for h in HUNTS:
        if h['teller'] == k and stage(g, h['id']) == 'letter' and g.overlay is None:
            start_tale(g, h)
            return True
    return False


def clue_line(g, k):
    """A neighbour who knows a piece of an open hunt says it instead of small talk."""
    for h in HUNTS:
        st = g.hunts.get(h['id'])
        if not st or st['stage'] != 'clues' or k not in h['clues'] or k in st['clues']:
            continue
        st['clues'].append(k)
        line = h['clues'][k][0]
        if all(c in st['clues'] for c in h['clues']):
            st['stage'] = 'craft'
            g.toast('You know enough to make the %s. Open the Legends page (L).' % h['lure_name'], (228, 178, 40))
        else:
            g.toast('Clue noted on the Legends page.', (228, 178, 40))
        g.audio.play('jingle1', 0.5)
        g.save()
        return line
    return None


def tale_beats(h):
    k = h['teller']
    you = 'you'
    beats = [('walk', k, ('by', you, 14)), ('sync',), ('face', you, k), ('face', k, you)]
    for ln in h['tale']:
        if isinstance(ln, tuple) and ln[0] == 'picture':
            beats.append(('picture', ln[1], ln[2]))
        elif isinstance(ln, tuple):
            beats.append(('say', ln[0], ln[1]))
        else:
            beats.append(('say', k, ln))
    beats += [('emote', k, 'fish'), ('call', lambda g, hid=h['id']: _after_tale(g, hid)), ('wait', 0.8)]
    return beats


def _after_tale(g, hid):
    st = g.hunts.get(hid)
    if st and st['stage'] == 'letter':
        st['stage'] = 'clues'
        h = HUNT_BY_ID[hid]
        who = ' and '.join(folk_name(c) for c in h['clues'])
        g.toast('Ask %s about %s.' % (who, fish_name(h)), (228, 178, 40))


def start_tale(g, h):
    g.scene = scenes.Cutscene(g, tale_beats(h), 'town', title='Legend of the %s' % fish_name(h))
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('wish', 0.5)


def missing(g, h):
    """[(fish id, have, need)] for the lure recipe, counting the basket."""
    out = []
    for fid, n in h['needs']:
        have = sum(1 for b in g.basket if b['id'] == fid)
        out.append((fid, have, n))
    return out


def can_craft(g, h):
    st = g.hunts.get(h['id'])
    if not st or st['stage'] not in ('craft', 'done'):
        return False
    if g.baits.get(h['lure'], 0) > 0 or g.coins < h['coins']:
        return False
    return all(have >= n for _, have, n in missing(g, h))


def craft(g, h):
    if not can_craft(g, h):
        return False
    for fid, n in h['needs']:
        for _ in range(n):
            item = min((b for b in g.basket if b['id'] == fid), key=lambda b: b['price'])
            g.basket.remove(item)
    g.coins -= h['coins']
    g.baits[h['lure']] = 1
    g.bait = h['lure']
    st = g.hunts[h['id']]
    if st['stage'] == 'craft':
        st['stage'] = 'hunt'
    g.stats['lures'] = g.stats.get('lures', 0) + 1
    g.audio.play('jingle3', 0.7)
    g.toast('You made the %s and tied it on. %s' % (h['lure_name'], h['when']), (228, 178, 40))
    g.save()
    return True


def equip(g, h):
    if g.baits.get(h['lure'], 0) > 0:
        g.bait = h['lure']
        g.audio.play('ui', 0.5)


def can_bite(g, fid):
    """Legends only bite on their own lure, and not again on a day they got away."""
    h = HUNT_BY_FISH.get(fid)
    if not h:
        return False
    st = g.hunts.get(h['id'])
    if not st or st['stage'] not in ('hunt', 'done'):
        return False
    return g.bait == h['lure'] and g.baits.get(h['lure'], 0) > 0 and st.get('rest') != g.day


def fight_lines(fid):
    h = HUNT_BY_FISH.get(fid)
    return h['fight'] if h else ('It fights!', 'It fights harder!', 'Last stand!')


def on_escape(g, fid):
    h = HUNT_BY_FISH.get(fid)
    if not h:
        return None
    st = g.hunts.get(h['id'])
    if st:
        st['rest'] = g.day
    g.save()
    return '%s got away! Your lure is safe. It will be back tomorrow.' % fish_name(h)


def on_catch(g, spec, size):
    """Called for every catch: a legend landed on its lure ends (or replays) its hunt."""
    h = HUNT_BY_FISH.get(spec['id'])
    if not h or g.bait != h['lure']:
        return
    g.baits[h['lure']] = 0
    g.bait = 'worm'
    st = g.hunts.setdefault(h['id'], {'stage': 'done', 'clues': list(h['clues'])})
    first = not st.get('day')
    st['stage'] = 'done'
    st['size'] = max(size, st.get('size', 0))
    if first:
        st['day'] = g.day
        g.queue.append(('scene', lambda g, hid=h['id']: start_victory(g, hid)))
    else:
        g.toast('%s again! Fernwick will be talking about this for weeks.' % fish_name(h), (228, 178, 40))


def victory_beats(g, h):
    k = h['teller']
    st = g.hunts[h['id']]
    w1, w2, w3 = h['win']
    beats = [('fade', 'Word travels fast. By sundown, half of Fernwick is crowded onto your little dock.'),
             ('say', k, w1),
             ('picture', 'trophy_' + h['id'], '%s  -  %.1f cm' % (fish_name(h), st.get('size', 0))),
             ('say', 'you', w2),
             ('say', k, w3),
             ('call', lambda g, hid=h['id']: _reward(g, hid)),
             ('wait', 1.0)]
    if done_count(g) == len(HUNTS):
        beats[-1:-1] = [('say', 'librarian', "All four legends of Lantern Lake, landed by one angler. I shall need "
                                             "a new shelf in the archive."),
                        ('say', 'you', "And a bigger wall in the cabin.")]
    return beats


def _reward(g, hid):
    h = HUNT_BY_ID[hid]
    st = g.hunts[hid]
    if st.get('rewarded'):
        return
    st['rewarded'] = True
    g.coins += h['reward']
    g.add_friend(h['teller'], 10)
    name = '%s, landed on day %d' % (fish_name(h), st.get('day', g.day))
    if name not in g.trophies:
        g.trophies.append(name)
    g.audio.play('jingle5', 0.7)
    g.toast('%d coins and a keepsake: %s. %s' % (h['reward'], h['keepsake'][0], h['keepsake'][1]), (228, 178, 40))
    if done_count(g) == len(HUNTS) and 'Legend of Lantern Lake' not in g.trophies:
        g.trophies.append('Legend of Lantern Lake')
        g.toast('All four legends landed! You are a Legend of Lantern Lake.', (228, 178, 40))
    g.check_badges()


def start_victory(g, hid):
    h = HUNT_BY_ID[hid]
    g.scene = scenes.Cutscene(g, victory_beats(g, h), 'lake', title='Legend landed')
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('wish', 0.7)


def hud_line(g):
    """One line for the left-hand card about the most urgent hunt."""
    for h in HUNTS:
        st = g.hunts.get(h['id'])
        if not st or st['stage'] == 'done':
            continue
        s = st['stage']
        if s == 'letter':
            return 'Legend: visit %s in Fernwick' % folk_name(h['teller'])
        if s == 'clues':
            left = [folk_name(c) for c in h['clues'] if c not in st['clues']]
            return 'Legend: ask %s' % ' and '.join(left)
        if s == 'craft':
            return 'Legend: make the %s (L)' % h['lure_name']
        if s == 'hunt':
            if g.baits.get(h['lure'], 0) <= 0:
                continue
            if st.get('rest') == g.day:
                return '%s is resting today' % fish_name(h)
            return 'Legend: %s on the line' % h['lure_name'] if g.bait == h['lure'] else \
                'Legend: tie on the %s (Tab)' % h['lure_name']
    return None


# ---------------------------------------------------------------- the Legends page (a tab on the L panel)
def draw_page(g, s, rect):
    ui = g.ui
    gap = 18
    cw = (rect.w - 60 - gap) // 2
    ch = (rect.h - 140 - 24 - gap) // 2
    year = (g.day - 1) // (DAYS_PER_SEASON * 4)
    for i, h in enumerate(HUNTS):
        col, row = i % 2, i // 2
        r = pygame.Rect(rect.x + 30 + col * (cw + gap), rect.y + 140 + row * (ch + gap), cw, ch)
        st = g.hunts.get(h['id'])
        done = bool(st and st.get('day'))
        ui.tile(s, r, (252, 242, 214) if done else (250, 244, 228) if st else (232, 226, 214),
                (228, 178, 40) if done else (196, 170, 140))
        spec = FISH_BY_ID[h['fish']]
        icon = _fish_icon(spec, done or bool(st))
        s.blit(icon, icon.get_rect(center=(r.x + 70, r.y + 52)))
        ui.blit_text(s, fish_name(h), (r.x + 140, r.y + 12), 'bodyb', U.INK, maxw=r.w - 250)
        ui.blit_text(s, SEASONS[h['season']], (r.right - 16, r.y + 14), 'small', U.SOFT, 'topright')
        ui.blit_text(s, 'Told by %s' % folk_name(h['teller']), (r.x + 140, r.y + 42), 'small', U.SOFT)
        x, y, w = r.x + 18, r.y + 98, r.w - 36
        if not st:
            when = 'Its season comes in %s.' % SEASONS[h['season']] if year == 0 else 'Soon...'
            _para(ui, s, when, x, y, w, U.SOFT)
            continue
        stg = st['stage']
        if done:
            _para(ui, s, 'Landed on day %d. Best: %.1f cm.' % (st['day'], st.get('size', 0)), x, y, w,
                  (170, 110, 60), 'smallb')
            _para(ui, s, 'Keepsake: %s. %s' % h['keepsake'], x, y + 26, w, U.INK)
            if g.baits.get(h['lure'], 0) > 0:
                _equip_button(g, s, r, h)
            else:
                _craft_row(g, s, r, h, 'Rematch')
            continue
        if stg == 'letter':
            _para(ui, s, 'Visit %s in Fernwick to hear the tale.' % folk_name(h['teller']), x, y, w, U.INK)
            continue
        if stg == 'hunt':
            _para(ui, s, 'Lure: %s' % h['lure_name'], x, y, w, (170, 110, 60), 'smallb')
            _para(ui, s, h['when'], x, y + 26, w, U.INK)
            if st.get('rest') == g.day:
                _para(ui, s, 'It got away today. Back tomorrow.', x, r.bottom - 50, w - 170, U.ROSE)
            _equip_button(g, s, r, h)
            continue
        # clues heard so far
        for c in h['clues']:
            got = c in st['clues']
            text = h['clues'][c][1] if got else 'Ask %s.' % folk_name(c)
            y = _para(ui, s, text, x + 22, y, w - 22, U.INK if got else U.SOFT, check=got)
        if stg == 'craft':
            _craft_row(g, s, r, h, 'Make it')


def _para(ui, s, text, x, y, w, col, font='small', check=None):
    if check is not None:
        pygame.draw.rect(s, (120, 170, 110) if check else (200, 180, 160), (x - 22, y + 3, 15, 15), border_radius=4)
        if check:
            pygame.draw.lines(s, (255, 255, 255), False, [(x - 19, y + 11), (x - 15, y + 15), (x - 10, y + 6)], 2)
    for ln in ui.wrap(text, font, w)[:3]:
        ui.blit_text(s, ln, (x, y), font, col)
        y += 22
    return y + 4


def _craft_row(g, s, r, h, label):
    ui = g.ui
    x, y = r.x + 18, r.bottom - 54
    U.coin(s, (x + 8, y + 20), 9)
    ui.blit_text(s, str(h['coins']), (x + 22, y + 20), 'smallb', U.INK if g.coins >= h['coins'] else U.ROSE,
                 'midleft')
    x += 70
    for fid, have, n in missing(g, h):
        spr = art.fish_sprite(FISH_BY_ID[fid], 1)
        s.blit(spr, spr.get_rect(midleft=(x, y + 20)))
        x += spr.get_width() + 6
        ui.blit_text(s, '%d/%d' % (min(have, n), n), (x, y + 20), 'smallb', U.INK if have >= n else U.ROSE,
                     'midleft')
        x += 44
    ok = can_craft(g, h)
    ui.button(s, (r.right - 156, y, 140, 40), label, lambda: craft(g, h), 'gold', font='small', enabled=ok)


def _equip_button(g, s, r, h):
    ui = g.ui
    if g.bait == h['lure']:
        ui.button(s, (r.right - 156, r.bottom - 54, 140, 40), 'On the line', None, font='small', enabled=False)
    else:
        ui.button(s, (r.right - 156, r.bottom - 54, 140, 40), 'Tie it on', lambda: equip(g, h), 'primary',
                  font='small')


_icons = {}


def _fish_icon(spec, known):
    key = (spec['id'], known)
    if key not in _icons:
        spr = art.fish_sprite(spec, 2)
        if spr.get_width() > 110:
            k = 110 / spr.get_width()
            spr = pygame.transform.smoothscale(spr, (110, max(1, int(spr.get_height() * k))))
        if not known:
            spr = spr.copy()
            spr.fill((60, 52, 48, 255), special_flags=pygame.BLEND_RGBA_MIN)
        _icons[key] = spr
    return _icons[key]


# ---------------------------------------------------------------- lure icons (art.item_icon asks here)
def lure_icon(lid):
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    d = pygame.draw
    hook = (190, 190, 200)
    if lid == 'lure_whiskers':                       # a honeycomb bob
        d.circle(s, (150, 100, 40), (7, 8), 5)
        d.circle(s, (240, 190, 70), (7, 8), 4)
        for p in ((5, 6), (8, 6), (6, 9), (9, 9)):
            s.set_at(p, (200, 140, 40))
        s.set_at((6, 6), (255, 245, 200))
    elif lid == 'lure_sunpetal':                     # a petal fly
        for a in range(5):
            x = 7 + int(math.cos(a * 1.26) * 3)
            y = 8 + int(math.sin(a * 1.26) * 3)
            d.circle(s, (250, 170, 110) if a % 2 else (255, 214, 120), (x, y), 2)
        d.circle(s, (255, 246, 200), (7, 8), 1)
    elif lid == 'lure_muskie':                       # a mossy spoon
        d.ellipse(s, (90, 110, 70), (3, 3, 8, 11))
        d.ellipse(s, (200, 200, 170), (4, 4, 6, 9))
        d.line(s, (140, 160, 110), (5, 7), (8, 11))
        s.set_at((6, 5), (255, 255, 240))
    else:                                            # starglass
        pts = [(7 + math.cos(a * math.pi / 4) * (6 if a % 2 == 0 else 2.5),
                8 + math.sin(a * math.pi / 4) * (6 if a % 2 == 0 else 2.5)) for a in range(8)]
        d.polygon(s, (170, 220, 250), pts)
        d.polygon(s, (240, 252, 255), pts, 1)
        s.set_at((7, 8), (255, 255, 255))
    d.line(s, hook, (12, 8), (14, 8))
    d.arc(s, hook, (11, 8, 5, 6), 3.1, 6.3)
    return s


# ---------------------------------------------------------------- pictures for the scenes
def _sepia(c):
    return (min(255, int(c * 1.05) + 40), int(c * 0.9) + 30, int(c * 0.7) + 20)


def _sketch(g, s, rect, t, fid):
    """An old drawing or painting of the legend on paper."""
    spec = FISH_BY_ID[fid]
    if fid == 'sunpetal':                          # Fen's painting: a sunrise in colour
        for i in range(rect.h):
            k = i / rect.h
            s.fill(art.lerp_c((255, 214, 150), (90, 120, 150), min(1, k * 1.4)), (rect.x, rect.y + i, rect.w, 1))
        pygame.draw.circle(s, (255, 236, 170), (rect.centerx, rect.y + 150), 46)
        s.fill((70, 100, 130), (rect.x, rect.y + 170, rect.w, rect.h - 170))
        for i in range(10):
            y = rect.y + 180 + i * 16
            pygame.draw.line(s, (255, 214, 140), (rect.centerx - 80 + i * 4, y), (rect.centerx + 80 - i * 4, y), 2)
        spr = art.fish_sprite(spec, 5)
        spr = pygame.transform.rotate(spr, 12)
        s.blit(spr, spr.get_rect(center=(rect.centerx + 10, rect.y + 236)))
        return
    for i in range(rect.h):
        s.fill(_sepia(220 - int(i / rect.h * 40)), (rect.x, rect.y + i, rect.w, 1))
    spr = art.fish_sprite(spec, 5)
    if spr.get_width() > rect.w - 80:
        k = (rect.w - 80) / spr.get_width()
        spr = pygame.transform.scale(spr, (int(spr.get_width() * k), int(spr.get_height() * k)))
    ink = spr.copy()
    ink.fill((120, 90, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(ink, ink.get_rect(center=(rect.centerx, rect.centery - 10)))
    col = _sepia(70)
    for i in range(5):                               # handwriting
        y = rect.bottom - 70 + (i // 2) * 20
        x0 = rect.x + 40 + (i % 2) * 240
        for j in range(9):
            pygame.draw.line(s, col, (x0 + j * 22, y + (j % 3)), (x0 + j * 22 + 14, y + 2 - (j % 2)), 1)
    if fid == 'whiskers':                            # the stolen hat, of course
        pygame.draw.ellipse(s, _sepia(60), (rect.centerx - 30, rect.y + 60, 60, 16), 2)
        pygame.draw.rect(s, _sepia(60), (rect.centerx - 16, rect.y + 40, 32, 24), 2)
        g.ui.blit_text(s, 'the thief!', (rect.centerx + 60, rect.y + 46), 'small', col)
    elif fid == 'spirit':
        for i in range(30):
            a = t * 0.6 + i
            x = rect.centerx + math.cos(a) * (120 + i * 3)
            y = rect.centery - 10 + math.sin(a * 1.3) * (60 + i)
            if rect.collidepoint(x, y):
                s.fill((255, 250, 220), (int(x), int(y), 2, 2))


def _trophy(g, s, rect, t, fid):
    """The legend mounted on a board with a brass plate."""
    spec = FISH_BY_ID[fid]
    st = g.hunts.get(HUNT_BY_FISH[fid]['id'], {})
    for i in range(rect.h):
        s.fill(art.lerp_c((96, 64, 44), (70, 46, 34), i / rect.h), (rect.x, rect.y + i, rect.w, 1))
    for i in range(0, rect.h, 22):
        pygame.draw.line(s, (84, 56, 40), (rect.x, rect.y + i), (rect.right, rect.y + i + 6), 1)
    board = pygame.Rect(0, 0, rect.w - 80, rect.h - 110)
    board.center = (rect.centerx, rect.centery - 24)
    pygame.draw.ellipse(s, (60, 40, 28), board.move(0, 6))
    pygame.draw.ellipse(s, (150, 104, 64), board)
    pygame.draw.ellipse(s, (196, 146, 90), board, 4)
    glow = spec.get('glow') or (255, 230, 160)
    k = 0.5 + 0.5 * math.sin(t * 2)
    halo = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*glow, int(40 + 30 * k)), halo.get_rect().inflate(-30, -30))
    s.blit(halo, board)
    spr = art.fish_sprite(spec, 5)
    if spr.get_width() > board.w - 40:
        sc = (board.w - 40) / spr.get_width()
        spr = pygame.transform.scale(spr, (int(spr.get_width() * sc), int(spr.get_height() * sc)))
    s.blit(spr, spr.get_rect(center=board.center))
    for i in range(6):                               # a few glints
        a = t * 1.5 + i * 1.05
        x = board.centerx + math.cos(a) * board.w * 0.42
        y = board.centery + math.sin(a) * board.h * 0.4
        U.star(s, (int(x), int(y)), 4 + int(2 * math.sin(t * 5 + i)), (255, 240, 180))
    plate = pygame.Rect(0, 0, 300, 46)
    plate.midbottom = (rect.centerx, rect.bottom - 16)
    pygame.draw.rect(s, (120, 90, 40), plate.inflate(6, 6), border_radius=6)
    pygame.draw.rect(s, (226, 190, 100), plate, border_radius=5)
    g.ui.blit_text(s, spec['name'].upper(), (plate.centerx, plate.y + 14), 'smallb', (90, 60, 30), 'center')
    g.ui.blit_text(s, 'Lantern Lake, day %d' % st.get('day', g.day), (plate.centerx, plate.y + 33), 'tiny',
                   (110, 80, 40), 'center')


def _register_lures():
    import data
    for b in lure_baits():
        if b['id'] not in data.BAIT_BY_ID:
            data.BAITS.append(b)
            data.BAIT_BY_ID[b['id']] = b


_register_lures()
for _h in HUNTS:
    scenes.PICTURES['sketch_' + _h['fish']] = (lambda f: lambda g, s, rect, t: _sketch(g, s, rect, t, f))(_h['fish'])
    scenes.PICTURES['trophy_' + _h['id']] = (lambda f: lambda g, s, rect, t: _trophy(g, s, rect, t, f))(_h['fish'])
