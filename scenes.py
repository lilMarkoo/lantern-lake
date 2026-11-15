"""Little story cutscenes: heart scenes with the Fernwick neighbours, and the lantern story at the lake.

A Cutscene runs a list of beats while Game.overlay is 'scene':
  ('walk', who, x)            start walking (town x); doesn't wait. ('walk', who, ('by', other, dx)) walks next to someone
  ('sync',)                   wait until everyone has stopped walking
  ('face', who, other)        turn to face someone ('you' or a neighbour id), or ('face', who, 1 / -1)
  ('say', who, text)          a line in the dialogue box; waits for Space / click
  ('emote', who, kind)        a bubble over their head (heart, note, bang, fish, dots)
  ('fade', caption, {who: x}) fade to black, show a caption, move people while it's dark, fade back in
  ('picture', id, caption)    show a picture in a frame until you press
  ('call', fn)                run fn(g) (rewards, story flags); also run when the scene is skipped
  ('wait', seconds)
  ('sound', name)
Town scenes move your walker and the neighbours on the street; lake scenes just play over the lake.
"""
import math
import random

import pygame

import actors
import art
import town as T
import ui as U
from art import darken, lerp_c
from data import FISH_BY_ID

ZOOM_W = 288                 # world pixels across while a town scene is zoomed in (16:9)
TYPE_SPEED = 46.0            # characters a second


class Cutscene:
    def __init__(self, g, beats, place='town', on_end=None, title=None):
        self.g = g
        self.beats = list(beats)
        self.place = place
        self.on_end = on_end
        self.title = title
        self.i = -1
        self.t = 0.0
        self.bt = 0.0
        self.bars = 0.0
        self.zoom = 0.0
        self.who = None
        self.text = ''
        self.shown = 0.0
        self.fade = 0.0
        self.fade_beat = None
        self.caption = None
        self.picture = None
        self.emotes = {}
        self.movers = {}
        self.done = False
        self.held = False
        self.focus = None            # lake scenes: the world point the camera closes in on
        self.zoom_w = 320
        self.cast = set()
        for b in self.beats:
            if b[0] in ('walk', 'say', 'face', 'emote') and b[1] not in ('you', None):
                self.cast.add(b[1])
        if place == 'town':
            g.town.scene_folk = set(self.cast)
            g.town.target, g.town.on_arrive = None, None
        self.next()

    # ------------------------------------------------------------ actors on the street
    def _pos(self, who):
        tn = self.g.town
        if who == 'you':
            return tn.x
        return tn.folk[who]['x']

    def _set(self, who, x=None, face=None, step=None):
        tn = self.g.town
        if who == 'you':
            if x is not None:
                tn.x = x
            if face is not None:
                tn.face = face
            if step is not None:
                tn.step = step
        else:
            f = tn.folk[who]
            if x is not None:
                f['x'] = x
            if face is not None:
                f['face'] = face
            if step is not None:
                f['step'] = step
            f['goal'] = None

    def _target(self, spec):
        if isinstance(spec, tuple):
            _, other, dx = spec
            return self._pos(other) + dx
        return float(spec)

    # ------------------------------------------------------------ flow
    def next(self):
        while True:
            self.i += 1
            self.bt = 0.0
            if self.i >= len(self.beats):
                self.end()
                return
            b = self.beats[self.i]
            kind = b[0]
            if kind == 'walk':
                if self.place == 'town':
                    self.movers[b[1]] = self._target(b[2])
                continue
            if kind == 'face':
                if self.place == 'town':
                    d = b[2]
                    if not isinstance(d, int):
                        d = 1 if self._pos(d) > self._pos(b[1]) else -1
                    self._set(b[1], face=d)
                continue
            if kind == 'emote':
                self.emotes[b[1]] = [b[2], 2.2]
                self.g.audio.play('ui', 0.4)
                continue
            if kind == 'call':
                b[1](self.g)
                continue
            if kind == 'sound':
                self.g.audio.play(b[1], b[2] if len(b) > 2 else 0.6)
                continue
            if kind == 'say':
                self.who, self.text, self.shown = b[1], (b[2](self.g) if callable(b[2]) else b[2]), 0.0
                self.g.audio.play('page', 0.3)
            elif kind == 'picture':
                self.picture = (b[1], b[2] if len(b) > 2 else None)
                self.g.audio.play('jingle1', 0.5)
            elif kind == 'fade':
                self.fade_beat = 'out'
                self.caption = b[1]
            return

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        self.bt += dt
        live = self.i < len(self.beats)
        self.bars += ((1.0 if live else 0.0) - self.bars) * min(1.0, dt * 5)
        self.zoom += (1.0 - self.zoom) * min(1.0, dt * 2.5)
        for k in list(self.emotes):
            self.emotes[k][1] -= dt
            if self.emotes[k][1] <= 0:
                del self.emotes[k]
        if self.place == 'town':
            for who, x in list(self.movers.items()):
                cur = self._pos(who)
                d = x - cur
                if abs(d) < 1.0:
                    self._set(who, x=x, step=0.0)
                    del self.movers[who]
                else:
                    face = 1 if d > 0 else -1
                    sp = 34.0 if who == 'you' else 26.0
                    self._set(who, x=cur + face * min(abs(d), sp * dt), face=face,
                              step=(self.g.town.step if who == 'you' else self.g.town.folk[who]['step']) + dt * 8)
        b = self.beats[self.i] if live else None
        if b is None:
            return
        kind = b[0]
        if kind == 'say':
            self.shown = min(len(self.text), self.shown + dt * TYPE_SPEED)
        elif kind == 'sync':
            if not self.movers:
                self.next()
        elif kind == 'wait':
            if self.bt >= b[1]:
                self.next()
        elif kind == 'fade':
            if self.fade_beat == 'out':
                self.fade = min(1.0, self.fade + dt / 0.6)
                if self.fade >= 1.0:
                    self.fade_beat = 'hold'
                    self.bt = 0.0
                    if self.place == 'town':
                        for who, x in (b[2] if len(b) > 2 else {}).items():
                            self._set(who, x=float(x), step=0.0)
                            self.movers.pop(who, None)
                        for who in list(self.movers):
                            self._set(who, x=self.movers.pop(who), step=0.0)
            elif self.fade_beat == 'hold':
                if self.bt > 2.4:
                    self.fade_beat = 'in'
            else:
                self.fade = max(0.0, self.fade - dt / 0.6)
                if self.fade <= 0.0:
                    self.fade_beat = None
                    self.caption = None
                    self.next()

    def press(self):
        if self.done or self.i >= len(self.beats):
            return
        kind = self.beats[self.i][0]
        if kind == 'say':
            if self.shown < len(self.text):
                self.shown = len(self.text)
            else:
                self.who = None
                self.next()
        elif kind == 'picture' and self.bt > 0.4:
            self.picture = None
            self.next()
        elif kind == 'fade' and self.fade_beat == 'hold' and self.bt > 0.5:
            self.fade_beat = 'in'

    def key(self, k):
        if k == pygame.K_ESCAPE:
            self.skip()
        elif k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
            self.press()

    def skip(self):
        """Jump to the end, but still give everything the scene gives."""
        for b in self.beats[self.i + 1:]:
            if b[0] == 'call':
                b[1](self.g)
        if self.place == 'town':
            for who, x in self.movers.items():
                self._set(who, x=x, step=0.0)
        self.movers = {}
        self.i = len(self.beats)
        self.end()

    def end(self):
        if self.done:
            return
        self.done = True
        g = self.g
        if self.place == 'town':
            g.town.scene_folk = set()
            g.town.step = 0.0
        g.scene = None
        if g.overlay == 'scene':
            g.overlay = None
        if self.on_end:
            self.on_end(g)
        g.save()

    def auto(self, dt):
        """For --bot: read at a comfortable pace."""
        if self.i >= len(self.beats):
            return
        kind = self.beats[self.i][0]
        if kind == 'say' and self.shown >= len(self.text) and self.bt > 0.6:
            self.press()
        elif kind == 'picture' and self.bt > 1.0:
            self.press()
        elif kind == 'fade' and self.fade_beat == 'hold' and self.bt > 1.0:
            self.press()

    # ------------------------------------------------------------ camera
    def cam(self, default):
        if self.place != 'town':
            f = self.focus
            if not f:
                return default
            z = self.zoom
            w = int(round((art.W + (self.zoom_w - art.W) * z) / 16)) * 16
            h = w * 9 // 16
            cx = art.W / 2 + (f[0] - art.W / 2) * z
            cy = art.H / 2 + (f[1] - art.H / 2) * z
            x = int(max(0, min(art.W - w, cx - w / 2)))
            y = int(max(0, min(art.H - h, cy - h / 2)))
            return pygame.Rect(x, y, w, h)
        g = self.g
        tn = g.town
        xs = [tn.x] + [tn.folk[k]['x'] for k in self.cast]
        mid = (min(xs) + max(xs)) / 2 - tn.scroll
        z = self.zoom
        w = int(round((art.W + (ZOOM_W - art.W) * z) / 16)) * 16
        h = w * 9 // 16
        cx = art.W / 2 + (mid - art.W / 2) * z
        cy = art.H / 2 + ((T.GROUND - 26) - art.H / 2) * z
        x = int(max(0, min(art.W - w, cx - w / 2)))
        y = int(max(0, min(art.H - h, cy - h / 2)))
        return pygame.Rect(x, y, w, h)

    # ------------------------------------------------------------ drawing
    def draw_world(self, frame):
        """Emote bubbles over heads, in world pixels."""
        if self.place != 'town':
            return
        tn = self.g.town
        for who, (kind, life) in self.emotes.items():
            x = int(self._pos(who) - tn.scroll)
            kid = who != 'you' and T.FOLK[who].get('kid')
            actors.draw_bubble(frame, x + 1, T.GROUND - (27 if kid else 33), kind, self.t)

    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        SW, SH = s.get_size()
        bh = int(round(self.bars * 56 / 2)) * 2
        if bh > 1:
            s.fill((10, 8, 12), (0, 0, SW, bh))
            s.fill((10, 8, 12), (0, SH - bh, SW, bh))
        if self.title and self.t < 3.0:
            a = int(255 * max(0.0, min(1.0, min(self.t / 0.4, (3.0 - self.t) / 0.5))))
            ui.blit_text(s, self.title, (SW // 2, 28), 'smallb', (250, 226, 170), 'center', alpha=a)
        if self.who and self.i < len(self.beats) and self.beats[self.i][0] == 'say':
            self._dialogue(s, SW, SH)
        if self.picture:
            self._picture(s, SW, SH)
        if self.fade > 0.005:
            buf = getattr(self, '_fadebuf', None)
            if buf is None or buf.get_size() != (SW, SH):
                buf = self._fadebuf = pygame.Surface((SW, SH), pygame.SRCALPHA)
            buf.fill((12, 10, 18, int(255 * self.fade)))
            s.blit(buf, (0, 0))
            if self.caption and self.fade > 0.6:
                a = int(255 * min(1.0, (self.fade - 0.6) / 0.4))
                y = SH // 2 - 16
                for ln in ui.wrap(self.caption, 'h3', SW - 260):
                    ui.blit_text(s, ln, (SW // 2, y), 'h3', (236, 226, 210), 'center', alpha=a)
                    y += 36
        parts = [('key', 'Space'), 'next    ', ('key', 'Esc'), 'skip']
        w = ui.rich(s, parts, (0, 0), measure=True)
        ui.rich(s, parts, (SW - 22 - w, SH - 30), (170, 160, 150))

    def _dialogue(self, s, SW, SH):
        g = self.g
        ui = g.ui
        rect = pygame.Rect(80, SH - 62 - 150, SW - 160, 150)
        ui.panel(s, rect, radius=18)
        pv = pygame.Rect(rect.x + 14, rect.y + 12, 126, 126)
        pygame.draw.rect(s, (226, 236, 240), pv, border_radius=12)
        pygame.draw.rect(s, (196, 170, 140), pv, 3, border_radius=12)
        clip = s.get_clip()
        s.set_clip(pv.inflate(-6, -6))
        if self.who == 'you':
            you_portrait(g, s, (pv.centerx, pv.y + 50), 4)
            name = 'You'
        else:
            T.portrait(g, s, self.who, (pv.centerx, pv.y + 50), 4)
            name = T.FOLK[self.who]['name']
        s.set_clip(clip)
        ui.blit_text(s, name, (rect.x + 164, rect.y + 14), 'bodyb', (170, 100, 70))
        text = self.text[:int(self.shown)]
        y = rect.y + 48
        for ln in ui.wrap(self.text, 'body', rect.w - 200):
            part = text[:len(ln)]
            text = text[len(ln):].lstrip(' ')
            if part:
                ui.blit_text(s, part, (rect.x + 164, y), 'body', U.INK)
            y += 30
        if self.shown >= len(self.text) and int(self.t * 2.5) % 2 == 0:
            x, yy = rect.right - 34, rect.bottom - 26
            pygame.draw.polygon(s, (170, 100, 70), [(x - 8, yy - 6), (x + 8, yy - 6), (x, yy + 4)])

    def _picture(self, s, SW, SH):
        g = self.g
        ui = g.ui
        pid, cap = self.picture
        k = min(1.0, self.bt / 0.35)
        w, h = 520, 360
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (SW // 2, SH // 2 - 30 + int((1 - k) * 30))
        pygame.draw.rect(s, (60, 40, 30), rect.inflate(28, 28), border_radius=8)
        pygame.draw.rect(s, (150, 104, 64), rect.inflate(20, 20), border_radius=6)
        pygame.draw.rect(s, (196, 146, 90), rect.inflate(20, 20), 4, border_radius=6)
        PICTURES.get(pid, _pic_blank)(g, s, rect, self.t)
        if cap:
            ui.blit_text(s, cap, (SW // 2, rect.bottom + 38), 'bodyb', (250, 240, 220), 'center',
                         outline=(30, 20, 20))


def you_portrait(g, s, center, scale=4):
    tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
    T.walker(tmp, 13, 38, 1, 0, actors.SHIRT[g.env.season], (112, 72, 52), g.hat, g.env.season)
    big = pygame.transform.scale(tmp, (26 * scale, 40 * scale))
    s.blit(big, big.get_rect(center=center))


# ---------------------------------------------------------------- the pictures
def _paper(s, rect, col=(240, 226, 196)):
    s.fill(col, rect)
    for i in range(0, rect.h, 6):
        s.fill(darken(col, 0.03), (rect.x, rect.y + i, rect.w, 2))


def _pic_blank(g, s, rect, t):
    _paper(s, rect)


def _pic_card(g, s, rect, t):
    ui = g.ui
    s.fill((120, 90, 70), rect)
    card = rect.inflate(-90, -70)
    _paper(s, card, (250, 240, 214))
    ui.blit_text(s, 'Sunny Tart', (card.x + 30, card.y + 24), 'h2', (110, 70, 60))
    lines = ['1 Honey Sunfish, 1 Bluegill', 'Butter the dish (more butter)', 'Bake till golden, not a minute more',
             'Share with someone you love']
    for i, ln in enumerate(lines):
        ui.blit_text(s, ln, (card.x + 30, card.y + 84 + i * 34), 'small', (90, 70, 100))
    ui.blit_text(s, '- Rosie', (card.right - 30, card.bottom - 36), 'bodyb', (90, 70, 100), 'topright')
    _star(s, card.right - 44, card.y + 40, 16, (240, 190, 70))


def _pic_photo(g, s, rect, t):
    sep = lambda c: (min(255, int(c * 1.05) + 40), int(c * 0.9) + 30, int(c * 0.7) + 20)
    for i in range(rect.h):
        v = 200 - int(i / rect.h * 70)
        s.fill(sep(v), (rect.x, rect.y + i, rect.w, 1))
    hy = rect.y + 150
    s.fill(sep(110), (rect.x, hy, rect.w, rect.h - 150))
    pygame.draw.ellipse(s, sep(80), (rect.x - 40, hy - 60, 260, 100))
    # young Tom in his boat, the Muskie leaping at the end of the line
    s.fill(sep(60), (rect.x + 80, hy + 70, 120, 18))
    tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
    T.walker(tmp, 13, 38, 1, 0, (100, 124, 92), (90, 70, 50), 'bucket', 1)
    big = pygame.transform.scale(tmp, (26 * 4, 40 * 4))
    big.fill((150, 130, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(big, (rect.x + 90, hy - 80))
    fish = art.fish_sprite(FISH_BY_ID['muskie'], 1)
    fish = pygame.transform.rotate(pygame.transform.scale(fish, (fish.get_width() * 5, fish.get_height() * 5)), 24)
    fish.fill((140, 120, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(fish, (rect.right - fish.get_width() - 40, hy - 70))
    pygame.draw.line(s, sep(40), (rect.x + 170, hy - 50), (rect.right - 120, hy - 10), 2)
    for _ in range(140):
        x = rect.x + (hash((_, 1)) % rect.w)
        y = rect.y + (hash((_, 2)) % rect.h)
        s.set_at((x, y), sep(230))
    g.ui.blit_text(s, 'The one that got away, 1971', (rect.centerx, rect.bottom - 30), 'small', sep(40), 'center')


def _pic_plaque(g, s, rect, t):
    ui = g.ui
    s.fill((60, 90, 110), rect)
    for i in range(0, rect.w, 40):
        pygame.draw.circle(s, (90, 130, 150), (rect.x + i + int(t * 10) % 40, rect.y + 60 + (i % 3) * 20), 4, 1)
    pl = rect.inflate(-120, -150)
    pygame.draw.rect(s, (150, 110, 40), pl.inflate(10, 10), border_radius=10)
    pygame.draw.rect(s, (226, 186, 90), pl, border_radius=8)
    ui.blit_text(s, 'THE LANTERN LAKE TANK', (pl.centerx, pl.y + 34), 'h3', (90, 60, 30), 'center')
    ui.blit_text(s, 'In honour of our finest angler', (pl.centerx, pl.y + 84), 'small', (110, 80, 40), 'center')
    ui.blit_text(s, 'and every fish they shared with us', (pl.centerx, pl.y + 112), 'small', (110, 80, 40),
                 'center')


def _pic_bracelet(g, s, rect, t):
    _paper(s, rect, (236, 230, 214))
    cx, cy = rect.center
    cols = [(90, 150, 210), (232, 150, 78), (250, 240, 228)]
    for i in range(22):
        a = i / 22 * 2 * math.pi
        x, y = cx + math.cos(a) * 110, cy + math.sin(a) * 80
        pygame.draw.circle(s, darken(cols[i % 3], 0.25), (int(x), int(y) + 3), 13)
        pygame.draw.circle(s, cols[i % 3], (int(x), int(y)), 13)
        pygame.draw.circle(s, (255, 255, 255), (int(x) - 4, int(y) - 4), 3)
    g.ui.blit_text(s, 'BFF', (cx, cy), 'h1', (200, 90, 90), 'center')


def _pic_key(g, s, rect, t):
    s.fill((120, 30, 50), rect)
    for i in range(0, rect.h, 8):
        s.fill((132, 36, 56), (rect.x, rect.y + i, rect.w, 3))
    cx, cy = rect.centerx - 90, rect.centery
    gold, dk = (240, 196, 80), (170, 120, 40)
    pygame.draw.circle(s, dk, (cx, cy + 4), 56)
    pygame.draw.circle(s, gold, (cx, cy), 56)
    pygame.draw.circle(s, (120, 30, 50), (cx, cy), 26)
    s.fill(dk, (cx + 50, cy - 10, 200, 28))
    s.fill(gold, (cx + 50, cy - 14, 200, 26))
    for x in (cx + 190, cx + 226):
        s.fill(gold, (x, cy + 10, 18, 40))
    sh = 0.5 + 0.5 * math.sin(t * 3)
    pygame.draw.line(s, (255, 250, 220), (cx - 30, cy - 40), (cx - 10 + int(10 * sh), cy - 46), 3)


def _pic_portrait(g, s, rect, t):
    """Fen's painting of you and Biscuit on the dock at golden hour (it hangs in your kitchen afterwards)."""
    paint_portrait(g, s, rect)


def paint_portrait(g, s, rect, scale=None):
    sky1, sky2 = (250, 190, 130), (150, 170, 220)
    for i in range(rect.h):
        k = i / rect.h
        c = lerp_c(sky2, sky1, min(1.0, k * 1.6)) if k < 0.55 else lerp_c((110, 150, 190), (70, 110, 150), k)
        s.fill(c, (rect.x, rect.y + i, rect.w, 1))
    hy = rect.y + int(rect.h * 0.55)
    pygame.draw.circle(s, (255, 226, 150), (rect.x + int(rect.w * 0.72), hy - 6), max(3, rect.w // 14))
    s.fill((96, 130, 90), (rect.x, hy - 4, rect.w, 6))
    for i in range(0, rect.w, max(2, rect.w // 40)):
        s.fill((250, 226, 170), (rect.x + i, hy + 8 + (i * 7) % max(1, rect.h // 3), max(1, rect.w // 50), 1))
    s.fill((150, 104, 70), (rect.x, rect.bottom - rect.h // 6, rect.w, rect.h // 6))
    sc = scale or max(1, rect.h // 60)
    tmp = pygame.Surface((26, 40), pygame.SRCALPHA)
    T.walker(tmp, 13, 38, 1, 0, actors.SHIRT[g.env.season], (112, 72, 52), g.hat, g.env.season)
    big = pygame.transform.scale(tmp, (26 * sc, 40 * sc))
    s.blit(big, big.get_rect(midbottom=(rect.x + int(rect.w * 0.38), rect.bottom - rect.h // 6 + sc * 2)))
    cat = pygame.Surface((26, 24), pygame.SRCALPHA)
    import cookscene
    cookscene.draw_cat(cat, 12, 22, 0.0, -1, True)
    bigc = pygame.transform.scale(cat, (26 * sc, 24 * sc))
    s.blit(bigc, bigc.get_rect(midbottom=(rect.x + int(rect.w * 0.6), rect.bottom - rect.h // 6 + sc)))


def _pic_map(g, s, rect, t):
    import story
    story.draw_map(g, s, rect, t)


STAR_SHAPES = [
    [(0.18, 0.62), (0.30, 0.44), (0.42, 0.40), (0.50, 0.24), (0.58, 0.40), (0.70, 0.66), (0.42, 0.40)],   # heron
    [(0.16, 0.60), (0.30, 0.42), (0.48, 0.34), (0.64, 0.38), (0.78, 0.28), (0.74, 0.50), (0.64, 0.38)],   # trout
    [(0.40, 0.70), (0.40, 0.40), (0.50, 0.22), (0.60, 0.40), (0.60, 0.70), (0.40, 0.70), (0.50, 0.50)],   # lantern
    [(0.16, 0.56), (0.30, 0.44), (0.50, 0.42), (0.66, 0.48), (0.80, 0.40), (0.84, 0.54), (0.66, 0.48)],   # bear
]


def _pic_stars(g, s, rect, t):
    for i in range(rect.h):
        f = i / rect.h
        s.fill((int(14 + 30 * f), int(18 + 34 * f), int(46 + 50 * f)), (rect.x, rect.y + i, rect.w, 1))
    rng = random.Random(7)
    for _ in range(220):
        x, y = rect.x + rng.randrange(rect.w), rect.y + rng.randrange(int(rect.h * 0.8))
        tw = 0.6 + 0.4 * math.sin(t * rng.uniform(1, 4) + rng.uniform(0, 6))
        v = int(rng.uniform(120, 250) * tw)
        s.fill((v, v, min(255, v + 20)), (x, y, 2 if rng.random() < 0.15 else 1, 2 if rng.random() < 0.15 else 1))
    # a soft band of the milky way
    band = pygame.Surface(rect.size, pygame.SRCALPHA)
    for i in range(40):
        pygame.draw.circle(band, (200, 190, 240, 6), (int(rect.w * i / 40), int(rect.h * (0.15 + 0.5 * i / 40))), 40)
    s.blit(band, rect.topleft)
    # this season's constellation, drawn in as you look
    pts = [(rect.x + px * rect.w, rect.y + py * rect.h) for px, py in STAR_SHAPES[g.env.season % 4]]
    k = min(len(pts) - 1, t * 2.2)
    for i in range(int(k)):
        pygame.draw.line(s, (170, 180, 230), pts[i], pts[i + 1], 2)
    if k < len(pts) - 1:
        i = int(k)
        a, b = pts[i], pts[i + 1]
        f = k - i
        pygame.draw.line(s, (170, 180, 230), a, (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), 2)
    for p in pts:
        pygame.draw.circle(s, (250, 246, 220), (int(p[0]), int(p[1])), 4)
        pygame.draw.circle(s, (255, 255, 255), (int(p[0]), int(p[1])), 2)
    # a shooting star now and then
    m = (t * 0.45) % 1.0
    if m < 0.35:
        f = m / 0.35
        hx, hy = rect.x + rect.w * (0.9 - 0.5 * f), rect.y + rect.h * (0.08 + 0.25 * f)
        for j in range(14):
            c = int(250 * (1 - j / 14.0))
            s.fill((c, c, c), (int(hx + j * 5), int(hy - j * 2.5), 3, 2))
    # treeline and the lake below
    hy = rect.bottom - int(rect.h * 0.18)
    s.fill((22, 30, 44), (rect.x, hy, rect.w, rect.bottom - hy))
    for x in range(rect.x, rect.right, 6):
        h = 18 + int(12 * math.sin(x * 0.05) + 8 * math.sin(x * 0.13))
        pygame.draw.polygon(s, (14, 22, 30), [(x - 6, hy), (x + 3, hy - h), (x + 12, hy)])
    for i in range(12):
        y = hy + 8 + i * 4
        if y < rect.bottom:
            s.fill((60, 70, 110), (rect.x + 30 + (i * 53) % (rect.w - 120), y, 30 + (i * 17) % 60, 1))


PICTURES = {'stars': _pic_stars, 'card': _pic_card, 'photo': _pic_photo, 'plaque': _pic_plaque, 'bracelet': _pic_bracelet,
            'key': _pic_key, 'portrait': _pic_portrait, 'map': _pic_map}


def _pic_lens(g, s, rect, t):
    import yeartwo
    yeartwo.pic_lens(g, s, rect, t)


PICTURES['lens'] = _pic_lens


def _star(s, cx, cy, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(s, col, pts)


# ---------------------------------------------------------------- heart scenes
HEART_SCENE_AT = 50          # friendship points (5 hearts)


def _reward(kind, v, text=None):
    def fn(g):
        if kind == 'recipe':
            if v not in g.recipes:
                g.recipes.append(v)
                g.toast('Rosie\'s card: you can now cook the Sunny Tart.', (200, 140, 90))
                return
            g.coins += 300
            g.toast('You already knew it, so Mabel slips you 300 coins "for butter".', (200, 140, 90))
            return
        what = g.give_reward(kind, v) if kind in ('coins', 'golden', 'storm', 'moon', 'corn', 'glow') else None
        if kind == 'tickets':
            g.tickets += v
            what = '%d ring toss tickets' % v
        g.toast(text % what if text and what else (text or 'You got %s.' % what), (220, 120, 140))
        g.audio.play('jingle3', 0.6)
    return fn


def _flag(name):
    def fn(g):
        g.story.setdefault('flags', [])
        if name not in g.story['flags']:
            g.story['flags'].append(name)
    return fn


def heart_beats(g, k):
    you = 'you'
    near = ('walk', k, ('by', you, 14))
    face = [('sync',), ('face', you, k), ('face', k, you)]
    if k == 'mabel':
        return [near] + face + [
            ('say', k, "Oh good, it's you! Come here a moment, I've something to show you."),
            ('emote', you, 'bang'),
            ('say', k, "When I was a girl, your Grandma Rosie bought a Honey Bun here every Sunday. Two, if the "
                       "fish were biting."),
            ('say', k, "She left a recipe card with my mother once. I found it in the flour bin this morning, "
                       "would you believe."),
            ('picture', 'card', "Rosie's Sunny Tart"),
            ('say', you, "That's her handwriting! She always drew a little star on the recipes she loved."),
            ('say', k, "Then it belongs with you. Bake it for someone you love, dear. That was her rule."),
            ('emote', k, 'heart'),
            ('call', _reward('recipe', 'tart')),
            ('wait', 1.0)]
    if k == 'tom':
        return [near] + face + [
            ('say', k, "Sit down a minute, kid. My knees need the excuse."),
            ('fade', 'Old Tom drags two crates out of his shop, and the two of you sit and watch the street.'),
            ('say', k, "Forty years ago I hooked the Mossback Muskie out in the Deep. Fought it till sunset."),
            ('picture', 'photo', 'Tom keeps this photo behind the counter'),
            ('say', k, "Line snapped right at the boat. It looked up at me. I swear the old thing winked."),
            ('say', you, "Do you think it's still down there?"),
            ('say', k, "I know it is. And I reckon you're the one to land it. Take my lucky lures. They never "
                       "worked for me, but they like you better."),
            ('emote', k, 'note'),
            ('call', _reward('golden', 3, 'Tom gives you %s.')),
            ('wait', 1.0)]
    if k == 'juniper':
        return [near] + face + [
            ('say', k, "Can you keep a secret? I've been making new name cards for the aquarium tanks."),
            ('say', k, "This one goes on the big tank by the window. Look!"),
            ('picture', 'plaque', None),
            ('emote', you, 'bang'),
            ('say', you, "...You named a tank after me?"),
            ('say', k, "Half the fish in there came from you! It's only fair. The fish voted. Well, I voted for "
                       "them."),
            ('emote', k, 'heart'),
            ('call', _reward('coins', 250, 'Juniper insists on %s from the aquarium fund.')),
            ('wait', 1.0)]
    if k == 'pip':
        return [('walk', k, ('by', you, 12))] + face + [
            ('say', k, "Close your eyes! No, keep them open, you'll walk into the fountain."),
            ('say', k, "I made you a friendship bracelet. It's lake blue and Biscuit orange. I ran out of green."),
            ('picture', 'bracelet', None),
            ('say', you, "It's perfect, Pip. I'll wear it every time I go fishing."),
            ('say', k, "Now we're official best friends. That means free throws at the ring toss. Forever. Mayor "
                       "Hazel can't stop me."),
            ('emote', k, 'heart'),
            ('emote', you, 'heart'),
            ('call', _reward('tickets', 15, 'Pip gives you %s.')),
            ('wait', 1.0)]
    if k == 'hazel':
        return [near] + face + [
            ('say', k, "Ahem. I have prepared a short speech in your honour. It is eleven pages."),
            ('emote', you, 'dots'),
            ('say', k, "...Fine, the short version. Fernwick was getting quiet before you came. Now the street is "
                       "busy again, and people smile at the fishmonger."),
            ('say', k, "By the powers vested in me, mostly by me, I name you an Honorary Citizen of Fernwick!"),
            ('picture', 'key', 'The Key to Fernwick'),
            ('say', k, "It doesn't open anything. But it is extremely shiny."),
            ('emote', k, 'note'),
            ('call', _reward('coins', 400, 'The town treasury gives you %s.')),
            ('wait', 1.0)]
    if k == 'fen':
        return [near] + face + [
            ('say', k, "Would you sit for me? Just for a little while. The light by the lookout is perfect today."),
            ('fade', 'Fen sets up an easel at the lookout bench. You try very hard to hold still.',
             {you: 1830, k: 1866}),
            ('face', you, k), ('face', k, you),
            ('say', k, "Stop smiling so much, it keeps changing the painting. No, keep smiling. That's the "
                       "painting."),
            ('fade', 'An hour later...'),
            ('picture', 'portrait', "Fen's painting of you and Biscuit"),
            ('say', k, "It's yours. Hang it somewhere warm. Next to a kitchen stove, I think."),
            ('emote', k, 'heart'),
            ('call', _flag('portrait')),
            ('call', lambda g: g.toast('The painting now hangs in your cabin kitchen.', (220, 120, 140))),
            ('wait', 1.0)]
    if k == 'librarian':
        return [near] + face + [
            ('say', k, "I found something in the archive that I think you should see. Quietly, please."),
            ('picture', 'map', 'A very old map of Lantern Lake'),
            ('say', k, "The lake was named for these four lanterns. Every year, they were lit for the Festival of "
                       "Lanterns, and the whole town came down to the water."),
            ('say', k, "The last keeper of the lanterns, according to the records, was a Rosie. Your grandmother."),
            ('say', you, "Grandma kept the lanterns? She never told me that..."),
            ('say', k, "Perhaps she was waiting until you loved the lake as much as she did. I think you might."),
            ('emote', k, 'heart'),
            ('call', lambda g: __import__('story').start(g)),
            ('call', _reward('coins', 300, 'Ms. Alder hands you %s "for lamp oil".')),
            ('wait', 1.0)]
    if k == 'rowan':
        import yeartwo
        return yeartwo.heart_beats(g)
    return []


def start_heart(g, k):
    g.heart_seen.append(k)
    g.stats['heart_scenes'] = g.stats.get('heart_scenes', 0) + 1
    beats = heart_beats(g, k)
    name = T.FOLK[k]['name']
    g.scene = Cutscene(g, beats, 'town', title='%s  -  5 hearts' % name)
    g.overlay = 'scene'
    g.release_holds()
    g.audio.play('wish', 0.5)
