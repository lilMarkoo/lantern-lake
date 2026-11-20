"""Gamepad support. Buttons become the same key presses the keyboard sends, and in menus and shop windows the
left stick drives a little pointer that clicks like the mouse.

Controllers SDL knows (Xbox, PlayStation, Switch Pro and most others) go through SDL's GameController mapping,
so every brand reports its buttons by position: A is the bottom face button, B the right, X the left, Y the top.
Anything else falls back to the raw joystick with the XInput layout (A0 B1 X2 Y3 LB4 RB5 Back6 Start7 LS8 RS9,
d-pad on hat 0, sticks on axes 0-3, triggers on 4-5). Each pad's brand ('xbox', 'ps' or 'switch') is worked out
from its USB vendor id and name, so the hints on screen can show its own buttons."""
import math
import os

# report Switch buttons by position too, so A is always the bottom button whatever is printed on it
os.environ.setdefault('SDL_GAMECONTROLLER_USE_BUTTON_LABELS', '0')

import pygame

try:
    import pygame._sdl2.controller as sdlc
except ImportError:                 # very old pygame: raw joysticks only
    sdlc = None

A, B, X, Y, LB, RB, BACK, START, LS, RS = range(10)
NICE = {'xbox': 'Xbox controller', 'ps': 'PlayStation controller', 'switch': 'Switch controller'}
SONY, NINTENDO = '054c', '057e'


def detect_layout(name, guid):
    """'ps', 'switch' or 'xbox' (the default: most PC pads copy the Xbox layout)."""
    n = (name or '').lower()
    vendor = ''
    if guid and len(guid) >= 12:
        vendor = (guid[10:12] + guid[8:10]).lower()       # SDL GUIDs keep the USB vendor id little-endian
    if vendor == SONY or any(k in n for k in ('playstation', 'ps3', 'ps4', 'ps5', 'dualshock', 'dualsense',
                                              'sony')):
        return 'ps'
    if vendor == NINTENDO or any(k in n for k in ('nintendo', 'switch', 'joy-con', 'joycon')):
        return 'switch'
    return 'xbox'
DEAD = 0.35
CURSOR_SPEED = 1100.0          # logical pixels a second at full tilt

# overlays the pointer is not used for: they have their own button meanings below
DIRECT = (None, 'cooking', 'scene', 'catch', 'letter', 'ringtoss', 'ice')
MENU_NAV = ('pause', 'quick')  # simple lists you step through with the d-pad
PTR_IDLE = 4.0                 # seconds before an unused pointer hides again
# the on-screen keyboard for names, addresses and chat
OSK_ROWS = ['1234567890', 'qwertyuiop', 'asdfghjkl.', "zxcvbnm:-'", ['Caps', 'Space', 'Del', 'Done']]


class Pad:
    def __init__(self, g):
        self.g = g
        self.joys = {}               # instance id -> Controller or Joystick
        self.kind = {}               # instance id -> 'ctl' (SDL mapping) or 'joy' (raw XInput layout)
        self.layouts = {}            # instance id -> 'xbox' / 'ps' / 'switch'
        self.names = {}
        self.layout = 'xbox'         # the brand of the pad used most recently
        self.last_iid = None         # ...and which pad that was (it gets the rumble)
        self.dpad = set()
        self.osk = [1, 0]            # row, column of the on-screen keyboard
        self.caps = False
        self.held = set()            # keyboard keys the pad is holding down right now
        self.cursor = None           # logical position of the pointer in windows, or None
        self.cursor_t = 0.0          # seconds since the pad last moved the pointer (it fades out when unused)
        self.a_down = None           # what pressing A started: 'mouse' or a key, so release matches
        self.rt_down = False
        self.axes = [0.0] * 6
        self.hat = (0, 0)
        self.nav_dir = (0, 0)
        self.nav_t = 0.0
        self.snap_dir = (0, 0)        # the d-pad held in a window, and the time to its next repeat
        self.snap_t = 0.0
        self.up_was = False
        try:
            if not pygame.joystick.get_init():
                pygame.joystick.init()
            if sdlc and not sdlc.get_init():
                sdlc.init()
            for i in range(pygame.joystick.get_count()):
                self._open(i, quiet=True)
        except pygame.error:
            pass
        if self.joys:
            g.last_input = 'pad'     # a pad already plugged in: show its buttons until the keyboard is used

    @property
    def connected(self):
        return bool(self.joys)

    def _open(self, index, quiet=False):
        try:
            j = pygame.joystick.Joystick(index)
            j.init()
            iid, name, guid = j.get_instance_id(), j.get_name(), j.get_guid()
        except pygame.error:
            return
        if iid in self.joys:
            return                   # already open (SDL announces pads that were plugged in at start-up too)
        dev, kind = j, 'joy'
        try:
            if sdlc and sdlc.is_controller(index):
                dev, kind = sdlc.Controller(index), 'ctl'
                name = dev.name or name
        except pygame.error:
            pass
        self.joys[iid] = dev
        self.kind[iid] = kind
        self.names[iid] = name
        self.layouts[iid] = detect_layout(name, guid)
        if not quiet:
            self._used(iid)
            self.g.toast('%s connected. The hints now show its buttons.' % NICE[self.layouts[iid]],
                         (110, 140, 170))

    def _used(self, iid):
        """This pad was just touched: show its buttons in the hints."""
        self.layout = self.layouts.get(iid, self.layout)
        self.last_iid = iid
        self.g.last_input = 'pad'

    def rumble(self, low, high, ms):
        """Shake the pad in your hands: low is the heavy motor (a fish's weight), high the light one (a buzz)."""
        dev = self.joys.get(self.last_iid)
        if dev is None and self.joys:
            dev = next(iter(self.joys.values()))
        if dev is None:
            return False
        try:
            return bool(dev.rumble(max(0.0, min(1.0, low)), max(0.0, min(1.0, high)), int(ms)))
        except (pygame.error, AttributeError, TypeError):
            return False

    # ------------------------------------------------------------ context
    def context(self):
        g = self.g
        if g.typing:
            return 'typing'
        if g.mode == 'title':
            return 'cursor' if g.overlay not in (None,) else 'menu'
        ov = g.overlay
        if ov in MENU_NAV:
            return 'menu'
        if ov in DIRECT:
            return ov or 'play'
        return 'cursor'

    def _center(self):
        c = self.g.canvas.get_size()
        return [c[0] / 2.0, c[1] / 2.0]

    # ------------------------------------------------------------ events
    def event(self, e):
        """Returns True if this was a gamepad event (handled or ignored)."""
        t = e.type
        if t == pygame.JOYDEVICEADDED:
            self._open(e.device_index)
            return True
        if t == pygame.JOYDEVICEREMOVED:
            iid = e.instance_id
            for d in (self.joys, self.kind, self.layouts, self.names):
                d.pop(iid, None)
            self.release_all()
            if not self.joys:
                self.g.last_input = 'kb'
            elif self.layouts:
                self.layout = list(self.layouts.values())[-1]
            return True
        if t in CTL_EVENTS:
            if t in (CTL_DOWN, CTL_UP):
                self._ctl_button(e, t == CTL_DOWN)
            elif t == CTL_AXIS:
                self._axis(e.instance_id, e.axis, max(-1.0, min(1.0, e.value / 32767.0)))
            return True
        if t in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            iid = getattr(e, 'instance_id', None)
            if self.kind.get(iid, 'joy') != 'joy':
                return True          # this pad talks through the controller events instead
            if t == pygame.JOYBUTTONDOWN:
                self._used(iid)
                self.button(e.button, True)
            elif t == pygame.JOYBUTTONUP:
                self.button(e.button, False)
            elif t == pygame.JOYHATMOTION:
                if e.hat == 0:
                    if e.value != (0, 0):
                        self._used(iid)
                    self.hat = e.value
                    self._dir_edge()
            else:
                self._axis(iid, e.axis, e.value)
            return True
        return False

    def _axis(self, iid, axis, v):
        if axis >= 6:
            return
        self.axes[axis] = v
        if abs(v) > 0.5:
            self._used(iid)
        if axis in (0, 1):
            self._dir_edge()
        elif axis == 5:
            self._trigger(v > 0.3)

    def _ctl_button(self, e, down):
        b = e.button
        if down:
            self._used(e.instance_id)
        if b in CTL_DPAD:
            (self.dpad.add if down else self.dpad.discard)(b)
            d = self.dpad
            self.hat = ((CTL_DPAD[3] in d) - (CTL_DPAD[2] in d), (CTL_DPAD[0] in d) - (CTL_DPAD[1] in d))
            self._dir_edge()
            return
        mine = CTL_MAP.get(b)
        if mine is not None:
            self.button(mine, down)

    def _key(self, k, down=True):
        g = self.g
        if down:
            g.key_down(k)
        else:
            g.key_up(k)

    def _hold(self, k, on):
        if on and k not in self.held:
            self.held.add(k)
            self._key(k, True)
        elif not on and k in self.held:
            self.held.discard(k)
            self._key(k, False)

    def release_all(self):
        for k in list(self.held):
            self._hold(k, False)
        if self.a_down == 'mouse':
            self.g.mouse_up()
        self.a_down = None
        self.rt_down = False

    def _trigger(self, on):
        """The right trigger is a second reel button: hold it to reel in."""
        if on == self.rt_down:
            return
        self.rt_down = on
        if self.context() in ('play', 'cooking', 'ice'):
            self._hold(pygame.K_SPACE, on)

    def pointer_on(self):
        """Is the right-stick pointer showing during play? Then A clicks where it points."""
        return self.cursor is not None and self.cursor_t < PTR_IDLE

    def button(self, b, down):
        g = self.g
        ctx = self.context()
        if ctx == 'typing':
            if down:
                self.osk_button(b)
            return
        if down and g.hide_ui and g.mode == 'play':
            if b == A:                              # photo mode: A takes a photo, X saves the screen,
                if g.place == 'lake' and g.fishing.state in ('idle', 'waiting'):     # anything else leaves
                    import wildlife
                    wildlife.snap(g)
                else:
                    g.screenshot()
            elif b == X:
                g.screenshot()
            else:
                g.hide_ui = False
            return
        if not down:
            if b == A and self.a_down is not None:
                if self.a_down == 'mouse':
                    g.mouse_up()
                else:
                    self._hold(self.a_down, False)
                self.a_down = None
            return
        if b in (B, START):
            # Start always pauses or backs out; B backs out of windows but is free during play
            if b == START or ctx not in ('play', 'scene'):
                self.release_all()
                g.key_down(pygame.K_ESCAPE)
            return
        if b == BACK and ctx in ('play', 'menu') and g.mode == 'play':
            if g.overlay == 'quick':
                g.key_down(pygame.K_ESCAPE)
            elif ctx == 'play':
                self.release_all()
                g.open_quick()
            return
        if ctx == 'cursor':
            if b == A:
                if self.cursor is None:
                    self.cursor = self._center()
                self.cursor_t = 0.0
                g.mouse_move(tuple(self.cursor))
                self.a_down = 'mouse'
                g.mouse_down(tuple(self.cursor))
            elif b == Y and g.overlay in ('journal', None):
                g.key_down(pygame.K_j)
            elif b == BACK and g.overlay == 'calendar':
                g.key_down(pygame.K_k)
            elif b == RB and g.overlay == 'lanterns':
                g.key_down(pygame.K_l)
            elif b == LB and g.overlay == 'lanterns':
                g.key_down(pygame.K_TAB)                # Lanterns / Legends
            elif b in (LB, RB) and g.overlay == 'cabin':
                g.cycle_cabin_tab(-1 if b == LB else 1)  # Fish tank / Kitchen / Home / Biscuit / Wardrobe
            return
        if ctx == 'menu':
            if b == A:
                g.key_down(pygame.K_RETURN)
            return
        if ctx == 'catch':
            k = {A: pygame.K_RETURN, X: pygame.K_t, Y: pygame.K_r}.get(b)
            if k:
                g.key_down(k)
            return
        if ctx in ('letter', 'ringtoss'):
            if b == A:
                g.key_down(pygame.K_RETURN)
            return
        if ctx in ('cooking', 'scene', 'ice'):
            if b == A:
                self.a_down = pygame.K_SPACE
                self._hold(pygame.K_SPACE, True)
            return
        # walking about and fishing
        if b == A:
            if self.pointer_on():
                # the pointer is out: click whatever it is on, just like the mouse (Biscuit, the mailbox,
                # the wagon, a shooting star, the toolbar, a shop door...)
                self.cursor_t = 0.0
                g.mouse_move(tuple(self.cursor))
                self.a_down = 'mouse'
                g.mouse_down(tuple(self.cursor))
                return
            self.a_down = pygame.K_SPACE
            self._hold(pygame.K_SPACE, True)
            return
        k = {X: pygame.K_e, Y: pygame.K_j, LB: pygame.K_TAB, RB: pygame.K_l, RS: pygame.K_t,
             LS: pygame.K_b}.get(b)
        if k:
            g.key_down(k)

    # ------------------------------------------------------------ sticks and the d-pad
    def stick(self):
        x = self.axes[0] if abs(self.axes[0]) > DEAD else 0.0
        y = self.axes[1] if abs(self.axes[1]) > DEAD else 0.0
        return x, y

    def direction(self):
        """-1/0/1 left-right and up-down from the d-pad or the left stick."""
        sx, sy = self.stick()
        dx = self.hat[0] or (1 if sx > 0.5 else -1 if sx < -0.5 else 0)
        dy = -self.hat[1] or (1 if sy > 0.5 else -1 if sy < -0.5 else 0)
        return dx, dy

    def _nav_step(self, ctx, dx, dy):
        if ctx == 'typing':
            self.osk_move(dx, dy)
        else:
            d = dy or dx
            self.g.key_down(pygame.K_DOWN if d > 0 else pygame.K_UP)

    def snap(self, dx, dy):
        """The d-pad in a window: jump the pointer to the nearest button, card or fish in that direction."""
        g = self.g
        hot = [r for r, _ in getattr(g.ui, 'hot', ()) if r.w > 4 and r.h > 4]
        if not hot:
            return False
        if self.cursor is None or not self.pointer_on():
            # the pointer was hidden: start on whatever is nearest the middle of the window
            cx, cy = self._center()
            r = min(hot, key=lambda r: math.hypot(r.centerx - cx, r.centery - cy))
            self.cursor = [float(r.centerx), float(r.centery)]
            self.cursor_t = 0.0
            g.mouse_move(tuple(self.cursor))
            return True
        px, py = self.cursor
        here = [r for r in hot if r.collidepoint(px, py)]
        if here:
            cur = min(here, key=lambda r: r.w * r.h)          # the smallest thing under the pointer
            px, py = cur.center
        seen, best, best_s = set(), None, None
        for r in hot:
            key = (r.x, r.y, r.w, r.h)
            if key in seen or r.collidepoint(px, py):
                continue
            seen.add(key)
            # measure to the nearest point of the rect, so long rows and tall columns line up sensibly
            cx = min(max(px, r.left), r.right - 1)
            cy = min(max(py, r.top), r.bottom - 1)
            vx, vy = cx - px, cy - py
            along = vx * dx + vy * dy
            if along <= 2:
                continue
            side = abs(vx * dy - vy * dx)
            if side > along * 2.5 + 40:                          # well off to the side: not "that way"
                continue
            sc = along + side * 2.2
            if best_s is None or sc < best_s:
                best, best_s = r, sc
        if best is None:
            return False
        self.cursor = [float(best.centerx), float(best.centery)]
        self.cursor_t = 0.0
        g.mouse_move(tuple(self.cursor))
        return True

    def _dir_edge(self):
        ctx = self.context()
        dx, dy = self.direction()
        if ctx == 'cursor':
            hd = (self.hat[0], -self.hat[1])
            if hd != self.snap_dir:
                self.snap_dir = hd
                self.snap_t = 0.4
                if any(hd):
                    self.snap(*hd)
            return
        if ctx in ('menu', 'typing'):
            d = (dx, dy)
            if d != self.nav_dir:
                self.nav_dir = d
                self.nav_t = 0.4
                if dx or dy:
                    self._nav_step(ctx, dx, dy)
        elif ctx == 'play':
            if (dx or dy) and self.pointer_on():
                self.cursor_t = PTR_IDLE              # walking or aiming with the left stick puts it away
            up = dy < 0
            if up and not self.up_was and self.g.place == 'town':
                self.g.key_down(pygame.K_w)          # step into a door, or talk
            self.up_was = up

    def update(self, dt):
        if not self.joys:
            return
        ctx = self.context()
        dx, dy = self.direction()
        # walking, steering the cast and the reel: the pad holds A/D like the keyboard
        walk = ctx in ('play', 'cooking') and self.g.typing is None
        self._hold(pygame.K_d, walk and dx > 0)
        self._hold(pygame.K_a, walk and dx < 0)
        ice = ctx == 'ice' and self.g.typing is None      # ice fishing: the stick sets the lure's depth
        self._hold(pygame.K_s, ice and dy > 0)
        self._hold(pygame.K_w, ice and dy < 0)
        if ctx == 'cursor' and any(self.snap_dir):
            self.snap_t -= dt
            if self.snap_t <= 0:
                self.snap_t = 0.16
                self.snap(*self.snap_dir)
        if ctx in ('menu', 'typing') and self.nav_dir and any(self.nav_dir):
            self.nav_t -= dt
            if self.nav_t <= 0:
                self.nav_t = 0.14
                self._nav_step(ctx, *self.nav_dir)
        rx = self.axes[2] if abs(self.axes[2]) > DEAD else 0.0
        ry = self.axes[3] if abs(self.axes[3]) > DEAD else 0.0
        if ctx in ('cursor', 'play'):
            if ctx == 'cursor':
                sx, sy = self.stick()          # the d-pad snaps between buttons instead (snap)
                vx, vy = sx or rx, sy or ry
            else:
                vx, vy = rx, ry                  # during play only the right stick moves the pointer
            mag = math.hypot(vx, vy)
            if mag > 0:
                if self.cursor is None:
                    self.cursor = self._center()
                sp = CURSOR_SPEED * min(1.0, mag) ** 1.6 / max(mag, 1e-6)
                w, h = self.g.canvas.get_size()
                self.cursor[0] = max(0.0, min(w - 1.0, self.cursor[0] + vx * sp * dt))
                self.cursor[1] = max(0.0, min(h - 1.0, self.cursor[1] + vy * sp * dt))
                self.cursor_t = 0.0
                self.g.mouse_move(tuple(self.cursor))
            else:
                self.cursor_t += dt
        else:
            self.cursor_t += dt

    # ------------------------------------------------------------ the on-screen keyboard
    def osk_row(self, r):
        row = OSK_ROWS[r]
        return row if isinstance(row, list) else list(row)

    def osk_move(self, dx, dy):
        r, c = self.osk
        if dy:
            old = len(self.osk_row(r))
            r = (r + dy) % len(OSK_ROWS)
            new = len(self.osk_row(r))
            c = min(new - 1, int((c + 0.5) * new / old))     # keep roughly the same spot across rows
        if dx:
            c = (c + dx) % len(self.osk_row(r))
        self.osk = [r, c]
        self.g.audio.play('ui', 0.25)

    def osk_key(self):
        r, c = self.osk
        return self.osk_row(r)[c]

    def osk_press(self, key):
        g = self.g
        if key == 'Caps':
            self.caps = not self.caps
        elif key == 'Space':
            g.type_text(' ')
        elif key == 'Del':
            g.typing_key(pygame.K_BACKSPACE)
        elif key == 'Done':
            g.typing_key(pygame.K_RETURN)
        else:
            g.type_text(key.upper() if self.caps else key)
        g.audio.play('click', 0.4)

    def osk_button(self, b):
        g = self.g
        g.last_input = 'pad'
        if b == A:
            self.osk_press(self.osk_key())
        elif b == B:
            g.typing_key(pygame.K_BACKSPACE)
        elif b == Y:
            g.type_text(' ')
        elif b == X:
            self.caps = not self.caps
        elif b == START:
            g.typing_key(pygame.K_RETURN)
        elif b == BACK:
            g.typing_key(pygame.K_ESCAPE)

    def draw_osk(self, s):
        g = self.g
        ui = g.ui
        kw, kh, gap = 50, 44, 6
        w = 10 * (kw + gap) - gap + 40
        h = len(OSK_ROWS) * (kh + gap) - gap + 92
        sw, sh = s.get_size()
        rect = pygame.Rect(sw // 2 - w // 2, sh - 16 - h, w, h)
        ui.panel(s, rect, radius=18)
        label = {'chat': 'Chat', 'mp_name': 'Your name', 'mp_addr': "Host's address"}.get(g.typing, 'Type')
        ui.blit_text(s, label, (rect.x + 20, rect.y + 14), 'smallb', (120, 90, 70))
        for r, row in enumerate(OSK_ROWS):
            keys = self.osk_row(r)
            y = rect.y + 44 + r * (kh + gap)
            if isinstance(row, list):
                bw = (w - 40 - gap * (len(keys) - 1)) // len(keys)
            else:
                bw = kw
            for c, k in enumerate(keys):
                x = rect.x + 20 + c * (bw + gap)
                on = [r, c] == self.osk
                lab = k.upper() if self.caps and len(k) == 1 else k
                if k == 'Caps' and self.caps:
                    lab = 'CAPS'
                fill = (250, 214, 130) if on else (246, 238, 222)
                pygame.draw.rect(s, (90, 64, 50), (x, y, bw, kh), border_radius=8)
                pygame.draw.rect(s, fill, (x + 2, y + 2, bw - 4, kh - 6), border_radius=7)
                ui.blit_text(s, lab, (x + bw // 2, y + kh // 2 - 2), 'bodyb' if len(k) == 1 else 'smallb',
                             (60, 40, 36), 'center')
        hint = [('pad', 'A'), 'type   ', ('pad', 'B'), 'delete   ', ('pad', 'Y'), 'space   ', ('pad', 'X'),
                'caps   ', ('pad', 'START'), 'done']
        hw = ui.rich(s, hint, (0, 0), measure=True)
        ui.rich(s, hint, (rect.centerx - hw // 2, rect.bottom - 24), (110, 90, 80))

    def keys(self, real):
        return PadKeys(real, self.held) if self.held else real

    # ------------------------------------------------------------ drawing the pointer
    def draw(self, s):
        if self.g.typing and self.g.last_input == 'pad':
            self.draw_osk(s)
            return
        if self.cursor is None or self.context() not in ('cursor', 'play') or self.cursor_t > PTR_IDLE:
            return
        if self.g.hide_ui:
            return
        x, y = int(self.cursor[0]), int(self.cursor[1])
        pts = [(x, y), (x, y + 30), (x + 8, y + 23), (x + 14, y + 36), (x + 20, y + 33), (x + 14, y + 21),
               (x + 24, y + 20)]
        pygame.draw.polygon(s, (255, 250, 236), pts)
        pygame.draw.polygon(s, (60, 40, 50), pts, 3)


if hasattr(pygame, 'CONTROLLERBUTTONDOWN'):
    CTL_DOWN, CTL_UP, CTL_AXIS = pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP, pygame.CONTROLLERAXISMOTION
    CTL_EVENTS = {CTL_DOWN, CTL_UP, CTL_AXIS, pygame.CONTROLLERDEVICEADDED, pygame.CONTROLLERDEVICEREMOVED,
                  pygame.CONTROLLERDEVICEREMAPPED}
    CTL_MAP = {pygame.CONTROLLER_BUTTON_A: A, pygame.CONTROLLER_BUTTON_B: B, pygame.CONTROLLER_BUTTON_X: X,
               pygame.CONTROLLER_BUTTON_Y: Y, pygame.CONTROLLER_BUTTON_LEFTSHOULDER: LB,
               pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: RB, pygame.CONTROLLER_BUTTON_BACK: BACK,
               pygame.CONTROLLER_BUTTON_START: START, pygame.CONTROLLER_BUTTON_LEFTSTICK: LS,
               pygame.CONTROLLER_BUTTON_RIGHTSTICK: RS}
    # up, down, left, right
    CTL_DPAD = (pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_DPAD_DOWN,
                pygame.CONTROLLER_BUTTON_DPAD_LEFT, pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
else:
    CTL_DOWN = CTL_UP = CTL_AXIS = -1
    CTL_EVENTS, CTL_MAP, CTL_DPAD = set(), {}, ()


class PadKeys:
    """pygame.key.get_pressed() with the gamepad's held keys mixed in."""
    def __init__(self, real, held):
        self.real = real
        self.held = held

    def __getitem__(self, k):
        return self.real[k] or k in self.held
