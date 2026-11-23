"""The Fernwick Angling Club (0.4.0): a little contest on the lake every Lanternday evening, 5 to 7 PM.

Odd weeks it's the biggest single fish, even weeks the most different species. Four regulars fish it with you:
Marlo (young, cocky, and your rival: he gets better every week you turn up), Dottie (knits between bites, steady
as a rock), Ferris (all gadgets: brilliant or hopeless) and Old Hen (quiet, and usually right). Their catches come
in over the two hours, so the board moves while you fish. Ribbons for the top three, a cup for a win, and a
letter from Marlo after each meet. State is Game.club (saved).
"""
import random

import ui as U

CLUB_DAY = 6                    # Lanternday
START, END = 17 * 60, 19 * 60
PRIZES = {1: 150, 2: 80, 3: 40}
RIBBONS = {1: 'blue', 2: 'red', 3: 'yellow'}
RIBBON_COL = {'blue': (70, 110, 200), 'red': (200, 70, 70), 'yellow': (230, 190, 70)}
RIVALS = [
    dict(id='marlo', name='Marlo', skill=0.40, var=0.15),
    dict(id='dottie', name='Dottie', skill=0.45, var=0.08),
    dict(id='ferris', name='Ferris', skill=0.40, var=0.35),
    dict(id='hen', name='Old Hen', skill=0.55, var=0.10),
]
RIVAL_BY_ID = {r['id']: r for r in RIVALS}
JIBES = [
    "Marlo shouts across the water: \"Is that a fish or did you hook a leaf?\"",
    "Dottie's needles click between bites. She doesn't even look at her float.",
    "Ferris's new electric reel whirs, sputters and dies. \"Prototype!\" he calls.",
    "Old Hen lifts a hand to you. That's practically a speech, for Hen.",
    "Marlo: \"I've had three bites already. You?\"",
    "Ferris is trying to cast with two rods at once.",
]


def new():
    return dict(day=0, rule='biggest', rivals={}, reveal={}, best=0.0, species=[], done=False, joined=False,
                meets=0, ribbons={'blue': 0, 'red': 0, 'yellow': 0}, h2h=[0, 0], last=0, jibe=0)


def clean(d):
    base = new()
    if not isinstance(d, dict):
        return base
    for k, v in base.items():
        if k in d and type(d[k]) is type(v):
            base[k] = d[k]
    base['rivals'] = {k: float(v) for k, v in base['rivals'].items() if k in RIVAL_BY_ID}
    base['reveal'] = {k: float(v) for k, v in base['reveal'].items() if k in RIVAL_BY_ID}
    base['species'] = [s for s in base['species'] if isinstance(s, str)]
    base['ribbons'] = {k: int(base['ribbons'].get(k, 0)) for k in ('blue', 'red', 'yellow')}
    if base['rule'] not in ('biggest', 'species'):
        base['rule'] = 'biggest'
    return base


def is_day(g, day=None):
    import almanac
    return almanac.dow(g.day if day is None else day) == CLUB_DAY


def rule_for(day):
    return 'biggest' if ((day - 1) // 7) % 2 == 0 else 'species'


def today(g):
    """Is there a meet still to come (or on) today?"""
    c = g.club
    return is_day(g) and not (c['day'] == g.day and c['done']) and g.minute < END


def live(g):
    c = g.club
    return is_day(g) and c['day'] == g.day and not c['done'] and START <= g.minute < END


def ensure(g):
    """Set up today's meet: the rule and how the regulars will do."""
    c = g.club
    if not is_day(g) or c['day'] == g.day or g.minute >= END:
        return
    import almanac
    rng = random.Random(g.day * 6151 + 5)
    year = almanac.year_of(g.day)
    c.update(day=g.day, rule=rule_for(g.day), best=0.0, species=[], done=False, joined=False, jibe=0)
    c['rivals'], c['reveal'] = {}, {}
    for r in RIVALS:
        sk = r['skill'] + (0.05 * min(c['meets'], 8) if r['id'] == 'marlo' else 0.0) + 0.06 * min(year, 3)
        x = max(0.05, min(1.2, sk + rng.gauss(0, r['var'])))
        if c['rule'] == 'biggest':
            c['rivals'][r['id']] = round(12 + 30 * x, 1)
        else:
            c['rivals'][r['id']] = float(max(1, min(8, round(1 + 4.5 * x))))
        c['reveal'][r['id']] = rng.uniform(0.3, 0.95)


def rival_now(g, rid):
    """A regular's score as it stands: their catches come in through the evening."""
    c = g.club
    final = c['rivals'].get(rid, 0.0)
    p = max(0.0, min(1.0, (g.minute - START) / float(END - START))) if c['day'] == g.day and not c['done'] else 1.0
    if p < 0.08:
        return 0.0
    k = min(1.0, p / c['reveal'].get(rid, 0.6))
    if c['rule'] == 'biggest':
        return round(final * (0.6 + 0.4 * k), 1) if k < 1 else final
    return float(int(final * k + 0.5))


def mine(g):
    c = g.club
    return c['best'] if c['rule'] == 'biggest' else float(len(c['species']))


def board(g):
    out = [(r['name'], rival_now(g, r['id'])) for r in RIVALS] + [('You', mine(g))]
    out.sort(key=lambda e: (-e[1], not (e[0] == 'You' and e[1] > 0)))   # ties go your way, once you've a score
    return out


def place(g):
    return [nm for nm, _ in board(g)].index('You') + 1


def fmt(rule, v):
    return '%.1f cm' % v if rule == 'biggest' else '%d species' % int(v)


def on_catch(g, spec, size):
    if not live(g) or g.place != 'lake' or spec.get('junk'):
        return
    import coast
    if coast.at_coast(g):
        return
    c = g.club
    c['joined'] = True
    old = mine(g)
    if c['rule'] == 'biggest':
        c['best'] = max(c['best'], round(size, 1))
    elif spec['id'] not in c['species']:
        c['species'].append(spec['id'])
    if mine(g) != old:
        p = place(g)
        g.toast('Angling Club: %s, %s' % (fmt(c['rule'], mine(g)), {1: 'in the lead!', 2: 'second',
                                                                    3: 'third'}.get(p, 'place %d' % p)),
                (90, 120, 190))


def tick(g, before):
    """Called as the clock moves: the start, a word from the regulars now and then, and the end."""
    ensure(g)
    c = g.club
    if not is_day(g) or c['day'] != g.day or c['done']:
        return
    if before < START <= g.minute:
        g.toast('The Angling Club is on until 7 PM: %s. Fish anywhere on the lake!' %
                ('biggest single fish' if c['rule'] == 'biggest' else 'most different species'), (90, 120, 190))
        g.audio.play('townbell', 0.5)
    if START <= g.minute < END and g.place == 'lake':
        slot = int((g.minute - START) // 35)
        if slot > c['jibe'] and slot < 4:
            c['jibe'] = slot
            g.toast(random.Random(g.day + slot).choice(JIBES), (120, 130, 160))
    if g.minute >= END or before < END <= g.minute:
        finish(g)


def finish(g):
    c = g.club
    if c['day'] != g.day or c['done']:
        return
    c['done'] = True
    if not c['joined']:
        return
    p = place(g)
    c['meets'] += 1
    c['last'] = p
    bd = board(g)
    marlo = next(sc for nm, sc in bd if nm == 'Marlo')
    if mine(g) >= marlo:
        c['h2h'][0] += 1
    else:
        c['h2h'][1] += 1
    prize = PRIZES.get(p, 10)
    g.coins += prize
    if p in RIBBONS:
        c['ribbons'][RIBBONS[p]] += 1
    if p == 1:
        g.stats['club_wins'] = g.stats.get('club_wins', 0) + 1
        import almanac
        g.trophies.append('Angling Club cup, year %d' % almanac.year_of(g.day))
    lines = '\n'.join('%d.  %s  -  %s' % (i + 1, nm, fmt(c['rule'], sc)) for i, (nm, sc) in enumerate(bd))
    w, l_ = c['h2h']
    if p == 1:
        talk = ("Fine. FINE. You won. Enjoy your cup. I'll be practising every night this week, and next "
                "Lanternday it's mine.")
    elif mine(g) >= marlo:
        talk = "You beat me again. Don't get used to it. Hen says I strike too early. Hen says a lot, for Hen."
    else:
        talk = "Ha! Beat you. Bring a bigger bucket next time. (Same time next Lanternday? It's no fun without you.)"
    body = '%s\n\n%s\n\nPrize: %d coins%s.\n\nYou and Marlo, all time: %d - %d.\n\n%s' % (
        {1: 'You won the Angling Club!', 2: 'Second place!', 3: 'Third place!'}.get(p, 'Thanks for fishing with us!'),
        lines, prize, (' and a %s ribbon' % RIBBONS[p]) if p in RIBBONS else '', w, l_, talk)
    g.post([('Angling Club results', body, '- Marlo (and the Club)')])
    g.audio.play('jingle4' if p == 1 else 'coin', 0.6)
    g.check_badges()
    g.save()


def note(g):
    """The day's note under the goal, on Lanternday."""
    if not today(g):
        return None
    c = g.club
    rule = 'biggest fish' if rule_for(g.day) == 'biggest' else 'most species'
    if live(g):
        return 'Angling Club until 7 PM: %s' % rule
    return 'Angling Club at 5 PM: %s' % rule


def hud(g):
    """(line, tip) for the slim tracker card."""
    c = g.club
    if not live(g):
        return 'Angling Club at 5 PM', 'Every Lanternday, 5 to 7 PM on the lake: %s.' % (
            'biggest single fish' if rule_for(g.day) == 'biggest' else 'most different species')
    bd = board(g)
    p = place(g)
    top = next((sc for nm, sc in bd if nm != 'You'), 0)
    if p == 1:
        nm, sc = bd[1]
        return 'Club %s - leading!' % fmt(c['rule'], mine(g)), \
            'You lead the Angling Club. %s is next with %s. Ends 7 PM.' % (nm, fmt(c['rule'], sc))
    lead = bd[0]
    return 'Club %s / %s' % (fmt(c['rule'], mine(g)).split()[0], fmt(c['rule'], lead[1])), \
        '%s leads with %s. You are %s. Ends 7 PM.' % (lead[0], fmt(c['rule'], lead[1]),
                                                      {2: 'second', 3: 'third'}.get(p, 'place %d' % p))


def ribbon(s, center, col, k=1.0):
    """A little rosette with two tails."""
    import pygame
    x, y = center
    r = int(8 * k)
    pygame.draw.polygon(s, U.darken(col, 0.2), [(x - r // 2, y), (x - r, y + r * 2), (x - r // 4, y + int(r * 1.6))])
    pygame.draw.polygon(s, U.darken(col, 0.2), [(x + r // 2, y), (x + r, y + r * 2), (x + r // 4, y + int(r * 1.6))])
    for i in range(10):
        import math
        a = i / 10 * math.tau
        pygame.draw.circle(s, U.lighten(col, 0.15), (x + int(math.cos(a) * r), y + int(math.sin(a) * r)), max(2, r // 3))
    pygame.draw.circle(s, col, (x, y), r)
    pygame.draw.circle(s, U.lighten(col, 0.45), (x, y), max(2, r // 2))
