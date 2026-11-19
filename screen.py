"""The game window, and putting each finished frame on it with the graphics card.

The world is drawn on a 640x360 pixel-art grid and the interface on its own see-through canvas. Instead of
blowing those up to the window on the CPU (slow at big sizes, and blurry when the window isn't a whole multiple
of the art), they go to the GPU as textures and are scaled there:

  * "sharp" scaling: first a whole-number zoom with hard pixels, then one smooth stretch for the last bit. Pixels
    stay crisp and even at any window size, and the camera can still glide by less than an art pixel.
  * vsync, when asked for, so a fast PC paces itself to the screen without tearing.

If the PC can't make a GPU renderer, Screen.gpu is False and main.py keeps its old CPU path.
"""
import os

import pygame

try:
    from pygame._sdl2 import video
except ImportError:                       # an old pygame: the CPU path it is
    video = None

BAR = (16, 14, 24, 255)
HARD = 2.5          # from this many screen pixels per art pixel up, scale with hard pixels only: crisp at any
                    # size (a pixel is n or n+1 wide, which can't be seen up here, while a smooth stretch blurs)


def hard_ok(s):
    """Draw at s screen pixels per art pixel with hard pixels alone?"""
    return s >= HARD or abs(s - round(s)) < 0.01


def _hint_scale(linear):
    # SDL reads the scale quality when a texture is made: '0' hard pixels, '1' smooth
    os.environ['SDL_RENDER_SCALE_QUALITY'] = '1' if linear else '0'


class Screen:
    def __init__(self, title, size, vsync=False):
        if video is None:
            raise RuntimeError('no GPU renderer in this pygame')
        self.window = pygame.Window(title, size, resizable=True)
        self.vsync = bool(vsync)
        self.renderer = None
        try:
            self._make_renderer()
        except Exception:
            self.window.destroy()
            raise

    def _make_renderer(self):
        self.tex = {}
        # Direct3D 11 is the quickest on Windows (SDL2 would pick the older Direct3D 9); if it isn't there, or
        # the player chose a driver with SDL_RENDER_DRIVER, take what SDL gives
        want = os.environ.get('SDL_RENDER_DRIVER') or ('direct3d11' if os.name == 'nt' else '')
        if want and not os.environ.get('SDL_RENDER_DRIVER'):
            os.environ['SDL_RENDER_DRIVER'] = want
            try:
                self.renderer = video.Renderer(self.window, accelerated=1, vsync=self.vsync)
                return
            except pygame.error:
                pass
            finally:
                del os.environ['SDL_RENDER_DRIVER']
        self.renderer = video.Renderer(self.window, accelerated=1, vsync=self.vsync)

    # ---------------------------------------------------------------- the window
    @property
    def size(self):
        return tuple(self.window.size)

    def set_vsync(self, on):
        on = bool(on)
        if on == self.vsync:
            return
        self.vsync = on
        self.renderer = None
        self.tex = {}
        try:
            self._make_renderer()
        except pygame.error:
            self.vsync = not on                     # keep what worked
            self._make_renderer()

    def set_fullscreen(self, on, windowed_size):
        if on:
            self.window.set_fullscreen(desktop=True)
        else:
            self.window.set_windowed()
            self.window.size = tuple(windowed_size)
            self.window.position = pygame.WINDOWPOS_CENTERED

    def set_size(self, size):
        self.window.size = tuple(size)
        self.window.position = pygame.WINDOWPOS_CENTERED

    def set_icon(self, surf):
        self.window.set_icon(surf)

    # ---------------------------------------------------------------- textures
    def _tex(self, key, size, streaming=False, target=False, linear=False, alpha=False):
        t = self.tex.get(key)
        if t is None or (t.width, t.height) != tuple(size):
            _hint_scale(linear)
            t = video.Texture(self.renderer, tuple(size), streaming=streaming, target=target)
            t.blend_mode = 1 if alpha else 0
            self.tex[key] = t
        return t

    def _sharp(self, key, tex, src_size, view_w, alpha):
        """tex at the biggest whole-number zoom that still fits the view (hard pixels), on a smooth target."""
        sw, sh = src_size
        n = max(1, int(view_w / sw + 1e-6))
        big = self._tex(key + '_n', (sw * n, sh * n), target=True, linear=True, alpha=alpha)
        r = self.renderer
        r.target = big
        if alpha:
            r.draw_color = (0, 0, 0, 0)
            r.clear()
        tex.draw(dstrect=(0, 0, sw * n, sh * n))
        r.target = None
        return big, n

    # ---------------------------------------------------------------- a frame
    def present(self, view, world=None, cam=None, ui=None, ui_art=None):
        """world: the 640x360 art frame and cam (x, y, w, h in art pixels, floats) the part of it to show.
        ui: the interface canvas (see-through), drawn over the world; ui_art its art-grid size (half the canvas).
        Either can be left out (the plain path passes only ui, holding everything)."""
        r = self.renderer
        r.target = None
        r.draw_color = BAR
        r.clear()
        vx, vy, vw, vh = view
        if world is not None:
            ww, wh = world.get_size()
            src = self._tex('world', (ww, wh), streaming=True)
            src.update(world)
            xf, yf, wf, hf = cam if cam else (0.0, 0.0, float(ww), float(wh))
            s = vw / wf                                     # window pixels per art pixel
            x0, y0 = int(xf), int(yf)
            x1, y1 = min(ww, int(xf + wf) + 1), min(wh, int(yf + hf) + 1)
            dst = pygame.FRect(-(xf - x0) * s, -(yf - y0) * s, (x1 - x0) * s, (y1 - y0) * s)
            r.set_viewport(pygame.Rect(view))
            if hard_ok(s):
                src.draw(srcrect=pygame.Rect(x0, y0, x1 - x0, y1 - y0), dstrect=dst)
            else:
                big, n = self._sharp('world', src, (ww, wh), s * ww, False)
                big.draw(srcrect=pygame.Rect(x0 * n, y0 * n, (x1 - x0) * n, (y1 - y0) * n), dstrect=dst)
            r.set_viewport(None)
        if ui is not None:
            cw, ch = ui.get_size()
            alpha = bool(ui.get_flags() & pygame.SRCALPHA)
            src = self._tex('ui', (cw, ch), streaming=True, linear=True)    # halves like a box filter
            src.update(ui)
            aw, ah = ui_art or (cw, ch)
            if (cw, ch) != (aw, ah):
                # the canvas is the art grid at 2x: shrink it back with hard pixels first
                art = self._tex('ui_art', (aw, ah), target=True, alpha=alpha)
                r.target = art
                if alpha:
                    r.draw_color = (0, 0, 0, 0)
                    r.clear()
                src.draw(dstrect=(0, 0, aw, ah))
                r.target = None
                src = art
            if hard_ok(vw / aw):
                src.blend_mode = 1 if alpha else 0
                src.draw(dstrect=pygame.Rect(view))
            else:
                big, n = self._sharp('ui', src, (aw, ah), vw, alpha)
                big.blend_mode = 1 if alpha else 0
                big.draw(dstrect=pygame.Rect(view))
        r.present()

    def show_surface(self, surf):
        """Put a plain picture (the loading screen) on the window, centred."""
        r = self.renderer
        r.target = None
        r.draw_color = BAR
        r.clear()
        t = video.Texture.from_surface(r, surf)
        rect = t.get_rect(center=(self.size[0] // 2, self.size[1] // 2))
        t.draw(dstrect=rect)
        r.present()

    def read(self):
        """What's on the window now, as a Surface (for screenshots)."""
        return self.renderer.to_surface()
