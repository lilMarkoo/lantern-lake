"""The radio: three little stations, each with its own music, and hosts who read the weather, the tides and
the news from round the lake between the songs. R opens the set; the station keeps playing while you fish."""
import math
import random

import pygame

import ui as U
import almanac
import coast
from data import FISH_BY_ID

STATIONS = [
    dict(id='lantern', name='Lantern FM', freq=88.4, style='lofi', host='Marigold',
         blurb='slow beats, slow mornings', col=(232, 170, 90)),
    dict(id='shanty', name='Saltmarsh Shanty', freq=96.1, style='shanty', host='Captain Dorrie',
         blurb='harbour squeezebox', col=(90, 140, 190)),
    dict(id='bells', name='Night Bells', freq=103.7, style='bells', host='Moth',
         blurb='chimes for late nights', col=(150, 130, 200)),
]
BY_ID = {st['id']: st for st in STATIONS}
LO, HI = 87.5, 108.0              # the dial
SONG = (75.0, 115.0)              # seconds a song lasts


def fmt_clock(m):                 # main swaps in its own
    m = int(m) % 1440
    return '%d:%02d' % (m // 60, m % 60)


# ---------------------------------------------------------------- songs (all made up)
TITLES = {
    'lofi': (('Kettle', 'Rainy', 'Sleepy', 'Lantern', 'Mossy', 'Sunday', 'Paper', 'Velvet', 'Porch', 'Biscuit',
              'Honey', 'Windowsill'),
             ('Jetty', 'Window', 'Afternoon', 'Ripples', 'Tea', 'Boats', 'Clouds', 'Pages', 'Puddles', 'Reeds',
              'Mittens', 'Bobber')),
    'shanty': (('Bonny', 'Leaky', 'Salty', 'Rolling', 'Herring', 'Jolly', 'Windy', 'Barnacle', 'Old'),
               ('Kittiwake', 'Mackerel', 'Bosun', 'Harbour Wall', 'Net Mender', 'Gull', 'Lighthouse', 'Tide')),
    'bells': (('Midnight', 'Moonlit', 'Three O\'Clock', 'Starry', 'Lantern', 'Hush', 'Frosted', 'Owl'),
              ('Chimes', 'Ripples', 'Moths', 'Bells', 'Frost', 'Fireflies', 'Lullaby', 'Snowfall')),
}
FORMS = {'lofi': ('{a} {b}', '{b} on the {c}', 'Slow {b}', '{a} {b} (Tape Version)'),
         'shanty': ('The {a} {b}', 'Haul Away the {b}', 'Farewell to {p}', 'The {b} of {p}'),
         'bells': ('{a} {b}', '{b} at {a}', 'A Little {b}', '{a}')}
ARTISTS = {'lofi': ('The Driftwood Three', 'Moss & Tide', 'Little Heron', 'Pebble Club', 'June Low',
                    'Cat on a Cushion'),
           'shanty': ('The Net Menders', 'Old Tam and the Boys', 'Squeezebox Sal', 'The Kelp Rock Choir'),
           'bells': ('Moth Orchestra', 'Glass Harbour', 'Hush Hush', 'The Owl Choir')}
PLACES = ('Saltmarsh', 'Kelp Rocks', 'Fernwick', 'the Pier', 'Lantern Lake')
FLAVOUR = {'lofi': ('Stay cozy out there.', "Put the kettle on. This next one's a slow one.",
                    'If the fish are shy today, so are we. No rush.'),
           'shanty': ('Heave ho, listeners!', "Mind the gulls, they're after your chips.",
                      'Stamp your boots for this one!'),
           'bells': ('For the night owls and the night anglers.', 'Quiet now. The fish are listening.',
                     'Look up if you can. The sky is doing its best tonight.')}
WEATHER = {'clear': 'clear and bright', 'rain': 'rainy, so pack a coat', 'fog': 'foggy in the morning',
           'snow': 'snowy. Mittens on!', 'storm': 'stormy, with thunder over the lake', 'cloudy': 'grey and mild',
           'wind': 'breezy'}


def song(rng, style):
    a, b = TITLES[style]
    form = rng.choice(FORMS[style])
    title = form.format(a=rng.choice(a), b=rng.choice(b), c=rng.choice(b).lower(), p=rng.choice(PLACES))
    return title, rng.choice(ARTISTS[style])


def news(g, rng):
    """A few things worth knowing today, as the hosts would say them."""
    out = []
    tom = g.forecast.get(str(g.day + 1)) if isinstance(g.forecast, dict) else None
    if tom:
        out.append('The weather for tomorrow: %s.' % WEATHER.get(tom, tom))
    if g.weather in ('rain', 'snow'):
        out.append("It's %s out there right now. A good day for a hot drink and a fish or two."
                   % ('raining' if g.weather == 'rain' else 'snowing'))
    if coast.is_open(g):
        hi = next(((d, m) for k, d, m in coast.next_tides(g, 3) if k == 'High'), None)
        if hi:
            out.append('Down at Saltmarsh, high water is at %s%s.' % (fmt_clock(hi[1]),
                                                                     '' if hi[0] == g.day else ' tomorrow'))
    try:
        run = g.run_fish(g.day)
    except Exception:
        run = None
    if run and run in FISH_BY_ID:
        out.append('Big news: the %s are running today, and they fetch half again at market.'
                   % FISH_BY_ID[run]['name'])
    if g.festival_today() and not g.festival.get('done'):
        out.append("Don't forget, it's the %s today, from %s." % (g.festival['name'], fmt_clock(g.festival['start'])))
    if g.wagon_here():
        out.append("Wren's Wagon is parked down by the lake until 8 o'clock.")
    req = g.request
    if req and not req.get('done') and req.get('fish') in FISH_BY_ID:
        out.append('A letter from a listener: %s is hoping someone can catch a %s.'
                   % (req['who'].split(' (')[0], FISH_BY_ID[req['fish']]['name']))
    if coast.lit(g):
        out.append('The Saltmarsh light is shining again. Thank you, whoever you are!')
    elif coast.is_open(g) and g.coast['tasks']:
        out.append('Word from the harbour: the old lighthouse is getting some love. Scaffold coming down!')
    if g.coast.get('boat', 0) >= len(coast.BOAT_STAGES) - 1:
        out.append('Congratulations to Ossian on the %s, the prettiest boat in Saltmarsh.' % coast.BOAT_NAME)
    rng.shuffle(out)
    return out


class Radio:
    def __init__(self, g):
        self.g = g
        self.rng = random.Random()
        self.station = None
        self.title = ('', '')
        self.song_t = 0.0
        self.talk = []                # [text, seconds] the host still has to say
        self.say = None               # [text, seconds left, seconds long]
        self.log = []                 # the last few things the host said
        self.dial = LO + 3            # where the needle is (it slides when you tune)
        self.blip_t = 0.0

    # ------------------------------------------------------------ tuning
    def tune(self, sid):
        g = self.g
        if sid == self.station:
            return
        self.station = sid
        g.settings['radio'] = sid
        g.audio.radio_static(0.45)
        if sid is None:
            g.audio.radio_off()
            self.talk, self.say = [], None
            g.audio.radio_duck = False
            g.audio.play('click', 0.5)
            return
        st = BY_ID[sid]
        self.title = song(self.rng, st['style'])
        self.song_t = self.rng.uniform(*SONG)
        self.talk, self.say = [], None
        when = '%s, %s' % (fmt_clock(g.minute), almanac.weekday(g.day))
        self._queue(["You're listening to %s, %.1f. I'm %s, and it's %s." % (st['name'], st['freq'], st['host'], when)]
                    + news(g, self.rng)[:1]
                    + ["Here's %s with '%s'." % (self.title[1], self.title[0])])
        self.log = []

    def cycle(self):
        ids = [None] + [st['id'] for st in STATIONS]
        self.tune(ids[(ids.index(self.station) + 1) % len(ids)])

    def _queue(self, lines):
        for ln in lines:
            self.talk.append([ln, max(3.2, len(ln) / 15.0)])

    # ------------------------------------------------------------ every frame
    def update(self, dt):
        g = self.g
        a = g.audio
        on = self.station is not None and g.mode == 'play'
        st = BY_ID.get(self.station)
        target = st['freq'] if st else LO + 3
        self.dial += (target - self.dial) * min(1.0, dt * 5)
        if not on:
            if a.radio:
                a.radio_off()
            return
        if a.radio != st['style']:
            a.radio_on(st['style'])
        set_ = g.settings
        a.radio_vol = set_.get('master', 1.0) * max(set_.get('music', 0.5), 0.35)
        if self.say is None and self.talk:
            text, dur = self.talk.pop(0)
            self.say = [text, dur, dur]
            self.log = (self.log + [text])[-4:]
        if self.say:
            self.say[1] -= dt
            self.blip_t -= dt
            if self.blip_t <= 0:                       # the host's voice: a soft murmur
                self.blip_t = self.rng.uniform(0.18, 0.34)
                a.chat(0.18 * a.radio_vol)
            if self.say[1] <= 0:
                self.say = None
        a.radio_duck = self.say is not None or bool(self.talk)
        if a.radio_duck:
            return
        self.song_t -= dt
        if self.song_t <= 0:                           # between songs: the host has a word
            old = self.title
            self.title = song(self.rng, st['style'])
            self.song_t = self.rng.uniform(*SONG)
            lines = ["That was '%s' by %s." % old]
            lines += news(self.g, self.rng)[:2]
            if self.rng.random() < 0.6:
                lines.append(self.rng.choice(FLAVOUR[st['style']]))
            lines.append("Next up: '%s', by %s." % self.title)
            self._queue(lines)

    def subtitle(self):
        """The bit of what the host is saying that fits on the HUD card now."""
        if not self.say:
            return None
        text, left, dur = self.say
        parts = self.g.ui.wrap(text, 'small', 296) or ['']
        k = min(len(parts) - 1, int((1 - left / dur) * len(parts)))
        return parts[k]

    # ------------------------------------------------------------ drawing
    def draw_widget(self, s, y, CW):
        """A small card under the others while a station is on. Returns the y below it."""
        if self.station is None:
            return y
        g = self.g
        ui = g.ui
        st = BY_ID[self.station]
        r = ui.panel(s, (16, y, CW, 64), radius=16)
        ui.hotspot(r, lambda: g.toggle('radio'))
        radio_icon(s, (r.x + 30, r.y + 32), g.t, st['col'])
        ui.blit_text(s, '%s  %.1f' % (st['name'], st['freq']), (r.x + 58, r.y + 9), 'smallb', U.INK,
                     maxw=CW - 120)
        for i in range(4):                             # a little level meter
            h = 4 + int(10 * abs(math.sin(g.t * (3 + i * 1.3) + i))) if not g.audio.radio_duck else 3
            s.fill(st['col'], (r.right - 54 + i * 9, r.y + 26 - h, 6, h))
        sub = self.subtitle()
        if sub:
            ui.blit_text(s, sub, (r.x + 58, r.y + 36), 'small', U.INK, maxw=CW - 70)
        else:
            ui.blit_text(s, "'%s' - %s" % self.title, (r.x + 58, r.y + 36), 'small', U.SOFT, maxw=CW - 70)
        return r.bottom + 8

    def draw_panel(self, s):
        g = self.g
        ui = g.ui
        sw, sh = s.get_size()
        rect = pygame.Rect(sw // 2 - 430, sh // 2 - 280, 860, 560)
        ui.panel(s, rect, radius=24)
        g.panel_header(s, rect, 'Radio')
        ui.button(s, (rect.right - 62, rect.y + 18, 44, 44), 'X', g.close_overlay, 'normal', font='h3')
        st = BY_ID.get(self.station)
        # the set: a wooden case, a speaker grille and the tuning dial
        box = pygame.Rect(rect.x + 40, rect.y + 100, rect.w - 80, 190)
        pygame.draw.rect(s, (150, 98, 62), box, border_radius=22)
        pygame.draw.rect(s, (120, 76, 48), box, 4, border_radius=22)
        pygame.draw.rect(s, (176, 120, 80), box.inflate(-16, -16), 2, border_radius=16)
        grille = pygame.Rect(box.x + 30, box.y + 30, 200, box.h - 60)
        pygame.draw.rect(s, (60, 44, 36), grille, border_radius=14)
        pulse = 0 if not st or g.audio.radio_duck else int(2 * abs(math.sin(g.t * 6)))
        for yy in range(grille.y + 12, grille.bottom - 8, 10):
            for xx in range(grille.x + 12, grille.right - 8, 10):
                pygame.draw.circle(s, (100, 78, 62) if not pulse else (116, 90, 70), (xx, yy), 3)
        win = pygame.Rect(grille.right + 30, box.y + 36, box.right - grille.right - 60, 70)
        pygame.draw.rect(s, (246, 232, 196) if st else (210, 200, 180), win, border_radius=10)
        pygame.draw.rect(s, (90, 66, 48), win, 3, border_radius=10)
        for f in range(88, 109):
            x = win.x + 16 + (f - LO) / (HI - LO) * (win.w - 32)
            tall = f % 4 == 0
            s.fill((120, 96, 80), (int(x), win.y + 12, 2, 16 if tall else 8))
            if tall:
                ui.blit_text(s, str(f), (int(x), win.y + 32), 'tiny', U.SOFT, 'midtop')
        for stn in STATIONS:
            x = win.x + 16 + (stn['freq'] - LO) / (HI - LO) * (win.w - 32)
            pygame.draw.circle(s, stn['col'], (int(x), win.bottom - 12), 5)
        nx = win.x + 16 + (self.dial - LO) / (HI - LO) * (win.w - 32)
        s.fill((200, 60, 50), (int(nx) - 1, win.y + 6, 3, win.h - 12))
        if st:                                          # the warm glow of a set that's on
            gl = pygame.Surface((win.w, win.h))
            gl.fill((40, 26, 0))
            s.blit(gl, win.topleft, special_flags=pygame.BLEND_RGB_ADD)
        for i, kx in enumerate((win.x + 40, win.right - 40)):     # two knobs
            c = (kx, box.bottom - 46)
            pygame.draw.circle(s, (70, 52, 40), c, 22)
            pygame.draw.circle(s, (210, 190, 150), c, 18)
            a = (self.dial - LO) / (HI - LO) * 5 if i == 0 else 2.2
            pygame.draw.line(s, (90, 66, 48), c, (c[0] + math.cos(a + 2) * 14, c[1] + math.sin(a + 2) * 14), 3)
        ui.blit_text(s, 'Volume follows your music setting', (win.centerx, box.bottom - 46), 'tiny', (250, 236, 210),
                     'center')
        # the stations
        y = box.bottom + 20
        ow = 120
        bw = (rect.w - 80 - 3 * 12 - ow) // 3
        x = rect.x + 40
        for stn in STATIONS + [None]:
            w = bw if stn else ow
            r = pygame.Rect(x, y, w, 72)
            x += w + 12
            on = (stn and stn['id'] == self.station) or (stn is None and self.station is None)
            ui.button(s, r, stn['name'] if stn else 'Off', (lambda sid=(stn['id'] if stn else None): self.tune(sid)),
                      'gold' if on else 'primary', font='smallb', nav=True)
            if stn:
                ui.blit_text(s, '%.1f  %s' % (stn['freq'], stn['blurb']), (r.centerx, r.bottom + 6), 'tiny', U.SOFT,
                             'midtop', maxw=w)
        y += 108
        if st:
            ui.blit_text(s, "Now playing: '%s' by %s" % self.title, (rect.x + 40, y), 'smallb', U.INK,
                         maxw=rect.w - 80)
            y += 30
            for ln in self.log[-2:]:
                ui.blit_text(s, '%s: "%s"' % (st['host'], ln), (rect.x + 40, y), 'small', U.SOFT, maxw=rect.w - 80)
                y += 24
        else:
            ui.blit_text(s, 'Pick a station. It keeps playing while you fish, and the host reads the weather and '
                            'the tides between songs.', (rect.x + 40, y), 'small', U.SOFT, maxw=rect.w - 80)


def radio_icon(s, c, t, col=(232, 170, 90)):
    """A little transistor radio for the HUD."""
    x, y = c
    pygame.draw.line(s, (90, 80, 76), (x + 6, y - 9), (x + 13, y - 19), 2)
    pygame.draw.circle(s, (90, 80, 76), (x + 13, y - 19), 2)
    body = pygame.Rect(x - 15, y - 10, 30, 21)
    pygame.draw.rect(s, (150, 98, 62), body, border_radius=5)
    pygame.draw.rect(s, (110, 70, 46), body, 2, border_radius=5)
    for i in range(3):
        for j in range(3):
            pygame.draw.circle(s, (70, 52, 40), (x - 9 + i * 4, y - 4 + j * 5), 1)
    pygame.draw.rect(s, (246, 232, 196), (x + 1, y - 5, 10, 6), border_radius=2)
    s.fill(col, (x + 3 + int(abs(math.sin(t * 0.7)) * 5), y - 4, 1, 4))
    pygame.draw.circle(s, (210, 190, 150), (x + 6, y + 6), 3)
