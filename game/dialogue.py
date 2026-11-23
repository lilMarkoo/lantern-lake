"""Extra things the Fernwick neighbours say, so they don't repeat themselves within a week.

SEASON_LINES: two lines per season (0 spring .. 3 winter).
CLOSE_LINES: said once you are good friends (6+ hearts).
NIGHT_LINES: after dark.
FESTIVAL_LINES: on a festival day.
"""
SEASON_LINES = {
    'mabel': {0: ["Rhubarb's up! Everything I bake this week is going to be pink.",
                  "Spring cleaning the bakery. I found a bun from last winter. It was still delicious. Don't ask."],
              1: ["Too hot to bake, too lovely to stop. I'm making iced tea buns. Yes, that's a thing now.",
                  "Summer folk want lemonade, not tea. My kettle is quite offended."],
              2: ["Pumpkin everything! Pumpkin bread, pumpkin tart, pumpkin in the tea if you're not watching.",
                  "The leaves blow in every time the door opens. I've started sweeping them into the shape of hearts."],
              3: ["Snow outside, ovens on inside. Best job in Fernwick in winter, mine.",
                  "Cocoa's on the stove for anyone who comes in with cold ears. Yours look cold."]},
    'tom': {0: ["Spring water's cold and the fish are hungry. Best time for a patient angler.",
                "My gnome has a little umbrella now. Don't know where he got it."],
            1: ["Summer evenings are made for catfish and porch chairs.",
                "Kids keep asking me about the Muskie. I tell 'em it's the size of a canoe. It's bigger."],
            2: ["Autumn's when the big ones feed. They know winter's coming. So do my knees.",
                "Fog on the lake this morning. Spooky. Good fishing, though."],
            3: ["Winter fishing is just sitting in the cold, being right about things.",
                "I'd lend you my ice auger, but the lake's never frozen deep enough. Thank goodness."]},
    'juniper': {0: ["Spring is spawning season! The shallows are full of tiny fish. Look, but no catching the babies.",
                    "I'm repainting the aquarium sign. It's going to be teal. Very bold."],
                1: ["The aquarium's the coolest building in town in summer. That's why everyone visits. Mostly.",
                    "Summer light makes the tanks sparkle. Bring me something colourful!"],
                2: ["Autumn fish are fat and grumpy. I relate to them deeply.",
                    "I'm labelling every leaf that blows into the aquarium. It's not science, it's a hobby."],
                3: ["Some fish slow right down in winter. Like little sleeping submarines.",
                    "The tanks fog up when it's cold. I draw fish on the glass. Juniper's Gallery!"]},
    'pip': {0: ["I found a frog egg! Well, lots of them. Mum says they stay in the pond.",
                "Spring means puddles. Puddles mean jumping. That's science."],
            1: ["It's ring toss weather! Everything's ring toss weather, but this is MORE.",
                "I ate three ice lollies. Don't tell Mayor Hazel. Or my mum."],
            2: ["I'm making a leaf pile so big you can't see me. Then I'm going to vanish.",
                "Autumn is the best because of conkers. I have forty-two."],
            3: ["Snowball ring toss! I invented it! It's mostly snowballs.",
                "I made a snow Biscuit. It has twig whiskers. It's better than the real Biscuit. Don't tell her."]},
    'hazel': {0: ["The spring fair committee met today. Unanimous decision: more bunting.",
                  "Fresh flowers in the town hall! I picked them myself. From the town hall planters. Hmm."],
              1: ["Summer means tourists! Well, one tourist. He was lost. Still counts.",
                  "I have declared today an official Lovely Day. I can do that, you know."],
              2: ["Harvest season! The town hall smells of apples and paperwork.",
                  "I've drafted a proclamation thanking the leaves for their service."],
              3: ["The winter budget is mostly cocoa. It's a sound investment.",
                  "If the snow gets any deeper I'm going to start a sledding committee."]},
    'fen': {0: ["Spring green is impossible. Every green is the wrong green.",
                "The cherry trees are out. I've painted them six times. They keep being better than my paintings."],
            1: ["Summer light is too bright to paint. I paint at dawn and nap at noon. Very professional.",
                "The lilies at the cove are a gift. I keep trying to give them back in paint."],
            2: ["Autumn is my season. Orange! Red! Gold! More orange!",
                "I painted the fog today. It's a white canvas. I'm calling it 'Tuesday'."],
            3: ["Painting snow is mostly painting blue. Nobody believes me until they try.",
                "My fingers are too cold to paint. So I'm thinking about painting. It counts."]},
    'librarian': {0: ["Spring is for reading outside. On a bench. In silence. Bliss.",
                      "We've had a flood of gardening books returned. And some actual mud."],
                  1: ["Summer reading club meets Thursdays. The members are me and one very loyal moth.",
                      "Too hot to think. Read something with a cold setting. I recommend the Arctic Char notes."],
                  2: ["Autumn is the best time for ghost stories. The library has three. Two are about fish.",
                      "The archive smells of old paper and woodsmoke. Lovely."],
                  3: ["Snowed in with a good book is not a problem. It is the plan.",
                      "We lend out blankets in winter now. Please return them unfolded. I like folding them."]},
}

SEASON_LINES['rowan'] = {
    0: ["Spring on a lake. No gulls screaming. I could get used to this.",
        "The frogs here are louder than my old foghorn. I mean that kindly."],
    1: ["I've started swimming in the mornings. Very slowly. Mostly floating.",
        "Long evenings are good for sitting at the lookout and doing nothing at all."],
    2: ["Autumn storms out on the coast would take the shutters off. Here they just rattle them politely.",
        "The leaves on the water look like little boats. I keep counting them."],
    3: ["Winter nights are burbot nights. Wrap up and go out late, you'll see.",
        "Snow on the lake and the northern lights over it. That's worth a whole life at sea."]}
CLOSE_LINES = {
    'rowan': ["I talk to you more than I talked to anyone in forty years. It's nice.",
              "If you ever need a light on in the window, I'll keep one burning. Habit."],
    'mabel': ["I save the best bun for you every morning. Don't tell the others.",
              "Your grandmother would be so proud of you, dear. I'm proud of you, and I'm not even related."],
    'tom': ["You've got a good hand on a rod now. Better than mine at your age. Don't let it go to your head.",
            "If you ever land that Muskie, you come straight here. I want to see its face."],
    'juniper': ["You're my favourite person to talk fish with. You actually listen!",
                "I'm going to name a new species after you one day. I just need to find a new species."],
    'pip': ["You're my best friend. And Biscuit is my second best friend. Is that allowed?",
            "When I grow up I'm going to have a dock and a cat just like you. And a ring toss on the dock."],
    'hazel': ["Fernwick's a better town with you in it. That's official. I wrote it down.",
              "Between you and me, the festival committee is now two people. You're the second one."],
    'fen': ["You've got a painter's eye, you know. You notice things. The fish, the light.",
            "I keep a little sketch of you and Biscuit in my coat pocket. For luck."],
    'librarian': ["I've started a shelf of books I think you'd like. It's getting long.",
                  "You're very good company. Quiet when it matters. That's the highest praise I have."],
}

NIGHT_LINES = {
    'rowan': ["Every night I still look for the lighthouse beam. Then I remember, and I just look at the stars.",
              "Couldn't sleep. Never could before midnight. The lamp needed me."],
    'fen': ["The stars over the lake are my favourite thing to paint. They never hold still.",
            "Night painting. Mostly dark blue. Very relaxing."],
    'mabel': ["The cocoa cart's my favourite part of the day. Everyone's sleepy and kind.",
              "A cocoa before bed and you'll dream of fish. Good fish."],
}

FESTIVAL_LINES = ["Happy festival day! Are you entering? Of course you're entering.",
                  "The whole town comes out for a festival. Even the cats.",
                  "I've got a good feeling about you today. Go win something!"]


def pick(g, k, base, rng):
    """Choose what neighbour k says today."""
    pool = list(base)
    season = g.env.season
    pool += SEASON_LINES.get(k, {}).get(season, []) * 2
    if g.friends.get(k, 0) >= 60:
        pool += CLOSE_LINES.get(k, []) * 2
    if (g.minute >= 1260 or g.minute < 300) and k in NIGHT_LINES:
        pool = NIGHT_LINES[k] * 2 + pool
    if g.festival_today() and rng.random() < 0.4:
        return rng.choice(FESTIVAL_LINES)
    return rng.choice(pool)


# ---------------------------------------------------------------- more to say (0.3.4)
MORE_LINES = {
    'mabel': ["I put a pinch of salt in the caramel. Don't tell anyone, it's the whole secret.",
              "Old Tom buys one bun and says it's for his gnome. The gnome is very well fed.",
              "If the oven's singing, the bread's ready. If it's shouting, run.",
              "I knead best when I'm cross. My best loaves were baked the day Pip spilled the jam.",
              "You smell like lake water and sunshine. Good day out there, I hope?"],
    'tom': ["Worms in a tin, a flask of tea, and no hurry. That's the whole secret.",
            "I lost a hook in that lake in nineteen-something. Still think about it.",
            "Fish don't read the almanac. But they do seem to agree with it.",
            "The best fishing spot is the one nobody's told you about. I'm not telling you either.",
            "Some days you catch fish. Some days you catch a nice sit down. Both count."],
    'juniper': ["I reorganised the tanks by colour. Then by size. Then back to colour. Science is hard.",
                "A fish's scales have rings, like a tree. You can tell how old it is. Isn't that wonderful?",
                "I named the aquarium snail Professor. He has never once been late.",
                "Some fish can hear thunder before we can. I believe them completely.",
                "Bring me anything strange you pull up. Even boots. Especially boots."],
    'pip': ["I'm saving up for a fishing rod. I have eleven coins and a button.",
            "Biscuit looked at me today. Like, really looked. I think we're friends now.",
            "Do fish sleep? Mayor Hazel says yes. Juniper says sort of. I say they're pretending.",
            "I can whistle with two fingers. Not today, my fingers are tired.",
            "When I'm big I'm going to catch the Muskie and name it Gerald."],
    'hazel': ["The town clock is four minutes fast. I've decided that's a feature.",
              "I'm drafting a bylaw that every Friday is a little bit of a holiday. Fridays approve.",
              "Every lantern lit on the lake makes Fernwick feel a little more like home.",
              "Someone left a single perfect plum on my desk. I suspect Pip. I'm touched.",
              "I keep a list of everyone who helps the town. You're on it, in ink."],
    'fen': ["I mix my greys with a bit of lake water. Don't ask me why it works. It just does.",
            "There's a heron at the cove that won't let me finish its portrait. Rude. Beautiful.",
            "I traded a painting for a loaf of bread once. Best deal I ever made.",
            "The reflections are the tricky part. The lake paints everything upside down and better.",
            "Paint the thing you love badly, and keep at it. That's the whole lesson."],
    'librarian': ["Someone has been dog-earing the fish atlas. I will find them.",
                  "I read the almanac every Sunday. It's the only book that promises the weather.",
                  "A library is just a quiet place where everybody is somewhere else.",
                  "We have a book on knots, a book on boats, and a book on knots in boats.",
                  "The old lantern keepers kept a log. Half of it is about the weather. The rest is about fish."],
    'rowan': ["I still wake at three to check a light that isn't mine any more.",
              "A lake's tide is just the wind. Took me a week to stop waiting for it.",
              "Out at sea you learn to love a grey day. Here they're almost cosy.",
              "Fog's an old friend of mine. It came along when I moved, I think.",
              "I made a model lighthouse out of matchsticks. It's on the windowsill, lit."],
}

# their own words for a rainy day (instead of everyone saying the same thing)
RAIN_LINES = {
    'mabel': ["When it rains, everybody wants cinnamon. I don't blame them.",
              "Rain on the bakery roof sounds like applause. I bow to it."],
    'tom': ["Rain stirs the bottom up. The fish come up to see what's for dinner.",
            "My knees told me this was coming yesterday. Never wrong, my knees."],
    'juniper': ["Rainy days, the trout come up right under the surface. Go and look!",
                "The aquarium gets so busy when it rains. Everybody wants to see fish that are drier than them."],
    'pip': ["I'm jumping in every puddle between here and the fountain. That's the plan.",
            "My boots are full of rain. It's like having a pond on each foot."],
    'hazel': ["Rain is good for the flower beds. I'm counting it as town work.",
              "I've declared this an official Indoor Afternoon. It's binding."],
    'fen': ["Grey sky, grey lake, a hundred greys. I'm in heaven.",
            "Rain on the lake makes it look like it's simmering. I'll never paint that."],
    'librarian': ["Rain is excellent for the library. Everybody remembers they like books.",
                  "Please shake your umbrella outside. The books have strong feelings about puddles."],
    'rowan': ["This? This is barely weather. At the lighthouse we'd call this a nice day.",
              "Rain on a lake is gentle. At sea it came in sideways and angry."],
}
SNOW_LINES = {
    'mabel': ["Snow on the rooftops! Fernwick looks like a cake."],
    'tom': ["Snow's quiet. Fish like quiet. I like quiet."],
    'pip': ["I caught a snowflake on my tongue. It tasted like nothing. Amazing."],
    'fen': ["Snow is just white paint that falls from the sky for free."],
    'hazel': ["The snow plough committee meets as soon as I find my boots."],
    'juniper': ["Under the snow the lake keeps going. The fish are fine. I checked!"],
    'librarian': ["A snowy day is a reading day. That's the law, or it should be."],
    'rowan': ["Snow on a lake. I never once saw that at the lighthouse. It's lovely."],
}

# a quick word in passing on the street (shown in a speech bubble, no window)
PASSING = {
    'mabel': ["Buns are warm!", "Morning, dear!", "Mind the flour!", "Off fishing?"],
    'tom': ["Tight lines.", "Mm. Good day for it.", "Watch your knots.", "Hrm. Afternoon."],
    'juniper': ["Found anything new?", "Hi hi hi!", "Fish facts later!", "Ooh, a lake day!"],
    'pip': ["Ring toss!", "Hi! Hi! HI!", "Where's Biscuit?", "Race you!"],
    'hazel': ["Lovely day, officially.", "Good to see you!", "Busy busy!", "Citizen!"],
    'fen': ["Hold that pose!", "The light's good today.", "Ah, my muse.", "Mind the wet paint."],
    'librarian': ["Shh. Hello.", "Books are due Friday.", "Good afternoon.", "Read anything good?"],
    'rowan': ["Ahoy.", "Calm water today.", "Evening, neighbour.", "Fair winds."],
}


def passing(g, k, rng):
    """A short hello for the street: who you are to them, what you've just done, or the hour."""
    hello = react(g, k, short=True)
    if hello and rng.random() < 0.6:
        return hello
    m = g.minute
    if m < 660 and rng.random() < 0.35:
        return 'Morning!'
    if m >= 1140 and rng.random() < 0.35:
        return 'Evening!'
    return rng.choice(PASSING.get(k, ['Hello!']))


def react(g, k, short=False):
    """Something about what you've just been up to, if there's anything worth mentioning (or None)."""
    ev = [e for e in getattr(g, 'recent', []) if e['day'] == g.day]
    if not ev:
        if not short and g.minute > 900 and not g.stats.get('caught_day') == g.day and g.place == 'town':
            return "Quiet on the water today? They'll come round. They always do."
        return None
    from data import ALL_BY_ID
    loves = None
    import town
    spec = town.FOLK.get(k)
    if spec:
        loves = spec['loves']
    last = ev[-1]
    fish = [e for e in ev if e['kind'] == 'catch']
    for e in reversed(fish):
        if e['fish'] == loves:
            name = ALL_BY_ID[loves]['name']
            return ('A %s? My favourite!' % name if short else
                    "You caught a %s today? That's my favourite fish in the whole lake!" % name)
    for e in reversed(fish):
        if e.get('new'):
            name = ALL_BY_ID[e['fish']]['name']
            return ('Your first %s!' % name if short else
                    "I heard you caught your very first %s today! What was it like?" % name)
        if e.get('record'):
            name = ALL_BY_ID[e['fish']]['name']
            if k == 'tom':
                return ('A record %s, eh?' % name if short else
                        "A record %s! I've been telling everyone. Well, I told the gnome." % name)
            return ('A record %s!' % name if short else
                    "A record %s! Old Tom's been telling everyone. Well, he told me." % name)
    if last['kind'] == 'lantern':
        return ('You lit a lantern!' if short else
                "I saw the lantern come on last night across the water. The whole street went quiet.")
    if last['kind'] == 'buy':
        return ('A new %s!' % last['name'].lower() if short else
                "A new %s on your dock? Very fancy. I'll have to row past and see." % last['name'].lower())
    if last['kind'] == 'sell' and last.get('coins', 0) >= 200:
        return ('Big day at market!' if short else
                "I heard the market did well out of you today. Treat yourself to a bun!")
    if len(fish) >= 8:
        return ('Busy day on the lake!' if short else
                "%d fish today? Leave a few for tomorrow!" % len(fish))
    if fish and not short:
        name = ALL_BY_ID[fish[-1]['fish']]['name']
        return "How's the lake today? Catch anything nice? A %s, I heard!" % name.lower()
    return None


def talk_line(g, k, base, rng):
    """What neighbour k says this time you talk: something about your day, the weather in their own words,
    or one of their lines (never one you've just heard from them)."""
    heard = g.stats.setdefault('heard', {}).setdefault(k, [])
    said = g.town_day.setdefault('reacted', {})
    r = react(g, k)
    if r and said.get(k) != r and rng.random() < 0.65:
        said[k] = r
        return _remember(heard, r)
    w = g.env.weather
    if w in ('rain', 'storm') and k in RAIN_LINES and rng.random() < 0.35:
        opts = [ln for ln in RAIN_LINES[k] if ln not in heard] or RAIN_LINES[k]
        return _remember(heard, rng.choice(opts))
    if w == 'snow' and k in SNOW_LINES and rng.random() < 0.3:
        return _remember(heard, SNOW_LINES[k][0])
    pool = [ln for ln in base if 'rains' not in ln] + MORE_LINES.get(k, [])
    for _ in range(8):
        line = pick(g, k, pool, rng)
        if line not in heard:
            break
    return _remember(heard, line)


def _remember(heard, line):
    heard.append(line)
    del heard[:-8]
    return line
