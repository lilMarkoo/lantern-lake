"""All sound is synthesised at start-up with numpy: ambience loops, effects and generative music."""
import math
import random

import numpy as np
import pygame

AMB_CH = {'water': 0, 'rain': 1, 'crickets': 2, 'wind': 3, 'fountain': 6}
PAD_CH = (4, 5)
BAND_SCALE = [55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72, 74, 76]     # C major for the bandstand tunes


class Audio:
    def __init__(self):
        self.ok = False
        self.music_vol = 0.5
        self.sfx_vol = 0.8
        self.amb_vol = 0.8
        self.sounds = {}
        self.notes = {}
        try:
            init = pygame.mixer.get_init()
            if not init:
                pygame.mixer.init(44100, -16, 2, 512)
                init = pygame.mixer.get_init()
            self.sr, _, self.ch = init
            pygame.mixer.set_num_channels(40)
            pygame.mixer.set_reserved(8)
            self.ok = True
        except Exception as e:  # no audio device: run silently
            print('Audio disabled:', e)
            return
        self.rng = np.random.default_rng(4)
        self._build()
        self.amb = {k: pygame.mixer.Channel(i) for k, i in AMB_CH.items()}
        for k, ch in self.amb.items():
            ch.set_volume(0)
            ch.play(self.sounds['amb_' + k], loops=-1)
        self.pads = [pygame.mixer.Channel(i) for i in PAD_CH]
        self.pad_i = 0
        self.beat_t = 0.0
        self.beat_n = 0
        self.chord_i = 0
        self.bird_t = 3.0
        self.chime_t = 6.0
        self.cur_amb = {k: 0.0 for k in AMB_CH}
        self.chat_t = 2.0
        self.band_t = 0.0
        self.band_n = 0
        self.band_m = 64
        self.band_vol = 0.0

    # ------------------------------------------------------------ synthesis helpers
    def _t(self, dur):
        return np.arange(int(self.sr * dur)) / self.sr

    def _noise(self, n):
        return self.rng.standard_normal(n)

    def _band(self, x, lo, hi, tilt=0.0):
        X = np.fft.rfft(x)
        f = np.fft.rfftfreq(len(x), 1 / self.sr)
        f[0] = 1.0
        Hh = 1 / (1 + (lo / f) ** 4) / (1 + (f / hi) ** 4)
        if tilt:
            Hh *= (np.maximum(f, 20) / 1000.0) ** (-tilt)
        return np.fft.irfft(X * Hh, len(x))

    @staticmethod
    def _norm(x, peak=0.8):
        m = np.max(np.abs(x))
        return x / m * peak if m > 0 else x

    def _snd(self, mono, peak=0.8):
        a = (np.clip(self._norm(mono, peak), -1, 1) * 32000).astype(np.int16)
        if self.ch >= 2:
            a = np.ascontiguousarray(np.repeat(a[:, None], self.ch, axis=1))
        return pygame.sndarray.make_sound(a)

    def _sweep(self, f0, f1, dur, k=6.0):
        t = self._t(dur)
        f = f1 + (f0 - f1) * np.exp(-t * k)
        return np.sin(2 * np.pi * np.cumsum(f) / self.sr), t

    def _bell(self, f, dur=1.2, decay=4.0):
        t = self._t(dur)
        x = (np.sin(2 * np.pi * f * t) * np.exp(-t * decay)
             + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * decay * 2.2)
             + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * decay * 4))
        return x * (1 - np.exp(-t * 800))

    def _kalimba(self, f, dur=2.4):
        t = self._t(dur)
        x = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6)
             + 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 6)
             + 0.12 * np.sin(2 * np.pi * f * 5.3 * t) * np.exp(-t * 16))
        return x * (1 - np.exp(-t * 500))

    def _mix(self, parts, dur):
        out = np.zeros(int(self.sr * dur))
        for offset, x, g in parts:
            i = int(offset * self.sr)
            n = min(len(x), len(out) - i)
            out[i:i + n] += x[:n] * g
        return out

    # ------------------------------------------------------------ build all sounds
    def _build(self):
        sr = self.sr
        S = self.sounds
        r = random.Random(9)
        # --- ambience loops (FFT filtering keeps them seamless)
        n = sr * 6
        rain = self._band(self._noise(n), 400, 9000, 0.3)
        for _ in range(500):
            i = r.randrange(n - 400)
            f = r.uniform(2500, 7000)
            tt = np.arange(300) / sr
            rain[i:i + 300] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 900) * r.uniform(0.5, 2.5) * np.std(rain)
        S['amb_rain'] = self._snd(rain, 0.55)

        n = sr * 8
        t = np.arange(n) / sr
        water = self._band(self._noise(n), 60, 500, 0.6)
        am = 0.55 + 0.25 * np.sin(2 * np.pi * t * 2 / 8) + 0.2 * np.sin(2 * np.pi * t * 5 / 8 + 1)
        lap = self._band(self._noise(n), 300, 1400) * (0.5 + 0.5 * np.sin(2 * np.pi * t * 3 / 8 + 2)) ** 3
        S['amb_water'] = self._snd(water * am + lap * 0.5, 0.5)

        n = sr * 4
        cr = np.zeros(n)
        for k in range(3):
            f = r.uniform(4200, 5200)
            count = r.choice([5, 6, 7])
            period = 4.0 / count
            for c in range(count):
                start = c * period + r.uniform(0, 0.08)
                for p in range(3):
                    i = int((start + p * 0.03) * sr)
                    m = int(0.014 * sr)
                    if i + m >= n:
                        continue
                    tt = np.arange(m) / sr
                    cr[i:i + m] += np.sin(2 * np.pi * f * tt) * np.hanning(m) * (0.6 + 0.4 * k / 2)
        S['amb_crickets'] = self._snd(cr, 0.35)

        n = sr * 8
        t = np.arange(n) / sr
        wind = self._band(self._noise(n), 150, 1100, 1.0) * (0.45 + 0.35 * np.sin(2 * np.pi * t / 8) + 0.2 * np.sin(2 * np.pi * t * 3 / 8))
        S['amb_wind'] = self._snd(wind, 0.5)

        n = sr * 6
        t = np.arange(n) / sr
        fount = self._band(self._noise(n), 700, 6000, 0.4) * (0.8 + 0.2 * np.sin(2 * np.pi * t / 3))
        for _ in range(260):              # little droplets landing in the basin
            i = r.randrange(n - 600)
            f = r.uniform(900, 2200)
            tt = np.arange(500) / sr
            fount[i:i + 500] += (np.sin(2 * np.pi * (f + 3000 * tt) * tt) * np.exp(-tt * 120)
                                 * r.uniform(0.6, 1.6) * np.std(fount))
        S['amb_fountain'] = self._snd(fount, 0.5)
        # --- footsteps on cobbles: a soft thud and a little scuff, four takes so they never repeat
        for i in range(4):
            t = self._t(0.12)
            thud = self._band(self._noise(len(t)), 60, 500) * np.exp(-t * (60 + i * 6))
            scuff = self._band(self._noise(len(t)), 1500, 6000) * np.exp(-t * (110 + i * 15)) * 0.35
            S['step%d' % i] = self._snd(thud + scuff, 0.32)
        # --- townsfolk chatter: little murmured syllables, not words
        for i in range(6):
            parts = []
            off = 0.0
            base = r.uniform(170, 300)
            for _ in range(r.randint(3, 6)):
                d = r.uniform(0.06, 0.11)
                t = self._t(d)
                f = base * r.uniform(0.85, 1.25) * (1 + 0.1 * np.sin(2 * np.pi * 9 * t))
                ph = 2 * np.pi * np.cumsum(f) / sr
                v = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.hanning(len(t))
                parts.append((off, self._band(v, 120, 2400), 1.0))
                off += d + r.uniform(0.01, 0.05)
            S['chat%d' % i] = self._snd(self._mix(parts, off + 0.05), 0.22)
        # --- one-shots
        x, t = self._sweep(700, 160, 0.28, 22)
        S['plop'] = self._snd(x * np.exp(-t * 14) + self._band(self._noise(len(t)), 800, 5000) * np.exp(-t * 60) * 0.4, 0.7)
        x, t = self._sweep(1300, 500, 0.12, 40)
        S['nibble'] = self._snd(x * np.exp(-t * 35), 0.35)
        for i, (dur, dec, pk) in enumerate(((0.7, 6, 0.75), (0.35, 12, 0.45))):
            t = self._t(dur)
            nz = self._band(self._noise(len(t)), 300, 6000) * np.exp(-t * dec) * (1 - np.exp(-t * 200))
            lo, _ = self._sweep(400, 120, dur, 18)
            S['splash' if i == 0 else 'splash_small'] = self._snd(nz + lo * np.exp(-t * 10) * 0.6, pk)
        t = self._t(0.4)
        S['cast'] = self._snd(self._band(self._noise(len(t)), 700, 4000) * np.sin(np.pi * t / 0.4) ** 2, 0.45)
        t = self._t(0.03)
        S['click'] = self._snd(self._band(self._noise(len(t)), 2000, 9000) * np.exp(-t * 260), 0.3)
        x, t = self._sweep(400, 120, 0.6, 5)
        S['snap'] = self._snd(x * np.exp(-t * 6) + self._band(self._noise(len(t)), 1500, 8000) * np.exp(-t * 40), 0.6)
        t = self._t(0.35)
        creak = np.sign(np.sin(2 * np.pi * (90 + 20 * np.sin(2 * np.pi * 7 * t)) * t))
        S['creak'] = self._snd(self._band(creak, 80, 900) * np.sin(np.pi * t / 0.35), 0.25)
        x, t = self._sweep(900, 300, 0.4, 14)
        bite = x * np.exp(-t * 8) + self._band(self._noise(len(t)), 400, 6000) * np.exp(-t * 14) * 0.7
        S['bite'] = self._snd(bite, 0.8)
        S['warn'] = self._snd(self._mix([(0, self._bell(1320, 0.18, 30), 1), (0.09, self._bell(1760, 0.2, 28), 1),
                                         (0, self._band(self._noise(int(sr * 0.25)), 600, 4000)
                                          * np.exp(-self._t(0.25) * 18), 0.5)], 0.32), 0.45)
        S['coin'] =self._snd(self._mix([(0, self._bell(1568, 0.5, 8), 1), (0.07, self._bell(2093, 0.6, 7), 1)], 0.7), 0.4)
        t = self._t(0.18)
        S['page'] = self._snd(self._band(self._noise(len(t)), 900, 5000) * np.sin(np.pi * t / 0.18), 0.3)
        t = self._t(1.3)
        purr = self._band(self._noise(len(t)), 30, 260) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t)) ** 2 * np.sin(np.pi * t / 1.3)
        S['purr'] = self._snd(purr, 0.6)
        t = self._t(0.09)
        S['ui'] = self._snd(np.sin(2 * np.pi * 880 * t) * np.exp(-t * 45) + 0.4 * np.sin(2 * np.pi * 1320 * t) * np.exp(-t * 60), 0.3)
        t = self._t(3.5)
        brown = np.cumsum(self._noise(len(t)))
        th = self._band(brown, 25, 320) * np.exp(-t * 1.1) * (1 - np.exp(-t * 18))
        S['thunder'] = self._snd(th, 0.7)
        # melodic stingers
        def arp(freqs, gap, dur=2.6, inst=None):
            inst = inst or self._kalimba
            return self._mix([(i * gap, inst(f), 1.0) for i, f in enumerate(freqs)], dur)
        C5, E5, G5, A5, C6, D6, E6, G6 = 523.25, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.5, 1568.0
        S['jingle1'] = self._snd(arp([C5, E5, G5], 0.08), 0.5)
        S['jingle2'] = self._snd(arp([C5, E5, G5, C6], 0.08), 0.5)
        S['jingle3'] = self._snd(arp([G5, C6, E6, G6], 0.09, 3.0, lambda f: self._bell(f, 2.0, 3)), 0.5)
        S['jingle4'] = self._snd(arp([C5, E5, G5, C6, E6, G6], 0.08, 3.2, lambda f: self._bell(f, 2.2, 2.6)), 0.5)
        S['jingle5'] = self._snd(arp([C5, G5, C6, E6, G6, C6 * 2, G6, C6 * 2], 0.1, 4, lambda f: self._bell(f, 2.6, 2.2)), 0.5)
        S['wish'] = self._snd(arp([G6, E6 * 1.5, D6 * 2, G6 * 2], 0.07, 2.6, lambda f: self._bell(f, 2.0, 3)), 0.35)
        S['hook'] = self._snd(arp([G5, D6], 0.05, 1.2), 0.45)
        S['sad'] = self._snd(arp([E5, C5, A5 / 2], 0.14, 2.0), 0.4)
        for i in range(5):
            S['chime%d' % i] = self._snd(self._bell([C6, D6, E6, G6, A5 * 2][i], 2.5, 1.8), 0.25)
        for i in range(4):
            parts = []
            off = 0.0
            for _ in range(r.randint(2, 5)):
                d = r.uniform(0.05, 0.11)
                f0, f1 = r.uniform(2600, 4200), r.uniform(3000, 5200)
                t = self._t(d)
                f = f0 + (f1 - f0) * t / d + 300 * np.sin(2 * np.pi * 40 * t)
                parts.append((off, np.sin(2 * np.pi * np.cumsum(f) / sr) * np.hanning(len(t)), 1.0))
                off += d + r.uniform(0.03, 0.08)
            S['bird%d' % i] = self._snd(self._mix(parts, off + 0.05), 0.25)
        # --- the camera, the watering can and a few animal calls (wildlife.py, garden.py)
        t = self._t(0.16)
        sh = self._band(self._noise(len(t)), 1500, 9000) * (np.exp(-t * 90) + 0.7 * (t > 0.08) * np.exp(-np.maximum(t - 0.08, 0) * 110))
        S['shutter'] = self._snd(sh, 0.4)
        t = self._t(0.9)
        S['water'] = self._snd(self._band(self._noise(len(t)), 500, 3500) * np.sin(np.pi * t / 0.9) ** 0.5
                               * (0.7 + 0.3 * np.sin(2 * np.pi * 9 * t)), 0.25)
        t = self._t(2.4)
        f = 620 + 300 * np.sin(np.pi * np.minimum(t / 1.6, 1.0)) + 12 * np.sin(2 * np.pi * 6 * t)
        ph = 2 * np.pi * np.cumsum(f) / sr
        S['loon'] = self._snd((np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.sin(np.pi * t / 2.4) ** 0.7, 0.3)

        def hoot(f0, d):
            t = self._t(d)
            return (np.sin(2 * np.pi * f0 * t) + 0.2 * np.sin(4 * np.pi * f0 * t)) * np.sin(np.pi * t / d) ** 1.5
        S['hoot'] = self._snd(self._mix([(0, hoot(380, 0.28), 1), (0.42, hoot(350, 0.55), 1)], 1.1), 0.32)

        # --- pads for the music
        def mf(m):
            return 440.0 * 2 ** ((m - 69) / 12)
        chords = [(48, 55, 60, 64), (45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 59)]
        self.chord_tones = [[c[1] + 12, c[2] + 12, c[3] + 12] for c in chords]
        self.pad_sounds = []
        t = self._t(9.0)
        env = np.minimum(1, t / 2.5) * np.minimum(1, (9.0 - t) / 3.0)
        for ch in chords:
            x = np.zeros(len(t))
            for m in ch:
                f = mf(m)
                x += np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.004 * t) + 0.15 * np.sin(2 * np.pi * f * 2 * t)
            x *= env * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t))
            self.pad_sounds.append(self._snd(x, 0.5))
        self.mf = mf

    def acc_note(self, m, dur=0.42):
        """A squeezebox note for the bandstand: reedy harmonics with a slow wobble."""
        key = ('acc', m, dur)
        snd = self.notes.get(key)
        if snd is None:
            f = self.mf(m)
            t = self._t(dur)
            env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.08)
            x = np.zeros(len(t))
            for h, a in ((1, 1.0), (2, 0.55), (3, 0.4), (4, 0.22), (5, 0.12)):
                x += a * (np.sin(2 * np.pi * f * h * t) + 0.6 * np.sin(2 * np.pi * f * 1.006 * h * t))
            x *= env * (0.9 + 0.1 * np.sin(2 * np.pi * 5.5 * t))
            snd = self._snd(x, 0.5)
            self.notes[key] = snd
        return snd

    def note(self, m):
        s = self.notes.get(m)
        if s is None:
            s = self._snd(self._kalimba(self.mf(m)), 0.6)
            self.notes[m] = s
        return s

    # ------------------------------------------------------------ playback
    def play(self, name, vol=1.0, pan=0.5):
        if not self.ok:
            return
        s = self.sounds.get(name)
        if s is None:
            return
        ch = s.play()
        if ch:
            v = vol * self.sfx_vol
            ch.set_volume(v * min(1.0, 2 * (1 - pan)), v * min(1.0, 2 * pan))

    def update(self, dt, env, ctx):
        """ctx: dict with flags like night, crickets, feeder, chimes, menu."""
        if not self.ok:
            return
        rain = env.rain
        night = env.nf
        winter = env.season == 3
        town = ctx.get('town')
        targets = {
            'water': 0.32 if ctx.get('sea') else 0.08 if town else 0.45,
            'fountain': ctx.get('fountain', 0.0) * 0.35,
            'rain': rain * 0.75,
            'crickets': night * (0 if winter else 1) * (1 - rain) * 0.32,
            'wind': min(1.0, env.snow * 0.6 + env.fog * 0.25 + (0.25 if winter else 0.05) + rain * 0.2) * 0.45,
        }
        for k, ch in self.amb.items():
            cur = self.cur_amb[k]
            cur += (targets[k] - cur) * min(1, dt * 0.8)
            self.cur_amb[k] = cur
            ch.set_volume(cur * self.amb_vol)
        # birds during the day
        self.bird_t -= dt
        if self.bird_t <= 0:
            self.bird_t = random.uniform(3, 9) / (2.0 if ctx.get('feeder') else 1.0)
            if env.nf < 0.3 and rain < 0.3 and env.season != 3:
                self.play('bird%d' % random.randrange(4), random.uniform(0.25, 0.55) * self.amb_vol, random.random())
        if ctx.get('chimes'):
            self.chime_t -= dt
            if self.chime_t <= 0:
                self.chime_t = random.uniform(2.5, 9)
                for i in range(random.randint(1, 3)):
                    self.play('chime%d' % random.randrange(5), random.uniform(0.2, 0.4) * self.amb_vol, 0.2)
        # the murmur of neighbours nearby
        chat = ctx.get('chatter')
        if chat:
            self.chat_t -= dt
            if self.chat_t <= 0:
                self.chat_t = random.uniform(1.8, 5.0)
                self.play('chat%d' % random.randrange(6), chat[0] * random.uniform(0.25, 0.45) * self.amb_vol, chat[1])
        self.band_vol += (ctx.get('band', 0.0) - self.band_vol) * min(1, dt * 1.5)
        self._band_music(dt)
        self._music(dt, env, quiet=self.band_vol > 0.3, town=bool(ctx.get('town')))

    def step(self, vol=0.3):
        self.play('step%d' % random.randrange(4), vol * random.uniform(0.7, 1.0), random.uniform(0.42, 0.58))

    def chat(self, vol=0.5):
        self.play('chat%d' % random.randrange(6), vol)

    def _band_music(self, dt):
        """Evenings with a bandstand: a jaunty squeezebox tune that gets louder as you walk up."""
        v = self.band_vol * self.music_vol
        if v < 0.02:
            self.band_t = 0.0
            return
        self.band_t += dt
        if self.band_t < 0.3:
            return
        self.band_t -= 0.3
        n = self.band_n
        self.band_n += 1
        chord = self.chord_tones[self.chord_i]
        if n % 4 == 0:                                   # oom..
            ch = self.acc_note(chord[0] - 24, 0.32).play()
            if ch:
                ch.set_volume(v * 0.45)
        elif n % 4 == 2:                                 # ..pah
            ch = self.acc_note(chord[1] - 12, 0.2).play()
            if ch:
                ch.set_volume(v * 0.3)
        if random.random() < 0.7:                        # the melody wanders up and down the scale
            i = BAND_SCALE.index(self.band_m) if self.band_m in BAND_SCALE else 5
            i = max(0, min(len(BAND_SCALE) - 1, i + random.choice((-2, -1, -1, 1, 1, 2, 0))))
            if n % 4 == 0 and random.random() < 0.6:
                near = [m for m in BAND_SCALE if (m - chord[0]) % 12 in (0, 4, 7)]
                i = BAND_SCALE.index(min(near, key=lambda m: abs(m - BAND_SCALE[i])))
            self.band_m = BAND_SCALE[i]
            ch = self.acc_note(self.band_m + 12, 0.42 if random.random() < 0.7 else 0.6).play()
            if ch:
                ch.set_volume(v * 0.42)
        if n % 32 == 0:
            self.chord_i = (self.chord_i + 1) % 4

    # each season has its own feel: bright spring, lazy summer (with a lydian lift), autumn in a minor key,
    # and slow, high, bell-like winter
    SEASON_TONES = {0: [60, 62, 64, 67, 69, 72, 74, 76], 1: [62, 64, 66, 67, 69, 71, 74, 76, 78],
                    2: [57, 60, 62, 64, 67, 69, 72], 3: [64, 67, 69, 72, 74, 76, 79, 81]}
    SEASON_BEAT = {0: 0.62, 1: 0.58, 2: 0.7, 3: 0.78}
    SEASON_P = {0: 0.42, 1: 0.46, 2: 0.36, 3: 0.3}

    def _music(self, dt, env, quiet=False, town=False):
        if self.music_vol <= 0.001:
            return
        season = env.season if env.season in self.SEASON_BEAT else 0
        beat = self.SEASON_BEAT[season] if env.nf < 0.5 else 0.8
        if town and env.nf < 0.5:
            beat *= 0.9                              # a little brisker in the village
        self.beat_t += dt
        if self.beat_t < beat:
            return
        self.beat_t -= beat
        if self.beat_n % 16 == 0:
            self.chord_i = (self.chord_i + 1) % 4
            old = self.pads[self.pad_i]
            old.fadeout(3000)
            self.pad_i = 1 - self.pad_i
            ch = self.pads[self.pad_i]
            ch.play(self.pad_sounds[self.chord_i], fade_ms=1500)
            ch.set_volume(self.music_vol * 0.32)
        self.beat_n += 1
        p = self.SEASON_P[season] if env.nf < 0.5 else 0.3
        if quiet:
            p *= 0.2
        if town and not quiet and self.beat_n % 4 == 0:   # Fernwick gets a soft walking bass
            ch = self.note(self.chord_tones[self.chord_i][0] - 24).play()
            if ch:
                ch.set_volume(self.music_vol * 0.3)
        if random.random() < p:
            tones = self.chord_tones[self.chord_i] + self.SEASON_TONES[season]
            m = random.choice(tones)
            if env.nf > 0.5 and m > 72:
                m -= 12
            ch = self.note(m).play()
            if ch:
                v = self.music_vol * random.uniform(0.25, 0.45)
                pan = random.uniform(0.3, 0.7)
                ch.set_volume(v * min(1, 2 * (1 - pan)), v * min(1, 2 * pan))

    def set_music(self, v):
        self.music_vol = max(0.0, min(1.0, v))
        if self.ok:
            for ch in self.pads:
                ch.set_volume(self.music_vol * 0.32)
