"""Pixel-art fonts, panels, buttons and little icons for the 1280x720 interface canvas.

The interface is laid out in 1280x720 coordinates, but the finished frame is reduced to the world's 640x360
pixel grid before it is scaled up to the window, so everything shares the same chunky pixels. Panels, buttons
and the bitmap font are built at that grid (one art pixel = 2 canvas pixels) and snapped to even coordinates.
"""
import math

import pygame

from pixfont import PixelFont

CREAM = (248, 240, 224)
CREAM_D = (236, 222, 196)
PAPER = (250, 242, 218)
BROWN = (118, 82, 58)
BROWN_D = (78, 54, 40)
INK = (72, 52, 40)
SOFT = (140, 118, 100)
SAGE = (126, 170, 118)
SAGE_D = (92, 136, 88)
ROSE = (222, 132, 128)
GOLD = (232, 182, 72)
SKY = (120, 170, 220)
LOGICAL = (1280, 720)


def _font_spec(names, size, bold=False):
    for n in names:
        p = pygame.font.match_font(n, bold=bold)
        if p:
            return (p, size)
    return (None, int(size * 1.35))


def lighten(c, k):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


PIXEL_FONTS = {
    'title': (8, True), 'h1': (4, True), 'h2': (4, False), 'h3': (2, True), 'body': (2, False),
    'bodyb': (2, True), 'small': (2, False), 'smallb': (2, True), 'tiny': (2, False), 'big': (4, False),
    'hand': (2, False), 'handb': (2, True), 'bang': (4, True),
}


def darken(c, k):
    return (int(c[0] * (1 - k)), int(c[1] * (1 - k)), int(c[2] * (1 - k)))


def snap(v):
    """Round down to the 2-pixel art grid."""
    return int(v) - (int(v) % 2)


def snap_rect(rect):
    r = pygame.Rect(rect)
    x, y = snap(r.x), snap(r.y)
    return pygame.Rect(x, y, snap(r.right - x + 1), snap(r.bottom - y + 1))


FONT_SPECS = {
    'title': (['gabriola', 'georgia'], 132, False),
    'h1': (['georgia'], 40, True),
    'h2': (['georgia'], 28, True),
    'h3': (['georgia'], 22, True),
    'body': (['segoeui', 'candara', 'arial'], 20, False),
    'bodyb': (['segoeuisemibold', 'segoeui', 'arial'], 20, False),
    'small': (['segoeui', 'arial'], 16, False),
    'smallb': (['segoeuisemibold', 'segoeui', 'arial'], 16, False),
    'tiny': (['segoeuisemibold', 'segoeui', 'arial'], 13, False),
    'big': (['segoeuisemibold', 'segoeui', 'arial'], 30, False),
    'hand': (['segoeprint', 'inkfree', 'georgia'], 20, False),
    'handb': (['segoeprint', 'inkfree', 'georgia'], 26, True),
    'bang': (['georgia'], 40, True),
}


# ---------------------------------------------------------------- controller button styles
# Buttons are named by position, the way SDL reports them: A is the bottom face button, B the right one,
# X the left one and Y the top one, whatever the controller prints on them.
PAD_TEXT = {
    'xbox': {'LB': 'LB', 'RB': 'RB', 'LT': 'LT', 'RT': 'RT', 'START': 'Menu', 'BACK': 'View', 'LS': 'LS',
             'RS': 'RS'},
    'ps': {'LB': 'L1', 'RB': 'R1', 'LT': 'L2', 'RT': 'R2', 'START': 'Options', 'BACK': 'Share', 'LS': 'L3',
           'RS': 'R3', 'A': 'Cross', 'B': 'Circle', 'X': 'Square', 'Y': 'Triangle'},
    'switch': {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X', 'LB': 'L', 'RB': 'R', 'LT': 'ZL', 'RT': 'ZR',
               'START': '+', 'BACK': '-', 'LS': 'LS', 'RS': 'RS'},
}
PAD_COLORS = {
    'xbox': {'A': (130, 210, 90), 'B': (240, 96, 84), 'X': (96, 160, 240), 'Y': (246, 204, 70)},
    'ps': {'A': (130, 170, 245), 'B': (245, 110, 110), 'X': (236, 140, 210), 'Y': (96, 214, 180)},
    'switch': {},
}
PAD_NAMES = {'xbox': 'Xbox', 'ps': 'PlayStation', 'switch': 'Switch'}
# keyboard keys in hint lines and the controller button that does the same thing
KEY_TO_PAD = {'Space': 'A', 'Click': 'A', 'Hold Click': 'A', 'Enter': 'A', 'E': 'X', 'J': 'Y', 'K': 'BACK',
              'Tab': 'LB', 'L': 'RB', 'T': 'RS', 'B': 'LS', 'Esc': 'START', 'A': 'STICK', 'D': 'STICK',
              'Left': 'STICK', 'Right': 'STICK', 'Mouse': 'STICK', 'Up': 'DPAD', 'Down': 'DPAD'}


def _pad_art(name, layout, aw):
    """The button at art resolution (half size, 12 pixels tall); the UI doubles it."""
    s = pygame.Surface((aw, 12), pygame.SRCALPHA)
    # a light rim keeps every button readable on the dark hint bars and the cream panels alike
    edge, body, hi = (236, 226, 210), (52, 46, 60), (96, 90, 106)
    round_ = name in ('A', 'B', 'X', 'Y', 'STICK', 'RSTICK') or (layout == 'switch' and name in ('START', 'BACK'))
    if name == 'DPAD':
        for rr in ((4, 0, 4, 12), (0, 4, 12, 4)):
            pygame.draw.rect(s, edge, rr)
        for rr in ((5, 1, 2, 10), (1, 5, 10, 2)):
            pygame.draw.rect(s, body, rr)
        s.fill((246, 240, 232), (5, 1, 2, 2))
        s.fill((246, 240, 232), (5, 9, 2, 2))
        return s
    if round_:
        pygame.draw.ellipse(s, edge, (0, 0, 12, 12))
        pygame.draw.ellipse(s, body, (1, 1, 10, 10))
        pygame.draw.arc(s, hi, (1, 1, 10, 10), 0.6, 2.6, 1)
    else:
        # shoulder buttons, triggers and the small menu buttons are pills; triggers get a taller top
        pygame.draw.rect(s, edge, (0, 0, aw, 12), border_radius=4 if name in ('LT', 'RT') else 5)
        pygame.draw.rect(s, body, (1, 1, aw - 2, 10), border_radius=3 if name in ('LT', 'RT') else 4)
        pygame.draw.line(s, hi, (3, 1), (aw - 4, 1))
        if name in ('LT', 'RT'):
            pygame.draw.line(s, hi, (2, 2), (aw - 3, 2))
    if name in ('STICK', 'RSTICK'):
        pygame.draw.ellipse(s, (130, 124, 140), (3, 3, 6, 6), 1)
        s.fill((246, 240, 232), (5, 5, 2, 2))
        return s
    if layout == 'switch' and name in ('START', 'BACK'):
        s.fill((246, 240, 232), (3, 5, 6, 2))
        if name == 'START':
            s.fill((246, 240, 232), (5, 3, 2, 6))
        return s
    if layout == 'ps' and name in ('A', 'B', 'X', 'Y'):
        c = PAD_COLORS['ps'][name]
        if name == 'A':
            pygame.draw.line(s, c, (3, 3), (8, 8))
            pygame.draw.line(s, c, (8, 3), (3, 8))
        elif name == 'B':
            pygame.draw.ellipse(s, c, (3, 3, 6, 6), 1)
        elif name == 'X':
            pygame.draw.rect(s, c, (3, 3, 6, 6), 1)
        else:
            pygame.draw.lines(s, c, True, [(6, 2), (9, 8), (2, 8)])
    return s


class UI:
    def __init__(self):
        self.specs = {k: _font_spec(*v) for k, v in FONT_SPECS.items()}
        self.fonts = {k: PixelFont(*v) for k, v in PIXEL_FONTS.items()}
        self.narrow = {k: PixelFont(v[0], v[1], 0) for k, v in PIXEL_FONTS.items()}
        self.target = None     # the canvas everything is drawn on this frame
        self.key_labels = {}   # default key label -> the key you bound instead (binds.py)
        self.cache = {}
        self.hicache = {}
        self.hifonts = {}
        self.skin = {}
        self.hot = []          # (rect, action) registered while drawing
        self.nav = []          # keyboard-navigable buttons registered while drawing
        self.focus = None
        self.nav_owner = None
        self.pad_layout = None   # 'xbox', 'ps' or 'switch' while hints should show controller buttons
        self.mouse = (0, 0)
        self.mouse_moved = False
        self.mouse_down = False
        self.k = 1.0           # window pixels per logical pixel
        self.layers = []
        self.stages = []
        self.used = 0

    # ---------------------------------------------------------------- stages and sharp text
    def begin_frame(self, k):
        self.k = k
        self.used = 0
        self.stages = []

    def stage(self):
        """The surface to draw the interface on (the shared canvas when the game provides one)."""
        if self.target is not None:
            return self.target
        if self.used >= len(self.layers):
            self.layers.append(pygame.Surface(LOGICAL, pygame.SRCALPHA))
        layer = self.layers[self.used]
        self.used += 1
        layer.fill((70, 50, 44, 0))
        self.stages.append((layer, []))
        return layer

    def _deferred(self, dst):
        if self.target is not None or abs(self.k - 1.0) < 0.01:
            return None
        for layer, texts in self.stages:
            if dst is layer:
                return texts
        return None

    def hifont(self, font, k):
        key = (font, k)
        f = self.hifonts.get(key)
        if f is None:
            path, size = self.specs[font]
            f = pygame.font.Font(path, max(6, int(round(size * k))))
            self.hifonts[key] = f
        return f

    def hitext(self, s, font, color, k):
        key = (s, font, color, k)
        surf = self.hicache.get(key)
        if surf is None:
            if len(self.hicache) > 1500:
                self.hicache.clear()
            surf = self.hifont(font, k).render(s, True, color)
            self.hicache[key] = surf
        return surf

    def draw_texts(self, dst, texts, k, ox=0, oy=0):
        kk = round(k, 3)
        for s, font, color, anchor, pos, shadow, alpha in texts:
            surf = self.hitext(s, font, color, kk)
            r = surf.get_rect(**{anchor: (ox + pos[0] * k, oy + pos[1] * k)})
            if shadow:
                sh = self.hitext(s, font, shadow, kk)
                if alpha is not None:
                    sh = sh.copy()
                    sh.set_alpha(int(alpha * 0.8))
                dst.blit(sh, r.move(0, max(1, round(2 * k))))
            if alpha is not None:
                surf = surf.copy()
                surf.set_alpha(int(alpha))
            dst.blit(surf, r)

    # ---------------------------------------------------------------- text
    def text(self, s, font='body', color=INK, narrow=False):
        key = (s, font, color, narrow)
        surf = self.cache.get(key)
        if surf is None:
            if len(self.cache) > 1200:
                self.cache.clear()
            surf = (self.narrow if narrow else self.fonts)[font].render(s, False, color)
            self.cache[key] = surf
        return surf

    def blit_text(self, dst, s, pos, font='body', color=INK, anchor='topleft', shadow=None, alpha=None,
                  maxw=None, outline=None, narrow=False):
        """Draw text snapped to the pixel grid. maxw squeezes (then trims) text that would not fit."""
        color = tuple(color[:3])
        if maxw and self.fonts[font].size(s)[0] > maxw:
            narrow = True
            while len(s) > 2 and self.narrow[font].size(s)[0] > maxw:
                s = s[:-3].rstrip() + '..'
        surf = self.text(s, font, color, narrow)
        r = surf.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        r.x, r.y = snap(r.x), snap(r.y)
        px = self.fonts[font].px
        layers = []
        if outline:
            o = self.text(s, font, tuple(outline[:3]), narrow)
            layers += [(o, r.move(dx, dy)) for dx, dy in ((-px, 0), (px, 0), (0, -px), (0, px))]
        if shadow:
            layers.append((self.text(s, font, tuple(shadow[:3]), narrow), r.move(0, px)))
        layers.append((surf, r))
        for img, rr in layers:
            if alpha is not None:
                img = img.copy()
                img.set_alpha(int(alpha))
            dst.blit(img, rr)
        return r

    def wrap(self, s, font, width, narrow=False):
        f = (self.narrow if narrow else self.fonts)[font]
        out = []
        for para in s.split('\n'):
            words = para.split(' ')
            line = ''
            for w in words:
                test = (line + ' ' + w).strip()
                if f.size(test)[0] <= width:
                    line = test
                else:
                    if line:
                        out.append(line)
                    line = w
            out.append(line)
        return out

    # ---------------------------------------------------------------- panels
    def _remember(self, key, surf):
        if len(self.skin) > 400:
            self.skin.clear()
        self.skin[key] = surf
        return surf

    def _px(self, aw, ah):
        return pygame.Surface((max(1, aw), max(1, ah)), pygame.SRCALPHA)

    def _up(self, s):
        return pygame.transform.scale(s, (s.get_width() * 2, s.get_height() * 2))

    def _shadow(self, w, h, radius=0, depth=0):
        key = ('sh', w, h)
        sh = self.skin.get(key)
        if sh is None:
            s = self._px(w // 2, h // 2)
            pygame.draw.rect(s, (30, 18, 20, 80), s.get_rect(), border_radius=3)
            sh = self._remember(key, self._up(s))
        return sh

    def _frame(self, w, h, fill, border, width):
        """A pixel-art frame: dark outline, bevelled wooden rim and a flat parchment middle."""
        key = ('frame', w, h, tuple(fill[:3]), tuple(border[:3]), width)
        surf = self.skin.get(key)
        if surf is None:
            aw, ah = w // 2, h // 2
            s = self._px(aw, ah)
            out = darken(border, 0.5)
            fill = tuple(fill[:3])
            if not width:
                pygame.draw.rect(s, fill, (0, 0, aw, ah), border_radius=2)
            elif min(aw, ah) >= 60:
                pygame.draw.rect(s, out, (0, 0, aw, ah), border_radius=3)
                pygame.draw.rect(s, lighten(border, 0.28), (1, 1, aw - 2, ah - 2), border_radius=2)
                pygame.draw.rect(s, darken(border, 0.3), (2, 2, aw - 3, ah - 3), border_radius=2)
                pygame.draw.rect(s, border, (2, 2, aw - 4, ah - 4), border_radius=2)
                for x in range(6, aw - 6, 9):           # wood grain flecks on the rim
                    s.set_at((x, 2), darken(border, 0.12))
                    s.set_at((x + 4, ah - 4), darken(border, 0.12))
                pygame.draw.rect(s, out, (4, 4, aw - 8, ah - 8), border_radius=1)
                pygame.draw.rect(s, fill, (5, 5, aw - 10, ah - 10))
                pygame.draw.line(s, darken(fill, 0.07), (5, 5), (aw - 6, 5))
                pygame.draw.line(s, darken(fill, 0.035), (5, 6), (aw - 6, 6))
            else:
                pygame.draw.rect(s, out, (0, 0, aw, ah), border_radius=2)
                pygame.draw.rect(s, border, (1, 1, aw - 2, ah - 2), border_radius=1)
                pygame.draw.line(s, lighten(border, 0.25), (2, 1), (aw - 3, 1))
                pygame.draw.rect(s, fill, (2, 2, aw - 4, ah - 4))
                pygame.draw.line(s, lighten(fill, 0.4), (2, 2), (aw - 3, 2))
            surf = self._remember(key, self._up(s))
        return surf

    def _body(self, w, h, fill, border, radius, width, sheen=0.05):
        return self._frame(w, h, fill, border, width)

    def panel(self, dst, rect, fill=CREAM, border=BROWN, radius=16, shadow=True, width=3):
        rect = snap_rect(rect)
        if rect.w < 8 or rect.h < 8:
            return rect
        if shadow:
            dst.blit(self._shadow(rect.w, rect.h), (rect.x, rect.y + 4))
        dst.blit(self._frame(rect.w, rect.h, fill, border, width), rect)
        return rect

    def glass(self, dst, rect, alpha=150, radius=14):
        rect = snap_rect(rect)
        key = ('glass', rect.w, rect.h, alpha)
        s = self.skin.get(key)
        if s is None:
            g = self._px(rect.w // 2, rect.h // 2)
            pygame.draw.rect(g, (30, 24, 38, alpha), g.get_rect(), border_radius=3)
            pygame.draw.rect(g, (255, 240, 220, 70), g.get_rect(), 1, border_radius=3)
            s = self._remember(key, self._up(g))
        dst.blit(s, rect)
        return rect

    def _button_skin(self, w, h, fill, border, lip):
        key = ('btn', w, h, tuple(fill[:3]), tuple(border[:3]), lip)
        surf = self.skin.get(key)
        if surf is None:
            aw, ah = w // 2, h // 2
            s = self._px(aw, ah)
            out = darken(border, 0.45)
            pygame.draw.rect(s, out, (0, 0, aw, ah), border_radius=2)
            pygame.draw.rect(s, darken(fill, 0.3), (1, 1, aw - 2, ah - 2), border_radius=1)
            pygame.draw.rect(s, fill, (1, 1, aw - 2, ah - 2 - lip), border_radius=1)
            pygame.draw.line(s, lighten(fill, 0.45), (2, 1), (aw - 3, 1))
            pygame.draw.line(s, lighten(fill, 0.2), (1, 2), (1, ah - 3 - lip))
            surf = self._remember(key, self._up(s))
        return surf

    # ---------------------------------------------------------------- controller buttons
    def pad_label(self, name, layout=None):
        layout = layout or self.pad_layout or 'xbox'
        return PAD_TEXT[layout].get(name, name)

    def pad_w(self, name, layout=None):
        layout = layout or self.pad_layout or 'xbox'
        if name in ('A', 'B', 'X', 'Y', 'STICK', 'RSTICK', 'DPAD'):
            return 24
        if layout == 'switch' and name in ('START', 'BACK'):
            return 24
        return snap(max(30, self.fonts['tiny'].size(self.pad_label(name, layout))[0] + 14))

    def padcap(self, dst, name, pos, anchor='midleft', layout=None):
        """A controller button drawn in that controller's own style. Returns its rect."""
        layout = layout or self.pad_layout or 'xbox'
        w = self.pad_w(name, layout)
        r = pygame.Rect(0, 0, w, 24)
        setattr(r, anchor, (int(pos[0]), int(pos[1])))
        r.x, r.y = snap(r.x), snap(r.y)
        key = ('pad', layout, name, w)
        surf = self.skin.get(key)
        if surf is None:
            surf = self._remember(key, self._up(_pad_art(name, layout, w // 2)))
        dst.blit(surf, r)
        face = name in ('A', 'B', 'X', 'Y')
        if face and layout == 'ps':
            return r                                    # the symbol is part of the art
        if name in ('STICK', 'RSTICK', 'DPAD') or (layout == 'switch' and name in ('START', 'BACK')):
            return r
        label = self.pad_label(name, layout)
        col = PAD_COLORS[layout].get(name, (246, 240, 232)) if face else (246, 240, 232)
        self.blit_text(dst, label, (r.centerx, r.y + 2), 'tiny', col, 'midtop')
        return r

    def pad_parts(self, parts):
        """Swap the keyboard keys in a hint line for the matching controller buttons."""
        out = []
        for p in parts:
            if isinstance(p, tuple) and p[0] == 'key':
                name = KEY_TO_PAD.get(p[1])
                if name is None:
                    out.append(p)
                    continue
                if p[1] == 'Hold Click':
                    out.append('Hold')
                p = ('pad', name)
            if isinstance(p, tuple) and p[0] == 'pad':
                if out and out[-1] == p:
                    continue
                if len(out) >= 2 and out[-1] == 'or' and out[-2] == p:
                    out.pop()
                    continue
            out.append(p)
        return out

    def keycap(self, dst, label, pos, anchor='midleft', dark=False, pad=True, remap=True):
        """A little keyboard key with a label on it, or the matching controller button while one is in use.
        Returns its rect."""
        if pad and self.pad_layout and label in KEY_TO_PAD:
            return self.padcap(dst, KEY_TO_PAD[label], pos, anchor)
        if remap:
            label = self.key_labels.get(label, label)
        w = max(24, self.fonts['tiny'].size(label)[0] + 12)
        r = pygame.Rect(0, 0, snap(w + 1), 24)
        setattr(r, anchor, (int(pos[0]), int(pos[1])))
        r.x, r.y = snap(r.x), snap(r.y)
        if dark:
            face, edge = (78, 68, 84), (36, 28, 40)
            tc = (250, 240, 226)
        else:
            face, edge = (250, 242, 226), (120, 92, 70)
            tc = INK
        dst.blit(self._button_skin(r.w, r.h, face, edge, 2), r)
        self.blit_text(dst, label, (r.centerx, r.y + 2), 'tiny', tc, 'midtop')
        return r

    def rich(self, dst, parts, pos, color=(250, 244, 232), dark_keys=True, measure=False, outline=None, pad=True):
        """Draw a hint line mixing text and keycaps: parts are strings, ('key', label) or ('pad', button).
        While a controller is in use, keys are swapped for its buttons (pad=False keeps the keyboard).
        Returns width."""
        x, y = pos
        x0 = x
        if pad and self.pad_layout:
            parts = self.pad_parts(parts)
        for p in parts:
            if isinstance(p, tuple) and p[0] == 'pad':
                w = self.pad_w(p[1])
                if not measure:
                    self.padcap(dst, p[1], (x, y), 'midleft')
                x += w + 6
            elif isinstance(p, tuple):
                w = snap(max(24, self.fonts['tiny'].size(self.key_labels.get(p[1], p[1]))[0] + 12) + 1)
                if not measure:
                    self.keycap(dst, p[1], (x, y), 'midleft', dark_keys, pad=False)
                x += w + 6
            else:
                w = self.fonts['small'].size(p)[0]
                if not measure:
                    self.blit_text(dst, p, (x, y), 'small', color, 'midleft', outline=outline)
                x += w + 6
        return x - x0 - 6

    # ---------------------------------------------------------------- buttons and controls
    def set_nav_owner(self, owner):
        if owner != self.nav_owner:
            self.nav_owner = owner
            self.focus = None

    def nav_move(self, d):
        if not self.nav:
            return
        if self.focus is None:
            self.focus = 0 if d > 0 else len(self.nav) - 1
        else:
            self.focus = (self.focus + d) % len(self.nav)

    def nav_action(self):
        if self.focus is not None and 0 <= self.focus < len(self.nav):
            return self.nav[self.focus][1]
        return None

    def button(self, dst, rect, label, action, style='normal', enabled=True, font='bodyb', icon=None, sub=None,
               nav=False):
        rect = pygame.Rect(rect)
        hover = enabled and rect.collidepoint(self.mouse)
        focused = False
        if nav and enabled and action is not None:
            idx = len(self.nav)
            self.nav.append((rect, action))
            if hover and self.mouse_moved:
                self.focus = idx
            focused = self.focus == idx
            hover = focused or (hover and self.focus is None)
        if style == 'primary':
            fill, border, tc = SAGE, SAGE_D, (255, 255, 250)
        elif style == 'gold':
            fill, border, tc = GOLD, (176, 128, 44), (84, 56, 28)
        elif style == 'rose':
            fill, border, tc = ROSE, (176, 92, 88), (255, 255, 250)
        elif style == 'tab':
            fill, border, tc = (236, 222, 196), (156, 120, 92), INK
        elif style == 'tab_on':
            fill, border, tc = BROWN, BROWN_D, CREAM
        else:
            fill, border, tc = (244, 233, 212), (150, 112, 84), INK
        if not enabled:
            fill, border, tc = (214, 206, 194), (170, 156, 140), (150, 138, 126)
        if hover and style != 'tab_on':
            fill = lighten(fill, 0.14)
        rect = snap_rect(rect)
        pressed = hover and self.mouse_down and rect.collidepoint(self.mouse)
        if focused:
            fr = rect.inflate(8, 8).move(0, -2)
            pygame.draw.rect(dst, (90, 60, 30), fr.inflate(4, 4), 2)
            pygame.draw.rect(dst, (255, 214, 110), fr, 2)
        lift = 0 if (pressed or not enabled) else (2 if hover else 0)
        lip = 1 if pressed or not enabled else (3 if hover else 2)
        face = pygame.Rect(rect.x, rect.y - lift + (2 if pressed else 0), rect.w, rect.h)
        dst.blit(self._button_skin(rect.w, rect.h, fill, border, lip), face)
        face.h -= lip * 2
        cx = face.centerx
        cy = face.centery + 1 if not sub else face.centery - 10
        if icon is not None:
            iw = icon.get_width()
            tw = self.fonts[font].size(label)[0]
            total = iw + 8 + tw
            dst.blit(icon, (face.centerx - total // 2, cy - icon.get_height() // 2))
            cx = face.centerx - total // 2 + iw + 8 + tw // 2
        self.blit_text(dst, label, (cx, cy), font, tc, 'center', maxw=rect.w - 16)
        if sub:
            self.blit_text(dst, sub, (face.centerx, face.centery + 14), 'small', mix(tc, fill, 0.25), 'center')
        if enabled and action is not None:
            self.hot.append((rect, action))
        return hover

    def slider(self, dst, rect, value, enabled=True, active=False):
        """A track with a round knob. The caller registers the drag hotspot."""
        rect = snap_rect(rect)
        hover = active or rect.inflate(0, 16).collidepoint(self.mouse)
        track = pygame.Rect(rect.x, snap(rect.centery - 6), rect.w, 12)
        pygame.draw.rect(dst, (96, 66, 48), track)
        pygame.draw.rect(dst, (214, 196, 168), track.inflate(-4, -4))
        fw = snap(int((track.w - 4) * max(0.0, min(1.0, value))))
        if fw > 0:
            pygame.draw.rect(dst, SAGE if enabled else (180, 170, 160), (track.x + 2, track.y + 2, fw, track.h - 4))
            pygame.draw.rect(dst, lighten(SAGE, 0.35), (track.x + 2, track.y + 2, fw, 2))
        kx = track.x + 2 + fw
        kw = 16 if hover else 14
        knob = pygame.Rect(snap(kx - kw // 2), snap(rect.centery - 12), kw, 24)
        dst.blit(self._button_skin(knob.w, knob.h, (250, 242, 226) if enabled else (210, 200, 190), BROWN, 2), knob)
        return rect

    def segment(self, dst, rect, options, index, on_pick, enabled=True):
        """A row of mutually exclusive choices (like Off / On)."""
        rect = snap_rect(rect)
        dst.blit(self._frame(rect.w, rect.h, (222, 206, 180), (150, 112, 84), 2), rect)
        n = len(options)
        w = (rect.w - 8) / n
        for i, label in enumerate(options):
            cell = snap_rect((rect.x + 4 + i * w, rect.y + 4, w, rect.h - 8))
            hover = enabled and cell.collidepoint(self.mouse)
            if i == index:
                dst.blit(self._button_skin(cell.w, cell.h, BROWN if enabled else (170, 156, 140), BROWN_D, 2), cell)
                tc = CREAM
            else:
                if hover:
                    pygame.draw.rect(dst, (238, 226, 204), cell.inflate(-4, -4))
                tc = INK if enabled else (160, 148, 136)
            self.blit_text(dst, label, (cell.centerx, cell.centery - (1 if i == index else 0)), 'smallb', tc,
                           'center', maxw=cell.w - 8)
            if enabled and i != index:
                self.hot.append((cell, lambda i=i: on_pick(i)))
        return rect

    def tile(self, dst, rect, fill, border, selected=False):
        """A small pixel tile (inventory-slot style) with a coloured rim."""
        rect = snap_rect(rect)
        dst.blit(self._frame(rect.w, rect.h, fill, border, 2), rect)
        if selected:
            pygame.draw.rect(dst, lighten(border, 0.35), rect.inflate(-8, -8), 2)
        return rect

    def hotspot(self, rect, action):
        self.hot.append((pygame.Rect(rect), action))

    def click(self, pos):
        for rect, action in reversed(self.hot):
            if rect.collidepoint(pos):
                return action
        return None



# ---------------------------------------------------------------- icons
def coin(dst, center, r=11):
    x, y = center
    pygame.draw.circle(dst, (176, 120, 36), (x, y + 2), r)
    pygame.draw.circle(dst, GOLD, (x, y), r)
    pygame.draw.circle(dst, (250, 214, 120), (x, y), r - 3, 2)
    pygame.draw.line(dst, (255, 240, 190), (x - r // 2, y - r // 3), (x - r // 4, y - r // 2), 2)


def star(dst, center, r, color, filled=True):
    x, y = center
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    if filled:
        pygame.draw.polygon(dst, color, pts)
    pygame.draw.polygon(dst, darken(color, 0.3), pts, 1 if filled else 2)


def clover(dst, center, r=7, color=(110, 176, 96)):
    x, y = center
    for a in (-math.pi / 2, math.pi / 6, math.pi * 5 / 6):
        pygame.draw.circle(dst, color, (int(x + math.cos(a) * r * 0.7), int(y + math.sin(a) * r * 0.7)), int(r * 0.62))
    pygame.draw.line(dst, darken(color, 0.3), (x, y), (x + r // 2, y + r + 2), 2)


def envelope(dst, rect, color=(250, 244, 230)):
    r = pygame.Rect(rect)
    pygame.draw.rect(dst, color, r, border_radius=3)
    pygame.draw.rect(dst, BROWN, r, 2, border_radius=3)
    pygame.draw.lines(dst, BROWN, False, [r.topleft, (r.centerx, r.centery + 2), r.topright], 2)
    pygame.draw.circle(dst, ROSE, (r.centerx, r.centery + 3), 4)


def weather_icon(dst, center, weather, night, r=16, bg=CREAM):
    x, y = center
    if weather in ('clear',):
        if night:
            pygame.draw.circle(dst, (236, 200, 110), (x, y), r - 3)
            pygame.draw.circle(dst, bg, (x + 7, y - 5), r - 5)
            for p in ((x + 10, y + 8), (x + 13, y - 12)):
                pygame.draw.circle(dst, (236, 200, 110), p, 2)
        else:
            for i in range(8):
                a = i * math.pi / 4
                pygame.draw.line(dst, (250, 200, 80), (x + math.cos(a) * (r - 4), y + math.sin(a) * (r - 4)),
                                 (x + math.cos(a) * (r + 2), y + math.sin(a) * (r + 2)), 3)
            pygame.draw.circle(dst, (252, 210, 90), (x, y), r - 6)
        return
    if weather == 'fog':
        for i, w in enumerate((26, 32, 22)):
            pygame.draw.line(dst, (200, 206, 214), (x - w // 2, y - 8 + i * 8), (x + w // 2, y - 8 + i * 8), 4)
        return
    # cloud base for cloudy / rain / snow
    cc = (226, 230, 238) if weather == 'cloudy' else (170, 176, 192)
    if weather == 'cloudy' and not night:
        pygame.draw.circle(dst, (252, 210, 90), (x + 7, y - 7), 8)
    pygame.draw.circle(dst, cc, (x - 6, y + 1), 8)
    pygame.draw.circle(dst, cc, (x + 3, y - 3), 10)
    pygame.draw.circle(dst, cc, (x + 10, y + 3), 7)
    pygame.draw.rect(dst, cc, (x - 12, y + 1, 26, 8), border_radius=4)
    if weather == 'rain':
        for i in range(3):
            pygame.draw.line(dst, (110, 160, 230), (x - 6 + i * 7, y + 12), (x - 9 + i * 7, y + 18), 2)
    elif weather == 'snow':
        for i in range(3):
            pygame.draw.circle(dst, (255, 255, 255), (x - 6 + i * 7, y + 15), 2)


def book(dst, center, color=(166, 104, 84)):
    x, y = center
    r = pygame.Rect(0, 0, 30, 34)
    r.center = (x, y)
    pygame.draw.rect(dst, darken(color, 0.25), r.move(2, 2), border_radius=4)
    pygame.draw.rect(dst, color, r, border_radius=4)
    pygame.draw.rect(dst, (250, 240, 220), (r.right - 6, r.y + 3, 4, r.h - 6))
    pygame.draw.rect(dst, GOLD, (r.x + 7, r.y + 9, 12, 3))
    pygame.draw.line(dst, darken(color, 0.3), (r.x + 4, r.y), (r.x + 4, r.bottom - 1), 2)


def bag(dst, center):
    x, y = center
    pygame.draw.ellipse(dst, (180, 140, 90), (x - 15, y - 8, 30, 26))
    pygame.draw.ellipse(dst, (200, 160, 104), (x - 13, y - 7, 26, 22))
    pygame.draw.rect(dst, (150, 110, 70), (x - 7, y - 14, 14, 7), border_radius=3)
    coin(dst, (x, y + 4), 7)


def moon_icon(dst, center, bg):
    x, y = center
    night = (70, 78, 136)
    pygame.draw.circle(dst, (44, 48, 92), (x, y + 2), 18)
    pygame.draw.circle(dst, night, (x, y), 18)
    pygame.draw.circle(dst, (250, 228, 150), (x - 2, y + 1), 11)
    pygame.draw.circle(dst, night, (x + 4, y - 3), 9)
    for p, r in (((x + 9, y + 7), 2), ((x + 10, y - 10), 1), ((x - 9, y - 10), 1)):
        pygame.draw.circle(dst, (255, 246, 210), p, r)


def house(dst, center):
    x, y = center
    pygame.draw.rect(dst, (176, 120, 80), (x - 12, y - 2, 24, 16))
    pygame.draw.polygon(dst, (186, 84, 70), [(x - 16, y - 1), (x, y - 15), (x + 16, y - 1)])
    pygame.draw.rect(dst, (110, 74, 52), (x - 4, y + 4, 7, 10))
    pygame.draw.rect(dst, (250, 210, 120), (x + 5, y + 1, 5, 5))
    pygame.draw.rect(dst, (130, 126, 122), (x + 7, y - 13, 4, 7))


def trophy(dst, center, s=1.0, color=GOLD):
    x, y = center
    w = int(14 * s)
    pygame.draw.polygon(dst, color, [(x - w, y - w), (x + w, y - w), (x + w // 2, y + w // 3), (x - w // 2, y + w // 3)])
    pygame.draw.circle(dst, color, (x, y - w // 2), w)
    pygame.draw.rect(dst, darken(color, 0.2), (x - 2, y + w // 3, 5, int(8 * s)))
    pygame.draw.rect(dst, (120, 84, 60), (x - w // 1.5, y + w // 3 + int(8 * s), int(w * 1.4), int(6 * s)))
    pygame.draw.circle(dst, (255, 240, 190), (x - w // 3, y - w // 2), max(2, w // 4))


def medal(dst, center, earned, r=18):
    x, y = center
    rib = (196, 92, 88) if earned else (196, 186, 172)
    pygame.draw.polygon(dst, rib, [(x - 9, y - r - 8), (x - 2, y - r - 8), (x + 2, y - 4), (x - 5, y - 4)])
    pygame.draw.polygon(dst, darken(rib, 0.15), [(x + 9, y - r - 8), (x + 2, y - r - 8), (x - 2, y - 4), (x + 5, y - 4)])
    col = GOLD if earned else (212, 202, 188)
    pygame.draw.circle(dst, darken(col, 0.25), (x, y + 2), r)
    pygame.draw.circle(dst, col, (x, y), r)
    star(dst, (x, y), r * 0.6, (255, 236, 160) if earned else (226, 218, 206))


def fish_icon(dst, center, color=(110, 170, 210)):
    x, y = center
    pygame.draw.ellipse(dst, color, (x - 12, y - 6, 22, 12))
    pygame.draw.polygon(dst, color, [(x - 10, y), (x - 18, y - 7), (x - 18, y + 7)])
    pygame.draw.circle(dst, (40, 40, 50), (x + 5, y - 1), 2)


def calendar_icon(dst, center):
    x, y = center
    r = pygame.Rect(0, 0, 32, 30)
    r.center = (x, y + 2)
    pygame.draw.rect(dst, darken((236, 226, 206), 0.2), r.move(2, 2), border_radius=5)
    pygame.draw.rect(dst, (250, 244, 230), r, border_radius=5)
    pygame.draw.rect(dst, ROSE, (r.x, r.y, r.w, 9), border_top_left_radius=5, border_top_right_radius=5)
    for i in (8, 22):
        pygame.draw.rect(dst, BROWN_D, (r.x + i, r.y - 4, 3, 7), border_radius=1)
    for row in range(2):
        for col in range(4):
            pygame.draw.rect(dst, SOFT if (row, col) != (1, 2) else ROSE, (r.x + 4 + col * 7, r.y + 13 + row * 7, 4, 4))


def cake(dst, center, s=1.0):
    x, y = center
    w, h = int(22 * s), int(12 * s)
    pygame.draw.rect(dst, (236, 170, 190), (x - w // 2, y - h // 2 + 2, w, h), border_radius=3)
    pygame.draw.rect(dst, (250, 240, 236), (x - w // 2, y - h // 2 + 2, w, max(2, h // 3)), border_radius=3)
    pygame.draw.line(dst, (240, 200, 90), (x, y - h // 2 + 2), (x, y - h // 2 - int(6 * s)), 2)
    pygame.draw.circle(dst, (255, 170, 70), (x, y - h // 2 - int(8 * s)), max(2, int(3 * s)))


def boat(dst, center, s=1.0):
    x, y = center
    pygame.draw.polygon(dst, (130, 86, 58), [(x - 14 * s, y), (x + 14 * s, y), (x + 10 * s, y + 7 * s), (x - 10 * s, y + 7 * s)])
    pygame.draw.rect(dst, (232, 214, 176), (x - 8 * s, y - 9 * s, 13 * s, 9 * s))
    pygame.draw.polygon(dst, (70, 140, 150), [(x - 10 * s, y - 9 * s), (x + 7 * s, y - 9 * s), (x + 4 * s, y - 13 * s), (x - 7 * s, y - 13 * s)])
    pygame.draw.circle(dst, (250, 210, 120), (int(x - 3 * s), int(y - 5 * s)), max(1, int(2 * s)))


def rowboat(dst, center, s=1.0):
    """A little wooden rowboat with crossed oars (your boat, as opposed to Wren's houseboat)."""
    x, y = center
    oar = (196, 156, 104)
    pygame.draw.line(dst, oar, (x - 12 * s, y - 9 * s), (x + 10 * s, y + 6 * s), max(2, int(2 * s)))
    pygame.draw.line(dst, oar, (x + 12 * s, y - 9 * s), (x - 10 * s, y + 6 * s), max(2, int(2 * s)))
    for ox in (-1, 1):
        pygame.draw.ellipse(dst, darken(oar, 0.15), (x + ox * 12 * s - 3 * s, y - 12 * s, 6 * s, 6 * s))
    hull = [(x - 16 * s, y - 2 * s), (x + 16 * s, y - 3 * s), (x + 11 * s, y + 6 * s), (x - 11 * s, y + 6 * s)]
    pygame.draw.polygon(dst, (150, 104, 70), hull)
    pygame.draw.line(dst, (190, 146, 100), hull[0], hull[1], max(1, int(s)))
    pygame.draw.line(dst, (84, 126, 150), (x - 14 * s, y + 1 * s), (x + 14 * s, y), max(2, int(2 * s)))
    pygame.draw.polygon(dst, (100, 68, 48), hull, max(1, int(s)))


def meteor(dst, center, s=1.0):
    x, y = center
    for i in range(6):
        pygame.draw.circle(dst, (200 - i * 20, 210 - i * 18, 250 - i * 14), (int(x + i * 3 * s), int(y - i * 2 * s)),
                           max(1, int((4 - i * 0.5) * s)))
    star(dst, (x, y), 7 * s, (255, 240, 170))


def leaf(dst, center, color=(126, 170, 96)):
    x, y = center
    pygame.draw.ellipse(dst, color, (x - 10, y - 6, 20, 12))
    pygame.draw.line(dst, darken(color, 0.3), (x - 11, y + 3), (x + 8, y - 2), 2)


def moon_phase(dst, center, phase, r=8, bg=CREAM):
    """Moon phase icon for the calendar. phase = day % 8; 0 and 7 are full."""
    x, y = center
    off = {0: None, 7: None, 1: 1.4, 2: 0.9, 3: 0.35, 4: -0.35, 5: -0.9, 6: -1.4}[phase]
    surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    pygame.draw.circle(surf, (246, 228, 160), (r + 1, r + 1), r)
    if off is not None:
        pygame.draw.circle(surf, (96, 96, 130, 255), (int(r + 1 + off * r), r + 1), r)
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r + 1, r + 1), r)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.circle(surf, (150, 130, 90), (r + 1, r + 1), r, 1)
    dst.blit(surf, (x - r - 1, y - r - 1))
