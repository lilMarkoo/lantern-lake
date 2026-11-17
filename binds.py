"""Rebindable keys. The game logic keeps thinking in its default keys; this layer translates the keys you
chose into those defaults, for presses and for held keys alike."""
import pygame

ACTIONS = [
    ('cast', 'Cast, hook and reel', pygame.K_SPACE),
    ('use', 'Talk, go in, crab pot', pygame.K_e),
    ('left', 'Walk and aim left', pygame.K_a),
    ('right', 'Walk and aim right', pygame.K_d),
    ('journal', 'Journal', pygame.K_j),
    ('shop', 'Shop', pygame.K_s),
    ('cabin', 'Cabin', pygame.K_c),
    ('calendar', 'Calendar', pygame.K_k),
    ('bait', 'Change bait', pygame.K_TAB),
    ('map', 'Lake map', pygame.K_b),
    ('town', 'Fernwick and back', pygame.K_t),
    ('rest', 'Rest until morning', pygame.K_z),
    ('photo', 'Photo mode', pygame.K_p),
    ('music', 'Music on and off', pygame.K_m),
    ('goals', 'Goals', pygame.K_q),
    ('radio', 'Radio', pygame.K_r),
]
DEFAULT = {a: k for a, _, k in ACTIONS}
NAMES = {a: n for a, n, _ in ACTIONS}
# never rebindable: these always do the same thing
FIXED = {pygame.K_ESCAPE, pygame.K_F11, pygame.K_F12, pygame.K_RETURN, pygame.K_KP_ENTER}
SPECIAL = {pygame.K_SPACE: 'Space', pygame.K_TAB: 'Tab', pygame.K_LSHIFT: 'Shift', pygame.K_RSHIFT: 'R Shift',
           pygame.K_LCTRL: 'Ctrl', pygame.K_RCTRL: 'R Ctrl', pygame.K_LALT: 'Alt', pygame.K_RALT: 'R Alt',
           pygame.K_UP: 'Up', pygame.K_DOWN: 'Down', pygame.K_LEFT: 'Left', pygame.K_RIGHT: 'Right',
           pygame.K_BACKSPACE: 'Bksp', pygame.K_CAPSLOCK: 'Caps', pygame.K_BACKQUOTE: '`'}


def key_label(k):
    if k in SPECIAL:
        return SPECIAL[k]
    name = pygame.key.name(k)
    if not name:
        return '?'
    return name.upper() if len(name) == 1 else name.title()[:6]


def clean(b):
    """Only known actions, real key codes, no two actions on one key."""
    out = {}
    if not isinstance(b, dict):
        return out
    used = set()
    for a, _, _ in ACTIONS:
        k = b.get(a)
        try:
            k = int(k)
        except (TypeError, ValueError):
            continue
        if k in FIXED or k <= 0 or k in used:
            continue
        used.add(k)
        if k != DEFAULT[a]:
            out[a] = k
    # a default key taken by another action can't also keep its old job
    final = {}
    for a, _, d in ACTIONS:
        final[a] = out.get(a, d)
    if len(set(final.values())) != len(final):
        return {}
    return out


class Binds:
    def __init__(self, settings):
        self.settings = settings
        self.rebuild()

    def rebuild(self):
        b = clean(self.settings.get('binds'))
        self.settings['binds'] = b
        self.to_default = {}         # the key you press -> the key the game expects
        self.from_default = {}       # the key the game expects -> the key you press
        for a, k in b.items():
            d = DEFAULT[a]
            self.to_default[k] = d
            self.from_default[d] = k
        # keycap labels in hints follow your keys (updated in place: the UI holds on to this dict)
        if not hasattr(self, 'labels'):
            self.labels = {}
        self.labels.clear()
        self.labels.update({key_label(d): key_label(k) for d, k in self.from_default.items()})

    def key_of(self, action):
        return self.settings['binds'].get(action, DEFAULT[action])

    def map(self, k):
        """The key the game should see, or None for a default key whose job moved to another key."""
        if k in self.to_default:
            return self.to_default[k]
        if k in self.from_default:
            return None
        return k

    def held(self, real):
        return Held(real, self) if self.to_default else real

    def assign(self, action, k):
        """Bind a key; if another action had it, they swap. Returns False for keys that can't be bound."""
        if k in FIXED:
            return False
        cur = {a: self.key_of(a) for a in DEFAULT}
        old = cur[action]
        for a, v in cur.items():
            if v == k and a != action:
                cur[a] = old
        cur[action] = k
        self.settings['binds'] = {a: v for a, v in cur.items() if v != DEFAULT[a]}
        self.rebuild()
        return True

    def reset(self):
        self.settings['binds'] = {}
        self.rebuild()

    def changed(self):
        return bool(self.settings['binds'])


class Held:
    """pygame.key.get_pressed(), seen through your bindings."""

    def __init__(self, real, b):
        self.real = real
        self.b = b

    def __getitem__(self, k):
        if k in self.b.from_default:
            return self.real[self.b.from_default[k]]
        if k in self.b.to_default:
            return False             # that physical key does another job now
        return self.real[k]
