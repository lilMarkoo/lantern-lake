"""The lake calendar: weekdays, seasonal events, birthdays, fish runs, the forecast and the calendar screen."""
import math
import random

import pygame

import ui as U
from data import (FISH, FISH_BY_ID, SEASONS, DAYS_PER_SEASON, WEEKDAYS, BIRTHDAYS, FESTIVALS, WAGON_DAYS,
                  FISH_RUN_DAY, METEOR_DAY, FESTIVAL_DAY)

SW, SH = 1280, 720


def dow(day):
    """Day of the week, 1..7."""
    return (day - 1) % DAYS_PER_SEASON + 1


def season_of(day):
    return ((day - 1) // DAYS_PER_SEASON) % 4


def year_of(day):
    return (day - 1) // (DAYS_PER_SEASON * 4) + 1


def weekday(day):
    return WEEKDAYS[dow(day) - 1]


def run_fish(day):
    """The species passing through on this season's Fishday (the same all week, so it can be announced)."""
    s = season_of(day)
    week = (day - 1) // DAYS_PER_SEASON
    rng = random.Random(week * 7919 + 13)
    pool = [f for f in FISH if 1 <= f['rarity'] <= 3 and f['weather'] is None and not f['needs'] and not f.get('method')
            and not f.get('event') and (f['seasons'] is None or s in f['seasons'])]
    return rng.choice(pool)['id']


def birthday(day):
    return BIRTHDAYS.get((season_of(day), dow(day)))


def events_on(day):
    """Everything special about a day, as (kind, title, description) tuples."""
    s, d = season_of(day), dow(day)
    out = []
    if d == 1:
        out.append(('season', 'First day of %s' % SEASONS[s],
                    "Grandma Rosie's almanac arrives with this week's events. Fresh bubbles are rising all over the lake."))
    if d in WAGON_DAYS:
        out.append(('wagon', "Wren's Wagon",
                    "Wren's houseboat shop moors on the lake from 6 AM to 8 PM. Click it for hats, outfits for Biscuit "
                    "and special bait."))
    if d == FESTIVAL_DAY:
        f = FESTIVALS[s]
        out.append(('festival', f['name'], f['desc'] + ' Festival Goldfish swim in all day.'))
    if d == 6:
        import club
        rule = 'the biggest single fish' if club.rule_for(day) == 'biggest' else 'the most different species'
        out.append(('club', 'Angling Club', 'From 5 to 7 PM, fish anywhere on the lake against Marlo, Dottie, '
                    'Ferris and Old Hen. This week: %s. Ribbons for the top three.' % rule))
    if d == 3:
        out.append(('stall', 'Market day', 'From 9 AM to 1 PM, set up your stall in Fernwick, at the top of the lake '
                    'path. Sell fish, dishes and garden things at your own prices.'))
    if d == FISH_RUN_DAY:
        name = FISH_BY_ID[run_fish(day)]['name']
        out.append(('run', '%s run' % name,
                    'Shoals of %s pass through the lake. They bite four times as often and sell for half again as '
                    'much.' % name))
    if d == METEOR_DAY:
        out.append(('meteor', 'Meteor shower',
                    'From 9 PM the sky fills with shooting stars and stays clear. Click them to wish. '
                    'The Starfall Shiner only bites tonight.'))
    b = birthday(day)
    if b:
        if b['fish']:
            out.append(('birthday', "%s's birthday" % b['who'],
                        '%s would love a %s. Bring one for a thank-you gift.' % (b['who'], FISH_BY_ID[b['fish']]['name'])))
        else:
            out.append(('birthday', "%s's birthday" % b['who'], 'Expect a letter (and something tucked inside).'))
    return out


def event_icon(s, kind, center, scale=1.0):
    x, y = center
    if kind == 'wagon':
        U.boat(s, (x, y + 2), 0.9 * scale)
    elif kind == 'festival':
        U.trophy(s, (x, y), 0.75 * scale)
    elif kind == 'club':
        import club
        club.ribbon(s, (x, y - int(4 * scale)), club.RIBBON_COL['blue'], 0.8 * scale)
    elif kind == 'lantern':
        k = scale
        s.fill((80, 66, 56), (x - int(2 * k), y - int(14 * k), int(4 * k), int(4 * k)))
        s.fill((80, 66, 56), (x - int(9 * k), y - int(10 * k), int(18 * k), int(18 * k)))
        s.fill((255, 210, 120), (x - int(6 * k), y - int(7 * k), int(12 * k), int(12 * k)))
        s.fill((255, 246, 200), (x - int(2 * k), y - int(4 * k), int(4 * k), int(6 * k)))
    elif kind == 'run':
        U.fish_icon(s, (x + 3, y), (110, 170, 210))
    elif kind == 'meteor':
        U.meteor(s, (x - 3, y + 3), 0.9 * scale)
    elif kind == 'birthday':
        U.cake(s, (x, y + 2), 0.8 * scale)
    elif kind == 'season':
        U.leaf(s, (x, y))
    elif kind == 'spot':
        U.rowboat(s, (x, y + 1), 0.75 * scale)
    elif kind == 'town':
        U.house(s, (x, y + 1))
    elif kind == 'stall':
        k = scale
        for i in range(4):
            pygame.draw.rect(s, (200, 84, 90) if i % 2 == 0 else (250, 242, 228),
                             (x - int(12 * k) + int(6 * k) * i, y - int(11 * k), int(6 * k) + 1, int(6 * k)))
        s.fill((150, 104, 70), (x - int(11 * k), y - int(5 * k), max(2, int(2 * k)), int(14 * k)))
        s.fill((150, 104, 70), (x + int(9 * k), y - int(5 * k), max(2, int(2 * k)), int(14 * k)))
        s.fill((176, 126, 84), (x - int(11 * k), y + int(3 * k), int(22 * k), int(6 * k)))
        s.fill((120, 170, 200), (x - int(6 * k), y, int(5 * k), int(3 * k)))
        s.fill((236, 120, 90), (x + int(1 * k), y, int(5 * k), int(3 * k)))
    elif kind == 'garden':
        pygame.draw.line(s, (110, 80, 54), (x - 9, y + 7), (x + 9, y + 7), 3)
        pygame.draw.line(s, (96, 156, 70), (x, y + 6), (x, y - 3), 2)
        pygame.draw.ellipse(s, (120, 180, 80), (x - 9, y - 7, 9, 6))
        pygame.draw.ellipse(s, (96, 156, 70), (x + 1, y - 9, 9, 6))
    elif kind == 'critter':
        s.fill((70, 64, 74), (x - 10, y - 5, 20, 13))
        s.fill((70, 64, 74), (x - 4, y - 8, 8, 4))
        pygame.draw.circle(s, (200, 220, 236), (x, y + 1), 5)
        pygame.draw.circle(s, (90, 120, 150), (x, y + 1), 3)
        s.fill((250, 230, 150), (x + 5, y - 4, 3, 2))
    elif kind == 'truck':                      # Rosie's truck
        import truck as TR
        spr = TR.truck_sprite((190, 74, 76))
        if scale != 1.0:
            spr = pygame.transform.scale(spr, (int(spr.get_width() * scale * 0.7),
                                               int(spr.get_height() * scale * 0.7)))
        s.blit(spr, spr.get_rect(center=(x, y)))
    elif kind == 'paw':                        # Biscuit's paw print
        c = (214, 132, 70)
        pygame.draw.ellipse(s, c, (x - 6, y - 1, 12, 9))
        for dx, dy in ((-7, -4), (-3, -8), (3, -8), (7, -4)):
            pygame.draw.circle(s, c, (x + dx, y + dy), 2)
    elif kind == 'reeds':                      # a clump of reeds with a cattail
        for dx, h in ((-6, 12), (-2, 16), (2, 14), (6, 10)):
            pygame.draw.line(s, (96, 150, 76), (x + dx, y + 8), (x + dx + 1, y + 8 - h), 2)
        s.fill((120, 80, 52), (x - 2, y - 9, 3, 6))
        pygame.draw.line(s, (120, 170, 200), (x - 10, y + 9), (x + 10, y + 9), 2)
    elif kind == 'mail':                       # an envelope
        s.fill((250, 244, 230), (x - 10, y - 6, 20, 14))
        pygame.draw.rect(s, (150, 120, 96), (x - 10, y - 6, 20, 14), 2)
        pygame.draw.lines(s, (150, 120, 96), False, [(x - 9, y - 5), (x, y + 2), (x + 9, y - 5)], 2)
        s.fill((220, 80, 80), (x - 2, y, 4, 3))
    elif kind == 'snack':
        pygame.draw.ellipse(s, (214, 150, 80), (x - 11, y - 5, 22, 12))
        pygame.draw.ellipse(s, (236, 190, 110), (x - 8, y - 5, 15, 5))
        pygame.draw.ellipse(s, (150, 96, 54), (x - 11, y - 5, 22, 12), 2)


# ---------------------------------------------------------------- the calendar screen
def draw(g, s):
    ui = g.ui
    rect = g.big_panel(s, 'Calendar')
    week0 = g.day - dow(g.day) + 1
    start = week0 + g.cal_off * DAYS_PER_SEASON
    sea, yr = season_of(start), year_of(start)
    # season header with arrows to look ahead
    hx = rect.x + 600
    ui.button(s, (hx - 190, rect.y + 24, 44, 44), '<', lambda: g.cal_shift(-1), 'normal', enabled=g.cal_off > 0,
              font='h3')
    ui.blit_text(s, '%s, year %d' % (SEASONS[sea], yr), (hx, rect.y + 46), 'h2', U.INK, 'center')
    ui.button(s, (hx + 146, rect.y + 24, 44, 44), '>', lambda: g.cal_shift(1), 'normal', enabled=g.cal_off < 7,
              font='h3')
    tw, th, gap = 134, 206, 8
    x0, y0 = rect.x + 28, rect.y + 90
    hover = None
    for i in range(DAYS_PER_SEASON):
        day = start + i
        r = pygame.Rect(x0 + i * (tw + gap), y0, tw, th)
        today, past = day == g.day, day < g.day
        sel = day == g.cal_sel
        hov = r.collidepoint(ui.mouse)
        if hov:
            hover = day
        fill = (252, 248, 236) if (hov or sel) else (240, 230, 210) if not past else (226, 218, 204)
        border = U.GOLD if today else U.BROWN if sel else (190, 172, 150)
        ui.tile(s, r, fill, border, today or sel)
        tc = U.SOFT if past else U.INK
        ui.blit_text(s, WEEKDAYS[i], (r.x + 12, r.y + 12), 'smallb', tc, maxw=tw - 44)
        ui.blit_text(s, str(i + 1), (r.centerx, r.y + 32), 'h1', tc, 'midtop')
        if today:
            pill = pygame.Rect(0, 0, 68, 26)
            pill.midtop = (r.centerx, r.y - 14)
            pill = U.snap_rect(pill)
            s.blit(ui._button_skin(pill.w, pill.h, U.GOLD, (150, 104, 40), 1), pill)
            ui.blit_text(s, 'Today', (pill.centerx, pill.centery - 1), 'smallb', (90, 60, 30), 'center')
        # forecast
        wx = g.forecast.get(str(day))
        if past:
            ui.blit_text(s, '-', (r.centerx, r.y + 104), 'h3', U.SOFT, 'center')
        elif wx:
            U.weather_icon(s, (r.centerx, r.y + 102), wx, False, 16, fill)
        else:
            ui.blit_text(s, '?', (r.centerx, r.y + 104), 'h2', (190, 176, 156), 'center')
        U.moon_phase(s, (r.right - 18, r.y + 18), day % 8, 7, fill)
        evs = events_on(day)
        n = len(evs)
        for j, (kind, title, _) in enumerate(evs):
            event_icon(s, kind, (r.centerx - (n - 1) * 17 + j * 34, r.y + 150))
        if n:
            label = evs[0][1] if n == 1 else '%d events' % n
            ui.blit_text(s, label, (r.centerx, r.bottom - 28), 'small', tc, 'midtop', maxw=tw - 14)
        ui.hotspot(r, lambda d=day: g.cal_pick(d))
    # details for the hovered or selected day
    day = hover if hover is not None else g.cal_sel
    if not (start <= day < start + DAYS_PER_SEASON):
        day = start
    dr = pygame.Rect(rect.x + 28, y0 + th + 18, rect.w - 56, rect.bottom - (y0 + th + 18) - 28)
    pygame.draw.rect(s, (244, 234, 214), dr, border_radius=16)
    pygame.draw.rect(s, (214, 196, 170), dr, 2, border_radius=16)
    diff = day - g.day
    when = {0: 'today', 1: 'tomorrow', -1: 'yesterday'}.get(diff, ('in %d days' % diff) if diff > 0 else '%d days ago' % -diff)
    ui.blit_text(s, '%s, %s %d' % (weekday(day), SEASONS[season_of(day)], dow(day)), (dr.x + 24, dr.y + 16), 'h3', U.INK)
    ui.blit_text(s, when, (dr.x + 24, dr.y + 46), 'small', U.SOFT)
    wx = g.forecast.get(str(day))
    moon = 'Full moon' if day % 8 in (0, 7) else 'New moon' if day % 8 in (3, 4) else 'Moon: %s' % (
        'waning' if day % 8 in (1, 2) else 'waxing')
    fc = ('Forecast: %s' % wx.capitalize()) if (wx and diff >= 0) else ('No forecast yet' if diff > 2 else '')
    ui.blit_text(s, '   '.join(t for t in (fc, moon) if t), (dr.right - 24, dr.y + 20), 'smallb', U.SOFT, 'topright')
    evs = events_on(day)
    y = dr.y + 80
    if not evs:
        ui.blit_text(s, 'A quiet day at the lake. Perfect for fishing and a cup of tea.', (dr.x + 24, y), 'body', U.SOFT)
    col_w = (dr.w - 48) // 2
    for j, (kind, title, desc) in enumerate(evs):
        cx = dr.x + 24 + (j % 2) * (col_w + 0)
        cy = y + (j // 2) * 96
        event_icon(s, kind, (cx + 20, cy + 22), 1.2)
        ui.blit_text(s, title, (cx + 50, cy + 2), 'bodyb', U.INK)
        for k, line in enumerate(ui.wrap(desc, 'small', col_w - 70)[:3]):
            ui.blit_text(s, line, (cx + 50, cy + 28 + k * 20), 'small', U.SOFT)
