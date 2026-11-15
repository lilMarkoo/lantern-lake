"""Draws the launcher's art: the window/exe icon (icon.png, icon.ico) and the banner (banner.png).

The banner is rendered by the game itself in headless mode (no window, no saves touched).
Run:  E:\\Phyton\\python.exe tools\\make_art.py            (both)
      E:\\Phyton\\python.exe tools\\make_art.py icon       (icon only)
"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'launcher')

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame  # noqa: E402

# a 32x32 lantern, one character per pixel
LANTERN = [
    '................................',
    '...............kk...............',
    '..............k..k..............',
    '..............k..k..............',
    '...............kk...............',
    '...............kk...............',
    '...........kkkkkkkkkk...........',
    '..........kRRRRRRRRRRk..........',
    '.........kkkkkkkkkkkkkk.........',
    '..........kyyyywwyyyyk..........',
    '.........kyyyyywwyyyyyk.........',
    '.........kyoyyywwyyyoyk.........',
    '........kyyoyyywwyyyoyyk........',
    '........kyyoyywwwwyyoyyk........',
    '........kyyoyywffwyyoyyk........',
    '........kyyoyywffwyyoyyk........',
    '........kyyoyywffwyyoyyk........',
    '........kyyoyyywwyyyoyyk........',
    '........kyyoyyyyyyyyoyyk........',
    '.........kyoyyyyyyyyoyk.........',
    '.........kyyyyyyyyyyyyk.........',
    '..........kyyyyyyyyyyk..........',
    '.........kkkkkkkkkkkkkk.........',
    '..........kRRRRRRRRRRk..........',
    '...........kkkkkkkkkk...........',
    '...............kk...............',
    '..............kRRk..............',
    '...............kk...............',
    '................................',
    '................................',
    '................................',
    '................................',
]
INK = {'k': (58, 36, 40), 'R': (178, 74, 58), 'y': (255, 196, 92), 'o': (232, 146, 66), 'w': (255, 240, 190),
       'f': (255, 255, 236)}
BG_TOP, BG_BOT = (44, 48, 96), (24, 22, 46)


def icon_surface(size):
    """The icon at any size: a rounded night-blue tile, a warm glow, the pixel lantern on top."""
    g = 32
    base = pygame.Surface((g, g), pygame.SRCALPHA)
    for y, row in enumerate(LANTERN):
        for x, ch in enumerate(row):
            if ch in INK:
                base.set_at((x, y + 1), INK[ch])
    k = max(1, size // g)
    big = pygame.transform.scale(base, (g * k, g * k))
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    tile = pygame.Surface((size, size), pygame.SRCALPHA)
    for y in range(size):
        t = y / max(1, size - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        pygame.draw.line(tile, c, (0, y), (size, y))
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, size, size), border_radius=max(2, size // 5))
    tile.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(tile, (0, 0))
    # glow
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, int(size * 0.47)
    for i in range(12, 0, -1):
        r = int(size * 0.045 * i)
        pygame.draw.circle(glow, (255, 190, 90, 7), (cx, cy), r)
    glow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(glow, (0, 0))
    # stars
    for fx, fy in ((0.16, 0.18), (0.82, 0.14), (0.88, 0.62), (0.12, 0.7), (0.74, 0.86)):
        r = max(1, size // 64)
        pygame.draw.circle(s, (255, 244, 210), (int(fx * size), int(fy * size)), r)
    if big.get_width() != size:
        big = pygame.transform.smoothscale(base, (size, size)) if size < g else pygame.transform.smoothscale(
            big, (size, size))
    s.blit(big, (0, 0))
    return s


def png_bytes(surf):
    buf = io.BytesIO()
    pygame.image.save(surf, buf, 'icon.png')
    return buf.getvalue()


def write_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """A Windows .ico holding PNG images (supported since Windows Vista)."""
    images = [(n, png_bytes(icon_surface(n))) for n in sizes]
    head = struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b'', b''
    for n, b in images:
        entries += struct.pack('<BBBBHHII', n % 256, n % 256, 0, 0, 1, 32, len(b), offset + len(data))
        data += b
    with open(path, 'wb') as f:
        f.write(head + entries + data)


def make_icon():
    pygame.init()
    pygame.display.set_mode((8, 8))
    os.makedirs(OUT, exist_ok=True)
    pygame.image.save(icon_surface(256), os.path.join(OUT, 'icon.png'))
    write_ico(os.path.join(OUT, 'icon.ico'))
    print('icon ->', OUT)


def make_banner():
    """A summer dusk at the dock, drawn by the game, cropped to the launcher's 960x540 window."""
    sys.argv = ['make_art', '--bot', '0']
    sys.path.insert(0, ROOT)
    import main  # noqa: E402  (headless because of --bot: no window, no saves)
    g = main.Game()
    g.mode = 'play'
    g.fade = 0
    g.minute, g.day, g.weather = 1165, 12, 'clear'
    g.env.minute, g.env.day, g.env.season, g.env.weather = g.minute, g.day, g.season_of(g.day), g.weather
    g.env.settle()
    for _ in range(90):
        g.world.update(1 / 30, g.env, g)
        g.update_camera(1 / 30)
    g.hide_ui = False
    g.toasts.clear()
    g.draw()
    shot = pygame.transform.scale(g.frame, (g.frame.get_width() * 2, g.frame.get_height() * 2))
    w, h = shot.get_size()
    cw, ch = 960, 540
    crop = shot.subsurface(pygame.Rect(0, h - ch - 40, cw, ch)).copy()
    pygame.image.save(crop, os.path.join(OUT, 'banner.png'))
    print('banner ->', OUT)


if __name__ == '__main__':
    what = sys.argv[1:] or ['icon', 'banner']
    if 'icon' in what:
        make_icon()
    if 'banner' in what:
        make_banner()
