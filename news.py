"""What's new: a card after an update, the first time you carry on with a save in a new version.

The highlights come from version.json ('highlights': [[title, line], ...]); the long 'notes' are for the
release page and the launcher. A new game never shows it (you've seen nothing old to compare)."""
import math

import pygame

import ui as U


def highlights(g):
    import main
    info = main.version_info()
    hl = info.get('highlights') or [[n.split(':')[0].split('.')[0][:40], n] for n in info.get('notes', [])[:5]]
    return [(str(t), str(d)) for t, d in hl][:6]


def due(g):
    import main
    seen = g.settings.get('seen_ver')
    return bool(highlights(g)) and seen != main.GAME_VERSION


def mark_seen(g):
    import main
    if g.settings.get('seen_ver') != main.GAME_VERSION:
        g.settings['seen_ver'] = main.GAME_VERSION
        g.save_settings()


def queue(g, continuing):
    """On starting play: queue the card if this save hasn't seen this version (and remember either way)."""
    if continuing and due(g):
        g.queue.insert(0, ('scene', open_card))
    else:
        mark_seen(g)


def open_card(g):
    g.overlay = 'news'
    g.news_t = 0.0
    g.audio.play('page', 0.7)
    mark_seen(g)


def close(g):
    g.overlay = None
    g.audio.play('page', 0.5)


ICONS = ((236, 170, 90), (120, 170, 120), (110, 150, 200), (200, 120, 160), (170, 140, 210), (220, 200, 110))


def draw(g, s):
    import main
    ui = g.ui
    sw, sh = s.get_size()
    items = highlights(g)
    g.news_t = getattr(g, 'news_t', 0.0) + 1 / 60.0
    rows = []
    for t, d in items:
        rows.append((t, ui.wrap(d, 'small', 700)[:3]))
    h = 150 + sum(44 + 26 * len(ls) for _, ls in rows) + 70
    h = min(h, sh - 30)
    rect = pygame.Rect(sw // 2 - 440, sh // 2 - h // 2, 880, h)
    ui.panel(s, rect, radius=24)
    # a little ribbon banner at the top
    band = pygame.Rect(rect.x + 30, rect.y + 24, rect.w - 60, 64)
    pygame.draw.rect(s, (236, 222, 196), band, border_radius=18)
    for i in range(7):                                  # bunting along the banner
        x = band.x + 40 + i * (band.w - 80) // 6
        c = ICONS[i % len(ICONS)]
        sway = int(math.sin(g.t * 2 + i) * 2)
        pygame.draw.polygon(s, c, [(x - 9, band.y + 2), (x + 9, band.y + 2), (x, band.y + 16 + sway)])
    ui.blit_text(s, "What's new in %s" % main.GAME_VERSION, (band.centerx, band.y + 40), 'h2', U.INK, 'center')
    y = band.bottom + 22
    for i, (t, lines) in enumerate(rows):
        if y + 30 > rect.bottom - 80:
            break
        c = ICONS[i % len(ICONS)]
        cx = rect.x + 58
        pygame.draw.circle(s, U.darken(c, 0.3), (cx, y + 14), 13)
        pygame.draw.circle(s, c, (cx, y + 13), 11)
        pygame.draw.circle(s, U.lighten(c, 0.4), (cx - 3, y + 9), 3)
        ui.blit_text(s, t, (rect.x + 86, y + 2), 'bodyb', U.INK)
        yy = y + 34
        for ln in lines:
            ui.blit_text(s, ln, (rect.x + 86, yy), 'small', U.SOFT)
            yy += 26
        y = yy + 10
    ui.button(s, (rect.centerx - 90, rect.bottom - 66, 180, 46), 'Lovely!', lambda: close(g), 'primary')
