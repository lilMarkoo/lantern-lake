"""Static game data: fish, junk, letters, shop items."""

PHASES = ('dawn', 'day', 'dusk', 'night')
SEASONS = ('Spring', 'Summer', 'Autumn', 'Winter')
DAYS_PER_SEASON = 7               # one week per season
WEEKDAYS = ('Moonday', 'Tideday', 'Leafday', 'Feastday', 'Fishday', 'Lanternday', 'Starday')
MINUTES_PER_SECOND = 2.0          # in-game minutes per real second (a day is 12 real minutes)

RARITY_NAMES = {0: 'Treasure', 1: 'Common', 2: 'Uncommon', 3: 'Rare', 4: 'Epic', 5: 'Legendary'}
RARITY_COLORS = {0: (150, 135, 120), 1: (112, 156, 104), 2: (84, 144, 196), 3: (156, 106, 206),
                 4: (226, 136, 58), 5: (228, 178, 40)}
RARITY_WEIGHT = {1: 100, 2: 38, 3: 12, 4: 3.5, 5: 0.9}


def phase_of(minute):
    if 300 <= minute < 420:
        return 'dawn'
    if 420 <= minute < 1080:
        return 'day'
    if 1080 <= minute < 1230:
        return 'dusk'
    return 'night'


def F(id, name, rarity, price, size, shape='normal', c1=(150, 150, 150), c2=(220, 220, 210), c3=None,
      pattern=None, pc=None, phases=None, seasons=None, weather=None, depth=(0.0, 1.0), strength=0.3,
      agility=0.3, glow=None, needs=None, desc='', hint='', behavior=None, event=None, spot=None, method=None,
      year=0):
    if behavior is None:
        behavior = ('darter' if shape == 'small' else 'zigzag' if shape in ('eel', 'spirit') else
                    'calm' if shape in ('round', 'catfish', 'sturgeon', 'axolotl') else 'runner')
    return dict(id=id, name=name, rarity=rarity, price=price, size=size, shape=shape, c1=c1, c2=c2,
                c3=c3 or c1, pattern=pattern, pc=pc, phases=phases, seasons=seasons, weather=weather,
                depth=depth, strength=strength, agility=agility, glow=glow, needs=needs, desc=desc,
                hint=hint, junk=False, behavior=behavior, event=event, spot=spot, method=method, year=year)


FISH = [
    F('minnow', 'Pond Minnow', 1, 4, (3, 8), 'small', (150, 166, 162), (226, 232, 222), pattern='scales',
      depth=(0, 0.6), strength=.12, agility=.45,
      desc="A tiny silver flicker. Every angler's first friend.", hint='Shallow water, any time at all.'),
    F('loach', 'Pebble Loach', 1, 6, (6, 14), 'small', (140, 116, 80), (212, 192, 150), pattern='spots',
      pc=(92, 72, 52), depth=(0, 0.45), strength=.15, agility=.3,
      desc='Hides among the stones and whiskers its way through the mud.', hint='Right beside the dock.'),
    F('bluegill', 'Bluegill', 1, 8, (10, 22), 'round', (70, 112, 134), (236, 162, 82), c3=(60, 92, 112),
      pattern='stripes', pc=(52, 84, 104), phases={'dawn', 'day', 'dusk'}, depth=(0.1, 0.7),
      strength=.25, agility=.35, desc='Round, bold and always hungry.', hint='Any daylight hour.'),
    F('perch', 'Sunny Perch', 1, 9, (12, 25), 'normal', (204, 190, 82), (242, 236, 192), c3=(222, 122, 62),
      pattern='stripes', pc=(94, 112, 62), phases={'dawn', 'day'}, seasons={0, 1}, depth=(0.1, 0.7),
      strength=.28, agility=.35, desc='Wears its stripes like a summer sweater.',
      hint='Spring and summer days.'),
    F('carp', 'Mud Carp', 1, 11, (25, 60), 'round', (152, 122, 72), (216, 192, 132), c3=(132, 96, 62),
      pattern='scales', depth=(0.2, 1.0), strength=.5, agility=.15,
      desc='Slow, steady and surprisingly heavy.', hint='Anywhere a little way out.'),
    F('sunfish', 'Honey Sunfish', 2, 20, (10, 20), 'round', (232, 172, 62), (250, 222, 132), c3=(202, 122, 42),
      pattern='spots', pc=(255, 240, 172), phases={'day'}, seasons={1}, depth=(0.1, 0.6), strength=.3,
      agility=.5, desc='Glows like warm honey in the afternoon light.',
      hint='Summer, in the middle of the day.'),
    F('dace', 'Blossom Dace', 2, 22, (10, 20), 'normal', (222, 152, 172), (250, 226, 232), c3=(240, 182, 202),
      pattern='spots', pc=(255, 242, 246), phases={'dawn', 'day', 'dusk'}, seasons={0}, depth=(0.1, 0.7),
      strength=.25, agility=.6, desc='Arrives with the cherry blossoms and leaves with them.',
      hint='Only in spring.'),
    F('guppy', 'Firefly Guppy', 2, 25, (4, 8), 'small', (62, 92, 72), (172, 222, 122), c3=(222, 242, 122),
      pattern='glow', pc=(242, 255, 152), phases={'dusk', 'night'}, seasons={1}, depth=(0, 0.5),
      strength=.12, agility=.75, glow=(220, 255, 120), desc='Its tail flickers just like the fireflies above.',
      hint='Summer nights, close to shore.'),
    F('char', 'Ember Char', 2, 32, (25, 50), 'normal', (122, 82, 62), (232, 112, 62), c3=(242, 142, 72),
      pattern='spots', pc=(252, 202, 122), phases={'dawn', 'day', 'dusk'}, seasons={2}, depth=(0.3, 0.9),
      strength=.45, agility=.45, desc='Its belly burns orange like falling maple leaves.',
      hint='Autumn, out in the deeper water.'),
    F('trout', 'Rainbow Trout', 2, 28, (25, 55), 'normal', (112, 142, 112), (236, 232, 216), c3=(122, 152, 122),
      pattern='rainbow', pc=(232, 122, 142), phases={'dawn', 'day'}, depth=(0.35, 1.0), strength=.45,
      agility=.55, desc='A streak of pink light under the water.', hint='Mornings and days, further out.'),
    F('bass', 'Moss Bass', 2, 24, (25, 50), 'normal', (92, 122, 62), (222, 226, 172), c3=(82, 106, 56),
      pattern='stripes', pc=(62, 82, 42), depth=(0.3, 1.0), strength=.5, agility=.4,
      desc='A greenish brawler that loves lily pads.', hint='Any time, a little way out.'),
    F('smelt', 'Ghost Smelt', 2, 26, (8, 16), 'small', (192, 206, 216), (236, 242, 246), c3=(212, 222, 236),
      pattern='glow', pc=(255, 255, 255), weather={'fog'}, depth=(0, 0.8), strength=.15, agility=.7,
      glow=(200, 220, 255), desc='Nearly see-through. Some say they are made of fog.',
      hint='Only while fog lies on the lake.'),
    F('catfish', 'Whiskered Catfish', 2, 30, (30, 80), 'catfish', (102, 96, 90), (192, 182, 162),
      c3=(82, 76, 70), pattern='spots', pc=(72, 66, 60), phases={'dusk', 'night'}, depth=(0.4, 1.0),
      strength=.6, agility=.2, desc='Grumpy old whiskers. Comes out when the sun goes down.',
      hint='Dusk and night, deep water.'),
    F('koi', 'Copper Koi', 3, 85, (30, 60), 'round', (226, 112, 52), (250, 246, 236), c3=(242, 152, 92),
      pattern='koi', pc=(250, 246, 236), phases={'day'}, seasons={0, 1, 2}, weather={'clear'},
      depth=(0.2, 0.9), strength=.45, agility=.45,
      desc='Someone released it years ago. It has grown very proud.',
      hint='Clear skies during the day. Never in winter.'),
    F('salmon', 'Duskfin Salmon', 3, 75, (45, 80), 'normal', (152, 92, 112), (242, 172, 152), c3=(202, 102, 112),
      pattern='scales', phases={'dusk'}, depth=(0.45, 1.0), strength=.7, agility=.65,
      desc='Turns the colour of the sunset as it swims.', hint='Only at dusk, far from the dock.'),
    F('pike', 'Frost Pike', 3, 90, (50, 100), 'long', (152, 186, 202), (232, 242, 246), c3=(122, 162, 186),
      pattern='stripes', pc=(112, 146, 172), seasons={3}, depth=(0.45, 1.0), strength=.75, agility=.6,
      desc='Cold-eyed hunter of the winter lake.', hint='Winter, in deep water.'),
    F('eel', 'Lantern Eel', 3, 95, (50, 110), 'eel', (52, 62, 92), (112, 132, 172), c3=(122, 222, 232),
      pattern='glow', pc=(152, 255, 242), phases={'night'}, depth=(0.55, 1.0), strength=.6, agility=.85,
      glow=(120, 240, 230), desc='Little lights run down its back like a string of lanterns.',
      hint='Night, far from shore.'),
    F('gar', 'Thunder Gar', 3, 110, (70, 140), 'gar', (112, 122, 92), (202, 202, 172), c3=(92, 102, 76),
      pattern='spots', pc=(72, 76, 56), weather={'rain'}, depth=(0.5, 1.0), strength=.8, agility=.7,
      desc='Rises from the deep when thunder rolls.', hint='Only in the rain, deep water.'),
    F('axolotl', 'Lotus Axolotl', 4, 200, (15, 28), 'axolotl', (246, 172, 192), (252, 216, 226),
      c3=(232, 92, 132), weather={'rain'}, seasons={0, 1}, depth=(0, 0.45), strength=.3, agility=.5,
      desc='Not technically a fish. Smiles anyway.', hint='Rainy spring or summer days, near the dock.'),
    F('aurora', 'Aurora Trout', 4, 240, (40, 70), 'normal', (92, 162, 172), (202, 242, 222), c3=(162, 122, 222),
      pattern='rainbow', pc=(182, 142, 242), phases={'night'}, seasons={3}, weather={'clear', 'snow'},
      depth=(0.5, 1.0), strength=.65, agility=.7, glow=(150, 230, 220),
      desc='Carries the northern lights in its scales.', hint='Winter nights.'),
    F('sturgeon', 'Moonscale Sturgeon', 4, 260, (100, 200), 'sturgeon', (122, 132, 162), (212, 216, 232),
      c3=(102, 112, 142), pattern='scutes', pc=(236, 242, 255), phases={'night'}, weather={'clear', 'cloudy'},
      depth=(0.65, 1.0), strength=.9, agility=.45,
      desc='Ancient and patient. Loves a bright moon.',
      hint='A night with open skies, very deep water. A full moon helps.'),
    F('whiskers', 'Old Whiskers', 5, 800, (150, 240), 'catfish', (72, 72, 62), (162, 152, 132), c3=(56, 56, 48),
      pattern='spots', pc=(112, 106, 92), phases={'night'}, weather={'rain'}, depth=(0.85, 1.0),
      strength=1.0, agility=.55, desc='The legend of the lake. Grandpa swore it stole his hat.',
      hint='A rainy night, at the very edge of a long cast.'),
    F('sunpetal', 'Sunpetal Koi', 5, 750, (50, 90), 'round', (252, 202, 72), (255, 246, 202), c3=(255, 172, 92),
      pattern='koi', pc=(255, 250, 232), phases={'dawn'}, seasons={1}, weather={'clear'}, depth=(0.8, 1.0),
      strength=.85, agility=.75, glow=(255, 220, 120), desc='Only rises to greet a clear summer sunrise.',
      hint='Summer dawn, clear skies, very far out.'),
    F('spirit', 'Lake Spirit', 5, 1500, (80, 160), 'spirit', (172, 212, 242), (232, 246, 255), c3=(202, 232, 255),
      pattern='glow', pc=(255, 255, 255), phases={'night'}, weather={'fog'}, depth=(0.9, 1.0), strength=.95,
      agility=.9, glow=(190, 230, 255), needs='starlight',
      desc='Did that really happen? The lake feels a little brighter now.',
      hint='A foggy night. Only a rod made of starlight can reach it.'),
    # event fish: only show up on special days of the calendar
    F('goldfish', 'Festival Goldfish', 3, 70, (8, 18), 'round', (244, 128, 48), (255, 214, 150), c3=(250, 90, 60),
      pattern='koi', pc=(255, 244, 220), depth=(0, 0.8), strength=.3, agility=.55, event='festival',
      desc='Won at a fair long ago and set free. Comes back every festival to show off.',
      hint='Only on a festival day (Feastday).'),
    F('tetra', 'Glowbelly Tetra', 3, 95, (5, 10), 'small', (60, 70, 120), (130, 220, 255), c3=(255, 120, 200),
      pattern='glow', pc=(160, 240, 255), phases={'dusk', 'night'}, depth=(0, 0.7), strength=.2, agility=.85,
      glow=(150, 220, 255), event='lantern', behavior='zigzag',
      desc='Follows the paper lanterns around like a tiny lantern of its own.',
      hint='Summer Lantern Night, after dark.'),
    F('shiner', 'Starfall Shiner', 4, 230, (12, 24), 'normal', (70, 80, 150), (220, 230, 255), c3=(250, 240, 170),
      pattern='glow', pc=(255, 250, 200), phases={'night'}, depth=(0.3, 1.0), strength=.55, agility=.8,
      glow=(255, 240, 170), event='meteor', behavior='darter',
      desc='Some say each one is a wish that fell into the lake and decided to stay.',
      hint='Only during a Starday meteor shower.'),
]
# fish that only live at the spots you reach by rowboat (appended so the first journal page stays the same)
FISH += [
    F('bullhead', 'Mud Bullhead', 1, 10, (15, 30), 'catfish', (112, 94, 66), (200, 186, 150), c3=(92, 76, 54),
      pattern='spots', pc=(84, 68, 50), depth=(0, 0.7), strength=.35, agility=.25, spot='cove',
      desc='A whiskery little grump that loves the warm mud under the lily pads.',
      hint='Lily Cove, any time of day.'),
    F('gourami', 'Lily Gourami', 2, 26, (8, 16), 'round', (206, 150, 196), (250, 226, 240), c3=(170, 120, 200),
      pattern='spots', pc=(255, 244, 250), phases={'dawn', 'day'}, seasons={0, 1}, depth=(0, 0.6),
      strength=.25, agility=.55, spot='cove',
      desc='Builds tiny bubble nests under the lily pads and guards them very seriously.',
      hint='Lily Cove, spring and summer days.'),
    F('tench', 'Velvet Tench', 3, 80, (25, 50), 'round', (70, 110, 64), (196, 190, 112), c3=(56, 88, 52),
      pattern='scales', phases={'dawn', 'dusk'}, weather={'cloudy', 'rain', 'fog'}, depth=(0.2, 0.7),
      strength=.55, agility=.35, glow=None, spot='cove', behavior='calm',
      desc='Soft as moss and gold-eyed. Old stories call it the doctor of the pond.',
      hint='Lily Cove at dawn or dusk, under grey skies.'),
    F('cisco', 'Silver Cisco', 2, 30, (20, 40), 'normal', (150, 170, 196), (236, 242, 250), c3=(112, 134, 170),
      pattern='scales', depth=(0.4, 1.0), strength=.4, agility=.6, spot='deep',
      desc='Travels in big shining schools far below the boat.', hint='The Deep, any time.'),
    F('burbot', 'Midnight Burbot', 3, 105, (40, 90), 'long', (86, 80, 62), (176, 166, 128), c3=(66, 60, 48),
      pattern='spots', pc=(56, 50, 40), phases={'dusk', 'night'}, seasons={2, 3}, depth=(0.6, 1.0),
      strength=.7, agility=.5, spot='deep',
      desc='A cold-water cousin of the cod that only wakes up on long autumn and winter nights.',
      hint='The Deep, autumn and winter nights.'),
    F('muskie', 'Mossback Muskie', 5, 950, (120, 180), 'long', (110, 130, 84), (222, 220, 180), c3=(84, 104, 62),
      pattern='stripes', pc=(70, 90, 52), phases={'dusk'}, depth=(0.9, 1.0), strength=1.0, agility=.7,
      spot='deep', desc='Older than the cabin. Fishermen call it the fish of ten thousand casts.',
      hint='The Deep at dusk, at the very end of a long cast.'),
    F('chub', 'Creek Chub', 1, 7, (8, 18), 'normal', (132, 140, 104), (224, 226, 204), c3=(110, 120, 88),
      pattern='scales', depth=(0, 0.8), strength=.2, agility=.45, spot='creek',
      desc='Cheerful, greedy and found in every stream that ever was.', hint='Willow Creek, any time.'),
    F('grayling', 'Sail Grayling', 3, 75, (25, 45), 'normal', (120, 120, 150), (220, 214, 236), c3=(170, 110, 170),
      pattern='spots', pc=(240, 210, 255), phases={'dawn', 'day'}, seasons={0, 2}, depth=(0.3, 0.9),
      strength=.45, agility=.7, spot='creek',
      desc='Raises a purple fin like a little sail when it turns in the current.',
      hint='Willow Creek, spring and autumn mornings.'),
    F('riverking', 'River King Salmon', 4, 290, (70, 120), 'normal', (176, 62, 58), (246, 180, 150),
      c3=(120, 40, 44), pattern='spots', pc=(60, 30, 30), seasons={2}, depth=(0.5, 1.0), strength=.9,
      agility=.65, spot='creek',
      desc='Comes home from the sea each autumn, red as a maple leaf, to the creek where it hatched.',
      hint='Willow Creek in autumn, when the salmon run upstream.'),
]
# seasonal and special fish: they live on the journal's third page. 'method' says how you catch them:
# 'pot' crab pot, 'ice' ice fishing, 'fly' fly casting at the creek, 'storm' / 'aurora' those rare nights,
# 'year2' new arrivals from year two on (year=1)
FISH += [
    F('crayfish', 'Mud Crayfish', 1, 12, (6, 14), 'crayfish', (150, 72, 52), (204, 120, 86), spot='pot', method='pot',
      strength=.1, agility=.2, desc='Walks backwards when it is cross, which is often.',
      hint='Leave a crab pot off the dock overnight.'),
    F('rivercrab', 'River Crab', 2, 26, (8, 16), 'crab', (120, 92, 70), (214, 156, 112), spot='pot', method='pot',
      strength=.1, agility=.2, desc='Sideways, always sideways. It has places to be.',
      hint='A crab pot, overnight. More in summer and autumn.'),
    F('moonsnail', 'Moon Snail', 2, 22, (4, 9), 'snail', (190, 168, 136), (236, 224, 204), c3=(140, 120, 150),
      spot='pot', method='pot', strength=.1, agility=.1, desc='Its shell spirals like the night sky.',
      hint='A crab pot. Snails love a pot left out in spring.'),
    F('bluecray', 'Blue Crayfish', 3, 70, (10, 18), 'crayfish', (70, 110, 196), (150, 192, 244), spot='pot',
      method='pot', strength=.1, agility=.2, desc='One in a thousand crayfish is born this blue.',
      hint='A crab pot, now and then. Sweet corn in the pot helps.'),
    F('icefin', 'Icefin Perch', 1, 14, (10, 22), 'normal', (170, 200, 212), (236, 246, 250), c3=(130, 160, 180),
      pattern='stripes', pc=(110, 142, 162), spot='ice', method='ice', strength=.25, agility=.35,
      desc='Swims slow and sleepy under the winter ice.', hint='Ice fishing at Lily Cove in winter.'),
    F('frosttrout', 'Frost Trout', 2, 30, (20, 40), 'normal', (150, 172, 204), (230, 238, 250), pattern='spots',
      pc=(255, 255, 255), spot='ice', method='ice', strength=.4, agility=.45,
      desc='Speckled like snow on a window.', hint='Ice fishing, a little way down.'),
    F('whitefish', 'Glass Whitefish', 3, 60, (25, 45), 'normal', (200, 222, 232), (246, 250, 252),
      glow=(220, 240, 255), spot='ice', method='ice', strength=.5, agility=.5,
      desc='You can almost see through it.', hint='Ice fishing, deep down. Jig patiently.'),
    F('snowcrown', 'Snowcrown Char', 4, 140, (40, 70), 'normal', (222, 92, 80), (250, 250, 250), c3=(240, 240, 250),
      pattern='spots', pc=(255, 255, 255), spot='ice', method='ice', strength=.7, agility=.6,
      desc='Red as a winter berry, with a crown of white spots.', hint='Ice fishing, right at the bottom.'),
    F('mayfly', 'Mayfly Trout', 2, 32, (18, 36), 'normal', (150, 140, 92), (236, 222, 172), c3=(120, 110, 70),
      pattern='spots', pc=(90, 62, 40), phases={'dawn', 'day', 'dusk'}, spot='creek', method='fly', strength=.4,
      agility=.55, desc='Leaps clean out of the water for a passing fly.',
      hint='Fly casting at Willow Creek, by daylight.'),
    F('brookjewel', 'Brook Jewel', 3, 75, (15, 30), 'normal', (60, 112, 82), (242, 152, 92), c3=(230, 92, 72),
      pattern='spots', pc=(252, 222, 122), spot='creek', method='fly', strength=.45, agility=.7,
      desc='Every colour of the creek in one small fish.', hint='Fly casting at Willow Creek, with a good rhythm.'),
    F('thunderfin', 'Thunderfin', 4, 180, (50, 90), 'long', (70, 82, 112), (202, 212, 232), c3=(250, 230, 120),
      pattern='stripes', pc=(250, 230, 120), glow=(250, 240, 160), phases={'dusk', 'night'}, depth=(0.5, 1.0),
      strength=.85, agility=.7, event='storm', method='storm',
      desc='Rises with the lightning and sinks with the dawn.', hint='Only on a stormy night.'),
    F('lightfish', 'Northern Lightfish', 4, 170, (30, 60), 'normal', (80, 200, 162), (222, 250, 240), c3=(200, 122, 222),
      pattern='glow', pc=(180, 255, 220), glow=(160, 255, 200), phases={'night'}, depth=(0.4, 1.0), strength=.6,
      agility=.75, event='aurora', method='aurora',
      desc='It glows in the same colours as the sky above it.', hint='Only under the northern lights, in winter.'),
    F('velvet', 'Velvet Bream', 2, 28, (20, 40), 'round', (122, 82, 112), (222, 192, 212), pattern='scales',
      phases={'dawn', 'day'}, depth=(0.2, 0.8), strength=.35, agility=.35, year=1, method='year2',
      desc='New to the lake. Soft as a cushion, and nearly as lazy.', hint='Year two, any daylight hour.'),
    F('moonbass', 'Moonlit Bass', 3, 85, (30, 55), 'normal', (72, 82, 122), (202, 212, 242), pattern='spots',
      pc=(240, 240, 255), glow=(200, 210, 255), phases={'night'}, depth=(0.4, 1.0), strength=.6, agility=.5,
      year=1, method='year2', desc='Only seen since the lanterns were lit again.',
      hint='Year two, at night, a long cast out.'),
    F('ghostcarp', 'Ghost Carp', 3, 90, (40, 80), 'round', (222, 228, 232), (250, 252, 255), pattern='scales',
      weather={'fog'}, depth=(0.3, 1.0), strength=.6, agility=.3, year=1, method='year2',
      desc='Pale as fog. Old Tom says it was white when he was a boy too.', hint='Year two, on a foggy day.'),
]
FISH_BY_ID = {f['id']: f for f in FISH}

# the four places you can fish. The dock is home; the rest need a rowboat
SPOTS = [
    dict(id='dock', name='Home Dock',
         desc='Your own little dock by the cabin. Biscuit, the mailbox and the kettle are all here.'),
    dict(id='cove', name='Lily Cove',
         desc='Warm, shallow water under the lily pads. Bites come quickly, from small and colourful fish.'),
    dict(id='deep', name='The Deep',
         desc='The middle of the lake, far from shore. Bites are slow, but the fish down there are big, '
              'old and rare.'),
    dict(id='creek', name='Willow Creek',
         desc='Where the river runs in under the willows. The current carries your bobber along.'),
]
SPOT_BY_ID = {s['id']: s for s in SPOTS}
# lake fish that also swim at each rowboat spot (each spot's own fish have spot=...)
SPOT_FISH = {
    'cove': {'minnow', 'loach', 'bluegill', 'perch', 'sunfish', 'dace', 'guppy', 'bass', 'smelt', 'koi',
             'axolotl', 'goldfish', 'tetra'},
    'deep': {'carp', 'trout', 'char', 'catfish', 'salmon', 'pike', 'eel', 'gar', 'aurora', 'sturgeon',
             'whiskers', 'spirit', 'shiner', 'thunderfin', 'lightfish', 'moonbass', 'ghostcarp'},
    'creek': {'minnow', 'loach', 'dace', 'trout', 'char', 'salmon', 'smelt', 'pike', 'goldfish', 'shiner'},
}


def fish_at(spot):
    """Every species that can bite at a spot, in journal order."""
    if spot == 'dock':
        return [f for f in FISH if not f['spot']]
    return [f for f in FISH if (f['spot'] == spot or f['id'] in SPOT_FISH.get(spot, ())) and f['spot'] in
            (None, 'cove', 'deep', 'creek')]


def regular(f):
    """An everyday fish: not one of the seasonal or special ones (for requests, jobs and so on)."""
    return not f.get('method')


def spots_of(fish_id):
    """The spots a species can be caught at."""
    return [s['id'] for s in SPOTS if any(f['id'] == fish_id for f in fish_at(s['id']))]


BOAT = dict(id='boat', name='Rowboat', price=500,
            desc='Oars, a cushion for Biscuit, and three new places to fish. Open the map with B.')
FROST_POINTS = {1: 1, 2: 3, 3: 8, 4: 20, 5: 50}     # Frost Cup scoring by rarity


def J(id, name, price, size, desc, weight):
    return dict(id=id, name=name, rarity=0, price=price, size=size, shape=id, desc=desc, junk=True,
                weight=weight, strength=0.1, agility=0.1, glow=None)


JUNK = [
    J('boot', 'Old Boot', 2, (25, 32), 'Somewhere, someone is hopping around in circles.', 5),
    J('can', 'Tin Can', 1, (10, 12), "Let's keep the lake tidy. Good job.", 5),
    J('driftwood', 'Driftwood', 3, (30, 70), 'Smooth as a river stone. Smells like summer.', 5),
    J('bottle', 'Message in a Bottle', 0, (20, 24), 'There is a rolled-up note inside!', 3),
    J('clam', 'Pearl Clam', 60, (8, 14), 'A tiny pearl winks at you.', 1.2),
]
JUNK_BY_ID = {j['id']: j for j in JUNK}
ALL_BY_ID = dict(FISH_BY_ID, **JUNK_BY_ID)

LETTERS = [
    ("To whoever finds this,",
     "I'm nine and I live across the lake. I am sending this bottle so I have a pen pal. My favourite fish "
     "is the bluegill because it looks like a sunset. Write back! (You can't. It's a bottle. Oh well.)",
     "- Pip"),
    ("Note to self,",
     "The secret to good tea is patience, and the secret to good fishing is also patience. "
     "The secret to patience is tea. It's all connected.",
     "- R."),
    ("Dear Lake,",
     "Thank you for the summer. Thank you for the frogs. Sorry about the sandwich I dropped in 1987.",
     "- a tourist"),
    ("Recipe: Rainy Day Soup",
     "One onion, two carrots, a potato, a handful of thyme, and a window to watch the rain through. "
     "Simmer until the rain stops or you get hungry, whichever comes first.",
     "- Mabel, the bakery"),
    ("If you are reading this,",
     "the big catfish is real. I saw it. It looked at me. It took my hat. I want my hat back.",
     "- Grandpa"),
    ("A poem,",
     "Little bobber, red and white / dancing in the evening light / wait for me, I'll wait for you / "
     "a fish will come. They always do.",
     "- anonymous"),
    ("Lost:",
     "One (1) orange cat named Biscuit. Answers to 'Biscuit', 'snack' and the sound of a can opening. "
     "UPDATE: found. She was on the dock. She is always on the dock.",
     "- Rosie"),
    ("Dear future me,",
     "I hope you still take walks by the water. I hope you still stop to watch the herons. "
     "I hope you learned to cast without hitting the tree.",
     "- past me"),
    ("Map? (sort of)",
     "Deepest part of the lake: past the third lily pad, keep going until the dock looks tiny. "
     "That is where the old ones sleep.",
     "- unknown"),
    ("Happy birthday!",
     "I didn't know your address so I'm trying the lake. If this reaches you, have a slice of cake "
     "and a quiet afternoon. You deserve both.",
     "- Fen"),
]

VILLAGERS = ['Mabel from the bakery', 'Old Tom', 'Juniper', 'Pip (age 9)', 'Mayor Hazel', 'Fen the painter',
             'The librarian']
REQUEST_REASONS = [
    "It's for a family dinner.", "I want to paint one!", "For a very important science project.",
    "My grandmother's recipe calls for it.", "I'd just like to see one up close.",
    "The festival cook asked me to find some.", "Please don't ask why.",
]

# arc: width of the golden reeling arc in degrees, turn: how fast it can swing (degrees per second)
RODS = [
    dict(id='twig', name='Twig Rod', price=0, range=0.6, arc=70, turn=250, reel=1.0, window=0.0, length=26,
         color=(150, 112, 72), desc='A bent stick and a lot of hope.'),
    dict(id='bamboo', name='Bamboo Rod', price=180, range=0.78, arc=82, turn=290, reel=1.15, window=0.1,
         length=30, color=(196, 176, 96), desc='Longer casts, a wider reeling arc.'),
    dict(id='willow', name='Willow Rod', price=650, range=0.92, arc=94, turn=330, reel=1.3, window=0.18,
         length=33, color=(176, 122, 82), desc='Supple and quick. Reaches the deep water.'),
    dict(id='starlight', name='Starlight Rod', price=2200, range=1.0, arc=110, turn=400, reel=1.5, window=0.25,
         length=36, color=(170, 196, 255), glow=True,
         desc='Woven from a falling star.'),
]
ROD_BY_ID = {r['id']: r for r in RODS}

BAITS = [
    dict(id='worm', name='Garden Worms', price=0, pack=0, desc='Free and wriggly. Fish like them fine.'),
    dict(id='corn', name='Sweet Corn', price=40, pack=10, desc='Fish bite much sooner.'),
    dict(id='glow', name='Glow Grubs', price=60, pack=10, desc='Night fish can see it from far away.'),
    dict(id='golden', name='Golden Lure', price=220, pack=5, desc='Rare fish find it irresistible.'),
    dict(id='moon', name='Moon Lure', price=180, pack=3, merchant=True,
         desc='Epic and legendary fish come three times as often at night.'),
    dict(id='storm', name='Storm Fly', price=120, pack=5, merchant=True,
         desc='Rain fish love it, and everything bites sooner in the rain.'),
]
BAIT_BY_ID = {b['id']: b for b in BAITS}

# cosmetics. 'where' tells the player how to find the ones they don't own yet
HATS = [
    dict(id='straw', name='Straw Hat', price=0, where='Your old favourite.'),
    dict(id='bucket', name='Bucket Hat', price=150, where="Sold at Wren's Wagon."),
    dict(id='beret', name='Painter Beret', price=180, where="Sold at Wren's Wagon."),
    dict(id='flower', name='Flower Crown', price=220, where="Sold at Wren's Wagon."),
    dict(id='captain', name='Captain Cap', price=260, where="Sold at Wren's Wagon."),
    dict(id='frog', name='Frog Hat', price=0, gift=True, where="A birthday gift from Pip."),
    dict(id='beanie', name='Cosy Beanie', price=0, gift=True, where='A birthday gift from the librarian.'),
    dict(id='party', name='Party Hat', price=0, gift=True, where="A prize from Pip's ring toss in Fernwick."),
    dict(id='tophat', name='Top Hat', price=0, gift=True, where="A grand prize from Pip's ring toss in Fernwick."),
    dict(id='lanternhat', name='Lantern Hat', price=0, gift=True, where='From the Night of Four Lanterns.'),
]
HAT_BY_ID = {h['id']: h for h in HATS}
CAT_ITEMS = [
    dict(id='none', name='Just Biscuit', price=0, where='Perfect as she is.'),
    dict(id='bell', name='Little Bell', price=90, where="Sold at Wren's Wagon."),
    dict(id='scarf', name='Knitted Scarf', price=140, where="Sold at Wren's Wagon."),
    dict(id='crown', name='Tiny Crown', price=400, where="Sold at Wren's Wagon."),
    dict(id='bow', name='Ribbon Bow', price=0, gift=True, where='A birthday gift from Juniper.'),
]
CAT_BY_ID = {c['id']: c for c in CAT_ITEMS}

DECOR = [
    dict(id='flowers', name='Flower Pots', price=90, desc='A little colour on the dock.'),
    dict(id='teaset', name='Tea Kettle', price=120, desc='Always something warm brewing.'),
    dict(id='catbed', name='Cat Cushion', price=100, desc="Biscuit's new favourite place to nap."),
    dict(id='chimes', name='Wind Chimes', price=140, desc='Sings softly when the breeze comes.'),
    dict(id='feeder', name='Bird Feeder', price=180, desc='Little visitors drop by in the daytime.'),
    dict(id='lights', name='String Lights', price=260, desc='Warm bulbs for long evenings.'),
    dict(id='lanterns', name='Floating Lanterns', price=420, desc='Paper lanterns drift on the lake at night.'),
    dict(id='pinwheel', name='Pinwheel', price=160, desc='Spins in the breeze. Biscuit watches it for hours.'),
    dict(id='telescope', name='Brass Telescope', price=450,
         desc='Spot more shooting stars, and your wishes are luckier.'),
]
GIFT_DECOR = [
    dict(id='bench', name='Garden Bench', desc="Mabel's birthday thank-you. Sit a while."),
    dict(id='rowboat', name='Little Rowboat', desc="Fen's old boat, tied up by the dock."),
    dict(id='gnome', name='Garden Gnome', desc="Old Tom swears it moves at night."),
]

# birthdays: (season, day of the week 1-7) -> who, the fish they would love, and what they send back
BIRTHDAYS = {
    (0, 3): dict(who='Pip', fish='bluegill', gift='hat:frog'),
    (0, 6): dict(who='Mabel', fish='perch', gift='decor:bench'),
    (1, 2): dict(who='Juniper', fish='sunfish', gift='cat:bow'),
    (1, 6): dict(who='Fen', fish='trout', gift='decor:rowboat'),
    (2, 3): dict(who='Old Tom', fish='catfish', gift='decor:gnome'),
    (2, 6): dict(who='The librarian', fish='char', gift='hat:beanie'),
    (3, 2): dict(who='Mayor Hazel', fish='pike', gift='coins:300'),
    (3, 6): dict(who='Grandma Rosie', fish=None, gift='coins:250'),
}

# one festival per season, always on Feastday (day 4)
FESTIVALS = {
    0: dict(name='Blossom Derby', rule='biggest', start=600, end=960,
            desc='Biggest single fish between 10 AM and 4 PM wins.'),
    1: dict(name='Lantern Night', rule='count', start=1200, end=1435,
            desc='Most fish caught between 8 PM and midnight, under the lanterns and fireworks.'),
    2: dict(name='Harvest Haul', rule='total', start=600, end=960,
            desc='Longest total length of all your fish, 10 AM to 4 PM.'),
    3: dict(name='Frost Cup', rule='points', start=660, end=900,
            desc='Points by rarity from 11 AM to 3 PM: 1, 3, 8, 20 and 50.'),
}
WAGON_DAYS = (2, 6)        # Tideday and Lanternday
FISH_RUN_DAY = 5
METEOR_DAY = 7
FESTIVAL_DAY = 4
BADGES = [
    dict(id='first', name='First Bite', desc='Catch your very first fish.', reward=20),
    dict(id='night', name='Night Angler', desc='Catch 10 fish after dark.', reward=80),
    dict(id='weather', name='Rain or Shine', desc='Catch fish in rain, fog and snow.', reward=150),
    dict(id='big', name='The Big One', desc='Land a fish over 100 cm long.', reward=150),
    dict(id='kind', name='Kind Heart', desc='Release 15 fish back into the lake.', reward=100),
    dict(id='neighbour', name='Good Neighbour', desc='Finish 5 villager requests.', reward=150),
    dict(id='tank', name='Aquarist', desc='Fill every spot in your fish tank.', reward=120),
    dict(id='decor', name='Home Sweet Dock', desc='Own every dock decoration.', reward=200),
    dict(id='letters', name='Pen Pal', desc='Find all 10 bottled letters.', reward=200),
    dict(id='festival', name='Champion', desc='Win a seasonal fishing festival.', reward=200),
    dict(id='legend', name='Legend Hunter', desc='Catch a legendary fish.', reward=300),
    dict(id='half', name='Naturalist', desc='Record 12 species in the journal.', reward=150),
    dict(id='full', name='Master of the Lake', desc='Record every species in the journal.', reward=1000),
    dict(id='birthday', name='Party Guest', desc="Bring a villager their birthday fish.", reward=150),
    dict(id='stargazer', name='Stargazer', desc='Catch a Starfall Shiner in a meteor shower.', reward=200),
    dict(id='stylish', name='Lakeside Style', desc='Collect 4 hats.', reward=120),
    dict(id='explorer', name='Explorer', desc='Catch a fish at every spot on the lake.', reward=150),
    dict(id='muskie', name='Ten Thousand Casts', desc='Land the Mossback Muskie in the Deep.', reward=300),
    dict(id='bestcat', name='Best Friends', desc='Reach five hearts with Biscuit.', reward=200),
    dict(id='master', name='Master Angler', desc='Every fish near its biggest size.', reward=2000),
    dict(id='green', name='Green Thumb', desc='Pick 40 crops from the cabin garden.', reward=250),
    dict(id='spotter', name='Spotter', desc='Photograph 8 different animals.', reward=150),
    dict(id='naturalist', name='Field Guide', desc='Photograph every animal on the Nature page.', reward=600),
    dict(id='restorer', name='Shorekeeper', desc='Finish all three shoreline projects.', reward=400),
    dict(id='rosie', name="Rosie's Secret", desc='Follow Biscuit all the way to the hidden bench.', reward=300),
    dict(id='outing', name='Good Company', desc='Finish an expedition with friends.', reward=200),
    dict(id='curator', name='Curator', desc='Complete five exhibits at the aquarium.', reward=400),
]
TANK_SIZE = 8

GEAR = [
    dict(id='lantern', name='Dock Lantern', price=150, desc='Lights the dock. Night fish bite sooner.'),
]
