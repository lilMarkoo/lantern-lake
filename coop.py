"""Online extras: send a fish to a friend, a friendly fishing race, and expeditions.

An expedition is a shared outing with three goals: catch three different kinds of fish between you, photograph an
animal, then hold a lakeside feast where everyone brings a dish. Everyone there earns a souvenir for their cabin.
Every player keeps the same picture of it from the messages ('t': 'exp'), and the host fills in anyone who joins
halfway.
"""
import random

import pygame

import ui as U
import art
from data import ALL_BY_ID, FISH_BY_ID, RARITY_COLORS

RACE_TIME = 180.0            # seconds of real time
EXP_SPECIES = 3              # different kinds of fish to catch together
SOUVENIRS = ('pennant', 'teamphoto', 'explantern')      # one per expedition, then coins and Golden Lures


def peers(g):
    n = g.net
    if not n.online:
        return []
    return sorted(n.peers.items())


# ---------------------------------------------------------------- gifts
def send_fish(g, pid, b):
    n = g.net
    if not n.online or pid not in n.peers or b not in g.basket:
        return False
    g.basket.remove(b)
    n.send({'t': 'gift', 'to': pid, 'fish': b['id'], 'size': b['size'], 'price': b['price']})
    name = n.peers[pid]['name']
    spec = ALL_BY_ID[b['id']]
    g.toast('You send %s your %s. What a friend!' % (name, spec['name']), (110, 150, 190))
    g.add_chat('', 'You sent %s a %s.' % (name, spec['name']), (150, 180, 220))
    g.stats['gifts_sent'] = g.stats.get('gifts_sent', 0) + 1
    g.audio.play('page', 0.6)
    return True


def on_gift(g, pid, m):
    """A friend sent you a fish: into your basket it goes."""
    n = g.net
    if m.get('to') != n.me or pid not in n.peers:
        return
    spec = FISH_BY_ID.get(m.get('fish'))
    if spec is None:
        return
    lo, hi = spec['size']
    try:
        size = max(lo, min(hi, float(m.get('size'))))
        price = max(1, min(spec['price'] * 3, int(m.get('price'))))
    except (TypeError, ValueError):
        return
    g.basket.append(dict(id=spec['id'], size=round(size, 1), price=price))
    name = n.peers[pid]['name']
    g.toast('%s sent you a %s (%.1f cm)! It is in your basket.' % (name, spec['name'], size),
            RARITY_COLORS[spec['rarity']])
    g.add_chat('', '%s sent you a %s.' % (name, spec['name']), g.peer_color(pid))
    g.stats['gifts_got'] = g.stats.get('gifts_got', 0) + 1
    g.audio.play('jingle2', 0.6)


# ---------------------------------------------------------------- the fishing race
def race_live(g):
    r = g.race
    return bool(r) and g.t < r['end']


def start_race(g):
    n = g.net
    if not n.online or not n.peers or race_live(g):
        return
    n.send({'t': 'race', 'op': 'start', 'dur': RACE_TIME})
    _begin(g, g.my_name())


def _begin(g, who):
    g.race = dict(end=g.t + RACE_TIME, scores={'me': 0}, by=who, done=False)
    for pid, _ in peers(g):
        g.race['scores'][pid] = 0
    g.toast('%s started a fishing race! Most fish in 3 minutes wins.' % who, (220, 160, 80))
    g.add_chat('', 'Fishing race! Most fish in 3 minutes. Go!', (240, 200, 120))
    g.audio.play('jingle3', 0.6)
    g.overlay = None if g.overlay == 'coop' else g.overlay


def on_race(g, pid, m):
    op = m.get('op')
    if op == 'start' and not race_live(g):
        _begin(g, g.net.peers.get(pid, {}).get('name', 'A friend'))
    elif op == 'score' and race_live(g):
        try:
            g.race['scores'][pid] = max(0, min(999, int(m.get('n'))))
        except (TypeError, ValueError):
            pass


def on_catch(g, spec):
    """Counts your fish (not junk) for a race or an expedition, and tells the others."""
    if spec.get('junk') or spec['id'] not in FISH_BY_ID:
        return
    if exp_live(g) and spec['id'] not in g.exp['species']:
        g.exp['species'][spec['id']] = g.my_name()
        g.net.send({'t': 'exp', 'op': 'fish', 'eid': g.exp['eid'], 'sp': spec['id']})
        _progress(g, 'You caught a %s for the expedition.' % spec['name'])
    if not race_live(g):
        return
    g.race['scores']['me'] += 1
    g.net.send({'t': 'race', 'op': 'score', 'n': g.race['scores']['me']})


# ---------------------------------------------------------------- expeditions
def exp_live(g):
    e = getattr(g, 'exp', None)
    return bool(e) and not e['done'] and g.net.online


def exp_goals(g):
    """(fish done, photo done, feast done) for the expedition."""
    e = g.exp
    fish = len(e['species']) >= EXP_SPECIES
    photo = e['photo'] is not None
    return fish, photo, fish and photo and len(e['dishes']) >= dishes_needed(g)


def dishes_needed(g):
    return max(2, 1 + len(g.net.peers))


def _new_exp(eid, by):
    return dict(eid=str(eid)[:16], by=by, species={}, photo=None, dishes=[], done=False, prize=None)


def start_exp(g):
    n = g.net
    if not n.online or not n.peers or exp_live(g):
        return False
    eid = '%08x' % random.getrandbits(32)
    g.exp = _new_exp(eid, g.my_name())
    n.send({'t': 'exp', 'op': 'start', 'eid': eid})
    _announce(g, g.my_name())
    return True


def _announce(g, who):
    g.toast('%s set off on an expedition! Catch three kinds of fish, photograph an animal, then feast.' % who,
            (90, 140, 170))
    g.add_chat('', 'Expedition! Three kinds of fish between you, one animal photo, then a lakeside feast.',
               (150, 200, 230))
    g.audio.play('jingle3', 0.6)


def end_exp(g):
    if not exp_live(g):
        return
    g.net.send({'t': 'exp', 'op': 'end', 'eid': g.exp['eid']})
    g.exp = None
    g.add_chat('', 'You called it a day. The expedition is over.', (150, 200, 230))


def on_photo(g, cid):
    """You photographed an animal: that's the expedition's photo, if it still needs one."""
    if exp_live(g) and g.exp['photo'] is None:
        import wildlife
        g.exp['photo'] = (g.my_name(), cid)
        g.net.send({'t': 'exp', 'op': 'photo', 'eid': g.exp['eid'], 'cid': cid})
        _progress(g, 'Your photo of the %s goes in the expedition album.' % wildlife.SPECIES_BY_ID[cid]['name'])


def bring_dish(g, rid):
    import kitchen
    if not exp_live(g) or rid not in kitchen.RECIPE_BY_ID or g.pantry.get(rid, 0) <= 0:
        return False
    fish, photo, _ = exp_goals(g)
    if not (fish and photo):
        g.toast('The feast comes last: fish and a photo first.', (150, 140, 130))
        return False
    g.pantry[rid] -= 1
    if g.pantry[rid] <= 0:
        del g.pantry[rid]
    g.exp['dishes'].append((g.my_name(), rid))
    g.net.send({'t': 'exp', 'op': 'dish', 'eid': g.exp['eid'], 'rid': rid})
    _progress(g, 'You bring %s to the feast.' % kitchen.RECIPE_BY_ID[rid]['name'])
    return True


def on_exp(g, pid, m):
    import kitchen
    import wildlife
    op = m.get('op')
    eid = str(m.get('eid', ''))[:16]
    who = g.net.peers.get(pid, {}).get('name', 'A friend')
    if op == 'start':
        if not exp_live(g):
            g.exp = _new_exp(eid, who)
            _announce(g, who)
        return
    if op == 'sync':
        if exp_live(g) and g.exp['eid'] == eid:
            return
        e = _new_exp(eid, str(m.get('by', who))[:20])
        for sp, nm in (m.get('species') or [])[:20]:
            if sp in FISH_BY_ID and not FISH_BY_ID[sp].get('junk'):
                e['species'][sp] = str(nm)[:20]
        ph = m.get('photo')
        if isinstance(ph, list) and len(ph) == 2 and ph[1] in wildlife.SPECIES_BY_ID:
            e['photo'] = (str(ph[0])[:20], ph[1])
        e['dishes'] = [(str(nm)[:20], rid) for nm, rid in (m.get('dishes') or [])[:8]
                       if rid in kitchen.RECIPE_BY_ID]
        g.exp = e
        g.add_chat('', 'You joined %s on an expedition.' % e['by'], (150, 200, 230))
        return
    if not exp_live(g) or g.exp['eid'] != eid:
        return
    e = g.exp
    if op == 'fish':
        sp = m.get('sp')
        if sp in FISH_BY_ID and not FISH_BY_ID[sp].get('junk') and sp not in e['species']:
            e['species'][sp] = who
            _progress(g, '%s caught a %s for the expedition.' % (who, FISH_BY_ID[sp]['name']))
    elif op == 'photo':
        cid = m.get('cid')
        if cid in wildlife.SPECIES_BY_ID and e['photo'] is None:
            e['photo'] = (who, cid)
            _progress(g, '%s photographed the %s for the expedition.' % (who, wildlife.SPECIES_BY_ID[cid]['name']))
    elif op == 'dish':
        rid = m.get('rid')
        if rid in kitchen.RECIPE_BY_ID and len(e['dishes']) < 8 and all(exp_goals(g)[:2]):
            e['dishes'].append((who, rid))
            _progress(g, '%s brought %s to the feast.' % (who, kitchen.RECIPE_BY_ID[rid]['name']))
    elif op == 'end':
        g.exp = None
        g.add_chat('', '%s called it a day. The expedition is over.' % who, (150, 200, 230))


def on_joined(g):
    """The host fills a newcomer in on an expedition that's already under way."""
    if g.net.role == 'host' and exp_live(g):
        e = g.exp
        g.net.send({'t': 'exp', 'op': 'sync', 'eid': e['eid'], 'by': e['by'],
                    'species': [[sp, nm] for sp, nm in e['species'].items()],
                    'photo': list(e['photo']) if e['photo'] else None,
                    'dishes': [[nm, rid] for nm, rid in e['dishes']]})


def _progress(g, text):
    g.add_chat('', text, (150, 200, 230))
    fish, photo, feast = exp_goals(g)
    if feast:
        _feast(g)
    elif fish and photo and not g.exp.get('told'):
        g.exp['told'] = True
        g.toast('Fish and a photo: time for the feast! Bring a dish from your pantry (G).', (200, 150, 80))
        g.audio.play('jingle2', 0.6)
    else:
        g.audio.play('ui', 0.5)


def _feast(g):
    e = g.exp
    e['done'] = True
    g.stats['expeditions'] = n = g.stats.get('expeditions', 0) + 1
    if n <= len(SOUVENIRS):
        sid = SOUVENIRS[n - 1]
        if sid not in g.home['owned']:
            g.home['owned'].append(sid)
        import home
        e['prize'] = home.BY_ID[sid]['name']
        prize_text = 'Your souvenir: the %s. It is in your cabin\'s Home catalogue.' % e['prize']
    else:
        g.coins += 150
        g.baits['golden'] = g.baits.get('golden', 0) + 2
        e['prize'] = '150 coins and 2 Golden Lures'
        prize_text = 'Your souvenir: %s.' % e['prize']
    names = sorted({nm for nm, _ in e['dishes']})
    g.add_chat('', 'The feast is ready! %s shared a meal on the dock.' % ' and '.join(names), (240, 200, 120))
    caption = ('Everyone gathers on the dock with their dishes. The lanterns come on, the food goes round, and '
               'somebody tells the one about the catfish that stole a hat.')

    def reward(g, text=prize_text):
        g.toast(text, (210, 160, 60))
        g.audio.play('jingle3', 0.7)
        if g.place == 'lake':
            g.world.hearts(220, 270, 8)
            g.world.sparkles(200, 260, 24, (255, 230, 160), 40)
    if g.place == 'lake' and g.overlay in (None, 'coop') and g.fishing.state == 'idle' and g.scene is None:
        import scenes
        g.overlay = 'scene'
        g.scene = scenes.Cutscene(g, [('fade', caption), ('call', reward)], 'lake', title='A lakeside feast')
        g.release_holds()
    else:
        reward(g)
    g.check_badges()
    g.save()


def exp_hud(g):
    """(title, line) for the HUD's objective card."""
    e = g.exp
    fish, photo, feast = exp_goals(g)
    if not fish:
        return 'Expedition', 'Catch %d kinds of fish: %d/%d' % (EXP_SPECIES, len(e['species']), EXP_SPECIES)
    if not photo:
        return 'Expedition', 'Photograph an animal (%s)' % _photo_key(g)
    return 'Expedition: the feast', 'Dishes %d/%d (G to bring one)' % (len(e['dishes']), dishes_needed(g))


def _photo_key(g):
    import wildlife
    return wildlife.photo_key(g)


def standings(g):
    r = g.race
    names = {pid: p['name'] for pid, p in peers(g)}
    rows = [(g.my_name() + ' (you)', r['scores']['me'], True)]
    rows += [(names[pid], sc, False) for pid, sc in r['scores'].items() if pid != 'me' and pid in names]
    rows.sort(key=lambda e: -e[1])
    return rows


def update(g, dt):
    e = getattr(g, 'exp', None)
    if e and not g.net.online:
        g.exp = None
    elif e and not e['done'] and all(exp_goals(g)):
        _feast(g)                           # someone left, so fewer dishes are needed now
    r = g.race
    if not r or r['done']:
        return
    if not g.net.online:
        g.race = None
        return
    if g.t >= r['end']:
        r['done'] = True
        rows = standings(g)
        top = rows[0][1]
        winners = [nm for nm, sc, _ in rows if sc == top]
        me_won = any(me for nm, sc, me in rows if sc == top and me)
        if top == 0:
            text = 'The race is over. Nobody caught a thing! The fish win this one.'
        elif len(winners) > 1:
            text = "The race is over: a tie between %s with %d fish!" % (' and '.join(winners), top)
        else:
            text = 'The race is over: %s wins with %d fish!' % (winners[0], top)
        g.add_chat('', text, (240, 200, 120))
        g.toast(text, (220, 160, 80))
        if me_won and top > 0:
            g.coins += 100
            g.stats['races_won'] = g.stats.get('races_won', 0) + 1
            g.toast('A little prize for the winner: 100 coins!', (210, 160, 60))
            g.audio.play('jingle3', 0.7)
        else:
            g.audio.play('jingle1', 0.5)


def hud_line(g):
    if not race_live(g):
        return None
    left = int(g.race['end'] - g.t)
    rows = standings(g)
    lead = rows[0]
    return 'Race %d:%02d  -  you %d, lead %s %d' % (left // 60, left % 60, g.race['scores']['me'],
                                                     lead[0].replace(' (you)', ''), lead[1])


# ---------------------------------------------------------------- the Friends window (G)
def draw_panel(g, s):
    ui = g.ui
    rect = g.big_panel(s, 'Friends at the lake')
    ps = peers(g)
    if not ps:
        ui.blit_text(s, 'Nobody else is here right now. Host or join a lake from the title screen.',
                     (rect.centerx, rect.centery), 'body', U.SOFT, 'center')
        return
    if g.gift_to not in dict(ps):
        g.gift_to = ps[0][0]
    tab = getattr(g, 'coop_tab', 'gifts')
    for i, (key, label) in enumerate((('gifts', 'Gifts and races'), ('exp', 'Expedition'))):
        ui.button(s, (rect.x + 476 + i * 200, rect.y + 26, 190, 40), label, lambda k=key: setattr(g, 'coop_tab', k),
                  'tab_on' if tab == key else 'tab', font='smallb')
    if tab == 'exp':
        return draw_exp(g, s, rect)
    x0, y = rect.x + 40, rect.y + 92
    ui.blit_text(s, 'Send a fish', (x0, y), 'h3', U.INK)
    for i, (pid, p) in enumerate(ps):
        ui.button(s, (x0 + 190 + i * 170, y - 6, 160, 38), p['name'], lambda pid=pid: setattr(g, 'gift_to', pid),
                  'tab_on' if g.gift_to == pid else 'tab', font='smallb')
    y += 46
    fish = [b for b in g.basket if b['id'] in FISH_BY_ID]
    if not fish:
        ui.blit_text(s, 'Your basket is empty. Catch something to share!', (x0, y + 10), 'body', U.SOFT)
    tw, th = 112, 104
    for n, b in enumerate(fish[:16]):
        r = pygame.Rect(x0 + (n % 8) * (tw + 8), y + (n // 8) * (th + 8), tw, th)
        spec = FISH_BY_ID[b['id']]
        hov = r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 248, 236) if hov else (240, 230, 210), RARITY_COLORS[spec['rarity']])
        spr = art.fish_sprite(spec, 2)
        if spr.get_width() > tw - 12:
            k = (tw - 12) / spr.get_width()
            spr = pygame.transform.scale(spr, (tw - 12, int(spr.get_height() * k)))
        s.blit(spr, spr.get_rect(center=(r.centerx, r.y + 38)))
        nm = spec['name'] if ui.fonts['small'].size(spec['name'])[0] < tw - 8 else spec['name'].split(' ')[-1]
        ui.blit_text(s, nm, (r.centerx, r.bottom - 40), 'small', U.INK, 'midtop')
        ui.blit_text(s, '%.1f cm' % b['size'], (r.centerx, r.bottom - 20), 'small', U.SOFT, 'midtop')
        ui.hotspot(r, lambda b=b: send_fish(g, g.gift_to, b))
    if len(fish) > 16:
        ui.blit_text(s, '+%d more in your basket' % (len(fish) - 16), (x0, y + 2 * (th + 8)), 'small', U.SOFT)
    ui.blit_text(s, 'Click a fish to send it to %s. It lands in their basket.' % dict(ps)[g.gift_to]['name'],
                 (x0, y + 2 * (th + 8) + 24), 'small', U.SOFT)
    # the race
    y = rect.bottom - 170
    pygame.draw.line(s, (226, 212, 190), (x0, y - 14), (rect.right - 40, y - 14), 2)
    ui.blit_text(s, 'Fishing race', (x0, y), 'h3', U.INK)
    if race_live(g):
        left = int(g.race['end'] - g.t)
        ui.blit_text(s, '%d:%02d left' % (left // 60, left % 60), (x0 + 200, y + 4), 'bodyb', (200, 120, 60))
        for i, (nm, sc, me) in enumerate(standings(g)[:4]):
            ui.blit_text(s, '%d.  %s   %d fish' % (i + 1, nm, sc), (x0 + (i % 2) * 380, y + 40 + (i // 2) * 28),
                         'bodyb' if me else 'body', U.INK)
    else:
        ui.blit_text(s, 'Everyone fishes for three minutes. Most fish wins (and 100 coins).', (x0, y + 40),
                     'body', U.SOFT)
        ui.button(s, (rect.right - 280, y - 4, 240, 48), 'Start a race', lambda: start_race(g), 'primary')


def _tick(s, box, on):
    pygame.draw.rect(s, (250, 246, 236), box, border_radius=5)
    pygame.draw.rect(s, (170, 150, 130), box, 2, border_radius=5)
    if on:
        pygame.draw.lines(s, (90, 150, 90), False, [(box.x + 5, box.y + 12), (box.x + 10, box.y + 18),
                                                     (box.x + 19, box.y + 5)], 3)


def draw_exp(g, s, rect):
    """The Expedition tab: the three goals, what everyone has done, and the feast."""
    import home
    import kitchen
    import wildlife
    ui = g.ui
    x0, y = rect.x + 40, rect.y + 96
    e = getattr(g, 'exp', None)
    if not exp_live(g):
        if e and e['done']:
            ui.blit_text(s, 'What a feast!', (x0, y), 'h2', U.INK)
            ui.blit_text(s, 'You brought home: %s.' % e['prize'], (x0, y + 44), 'bodyb', (90, 140, 90))
            y += 90
        lines = ('Set off together with everyone at the lake. Between you, catch three different kinds of fish '
                 'and photograph an animal. Then hold a lakeside feast: everyone brings a dish they cooked. '
                 'Everyone there takes home a souvenir for their cabin.')
        for ln in ui.wrap(lines, 'body', rect.w - 80):
            ui.blit_text(s, ln, (x0, y), 'body', U.INK)
            y += 28
        y += 20
        ui.blit_text(s, 'Souvenirs', (x0, y), 'h3', U.INK)
        y += 40
        got = g.stats.get('expeditions', 0)
        for i, sid in enumerate(SOUVENIRS):
            r = pygame.Rect(x0 + i * 200, y, 186, 120)
            have = sid in g.home['owned']
            ui.tile(s, r, (246, 238, 220), U.GOLD if have else (190, 176, 160), have)
            ic = home.icon(g, sid)
            s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 44)))
            ui.blit_text(s, home.BY_ID[sid]['name'] if have else 'Expedition %d' % (i + 1), (r.centerx, r.bottom - 34),
                         'small', U.INK if have else U.SOFT, 'midtop', maxw=r.w - 12)
        ui.blit_text(s, 'Expeditions so far: %d. After the third, each one brings coins and Golden Lures.' % got,
                     (x0, y + 136), 'small', U.SOFT)
        ui.button(s, (rect.right - 340, rect.bottom - 76, 300, 50), 'Set off on an expedition',
                  lambda: start_exp(g), 'primary', enabled=bool(g.net.peers))
        return
    fish, photo, feast = exp_goals(g)
    ui.blit_text(s, 'Expedition led by %s' % e['by'], (x0, y), 'h3', U.INK)
    y += 50
    # 1: three kinds of fish
    _tick(s, pygame.Rect(x0, y, 24, 24), fish)
    ui.blit_text(s, 'Catch %d different kinds of fish between you  (%d/%d)' % (EXP_SPECIES, min(EXP_SPECIES,
                 len(e['species'])), EXP_SPECIES), (x0 + 40, y), 'bodyb', U.INK)
    caught = ', '.join('%s (%s)' % (FISH_BY_ID[sp]['name'], nm) for sp, nm in list(e['species'].items())[:5])
    ui.blit_text(s, caught or 'Nothing yet. Any fish counts, as long as it is a new kind for the expedition.',
                 (x0 + 40, y + 28), 'small', U.SOFT, maxw=rect.w - 120)
    y += 74
    # 2: a photo
    _tick(s, pygame.Rect(x0, y, 24, 24), photo)
    ui.blit_text(s, 'Photograph an animal', (x0 + 40, y), 'bodyb', U.INK)
    ui.blit_text(s, ('%s photographed the %s.' % (e['photo'][0], wildlife.SPECIES_BY_ID[e['photo'][1]]['name']))
                 if photo else 'Anyone can take it: press %s for photo mode when an animal is about.' % _photo_key(g),
                 (x0 + 40, y + 28), 'small', U.SOFT, maxw=rect.w - 120)
    y += 74
    # 3: the feast
    _tick(s, pygame.Rect(x0, y, 24, 24), feast)
    need = dishes_needed(g)
    ui.blit_text(s, 'A lakeside feast: everyone brings a dish  (%d/%d)' % (len(e['dishes']), need), (x0 + 40, y),
                 'bodyb', U.INK if fish and photo else U.SOFT)
    brought = ', '.join('%s (%s)' % (kitchen.RECIPE_BY_ID[rid]['name'], nm) for nm, rid in e['dishes'][:5])
    ui.blit_text(s, brought or ('Pick a dish from your pantry below.' if fish and photo else
                                'Unlocks once you have the fish and the photo.'),
                 (x0 + 40, y + 28), 'small', U.SOFT, maxw=rect.w - 120)
    y += 70
    dishes = [rid for rid in sorted(g.pantry) if g.pantry[rid] > 0][:7]
    if not dishes:
        ui.blit_text(s, 'Your pantry is empty. Cook something in the cabin kitchen to bring along.', (x0 + 40, y + 20),
                     'small', (176, 110, 80))
    for i, rid in enumerate(dishes):
        r = pygame.Rect(x0 + 40 + i * 122, y, 112, 104)
        ok = fish and photo
        hov = ok and r.collidepoint(ui.mouse)
        ui.tile(s, r, (252, 248, 236) if hov else (240, 230, 210), (200, 150, 90) if ok else (196, 182, 162))
        ic = kitchen.dish_icon(rid, 2)
        s.blit(ic, ic.get_rect(center=(r.centerx, r.y + 38)))
        nm = kitchen.RECIPE_BY_ID[rid]['name']
        nm = nm if ui.fonts['small'].size(nm)[0] < r.w - 8 else nm.split(' ')[-1]
        ui.blit_text(s, nm, (r.centerx, r.bottom - 40), 'small', U.INK, 'midtop')
        ui.blit_text(s, 'x%d' % g.pantry[rid], (r.centerx, r.bottom - 20), 'small', U.SOFT, 'midtop')
        if ok:
            ui.hotspot(r, lambda rid=rid: bring_dish(g, rid))
    ui.button(s, (rect.right - 250, rect.bottom - 76, 210, 50), 'Call it a day', lambda: end_exp(g), 'rose')
