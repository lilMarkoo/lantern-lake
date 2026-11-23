"""First-day tips: a short, friendly walkthrough for a brand new game. Each tip goes away once you've done it."""
import pygame

import ui as U

STEPS = [
    ('cast', ['Hold', ('key', 'Space'), 'or', ('key', 'Click'), 'to wind up, then let go to cast.']),
    ('bite', ['When the bobber dips under for real,', ('key', 'Click'), 'to hook it!']),
    ('reel', ['Keep the fish in the gold arc and hold', ('key', 'Click'), 'to reel it in.']),
    ('sell', ['Sell your catch at the', ('key', 'S'), 'Shop, or keep the best for your tank.']),
    ('cat', ['Click Biscuit on the dock for a pet. It brings luck!']),
    ('town', ['Press', ('key', 'T'), 'to stroll up the lane to Fernwick village.']),
    ('rest', ['After 6 PM, press', ('key', 'Z'), 'to rest until morning. Sweet dreams!']),
]
DONE = len(STEPS)


def active(g):
    return (g.mode == 'play' and g.tut < DONE and g.settings.get('tutorial', True) and not g.net.online
            and (not g.tut_day or g.day <= g.tut_day or getattr(g, 'show_help', False)))


def relevant(g, sid=None):
    """Is the current tip worth showing right now? (selling with nothing to sell, resting at noon: not yet)"""
    if sid is None:
        if g.tut >= DONE:
            return False
        sid = STEPS[g.tut][0]
    if g.place != 'lake':
        return False
    if sid == 'sell':
        return bool(g.basket)
    if sid == 'rest':
        return g.minute >= 18 * 60
    if sid in ('cast', 'cat', 'town'):
        return g.fishing.state in ('idle', 'charging')
    return True


TIMEOUT = 40.0           # a tip that has been up this long moves on by itself


def _done(g, sid):
    f = g.fishing
    if sid == 'cast':
        return f.state in ('casting', 'waiting', 'bite', 'fight') or g.total > 0
    if sid == 'bite':
        return f.state == 'fight' or g.total > 0
    if sid == 'reel':
        return g.total > 0
    if sid == 'sell':
        return g.overlay == 'shop' or g.stats.get('sold', 0) > 0
    if sid == 'cat':
        return g.pet_day == g.day or g.cat_bond > 0
    if sid == 'town':
        return g.stats.get('town_visits', 0) > 0
    if sid == 'rest':
        return g.day > g.tut_day
    return True


def update(g, dt):
    if not active(g):
        return
    if not g.tut_day:
        g.tut_day = g.day
    sid = STEPS[g.tut][0]
    if not relevant(g, sid) and not _done(g, sid):
        return
    g.tut_t += dt
    if (_done(g, sid) and g.tut_t > 0.6) or g.tut_t > TIMEOUT:
        g.tut += 1
        g.tut_t = 0.0
        g.audio.play('chime2', 0.35)
        if g.tut >= DONE:
            g.toast("That's the basics! The rest of the lake is yours to find.", (110, 150, 100))


def skip(g):
    g.tut = DONE
    g.audio.play('ui', 0.5)


def draw(g, s):
    if not active(g) or g.overlay is not None or g.rest_phase is not None or g.hide_ui or not relevant(g):
        return
    ui = g.ui
    parts = STEPS[g.tut][1]
    w = ui.rich(s, parts, (0, 0), measure=True)
    pw = max(420, w + 44)
    left, right = 16 + 372 + 14, s.get_width() - 16 - 188 - 14     # between the clock card and the coins
    cx = (left + right) // 2
    a = min(1.0, g.tut_t * 3)
    r = pygame.Rect(cx - pw // 2, 12 - int((1 - a) * 20), pw, 64)
    ui.panel(s, r, radius=18)
    ui.blit_text(s, 'Tip %d of %d' % (g.tut + 1, DONE), (r.x + 18, r.y + 9), 'smallb', U.SOFT)
    for i in range(DONE):
        col = (226, 170, 80) if i < g.tut else (240, 200, 110) if i == g.tut else (220, 208, 190)
        pygame.draw.circle(s, col, (r.x + 128 + i * 14, r.y + 19), 4)
    ui.rich(s, parts, (r.x + 18, r.y + 44), U.INK, False)
    sk = pygame.Rect(r.right - 78, r.y + 6, 64, 24)
    ui.button(s, sk, 'Skip', lambda: skip(g), 'normal', font='small')
