"""Lantern Lake launcher.

    LanternLake.exe                     the launcher: Play, update check, update pop-up
    LanternLake.exe --run-game [ARGS]   runs game\\main.py in this process (Play starts this)
    python launcher.py --root DIR       the same from source, pointed at an install folder

Install folder:
    LanternLake.exe, _internal\\        the launcher itself (built with PyInstaller)
    game\\                              the game's files, plus your saves, settings, screenshots and photos
    update.json                         where updates come from: {"github": "owner/repo"}

Updates are GitHub releases holding manifest.json and lantern-lake-game-<version>.zip. An update only ever
replaces the game's own files (the list in game\\version.json). Saves, settings, screenshots, photos and the
log are never written or removed, and a failed update puts every file back the way it was.
"""
import hashlib
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
LAUNCHER_VERSION = '1.0.0'
UA = 'LanternLakeLauncher/' + LAUNCHER_VERSION
FROZEN = getattr(sys, 'frozen', False)
W, H = 960, 540
MAX_MANIFEST = 256 * 1024
MAX_PAYLOAD = 200 * 1024 * 1024
TIMEOUT = 10


# ====================================================================== paths and small helpers
def resource(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def find_root(argv):
    if '--root' in argv:
        return os.path.abspath(argv[argv.index('--root') + 1])
    if FROZEN:
        return os.path.dirname(os.path.abspath(sys.executable))
    return None


def parse_version(v):
    nums = re.findall(r'\d+', str(v or ''))
    return tuple(int(n) for n in (nums + ['0', '0', '0'])[:3])


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def game_info(game_dir):
    info = read_json(os.path.join(game_dir, 'version.json'), {})
    return info if isinstance(info, dict) else {}


def fmt_mb(n):
    return '%.1f MB' % (n / 1048576.0) if n >= 104858 else '%d KB' % max(1, round(n / 1024.0))


class UpdateError(Exception):
    """A problem worth telling the player about, in plain words."""


class Cancelled(Exception):
    pass


# ====================================================================== where updates come from
GITHUB_RE = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')


def load_config(root):
    cfg = read_json(os.path.join(root, 'update.json'), {})
    return cfg if isinstance(cfg, dict) else {}


def github_repo(cfg):
    gh = str(cfg.get('github', '')).strip().strip('/')
    if gh.lower().startswith('https://github.com/'):
        gh = gh[len('https://github.com/'):].strip('/')
    if GITHUB_RE.match(gh) and 'OWNER' not in gh.upper().split('/')[0]:
        return gh
    return None


def manifest_source(cfg):
    if cfg.get('manifest'):
        return str(cfg['manifest'])
    gh = github_repo(cfg)
    if gh:
        return 'https://github.com/%s/releases/latest/download/manifest.json' % gh
    return None


def release_page(cfg):
    gh = github_repo(cfg)
    return 'https://github.com/%s/releases/latest' % gh if gh else None


def is_url(s):
    return bool(re.match(r'^https?://', s, re.I))


def open_source(src, timeout=TIMEOUT):
    """(stream, length or None) for an http(s) URL or a local file path (local paths are for testing)."""
    if is_url(src):
        req = urllib.request.Request(src, headers={'User-Agent': UA, 'Accept': 'application/octet-stream'})
        r = urllib.request.urlopen(req, timeout=timeout)
        n = r.headers.get('Content-Length')
        return r, (int(n) if n and n.isdigit() else None)
    f = open(src, 'rb')
    return f, os.path.getsize(src)


def fetch_manifest(src):
    try:
        stream, _ = open_source(src)
        with stream:
            raw = stream.read(MAX_MANIFEST + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UpdateError('No release has been published yet.')
        raise UpdateError('The update server answered with an error (%d).' % e.code)
    except (urllib.error.URLError, OSError):
        raise UpdateError("Couldn't reach the update server.")
    if len(raw) > MAX_MANIFEST:
        raise UpdateError('The update information looks wrong.')
    try:
        man = json.loads(raw.decode('utf-8-sig'))
    except ValueError:
        raise UpdateError('The update information looks wrong.')
    return check_manifest(man)


def check_manifest(man):
    ok = (isinstance(man, dict) and isinstance(man.get('version'), str) and isinstance(man.get('zip'), str)
          and re.match(r'^[A-Za-z0-9_.-]+\.zip$', man['zip'])
          and isinstance(man.get('sha256'), str) and re.match(r'^[0-9a-fA-F]{64}$', man['sha256'])
          and isinstance(man.get('size'), int) and 0 < man['size'] <= MAX_PAYLOAD)
    if not ok:
        raise UpdateError('The update information looks wrong.')
    notes = man.get('notes')
    man['notes'] = [str(n) for n in notes][:12] if isinstance(notes, list) else []
    return man


def asset_source(cfg, src, man):
    name = man['zip']
    gh = github_repo(cfg)
    if gh and not cfg.get('manifest') and isinstance(man.get('tag'), str) and man['tag']:
        return 'https://github.com/%s/releases/download/%s/%s' % (gh, urllib.parse.quote(man['tag']),
                                                                 urllib.parse.quote(name))
    if is_url(src):
        return urllib.parse.urljoin(src, urllib.parse.quote(name))
    return os.path.join(os.path.dirname(os.path.abspath(src)), name)


def download(src, dest, size, sha256, progress=None, cancel=None):
    """Downloads to dest and checks the size and the sha256. Raises UpdateError or Cancelled."""
    h = hashlib.sha256()
    got = 0
    try:
        stream, _ = open_source(src, timeout=20)
        with stream, open(dest, 'wb') as out:
            while True:
                if cancel and cancel():
                    raise Cancelled()
                chunk = stream.read(65536)
                if not chunk:
                    break
                got += len(chunk)
                if got > size:
                    raise UpdateError('The download was bigger than expected.')
                h.update(chunk)
                out.write(chunk)
                if progress:
                    progress(got, size)
    except urllib.error.HTTPError as e:
        raise UpdateError("Couldn't download the update (error %d)." % e.code)
    except (urllib.error.URLError, OSError) as e:
        if isinstance(e, (UpdateError, Cancelled)):
            raise
        raise UpdateError('The download was interrupted.')
    if got != size or h.hexdigest().lower() != sha256.lower():
        raise UpdateError("The download didn't check out, so it wasn't installed.")


# ====================================================================== installing an update
def clean_rel(name):
    """A safe relative path with forward slashes, or UpdateError."""
    n = name.replace('\\', '/')
    parts = [p for p in n.split('/') if p not in ('', '.')]
    if (not parts or n.startswith('/') or ':' in n or any(p == '..' for p in parts)
            or any(p.strip(' .') != p for p in parts)):
        raise UpdateError('The update has a file in the wrong place.')
    return '/'.join(parts)


def protected(rel):
    """Files that belong to the player. An update never writes or removes these."""
    r = rel.replace('\\', '/').lower()
    top = r.split('/')[0]
    base = r.rsplit('/', 1)[-1]
    return (top in ('screenshots', 'photos', '__pycache__') or base in ('settings.json', 'log.txt')
            or (base.startswith('save') and base.endswith('.json')) or base.endswith('.tmp'))


_fail_after = None     # tests: make install_zip fail after this many files, to check the rollback


def install_zip(zip_path, game_dir, tmp_dir, expect_version):
    stage = os.path.join(tmp_dir, 'new')
    backup = os.path.join(tmp_dir, 'old')
    for d in (stage, backup):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(stage)
    os.makedirs(backup)
    # 1. unpack into a staging folder, checking every name
    try:
        with zipfile.ZipFile(zip_path) as z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            if sum(i.file_size for i in infos) > MAX_PAYLOAD:
                raise UpdateError('The update is too big.')
            names = []
            for info in infos:
                rel = clean_rel(info.filename)
                if protected(rel):
                    raise UpdateError('The update tried to touch your saves, so it was stopped.')
                names.append(rel)
                dst = os.path.join(stage, *rel.split('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with z.open(info) as src, open(dst, 'wb') as out:
                    shutil.copyfileobj(src, out)
    except zipfile.BadZipFile:
        raise UpdateError('The update file is damaged.')
    info = read_json(os.path.join(stage, 'version.json'), {})
    files = info.get('files') if isinstance(info, dict) else None
    if not isinstance(files, list) or 'main.py' not in files or 'version.json' not in files:
        raise UpdateError('The update is missing some of its files.')
    files = [clean_rel(f) for f in files]
    if set(files) != set(names):
        raise UpdateError('The update is missing some of its files.')
    if parse_version(info.get('version')) != parse_version(expect_version):
        raise UpdateError("The update isn't the version it said it was.")
    old = game_info(game_dir).get('files')
    old_files = []
    for f in old if isinstance(old, list) else []:
        try:
            rel = clean_rel(str(f))
        except UpdateError:
            continue
        if not protected(rel) and rel not in files:
            old_files.append(rel)
    # 2. swap the files in, keeping the old ones until the end; version.json goes last
    done = []          # (path in game, backup path or None, made new?)
    order = sorted(f for f in files if f != 'version.json')
    try:
        for i, rel in enumerate(order + ['version.json']):
            if _fail_after is not None and i >= _fail_after:
                raise OSError('test failure')
            dst = os.path.join(game_dir, *rel.split('/'))
            bak = None
            if os.path.exists(dst):
                bak = os.path.join(backup, *rel.split('/'))
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                os.replace(dst, bak)
            done.append((dst, bak, True))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(stage, *rel.split('/')), dst)
        # files the old version had and the new one doesn't
        vj = done.pop()            # put version.json back on top after the stale files are gone
        for rel in old_files:
            dst = os.path.join(game_dir, *rel.split('/'))
            if os.path.isfile(dst):
                bak = os.path.join(backup, *rel.split('/'))
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                os.replace(dst, bak)
                done.append((dst, bak, False))
        done.append(vj)
    except BaseException:
        for dst, bak, made in reversed(done):
            try:
                if made and os.path.exists(dst):
                    os.remove(dst)
                if bak and os.path.exists(bak):
                    os.replace(bak, dst)
            except OSError:
                pass
        raise
    shutil.rmtree(os.path.join(game_dir, '__pycache__'), ignore_errors=True)
    for d in (stage, backup):
        shutil.rmtree(d, ignore_errors=True)


# ====================================================================== the update worker
class Updater:
    """Runs the check, the download and the install on a background thread; the window reads .state."""

    def __init__(self, root):
        self.root = root
        self.game = os.path.join(root, 'game')
        self.tmp = os.path.join(root, 'update_tmp')
        self.state = 'idle'
        self.manual = False
        self.man = None
        self.cfg = {}
        self.src = None
        self.error = ''
        self.got = 0
        self.total = 0
        self.cancel = False

    def busy(self):
        return self.state in ('checking', 'downloading', 'installing')

    def local_version(self):
        return game_info(self.game).get('version') or '0.0.0'

    def check(self, manual=False):
        if self.busy():
            return
        self.manual = manual
        self.state = 'checking'
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            self.cfg = load_config(self.root)
            self.src = manifest_source(self.cfg)
            if not self.src:
                self.state = 'noconfig'
                return
            man = fetch_manifest(self.src)
            if parse_version(man['version']) <= parse_version(self.local_version()):
                self.man = man
                self.state = 'uptodate'
            elif parse_version(man.get('min_launcher')) > parse_version(LAUNCHER_VERSION):
                self.man = man
                self.state = 'needs_launcher'
            else:
                self.man = man
                self.state = 'available'
        except UpdateError as e:
            self.error = str(e)
            self.state = 'offline'
        except Exception as e:  # never let a check crash the launcher
            self.error = "Couldn't check for updates (%s)." % type(e).__name__
            self.state = 'offline'

    def start_update(self):
        if self.busy() or not self.man:
            return
        self.cancel = False
        self.got, self.total = 0, self.man['size']
        self.state = 'downloading'
        threading.Thread(target=self._update, daemon=True).start()

    def _progress(self, got, total):
        self.got, self.total = got, total

    def _update(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        try:
            os.makedirs(self.tmp, exist_ok=True)
            zp = os.path.join(self.tmp, 'payload.zip')
            download(asset_source(self.cfg, self.src, self.man), zp, self.man['size'], self.man['sha256'],
                     self._progress, lambda: self.cancel)
            self.state = 'installing'
            install_zip(zp, self.game, self.tmp, self.man['version'])
            self.state = 'done'
        except Cancelled:
            self.state = 'cancelled'
        except UpdateError as e:
            self.error = str(e)
            self.state = 'failed'
        except Exception as e:
            self.error = 'Something went wrong while installing (%s).' % type(e).__name__
            self.state = 'failed'
        finally:
            shutil.rmtree(self.tmp, ignore_errors=True)


# ====================================================================== the window
CREAM = (250, 241, 224)
CREAM_D = (234, 220, 196)
BROWN = (112, 74, 58)
INK = (66, 44, 46)
WARM = (240, 150, 78)
WARM_L = (255, 196, 112)
NIGHT = (24, 22, 44)
GLOW = (255, 220, 150)


class Launcher:
    def __init__(self, root, demo=False):
        import pygame
        import lfont
        self.pg = pygame
        self.root = root
        self.demo = demo
        self.up = Updater(root)
        self.k = 1
        if not demo and sys.platform == 'win32':
            try:
                import ctypes
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.display.init()
        pygame.font.init() if hasattr(pygame, 'font') else None
        if not demo:
            try:
                dw, dh = pygame.display.get_desktop_sizes()[0]
                self.k = 2 if dw >= W * 3 and dh >= H * 3 else 1
            except Exception:
                self.k = 1
        pygame.display.set_caption('Lantern Lake')
        try:
            pygame.display.set_icon(pygame.image.load(resource('icon.png')))
        except Exception:
            pass
        self.window = pygame.display.set_mode((W * self.k, H * self.k))
        self.s = pygame.Surface((W, H))
        F = lfont.PixelFont
        self.f = {'title': F(7, True), 'h': F(3, True), 'hb': F(4, True), 'body': F(2), 'bodyb': F(2, True),
                  'play': F(5, True)}
        self._tc = {}
        try:
            self.banner = pygame.image.load(resource('banner.png')).convert()
        except Exception:
            self.banner = pygame.Surface((W, H))
            self.banner.fill((60, 50, 90))
        self.shade = self._make_shade()
        self.dot = self._make_glow(10, GLOW)
        rng = random.Random(4)
        self.flies = [[rng.uniform(0, W), rng.uniform(260, 520), rng.uniform(0, 6.3), rng.uniform(0.3, 0.8)]
                      for _ in range(16)]
        self.t = 0.0
        self.running = True
        self.popup = None
        self.seen = 'idle'
        self.buttons = []
        self.focus = None
        self.mouse = (-1, -1)
        self.launched = False
        self.auto = None
        self.check_at = 0.5
        self.pads = {}
        self.axis_held = 0
        try:
            import pygame._sdl2.controller as sdlc
            sdlc.init()
            self.sdlc = sdlc
        except Exception:
            self.sdlc = None
        pygame.joystick.init()

    # ------------------------------------------------------------ art helpers
    def _make_shade(self):
        pg = self.pg
        s = pg.Surface((W, H), pg.SRCALPHA)
        for y in range(H):
            a = 0
            if y > 300:
                a = int(min(1.0, (y - 300) / 200.0) ** 1.3 * 215)
            if y < 150:
                a = max(a, int((1 - y / 150.0) ** 2 * 120))
            pg.draw.line(s, (*NIGHT, a), (0, y), (W, y))
        return s

    def _make_glow(self, r, color):
        pg = self.pg
        s = pg.Surface((r * 2, r * 2), pg.SRCALPHA)
        for i in range(r, 0, -1):
            a = int(110 * (1 - i / r) ** 1.6) + 6
            pg.draw.circle(s, (*color, min(255, a)), (r, r), i)
        return s

    def text(self, s, txt, pos, font='body', color=INK, anchor='topleft', outline=None, shadow=None):
        key = (txt, font, color)
        img = self._tc.get(key)
        if img is None:
            if len(self._tc) > 600:
                self._tc.clear()
            img = self.f[font].render(txt, False, color)
            self._tc[key] = img
        r = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        px = self.f[font].px
        if outline:
            o = self.f[font].render(txt, False, outline)
            for dx, dy in ((-px, 0), (px, 0), (0, -px), (0, px), (-px, -px), (px, -px), (-px, px), (px, px)):
                s.blit(o, (r.x + dx, r.y + dy))
        if shadow:
            sh = self.f[font].render(txt, False, shadow)
            s.blit(sh, (r.x + px, r.y + px * (2 if outline else 1)))
        s.blit(img, r)
        return r

    def wrap(self, txt, font, width):
        out, cur = [], ''
        for w in str(txt).split():
            t = (cur + ' ' + w).strip()
            if not cur or self.f[font].size(t)[0] <= width:
                cur = t
            else:
                out.append(cur)
                cur = w
        if cur:
            out.append(cur)
        return out

    def panel(self, s, rect, fill, border=None, radius=14, width=3, shadow=True):
        pg = self.pg
        r = pg.Rect(rect)
        if shadow:
            sh = pg.Surface((r.w, r.h), pg.SRCALPHA)
            pg.draw.rect(sh, (10, 8, 20, 90), sh.get_rect(), border_radius=radius)
            s.blit(sh, (r.x + 4, r.y + 6))
        if len(fill) == 4:
            p = pg.Surface((r.w, r.h), pg.SRCALPHA)
            pg.draw.rect(p, fill, p.get_rect(), border_radius=radius)
            s.blit(p, r.topleft)
        else:
            pg.draw.rect(s, fill, r, border_radius=radius)
        if border:
            pg.draw.rect(s, border, r, width, border_radius=radius)
        return r

    def button(self, s, rect, key, label, action, style='normal', font='bodyb', enabled=True, sub=None):
        pg = self.pg
        r = pg.Rect(rect)
        if enabled:
            self.buttons.append((r, key, action))
        hot = enabled and (self.focus == key)
        lift = -2 if hot else 0
        rr = r.move(0, lift)
        if style == 'play':
            base = (WARM_L if hot else WARM) if enabled else (150, 130, 120)
            top = tuple(min(255, c + 30) for c in base)
            pg.draw.rect(s, (60, 30, 30), r.move(0, 5), border_radius=18)
            pg.draw.rect(s, base, rr, border_radius=18)
            pg.draw.rect(s, top, (rr.x + 6, rr.y + 5, rr.w - 12, rr.h // 2 - 4), border_radius=14)
            pg.draw.rect(s, (90, 44, 36), rr, 3, border_radius=18)
            if hot:
                pg.draw.rect(s, (255, 244, 214), rr.inflate(8, 8), 2, border_radius=22)
            self.text(s, label, (rr.centerx, rr.centery - (8 if sub else 0)), font, (255, 250, 238), 'center',
                      outline=(110, 52, 40))
            if sub:
                self.text(s, sub, (rr.centerx, rr.bottom - 14), 'body', (110, 52, 40), 'center')
            return r
        if style == 'primary':
            fill, edge, ink = ((WARM_L if hot else WARM), (110, 52, 40), (255, 250, 238))
        elif style == 'ghost':
            fill, edge, ink = ((255, 250, 238, 70 if hot else 36), (255, 236, 200) if hot else (200, 186, 200),
                               (255, 244, 224))
        else:
            fill, edge, ink = ((255, 250, 240) if hot else CREAM_D), BROWN, INK
        if not enabled:
            ink = (150, 140, 140)
        if len(fill) == 4:
            p = pg.Surface(rr.size, pg.SRCALPHA)
            pg.draw.rect(p, fill, p.get_rect(), border_radius=10)
            s.blit(p, rr.topleft)
        else:
            pg.draw.rect(s, (40, 26, 30), r.move(0, 3), border_radius=10)
            pg.draw.rect(s, fill, rr, border_radius=10)
        pg.draw.rect(s, edge, rr, 2, border_radius=10)
        self.text(s, label, rr.center, font, ink, 'center')
        return r

    # ------------------------------------------------------------ state
    def sync_popup(self):
        st = self.up.state
        if st == self.seen:
            return
        self.seen = st
        manual = self.up.manual
        pop = {'available': 'available', 'needs_launcher': 'needs_launcher', 'downloading': 'progress',
               'installing': 'progress', 'done': 'done', 'failed': 'failed'}.get(st)
        if st in ('uptodate', 'offline', 'noconfig') and manual:
            pop = st
        if st == 'cancelled':
            pop = None
        if pop or st in ('cancelled',):
            self.popup = pop
            self.focus = None
        if st in ('available', 'needs_launcher'):
            self.flash_taskbar()

    def status(self):
        st, up = self.up.state, self.up
        v = up.man['version'] if up.man else ''
        dots = '.' * (1 + int(self.t * 2) % 3)
        return {
            'idle': ('Checking for updates' + dots, (200, 200, 220)),
            'checking': ('Checking for updates' + dots, (200, 200, 220)),
            'uptodate': ('You have the newest version.', (150, 220, 150)),
            'available': ('Version %s is ready to install.' % v, WARM_L),
            'needs_launcher': ('Version %s needs a new launcher.' % v, WARM_L),
            'offline': ("Couldn't check for updates. You can still play.", (210, 196, 200)),
            'noconfig': ("Updates aren't set up yet.", (210, 196, 200)),
            'downloading': ('Downloading the update' + dots, WARM_L),
            'installing': ('Installing the update' + dots, WARM_L),
            'done': ('Updated to version %s.' % up.local_version(), (150, 220, 150)),
            'failed': ("The update didn't finish. Your game wasn't changed.", (240, 160, 150)),
            'cancelled': ('Update cancelled.', (210, 196, 200)),
        }.get(st, ('', INK))

    def flash_taskbar(self):
        if self.demo or sys.platform != 'win32':
            return
        try:
            if self.pg.key.get_focused():
                return
            import ctypes
            hwnd = self.pg.display.get_wm_info().get('window')

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint), ('hwnd', ctypes.c_void_p), ('dwFlags', ctypes.c_uint),
                            ('uCount', ctypes.c_uint), ('dwTimeout', ctypes.c_uint)]
            fi = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3 | 12, 0, 0)
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))
        except Exception:
            pass

    # ------------------------------------------------------------ actions
    def play(self):
        if self.up.state in ('downloading', 'installing'):
            return
        game = self.up.game
        if not os.path.isfile(os.path.join(game, 'main.py')):
            self.popup = 'missing'
            self.focus = None
            return
        if FROZEN:
            args = [sys.executable, '--run-game']
        else:
            args = [sys.executable, os.path.abspath(__file__), '--root', self.root, '--run-game']
        if self.demo:
            self.launched = True
            return
        subprocess.Popen(args, cwd=game, close_fds=True)
        self.launched = True

    def open_folder(self):
        try:
            os.startfile(self.up.game)
        except (OSError, AttributeError):
            pass

    def open_page(self):
        import webbrowser
        url = (self.up.man or {}).get('page') or release_page(self.up.cfg)
        if url and is_url(url):
            webbrowser.open(url)
        self.popup = None

    def close_popup(self):
        self.popup = None
        self.focus = None

    def cancel_update(self):
        self.up.cancel = True

    def back(self):
        if self.popup in ('progress',):
            if self.up.state == 'downloading':
                self.cancel_update()
            return
        if self.popup:
            self.close_popup()
        else:
            self.running = False

    # ------------------------------------------------------------ input
    def move_focus(self, d):
        keys = [b[1] for b in self.buttons]
        if not keys:
            return
        i = keys.index(self.focus) if self.focus in keys else -1
        self.focus = keys[(i + d) % len(keys)]

    def activate(self):
        for r, key, action in self.buttons:
            if key == self.focus:
                action()
                return

    def handle(self):
        pg = self.pg
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.running = False
            elif e.type == pg.MOUSEMOTION:
                self.mouse = (e.pos[0] // self.k, e.pos[1] // self.k)
                for r, key, _ in self.buttons:
                    if r.collidepoint(self.mouse):
                        self.focus = key
            elif e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                self.mouse = (e.pos[0] // self.k, e.pos[1] // self.k)
                for r, key, action in self.buttons:
                    if r.collidepoint(self.mouse):
                        self.focus = key
                        action()
                        break
            elif e.type == pg.KEYDOWN:
                if e.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                    self.activate()
                elif e.key == pg.K_ESCAPE:
                    self.back()
                elif e.key in (pg.K_TAB, pg.K_DOWN, pg.K_RIGHT, pg.K_s, pg.K_d):
                    self.move_focus(-1 if (e.key == pg.K_TAB and e.mod & pg.KMOD_SHIFT) else 1)
                elif e.key in (pg.K_UP, pg.K_LEFT, pg.K_w, pg.K_a):
                    self.move_focus(-1)
            elif self.sdlc and e.type == getattr(pg, 'CONTROLLERDEVICEADDED', -1):
                try:
                    if self.sdlc.is_controller(e.device_index):
                        c = self.sdlc.Controller(e.device_index)
                        self.pads[c.id] = c
                except Exception:
                    pass
            elif e.type == getattr(pg, 'CONTROLLERBUTTONDOWN', -1):
                b = e.button
                if b == pg.CONTROLLER_BUTTON_A or b == pg.CONTROLLER_BUTTON_START:
                    self.activate()
                elif b == pg.CONTROLLER_BUTTON_B:
                    self.back()
                elif b in (pg.CONTROLLER_BUTTON_DPAD_DOWN, pg.CONTROLLER_BUTTON_DPAD_RIGHT):
                    self.move_focus(1)
                elif b in (pg.CONTROLLER_BUTTON_DPAD_UP, pg.CONTROLLER_BUTTON_DPAD_LEFT):
                    self.move_focus(-1)
            elif e.type == getattr(pg, 'CONTROLLERAXISMOTION', -1):
                if e.axis in (pg.CONTROLLER_AXIS_LEFTY, pg.CONTROLLER_AXIS_LEFTX):
                    v = e.value / 32767.0
                    d = 1 if v > 0.6 else -1 if v < -0.6 else 0
                    if d and not self.axis_held:
                        self.move_focus(d)
                    if abs(v) < 0.3 or d:
                        self.axis_held = d

    # ------------------------------------------------------------ drawing
    def draw(self):
        pg = self.pg
        s = self.s
        self.buttons = []
        s.blit(self.banner, (0, 0))
        # fireflies
        for f in self.flies:
            x = (f[0] + math.sin(self.t * f[3] + f[2]) * 30 + self.t * 6 * f[3]) % (W + 40) - 20
            y = f[1] + math.sin(self.t * f[3] * 1.7 + f[2] * 2) * 14
            a = 0.5 + 0.5 * math.sin(self.t * 2.2 * f[3] + f[2] * 3)
            if a > 0.15:
                g = self.dot.copy()
                g.set_alpha(int(255 * a))
                s.blit(g, (x - 10, y - 10))
                s.set_at((int(x), int(y)), (255, 250, 210))
        s.blit(self.shade, (0, 0))
        # title
        bob = math.sin(self.t * 1.2) * 2
        self.text(s, 'Lantern Lake', (40, 30 + bob), 'title', (255, 232, 190), outline=(54, 30, 34),
                  shadow=(120, 60, 40))
        self.text(s, 'a cozy little fishing game', (46, 104), 'bodyb', (250, 230, 210), shadow=(40, 24, 30))
        # what's new
        info = game_info(self.up.game)
        notes = info.get('notes') if isinstance(info.get('notes'), list) else []
        if notes:
            box = pg.Rect(616, 30, 314, 0)
            lines = []
            for n in notes[:8]:
                for i, ln in enumerate(self.wrap(n, 'body', box.w - 52)):
                    lines.append((i == 0, ln))
            lines = lines[:11]
            box.h = 58 + len(lines) * 21
            self.panel(s, box, (22, 20, 40, 190), (255, 214, 150), radius=12, width=2)
            self.text(s, "What's new in %s" % info.get('version', '?'), (box.x + 18, box.y + 16), 'bodyb',
                      (255, 214, 150))
            y = box.y + 46
            for first, ln in lines:
                if first:
                    pg.draw.rect(s, WARM_L, (box.x + 20, y + 6, 6, 6))
                self.text(s, ln, (box.x + 34, y), 'body', (240, 232, 236))
                y += 21
        # buttons
        busy = self.up.state in ('downloading', 'installing')
        self.button(s, (40, 392, 296, 104), 'play', 'Play', self.play, 'play', 'play', enabled=not busy,
                    sub='Enter' if not busy else None)
        if self.up.state == 'available':
            self.button(s, (356, 392, 230, 32), 'check', 'Update to %s' % self.up.man['version'],
                        lambda: setattr(self, 'popup', 'available'), 'primary')
        else:
            self.button(s, (356, 392, 230, 32), 'check', 'Check for updates', lambda: self.up.check(True),
                        'ghost', enabled=not self.up.busy())
        self.button(s, (356, 428, 230, 32), 'folder', 'Open game folder', self.open_folder, 'ghost')
        self.button(s, (356, 464, 230, 32), 'quit', 'Quit', lambda: setattr(self, 'running', False), 'ghost')
        # status and versions
        msg, col = self.status()
        pg.draw.circle(s, col, (46, 520), 4)
        self.text(s, msg, (58, 511), 'body', col)
        self.text(s, 'game %s  -  launcher %s' % (self.up.local_version(), LAUNCHER_VERSION), (928, 511),
                  'body', (190, 180, 200), 'topright')
        if self.popup:
            self.buttons = []
            self.draw_popup(s)
        if self.focus not in [b[1] for b in self.buttons] and self.buttons:
            self.focus = self.buttons[0][1]
        if self.launched:
            dim = pg.Surface((W, H), pg.SRCALPHA)
            dim.fill((*NIGHT, 200))
            s.blit(dim, (0, 0))
            self.text(s, 'Lighting the lanterns...', (W // 2, H // 2), 'h', (255, 232, 190), 'center',
                      shadow=(40, 24, 30))

    def draw_popup(self, s):
        pg = self.pg
        up = self.up
        man = up.man or {}
        dim = pg.Surface((W, H), pg.SRCALPHA)
        dim.fill((*NIGHT, 165))
        s.blit(dim, (0, 0))
        title, body, notes, btns, bar = '', [], [], [], None
        p = self.popup
        if p == 'available':
            title = 'A new update is here!'
            body = ['Version %s is ready to install. You have %s.' % (man.get('version'), up.local_version()),
                    'Download size: %s' % fmt_mb(man.get('size', 0))]
            notes = man.get('notes', [])
            btns = [('upd', 'Update now', up.start_update, 'primary'), ('later', 'Later', self.close_popup, 'normal')]
        elif p == 'needs_launcher':
            title = 'A new launcher is needed'
            body = ['Version %s changes the launcher too, so it has to be downloaded from the release page.'
                    % man.get('version'),
                    'Unzip it into this folder and let it replace the files. Your saves stay put.']
            btns = [('page', 'Open the release page', self.open_page, 'primary'),
                    ('later', 'Later', self.close_popup, 'normal')]
        elif p == 'progress':
            installing = up.state == 'installing'
            title = 'Installing version %s' % man.get('version') if installing else \
                'Downloading version %s' % man.get('version')
            frac = 1.0 if installing else (up.got / up.total if up.total else 0.0)
            bar = frac
            body = ['Putting the new files in place. Your saves are not touched.' if installing else
                    '%s of %s' % (fmt_mb(up.got), fmt_mb(up.total or man.get('size', 0)))]
            if not installing:
                btns = [('cancel', 'Cancel', self.cancel_update, 'normal')]
        elif p == 'done':
            title = 'All set!'
            body = ['Lantern Lake is now version %s.' % up.local_version()]
            notes = game_info(up.game).get('notes') or []
            btns = [('play', 'Play', self.play, 'primary'), ('close', 'Close', self.close_popup, 'normal')]
        elif p == 'failed':
            title = "The update didn't finish"
            body = [up.error or 'Something went wrong.', "Your game wasn't changed, and you can still play."]
            btns = [('retry', 'Try again', up.start_update, 'primary'), ('anyway', 'Play anyway', self.play,
                                                                         'normal')]
        elif p == 'uptodate':
            title = "You're up to date"
            body = ['You have the newest version of Lantern Lake (%s).' % up.local_version()]
            btns = [('ok', 'OK', self.close_popup, 'primary')]
        elif p == 'offline':
            title = "Couldn't check for updates"
            body = [up.error or "Couldn't reach the update server.", 'Check your internet connection and try '
                    'again later. You can still play.']
            btns = [('ok', 'OK', self.close_popup, 'primary')]
        elif p == 'noconfig':
            title = "Updates aren't set up yet"
            body = ['update.json next to LanternLake.exe needs the GitHub repository the game is released '
                    'from, like {"github": "name/lantern-lake"}.']
            btns = [('ok', 'OK', self.close_popup, 'primary')]
        elif p == 'missing':
            title = "The game files are missing"
            body = ["The game folder doesn't have main.py. Download the game again from its release page."]
            btns = [('ok', 'OK', self.close_popup, 'primary')]
        pw = 560
        tw = pw - 56
        lines = []
        for para in body:
            lines += [('body', ln) for ln in self.wrap(para, 'body', tw)]
            lines.append(('gap', ''))
        if notes:
            lines.append(('bodyb', "What's new"))
            for n in notes[:6]:
                for i, ln in enumerate(self.wrap(n, 'body', tw - 20)):
                    lines.append(('note' if i == 0 else 'note2', ln))
            lines.append(('gap', ''))
        while lines and lines[-1][0] == 'gap':
            lines.pop()
        ph = 70 + sum(8 if k == 'gap' else 22 for k, _ in lines) + (44 if bar is not None else 0) + \
            (64 if btns else 18)
        r = pg.Rect(0, 0, pw, ph)
        r.center = (W // 2, H // 2)
        self.panel(s, r, CREAM, BROWN, radius=16)
        pg.draw.rect(s, CREAM_D, (r.x + 10, r.y + 10, r.w - 20, 44), border_radius=10)
        self.text(s, title, (r.x + 28, r.y + 32), 'h', INK, 'midleft')
        # a little lantern in the corner
        lx, ly = r.right - 40, r.y + 20
        pg.draw.line(s, BROWN, (lx + 8, ly - 4), (lx + 8, ly), 2)
        pg.draw.rect(s, (178, 74, 58), (lx + 1, ly, 14, 4))
        pg.draw.rect(s, WARM_L, (lx + 2, ly + 4, 12, 16), border_radius=3)
        pg.draw.rect(s, (255, 244, 214), (lx + 6, ly + 8, 4, 8))
        pg.draw.rect(s, (178, 74, 58), (lx + 1, ly + 20, 14, 4))
        y = r.y + 70
        for k, ln in lines:
            if k == 'gap':
                y += 8
                continue
            if k == 'note':
                pg.draw.rect(s, WARM, (r.x + 32, y + 6, 6, 6))
            x = r.x + 28 + (18 if k in ('note', 'note2') else 0)
            self.text(s, ln, (x, y), 'bodyb' if k == 'bodyb' else 'body', BROWN if k == 'bodyb' else INK)
            y += 22
        if bar is not None:
            y += 8
            br = pg.Rect(r.x + 28, y, r.w - 56, 24)
            pg.draw.rect(s, CREAM_D, br, border_radius=12)
            if bar > 0:
                fr = pg.Rect(br.x, br.y, max(24, int(br.w * min(1.0, bar))), br.h)
                pg.draw.rect(s, WARM, fr, border_radius=12)
                pg.draw.rect(s, WARM_L, (fr.x + 6, fr.y + 4, max(0, fr.w - 12), 6), border_radius=3)
            pg.draw.rect(s, BROWN, br, 2, border_radius=12)
            self.text(s, '%d%%' % int(min(1.0, bar) * 100), br.center, 'bodyb', INK, 'center')
        if btns:
            ws = [max(160, self.f['bodyb'].size(b[1])[0] + 44) for b in btns]
            gap = 16
            x = r.centerx - (sum(ws) + (len(btns) - 1) * gap) // 2
            for (key, label, action, style), bw in zip(btns, ws):
                self.button(s, (x, r.bottom - 56, bw, 38), key, label, action, style)
                x += bw + gap

    # ------------------------------------------------------------ loop
    def tick(self, dt):
        self.t += dt
        if self.check_at is not None and self.t >= self.check_at:
            self.check_at = None
            self.up.check(False)
        self.sync_popup()
        if self.auto:
            self.auto_step()

    def auto_step(self):
        """--auto-update: press Update on the pop-up, then write the outcome to a file and close (testing)."""
        st = self.up.state
        if self.popup == 'available':
            self.up.start_update()
        if st in ('done', 'failed', 'uptodate', 'offline', 'noconfig', 'needs_launcher') and self.seen == st:
            with open(self.auto, 'w', encoding='utf-8') as f:
                json.dump({'state': st, 'error': self.up.error, 'version': self.up.local_version()}, f)
            self.running = False

    def run(self):
        pg = self.pg
        clock = pg.time.Clock()
        launched_t = None
        while self.running:
            dt = clock.tick(60) / 1000.0
            self.handle()
            self.tick(min(dt, 0.05))
            self.draw()
            if self.k == 1:
                self.window.blit(self.s, (0, 0))
            else:
                pg.transform.scale(self.s, self.window.get_size(), self.window)
            pg.display.flip()
            if self.launched:
                launched_t = launched_t or time.time()
                if time.time() - launched_t > 0.4:
                    break
        self.up.cancel = True
        pg.quit()


# ====================================================================== running the game
def message_box(text):
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, 'Lantern Lake', 0x10)
        except Exception:
            pass


def run_game(root, extra):
    import runpy
    game = os.path.join(root, 'game')
    main = os.path.join(game, 'main.py')
    quiet = '--bot' in extra or '--shots' in extra
    if not os.path.isfile(main):
        message_box("Lantern Lake couldn't find its game files (game\\main.py).")
        return 1
    log = None
    try:
        log = open(os.path.join(game, 'log.txt'), 'w', encoding='utf-8', buffering=1)
        sys.stdout = sys.stderr = log
    except OSError:
        pass
    os.chdir(game)
    sys.path.insert(0, game)
    sys.argv = [main] + list(extra)
    try:
        runpy.run_path(main, run_name='__main__')
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    except BaseException:
        traceback.print_exc()
        if log:
            log.flush()
        if not quiet:
            message_box('Lantern Lake ran into a problem and had to close.\n\nThe details are in\n%s'
                        % os.path.join(game, 'log.txt'))
        return 1
    return 0


def main(argv):
    root = find_root(argv)
    if '--demo-shots' in argv:
        return demo_shots(argv[argv.index('--demo-shots') + 1])
    if root is None:
        print('From source, pass --root <install folder> (never the development folder).')
        return 2
    if '--run-game' in argv:
        extra = argv[argv.index('--run-game') + 1:]
        return run_game(root, extra)
    try:
        app = Launcher(root)
        if '--auto-update' in argv:
            app.auto = argv[argv.index('--auto-update') + 1]
        app.run()
    except Exception:
        try:
            with open(os.path.join(root, 'launcher_log.txt'), 'w', encoding='utf-8') as f:
                traceback.print_exc(file=f)
        except OSError:
            pass
        message_box('The launcher ran into a problem. Details are in launcher_log.txt.')
        return 1
    return 0


# ====================================================================== screenshots of every state (testing)
def demo_shots(outdir):
    import tempfile
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.makedirs(outdir, exist_ok=True)
    root = tempfile.mkdtemp(prefix='ll_demo_')
    os.makedirs(os.path.join(root, 'game'))
    with open(os.path.join(root, 'game', 'main.py'), 'w') as f:
        f.write('')
    with open(os.path.join(root, 'game', 'version.json'), 'w') as f:
        json.dump({'version': '1.0.0', 'notes': ['A garden under the cabin with 13 crops to grow.',
                                                 'Sixteen animals to spot and photograph for the Nature page.',
                                                 'A launcher that keeps the game up to date.']}, f)
    app = Launcher(root, demo=True)
    app.check_at = None
    man = {'version': '1.1.0', 'size': 2400000, 'zip': 'x.zip', 'sha256': '0' * 64,
           'notes': ['Ice fishing gets a warm cocoa stand.', 'Two new fish in the creek.',
                     'Fixed the heron sometimes standing on the boat.']}

    def shot(name, state, popup, **kw):
        app.up.state = state
        app.seen = state
        app.popup = popup
        app.up.man = man if state not in ('idle',) else None
        for k, v in kw.items():
            setattr(app.up, k, v)
        app.t += 0.7
        app.draw()
        app.draw()
        app.pg.image.save(app.s, os.path.join(outdir, name + '.png'))
        print('shot', name)
    shot('main_checking', 'checking', None)
    shot('main_uptodate', 'uptodate', None)
    shot('popup_available', 'available', 'available')
    shot('main_later', 'available', None)
    shot('popup_progress', 'downloading', 'progress', got=900000, total=2400000)
    shot('popup_installing', 'installing', 'progress')
    shot('popup_done', 'done', 'done')
    shot('popup_failed', 'failed', 'failed', error="The download didn't check out, so it wasn't installed.")
    shot('popup_offline', 'offline', 'offline', error="Couldn't reach the update server.")
    shot('popup_needs_launcher', 'needs_launcher', 'needs_launcher')
    shot('popup_uptodate', 'uptodate', 'uptodate')
    app.pg.quit()
    shutil.rmtree(root, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
