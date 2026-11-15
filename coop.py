"""Online extras: send a fish to a friend, and a friendly fishing race (most fish in three minutes)."""
import pygame

import ui as U
import art
from data import ALL_BY_ID, FISH_BY_ID, RARITY_COLORS

RACE_TIME = 180.0            # seconds of real time


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
    """Counts your fish (not junk) while a race is on, and tells the others."""
    if not race_live(g) or spec.get('junk'):
        return
    g.race['scores']['me'] += 1
    g.net.send({'t': 'race', 'op': 'score', 'n': g.race['scores']['me']})


def standings(g):
    r = g.race
    names = {pid: p['name'] for pid, p in peers(g)}
    rows = [(g.my_name() + ' (you)', r['scores']['me'], True)]
    rows += [(names[pid], sc, False) for pid, sc in r['scores'].items() if pid != 'me' and pid in names]
    rows.sort(key=lambda e: -e[1])
    return rows


def update(g, dt):
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
