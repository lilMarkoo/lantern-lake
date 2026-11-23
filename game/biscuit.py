"""Biscuit, the cabin cat: her bond with you, the tricks she learns, morning presents and walks to Fernwick."""
import math
import random

import pygame

import actors
import art
import ui as U
from data import FISH_BY_ID, BAIT_BY_ID

# bond points needed for each heart (0..5)
LEVELS = (0, 12, 28, 48, 70, 92)
MAX_BOND = 100
TRICKS = [
    (1, 'paw', 'High five', 'She lifts a paw to meet your hand.'),
    (2, 'roll', 'Roll over', 'Over she goes, belly to the sky.'),
    (3, 'spin', 'Tail chase', 'Round and round after her own tail.'),
    (4, 'beg', 'Sit pretty', 'Up on her back paws, very proud.'),
    (5, 'flip', 'Backflip', 'A whole backflip. Nobody taught her this.'),
]
TRICK_BY_ID = {t[1]: t for t in TRICKS}
# what raises the bond, once each a day
GAINS = {'pet': 2, 'treat': 4, 'play': 3, 'walk': 1, 'nip': 4}
TODAY = [('pet', 'A pet on the dock'), ('treat', 'A fishy treat'), ('play', 'Playtime with a toy'),
         ('walk', 'A walk to Fernwick')]
TOYS = ('yarn', 'scratcher', 'toybox')      # from the cabin catalogue (home.py)
FOLLOW_LEVEL = 2
GIFT_FISH = ('minnow', 'bluegill', 'perch', 'loach', 'sunfish', 'crayfish', 'shiner')
HEART_LINES = {
    1: 'Biscuit headbutts your hand. She learned a High five!',
    2: 'Biscuit follows you everywhere now. She can walk with you to Fernwick, and she learned to Roll over!',
    3: 'Biscuit purrs the moment you sit down. New trick: Tail chase!',
    4: 'Biscuit brings you presents more often now. New trick: Sit pretty!',
    5: 'Biscuit is your best friend in the whole world. She learned a Backflip!',
}


def clean(g):
    try:
        g.cat_bond = max(0, min(MAX_BOND, int(g.cat_bond)))
    except (TypeError, ValueError):
        g.cat_bond = 0
    if not isinstance(g.cat_day, dict):
        g.cat_day = {}
    g.cat_day = {k: v for k, v in g.cat_day.items() if k in GAINS and isinstance(v, int)}
    gift = g.cat_gift
    if not (isinstance(gift, dict) and gift.get('kind') in ('fish', 'coins', 'bait', 'luck')):
        g.cat_gift = None
    elif gift['kind'] == 'fish' and gift.get('id') not in FISH_BY_ID:
        g.cat_gift = None
    elif gift['kind'] == 'bait' and gift.get('id') not in BAIT_BY_ID:
        g.cat_gift = None
    g.cat_follow = bool(g.cat_follow)


def level(g):
    return sum(1 for v in LEVELS[1:] if g.cat_bond >= v)


def progress(g):
    """How far along the way to the next heart (0..1), or 1 at full bond."""
    lv = level(g)
    if lv >= 5:
        return 1.0
    lo, hi = LEVELS[lv], LEVELS[lv + 1]
    return (g.cat_bond - lo) / (hi - lo)


def tricks(g):
    lv = level(g)
    return [t for t in TRICKS if t[0] <= lv]


def done_today(g, what):
    return g.cat_day.get(what) == g.day


def gain(g, what):
    """Bond for one of the day's little things. Returns True the first time today."""
    if done_today(g, what):
        return False
    g.cat_day[what] = g.day
    before = level(g)
    g.cat_bond = min(MAX_BOND, g.cat_bond + GAINS[what])
    after = level(g)
    if after > before:
        g.toast(HEART_LINES[after], (200, 130, 80))
        g.audio.play('jingle3', 0.5)
        g.stats['cat_hearts'] = after
        if after >= FOLLOW_LEVEL and before < FOLLOW_LEVEL:
            g.cat_follow = True
        if g.place == 'lake':
            g.world.hearts(actors.CAT_X + 3, actors.DECK_Y - 18, 6)
        g.save()
    return True


def follows(g):
    return g.cat_follow and level(g) >= FOLLOW_LEVEL


# ---------------------------------------------------------------- things you do with her
def on_pet(g):
    """Called when you pet her. Presents first, then bond or a trick."""
    if g.cat_gift:
        collect(g)
        return
    if not gain(g, 'pet') and tricks(g):
        do_trick(g)


def do_trick(g, tid=None, rng=random):
    known = tricks(g)
    if not known:
        g.toast('Biscuit blinks at you slowly. Maybe when you know each other better.', (160, 140, 120))
        return
    tr = TRICK_BY_ID[tid] if tid else rng.choice(known)
    g.cat['trick'] = [tr[1], actors.TRICK_TIME]
    g.cat['sleep'] = False
    g.cat['pet'] = 0
    g.stats['tricks'] = g.stats.get('tricks', 0) + 1
    g.audio.play('chime3', 0.45)
    g.toast('%s! %s' % (tr[2], tr[3]), (200, 130, 80))


def treat_fish(g):
    """The smallest, cheapest fish in the basket, which is what a cat would pick anyway."""
    fish = [b for b in g.basket if b['id'] in FISH_BY_ID]          # not the old boots
    if not fish:
        return None
    return min(fish, key=lambda b: (b['price'], b['size']))


def give_treat(g):
    if done_today(g, 'treat'):
        g.toast('Biscuit has had her treat today. Look at that round tummy.', (160, 140, 120))
        return False
    b = treat_fish(g)
    if b is None:
        g.toast('Nothing in your basket for Biscuit yet. Catch her a little fish!', (160, 140, 120))
        return False
    g.basket.remove(b)
    gain(g, 'treat')
    g.cat['excited'] = 1.6
    g.audio.play('purr', 0.9)
    g.toast('Biscuit gobbles up the %s and purrs like a little engine.' % FISH_BY_ID[b['id']]['name'],
            (200, 130, 80))
    return True


def toys(g):
    home = getattr(g, 'home', None) or {}
    return [t for t in TOYS if t in home.get('owned', ())]


def play(g):
    if not toys(g):
        g.toast('Biscuit needs a toy first: look in the Home catalogue in your cabin.', (160, 140, 120))
        return False
    first = gain(g, 'play')
    g.cat['excited'] = 2.5
    g.cat['sleep'] = False
    g.cat['trick'] = ['spin', actors.TRICK_TIME]
    g.audio.play('purr', 0.7)
    if first:
        g.toast('You wiggle the %s and Biscuit pounces. Best game ever.'
                % {'yarn': 'yarn', 'scratcher': 'scratching post', 'toybox': 'feather wand'}[toys(g)[0]],
                (200, 130, 80))
    else:
        g.toast('Biscuit is happily worn out from playing today.', (160, 140, 120))
    return first


def on_town(g):
    """Arriving in Fernwick: if she comes along, that's her walk for the day."""
    if follows(g):
        gain(g, 'walk')


def update(g, dt):
    tr = g.cat.get('trick')
    if tr:
        tr[1] -= dt
        if tr[1] <= 0:
            g.cat['trick'] = None


# ---------------------------------------------------------------- morning presents
def morning(g, rng=random):
    """Sometimes she leaves a present by the door. Better friends, more presents."""
    if g.cat_gift:
        return
    lv = level(g)
    if rng.random() >= 0.08 + 0.07 * lv:
        return
    kinds = ['fish'] * 4 + ['coins'] * 3 + ['bait'] * 2 + (['luck'] * 2 if lv >= 3 else [])
    kind = rng.choice(kinds)
    if kind == 'fish':
        ids = [i for i in GIFT_FISH if i in FISH_BY_ID]
        g.cat_gift = dict(kind='fish', id=rng.choice(ids), n=1)
    elif kind == 'coins':
        g.cat_gift = dict(kind='coins', id='coins', n=int(rng.randint(8, 30) * (1 + 0.3 * lv)))
    elif kind == 'bait':
        b = rng.choice(('corn', 'corn', 'glow'))
        g.cat_gift = dict(kind='bait', id=b, n=rng.randint(2, 4))
    else:
        g.cat_gift = dict(kind='luck', id='clover', n=1)


def gift_text(gift):
    k = gift['kind']
    if k == 'fish':
        return 'a %s (still wriggling)' % FISH_BY_ID[gift['id']]['name']
    if k == 'coins':
        return '%d coins she dug up somewhere' % gift['n']
    if k == 'bait':
        return '%d %s she found who knows where' % (gift['n'], BAIT_BY_ID[gift['id']]['name'])
    return 'a four-leaf clover. You feel very lucky today!'


def collect(g, rng=random):
    gift = g.cat_gift
    if not gift:
        return None
    import seasons
    k = gift['kind']
    if k == 'fish':
        spec = FISH_BY_ID[gift['id']]
        seasons.bank_catch(g, spec, seasons.rand_size(spec, rng))
    elif k == 'coins':
        g.coins += gift['n']
        g.audio.play('coin', 0.7)
    elif k == 'bait':
        g.baits[gift['id']] = g.baits.get(gift['id'], 0) + gift['n']
    else:
        g.luck = min(3.0, g.luck + 1.5)
    g.cat_gift = None
    g.stats['cat_gifts'] = g.stats.get('cat_gifts', 0) + 1
    g.cat['excited'] = 1.5
    g.audio.play('purr', 0.8)
    g.toast('Biscuit brought you %s!' % gift_text(gift), (200, 130, 80))
    return gift


def gift_rect():
    return pygame.Rect(actors.CAT_X + 7, actors.DECK_Y - 9, 14, 10)


def draw_gift(s, g, t):
    """The present on the dock boards next to her."""
    gift = g.cat_gift
    if not gift or g.place != 'lake':
        return
    x, y = actors.CAT_X + 14, actors.DECK_Y
    k = gift['kind']
    if k == 'fish':
        spr = art.fish_sprite(FISH_BY_ID[gift['id']])
        spr = pygame.transform.scale(spr, (spr.get_width() // 4, spr.get_height() // 4))
        s.blit(spr, spr.get_rect(midbottom=(x, y)))
    elif k == 'coins':
        for i, (dx, dy) in enumerate(((-2, 0), (2, 0), (0, -2))):
            pygame.draw.circle(s, (240, 196, 70), (x + dx, y - 2 + dy), 2)
            s.set_at((x + dx, y - 3 + dy), (255, 240, 170))
    elif k == 'bait':
        s.fill((236, 210, 90) if gift['id'] == 'corn' else (150, 230, 200), (x - 3, y - 4, 6, 4))
        s.fill((120, 90, 60), (x - 3, y - 4, 6, 1))
    else:
        c = (80, 170, 90)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            pygame.draw.circle(s, c, (x + dx, y - 4 + dy), 1)
        pygame.draw.line(s, (60, 130, 70), (x, y - 3), (x + 1, y))
    if int(t * 2) % 2:
        s.set_at((x + 3, y - 7), (255, 255, 230))


def hud_line(g):
    if g.cat_gift and g.place == 'lake':
        return 'Biscuit left you a present: pet her'
    return None


# ---------------------------------------------------------------- the Biscuit tab in the cabin
def portrait(g, t, sleep=None):
    surf = pygame.Surface((60, 46), pygame.SRCALPHA)
    actors.draw_cat(surf, g, t, 30, 40, bed=False, sleep=sleep, look=0)
    return surf


def draw_tab(g, s, rect):
    ui = g.ui
    t = g.t
    pv = pygame.Rect(rect.x + 40, rect.y + 96, 340, 280)
    pygame.draw.rect(s, (120, 80, 54), pv.inflate(16, 16), border_radius=14)
    sky = art.lerp_c((236, 222, 196), (70, 76, 110), g.env.nf)
    pygame.draw.rect(s, sky, pv, border_radius=10)
    pygame.draw.rect(s, art.lerp_c((190, 150, 110), (90, 70, 70), g.env.nf * 0.6),
                     (pv.x, pv.bottom - 60, pv.w, 60), border_bottom_left_radius=10, border_bottom_right_radius=10)
    pygame.draw.ellipse(s, (170, 60, 64), (pv.centerx - 92, pv.bottom - 86, 184, 44))
    pygame.draw.ellipse(s, (210, 96, 92), (pv.centerx - 82, pv.bottom - 92, 164, 36))
    sleep = g.cat['sleep'] and not g.cat.get('trick')
    img = pygame.transform.scale(portrait(g, t, sleep), (300, 230))
    s.blit(img, img.get_rect(midbottom=(pv.centerx, pv.bottom - 40)))
    pygame.draw.rect(s, (150, 104, 70), pv.inflate(8, 8), 3, border_radius=12)
    lv = level(g)
    ui.blit_text(s, 'Biscuit', (pv.centerx, pv.bottom + 20), 'h3', U.INK, 'midtop')
    for i in range(5):
        cx, cy = pv.centerx - 72 + i * 36, pv.bottom + 62
        col = (226, 90, 100) if i < lv else (214, 200, 186)
        pygame.draw.circle(s, col, (cx - 6, cy), 7)
        pygame.draw.circle(s, col, (cx + 6, cy), 7)
        pygame.draw.polygon(s, col, [(cx - 13, cy + 2), (cx + 13, cy + 2), (cx, cy + 16)])
    bar = pygame.Rect(pv.x + 40, pv.bottom + 94, pv.w - 80, 12)
    pygame.draw.rect(s, (226, 214, 196), bar, border_radius=6)
    pygame.draw.rect(s, (226, 120, 120), (bar.x, bar.y, int(bar.w * progress(g)), bar.h), border_radius=6)
    ui.blit_text(s, 'Full of love' if lv >= 5 else 'Next heart', (bar.centerx, bar.bottom + 6), 'small', U.SOFT,
                 'midtop')
    # today
    x0 = rect.x + 430
    y = rect.y + 92
    ui.blit_text(s, 'Today with Biscuit', (x0, y), 'h3', U.INK)
    y += 36
    for key, label in TODAY:
        done = done_today(g, key)
        box = pygame.Rect(x0, y + 2, 18, 18)
        pygame.draw.rect(s, (250, 246, 236), box, border_radius=4)
        pygame.draw.rect(s, (170, 150, 130), box, 2, border_radius=4)
        if done:
            pygame.draw.lines(s, (90, 150, 90), False, [(box.x + 4, box.y + 9), (box.x + 8, box.y + 14),
                                                         (box.x + 15, box.y + 4)], 3)
        extra = ''
        if key == 'walk' and lv < FOLLOW_LEVEL:
            extra = '  (at 2 hearts)'
        elif key == 'play' and not toys(g):
            extra = '  (needs a toy)'
        ui.blit_text(s, label + extra, (x0 + 30, y), 'body', U.INK if not done else U.SOFT)
        y += 30
    y += 8
    bw = 184
    ui.button(s, (x0, y, bw, 44), 'Give a treat', lambda: give_treat(g), 'primary',
              enabled=not done_today(g, 'treat') and treat_fish(g) is not None)
    ui.button(s, (x0 + bw + 12, y, bw, 44), 'Play', lambda: play(g), 'normal', enabled=bool(toys(g)))
    ui.button(s, (x0 + 2 * (bw + 12), y, bw, 44), 'Ask for a trick', lambda: do_trick(g), 'normal',
              enabled=bool(tricks(g)))
    b = treat_fish(g)
    tip = ('Treat: your %s' % FISH_BY_ID[b['id']]['name']) if b and not done_today(g, 'treat') else \
        'Pet her on the dock once a day, too.'
    ui.blit_text(s, tip, (x0, y + 52), 'small', U.SOFT)
    y += 88
    ui.blit_text(s, 'Tricks', (x0, y), 'h3', U.INK)
    y += 34
    for i, (need, tid, name, desc) in enumerate(TRICKS):
        r = pygame.Rect(x0 + (i % 3) * 196, y + (i // 3) * 64, 186, 56)
        have = need <= lv
        ui.tile(s, r, (246, 238, 220) if have else (236, 228, 214), (226, 120, 120) if have else (190, 176, 160))
        ui.blit_text(s, name if have else '???', (r.x + 12, r.y + 8), 'smallb', U.INK if have else U.SOFT)
        ui.blit_text(s, ('Known' if have else '%d hearts' % need), (r.x + 12, r.y + 30), 'small', U.SOFT)
        if have:
            ui.hotspot(r, lambda tid=tid: do_trick(g, tid))
    y += 2 * 64 + 6
    if lv >= FOLLOW_LEVEL:
        ui.button(s, (x0, y, 280, 40), 'Walks to Fernwick: %s' % ('On' if g.cat_follow else 'Off'),
                  lambda: setattr(g, 'cat_follow', not g.cat_follow), 'tab_on' if g.cat_follow else 'tab',
                  font='smallb')
    n = g.stats.get('cat_gifts', 0)
    ui.blit_text(s, 'Presents so far: %d' % n, (x0 + 300, y + 10), 'smallb', U.SOFT)


# ---------------------------------------------------------------- Fernwick walks
class Follower:
    """Biscuit trotting a few steps behind you through Fernwick."""

    def __init__(self):
        self.x = None
        self.face = 1
        self.step = 0.0
        self.sit = 0.0

    def update(self, dt, px, pface):
        want = px - 18 * pface
        if self.x is None or abs(self.x - px) > 160:
            self.x = want
        d = want - self.x
        if abs(d) > 3:
            sp = min(abs(d) * 4, 110.0)
            self.x += math.copysign(sp * dt, d)
            self.face = 1 if d > 0 else -1
            self.step += dt * 12
            self.sit = 0.0
        else:
            self.face = 1 if px >= self.x else -1
            self.step = 0.0
            self.sit += dt

    def draw(self, s, g, t, scroll, ground):
        if self.x is None:
            return
        x = int(self.x - scroll)
        if -20 < x < s.get_width() + 20:
            actors.draw_cat(s, g, t, x, ground, bed=False, sleep=False, face=self.face, walk=self.step, look=0)
