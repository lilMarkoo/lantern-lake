"""The game's little tunes: one written melody for each season by day, for dawn, for dusk, for night and for the
village. A tune plays through once over a slow pad, then the music rests for a while and you just hear the lake.

Each bar is a chord and eight steps of melody ('-' holds: the kalimba rings on). All the tunes are original."""
import random

NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9,
        'Bb': 10, 'B': 11}

CH = {'C': (48, 55, 60, 64), 'Cmaj7': (48, 55, 59, 64), 'Dm': (50, 53, 57, 62), 'D': (50, 54, 57, 62),
      'Em': (52, 55, 59, 64), 'E': (52, 56, 59, 64), 'F': (41, 48, 53, 57), 'Fmaj7': (41, 48, 52, 57),
      'G': (43, 50, 55, 59), 'Am': (45, 52, 57, 60), 'A': (45, 52, 57, 61), 'Bm': (47, 54, 59, 62),
      'Bb': (46, 53, 58, 62)}

REST = (22.0, 48.0)       # seconds of quiet between tunes


def midi(tok):
    name, octave = tok[:-1], int(tok[-1])
    return 12 * (octave + 1) + NOTE[name]


def _tune(tid, name, beat, rows):
    bars = []
    for chord, mel in rows:
        steps = mel.split()
        assert len(steps) == 8, (tid, mel)
        bars.append((CH[chord], [None if s == '-' else midi(s) for s in steps]))
    return dict(id=tid, name=name, beat=beat, bars=bars)


TUNES = [
    _tune('spring', 'Thaw', 0.5, [
        ('C', 'E5 - G5 - A5 - G5 -'), ('F', 'A5 - C6 - A5 G5 E5 -'), ('Am', 'C5 - E5 - G5 - E5 D5'),
        ('G', 'D5 - - - - - - -'), ('C', 'E5 - G5 - A5 - C6 -'), ('F', 'D6 - C6 - A5 - G5 -'),
        ('Dm', 'F5 - E5 - D5 - E5 -'), ('C', 'C5 - - - - - - -')]),
    _tune('summer', 'Long Afternoon', 0.55, [
        ('G', 'B4 - D5 - G5 - - F#5'), ('Em', 'E5 - - - D5 - B4 -'), ('C', 'C5 - E5 - G5 - A5 -'),
        ('D', 'F#5 - - - A5 - - -'), ('G', 'G5 - B5 - A5 - G5 -'), ('Em', 'E5 - G5 - F#5 - E5 -'),
        ('C', 'D5 - E5 - C5 - A4 -'), ('G', 'B4 - - - G4 - - -')]),
    _tune('autumn', 'Woodsmoke', 0.62, [
        ('Am', 'A4 - C5 - E5 - D5 -'), ('F', 'C5 - - A4 - - G4 -'), ('C', 'G4 - C5 - E5 - G5 -'),
        ('G', 'F5 - E5 - D5 - - -'), ('Am', 'E5 - A5 - G5 - E5 -'), ('F', 'F5 - E5 - C5 - A4 -'),
        ('Dm', 'D5 - F5 - E5 - D5 -'), ('Am', 'A4 - - - - - - -')]),
    _tune('winter', 'First Snow', 0.72, [
        ('Cmaj7', 'G5 - - - E5 - - -'), ('Fmaj7', 'A5 - - - C6 - - -'), ('Am', 'B5 - A5 - E5 - - -'),
        ('G', 'D5 - - - - - - -'), ('Cmaj7', 'E5 - G5 - B5 - - -'), ('Fmaj7', 'A5 - G5 - E5 - - -'),
        ('Dm', 'F5 - E5 - D5 - - -'), ('C', 'C5 - - - - - - -')]),
    _tune('dawn', 'Mist on the Water', 0.68, [
        ('F', 'C5 - - F5 - - A5 -'), ('C', 'G5 - - - E5 - - -'), ('Dm', 'F5 - - D5 - - A4 -'),
        ('C', 'C5 - - - - - - -'), ('F', 'A5 - - C6 - - A5 -'), ('Bb', 'D6 - - - C6 - - -'),
        ('C', 'G5 - - E5 - - C5 -'), ('F', 'F5 - - - - - - -')]),
    _tune('dusk', 'Lanterns', 0.66, [
        ('D', 'F#5 - A5 - - - D6 -'), ('Bm', 'B5 - - A5 - F#5 - -'), ('G', 'G5 - B5 - D6 - - B5'),
        ('A', 'A5 - - - - - - -'), ('D', 'F#5 - E5 - D5 - F#5 -'), ('Bm', 'D5 - - B4 - - D5 -'),
        ('G', 'E5 - G5 - F#5 - E5 -'), ('D', 'D5 - - - - - - -')]),
    _tune('night', 'Stars on the Lake', 0.86, [
        ('Am', 'E5 - - - A4 - - -'), ('F', 'C5 - - - - - - -'), ('C', 'E5 - - - G5 - - -'),
        ('E', 'B4 - - - G#4 - - -'), ('Am', 'A4 - - - C5 - - -'), ('Dm', 'D5 - - - F5 - - -'),
        ('Am', 'E5 - - - C5 - - -'), ('Am', 'A4 - - - - - - -')]),
    _tune('town', 'Market Day', 0.42, [
        ('C', 'E5 G5 E5 C5 D5 E5 G5 -'), ('F', 'A5 G5 F5 A5 G5 - E5 -'), ('G', 'D5 E5 F5 D5 B4 D5 G5 -'),
        ('C', 'E5 - C5 - G4 - - -'), ('C', 'E5 G5 E5 C5 D5 E5 G5 -'), ('Am', 'A5 C6 B5 A5 G5 - E5 -'),
        ('G', 'F5 E5 D5 F5 E5 D5 B4 -'), ('C', 'C5 - - - - - - -')]),
]
TUNE_BY_ID = {t['id']: t for t in TUNES}
SEASON_TUNE = {0: 'spring', 1: 'summer', 2: 'autumn', 3: 'winter'}


def mood(env, town=False):
    """Which tune suits the moment."""
    if town and env.nf < 0.5:
        return 'town'
    if env.nf > 0.5:
        return 'night'
    m = env.minute
    if 300 <= m < 450:
        return 'dawn'
    if 1050 <= m < 1250:
        return 'dusk'
    return SEASON_TUNE.get(env.season, 'spring')


def pick(md):
    return TUNE_BY_ID.get(md, TUNE_BY_ID['spring'])


def rest():
    return random.uniform(*REST)
