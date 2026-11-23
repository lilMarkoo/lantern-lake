"""Year two and beyond: a new neighbour, tougher festivals, and the Master Angler goal."""
import math

import pygame

import seasons
from data import FISH

MASTER_AT = 0.8              # Master Angler: every kind of fish at 80% of its biggest size or more
COTTAGE_X = 1651             # the cream cottage between the library and the lookout


def year(g):
    return seasons.year(g)


def flags(g):
    return g.story.setdefault('flags', [])


def master_fish():
    """Every fish that counts towards Master Angler: all of them except the four legends and the muskie."""
    return [f for f in FISH if f['rarity'] < 5 and not f.get('junk')]


def is_big(g, f):
    e = g.journal.get(f['id'])
    if not e:
        return False
    lo, hi = f['size']
    return e['best'] >= lo + (hi - lo) * MASTER_AT


def master_progress(g):
    fl = master_fish()
    return sum(1 for f in fl if is_big(g, f)), len(fl)


def festival_boost(g):
    """Rivals get better every year."""
    return 0.3 * min(year(g), 3)


def festival_prize(g, prize):
    return int(prize * (1 + 0.5 * min(year(g), 2)))


def rowan_here(g):
    return year(g) >= 1


# ---------------------------------------------------------------- the new year
NEW_YEAR = {
    1: ('Dear neighbour,',
        "Happy new year from all of Fernwick! A whole year at Lantern Lake already.\n\n"
        "Some news: the cream cottage by the lookout finally has someone in it. Rowan kept the lighthouse "
        "on the coast for forty years and has come inland to be near the water without all the salt. "
        "Do say hello.\n\n"
        "Also, fair warning: the festival crowd has been practising all winter. The prizes are bigger this "
        "year, and so are the fish. Old Tom swears he saw something new in the Deep on a moonlit night.",
        '- Mayor Hazel'),
}


def morning(g):
    """The first morning of a new year brings a letter."""
    y = year(g)
    if y < 1:
        return
    key = 'year%d' % y
    if key in flags(g):
        return
    flags(g).append(key)
    letter = NEW_YEAR.get(y) or ('Dear neighbour,',
                                 'Another year by the lake! The festivals will be fierce again. '
                                 'We are all very glad you are here.', '- Mayor Hazel')
    g.queue.append(('letter', letter))


# ---------------------------------------------------------------- meeting Rowan
def on_talk(g, k):
    """The first time you talk to Rowan there's a little scene."""
    if k != 'rowan' or 'met_rowan' in flags(g) or g.overlay is not None:
        return False
    import scenes
    flags(g).append('met_rowan')
    g.scene = scenes.Cutscene(g, meet_beats(g), 'town', title='A new neighbour')
    g.overlay = 'scene'
    g.release_holds()
    return True


def meet_beats(g):
    you, k = 'you', 'rowan'
    return [('walk', k, ('by', you, 14)), ('sync',), ('face', you, k), ('face', k, you),
            ('say', k, "Hello there! You'll be the one from the cabin by the lake. Hazel said you'd come by."),
            ('say', k, "Rowan. I kept the Gull Point lighthouse for forty years. Thought I'd retire somewhere "
                       "the water doesn't throw itself at the windows."),
            ('emote', you, 'note'),
            ('say', you, "Welcome to Fernwick! The lake's very calm. Mostly. There's a muskie that disagrees."),
            ('say', k, "Ha! Every bit of water has one of those. Out on the coast it was a crab the size of a "
                       "dinner plate. Called him the Admiral."),
            ('say', k, "I'll tell you a secret, since you fish. Burbot. Cold, deep, ugly as sin, and the best "
                       "supper there is. Bring me one some winter night and you'll have a friend for life."),
            ('emote', k, 'heart'),
            ('call', lambda g: g.add_friend('rowan', 6)),
            ('wait', 0.8)]


def heart_beats(g):
    you, k = 'you', 'rowan'
    return [('walk', k, ('by', you, 14)), ('sync',), ('face', you, k), ('face', k, you),
            ('say', k, "Walk with me to the lookout? I like to see the lake go dark. Old habits."),
            ('fade', 'You sit on the lookout bench with Rowan while the sun goes down over Lantern Lake.',
             {you: 1830, k: 1858}),
            ('face', you, k), ('face', k, you),
            ('say', k, "Forty years, every single night, I climbed a hundred and twelve steps and lit the lamp. "
                       "Never missed one. Not even the night of the great storm."),
            ('say', k, "When they put in the electric light, they let me keep the old lens. It's been sitting "
                       "in a crate since I moved."),
            ('picture', 'lens', 'The Gull Point lighthouse lens'),
            ('say', you, "It's beautiful. It's like a whole jar of rainbows."),
            ('say', k, "It wants a window and somebody to keep it company. You've got a cabin by the water. "
                       "I think it would be happy there."),
            ('emote', k, 'heart'),
            ('call', _give_lens),
            ('wait', 1.0)]


def _give_lens(g):
    h = g.home
    if 'lens' not in h['owned']:
        h['owned'].append('lens')
    g.toast("Rowan's lighthouse lens is in your cabin. Place it from the Home tab.", (220, 120, 140))
    g.audio.play('jingle3', 0.6)


def pic_lens(g, s, rect, t):
    """A brass lighthouse lens with glass rings that catch the light."""
    cx, cy = rect.centerx, rect.centery - 6
    pygame.draw.rect(s, (150, 110, 60), (cx - 70, cy + 70, 140, 18), border_radius=4)
    pygame.draw.rect(s, (120, 86, 46), (cx - 50, cy + 56, 100, 16))
    pygame.draw.circle(s, (180, 140, 70), (cx, cy), 74)
    for i in range(7, 0, -1):
        r = 10 * i
        k = (math.sin(t * 2 + i * 0.7) + 1) / 2
        col = (int(200 + 40 * k), int(220 + 30 * k), int(230 + 20 * k))
        pygame.draw.circle(s, col, (cx, cy), r)
        pygame.draw.circle(s, (160, 190, 210), (cx, cy), r, 2)
    pygame.draw.circle(s, (255, 250, 220), (cx, cy), 8)
    for a in range(0, 360, 45):
        ang = math.radians(a + t * 20)
        pygame.draw.line(s, (255, 244, 200), (cx + math.cos(ang) * 76, cy + math.sin(ang) * 76),
                         (cx + math.cos(ang) * 92, cy + math.sin(ang) * 92), 3)


def draw_cottage(s, g, sc, ground, t):
    """The cream cottage: a 'to let' sign in year one, a mailbox and a lamp once Rowan moves in."""
    x = int(COTTAGE_X - sc)
    if not -80 < x < s.get_width() + 80:
        return
    if not rowan_here(g):
        s.fill((120, 88, 60), (x + 30, ground - 22, 2, 18))
        s.fill((236, 226, 200), (x + 20, ground - 30, 22, 10))
        s.fill((150, 60, 50), (x + 22, ground - 27, 18, 1))
        s.fill((150, 60, 50), (x + 22, ground - 24, 12, 1))
        return
    s.fill((90, 70, 56), (x - 22, ground - 16, 2, 12))       # mailbox
    s.fill((60, 84, 120), (x - 25, ground - 22, 8, 6))
    s.fill((200, 60, 50), (x - 18, ground - 24, 1, 4))
    lit = g.env.nf > 0.3
    s.fill((60, 58, 64), (x - 3, ground - 50, 6, 2))         # a little ship's lantern by the door
    s.fill((255, 220, 140) if lit else (200, 190, 160), (x - 2, ground - 48, 4, 5))
    if lit and int(t * 3) % 5:
        s.set_at((x, ground - 50), (255, 250, 220))
    for i, col in enumerate(((230, 120, 120), (240, 200, 90), (130, 170, 220))):   # a window box
        s.fill(col, (x - 21 + i * 4, ground - 44, 3, 2))
