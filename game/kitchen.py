"""Cooking: turn fish from your basket into dishes at the cabin stove.

A dish can be eaten (one meal a day, with an effect that lasts until bedtime), given to a neighbour in Fernwick
(everyone has a favourite) or sold at the shop for more than the fish were worth on their own.
Recipes are learned from Mabel at the bakery; two are written on the inside of the cabin cupboard from the start.
"""
import math

import pygame

import ui as U
from art import darken, lighten
from data import ALL_BY_ID, RARITY_NAMES

# needs: ('id', fish or junk id, n), ('rare', minimum rarity, n), ('any', None, n). fx: what eating it does today.
RECIPES = [
    dict(id='fritters', name='Minnow Fritters', needs=[('any', None, 3)], price=20, card=0,
         fx={'luck': 1.5}, effect='A good dose of luck',
         look=('fritters', (214, 160, 80), (236, 200, 120))),
    dict(id='chowder', name='Perch Chowder', needs=[('id', 'perch', 2), ('any', None, 1)], price=30, card=0,
         fx={'bite': 0.7}, effect='Fish bite much sooner',
         look=('bowl', (240, 226, 196), (232, 150, 90))),
    dict(id='grilled', name='Grilled Trout', needs=[('id', 'trout', 1)], price=45, card=150,
         fx={'size': 0.1}, effect='Fish run bigger',
         look=('plate', (150, 170, 150), (230, 120, 90))),
    dict(id='fishpie', name="Fisherman's Pie", needs=[('rare', 2, 1), ('any', None, 2)], price=75, card=250,
         fx={'rare': 1.4}, effect='Rare fish come out more',
         look=('pie', (214, 160, 96), (240, 220, 170))),
    dict(id='clam', name='Pearl Clam Chowder', needs=[('id', 'clam', 1), ('any', None, 2)], price=90, card=200,
         fx={'sell': 1.2}, effect='Fish sell for 20% more',
         look=('bowl', (246, 240, 228), (250, 250, 250))),
    dict(id='stew', name='Catfish Stew', needs=[('id', 'catfish', 1), ('any', None, 1)], price=50, card=200,
         fx={'night': 1.8}, effect='Night fish come out more',
         look=('bowl', (170, 110, 70), (120, 170, 90))),
    dict(id='tart', name='Sunny Tart', needs=[('id', 'sunfish', 1), ('id', 'bluegill', 1)], price=45, card=300,
         fx={'friend': 1.5}, effect='Neighbours warm to you faster',
         look=('tart', (226, 176, 96), (250, 210, 80))),
    dict(id='feast', name='Lakeside Feast', needs=[('rare', 3, 1), ('any', None, 3)], price=160, card=600,
         fx={'luck': 1.0, 'bite': 0.8, 'size': 0.06, 'rare': 1.25}, effect='A little of everything',
         look=('feast', (230, 140, 100), (150, 190, 110))),
]
RECIPE_BY_ID = {r['id']: r for r in RECIPES}
FAVOURITE_DISH = {'mabel': 'tart', 'tom': 'stew', 'juniper': 'clam', 'pip': 'fritters', 'hazel': 'fishpie',
                  'fen': 'grilled', 'librarian': 'chowder', 'rowan': 'stew'}


def known(g, r):
    return r['card'] == 0 or r['id'] in g.recipes


def need_text(need):
    kind, v, n = need
    if kind == 'id':
        name = ALL_BY_ID[v]['name']
    elif kind == 'rare':
        name = '%s+ fish' % RARITY_NAMES[v]
    else:
        name = 'any fish'
    return '%d %s' % (n, name) if n > 1 else name


def ingredients(g, r):
    """The basket items this recipe would use, cheapest first, or None. Also returns how many of each need
    you have, for showing progress."""
    used = set()
    picks = []
    have = []
    ok = True
    order = sorted(range(len(r['needs'])), key=lambda i: ('id', 'rare', 'any').index(r['needs'][i][0]))
    have = [0] * len(r['needs'])
    for i in order:
        kind, v, n = r['needs'][i]
        cands = []
        for b in sorted(g.basket, key=lambda b: b['price']):
            if id(b) in used:
                continue
            spec = ALL_BY_ID.get(b['id'])
            if spec is None:
                continue
            if kind == 'id' and b['id'] == v or \
                    kind == 'rare' and not spec.get('junk') and spec['rarity'] >= v or \
                    kind == 'any' and not spec.get('junk'):
                cands.append(b)
        take = cands[:n]
        have[i] = len(take)
        for b in take:
            used.add(id(b))
        picks += take
        if len(take) < n:
            ok = False
    return (picks if ok else None), have


def take(g, rid):
    """Take this recipe's fish out of the basket (they go into the pot). None if you can't cook it."""
    r = RECIPE_BY_ID[rid]
    if not known(g, r):
        return None
    items, _ = ingredients(g, r)
    if items is None:
        return None
    for it in items:
        g.basket.remove(it)
    return items


SERVINGS = {0: 0, 1: 1, 2: 1, 3: 2}


def finish(g, rid, stars, quiet=False):
    """Put the finished dish in the pantry. 0 stars is burnt (the fish are lost), 1-2 stars make a serving,
    3 stars two, and the copper stove adds one to anything that isn't burnt. 2 stars also gives a little luck
    (you taste as you go). Returns what happened, for the result card."""
    r = RECIPE_BY_ID[rid]
    n = SERVINGS[stars] + (1 if stars and g.has_up('stove') else 0)
    fresh = None
    if stars and hasattr(g, 'garden'):
        import garden
        fresh = garden.use_garnish(g, rid)
        if fresh:
            n += 1
    if n:
        g.pantry[rid] = g.pantry.get(rid, 0) + n
        g.stats['cooked'] = g.stats.get('cooked', 0) + n
    else:
        g.stats['burnt'] = g.stats.get('burnt', 0) + 1
    if stars == 3:
        g.stats['perfect_dishes'] = g.stats.get('perfect_dishes', 0) + 1
    new_best = stars > g.cook_best.get(rid, 0)
    if new_best:
        g.cook_best[rid] = stars
    if stars == 2:
        g.luck = min(3.0, g.luck + 0.3)
    if stars == 0:
        text = 'The %s is ruined. Biscuit sniffs it and walks away.' % r['name']
    else:
        text = '%d serving%s of %s in the pantry.' % (n, '' if n == 1 else 's', r['name'])
        if stars == 2:
            text += ' (A taste on the spoon: a little luck.)'
        if stars == 3 and new_best:
            text += ' Your first perfect one!'
        if fresh:
            import garden
            text += ' (Fresh %s from the garden made one more.)' % garden.CROP_BY_ID[fresh]['name'].lower()
    res = {'stars': stars, 'servings': n, 'text': text, 'new_best': new_best}
    if not quiet:
        finish_toast(g, res)
    return res


def finish_toast(g, res):
    g.toast(res['text'], (200, 140, 90) if res['stars'] else (170, 110, 100))
    g.check_badges()
    g.save()


def cook(g, rid, stars=2):
    """Cook straight away with a fixed result (tests and the old instant path)."""
    if take(g, rid) is None:
        return None
    g.audio.play('jingle2', 0.6)
    return finish(g, rid, stars)


def eat(g, rid):
    if g.pantry.get(rid, 0) <= 0:
        return
    m = g.meal_today()
    if m:
        g.toast("You're still full from the %s." % RECIPE_BY_ID[m]['name'], (150, 140, 130))
        return
    r = RECIPE_BY_ID[rid]
    g.pantry[rid] -= 1
    if not g.pantry[rid]:
        del g.pantry[rid]
    g.meal = {'id': rid, 'day': g.day}
    if 'luck' in r['fx']:
        g.luck = min(3.0, g.luck + r['fx']['luck'])
    g.audio.play('jingle1', 0.6)
    g.toast('You eat the %s. %s until bedtime.' % (r['name'], r['effect']), (200, 140, 90))
    g.save()


# ---------------------------------------------------------------- art
def dish_icon(rid, scale=2):
    """A little plate of food, drawn at 40x32 and scaled up in whole steps."""
    r = RECIPE_BY_ID[rid]
    kind, c1, c2 = r['look']
    s = pygame.Surface((40, 32), pygame.SRCALPHA)
    d = pygame.draw
    plate = (238, 236, 230)
    if kind == 'bowl':
        d.ellipse(s, darken(plate, 0.15), (6, 18, 28, 10))
        d.polygon(s, (200, 220, 236), [(5, 14), (35, 14), (31, 25), (9, 25)])
        d.polygon(s, (150, 176, 206), [(5, 14), (35, 14), (34, 17), (6, 17)])
        d.ellipse(s, c1, (6, 10, 28, 8))
        for x, y in ((12, 13), (19, 12), (26, 14)):
            d.circle(s, c2, (x, y), 2)
        d.line(s, (220, 220, 230), (30, 6), (26, 13), 2)
    elif kind == 'plate':
        d.ellipse(s, darken(plate, 0.12), (2, 16, 36, 12))
        d.ellipse(s, plate, (2, 14, 36, 12))
        d.ellipse(s, c1, (8, 14, 22, 8))
        d.polygon(s, darken(c1, 0.15), [(29, 18), (35, 14), (35, 22)])
        for x in (13, 18, 23):
            d.line(s, (90, 70, 60), (x, 15), (x + 2, 21))
        d.circle(s, c2, (9, 23), 2)
        d.circle(s, (110, 170, 90), (13, 24), 2)
    elif kind == 'pie':
        d.ellipse(s, darken(c1, 0.3), (4, 16, 32, 12))
        d.ellipse(s, c1, (4, 12, 32, 12))
        d.ellipse(s, c2, (8, 14, 24, 7))
        for x in range(9, 32, 5):
            d.line(s, darken(c1, 0.1), (x, 14), (x + 2, 21), 2)
        d.polygon(s, lighten(c1, 0.2), [(20, 18), (34, 13), (35, 20)])
    elif kind == 'tart':
        d.ellipse(s, darken(plate, 0.12), (2, 18, 36, 10))
        d.ellipse(s, plate, (2, 16, 36, 10))
        d.ellipse(s, darken(c1, 0.2), (8, 12, 24, 12))
        d.ellipse(s, c1, (8, 10, 24, 12))
        d.ellipse(s, c2, (11, 12, 18, 7))
        for x, y in ((15, 14), (20, 13), (25, 15)):
            d.circle(s, (255, 250, 220), (x, y), 1)
    elif kind == 'fritters':
        d.ellipse(s, darken(plate, 0.12), (2, 18, 36, 10))
        d.ellipse(s, plate, (2, 16, 36, 10))
        for x, y in ((12, 17), (20, 15), (28, 17), (16, 12), (24, 12)):
            d.circle(s, darken(c1, 0.2), (x, y + 1), 5)
            d.circle(s, c1, (x, y), 5)
            d.circle(s, c2, (x - 1, y - 2), 2)
    else:   # feast
        d.ellipse(s, darken(plate, 0.15), (0, 18, 40, 12))
        d.ellipse(s, plate, (0, 15, 40, 12))
        d.ellipse(s, c1, (5, 14, 18, 7))
        d.polygon(s, darken(c1, 0.15), [(22, 17), (26, 13), (26, 21)])
        d.circle(s, c2, (29, 17), 4)
        d.circle(s, (240, 200, 90), (34, 19), 3)
        d.ellipse(s, (214, 160, 96), (24, 6, 12, 9))
        d.ellipse(s, (240, 220, 170), (26, 7, 8, 4))
    return pygame.transform.scale(s, (40 * scale, 32 * scale))


def stove_art(s, rect, copper, t):
    """The cabin stove, drawn into the kitchen screen."""
    x, y, w, h = rect
    body = (196, 120, 70) if copper else (70, 70, 78)
    pygame.draw.rect(s, darken(body, 0.25), (x, y + 30, w, h - 30), border_radius=10)
    pygame.draw.rect(s, body, (x + 6, y + 36, w - 12, h - 48), border_radius=8)
    pygame.draw.rect(s, (40, 30, 30), (x + 30, y + 64, w - 60, h - 110), border_radius=8)
    for i in range(3):
        k = 0.5 + 0.5 * math.sin(t * 5 + i * 2.1)
        col = (240, int(120 + 80 * k), 60)
        pygame.draw.circle(s, col, (x + w // 2 - 24 + i * 24, y + h - 64), 8 + int(3 * k))
    pygame.draw.rect(s, darken(body, 0.35), (x - 6, y + 24, w + 12, 12), border_radius=4)
    pygame.draw.rect(s, (90, 90, 96), (x + w // 2 - 10, y - 40, 20, 64))
    pot = (150, 156, 170)
    pygame.draw.rect(s, pot, (x + 20, y - 6, 70, 30), border_radius=8)
    pygame.draw.rect(s, lighten(pot, 0.2), (x + 14, y - 10, 82, 8), border_radius=4)
    for i in range(3):
        k = (t * 0.6 + i / 3.0) % 1.0
        pygame.draw.circle(s, (236, 236, 240), (x + 40 + i * 14 + int(6 * k), y - 20 - int(40 * k)),
                           3 + int(5 * k), 2)


# ---------------------------------------------------------------- the kitchen tab in the cabin
def draw_kitchen(g, s, rect):
    ui = g.ui
    copper = g.has_up('stove')
    # recipes: two columns of cards
    x0, y0 = rect.x + 30, rect.y + 90
    cw, ch = 340, 104
    for i, r in enumerate(RECIPES):
        col, row = i % 2, i // 2
        c = pygame.Rect(x0 + col * (cw + 12), y0 + row * (ch + 8), cw, ch)
        kn = known(g, r)
        items, have = ingredients(g, r) if kn else (None, [0] * len(r['needs']))
        ui.tile(s, c, (250, 244, 228) if kn else (230, 224, 212), (196, 170, 140) if kn else (200, 190, 176))
        ic = dish_icon(r['id'], 2)
        if not kn:
            ic = pygame.mask.from_surface(ic, 1).to_surface(setcolor=(190, 178, 162, 255), unsetcolor=(0, 0, 0, 0))
        s.blit(ic, ic.get_rect(center=(c.x + 50, c.y + 38)))
        ui.blit_text(s, r['name'] if kn else '???', (c.x + 100, c.y + 10), 'smallb', U.INK, maxw=c.w - 110)
        if kn:
            ui.blit_text(s, r['effect'], (c.x + 100, c.y + 34), 'tiny', (90, 130, 80), maxw=c.w - 110)
            nx = c.x + 100
            for j, need in enumerate(r['needs']):
                done = have[j] >= need[2]
                label = need_text(need)
                if need[2] > 1:
                    label = '%s %d/%d' % (label.split(' ', 1)[1], have[j], need[2])
                w = ui.fonts['tiny'].size(label)[0] + 14
                if nx + w > c.right - 8:
                    break
                pill = U.snap_rect(pygame.Rect(nx, c.y + 58, w, 22))
                pygame.draw.rect(s, (214, 234, 204) if done else (240, 226, 206), pill, border_radius=8)
                pygame.draw.rect(s, (120, 170, 110) if done else (200, 170, 140), pill, 2, border_radius=8)
                ui.blit_text(s, label, pill.center, 'tiny', U.INK, 'center')
                nx += w + 6
            import garden
            fresh = garden.garnish_for(g, r['id'])
            if fresh:
                ic = garden.crop_icon(fresh, 1)
                s.blit(ic, (c.right - 26, c.bottom - 26))
                ui.blit_text(s, '+1', (c.right - 30, c.bottom - 18), 'tiny', (90, 140, 70), 'midright')
            ui.button(s, (c.x + 12, c.bottom - 30, 76, 24), 'Cook', lambda rid=r['id']: g.start_cooking(rid),
                      'primary', enabled=items is not None, font='small')
            best = g.cook_best.get(r['id'], 0)
            for k in range(3):
                col = (240, 196, 70) if k < best else (214, 204, 190)
                _star(s, c.right - 50 + k * 16, c.y + 14, 7, col)
        else:
            ui.blit_text(s, 'A recipe card from', (c.x + 100, c.y + 38), 'tiny', U.SOFT)
            ui.blit_text(s, "Mabel's bakery", (c.x + 100, c.y + 60), 'tiny', U.SOFT)
    # the stove and the pantry, right
    px = rect.x + 30 + 2 * (cw + 12) + 10
    pw = rect.right - 30 - px
    stove_art(s, (px + pw // 2 - 70, rect.y + 120, 140, 150), copper, g.t)
    ui.blit_text(s, 'Copper stove: one extra serving' if copper else 'Old iron stove', (px + pw // 2, rect.y + 282),
                 'small', U.SOFT, 'midtop', maxw=pw)
    m = g.meal_today()
    if m:
        ui.blit_text(s, "Today's meal: %s" % RECIPE_BY_ID[m]['name'], (px + pw // 2, rect.y + 308), 'tiny',
                     (90, 130, 80), 'midtop', maxw=pw)
    ui.blit_text(s, 'Pantry', (px, rect.y + 340), 'h3', U.INK)
    dishes = [(rid, n) for rid, n in sorted(g.pantry.items()) if n > 0 and rid in RECIPE_BY_ID]
    if not dishes:
        ui.blit_text(s, 'Nothing cooked yet.', (px, rect.y + 376), 'small', U.SOFT)
    for i, (rid, n) in enumerate(dishes[:5]):
        r = RECIPE_BY_ID[rid]
        row = pygame.Rect(px, rect.y + 372 + i * 40, pw, 36)
        ic = dish_icon(rid, 1)
        s.blit(ic, ic.get_rect(center=(row.x + 20, row.centery)))
        ui.blit_text(s, '%s x%d' % (r['name'], n), (row.x + 44, row.centery), 'tiny', U.INK, 'midleft',
                     maxw=pw - 116)
        ui.button(s, (row.right - 64, row.y + 4, 64, 28), 'Eat', lambda rid=rid: eat(g, rid),
                  'gold', enabled=m is None, font='small')
    ui.blit_text(s, 'Cooking well (3 stars) makes two servings. One meal a day; dishes make lovely gifts.',
                 (rect.centerx, rect.bottom - 26), 'small', U.SOFT, 'center')


def _star(s, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(s, col, pts)
