"""Lantern Lake - a cozy fishing game.

Run:  E:\\Phyton\\python.exe main.py
Test: E:\\Phyton\\python.exe main.py --shots <dir>   (headless screenshots)
      E:\\Phyton\\python.exe main.py --bot <seconds> (headless auto-fishing soak test)
"""
import json
import math
import os
import random
import sys
import time

HEADLESS = '--shots' in sys.argv or '--bot' in sys.argv
if HEADLESS:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
SHOT_SIZE = (1280, 720)
if '--size' in sys.argv:
    _w, _h = sys.argv[sys.argv.index('--size') + 1].lower().split('x')
    SHOT_SIZE = (int(_w), int(_h))
if not HEADLESS and sys.platform == 'win32':
    # draw at the real pixel size on scaled Windows displays instead of being stretched (blurry) by Windows. Per
    # monitor, so it stays sharp when the window moves to another screen or the Windows scale changes mid-game
    os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS', 'permonitorv2')
    try:
        import ctypes
        try:
            if not ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame

try:
    pygame.mixer.pre_init(44100, -16, 2, 512, allowedchanges=0)   # force stereo even on surround devices
except TypeError:
    pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

import actors
import almanac
import art
import minigame
import net as netmod
import pixfont
import town as townmod
import kitchen as kitchenmod
import cookscene
import scenes as scenemod
import story
import legends
import seasons
import biscuit
import home as homemod
import yeartwo
import binds as bindsmod
import tutorial
import coop
import screen as screenmod
import creator
import look as looks
import garden as gardenmod
import cabinui
import hatchery
import dungeon
import morphs
import wildlife
import shore as shoremod
import discover
import aquarium as aqmod
import coast
import harbour as hbmod
import goals as goalmod
import radio as radiomod
import news
import farshore as farmod
import club as clubmod
import stall as stallmod
import truck as truckmod
import drive as drivemod
import areas as areamod
import pad as padmod
import lakelife
import lakeshow
import fishing as fishmod
import ui as U
from art import W, H, DECK_Y
from audio import Audio
from data import (FISH, FISH_BY_ID, ALL_BY_ID, LETTERS, VILLAGERS, REQUEST_REASONS, RODS, ROD_BY_ID, BAITS,
                  BAIT_BY_ID, DECOR, GEAR, SEASONS, DAYS_PER_SEASON, MINUTES_PER_SECOND, RARITY_NAMES,
                  RARITY_COLORS, BADGES, TANK_SIZE, WEEKDAYS, HATS, HAT_BY_ID, CAT_ITEMS, CAT_BY_ID, GIFT_DECOR,
                  FESTIVALS, WAGON_DAYS, FROST_POINTS, METEOR_DAY, FESTIVAL_DAY, FISH_RUN_DAY, SPOT_BY_ID,
                  fish_at, spots_of, BOAT)
import tank as tankmod
from data import LAKE_SPOTS, COAST_SPOTS, COAST_IDS, SEA_FISH, HOLLOW_FISH, ROAD_FISH
from fishing import Fishing, PLAYER_X, HAND, cast_point, aim_for, clamp, spot_depth
from world import World, Env, WAGON_RECT, CROSS_POS, cross_at

# where a new dock decoration sits, so the game can point at it when it arrives
DOCK_PROP_POS = {'bench': (156, DECK_Y - 12), 'pinwheel': (197, DECK_Y - 14), 'lantern': (104, 246),
                 'lanterns': (330, 300), 'telescope': (89, 222), 'feeder': (44, 222), 'chimes': (104, 252),
                 'flowers': (120, DECK_Y - 4), 'gnome': (112, DECK_Y - 4), 'catbed': (206, DECK_Y - 6),
                 'teaset': (170, DECK_Y - 6), 'lights': (180, 252)}

SW, SH = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(HERE, 'save.json')
SETTINGS_PATH = os.path.join(HERE, 'settings.json')


def version_info():
    """version.json: the version, its release notes and the short highlights for the What's new card."""
    try:
        with open(os.path.join(HERE, 'version.json'), encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _game_version():
    return str(version_info().get('version', '')) or '1.5.0'


GAME_VERSION = _game_version()
WINDOW_SIZES = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]
FPS_CHOICES = [30, 60, 120, 144, 0]       # 0: match the screen (vsync)
FPS_LABELS = ['30', '60', '120', '144', 'Screen']
SCALINGS = ('auto', 'sharp', 'fill')
FX_LEVELS = ('simple', 'auto', 'full')
SHAKE_LEVELS = [0.0, 0.5, 1.0]
DAY_SPEEDS = [0.7, 1.0, 1.5]
UI_SCALES = [50, 60, 67, 75, 85, 100, 110]      # interface size, percent (100 = the 1280x720 layout)
DEFAULT_SETTINGS = dict(master=1.0, music=0.5, sfx=0.8, amb=0.8, assist=False, fullscreen=False, window=None,
                        fps=0, show_fps=False, scaling='auto', shake=1.0, zoom=True, hints=True, clock24=False, speed=1.0,
                        bg_pause=True, ui_scale=100, mp_name='', mp_addr='', slot=1, prompts='auto',
                        tutorial=True, binds={}, hud='clean', radio=None, rumble=True,
                        radio_vol=0.5, fx='auto')
HUD_STYLES = ('full', 'calm', 'compact', 'clean')
PROMPTS = ['auto', 'keyboard', 'xbox', 'ps', 'switch']
PROMPT_LABELS = ['Auto', 'Keyboard', 'Xbox', 'PS', 'Switch']
SLOTS = (1, 2, 3)


MARKET_FULL = 5        # this many of one fish a day sell at full price...
MARKET_DROP = 0.08     # ...then each one after fetches 8% less...
MARKET_FLOOR = 0.5     # ...down to half price
DISH_FULL = 3          # Old Tom pays full price for three dishes a day
DISH_DROP = 0.8
DISH_FLOOR = 0.35


def market_mult(nth):
    return max(MARKET_FLOOR, 1.0 - MARKET_DROP * max(0, nth + 1 - MARKET_FULL))


def dish_mult(nth):
    return max(DISH_FLOOR, DISH_DROP ** max(0, nth + 1 - DISH_FULL))


def slot_path(n):
    """Slot 1 is the old save.json, so saves from before slots existed carry straight on."""
    return os.path.join(HERE, 'save.json' if n == 1 else 'save%d.json' % n)
CLOCK24 = [False]
BAR_COLOR = (16, 14, 24)
WEATHERS = ('clear', 'cloudy', 'rain', 'fog', 'snow')
FISH_STATES = ('idle', 'charging', 'casting', 'waiting', 'bite', 'fight', 'landing', 'caught', 'reel_back')
SYS_C = (150, 140, 160)          # colour of "so-and-so came to fish" chat lines


def clip_put(text):
    """Copy text to the clipboard. True when it worked."""
    try:
        import pygame.scrap
        pygame.scrap.put_text(text)
        return True
    except Exception:
        return False


def clip_get():
    try:
        import pygame.scrap
        return pygame.scrap.get_text() or ''
    except Exception:
        return ''
NET_ARGS = dict(host='--host' in sys.argv, join=None, port=netmod.PORT, name=None, speed=None)
for _flag, _key, _conv in (('--join', 'join', str), ('--port', 'port', int), ('--name', 'name', str),
                           ('--speed', 'speed', float)):
    if _flag in sys.argv:
        NET_ARGS[_key] = _conv(sys.argv[sys.argv.index(_flag) + 1])


def _num(v, default, lo, hi):
    """A number from the network, or the default when it is missing or silly."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    if v != v:
        return default
    return max(lo, min(hi, v))


def ui_grid(pct):
    """Size of the interface canvas for a UI scale: always exactly 16:9 and a whole number of 2-px art pixels."""
    m = int(round(4000 / pct))
    return 32 * m, 18 * m

WEATHER_TABLE = {
    0: [('clear', .40), ('cloudy', .25), ('rain', .22), ('fog', .13)],
    1: [('clear', .58), ('cloudy', .15), ('rain', .17), ('fog', .10)],
    2: [('clear', .34), ('cloudy', .30), ('rain', .21), ('fog', .15)],
    3: [('clear', .34), ('cloudy', .24), ('snow', .30), ('fog', .12)],
}
INTRO = ("Dear little minnow,",
         "The cabin by Lantern Lake is yours now. The kettle still works, the dock creaks in all the right "
         "places, and the cat came with the house. She answers to Biscuit, mostly.\n"
         "I've left my rocking chair and a few bits and pieces inside. Make it yours. The rest you'll pick up as "
         "you go: the lake is a good teacher.\n"
         "Take it slow. The lake isn't going anywhere.",
         "- Grandma Rosie")


def fmt_clock(minute):
    m = int(minute) // 10 * 10
    h, mm = divmod(m, 60)
    h %= 24
    if CLOCK24[0]:
        return '%02d:%02d' % (h, mm)
    ap = 'AM' if h < 12 else 'PM'
    h12 = h % 12 or 12
    return '%d:%02d %s' % (h12, mm, ap)


CABIN_TABS = (('tank', 'Fish tank'), ('kitchen', 'Kitchen'), ('garden', 'Garden'), ('hatchery', 'Hatchery'),
              ('home', 'Home'), ('biscuit', 'Biscuit'), ('wardrobe', 'Wardrobe'))


class Game:
    def __init__(self):
        self.settings = self.load_settings()
        self.fullscreen = False
        self.drag = None
        self.opt_tab = 'audio'
        self.options_from = None
        self.tracked = None          # which objective the HUD card follows (None: the most urgent)
        self.hud_tuck = 0.0          # 0 = toolbar shown, 1 = tucked away while a cast is out
        self.hud_calm = 0.0          # 1 = the cards have faded right back: just you, the water and the bobber
        self._hud_layer = None
        self._hud_t = 0.0
        self._dock_n = 6
        self.show_help = False       # F1 / ?: the key hints and tips come back after day one
        self.menu_open = False       # calm HUD: the menu tile is unfolded into the full toolbar
        self._goal_slim = False      # the objective card shrinks to one line while a cast is out
        self._hud_wake = 0.0         # calm HUD: when something last changed (it wakes the cards)
        self._wake_sig = None
        self._bufs = {}
        self._ui_pct = None
        self._small = pygame.Surface((W, H), 0, 32)
        self._wsmall = pygame.Surface((W, H), 0, 32)
        self.gpu = None              # screen.Screen when the graphics card draws the frames
        self.fx_low = False          # Light effects on Auto: eased off because frames were running slow
        self._perf = [0.0, 0.0, 0.0]  # average frame work (s), seconds over budget, seconds well under
        self.apply_ui_scale()
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError):
            dw, dh = 1920, 1080
        self.desktop = (dw, dh)
        self.win_sizes = [s for s in WINDOW_SIZES if s[0] <= dw and s[1] <= dh - 60] or [WINDOW_SIZES[0]]
        self.open_window()
        self.screen = self.window
        if self.gpu is None:
            pygame.display.set_caption('Lantern Lake')
        self._icon()
        self.frame = pygame.Surface((W, H))
        self.ui = U.UI()
        self._ui_pct = None
        self.apply_ui_scale()                  # the GPU path keeps the interface on its own layer
        self._loading()
        self.audio = Audio()
        self.radio = radiomod.Radio(self)
        radiomod.fmt_clock = fmt_clock
        self.pad = None
        self.last_input = 'kb'       # 'kb' or 'pad': which one the hints on screen should show
        self.env = Env()
        self.world = World()
        self.town = townmod.Town()
        self.place = 'lake'          # 'lake' or 'town'
        self.place_to = None
        self.fishing = Fishing(self)
        self.net = netmod.Net(set(pixfont.GLYPHS))
        self.solo = None             # your own calendar, kept safe while you visit a friend's lake
        self.visit_shore = None      # the host's shore while you visit (shore.py)
        self.shore_sel = 'reeds'
        self.coop_tab = 'gifts'
        self.l_page = 0              # the journal's Letters tab: 0 letters, 1 Rosie's diary
        self.b_page = 0              # the journal's Badges tab page
        self.host_clock = None       # guest: [host minutes, when heard, minutes per second]
        self.clock_jumps = 0
        self.chat = []               # [name, text, colour, seconds left]
        self.typing = None           # None, 'chat', 'mp_name' or 'mp_addr'
        self.chat_text = ''
        self.emote = None            # [kind, seconds left]
        self.mp_ready = False        # voted to rest for the night
        self.lobby_msg = ''
        self.online_seen = None      # the last internet state we told the host about (portmap.Opener.state)
        self.net_send_t = 0.0
        self.net_world_t = 0.0
        self.clock = pygame.time.Clock()
        self.mode = 'title'
        self.overlay = None
        self.queue = []
        self.toasts = []
        self.toast_q = []            # toasts waiting their turn (two show at a time at most)
        self.quick_pop = None        # a repeat common catch: a little note in the corner instead of the full card
        self.mouse_hold = False
        self.space_hold = False
        self.holding = False
        self.hide_ui = False
        self.critter_rng = random.Random()
        self.snap_flash = 0.0        # photo mode (wildlife.py): the flash and the photo card
        self.snap_card = None
        self.n_sel = 0               # the Nature page's chosen animal
        self.garden_sel = None       # the Garden tab's chosen bed
        self.hatch_sel = None        # the Hatchery tab's chosen pond fish
        self.garden_fx = 0.0
        self.fade = 1.0
        self.fade_dir = -1
        self.rest_phase = None
        self.confirm_new = 0
        self.crossing = None
        self.spot_mark = None         # something new on the dock: a bouncing arrow over it for a few seconds          # rowing between spots: you see the boat cross the lake
        self.card = None
        self.letter = None
        self.j_tab = 'fish'
        self.j_sel = 0
        self.j_page = 0
        self.map_sel = 'cove'
        self.travel_to = None
        self._mapcache = {}
        self.shop_tab = 'sell'
        self.cat = dict(sleep=False, excited=0.0, pet=0.0, z=0.0)
        self.tankview = tankmod.Tank()
        self.tank_sel = None
        self.cabin_tab = 'tank'
        self.ward_hover = None
        self.cal_off = 0
        self.cal_sel = 1
        self.steer_mode = 'mouse'
        self.mouse_acc = 0           # how far the mouse has really travelled since the keys last steered
        self.bot_aim = None
        self.cam = [1.0, W / 2, H / 2]
        self.cam_look = 0.35         # where the resting view looks along the shore (0 the cabin .. 1 the far side)
        self.cam_rect = pygame.Rect(0, 0, W, H)
        self.cam_f = (0.0, 0.0, float(W), float(H))
        self.shake_amt = 0.0
        self._jcache = {}
        self.save_t = 60
        self.t = 0.0
        self.running = True
        self.new_game_state()
        self.slot_del = None
        if not HEADLESS:
            self.use_slot(self.settings.get('slot', 1))
        self.has_save = self.load()
        self.env.minute = self.minute
        self.env.day = self.day
        self.env.season = self.season_of(self.day)
        self.env.weather = self.weather
        self.env.settle()
        self.apply_settings()
        self.view_info = self.calc_view()

    # ------------------------------------------------------------ setup / persistence
    def _icon(self):
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(s, (40, 50, 90), (16, 16), 15)
        pygame.draw.rect(s, (255, 200, 110), (12, 9, 8, 11))
        pygame.draw.rect(s, (90, 70, 60), (11, 7, 10, 2))
        pygame.draw.rect(s, (90, 70, 60), (11, 20, 10, 2))
        pygame.draw.line(s, (90, 70, 60), (16, 4), (16, 7), 2)
        if self.gpu:
            self.gpu.set_icon(s)
        else:
            pygame.display.set_icon(s)

    def _loading(self):
        win = pygame.Surface(self.gpu.size) if self.gpu else pygame.display.get_surface()
        win.fill((26, 24, 40))
        cx, cy = win.get_width() // 2, win.get_height() // 2
        self.ui.blit_text(win, 'Lantern Lake', (cx, cy - 20), 'title', (248, 230, 200), 'center')
        self.ui.blit_text(win, 'tuning the crickets...', (cx, cy + 70), 'body', (200, 190, 200), 'center')
        if self.gpu:
            self.gpu.show_surface(win)
        else:
            pygame.display.flip()

    # ------------------------------------------------------------ window, fullscreen and settings
    def default_window(self):
        dw, dh = self.desktop
        best = WINDOW_SIZES[0]
        for w, h in WINDOW_SIZES:
            if w % W == 0 and w <= dw * 0.88 and h <= dh * 0.86:
                best = (w, h)
        return best

    def open_window(self):
        if HEADLESS:
            self.window = pygame.display.set_mode(SHOT_SIZE)
            return
        size = tuple(self.settings.get('window') or self.default_window())
        self.gpu = None
        if os.environ.get('LANTERN_CPU') != '1':
            try:
                self.gpu = screenmod.Screen('Lantern Lake', size, vsync=self.settings.get('fps') == 0)
            except Exception as e:                       # no usable graphics card: draw on the CPU instead
                print('drawing on the CPU:', e)
                self.gpu = None
        if self.gpu:
            # a tiny hidden window only so pictures can be convert()ed to the screen's format
            pygame.display.set_mode((1, 1), pygame.HIDDEN)
            self.gpu.window.focus()
            self.window = None
        else:
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        if self.settings.get('fullscreen'):
            self.set_fullscreen(True, save=False)

    def set_fullscreen(self, on, save=True):
        on = bool(on)
        if self.gpu and on != self.fullscreen:
            try:
                self.gpu.set_fullscreen(on, self.settings.get('window') or self.default_window())
            except pygame.error as e:
                print('fullscreen failed', e)
                return
        elif not HEADLESS and on != self.fullscreen:
            try:
                win = pygame.Window.from_display_module()
            except Exception:
                win = None
            try:
                if win is None:
                    pygame.display.toggle_fullscreen()
                elif on:
                    win.set_fullscreen(desktop=True)
                else:
                    win.set_windowed()
                    win.size = tuple(self.settings.get('window') or self.default_window())
                    win.position = pygame.WINDOWPOS_CENTERED
            except pygame.error as e:
                print('fullscreen failed', e)
                return
            self.window = pygame.display.get_surface()
        self.fullscreen = on
        self.settings['fullscreen'] = on
        if save:
            self.save_settings()

    def set_window_size(self, i):
        size = self.win_sizes[i]
        self.settings['window'] = list(size)
        self.save_settings()
        if self.gpu and not self.fullscreen:
            self.gpu.set_size(size)
        elif not HEADLESS and not self.fullscreen:
            self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
            try:
                pygame.Window.from_display_module().position = pygame.WINDOWPOS_CENTERED
            except Exception:
                pass
        self.audio.play('ui', 0.6)

    def load_settings(self):
        st = dict(DEFAULT_SETTINGS)
        if HEADLESS:
            if '--ui' in sys.argv:
                st['ui_scale'] = int(sys.argv[sys.argv.index('--ui') + 1])
            return st
        for path, key in ((SETTINGS_PATH, None), (SAVE_PATH, 'settings')):
            try:
                with open(path, encoding='utf-8') as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            d = d.get(key) if key else d
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in st:
                        st[k] = v
                break
        for k in ('master', 'music', 'sfx', 'amb', 'radio_vol'):
            try:
                st[k] = max(0.0, min(1.0, float(st[k])))
            except (TypeError, ValueError):
                st[k] = DEFAULT_SETTINGS[k]
        if st['fps'] not in FPS_CHOICES:
            st['fps'] = 0
        if st.get('scaling') not in SCALINGS:
            st['scaling'] = 'auto'
        if st['shake'] not in SHAKE_LEVELS:
            st['shake'] = 1.0
        if st.get('fx') not in FX_LEVELS:
            st['fx'] = 'auto'
        if st.get('radio') not in radiomod.BY_ID:
            st['radio'] = None
        if st['speed'] not in DAY_SPEEDS:
            st['speed'] = 1.0
        if st['ui_scale'] not in UI_SCALES:
            st['ui_scale'] = 100
        if st.get('hud_v', 1) < 2:
            if st.get('hud', 'calm') == 'calm':
                st['hud'] = 'clean'          # 0.3.9: the old default becomes the new, tidier one
            st['hud_v'] = 2
        if st.get('slot') not in SLOTS:
            st['slot'] = 1
        if st.get('prompts') not in PROMPTS:
            st['prompts'] = 'auto'
        st['binds'] = bindsmod.clean(st.get('binds'))
        st['tutorial'] = bool(st.get('tutorial', True))
        for k in ('mp_name', 'mp_addr'):
            st[k] = netmod.clean_text(st.get(k) or '', 40, set(pixfont.GLYPHS))
        w = st.get('window')
        if not (isinstance(w, list) and len(w) == 2 and tuple(w) in WINDOW_SIZES):
            st['window'] = None
        return st

    def save_settings(self):
        if HEADLESS:
            return
        try:
            tmp = SETTINGS_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=1)
            os.replace(tmp, SETTINGS_PATH)
        except OSError as e:
            print('settings save failed', e)

    def calc_view(self):
        """Where the 1280x720 picture goes in the real window: (window, rect, scale).
        Pixel scaling 'sharp' keeps every art pixel a whole number of screen pixels (a border fills the rest),
        'fill' uses all the room it can, and 'auto' is sharp unless that would waste much of the window."""
        win = None if self.gpu else pygame.display.get_surface()
        ww, wh = self.gpu.size if self.gpu else win.get_size()
        n = int(min(ww / W, wh / H))
        mode = self.settings.get('scaling', 'auto')
        if n >= 1 and mode != 'fill' and (mode == 'sharp' or W * n >= 0.85 * min(ww, wh * W / H)):
            dw, dh = W * n, H * n
            return win, pygame.Rect((ww - dw) // 2, (wh - dh) // 2, dw, dh), dw / SW
        k = max(0.05, min(ww / SW, wh / SH))
        dw, dh = max(1, min(ww, int(round(SW * k)))), max(1, min(wh, int(round(SH * k))))
        return win, pygame.Rect((ww - dw) // 2, (wh - dh) // 2, dw, dh), k

    def to_logical(self, pos):
        _, view, k = self.view_info
        return (int((pos[0] - view.x) / k), int((pos[1] - view.y) / k))

    def _buf(self, key, size, alpha=False):
        b = self._bufs.get(key)
        if b is None or b.get_size() != size:
            b = self._bufs[key] = pygame.Surface(size, pygame.SRCALPHA if alpha else 0, 32)
        return b

    def _buf_atleast(self, key, size):
        """A buffer of exactly `size`, cut from one that only grows (sizes that change every frame, like a zooming
        camera's, then cost nothing to make)."""
        b = self._bufs.get(key)
        if b is None or b.get_width() < size[0] or b.get_height() < size[1]:
            b = self._bufs[key] = pygame.Surface((size[0] + 24, size[1] + 24), 0, 32)
        return b.subsurface((0, 0, size[0], size[1]))

    def _scale_into(self, src, dst, key):
        """Blow a pixel-grid picture up onto dst with square pixels."""
        sw, sh = src.get_size()
        size = dst.get_size()
        if (size[0] % sw == 0 and size[1] % sh == 0) or screenmod.hard_ok(size[0] / sw):
            pygame.transform.scale(src, size, dst)                 # whole-number or big zoom: hard, crisp pixels
        elif size[0] < sw:
            pygame.transform.smoothscale(src, size, dst)
        else:
            # "sharp bilinear": grow by the biggest whole number that fits with hard pixels, then one smooth
            # stretch for the rest (edges stay within a pixel, so it reads sharp)
            n = max(1, size[0] // sw)
            big = self._buf(key + 'big', (sw * n, sh * n), bool(src.get_flags() & pygame.SRCALPHA))
            pygame.transform.scale(src, big.get_size(), big)
            pygame.transform.smoothscale(big, size, dst)

    def _world_into(self, out):
        """Scale what the camera sees onto the window. The camera's position and zoom aren't rounded to art
        pixels, so a zoom or a pan moves smoothly instead of jumping a whole (big) pixel at a time."""
        xf, yf, wf, hf = self.cam_f
        ow, oh = out.get_size()
        if wf >= W - 0.01 and hf >= H - 0.01:
            self._scale_into(self.frame, out, 'w')
            return
        s = ow / wf                                    # window pixels per art pixel
        x0, y0 = int(xf), int(yf)
        x1, y1 = min(W, int(xf + wf) + 1), min(H, int(yf + hf) + 1)
        src = self.frame.subsurface((x0, y0, x1 - x0, y1 - y0))
        tw, th = int(round((x1 - x0) * s)), int(round((y1 - y0) * s))
        big = self._buf_atleast('wz', (tw, th))
        pygame.transform.scale(src, (tw, th), big)
        out.blit(big, (-int(round((xf - x0) * s)), -int(round((yf - y0) * s))))

    def _grid2_into(self, src, out, key):
        """Put a picture drawn at twice the art's pixel size onto the window. A whole-number fit goes
        straight there; otherwise it's halved to the art grid first (a camera sitting half a pixel over
        shows as a soft blend, so moves stay smooth) and blown up from that, which is far cheaper."""
        sw, sh = src.get_size()
        ow, oh = out.get_size()
        if ow % sw == 0 and oh % sh == 0:
            pygame.transform.scale(src, (ow, oh), out)
            return
        small = self._small
        pygame.transform.smoothscale(src, small.get_size(), small)
        self._scale_into(small, out, key)

    def present(self):
        """Reduce the finished frame to its pixel grid, then blow it up to the window."""
        win, view, k = self.view_info
        self.screen = win
        if view.w < 8 or view.h < 8:
            return
        self._t_present = time.perf_counter()     # (vsync waits inside present: not counted as work)
        if self.gpu:
            # the graphics card scales the world and lays the interface over it
            try:
                self.gpu.present(view, world=self.frame, cam=self.cam_f, ui=self.canvas, ui_art=(SW // 2, SH // 2))
            except pygame.error as e:
                print('GPU present failed, switching to the CPU:', e)
                self.gpu_fallback()
            return
        if view.size != win.get_size():
            win.fill(BAR_COLOR)
        out = win.subsurface(view)
        if not self.layered:
            # the canvas holds the art (and the interface) at exactly twice its pixel size, so it goes
            # straight to the window: the world keeps the half-pixel camera moves it was drawn with
            self._grid2_into(self.canvas, out, 'w')
            return
        # the world at twice its own size (half-pixel camera), then the interface on its own grid on top
        if (view.w % W == 0 and view.h % H == 0) or screenmod.hard_ok(view.w / W):
            self._world_into(out)                # a whole-number fit, or big: straight on with hard pixels
        else:
            # hard pixels at the next whole size up, then one smooth resize to fit (sharp bilinear), with the
            # camera placed at that bigger size so it still glides
            n = max(1, view.w // W)
            wb = self._buf('wn%d' % n, (W * n, H * n))
            self._world_into(wb)
            pygame.transform.smoothscale(wb, view.size, out)
        cv = self.canvas
        aw, ah = SW // 2, SH // 2
        if view.size == cv.get_size():
            out.blit(cv, (0, 0))                 # the canvas already is the art grid at 2 screen pixels each
            return
        layer = self._buf('uview', view.size, True)
        whole = view.w % aw == 0 and view.h % ah == 0
        if not whole and view.w < aw * 3 and not screenmod.hard_ok(view.w / aw):
            # the canvas is the art grid blown up 2x with hard pixels, so it is already the sharp-bilinear
            # prescale: one smooth resize to the window finishes the job
            pygame.transform.smoothscale(cv, view.size, layer)
        else:
            art = self._buf('uart', (aw, ah), True)
            pygame.transform.smoothscale(cv, (aw, ah), art)
            if whole or screenmod.hard_ok(view.w / aw):
                pygame.transform.scale(art, view.size, layer)
            else:
                # sharp bilinear: whole-number zoom with hard pixels, then a small smooth stretch up to fit
                n = view.w // aw
                big = self._buf('ubig', (aw * n, ah * n), True)
                pygame.transform.scale(art, big.get_size(), big)
                pygame.transform.smoothscale(big, view.size, layer)
        out.blit(layer, (0, 0))

    def new_game_state(self):
        self.race = None             # a fishing race with friends online (coop.py)
        self.exp = None              # an expedition with friends online (coop.py)
        self.gift_to = None
        self.garden = gardenmod.new()   # the cabin garden (garden.py)
        self.hatch = hatchery.new()     # the hatchery pond and the colours found (hatchery.py, morphs.py)
        self.delve = dungeon.new_rec()  # the Drowned Stair's records (dungeon.py): runs are never saved
        self.shore = shoremod.new()     # restoring the shore by the dock (shore.py)
        self.finds = discover.new()     # what Biscuit has found in Fernwick (discover.py)
        self.disc = None
        self.aqscene = None          # inside the aquarium (aquarium.py), under overlay 'aquarium'
        self.nature = {}             # animals photographed: id -> {'stars', 'day', 'n', 'at'} (wildlife.py)
        self.photos = {}             # their best photos this session, and drawn stand-ins
        self.critter = None          # the animal visiting right now
        self.critter_cd = 8.0
        self.critter_told = None
        self.tut = 0                 # first-day tips (tutorial.py)
        self.tut_day = 0
        self.tut_t = 0.0
        self.coins = 25
        self.day = 1
        self.minute = 360.0
        self.weather = 'clear'
        self.rod = 'twig'
        self.rods = ['twig']
        self.bait = 'worm'
        self.baits = {'corn': 0, 'glow': 0, 'golden': 0, 'moon': 0, 'storm': 0}
        self.owned = []
        self.journal = {}
        self.letters = []
        self.basket = []
        self.request = None
        self.luck = 0.0
        self.pet_day = 0
        self.total = 0
        self.tank = []
        self.badges = []
        self.stats = dict(night=0, released=0, requests=0, weathers=[], wins=0, festivals=0, spots=[])
        self.spot = 'dock'
        self.visited = []
        self.trophies = []
        self.festival = None
        self.forecast = {'1': 'clear'}
        self.hat = 'straw'
        self.hats = ['straw']
        self.look = dict(looks.DEFAULT)          # how you look (look.py); the creator sets it
        self.cat_item = 'none'
        self.cat_items = ['none']
        self.wagon = {}
        self.place = 'lake'
        # Fernwick village
        self.museum = []             # fish ids on display at the aquarium
        self.friends = {}            # townsfolk id -> friendship points (10 per heart)
        self.friend_gifts = {}       # townsfolk id -> heart milestones already thanked for
        self.buffs = {}              # bakery snack id -> the day it was eaten
        self.jobs = None             # today's notices: {'day': d, 'list': [...]}
        self.tickets = 0
        self.projects = []
        self.town_day = {}           # once-a-day things: the wish, the bench, talks and gifts
        self.recipes = []            # recipe cards bought from Mabel
        self.cook_best = {}          # recipe id -> best stars
        self.cooking = None          # the CookScene while you are at the stove
        self.story = story.new_state()   # the four lanterns
        self.heart_seen = []         # neighbours whose 5-heart scene you've seen
        self.market = {}             # what Fernwick has bought today: fish per kind and dishes
        self.hunts = {}              # legend hunts (legends.py)
        self.pot = {'set': None, 'corn': False}     # the crab pot (seasons.py)
        self.sky = None              # tonight's rare sky: 'storm' or 'aurora'
        self.ice_hole = 0            # the day you last drilled through the ice
        self.icescene = None         # ice fishing (icefish.py), under overlay 'ice'
        self.dungeon = None          # a run down the Drowned Stair (dungeon.py), under overlay 'dungeon'
        aqmod.HEADLESS, aqmod.fmt_clock = HEADLESS, fmt_clock
        hbmod.HEADLESS, hbmod.fmt_clock = HEADLESS, fmt_clock
        farmod.HEADLESS, farmod.fmt_clock = HEADLESS, fmt_clock
        drivemod.HEADLESS, drivemod.fmt_clock = HEADLESS, fmt_clock
        areamod.HEADLESS, areamod.fmt_clock = HEADLESS, fmt_clock
        self.aqscene = None          # also Saltmarsh harbour (harbour.py), under overlay 'harbour'
        self.coast = coast.new()     # Saltmarsh, down the river (coast.py)
        self.far = farmod.new()      # the Far Shore, across from the landing (farshore.py)
        self.club = clubmod.new()    # the Angling Club on Lanternday evenings (club.py)
        self.stall = stallmod.new()  # your market stall on Leafday mornings (stall.py)
        self.stallrun = None         # this morning's market (not saved)
        self.truck = truckmod.new()  # Grandma Rosie's truck and the roads out (truck.py, drive.py, areas.py)
        self.road_trip = None        # walked down to Saltmarsh from Gull Point (not saved)
        self.goals = goalmod.new()   # the welcome quest and the pinned goal (goals.py)
        goalmod.fmt_clock = fmt_clock
        self.cat_bond = 0            # Biscuit (biscuit.py): bond points, today's little things, a present
        self.cat_day = {}
        self.cat_gift = None
        self.cat_follow = False
        self.home = homemod.starter()   # the cabin room (home.py), with a few of Grandma's things in it
        self.home_sel = ('wall', 0)
        self.home_tab = 'wall'
        self.home_page = 0
        self.room = homemod.Room()
        self.lan_tab = 'lanterns'    # the L panel: 'lanterns' or 'legends'
        self.scene = None            # a Cutscene playing
        self.festival_fx = None
        self.pantry = {}             # cooked dish id -> servings
        self.meal = None             # {'id': dish, 'day': d}: today's meal
        self.upgrades = []           # home upgrades built by Birch
        self.settings = getattr(self, 'settings', None) or dict(DEFAULT_SETTINGS)
        self.ensure_forecast()
        self.new_request()

    def save(self):
        if HEADLESS:
            return
        data = dict(coins=self.coins, day=self.day, minute=self.minute, weather=self.weather, rod=self.rod,
                    rods=self.rods, bait=self.bait, baits=self.baits, owned=self.owned, journal=self.journal,
                    letters=self.letters, basket=self.basket + truckmod.in_cooler(self), request=self.request, luck=self.luck,
                    pet_day=self.pet_day, total=self.total, settings=self.settings, tank=self.tank,
                    badges=self.badges, stats=self.stats, trophies=self.trophies, festival=self.festival,
                    forecast=self.forecast, hat=self.hat, hats=self.hats, look=self.look, cat_item=self.cat_item,
                    cat_items=self.cat_items, wagon=self.wagon, visited=self.visited, dps=DAYS_PER_SEASON,
                    museum=self.museum, friends=self.friends, friend_gifts=self.friend_gifts, buffs=self.buffs,
                    jobs=self.jobs, tickets=self.tickets, projects=self.projects, town_day=self.town_day,
                    recipes=self.recipes, pantry=self.pantry, meal=self.meal, upgrades=self.upgrades,
                    cook_best=self.cook_best, story=self.story, heart_seen=self.heart_seen, market=self.market,
                    hunts=self.hunts, pot=self.pot, sky=self.sky, ice_hole=self.ice_hole,
                    cat_bond=self.cat_bond, cat_day=self.cat_day, cat_gift=self.cat_gift,
                    cat_follow=self.cat_follow, home=self.home, tut=self.tut, tut_day=self.tut_day,
                    garden=self.garden, nature=self.nature, shore=self.shore, finds=self.finds,
                    coast=self.coast, goals=self.goals, hatch=self.hatch, delve=self.delve, far=self.far, club=self.club,
                    stall=self.stall, truck=self.truck)
        if self.solo:
            data.update(self.solo)       # visiting a friend: your own lake keeps its own day and weather
        try:
            tmp = SAVE_PATH + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            os.replace(tmp, SAVE_PATH)
        except OSError as e:
            print('save failed', e)

    # ------------------------------------------------------------ save slots
    def use_slot(self, n):
        global SAVE_PATH
        n = n if n in SLOTS else 1
        self.settings['slot'] = n
        SAVE_PATH = slot_path(n)

    def slot_summary(self, n):
        """A peek inside a slot for the title screen, or None if it is empty."""
        try:
            with open(slot_path(n), encoding='utf-8') as f:
                d = json.load(f)
            day = int(d.get('day', 1))
            return dict(day=day, season=SEASONS[self.season_of(day)], coins=int(d.get('coins', 0)),
                        fish=len(d.get('journal') or {}), lit=len((d.get('story') or {}).get('lit') or []))
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def switch_slot(self, n):
        self.use_slot(n)
        self.save_settings()
        self.new_game_state()
        self.has_save = self.load()
        self.env.minute, self.env.day = self.minute, self.day
        self.env.season = self.season_of(self.day)
        self.env.weather = self.weather
        self.env.settle()
        self.fishing.reset()
        self.confirm_new = 0

    def play_slot(self, n):
        if n != self.settings.get('slot', 1) or not self.has_save:
            self.switch_slot(n)
        self.overlay = None
        self.slot_del = None
        if self.has_save:
            self.start_game(True)
        else:
            self.new_game()

    def new_game(self):
        """A fresh start begins in the character creator; it starts the game when you're happy."""
        self.confirm_new = 0
        self.overlay = None
        creator.open_(self, 'new')

    def delete_slot(self, n):
        if self.slot_del is None or self.slot_del[0] != n or self.t - self.slot_del[1] > 3.0:
            self.slot_del = (n, self.t)          # ask first: the second click within 3 seconds deletes
            self.audio.play('warn', 0.4)
            return
        self.slot_del = None
        path = slot_path(n)
        try:
            if os.path.exists(path):
                os.replace(path, path + '.bak')  # keep a .bak, just in case
        except OSError as e:
            print('delete failed', e)
        if n == self.settings.get('slot', 1):
            self.switch_slot(n)
        self.audio.play('page', 0.6)

    def draw_slots(self, s):
        ui = self.ui
        rect = pygame.Rect(SW // 2 - 390, SH // 2 - 250, 780, 500)
        ui.panel(s, rect, radius=24)
        self.panel_header(s, rect, 'Save slots')
        ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', lambda: setattr(self, 'overlay', None), 'normal',
                  font='h3')
        cur = self.settings.get('slot', 1)
        for i, n in enumerate(SLOTS):
            r = pygame.Rect(rect.x + 30, rect.y + 96 + i * 120, rect.w - 60, 108)
            on = n == cur
            ui.tile(s, r, (238, 244, 228) if on else (246, 236, 216), (150, 180, 130) if on else (196, 170, 140))
            info = self.slot_summary(n)
            ui.blit_text(s, 'Slot %d%s' % (n, '   (playing)' if on else ''), (r.x + 24, r.y + 16), 'bodyb', U.INK)
            if info:
                line = 'Day %d  -  %s  -  %s coins' % (info['day'], info['season'], '{:,}'.format(info['coins']))
                ui.blit_text(s, line, (r.x + 24, r.y + 52), 'small', U.SOFT)
                more = '%d kinds of fish' % info['fish'] + (
                    '  -  %d lantern%s lit' % (info['lit'], '' if info['lit'] == 1 else 's') if info['lit'] else '')
                ui.blit_text(s, more, (r.x + 24, r.y + 76), 'tiny', U.SOFT)
            else:
                ui.blit_text(s, 'Empty. A fresh cabin by the lake is waiting.', (r.x + 24, r.y + 56), 'small',
                             U.SOFT)
            ui.button(s, (r.right - 190, r.y + 24, 170, 60), 'Play' if info else 'Begin',
                      lambda n=n: self.play_slot(n), 'primary', font='h3', nav=True)
            if info:
                asking = self.slot_del is not None and self.slot_del[0] == n and self.t - self.slot_del[1] < 3.0
                ui.button(s, (r.right - 390, r.y + 30, 184, 48), 'Sure? Click again' if asking else 'Delete',
                          lambda n=n: self.delete_slot(n), 'rose' if asking else 'normal', font='smallb')

    def load(self):
        if HEADLESS or not os.path.exists(SAVE_PATH):
            return False
        try:
            with open(SAVE_PATH, encoding='utf-8') as f:
                d = json.load(f)
        except (OSError, ValueError):
            return False
        self.tut = tutorial.DONE         # older saves have long since learned the ropes
        for k in ('coins', 'day', 'minute', 'weather', 'rod', 'rods', 'bait', 'baits', 'owned', 'journal',
                  'letters', 'basket', 'request', 'luck', 'pet_day', 'total', 'tank', 'badges',
                  'trophies', 'festival', 'forecast', 'hat', 'hats', 'look', 'cat_item', 'cat_items', 'wagon', 'visited',
                  'museum', 'friends', 'friend_gifts', 'buffs', 'jobs', 'tickets', 'projects', 'town_day',
                  'recipes', 'pantry', 'meal', 'upgrades', 'cook_best', 'story', 'heart_seen', 'market', 'hunts', 'pot', 'sky', 'ice_hole',
                  'cat_bond', 'cat_day', 'cat_gift', 'cat_follow', 'home', 'tut', 'tut_day', 'garden',
                  'nature', 'shore', 'finds', 'coast', 'hatch', 'delve', 'far', 'club', 'stall', 'truck'):
            if k in d:
                setattr(self, k, d[k])
        self.place = 'lake'
        self.museum = [f for f in self.museum if f in FISH_BY_ID] if isinstance(self.museum, list) else []
        self.friends = {k: int(v) for k, v in self.friends.items() if k in townmod.FOLK} \
            if isinstance(self.friends, dict) else {}
        self.projects = [x for x in self.projects if x in {p['id'] for p in townmod.PROJECTS}] \
            if isinstance(self.projects, list) else []
        self.upgrades = [x for x in self.upgrades if x in {u['id'] for u in townmod.UPGRADES}] \
            if isinstance(self.upgrades, list) else []
        self.recipes = [x for x in self.recipes if x in kitchenmod.RECIPE_BY_ID] \
            if isinstance(self.recipes, list) else []
        self.pantry = {k: int(v) for k, v in self.pantry.items() if k in kitchenmod.RECIPE_BY_ID and int(v) > 0} \
            if isinstance(self.pantry, dict) else {}
        if not isinstance(self.meal, dict) or self.meal.get('id') not in kitchenmod.RECIPE_BY_ID:
            self.meal = None
        self.story = story.clean(self.story)
        self.heart_seen = [k for k in self.heart_seen if k in townmod.FOLK] if isinstance(self.heart_seen, list) else []
        self.hunts = legends.clean(self.hunts)
        biscuit.clean(self)
        self.home = homemod.clean(self.home)
        self.garden = gardenmod.clean(self.garden)
        self.hatch = hatchery.clean(self.hatch)
        self.delve = dungeon.clean_rec(self.delve)
        self.shore = shoremod.clean(self.shore)
        self.finds = discover.clean(self.finds)
        self.coast = coast.clean(self.coast)
        self.far = farmod.clean(getattr(self, 'far', None))
        self.club = clubmod.clean(getattr(self, 'club', None))
        self.stall = stallmod.clean(getattr(self, 'stall', None))
        self.stallrun = None
        self.truck = truckmod.clean(getattr(self, 'truck', None))
        self.road_trip = None
        self.goals = goalmod.clean(d.get('goals'))
        self.nature = {k: {'stars': max(1, min(3, int(v.get('stars', 1)))), 'day': int(v.get('day', 0)),
                           'n': max(1, int(v.get('n', 1))),
                           'at': v.get('at') if v.get('at') in SPOT_BY_ID or v.get('at') == 'town' else None}
                       for k, v in self.nature.items() if k in wildlife.SPECIES_BY_ID and isinstance(v, dict)} \
            if isinstance(self.nature, dict) else {}
        self.photos = {}
        if not isinstance(self.tut, int) or not 0 <= self.tut <= tutorial.DONE:
            self.tut = tutorial.DONE
        if not isinstance(self.tut_day, int):
            self.tut_day = 0
        if not isinstance(self.pot, dict):
            self.pot = {'set': None, 'corn': False}
        if self.sky not in ('storm', 'aurora'):
            self.sky = None
        self.cook_best = {k: max(0, min(3, int(v))) for k, v in self.cook_best.items()
                          if k in kitchenmod.RECIPE_BY_ID} if isinstance(self.cook_best, dict) else {}
        for k in ('friend_gifts', 'buffs', 'town_day'):
            if not isinstance(getattr(self, k), dict):
                setattr(self, k, {})
        if not isinstance(self.jobs, dict) or not isinstance(self.jobs.get('list'), list):
            self.jobs = None
        self.stats.update(d.get('stats', {}))
        self.stats.setdefault('spots', [])
        self.spot = 'dock'                 # every session starts at home
        old = d.get('dps', 3)
        if old != DAYS_PER_SEASON:
            # older saves had shorter seasons: keep the same season and year, start of a fresh week
            yr, rem = divmod(self.day - 1, old * 4)
            sea, dd = divmod(rem, old)
            self.day = yr * DAYS_PER_SEASON * 4 + sea * DAYS_PER_SEASON + dd + 1
            self.forecast = {}
            if self.request:
                self.request['day'] = self.day
        if self.festival and 'rule' not in self.festival:
            self.festival = None
        for k in ('corn', 'glow', 'golden', 'moon', 'storm'):
            self.baits.setdefault(k, 0)
        if self.bait not in BAIT_BY_ID:
            self.bait = 'worm'
        if self.hat not in HAT_BY_ID:
            self.hat = 'straw'
        self.look = looks.clean(getattr(self, 'look', None))
        if self.cat_item not in CAT_BY_ID:
            self.cat_item = 'none'
        self.forecast = {k: v for k, v in self.forecast.items() if k.isdigit()}
        self.ensure_forecast()
        self.basket = [b for b in self.basket if b.get('id') in ALL_BY_ID]
        self.tank = [b for b in self.tank if b.get('id') in FISH_BY_ID][:self.tank_size()]
        if self.rod not in ROD_BY_ID:
            self.rod = 'twig'
        return True

    def apply_settings(self):
        st = self.settings
        m = st.get('master', 1.0)
        self.audio.set_music(st.get('music', 0.5) * m)
        self.audio.sfx_vol = st.get('sfx', 0.8) * m
        self.audio.amb_vol = st.get('amb', 0.8) * m
        CLOCK24[0] = bool(st.get('clock24'))
        self.apply_ui_scale()
        if self.gpu:
            self.gpu.set_vsync(st.get('fps') == 0)
        if st.get('fx') != 'auto':
            self.fx_low = False

    def apply_ui_scale(self):
        """Resize the interface canvas. Smaller percentages give the HUD and menus more room (they look smaller)."""
        global SW, SH
        pct = self.settings.get('ui_scale', 100)
        if pct == self._ui_pct:
            return
        self._ui_pct = pct
        SW, SH = ui_grid(pct)
        almanac.SW, almanac.SH = SW, SH
        U.LOGICAL = (SW, SH)
        minigame.CY = SH - 168                                # the reel ring sits in the bottom-left corner
        # at 100% the world is drawn straight into the canvas (fastest); other sizes keep the world on its own
        # and lay the interface over it as a separate see-through layer
        self.layered = bool(getattr(self, 'gpu', None)) or (SW, SH) != (1280, 720)
        self.canvas = pygame.Surface((SW, SH), pygame.SRCALPHA if self.layered else 0, 32)
        self._fadebuf = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self._dim = None
        self._tskin = None
        self._bufs = {}
        if pygame.display.get_surface() is not None:
            self.view_info = self.calc_view()
            if not HEADLESS:
                self.ui.mouse = self.to_logical(pygame.mouse.get_pos())

    def ui_sharp_sizes(self):
        """The interface sizes that land on whole screen pixels in the current window."""
        view = self.calc_view()[1]
        out = []
        for p in UI_SCALES:
            aw, ah = ui_grid(p)[0] // 2, ui_grid(p)[1] // 2
            if view.w % aw == 0 and view.h % ah == 0:
                out.append(p)
        return out

    # ------------------------------------------------------------ helpers used by other modules
    def has(self, item):
        return item in self.owned

    def owns_boat(self):
        return self.has('boat') or self.has('rowboat')

    def has_boat(self):
        """A boat to row out in: your own, or Wren's, lent to you for the day on her first visit."""
        return self.owns_boat() or self.stats.get('boat_loan') == self.day

    def note(self, kind, **kw):
        """Remember something you just did (for the neighbours to mention). Kept for today only, not saved."""
        rec = getattr(self, 'recent', None)
        if rec is None:
            rec = self.recent = []
        rec.append(dict(kind=kind, day=self.day, **kw))
        del rec[:-24]

    def loan_waiting(self):
        """Wren's boat is tied at the dock for today and you haven't taken it out yet."""
        return (self.stats.get('boat_loan') == self.day and not self.owns_boat()
                and self.stats.get('rowed_day') != self.day and self.place == 'lake' and self.spot == 'dock')

    def mark(self, x, y, label, secs=10.0):
        """Point at something new on the dock for a few seconds (a bouncing arrow and its name)."""
        self.spot_mark = dict(x=x, y=y, label=label, t=secs)
        self.world.sparkles(x, y - 4, 18, (255, 240, 170), 12)

    def draw_world_marks(self, s):
        """Labels for the things the world is pointing at: Wren calling you over, something new on the dock."""
        if self.place != 'lake' or self.overlay is not None or self.rest_phase is not None:
            return
        ui = self.ui
        items = []
        f = self.fishing
        if f.state == 'waiting' and getattr(f, 'snag', False):
            x, y = f.dst
            items.append((x, y - 8, 'Snagged! Tap to work it loose'))
        if self.spot != 'dock':
            items = items[:1]
        if self.loan_waiting():
            items.append((actors.WREN_X, DECK_Y - 30, "She's yours for today! Press B to row out."))
        m = self.spot_mark if self.spot == 'dock' else None
        if m:
            items.append((m['x'], m['y'] - 24, 'New: %s' % m['label']))
        for wx, wy, text in items:
            x, y = self.w2s(wx, wy)
            tw = ui.fonts['smallb'].size(text)[0] + 28
            r = pygame.Rect(0, 0, tw, 38)
            r.midbottom = (x, y - 6)
            r.clamp_ip(pygame.Rect(8, 8, SW - 16, SH - 16))
            r = ui.panel(s, r, radius=14)
            pygame.draw.polygon(s, U.INK, [(x - 7, r.bottom - 1), (x + 7, r.bottom - 1), (x, r.bottom + 8)])
            pygame.draw.polygon(s, (255, 248, 232), [(x - 5, r.bottom - 2), (x + 5, r.bottom - 2), (x, r.bottom + 5)])
            ui.blit_text(s, text, r.center, 'smallb', U.INK, 'center')

    def toast_few(self, key, text, color=(120, 100, 80), limit=3):
        """A toast that stops once it has been said a few times (the game shows it in other ways after that)."""
        told = self.stats.setdefault('told', {})
        if told.get(key, 0) < limit:
            told[key] = told.get(key, 0) + 1
            self.toast(text, color)

    def walk_scene(self):
        """The scene you are walking around right now (the aquarium hall or Saltmarsh harbour), if any."""
        return self.aqscene if self.overlay in ('aquarium', 'harbour', 'farshore', 'drive', 'area') and \
            self.aqscene else None

    # ------------------------------------------------------------ the rowboat
    def open_map(self):
        if self.place != 'lake':
            self.toast('Your boat is tied up down at the lake.', (110, 140, 170))
            return
        if not self.has_boat():
            self.toast("You'll need a rowboat. Wren sells one at her wagon.", (110, 140, 170))
            return
        if self.overlay != 'map':
            self.map_sel = self.spot if self.spot != 'dock' else (
                next((sp['id'] for sp in LAKE_SPOTS[1:] if sp['id'] not in self.visited), 'cove'))
        self.toggle('map')

    def travel(self, spot):
        if spot == self.spot or self.rest_phase is not None or self.place != 'lake':
            return
        self.overlay = None
        self.fishing.reset()
        self.release_holds()
        self.travel_to = spot
        self.rest_phase = 'row_out'
        self.stats['rowed_day'] = self.day
        self.audio.play('plop', 0.6)

    def arrive(self):
        spot = self.travel_to or 'dock'
        river = coast.region(spot) != coast.region(self.spot)
        self.spot = spot
        self.travel_to = None
        self.cam = [1.0, W / 2, H / 2]
        if river:                                 # the long row down the river (or back up it) takes a while
            mins = coast.river_minutes(self)
            self.advance_time(mins)
            self.stats['river'] = self.stats.get('river', 0) + 1
        if spot == 'dock':
            self.toast('Home again, up the river. Biscuit hops out onto the dock first.' if river else
                       'Home again. Biscuit hops out onto the dock first.', (200, 150, 80))
        elif river:
            first = spot not in self.visited
            if first:
                self.visited.append(spot)
            self.toast('Down the river and out to the sea: %s.%s  (%d minutes)'
                       % (SPOT_BY_ID[spot]['name'], '  Smell that salt air!' if first else '', mins), (90, 140, 180))
        else:
            first = spot not in self.visited
            if first:
                self.visited.append(spot)
            self.toast('You row out to %s.%s' % (SPOT_BY_ID[spot]['name'], '  A new place to fish!' if first else ''),
                       (90, 140, 180))
        self.save()

    def go_place(self, where):
        if where == self.place or self.rest_phase is not None or self.mode != 'play':
            return
        if where == 'town' and coast.at_coast(self):
            if self.spot != 'pier':
                self.toast('Row round to Saltmarsh Pier to go ashore at the harbour.', (90, 140, 180))
                return
            if self.fishing.state not in ('idle', 'waiting', 'charging'):
                self.toast('Finish what is on the line first.')
                return
            self.overlay = None
            hbmod.enter(self)
            return
        if self.fishing.state not in ('idle', 'waiting', 'charging'):
            self.toast('Finish what is on the line first.')
            return
        self.overlay = None
        self.fishing.reset()
        self.release_holds()
        self.place_to = where
        self.rest_phase = 'walk_out'
        self.audio.play('page', 0.6)

    def arrive_place(self):
        where, self.place_to = self.place_to or 'lake', None
        self.place = where
        self.spot = 'dock'               # the path to the village starts at the dock
        self.cam = [1.0, W / 2, H / 2]
        tn = self.town
        if where == 'town':
            tn.x, tn.face, tn.target, tn.on_arrive, tn.scroll = 60.0, 1, None, None, 0.0
            tn.cat.x = None
            biscuit.on_town(self)
            discover.on_town(self)
            n = self.stats.get('town_visits', 0)
            self.stats['town_visits'] = n + 1
            if n == 0:
                self.toast('Welcome to Fernwick! Walk with A and D, and press E at a door or a neighbour.',
                           (200, 150, 80))
            else:
                self.toast('You stroll up the lane into Fernwick.', (200, 150, 80))
        else:
            self.toast('Back home at the lake, Biscuit trotting ahead of you.' if biscuit.follows(self) else
                       'Back home at the lake. Biscuit was waiting for you.', (200, 150, 80))
        self.save()

    # ------------------------------------------------------------ Fernwick
    def buff(self, sid):
        if sid in ('cocoa', 'mooncake'):
            return self.buffs.get(sid) == self.night_id() and self.night_now()      # gone at dawn
        return self.buffs.get(sid) == self.day

    def night_id(self):
        """Evenings and the small hours after them count as one night: the day the evening began."""
        return self.day if self.minute >= 720 else self.day - 1

    def night_now(self):
        return self.minute >= 1200 or self.minute < 360

    def has_up(self, uid):
        return uid in self.upgrades

    def tank_size(self):
        return 12 if self.has_up('tank') else TANK_SIZE

    def meal_today(self):
        m = self.meal
        if m and m.get('day') == self.day and m.get('id') in kitchenmod.RECIPE_BY_ID:
            return m['id']
        return None

    def boost(self, kind):
        """Today's food and upgrades. 'size' is added to the size roll; everything else is a multiplier."""
        meal = self.meal_today()
        fx = kitchenmod.RECIPE_BY_ID[meal]['fx'] if meal else {}
        if kind == 'size':
            return (0.08 if self.buff('pie') else 0.0) + fx.get('size', 0.0) + legends.perk(self, 'size')
        v = fx.get(kind, 1.0) * legends.perk(self, kind)
        if kind == 'bite' and self.buff('cocoa') and self.night_now():
            v *= 0.8
        if kind == 'night' and self.buff('mooncake'):
            v *= 1.5
        if kind == 'bite' and self.buff('tea'):
            v *= 0.75
        elif kind == 'rare' and self.buff('cookie'):
            v *= 1.3
        elif kind == 'sell' and self.has_up('icebox'):
            v *= 1.15
        return v

    def sale_price(self, b, nth=0):
        """What one fish fetches. nth is how many of its kind went to market earlier today."""
        if ALL_BY_ID[b['id']].get('junk'):
            return b['price']
        return int(round(b['price'] * self.boost('sell') * market_mult(nth) * coast.price_mult(self, b['id'])))

    def todays_market(self):
        m = self.market
        if not isinstance(m, dict) or m.get('day') != self.day:
            self.market = m = dict(day=self.day, fish={}, dish=0)
        return m

    def quote(self, items):
        """Price for selling these fish now, counting what the market has already had today."""
        seen = dict(self.todays_market()['fish'])
        total = 0
        for b in sorted(items, key=lambda b: -b['price']):       # the best fish go first, at the best price
            n = seen.get(b['id'], 0)
            total += self.sale_price(b, n)
            seen[b['id']] = n + 1
        return total

    def market_note(self, fid):
        """How full the market is of this fish today: 1.0 means it still pays full price."""
        return market_mult(self.todays_market()['fish'].get(fid, 0))

    def sell_fish(self, items):
        total = self.quote(items)
        fish = self.todays_market()['fish']
        for b in items:
            if not ALL_BY_ID[b['id']].get('junk'):
                fish[b['id']] = fish.get(b['id'], 0) + 1
        ids = {id(b) for b in items}
        self.basket = [b for b in self.basket if id(b) not in ids]
        self.coins += total
        self.stats['sold'] = self.stats.get('sold', 0) + len(items)
        self.note('sell', coins=total)
        return total

    def dish_quote(self, rid, n=None):
        """Old Tom pays full price for a few dishes a day; after that his shelves are full."""
        n = self.pantry.get(rid, 0) if n is None else n
        done = self.todays_market()['dish']
        price = kitchenmod.RECIPE_BY_ID[rid]['price']
        return sum(int(round(price * dish_mult(done + i))) for i in range(n))

    def start_cooking(self, rid):
        """Walk over to the stove and cook this recipe as a little playable scene (cookscene.py)."""
        if self.cooking is not None:
            return False
        items = kitchenmod.take(self, rid)
        if items is None:
            return False
        first = not self.stats.get('cook_scenes')
        self.stats['cook_scenes'] = self.stats.get('cook_scenes', 0) + 1
        self.release_holds()
        self.cooking = cookscene.CookScene(self, rid, items, first)
        self.overlay = 'cooking'
        return True

    def set_lan_tab(self, tab):
        if tab != self.lan_tab:
            self.lan_tab = tab
            self.audio.play('page', 0.4)

    def open_lanterns(self):
        if self.overlay is None and self.story['started']:
            self.overlay = 'lanterns'
            self.release_holds()
            self.audio.play('page', 0.5)

    def end_cooking(self):
        sc = self.cooking
        self.cooking = None
        if sc is not None and sc.items:          # never lose fish to a scene that didn't finish
            self.basket.extend(sc.items)
            sc.items = []
        self.overlay = 'cabin'
        self.cabin_tab = 'kitchen'
        self.cam = [1.0, W / 2, H / 2] if isinstance(self.cam, list) else self.cam

    def learn_recipe(self, r):
        if r['id'] in self.recipes or self.coins < r['card']:
            return
        self.coins -= r['card']
        self.recipes.append(r['id'])
        self.add_friend('mabel', 3)
        self.audio.play('jingle2', 0.6)
        self.toast('You copy out the %s card. Cook it on your cabin stove.' % r['name'], (200, 140, 90))
        self.save()

    def fund_upgrade(self, up):
        if self.coins < up['cost'] or up['id'] in self.upgrades:
            return
        self.coins -= up['cost']
        self.upgrades.append(up['id'])
        self.add_friend('hazel', 4)
        self.audio.play('jingle3', 0.7)
        self.toast({'stove': 'A gleaming copper stove for your cabin kitchen!',
                    'tank': 'Birch fits a bigger tank in your cabin. Room for 12 fish now.',
                    'icebox': 'An ice chest for your basket. Fish sell for more now.',
                    'shed': 'A little bait shed by the cabin. Check it every morning!',
                    'loft': 'A cozy loft under the cabin roof. Sweet dreams.'}[up['id']], (110, 150, 100))
        self.check_badges()
        self.save()

    def sell_dish(self, rid):
        n = self.pantry.get(rid, 0)
        if n <= 0:
            return
        total = self.dish_quote(rid, n)
        self.todays_market()['dish'] += n
        del self.pantry[rid]
        self.coins += total
        self.audio.play('coin', 0.8)
        self.toast('Old Tom buys your %s for %d coins.' % (kitchenmod.RECIPE_BY_ID[rid]['name'], total),
                   (200, 160, 70))
        self.save()

    def give_reward(self, kind, v):
        if kind == 'coins':
            self.coins += v
            return '%d coins' % v
        self.baits[kind] = self.baits.get(kind, 0) + v
        return '%d %s%s' % (v, BAIT_BY_ID[kind]['name'], '' if v == 1 or BAIT_BY_ID[kind]['name'].endswith('s')
                            else 's')

    def add_friend(self, k, pts):
        if k not in townmod.FOLK or not pts:
            return
        old = self.friends.get(k, 0)
        new = max(0, min(100, old + pts))
        self.friends[k] = new
        got = self.friend_gifts.setdefault(k, [])
        name = townmod.FOLK[k]['name']
        for hearts, kind, v in townmod.HEART_GIFTS:
            if new >= hearts * 10 and hearts not in got:
                got.append(hearts)
                what = self.give_reward(kind, v)
                body = {3: "It's always nice to bump into you in Fernwick. I put a little something in here for "
                           "you: %s. Don't spend it all on bait!",
                        6: "You've become a real friend to me, you know. Please take %s. I insist, and I won't "
                           "hear another word about it.",
                        10: "Fernwick is lucky to have you, and so am I. You're one of my very best friends. "
                            "Here's %s, with all my love."}[hearts] % what
                self.queue.append(('letter', ('Dear friend,', body, '- ' + name)))
                self.toast('%s now counts you as a friend: %d hearts!' % (name, hearts), (220, 120, 140))
                self.audio.play('jingle3', 0.6)

    def buy_snack(self, sn, quiet=False):
        """quiet: the bakery shows Mabel serving it instead of a pop-up."""
        if self.coins < sn['price'] or self.buff(sn['id']):
            return
        self.coins -= sn['price']
        self.buffs = {k: v for k, v in self.buffs.items() if v >= self.day - 1}
        self.buffs[sn['id']] = self.night_id() if sn.get('night') else self.day
        if sn['id'] == 'bun':
            self.luck = min(3.0, self.luck + 1.0)
        self.add_friend('mabel', 1)
        self.audio.play('coin', 0.6)
        if not quiet:
            self.toast('%s. Delicious! %s' % (sn['name'], sn['desc'].split('.')[-2].strip() + '.'), (200, 140, 90))
        self.save()

    def donate(self, fid):
        items = [b for b in self.basket if b['id'] == fid]
        if not items or fid in self.museum or fid not in FISH_BY_ID:
            return
        self.basket.remove(min(items, key=lambda b: b['price']))
        self.museum.append(fid)
        n = len(self.museum)
        self.add_friend('juniper', 3)
        self.audio.play('jingle2', 0.6)
        self.toast('Juniper gives your %s a tank of its own. (%d of %d)' % (FISH_BY_ID[fid]['name'], n, len(FISH)),
                   (90, 140, 180))
        for need, kind, v in townmod.MUSEUM_REWARDS:
            if n == need:
                what = self.give_reward(kind, v)
                full = n == len(FISH)
                self.queue.append(('letter', ('Dear curator,' if full else 'Dear angler,', (
                    "Every single fish in the lake is on display now, and people come from three towns over to see "
                    "them. I couldn't have done it without you. Here is %s, and a little brass plaque with your "
                    "name on it." if full else
                    "The aquarium now has %d fish on display, thanks to you! The children press their noses to the "
                    "glass all day. Please accept %%s from the museum fund." % n) % what, '- Juniper')))
        aqmod.on_donate(self, fid)
        self.check_badges()
        self.save()

    def town_jobs(self):
        j = self.jobs
        if not j or j.get('day') != self.day:
            self.jobs = j = dict(day=self.day, list=townmod.make_jobs(self))
        return j['list']

    def job_ready(self, job):
        return townmod.job_items(self, job)

    def hand_in(self, job):
        items = self.job_ready(job)
        if job.get('done') or items is None:
            return
        for it in items:
            self.basket.remove(it)
        job['done'] = True
        self.coins += job['reward']
        self.stats['jobs'] = self.stats.get('jobs', 0) + 1
        self.add_friend(job['who'], 6)
        self.audio.play('coin', 0.7)
        self.toast('%s pays you %d coins. Thank you!' % (townmod.FOLK[job['who']]['name'], job['reward']),
                   (200, 150, 80))
        self.save()

    def fund_project(self, pr):
        if self.coins < pr['cost'] or pr['id'] in self.projects:
            return
        self.coins -= pr['cost']
        self.projects.append(pr['id'])
        self.add_friend('hazel', 8)
        self.audio.play('jingle3', 0.7)
        self.toast({'bandstand': 'The Bandstand is built! Come back in the evening for music.',
                    'lighthouse': 'The Lighthouse is lit on the far shore of the lake. Go and see it tonight!'}.get(
            pr['id'], 'The %s are going up! Step outside and have a look.' % pr['name']), (110, 150, 100))
        self.save()

    def draw_town_ui(self, s):
        ui = self.ui
        tn = self.town
        if self.overlay is not None or self.rest_phase is not None:
            return
        for k, (text, left) in getattr(tn, 'says', {}).items():
            f = tn.folk[k]
            sx, sy = self.w2s(f['x'] - tn.scroll, townmod.GROUND - 36)
            a = int(255 * min(1.0, left / 0.4, (3.2 - left) / 0.2))
            w = ui.fonts['smallb'].size(text)[0] + 28
            r = pygame.Rect(0, 0, w, 36)
            r.midbottom = (sx, sy - 8)
            r.x = max(12, min(SW - 12 - w, r.x))
            bub = pygame.Surface((w, 46), pygame.SRCALPHA)
            rr = ui.panel(bub, (0, 0, w, 36), fill=(255, 250, 238), radius=14)
            tx = max(10, min(w - 10, sx - r.x))
            pygame.draw.polygon(bub, U.INK, [(tx - 7, 35), (tx + 7, 35), (tx, 44)])
            pygame.draw.polygon(bub, (255, 250, 238), [(tx - 5, 34), (tx + 5, 34), (tx, 41)])
            ui.blit_text(bub, text, rr.center, 'smallb', U.INK, 'center')
            bub.set_alpha(a)
            s.blit(bub, r.topleft)
        p = tn.prompt(self)
        if p and self.typing != 'chat':
            sx, sy = self.w2s(tn.x - tn.scroll, townmod.GROUND - 40)
            w = ui.fonts['smallb'].size(p)[0] + 72
            r = pygame.Rect(0, 0, w, 42)
            r.midbottom = (sx, sy - 6)
            r.x = max(12, min(SW - 12 - w, r.x))
            r = ui.panel(s, r, fill=(255, 250, 238), radius=14)
            ui.keycap(s, 'E', (r.x + 10, r.centery))
            ui.blit_text(s, p, (r.x + 46, r.centery), 'smallb', U.INK, 'midleft')
        if self.help_on() and self.typing != 'chat':
            hint = self.hint([('key', 'A'), ('key', 'D'), 'or', ('key', 'Click'), 'to walk.   ', ('key', 'E'),
                              'go in or talk   ', ('key', 'T'), 'back to the lake'],
                             [('pad', 'STICK'), 'walk   ', ('pad', 'X'), 'go in or talk   ', ('pad', 'RS'),
                              'back to the lake'])
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            room = SW - 16 - (20 + getattr(self, '_dock_n', 5) * 72) - 32
            if w > room:
                hint = [('key', 'A'), ('key', 'D'), 'walk   ', ('key', 'E'), 'go in or talk']
                w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, SH - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))

    def rod_spec(self):
        return ROD_BY_ID[self.rod]

    def assist(self):
        return bool(self.settings.get('assist'))

    def shake(self, amt):
        self.shake_amt = max(self.shake_amt, amt * self.settings.get('shake', 1.0))

    def rumble(self, low, high, ms):
        """Rumble the pad you're playing with (only while you're using one, and only if it's switched on)."""
        if self.pad is None or self.last_input != 'pad' or not self.settings.get('rumble', True):
            return False
        return self.pad.rumble(low, high, ms)

    # ------------------------------------------------------------ calendar helpers
    def run_fish(self, day):
        return almanac.run_fish(day) if almanac.dow(day) == FISH_RUN_DAY else None

    def wagon_today(self):
        return almanac.dow(self.day) in WAGON_DAYS

    def wagon_here(self):
        return self.wagon_today() and 360 <= self.minute < 1200

    def meteor_live(self):
        m = self.minute
        return ((almanac.dow(self.day) == METEOR_DAY and m >= 1260) or
                (self.day > 1 and almanac.dow(self.day - 1) == METEOR_DAY and m < 300))

    def lantern_night(self):
        f = self.festival
        return self.festival_today() and f.get('rule') == 'count' and self.minute >= 1140 and not f.get('done')

    def event_active(self, kind):
        if kind == 'festival':
            return self.festival_today()
        if kind == 'lantern':
            return self.lantern_night()
        if kind == 'meteor':
            return self.meteor_live()
        if kind in ('storm', 'aurora'):
            return seasons.sky_live(self, kind)
        return False

    def cal_shift(self, d):
        self.cal_off = max(0, min(7, self.cal_off + d))
        week0 = self.day - almanac.dow(self.day) + 1
        self.cal_sel = self.day if self.cal_off == 0 else week0 + self.cal_off * DAYS_PER_SEASON
        self.audio.play('page', 0.5)

    def cal_pick(self, day):
        self.cal_sel = day
        self.audio.play('ui', 0.5)

    # ------------------------------------------------------------ badges
    def check_badges(self):
        st = self.stats
        fish_known = [f for f in FISH if f['id'] in self.journal]
        cond = {
            'first': len(fish_known) >= 1,
            'night': st['night'] >= 10,
            'weather': all(w in st['weathers'] for w in ('rain', 'fog', 'snow')),
            'big': any(e.get('best', 0) > 100 for k, e in self.journal.items() if k in FISH_BY_ID),
            'kind': st['released'] >= 15,
            'neighbour': st['requests'] >= 5,
            'tank': len(self.tank) >= TANK_SIZE,
            'decor': all(self.has(d['id']) for d in DECOR),
            'letters': len(self.letters) >= len(LETTERS),
            'festival': st['wins'] >= 1,
            'legend': any(f['rarity'] == 5 for f in fish_known),
            'half': len(fish_known) >= 12,
            'full': len(fish_known) >= len(FISH),
            'birthday': st.get('birthdays', 0) >= 1,
            'stargazer': 'shiner' in self.journal,
            'stylish': len([h for h in self.hats if h != 'straw']) >= 4,
            'explorer': all(sp['id'] in st.get('spots', []) for sp in LAKE_SPOTS),
            'muskie': 'muskie' in self.journal,
            'bestcat': biscuit.level(self) >= 5,
            'master': yeartwo.master_progress(self)[0] >= yeartwo.master_progress(self)[1],
            'green': st.get('harvested', 0) >= 40,
            'spotter': len(self.nature) >= 8,
            'naturalist': len(self.nature) >= len(wildlife.SPECIES),
            'restorer': all(shoremod.done(self, p['id']) for p in shoremod.PROJECTS),
            'rosie': bool(self.finds.get('secret')),
            'outing': self.stats.get('expeditions', 0) >= 1,
            'curator': len(self.stats.get('exhibits', [])) >= aqmod.CURATOR,
            'sealegs': coast.sea_known(self) >= 10,
            'keeper': coast.lit(self),
            'breeder': self.hatch['raised'] >= 1,
            'colours': all(self.hatch['found'].get(m) for m in morphs.IDS),
            'delver': self.delve['bosses'] >= 1,
            'abyss': self.delve['best'] >= 20,
            'clubstar': self.stats.get('club_wins', 0) >= 5,
        }
        cond.update(farmod.badge_cond(self))
        cond.update(stallmod.badge_cond(self))
        cond.update(truckmod.badge_cond(self))
        for b in BADGES:
            if b['id'] not in self.badges and cond.get(b['id']):
                self.badges.append(b['id'])
                self.coins += b['reward']
                self.toast('Badge earned: %s  (+%d coins)' % (b['name'], b['reward']), (210, 160, 60))
                self.audio.play('jingle3', 0.6)

    # ------------------------------------------------------------ festival
    def festival_today(self):
        f = self.festival
        return f is not None and f.get('day') == self.day

    def festival_live(self):
        f = self.festival
        return self.festival_today() and not f.get('done') and f['start'] <= self.minute < f['end']

    @staticmethod
    def fest_score(rule, v):
        return {'biggest': '%.1f cm', 'total': '%.1f cm', 'count': '%d fish', 'points': '%d pts'}[rule] % v

    def ensure_festival(self):
        if almanac.dow(self.day) != FESTIVAL_DAY or self.festival_today():
            return
        sea = self.season_of(self.day)
        fd = FESTIVALS[sea]
        if self.minute >= fd['end']:
            return
        n = self.stats.get('festivals', 0)
        k = 1 + 0.1 * min(n, 4) + yeartwo.festival_boost(self)       # practice, and every new year
        rule = fd['rule']
        ranges = {'biggest': [(18, 30), (28, 42), (36, 52)], 'count': [(2, 4), (4, 6), (5, 8)],
                  'total': [(80, 140), (130, 200), (180, 260)], 'points': [(5, 9), (9, 14), (13, 20)]}[rule]
        names = random.sample(['Old Tom', 'Juniper', 'Fen the painter', 'Mayor Hazel', 'Mabel', 'Pip'] +
                              (['Rowan'] if yeartwo.rowan_here(self) else []), 3)
        scores = sorted(random.uniform(a, b) * k for a, b in ranges)
        scores = [round(x, 1) if rule in ('biggest', 'total') else int(round(x)) for x in scores]
        self.festival = dict(day=self.day, season=sea, rule=rule, name=fd['name'], start=fd['start'], end=fd['end'],
                             best=0.0 if rule in ('biggest', 'total') else 0, best_id=None, done=False,
                             rivals=[[nm, sc] for nm, sc in zip(names, scores)])
        self.toast('Festival day: the %s! It starts at %s.' % (fd['name'], fmt_clock(fd['start'])), (200, 120, 160))

    def finish_festival(self):
        f = self.festival
        if not f or f.get('done'):
            return
        f['done'] = True
        self.stats['festivals'] = self.stats.get('festivals', 0) + 1
        board = [(nm, sz) for nm, sz in f['rivals']] + [('You', f['best'])] + self.friend_scores()
        board.sort(key=lambda e: -e[1])
        place = [nm for nm, _ in board].index('You') + 1
        prize = yeartwo.festival_prize(self, {1: 300, 2: 150, 3: 75}.get(place, 25))
        self.coins += prize
        if place == 1:
            self.stats['wins'] = self.stats.get('wins', 0) + 1
            self.trophies.append('%s, year %d' % (f['name'], almanac.year_of(self.day)))
        lines = '\n'.join('%d.  %s  -  %s' % (i + 1, nm, self.fest_score(f['rule'], sc)) for i, (nm, sc) in enumerate(board))
        head = {1: 'You won the %s!' % f['name'], 2: 'Second place!', 3: 'Third place!'}.get(place, 'Thanks for joining in!')
        body = '%s\n\n%s\n\nYour prize: %d coins.%s' % (
            head, lines, prize, ' A little trophy is waiting on your cabin shelf.' if place == 1 else '')
        self.queue.append(('letter', ('Festival results', body, '- Mayor Hazel')))
        self.audio.play('jingle4' if place == 1 else 'coin', 0.7)
        self.check_badges()
        self.next_queue()
        self.save()

    def light_bulbs(self):
        return actors.light_bulbs()

    def draw_actors(self, near):
        actors.draw_all(near, self, self.world.t)

    def request_flag(self):
        return bool(self.mail()) or self.request is not None and not self.request.get('done')

    def mail(self):
        """Letters waiting in the mailbox: news that can wait until you go and look (the flag goes up)."""
        return self.stats.setdefault('mail', [])

    def post(self, letters):
        """Put letters in the mailbox instead of opening them on top of whatever you're doing."""
        if not letters:
            return
        box = self.mail()
        box.extend(letters)
        who = letters[0][2].lstrip('- ').strip() if len(letters) == 1 else None
        self.toast('Mail! A letter from %s is in the mailbox.' % who if who else
                   'Mail! %d letters are in the mailbox.' % len(box), (180, 110, 90))

    def open_mailbox(self):
        box = self.mail()
        if box:
            self.open_letter(tuple(box.pop(0)))
            self.release_holds()
        else:
            self.read_request()

    def season_of(self, day):
        return ((day - 1) // DAYS_PER_SEASON) % 4

    def toast(self, text, color=(120, 100, 80)):
        """A note at the top of the screen. Two at most at a time; the rest wait their turn (no repeats)."""
        q = getattr(self, 'toast_q', None)
        if q is None:
            q = self.toast_q = []
        if any(t[0] == text for t in self.toasts) or any(t[0] == text for t in q):
            return
        if len(self.toasts) < self.toast_max():
            self.toasts.append([text, 3.6, color])
        else:
            q.append([text, 3.6, color])
            del q[:-6]

    def toast_max(self):
        """How many notes show at once: one in the clean HUD (the rest queue up behind it), two otherwise."""
        return 1 if self.hud_style() == 'clean' else 2

    def toasted(self, part):
        """Is a toast with this text showing or waiting? (for tests)"""
        return any(part in t[0] for t in self.toasts + getattr(self, 'toast_q', []))

    WORM_TIN = 30                    # the worm tin fills back up to this every morning
    WORM_PACK, WORM_PRICE = 15, 20

    def worms(self):
        return self.baits.setdefault('worm', self.WORM_TIN)

    def bait_ready(self):
        """Can you cast? With an empty worm tin you switch to other bait, or wait for morning (or buy more)."""
        if self.bait != 'worm' or self.worms() > 0:
            return True
        other = [b['id'] for b in BAITS[1:] if self.baits.get(b['id'], 0) > 0]
        if other:
            self.bait = other[0]
            self.toast('The worm tin is empty. On with the %s.' % BAIT_BY_ID[other[0]]['name'], (150, 130, 100))
            return True
        if self.place == 'lake' and self.spot == 'dock':
            self.dig_worms()
            return False
        self.toast("The worm tin is empty! Row home to dig for more, or buy some at the shop.", (200, 120, 100))
        self.audio.play('nibble', 0.5)
        return False

    DIG_WORMS = 10                   # worms you dig up along the bank when the tin runs out
    DIG_MINUTES = 30

    def dig_worms(self):
        """Out of worms at the dock: dig along the bank for a few more. It takes half an hour."""
        self.advance_time(self.DIG_MINUTES)
        self.baits['worm'] = self.worms() + self.DIG_WORMS
        self.bait = 'worm'
        self.audio.play('rustle', 0.6)
        self.world.splash(70, 250, 6, 0.4, (120, 90, 60))
        self.stats['dug'] = self.stats.get('dug', 0) + 1
        self.toast('The tin was empty, so you dug along the bank: +%d worms (half an hour went by).'
                   % self.DIG_WORMS, (150, 120, 90))
        self.save()

    def buy_worms(self):
        if self.coins < self.WORM_PRICE:
            self.toast('Not enough coins yet.', (200, 120, 100))
            return
        self.coins -= self.WORM_PRICE
        self.baits['worm'] = self.worms() + self.WORM_PACK
        self.bait = 'worm'
        self.audio.play('coin', 0.7)
        self.toast('+%d worms in the tin.' % self.WORM_PACK, (150, 120, 90))

    def spook(self, spec):
        sp = getattr(self, '_spooked', None)
        if not sp or sp.get('day') != self.day:
            sp = self._spooked = dict(day=self.day, ids=[])
        if spec['id'] not in sp['ids']:
            sp['ids'].append(spec['id'])
            self.toast('The %s is spooked. It won\'t come back today.' % spec['name'], (150, 130, 170))

    def spooked(self, fid):
        sp = getattr(self, '_spooked', None)
        return bool(sp and sp.get('day') == self.day and fid in sp['ids'])

    def use_bait(self):
        if BAIT_BY_ID[self.bait].get('legend'):
            return                           # a legend's lure lasts until the legend is landed
        if self.bait == 'worm':
            self.baits['worm'] = max(0, self.worms() - 1)
            if self.baits['worm'] == 5:
                self.toast_few('worms_low', 'Only five worms left in the tin today.', (150, 130, 100), 3)
            return
        if self.bait != 'worm':
            self.baits[self.bait] = max(0, self.baits.get(self.bait, 0) - 1)
            if self.baits[self.bait] <= 0:
                self.toast('Out of %s. Back to worms.' % BAIT_BY_ID[self.bait]['name'])
                self.bait = 'worm'

    def on_bite(self):
        self.cat['excited'] = 0.8

    # ------------------------------------------------------------ requests & weather
    def give_gift(self, code):
        kind, val = code.split(':')
        if kind == 'hat':
            if val not in self.hats:
                self.hats.append(val)
            return 'a %s. Try it on in the cabin wardrobe!' % HAT_BY_ID[val]['name']
        if kind == 'cat':
            if val not in self.cat_items:
                self.cat_items.append(val)
            return 'a %s for Biscuit. Find it in the cabin wardrobe.' % CAT_BY_ID[val]['name']
        if kind == 'decor':
            if val not in self.owned:
                self.owned.append(val)
            name = next(d['name'] for d in GIFT_DECOR if d['id'] == val)
            return 'my old %s. I have set it up by your dock.' % name
        self.coins += int(val)
        return '%s coins, tucked in this envelope' % val

    def almanac_letter(self, day):
        lines = []
        for i in range(DAYS_PER_SEASON):
            for kind, title, _ in almanac.events_on(day + i):
                if kind != 'season':
                    lines.append('%s:  %s' % (WEEKDAYS[i], title))
        body = ('%s has come to the lake! Here is what the week holds:\n%s\n'
                'The calendar (K) has all the details. Take it slow, and eat something warm.'
                % (SEASONS[self.season_of(day)], '\n'.join(lines)))
        return ('The %s almanac' % SEASONS[self.season_of(day)], body, '- Grandma Rosie')

    def start_day(self):
        """Morning: everything that happens overnight. Its letters go in the mailbox rather than popping up."""
        n = len(self.queue)
        self._start_day()
        news = [q for q in self.queue[n:] if q[0] == 'letter']
        if news:
            self.queue[n:] = [q for q in self.queue[n:] if q[0] != 'letter']
            self.post([q[1] for q in news])

    def _start_day(self):
        self.baits['worm'] = max(self.worms(), self.WORM_TIN)      # a fresh tin of worms dug every morning
        story.morning(self)
        legends.morning(self)
        biscuit.morning(self)
        yeartwo.morning(self)
        gardenmod.morning(self)
        hatchery.morning(self)
        shoremod.morning(self)
        coast.morning(self)
        farmod.morning(self)
        truckmod.morning(self)
        """Morning routine: forecast, the day's letter, birthdays and events."""
        d = self.day
        self.ensure_forecast()
        b = almanac.birthday(d)
        if self.request is None or self.request.get('day', 0) < d:
            if b and b['fish']:
                self.request = dict(fish=b['fish'], need=1, have=0, who=b['who'], why="It's my birthday today!",
                                    reward=0, gift=b['gift'], birthday=True, day=d, done=False)
                self.toast("It's %s's birthday! Check the mailbox." % b['who'], (200, 120, 160))
            else:
                self.new_request()
                self.toast_few('request', 'A neighbour wrote asking for a fish. Check the mailbox.', (180, 110, 90))
        if b and not b['fish'] and self.stats.get('rosie_day') != d:
            self.stats['rosie_day'] = d
            self.give_gift(b['gift'])
            self.queue.append(('letter', ('My dear,', "It's my birthday today, and do you know what I wished for? "
                                          "That you are warm, well fed and catching lovely fish. I've tucked 250 "
                                          "coins in here. Buy yourself something silly.", '- Grandma Rosie')))
        if almanac.dow(d) == 1 and self.stats.get('almanac_day') != d:
            self.stats['almanac_day'] = d
            self.queue.append(('letter', self.almanac_letter(d)))
            self.world.spot_cd = 0.5
        for kind, title, _ in almanac.events_on(d):
            if kind == 'wagon':
                if not self.owns_boat() and not self.stats.get('boat_loan'):
                    # her first visit: Wren lends you her rowboat for the day, so you see the rest of the lake
                    self.stats['boat_loan'] = self.day
                    self.queue.append(('letter', ('Ahoy there!', (
                        "I've tied my old rowboat to the end of your dock. She's yours for today. Press B, or click "
                        "the boat, and row out to Lily Cove, the Deep or Willow Creek: different water, different "
                        "fish. I'll take her back at bedtime. And if you two get on, she's 500 coins at my wagon."),
                        '- Wren')))
                else:
                    self.toast("Wren's Wagon has floated in! Click the houseboat to shop.", (70, 140, 150))
            elif kind == 'run':
                self.toast('Fishday: the %s is on!' % title.lower().replace(' run', ' run'), (90, 140, 190))
            elif kind == 'meteor':
                self.toast('Starday: a meteor shower tonight from 9 PM.', (120, 130, 200))
        self.ensure_festival()
        if self.has_up('shed') and self.stats.get('shed_day') != d:
            self.stats['shed_day'] = d
            self.baits['corn'] = self.baits.get('corn', 0) + 3
            self.baits['glow'] = self.baits.get('glow', 0) + 2
            self.toast('The bait shed has 3 Sweet Corn and 2 Glow Grubs for you this morning.', (150, 120, 80))

    def new_request(self):
        season = self.season_of(self.day)
        rng_ = ROD_BY_ID[self.rod]['range']
        top = 2 if self.rod == 'twig' else 3
        boat = self.owns_boat()
        pool = [f for f in FISH if f['rarity'] <= top and f['weather'] is None and not f['needs'] and not f.get('method')
                and (f['seasons'] is None or season in f['seasons'])
                and (not f['spot'] or boat)
                and f['depth'][0] <= spot_depth(f['spot'] or 'dock', rng_) - 0.05]
        if self.request and not self.request.get('done'):
            pool = [f for f in pool if f['id'] != self.request['fish']] or pool
        f = random.choice(pool)
        need = {1: 3, 2: 2, 3: 1}[f['rarity']]
        who = random.choice(VILLAGERS + ([townmod.FOLK['rowan']['req']] if yeartwo.rowan_here(self) else []))
        self.request = dict(fish=f['id'], need=need, have=0, who=who,
                            why=random.choice(REQUEST_REASONS), reward=f['price'] * need * 2 + 25, day=self.day,
                            done=False)

    @staticmethod
    def pick_weather(season, table=None):
        table = table or WEATHER_TABLE[season]
        total = sum(p for _, p in table)
        x = random.uniform(0, total)
        w = table[-1][0]
        for name, p in table:
            x -= p
            if x <= 0:
                w = name
                break
        if season == 3 and w == 'rain':
            w = 'snow'
        if season != 3 and w == 'snow':
            w = 'rain'
        return w

    def ensure_forecast(self):
        for d in range(self.day, self.day + 3):
            if str(d) not in self.forecast:
                self.forecast[str(d)] = self.pick_weather(self.season_of(d))
        for k in list(self.forecast):
            if int(k) < self.day - 1:
                del self.forecast[k]

    def roll_weather(self, slot):
        season = self.season_of(self.day)
        table = WEATHER_TABLE[season]
        cur = self.weather
        if slot == 'morning':
            self.ensure_forecast()
            self.weather = self.forecast[str(self.day)]
            return
        if slot == 'afternoon':
            if cur == 'fog':
                self.weather = random.choice(['clear', 'cloudy'])
                return
            if random.random() < 0.65:
                return
            table = [(w, p) for w, p in table if w != 'fog']
        elif slot == 'night':
            dw = almanac.dow(self.day)
            if dw == METEOR_DAY or (dw == FESTIVAL_DAY and season == 1):
                self.weather = 'clear'          # the sky always behaves for meteors and lanterns
                return
            if random.random() < 0.55:
                return
        self.weather = self.pick_weather(season, table)

    def advance_time(self, mins):
        before = self.minute
        old_season = self.season_of(self.day)
        self.minute += mins
        self.luck = max(0.0, self.luck - mins * 0.001)
        if self.minute >= 1440:
            self.minute -= 1440
            self.day += 1
            before -= 1440
        for mark, slot in ((360, 'morning'), (780, 'afternoon'), (1200, 'night')):
            if before < mark <= self.minute:
                self.env.season = self.season_of(self.day)
                if self.net.role != 'guest':        # a guest's weather comes from the host
                    self.roll_weather(slot)
                    seasons.roll_sky(self, slot)
                if slot == 'morning':
                    self.start_day()
        if before < 1260 <= self.minute and almanac.dow(self.day) == METEOR_DAY:
            self.weather = 'clear'
            self.toast('The meteor shower has begun! Click the shooting stars to wish.', (120, 130, 200))
        f = self.festival
        if self.festival_today() and not f.get('done'):
            if before < f['start'] <= self.minute:
                self.toast('The %s has begun! %s' % (f['name'], FESTIVALS[f['season']]['desc']), (200, 120, 160))
                self.audio.play('jingle2', 0.6)
            if before < f['end'] <= self.minute:
                self.finish_festival()
        clubmod.tick(self, before)
        stallmod.tick(self, before)
        truckmod.tick(self, before)
        if before < 1200 <= self.minute and self.wagon_today():
            self.toast("Wren's Wagon sails off for the night. See you soon!", (70, 140, 150))
        self.ensure_festival()
        new_season = self.season_of(self.day)
        if new_season != old_season:
            self.toast('%s has arrived at the lake.' % SEASONS[new_season], (110, 150, 100))

    # ------------------------------------------------------------ catching
    def on_catch(self, c):
        spec, size = c['spec'], c['size']
        v = c.get('v') if not spec.get('junk') else None
        lo, hi = spec['size']
        k = (size - lo) / max(0.01, hi - lo)
        price = spec['price'] if spec.get('junk') else int(round(spec['price'] * (0.8 + 0.6 * k)))
        if self.run_fish(self.day) == spec['id']:
            price = int(round(price * 1.5))
        price *= morphs.mult(v)
        new_colour = hatchery.note_found(self, spec['id'], v)
        entry = self.journal.get(spec['id'])
        new = entry is None and not spec.get('junk')
        record = entry is not None and size > entry.get('best', 0) and not spec.get('junk')
        old_best = entry.get('best', 0) if entry else 0
        if entry is None:
            entry = {'count': 0, 'best': 0}
            self.journal[spec['id']] = entry
        entry['count'] += 1
        entry['best'] = max(entry['best'], size)
        self.total += 1
        if not spec.get('junk'):
            self.note('catch', fish=spec['id'], new=new, record=record)
            self.stats['caught_day'] = self.day
        lakelife.dock_progress(self)
        goalmod.on_catch(self, spec)
        if not spec.get('junk'):
            if self.spot not in self.stats.setdefault('spots', []):
                self.stats['spots'].append(self.spot)
            if self.env.nf > 0.5:
                self.stats['night'] += 1
            if self.weather in ('rain', 'fog', 'snow') and self.weather not in self.stats['weathers']:
                self.stats['weathers'].append(self.weather)
            f = self.festival
            if self.festival_live():
                rule, old = f['rule'], f['best']
                if rule == 'biggest':
                    f['best'] = max(old, size)
                elif rule == 'count':
                    f['best'] = old + 1
                elif rule == 'total':
                    f['best'] = round(old + size, 1)
                else:
                    f['best'] = old + FROST_POINTS[spec['rarity']]
                if f['best'] != old:
                    lead = max(sz for _, sz in f['rivals'])
                    self.toast('%s: %s%s' % (f['name'], self.fest_score(rule, f['best']),
                                             '  - you are in the lead!' if f['best'] > lead else ''), (200, 120, 160))
        legends.on_catch(self, spec, size)
        if not spec.get('junk'):
            clubmod.on_catch(self, spec, size)
        req = self.request
        wanted = bool(req and not req.get('done') and req['fish'] == spec['id'])
        if (not new and not record and not spec.get('junk') and spec['rarity'] <= 2 and not wanted and not v
                and not self.festival_live() and self.settings.get('quick_commons', True)):
            # one you've caught before, nothing special: into the basket, a little note in the corner, cast again
            self.basket.append(dict(id=spec['id'], size=size, price=price))
            self.quick_pop = dict(spec=spec, size=size, price=price, t=0.0, n=entry['count'])
            self.fishing.quick_t = 0.55
            self.audio.play('jingle1', 0.45)
            self.world.sparkles(PLAYER_X + 8, DECK_Y - 30, 6, (255, 240, 180))
            self.cat['excited'] = max(self.cat['excited'], 1.0)
            if self.net.online:
                self.net.send({'t': 'catch', 'fish': spec['id'], 'size': round(size, 1), 'new': False, 'rec': False})
                coop.on_catch(self, spec)
            self.check_badges()
            self.save()
            return
        # before the card: a moment holding it up for everyone to see (any key or click moves on)
        show = 0.0 if spec.get('junk') else 1.0 + 0.2 * spec['rarity'] + (0.4 if new or record else 0.0)
        if v:
            show += 0.6
        self.card = dict(spec=spec, size=size, price=price, new=new, record=record, old=old_best, t=-show,
                         show=show, v=v, new_colour=new_colour)
        if v:
            m = morphs.MORPH_BY_ID[v]
            self.stats['morphs'] = self.stats.get('morphs', 0) + 1
            self.toast('A %s! %s' % (morphs.name(spec, v), 'A new colour for your collection.' if new_colour
                                     else 'Its colours shimmer in the light.'), m['col'])
        self.overlay = 'catch'
        self.release_holds()
        r = spec['rarity']
        self.audio.play('jingle%d' % max(1, min(5, r if r else 1)), 0.7)
        self.world.sparkles(PLAYER_X + 8, DECK_Y - 30, 10 + r * 6, RARITY_COLORS[r] if r >= 2 else (255, 240, 180))
        self.cat['excited'] = 2.0
        req = self.request
        if req and not req.get('done') and req['fish'] == spec['id']:
            req['have'] += 1
            if req['have'] >= req['need'] and req.get('birthday'):
                req['done'] = True
                self.stats['birthdays'] = self.stats.get('birthdays', 0) + 1
                self.stats['requests'] += 1
                self.add_friend(townmod.REQ_TO_FOLK.get(req['who']), 20)
                what = self.give_gift(req['gift'])
                self.queue.append(('letter', ('Thank you!!', 'You remembered my birthday! The %s is perfect. I want '
                                              'you to have %s' % (FISH_BY_ID[req['fish']]['name'], what),
                                              '- ' + req['who'])))
                self.audio.play('jingle3', 0.7)
            elif req['have'] >= req['need']:
                req['done'] = True
                self.coins += req['reward']
                self.stats['requests'] += 1
                self.add_friend(townmod.REQ_TO_FOLK.get(req['who']), 8)
                name = FISH_BY_ID[req['fish']]['name']
                self.queue.append(('letter', ('Dear angler,',
                                              'Thank you so much for the %s! It means a lot. I have tucked %d coins '
                                              'into this envelope for your trouble. See you at the lake!'
                                              % (name, req['reward']), '- ' + req['who'])))
                self.audio.play('coin', 0.7)
            else:
                self.toast('Request: %d / %d %s' % (req['have'], req['need'], FISH_BY_ID[req['fish']]['name']))
        if self.net.online:
            self.net.send({'t': 'catch', 'fish': spec['id'], 'size': round(size, 1), 'new': new, 'rec': record,
                           'v': v})
            coop.on_catch(self, spec)
        self.check_badges()
        self.save()

    def keep_catch(self):
        c = self.card
        spec = c['spec']
        if spec['id'] == 'bottle':
            unread = [i for i in range(len(LETTERS)) if i not in self.letters]
            idx = random.choice(unread) if unread else random.randrange(len(LETTERS))
            if idx not in self.letters:
                self.letters.append(idx)
            self.queue.insert(0, ('letter', LETTERS[idx]))
        elif c.get('v'):
            # a colour morph: into the hatchery pond, or to a collector if the pond is full
            if not hatchery.add_catch(self, spec, c['size'], c['v'], c['price']):
                self.coins += c['price']
                self.note('sell', coins=c['price'])
                self.audio.play('coin', 0.7)
                self.toast('The pond is full, so a collector paid %d coins for it.' % c['price'], (200, 160, 70))
            else:
                self.toast_few('pond', 'Into the hatchery pond by the garden.', (90, 140, 170))
        else:
            self.basket.append(dict(id=spec['id'], size=c['size'], price=c['price']))
        self.audio.play('ui', 0.6)
        self.close_card()
        self.check_badges()

    def tank_catch(self):
        c = self.card
        if c['spec'].get('junk') or len(self.tank) >= self.tank_size():
            return
        self.tank.append(dict(id=c['spec']['id'], size=c['size'], v=c.get('v')))
        self.audio.play('splash_small', 0.6)
        self.toast_few('tank', '%s is settling into the cabin tank.' % c['spec']['name'], (90, 140, 190))
        self.close_card()
        self.check_badges()

    def release_from_tank(self, i):
        if 0 <= i < len(self.tank):
            fish = self.tank.pop(i)
            hatchery.stock(self, fish)
            self.luck = min(3.0, self.luck + 0.3)
            self.stats['released'] += 1
            self.audio.play('splash_small', 0.6)
            self.toast('You walk the %s back to the lake.' % FISH_BY_ID[fish['id']]['name'], (110, 150, 100))
            self.tank_sel = None
            self.check_badges()
            self.save()

    def release_catch(self):
        c = self.card
        if c['spec'].get('junk'):
            return self.keep_catch()
        self.stats['released'] += 1
        self.check_badges()
        self.luck = min(3.0, self.luck + 0.3)
        if c.get('v'):
            hatchery.stock(self, dict(id=c['spec']['id'], v=c['v']))
        self.world.hearts(300, 312, 3)
        self.world.ripple(300, 314, 12)
        self.audio.play('splash_small', 0.5)
        self.toast('Back it goes, happy as can be. You feel a little luckier.', (110, 150, 100))
        self.close_card()

    def close_card(self):
        self.card = None
        self.overlay = None
        self.fishing.finish()
        self.save()
        self.next_queue()

    def next_queue(self):
        if self.queue and self.overlay is None and self.fishing.state == 'idle':
            kind, data = self.queue.pop(0)
            if kind == 'scene':
                data(self)
            elif kind == 'letter':
                self.letter = data
                self.overlay = 'letter'
                self.audio.play('page', 0.7)

    # ------------------------------------------------------------ world interactions
    def wish_on_star(self):
        s = self.world.shooting
        if not s:
            return False
        self.world.shooting = None
        self.luck = min(3.0, self.luck + (2.0 if self.has('telescope') else 1.5))
        self.world.sparkles(s['x'], s['y'], 24, (220, 230, 255), 12)
        self.audio.play('wish', 0.8)
        self.toast('You made a wish on a shooting star. Luck is with you tonight.', (120, 130, 200))
        return True

    # ------------------------------------------------------------ the quick menu (controller's View button)
    def quick_items(self):
        """Everything the keyboard and mouse can reach, as buttons: (label, action) or None for a gap."""
        lake = self.place == 'lake'
        dock = lake and self.spot == 'dock'
        key = lambda k: (lambda: self.key_down(k))
        items = []
        if self.world.shooting and lake:
            items.append(('Wish on the shooting star!', self.wish_on_star))
        items += [('Journal', key(pygame.K_j)), ('Shop', key(pygame.K_s)), ('Calendar', key(pygame.K_k)),
                  ('Goals', key(pygame.K_q))]
        if lake:
            items.append(('Cabin', key(pygame.K_c)))
        if dock:
            items.append(('Pet Biscuit', self.pet_cat))
            if self.has('pot'):
                items.append(('Crab pot', lambda: seasons.pot_action(self)))
            items.append(('Mailbox', self.open_mailbox))
            items.append(('The Drowned Stair', lambda: dungeon.open_stair(self)))
            if farmod.unlocked(self) and self.visit_shore is None:
                items.append(('Row to the Far Shore', lambda: farmod.go(self)))
            if self.truck['told'] and self.visit_shore is None:
                items.append(("Rosie's truck", lambda: truckmod.open_(self)))
            if self.shore.get('told') and self.visit_shore is None:
                items.append(('The Shore', lambda: shoremod.open_panel(self)))
            if self.wagon_here():
                items.append(("Wren's Wagon", lambda: (setattr(self, 'shop_tab', 'wagon'), self.toggle('shop'))))
        if lake and self.has_boat():
            items.append(('Lake map', key(pygame.K_b)))
        if self.story.get('started'):
            items.append(('Lanterns & Legends', key(pygame.K_l)))
        items.append(('Go ashore at Saltmarsh' if coast.at_coast(self) else 'Walk to Fernwick' if lake else
                      'Back to the lake', key(pygame.K_t)))
        items.append(('Rest until morning', key(pygame.K_z)))
        items.append(('Photo mode', key(pygame.K_p)))
        items.append(('Music on' if self.settings['music'] <= 0 else 'Music off', key(pygame.K_m)))
        items.append(('Radio', key(pygame.K_r)))
        if self.net.online:
            items.append(('Chat', key(pygame.K_RETURN)))
            items.append(('Friends: gifts, races, outings', lambda: self.toggle('coop')))
        return items

    def open_quick(self):
        if self.overlay is not None or self.rest_phase is not None or self.mode != 'play':
            return
        if self.fishing.state not in ('idle', 'waiting'):
            return
        self.overlay = 'quick'
        self.ui.nav_owner = None             # start at the top every time
        self.ui.focus = None
        self.release_holds()
        self.audio.play('page', 0.5)

    def quick_do(self, act):
        self.overlay = None
        act()

    def draw_quick(self, s):
        ui = self.ui
        items = self.quick_items()
        cols = 3
        rows = (len(items) + cols - 1) // cols
        bw, bh, gap = 250, 52, 12
        w = cols * (bw + gap) - gap + 72
        h = 104 + rows * (bh + gap) + 68 + 70
        rect = pygame.Rect(SW // 2 - w // 2, SH // 2 - h // 2, w, h)
        ui.panel(s, rect, radius=24)
        self.panel_header(s, rect, 'Quick menu')
        ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', self.close_overlay, 'normal', font='h3')
        for i, (label, act) in enumerate(items):
            r, c = divmod(i, cols)
            x = rect.x + 36 + c * (bw + gap)
            y = rect.y + 96 + r * (bh + gap)
            style = 'primary' if label.startswith('Wish') else 'normal'
            ui.button(s, (x, y, bw, bh), label, lambda a=act: self.quick_do(a), style, font='smallb', nav=True)
        # emotes
        y = rect.y + 96 + rows * (bh + gap) + 8
        ui.blit_text(s, 'Emotes', (rect.x + 36, y + 22), 'smallb', U.SOFT, 'midleft')
        for i, (em, label) in enumerate(zip(actors.EMOTES, ('Heart', 'Music', '!', 'Fish'))):
            x = rect.x + 150 + i * 150
            ui.button(s, (x, y, 138, 46), label,
                      lambda k=pygame.K_1 + i: self.quick_do(lambda: self.key_down(k)), font='smallb', nav=True)
        if ui.focus is None and self.last_input == 'pad':
            ui.focus = 0
        hint = [('pad', 'DPAD'), 'choose   ', ('pad', 'A'), 'select   ', ('pad', 'B'), 'close']
        if ui.pad_layout:
            hw = ui.rich(s, hint, (0, 0), measure=True)
            ui.rich(s, hint, (rect.centerx - hw // 2, rect.bottom - 30), U.SOFT, False)

    def world_click(self, wx, wy):
        s = self.world.shooting
        if s and math.hypot(wx - s['x'], wy - s['y']) < 16:
            self.world.shooting = None
            self.luck = min(3.0, self.luck + (2.0 if self.has('telescope') else 1.5))
            self.world.sparkles(s['x'], s['y'], 24, (220, 230, 255), 12)
            self.audio.play('wish', 0.8)
            self.toast('You made a wish on a shooting star. Luck is with you tonight.', (120, 130, 200))
            return True
        if (pygame.Rect(actors.CAT_X - 9, DECK_Y - 19, 18, 19).collidepoint(wx, wy)
                or self.cat_gift and biscuit.gift_rect().collidepoint(wx, wy)):
            self.pet_cat()
            return True
        if self.spot != 'dock':
            return False
        if self.goals['step'] == 3 and goalmod.PLANK_CLICK.collidepoint(wx, wy):
            goalmod.mend_plank(self)
            return True
        if self.has('pot') and seasons.pot_rect(self).collidepoint(wx, wy):
            seasons.pot_action(self)
            return True
        if self.has_boat() and pygame.Rect(146, 302, 44, 18).collidepoint(wx, wy):
            self.open_map()
            return True
        if pygame.Rect(73, 220, 16, 22).collidepoint(wx, wy):
            self.open_mailbox()
            return True
        if art.CABIN_DOOR.inflate(4, 4).collidepoint(wx, wy) or art.CABIN_WINDOW.inflate(4, 4).collidepoint(wx, wy):
            self.toggle('cabin')
            return True
        if gardenmod.AREA.collidepoint(wx, wy):
            self.open_cabin_tab('garden')
            return True
        if hatchery.AREA.collidepoint(wx, wy):
            self.open_cabin_tab('hatchery')
            return True
        if dungeon.AREA.collidepoint(wx, wy):
            dungeon.open_stair(self)
            return True
        if self.overlay is None and shoremod.click(self, wx, wy):
            return True
        if self.wagon_here() and WAGON_RECT.collidepoint(wx, wy):
            self.shop_tab = 'wagon'
            self.toggle('shop')
            return True
        return False

    def open_cabin_tab(self, tab):
        self.cabin_tab = tab
        if self.overlay != 'cabin':
            self.toggle('cabin')

    def photo_dir(self):
        """Where the Nature page keeps its photos: next to the save, one folder per save slot."""
        if HEADLESS:
            return None
        return os.path.join(os.path.dirname(SAVE_PATH), 'photos', os.path.splitext(os.path.basename(SAVE_PATH))[0])

    def pet_cat(self):
        biscuit.on_pet(self)
        if self.cat.get('trick'):
            return
        self.cat['pet'] = 1.6
        self.cat['sleep'] = False
        self.world.hearts(actors.CAT_X + 3, DECK_Y - 18, 3)
        self.audio.play('purr', 0.9)
        if self.pet_day != self.day:
            self.pet_day = self.day
            self.luck = min(3.0, self.luck + 1.0)
            self.toast('Biscuit purrs happily. You feel lucky today!', (200, 130, 80))

    def read_request(self):
        r = self.request
        if r is None:
            return
        name = FISH_BY_ID[r['fish']]['name']
        if r.get('birthday') and not r.get('done'):
            body = ("It's my birthday today! Could you catch me a %s? I'd love that more than any cake, "
                    "and I'll send a little something back.\n\nHint: %s" % (name, FISH_BY_ID[r['fish']]['hint']))
        elif r.get('done'):
            body = "You already helped me today. Thank you again! I'll write tomorrow."
        else:
            body = ('Could you catch me %d %s? %s I will pay %d coins. (So far: %d of %d)\n\nHint: %s'
                    % (r['need'], name, r['why'], r['reward'], r['have'], r['need'], FISH_BY_ID[r['fish']]['hint']))
        self.letter = ('Dear neighbour,', body, '- ' + r['who'])
        self.overlay = 'letter'
        self.release_holds()
        self.audio.play('page', 0.7)

    def try_rest(self):
        if self.fishing.state not in ('idle', 'charging'):
            self.toast('Finish what is on the line first.')
            return
        m = self.minute
        if (m >= 1080 or m < 300) and self.net.online and self.net.peers:
            self.mp_ready = not self.mp_ready
            if self.mp_ready:
                self.fishing.reset()
                self.release_holds()
                waiting = [p['name'] for p in self.net.peers.values() if not p.get('v', {}).get('rest')]
                self.toast('You settle down to rest. Waiting for %s.' % ', '.join(waiting) if waiting
                           else 'You settle down to rest.', (120, 130, 200))
            else:
                self.toast('You get back up. The night is young.', (150, 140, 130))
            self.net_send_t = 0
        elif m >= 1080 or m < 300:
            self.rest_phase = 'out'
            self.fishing.reset()
            self.release_holds()
        else:
            self.toast('Too early for bed. You can rest after 6 PM.')

    def sleep_now(self):
        old_season = self.season_of(self.day)
        clubmod.finish(self)
        f = self.festival
        if self.festival_today() and not f.get('done'):
            if f['best']:
                self.finish_festival()
            else:
                f['done'] = True
        if self.stats.get('boat_loan') == self.day and not self.owns_boat():
            self.toast("Wren rowed her boat home. She's 500 coins at the wagon whenever you're ready.",
                       (70, 140, 150))
        if self.minute >= 300:
            self.day += 1
        self.minute = 360.0
        self.spot = 'dock'                 # you row home to sleep
        self.place = 'lake'                # ...or walk home from the village
        if self.overlay in ('aquarium', 'harbour', 'farshore', 'drive', 'area', 'truck'):
            self.overlay = None
        self.aqscene = None
        self.road_trip = None
        self.audio.engine(0)
        self.mp_ready = False
        self.net_world_t = 0               # host: tell everyone it is morning right away
        self.luck = max(0.0, self.luck - 0.5)
        if self.has_up('loft'):
            self.luck = min(3.0, self.luck + 0.6)
        self.env.season = self.season_of(self.day)
        self.roll_weather('morning')
        self.env.weather = self.weather
        self.env.minute = self.minute
        self.env.day = self.day
        self.env.settle()
        ns = self.season_of(self.day)
        self.toast('Good morning! %s, %s %d.' % (almanac.weekday(self.day), SEASONS[ns], almanac.dow(self.day)),
                   (200, 150, 80))
        self.start_day()
        if ns != old_season:
            self.toast('%s has arrived at the lake.' % SEASONS[ns], (110, 150, 100))
        self.save()

    def release_holds(self):
        self.mouse_hold = False
        self.space_hold = False
        self.holding = False
        if self.fishing.state == 'charging':
            self.fishing.state = 'idle'

    # ------------------------------------------------------------ shop actions
    def buy(self, kind, item):
        price = item['price'] if kind != 'bait' else item['price']
        if self.coins < price:
            self.toast('Not enough coins yet.', (200, 120, 100))
            self.audio.play('nibble', 0.5)
            return
        self.coins -= price
        if kind == 'rod':
            self.rods.append(item['id'])
            self.rod = item['id']
            self.toast('You got the %s!' % item['name'], (110, 150, 100))
        elif kind == 'bait':
            self.baits[item['id']] = self.baits.get(item['id'], 0) + item['pack']
            self.bait = item['id']
        elif kind == 'hat':
            self.hats.append(item['id'])
            self.hat = item['id']
            self.toast('You put on the %s. Lovely!' % item['name'], (110, 150, 100))
        elif kind == 'cat':
            self.cat_items.append(item['id'])
            self.cat_item = item['id']
            self.toast('Biscuit looks very proud in her %s.' % item['name'], (200, 130, 80))
        elif kind == 'boat':
            self.owned.append('boat')
            self.toast('The rowboat is tied up by your dock. Press B to open the lake map!', (90, 140, 180))
            self.mark(172, 300, 'your rowboat')
        else:
            self.owned.append(item['id'])
            self.toast('%s added to the dock.' % item['name'], (110, 150, 100))
            x, y = DOCK_PROP_POS.get(item['id'], (190, DECK_Y - 8))
            self.mark(x, y, item['name'])
            self.note('buy', name=item['name'])
        self.audio.play('coin', 0.8)
        self.check_badges()
        self.save()

    def sell_stack(self, fid):
        items = [b for b in self.basket if b['id'] == fid]
        if not items:
            return
        self.sell_fish(items)
        self.audio.play('coin', 0.8)
        self.save()

    def sell_all(self):
        if not self.basket:
            return
        total = self.sell_fish(list(self.basket))
        self.audio.play('coin', 0.9)
        self.toast('Sold all your fish for %d coins.' % total, (200, 160, 70))
        self.save()

    def cycle_bait(self):
        opts = ['worm'] + [b['id'] for b in BAITS[1:] if self.baits.get(b['id'], 0) > 0]
        i = opts.index(self.bait) if self.bait in opts else 0
        self.bait = opts[(i + 1) % len(opts)]
        self.audio.play('ui', 0.5)

    # ------------------------------------------------------------ main loop
    def frame_cap_screen(self):
        try:
            hz = pygame.display.get_desktop_refresh_rates()[0]
        except (AttributeError, IndexError, pygame.error):
            hz = 60
        return hz if 30 <= hz <= 360 else 60

    def frame_cap(self):
        """The frame rate to hold. 'Screen' (0) lets vsync pace the GPU path (with a safety cap), and uses the
        screen's refresh rate on the CPU path."""
        fps = self.settings.get('fps', 0)
        if fps:
            return fps
        if self.gpu and self.gpu.vsync:
            return 360
        return self.frame_cap_screen()

    def watch_speed(self, work, dt):
        """Light effects on Auto: if frames keep taking longer than the frame rate allows, ease the effects off
        (and bring them back later if there's plenty of room again)."""
        p = self._perf
        p[0] += (work - p[0]) * min(1.0, dt * 2)
        if self.settings.get('fx') != 'auto' or self.mode != 'play' or self.overlay:
            p[1] = p[2] = 0.0
            return
        fps = self.settings.get('fps') or self.frame_cap_screen()
        budget = 1.0 / max(30, min(fps, 144))
        if not self.fx_low:
            p[1] = p[1] + dt if p[0] > budget * 0.92 else max(0.0, p[1] - dt)
            if p[1] > 4.0:
                self.fx_low = True
                p[1] = p[2] = 0.0
        else:
            p[2] = p[2] + dt if p[0] < budget * 0.4 else 0.0
            if p[2] > 30.0:
                self.fx_low = False
                p[1] = p[2] = 0.0

    def gpu_fallback(self):
        """The graphics card stopped working for us: carry on with the CPU path in a plain window."""
        size = self.gpu.size if self.gpu else (1280, 720)
        try:
            self.gpu.window.destroy()
        except Exception:
            pass
        self.gpu = None
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.fullscreen = False
        self._ui_pct = None
        self.apply_ui_scale()

    def run(self):
        last = time.perf_counter()
        while self.running:
            self.clock.tick(self.frame_cap())
            now = time.perf_counter()
            dt = min(0.05, max(0.0, now - last))      # measured, not rounded to whole milliseconds
            last = now
            self.handle_events()
            self.update(dt)
            self.draw()
            if not self.gpu:
                pygame.display.flip()
            self.watch_speed(max(0.0, getattr(self, '_t_present', now) - now), dt)
        if self.mode == 'play':
            self.save()
        self.net_shutdown()
        pygame.quit()

    def key_steer(self):
        self.steer_mode = 'keys'
        self.mouse_acc = 0

    def mouse_move(self, pos, steer=True):
        self.ui.mouse = pos
        self.ui.mouse_moved = True
        if steer:
            self.steer_mode = 'mouse'
        if self.drag:
            self.drag_to(pos)

    def mouse_down(self, pos):
        self.ui.mouse = pos
        self.ui.mouse_down = True
        if self.overlay == 'catch' and self.card and self.card['t'] < 0:
            self.card['t'] = 0.0
            return
        if self.typing:
            self.typing = None        # clicking elsewhere ends typing (a text field click starts it again)
        act = self.ui.click(pos)
        if act:
            act()
            return
        if self.overlay == 'cooking' and self.cooking:
            self.cooking.press('mouse')
            return
        if self.overlay == 'ice' and self.icescene:
            self.icescene.press('mouse')
            return
        if self.overlay == 'dungeon' and self.dungeon:
            self.dungeon.press('mouse')
            return
        if self.walk_scene():
            self.aqscene.press('mouse')
            return
        if self.overlay == 'scene' and self.scene:
            self.scene.press()
            return
        if (self.mode == 'play' and self.overlay is None and self.hide_ui and self.place == 'lake'
                and self.fishing.state in ('idle', 'waiting')):
            wildlife.snap(self)
            return
        if self.mode == 'play' and self.overlay is None and self.rest_phase is None:
            wx, wy = self.s2w(*pos)
            if self.place == 'town':
                self.town.click(self, wx, wy)
                return
            if self.fishing.state == 'idle' and self.world_click(wx, wy):
                return
            self.mouse_hold = True
            self.fishing.press()

    def mouse_up(self):
        self.ui.mouse_down = False
        self.end_drag()
        if self.cooking:
            self.cooking.release('mouse')
        if self.icescene:
            self.icescene.release('mouse')
        if self.dungeon:
            self.dungeon.release('mouse')
        if self.walk_scene():
            self.aqscene.release('mouse')
        if self.mouse_hold:
            self.mouse_hold = False
            if not self.space_hold:
                self.fishing.release()

    def key_up(self, k):
        if k == pygame.K_SPACE and self.cooking:
            self.cooking.release('key')
        if k == pygame.K_SPACE and self.icescene:
            self.icescene.release('key')
        if k == pygame.K_SPACE and self.dungeon:
            self.dungeon.release('key')
        if k in (pygame.K_SPACE, pygame.K_e, pygame.K_RETURN) and self.walk_scene():
            self.aqscene.release('key')
        if k == pygame.K_SPACE and self.space_hold:
            self.space_hold = False
            if not self.mouse_hold:
                self.fishing.release()

    def prompt_layout(self):
        """Which buttons the hints show: None for keyboard and mouse, or 'xbox' / 'ps' / 'switch'."""
        pad = self.pad
        if pad is None or not pad.connected:
            return None
        pick = self.settings.get('prompts', 'auto')
        if pick == 'keyboard':
            return None
        if pick != 'auto':
            return pick
        return pad.layout if self.last_input == 'pad' else None

    def binds(self):
        b = getattr(self, '_binds', None)
        if b is None or b.settings is not self.settings:
            b = self._binds = bindsmod.Binds(self.settings)
            self.ui.key_labels = b.labels
        return b

    def rebind(self, action):
        self.rebinding = action
        self.audio.play('ui', 0.5)

    def finish_rebind(self, k):
        a, self.rebinding = self.rebinding, None
        if k == pygame.K_ESCAPE:
            self.audio.play('ui', 0.4)
            return
        b = self.binds()
        if b.assign(a, k):
            self.ui.key_labels = b.labels
            self.save_settings()
            self.audio.play('chime2', 0.5)
        else:
            self.toast('That key is kept for something else.', (200, 120, 100))
            self.audio.play('nibble', 0.5)

    def reset_binds(self):
        b = self.binds()
        b.reset()
        self.ui.key_labels = b.labels
        self.save_settings()
        self.audio.play('ui', 0.6)

    def cap_icon(self, key, button):
        """A keycap to sit beside a button's label, or that controller's own button while a pad is in use."""
        ui = self.ui
        if ui.pad_layout:
            surf = pygame.Surface((ui.pad_w(button), 24), pygame.SRCALPHA)
            ui.padcap(surf, button, (0, 12), 'midleft')
        else:
            label = ui.key_labels.get(key, key)
            surf = pygame.Surface((max(24, ui.fonts['tiny'].size(label)[0] + 12) + 2, 24), pygame.SRCALPHA)
            ui.keycap(surf, key, (0, 12), 'midleft', pad=False)
        return surf

    def hint(self, kb, pad):
        """Pick the keyboard or the controller version of a hint line."""
        return pad if self.ui.pad_layout else kb

    def keys(self):
        """The keys held down right now, keyboard and gamepad together (and through your key bindings)."""
        real = self.binds().held(pygame.key.get_pressed())
        return self.pad.keys(real) if self.pad else real

    def handle_events(self):
        if self.pad is None and not HEADLESS:
            self.pad = padmod.Pad(self)
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.WINDOWCLOSE and self.gpu):
                self.running = False
            elif self.pad and self.pad.event(e):
                pass
            elif e.type == pygame.MOUSEMOTION:
                # a bumped mouse or a click's wobble must not steal the reel from the keys: the mouse only takes
                # over after it has really travelled
                self.mouse_acc += abs(e.rel[0]) + abs(e.rel[1])
                self.mouse_move(self.to_logical(e.pos), steer=self.mouse_acc > 40)
                if abs(e.rel[0]) + abs(e.rel[1]) > 3:        # a real nudge, not a bumped desk
                    self.last_input = 'kb'
                    if self.pad:
                        self.pad.cursor = None      # the real mouse takes over from the pad pointer
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                self.last_input = 'kb'
                self.mouse_down(self.to_logical(e.pos))
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                self.mouse_up()
            elif e.type == getattr(pygame, 'WINDOWFOCUSLOST', -1):
                self.release_holds()
                if self.pad:
                    self.pad.release_all()
                if self.cooking:
                    self.cooking.holds.clear()
                self.ui.mouse_down = False
                self.end_drag()
                if (self.settings.get('bg_pause') and self.mode == 'play' and self.overlay is None
                        and self.rest_phase is None and not self.net.online):
                    self.overlay = 'pause'
            elif e.type == pygame.TEXTINPUT and self.typing:
                self.type_text(e.text)
            elif e.type == pygame.KEYDOWN:
                if e.key not in (pygame.K_F11, pygame.K_F12):
                    self.last_input = 'kb'
                if getattr(self, 'rebinding', None):
                    self.finish_rebind(e.key)           # Options > Controls: waiting for a new key
                elif self.typing and e.key != pygame.K_F11:
                    self.typing_key(e.key)
                else:
                    k = self.binds().map(e.key)
                    if k is not None:
                        self.key_down(k)
            elif e.type == pygame.KEYUP:
                k = self.binds().map(e.key)
                if k is not None:
                    self.key_up(k)
        if self.pad:
            self.pad.update(self.clock.get_time() / 1000.0 if self.clock.get_time() else 1 / 60)
        self.holding = self.mouse_hold or self.space_hold

    def key_down(self, k):
        if k == pygame.K_F11:
            self.set_fullscreen(not self.fullscreen)
            return
        if k == pygame.K_F12:
            self.screenshot()
            return
        if self.mode == 'play' and not self.typing and (
                k == pygame.K_F1 or (k == pygame.K_SLASH and pygame.key.get_mods() & pygame.KMOD_SHIFT)):
            self.toggle_help()
            return
        ov = self.overlay
        if self.mode == 'title' or ov in ('pause', 'options', 'quick', 'creator'):
            ui = self.ui
            if k in (pygame.K_UP, pygame.K_LEFT, pygame.K_w):
                ui.nav_move(-1)
                self.audio.play('ui', 0.3)
            elif k in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_s):
                ui.nav_move(1)
                self.audio.play('ui', 0.3)
            elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                act = ui.nav_action()
                if act:
                    act()
                elif self.mode == 'title' and ov is None:
                    if self.has_save:
                        self.start_game(True)
                    else:
                        self.new_game()
            elif k == pygame.K_ESCAPE:
                if ov == 'creator':
                    creator.cancel(self)
                elif ov == 'options':
                    self.close_options()
                elif ov == 'pause':
                    self.close_overlay()
                elif ov == 'lobby':
                    self.close_lobby()
                elif ov in ('slots', 'quick'):
                    self.overlay = None
                    self.audio.play('page', 0.5)
                else:
                    self.running = False
            return
        if ov == 'cooking' and self.cooking:
            self.cooking.key(k)
            return
        if ov == 'ice' and self.icescene:
            self.icescene.key(k)
            return
        if ov == 'dungeon' and self.dungeon:
            self.dungeon.key(k)
            return
        if self.walk_scene():
            self.aqscene.key(k)
            return
        if ov == 'scene' and self.scene:
            self.scene.key(k)
            return
        if ov == 'cabin' and k == pygame.K_TAB:
            self.cycle_cabin_tab(-1 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
            return
        if ov == 'lanterns' and k in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
            self.set_lan_tab('legends' if self.lan_tab == 'lanterns' else 'lanterns')
            return
        if self.hide_ui and ov is None and self.mode == 'play' and self.fishing.state in ('idle', 'waiting'):
            if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                wildlife.snap(self)
                return
            if k == pygame.K_ESCAPE:
                self.hide_ui = False
                self.audio.play('page', 0.4)
                return
        if k == pygame.K_ESCAPE:
            if ov == 'catch':
                self.keep_catch()
            elif ov == 'letter':
                self.close_letter()
            elif ov == 'stall':
                stallmod.close(self)
            elif ov:
                self.overlay = None
                self.audio.play('page', 0.5)
            else:
                self.overlay = 'pause'
                self.release_holds()
            return
        if ov == 'catch':
            if self.card['t'] < 0:
                if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_k, pygame.K_e):
                    self.card['t'] = 0.0             # on to the card
                return
            if self.card['t'] < 0.4:
                return
            if k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_k):
                self.keep_catch()
            elif k == pygame.K_r:
                self.release_catch()
            elif k == pygame.K_t:
                self.tank_catch()
            return
        if ov == 'letter':
            if k in (pygame.K_SPACE, pygame.K_RETURN):
                self.close_letter()
            return
        if ov == 'ringtoss' and k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            tn = self.town
            if tn.rt['rings'] > 0:
                tn.throw(self)
            elif not tn.rt['fly']:
                tn.start_toss(self)
            return
        if k in (pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT):
            self.key_steer()
        if k == pygame.K_j:
            self.toggle('journal')
        elif k == pygame.K_k:
            self.toggle('calendar')
        elif k == pygame.K_l and ov in (None, 'lanterns'):
            if ov == 'lanterns':
                self.close_overlay()
            elif self.story['started']:
                self.overlay = 'lanterns'
                self.release_holds()
                self.audio.play('page', 0.5)
        elif k == pygame.K_s:
            self.toggle('shop')
        elif k == pygame.K_c:
            if self.place == 'town' and ov != 'cabin':
                if not ov:
                    self.toast('Your cabin is down by the lake. Press T to walk home.', (150, 140, 130))
            else:
                self.toggle('cabin')
        elif k == pygame.K_b:
            if ov == 'map':
                self.toggle('map')
            elif not ov:
                self.open_map()
        elif k == pygame.K_q and ov in (None, 'goals'):
            self.toggle('goals')
        elif k == pygame.K_r and ov in (None, 'radio'):
            self.toggle('radio')
        elif k == pygame.K_v and ov in (None, 'truck'):
            if ov == 'truck':
                self.close_overlay()
            elif self.rest_phase is None:
                truckmod.open_(self)
        elif ov:
            return
        elif k == pygame.K_t:
            self.go_place('lake' if self.place == 'town' else 'town')
        elif self.place == 'town' and k in (pygame.K_SPACE, pygame.K_e, pygame.K_w, pygame.K_UP):
            if self.rest_phase is None:
                self.town.interact(self)
        elif k == pygame.K_e and self.place == 'lake' and self.rest_phase is None and self.has('pot'):
            seasons.pot_action(self)
        elif k == pygame.K_SPACE and self.rest_phase is None:
            self.space_hold = True
            self.fishing.press()
        elif k == pygame.K_z:
            self.try_rest()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.net.online and self.rest_phase is None:
            self.release_holds()
            self.typing = 'chat'
            pygame.key.start_text_input()
        elif pygame.K_1 <= k <= pygame.K_4:
            self.emote = [actors.EMOTES[k - pygame.K_1], 2.6]
            self.net_send_t = 0
        elif k == pygame.K_TAB:
            self.cycle_bait()
        elif k == pygame.K_p:
            self.hide_ui = not self.hide_ui
        elif k == pygame.K_g and self.net.online:
            self.toggle('coop')
        elif k == pygame.K_m:
            self.settings['music'] = 0.0 if self.settings['music'] > 0 else 0.5
            self.apply_settings()
            self.toast('Music %s' % ('on' if self.settings['music'] else 'off'))

    def toggle(self, name):
        if self.overlay == name:
            self.overlay = None
        elif self.overlay is None and self.fishing.state in ('idle', 'waiting'):
            if self.fishing.state == 'waiting':
                self.fishing.flee_shadow()
                self.fishing.to_reel_back()
            if name == 'calendar':
                self.cal_off = 0
                self.cal_sel = self.day
            self.overlay = name
            self.release_holds()
        else:
            return
        self.audio.play('page', 0.6)

    def close_letter(self):
        self.letter = None
        self.overlay = None
        self.audio.play('page', 0.5)
        self.next_queue()

    def start_game(self, continue_=True, look=None):
        if self.radio.station is None and self.settings.get('radio') in radiomod.BY_ID:
            self.radio.tune(self.settings['radio'])
        if not continue_:
            self.new_game_state()
            if look:
                self.look = looks.clean(look)        # made in the character creator
            self.env.minute = self.minute
            self.env.day = self.day
            self.env.season = 0
            self.env.weather = self.weather
            self.env.settle()
            self.fishing.reset()
            self.queue.append(('letter', INTRO))
            self.stats['almanac_day'] = 1
            self.mail().append(self.almanac_letter(1))     # waits in the mailbox; the flag is up
            self.has_save = True
            self.save()
        self.mode = 'play'
        self.fade = 1.0
        self.fade_dir = -1
        self.audio.play('ui', 0.6)
        if not HEADLESS:
            news.queue(self, continue_)          # an update since you last played: what's new
        self.next_queue()

    def screenshot(self):
        d = os.path.join(HERE, 'screenshots')
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, time.strftime('lantern_%Y%m%d_%H%M%S.png'))
        pygame.image.save(self.gpu.read() if self.gpu else pygame.display.get_surface(), path)
        self.toast('Photo saved to screenshots folder.', (110, 130, 170))

    # ------------------------------------------------------------ update
    def update(self, dt):
        self.t += dt
        env = self.env
        self.net_update(dt)
        paused = self.overlay is not None or self.rest_phase is not None
        if self.walk_scene() and self.aqscene.panel is None and self.rest_phase is None and \
                self.overlay != 'drive':
            paused = False                                 # strolling the aquarium or the quay: the day goes on
        if stallmod.running(self) and self.rest_phase is None:
            paused = False                                 # the market morning goes by while you sell
        if self.net.online:
            paused = self.rest_phase in ('out', 'in')     # with friends here the lake never stops
        if self.mode == 'play' and self.net.role == 'guest':
            self.guest_clock()
        elif self.mode == 'play' and not paused:
            self.advance_time(dt * MINUTES_PER_SECOND * self.day_speed() * (stallmod.SPEED if stallmod.running(self)
                                                                             else 1.0))
        elif self.mode == 'title':
            self.minute = (self.minute + dt * 1.0) % 1440
        env.minute = self.minute
        env.day = self.day
        env.season = self.season_of(self.day)
        env.weather = self.weather
        env.step(dt)
        self.world.update(dt, env, self)
        if self.overlay == 'cooking' and self.cooking:
            self.cooking.update(dt)
        if self.overlay == 'ice' and self.icescene:
            self.icescene.update(dt)
        if self.overlay == 'dungeon' and self.dungeon:
            self.dungeon.update(dt)
        if self.overlay == 'stall':
            stallmod.update(self, dt)
        truckmod.update(self, dt)
        if self.walk_scene():
            self.aqscene.update(dt)
        if self.mode == 'play':
            seasons.update(self, dt)
            biscuit.update(self, dt)
            gardenmod.update(self, dt)
            wildlife.update(self, dt)
            lakelife.update(self, dt)
            lakeshow.update(self, dt)
            tutorial.update(self, dt)
            goalmod.update(self, dt)
            coop.update(self, dt)
            story.update(self, dt)
            story.update_fx(self, dt)
        self.radio.update(dt)
        if self.place == 'town' and self.mode == 'play':
            walk = 0
            if self.typing is None and not HEADLESS:
                keys = self.keys()
                walk = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
                       (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
            self.town.update(dt, self, walk)
        if self.overlay == 'scene' and self.scene:
            self.scene.update(dt)
        if self.mode == 'play' and self.overlay is None and self.rest_phase is None and self.place == 'lake':
            self.fishing.update(dt)
        elif self.fishing.state in ('caught', 'reel_back', 'landing'):
            self.fishing.update(dt)
        else:
            self.fishing._rod_geometry()
        self.update_camera(dt)
        # cat
        c = self.cat
        c['excited'] = max(0, c['excited'] - dt)
        c['pet'] = max(0, c['pet'] - dt)
        c['sleep'] = (env.nf > 0.8 and c['excited'] <= 0 and c['pet'] <= 0 and not c.get('trick')
                      and self.fishing.state in ('idle', 'waiting'))
        if c['sleep']:
            c['z'] -= dt
            if c['z'] <= 0:
                c['z'] = 1.8
                self.world.zzz(actors.CAT_X + 6, DECK_Y - 14)
        if self.walk_scene():
            actx = self.aqscene.audio_ctx()
        elif self.place == 'town' and self.cooking is None:
            actx = self.town.audio_ctx(self)
        else:
            actx = dict(feeder=self.has('feeder'), chimes=self.has('chimes'))
        self.audio.update(dt, env, actx)
        hurry = 1.5 if self.toast_q else 1.0          # with more waiting, each one moves along a little sooner
        for tt in self.toasts:
            tt[1] -= dt * hurry
        self.toasts = [tt for tt in self.toasts if tt[1] > 0]
        while self.toast_q and len(self.toasts) < self.toast_max():
            self.toasts.append(self.toast_q.pop(0))
        self._new_t = getattr(self, '_new_t', 0.0) - dt
        if self._new_t <= 0 and self.mode == 'play':
            # every few seconds: is there a fish you've never caught that could bite here right now?
            self._new_t = 4.0
            fish = fishmod.new_now(self) if self.place == 'lake' else []
            why = fishmod.why_now(self, fish)
            ids = {f['id'] for f in fish}
            seen = getattr(self, '_new_seen', None)
            if fish and why and seen is not None and ids - seen and self.overlay is None and self.rest_phase is None:
                self.toast('Something new is stirring %s. A fish you have never caught could bite now!'
                           % ' and '.join(why), (110, 150, 190))
            self._new_seen = ids
            self._new_now = (fish, why) if fish else None
        sm = self.spot_mark
        if sm:
            sm['t'] -= dt
            if sm['t'] <= 0:
                self.spot_mark = None
        qp = self.quick_pop
        if qp:
            qp['t'] += dt
            if qp['t'] > 3.2:
                self.quick_pop = None
        if self.card:
            self.card['t'] += dt
        # fades
        if self.rest_phase == 'out':
            self.fade = min(1.0, self.fade + dt / 1.1)
            if self.fade >= 1:
                self.sleep_now()
                self.rest_phase = 'in'
        elif self.rest_phase == 'row_out':
            self.fade = min(1.0, self.fade + dt / 0.7)
            if self.fade >= 1:
                to = self.travel_to or 'dock'
                if to in CROSS_POS and self.spot in CROSS_POS and self.place == 'lake':
                    # a short row across the lake: you watch the boat cross (three seconds or so)
                    self.crossing = dict(t=0.0, dur=3.2, frm=self.spot, to=to)
                    self.rest_phase = 'row_cross'
                    bx, by = cross_at(self.crossing)
                    self.cam = [1.45, clamp(bx, W / 2.9, W - W / 2.9), clamp(by - 20, H / 2.9, H - H / 2.9)]
                else:
                    self.arrive()
                    self.rest_phase = 'row_in'
        elif self.rest_phase == 'row_cross':
            c = self.crossing
            c['t'] += dt
            k, dur = c['t'], c['dur']
            self.fade = max(0.0, 1 - k / 0.45) if k < dur - 0.5 else min(1.0, (k - (dur - 0.5)) / 0.45)
            if k >= dur:
                self.fade = 1.0
                self.crossing = None
                self.arrive()
                self.rest_phase = 'row_in'
        elif self.rest_phase == 'walk_out':
            self.fade = min(1.0, self.fade + dt / 0.7)
            if self.fade >= 1:
                self.arrive_place()
                self.rest_phase = 'walk_in'
        elif self.rest_phase in ('in', 'row_in', 'walk_in'):
            self.fade = max(0.0, self.fade - dt / (1.4 if self.rest_phase == 'in' else 0.9))
            if self.fade <= 0:
                self.rest_phase = None
        elif self.fade_dir < 0:
            self.fade = max(0.0, self.fade - dt / 1.2)
        self.confirm_new = max(0, self.confirm_new - dt)
        if self.overlay == 'cabin':
            self.tankview.update(dt, self.tank)
        if self.mode == 'play' and self.queue and self.overlay is None and self.rest_phase is None:
            self.next_queue()
        if self.mode == 'play':
            self.save_t -= dt
            if self.save_t <= 0:
                self.save_t = 60
                self.save()

    # ------------------------------------------------------------ camera and input helpers
    HOME_Z = 2.0           # how close the camera sits on you and the dock between casts

    def view_lift(self):
        """How much sky the resting shot shows: the far horizon out on the Deep, the willows over the creek,
        and more of the sky at sunrise, sunset and under the stars."""
        if self.place != 'lake':
            return 0
        lift = {'deep': 26, 'creek': 14, 'cove': 4}.get(self.spot, 0)
        m = self.minute
        if 300 <= m < 450 or 1050 <= m < 1250:
            lift += 22
        elif m >= 1250 or m < 300:
            lift += 26 if self.weather == 'clear' else 12      # a clear night: more of the stars
        return min(40, lift)

    def update_camera(self, dt):
        f = self.fishing
        z, fx, fy = 1.0, W / 2, H / 2
        if self.mode == 'play' and f.state == 'fight' and f.fish_pos:
            # in close on the fight: you at one edge, the fish thrashing on the line at the other
            fxp, fyp = f.fish_pos[0], f.fish_pos[1] - f.leap_h
            lo, hi = min(PLAYER_X - 40, fxp - 50), max(PLAYER_X + 30, fxp + 50)
            z = clamp(W / max(1.0, hi - lo), 1.35, 2.1)
            if f.mg and f.mg.leap:
                z = min(2.3, z * 1.12)
            fx = (lo + hi) / 2
            fy = (fyp + DECK_Y - 30) / 2 + 10
        elif f.state == 'landing' and f.fly_pos:
            z = 1.08
            fx = W / 2 + (f.fly_pos[0] - W / 2) * 0.5
            fy = H / 2 + (f.fly_pos[1] - H / 2) * 0.5
        rate = 3.0
        st = f.state
        if (self.mode == 'play' and self.place != 'town' and not self.walk_scene()
                and self.overlay in (None, 'catch') and st not in ('fight', 'landing')):
            rate = 2.2
            if st == 'charging' or (st in ('casting', 'waiting', 'bite') and f.bob):
                # a cast: frame you and where the line is going (or went)
                if st == 'charging':
                    rod = self.rod_spec()
                    tx = cast_point(rod['range'], f.aim)[0]
                else:
                    tx = f.dst[0]
                lo, hi = min(PLAYER_X - 70, tx - 50), max(PLAYER_X + 60, tx + 50)
                z = clamp(W / max(1.0, hi - lo), 1.0, 1.6)
                fx = (lo + hi) / 2
                fy = H - H / z / 2 - 18
                if st in ('waiting', 'bite'):
                    rate = 1.3
            else:
                # at rest: in close on you and the dock, and the view drifts toward wherever you point
                z = self.HOME_Z
                w = W / z
                self.cam_look += (self.ui.mouse[0] / SW - self.cam_look) * min(1.0, dt * 2.5)
                # you and Biscuit a third of the way in, the open lake ahead; pointing pans a little
                fx = clamp(PLAYER_X + w * 0.17 + (self.cam_look - 0.5) * w * 0.55, w / 2, W - w / 2)
                fy = H - H / z / 2 - 2 - self.view_lift()      # down on the water: most of the sky cropped away
        elif self.mode == 'play' and self.place == 'town' and self.overlay is None:
            # Fernwick: in close on the street and the people on it, not on the sky
            tn = self.town
            rate = 2.5
            if tn.sitting is not None:
                z = 2.3                    # sitting on the lookout bench: just you, Biscuit and the lake
                px = townmod.BENCH_X + 6 - tn.scroll
                fy = townmod.GROUND - 30
                rate = 0.9
            else:
                z = townmod.TOWN_Z
                px = tn.x - tn.scroll
                fy = townmod.GROUND + 36 - H / z / 2     # the street low on screen, with a little sky over the roofs
            w = W / z
            fx = clamp(px, w / 2, W - w / 2)
        if self.rest_phase == 'row_cross' and self.crossing:
            # follow the boat across, a little way back so the lake and its far shore are in the shot
            bx, by = cross_at(self.crossing)
            z = 1.45
            w, h = W / z, H / z
            fx = clamp(bx, w / 2, W - w / 2)
            fy = clamp(by - 20, h / 2, H - h / 2)
            rate = 4.0
        elif not self.settings.get('zoom', True):
            z, fx, fy = 1.0, W / 2, H / 2
        if self.shake_amt > 0.05:
            z = max(z, 1.03)
        k = min(1.0, dt * rate)
        c = self.cam
        c[0] += (z - c[0]) * k
        if abs(z - c[0]) < 0.001:
            c[0] = z                     # settle exactly: a zoom of 1.9999 can't sit on whole pixels
        c[1] += (fx - c[1]) * k
        c[2] += (fy - c[2]) * k
        self.shake_amt = max(0.0, self.shake_amt - dt * 6)

    def cam_view_f(self):
        """What the camera sees, in world pixels, not rounded: (x, y, w, h). Zooms and pans glide between
        art pixels instead of stepping a whole pixel at a time."""
        z, fx, fy = self.cam
        if z < 1.002 and self.shake_amt <= 0.05:
            return (0.0, 0.0, float(W), float(H))
        z = max(1.0, z)
        w, h = W / z, H / z
        x = fx - w / 2 + random.uniform(-1, 1) * self.shake_amt
        y = fy - h / 2 + random.uniform(-1, 1) * self.shake_amt
        f = self.fishing
        if f.state == 'fight':
            x = min(x, actors.CAT_X - 10 - 250 * w / SW)       # keep Biscuit and you clear of the reel ring
            if f.fish_pos:
                x = max(x, f.fish_pos[0] + 24 - w)              # ...but never lose sight of the fish
        return (clamp(x, 0.0, W - w), clamp(y, 0.0, H - h), w, h)

    def cam_view(self):
        x, y, w, h = self.cam_view_f()
        w, h = int(round(w)), int(round(h))
        return pygame.Rect(int(clamp(round(x), 0, W - w)), int(clamp(round(y), 0, H - h)), w, h)

    def w2s(self, x, y):
        rx, ry, rw, rh = self.cam_f
        return (int((x - rx) * SW / rw), int((y - ry) * SH / rh))

    def s2w(self, px, py):
        rx, ry, rw, rh = self.cam_f
        return (rx + px * rw / SW, ry + py * rh / SH)

    def reel_input(self):
        """(aim angle on the reel ring or None, steer -1/0/1) for the reeling minigame."""
        if self.bot_aim is not None:
            return self.bot_aim, 0
        keys = self.keys()
        steer = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - \
                (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        if steer:
            self.key_steer()
            return None, steer
        if self.steer_mode == 'mouse':
            mx, my = self.ui.mouse
            if math.hypot(mx - minigame.CX, my - minigame.CY) > 6:
                return math.degrees(math.atan2(my - minigame.CY, mx - minigame.CX)), 0
        return None, 0

    def aim_cast(self, dt):
        """While winding up: aim the cast with the mouse over the lake, or the arrow keys."""
        f = self.fishing
        keys = self.keys()
        k = (1 if (keys[pygame.K_d] or keys[pygame.K_RIGHT]) else 0) - \
            (1 if (keys[pygame.K_a] or keys[pygame.K_LEFT]) else 0)
        if k:
            self.key_steer()
            f.aim = clamp(f.aim + k * dt * 1.4, -1.0, 1.0)
        elif self.steer_mode == 'mouse' and not HEADLESS:
            wx, wy = self.s2w(*self.ui.mouse)
            if wx > 270 and wy > 180:
                rod = self.rod_spec()
                f.aim = aim_for(0.1 + f.power * (rod['range'] - 0.1), wx)

    # ------------------------------------------------------------ draw
    def draw(self):
        ui = self.ui
        self.view_info = self.calc_view()
        ui.begin_frame(self.view_info[2])
        ui.pad_layout = self.prompt_layout()
        ui.hot = []
        ui.nav = []
        ui.set_nav_owner((self.mode, self.overlay, self.opt_tab if self.overlay == 'options' else
                          (self.cre['tab'] if self.overlay == 'creator' else None)))
        cooking = self.cooking if self.overlay == 'cooking' and self.mode == 'play' else None
        if cooking is None and self.overlay == 'ice' and self.icescene and self.mode == 'play':
            cooking = self.icescene          # drawn and framed just like the kitchen scene
        if cooking is None and self.overlay == 'dungeon' and self.dungeon and self.mode == 'play':
            cooking = self.dungeon           # so is the Drowned Stair
        if cooking is None and self.walk_scene() and self.mode == 'play':
            cooking = self.aqscene           # so is the walk round the aquarium, or the harbour
        if cooking:
            cooking.draw_world(self.frame)
        elif self.place == 'town' and self.mode == 'play':
            self.town.draw(self.frame, self.env, self)
        else:
            self.world.draw(self.frame, self.env, self)
        scene = self.scene if self.overlay == 'scene' and self.mode == 'play' else None
        if scene:
            scene.draw_world(self.frame)
        if cooking or scene:
            self.cam_rect = cooking.cam() if cooking else scene.cam(self.cam_view())
            r = self.cam_rect
            self.cam_f = (float(r.x), float(r.y), float(r.w), float(r.h))
        else:
            self.cam_f = self.cam_view_f()
            self.cam_rect = self.cam_view()
        cv = self.canvas
        self._wsrc = self.frame
        if self.layered:
            cv.fill((0, 0, 0, 0))
        else:
            self._world_into(cv)                 # at twice the art's size: the camera moves in half-pixels
        ui.target = cv
        scr = cv
        if self.mode == 'title':
            self.draw_title(scr)
            if self.overlay in ('options', 'lobby', 'slots', 'creator'):
                ui.hot = []
                ui.nav = []
                scr = ui.stage()
                self.dim(scr)
                {'options': self.draw_options, 'lobby': self.draw_lobby, 'slots': self.draw_slots,
                 'creator': lambda sc: creator.draw(self, sc)}[self.overlay](scr)
        elif cooking:
            cooking.draw_ui(scr)
        elif scene:
            scene.draw_ui(scr)
        elif not self.hide_ui and self.rest_phase != 'row_cross':
            if self.overlay is None:
                self.draw_world_marks(scr)
                self.draw_hud(scr)            # a window that's open stands alone: no HUD peeking out behind it
            tutorial.draw(self, scr)
            ov = self.overlay
            showoff = ov == 'catch' and self.card and self.card['t'] < 0
            if ov and not showoff:
                ui.hot = []          # the HUD underneath is not clickable while a window is open
                ui.nav = []
                scr = ui.stage()
                self.dim(scr)
            if showoff:
                ui.hot = []
                ui.nav = []
                self.draw_showoff(scr)
            elif ov == 'catch':
                self.draw_card(scr)
            elif ov == 'journal':
                self.draw_journal(scr)
            elif ov == 'shop':
                self.draw_shop(scr)
            elif ov == 'letter':
                self.draw_letter(scr)
            elif ov == 'pause':
                self.draw_pause(scr)
            elif ov == 'options':
                self.draw_options(scr)
            elif ov == 'cabin':
                self.draw_cabin(scr)
            elif ov == 'creator':
                creator.draw(self, scr)
            elif ov == 'coop':
                coop.draw_panel(self, scr)
            elif ov == 'shore':
                shoremod.draw_panel(self, scr)
            elif ov == 'calendar':
                almanac.draw(self, scr)
            elif ov == 'map':
                self.draw_map(scr)
            elif ov in townmod.PANELS:
                townmod.draw_panel(self, scr, ov)
            elif ov == 'lanterns':
                story.draw_panel(self, scr)
            elif ov == 'goals':
                goalmod.draw_panel(self, scr)
            elif ov == 'radio':
                self.radio.draw_panel(scr)
            elif ov == 'news':
                news.draw(self, scr)
            elif ov == 'quick':
                self.draw_quick(scr)
            elif ov == 'stall':
                stallmod.draw(self, scr)
            elif ov == 'truck':
                truckmod.draw(self, scr)
        elif self.rest_phase == 'row_cross':
            pass                                     # rowing across: just the lake and the boat
        elif self.mode == 'play' and self.place == 'lake':
            wildlife.draw_viewfinder(self, scr)
        elif self.t % 6 < 2:
            ui.blit_text(scr, 'Photo mode - P to return, F12 to save a picture', (SW // 2, SH - 30),
                         'small', (250, 240, 220), 'center', (30, 20, 30))
        if self.quick_pop and self.mode == 'play' and not self.hide_ui:
            self.draw_quick_pop(cv)
        if self.toasts and self.mode == 'play':
            self.draw_toasts(cv)
        if self.rest_phase == 'row_cross' and self.crossing:
            c = self.crossing
            a = max(0.0, min(1.0, c['t'] / 0.5, (c['dur'] - c['t']) / 0.5))
            ui.blit_text(cv, 'Rowing to %s...' % SPOT_BY_ID[c['to']]['name'], (SW // 2, 70), 'h2',
                         (252, 246, 232), 'center', alpha=int(255 * a), outline=(30, 26, 40))
        if self.fade > 0.005:
            self._fadebuf.fill((14, 12, 26, int(255 * self.fade)))
            cv.blit(self._fadebuf, (0, 0))
            if self.rest_phase in ('out', 'in'):
                ui.blit_text(cv, 'z z z', (SW // 2, SH // 2), 'h1', (200, 200, 230), 'center')
            elif self.rest_phase in ('row_out', 'row_in'):
                to = self.travel_to or self.spot
                where = SPOT_BY_ID[to]['name']
                text = 'Rowing to %s...' % where
                if self.rest_phase == 'row_out' and coast.region(to) != coast.region(self.spot):
                    text = ('Rowing down the river to Saltmarsh...' if to in COAST_IDS else
                            'Rowing back up the river to Lantern Lake...')
                ui.blit_text(cv, text, (SW // 2, SH // 2), 'h2', (220, 226, 240), 'center',
                             alpha=int(255 * self.fade))
            elif self.rest_phase in ('walk_out', 'walk_in'):
                to = self.place_to or self.place
                ui.blit_text(cv, 'Walking up to Fernwick...' if to == 'town' else 'Walking home to the lake...',
                             (SW // 2, SH // 2), 'h2', (220, 226, 240), 'center', alpha=int(255 * self.fade))
        if self.settings.get('show_fps'):
            ui.blit_text(cv, '%d fps' % round(self.clock.get_fps()), (SW - 18, 184), 'smallb', (255, 250, 230),
                         'topright', outline=(20, 16, 24))
        if self.pad:
            self.pad.draw(cv)
        self.present()
        ui.mouse_moved = False

    def dim(self, s):
        d = getattr(self, '_dim', None)
        if d is None:
            d = self._dim = pygame.Surface((SW, SH), pygame.SRCALPHA)
            d.fill((20, 14, 30, 150))
        s.blit(d, (0, 0))

    def panel_header(self, s, rect, title):
        """A soft title band across the top of a big window."""
        band = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, 74)
        pygame.draw.rect(s, (240, 227, 202), band, border_top_left_radius=22, border_top_right_radius=22)
        pygame.draw.line(s, (216, 196, 164), (rect.x + 2, band.bottom), (rect.right - 3, band.bottom), 2)
        self.ui.blit_text(s, title, (rect.x + 34, rect.y + 17), 'h1', U.INK)

    # ---------------- title
    def _title_skin(self):
        sk = getattr(self, '_tskin', None)
        if sk is None:
            top = pygame.Surface((SW, 360), pygame.SRCALPHA)
            for y in range(360):
                pygame.draw.line(top, (16, 12, 30, int(170 * (1 - y / 360) ** 1.6)), (0, y), (SW, y))
            bot = pygame.Surface((SW, 260), pygame.SRCALPHA)
            for y in range(260):
                pygame.draw.line(bot, (16, 12, 30, int(150 * (y / 260) ** 1.8)), (0, y), (SW, y))
            glow = pygame.Surface((820, 300), pygame.SRCALPHA)
            for i in range(30, 0, -1):
                pygame.draw.ellipse(glow, (255, 206, 140, 4), (410 - i * 13, 150 - i * 4.6, i * 26, i * 9.2))
            dot = pygame.Surface((24, 24), pygame.SRCALPHA)
            for i in range(12, 0, -1):
                pygame.draw.circle(dot, (255, 236, 150, int(70 * (1 - i / 12) ** 1.5)), (12, 12), i)
            sk = self._tskin = dict(top=top, bot=bot, glow=glow, dot=dot,
                                    lglow=pygame.transform.smoothscale(dot, (150, 150)))
        return sk

    def draw_lantern(self, s, x, y, swing, scale=1.0):
        """A hanging paper lantern on a string from (x, y)."""
        L = 86 * scale
        a = math.radians(swing)
        lx, ly = x + math.sin(a) * L, y + math.cos(a) * L
        pygame.draw.line(s, (60, 44, 40), (x, y), (lx, ly), 2)
        g = self._title_skin()['lglow']
        s.blit(g, g.get_rect(center=(lx, ly + 30 * scale)))
        w, h = int(40 * scale), int(52 * scale)
        body = pygame.Rect(0, 0, w, h)
        body.midtop = (lx, ly + 6 * scale)
        pygame.draw.rect(s, (90, 54, 40), (body.x + 6 * scale, ly, w - 12 * scale, 8 * scale), border_radius=3)
        pygame.draw.rect(s, (236, 120, 70), body, border_radius=int(14 * scale))
        pygame.draw.rect(s, (255, 196, 110), body.inflate(-12 * scale, -10 * scale), border_radius=int(10 * scale))
        pygame.draw.rect(s, (255, 236, 170), body.inflate(-24 * scale, -22 * scale), border_radius=int(6 * scale))
        for i in (-1, 1):
            pygame.draw.line(s, (200, 96, 60), (body.centerx + i * w * 0.22, body.y + 3),
                             (body.centerx + i * w * 0.22, body.bottom - 3), 2)
        pygame.draw.rect(s, (110, 64, 46), body, 2, border_radius=int(14 * scale))
        pygame.draw.rect(s, (90, 54, 40), (body.x + 8 * scale, body.bottom - 2, w - 16 * scale, 7 * scale),
                         border_radius=3)
        pygame.draw.line(s, (200, 120, 70), (body.centerx, body.bottom + 5 * scale), (body.centerx, body.bottom + 16 * scale), 2)

    def open_slots(self):
        self.overlay = 'slots'
        self.slot_del = None
        self.audio.play('page', 0.5)

    def draw_title(self, s):
        ui = self.ui
        sk = self._title_skin()
        s.blit(sk['top'], (0, 0))
        s.blit(sk['bot'], (0, SH - 260))
        s.blit(sk['glow'], (SW // 2 - 410, 0))
        # fireflies drifting around the title
        for i in range(16):
            ph = i * 2.39
            fx = SW / 2 + math.sin(self.t * 0.21 + ph) * (300 + (i % 4) * 70)
            fy = 170 + math.sin(self.t * 0.37 + ph * 1.7) * 110 + math.cos(self.t * 0.13 + i) * 30
            tw = 0.5 + 0.5 * math.sin(self.t * (1.4 + (i % 3) * 0.5) + ph)
            if tw > 0.2:
                s.blit(sk['dot'], (fx - 12, fy - 12))
                pygame.draw.circle(s, (255, 248, 200), (int(fx), int(fy)), 2)
        self.draw_lantern(s, SW // 2 - 360, -10, math.sin(self.t * 1.1) * 6, 1.0)
        self.draw_lantern(s, SW // 2 + 360, -10, math.sin(self.t * 1.1 + 1.9) * 6, 1.0)
        bob = math.sin(self.t * 1.2) * 4
        ui.blit_text(s, 'Lantern Lake', (SW // 2, 142 + bob), 'title', (255, 232, 190), 'center', (120, 60, 40),
                     outline=(54, 30, 34))
        sub = ui.blit_text(s, 'a cozy little fishing game', (SW // 2, 226), 'h3', (244, 226, 204), 'center',
                           (40, 24, 30))
        for side in (-1, 1):
            x0 = sub.centerx + side * (sub.w // 2 + 18)
            pygame.draw.line(s, (244, 226, 204), (x0, 228), (x0 + side * 60, 228), 2)
            pygame.draw.circle(s, (255, 214, 140), (x0 + side * 68, 228), 4)
        # menu
        bw = 380
        bx = SW // 2 - bw // 2
        y = 290
        items = 5 if self.has_save else 4
        ui.panel(s, (bx - 30, y - 26, bw + 60, 52 + items * 70 + (10 if self.has_save else 0)), radius=24)
        if self.has_save:
            sub_t = 'Slot %d - Day %d - %s - %s coins' % (self.settings.get('slot', 1), self.day,
                                                        SEASONS[self.season_of(self.day)], '{:,}'.format(self.coins))
            if self.ui.fonts['small'].size(sub_t)[0] > bw - 30:
                sub_t = 'Slot %d - Day %d - %s' % (self.settings.get('slot', 1), self.day,
                                                   SEASONS[self.season_of(self.day)])
            ui.button(s, (bx, y, bw, 70), 'Continue', lambda: self.start_game(True), 'primary', font='h2',
                      sub=sub_t, nav=True)
            y += 84
            if self.confirm_new > 0:
                ui.button(s, (bx, y, bw, 56), 'Really start over? Click again', self.new_game,
                          'rose', nav=True)
            else:
                ui.button(s, (bx, y, bw, 56), 'New game', lambda: setattr(self, 'confirm_new', 3.0), font='h2',
                          nav=True)
        else:
            ui.button(s, (bx, y, bw, 64), 'Begin', self.new_game, 'primary', font='h2', nav=True)
            y += 8
        y += 70
        ui.button(s, (bx, y, bw, 56), 'Save slots', self.open_slots, font='h2', nav=True)
        y += 70
        ui.button(s, (bx, y, bw, 56), 'Play together', self.open_lobby, font='h2', nav=True)
        y += 70
        half = (bw - 12) // 2
        ui.button(s, (bx, y, half, 56), 'Options', lambda: self.open_options('title'), font='h2', nav=True)
        ui.button(s, (bx + bw - half, y, half, 56), 'Quit', lambda: setattr(self, 'running', False), font='h2',
                  nav=True)
        # footer
        ui.blit_text(s, 'v' + GAME_VERSION, (20, SH - 30), 'small', (220, 210, 214), 'midleft')
        parts = self.hint([('key', 'F11'), 'Fullscreen    ', ('key', 'Up'), ('key', 'Down'), 'Choose    ',
                           ('key', 'Enter'), 'Select'],
                          [('pad', 'DPAD'), 'Choose    ', ('pad', 'A'), 'Select    ', ('pad', 'B'), 'Back'])
        w = ui.rich(s, parts, (0, 0), measure=True)
        ui.rich(s, parts, (SW - 20 - w, SH - 30), (236, 228, 230))

    # ---------------- HUD
    def _dial(self, s, center, r):
        """Clock dial: a ring that fills through the day around a little sky with the weather in it."""
        env = self.env
        x, y = center
        frac = (self.minute % 1440) / 1440.0
        night = env.nf > 0.5
        sky = art.lerp_c((178, 214, 236), (52, 60, 104), min(1.0, env.nf * 1.2))
        pygame.draw.circle(s, (222, 206, 178), (x, y), r)
        pygame.draw.circle(s, (244, 234, 214), (x, y), r - 6)
        pts = [(x, y)]
        n = max(2, int(48 * frac) + 1)
        for i in range(n + 1):
            a = -math.pi / 2 + frac * 2 * math.pi * i / n
            pts.append((x + math.cos(a) * (r - 1), y + math.sin(a) * (r - 1)))
        if len(pts) >= 3:
            pygame.draw.polygon(s, (120, 132, 196) if night else U.GOLD, pts)
        pygame.draw.circle(s, sky, (x, y), r - 6)
        pygame.draw.circle(s, (150, 112, 84), (x, y), r, 2)
        a = -math.pi / 2 + frac * 2 * math.pi
        pygame.draw.circle(s, (255, 252, 240), (int(x + math.cos(a) * (r - 3)), int(y + math.sin(a) * (r - 3))), 4)
        U.weather_icon(s, (x, y), self.weather, night, int(r * 0.52), sky)

    # ---------------- HUD
    def help_on(self):
        """Key hints and tips: all through the first day (and the first few fish), then only on F1 / ?."""
        if not self.settings.get('hints', True):
            return False
        first = self.tut_day or 1
        return self.show_help or self.day <= first or self.total < 3

    def toggle_help(self):
        self.show_help = not self.show_help
        self.audio.play('ui', 0.5)
        self.toast('Hints on. F1 or ? hides them again.' if self.show_help else 'Hints tucked away. F1 or ? for help.',
                   (120, 140, 170))

    def hud_style(self):
        v = self.settings.get('hud', 'clean')
        return v if v in HUD_STYLES else 'clean'

    def hud_quiet(self):
        """Once the bobber has settled (and all through the fight), the HUD cards fade nearly away.
        Pointing at them brings them back."""
        showoff = self.overlay == 'catch' and self.card and self.card['t'] < 0
        if self.hud_style() == 'full' or self.place == 'town' or self.mode != 'play' or (
                self.overlay is not None and not showoff):
            return False
        f = self.fishing
        if showoff:
            return True
        st = f.state
        if st in ('fight', 'landing'):
            return True
        idle = (st == 'idle' and self.hud_style() in ('calm', 'clean') and self.total >= 3 and not self.help_on()
                and self.t - self._hud_wake > 5.0)
        if not idle and (st not in ('waiting', 'bite') or (st == 'waiting' and f.t < 1.6)):
            return False
        mx, my = self.ui.mouse
        if (8 <= mx < 16 + 372 + 24 and 6 <= my < getattr(self, '_hud_left', 300) + 16) or (
                mx > SW - 16 - 320 and my < 190):
            return False
        return True

    def hud_tucked(self):
        """Calm HUD: while a cast is out, the menu toolbar and the day's notes step aside."""
        if self.hud_style() == 'full' or self.place == 'town' or self.overlay is not None:
            return False
        st = self.fishing.state
        if st == 'idle':
            return False
        # pointing at the corner while you wait brings the toolbar back
        if st == 'waiting' and self.ui.mouse[0] > SW - 16 - (20 + max(2, self._dock_n) * 72) and self.ui.mouse[1] > SH - 130:
            return False
        return True

    def objectives(self):
        """What the HUD can track: an expedition with friends, the welcome quest, today's festival, the open
        request (at the sea, the harbour's jobs come first). A pinned goal (Q) always comes first."""
        out = ['expedition'] if coop.exp_live(self) else []
        if goalmod.active(self):
            out.append('welcome')
        fest = self.festival_today() and not self.festival.get('done')
        req = self.request and not self.request.get('done')
        if fest and self.minute >= self.festival['start']:
            out.append('festival')
        if coast.at_coast(self):
            sea = [gid for gid in goalmod.COAST_GOALS if goalmod.info(self, gid)]
            if req and goalmod.catchable_here(self, FISH_BY_ID[self.request['fish']]):
                out.append('request')
            out += sea
        if req and 'request' not in out:
            out.append('request')
        if fest and 'festival' not in out:
            out.append('festival')
        if clubmod.today(self) and not coast.at_coast(self):
            if clubmod.live(self):
                out.insert(1 if out and out[0] == 'expedition' else 0, 'club')
            else:
                out.append('club')
        pin = self.goals.get('pinned')
        if pin:
            if pin in out:
                out.remove(pin)
                out.insert(0, pin)
            elif goalmod.info(self, pin):
                out.insert(0, pin)
        return out

    def tracked_objective(self):
        objs = self.objectives()
        if not objs:
            return None, objs
        return (self.tracked if self.tracked in objs else objs[0]), objs

    def cycle_objective(self):
        cur, objs = self.tracked_objective()
        if len(objs) > 1:
            self.tracked = objs[(objs.index(cur) + 1) % len(objs)]
            self.audio.play('ui', 0.5)

    def _hud_switch(self, s, r, objs, cur):
        """A 'next' arrow with page dots on the objective card: click it to track the other one."""
        ui = self.ui
        chip = pygame.Rect(0, 0, 30, 46)
        chip.midright = (r.right - 10, r.centery)
        hov = chip.collidepoint(ui.mouse)
        pygame.draw.rect(s, (255, 246, 226) if hov else (244, 232, 210), chip, border_radius=10)
        cx, cy = chip.centerx, chip.y + 17
        col = U.INK if hov else U.BROWN
        pygame.draw.polygon(s, col, [(cx - 4, cy - 7), (cx + 5, cy), (cx - 4, cy + 7)])
        k = objs.index(cur)
        x0 = cx - (len(objs) - 1) * 4
        for i in range(len(objs)):
            pygame.draw.circle(s, col if i == k else (206, 188, 160), (x0 + i * 8, chip.bottom - 9), 3)
        ui.hotspot(chip.inflate(8, 8), self.cycle_objective)
        return chip.w + 8

    GOAL_H = 84                  # the tracker card: what to do, where, and when

    def goal_h(self):
        return 46 if self._goal_slim else self.GOAL_H

    def _hud_lines(self, s, r, extra, top, where, when, prog=None):
        """The words on a tracker card, with a progress pill beside the first line."""
        ui = self.ui
        right = r.right - 14 - extra
        if self._goal_slim:          # one line while a cast is out: what, and how far along
            tw1 = right - r.x - 58
            if prog:
                a, b = prog
                pill = U.snap_rect(pygame.Rect(right - 52, r.centery - 12, 52, 24))
                s.blit(ui._button_skin(pill.w, pill.h, U.SAGE if a >= b else (234, 220, 194),
                                       U.SAGE_D if a >= b else U.BROWN, 1), pill)
                ui.blit_text(s, '%d/%d' % (a, b), (pill.centerx, pill.centery - 1), 'small',
                             (255, 255, 250) if a >= b else U.INK, 'center')
                tw1 = pill.x - 6 - r.x - 58
            ui.blit_text(s, top, (r.x + 58, r.centery), 'smallb', U.INK, 'midleft', maxw=tw1)
            return
        tw = right - r.x - 58
        if prog:
            a, b = prog
            done = a >= b
            pill = U.snap_rect(pygame.Rect(right - 60, r.y + 8, 60, 26))
            s.blit(ui._button_skin(pill.w, pill.h, U.SAGE if done else (234, 220, 194),
                                   U.SAGE_D if done else U.BROWN, 1), pill)
            ui.blit_text(s, '%d/%d' % (a, b), (pill.centerx, pill.centery - 1), 'smallb',
                         (255, 255, 250) if done else U.INK, 'center')
            tw1 = pill.x - 6 - r.x - 58
        else:
            tw1 = tw
        ui.blit_text(s, top, (r.x + 58, r.y + 9), 'smallb', U.INK, maxw=tw1)
        ui.blit_text(s, where, (r.x + 58, r.y + 35), 'small', U.SOFT, maxw=tw)
        ui.blit_text(s, when, (r.x + 58, r.y + 57), 'small', U.SOFT, maxw=tw)

    def _hud_request(self, s, y, CW, objs):
        ui = self.ui
        req = self.request
        f = FISH_BY_ID[req['fish']]
        bday = req.get('birthday')
        r2 = ui.panel(s, (16, y, CW, self.goal_h()), fill=(252, 236, 240) if bday else U.PAPER, radius=16)
        cy = r2.centery if self._goal_slim else r2.y + 34
        if bday:
            U.cake(s, (r2.x + 30, cy), 0.8 if self._goal_slim else 1.1)
        else:
            U.envelope(s, (r2.x + 16, cy - 11 if self._goal_slim else r2.y + 24, 30, 22))
        ui.hotspot(r2, self.read_request)
        extra = self._hud_switch(s, r2, objs, 'request') if len(objs) > 1 and not self._goal_slim else 0
        who = req['who'].split(' (')[0]
        where, when = goalmod.fish_where(self, f)
        self._hud_lines(s, r2, extra, ("%s's birthday: %s" if bday else '%s needs: %s') % (who, f['name']),
                        where, when, (req['have'], req['need']))
        if self.goals.get('pinned') == 'request':
            goalmod.draw_pin(s, (r2.x + 10, r2.y + 6))

    def _hud_goal(self, s, y, CW, objs, gid):
        """Any other goal: its next step, then where and when, and how far along it is."""
        ui = self.ui
        gl = goalmod.info(self, gid)
        if not gl:
            return
        if gid == 'welcome':
            r = ui.panel(s, (16, y, CW, self.goal_h()), fill=(240, 246, 232), border=(120, 160, 110), radius=16)
        else:
            r = ui.panel(s, (16, y, CW, self.goal_h()), radius=16)
        if self._goal_slim:
            almanac.event_icon(s, gl['icon'], (r.x + 30, r.centery), 0.8)
        else:
            almanac.event_icon(s, gl['icon'], (r.x + 30, r.y + 34), 1.0)
        ui.hotspot(r, gl['act'] or (lambda: self.toggle('goals')))
        extra = self._hud_switch(s, r, objs, gid) if len(objs) > 1 and not self._goal_slim else 0
        self._hud_lines(s, r, extra, gl['next'], gl['where'] or gl['title'], gl['when'], gl.get('pill'))
        if self.goals.get('pinned') == gid:
            goalmod.draw_pin(s, (r.x + 10, r.y + 6))

    def _hud_slim(self, s, y, CW, fill, border, icon, line, tip, act=None):
        """A one-line tracker card for the clean HUD; the details hang under it when you point at it."""
        ui = self.ui
        r = ui.panel(s, (16, y, CW, 46), fill=fill, border=border, radius=16)
        icon(r)
        ui.blit_text(s, line, (r.x + 52, r.centery), 'smallb', U.INK, 'midleft', maxw=CW - 66)
        if act:
            ui.hotspot(r, act)
        if r.collidepoint(ui.mouse) and tip:
            self._hud_tip = (tip, (r.centerx, r.bottom + 6))
        return r

    def _hud_festival(self, s, y, CW, objs):
        ui = self.ui
        fest = self.festival
        if self._goal_slim:
            if self.minute < fest['start']:
                line = '%s at %s' % (fest['name'], fmt_clock(fest['start']))
                tip = FESTIVALS[fest['season']]['desc']
            else:
                lead_nm, lead_sz = max(fest['rivals'] + self.friend_scores(), key=lambda e: e[1])
                mine = self.fest_score(fest['rule'], fest['best'])
                short = fest['name'].split()[-1]
                if fest['best'] > lead_sz:
                    line, tip = '%s %s - leading!' % (short, mine), 'In the lead! Ends %s' % fmt_clock(fest['end'])
                else:
                    top = self.fest_score(fest['rule'], lead_sz)
                    line = '%s %s / %s' % (short, mine.split()[0], top)
                    tip = '%s: %s has %s. Ends %s' % (fest['name'], lead_nm, self.fest_score(fest['rule'], lead_sz),
                                                     fmt_clock(fest['end']))
            self._hud_slim(s, y, CW, (252, 236, 240), (176, 100, 130),
                           lambda r: U.trophy(s, (r.x + 26, r.centery), 0.7), line, tip,
                           self.cycle_objective if len(objs) > 1 else None)
            return
        r6 = ui.panel(s, (16, y, CW, 64), fill=(252, 236, 240), border=(176, 100, 130), radius=16)
        U.trophy(s, (r6.x + 30, r6.y + 32), 0.9)
        extra = self._hud_switch(s, r6, objs, 'festival') if len(objs) > 1 else 0
        tw = CW - 70 - extra
        if self.minute < fest['start']:
            ui.blit_text(s, '%s today!' % fest['name'], (r6.x + 58, r6.y + 10), 'smallb', U.INK, maxw=tw)
            ui.blit_text(s, 'Starts at %s' % fmt_clock(fest['start']), (r6.x + 58, r6.y + 34), 'small', U.SOFT,
                         maxw=tw)
        else:
            lead_nm, lead_sz = max(fest['rivals'] + self.friend_scores(), key=lambda e: e[1])
            ui.blit_text(s, '%s: %s' % (fest['name'], self.fest_score(fest['rule'], fest['best'])),
                         (r6.x + 58, r6.y + 10), 'smallb', U.INK, maxw=tw)
            if fest['best'] > lead_sz:
                ui.blit_text(s, 'In the lead! Ends %s' % fmt_clock(fest['end']), (r6.x + 58, r6.y + 34),
                             'small', (80, 130, 70), maxw=tw)
            else:
                ui.blit_text(s, 'To beat: %s, %s' % (lead_nm, self.fest_score(fest['rule'], lead_sz)),
                             (r6.x + 58, r6.y + 34), 'small', U.SOFT, maxw=tw)

    def _hud_club(self, s, y, CW, objs):
        """The Angling Club's card: your score against the leader (the board when you point at it)."""
        ui = self.ui
        line, tip = clubmod.hud(self)
        icon = lambda r: clubmod.ribbon(s, (r.x + 26, r.centery - 4), clubmod.RIBBON_COL['blue'], 0.9)
        if self._goal_slim:
            self._hud_slim(s, y, CW, (234, 240, 252), (90, 110, 170), icon, line, tip,
                           self.cycle_objective if len(objs) > 1 else None)
            return
        r = ui.panel(s, (16, y, CW, 64), fill=(234, 240, 252), border=(90, 110, 170), radius=16)
        clubmod.ribbon(s, (r.x + 30, r.y + 26), clubmod.RIBBON_COL['blue'], 1.0)
        extra = self._hud_switch(s, r, objs, 'club') if len(objs) > 1 else 0
        ui.blit_text(s, line, (r.x + 58, r.y + 10), 'smallb', U.INK, maxw=CW - 70 - extra)
        ui.blit_text(s, tip, (r.x + 58, r.y + 34), 'small', U.SOFT, maxw=CW - 70 - extra)

    def _hud_expedition(self, s, y, CW, objs):
        ui = self.ui
        if self._goal_slim:
            title, line = coop.exp_hud(self)

            def flag(r):
                cx, cy = r.x + 26, r.centery
                pygame.draw.line(s, U.BROWN, (cx - 6, cy - 11), (cx - 6, cy + 11), 3)
                pygame.draw.polygon(s, (60, 110, 150), [(cx - 4, cy - 11), (cx + 12, cy - 5), (cx - 4, cy + 1)])
            self._hud_slim(s, y, CW, (232, 242, 246), (90, 130, 160), flag, title, line,
                           lambda: (setattr(self, 'coop_tab', 'exp'), self.toggle('coop')))
            return
        r = ui.panel(s, (16, y, CW, 64), fill=(232, 242, 246), border=(90, 130, 160), radius=16)
        cx, cy = r.x + 30, r.y + 32                  # a little pennant on a pole
        pygame.draw.line(s, U.BROWN, (cx - 8, cy - 14), (cx - 8, cy + 14), 3)
        pygame.draw.polygon(s, (60, 110, 150), [(cx - 6, cy - 14), (cx + 14, cy - 7), (cx - 6, cy)])
        pygame.draw.circle(s, (230, 190, 90), (cx, cy - 7), 3)
        ui.hotspot(r, lambda: (setattr(self, 'coop_tab', 'exp'), self.toggle('coop')))
        extra = self._hud_switch(s, r, objs, 'expedition') if len(objs) > 1 else 0
        title, line = coop.exp_hud(self)
        ui.blit_text(s, title, (r.x + 58, r.y + 10), 'smallb', U.INK, maxw=CW - 70 - extra)
        ui.blit_text(s, line, (r.x + 58, r.y + 34), 'small', U.SOFT, maxw=CW - 70 - extra)

    def _note_act(self, kind, text):
        """What clicking a day note does (or None)."""
        if kind == 'lantern':
            return self.open_lanterns
        if kind == 'garden':
            return lambda: self.open_cabin_tab('garden')
        if kind == 'stall':
            return (lambda: stallmod.open_(self)) if self.place == 'town' else (lambda: self.go_place('town'))
        if kind == 'reeds':
            return lambda: shoremod.open_panel(self)
        if kind == 'truck':
            return lambda: truckmod.open_(self, 'orders' if self.truck['order'] else None)
        if kind == 'mail' and self.place == 'lake' and self.spot == 'dock':
            return self.open_mailbox
        if kind == 'festival' and text.startswith('Legend'):
            return lambda: (self.set_lan_tab('legends'), self.open_lanterns())
        return None

    def _tipbox(self, s, text, pos):
        """A small label hanging under something you point at."""
        ui = self.ui
        w = ui.fonts['small'].size(text)[0] + 28
        x = int(clamp(pos[0] - w // 2, 8, SW - 8 - w))
        r = ui.panel(s, (x, pos[1], w, 36), fill=(255, 250, 238), radius=14, shadow=False, width=2)
        ui.blit_text(s, text, (r.centerx, r.centery), 'small', U.INK, 'center')

    def day_lines(self):
        """The day's notes under the objective: where you are, snacks, visitors, sky events..."""
        lines = []
        run = self.run_fish(self.day)
        if self.place == 'town':
            lines.append(('town', 'In Fernwick Village'))
        elif self.spot != 'dock':
            lines.append(('spot', 'Fishing at %s' % SPOT_BY_ID[self.spot]['name']))
            lines += coast.day_lines(self)
        for sn in townmod.SNACKS + townmod.NIGHT_SNACKS:
            if self.buff(sn['id']):
                lines.append(('snack', {'bun': 'Honey Bun: a little luck', 'tea': 'Lakeside Tea: quick bites',
                                        'pie': 'Blueberry Pie: bigger fish',
                                        'cookie': 'Star Cookie: rare fish',
                                        'cocoa': 'Hot Cocoa: night bites come sooner',
                                        'mooncake': 'Moon Cake: more night fish'}[sn['id']]))
        meal = self.meal_today()
        if meal:
            r_ = kitchenmod.RECIPE_BY_ID[meal]
            lines.append(('snack', '%s: %s' % (r_['name'], r_['effect'].lower())))
        nn = getattr(self, '_new_now', None)
        if nn and self.place == 'lake':
            fish, why = nn
            lines.append(('run', '%s new fish could bite now%s' % (
                'A' if len(fish) == 1 else len(fish), (' (%s)' % ', '.join(why)) if why else '')))
        if self.mail():
            n_ = len(self.mail())
            lines.append(('mail', 'A letter in the mailbox' if n_ == 1 else '%d letters in the mailbox' % n_))
        if self.wagon_here():
            lines.append(('wagon', "Wren's Wagon until %s" % fmt_clock(1200)))
        sl = story.hud_line(self)
        if sl:
            lines.append(('lantern', sl))
        ll = legends.hud_line(self)
        if ll:
            lines.append(('festival', ll))
        cl = clubmod.note(self)
        if cl and self.tracked_objective()[0] != 'club':
            lines.append(('club', cl))
        sl = stallmod.day_note(self)
        if sl:
            lines.append(('stall', sl))
        tl = truckmod.day_note(self)
        if tl:
            lines.append(('truck', tl))
        bl = biscuit.hud_line(self)
        if bl:
            lines.append(('birthday', bl))
        gl = gardenmod.hud_line(self)
        if gl:
            lines.append(('garden', gl))
        dl = discover.hud_line(self)
        if dl:
            lines.append(('paw', dl))
        sl2 = shoremod.hud_line(self)
        if sl2:
            lines.append(('reeds', sl2))
        wl = wildlife.hud_line(self)
        if wl:
            lines.append(('critter', wl))
        rl = coop.hud_line(self)
        if rl:
            lines.append(('festival', rl))
        if self.place == 'lake' and self.has('pot') and seasons.pot_ready(self):
            lines.append(('spot', 'Crab pot ready: haul it up (E)'))
        if seasons.sky_live(self, 'storm'):
            lines.append(('meteor', 'Thunderstorm: Thunderfin are rising'))
        elif seasons.sky_live(self, 'aurora'):
            lines.append(('meteor', 'Northern lights tonight'))
        if run:
            lines.append(('run', '%s run today' % FISH_BY_ID[run]['name']))
        if almanac.dow(self.day) == METEOR_DAY and self.minute >= 1080:
            lines.append(('meteor', 'Meteor shower now!' if self.meteor_live()
                          else 'Meteors from %s' % fmt_clock(1260)))
        elif self.meteor_live():
            lines.append(('meteor', 'Meteor shower now!'))
        if coast.at_coast(self):
            lines = [ln for ln in lines if ln[0] not in ('garden', 'wagon', 'reeds', 'birthday')
                     and not ln[1].startswith('Crab pot')]
        cur = self.tracked_objective()[0]
        if cur in ('lantern', 'garden', 'shore'):
            kind = {'lantern': 'lantern', 'garden': 'garden', 'shore': 'reeds'}[cur]
            lines = [ln for ln in lines if ln[0] != kind]
        elif cur == 'legend':
            lines = [ln for ln in lines if not ln[1].startswith('Legend')]
        return lines

    def draw_hud(self, s):
        ui = self.ui
        env = self.env
        if self.net.online:
            self.draw_name_tags(s)
        style = self.hud_style()
        compact = style == 'compact'
        # the calm HUD eases the toolbar away while a cast is out
        now = self.t
        dt = max(0.0, min(0.1, now - self._hud_t))
        self._hud_t = now
        target = 1.0 if self.hud_tucked() else 0.0
        self.hud_tuck += (target - self.hud_tuck) * min(1.0, dt * 9)
        if abs(target - self.hud_tuck) < 0.01:
            self.hud_tuck = target
        tuck = 1 - (1 - self.hud_tuck) ** 3
        sig = (self.coins, self.place, self.overlay, self.fishing.state if self.fishing.state == 'idle' else 'out',
               self.tracked_objective()[0], self.bait, len(self.toasts) > 0)
        if sig != self._wake_sig:
            self._wake_sig = sig
            self._hud_wake = now
        clean = style == 'clean'
        self._goal_slim = style != 'full' and (self.hud_tuck > 0.5 or clean)
        calm_card = style in ('calm', 'clean')
        tip = None                 # (text, (x, y)): a little label under whatever the mouse is on
        self._hud_tip = None       # ...or one a card set while it drew
        want = 1.0 if self.hud_quiet() else 0.0
        self.hud_calm += (want - self.hud_calm) * min(1.0, dt * (1.3 if want > self.hud_calm else 7))
        if abs(want - self.hud_calm) < 0.01:
            self.hud_calm = want
        self.audio.calm = self.hud_calm
        real = s
        if self.hud_calm > 0.01:
            # the cards are drawn on a layer of their own so they can fade as one
            lay = self._hud_layer
            if lay is None or lay.get_size() != s.get_size():
                lay = self._hud_layer = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            lay.fill((0, 0, 0, 0))
            s = lay
        CW = 320 if clean else 372    # width of the left-hand cards
        tw = CW - 70               # room for text beside the card icons
        # clock
        if compact:
            r = ui.panel(s, (16, 14, 262, 48), radius=22)
            self._dial(s, (r.x + 27, r.centery), 17)
            ui.blit_text(s, fmt_clock(self.minute), (r.x + 54, r.centery), 'bodyb', U.INK, 'midleft')
            ui.blit_text(s, almanac.weekday(self.day), (r.right - 16, r.centery), 'small', U.SOFT, 'midright',
                         maxw=100)
            y = 70
        elif clean:
            # one slim line: the time, the day, your purse (the date comes up when you point at it)
            r = ui.panel(s, (16, 14, 320, 52), radius=24)
            self._dial(s, (r.x + 28, r.centery), 18)
            clk = fmt_clock(self.minute)
            ui.blit_text(s, clk, (r.x + 56, r.centery), 'bodyb', U.INK, 'midleft')
            cs = '{:,}'.format(self.coins)
            cw_ = ui.fonts['bodyb'].size(cs)[0]
            ui.blit_text(s, cs, (r.right - 18, r.centery), 'bodyb', U.INK, 'midright')
            U.coin(s, (r.right - 32 - cw_, r.centery), 10)
            dx = r.x + 66 + ui.fonts['bodyb'].size(clk)[0]
            ui.blit_text(s, almanac.weekday(self.day), (dx, r.centery), 'small', U.SOFT, 'midleft',
                         maxw=max(10, r.right - 50 - cw_ - dx))
            if env.full_moon and env.nf > 0.4:
                U.moon_phase(s, (r.x + 28, r.bottom + 2), 0, 6)
            if r.collidepoint(ui.mouse):
                tip = ('%s, %s %d   (K: calendar)' % (almanac.weekday(self.day), SEASONS[env.season],
                                                       almanac.dow(self.day)), (r.centerx, r.bottom + 6))
            y = 74
        elif calm_card:
            # one card for the time, the day and your purse
            r = ui.panel(s, (16, 14, CW, 72), radius=20)
            self._dial(s, (r.x + 38, r.centery), 25)
            ui.blit_text(s, fmt_clock(self.minute), (r.x + 76, r.y + 6), 'big', U.INK)
            sub = '%s, %s %d' % (almanac.weekday(self.day), SEASONS[env.season], almanac.dow(self.day))
            ui.blit_text(s, sub, (r.x + 78, r.y + 46), 'small', U.SOFT, maxw=CW - 196)
            cw_ = ui.fonts['bodyb'].size('{:,}'.format(self.coins))[0]
            ui.blit_text(s, '{:,}'.format(self.coins), (r.right - 16, r.y + 24), 'bodyb', U.INK, 'midright')
            U.coin(s, (r.right - 30 - cw_, r.y + 24), 11)
            if env.full_moon and env.nf > 0.4:
                U.moon_phase(s, (r.right - 26, r.y + 52), 0, 8)
            y = 94
        else:
            r = ui.panel(s, (16, 14, CW, 88), radius=20)
            self._dial(s, (r.x + 46, r.y + 44), 30)
            ui.blit_text(s, fmt_clock(self.minute), (r.x + 92, r.y + 12), 'big', U.INK)
            sub = '%s, %s %d' % (almanac.weekday(self.day), SEASONS[env.season], almanac.dow(self.day))
            ui.blit_text(s, sub, (r.x + 94, r.y + 58), 'small', U.SOFT, maxw=CW - 150)
            ui.keycap(s, 'K', (r.right - 14, r.y + 14), 'topright')
            if env.full_moon and env.nf > 0.4:
                U.moon_phase(s, (r.right - 60, r.y + 26), 0, 10)
            y = 110
        ui.hotspot(r, lambda: self.toggle('calendar'))
        # one tracked objective (a request, a birthday or today's festival); the chip switches between them
        cur, objs = self.tracked_objective()
        if cur == 'request':
            self._hud_request(s, y, CW, objs)
            y += self.goal_h() + 8
        elif cur == 'festival':
            self._hud_festival(s, y, CW, objs)
            y += 54 if self._goal_slim else 72
        elif cur == 'expedition':
            self._hud_expedition(s, y, CW, objs)
            y += 54 if self._goal_slim else 72
        elif cur == 'club':
            self._hud_club(s, y, CW, objs)
            y += 54 if self._goal_slim else 72
        elif cur:
            self._hud_goal(s, y, CW, objs, cur)
            y += self.goal_h() + 8
        # today's other notes: they step aside while a cast is out (and always while reeling)
        quiet = (self.hud_tuck > 0.5) if style != 'full' else self.fishing.state in ('fight', 'landing')
        if not quiet and clean:
            # the day's notes as a row of icons: point at one to read it, click to go there
            lines = [ln for ln in self.day_lines() if ln[0] != 'town'][:9]
            if lines:
                r7 = ui.panel(s, (16, y, 18 + 38 * len(lines), 46), radius=22)
                for i, (kind, text) in enumerate(lines):
                    c = (r7.x + 28 + i * 38, r7.centery)
                    almanac.event_icon(s, kind, c, 0.8)
                    hit = pygame.Rect(c[0] - 19, r7.y, 38, r7.h)
                    act = self._note_act(kind, text)
                    if act:
                        ui.hotspot(hit, act)
                    if hit.collidepoint(ui.mouse):
                        tip = (text, (hit.centerx, r7.bottom + 6))
                        pygame.draw.line(s, U.BROWN, (hit.x + 8, r7.bottom - 7), (hit.right - 8, r7.bottom - 7), 2)
                y = r7.bottom + 8
        elif not quiet:
            lines = self.day_lines()
            if lines:
                r7 = ui.panel(s, (16, y, CW, 20 + 30 * len(lines)), radius=16)
                for i, (kind, text) in enumerate(lines):
                    almanac.event_icon(s, kind, (r7.x + 30, r7.y + 25 + i * 30), 0.8)
                    if kind == 'lantern':
                        ui.hotspot(pygame.Rect(r7.x, r7.y + 10 + i * 30, r7.w, 30), self.open_lanterns)
                    elif kind == 'garden':
                        ui.hotspot(pygame.Rect(r7.x, r7.y + 10 + i * 30, r7.w, 30),
                                   lambda: self.open_cabin_tab('garden'))
                    elif kind == 'reeds':
                        ui.hotspot(pygame.Rect(r7.x, r7.y + 10 + i * 30, r7.w, 30),
                                   lambda: shoremod.open_panel(self))
                    elif kind == 'festival' and text.startswith('Legend'):
                        ui.hotspot(pygame.Rect(r7.x, r7.y + 10 + i * 30, r7.w, 30),
                                   lambda: (self.set_lan_tab('legends'), self.open_lanterns()))
                    ui.blit_text(s, text, (r7.x + 58, r7.y + 25 + i * 30), 'small', U.INK, 'midleft', maxw=tw)
                y = r7.bottom + 8
        if self.fishing.state not in ('fight', 'landing'):
            y = self.radio.draw_widget(s, y, CW, slim=clean)
        tip = tip or self._hud_tip
        self._hud_left = y           # the chat sits under the left-hand cards
        # coins, bait and luck down the right-hand side
        b = BAIT_BY_ID[self.bait]
        label = '%s x%d' % (b['name'], self.worms() if self.bait == 'worm' else self.baits.get(self.bait, 0))
        if clean:
            # just the bait and how much is left (its name when you point at it), and any luck
            cnt = 'x%d' % (self.worms() if self.bait == 'worm' else self.baits.get(self.bait, 0))
            nl = min(3, int(math.ceil(self.luck))) if self.luck > 0.05 else 0
            bw = ui.fonts['bodyb'].size(cnt)[0] + 70 + nl * 20
            r4 = ui.panel(s, (SW - 16 - bw, 14, bw, 52), radius=24)
            s.blit(art.item_icon(self.bait, 2), (r4.x + 12, r4.centery - 16))
            ui.blit_text(s, cnt, (r4.x + 52, r4.centery), 'bodyb', U.INK, 'midleft')
            for i in range(nl):
                U.clover(s, (r4.right - 22 - i * 20, r4.centery - 2), 7)
            if r4.collidepoint(ui.mouse):
                tip = ('%s%s   (Tab: switch bait)' % (label, ', and luck' if nl else ''), (r4.centerx, r4.bottom + 6))
            ry = 74
        elif calm_card:
            bw = min(300, ui.fonts['small'].size(label)[0] + 64)
            r4 = ui.panel(s, (SW - 16 - bw, 14, bw, 44), radius=21)
            s.blit(art.item_icon(self.bait, 2), (r4.x + 8, r4.centery - 16))
            ui.blit_text(s, label, (r4.x + 46, r4.centery), 'small', U.INK, 'midleft', maxw=r4.w - 56)
            ry = 66
        elif compact:
            r3 = ui.panel(s, (SW - 16 - 164, 14, 164, 48), radius=22)
            U.coin(s, (r3.x + 26, r3.centery), 11)
            ui.blit_text(s, '{:,}'.format(self.coins), (r3.x + 46, r3.centery), 'bodyb', U.INK, 'midleft',
                         maxw=r3.w - 56)
            r4 = ui.panel(s, (SW - 16 - 236, 70, 236, 42), radius=20)
            s.blit(art.item_icon(self.bait, 2), (r4.x + 10, r4.centery - 16))
            ui.blit_text(s, label, (r4.x + 48, r4.centery), 'small', U.INK, 'midleft', maxw=r4.w - 60)
            ry = 120
        else:
            r3 = ui.panel(s, (SW - 16 - 188, 14, 188, 56), radius=26)
            U.coin(s, (r3.x + 32, r3.centery), 14)
            ui.blit_text(s, '{:,}'.format(self.coins), (r3.x + 56, r3.centery + 2), 'big', U.INK, 'midleft',
                         maxw=r3.w - 66)
            r4 = ui.panel(s, (SW - 16 - 300, 78, 300, 48), radius=22)
            s.blit(art.item_icon(self.bait, 2), (r4.x + 12, r4.y + 8))
            ui.blit_text(s, label, (r4.x + 52, r4.centery), 'smallb', U.INK, 'midleft', maxw=r4.w - 120)
            ui.keycap(s, 'Tab', (r4.right - 12, r4.centery), 'midright')
            ry = 134
        ui.hotspot(r4, self.cycle_bait)
        if self.luck > 0.05 and not clean:
            r5 = ui.panel(s, (SW - 16 - 150, ry, 150, 40), radius=19)
            n = min(3, int(math.ceil(self.luck)))
            for i in range(n):
                U.clover(s, (r5.x + 24 + i * 22, r5.centery - 2), 8)
            ui.blit_text(s, 'Luck', (r5.right - 14, r5.centery), 'smallb', U.SOFT, 'midright')
            ry += 48
        if s is not real:
            s.set_alpha(int(255 * (1 - 0.8 * self.hud_calm)))
            real.blit(s, (0, 0))
            s = real
        if tip:
            self._tipbox(s, *tip)
        # toolbar of menu buttons, bottom right: item-slot style tiles
        if self.place == 'town':
            slots = [('Journal', 'J', lambda: self.toggle('journal')),
                     ('Shop', 'S', lambda: self.toggle('shop')),
                     ('Calendar', 'K', lambda: self.toggle('calendar')),
                     ('Lake', 'T', lambda: self.go_place('lake')),
                     ('Rest', 'Z', self.try_rest)]
        else:
            slots = [('Journal', 'J', lambda: self.toggle('journal')),
                     ('Shop', 'S', lambda: self.toggle('shop')),
                     ('Cabin', 'C', lambda: self.toggle('cabin')),
                     ('Calendar', 'K', lambda: self.toggle('calendar')),
                     ('Harbour' if coast.at_coast(self) else 'Town', 'T', lambda: self.go_place('town')),
                     ('Rest', 'Z', self.try_rest)]
            if self.has_boat():
                slots.insert(5, ('Boat', 'B', self.open_map))
            if self.truck['told'] and not self.net.online:
                slots.insert(len(slots) - 1, ('Truck', 'V', lambda: truckmod.open_(self)))
        n = len(slots)
        fold = False
        if calm_card:
            full = pygame.Rect(SW - 16 - (20 + n * 72), SH - 16 - 92, 20 + n * 72, 92)
            near_dock = full.inflate(24, 40).collidepoint(ui.mouse) if self._dock_n > 1 else (
                pygame.Rect(SW - 16 - 92, SH - 16 - 92, 92, 92).collidepoint(ui.mouse))
            if self.overlay is not None or self.fishing.state != 'idle':
                self.menu_open = False       # a click on the tile keeps it open until you pick or cast
            fold = not (self.menu_open or near_dock)
        self._dock_n = 1 if fold else n
        drop = int(tuck * 124)
        if fold and drop < 120:
            rr = pygame.Rect(SW - 16 - 82, SH - 16 - 82 + drop, 82, 82)
            hover = rr.collidepoint(ui.mouse) and not drop
            dock = ui.panel(s, rr, radius=24)
            slot = pygame.Rect(dock.x + 8, dock.y + 8 - (2 if hover else 0), 66, 66)
            s.blit(ui._frame(slot.w, slot.h, (255, 250, 238) if hover else (236, 222, 196),
                             (196, 160, 120) if hover else (170, 134, 100), 2), slot)
            cx, cy = slot.centerx, slot.y + 26
            for i in (-8, 0, 8):
                pygame.draw.line(s, U.INK, (cx - 12, cy + i), (cx + 12, cy + i), 3)
            ui.blit_text(s, 'Menu', (slot.centerx, slot.bottom - 14), 'tiny', U.INK, 'center')
            if not drop:
                ui.hotspot(rr, self.toggle_menu)
        elif drop < 120:
            dock = ui.panel(s, (SW - 16 - (20 + n * 72), SH - 16 - 92 + drop, 20 + n * 72, 92), radius=24)
            tip = None
            for i, (label, key, act) in enumerate(slots):
                rr = pygame.Rect(dock.x + 10 + i * 72, dock.y + 10, 68, 72)
                hover = rr.collidepoint(ui.mouse) and not drop
                lift = -2 if hover else 0
                slot = rr.move(0, lift)
                s.blit(ui._frame(slot.w, slot.h, (255, 250, 238) if hover else (236, 222, 196),
                                 (196, 160, 120) if hover else (170, 134, 100), 2), slot)
                c = (slot.centerx, slot.y + 28)
                if label == 'Journal':
                    U.book(s, c)
                elif label == 'Shop':
                    U.bag(s, (c[0], c[1] + 2))
                elif label == 'Cabin':
                    U.house(s, (c[0], c[1] + 1))
                elif label == 'Calendar':
                    U.calendar_icon(s, c)
                elif label == 'Boat':
                    U.rowboat(s, (c[0], c[1] + 2), 1.0)
                elif label == 'Truck':
                    spr = truckmod.truck_sprite(truckmod.paint_col(self) if self.truck['fixed'] else (150, 130, 120))
                    s.blit(spr, spr.get_rect(center=(c[0], c[1] + 2)))
                elif label in ('Town', 'Lake', 'Harbour'):
                    townmod.signpost_icon(s, c, label == 'Lake')
                else:
                    U.moon_icon(s, c, U.CREAM)
                ui.blit_text(s, label, (slot.centerx, slot.bottom - 16), 'tiny', U.INK, 'center', maxw=slot.w - 6)
                if not drop:
                    ui.hotspot(rr, act)
                if hover:
                    tip = (slot, label, key)
            if tip:
                slot, label, key = tip
                w = ui.fonts['smallb'].size(label)[0] + 62
                tr = pygame.Rect(0, 0, w, 40)
                tr.midbottom = (slot.centerx, dock.y - 6)
                tr.right = min(tr.right, SW - 12)
                tr = ui.panel(s, tr, radius=12)
                ui.blit_text(s, label, (tr.x + 12, tr.centery), 'smallb', U.INK, 'midleft')
                ui.keycap(s, key, (tr.right - 10, tr.centery), 'midright')
        # fishing feedback
        self.draw_fishing_ui(s)
        if self.net.online:
            self.draw_friends(s, ry)
        self.draw_chat(s)

    def draw_help_chip(self, s):
        """A small '?' in the corner once the hints have gone: click it (or F1) for them back."""
        ui = self.ui
        r = pygame.Rect(16, SH - 16 - 40, 40, 40)
        hov = r.collidepoint(ui.mouse)
        r = ui.glass(s, r, 170 if hov else 90, 20)
        ui.blit_text(s, '?', r.center, 'bodyb', (255, 250, 238), 'center')
        ui.hotspot(r, self.toggle_help)

    def toggle_menu(self):
        self.menu_open = not self.menu_open
        self.audio.play('ui', 0.5)

    def draw_fishing_ui(self, s):
        if self.place == 'town':
            self.draw_town_ui(s)
            return
        ui = self.ui
        f = self.fishing
        st = f.state
        hint = {
            'idle': [('key', 'Hold Click'), 'or', ('key', 'Space'), 'to wind up a cast.    Bubbles on the water mean '
                                                                    'hungry fish'],
            'charging': self.hint(['Aim with the mouse or', ('key', 'A'), ('key', 'D'), 'then let go to cast!'],
                                  ['Aim with', ('pad', 'STICK'), 'then let go of', ('pad', 'A'), 'to cast!']),
            'waiting': self.hint([('key', 'Tap'), 'to twitch the bobber (try it on a nibble!)  ', ('key', 'Hold'),
                                  'reels in'],
                                 [('pad', 'A'), 'twitches the bobber (try it on a nibble!)  Hold', ('pad', 'A'),
                                  'to reel in']),
            'fly': self.hint(['Fly casting: tap', ('key', 'Space'), 'or', ('key', 'Click'), 'on each beat'],
                             ['Fly casting: tap', ('pad', 'A'), 'on each beat']),
        }.get(st)
        if st == 'idle' and seasons.frozen(self):
            hint = [seasons.ice_tip(self)]
        elif st == 'idle' and seasons.fly_on(self):
            hint = self.hint([('key', 'Space'), 'or', ('key', 'Click'), 'to start a fly cast'],
                             [('pad', 'A'), 'to start a fly cast'])
        if st == 'waiting' and f.t > 7 and self.total >= 3:
            hint = None                  # it has been said: let the water have the screen
        if hint and self.overlay is None and self.help_on() and self.typing != 'chat':
            w = ui.rich(s, hint, (0, 0), measure=True) + 40
            room = SW - 16 - (0 if self.hud_tuck > 0.5 else 20 + self._dock_n * 72) - 16 - 16
            if w > room:
                hint = {'idle': [('key', 'Hold Click'), 'or', ('key', 'Space'), 'to wind up a cast'],
                        'waiting': [('key', 'Tap'), 'to twitch,', ('key', 'Hold'), 'to reel in']}.get(st, hint)
                w = ui.rich(s, hint, (0, 0), measure=True) + 40
            r = ui.glass(s, (16, SH - 16 - 46, w, 46), 150, 23)
            ui.rich(s, hint, (r.x + 20, r.centery))
        elif self.overlay is None and st == 'idle' and self.settings.get('hints', True) and self.typing != 'chat':
            self.draw_help_chip(s)
        if st == 'fly':
            px, py = self.w2s(PLAYER_X, DECK_Y)
            seasons.draw_fly(s, ui, f, (px + 130, py - 170))
        if st == 'charging':
            px, py = self.w2s(PLAYER_X, DECK_Y)
            bx, by = px - 64, py - 170
            ui.panel(s, (bx - 6, by - 6, 30, 142), radius=10)
            pygame.draw.rect(s, (220, 206, 182), (bx, by, 18, 130), border_radius=6)
            hgt = int(130 * f.power)
            col = art.lerp_c((126, 180, 118), (236, 176, 80), f.power)
            if f.power > 0.8:
                col = art.lerp_c(col, (232, 120, 110), (f.power - 0.8) * 5)
            pygame.draw.rect(s, col, (bx, by + 130 - hgt, 18, hgt), border_radius=6)
            rod = self.rod_spec()
            d = 0.1 + f.power * (rod['range'] - 0.1)
            tx, ty = self.w2s(*cast_point(d, f.aim))
            pulse = 6 + int(math.sin(self.t * 10) * 2)
            pygame.draw.circle(s, (255, 250, 230), (tx, ty), pulse + 4, 2)
            pygame.draw.circle(s, (255, 250, 230), (tx, ty), 2)
            # dotted arc showing the throw
            hx, hy = self.w2s(*f.tip)
            for i in range(1, 12):
                k = i / 12
                ax = hx + (tx - hx) * k
                ay = hy + (ty - hy) * k - math.sin(math.pi * k) * (60 + d * 80)
                pygame.draw.circle(s, (255, 250, 230), (int(ax), int(ay)), 2)
        if st == 'bite':
            x, y = self.w2s(PLAYER_X + 3, DECK_Y - 34)
            y -= abs(math.sin(self.t * 14)) * 10
            r = pygame.Rect(0, 0, 48, 56)
            r.center = (x, y)
            ui.panel(s, r, fill=(255, 250, 238), radius=16)
            pygame.draw.polygon(s, (255, 250, 238), [(x - 8, r.bottom - 3), (x - 2, r.bottom + 12), (x + 6, r.bottom - 3)])
            ui.blit_text(s, '!', r.center, 'bang', (220, 80, 70), 'center')
        if st == 'fight' and f.mg:
            sv = f.catch['spec']['strength']
            what = ('A little nibbler' if sv < 0.3 else 'A good fighter' if sv < 0.6 else
                    'Something strong!' if sv < 0.85 else 'Something HUGE!!')
            if getattr(f.mg, 'stage', 0):
                what = f.mg.spec['name'] + '!'
            elif f.mg.t < 2.5:
                what = '%s... %s!' % (what.rstrip('!'), minigame.STYLE_NAMES.get(f.mg.style, 'a fighter').lower())
            minigame.draw(s, ui, f.mg, self.t, what, teach=self.total < 10 and self.settings.get('hints', True))

    def draw_quick_pop(self, s):
        """The corner note for a repeat catch: what, how big, and that it went in the basket."""
        qp = self.quick_pop
        if not qp or self.overlay is not None:
            return
        ui = self.ui
        t = qp['t']
        k = min(1.0, t / 0.25, max(0.0, (3.2 - t) / 0.4))
        e = 1 - (1 - k) ** 3
        spec = qp['spec']
        name = '%s  %.1f cm' % (spec['name'], qp['size'])
        w = max(ui.fonts['smallb'].size(name)[0], ui.fonts['small'].size('Into the basket (%d coins)' % qp['price'])[0]) + 112
        r = pygame.Rect(16 - int((1 - e) * (w + 20)), SH - 16 - 46 - 74, w, 64)
        r = ui.panel(s, r, radius=18)
        icon = art.fish_sprite(spec, 2)
        if icon.get_width() > 64:
            icon = pygame.transform.scale(icon, (64, max(1, icon.get_height() * 64 // icon.get_width())))
        s.blit(icon, icon.get_rect(center=(r.x + 46, r.centery)))
        ui.blit_text(s, name, (r.x + 86, r.y + 10), 'smallb', U.INK, maxw=w - 96)
        ui.blit_text(s, 'Into the basket (%d coins)' % qp['price'], (r.x + 86, r.y + 36), 'small', U.SOFT,
                     maxw=w - 96)

    def draw_toasts(self, s):
        ui = self.ui
        # over a window: one slim line in the gap above it, clear of its title and buttons;
        # on the lake, at the top (under any tip)
        bottom = False
        y, step = 18, 54
        over = bool(self.overlay) and self.overlay not in ('pause', 'options')
        if over:
            y = 5
        elif tutorial.active(self) and tutorial.relevant(self) and self.overlay is None:
            y = 88
        slim = self.hud_style() == 'clean'
        for n_, (text, life, col) in enumerate(self.toasts):
            k = max(0.0, min(1.0, (3.6 - life) / 0.3, life / 0.35))
            e = 1 - (1 - k) ** 3
            if over:
                if n_:
                    break                                 # one at a time over a window
                waiting = len(self.toast_q) + len(self.toasts) - 1
                tw_ = ui.fonts['smallb'].size(text)[0]
                w = min(SW - 240, tw_ + 58 + (40 if waiting else 0))
                r = pygame.Rect(SW // 2 - w // 2, y - int((1 - e) * 44), w, 32)
                ui.panel(s, r, radius=16)
                pygame.draw.circle(s, col, (r.x + 18, r.centery), 5)
                pygame.draw.circle(s, U.darken(col, 0.3), (r.x + 18, r.centery), 5, 2)
                ui.blit_text(s, text, (r.x + 32, r.centery), 'smallb', U.INK, 'midleft',
                             maxw=r.w - 44 - (40 if waiting else 0))
                if waiting:
                    c = (r.right - 24, r.centery)
                    pygame.draw.circle(s, (236, 222, 196), c, 12)
                    ui.blit_text(s, '+%d' % waiting, c, 'tiny', U.BROWN, 'center')
                continue
            if slim:
                # a small pill; long notes wrap onto two lines rather than stretching across the lake
                lines = ui.wrap(text, 'smallb', SW - 16 - 188 - 12 - (16 + 320 + 12) - 110)[:2]
                w = max(ui.fonts['smallb'].size(ln)[0] for ln in lines) + 58
                waiting = len(self.toast_q)
                if waiting:
                    w += 40
                h = 38 if len(lines) == 1 else 62
                off = int((1 - e) * 60)
                lo, hi = 16 + 320 + 12, SW - 16 - 188 - 12
                cx = (lo + hi) // 2 if w > hi - lo else max(lo + w // 2, min(hi - w // 2, SW // 2))
                r = pygame.Rect(cx - w // 2, y - off, w, h)
                ui.panel(s, r, radius=18)
                pygame.draw.circle(s, col, (r.x + 20, r.centery), 6)
                pygame.draw.circle(s, U.darken(col, 0.3), (r.x + 20, r.centery), 6, 2)
                for i, ln in enumerate(lines):
                    ui.blit_text(s, ln, (r.x + 36, r.centery + (i * 2 - len(lines) + 1) * 12), 'smallb', U.INK,
                                 'midleft')
                if waiting:
                    c = (r.right - 26, r.centery)
                    pygame.draw.circle(s, (236, 222, 196), c, 13)
                    ui.blit_text(s, '+%d' % waiting, c, 'tiny', U.BROWN, 'center')
                y += h + 8
                continue
            w = ui.fonts['bodyb'].size(text)[0] + 64
            off = int((1 - e) * 80)
            cx = SW // 2
            if not bottom:
                # keep clear of the HUD cards on both sides (matters at large interface sizes)
                lo, hi = 16 + 372 + 12, SW - 16 - (188 if y < 60 else 300) - 12
                cx = (lo + hi) // 2 if w > hi - lo else max(lo + w // 2, min(hi - w // 2, cx))
            r = pygame.Rect(cx - w // 2, y + (off if bottom else -off), w, 44)
            ui.panel(s, r, radius=22)
            pygame.draw.circle(s, col, (r.x + 24, r.centery), 7)
            pygame.draw.circle(s, U.darken(col, 0.3), (r.x + 24, r.centery), 7, 2)
            ui.blit_text(s, text, (r.x + 42, r.centery), 'bodyb', U.INK, 'midleft')
            y += step

    # ---------------- catch card
    def draw_showoff(self, s):
        """The angler holds the catch up: light behind it, its name and size, then the card."""
        ui = self.ui
        c = self.card
        spec = c['spec']
        r = spec['rarity']
        el = c['show'] + c['t']                       # seconds since it landed in your hands
        hx, hy = self.w2s(HAND[0] + 2, HAND[1] - 22)
        rc = RARITY_COLORS[r] if r >= 2 else (255, 236, 180)
        nm = morphs.name(spec, c.get('v'))
        if c.get('v'):
            rc = morphs.MORPH_BY_ID[c['v']]['col']
            r = max(r, 3)                             # a morph gets the full show
        # rays of light turning slowly behind the fish
        grow = min(1.0, el / 0.35)
        rad = max(8, int((90 + 30 * r) * grow))
        rays = pygame.Surface((rad * 2, rad * 2))
        n = 10 + r * 2
        bright = 0.06 + 0.025 * r
        col = tuple(int(v * bright) for v in rc)
        inner = 34                                    # keep the angler and the fish clear
        for i in range(n):
            a = self.t * 0.6 + i * 2 * math.pi / n
            pts = [(rad + math.cos(a + d) * rr, rad + math.sin(a + d) * rr)
                   for d, rr in ((-0.05, inner), (-0.11, rad), (0.11, rad), (0.05, inner))]
            pygame.draw.polygon(rays, col, pts)
        s.blit(rays, (hx - rad, hy - rad), special_flags=pygame.BLEND_RGB_ADD)
        if r >= 3 and int(self.t * 20) % 3 == 0:
            self.world.sparkles(HAND[0] + 10, HAND[1] - 26, 1, rc, 14)
        # the banner over the angler
        k = min(1.0, el / 0.3)
        e = 1 - (1 - k) ** 3
        bw = max(300, ui.fonts['h2'].size(nm)[0] + 70)
        bx, by = hx - bw // 2, hy - 190 + int((1 - e) * 24)
        bx = max(16, min(SW - 16 - bw, bx))
        rect = pygame.Rect(bx, by, bw, 104)
        ui.panel(s, rect, radius=18)
        tag = 'NEW!' if c['new'] else 'Record!' if c['record'] else (RARITY_NAMES[r] if r else '')
        if tag:
            tc = U.ROSE if c['new'] else U.GOLD if c['record'] else rc
            pw = ui.fonts['smallb'].size(tag)[0] + 26
            pill = pygame.Rect(0, 0, pw, 28)
            pill.midtop = (rect.centerx, rect.y - 14)
            pygame.draw.rect(s, tc, pill, border_radius=14)
            ui.blit_text(s, tag, pill.center, 'smallb', (90, 60, 30) if c['record'] and not c['new'] else
                         (255, 255, 250), 'center')
        ui.blit_text(s, nm, (rect.centerx, rect.y + 34), 'h2', U.INK, 'center')
        grow_k = min(1.0, max(0.0, (el - 0.15) / 0.7))
        grow_k = 1 - (1 - grow_k) ** 2
        ui.blit_text(s, '%.1f cm' % (c['size'] * grow_k), (rect.centerx, rect.y + 64), 'bodyb', U.SOFT, 'center')
        # the measuring tape
        lo, hi = spec['size']
        tw = rect.w - 60
        tx, ty = rect.x + 30, rect.y + 82
        pygame.draw.rect(s, (236, 206, 110), (tx, ty, tw, 12), border_radius=3)
        fill = int(tw * min(1.0, c['size'] * grow_k / max(0.1, hi)))
        if fill > 0:
            pygame.draw.rect(s, (250, 226, 140), (tx, ty, fill, 12), border_radius=3)
        for i in range(21):
            xx = tx + int(tw * i / 20)
            pygame.draw.line(s, (120, 90, 50), (xx, ty), (xx, ty + (7 if i % 5 == 0 else 4)))
        if fill > 0:
            pygame.draw.line(s, U.ROSE, (tx + fill, ty - 3), (tx + fill, ty + 14), 2)
        best = c.get('old', 0)
        if best and best < hi and not spec.get('junk'):
            bx2 = tx + int(tw * best / hi)
            pygame.draw.polygon(s, U.GOLD, [(bx2 - 5, ty + 20), (bx2 + 5, ty + 20), (bx2, ty + 13)])
        pygame.draw.rect(s, (150, 112, 60), (tx, ty, tw, 12), 1, border_radius=3)
        ticks = int(grow_k * 12)
        if ticks > c.get('tape_n', 0):
            c['tape_n'] = ticks
            self.audio.play('click', 0.25 + 0.03 * ticks)
        tip = self.hint(['Click or', ('key', 'Space'), 'to look closer'], [('pad', 'A'), 'to look closer'])
        tw = ui.rich(s, tip, (0, 0), measure=True)
        ui.rich(s, tip, (rect.centerx - tw // 2, rect.bottom + 22), outline=(30, 20, 30))

    def draw_card(self, s):
        ui = self.ui
        c = self.card
        spec = c['spec']
        r = spec['rarity']
        k = min(1.0, c['t'] / 0.35)
        ease = 1 - (1 - k) ** 3
        w, h = 540, 536
        rect = pygame.Rect(SW // 2 - w // 2, SH // 2 - h // 2 + int((1 - ease) * 60), w, h)
        ui.panel(s, rect, radius=24)
        rc = RARITY_COLORS[r]
        # rarity pill
        label = RARITY_NAMES[r] if not spec.get('junk') else ('Treasure' if spec['price'] >= 50 else 'Lake find')
        pill = pygame.Rect(0, 0, ui.fonts['smallb'].size(label)[0] + 30, 30)
        pill.midtop = (rect.centerx, rect.y + 18)
        pygame.draw.rect(s, rc, pill, border_radius=15)
        ui.blit_text(s, label, pill.center, 'smallb', (255, 255, 250), 'center')
        if c['new']:
            nb = pygame.Rect(rect.x + 18, rect.y + 18, 76, 30)
            pygame.draw.rect(s, U.ROSE, nb, border_radius=15)
            ui.blit_text(s, 'NEW!', nb.center, 'smallb', (255, 255, 250), 'center')
        elif c['record']:
            nb = pygame.Rect(rect.x + 18, rect.y + 18, 100, 30)
            pygame.draw.rect(s, U.GOLD, nb, border_radius=15)
            ui.blit_text(s, 'Record!', nb.center, 'smallb', (90, 60, 30), 'center')
        # sprite with halo
        cy = rect.y + 150
        halo = pygame.Surface((300, 170), pygame.SRCALPHA)
        hc = spec.get('glow') or rc
        for i in range(10, 0, -1):
            pygame.draw.ellipse(halo, (*hc, 10 + (10 - i) * 4), (150 - i * 14, 85 - i * 8, i * 28, i * 16))
        s.blit(halo, (rect.centerx - 150, cy - 85))
        spr = morphs.sprite(spec, c.get('v'), 4)
        wob = math.sin(self.t * 2.2) * 4
        rot = pygame.transform.rotate(spr, math.sin(self.t * 1.7) * 4)
        s.blit(rot, rot.get_rect(center=(rect.centerx, cy + wob)))
        if r >= 3:
            for i in range(6):
                a = self.t * 1.5 + i * 1.05
                px = rect.centerx + math.cos(a) * 130
                py = cy + math.sin(a) * 50
                U.star(s, (int(px), int(py)), 5 + (i % 2) * 2, (255, 236, 160))
        # text
        y = rect.y + 252
        ui.blit_text(s, morphs.name(spec, c.get('v')), (rect.centerx, y), 'h1', U.INK, 'center', maxw=w - 40)
        if c.get('v'):
            mr = morphs.badge(s, ui, c['v'], (rect.centerx, rect.y + 64), 'smallb')
            if c.get('new_colour'):
                ui.blit_text(s, 'New colour!', (mr.right + 10, mr.centery), 'tiny', U.ROSE, 'midleft')
            for i in range(8):
                a = self.t * 0.9 + i * math.tau / 8
                px = rect.centerx + math.cos(a) * 150
                py = rect.y + 150 + math.sin(a) * 60
                if math.sin(self.t * 3 + i * 1.7) > 0:
                    U.star(s, (int(px), int(py)), 4 + (i % 3), U.lighten(morphs.MORPH_BY_ID[c['v']]['col'], 0.4))
        y += 36
        if r >= 1:
            for i in range(5):
                # the earned stars pop in one after another
                pk = min(1.0, max(0.0, (c['t'] - 0.25 - i * 0.09) / 0.14)) if i < r else 1.0
                size = int(10 * (pk + 0.35 * math.sin(math.pi * pk))) if i < r else 10
                if size > 0:
                    U.star(s, (rect.centerx - 52 + i * 26, y), size, U.GOLD if i < r else (220, 210, 190), True)
            y += 26
        tick = min(1.0, max(0.0, c['t'] / 0.6))
        tick = 1 - (1 - tick) ** 2
        info = '%.1f cm' % (c['size'] * tick)
        if c['record'] and c.get('old') and tick >= 1:
            info += '  (best was %.1f)' % c['old']
        surf = ui.text(info, 'bodyb', U.SOFT)
        vs = ui.text('%d' % c['price'], 'bodyb', U.INK)
        total = surf.get_width() + 40 + vs.get_width() + 26
        x0 = rect.centerx - total // 2
        s.blit(surf, (x0, y))
        U.coin(s, (x0 + surf.get_width() + 40, y + 13), 10)
        s.blit(vs, (x0 + surf.get_width() + 56, y))
        y += 36
        for line in ui.wrap(spec['desc'], 'body', w - 80):
            ui.blit_text(s, line, (rect.centerx, y), 'body', U.INK, 'midtop')
            y += 26
        by = rect.bottom - 100
        keep = self.cap_icon('Space', 'A')
        if spec['id'] == 'bottle':
            ui.button(s, (rect.centerx - 120, by, 240, 52), 'Read the note', self.keep_catch, 'primary', icon=keep)
        elif spec.get('junk'):
            ui.button(s, (rect.centerx - 120, by, 240, 52), 'Into the basket', self.keep_catch, 'primary', icon=keep)
        else:
            # the buttons show the key, or the controller button, that picks them (A keep, X tank, Y release)
            full = len(self.tank) >= self.tank_size()
            if c.get('v'):
                pond = hatchery.room(self) > 0 and hatchery.can_live(spec)
                ui.button(s, (rect.centerx - 244, by, 156, 52), 'To pond' if pond else 'Sell', self.keep_catch,
                          'primary', icon=keep)
            else:
                ui.button(s, (rect.centerx - 244, by, 156, 52), 'Keep', self.keep_catch, 'primary', icon=keep)
            ui.button(s, (rect.centerx - 78, by, 156, 52), 'Tank full' if full else 'To tank',
                      self.tank_catch, 'normal', enabled=not full, icon=None if full else self.cap_icon('T', 'X'))
            ui.button(s, (rect.centerx + 88, by, 156, 52), 'Release', self.release_catch, 'rose',
                      icon=self.cap_icon('R', 'Y'))
            ui.blit_text(s, 'Fish in your cabin tank: %d / %d' % (len(self.tank), self.tank_size()),
                         (rect.centerx, rect.bottom - 18), 'small', U.SOFT, 'midbottom')

    # ---------------- letter
    def draw_letter(self, s):
        ui = self.ui
        head, body, sign = self.letter
        # long letters get wider paper, then tighter lines, so the whole note and its button always fit
        for tw in (560, 700, 840):
            lines = ui.wrap(body, 'hand', tw)
            sp = 34
            if 240 + len(lines) * sp <= SH - 24:
                break
        else:
            sp = max(26, (SH - 24 - 240) // max(1, len(lines)))
        h = 150 + len(lines) * sp + 90
        rect = pygame.Rect(SW // 2 - (tw + 80) // 2, SH // 2 - h // 2, tw + 80, h)
        ui.panel(s, rect, fill=(250, 242, 216), border=(176, 140, 100), radius=10)
        for yy in range(rect.y + 90, rect.bottom - 70 - sp, sp):
            pygame.draw.line(s, (232, 218, 190), (rect.x + 36, yy + sp - 6), (rect.right - 36, yy + sp - 6))
        pygame.draw.circle(s, (196, 80, 74), (rect.right - 50, rect.y + 46), 18)
        pygame.draw.circle(s, (220, 110, 100), (rect.right - 50, rect.y + 46), 12, 2)
        ui.blit_text(s, head, (rect.x + 40, rect.y + 30), 'handb', (80, 60, 70))
        y = rect.y + 90
        for line in lines:
            ui.blit_text(s, line, (rect.x + 40, y), 'hand', (70, 56, 66))
            y += sp
        ui.blit_text(s, sign, (rect.right - 50, y + 10), 'handb', (80, 60, 70), 'topright')
        ui.button(s, (rect.centerx - 80, rect.bottom - 64, 160, 46), 'Close', self.close_letter, 'primary')

    # ---------------- journal
    def big_panel(self, s, title):
        ui = self.ui
        rect = pygame.Rect(SW // 2 - 520, SH // 2 - 318, 1040, 636)
        ui.panel(s, rect, radius=24)
        self.panel_header(s, rect, title)
        close = pygame.Rect(rect.right - 62, rect.y + 18, 44, 44)
        ui.button(s, close, 'X', lambda: self.close_overlay(), 'normal', font='h3')
        return rect

    MAP_PINS = {'dock': (44, 108), 'cove': (98, 180), 'deep': (166, 101), 'creek': (246, 54)}

    def draw_map(self, s):
        ui = self.ui
        at_sea = self.spot in COAST_IDS
        rect = self.big_panel(s, 'Saltmarsh Coast' if at_sea else 'Lake Map')
        sea = self.env.season
        mp = self._mapcache.get((at_sea, sea))
        if mp is None:
            src = coast.make_map(sea) if at_sea else art.make_map(sea)
            mp = self._mapcache[(at_sea, sea)] = pygame.transform.scale(src, (600, 440))
        mr = U.snap_rect(pygame.Rect(rect.x + 28, rect.y + 92, 600, 440))
        s.blit(ui._frame(mr.w + 16, mr.h + 16, (120, 86, 60), (84, 58, 42), 2), mr.inflate(16, 16))
        s.blit(mp, mr)
        spots = COAST_SPOTS if at_sea else LAKE_SPOTS
        pins = coast.COAST_PINS if at_sea else self.MAP_PINS
        if at_sea:                                  # the river back up to the lake
            ax, ay = pins['dock']
            ui.blit_text(s, 'To Lantern Lake', (mr.x + ax * 2 + 14, mr.y + ay * 2 + 4), 'smallb', (255, 250, 236),
                         'topleft', outline=(50, 36, 30))
        for sp in spots:
            ax, ay = pins[sp['id']]
            px, py = mr.x + ax * 2, mr.y + ay * 2
            sel = sp['id'] == self.map_sel
            here = sp['id'] == self.spot
            hit = pygame.Rect(px - 18, py - 18, 36, 36)
            hov = hit.collidepoint(ui.mouse)
            r = 12 if (sel or hov) else 9
            pygame.draw.circle(s, (60, 40, 30), (px, py + 2), r + 2)
            pygame.draw.circle(s, U.GOLD if sel else (250, 244, 226), (px, py), r)
            pygame.draw.circle(s, (90, 60, 40), (px, py), r, 2)
            pygame.draw.circle(s, (90, 60, 40), (px, py), 3)
            ui.blit_text(s, sp['name'], (px, py + r + 6), 'smallb', (255, 250, 236), 'midtop', outline=(50, 36, 30))
            if here:
                U.rowboat(s, (px + 32, py - 6), 0.9)
            ui.hotspot(hit, lambda k=sp['id']: self.map_pick(k))
        # the spot list and details
        x0 = mr.right + 28
        w = rect.right - 28 - x0
        entries = [(sp['id'], sp['name'] + ('  (here)' if sp['id'] == self.spot else '')) for sp in spots]
        if at_sea:
            entries.append(('dock', 'Row home, up the river'))
        elif coast.is_open(self):
            entries.append(('pier', 'Saltmarsh, down the river'))
        step = 52 if len(entries) <= 4 else 46
        if self.map_sel not in [e[0] for e in entries]:
            self.map_sel = entries[0][0]
        for i, (sid, label) in enumerate(entries):
            ui.button(s, (x0, rect.y + 86 + i * step, w, step - 8), label, lambda k=sid: self.map_pick(k),
                      'tab_on' if sid == self.map_sel else 'tab', nav=True, font='bodyb')
        sel = self.map_sel
        spec = SPOT_BY_ID[sel]
        river = coast.region(sel) != coast.region(self.spot)
        desc = spec['desc']
        if river:
            desc = ('About %d minutes back up the river to your own dock, and Biscuit.' % coast.river_minutes(self)
                    if sel == 'dock' else 'About %d minutes down the river to the sea: a harbour, a dark old '
                    'lighthouse and fish that follow the tide.' % coast.river_minutes(self))
        y = rect.y + 86 + len(entries) * step + 8
        for line in ui.wrap(desc, 'small', w)[:4 if len(entries) <= 4 else 3]:
            ui.blit_text(s, line, (x0, y), 'small', U.SOFT)
            y += 22
        y += 8
        here = SEA_FISH if river and sel != 'dock' else fish_at(sel)
        known = sum(1 for f in here if f['id'] in self.journal)
        ui.blit_text(s, 'Species here:  %d / %d' % (known, len(here)), (x0, y), 'smallb', U.INK)
        y += 28
        locals_ = [f for f in FISH if f['spot'] == sel and f['rarity'] < 5]
        if not locals_:
            ui.blit_text(s, 'Every lake fish swims past', (x0, y + 6), 'small', U.SOFT)
            ui.blit_text(s, 'the dock sooner or later.', (x0, y + 28), 'small', U.SOFT)
        tw = (w - 16) // 3
        for i, f in enumerate(locals_[:3]):
            tr = pygame.Rect(x0 + i * (tw + 8), y, tw, 78)
            k = f['id'] in self.journal
            ui.tile(s, tr, (244, 236, 218), RARITY_COLORS[f['rarity']] if k else (186, 170, 150))
            key = ('map', f['id'], k)
            spr = self._jcache.get(key)
            if spr is None:
                src = art.fish_sprite(f, 2) if k else art.silhouette(f, 2)
                spr = self._jcache[key] = pygame.transform.scale(src, (72, 36))
            s.blit(spr, spr.get_rect(center=(tr.centerx, tr.y + 28)))
            ui.blit_text(s, f['name'].split(' ')[-1] if k else '???', (tr.centerx, tr.bottom - 18), 'small',
                         U.INK if k else U.SOFT, 'center', maxw=tr.w - 8)
        by = rect.bottom - 28 - 54
        if sel == self.spot:
            ui.button(s, (x0, by, w, 54), 'You are here', None, enabled=False, font='h3')
        else:
            ui.button(s, (x0, by, w, 54), 'Row home' if sel == 'dock' else 'Row down the river' if river else
                      'Row there', lambda: self.travel(self.map_sel), 'primary', font='h3', nav=True)

    def map_pick(self, spot):
        self.map_sel = spot
        self.audio.play('ui', 0.5)

    def close_overlay(self):
        if self.overlay == 'stall':
            return stallmod.close(self)
        if self.walk_scene() and self.aqscene.panel:
            self.aqscene.close_panel()       # a window inside the aquarium or the harbour: back to walking
            return
        self.overlay = None
        self.audio.play('page', 0.5)

    def draw_journal(self, s):
        ui = self.ui
        rect = self.big_panel(s, 'Lake Journal')
        tx = rect.x + 330
        for i, (key, label) in enumerate((('fish', 'Fish'), ('letters', 'Letters'), ('badges', 'Badges'),
                                          ('nature', 'Nature'))):
            st = 'tab_on' if self.j_tab == key else 'tab'
            ui.button(s, (tx + i * 130, rect.y + 26, 120, 40), label, lambda k=key: setattr(self, 'j_tab', k), st)
        caught = sum(1 for f in FISH if f['id'] in self.journal)
        fx = rect.x + 34
        if self.j_tab == 'letters' and self.diary_entries():
            for i, label in enumerate(('Letters', "Rosie's diary")):
                ui.button(s, (rect.x + 28 + i * 104, rect.bottom - 52, 98 + 48 * i, 36), label,
                          lambda i=i: setattr(self, 'l_page', i), 'tab_on' if self.l_page == i else 'tab',
                          font='smallb')
            fx = rect.x + 300
        if self.j_tab == 'nature':
            return wildlife.draw_page(self, s, rect)
        if self.j_tab == 'letters':
            ui.blit_text(s, 'Species  %d / %d      Letters  %d / %d      Fish caught  %d'
                         % (caught, len(FISH), len(self.letters), len(LETTERS), self.total),
                         (fx, rect.bottom - 40), 'smallb', U.SOFT)
            return self.draw_letters_tab(s, rect)
        if self.j_tab == 'badges':
            return self.draw_badges_tab(s, rect)
        self.draw_fish_tab(s, rect, caught)

    # the journal's fish pages: (chip label, a line about the place)
    JOURNAL_PAGES = (
        ('Lake', 'Fish from your dock and the open lake. Most of them bite all year round.'),
        ('Rowboat', 'Fish from the cove, the deep water and the creek. Row out to meet them.'),
        ('Seasonal', 'Fish that want a particular season, bait or way of fishing.'),
        ('Coast', 'Fish from the sea at Saltmarsh, down the river. Mind the tide.'),
        ('Far Shore', 'Fish from the Hollow Pool, in the woods across the lake. They rise after 7:30 PM.'),
        ('Roads', "Fish from the places Rosie's truck reaches: the reservoir, the falls, Gull Point and the "
                  'quarry.'),
    )

    def journal_page(self, i):
        if i == 0:
            return [f for f in fish_at('dock') if not f.get('method')]
        if i == 1:
            return [f for f in FISH if f['spot'] in ('cove', 'deep', 'creek') and not f.get('method')]
        if i == 2:
            return [f for f in FISH if f.get('method') and f['method'] not in ('sea', 'hollow', 'road')]
        if i == 5:
            return ROAD_FISH
        return SEA_FISH if i == 3 else HOLLOW_FISH

    def journal_locked(self, i, page):
        """How to reach a page's fish, while you can't yet (None once you can, or have caught one)."""
        if any(f['id'] in self.journal for f in page):
            return None
        if i == 1 and not self.has_boat():
            return 'A rowboat would take you there.'
        if i == 3 and not coast.is_open(self):
            return 'With a rowboat, the river will take you there.'
        if i == 4 and not farmod.unlocked(self):
            return 'Mend the old landing across from your dock to get there.'
        if i == 5 and not truckmod.unlocked(self):
            return "Fix up Grandma Rosie's old truck to reach them."
        return None

    def draw_fish_tab(self, s, rect, caught):
        ui = self.ui
        gx, gw = rect.x + 28, 688
        # the places, as chips: how many you've found at each, with a little bar
        npg = len(self.JOURNAL_PAGES)
        cy, cw = rect.y + 92, (688 - (npg - 1) * 8) // npg
        for i, (label, _) in enumerate(self.JOURNAL_PAGES):
            pg = self.journal_page(i)
            got = sum(1 for f in pg if f['id'] in self.journal)
            r = pygame.Rect(gx + i * (cw + 8), cy, cw, 52)
            on = self.j_page == i
            hov = r.collidepoint(ui.mouse)
            ui.tile(s, r, (252, 248, 236) if on else (246, 238, 220) if hov else (234, 222, 198),
                    (150, 112, 76) if on else (200, 180, 154), on)
            ui.blit_text(s, label, (r.x + 12, r.y + 8), 'smallb', U.INK if on else U.BROWN, maxw=cw - 22)
            bar = pygame.Rect(r.x + 12, r.y + 35, cw - 70, 6)
            pygame.draw.rect(s, (222, 206, 180), bar, border_radius=3)
            if got:
                full = got == len(pg)
                pygame.draw.rect(s, U.GOLD if full else (120, 164, 110),
                                 (bar.x, bar.y, max(6, bar.w * got // max(1, len(pg))), bar.h), border_radius=3)
            ui.blit_text(s, '%d/%d' % (got, len(pg)), (r.right - 12, bar.centery), 'tiny',
                         U.INK if on else U.SOFT, 'midright')
            ui.hotspot(r, lambda i=i: setattr(self, 'j_page', i))
        page = self.journal_page(self.j_page)
        if page and FISH[self.j_sel] not in page:
            self.j_sel = FISH.index(page[0])      # keep the detail card on this page
        # the grid sizes itself to the page: big tiles for a handful of fish, seven across for the lake
        top = cy + 52 + 14
        avail = rect.bottom - 24 - top
        n = len(page)
        cols = 7 if n > 15 else 5
        tw = (gw - (cols - 1) * 8) // cols
        rows = max(1, -(-n // cols))
        th = min(tw + 8, 140, (avail - (rows - 1) * 8) // rows)
        hover_i = None
        for k, f in enumerate(page):
            i = FISH.index(f)
            tr = pygame.Rect(gx + (k % cols) * (tw + 8), top + (k // cols) * (th + 8), tw, th)
            known = f['id'] in self.journal
            hov = tr.collidepoint(ui.mouse)
            if hov:
                hover_i = i
            sel = i == self.j_sel
            fill = (252, 248, 236) if hov or sel else (240, 230, 210)
            ui.tile(s, tr, fill, RARITY_COLORS[f['rarity']] if known else (186, 170, 150), sel)
            src = art.fish_sprite(f, 1) if known else art.silhouette(f, 1)
            sc = max(1, min(3, (tw - 18) // src.get_width(), (th - 54) // src.get_height()))
            key = (f['id'], known, sc)
            spr = self._jcache.get(key)
            if spr is None:
                spr = self._jcache[key] = pygame.transform.scale(src, (src.get_width() * sc, src.get_height() * sc))
            s.blit(spr, spr.get_rect(center=(tr.centerx, (tr.y + 8 + tr.bottom - 46) // 2)))
            name = f['name'] if known else '???'
            if ui.fonts['small'].size(name)[0] > tw - 12:
                name = name.split(' ')[-1]
            ui.blit_text(s, name, (tr.centerx, tr.bottom - 37), 'small', U.INK if known else U.SOFT, 'center',
                         maxw=tw - 10)
            for st in range(f['rarity']):
                U.star(s, (tr.centerx - (f['rarity'] - 1) * 7 + st * 14, tr.bottom - 18), 5,
                       U.GOLD if known else (210, 198, 180))
            ui.hotspot(tr, lambda i=i: setattr(self, 'j_sel', i))
        # room left under a short page: a word about the place (and how to get there)
        y0 = top + rows * (th + 8) + 4
        if rect.bottom - 24 - y0 >= 70:
            label, blurb = self.JOURNAL_PAGES[self.j_page]
            lock = self.journal_locked(self.j_page, page)
            lines = ui.wrap(blurb, 'small', gw - 48) + (ui.wrap(lock, 'small', gw - 48) if lock else [])
            br = pygame.Rect(gx, y0, gw, 20 + 22 * len(lines) + 16)
            pygame.draw.rect(s, (244, 234, 214), br, border_radius=14)
            pygame.draw.rect(s, (222, 204, 178), br, 2, border_radius=14)
            for k, ln in enumerate(lines):
                lc = (90, 120, 150) if lock and k >= len(lines) - len(ui.wrap(lock, 'small', gw - 48)) else U.SOFT
                ui.blit_text(s, ln, (br.x + 24, br.y + 18 + k * 22), 'small', lc)
        self.draw_fish_detail(s, rect, FISH[hover_i if hover_i is not None else self.j_sel], caught)

    def draw_fish_detail(self, s, rect, f, caught):
        """The card on the right: the fish up close, then what you know about it; your totals under it."""
        ui = self.ui
        known = f['id'] in self.journal
        dr = pygame.Rect(rect.x + 740, rect.y + 92, 272, rect.h - 92 - 80)
        pygame.draw.rect(s, (244, 234, 214), dr, border_radius=16)
        pygame.draw.rect(s, (214, 196, 170), dr, 2, border_radius=16)
        halo = pygame.Surface((236, 112), pygame.SRCALPHA)
        hc = RARITY_COLORS[f['rarity']] if known else (190, 180, 170)
        pygame.draw.ellipse(halo, (*hc, 60), halo.get_rect())
        pygame.draw.ellipse(halo, (*hc, 60), halo.get_rect().inflate(-80, -40))
        s.blit(halo, (dr.centerx - 118, dr.y + 16))
        spr = art.fish_sprite(f, 4) if known else art.silhouette(f, 4)
        s.blit(spr, spr.get_rect(center=(dr.centerx, dr.y + 72)))
        y = dr.y + 136
        ui.blit_text(s, f['name'] if known else 'Unknown fish', (dr.centerx, y), 'h3', U.INK, 'center',
                     maxw=dr.w - 24)
        y += 24
        ui.blit_text(s, RARITY_NAMES[f['rarity']], (dr.centerx, y), 'smallb', RARITY_COLORS[f['rarity']], 'center')
        y += 26
        x0, iw = dr.x + 18, dr.w - 36
        if known:
            e = self.journal[f['id']]
            for line in ui.wrap(f['desc'], 'small', iw)[:3]:
                ui.blit_text(s, line, (x0, y), 'small', U.INK)
                y += 22
            y += 8
            bw = (iw - 12) // 3
            for k, (lab, val) in enumerate((('Biggest', '%.1f cm' % e['best']), ('Caught', '%d' % e['count']),
                                            ('Sells for', '%d' % f['price']))):
                br = pygame.Rect(x0 + k * (bw + 6), y, bw, 46)
                pygame.draw.rect(s, (236, 224, 200), br, border_radius=10)
                ui.blit_text(s, lab, (br.centerx, br.y + 13), 'tiny', U.SOFT, 'center', maxw=bw - 6)
                ui.blit_text(s, val, (br.centerx, br.y + 32), 'smallb', U.INK, 'center', maxw=bw - 8)
            y += 60
            ui.blit_text(s, 'Where and when', (x0, y), 'smallb', U.SOFT)
        else:
            ui.blit_text(s, 'Not caught yet.', (x0, y), 'small', U.SOFT)
            y += 30
            ui.blit_text(s, 'Hint', (x0, y), 'smallb', U.SOFT)
        y += 22
        for line in ui.wrap(f['hint'], 'small', iw):
            ui.blit_text(s, line, (x0, y), 'small', U.INK)
            y += 22
        others = [SPOT_BY_ID[sp]['name'] for sp in spots_of(f['id']) if sp != (f['spot'] or 'dock')]
        if others and y < dr.bottom - 30:
            text = 'Also at %s.' % ' and '.join(others) if len(others) < 3 else 'Also at %s and %s.' % (
                ', '.join(others[:-1]), others[-1])
            for line in ui.wrap(text, 'small', iw)[:max(1, (dr.bottom - 8 - y) // 22)]:
                ui.blit_text(s, line, (x0, y + 4), 'small', (90, 120, 150))
                y += 22
        # your totals, under the card
        ty = dr.bottom + 16
        ui.blit_text(s, '%d / %d species' % (caught, len(FISH)), (dr.x + 4, ty), 'smallb', U.INK)
        ui.blit_text(s, '%d caught' % self.total, (dr.right - 4, ty), 'small', U.SOFT, 'topright')
        bar = pygame.Rect(dr.x + 4, ty + 28, dr.w - 8, 8)
        pygame.draw.rect(s, (222, 206, 180), bar, border_radius=4)
        if caught:
            pygame.draw.rect(s, (120, 164, 110), (bar.x, bar.y, max(8, bar.w * caught // len(FISH)), bar.h),
                             border_radius=4)

    def diary_entries(self):
        """The diary pages Biscuit has found, in order, then the letter from the tin under the bench."""
        out = [discover.page_letter(i) for i in sorted(self.finds['pages'])]
        if self.finds.get('secret'):
            out.append(discover.SECRET_LETTER)
        return out

    def draw_letters_tab(self, s, rect):
        ui = self.ui
        y = rect.y + 96
        diary = self.diary_entries()
        if self.l_page == 1 and diary:
            for n, L in enumerate(diary):
                col, row = n % 2, n // 2
                r = pygame.Rect(rect.x + 34 + col * 490, y + row * 86, 470, 74)
                hov = r.collidepoint(ui.mouse)
                ui.tile(s, r, (252, 246, 228) if hov else (246, 236, 212), (176, 146, 110))
                pg = pygame.Rect(r.x + 20, r.y + 16, 28, 40)          # a torn diary page
                pygame.draw.rect(s, (250, 242, 220), pg)
                pygame.draw.rect(s, (176, 146, 110), pg, 1)
                for k in range(4):
                    pygame.draw.line(s, (200, 180, 150), (pg.x + 5, pg.y + 9 + k * 7), (pg.right - 5, pg.y + 9 + k * 7))
                if L is discover.SECRET_LETTER:
                    pygame.draw.circle(s, (196, 80, 80), (pg.right - 4, pg.y + 4), 5)
                ui.blit_text(s, L[0], (r.x + 66, r.y + 12), 'smallb', U.INK, maxw=r.w - 80)
                ui.blit_text(s, L[2], (r.x + 66, r.y + 40), 'small', U.SOFT)
                ui.hotspot(r, lambda L=L: self.open_letter(L))
            left = len(discover.PAGES) - len(self.finds['pages'])
            if left:
                ui.blit_text(s, '%d more page%s out there somewhere. Biscuit might know where.'
                             % (left, '' if left == 1 else 's'), (rect.centerx, rect.bottom - 86), 'small',
                             U.SOFT, 'center')
            return
        if not self.letters:
            ui.blit_text(s, 'No letters yet. Bottles sometimes drift in on the current...', (rect.centerx, y + 120),
                         'body', U.SOFT, 'center')
            return
        for n, idx in enumerate(sorted(self.letters)):
            head, body, sign = LETTERS[idx]
            col, row = n % 2, n // 2
            r = pygame.Rect(rect.x + 34 + col * 490, y + row * 86, 470, 74)
            hov = r.collidepoint(ui.mouse)
            ui.tile(s, r, (252, 246, 228) if hov else (246, 236, 212), (176, 146, 110))
            U.envelope(s, (r.x + 16, r.y + 22, 36, 28))
            ui.blit_text(s, head, (r.x + 66, r.y + 12), 'smallb', U.INK)
            ui.blit_text(s, sign, (r.x + 66, r.y + 40), 'small', U.SOFT)
            ui.hotspot(r, lambda L=LETTERS[idx]: self.open_letter(L))

    BADGES_PER_PAGE = 16

    def draw_badges_tab(self, s, rect):
        ui = self.ui
        y0 = rect.y + 88
        per = self.BADGES_PER_PAGE
        pages = (len(BADGES) + per - 1) // per
        self.b_page = max(0, min(pages - 1, getattr(self, 'b_page', 0)))
        shown = BADGES[self.b_page * per:(self.b_page + 1) * per]
        if pages > 1:
            for i in range(pages):
                ui.button(s, (rect.x + 28 + i * 104, rect.bottom - 52, 98, 36), 'Page %d' % (i + 1),
                          lambda i=i: setattr(self, 'b_page', i), 'tab_on' if self.b_page == i else 'tab',
                          font='smallb')
        rh = min(60, 496 // ((len(shown) + 1) // 2))
        for n, b in enumerate(shown):
            col, row = n % 2, n // 2
            r = pygame.Rect(rect.x + 30 + col * 494, y0 + row * rh, 482, rh - 3)
            got = b['id'] in self.badges
            ui.tile(s, r, (252, 244, 222) if got else (240, 232, 216), U.GOLD if got else (196, 182, 162))
            U.medal(s, (r.x + 34, r.centery), got, 13)
            tight = rh < 46
            ui.blit_text(s, b['name'], (r.x + 66, r.y + (2 if tight else 8)), 'smallb', U.INK if got else U.SOFT)
            desc = b['desc']
            if b['id'] == 'master' and not got:
                desc += '  (%d / %d)' % yeartwo.master_progress(self)
            ui.blit_text(s, desc, (r.x + 66, r.y + (21 if tight else 30)), 'tiny' if tight else 'small', U.SOFT,
                         maxw=r.w - 66 - 84)
            ui.blit_text(s, 'Earned' if got else '+%d' % b['reward'], (r.right - 16, r.centery), 'smallb',
                         (110, 150, 90) if got else U.SOFT, 'midright')
        ui.blit_text(s, 'Badges  %d / %d      Festival wins  %d' % (len(self.badges), len(BADGES),
                                                                    self.stats.get('wins', 0)),
                     (rect.right - 34, rect.bottom - 40), 'smallb', U.SOFT, 'topright')

    # ---------------- cabin
    def cycle_cabin_tab(self, d):
        keys = [k for k, _ in CABIN_TABS]
        i = keys.index(self.cabin_tab) if self.cabin_tab in keys else 0
        self.cabin_tab = keys[(i + d) % len(keys)]
        self.audio.play('ui', 0.4)

    def draw_cabin(self, s):
        ui = self.ui
        if cabinui.fits(SW):
            rect = cabinui.frame(self, s, CABIN_TABS, self.cabin_tab, SW, SH)
        else:
            # the biggest interface size: no room for the rail, so the tabs go along the top
            rect = self.big_panel(s, 'Cabin')
            for i, (key, label) in enumerate(CABIN_TABS):
                st = 'tab_on' if self.cabin_tab == key else 'tab'
                ui.button(s, (rect.x + 168 + i * 114, rect.y + 26, 108, 40), label,
                          lambda k=key: setattr(self, 'cabin_tab', k), st, font='smallb')
        if self.cabin_tab == 'wardrobe':
            return self.draw_wardrobe(s, rect)
        if self.cabin_tab == 'home':
            return homemod.draw_tab(self, s, rect)
        if self.cabin_tab == 'biscuit':
            return biscuit.draw_tab(self, s, rect)
        if self.cabin_tab == 'kitchen':
            return kitchenmod.draw_kitchen(self, s, rect)
        if self.cabin_tab == 'garden':
            return gardenmod.draw_tab(self, s, rect)
        if self.cabin_tab == 'hatchery':
            return hatchery.draw_tab(self, s, rect)
        tx, ty = rect.x + 40, rect.y + 86
        frame = pygame.Rect(tx - 10, ty - 10, 960 + 20, 396 + 20)
        pygame.draw.rect(s, (120, 80, 54), frame, border_radius=10)
        pygame.draw.rect(s, (150, 104, 70), frame.inflate(-6, -6), 3, border_radius=8)
        surf = self.tankview.render(self.tank_sel, self.home['tank'])
        s.blit(pygame.transform.scale(surf, (960, 396)), (tx, ty))
        if not self.tank:
            ui.blit_text(s, 'The tank is empty. Choose "To tank" on a catch card to bring a fish home.',
                         (tx + 480, ty + 170), 'bodyb', (250, 250, 240), 'center', (30, 60, 70))
        ui.hotspot((tx, ty, 960, 396), lambda: self.click_tank(tx, ty))
        # info row
        iy = frame.bottom + 14
        sel = self.tank_sel
        if sel is not None and sel < len(self.tank):
            f = self.tank[sel]
            spec = FISH_BY_ID[f['id']]
            ui.blit_text(s, morphs.name(spec, f.get('v')), (rect.x + 40, iy), 'h3', U.INK)
            ui.blit_text(s, '%.1f cm  -  %s' % (f['size'], RARITY_NAMES[spec['rarity']]), (rect.x + 40, iy + 30),
                         'small', U.SOFT)
            ui.button(s, (rect.x + 300, iy + 4, 220, 48), 'Release to the lake', lambda: self.release_from_tank(sel),
                      'rose')
        else:
            ui.blit_text(s, 'Fish in the tank: %d / %d' % (len(self.tank), self.tank_size()), (rect.x + 40, iy), 'h3', U.INK)
            ui.blit_text(s, 'Click a fish to see it up close.', (rect.x + 40, iy + 30), 'small', U.SOFT)
        # trophy shelf
        shelf_x = rect.x + 560
        pygame.draw.rect(s, (150, 104, 70), (shelf_x, iy + 46, 220, 6), border_radius=2)
        if self.trophies:
            for i, _ in enumerate(self.trophies[:6]):
                U.trophy(s, (shelf_x + 20 + i * 36, iy + 24), 0.85)
            if len(self.trophies) > 6:
                ui.blit_text(s, '+%d' % (len(self.trophies) - 6), (shelf_x + 226, iy + 30), 'smallb', U.SOFT)
        else:
            ui.blit_text(s, 'Trophy shelf (win a festival)', (shelf_x + 110, iy + 26), 'small', U.SOFT, 'center')
        rb = [(k, n) for k, n in self.club['ribbons'].items() if n]
        for i, (k, n_) in enumerate(rb):             # the Angling Club's ribbons, pinned under the shelf
            clubmod.ribbon(s, (shelf_x + 18 + i * 62, iy + 70), clubmod.RIBBON_COL[k], 0.8)
            ui.blit_text(s, 'x%d' % n_, (shelf_x + 34 + i * 62, iy + 72), 'smallb', U.SOFT, 'midleft')
        can_sleep = self.minute >= 1080 or self.minute < 300
        ui.button(s, (rect.right - 214, iy + 4, 180, 48), 'Sleep  (Z)', self.sleep_from_cabin, 'primary',
                  enabled=can_sleep)
        if not can_sleep:
            ui.blit_text(s, 'after 6 PM', (rect.right - 124, iy + 58), 'small', U.SOFT, 'midtop')

    def draw_wardrobe(self, s, rect):
        ui = self.ui
        # live view of the dock so you can see the outfit on
        pv = pygame.Rect(rect.x + 40, rect.y + 96, 320, 256)
        pygame.draw.rect(s, (120, 80, 54), pv.inflate(16, 16), border_radius=12)
        crop = self.frame.subsurface((196, 250, 60, 48))
        s.blit(pygame.transform.scale(crop, pv.size), pv)
        pygame.draw.rect(s, (150, 104, 70), pv.inflate(8, 8), 3, border_radius=10)
        ui.blit_text(s, 'Live from the dock', (pv.centerx, pv.bottom + 18), 'small', U.SOFT, 'midtop')
        ui.button(s, (pv.x, pv.bottom + 54, pv.w, 52), 'Change your look', lambda: creator.open_(self, 'edit'),
                  'gold', font='bodyb')
        self.ward_hover_now = None
        x0 = rect.x + 400

        def section(title, items, owned, current, prefix, kind, y):
            ui.blit_text(s, title, (x0, y), 'h3', U.INK)
            # what you own, then just the next couple still to find, then how many more are out there
            have_ = [it for it in items if it['id'] in owned]
            locked = [it for it in items if it['id'] not in owned]
            show = have_ + locked[:max(1, 4 - len(have_) // 3)]
            rest = len(items) - len(show)
            if rest > 0 and len(show) % 5 == 0:
                show, rest = show[:-1], rest + 1
            items = show
            if rest > 0:
                i = len(items)
                tr = pygame.Rect(x0 + (i % 5) * 120, y + 34 + (i // 5) * 116, 110, 106)
                ui.tile(s, tr, (236, 226, 206), (206, 190, 170))
                ui.blit_text(s, '+%d' % rest, (tr.centerx, tr.y + 26), 'h2', U.SOFT, 'midtop')
                ui.blit_text(s, 'more to find', (tr.centerx, tr.bottom - 30), 'small', U.SOFT, 'midtop')
                if tr.collidepoint(ui.mouse):
                    self.ward_hover_now = dict(id='', name='More to find',
                                               where='Wren\'s wagon, festivals, friends and Biscuit all have some.')
            for i, it in enumerate(items):
                col, row = i % 5, i // 5
                tr = pygame.Rect(x0 + col * 120, y + 34 + row * 116, 110, 106)
                have = it['id'] in owned
                on = it['id'] == current
                hov = tr.collidepoint(ui.mouse)
                if hov:
                    self.ward_hover_now = it
                ui.tile(s, tr, (252, 248, 236) if hov else (240, 230, 210), U.GOLD if on else (186, 170, 150),
                        on)
                icon = art.item_icon(prefix + it['id'], 4)
                if not have:
                    icon = pygame.mask.from_surface(icon, 1).to_surface(setcolor=(176, 162, 146, 255),
                                                                         unsetcolor=(0, 0, 0, 0))
                s.blit(icon, icon.get_rect(center=(tr.centerx, tr.y + 42)))
                name = it['name'] if have else '???'
                if ui.fonts['small'].size(name)[0] > tr.w - 8:
                    name = name.split(' ')[-1]
                ui.blit_text(s, name, (tr.centerx, tr.bottom - 24), 'small', U.INK if have else U.SOFT, 'midtop')
                if have and not on:
                    ui.hotspot(tr, lambda i_=it: self.wear(kind, i_['id']))
        section('Hats', HATS, self.hats, self.hat, 'hat_', 'hat', rect.y + 86)
        section('Biscuit', CAT_ITEMS, self.cat_items, self.cat_item, 'cat_', 'cat', rect.y + 86 + 34 + 2 * 116 + 6)
        it = self.ward_hover_now
        if it:
            have = it['id'] in self.hats or it['id'] in self.cat_items or not it['id']
            ui.blit_text(s, it['name'] if have else 'Not found yet', (x0, rect.bottom - 70), 'bodyb', U.INK)
            ui.blit_text(s, it['where'], (x0, rect.bottom - 44), 'small', U.SOFT)
        else:
            ui.blit_text(s, 'Click something you own to wear it.', (x0, rect.bottom - 56), 'small', U.SOFT)

    def wear(self, kind, item_id):
        if kind == 'hat':
            self.hat = item_id
        else:
            self.cat_item = item_id
            if item_id != 'none':
                self.cat['excited'] = 1.0
        self.audio.play('ui', 0.6)
        self.save()

    def click_tank(self, tx, ty):
        mx, my = self.ui.mouse
        i = self.tankview.hit((mx - tx) / 3, (my - ty) / 3)
        self.tank_sel = i
        if i is not None:
            self.audio.play('ui', 0.5)

    def sleep_from_cabin(self):
        self.overlay = None
        self.try_rest()

    def open_letter(self, letter):
        self.letter = letter
        self.overlay = 'letter'
        self.audio.play('page', 0.6)

    # ---------------- shop
    def draw_shop(self, s):
        ui = self.ui
        rect = self.big_panel(s, 'Trading Post')
        tabs = (('sell', 'Sell'), ('tackle', 'Tackle'), ('bait', 'Bait'), ('decor', 'Decor'), ('wagon', 'Wagon'))
        tx = rect.x + 320
        for i, (key, label) in enumerate(tabs):
            st = 'tab_on' if self.shop_tab == key else 'tab'
            ui.button(s, (tx + i * 94, rect.y + 26, 88, 40), label, lambda k=key: setattr(self, 'shop_tab', k), st)
            if key == 'wagon' and self.wagon_here() and self.shop_tab != 'wagon':
                pygame.draw.circle(s, U.ROSE, (tx + i * 94 + 82, rect.y + 28), 7)
        cr = pygame.Rect(rect.right - 232, rect.y + 24, 156, 44)
        pygame.draw.rect(s, (240, 230, 210), cr, border_radius=14)
        U.coin(s, (cr.x + 24, cr.centery), 12)
        ui.blit_text(s, '{:,}'.format(self.coins), (cr.x + 46, cr.centery), 'big', U.INK, 'midleft')
        body = pygame.Rect(rect.x + 28, rect.y + 92, rect.w - 56, rect.h - 120)
        getattr(self, 'shop_' + self.shop_tab)(s, body)

    def shop_sell(self, s, body):
        ui = self.ui
        dishes = [(rid, n) for rid, n in sorted(self.pantry.items()) if n > 0]
        if not self.basket and not dishes:
            ui.blit_text(s, 'Your basket is empty. Go catch something!', (body.centerx, body.y + 160), 'h3',
                         U.SOFT, 'center')
            return
        stacks = {}
        for b in self.basket:
            stacks.setdefault(b['id'], []).append(b)
        tiles = [('dish', rid, n, self.dish_quote(rid, n)) for rid, n in dishes]
        tiles += [('fish', fid, len(items), self.quote(items)) for fid, items in stacks.items()]
        full = False
        tw, th = 152, 128
        for i, (kind, iid, n, total) in enumerate(tiles):
            col, row = i % 6, i // 6
            if row > 2:
                break
            tr = pygame.Rect(body.x + col * (tw + 12), body.y + row * (th + 12), tw, th)
            hov = tr.collidepoint(ui.mouse)
            if kind == 'dish':
                ui.tile(s, tr, (252, 248, 236) if hov else (246, 236, 216), (220, 150, 120))
                spr = kitchenmod.dish_icon(iid, 2)
                name = kitchenmod.RECIPE_BY_ID[iid]['name']
                act = (lambda rid=iid: self.sell_dish(rid))
            else:
                spec = ALL_BY_ID[iid]
                ui.tile(s, tr, (252, 248, 236) if hov else (240, 230, 210), RARITY_COLORS[spec['rarity']])
                spr = art.fish_sprite(spec, 2)
                name = spec['name']
                act = (lambda fid=iid: self.sell_stack(fid))
            s.blit(spr, spr.get_rect(center=(tr.centerx, tr.y + 38)))
            ui.blit_text(s, '%s x%d' % (name, n), (tr.centerx, tr.y + 80), 'small', U.INK, 'center',
                         maxw=tr.w - 12)
            low = (dish_mult(self.todays_market()['dish']) if kind == 'dish' else self.market_note(iid)) < 0.99
            if kind == 'fish' and ALL_BY_ID[iid].get('junk'):
                low = False
            if low:
                full = True
                pygame.draw.circle(s, U.ROSE, (tr.right - 14, tr.y + 14), 6)
            U.coin(s, (tr.centerx - 22, tr.y + 106), 9)
            ui.blit_text(s, '%d' % total, (tr.centerx - 8, tr.y + 106), 'smallb', U.INK, 'midleft')
            if hov:
                ui.blit_text(s, 'click to sell', (tr.centerx, tr.y + 6), 'small', U.SOFT, 'midtop')
            ui.hotspot(tr, act)
        if self.basket:
            total = self.quote(self.basket)
            ui.button(s, (body.centerx - 170, body.bottom - 56, 340, 52), 'Sell all fish  (%d)' % total,
                      self.sell_all, 'gold')
        if self.boost('sell') > 1.01:
            ui.blit_text(s, 'Fish sell for %d%% more today' % round((self.boost('sell') - 1) * 100),
                         (body.right, body.bottom - 30), 'small', (80, 130, 70), 'midright')
        if full:
            ui.blit_text(s, 'Red dot: the market has plenty of that today.', (body.x, body.bottom - 42), 'small',
                         U.ROSE, 'midleft', maxw=body.centerx - 180 - body.x)
            ui.blit_text(s, 'Prices recover tomorrow.', (body.x, body.bottom - 20), 'small', U.SOFT, 'midleft',
                         maxw=body.centerx - 180 - body.x)

    def item_row(self, s, r, icon, name, desc, right, reserve=None):
        ui = self.ui
        hov = r.collidepoint(ui.mouse)
        ui.tile(s, r, (250, 244, 230) if hov else (242, 232, 212), (186, 160, 124))
        ib = pygame.Rect(r.x + 12, r.y + 12, r.h - 24, r.h - 24)
        ui.tile(s, ib, (226, 212, 186), (196, 172, 140))
        s.blit(icon, icon.get_rect(center=ib.center))
        ui.blit_text(s, name, (ib.right + 14, r.y + 12), 'h3', U.INK, maxw=r.right - ib.right - 180)
        width = r.right - ib.right - 14 - (reserve or 160)
        fit = max(2, (r.h - 50) // 21)              # a taller row reads its whole description
        lines = ui.wrap(desc, 'small', width)
        tight = len(lines) > fit
        if tight:
            lines = ui.wrap(desc, 'small', width, narrow=True)
        for i, line in enumerate(lines[:fit]):
            ui.blit_text(s, line, (ib.right + 14, r.y + 42 + i * 21), 'small', U.SOFT, narrow=tight)
        right(pygame.Rect(r.right - 150, r.centery - 22, 136, 44))

    def price_button(self, s, r, price, action, enabled=True):
        self.ui.button(s, r, '%d' % price, action, 'gold', enabled=enabled and self.coins >= price,
                       icon=self._coin_icon())

    def _coin_icon(self):
        if not hasattr(self, '_ci'):
            self._ci = pygame.Surface((22, 24), pygame.SRCALPHA)
            U.coin(self._ci, (11, 11), 9)
        return self._ci

    # The shop's shelves: a grid of cards on the left, the one you point at (or picked) told in full on the right.
    # entries: dicts with id, name, desc, icon (a function of scale), and any of
    #   price + buy      for sale
    #   status           'Owned', 'Equipped'... (shown in place of a price)
    #   acts             [(label, action, style, enabled)] extra buttons in the detail pane
    #   note             one more line in the detail pane ('In your box: 4')
    #   stats            [(label, 0..1)] little bars in the detail pane
    #   tint             the card's rim colour
    def shop_catalog(self, s, body, entries, cols=4):
        ui = self.ui
        if not entries:
            return
        grid_w = 620
        pane = pygame.Rect(body.x + grid_w + 22, body.y, body.w - grid_w - 22, body.h)
        rows = (len(entries) + cols - 1) // cols
        gap = 12
        cw = (grid_w - (cols - 1) * gap) // cols
        ch = max(120, min(168, (body.h - (rows - 1) * gap) // rows))
        picks = self.__dict__.setdefault('shop_pick', {})
        ids = [e['id'] for e in entries]
        if picks.get(self.shop_tab) not in ids:
            picks[self.shop_tab] = ids[0]
        show = picks[self.shop_tab]
        for i, e in enumerate(entries):
            r = pygame.Rect(body.x + (i % cols) * (cw + gap), body.y + (i // cols) * (ch + gap), cw, ch)
            on = e['id'] == picks[self.shop_tab]
            hov = r.collidepoint(ui.mouse)
            if hov:
                show = e['id']
            owned = 'price' not in e
            fill = (255, 250, 236) if on or hov else (244, 234, 214)
            ui.tile(s, r, fill, (214, 170, 92) if on else e.get('tint', (196, 172, 140)))
            if on:
                pygame.draw.rect(s, (232, 182, 72), r.inflate(-6, -6), 2, border_radius=6)
            lines = ui.wrap(e['name'], 'smallb', r.w - 14)[:2]
            plate = (r.centerx, r.y + ch // 2 - (24 if len(lines) > 1 else 16))
            pygame.draw.circle(s, (232, 220, 196) if not owned else (222, 232, 206), plate, min(36, ch // 3))
            ic = e['icon'](3)
            s.blit(ic, ic.get_rect(center=plate))
            for k, line in enumerate(lines):
                ui.blit_text(s, line, (r.centerx, r.bottom - 50 - (len(lines) - 1 - k) * 22), 'smallb', U.INK,
                             'center', maxw=r.w - 10)
            if owned:
                st = e.get('status', 'Owned')
                ui.blit_text(s, st, (r.centerx, r.bottom - 22), 'small', e.get('status_col', (96, 140, 80)), 'center',
                             maxw=r.w - 14)
            else:
                ok = self.coins >= e['price']
                txt = '{:,}'.format(e['price'])
                tw = ui.fonts['smallb'].size(txt)[0]
                U.coin(s, (r.centerx - tw // 2 - 6, r.bottom - 22), 8)
                ui.blit_text(s, txt, (r.centerx - tw // 2 + 6, r.bottom - 22), 'smallb',
                             U.INK if ok else (178, 150, 130), 'midleft')
            ui.hotspot(r, lambda k=e['id']: (picks.__setitem__(self.shop_tab, k), self.audio.play('ui', 0.4)))
        self._shop_pane(s, pane, next(e for e in entries if e['id'] == show),
                        show == picks[self.shop_tab])

    def _shop_pane(self, s, r, e, picked):
        """The detail card on the right of the shop."""
        ui = self.ui
        ui.tile(s, r, (252, 247, 234), (196, 172, 140))
        x0, cw = r.x + 22, r.w - 44
        plate = (r.centerx, r.y + 78)
        pygame.draw.circle(s, (236, 224, 200), plate, 58)
        pygame.draw.circle(s, (224, 208, 180), plate, 58, 3)
        ic = e['icon'](5)
        s.blit(ic, ic.get_rect(center=plate))
        y = r.y + 150
        ui.blit_text(s, e['name'], (r.centerx, y), 'h3', U.INK, 'midtop', maxw=cw)
        y += 38
        for line in ui.wrap(e['desc'], 'small', cw)[:5]:
            ui.blit_text(s, line, (x0, y), 'small', U.SOFT)
            y += 23
        if e.get('note'):
            y += 6
            for line in ui.wrap(e['note'], 'smallb', cw)[:2]:
                ui.blit_text(s, line, (x0, y), 'smallb', (96, 120, 140))
                y += 24
        for label, k, val in e.get('stats', ()):
            y += 6
            ui.blit_text(s, label, (x0, y), 'small', U.INK)
            ui.blit_text(s, val, (x0 + 88, y), 'small', U.SOFT, 'topright')
            bar = pygame.Rect(x0 + 100, y + 6, cw - 100, 12)
            pygame.draw.rect(s, (230, 218, 196), bar, border_radius=6)
            pygame.draw.rect(s, (126, 176, 112), (bar.x, bar.y, max(12, int(bar.w * min(1, k))), bar.h),
                             border_radius=6)
            y += 24
        # the buttons sit at the bottom of the card
        acts = list(e.get('acts', ()))
        by = r.bottom - 22 - 50
        if 'price' in e:
            self.price_button(s, (x0, by, cw, 50), e['price'], e['buy'])
            if self.coins < e['price']:
                ui.blit_text(s, '%s more coins' % '{:,}'.format(e['price'] - self.coins), (r.centerx, by - 14),
                             'small', (190, 120, 100), 'center')
            by -= 58 if not self.coins < e['price'] else 72
        elif not acts:
            ui.button(s, (x0, by, cw, 50), e.get('status', 'Owned'), None, enabled=False)
            by -= 58
        for label, act, style, en in reversed(acts):
            ui.button(s, (x0, by, cw, 46), label, act, style, enabled=en, font='bodyb')
            by -= 54

    def shop_tackle(self, s, body):
        items = [('rod', r) for r in RODS] + [('gear', g) for g in GEAR]
        top = max(r['range'] for r in RODS), max(r['arc'] for r in RODS)
        out = []
        for kind, it in items:
            e = dict(id=it['id'], name=it['name'], desc=it['desc'])
            if kind == 'rod':
                e['icon'] = lambda k, it=it: art.item_icon(it['id'], k, it['color'])
                e['stats'] = [('Range', it['range'] / top[0], '%d%%' % round(it['range'] * 100)),
                              ('Arc', it['arc'] / top[1], '%d' % it['arc'])]
                if it['id'] in self.rods:
                    if self.rod == it['id']:
                        e['status'] = 'Equipped'
                    else:
                        e['status'] = 'In your shed'
                        e['acts'] = [('Equip', lambda it=it: (setattr(self, 'rod', it['id']), self.audio.play('ui')),
                                      'primary', True)]
                else:
                    e['price'], e['buy'] = it['price'], (lambda it=it: self.buy('rod', it))
            else:
                e['icon'] = lambda k, it=it: art.item_icon(it['id'], k)
                if self.has(it['id']):
                    e['status'] = 'Owned'
                else:
                    e['price'], e['buy'] = it['price'], (lambda it=it: self.buy('gear', it))
            out.append(e)
        self.shop_catalog(s, body, out)

    def shop_bait(self, s, body):
        out = []
        for b in [b for b in BAITS if not b.get('merchant')]:
            have = self.worms() if b['id'] == 'worm' else self.baits.get(b['id'], 0)
            e = dict(id=b['id'], name=b['name'], desc=b['desc'], icon=lambda k, b=b: art.item_icon(b['id'], k),
                     tint=(150, 186, 200) if self.bait == b['id'] else (196, 172, 140))
            e['note'] = ('In the tin: %d  (it fills to %d each morning)' % (have, self.WORM_TIN)
                         if b['id'] == 'worm' else 'In your box: %d' % have)
            acts = []
            if b['pack']:
                acts.append(('Buy %d  for %d' % (b['pack'], b['price']), lambda b=b: self.buy('bait', b), 'gold',
                             self.coins >= b['price']))
            elif b['id'] == 'worm':
                acts.append(('Dig %d more  for %d' % (self.WORM_PACK, self.WORM_PRICE), self.buy_worms, 'gold',
                             self.coins >= self.WORM_PRICE))
            if self.bait == b['id']:
                e['status'] = 'On your hook'
            elif have > 0:
                acts.append(('Use it', lambda b=b: (setattr(self, 'bait', b['id']), self.audio.play('ui')),
                             'primary', True))
                e['status'], e['status_col'] = 'x%d in your box' % have, U.INK
            else:
                e['status'], e['status_col'] = 'None left', U.SOFT
            e['acts'] = acts
            out.append(e)
        self.shop_catalog(s, body, out)

    def shop_decor(self, s, body):
        out = []
        for d in DECOR:
            e = dict(id=d['id'], name=d['name'], desc=d['desc'], icon=lambda k, d=d: art.item_icon(d['id'], k))
            if self.has(d['id']):
                e['status'] = 'On the dock'
            else:
                e['price'], e['buy'] = d['price'], (lambda d=d: self.buy('decor', d))
            out.append(e)
        self.shop_catalog(s, body, out)

    def wagon_stock(self):
        """Four things for sale, picked once per wagon visit."""
        if self.wagon.get('day') != self.day:
            rng = random.Random(self.day * 31 + 7)
            cos = [('hat', h['id']) for h in HATS if h['price'] and not h.get('gift')] + \
                  [('cat', c['id']) for c in CAT_ITEMS if c['price'] and not c.get('gift')]
            rng.shuffle(cos)
            unowned = [c for c in cos if c[1] not in self.hats and c[1] not in self.cat_items]
            pick = (unowned + [c for c in cos if c not in unowned])[:2]
            self.wagon = dict(day=self.day, stock=[('bait', 'moon'), ('bait', 'storm')] + pick)
        return self.wagon['stock']

    def shop_wagon(self, s, body):
        ui = self.ui
        hdr = pygame.Rect(body.x, body.y, body.w, 64)
        pygame.draw.rect(s, (226, 240, 238), hdr, border_radius=14)
        pygame.draw.rect(s, (110, 160, 160), hdr, 2, border_radius=14)
        U.boat(s, (hdr.x + 44, hdr.centery + 4), 1.6)
        if not self.wagon_here():
            nxt = next(d for d in range(self.day + 1, self.day + 8) if almanac.dow(d) in WAGON_DAYS)
            ui.blit_text(s, "Wren's houseboat isn't on the lake right now.", (hdr.x + 90, hdr.y + 10), 'bodyb', U.INK)
            when = 'today' if (self.wagon_today() and self.minute < 360) else '%s (in %d day%s)' % (
                almanac.weekday(nxt), nxt - self.day, '' if nxt - self.day == 1 else 's')
            ui.blit_text(s, 'She visits on Tideday and Lanternday, 6 AM to 8 PM. Next visit: %s.' % when,
                         (hdr.x + 90, hdr.y + 36), 'small', U.SOFT)
            ui.blit_text(s, 'Wren sells special bait, hats and little outfits for Biscuit.', (body.centerx, body.y + 200),
                         'body', U.SOFT, 'center')
            return
        ui.blit_text(s, "Wren's Wagon", (hdr.x + 90, hdr.y + 8), 'h3', U.INK)
        ui.blit_text(s, '"Fresh from up the river! Have a look, have a look."', (hdr.x + 90, hdr.y + 36), 'small', U.SOFT)
        stock = list(self.wagon_stock())
        if not self.owns_boat():
            stock = [('boat', 'boat')] + stock[:3]
        out = []
        for kind, iid in stock:
            if kind == 'boat':
                it = BOAT

                def icon(k):
                    ic = pygame.Surface((16 * k, 16 * k), pygame.SRCALPHA)
                    U.rowboat(ic, (8 * k, 9 * k), 0.45 * k)
                    return ic
                e = dict(id='boat', name=it['name'], desc=it['desc'], icon=icon, price=it['price'],
                         buy=lambda it=it: self.buy('boat', it))
            elif kind == 'bait':
                it = BAIT_BY_ID[iid]
                e = dict(id=iid, name=it['name'], desc='%s  A pack of %d.' % (it['desc'], it['pack']),
                         icon=lambda k, iid=iid: art.item_icon(iid, k), price=it['price'],
                         buy=lambda it=it: self.buy('bait', it), note='In your box: %d' % self.baits.get(iid, 0))
            elif kind == 'hat':
                it = HAT_BY_ID[iid]
                e = dict(id='hat_' + iid, name=it['name'],
                         desc='A hat for you. Change outfits any time in the cabin wardrobe.',
                         icon=lambda k, iid=iid: art.item_icon('hat_' + iid, k))
                if it['id'] in self.hats:
                    e['status'] = 'Owned'
                else:
                    e['price'], e['buy'] = it['price'], (lambda it=it: self.buy('hat', it))
            else:
                it = CAT_BY_ID[iid]
                e = dict(id='cat_' + iid, name=it['name'],
                         desc='Something for Biscuit to wear. She pretends not to care.',
                         icon=lambda k, iid=iid: art.item_icon('cat_' + iid, k))
                if it['id'] in self.cat_items:
                    e['status'] = 'Owned'
                else:
                    e['price'], e['buy'] = it['price'], (lambda it=it: self.buy('cat', it))
            out.append(e)
        self.shop_catalog(s, pygame.Rect(body.x, body.y + 80, body.w, body.h - 80), out, cols=2)

    # ---------------- pause
    def draw_pause(self, s):
        ui = self.ui
        n = self.net
        extra = 168 if n.role == 'host' else 92 if n.online else 68
        rect = pygame.Rect(SW // 2 - 230, SH // 2 - (472 + extra) // 2, 460, 472 + extra)
        ui.panel(s, rect, radius=26)
        ui.blit_text(s, 'Taking a break', (rect.centerx, rect.y + 50), 'h1', U.INK, 'center')
        info = 'Day %d  -  %s, %s %d  -  %s coins' % (self.day, almanac.weekday(self.day),
                                                    SEASONS[self.season_of(self.day)], almanac.dow(self.day),
                                                    '{:,}'.format(self.coins))
        ui.blit_text(s, info, (rect.centerx, rect.y + 92), 'small', U.SOFT, 'center', maxw=rect.w - 40)
        pygame.draw.line(s, (226, 210, 184), (rect.x + 50, rect.y + 120), (rect.right - 50, rect.y + 120), 2)
        bx, bw = rect.x + 50, rect.w - 100
        y = rect.y + 146
        ui.button(s, (bx, y, bw, 58), 'Back to the lake', self.close_overlay, 'primary', font='h2', nav=True)
        y += 76
        ui.button(s, (bx, y, bw, 52), 'Options', lambda: self.open_options('pause'), nav=True)
        y += 68
        if n.role == 'host':
            ui.button(s, (bx, y, bw, 52), 'Close my lake to friends', self.stop_hosting, nav=True)
            y += 64
            st, code = n.online_state(), n.room_code()
            if code:
                ui.button(s, (bx, y, bw, 64), 'Copy room code', self.copy_room_code, nav=True, sub=code)
            elif st == 'working':
                ui.blit_text(s, 'Opening your lake to the internet' + '.' * (1 + int(self.t * 2) % 3),
                             (rect.centerx, y + 32), 'smallb', U.SOFT, 'center', maxw=bw)
            else:
                ui.button(s, (bx, y, bw, 52), 'Try again online' if st else 'Open to the internet',
                          self.go_online, nav=True)
            y += 76
            ui.blit_text(s, 'On your Wi-Fi:  %s' % self.my_address(), (rect.centerx, y), 'small', U.SOFT,
                         'center', maxw=bw)
            y += 28
            if self.my_vpn():
                ui.blit_text(s, 'On Radmin / VPN:  %s' % self.my_vpn(), (rect.centerx, y), 'small', U.SOFT,
                             'center', maxw=bw)
                y += 28
        elif n.role == 'guest':
            ui.button(s, (bx, y, bw, 52), "Leave %s's lake" % n.host_name, self.leave_lake, nav=True)
            ui.blit_text(s, 'Your own lake keeps its own calendar.', (rect.centerx, y + 64), 'small', U.SOFT,
                         'center', maxw=bw)
            y += 92
        else:
            ui.button(s, (bx, y, bw, 52), 'Open my lake to friends', lambda: self.open_to_friends(True), nav=True)
            y += 68
        ui.button(s, (bx, y, bw, 52), 'Save and return to title', self.quit_to_title, nav=True)
        y += 68
        ui.button(s, (bx, y, bw, 52), 'Save and quit', self.quit_game, 'rose', nav=True)
        if n.online:
            ui.blit_text(s, 'Friends are here, so the lake keeps going.', (rect.centerx, rect.bottom - 30),
                         'small', U.SOFT, 'center')
        else:
            ui.rich(s, [('key', 'Esc'), 'Resume'], (rect.centerx - 44, rect.bottom - 30), U.SOFT, False)

    # ---------------- together (online co-op)
    def day_speed(self):
        if NET_ARGS['speed']:
            return NET_ARGS['speed']
        return self.settings.get('speed', 1.0)

    def my_address(self):
        n = self.net
        ip = getattr(self, '_lan_ip', None) or netmod.lan_address()
        self._lan_ip = ip
        return ip if n.port == netmod.PORT else '%s:%d' % (ip, n.port)

    def my_vpn(self):
        """The address friends on Radmin VPN or Hamachi join at, or None."""
        if not hasattr(self, '_vpn_ip'):
            found = netmod.portmap.vpn_addresses()
            self._vpn_ip = found[0] if found else None
        ip = self._vpn_ip
        if not ip:
            return None
        return ip if self.net.port == netmod.PORT else '%s:%d' % (ip, self.net.port)

    def my_name(self):
        return self.net.clean_name(self.settings.get('mp_name', ''))

    def friend_scores(self):
        """Festival scores of friends fishing the same festival."""
        out = []
        for p in self.net.peers.values():
            v = p.get('v')
            if self.net.online and v and v['fest'] is not None:
                out.append((p['name'], v['fest']))
        return out

    def open_lobby(self):
        self.overlay = 'lobby'
        self.lobby_msg = ''
        self.net.listen_lan(True)
        self.audio.play('page', 0.6)

    def close_lobby(self):
        if self.net.role == 'joining':
            self.net.close()
        self.net.listen_lan(False)
        self.typing = None
        self.overlay = None
        self.save_settings()
        self.audio.play('page', 0.5)

    def host_lake(self, online=False):
        self.save_settings()
        err = self.net.host(self.my_name(), NET_ARGS['port'])
        if err:
            self.lobby_msg = err
            self.audio.play('sad', 0.5)
            return
        self.online_seen = None
        self.net.listen_lan(False)
        self.typing = None
        self.overlay = None
        self.start_game(self.has_save)
        self.add_chat('', 'Your lake is open. Friends on your Wi-Fi join at %s' % self.my_address(), SYS_C)
        if self.my_vpn():
            self.add_chat('', 'Friends on Radmin or a VPN join at %s' % self.my_vpn(), SYS_C)
        if online:
            self.go_online()
        else:
            self.toast('Your lake is open! Friends can join at %s' % self.my_address(), (110, 150, 190))

    def open_to_friends(self, online=False):
        err = self.net.host(self.my_name(), NET_ARGS['port'])
        if err:
            self.toast(err, (200, 120, 100))
            return
        self.online_seen = None
        self.overlay = None
        self.add_chat('', 'Your lake is open. Friends on your Wi-Fi join at %s' % self.my_address(), SYS_C)
        if self.my_vpn():
            self.add_chat('', 'Friends on Radmin or a VPN join at %s' % self.my_vpn(), SYS_C)
        if online:
            self.go_online()
        else:
            self.toast('Your lake is open! Friends can join at %s' % self.my_address(), (110, 150, 190))

    def go_online(self):
        """Host: ask the router to open the port, then hand out a room code (see on_online)."""
        if self.net.role != 'host':
            return
        self.online_seen = 'working'
        self.net.open_online()
        self.toast('Opening your lake to the internet...', (110, 150, 190))

    def on_online(self, st):
        n = self.net
        code = n.room_code()
        why = n.online_why()
        if code:
            copied = clip_put(code)
            self.add_chat('', 'Room code: %s   Friends paste it in Play together > Join.' % code, SYS_C)
            if st == 'open':
                self.toast('Your lake is online! Room code %s%s' % (code, '  (copied)' if copied else ''),
                           (110, 150, 190))
                self.audio.play('jingle1', 0.5)
            else:
                self.toast('Room code %s%s. Your router needs a hand first: see the chat.'
                           % (code, '  (copied)' if copied else ''), (200, 160, 90))
                self.add_chat('', why, SYS_C)
        else:
            self.toast("Your lake couldn't go online. See the chat for why.", (200, 120, 100))
            self.add_chat('', why or "Your lake couldn't go online.", SYS_C)
            self.add_chat('', 'Friends on your Wi-Fi can still join.', SYS_C)
            self.audio.play('sad', 0.5)

    def copy_room_code(self):
        code = self.net.room_code()
        if code and clip_put(code):
            self.toast('Room code copied. Send it to your friends!', (110, 150, 190))
        elif code:
            self.toast('Room code: %s' % code, (110, 150, 190))

    def paste_addr(self):
        txt = ' '.join(clip_get().split())
        if txt:
            self.settings['mp_addr'] = ''
            self.typing = 'mp_addr'
            self.type_text(txt)
            self.typing = None
        else:
            self.lobby_msg = 'Nothing to paste. Copy the room code your friend sent first.'

    def stop_hosting(self):
        self.net.close()
        self.mp_ready = False
        self.overlay = None
        self.toast('Your lake is quiet again.', (110, 150, 100))

    def join_lake(self, addr=None):
        if addr:
            self.settings['mp_addr'] = addr
        addr = self.settings.get('mp_addr', '').strip()
        self.typing = None
        if not addr:
            self.lobby_msg = 'Paste the room code your friend sent (it is in their pause menu).'
            return
        self.save_settings()
        err = self.net.join(addr, self.my_name())
        self.lobby_msg = err or ''
        self.audio.play('ui', 0.5)

    def leave_lake(self):
        self.net.close()
        self.end_visit()
        self.overlay = None
        self.toast('You row home to your own lake.', (110, 150, 100))

    def net_shutdown(self):
        if self.net.role == 'guest':
            self.net.close()
            self.end_visit()
        else:
            self.net.close()
        self.net.listen_lan(False)
        self.mp_ready = False

    def begin_visit(self, world):
        self.solo = dict(day=self.day, minute=self.minute, weather=self.weather, forecast=dict(self.forecast),
                         festival=json.loads(json.dumps(self.festival)) if self.festival else None)
        if isinstance(world, dict):
            self.on_world(world, snap=True)

    def end_visit(self):
        self.host_clock = None
        self.mp_ready = False
        self.visit_shore = None
        sv, self.solo = self.solo, None
        if not sv:
            return
        self.day, self.minute, self.weather = sv['day'], sv['minute'], sv['weather']
        self.forecast, self.festival = sv['forecast'], sv['festival']
        if self.request and self.request.get('day', 0) > self.day:
            self.request['day'] = self.day
        self.ensure_forecast()
        env = self.env
        env.minute, env.day, env.season, env.weather = self.minute, self.day, self.season_of(self.day), self.weather
        env.settle()
        self.save()

    def on_world(self, m, snap=False):
        try:
            day, minute = int(m['day']), float(m['minute'])
        except (KeyError, TypeError, ValueError):
            return
        if not (1 <= day < 10 ** 6 and 0 <= minute < 1440):
            return
        if m.get('weather') in WEATHERS:
            self.weather = m['weather']
        fc = m.get('forecast')
        if isinstance(fc, dict):
            self.forecast = {str(k): v for k, v in list(fc.items())[:10] if str(k).isdigit() and v in WEATHERS}
        if 'shore' in m:
            self.visit_shore = shoremod.from_summary(m['shore'])     # draw the host's shore, not yours
        rate = MINUTES_PER_SECOND * _num(m.get('speed'), 1.0, 0.2, 40.0) if m.get('run', True) else 0.0
        self.host_clock = [day * 1440 + minute, self.t, rate]
        if snap:
            self.jump_clock(day * 1440 + minute)
            self.env.weather = self.weather
            self.env.settle()

    def world_msg(self):
        return {'t': 'world', 'day': self.day, 'minute': round(self.minute, 2), 'weather': self.weather,
                'forecast': {k: v for k, v in self.forecast.items() if int(k) >= self.day - 1},
                'speed': self.day_speed(), 'run': self.rest_phase not in ('out', 'in'),
                'shore': shoremod.summary(self)}

    def guest_clock(self):
        hc = self.host_clock
        if hc is None or self.rest_phase in ('out', 'in'):
            return
        target = hc[0] + min(self.t - hc[1], 3.0) * hc[2]
        diff = target - (self.day * 1440 + self.minute)
        if 0 < diff <= 180:
            self.advance_time(diff)
        elif abs(diff) > 180:
            self.jump_clock(target)

    def jump_clock(self, target):
        old = self.day
        self.clock_jumps += 1
        self.day = max(1, int(target // 1440))
        self.minute = target - self.day * 1440
        env = self.env
        env.minute, env.day, env.season, env.weather = self.minute, self.day, self.season_of(self.day), self.weather
        env.settle()
        if self.day != old and self.minute >= 360:
            self.start_day()

    def begin_sleep(self):
        if self.overlay == 'catch' and self.card:
            self.keep_catch()
        if self.overlay == 'letter' and self.letter:
            self.queue.insert(0, ('letter', self.letter))
            self.letter = None
        self.overlay = None
        self.typing = None
        self.travel_to = None
        self.fishing.reset()
        self.release_holds()
        self.mp_ready = False
        self.rest_phase = 'out'

    def add_chat(self, who, text, color):
        self.chat.append([who, text, color, 14.0])
        self.chat = self.chat[-30:]

    def peer_color(self, pid):
        return actors.PEER_COLORS[pid % 4]

    def peer_view(self, st):
        """A friend's last state with every value checked, ready to draw."""
        bob = st.get('bob')
        if isinstance(bob, list) and len(bob) == 2:
            bob = (_num(bob[0], 300, 0, W), _num(bob[1], 300, 0, H))
        else:
            bob = None
        return dict(spot=st.get('spot') if st.get('spot') in SPOT_BY_ID else 'dock',
                    fs=st.get('fs') if st.get('fs') in FISH_STATES else 'idle',
                    rod=st.get('rod') if st.get('rod') in ROD_BY_ID else 'twig',
                    hat=st.get('hat') if st.get('hat') in HAT_BY_ID else 'straw',
                    ang=_num(st.get('ang'), -55, -180, 180), bend=_num(st.get('bend'), 0, 0, 1.2), bob=bob,
                    held=st.get('held') if st.get('held') in ALL_BY_ID else None,
                    rest=bool(st.get('rest')), away=bool(st.get('away')),
                    em=st.get('em') if st.get('em') in actors.EMOTES else None,
                    fest=_num(st.get('fest'), 0, 0, 99999) if st.get('fest') is not None else None,
                    place='town' if st.get('place') == 'town' else 'lake',
                    tx=_num(st.get('tx'), 60, 0, townmod.TOWN_W), face=-1 if st.get('face') == -1 else 1,
                    walk=bool(st.get('walk')), look=looks.decode(st.get('lk')))

    def my_state(self):
        f = self.fishing
        bob = f.fish_pos if (f.state == 'fight' and f.fish_pos) else f.bob
        return {'t': 'st', 'spot': self.spot, 'fs': f.state, 'rod': self.rod, 'hat': self.hat,
                'ang': round(f.angle, 1), 'bend': round(f.bend, 2),
                'bob': [round(bob[0], 1), round(bob[1], 1)] if bob else None,
                'held': f.catch['spec']['id'] if f.state == 'caught' and f.catch else None,
                'rest': self.mp_ready, 'fest': self.festival['best'] if self.festival_live() else None,
                'em': self.emote[0] if self.emote else None,
                'away': self.overlay is not None or self.typing == 'chat',
                'place': self.place, 'tx': round(self.town.x, 1), 'face': self.town.face,
                'walk': self.town.step > 0, 'lk': looks.encode(self.look)}

    def net_update(self, dt):
        if self.fishing.state not in ('fight', 'landing'):     # the chat is hidden while reeling
            for c in self.chat:
                c[3] -= dt
        if self.emote:
            self.emote[1] -= dt
            if self.emote[1] <= 0:
                self.emote = None
        n = self.net
        if n.role is None:
            return
        for ev in n.poll():
            self.net_event(ev)
        if n.role == 'host':
            st = n.online_state()
            if st != self.online_seen:
                self.online_seen = st
                if st not in (None, 'working'):
                    self.on_online(st)
        if not n.online or self.mode != 'play':
            return
        for pid, p in n.peers.items():
            v = self.peer_view(p.get('st') or {})
            old = p.get('v')
            if old and old['bob'] and v['bob'] and old['fs'] == v['fs']:
                k = min(1.0, dt * 12)
                v['bob'] = (old['bob'][0] + (v['bob'][0] - old['bob'][0]) * k,
                            old['bob'][1] + (v['bob'][1] - old['bob'][1]) * k)
            if v['rest'] and not (old and old['rest']) and p.get('st'):
                ready = 1 + sum(1 for q in n.peers.values() if q.get('v', {}).get('rest')) + int(self.mp_ready)
                if not self.mp_ready:
                    self.toast('%s is ready to rest (%d of %d). Press Z to rest too.'
                               % (p['name'], ready, len(n.peers) + 1), (120, 130, 200))
            p['v'] = v
        for pid, v, kind, x, y, sc in actors.peer_places(self):
            if v['rest'] and random.random() < dt * 0.7:
                self.world.zzz(x + 4, y - (26 if kind == 'dock' else 14))
        if self.mp_ready:
            if self.fishing.state not in ('idle',):
                self.mp_ready = False
                self.toast('You get back up to fish.', (150, 140, 130))
            elif random.random() < dt * 0.7:
                self.world.zzz(PLAYER_X + 4, DECK_Y - 26)
        self.net_send_t -= dt
        if self.net_send_t <= 0:
            self.net_send_t = 0.1
            n.send(self.my_state())
        if n.role == 'host':
            self.net_world_t -= dt
            if self.net_world_t <= 0:
                self.net_world_t = 1.0
                n.world = self.world_msg()
                n.send(dict(n.world))
            if (self.mp_ready and n.peers and self.rest_phase is None
                    and all(p.get('v', {}).get('rest') for p in n.peers.values())):
                n.send({'t': 'sleep'})
                self.begin_sleep()

    def net_event(self, ev):
        n = self.net
        kind = ev[0]
        if kind == 'welcome':
            self.lobby_msg = ''
            n.listen_lan(False)
            self.typing = None
            self.overlay = None
            if self.mode != 'play':
                self.start_game(self.has_save)
            self.begin_visit(ev[1].get('world'))
            self.toast("Welcome to %s's lake!" % n.host_name, (110, 150, 190))
            self.add_chat('', "You joined %s's lake as %s." % (n.host_name, n.name), SYS_C)
            self.net_send_t = 0
        elif kind == 'failed':
            self.lobby_msg = ev[1]
            self.audio.play('sad', 0.5)
        elif kind == 'lost':
            self.end_visit()
            self.toast(ev[1], (200, 120, 100))
            self.add_chat('', ev[1], SYS_C)
        elif kind == 'joined':
            self.toast('%s has come to the lake!' % ev[2], (110, 150, 190))
            self.add_chat('', '%s came to fish.' % ev[2], SYS_C)
            self.audio.play('jingle1', 0.5)
            self.net_world_t = 0
            coop.on_joined(self)
        elif kind == 'left':
            self.add_chat('', '%s headed home.' % ev[2], SYS_C)
            self.toast('%s headed home. See you soon!' % ev[2], (150, 140, 130))
        elif kind == 'chat':
            p = n.peers.get(ev[1])
            if p and ev[2].get('text'):
                self.add_chat(p['name'], ev[2]['text'], self.peer_color(ev[1]))
                self.audio.play('ui', 0.35)
        elif kind == 'catch':
            p, m = n.peers.get(ev[1]), ev[2]
            spec = ALL_BY_ID.get(m.get('fish'))
            if not p or not spec:
                return
            size = _num(m.get('size'), 0, 0, 999)
            if spec.get('junk'):
                text = '%s fished up %s.' % (p['name'], spec['name'].lower())
            else:
                mv = m.get('v') if m.get('v') in morphs.MORPH_BY_ID else None
                text = '%s caught a %s (%.1f cm)%s' % (p['name'], morphs.name(spec, mv), size,
                                                        '  - a new record!' if m.get('rec') else '')
            self.add_chat('', text, self.peer_color(ev[1]))
            if not spec.get('junk') and (spec['rarity'] >= 3 or mv):
                self.toast('%s landed a %s!' % (p['name'], morphs.name(spec, mv)),
                           morphs.MORPH_BY_ID[mv]['col'] if mv else RARITY_COLORS[spec['rarity']])
            for pid, v, kd, x, y, sc in actors.peer_places(self):
                if pid == ev[1]:
                    r = spec.get('rarity', 0)
                    self.world.sparkles(x + 6, y - 24, 8 + r * 4,
                                        RARITY_COLORS[r] if r >= 2 else (255, 240, 180))
        elif kind == 'gift':
            coop.on_gift(self, ev[1], ev[2])
        elif kind == 'race':
            coop.on_race(self, ev[1], ev[2])
        elif kind == 'exp':
            coop.on_exp(self, ev[1], ev[2])
        elif kind == 'world':
            self.on_world(ev[1])
        elif kind == 'sleep':
            self.begin_sleep()

    # typing (chat and the lobby's text fields)
    def type_text(self, txt):
        allowed = set(pixfont.GLYPHS)
        txt = ''.join(ch for ch in txt if ch in allowed or ch == ' ')
        if self.typing == 'chat':
            self.chat_text = (self.chat_text + txt)[:netmod.CHAT_MAX]
        elif self.typing in ('mp_name', 'mp_addr'):
            limit = netmod.NAME_MAX if self.typing == 'mp_name' else 60
            self.settings[self.typing] = (self.settings.get(self.typing, '') + txt)[:limit]

    def typing_key(self, k):
        t = self.typing
        if k == pygame.K_v and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.type_text(' '.join(clip_get().split()))
        elif k == pygame.K_BACKSPACE:
            if t == 'chat':
                self.chat_text = self.chat_text[:-1]
            else:
                self.settings[t] = self.settings.get(t, '')[:-1]
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if t == 'chat':
                text = self.net.clean_chat(self.chat_text)
                self.chat_text = ''
                self.typing = None
                if text and self.net.online:
                    self.net.send({'t': 'chat', 'text': text})
                    self.add_chat(self.net.name, text, (226, 196, 120))
            elif t == 'mp_addr':
                self.join_lake()
            else:
                self.typing = None
        elif k == pygame.K_ESCAPE:
            if t == 'chat':
                self.chat_text = ''
            self.typing = None
        elif k == pygame.K_TAB and t in ('mp_name', 'mp_addr') and self.overlay == 'lobby':
            self.typing = 'mp_addr' if t == 'mp_name' else 'mp_name'

    def start_typing(self, key):
        self.typing = key
        pygame.key.start_text_input()

    def text_field(self, s, rect, key, placeholder):
        ui = self.ui
        r = U.snap_rect(rect)
        on = self.typing == key
        s.blit(ui._frame(r.w, r.h, (255, 252, 244) if on else (244, 236, 220), U.BROWN if on else (170, 134, 100),
                         2), r)
        val = self.settings.get(key, '')
        if val:
            ui.blit_text(s, val, (r.x + 14, r.centery), 'bodyb', U.INK, 'midleft', maxw=r.w - 30)
        else:
            ui.blit_text(s, placeholder, (r.x + 14, r.centery), 'body', (170, 150, 136), 'midleft', maxw=r.w - 30)
        if on and (self.t * 2) % 2 < 1.3:
            cx = r.x + 14 + (min(ui.fonts['bodyb'].size(val)[0], r.w - 30) if val else 0)
            s.fill(U.INK, (U.snap(cx + 2), r.centery - 12, 2, 24))
        ui.hotspot(r, lambda: self.start_typing(key))

    def draw_lobby(self, s):
        ui = self.ui
        n = self.net
        rect = pygame.Rect(SW // 2 - 440, SH // 2 - 300, 880, 600)
        ui.panel(s, rect, radius=26)
        ui.blit_text(s, 'Play together', (rect.centerx, rect.y + 46), 'h1', U.INK, 'center')
        ui.blit_text(s, 'Fish the same lake with up to three friends. Everyone keeps their own save.',
                     (rect.centerx, rect.y + 90), 'small', U.SOFT, 'center', maxw=rect.w - 60)
        ui.blit_text(s, 'Your name', (rect.x + 60, rect.y + 144), 'bodyb', U.INK, 'midleft')
        self.text_field(s, (rect.x + 220, rect.y + 120, 380, 48), 'mp_name', 'Angler')
        pygame.draw.line(s, (226, 210, 184), (rect.x + 40, rect.y + 190), (rect.right - 40, rect.y + 190), 2)
        pygame.draw.line(s, (226, 210, 184), (rect.centerx, rect.y + 210), (rect.centerx, rect.y + 470), 2)
        # host
        lx, cw = rect.x + 50, rect.w // 2 - 90
        ui.blit_text(s, 'Host', (lx, rect.y + 208), 'h2', U.INK)
        yy = rect.y + 254
        for line in ui.wrap('Open your own lake. Friends anywhere join with a room code; friends on your Wi-Fi see '
                            'it in their list.', 'small', cw):
            ui.blit_text(s, line, (lx, yy), 'small', U.SOFT)
            yy += 24
        busy = n.role == 'joining'
        ui.button(s, (lx, rect.y + 326, cw, 56), 'Host online', lambda: self.host_lake(True), 'primary',
                  enabled=not busy, font='h3', nav=True)
        ui.button(s, (lx, rect.y + 394, cw, 46), 'Host on this Wi-Fi only', self.host_lake, enabled=not busy,
                  nav=True)
        ui.blit_text(s, 'Your Wi-Fi address:  %s' % self.my_address(), (lx, rect.y + 452), 'small', U.SOFT, maxw=cw)
        if self.my_vpn():
            ui.blit_text(s, 'Radmin / VPN address:  %s' % self.my_vpn(), (lx, rect.y + 476), 'small', U.SOFT, maxw=cw)
        # join
        rx = rect.centerx + 40
        rw = rect.right - 50 - rx
        ui.blit_text(s, 'Join', (rx, rect.y + 208), 'h2', U.INK)
        self.text_field(s, (rx, rect.y + 252, rw, 48), 'mp_addr', 'Room code or address')
        ui.button(s, (rx, rect.y + 308, 112, 44), 'Paste', self.paste_addr, enabled=not busy, nav=True)
        ui.button(s, (rx + 124, rect.y + 308, rw - 124, 44), 'Join', self.join_lake, 'primary',
                  enabled=not busy, font='h3', nav=True)
        ui.blit_text(s, 'Lakes on your Wi-Fi', (rx, rect.y + 368), 'smallb', U.SOFT)
        lakes = n.lan_lakes()[:2]
        for i, (ip, port, name, cnt) in enumerate(lakes):
            addr = ip if port == netmod.PORT else '%s:%d' % (ip, port)
            ui.button(s, (rx, rect.y + 394 + i * 50, rw, 42), "%s's lake   (%d/%d)" % (name, cnt, netmod.MAX_PLAYERS),
                      (lambda a=addr: self.join_lake(a)), enabled=not busy, nav=True)
        if not lakes:
            dots = '.' * (1 + int(self.t * 2) % 3)
            ui.blit_text(s, 'Looking on your network' + dots, (rx, rect.y + 400), 'small', (170, 150, 136))
        # status and back
        msg = self.lobby_msg
        if busy:
            msg = 'Connecting to %s%s' % (self.settings.get('mp_addr', ''), '.' * (1 + int(self.t * 3) % 3))
        if msg:
            ui.blit_text(s, msg, (rect.centerx, rect.y + 500), 'smallb', U.SOFT if busy else (176, 92, 88),
                         'center', maxw=rect.w - 60)
        ui.button(s, (rect.centerx - 120, rect.bottom - 70, 240, 50), 'Cancel' if busy else 'Back',
                  self.close_lobby, nav=True)

    def draw_name_tags(self, s):
        ui = self.ui
        if self.fishing.state in ('fight', 'landing'):
            return
        placed = []
        if self.place == 'town':
            tn = self.town
            for pid, v in tn.town_peers(self):
                p = self.net.peers.get(pid)
                if not p:
                    continue
                sx, sy = self.w2s(v['tx'] - tn.scroll, townmod.GROUND - 36)
                if v['em'] or v['away']:
                    sy -= 26
                w = ui.fonts['tiny'].size(p['name'])[0] + 20
                r = pygame.Rect(sx - w // 2, sy - 20, w, 20)
                while any(r.colliderect(q) for q in placed):
                    r.y -= 20
                placed.append(r)
                ui.blit_text(s, p['name'], (r.centerx, r.bottom), 'tiny', (255, 250, 236), 'midbottom',
                             outline=U.darken(self.peer_color(pid), 0.55))
            return
        for pid, v, kind, x, y, sc in actors.peer_places(self):
            p = self.net.peers.get(pid)
            if not p:
                continue
            sx, sy = self.w2s(x + 1, y - (36 if kind == 'dock' else int(14 * sc) + 14))
            if v['em'] or v['away']:
                sy -= 26
            w = ui.fonts['tiny'].size(p['name'])[0] + 20
            r = pygame.Rect(sx - w // 2, sy - 20, w, 20)
            while any(r.colliderect(q) for q in placed):
                r.y -= 20
            placed.append(r)
            ui.blit_text(s, p['name'], (r.centerx, r.bottom), 'tiny', (255, 250, 236), 'midbottom',
                         outline=U.darken(self.peer_color(pid), 0.55))

    def draw_friends(self, s, y):
        ui = self.ui
        n = self.net
        if self.fishing.state in ('fight', 'landing'):
            return
        rows = [(n.me, 'You', 'town' if self.place == 'town' else self.spot, self.mp_ready)]
        for pid, p in sorted(n.peers.items()):
            v = p.get('v') or {}
            rows.append((pid, p['name'], 'town' if v.get('place') == 'town' else v.get('spot', 'dock'),
                         v.get('rest', False)))
        w = 300
        r = ui.panel(s, (SW - 16 - w, y, w, 58 + 30 * len(rows) + 30), radius=18)
        head = 'Your lake' if n.role == 'host' else "%s's lake" % n.host_name
        ui.blit_text(s, head, (r.x + 18, r.y + 12), 'smallb', U.INK, maxw=w - 90)
        ui.blit_text(s, '%d/%d' % (len(rows), netmod.MAX_PLAYERS), (r.right - 18, r.y + 12), 'small', U.SOFT,
                     'topright')
        for i, (pid, name, spot, rest) in enumerate(rows):
            cy = r.y + 52 + i * 30
            pygame.draw.circle(s, self.peer_color(pid), (r.x + 26, cy), 7)
            pygame.draw.circle(s, U.darken(self.peer_color(pid), 0.35), (r.x + 26, cy), 7, 2)
            ui.blit_text(s, name, (r.x + 42, cy), 'smallb', U.INK, 'midleft', maxw=120)
            if rest:
                where, col = 'Resting  z z', (110, 116, 180)
            else:
                where, col = (SPOT_BY_ID[spot]['name'] if spot in SPOT_BY_ID else
                              'Fernwick' if spot == 'town' else ''), U.SOFT
            ui.blit_text(s, where, (r.right - 18, cy), 'small', col, 'midright', maxw=118)
        ui.rich(s, [('key', 'Enter'), 'chat   ', ('key', '1-4'), 'emotes'], (r.x + 18, r.bottom - 22), U.SOFT, False,
                pad=False)

    def draw_chat(self, s):
        ui = self.ui
        if self.mode != 'play' or self.overlay is not None:
            return
        open_ = self.typing == 'chat'
        if self.fishing.state in ('fight', 'landing') and not open_:
            return
        cw = 372
        top = getattr(self, '_hud_left', 110)
        limit = int(SH * 0.66)                       # the dock starts about here
        src = self.chat[-12:] if open_ else [c for c in self.chat[-8:] if c[3] > 0]
        rows = []
        for who, text, col, life in src:
            a = 255 if open_ else int(255 * max(0.0, min(1.0, life / 1.5)))
            prefix = who + ': ' if who else ''
            for j, ln in enumerate(ui.wrap(prefix + text, 'small', cw - 32)):
                rows.append((who if j == 0 else '', ln, col, a, bool(who)))
        input_h = 48 if open_ else 0
        room = max(0, (limit - input_h - top - 12) // 26)
        rows = rows[-room:] if room else []
        if not rows and not open_:
            return
        box = pygame.Rect(16, top, cw, 12 + 26 * len(rows) + input_h)
        ui.glass(s, box, 150 if open_ else 110, 16)
        for i, (who, ln, col, a, said) in enumerate(rows):
            yy = box.y + 6 + i * 26 + 13
            x = box.x + 16
            if who and ln.startswith(who + ':'):
                ui.blit_text(s, who + ':', (x, yy), 'smallb', col, 'midleft', alpha=a, outline=(30, 24, 34))
                x += ui.fonts['smallb'].size(who + ':')[0] + 8
                ln = ln[len(who) + 1:].lstrip()
                ui.blit_text(s, ln, (x, yy), 'small', (250, 244, 232), 'midleft', alpha=a, maxw=box.right - x - 10)
            else:
                c = (250, 244, 232) if said else U.lighten(col, 0.35)     # wrapped speech stays white
                ui.blit_text(s, ln, (x, yy), 'small', c, 'midleft', alpha=a, maxw=box.w - 26)
        if open_:
            r = pygame.Rect(box.x + 8, box.bottom - input_h + 4, box.w - 16, input_h - 12)
            pygame.draw.rect(s, (250, 244, 232), r, border_radius=8)
            pygame.draw.rect(s, (150, 112, 84), r, 2, border_radius=8)
            shown = self.chat_text + ('_' if (self.t * 2) % 2 < 1.3 else '')
            if self.chat_text:
                ui.blit_text(s, shown, (r.x + 12, r.centery), 'smallb', U.INK, 'midleft', maxw=r.w - 24)
            else:
                ui.blit_text(s, 'Say something...  Enter sends, Esc closes', (r.x + 12, r.centery), 'small',
                             (170, 150, 136), 'midleft', maxw=r.w - 24)

    # ---------------- options
    OPT_TABS = (('audio', 'Audio'), ('display', 'Display'), ('game', 'Gameplay'), ('controls', 'Controls'))

    def open_options(self, came_from):
        self.options_from = came_from
        self.overlay = 'options'
        self.audio.play('page', 0.6)

    def close_options(self):
        self.drag = None
        self.save_settings()
        self.overlay = 'pause' if self.options_from == 'pause' else None
        self.audio.play('page', 0.5)

    def opt_rows(self, tab):
        st = self.settings
        if tab == 'audio':
            return [('slider', 'master', 'Master volume', 'Everything at once'),
                    ('slider', 'music', 'Music', 'Kalimba and soft pads'),
                    ('slider', 'sfx', 'Sound effects', 'Splashes, reels and menus'),
                    ('slider', 'amb', 'Ambience', 'Water, rain, birds and crickets'),
                    ('slider', 'radio_vol', 'Radio', 'The stations: their music and the hosts')]
        if tab == 'display':
            sizes = ["%dx%d" % wh for wh in self.win_sizes]
            sharp = self.ui_sharp_sizes()
            ui_desc = ('HUD and menus, in %%. Sharpest: %s' % ', '.join(str(p) for p in sharp)) if sharp \
                else 'Size of the HUD and menus, in %'
            cur = tuple(st.get('window') or self.default_window())
            sizes = sizes[-3:]
            off = len(self.win_sizes) - len(sizes)
            win_i = len(sizes) if self.fullscreen else (self.win_sizes.index(cur) - off
                                                        if cur in self.win_sizes[off:] else -1)
            scl = st.get('scaling', 'auto')
            return [('choice', 'Window', 'Its size, or the full screen. F11 switches any time',
                     sizes + ['Full'], win_i, lambda i, o=off, n=len(sizes): self.pick_window(i, o, n), True),
                    ('choice', 'Pixel scaling', 'Sharp keeps every pixel crisp; Fill uses all the room',
                     ['Auto', 'Sharp', 'Fill'], SCALINGS.index(scl) if scl in SCALINGS else 0,
                     lambda i: self.set_opt('scaling', SCALINGS[i]), True),
                    ('choice', 'Interface size', ui_desc, [str(p) for p in UI_SCALES],
                     UI_SCALES.index(st['ui_scale']) if st['ui_scale'] in UI_SCALES else UI_SCALES.index(100),
                     lambda i: self.set_opt('ui_scale', UI_SCALES[i]), True),
                    ('choice', 'Frame rate', 'Screen matches your monitor, smooth and tear-free',
                     FPS_LABELS, FPS_CHOICES.index(st['fps']) if st['fps'] in FPS_CHOICES else 4,
                     lambda i: self.set_opt('fps', FPS_CHOICES[i]), True),
                    ('choice', 'Show frame rate', 'A small counter in the corner', ['Off', 'On'],
                     int(bool(st['show_fps'])), lambda i: self.set_opt('show_fps', bool(i)), True),
                    ('choice', 'Screen shake', 'When fish lunge, leap and splash down', ['Off', 'Gentle', 'Full'],
                     SHAKE_LEVELS.index(st['shake']) if st['shake'] in SHAKE_LEVELS else 2,
                     lambda i: self.set_opt('shake', SHAKE_LEVELS[i]), True),
                    ('choice', 'Camera zoom while fishing', 'Leans in on the bobber and the fight', ['Off', 'On'],
                     int(bool(st['zoom'])), lambda i: self.set_opt('zoom', bool(i)), True),
                    ('choice', 'Light effects', 'Sunbeams, glow and mist. Auto eases off on slow PCs',
                     ['Simple', 'Auto', 'Full'], FX_LEVELS.index(st.get('fx', 'auto')) if st.get('fx') in FX_LEVELS
                     else 1, lambda i: self.set_opt('fx', FX_LEVELS[i]), True)]
        if tab == 'game':
            return [('choice', 'Relaxed reeling', 'Wider arc, longer warnings, slower leaps', ['Off', 'On'],
                     int(self.assist()), lambda i: self.set_opt('assist', bool(i)), True),
                    ('choice', 'Day length', 'About %d, 12 or %d real minutes per day' % (
                        round(12 / DAY_SPEEDS[0]), round(12 / DAY_SPEEDS[2])), ['Slow', 'Normal', 'Quick'],
                     DAY_SPEEDS.index(st['speed']) if st['speed'] in DAY_SPEEDS else 1,
                     lambda i: self.set_opt('speed', DAY_SPEEDS[i]), True),
                    ('choice', 'Clock', 'How times are shown', ['12-hour', '24-hour'], int(bool(st['clock24'])),
                     lambda i: self.set_opt('clock24', bool(i)), True),
                    ('choice', 'HUD', 'Clean: one slim line each, icons for the day', ['Full', 'Calm', 'Compact',
                                                                                    'Clean'],
                     HUD_STYLES.index(self.hud_style()),
                     lambda i: self.set_opt('hud', HUD_STYLES[i]), True),
                    ('choice', 'Hints', 'Tips along the bottom of the screen', ['Off', 'On'],
                     int(bool(st['hints'])), lambda i: self.set_opt('hints', bool(i)), True),
                    ('choice', 'Pause in the background', 'Pauses when you switch to another window',
                     ['Off', 'On'], int(bool(st['bg_pause'])), lambda i: self.set_opt('bg_pause', bool(i)), True),
                    ('choice', 'First-day tips', 'A short walkthrough at the start of a new game',
                     ['Off', 'On'], int(bool(st.get('tutorial', True))),
                     lambda i: self.set_opt('tutorial', bool(i)), True),
                    ('choice', 'Controller rumble', 'Feel the nibbles, the bite and the line', ['Off', 'On'],
                     int(bool(st.get('rumble', True))), lambda i: self.set_opt('rumble', bool(i)), True)]
        return []

    def draw_options(self, s):
        ui = self.ui
        rect = pygame.Rect(SW // 2 - 430, SH // 2 - 310, 860, 620)
        ui.panel(s, rect, radius=26)
        self.panel_header(s, rect, 'Options')
        close = pygame.Rect(rect.right - 62, rect.y + 18, 44, 44)
        ui.button(s, close, 'X', self.close_options, font='h3')
        tab = self.opt_tab
        tx = rect.x + 40
        for tid, label in self.OPT_TABS:
            ui.button(s, (tx, rect.y + 94, 170, 44), label, lambda t=tid: self.set_opt_tab(t),
                      'tab_on' if tid == tab else 'tab', nav=True)
            tx += 182
        y = rect.y + 158
        if tab == 'controls':
            self.draw_controls(s, rect, y)
        else:
            rows = self.opt_rows(tab)
            cx_room = 440 - 56 - 12
            step = 47 if len(rows) > 7 else 54 if len(rows) > 6 else 58 if len(rows) > 5 else 68
            for row in rows:
                if row[0] == 'slider':
                    _, key, label, desc = row
                    enabled = True
                else:
                    _, label, desc, opts, idx, pick, enabled = row
                top = y + (step - 52) // 2
                ui.blit_text(s, label, (rect.x + 56, top), 'bodyb', U.INK if enabled else (160, 146, 132))
                ui.blit_text(s, desc, (rect.x + 56, top + 26), 'small', U.SOFT, maxw=cx_room)
                cx = rect.x + 440
                mid = y + step // 2 - 2
                if row[0] == 'slider':
                    v = self.settings.get(key, 0.5)
                    sr = pygame.Rect(cx + 12, mid - 14, 290, 28)
                    ui.slider(s, sr, v, active=bool(self.drag and self.drag[0] == key))
                    ui.blit_text(s, '%d%%' % round(v * 100), (rect.right - 56, mid), 'bodyb', U.INK, 'midright')
                    ui.hotspot(sr.inflate(24, 16), lambda k=key, r=sr: self.begin_drag(k, r))
                else:
                    ui.segment(s, (cx, mid - 20, rect.right - 56 - cx, 40), opts, idx, pick, enabled)
                y += step
                pygame.draw.line(s, (232, 220, 198), (rect.x + 56, y - 3), (rect.right - 56, y - 3), 1)
        by = rect.bottom - 76
        if tab != 'controls':
            ui.button(s, (rect.x + 56, by, 230, 50), 'Restore defaults', self.reset_tab, nav=True)
        ui.button(s, (rect.right - 56 - 200, by, 200, 50), 'Done', self.close_options, 'primary', nav=True)

    def draw_controls(self, s, rect, y):
        ui = self.ui
        pick = self.settings.get('prompts', 'auto')
        ui.blit_text(s, 'Button prompts', (rect.x + 56, y), 'bodyb', U.INK)
        pad = self.pad
        if pad and pad.connected:
            desc = '%s controller connected' % U.PAD_NAMES[pad.layout]
        else:
            desc = 'Auto shows a controller once you plug one in'
        ui.blit_text(s, desc, (rect.x + 56, y + 26), 'small', U.SOFT, maxw=250)
        cx = rect.x + 316
        ui.segment(s, (cx, y + 2, rect.right - 56 - cx, 40), PROMPT_LABELS, PROMPTS.index(pick),
                   lambda i: self.set_opt('prompts', PROMPTS[i]), True)
        y += 58
        pygame.draw.line(s, (232, 220, 198), (rect.x + 56, y - 6), (rect.right - 56, y - 6), 1)
        # the table: the controller's buttons when one is in use or picked, else the keyboard
        lay = pick if pick in ('xbox', 'ps', 'switch') else (pad.layout if pad and pad.connected and
                                                             pick == 'auto' else None)
        if lay:
            rows = ((('A',), 'Hold to wind up, let go to cast'),
                    (('STICK',), 'Aim, steer the reel, walk'),
                    (('A', 'RT'), 'Hook a bite, reel faster, leap'),
                    (('A', 'X', 'Y'), 'Keep / tank / release a catch'),
                    (('X',), 'Talk or go in (Fernwick)'),
                    (('Y', 'BACK'), 'Journal, calendar'),
                    (('LB', 'RB'), 'Change bait, the lanterns'),
                    (('LS', 'RS'), 'Lake map, Fernwick and back'),
                    (('STICK', 'A'), 'Move the pointer and click'),
                    (('B',), 'Back out of a window'),
                    (('START',), 'Pause, skip a cutscene'))
            half = (len(rows) + 1) // 2
            for i, (btns, what) in enumerate(rows):
                col, row = divmod(i, half)
                x = rect.x + 56 + col * 400
                yy = y + 18 + row * 50
                kx = x
                for b in btns:
                    kx = ui.padcap(s, b, (kx, yy), 'midleft', lay).right + 6
                ui.blit_text(s, what, (x + 4, yy + 24), 'small', U.SOFT, 'midleft')
            return
        self.draw_rebind(s, rect, y)
        return
        rows = ((('Hold Click', 'Space'), 'Wind up a cast, let go to throw'),
                (('Mouse', 'Left', 'Right'), 'Aim the cast'),
                (('Click',), 'Hook a bite (wait for a real one)'),
                (('Mouse', 'A', 'D'), 'Steer the golden arc while reeling'),
                (('Hold Click',), 'Reel faster (let go when it lunges)'),
                (('Click', 'Space'), 'Leap: when the rings meet'),
                (('Space', 'T', 'R'), 'Keep / tank / release a catch'),
                (('J', 'S', 'C', 'K'), 'Journal, shop, cabin, calendar'),
                (('Z',), 'Rest until morning (after dark)'),
                (('Tab',), 'Change bait'),
                (('B',), 'Lake map (once you have a rowboat)'),
                (('P', 'F12'), 'Photo mode / save a picture'),
                (('F11', 'M', 'Esc'), 'Fullscreen, music, pause'))
        half = (len(rows) + 1) // 2
        for i, (keys, what) in enumerate(rows):
            col, row = divmod(i, half)
            x = rect.x + 56 + col * 400
            yy = y + 18 + row * 50
            kx = x
            for k in keys:
                kx = ui.keycap(s, k, (kx, yy), 'midleft', pad=False).right + 6
            ui.blit_text(s, what, (x + 4, yy + 24), 'small', U.SOFT, 'midleft')

    def draw_rebind(self, s, rect, y):
        """Keyboard keys you can change: click one, then press the key you want."""
        ui = self.ui
        b = self.binds()
        acts = bindsmod.ACTIONS
        half = (len(acts) + 1) // 2
        for i, (a, name, _) in enumerate(acts):
            col, row = divmod(i, half)
            x = rect.x + 56 + col * 384
            yy = y + 2 + row * 35
            r = pygame.Rect(x - 8, yy - 1, 368, 33)
            waiting = getattr(self, 'rebinding', None) == a
            hov = r.collidepoint(ui.mouse)
            if waiting or hov:
                pygame.draw.rect(s, (252, 240, 214) if waiting else (246, 236, 216), r, border_radius=8)
            ui.blit_text(s, name, (x, yy + 15), 'small', U.INK, 'midleft')
            if waiting:
                ui.blit_text(s, 'Press a key...', (r.right - 10, yy + 15), 'smallb', (200, 120, 60), 'midright')
            else:
                k = b.key_of(a)
                kr = ui.keycap(s, bindsmod.key_label(k), (0, 0), 'midleft', pad=False, remap=False)
                kr.midright = (r.right - 10, yy + 15)
                pygame.draw.rect(s, (246, 236, 216) if hov else (250, 244, 232), kr.inflate(4, 4))
                ui.keycap(s, bindsmod.key_label(k), kr.topleft, 'topleft', pad=False, remap=False)
                if k != bindsmod.DEFAULT[a]:
                    pygame.draw.circle(s, (226, 150, 70), (kr.x - 10, kr.centery), 4)
            ui.hotspot(r, lambda a=a: self.rebind(a))
        ny = y + 2 + half * 35 + 6
        ui.blit_text(s, 'Click an action, then press its new key (Esc cancels). The mouse always works too.',
                     (rect.x + 56, ny), 'small', U.SOFT)
        by = rect.bottom - 76
        ui.button(s, (rect.x + 56, by, 230, 50), 'Default keys', self.reset_binds, nav=True,
                  enabled=b.changed())

    def pick_window(self, i, off, n):
        if i == n:
            self.set_fullscreen(True)
            self.audio.play('ui', 0.6)
            return
        if self.fullscreen:
            self.set_fullscreen(False)
        self.set_window_size(i + off)

    def set_opt_tab(self, t):
        self.opt_tab = t
        self.audio.play('ui', 0.5)

    def set_opt(self, key, value):
        self.settings[key] = value
        self.apply_settings()
        self.save_settings()
        self.audio.play('ui', 0.6)

    def reset_tab(self):
        keys = {'audio': ('master', 'music', 'sfx', 'amb', 'radio_vol'),
                'display': ('fps', 'show_fps', 'shake', 'zoom', 'ui_scale', 'fx', 'scaling'),
                'game': ('assist', 'speed', 'clock24', 'hud', 'hints', 'bg_pause', 'tutorial', 'rumble')}.get(self.opt_tab, ())
        for k in keys:
            self.settings[k] = DEFAULT_SETTINGS[k]
        if self.opt_tab == 'display' and self.fullscreen:
            self.set_fullscreen(False)
        self.apply_settings()
        self.save_settings()
        self.audio.play('ui', 0.6)

    def begin_drag(self, key, rect):
        self.drag = (key, pygame.Rect(rect))
        self.drag_to(self.ui.mouse)

    def drag_to(self, pos):
        key, r = self.drag
        v = max(0.0, min(1.0, (pos[0] - r.x) / r.w))
        self.settings[key] = round(v, 2)
        self.apply_settings()

    def end_drag(self):
        if self.drag:
            self.drag = None
            self.save_settings()
            self.audio.play('ui', 0.7)

    def toggle_assist(self):
        self.set_opt('assist', not self.assist())

    def adjust(self, key, d):
        self.set_opt(key, round(max(0.0, min(1.0, self.settings.get(key, 0.5) + d)), 2))

    def quit_to_title(self):
        self.save()
        self.place = 'lake'
        self.net_shutdown()
        self.release_holds()
        self.fishing.reset()
        self.overlay = None
        self.card = None
        self.mode = 'title'
        self.has_save = True
        self.fade = 1.0
        self.fade_dir = -1
        self.audio.play('page', 0.5)

    def quit_game(self):
        self.save()
        self.net_shutdown()
        self.running = False


# ---------------------------------------------------------------- headless tests
FOLK_KEYS = townmod.FOLK_ORDER


def run_shots(outdir):
    os.makedirs(outdir, exist_ok=True)
    g = Game()
    g.mode = 'play'
    g.fade = 0
    g.owned = [d['id'] for d in DECOR] + ['lantern']

    def shot(name):
        if not name.startswith('ui_toast'):
            g.toasts.clear()
        g.draw()
        pygame.image.save(g.screen, os.path.join(outdir, name + '.png'))
        print('shot', name)

    def set_time(minute, day, weather):
        g.minute, g.day, g.weather = minute, day, weather
        g.env.minute, g.env.day, g.env.season, g.env.weather = minute, day, g.season_of(day), weather
        g.env.settle()

    def tick(n, fishing=True):
        for _ in range(n):
            g.world.update(1 / 30, g.env, g)
            if fishing:
                g.fishing.update(1 / 30)
            g.update_camera(1 / 30)

    scenes = [
        ('dawn_spring', 372, 1, 'clear'), ('noon_summer', 720, 10, 'clear'), ('dusk_autumn', 1150, 17, 'cloudy'),
        ('night_summer', 1350, 12, 'clear'), ('rain_spring', 600, 3, 'rain'), ('fog_autumn', 400, 19, 'fog'),
        ('snow_winter', 660, 24, 'snow'), ('night_winter', 30, 26, 'clear'), ('rain_night', 1320, 5, 'rain'),
    ]
    for name, minute, day, weather in scenes:
        set_time(minute, day, weather)
        tick(40)
        shot(name)
    # gameplay states at dusk in summer, with a couple of bubble spots
    set_time(1120, 9, 'clear')
    g.world.spot_cd = 0
    tick(5)
    g.world.spot_cd = 0
    tick(30)
    f = g.fishing
    f.aim = -0.4
    f.press()
    tick(40)
    shot('state_charging')
    f.release()
    tick(60)
    f.catch = dict(spec=FISH_BY_ID['salmon'], size=60.0)
    f.bite_at = f.t + 0.01
    f.update(1 / 30)
    shot('state_bite')
    f.hook()
    mg = f.mg
    for i in range(150):
        g.bot_aim = mg.fa
        g.holding = (i // 20) % 2 == 0
        tick(1)
        if f.state != 'fight':
            break
    shot('state_fight')
    mg.warn = 0.4
    mg.lunge = 0
    tick(1)
    shot('state_warning')
    mg.warn = 0
    mg._start_leap()
    for _ in range(12):
        tick(1)
    mg.leap['r'] = 64
    tick(1)
    shot('state_leap')
    g.bot_aim = None
    g.on_catch(dict(spec=FISH_BY_ID['eel'], size=88.0))
    g.card['t'] = 1.0
    shot('ui_card')
    g.keep_catch()
    for fid in ('minnow', 'bluegill', 'koi', 'eel', 'carp', 'whiskers', 'axolotl', 'shiner', 'goldfish', 'tetra'):
        g.journal[fid] = {'count': 2, 'best': 30.0}
        g.basket.append(dict(id=fid, size=30.0, price=FISH_BY_ID[fid]['price']))
    g.overlay = 'journal'
    g.j_sel = 26
    shot('ui_journal')
    for tab in ('sell', 'tackle', 'bait', 'decor', 'wagon'):
        g.overlay = 'shop'
        g.shop_tab = tab
        g.coins = 700
        shot('ui_shop_%s' % tab)
    g.overlay = 'letter'
    g.letter = INTRO
    shot('ui_letter')
    g.letter = g.almanac_letter(1)
    shot('ui_almanac')
    g.overlay = 'pause'
    shot('ui_pause')
    g.overlay = 'options'
    g.options_from = 'pause'
    for tab in ('audio', 'display', 'game', 'controls'):
        g.opt_tab = tab
        shot('ui_options_%s' % tab)
    g.toast('Photo saved to screenshots folder.', (110, 130, 170))
    g.toasts[-1][1] = 2.0
    g.overlay = None
    shot('ui_toast_hud')
    g.toasts.clear()
    # cabin tank with a few fish, a trophy and badges
    g.tank = [dict(id=i, size=FISH_BY_ID[i]['size'][1] * 0.7) for i in
              ('koi', 'bluegill', 'axolotl', 'eel', 'minnow', 'sunpetal', 'perch')]
    g.trophies = ['Blossom Derby, year 1', 'Lantern Night, year 1']
    g.badges = ['first', 'night', 'big', 'tank', 'birthday']
    g.overlay = 'cabin'
    for _ in range(90):
        g.update(1 / 30)
    g.tank_sel = 2
    shot('ui_cabin')
    g.hats += ['bucket', 'frog', 'captain']
    g.hat = 'frog'
    g.cat_items += ['crown', 'bell']
    g.cat_item = 'crown'
    # the rowboat spots
    g.owned.append('boat')
    for spot, minute, day, weather in (('cove', 700, 10, 'clear'), ('cove', 420, 2, 'rain'), ('deep', 1150, 17, 'cloudy'),
                                       ('deep', 60, 26, 'clear'), ('creek', 480, 16, 'clear'),
                                       ('creek', 660, 24, 'snow')):
        g.overlay = None
        g.spot = spot
        set_time(minute, day, weather)
        tick(40)
        shot('spot_%s_%s' % (spot, g.env.phase))
    g.spot = 'cove'
    set_time(700, 10, 'clear')
    tick(5)
    g.overlay = 'map'
    g.map_sel = 'deep'
    g.journal['tench'] = {'count': 1, 'best': 40.0}
    shot('ui_map')
    g.overlay = 'journal'
    g.j_page = 1
    g.j_sel = FISH.index(FISH_BY_ID['tench'])
    shot('ui_journal_rowboat')
    g.j_page = 0
    g.j_tab = 'badges'
    shot('ui_badges')
    g.j_tab = 'fish'
    g.overlay = None
    g.spot = 'dock'
    tick(2)
    g.owned.remove('boat')
    g.wagon = {}
    set_time(700, 2, 'clear')
    g.overlay = 'shop'
    g.shop_tab = 'wagon'
    shot('ui_shop_wagon_boat')
    g.overlay = None
    g.owned += ['bench', 'rowboat', 'gnome']
    set_time(700, 9, 'clear')
    tick(5)
    g.cabin_tab = 'wardrobe'
    shot('ui_wardrobe')
    g.overlay = 'journal'
    g.j_tab = 'badges'
    shot('ui_badges')
    # calendar on a festival week, then the dock with every outfit and decoration
    g.overlay = None
    g.cabin_tab = 'tank'
    g.queue.clear()
    g.fishing.reset()
    g.request = None
    set_time(400, 9, 'clear')
    g.start_day()
    g.queue.clear()
    g.overlay = 'calendar'
    g.cal_off, g.cal_sel = 0, 11
    shot('ui_calendar')
    g.overlay = None
    set_time(560, 9, 'clear')
    tick(30)
    shot('state_wagon_dressed')
    # summer Lantern Night (day 11 is Feastday of summer) with fireworks
    g.festival = None
    set_time(1210, 11, 'clear')
    g.ensure_festival()
    g.festival['best'] = 3
    tick(60)
    for _ in range(200):
        tick(1)
        if sum(1 for p_ in g.world.particles if p_['kind'] == 'fw') > 60:
            break
    tick(6)
    shot('state_lantern_night')
    g.festival['best'] = 999
    g.finish_festival()
    shot('ui_festival_result')
    g.overlay = None
    g.queue.clear()
    # spring Blossom Derby at noon (day 4)
    g.festival = None
    set_time(700, 4, 'clear')
    g.ensure_festival()
    tick(30)
    shot('state_festival')
    # Starday meteor shower
    g.festival = None
    set_time(1300, 7, 'clear')
    tick(120)
    shot('state_meteor')
    g.overlay = None
    g.mode = 'title'
    g.toasts.clear()
    g.has_save = True
    set_time(1150, 17, 'clear')
    tick(30, False)
    shot('ui_title')
    g.overlay = 'options'
    g.options_from = 'title'
    g.opt_tab = 'display'
    shot('ui_title_options')
    g.overlay = None
    g.overlay = 'slots'
    shot('ui_title_slots')
    g.overlay = None
    # together: friends on the dock, chat, the friends card, boats at the cove, the pause menu and the lobby
    g.mode = 'play'
    g.overlay = None
    g.typing = None
    g.toasts.clear()
    g.spot = 'dock'
    g.festival = None
    set_time(1000, 10, 'clear')
    n_ = g.net
    n_.role, n_.name = 'host', 'Rosie'
    n_.peers = {
        1: dict(name='Mira', st=dict(spot='dock', fs='waiting', rod='willow', hat='frog', ang=-48, bend=0.05,
                                     bob=[402.0, 296.0], em='heart')),
        2: dict(name='Juniper', st=dict(spot='dock', fs='caught', rod='twig', hat='beret', ang=-70, bend=0.0,
                                        held='perch')),
        3: dict(name='Pip', st=dict(spot='dock', fs='fight', rod='willow', hat='bucket', ang=-35, bend=0.7,
                                    bob=[470.0, 318.0])),
    }
    g.add_chat('', 'Your lake is open. Friends join at 192.168.1.20', SYS_C)
    g.add_chat('', 'Mira came to fish.', SYS_C)
    g.add_chat('Mira', 'the light on the water is so pretty right now', actors.PEER_COLORS[1])
    g.add_chat('', 'Juniper caught a Yellow Perch (21.4 cm)', actors.PEER_COLORS[2])
    g.emote = ['note', 2.5]
    tick(8)
    g.net_update(1 / 30)        # tick() skips Game.update, so build the friends' views here
    shot('mp_dock')
    g.typing, g.chat_text = 'chat', 'want to row over to the cove?'
    shot('mp_chat')
    g.typing, g.chat_text = None, ''
    for pid_ in n_.peers:
        n_.peers[pid_]['st']['spot'] = 'cove'
    n_.peers[1]['st']['rest'] = True
    n_.peers[1]['st']['em'] = None
    n_.peers[2]['st'].update(fs='waiting', held=None)
    g.spot = 'cove'
    set_time(1150, 10, 'clear')
    tick(20)
    g.net_update(1 / 30)
    shot('mp_cove')
    g.overlay = 'pause'
    shot('mp_pause')
    g.overlay = None
    n_.role, n_.peers = None, {}
    g.spot = 'dock'
    g.mode = 'title'
    g.settings['mp_name'], g.settings['mp_addr'] = 'Rosie', '192.168.1.31'
    n_.found = {('192.168.1.31', netmod.PORT): ('Mira', 2, time.time() + 60)}
    g.overlay = 'lobby'
    g.typing = 'mp_addr'
    tick(4, False)
    shot('mp_lobby')
    g.lobby_msg = 'That computer is not hosting a lake right now.'
    g.typing = None
    n_.found = {}
    shot('mp_lobby_error')
    g.overlay = None
    g.lobby_msg = ''
    # Fernwick: the street in different seasons and times, then every window you can open there
    g.mode = 'play'
    g.overlay = None
    g.place = 'town'
    g.chat = []
    g.emote = None
    tn = g.town

    def town_at(x, n=60):
        tn.x = float(x)
        tn.target = None
        tn.scroll = max(0.0, min(townmod.TOWN_W - W, x - W / 2))
        for _ in range(n):
            g.world.update(1 / 30, g.env, g)
            tn.update(1 / 30, g, 0)
            tn.scroll = max(0.0, min(townmod.TOWN_W - W, x - W / 2))
    g.coins = 1240
    g.basket = [dict(id=i, size=sz, price=pr) for i, sz, pr in (
        ('perch', 22.0, 14), ('perch', 25.0, 16), ('bluegill', 14.0, 10), ('trout', 41.0, 40), ('boot', 28.0, 2),
        ('sunfish', 18.0, 22), ('catfish', 60.0, 55), ('minnow', 6.0, 4))]
    for fid in ('minnow', 'perch', 'bluegill', 'trout', 'sunfish', 'carp', 'pike', 'catfish'):
        g.journal.setdefault(fid, {'count': 1, 'best': 10})
    g.museum = ['minnow', 'carp', 'pike', 'loach'] if 'loach' in FISH_BY_ID else ['minnow', 'carp', 'pike']
    g.friends = {'mabel': 34, 'pip': 62, 'juniper': 18, 'tom': 100}
    g.tickets = 23
    for name, x, minute, day, weather, proj in (
            ('town_spring', 420, 600, 2, 'clear', []),
            ('town_square_summer', 720, 1110, 10, 'clear', ['flowers', 'lamps', 'bandstand']),
            ('town_hall_autumn_rain', 1200, 800, 16, 'rain', ['flowers']),
            ('town_winter_night', 1000, 1300, 23, 'snow', ['flowers', 'lamps']),
            ('town_east_fog', 1700, 420, 18, 'fog', []),
            ('town_west_dusk', 160, 1160, 4, 'clear', ['lamps'])):
        g.projects = proj
        set_time(minute, day, weather)
        town_at(x, 90)
        shot(name)
    g.projects = ['flowers', 'lamps', 'bandstand']
    set_time(660, 9, 'clear')
    g.buffs = {'tea': 9, 'pie': 9}
    town_at(404, 20)
    tn.folk['mabel']['x'] = 380.0
    shot('town_hud')
    n_ = g.net
    n_.role, n_.name = 'host', 'Rosie'
    n_.peers = {1: dict(name='Mira', st=dict(place='town', tx=470.0, face=-1, walk=True, hat='party', em='heart')),
                2: dict(name='Juniper', st=dict(place='town', tx=520.0, face=1, walk=False, hat='beret')),
                3: dict(name='Pip', st=dict(place='lake', spot='dock', hat='bucket'))}
    g.net_update(1 / 30)
    shot('town_mp')
    n_.role, n_.peers = None, {}
    for ov in ('bakery', 'museum', 'board', 'hall', 'library'):
        g.overlay = ov
        shot('town_' + ov)
    tn.bake_tab, g.recipes, g.overlay = 'recipes', ['grilled', 'stew'], 'bakery'
    shot('town_bakery_recipes')
    tn.hall_tab, g.upgrades, g.overlay = 'home', ['stove'], 'hall'
    shot('town_hall_home')
    tn.bake_tab, tn.hall_tab = 'treats', 'town'
    g.pantry = {'fritters': 2, 'tart': 1}
    g.overlay = 'ringtoss'
    tn.rt.update(rings=3, t=1.0, fly=None, marks=[(-0.02, True), (0.37, False)], won=3, msg='Ringer! +3 tickets',
                 speed=2.0)
    shot('town_ringtoss')
    tn.open_talk(g, 'pip')
    shot('town_talk')
    tn.gift_mode = True
    shot('town_talk_gift')
    g.overlay = None
    tn.talk_to = None
    g.place = 'lake'
    g.projects = []
    g.buffs = {}
    set_time(700, 9, 'clear')
    tick(10)
    shot('town_lake_toolbar')
    # cooking: the kitchen, selling dishes, the lighthouse by night and day
    g.basket = [dict(id=i, size=sz, price=pr) for i, sz, pr in (
        ('perch', 22.0, 14), ('perch', 25.0, 16), ('minnow', 6.0, 4), ('trout', 41.0, 40), ('catfish', 60.0, 55),
        ('clam', 10.0, 60), ('bluegill', 12.0, 9))]
    g.recipes, g.upgrades = ['grilled', 'stew', 'clam'], ['stove', 'icebox']
    g.pantry = {'fritters': 2, 'tart': 1, 'stew': 2}
    g.meal = {'id': 'chowder', 'day': g.day}
    g.cabin_tab, g.overlay = 'kitchen', 'cabin'
    shot('cook_kitchen')
    g.shop_tab, g.overlay = 'sell', 'shop'
    shot('cook_shop_sell')
    # the cooking scene, step by step
    crng = random.Random(3)

    def cook_until(rid, cond, scores=None, first=False, auto=True, limit=2400):
        if g.cooking is None:
            g.basket = [dict(id=i, size=10.0, price=20) for i in
                        ('trout', 'perch', 'perch', 'minnow', 'catfish', 'clam', 'sunfish', 'bluegill', 'pike')]
            g.stats['cook_scenes'] = 0 if first else 5
            g.recipes = [r['id'] for r in kitchenmod.RECIPES if r['card']]
            g.start_cooking(rid)
        sc = g.cooking
        n = 0
        while not cond(sc) and n < limit and g.cooking is sc:
            if auto:
                sc.auto(1 / 30, crng, 0.9)
            if scores and sc.state == 'to_table':
                sc.scores.update(scores)
            sc.update(1 / 30)
            n += 1
        return sc

    set_time(1000, 9, 'clear')
    cook_until('grilled', lambda sc: sc.st_t > 4.2, first=True, auto=False)
    shot('cook_scene_intro_first')
    g.cooking.escape()
    cook_until('grilled', lambda sc: sc.st_t > 2.4, auto=False)
    shot('cook_scene_title')
    cook_until('grilled', lambda sc: sc.state == 'chop' and sc.ci == 2 and sc.st_t > 0 and sc.slam > 0.08)
    shot('cook_scene_chop')
    cook_until('grilled', lambda sc: sc.state == 'move_heat' and sc.st_t > 0.5)
    shot('cook_scene_walk')
    cook_until('grilled', lambda sc: sc.state == 'heat' and sc.heat_time > 3.4)
    shot('cook_scene_heat_pan')
    cook_until('grilled', lambda sc: sc.state == 'flip' and sc.brown > 0.55)
    shot('cook_scene_flip')
    cook_until('grilled', lambda sc: sc.flip is not None and sc.flip > 0.25)
    shot('cook_scene_flip_air')
    cook_until('grilled', lambda sc: sc.state == 'plate' and sc.st_t > 2.4, scores={'chop': 1, 'heat': 1, 'finish': 1})
    shot('cook_scene_plate3')
    g.cooking.finish_scene()
    set_time(1290, 9, 'clear')
    cook_until('chowder', lambda sc: sc.state == 'heat' and sc.heat_time > 2.5)
    sc = g.cooking
    sc.heat = min(1.0, sc.band()[0] + sc.band()[1] + 0.2)
    for _ in range(20):
        sc.holds.add('auto')
        sc.update(1 / 30)
    shot('cook_scene_heat_night_hot')
    cook_until('chowder', lambda sc: sc.state == 'season' and sc.sprinkled == 1 and sc.shaking > 0.2)
    shot('cook_scene_season')
    cook_until('chowder', lambda sc: sc.state == 'plate' and sc.st_t > 2.4, scores={'chop': 0.1, 'heat': 0.2, 'finish': 0})
    shot('cook_scene_burnt')
    g.cooking.finish_scene()
    set_time(1000, 9, 'clear')
    cook_until('tart', lambda sc: sc.state == 'oven' and sc.in_oven and sc.brown > 0.5)
    shot('cook_scene_oven')
    cook_until('tart', lambda sc: sc.state == 'oven' and sc.fin_q and sc.oven_open > 0.9)
    shot('cook_scene_oven_open')
    cook_until('tart', lambda sc: sc.state == 'plate' and sc.st_t > 2.4, scores={'chop': .7, 'heat': .6, 'finish': .7})
    shot('cook_scene_plate2')
    g.cooking.finish_scene()
    shot('cook_kitchen_after')
    g.overlay = None
    # heart scenes in Fernwick
    def scene_until(cond, limit=900):
        n = 0
        while g.scene is not None and not cond(g.scene) and n < limit:
            g.update(1 / 30)
            tn.scroll = max(0.0, min(townmod.TOWN_W - W, tn.x - W / 2))
            n += 1

    def beat(sc):
        return sc.beats[sc.i][0] if sc.i < len(sc.beats) else None

    def to_beat(kind, nth=1):
        seen = 0
        while g.scene is not None:
            sc = g.scene
            if beat(sc) == kind:
                seen += 1
                if seen >= nth:
                    break
            if beat(sc) in ('say', 'picture') or (beat(sc) == 'fade' and sc.fade_beat == 'hold'):
                sc.shown = len(sc.text)
                sc.bt = 2.0
                sc.press()
            else:
                scene_until(lambda sc, b=beat(sc), i=sc.i: sc.i != i, 400)

    g.place = 'town'
    g.heart_seen = []
    set_time(800, 9, 'clear')
    for k, x in (('mabel', 404), ('fen', 1702), ('librarian', 1512), ('tom', 226)):
        town_at(x - 30, 10)
        tn.folk[k]['x'] = float(x)
        g.friends[k] = 55
        tn.open_talk(g, k)
        if k == 'mabel':
            scene_until(lambda sc: beat(sc) == 'say' and sc.i >= 5 and sc.shown >= len(sc.text))
            to_beat('say', 2)
            scene_until(lambda sc: sc.shown >= len(sc.text))
            shot('heart_mabel_say')
            to_beat('picture')
            scene_until(lambda sc: sc.bt > 0.5)
            shot('heart_mabel_card')
        elif k == 'fen':
            to_beat('fade')
            scene_until(lambda sc: sc.fade_beat == 'hold')
            shot('heart_fen_fade')
            to_beat('picture')
            scene_until(lambda sc: sc.bt > 0.5)
            shot('heart_fen_portrait')
        elif k == 'librarian':
            to_beat('picture')
            scene_until(lambda sc: sc.bt > 0.5)
            shot('heart_alder_map')
        else:
            to_beat('picture')
            scene_until(lambda sc: sc.bt > 0.5)
            shot('heart_tom_photo')
        if g.scene:
            g.scene.skip()
    g.place = 'lake'
    # the lantern story
    g.story = story.new_state()
    g.story['started'] = True
    for fid in [f['id'] for f in FISH][:21]:
        g.journal.setdefault(fid, {'count': 1, 'best': 10})
    g.stats['perfect_dishes'] = 2
    g.friends = {k: 60 for k in townmod.FOLK}
    set_time(1000, 2, 'clear')
    g.overlay = 'lanterns'
    shot('story_lanterns')
    g.overlay = None
    set_time(1250, 3, 'clear')
    tick(20)
    shot('story_dock_ready')
    story.light(g, story.LANTERNS[0])
    to_beat('say', 2)
    scene_until(lambda sc: sc.shown >= len(sc.text))
    shot('story_light_dock')
    g.scene.skip()
    g.story['lit'] = ['dock', 'cove', 'deep', 'creek']
    set_time(1200, 28, 'clear')
    g.overlay, g.spot = None, 'dock'
    g.update(1 / 30)
    to_beat('wait', 1)
    scene_until(lambda sc: sc.bt > 3.0)
    shot('story_festival')
    to_beat('picture')
    scene_until(lambda sc: sc.bt > 0.5)
    shot('story_yearone')
    g.scene.skip()
    for _ in range(200):
        g.update(1 / 30)
    shot('story_after_festival')
    g.overlay = None
    g.story = story.new_state()
    g.festival_fx = None
    # Fernwick after dark: Mabel's cocoa cart and stargazing at the lookout
    g.place = 'town'
    g.overlay = None
    set_time(1300, 9, 'clear')
    tn.folk['mabel']['x'] = 712.0
    tn.folk['mabel']['goal'] = None
    town_at(690, 30)
    shot('night_cocoa_cart')
    g.overlay = 'cocoa'
    shot('night_cocoa_panel')
    g.overlay = None
    tn.folk['fen']['x'] = 1870.0
    town_at(1846, 5)
    g.town_day.pop('stars', None)
    tn.use_place(g, 'lookout')
    to_beat('picture')
    scene_until(lambda sc: sc.bt > 2.5, 200)
    shot('night_stars')
    to_beat('say')
    scene_until(lambda sc: sc.shown >= len(sc.text))
    shot('night_stars_fen')
    if g.scene:
        g.scene.skip()
    set_time(700, 9, 'clear')
    town_at(700, 5)
    shot('day_cart_folded')
    g.place = 'lake'
    g.overlay, g.cabin_tab = None, 'tank'
    g.projects = ['lighthouse']
    set_time(1300, 9, 'clear')
    tick(30)
    shot('cook_lighthouse_night')
    set_time(1000, 9, 'clear')
    tick(10)
    shot('cook_lighthouse_day')
    g.projects, g.upgrades, g.recipes, g.pantry, g.meal = [], [], [], {}, None
    # fish gallery
    gal = pygame.Surface((6 * 200, 6 * 110))
    gal.fill((240, 230, 210))
    from data import JUNK
    for i, f_ in enumerate(FISH + JUNK):
        spr = art.fish_sprite(f_, 4)
        gal.blit(spr, (i % 6 * 200 + 4, i // 6 * 110 + 6))
    pygame.image.save(gal, os.path.join(outdir, 'fish_gallery.png'))
    print('done')


def run_bot(seconds):
    """Auto-fish with a simple reeling policy to soak-test every state and report outcomes."""
    g = Game()
    g.mode = 'play'
    g.fade = 0
    rng = random.Random(1)
    stats = {'casts': 0, 'caught': 0, 'snap': 0, 'slip': 0, 'missed': 0, 'leaps': 0, 'perfect': 0, 'coins_ring': 0}
    orig_fail = g.fishing.fail

    def fail(text, sound='sad'):
        if 'Snap' in text:
            stats['snap'] += 1
        elif 'got away' in text:
            stats['slip'] += 1
        else:
            stats['missed'] += 1
        orig_fail(text, sound)
    g.fishing.fail = fail
    g.rod = 'willow'
    g.rods.append('willow')
    g.baits['storm'] = 20
    g.baits['moon'] = 10
    g.owned.append('boat')
    dt = 1 / 30
    t = 0
    frames = 0
    t0 = time.time()
    seen_events = set()
    nets = {'events': {}, 'sleeps': 0, 'max_drift': 0.0, 'catches_heard': 0}
    online = NET_ARGS['host'] or NET_ARGS['join']
    if online:
        g.settings['mp_name'] = NET_ARGS['name'] or ('Host' if NET_ARGS['host'] else 'Guest')
        orig_ev, orig_sleep = g.net_event, g.begin_sleep

        def count_event(ev):
            nets['events'][ev[0]] = nets['events'].get(ev[0], 0) + 1
            orig_ev(ev)
        g.net_event = count_event

        def count_sleep():
            nets['sleeps'] += 1
            orig_sleep()
        g.begin_sleep = count_sleep
        if NET_ARGS['host']:
            err = g.net.host(g.my_name(), NET_ARGS['port'], bind='127.0.0.1')
            assert err is None, err
        else:
            g.net.join(NET_ARGS['join'], g.my_name())
            g.mode = 'title'
            end = time.time() + 12
            while g.net.role != 'guest' and time.time() < end:
                g.update(dt)
                time.sleep(dt)
            assert g.net.role == 'guest', 'could not join: %s' % g.lobby_msg
            g.fade = 0
            g.overlay = None
            print('joined', g.net.host_name, 'as', g.net.name, 'host day', g.day, 'minute %.0f' % g.minute,
                  flush=True)
    # Fernwick: once a day the bot walks up to the village and does a round of everything there
    tb = {'day': None, 'need_plan': False, 'plan': [], 'acts': {}, 'visits': 0, 'tosses': 0, 'cook_day': None,
          'meals': 0, 'stars': [], 'scenes': []}

    def did(name):
        tb['acts'][name] = tb['acts'].get(name, 0) + 1

    def town_plan():
        tn = g.town

        def at(pid):
            def go():
                did(pid)
                tn.use_place(g, pid)
                ov = g.overlay
                if ov == 'cocoa':
                    g.buy_snack(rng.choice(townmod.NIGHT_SNACKS))
                elif ov == 'bakery':
                    g.buy_snack(rng.choice(townmod.SNACKS))
                    for r in kitchenmod.RECIPES:
                        if r['card'] and g.coins > r['card'] + 300:
                            g.learn_recipe(r)
                elif ov == 'board':
                    for job in g.town_jobs():
                        g.hand_in(job)
                elif ov == 'aquarium':
                    did('aquarium')                 # walked in: the tour runs in town_step
                elif ov == 'hall':
                    for pr in townmod.PROJECTS:
                        if g.coins > pr['cost'] + 300:
                            g.fund_project(pr)
                    for up in townmod.UPGRADES:
                        if g.coins > up['cost'] + 300:
                            g.fund_upgrade(up)
                elif ov == 'ringtoss':
                    tn.start_toss(g)
                elif ov == 'library':
                    tn.lib_page += 1
                elif ov == 'shop':
                    if rng.random() < 0.5:
                        g.sell_all()
                    for rid in list(g.pantry):
                        if g.pantry[rid] > 1:
                            g.sell_dish(rid)
                            did('sell_dish')
            return (townmod.PLACE_BY_ID[pid]['door'], go)

        def chat(k):
            def go():
                did('talk')
                tn.open_talk(g, k)
                if g.overlay == 'scene':
                    return
                if g.pantry and rng.random() < 0.4:
                    tn.give_dish(g, rng.choice(sorted(g.pantry)))
                    did('dish_gift')
                elif g.basket and rng.random() < 0.6:
                    tn.give(g, rng.choice(g.basket)['id'])
                    did('gift')
            return (tn.folk[k]['x'], go)
        plan = [at(pid) for pid in ('bakery', 'board', 'fountain', 'museum', 'hall', 'ringtoss', 'library',
                                    'lookout', 'tackle', 'cocoa')]
        plan += [chat(k) for k in FOLK_KEYS if tn.folk_here(k, g.minute)]
        rng.shuffle(plan)
        if stallmod.market_open(g) and stallmod.run(g) is None:
            plan.insert(0, at('stall'))           # Leafday: the market stall comes first
        return plan

    def town_step():
        tn = g.town
        if g.rest_phase is not None or g.place != 'town' or g.overlay == 'scene':
            return
        if tb['need_plan']:
            tb['need_plan'] = False
            tb['plan'] = town_plan()
            tb['visits'] += 1
        ov = g.overlay
        if ov == 'aquarium' and g.aqscene:
            g.aqscene.auto(dt, rng)              # a little tour: donate, look, sit, leave
            return
        if ov == 'stall':
            stallmod.auto(g, dt, rng)            # set out everything, sell the morning, pack up
            if g.overlay is None:
                did('stall')
            return
        if ov == 'ringtoss':
            rt = tn.rt
            if rt['rings'] > 0 and not rt['fly']:
                mx = tn.marker_x()
                if min(abs(mx - (-0.8 + i * 0.4)) for i in range(5)) < 0.04 or rng.random() < dt / 3:
                    g.key_down(pygame.K_SPACE)
                    tb['tosses'] += 1
            elif rt['rings'] == 0 and not rt['fly']:
                for pr in townmod.PRIZES:
                    tn.redeem(g, pr)
                g.overlay = None
            return
        if ov:
            g.overlay = None
            g.letter = None
            g.queue.clear()
            return
        if discover.busy(g):                    # Biscuit is onto something: follow her and look
            if discover.waiting(g) and tn.target is None:
                did('follow_biscuit')
                tn.walk_to(g.disc['x'] - 10, lambda: did('find') if discover.reveal(g) else None)
            return
        if tn.target is not None:
            return
        if not tb['plan'] or (clubmod.today(g) and g.minute >= 16 * 60 + 30):
            g.go_place('lake')                    # (home in time for the Angling Club on Lanternday)
            return
        x, act = tb['plan'].pop(0)
        tn.walk_to(x, act)

    while t < seconds:
        f = g.fishing
        in_town = g.place == 'town' or g.rest_phase in ('walk_out', 'walk_in')
        if g.overlay == 'scene' and g.scene:
            if g.scene is not tb.get('last_scene'):
                tb['last_scene'] = g.scene
                tb['scenes'].append(g.scene.title)
            g.scene.auto(dt)
        elif in_town:
            town_step()
        elif g.overlay in ('drive', 'area') and g.aqscene:
            key = 'drive_seen' if g.overlay == 'drive' else 'area_seen'
            if tb.get(key) is not g.aqscene:
                tb[key] = g.aqscene
                did(g.overlay + ('_' + g.aqscene.rid if g.overlay == 'drive' else '_' + g.aqscene.area))
            g.aqscene.auto(dt, rng)              # drive along stopping for everything; fish, chat, drive home
        elif g.overlay == 'truck':
            truckmod.bot_garage(g)
            for tab in ('map', 'garage', 'orders'):
                g.truck_tab = tab
                g.draw()
            g.overlay = None
        elif g.overlay == 'farshore' and g.aqscene:
            if tb.get('far_seen') is not g.aqscene:
                tb['far_seen'] = g.aqscene
                did('farshore')
            g.aqscene.auto(dt, rng)              # finds, Bramwell, the fire, the pool after dark
        elif g.overlay == 'harbour' and g.aqscene:
            if tb.get('hb_seen') is not g.aqscene:
                tb['hb_seen'] = g.aqscene
                did('harbour')
            g.aqscene.auto(dt, rng)              # a stroll round the quay: orders, Nell, chowder, Sol, the beach
        elif g.overlay == 'dungeon' and g.dungeon:
            if tb.get('dg_seen') is not g.dungeon:
                tb['dg_seen'] = g.dungeon
                did('dungeon')
            g.dungeon.auto(dt, rng, rng.uniform(0.6, 1.0))   # down the Drowned Stair: fish, gear up, camp or climb
        elif g.overlay == 'ice' and g.icescene:
            sc = g.icescene                       # ice fishing: jig, reel, and now and then get up and go
            sc.auto(dt, rng, rng.uniform(0.6, 1.0))
            if sc.state == 'jig' and rng.random() < dt / 90:
                sc.leave()
                did('ice_leave')
        elif g.overlay == 'catch':
            stats['caught'] += 1
            if g.card and g.card.get('v'):
                stats['morphs'] = stats.get('morphs', 0) + 1
            rr = rng.random()
            (g.keep_catch if rr < 0.7 else g.tank_catch if rr < 0.8 else g.release_catch)()
            if g.overlay == 'catch':      # tank was full or it was junk
                g.keep_catch()
        elif g.overlay and g.overlay != 'scene':
            g.overlay = None
            g.letter = None
            g.queue.clear()
        for kind, _, _ in almanac.events_on(g.day):
            seen_events.add(kind)
        if g.wagon_here() and rng.random() < 0.002:
            stock = g.wagon_stock()
            kind, iid = stock[rng.randrange(len(stock))]
            item = BAIT_BY_ID[iid] if kind == 'bait' else HAT_BY_ID[iid] if kind == 'hat' else CAT_BY_ID[iid]
            if kind == 'bait' or (iid not in g.hats and iid not in g.cat_items):
                g.buy(kind, item)
        for it in seasons.GEAR_ITEMS:                # seasonal gear, once there's money to spare
            if not g.has(it['id']) and g.coins > it['price'] + 400:
                g.buy('gear', it)
                did('buy_' + it['id'])
        if (g.place == 'lake' and g.spot == 'dock' and g.has('pot') and g.rest_phase is None
                and g.overlay is None and f.state == 'idle'):
            ps = seasons.pot_state(g)
            if (ps is None and g.minute >= 960) or seasons.pot_ready(g):
                did('pot_haul' if ps is not None else 'pot_set')
                seasons.pot_action(g)
        best = wildlife.best_candidate(g) if g.place == 'lake' and g.overlay is None else None
        if best and f.state in ('idle', 'waiting') and g.rest_phase is None:
            have = g.nature.get(best[1]['id'], {}).get('stars', 0)
            if best[0] > have and (best[0] == 3 or rng.random() < 0.02):
                g.hide_ui = True                     # out with the camera
                g.draw()
                wildlife.snap(g)
                tb.setdefault('snaps', []).append((best[1]['id'], best[0]))
                g.update(dt)
                g.draw()
                g.hide_ui = False
                did('photo')
        if g.critter:
            tb.setdefault('critters', set()).add(g.critter.id)
        for h in legends.HUNTS:                      # legend hunts: make the lure when we can, then use it
            if legends.can_craft(g, h) and g.coins > h['coins'] + 200:
                legends.craft(g, h)
                did('craft_lure')
            elif g.baits.get(h['lure'], 0) > 0 and g.bait != h['lure'] and rng.random() < 0.01:
                legends.equip(g, h)
        if online and g.net.online:
            if rng.random() < dt / 8:
                g.key_down(pygame.K_1 + rng.randrange(4))
            if rng.random() < dt / 25:
                g.net.send({'t': 'chat', 'text': 'bot says hi at %s' % fmt_clock(g.minute)})
            if g.net.peers and not coop.exp_live(g) and rng.random() < dt / 120:
                coop.start_exp(g)                   # an outing together
                did('exp_start')
            ex = g.exp
            if coop.exp_live(g) and all(coop.exp_goals(g)[:2]) and g.pantry and rng.random() < dt / 20 and                     coop.bring_dish(g, rng.choice(sorted(g.pantry))):
                did('exp_dish')
            if ex and ex.get('done') and not tb.get('exp_seen_%s' % ex.get('eid')):
                tb['exp_seen_%s' % ex.get('eid')] = True
                did('exp_feast')
            if (g.net.peers and not g.mp_ready and g.rest_phase is None and f.state == 'idle'
                    and (g.minute >= 1100 or g.minute < 300)):
                g.try_rest()
            if g.net.role == 'guest' and g.host_clock and g.rest_phase is None:
                hc = g.host_clock
                drift = hc[0] + min(g.t - hc[1], 3.0) * hc[2] - (g.day * 1440 + g.minute)
                nets['max_drift'] = max(nets['max_drift'], abs(drift))
        lan = story.current(g)
        if g.mp_ready or in_town or g.overlay == 'scene':
            pass
        elif (lan and g.rest_phase is None and f.state == 'idle' and g.overlay is None and story.awake(g, lan)
              and story.tasks_done(g, lan)):
            if g.spot != lan['spot']:            # row out to the lantern that's ready and light it
                g.travel(lan['spot'])
            else:
                story.light(g, lan)
        elif (g.rest_phase is None and f.state == 'idle' and g.overlay is None and g.minute >= 420
              and tb['cook_day'] != g.day):
            tb['cook_day'] = g.day             # morning in the cabin kitchen: cook what we can, eat one meal
            for r in kitchenmod.RECIPES:
                for _ in range(3):
                    if kitchenmod.known(g, r) and kitchenmod.ingredients(g, r)[0] is not None:
                        if not g.start_cooking(r['id']):
                            continue
                        sc, n = g.cooking, 0           # play the cooking scene through with a stand-in cook
                        while g.cooking is sc and n < 4000:
                            sc.auto(1 / 30, rng, rng.uniform(0.5, 0.95))
                            g.update(1 / 30)
                            if n % 9 == 0:
                                g.draw()
                            n += 1
                        tb['stars'].append(sc.result['stars'] if sc.result else -1)
                        g.overlay = None
            if g.pantry and not g.meal_today():
                kitchenmod.eat(g, rng.choice(sorted(g.pantry)))
                tb['meals'] += 1
            g.pet_cat()
            biscuit.give_treat(g)                 # Biscuit's day, and a bit of decorating
            if biscuit.toys(g):
                biscuit.play(g)
            g.update(1 / 30)                      # (the welcome quest notices the play)
            if g.goals['step'] == 3 and goalmod.mend_plank(g):
                did('mend_plank')
            if rng.random() < 0.5:
                g.radio.tune(rng.choice([None] + [st['id'] for st in radiomod.STATIONS]))
                did('radio')
                g.overlay = 'radio'
                g.draw()
                g.overlay = None
            if rng.random() < 0.4:
                gl = goalmod.all_goals(g)
                if gl:
                    goalmod.pin(g, rng.choice(gl)['id'] if rng.random() < 0.8 else g.goals['pinned'] or gl[0]['id'])
                    did('pin')
                g.overlay = 'goals'
                g.draw()
                g.overlay = None
            pick = rng.choice(homemod.CATALOGUE + homemod.mounts(g) + homemod.photos(g))
            if not homemod.owns(g, pick['id']) and g.coins > pick['price'] + 600:
                if pick['kind'] in ('wall', 'floor'):
                    g.home_sel = (pick['kind'], rng.randrange(4))
                homemod.choose(g, pick)
                did('furnish')
            gardenmod.harvest_all(g)              # the garden: pick, plant, water, compost, sell
            for i in range(g.garden['open']):
                if g.garden['beds'][i] is None:
                    c = rng.choice(gardenmod.seeds_now(g))
                    if g.coins > c['seed'] + 150 and gardenmod.plant(g, i, c['id']):
                        did('plant')
            if gardenmod.water_all(g):
                did('water')
            gardenmod.compost(g)
            for i in range(g.garden['open']):
                gardenmod.feed(g, i)
            if g.garden['open'] < gardenmod.BEDS and \
                    g.coins > gardenmod.BED_PRICES[g.garden['open'] - gardenmod.START_OPEN] + 800:
                gardenmod.open_bed(g)
                did('dig_bed')
            if gardenmod.give_catnip(g):
                did('catnip')
            if not g.garden['barrel'] and g.coins > gardenmod.BARREL_PRICE + 1000 and gardenmod.buy_barrel(g):
                did('barrel')
            while g.garden['produce'].get('corn', 0) > 1:
                gardenmod.corn_to_bait(g)
            for cid, n in list(g.garden['produce'].items()):
                if n > 4:
                    gardenmod.sell(g, cid)
            # the hatchery: collect young, start a pair from the basket, and make room when it fills
            for i in range(len(g.hatch['clutches']) - 1, -1, -1):
                if hatchery.collect(g, i):
                    did('hatch_collect')
            if not hatchery.pairs(g) and hatchery.room(g) >= 2 and len(g.hatch['clutches']) < hatchery.CLUTCHES:
                for sid, n in hatchery.basket_kinds(g):
                    if n >= 2:
                        hatchery.from_basket(g, sid)
                        hatchery.from_basket(g, sid)
                        did('hatch_pair')
                        break
            while hatchery.room(g) < 2 and g.hatch['pond']:
                pond = g.hatch['pond']
                i = min(range(len(pond)), key=lambda k: (pond[k]['v'] is not None, pond[k]['price']))
                (hatchery.sell if rng.random() < 0.6 else hatchery.release)(g, i)
                did('hatch_make_room')
            if g.shore['told']:                     # the shoreline projects, a step at a time
                for p in shoremod.PROJECTS:
                    if shoremod.can_do(g, p['id']) and g.coins > shoremod.next_step(g, p['id'])[1].get('coins', 0) + 200:
                        shoremod.do_step(g, p['id'])
                        did('shore_' + p['id'])
                shoremod.open_panel(g)
                g.draw()
            g.overlay = 'cabin'
            for tab in ('home', 'biscuit', 'tank', 'garden', 'hatchery'):
                g.cabin_tab = tab
                g.draw()
            g.overlay = None
        elif (g.rest_phase is None and f.state in ('idle', 'waiting') and g.overlay is None
              and (750 <= g.minute < 960 or stallmod.market_open(g) and 540 <= g.minute < 720 and (g.basket or g.pantry))
              and tb['day'] != g.day):
            tb['day'] = g.day
            tb['need_plan'] = True
            g.go_place('town')
        elif (g.rest_phase is None and f.state in ('idle', 'waiting') and g.overlay is None and g.spot == 'dock'
              and g.place == 'lake' and tb.get('dg_day') != g.day and 600 <= g.minute < 1080 and rng.random() < 0.01
              and not (clubmod.today(g) and g.minute >= 14 * 60)):
            tb['dg_day'] = g.day
            dungeon.open_stair(g)                 # down the stone steps under the hill
        elif (g.rest_phase is None and f.state in ('idle', 'waiting') and g.overlay is None and g.spot == 'dock'
              and g.place == 'lake' and g.truck['told'] and tb.get('truck_day') != g.day
              and 7 * 60 <= g.minute < 10 * 60):
            tb['truck_day'] = g.day
            g.fishing.reset()
            truckmod.open_(g)                     # a look in the shed: fix it up, buy things, the board
            did('truck_window')
        elif (g.rest_phase is None and f.state in ('idle', 'waiting') and g.overlay is None and g.spot == 'dock'
              and g.place == 'lake' and g.truck['fixed'] and tb.get('road_day') != g.day
              and (8 * 60 <= g.minute < 12 * 60 or 20 * 60 <= g.minute < 21 * 60) and not g.net.online):
            if truckmod.bot_trip(g, rng):          # off up one of the roads (the quarry after dark)
                tb['road_day'] = g.day
                did('road_trip')
        elif (g.rest_phase is None and f.state == 'idle' and g.overlay is None and g.spot == 'dock'
              and g.place == 'lake' and farmod.unlocked(g) and tb.get('far_day') != g.day
              and 19 * 60 + 40 <= g.minute < 22 * 60):
            tb['far_day'] = g.day
            farmod.go(g)                          # row across to the Far Shore for the evening
        elif (g.rest_phase is None and f.state == 'idle' and g.overlay is None and g.spot != 'dock'
              and g.place == 'lake' and farmod.unlocked(g) and tb.get('far_day') != g.day
              and tb.get('far_home') != g.day and 19 * 60 + 10 <= g.minute < 21 * 60):
            tb['far_home'] = g.day
            g.travel('dock')                      # head home to the dock first: the landing is across from it
        elif (g.rest_phase is None and f.state == 'idle' and g.overlay is None and g.spot == 'pier'
              and tb.get('hb_day') != g.day and 420 <= g.minute < 1140):
            tb['hb_day'] = g.day
            g.go_place('town')                    # up the steps into Saltmarsh
        elif g.rest_phase is None and f.state == 'idle' and g.overlay is None and rng.random() < 0.05:
            near = [sid for sid in coast.reachable(g) if sid != g.spot]
            if clubmod.today(g) and g.minute >= 15 * 60:   # Lanternday evening: stay on the lake for the club
                near = [sid for sid in near if sid in LAKE_SPOTS] or near
            g.travel(rng.choice(near))
            stats['trips'] = stats.get('trips', 0) + 1
        if g.rest_phase is not None or g.mp_ready or in_town or g.overlay in ('ice', 'harbour', 'dungeon', 'farshore'):
            pass
        elif f.state == 'idle':
            stats['casts'] += 1
            if g.bait == 'worm' and g.worms() <= 0:
                stats['empty_tin'] = stats.get('empty_tin', 0) + 1
                g.coins = max(g.coins, g.WORM_PRICE)
                g.buy_worms()                         # an empty tin: buy more
            f.aim = rng.uniform(-1, 1)
            if rng.random() < 0.1:
                g.cycle_bait()
            f.press()
            g.holding = True
        elif f.state == 'charging' and f.power > rng.uniform(0.4, 1.0):
            g.holding = False
            f.release()
        elif f.state == 'fly':
            k = int(f.t / seasons.FLY_BEAT + 0.5)          # tap near each beat, a little off sometimes
            if k >= 1 and abs(f.t - k * seasons.FLY_BEAT) < 0.05 and f.fly_beat == k - 1 \
                    and rng.random() < 0.5:
                f.press()
                did('fly_tap')
        elif f.state == 'waiting' and rng.random() < dt / 5:
            f.press()                                 # a tap: twitch the bobber
            f.release()
            stats['twitch'] = stats.get('twitch', 0) + 1
        elif f.state == 'bite' and f.t > 0.3:
            f.press()
        elif f.state == 'fight':
            mg = f.mg
            g.bot_aim = (mg.fa + rng.uniform(-15, 15)) % 360
            g.holding = mg.strain < 0.6 and mg.warn <= 0 and mg.lunge <= 0
            L = mg.leap
            if L and not L['done'] and abs(L['r'] - minigame.TARGET) < 8 and L['t'] > 0.2:
                stats['leaps'] += 1
                c0 = mg.perfects
                f.press()
                stats['perfect'] += mg.perfects - c0
            c_before = mg.coins
        g.update(dt)
        if f.state != 'fight':
            g.bot_aim = None
        if frames % 10 == 0:
            g.draw()
        frames += 1
        t += dt
        if online:
            lag = t0 + t - time.time()        # two games over a real network: keep to real time
            if lag > 0:
                time.sleep(lag)
            if not g.net.online and NET_ARGS['join']:
                break
    if online:
        print('net', g.net.role, 'me', g.net.name, 'peers', sorted(p['name'] for p in g.net.peers.values()),
              'events', nets['events'], 'sleeps', nets['sleeps'], 'clock jumps', g.clock_jumps,
              'max drift %.2f min' % nets['max_drift'], 'day', g.day, 'minute %.1f' % g.minute,
              'weather', g.weather, 'sent', g.net.sent, 'received', g.net.received, flush=True)
        solo_day = g.solo['day'] if g.solo else None
        g.net_shutdown()
        print('after leaving: day', g.day, 'weather', g.weather, '(own calendar was day %s)' % solo_day, flush=True)
    print('biscuit: bond', g.cat_bond, 'hearts', biscuit.level(g), 'gifts', g.stats.get('cat_gifts', 0), 'tricks',
          g.stats.get('tricks', 0), 'home', {k: v for k, v in g.home.items() if k != 'owned'}, 'owned',
          len(g.home['owned']), flush=True)
    print('seasons: owned', [x for x in ('pot', 'flyrod', 'auger') if g.has(x)], 'pots', g.stats.get('pots', 0),
          'ice fish', g.stats.get('ice_fish', 0), 'special caught',
          sorted(f['id'] for f in FISH if f.get('method') and f['id'] in g.journal), flush=True)
    print('garden:', 'beds open', g.garden['open'], 'beds', [(b['crop'], b['age']) if b else None
                                                         for b in g.garden['beds']],
          'produce', g.garden['produce'], 'food', g.garden['food'], 'planted', g.stats.get('planted', 0),
          'harvested', g.stats.get('harvested', 0), flush=True)
    print('hatchery:', 'pond', [(f['id'], f['v']) for f in g.hatch['pond']], 'clutches',
          [(c['id'], c['pv'], c['day']) for c in g.hatch['clutches']], 'raised', g.hatch['raised'],
          'found', {k: len(v) for k, v in g.hatch['found'].items()}, 'stock', g.hatch['stock'], flush=True)
    print('dungeon:', g.delve, 'lost', g.stats.get('delve_lost', 0), 'coins', g.stats.get('delve_coins', 0),
          flush=True)
    print('nature:', {k: v['stars'] for k, v in g.nature.items()}, 'seen', sorted(tb.get('critters', ())),
          'snaps', len(tb.get('snaps', [])), flush=True)
    print('legends:', {k: (v['stage'], v.get('clues'), v.get('day')) for k, v in g.hunts.items()},
          'lures made', g.stats.get('lures', 0), flush=True)
    cs = g.coast
    print('coast: open', cs['open'], 'river trips', g.stats.get('river', 0), 'harbour visits', cs['visits'],
          'orders', g.stats.get('coast_orders', 0), 'combed', g.stats.get('combed', 0), 'shells', len(cs['shells']),
          'glass', cs['glass'], 'light', cs['light'], cs['tasks'], 'ups', cs['ups'], 'chowder', cs['chowder'],
          'sea fish', coast.sea_known(g), 'friends', cs['friends'], flush=True)
    print('feedback 2.2: welcome step', g.goals['step'], 'pinned', g.goals['pinned'], 'boat', cs['boat'],
          'boat help', g.stats.get('boat_help', 0), 'round day', cs['round_day'], 'shells', cs['shells'],
          'radio', g.radio.station, 'host lines', len(g.radio.log), flush=True)
    print('story: lit', g.story['lit'], 'festival', g.story['festival'], 'heart scenes', g.heart_seen,
          'scenes played', tb['scenes'], flush=True)
    print('cook scenes', len(tb['stars']), 'stars', {k: tb['stars'].count(k) for k in (-1, 0, 1, 2, 3)},
          'best', g.cook_best, flush=True)
    print('kitchen: cooked', g.stats.get('cooked', 0), 'meals', tb['meals'], 'pantry', g.pantry, 'recipes',
          g.recipes, 'upgrades', g.upgrades, 'dish gifts', g.stats.get('dish_gifts', 0), flush=True)
    print('town visits', tb['visits'], 'acts', tb['acts'], 'tosses', tb['tosses'], 'tickets', g.tickets,
          'museum', len(g.museum), 'friends', g.friends, 'projects', g.projects, 'jobs done',
          g.stats.get('jobs', 0), 'wishes', g.stats.get('wishes', 0), 'place now', g.place, flush=True)
    el = time.time() - t0
    print('bot', stats, 'day', g.day, 'coins', g.coins, 'basket', len(g.basket),
          'journal', len(g.journal), 'tank', len(g.tank), 'badges', g.badges, 'gstats', g.stats,
          'hats', g.hats, 'cat', g.cat_items, 'events seen', sorted(seen_events),
          'trophies', g.trophies, 'spots fished', g.stats.get('spots'), 'visited', g.visited,
          'sim %.0fs in %.1fs real' % (seconds, el))


if __name__ == '__main__':
    if '--shots' in sys.argv:
        run_shots(sys.argv[sys.argv.index('--shots') + 1])
    elif '--bot' in sys.argv:
        run_bot(float(sys.argv[sys.argv.index('--bot') + 1]))
    else:
        Game().run()
