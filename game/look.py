"""How you look: the character creator's options, and the helpers every scene uses to draw you and Biscuit.

g.look is a small dict of option ids. The default reproduces the angler (and Biscuit) exactly as they have
always looked, so old saves are unchanged until someone opens the creator.
"""
import random

# ---------------------------------------------------------------- the options
# skin: (id, label, skin, blush, eye)
SKINS = (
    ('porcelain', 'Porcelain', (255, 226, 206), (244, 168, 160), (50, 40, 40)),
    ('peach', 'Peach', (240, 202, 172), (236, 160, 150), (50, 40, 40)),
    ('sand', 'Sand', (226, 182, 144), (222, 140, 120), (50, 40, 40)),
    ('honey', 'Honey', (204, 152, 110), (206, 118, 98), (44, 32, 30)),
    ('amber', 'Amber', (176, 122, 84), (186, 98, 84), (36, 26, 24)),
    ('cocoa', 'Cocoa', (140, 94, 64), (160, 82, 72), (28, 20, 20)),
    ('umber', 'Umber', (110, 72, 50), (138, 70, 62), (22, 16, 16)),
    ('ebony', 'Ebony', (84, 56, 42), (116, 60, 54), (18, 12, 12)),
)
HAIRS = (
    ('brown', 'Brown', (112, 72, 52)),
    ('dark', 'Dark', (46, 36, 38)),
    ('blonde', 'Blonde', (226, 188, 108)),
    ('ginger', 'Ginger', (202, 102, 52)),
    ('auburn', 'Auburn', (140, 60, 50)),
    ('silver', 'Silver', (208, 210, 220)),
    ('teal', 'Lake teal', (64, 168, 166)),
    ('rose', 'Rose', (232, 128, 160)),
    ('lavender', 'Lavender', (166, 138, 222)),
    ('sky', 'Sky', (104, 158, 230)),
)
HSTYLES = (('side', 'Side part'), ('short', 'Short'), ('long', 'Long'), ('ponytail', 'Ponytail'),
           ('bun', 'Bun'), ('curly', 'Curls'), ('buzz', 'Buzz'), ('braids', 'Braids'))
EYES = (('dot', 'Bright'), ('happy', 'Smiley'), ('sleepy', 'Sleepy'), ('glasses', 'Glasses'), ('shades', 'Shades'))
BEARDS = (('none', 'None'), ('stubble', 'Stubble'), ('moustache', 'Moustache'), ('beard', 'Beard'))
TOPS = (('overalls', 'Overalls'), ('tee', 'Striped tee'), ('sweater', 'Knit sweater'), ('raincoat', 'Raincoat'),
        ('vest', 'Angler vest'))
# theme: (id, label, {season: shirt}, accent, scarf)
THEMES = (
    ('classic', 'Classic', {0: (214, 128, 112), 1: (236, 196, 96), 2: (196, 98, 66), 3: (122, 144, 196)},
     (196, 82, 72), (200, 70, 70)),
    ('meadow', 'Meadow', {0: (150, 194, 112), 1: (236, 214, 112), 2: (196, 150, 82), 3: (118, 160, 150)},
     (250, 236, 196), (236, 200, 90)),
    ('harbour', 'Harbour', {0: (92, 128, 178), 1: (238, 238, 230), 2: (64, 94, 146), 3: (48, 66, 108)},
     (226, 80, 70), (236, 236, 228)),
    ('berry', 'Berry', {0: (204, 96, 146), 1: (238, 134, 152), 2: (152, 62, 102), 3: (172, 112, 184)},
     (250, 212, 230), (120, 70, 140)),
    ('ember', 'Ember', {0: (222, 114, 64), 1: (240, 172, 72), 2: (182, 72, 52), 3: (204, 92, 72)},
     (250, 222, 152), (250, 200, 90)),
    ('moss', 'Moss', {0: (112, 142, 92), 1: (156, 172, 92), 2: (132, 112, 62), 3: (92, 122, 102)},
     (214, 194, 142), (182, 120, 70)),
    ('dusk', 'Dusk', {0: (134, 112, 182), 1: (222, 162, 200), 2: (112, 92, 152), 3: (84, 102, 164)},
     (255, 210, 150), (240, 150, 120)),
    ('snow', 'Snow', {0: (228, 230, 238), 1: (250, 246, 234), 2: (210, 212, 222), 3: (238, 242, 252)},
     (118, 160, 212), (92, 140, 202)),
)
PANTS = (('denim', 'Denim', (72, 92, 140)), ('khaki', 'Khaki', (172, 148, 104)), ('black', 'Charcoal', (54, 52, 62)),
         ('forest', 'Forest', (70, 110, 80)), ('rust', 'Rust', (160, 86, 62)), ('cream', 'Cream', (224, 212, 184)))
BOOTS = (('brown', 'Brown boots', (84, 58, 42)), ('black', 'Black boots', (40, 38, 46)),
         ('yellow', 'Yellow wellies', (240, 196, 60)), ('red', 'Red wellies', (204, 66, 66)),
         ('green', 'Green wellies', (82, 142, 82)), ('white', 'White sneakers', (236, 236, 230)))
CHARMS = (('none', 'None', 'Nothing hangs from your rod.'),
          ('bell', 'Little bell', 'It shivers when a fish nibbles.'),
          ('feather', 'Heron feather', 'Found on the dock one misty morning.'),
          ('shell', 'Lake shell', 'Pink inside, like a sunrise.'),
          ('ribbon', 'Red ribbon', 'Tied on for luck. It flutters in the wind.'),
          ('clover', 'Four-leaf clover', 'Pressed flat, and very lucky.'),
          ('star', 'Tin star', 'It catches the starlight after dark.'),
          ('lantern', 'Tiny lantern', 'It glows softly at night.'))
MOODS = (('patient', 'Patient', 'Waits quietly for a bite.'),
         ('hummer', 'Hummer', 'Hums a little tune while waiting.'),
         ('stargazer', 'Stargazer', 'Looks up at the sky, and spots stars at night.'),
         ('fidget', 'Fidgety', 'Taps a foot, ready for the next bite.'),
         ('dozy', 'Dozy', 'Yawns a lot, and nods off after dark.'),
         ('chatty', 'Chatty', 'Has plenty to tell Biscuit.'))
# Biscuit's coat: (id, label, main, white, dark, ears)
COATS = (('tabby', 'Ginger tabby', (232, 150, 78), (250, 240, 228), (192, 110, 56), (240, 170, 160)),
         ('tuxedo', 'Tuxedo', (52, 50, 60), (248, 248, 246), (30, 28, 36), (210, 140, 150)),
         ('grey', 'Grey', (150, 156, 168), (240, 240, 244), (112, 118, 132), (232, 168, 170)),
         ('calico', 'Calico', (246, 236, 220), (255, 255, 255), (222, 132, 64), (240, 170, 160)),
         ('cream', 'Cream', (240, 212, 164), (252, 246, 234), (214, 176, 124), (244, 180, 170)),
         ('siamese', 'Siamese', (238, 226, 206), (250, 246, 238), (96, 70, 60), (120, 90, 80)),
         ('midnight', 'Midnight', (40, 38, 52), (64, 62, 80), (24, 22, 34), (120, 90, 120)))

FIELDS = (('skin', SKINS), ('hair', HAIRS), ('hstyle', HSTYLES), ('eyes', EYES), ('beard', BEARDS),
          ('top', TOPS), ('theme', THEMES), ('pants', PANTS), ('boots', BOOTS), ('charm', CHARMS),
          ('mood', MOODS), ('coat', COATS))
DEFAULT = {'skin': 'peach', 'hair': 'brown', 'hstyle': 'side', 'eyes': 'dot', 'beard': 'none', 'top': 'overalls',
           'theme': 'classic', 'pants': 'denim', 'boots': 'brown', 'charm': 'none', 'mood': 'patient',
           'coat': 'tabby', 'freckles': False, 'blush': True}
_BY = {k: {row[0]: row for row in rows} for k, rows in FIELDS}
_IDS = {k: [row[0] for row in rows] for k, rows in FIELDS}


def clean(d):
    """A complete, valid look from whatever was saved (or sent by a friend's game)."""
    out = dict(DEFAULT)
    if isinstance(d, dict):
        for k, ids in _IDS.items():
            if d.get(k) in ids:
                out[k] = d[k]
        for k in ('freckles', 'blush'):
            if isinstance(d.get(k), bool):
                out[k] = d[k]
    return out


def of(g):
    lk = getattr(g, 'look', None)
    return lk if isinstance(lk, dict) and 'skin' in lk else DEFAULT


def is_default(lk):
    return clean(lk) == DEFAULT


# ---------------------------------------------------------------- over the network: a few characters
_CODE = '0123456789abcdefghijklmnopqrstuvwxyz'


def encode(lk):
    lk = clean(lk)
    s = ''.join(_CODE[_IDS[k].index(lk[k])] for k, _ in FIELDS)
    return s + _CODE[int(lk['freckles']) + 2 * int(lk['blush'])]


def decode(code):
    if not isinstance(code, str) or len(code) != len(FIELDS) + 1:
        return None
    out = {}
    for (k, _), ch in zip(FIELDS, code):
        i = _CODE.find(ch)
        if not 0 <= i < len(_IDS[k]):
            return None
        out[k] = _IDS[k][i]
    f = _CODE.find(code[-1])
    if not 0 <= f < 4:
        return None
    out['freckles'], out['blush'] = bool(f & 1), bool(f & 2)
    return out


# ---------------------------------------------------------------- colours
def skin(lk):
    return _BY['skin'][lk['skin']][2]


def blush(lk):
    return _BY['skin'][lk['skin']][3]


def eye(lk):
    return _BY['skin'][lk['skin']][4]


def hair(lk):
    return _BY['hair'][lk['hair']][2]


def shirt(lk, season):
    return _BY['theme'][lk['theme']][2][season]


def accent(lk):
    return _BY['theme'][lk['theme']][3]


def scarf(lk):
    return _BY['theme'][lk['theme']][4]


def pants(lk):
    return _BY['pants'][lk['pants']][2]


def boots(lk):
    return _BY['boots'][lk['boots']][2]


def coat(lk):
    """Biscuit's (main, white, dark, inner ear) colours."""
    return _BY['coat'][lk['coat']][2:6]


def label(field, oid):
    return _BY[field][oid][1]


def blurb(field, oid):
    row = _BY[field][oid]
    return row[2] if field in ('charm', 'mood') else ''


def options(field):
    return _IDS[field]


def player_colors(g, season):
    """(shirt, hair) for you, in this season."""
    lk = of(g)
    return shirt(lk, season), hair(lk)


def cat_colors(g):
    return coat(of(g))


def random_look(rng=random, keep=None):
    """A surprise look that still goes together: one of a few colour moods, then everything else at random."""
    lk = {k: rng.choice(ids) for k, ids in _IDS.items()}
    lk['freckles'] = rng.random() < 0.35
    lk['blush'] = rng.random() < 0.8
    lk['beard'] = 'none' if rng.random() < 0.6 else lk['beard']
    if rng.random() < 0.7:
        lk['hair'] = rng.choice(('brown', 'dark', 'blonde', 'ginger', 'auburn', 'silver'))
    if keep:
        for k in keep:
            lk[k] = keep[k]
    return clean(lk)
