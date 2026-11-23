"""Ice fishing at frozen Lily Cove (winter, with the Ice Auger).

A side-on view under the ice. Three phases:
  drill   hold Space / click / A to drill through the ice (once a day: the hole stays open)
  jig     move the lure up and down (W/S, arrows, mouse, stick) and tap Space to jig it. Fish near the lure's
          depth get curious, swim over, nibble, then bite: press then, not on a nibble
  reel    a calm tug of war: hold to bring it up, let go when the line shakes and the fish pulls, or it snaps
The deeper fish are rarer and need more patience. Runs under Game.overlay 'ice' with Game.icescene.
"""
import math
import random

import pygame

import actors
import look as looks
import art
import ui as U
from art import lerp_c, darken
from data import FISH_BY_ID

W, H = 640, 360
ICE_TOP, ICE_BOT = 78, 98          # the ice sheet, in world pixels
HOLE_X = 330
DEPTH_TOP, DEPTH_SPAN = 118, 222    # lure depth 0 -> y 118, depth 1 -> y 340
# what swims under the ice: (id, weight, depth range)
POOL = [('icefin', 10, (0.05, 0.5)), ('minnow', 7, (0.0, 0.35)), ('loach', 5, (0.2, 0.55)),
        ('frosttrout', 5, (0.3, 0.7)), ('pike', 3, (0.5, 0.9)), ('whitefish', 2, (0.55, 0.9)),
        ('snowcrown', 0.7, (0.8, 1.0))]


def _clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


class IceScene:
    def __init__(self, g, drilled=False, rng=None):
        self.g = g
        self.rng = rng or random.Random()
        self.state = 'jig' if drilled else 'drill'
        self.t = 0.0
        self.st = 0.0                       # time in this state
        self.drill = 0.0
        self.chips = []
        self.lure = 0.15
        self.jig_t = 0.0
        self.fish = []
        self.hooked = None
        self.holds = set()
        self.popups = []
        self.mouse_last = None
        self.reel = None
        self.done = False
        self.result = None                  # (spec, size) once landed
        for _ in range(5):
            self._spawn()

    # ------------------------------------------------------------ fish
    def _spawn(self):
        rng = self.rng
        luck = self.g.luck
        ws = [w * (1 + luck * 0.3 * (FISH_BY_ID[fid]['rarity'] - 1)) for fid, w, _ in POOL]
        fid, _, (lo, hi) = rng.choices(POOL, ws)[0]
        spec = FISH_BY_ID[fid]
        side = rng.choice((-1, 1))
        self.fish.append(dict(spec=spec, d=rng.uniform(lo, hi), lo=lo, hi=hi, x=-30.0 if side > 0 else W + 30.0,
                              vx=side * rng.uniform(14, 30) * (1.2 - spec['rarity'] * 0.1), mode='swim',
                              interest=0.0, need=0.8 + spec['rarity'] * 0.7, mt=0.0, nibbles=0))

    def lure_xy(self):
        sway = math.sin(self.t * 1.3) * 2
        y = DEPTH_TOP + self.lure * DEPTH_SPAN - (6 if self.jig_t > 0.18 else 0)
        return HOLE_X + sway, y

    def busy(self):
        return any(f['mode'] in ('come', 'nibble', 'bite') for f in self.fish)

    def _update_fish(self, dt):
        rng = self.rng
        lx, ly = self.lure_xy()
        for f in self.fish:
            m = f['mode']
            fy = DEPTH_TOP + f['d'] * DEPTH_SPAN
            if m == 'swim':
                f['x'] += f['vx'] * dt
                f['d'] = _clamp(f['d'] + math.sin(self.t * 0.7 + f['x'] * 0.02) * 0.01 * dt, f['lo'], f['hi'])
                near = abs(f['d'] - self.lure) < 0.14 and abs(f['x'] - lx) < 180
                if near and self.jig_t > 0 and not self.busy():
                    f['interest'] += dt * 2.2
                    if f['interest'] >= f['need']:
                        f['mode'], f['mt'] = 'come', 0.0
                        f['nibbles'] = rng.choice((0, 1, 1, 2, 2, 3))
                else:
                    f['interest'] = max(0.0, f['interest'] - dt * 0.15)
            elif m == 'come':
                tx = lx + (-18 if f['x'] < lx else 18)
                f['x'] += (tx - f['x']) * min(1.0, dt * 1.6)
                f['d'] += (self.lure - f['d']) * min(1.0, dt * 1.6)
                f['vx'] = abs(f['vx']) * (1 if tx > f['x'] else -1) if abs(tx - f['x']) > 2 else f['vx']
                if abs(f['x'] - tx) < 3 and abs(f['d'] - self.lure) < 0.02:
                    f['mode'], f['mt'] = 'nibble', 0.0
            elif m == 'nibble':
                f['d'] = self.lure
                f['mt'] += dt
                if f['mt'] > 0.9:
                    if f['nibbles'] > 0:
                        f['nibbles'] -= 1
                        f['mt'] = 0.0
                        self.popups.append(['nibble...', (210, 230, 240), 0.0])
                        self.g.audio.play('nibble', 0.5)
                    else:
                        f['mode'], f['mt'] = 'bite', 0.0
                        self.g.audio.play('bite', 0.8)
                        self.popups.append(['Bite! Now!', (255, 226, 120), 0.0])
            elif m == 'bite':
                f['mt'] += dt
                win = 0.75 + (0.3 if self.g.assist() else 0.0)
                if f['mt'] > win:
                    self._spook(f, 'Too slow. It swam off.')
            elif m == 'leave':
                f['x'] += f['vx'] * 2.4 * dt
                f['d'] = _clamp(f['d'] + 0.12 * dt, 0, 1)
            # off the edge: gone
        self.fish = [f for f in self.fish if -60 < f['x'] < W + 60 or f['mode'] in ('come', 'nibble', 'bite')]
        while len(self.fish) < 5:
            self._spawn()

    def _spook(self, f, text):
        f['mode'] = 'leave'
        f['vx'] = (1 if f['x'] > HOLE_X else -1) * max(20.0, abs(f['vx']))
        f['interest'] = 0.0
        if text:
            self.popups.append([text, (240, 180, 160), 0.0])

    # ------------------------------------------------------------ input
    def press(self, src='key'):
        if src in self.holds:
            return
        self.holds.add(src)
        st = self.state
        if st == 'jig':
            biting = next((f for f in self.fish if f['mode'] == 'bite'), None)
            nib = next((f for f in self.fish if f['mode'] in ('nibble', 'come')), None)
            if biting:
                self._hook(biting)
            elif nib and nib['mode'] == 'nibble':
                self._spook(nib, 'Too soon! That was only a nibble.')
            else:
                self.jig_t = 0.35
                self.g.audio.play('click', 0.4)
        elif st == 'caught' and self.st > 0.6:
            self.finish()

    def release(self, src='key'):
        self.holds.discard(src)

    def key(self, k):
        if k == pygame.K_ESCAPE:
            self.leave()
        elif k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e):
            self.press('key' if k == pygame.K_SPACE else 'enter')
            if k != pygame.K_SPACE:
                self.release('enter')

    def holding(self):
        return bool(self.holds)

    def _hook(self, f):
        self.fish.remove(f)
        spec = f['spec']
        lo, hi = spec['size']
        size = round(lo + (hi - lo) * min(1.0, self.rng.random() ** 1.6 + self.g.luck * 0.03 + self.g.boost('size')), 1)
        self.hooked = (spec, size)
        s = spec['strength']
        self.reel = dict(p=0.25, tension=0.0, phase='rest', pt=self.rng.uniform(1.0, 2.2), s=s)
        self.state, self.st = 'reel', 0.0
        self.g.audio.play('hook', 0.7)
        self.g.use_bait()

    def leave(self):
        """Esc: get up off the ice (cutting the line if something is on it)."""
        if self.state == 'reel':
            self.popups.append(['You cut the line.', (240, 180, 160), 0.0])
        self.close()

    def close(self):
        g = self.g
        self.done = True
        g.icescene = None
        if g.overlay == 'ice':
            g.overlay = None
        g.release_holds()

    def finish(self):
        spec, size = self.result
        g = self.g
        self.close()
        g.stats['ice_fish'] = g.stats.get('ice_fish', 0) + 1
        g.on_catch(dict(spec=spec, size=size))

    # ------------------------------------------------------------ update
    def update(self, dt):
        if self.done:
            return
        g = self.g
        self.t += dt
        self.st += dt
        self.jig_t = max(0.0, self.jig_t - dt)
        for p in self.popups:
            p[2] += dt
        self.popups = [p for p in self.popups if p[2] < 1.4]
        for c in self.chips:
            c[0] += c[2] * dt
            c[1] += c[3] * dt
            c[3] += 260 * dt
            c[4] -= dt
        self.chips = [c for c in self.chips if c[4] > 0]
        keys = g.keys()
        up = keys[pygame.K_w] or keys[pygame.K_UP]
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        st = self.state
        if st == 'drill':
            if self.holding():
                self.drill += dt * 0.42
                if self.rng.random() < dt * 30:
                    self.chips.append([HOLE_X + self.rng.uniform(-6, 6), ICE_TOP + 4, self.rng.uniform(-60, 60),
                                       self.rng.uniform(-110, -50), 0.6])
                if int(self.t * 8) != int((self.t - dt) * 8):
                    g.audio.play('creak', 0.25)
            if self.drill >= 1.0:
                self.state, self.st = 'jig', 0.0
                g.ice_hole = g.day
                g.audio.play('splash_small', 0.7)
                self.popups.append(['Through! Lower the lure and jig.', (210, 236, 250), 0.0])
            return
        if st == 'jig':
            if up or down:
                self.lure = _clamp(self.lure + (0.4 if down else -0.4) * dt)
                self.mouse_last = g.ui.mouse
            else:
                m = g.ui.mouse
                if self.mouse_last is not None and m != self.mouse_last:
                    sh = g.canvas.get_height()
                    wy = m[1] * H / sh
                    self.lure = _clamp((wy - DEPTH_TOP) / DEPTH_SPAN)
                self.mouse_last = m
            self._update_fish(dt)
            return
        if st == 'reel':
            self._update_fish(dt)
            r = self.reel
            r['pt'] -= dt
            hold = self.holding()
            if r['phase'] == 'rest':
                if hold:
                    r['p'] += 0.16 * dt / (0.6 + r['s'])
                    r['tension'] = max(0.0, r['tension'] - 0.3 * dt)
                else:
                    r['tension'] = max(0.0, r['tension'] - 0.8 * dt)
                if r['pt'] <= 0:
                    r['phase'], r['pt'] = 'warn', 0.55 if not g.assist() else 0.9
                    g.audio.play('warn', 0.5)
            elif r['phase'] == 'warn':
                if hold:
                    r['p'] += 0.1 * dt
                if r['pt'] <= 0:
                    r['phase'], r['pt'] = 'pull', self.rng.uniform(0.7, 1.2 + r['s'])
            else:
                if hold:
                    r['tension'] += (1.0 + r['s']) * dt
                else:
                    r['p'] -= 0.05 * dt
                if r['pt'] <= 0:
                    r['phase'], r['pt'] = 'rest', self.rng.uniform(1.0, 2.4)
            if r['tension'] >= 1.0:
                self.popups.append(['Snap! Let go when it pulls.', (240, 170, 150), 0.0])
                g.audio.play('snap', 0.6)
                self.hooked, self.reel = None, None
                self.state, self.st = 'jig', 0.0
                return
            if r['p'] <= 0:
                self.popups.append(['It slipped away.', (240, 180, 160), 0.0])
                self.hooked, self.reel = None, None
                self.state, self.st = 'jig', 0.0
                return
            if r['p'] >= 1.0:
                self.result = self.hooked
                self.state, self.st = 'caught', 0.0
                g.audio.play('splash', 0.7)
                g.audio.play('jingle2', 0.5)
            return
        if st == 'caught' and self.st > 2.5:
            self.finish()

    # ------------------------------------------------------------ the bot
    def auto(self, dt, rng, skill=0.8):
        st = self.state
        if st == 'drill':
            self.press('bot')
            return
        if st == 'jig':
            self.release('bot')
            bite = next((f for f in self.fish if f['mode'] == 'bite'), None)
            if bite and bite['mt'] > 0.15 + rng.random() * 0.3:
                self.press('bot')
                self.release('bot')
                return
            if self.busy():
                return
            target = max(self.fish, key=lambda f: f['spec']['rarity'] + rng.random())
            self.lure += _clamp(target['d'] - self.lure, -0.4 * dt, 0.4 * dt)
            if rng.random() < dt * 2.5:
                self.press('bot')
                self.release('bot')
            return
        if st == 'reel':
            r = self.reel
            want = r['phase'] == 'rest' or (r['phase'] == 'warn' and rng.random() > skill)
            if want:
                self.press('bot')
            else:
                self.release('bot')
            return
        if st == 'caught':
            self.release('bot')
            if self.st > 0.8:
                self.press('bot')

    # ------------------------------------------------------------ drawing
    def cam(self):
        return pygame.Rect(0, 0, W, H)

    def draw_world(self, frame):
        g = self.g
        env = g.env
        t = self.t
        top, mid, bot = env.sky
        for y in range(ICE_TOP):
            frame.fill(lerp_c(top, bot, y / ICE_TOP), (0, y, W, 1))
        # far shore: snowy pines
        rng = random.Random(3)
        for i in range(30):
            x = i * 23 + rng.randint(-6, 6)
            h = rng.randint(16, 30)
            col = lerp_c((40, 60, 56), env.near_amb, 0.3)
            pygame.draw.polygon(frame, col, [(x - 8, ICE_TOP - 2), (x + 8, ICE_TOP - 2), (x, ICE_TOP - 2 - h)])
            pygame.draw.polygon(frame, (236, 240, 246), [(x - 3, ICE_TOP - h + 6), (x + 3, ICE_TOP - h + 6),
                                                          (x, ICE_TOP - 2 - h)])
        # the ice sheet, seen side on
        night = env.nf
        for y in range(ICE_TOP, ICE_BOT):
            k = (y - ICE_TOP) / (ICE_BOT - ICE_TOP)
            frame.fill(lerp_c((240, 246, 252), (170, 200, 220), k), (0, y, W, 1))
        frame.fill((252, 254, 255), (0, ICE_TOP - 3, W, 4))
        # water below
        wtop = lerp_c((60, 120, 150), (14, 30, 48), night)
        wbot = lerp_c((14, 40, 60), (4, 10, 20), night)
        for y in range(ICE_BOT, H):
            frame.fill(lerp_c(wtop, wbot, (y - ICE_BOT) / (H - ICE_BOT)), (0, y, W, 1))
        # light through the hole
        if self.state != 'drill':
            shaft = pygame.Surface((90, H - ICE_BOT), pygame.SRCALPHA)
            for y in range(H - ICE_BOT):
                a = int(60 * (1 - y / (H - ICE_BOT)) * (1 - night * 0.6))
                w = 10 + y * 0.25
                shaft.fill((200, 236, 255, a), (45 - w / 2, y, w, 1))
            frame.blit(shaft, (HOLE_X - 45, ICE_BOT))
            pygame.draw.rect(frame, lerp_c(wtop, (20, 40, 60), 0.4), (HOLE_X - 9, ICE_TOP - 1, 18, ICE_BOT - ICE_TOP + 1))
        else:
            dk = int(self.drill * (ICE_BOT - ICE_TOP))
            if dk > 0:
                pygame.draw.rect(frame, (150, 180, 200), (HOLE_X - 9, ICE_TOP, 18, dk))
        # weeds and stones on the bottom
        for i in range(24):
            x = i * 28 + 8
            sw = math.sin(t * 0.8 + i) * 3
            col = lerp_c((40, 80, 60), (10, 24, 22), night)
            pygame.draw.lines(frame, col, False, [(x, H), (x + sw * 0.5, H - 14), (x + sw, H - 26 - (i % 3) * 6)], 2)
            pygame.draw.ellipse(frame, lerp_c((70, 74, 78), (20, 22, 26), night), (x + 10, H - 6, 12, 8))
        # bubbles
        for i in range(10):
            y = H - ((t * 18 + i * 37) % (H - ICE_BOT))
            frame.fill((180, 220, 240), (int(60 + i * 57 + math.sin(t + i) * 3), int(y), 2, 2))
        # fish
        for f in self.fish:
            spr = art.fish_sprite(f['spec'], 1)
            if f['vx'] < 0:
                spr = pygame.transform.flip(spr, True, False)
            y = DEPTH_TOP + f['d'] * DEPTH_SPAN
            x = f['x']
            if f['mode'] in ('nibble', 'bite'):
                x += math.sin(t * (30 if f['mode'] == 'bite' else 12)) * 1.5
            dim = spr.copy()
            k = int(255 * (0.55 + 0.45 * (1 - f['d'] * 0.7)) * (1 - night * 0.4))
            dim.fill((k, k, min(255, k + 20), 255), special_flags=pygame.BLEND_RGBA_MULT)
            frame.blit(dim, dim.get_rect(center=(int(x), int(y))))
        # the hooked fish coming up the line
        lx, ly = self.lure_xy()
        if self.state == 'reel' and self.hooked:
            r = self.reel
            fy = DEPTH_TOP + self.lure * DEPTH_SPAN
            ly = fy + (ICE_BOT + 10 - fy) * r['p']
            if r['phase'] == 'pull':
                lx += math.sin(t * 40) * 3
            spr = art.fish_sprite(self.hooked[0], 1)
            spr = pygame.transform.rotate(spr, 70 + math.sin(t * 8) * 15)
            frame.blit(spr, spr.get_rect(center=(int(lx), int(ly) + 10)))
        # line and lure
        if self.state != 'drill':
            shake = math.sin(t * 50) * 2 if any(f['mode'] == 'bite' for f in self.fish) else 0
            pygame.draw.line(frame, (230, 236, 240), (HOLE_X, ICE_TOP - 18), (int(lx + shake), int(ly)))
            if self.state in ('jig',):
                frame.fill((220, 224, 232), (int(lx + shake) - 1, int(ly), 3, 5))
                frame.fill((250, 210, 90), (int(lx + shake) - 1, int(ly) + 4, 3, 2))
                if self.jig_t > 0.2:
                    pygame.draw.circle(frame, (230, 240, 250), (int(lx), int(ly) + 2), int(6 + (0.35 - self.jig_t) * 30), 1)
        # you, kneeling by the hole, with Biscuit
        season = 3
        lk = looks.of(g)
        shirt = looks.shirt(lk, season)
        actors.draw_person(frame, HOLE_X - 22, ICE_TOP - 2, shirt, looks.hair(lk), getattr(g, 'hat', 'straw'), season,
                           1 if math.sin(t * 1.6) > 0.6 else 0, look=lk)
        pull = self.state == 'reel' and self.reel['phase'] == 'pull'
        tip = (HOLE_X + 2, ICE_TOP - 20 + (4 if pull else 0))
        pygame.draw.line(frame, (110, 80, 60), (HOLE_X - 18, ICE_TOP - 14), tip, 2)
        pygame.draw.line(frame, shirt, (HOLE_X - 21, ICE_TOP - 12), (HOLE_X - 16, ICE_TOP - 14))
        if self.state == 'drill':
            ax = HOLE_X
            spin = int(t * 20) % 2
            pygame.draw.line(frame, (110, 84, 60), (ax - 8, ICE_TOP - 22), (ax + 8, ICE_TOP - 22), 2)
            pygame.draw.line(frame, (150, 150, 160), (ax, ICE_TOP - 22), (ax, ICE_TOP + int(self.drill * 20)), 2)
            frame.fill((210, 210, 220), (ax - 2 + spin, ICE_TOP - 6, 2, 2))
        cx = HOLE_X - 50
        o, wht = looks.cat_colors(g)[:2]
        pygame.draw.ellipse(frame, o, (cx - 6, ICE_TOP - 11, 11, 9))
        pygame.draw.circle(frame, o, (cx + 4, ICE_TOP - 13), 4)
        pygame.draw.polygon(frame, o, [(cx + 1, ICE_TOP - 15), (cx + 2, ICE_TOP - 19), (cx + 4, ICE_TOP - 16)])
        pygame.draw.polygon(frame, o, [(cx + 7, ICE_TOP - 15), (cx + 6, ICE_TOP - 19), (cx + 4, ICE_TOP - 16)])
        frame.fill(wht, (cx + 2, ICE_TOP - 9, 3, 6))
        frame.fill((60, 70, 40), (cx + 2, ICE_TOP - 14, 1, 1))
        frame.fill((60, 70, 40), (cx + 5, ICE_TOP - 14, 1, 1))
        for c in self.chips:
            frame.fill((240, 248, 255), (int(c[0]), int(c[1]), 2, 2))
        if self.state == 'caught' and self.result:
            spr = art.fish_sprite(self.result[0], 1)
            k = min(1.0, self.st / 0.5)
            y = ICE_TOP - 20 - math.sin(math.pi * min(1, k)) * 30
            frame.blit(spr, spr.get_rect(center=(HOLE_X, int(y))))

    def draw_ui(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        k = sw / W
        ui.blit_text(s, 'Ice fishing at Lily Cove', (sw // 2, 26), 'h3', (255, 250, 240), 'center', (30, 30, 50))
        st = self.state
        if st == 'drill':
            ring = (int(HOLE_X * k), int((ICE_TOP - 50) * k))
            pygame.draw.circle(s, (30, 40, 60), ring, 34)
            if self.drill > 0:
                pygame.draw.arc(s, (210, 236, 255), (ring[0] - 30, ring[1] - 30, 60, 60), math.pi / 2,
                                math.pi / 2 + self.drill * 2 * math.pi, 6)
            hint = g.hint([('key', 'Hold Space'), 'or', ('key', 'Click'), 'to drill through the ice'],
                          [('pad', 'A'), 'hold to drill through the ice'])
        elif st == 'jig':
            # a depth gauge on the left
            gx, gy0, gy1 = 40, int(DEPTH_TOP * k), int((DEPTH_TOP + DEPTH_SPAN) * k)
            pygame.draw.rect(s, (30, 40, 60), (gx - 6, gy0 - 6, 12, gy1 - gy0 + 12), border_radius=6)
            ly = gy0 + int(self.lure * (gy1 - gy0))
            pygame.draw.circle(s, (250, 210, 90), (gx, ly), 9)
            ui.blit_text(s, 'Deeper fish are rarer', (gx + 18, gy1), 'small', (220, 230, 240), 'midleft', (20, 30, 40))
            hint = g.hint([('key', 'W'), ('key', 'S'), 'or the mouse to set the depth   ', ('key', 'Space'),
                           'jig, then hook on a bite   ', ('key', 'Esc'), 'leave'],
                          [('pad', 'STICK'), 'depth   ', ('pad', 'A'), 'jig, then hook on a bite   ', ('pad', 'B'),
                           'leave'])
        elif st == 'reel':
            r = self.reel
            bx, by, bw = sw // 2 - 160, sh - 150, 320
            ui.blit_text(s, 'Bringing it up', (bx, by - 24), 'smallb', (250, 244, 232), 'topleft', (30, 20, 30))
            pygame.draw.rect(s, (226, 214, 192), (bx, by, bw, 16), border_radius=8)
            pygame.draw.rect(s, (130, 206, 176), (bx, by, int(bw * _clamp(r['p'])), 16), border_radius=8)
            ui.blit_text(s, 'Line strain', (bx, by + 26), 'smallb', (250, 244, 232), 'topleft', (30, 20, 30))
            pygame.draw.rect(s, (226, 214, 192), (bx, by + 50, bw, 12), border_radius=6)
            c = lerp_c((150, 200, 160), (230, 90, 70), _clamp(r['tension']))
            pygame.draw.rect(s, c, (bx, by + 50, int(bw * _clamp(r['tension'])), 12), border_radius=6)
            if r['phase'] in ('warn', 'pull'):
                ui.blit_text(s, 'It pulls! Let go!' if r['phase'] == 'pull' else 'It is about to pull...',
                             (sw // 2, by - 60), 'h3', (255, 200, 150), 'center', (40, 20, 20))
            hint = g.hint([('key', 'Hold Space'), 'to reel, let go when it pulls'],
                          [('pad', 'A'), 'hold to reel, let go when it pulls'])
        else:
            spec, size = self.result
            ui.blit_text(s, '%s!  %.1f cm' % (spec['name'], size), (sw // 2, int(ICE_TOP * k) - 120), 'h2',
                         (255, 246, 220), 'center', (40, 30, 30))
            hint = None
        for text, col, pt in self.popups:
            a = 1 - pt / 1.4
            ui.blit_text(s, text, (int(HOLE_X * k) + 120, int(170 * k) - pt * 30), 'bodyb', col, 'midleft',
                         (20, 30, 40), alpha=255 * min(1, a * 2))
        if hint:
            w = ui.rich(s, hint, (0, 0), measure=True)
            ui.rich(s, hint, (sw // 2 - w // 2, sh - 40), (230, 236, 244), outline=(20, 30, 40))
