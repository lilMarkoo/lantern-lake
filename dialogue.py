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
