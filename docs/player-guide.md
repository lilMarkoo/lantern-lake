# Lantern Lake guide

[Back to Lantern Lake](../README.md)

## Controls

| Action | Input |
|---|---|
| Wind up and cast | Hold left click or Space, point where it should land (mouse or arrow keys), let go |
| Twitch the bobber | Tap click or Space while you wait. A twitch right on a nibble makes it bite |
| Reel the line back in | Hold click or Space while you wait |
| Hook a bite | Click when the bobber goes under |
| Reel | Keep the golden arc on the fish (mouse, or A / D). Hold to reel faster, let go when it lunges |
| Leap | When the fish jumps, click or press Space as the shrinking ring meets the gold ring |
| Keep / put in tank / release a catch | Space / T / R |
| Journal, Shop, Cabin, Calendar, Rest | J, S, C, K, Z (or the buttons bottom-right) |
| Change bait | Tab |
| Lake map (row to another spot) | B, the Boat button, or click the rowboat by the dock |
| The lanterns (your long-term goal) | L, or click the lantern line on the left of the screen |
| Goals: see everything on the go, pin one to the HUD | Q |
| The radio | R |
| Walk up to Fernwick village and back | T, or the Town / Lake button |
| In Fernwick: walk / go in or talk | A and D (or the arrow keys, or click where to go) / E, W or Space |
| Pet Biscuit, read the mailbox, visit the cabin, shop at Wren's Wagon | Click the cat, the mailbox, the cabin door, the houseboat |
| Open the garden | Click the beds under the cabin |
| Set or haul the crab pot (from the dock) | E, or click the pot's float |
| Friends window: send a fish, start a race (playing together) | G |
| Make a wish | Click a shooting star at night |
| Emotes (heart, music, !, fish) | 1, 2, 3, 4 |
| Chat (when playing together) | Enter to type, Enter to send, Esc to close |
| Photo mode / save a picture | P / F12 |
| Take a photo (in photo mode) | Space or click. Esc or P puts the camera away |
| Fullscreen, mute music, pause | F11, M, Esc |
| Show or hide the key hints and tips | F1 or ? |
| Move through menus | Arrow keys (or W / S), Enter to choose, Esc to go back |
| Cooking and cutscenes | Space or click (hold it when the dish asks), Esc to skip a scene |
| Cabin tabs | Tab (Shift+Tab goes back), or LB / RB on a controller |

Most of these keys can be changed in **Options > Controls**: click an action, then press the new key. If the key
already did something else, the two swap. **Default keys** puts everything back.

### Controllers

Plug in an Xbox, PlayStation (DualShock 4 / DualSense) or Switch Pro controller at any time. The game tells
which kind it is, and every hint on screen switches to that controller's own buttons straight away: the
Xbox letters in their colours, the PlayStation cross, circle, square and triangle, or the Switch letters,
plus LB / L1 / L, Menu / Options / + and so on. Type or move the mouse and the hints go back to keys; touch the
controller and they come back. Options > Controls has a **Button prompts** setting (Auto, Keyboard, Xbox, PS,
Switch) if you want to pick them yourself, and shows the full button list for your controller.

Buttons are the same on every controller, by position (the bottom face button is Xbox A, PlayStation cross and
Switch B):

| Button (Xbox / PlayStation / Switch) | While playing | In menus and windows |
|---|---|---|
| Left stick or d-pad | Walk, aim the cast, steer the reel. Up goes into a door in Fernwick | Moves a pointer (pause and quick menu: steps through the list) |
| Right stick | Brings out a pointer: while it shows, the bottom button clicks like the mouse (pet Biscuit, the mailbox, the wagon, shooting stars, the toolbar, shop doors). The left stick puts it away | Also moves the pointer |
| A / cross / B, or RT / R2 / ZR | Cast and reel (hold), the same as Space | Click |
| B / circle / A | | Back / close |
| X / square / Y | Talk or go in (Fernwick) | Tank a catch |
| Y / triangle / X | Journal | Release a catch |
| LB, RB / L1, R1 / L, R | Change bait / the lanterns | |
| View / Share / - | **Quick menu** | Close the quick menu |
| Menu / Options / + | Pause | Back / close, skip a cutscene |
| Left / right stick click | Lake map / walk to Fernwick or back to the lake | |

In cooking and cutscenes the bottom button works like Space. Moving the mouse hides the controller's pointer.

The **quick menu** (View / Share / -) has everything that otherwise needs the keyboard or mouse: Journal, Shop,
Calendar, Goals, Cabin, Pet Biscuit, Mailbox, Wren's Wagon (when it's moored), Lake map, Lanterns, Walk to
Fernwick / Back to the lake, Rest until morning, Photo mode, music on/off, the Radio, Chat (when playing together)
and the four emotes. When a shooting star is falling, *Wish on the shooting star!* is at the top. In photo mode the bottom
button takes a photo, the left button saves a picture of the screen, and any other button leaves.

Text boxes (your name, the host's address, chat) open an **on-screen keyboard** when you use a controller:
d-pad or stick to pick a key, bottom button to type, right button to delete, top button for a space, left
button for capitals, and Menu / Options / + when you're done.

## Options

Open Options from the title screen or the pause menu (Esc). Settings are kept in `settings.json`, separate from
your save, so they stay the same when you start a new game.

- **Audio**: master, music, sound effects, ambience and radio volume sliders
- **Display**:
  - **Window**: three window sizes that fit your screen, or Full for fullscreen.
  - **Pixel scaling**:
    - Sharp always uses a whole-number zoom, so every art pixel is the same size. That can leave a border.
    - Fill stretches the picture to fill the window, with a sharp-then-smooth filter.
    - Auto (the default) picks Sharp whenever that fills nearly all of the window.
  - **Interface size**: 50% to 110%, for the HUD and menus. The row lists which sizes land on whole screen
    pixels for your window. Those are the sharpest and also the fastest to draw (on a 1080p screen: 67% and 100%).
  - **Frame rate**: 30, 60, 120, 144 or Screen. Screen, the default, matches your monitor's refresh rate and
    uses vsync, so motion is smooth and doesn't tear.
  - A frame rate counter.
  - **Screen shake**: off, gentle or full.
  - The camera zoom while fishing.
  - **Light effects**:
    - Full gives sunbeams, the soft glow around lights, mist and cloud shadows.
    - Simple leaves them out, for older or slower computers.
    - Auto (the default) keeps them on, but if your computer falls behind for a few seconds it switches to
      Simple, and turns them back on once there's room again.

  The game draws through your graphics card (Direct3D 11 on Windows). It stays sharp when you change the window
  size, go fullscreen, or move the window to a screen with a different Windows scale setting. A computer that
  can't do that falls back to drawing on the CPU, which looks the same but runs slower.
- **Gameplay**: relaxed reeling, day length (slow, normal or quick days), 12 or 24-hour clock, the HUD style
  (see below), hints, pausing when you switch to another window, controller rumble, and the first-day tips (seven short tips at the top of the screen
  in a new game, each gone once you've done it, with a Skip button). The key hints at the bottom of the screen
  and the tips show through your first day (and your first few fish). After that they tuck away: press **F1**
  or **?**, or click the small ? in the bottom-left corner, to bring them back
- **Controls**: rebind the keyboard keys, or see the controller buttons when a pad is in use

### The HUD

The top left shows one card with the clock, the day and your coins, and under it **one tracked goal**: what to do next, where to go, and when (for a fish: the
spots it swims at, and the hours, seasons, weather and tide it wants). When there's more than one, a small arrow
on the card switches between them (dots show which one you're on). A live festival comes first, then the
request. At the sea, the harbour's jobs (the lighthouse, Morwen's orders, Kit's shells) come before a letter
asking for a lake fish. Under it are the day's notes: snacks, visitors, fish runs, the sky. Away at the sea,
the lake's chores (the garden, the wagon, the crab pot) stay at home.

When a fish you have never caught could bite **right now** (because it's dusk, or raining, or you're at the one
spot it lives), the notes say so, for example *2 new fish could bite now (at dusk)*, and a note pops up the
moment it starts.

Notes at the top of the screen come two at a time; the rest wait their turn instead of piling up, and over a
window they sit at the very top, clear of its buttons. A fish you've caught before that's nothing special (not
new, not a record, not rare, not wanted for a request) goes straight into your basket with a small note in the
bottom corner, so you can cast again. New fish, records and anything rare still get the full card. First-day
tips show only when they make sense (no "sell your catch" with an empty basket, no "rest" at noon) and move on
by themselves.

With the Calm or Compact HUD, the cards fade nearly away once your bobber has settled and all through the
fight, so it's just you and the water. With the Calm HUD they also fade when nothing has changed for a few
seconds. Point at them, or earn some coins, and they come back. While a cast is out the goal card shrinks to a
single line.

### Goals (Q)

The **Goals** window lists everything you have on the go: the letter in your mailbox, today's festival, the
lighthouse, Morwen's orders, Kit's shells, the lanterns, a legend hunt, the garden and the shore, each with its
next step, where and when. **Pin** one and the card in the corner follows it everywhere until you unpin it
(a little red pin marks it).

### The radio (R)

A little set with three stations, each with its own music. The station keeps playing while you fish, in place
of the usual music, and the host reads the weather for tomorrow, the high tide at Saltmarsh, fish runs,
festivals, the wagon and letters from listeners between the songs. A card under the others shows the station
and what the host is saying; click it to open the set.

| Station | Music | Host |
| --- | --- | --- |
| Lantern FM 88.4 | Slow beats, soft keys and kalimba | Marigold |
| Saltmarsh Shanty 96.1 | A squeezebox in six-eight with a stamping foot | Captain Dorrie |
| Night Bells 103.7 | Glassy bells over slow pads | Moth |

The radio has its own volume slider in Options, Audio, so you can turn the usual music off and still have
the radio, or the other way round. The game remembers your station.

The **HUD** setting (Options > Gameplay) has three styles:

- **Calm** (the default): the menu toolbar is folded into one **Menu** button in the bottom-right corner.
  Point at it (or click it) and it opens into the Journal, Shop, Cabin, Calendar, Town and Rest buttons. While
  a cast is out it slides away and the day's notes step aside, so it's just you and the water. The keys (J, S,
  C, K...) still work. Your bait sits in a small label at the top right
- **Compact**: like Calm, with a small clock, coin and bait display
- **Full**: everything stays on screen, as before

The whole screen, menus and text included, is pixel art on the lake's 640x360 grid. Panels have wooden frames,
and the text uses a bitmap font drawn in code (`pixfont.py`). Fullscreen uses your monitor's own resolution, and
whole-number sizes (1280x720, 1920x1080, 2560x1440) give perfectly square pixels. At other window sizes, Pixel
scaling decides: Sharp keeps whole-number pixels with a thin border, and Fill uses a sharp-then-smooth filter so
the pixels stay even.

## Making your angler

A new game opens the **character creator** first. On the left is a little living diorama of your dock: you,
Biscuit, the lantern post and the water, which reflects everything. Every change shows there straight away.
Switch it between **dawn, noon, dusk and night**, and click one of the four **season** figures underneath to see
that season's colours (and your winter scarf). *Hat: on/off* takes your hat off so you can see your hair.

- **Face**: eight skin tones, five eyes (bright, smiley, sleepy, glasses or shades), a beard, stubble or
  moustache, and freckles or rosy cheeks
- **Hair**: ten colours, from brown and silver to lake teal, rose and lavender, and eight styles: side part,
  short, long, ponytail, bun, curls, buzz and braids
- **Clothes**: overalls, a striped tee, a knit sweater, a raincoat or an angler vest. **Colours** gives your top
  one shade for each season, from eight palettes. Then trousers, and boots or wellies
- **Keepsake**: a charm tied to your rod. It sways while you wait and shivers when a fish nibbles. The bell
  shivers, the ribbon flutters, and the tin star and tiny lantern glow after dark. And **While you wait**: how
  you pass the time until a bite. Hummers hum little notes, stargazers look up and spot stars at night, fidgety
  anglers tap a foot, dozy ones yawn and nod off after dark, and chatty ones have plenty to tell Biscuit
- **Biscuit**: her coat. Ginger tabby, tuxedo, grey, calico, cream, siamese or midnight black. She wears it
  everywhere: on the dock, in the cabin, in the kitchen and around the village

Your name is typed at the top (it's the name friends see when you play together). **Surprise me** rolls the dice
through a flicker of looks and settles on one. **Reset** goes back to the classic look. Then **Start fishing**.

You can change any of it later: Cabin, **Wardrobe** tab, **Change your look**. Older saves keep the classic look
until you do. When you play together, friends see the look you made, keepsake and all.

## Your first day

A new game starts with a short welcome, **Settling in**, on the tracker card: catch two fish, and Grandma's
radishes (planted before you came) pop up ready to pick. Pick them, and a yarn basket arrives for Biscuit. Play
with her (Cabin, Biscuit tab), and she finds Grandma's old tool box under the dock. Click the loose plank
sticking up on the dock to mend it: the dock gets a fresh plank and a pennant, and the tool box has 50 coins in
it.

Letters that can wait go in the **mailbox** instead of popping up: the flag on the mailbox goes up, a line
under your goals says how many are waiting, and you read them when you like (click the mailbox, or Mailbox in
the menu). Only Grandma's welcome on your very first morning opens by itself.

The view sits close to you and Biscuit on the dock and drifts a little toward wherever you point. When you
cast, it pulls back to keep both you and your bobber in view.

Your dock fills up as you fish: a bait bucket after 5 catches, a tally board on the post after 15, a carved
fish sign once you have 8 kinds of fish, a coil of rope and a drying net after 30, flower pots after 50 and a
wind chime of old lures after 80.

The same common fish turns up less often if you have just caught a few of them, and fish you've never caught
come along more often.

## Reeling

The hooked fish swims around a ring and you steer a golden arc to stay on it. While it is inside the arc
the line comes in, and outside it the fish gets away. Holding the button reels faster but builds line strain.
Fish shake and show a "!" before they lunge, and holding through a lunge snaps the line. Calm fish drift,
small ones dart, eels zigzag and big fish make long runs. The first seconds of a fight tell you what kind of
fighter you have:

- **Circlers** race round faster and faster, give a little shiver, then turn back hard. Watch for the shiver
- **Divers** vanish into the deep for a moment. Only a trail of bubbles on the ring shows where they are, and
  holding while one dives strains the line more
- **Sulkers** (catfish and sturgeon) stop dead on the bottom. Only pulling brings a sulking fish in, and pulling
  is hard on the line, so pump it: hold, let go, hold

Big fish get a **second wind** near the end: they change how they fight and come straight at you. Rarer fish
also leap out of the water for a timing challenge (Perfect gives a big boost, a miss costs you), and golden
glimmers on the ring are worth a few coins.

The ring is a small readout in the bottom-left corner: the fish is the show. The camera closes in on the
fight, and the hooked fish itself thrashes just under the surface at the end of your line, big and in its own
colours, rolling harder when it lunges. Its fin cuts the
water when it runs, it slaps the surface when it lunges, and a tight line shivers and flicks off drops. When it
comes in, it bursts out of the water and you hold it up for a moment (with its name, its size and a NEW or
Record tag) before the catch card. The world holds its breath for a moment as a fish breaks the surface,
water runs off it on the way in, and a measuring tape fills as its size counts up (a gold mark shows your
old record). Click or press Space to skip ahead.

You can hear the line too: the reel ticks as it turns (faster when you hold), the drag sings when a fish runs
or lunges, and a tight line starts to hum, higher and higher as the strain builds. With a controller, you
feel it: a tick on a nibble, a thump on the bite, the weight of the fish growing with the strain, and a jolt
when it lunges or splashes down (Options, Gameplay, Controller rumble). The how-to lines under the ring show
for your first ten catches.
Small common fish come in quickly, so the long fights are saved for the good ones. The ring takes the fish's
colours: lake blue for common fish, green for uncommon, deep blue for rare, violet for very rare and gold for a
legend, with more sparkles the rarer it is. Your angler hops when a fish bites and slumps with a sigh when one
gets away.
The camera leans in during the fight. Better rods have a wider, faster arc. "Relaxed reeling" in the pause
menu gives a wider arc, longer warnings and slower leaps. The arc has brackets and the strain bar is hatched,
so it does not rely on colour.

## Waiting for a bite

While the bobber sits, fish nose around it. Small dips are nibbles. **Tap** to twitch the bobber: the first
few twitches draw fish in a little sooner, a twitch right on a nibble makes it bite, and too much twitching
spooks them. **Hold** to reel the line back in. A nibble pulls the float half under, and a real bite yanks
it clean under with a bloop and a swirl: that's when to strike.

While you wait the view leans gently in toward your bobber and the lake gets on with its day: a fish jumps far
out, rings spread where one rises, the reeds rustle, and on a fine spring or summer day a damselfly may come
and rest on your bobber (it's off at the first twitch or nibble). Biscuit watches the bobber too and sits
up, tail going, at every nibble. Every so often a kingfisher comes to sit on the dock post; now and then it
dives for a minnow and flies back up with it (it's off as soon as you hook something). The wind moves through the trees in gusts
and you can see each gust ruffle across the water.

About once a minute something bigger happens on the lake: a **heron** wades slowly through the shallows and
stabs at a fish (it flies off when you hook one), a **canoe** paddles past with a lantern at the bow after dark,
a big fish **leaps** clear of the water two or three times, or a **breeze** sweeps across the whole lake,
darkening the water and setting the reeds and willows swaying. In spring, blossom petals drift down and float.
At dawn, dusk and under the stars the camera sits a little higher, so you see more of the sky.

The light changes through the day. The sun comes up over the far shore on your left and goes down behind the
trees on your right, and while it's low, beams of light slant across the water. They're at their best through
a foggy morning. Mist lies on the lake at first light and a thinner haze comes back at dusk. On a clear day the
sun's path on the water twinkles, cloud shadows slide across the lake and over the dock, and lanterns, windows
and fireflies glow softly after dark. On a clear, moonless night the Milky Way arcs across the sky and shows in
the still water. In the rain, sheets of it sweep past in the wind and every drop kicks up a tiny crown. When a
fish breaks the surface, white water bursts up, the spray catches the light, and a ring of foam spreads out.

**The evening rise**: at dusk on the lake (not in a storm, and not under ice), fish come up to feed. Fish jump
and rise all over the water, bites come about a third quicker and the better fish are likelier.

Two things on the water are worth casting at:

- **Bubbles**: a wide fizzing patch with big bubbles breaking the surface. Something hungry is down there:
  bites come much quicker and rarer fish are a lot likelier. They come often, and they're easy to hit
- **Feeding schools**: a dark patch with little fins breaking the surface, drifting slowly across the water.
  Cast into one for quick bites (a school is good for a couple of fish before it moves on)

### The worm tin

Garden worms are free, but you get one tin a day: **30 worms**, dug fresh every morning. A worm goes when you
hook a fish (a bite you miss keeps its worm). When the tin is empty you switch to whatever other bait you have.
With none, casting at the dock digs along the bank for 10 more (half an hour goes by); away from the dock, row
home to dig, or buy another 15 worms at the shop for 20 coins (extras you buy carry over). The bait label at the
top right shows how many are left.

**Spooked fish**: a rare fish (rare, very rare or legendary) that snaps your line or gets away is spooked. It
won't bite again until tomorrow.

## The rowboat and fishing spots

Wren's Wagon sells a rowboat for 500 coins. Fen's birthday gift, the Little Rowboat, works too. On her very
first visit (if you have no boat yet) Wren lends you her rowboat for the day, so you can try the other spots
before you save up; she takes it back at bedtime. That day Wren waits on your dock beside her boat, waving,
with an arrow over the boat, until you take it out. On other wagon days her rowboat for sale is tied up beside
the wagon with a price tag. Once you have one, open the lake map (B) and row to one of three new places.
Biscuit comes along. You see the whole lake as you row across it (a few seconds, with the wake opening out
behind you). You row home automatically when you rest for the night.

- **Lily Cove**: shallow water full of lily pads and frogs, with big pads and cattails right in front of you
  and a willow hanging over the boat. Bites come quickly, but casts never reach deep water.
  The hook sometimes **snags in the lily stems**: tap to try to work it loose (it keeps your bait), hold to
  tear it free (the bait stays in the weeds), or just wait a few seconds and it comes loose by itself
  Home of the Mud Bullhead, the Lily Gourami and the Velvet Tench
- **The Deep**: the middle of the lake, marked by a red buoy. Open, darker water with long swells and low mist,
  and the shore far away. A fish hooked here **bolts for the bottom**
  first: it's heavy on the line and out of sight, so follow its bubbles. Bites are slow, but there are few small
  fish and more rare ones,
  bigger catches and more pearl clams. Home of the Silver Cisco, the Midnight Burbot and the legendary Mossback
  Muskie
- **Willow Creek**: where the river comes in, between close grassy banks under weeping willows, with stones at
  the water's edge. The current runs fast and carries your bobber downstream while you wait.
  Home of the Creek Chub, the Sail Grayling and the River King Salmon. In autumn the salmon run upstream at
  any hour

Each spot also has some of the lake's own fish. The map shows how many species you've found at each spot, and
the journal has a second page (Rowboat) for the new fish.

## Saltmarsh, down the river

The morning after you get a rowboat, Harbourmaster Morwen writes to say the old river channel is open again.
Open the map (B) and pick **Saltmarsh, down the river**. The row takes about an hour of game time each way (20
minutes once Ossian fits a sail). At the coast the map shows the coast instead, with *Row home, up the river* at
the bottom. Resting for the night still rows you home.

There are two places to fish at the coast:

- **Saltmarsh Pier**: under the harbour pier, with the village up the steps. Sprats, mackerel, pollock and
  bream, Silver Sea Bass after dusk, Conger Eels at night, and the big Halibut and Bluefin Runner on a high tide
- **Kelp Rocks**: weedy rocks below the lighthouse. Gobies and Shore Crabs in the rock pools at low tide, Kelp
  Wrasse any time, Wolf Fish in the cold months and the Blue Lobster after dark at low water

The journal has a Coast page for the sea fish, and the aquarium has two new exhibits for them.

### Tides

The sea rises and falls twice a day, and each day the high tide comes about 50 minutes later. The HUD says what
the tide is doing, and the harbour board has a tide table for the next day. Some fish only come in at high water
and some only at low water (their journal hints say which). You can watch the tide climb the quay wall in the
harbour, and cover the rocks at Kelp Rocks.

### The harbour

At Saltmarsh Pier, press T (or the *Harbour* button) to climb the steps into the village. Walk with A and D or
click, press E at a door or a neighbour, and press Esc to go back down to your boat. The clock keeps running.
The harbour folk keep 7 AM to 8 PM, and each of them grows a friendship with you. Talk once a day for a little,
and at five hearts they give you a present.

- **The harbour board** (Harbourmaster Morwen): three orders a day for sea fish, paid at about two and a half
  times the fish's price, and the tide table
- **Nell's Fish Stall**: the *catch of the day* sells for double (anywhere, all day). Nell sells two sea baits,
  *Ragworm* (sea fish bite much sooner) and *Squid Strips* (rare sea fish come twice as often), and buys your sea
  fish
- **The Gull & Lantern**: a room with a fire, a bar and two old fishermen, Bram and Old Tam, talking about the
  tide, tomorrow's weather, the lighthouse, Ossian's boat and you (what they say changes with what's going on).
  *Harbour Chowder* (45 coins, once a day) makes rare sea fish bite more often. *Buy them a round* (30 coins,
  once a day) for a little luck and a tip about a sea fish you haven't caught yet
- **Ossian's Boatyard**: a *Little Sail* (the river in 20 minutes) and a *Bow Lamp* (sea fish bite sooner at
  night). Ossian is building a new boat on the trestles in his shed: *Lend a hand* once a day and watch it go
  from a bare keel to ribs, planks and paint. On the fourth day she's launched and moored by the slipway, and
  Ossian gives you 250 coins (25 for each day before that)
- **The beach**: new shells and sea glass wash up every morning (always at least one piece of sea glass while
  Sol still needs it). Find all eight kinds of shell for Kit's collection and a 600-coin prize
- **Swapping with Kit**: spare shells (any you have more than one of) can be swapped. Kit gives you a missing
  shell of your choice for 2 spares (3 for a Pink Conch, 4 for a Tiger Cowrie), or a piece of sea glass for 2.
  Kit never takes your last one of a kind

### The lighthouse

The Saltmarsh lighthouse has been dark for years. Sol, the old keeper, needs three things to light it again: six
pieces of sea glass to mend the lens, a Silver Sea Bass for supper, and 600 coins for oil and a wick. Bring them
to Sol at the lighthouse, then press *Light the lamp*. You can watch the work as you go: the lighthouse wears
a scaffold that comes down a section with each thing you bring, the mended lens glints in the sun, barrels of oil
stand on the quay, Sol's cottage window glows and the chimney smokes once he has his supper, and Sol taps away
with a hammer while the work goes on. When all three are done, the lamp room flickers, ready. You earn the *Keeper of the Light* badge, the beam sweeps
the sky every night, rare sea fish bite a little more often after dusk, and Sol writes about something he saw
off Kelp Rocks.

## Fernwick village

Press T (or the Town button) to walk up the lane to Fernwick, a little village street three screens long.
Walk with A and D or click where you want to go. Clicking a shop or a neighbour walks you there and goes
in. Seven townsfolk keep their own day: they open their shops, wander the street, shelter under umbrellas
in the rain and gather in the square in the evening. Shops keep opening hours. The view stays close on the
street and the people in it, with barrels, crates, bikes and milk churns along the front, and pigeons that
clatter up when you walk through them.

- **Old Tom's Tackle**: the shop you know, inside a real building now
- **Mabel's Bakery**: Mabel stands behind her counter. Point at a treat and she tells you about it; buy one and
  she fetches it from the shelf and sets it down, still steaming. One treat a day each, lasting until bedtime:
  Honey Bun (luck), Lakeside Tea (fish bite sooner), Blueberry Pie (bigger fish) and Star Cookie (rare fish come
  more often). The *Recipes* tab sells her recipe cards for your kitchen
- **Notice board**: three odd jobs every morning, such as a certain fish, a big one, any few fish or a piece of
  junk for the clean-up. Hand them in from your basket for coins and friendship
- **Wishing fountain**: toss in 10 coins once a day for luck, and sometimes a surprise
- **Fernwick Aquarium**: walk inside and stroll the hall (see *The aquarium* below). Donate one of each fish at
  Juniper's desk. She rewards you at 5, 10, 20 and 30 fish, and for the whole collection
- **Town Hall**: fund Mayor Hazel's projects, Flower Beds, Street Lanterns and a Bandstand. Each one changes
  the street, and the band plays in the square every evening. The biggest project is a Lighthouse on the far
  shore of the lake (6,000 coins): you can see it from the dock, and rare fish come out more at night by its
  light. The *Home upgrades* tab has things built for your own cabin (see Cooking and upgrades below)
- **Pip's Ring Toss**: 15 coins for five rings. Throw (Space or click) as the arrow sweeps under a bottle. The
  gold bottle is worth three tickets. Trade tickets for bait, coins, a Party Hat and a Top Hat
- **Library**: Ms. Alder's notes on every fish you haven't caught yet, with when and where to look
- **Lookout bench**: at the east end the street opens out onto the lake. Sit on the bench and you settle down
  facing the water, Biscuit hops up beside you if she's along, and the view comes in close on the two of you
  (a little luck, once a day). Walk, click or press E to stand up. On a clear night, lie back and look
  at the stars instead: each season has its own constellation, and if Fen is out painting they come and sit
  with you (once a night, +1 luck)
- **Mabel's Cocoa Cart**: from 8:30 PM to midnight Mabel wheels a cart out next to the fountain. Hot Cocoa makes
  night fish bite sooner and a Moon Cake brings out more night-time fish. Both last until dawn. By day the cart
  sits folded under a tarp

Fernwick has its own sounds: footsteps on the cobbles, the fountain, neighbours murmuring as you pass and, once
the Bandstand is built, a squeezebox tune in the evenings that gets louder as you walk up to it.

The street has depth: you see the side walls and roofs of the buildings turn as you walk past, and a verge of
hedges, fences and flower barrels slides by in front. Every building has its own look: a rusty tin roof with a brass fish weathervane that turns in the wind on Old
Tom's, a scalloped pink roof and dormer on the bakery, a green copper cupola on the aquarium, slate on the
library, and a thatched cottage beside a saltbox. Shop signs swing on their brackets in the breeze. The street
dresses up for each season:

- **Spring**: pastel bunting, tulips on the doorsteps and in the window boxes
- **Summer**: bright bunting and geraniums
- **Autumn**: leaf garlands, mums and pumpkins
- **Winter**: wreaths on the doors, little evergreens, and string lights that glow after dark

Mabel changes her shop window with the seasons too: a pink layer cake in spring, berry tarts and a lemon loaf in
summer, pumpkin pie in autumn and a gingerbread house in winter.

### The aquarium

Press E at the aquarium door (open 9 AM to 5 PM) to walk inside. Walk the hall with A and D or click, and press E
to look, sit or talk. Esc leaves. The clock keeps running while you look around, and Juniper sees everyone out
at closing time. Even before you donate anything, the tanks have their own little residents: a school of fry
turning together, a snail on the glass and a hermit crab in Crab Pot Corner.

The cabin **Wardrobe** shows what you own, the next few things still to find, and how many more are out there.

Every fish you donate swims in one of twelve themed exhibits: Lantern Lake, Lily Cove, Willow Creek, The Deep,
Legends of the Lake (a round brass porthole), Under the Ice, Crab Pot Corner, Spring & Summer, Autumn & Winter,
Weather & Wonders, and two for the sea, Harbour Waters and the Kelp Forest. Press E at a tank to see who belongs there, read about them, and donate straight from
your basket.

- **Finish an exhibit** for a one-time coin reward, from 150 to 600 coins. Finish five for the *Curator* badge. If
  you filled exhibits before they existed, Juniper pays you the first time you walk in
- **Benches** sit in front of five of the tanks. Sit a while to read about the fish drifting past (+0.3 luck,
  once a day)
- **Visitors**: two neighbours wander in each day and react to your discoveries. Chat with them for a little
  friendship, once a day each

Talk to anyone (E) once a day to grow your friendship, and give them a fish. Everyone has a favourite, and a
loved fish counts for a lot. At 3, 6 and 10 hearts they send you a letter with a gift. Finishing a mailbox
request also makes a friend. Resting for the night walks you home to the lake.

What people say changes with the season, the weather (each in their own words), the time of day and
festivals, and close friends talk more openly. They pick something new each time you talk, and they notice what
you've been up to: your first catch of a fish, a record, their favourite fish, a new dock decoration, a lantern
you lit, a big day at the market. Walk past a neighbour on the street and they say a word or two in a speech
bubble, no window, and you keep walking. At **5 hearts** each neighbour has a short scene with you, played out on the street the next time
you talk to them:

- **Mabel** finds Grandma Rosie's Sunny Tart recipe card in her flour bin
- **Old Tom** tells you about the Mossback Muskie that got away, and gives you his lucky lures
- **Juniper** shows you the tank she named after you
- **Pip** makes you a friendship bracelet
- **Mayor Hazel** gives you the Key to Fernwick
- **Fen** takes you up to the lookout and paints your portrait with Biscuit. It hangs over your kitchen table
  afterwards
- **Ms. Alder** finds an old map of the lake, and the lantern story begins

## Cooking and upgrades

The cabin (C) has a **Kitchen** tab. Recipes turn fish from your basket into dishes, always using the
cheapest fish that fit. Minnow Fritters and Perch Chowder are known from the start. Mabel sells six more
recipe cards.

Pressing **Cook** takes you into the kitchen, where you cook the dish yourself, step by step, with the camera
following you round the room (Space or click for everything):

1. **Chop**: stop the swinging knife on the marked line, three or four times
2. **Heat**: hold to keep the flame inside the moving band (it wanders more on harder dishes)
3. **Finish**, which depends on the dish: flip it in the pan when it turns golden, take a pie out of the oven
   at the right moment, or climb the step stool and season the pot as the shaker swings over it
4. **Plate up**: the dish gets 0 to 3 stars

Harder recipes (shown as stars on the recipe) move faster and leave less room for error. 3 stars makes two
servings, 1 or 2 stars make one (2 stars also gives a taste of luck), and 0 stars burns it and the fish are
lost. Biscuit jumps up on a chair for a perfect dish. The first time you cook there is a little scene with
Grandma Rosie's recipe book. Your best stars for each recipe are shown in the kitchen.

| Dish | Needs | Eat it for |
| --- | --- | --- |
| Minnow Fritters | 3 fish of any kind | A good dose of luck |
| Perch Chowder | 2 Sunny Perch and 1 other fish | Fish bite much sooner |
| Grilled Trout | a Rainbow Trout | Bigger fish |
| Fisherman's Pie | an uncommon (or rarer) fish and 2 others | Rare fish come out more |
| Pearl Clam Chowder | a Pearl Clam and 2 fish | Fish sell for 20% more |
| Catfish Stew | a Whiskered Catfish and 1 other fish | Night fish come out more |
| Sunny Tart | a Honey Sunfish and a Bluegill | Neighbours warm to you faster |
| Lakeside Feast | a rare (or rarer) fish and 3 others | A little of everything |

You can eat one meal a day, and its effect lasts until bedtime, on top of any bakery treat. Dishes also make
the best gifts in Fernwick: every neighbour has a favourite dish (shown when you talk to them once you know the
recipe). And the shop buys dishes for a little more than the fish were worth.

**Market days.** Fernwick only needs so much of one thing in a day. The first 5 of each kind of fish sell at full
price, then each one after that fetches 8% less (down to half price), and Old Tom pays full price for 3 dishes a
day, then 20% less for each one after (down to about a third). A red dot on a shop tile means that market is full
for today. Prices recover the next morning, so it pays to fish a bit of everything and spread your selling out.

**Home upgrades** (Town Hall, Home upgrades tab), built by Hazel's cousin Birch:

| Upgrade | Cost | What it does |
| --- | --- | --- |
| Copper Stove | 900 | One extra serving of anything you don't burn |
| Bigger Fish Tank | 1,200 | The cabin tank holds 12 fish instead of 8 |
| Ice Chest | 1,500 | Fish sell for 15% more |
| Bait Shed | 2,000 | 3 Sweet Corn and 2 Glow Grubs waiting every morning |
| Cozy Loft | 2,500 | You wake up with a little luck every day |

## The lanterns of Lantern Lake

Once Ms. Alder shows you her map (5 hearts with her), she writes to you about the four old lanterns around the
lake, which nobody has lit since Grandma Rosie kept them. Each one wakes up in its own season and needs three
things done first. Press L to see them:

| Lantern | Season | To light it |
| --- | --- | --- |
| Dock Lantern | Spring | 8 kinds of fish, a 3-star dish, 3 hearts with a neighbour |
| Cove Lantern | Summer | 8 fish in the aquarium, fish at 3 spots, fund a town project |
| Deep Lantern | Autumn | 3 kinds of rare fish, cook 5 different recipes, 5 hearts with 3 neighbours |
| Creek Lantern | Winter | 20 kinds of fish, a home upgrade, cook 15 dishes |

When a lantern is ready it pulses on the far shore. Lanterns are lit as the light goes: from **5:30 PM**,
when a ready lantern calls you out with a note. Row to its spot and light it from the lanterns window. You
row across and the view closes in on the old lantern; **hold Space or the mouse** (or keep tapping) to light the
wick, and the flame catches and flares with its own little tune. Then the view pulls back over the whole lake,
the windows of Fernwick light up one by one along the far shore, the old bell rings on the hill, and someone
calls across the water. Each lantern gives you some luck. Once all four burn, come down to the dock one evening (after 7:30 PM) for
the Night of Four Lanterns: the whole village comes to the water, with paper lanterns and fireworks, and you get
a keepsake (the Lantern Hat, 1,000 coins and friendship with everyone).

## Legends of the lake

Each season one of the lake's four legendary fish stirs, and you can only catch it by hunting it down. Legendary
fish never bite at random any more: only on their own lure.

| Legend | Season | Told by | Clues from | The lure |
| --- | --- | --- | --- | --- |
| Old Whiskers | Spring | Mabel | Pip, Mayor Hazel | Honeycomb Bob: 300 coins, 2 catfish, 2 carp |
| Sunpetal Koi | Summer | Fen | Juniper, Mabel | Dawnpetal Fly: 450 coins, 2 Honey Sunfish, 1 Koi |
| Mossback Muskie | Autumn | Old Tom | Mayor Hazel, Juniper | Mossback Spoon: 600 coins, 1 salmon, 2 cisco |
| Lake Spirit | Winter | Ms. Alder | Fen, Pip | Starglass Lure: 800 coins, 1 Aurora Fish, 2 eels |

1. The teller writes to you when the season comes (from day 3). Talk to them in Fernwick and they tell you the
   tale, with a little scene and an old drawing.
2. Two neighbours each know a piece of it. Talk to them and the clue is noted.
3. Open the **Legends** tab of the L window (Tab, or LB on a controller) and make the lure from coins and fish
   in your basket. It goes straight on your line.
4. With the lure on, the legend bites at its own time and place, whatever the weather (the clues tell you
   where). The lure is not used up by bites.
5. The fight has **three stages**. Each one has a banner, a new swimming style (runs, then zigzags, then a
   frenzy) and a leap. Reaching a new stage sets a checkpoint on the reel: the legend can't drag you back past
   it, but if it pins you there for 4 seconds it breaks away. If it gets away, your lure is safe and the legend
   comes back tomorrow.
6. Land it and half of Fernwick turns up at your dock for a scene, the legend goes on a trophy board, and you get
   coins and a keepsake that helps from then on: more night fish, bigger fish, more rare fish, or quicker bites.
   You can make the lure again any time for a rematch. Land all four to become a Legend of Lantern Lake.

## Fishing through the seasons

Three pieces of gear in the shop's Rods & Gear tab open up new ways to fish, with 15 fish of their own (they
have a **Seasonal** page in the journal):

- **Crab Pot** (250): from 4 PM, press E on the dock (or click it) to lower the pot. Haul it up the next morning
  for one to three crayfish, crabs or snails. Sweet corn in your bag goes in as bait for one more
- **Fly Rod** (700): at Willow Creek, casting turns into a rhythm. Tap on each of the three beats as the line
  loops overhead. Good timing makes a longer, gentler cast, quicker bites and better fish, and the Mayfly Dace
  and Brook Jewel only rise to a really good fly
- **Ice Auger** (300): in winter Lily Cove freezes over. Drill a hole (hold Space), then jig the lure up and down
  (W / S, or the stick) at the depth the fish are swimming. Hook with Space and bring it up gently. The hole
  stays open for the rest of the day
- **Rare nights**: rainy summer and autumn nights can turn into thunderstorms, when the Thunderfin rises in the
  Deep. Clear or snowy winter nights sometimes bring the northern lights, and the Aurora Lightfish

## Biscuit

Your cat has a bond with you, shown as five hearts in the cabin's **Biscuit** tab. Each day she likes a pet on the
dock, a fishy treat (the smallest fish in your basket), a play with a toy, and a walk to Fernwick. Every heart
teaches her a trick: High five, Roll over, Tail chase, Sit pretty and a Backflip. Pet her again (or use *Ask for
a trick*) to see one. From two hearts she follows you up to Fernwick (you can switch that off), and some
mornings she leaves a present by the door: a fish, a few coins, some bait, or a four-leaf clover.

**Biscuit's discoveries.** On a walk through Fernwick, Biscuit sometimes stops, ears up, and trots off on her own
(the more hearts she has, the more often). Follow her: she waits by what she found, under the bakery steps or
behind the notice board, until you walk up and press **E** (or click her). Most finds are pages from Grandma
Rosie's diary, which you can read again in the journal (*Letters*, then *Rosie's diary*). Others are Rosie's old
handmade lures, which go up on a lure board in your cabin. She finds one thing a day at most. Find everything and
she leads you somewhere new at the end of the street. After that she still turns up the odd coin or treat.

## Your cabin

The cabin window keeps its rooms on a wooden rail down the left: Fish tank, Kitchen, Garden, Hatchery, Home,
Biscuit and Wardrobe. A dot on a tab means something there wants you, like beds to pick or young fish to collect.
The little window at the bottom of the rail looks out on the lake as it is right now. At the biggest interface
size, the tabs sit along the top instead.

The cabin's **Home** tab shows your room. Grandma left her rocking chair, a braided rug, a potted fern, an old
lake map and a flower garland behind, so it never starts bare. Click a spot on the wall or floor, then pick something from the
catalogue on the right: paintings, a clock that keeps the lake's time, shelves, an armchair, a wood stove, lamps
that glow in the evening, a cat basket and three toys for Biscuit, four rugs and five wallpapers. Moving things
around is free. Any fish you've caught at 70% of its biggest size can be mounted on the wall as a trophy.

Your wildlife photos can go up too. Every animal on the Nature page shows up in the **Wall art** catalogue: frame
your best photo of it for 40 coins and hang it in any wall spot. Each frame carries a little ink stamp in the
season's colour, and the room tells you when and where you took it (*Summer 5, Lily Cove*). Take a better photo
later and the frame shows the new one. The
**Tank** tab of the catalogue changes the fish tank: Coral Garden, Mossy Log, Sunken Rowboat or Moonlit Tank.

## The shoreline

From your second day, Juniper writes about the shore by your dock, which has gone a bit wild since Grandma
Rosie's time. Click the litter in the shallows past the dock (or the far shore across the water) to open
**The Shore**, which has three projects. Each one changes how the lake looks and brings a new animal to photograph:

- **Reed beds**: clear the litter with 4 lake junk (old boots, cans, driftwood), then plant reed shoots with
  2 plant food and 50 coins. The reeds grow tall over three days and bring the **Reed Warbler**
- **The old landing**: clip the brambles on the far shore once a day for three days (free, but it takes a little
  while), then mend the planks with 3 lake junk and 150 coins. A lantern lights the landing at night, and a
  **Muskrat** swims over from it mornings and evenings
- **Wildlife hide**: once the reeds are tall and you have photographed six animals, build a hide for 300 coins.
  At dawn and dusk a shy **Bittern** stands in the reeds and booms

Finishing all three earns the *Shorekeeper* badge. On a controller, *The Shore* is in the quick menu (View) at
your dock.

## The garden

Six raised beds sit on the slope under the cabin (three to start; dig the others for 150, 300 and 500 coins).
Click them on the lake, or open the cabin's **Garden** tab. Pick a bed, then plant seeds for the season: radishes,
snap peas and strawberries in spring; sweetcorn, tomatoes and sunflowers in summer; pumpkins, carrots and beetroot
in autumn; winter kale and garlic in winter; dill and catnip all year round.

- Water the beds once a day (*Water the beds*). Every watered bed grows a day overnight. Rain and snow do the
  watering for you, and a bed you forgot simply waits. Nothing ever dies
- Peas, strawberries, tomatoes, dill and catnip keep giving: after a picking they grow back in a few days
- Fresh crops go with dishes in the kitchen. Cooking with the right one makes **one extra serving**: dill for
  fritters, sweetcorn or peas for chowder, strawberries for the Sunny Tart, pumpkin for the Lakeside Feast, and so
  on (a little crop icon on the recipe card shows when you have one)
- Sell what you pick, turn sweetcorn into crab-pot bait (5 per cob), or give Biscuit some catnip once a day
- Old boots, tin cans and driftwood from the lake go on the **compost heap**. Every three make one plant food, which
  puts a bed a day ahead and adds one more crop to its harvest

## Colour morphs and the hatchery

Now and then a fish bites in colours it doesn't usually wear. About one catch in fifty is a **colour morph**, and
every kind of fish in the lake can turn up in all six:

| Morph | Looks like | When | Worth |
| --- | --- | --- | --- |
| Golden | Scales like a coin in the sun. The rarest | Any time | x5 |
| Ghost | Pale as morning mist, with a blush of pink | Any time | x3 |
| Shadow | Dark as deep water, with a blue sheen | Any time | x3 |
| Koi | Patched in cream, orange and ink | Any time | x3 |
| Starry | Night-blue and freckled with stars | After dark | x4 |
| Prism | Bands of colour, like oil on a puddle | In the rain | x4 |

Fishing on the bubbles makes morphs a little likelier, and so does luck. Crabs, snails, the lake spirit and the
legends never change colour.

A morph always gets the full catch card, with its name and colour. It never goes into the basket, so a recipe, a
request or *Sell all* can't use it up by accident. Instead, *To pond* puts it in the **hatchery pond**. If the
pond is full, or it's a sea fish, the button reads *Sell* and a collector pays the full price. You can also send
it to the tank, or release it.

**The hatchery pond** is the stone-ringed pool on the slope under the garden. Click it on the lake, or open the
cabin's **Hatchery** tab.

- It holds 6 fish. Colour morphs come here from the catch card. To bring ordinary fish, click their kind under
  *Add from the basket* (the biggest one goes in). Only freshwater fish live here.
- Two fish of the same kind that have spent a night in the pond lay a **clutch of eggs** at dawn. The pond raises
  up to two clutches at once.
- The eggs hatch into fry two days later, and three days after that the young are ready: *Collect* brings 2 to 4
  young fish into the pond. Young that don't fit swim off into the lake.
- **Young take after their parents.** If both parents are the same morph, most of the young wear it too. If one
  parent is a morph, about half of them do. Now and then a young fish comes out in a colour neither parent had.
- Click a pond fish to **sell** it to a collector (morphs pay their full multiplier and don't flood the market),
  move it to the **tank**, or **release** it. Plain fish can also go back to the basket.
- **Releasing a morph stocks the lake.** For a week, that kind of fish bites in that colour far more often. This
  works whether you release it from the pond, the tank or a catch card. Breed a pair of golden perch, let one go,
  and golden perch start turning up on your line.
- *Colours found* along the bottom of the tab tracks every kind you've seen in each morph. Hover over one to see
  its description, or a hint about when it bites if you haven't found it yet.
- Badges: **Fish Nursery** for raising your first clutch, and **Every Colour** for finding all six morphs.

## The Drowned Stair

An old stone arch in the bank below the garden leads down into flooded caves. Click it (or pick *The Drowned
Stair* in the quick menu at the dock) to start a run. The day stands still while you're down there.

**You go down with nothing.** No rod, no reel: just your hands and a bit of string, which gives a narrower reeling
arc than even the Twig Rod. Everything you use, you find on the way.

- **Floors.** Each floor is a cave with a pool. Press Space or click to cast, wait for the bobber to dip, then hook
  the fish and reel it in on the usual ring. Catch the number of fish the top-left panel asks for and the stone door
  on the right opens: press **E** (or *Go down the stair*) to go deeper. You can keep fishing the pool first for
  more loot.
- **Loot.** Every fish drops pearls, and often gear or something useful. Gear fills five slots: **rod** (wider arc,
  faster swing), **reel** (reels in faster), **line** (strains slower), **lure** (quicker bites, better loot) and
  **charm** (extra hearts, more pearls, or a chance to mend a heart each floor). It comes in five tiers, Worn,
  Sturdy, Fine, Gleaming and Abyssal, and deeper floors drop better tiers. Gear for an empty slot goes on straight
  away.
- **The bag (I or Tab).** Twelve slots. Click an item to see what it does and how it compares with what you're
  wearing (a green ^ marks an upgrade), then *Equip*, *Use* or *Drop* it. When the bag is full, new loot lands on
  the floor. You can swap it in from the bag screen, but whatever is on the floor stays behind when you go down.
- **Things to use:** a *Kelp Wrap* heals a heart, *Glow Worms* make your next three casts bite fast and drop
  better loot, a *Calm Tonic* halves the line strain for one fight, and a *Homeward Shell* takes you out safely,
  keeping everything.
- **Hearts.** You start with three. A snapped line costs one. **Biters** (fish with red eyes) cost one if they get
  away, but they drop double loot. When a biter swims at your lure, reel in to dodge it.
- **Sunken chests** sometimes sit on the bottom of a pool. Fish one up for guaranteed gear.
- **Bosses.** Every fifth floor a boss fish guards the stair: Old Mossjaw, the Lantern Matriarch, the Coral
  Tyrant and the Drowned King. They fight in three stages, like the lake's legends. If one gets away or snaps
  your line, you lose a heart and can try again.
- **The camp.** Beating a boss brings you to a camp. *Climb out* and everything you carry is sold for coins:
  pearls, gear and leftovers. Or *Go deeper*. The deeper floors are richer, and much meaner.
- **Failing.** Lose your last heart, or give up with Esc, and the water carries you back up the stair with
  nothing. **All the loot from that run is lost.** Only your records stay: your deepest floor, runs, bosses beaten
  and best haul.
- Badges: **Into the Deep** for beating your first boss, and **The Bottom Step** for reaching floor 20.

## Wildlife and the Nature page

Animals visit the lake by spot, season, time of day and weather: a grey heron fishing in the shallows at dawn,
a kingfisher diving from the dock pole, a dragonfly resting on it in summer, painted turtles basking on the lily
pads, otters cracking clams on their tummies, deer and foxes on the far shore, an owl on the pole at night, loons
calling at dusk, a beaver slapping its tail, a pair of swans, bats sipping from the lake, a moose wading in the
creek on grey mornings, and the mallards and frogs who are always about. Some say a white stag walks the far
shore on snowy winter dawns. Restoring the shoreline brings three more: a reed warbler, a muskrat and a bittern
(see *The shoreline*).

Press **P** for photo mode and **Space** (or click) to take a photo. The camera frames whatever is in view and
shows how good the shot would be: one star while the animal is on the move, two once it settles, and three if you
catch its special moment (the heron's strike, the loon's call, the swans making a heart). The best photo of each
animal goes on the **Nature** page of the journal, stamped with the day and the place you took it, with a tip on
where to look for the ones you haven't found. You can frame your photos for the cabin wall (see *Your cabin*).
A new animal earns 25 coins, and its first three-star photo 25 more. Photos are saved in the `photos` folder next
to your save.

## Year two

After four seasons a new year begins, and Mayor Hazel writes with the news:

- **Rowan**, a retired lighthouse keeper, moves into the empty cottage by the lookout. Say hello, bring them a
  burbot, and at five hearts they share something from the old lighthouse
- The festival rivals have practised. They score higher every year, and the prizes grow too
- Three new fish arrive in the Deep: the Velvet Perch, the Moonlit Bass and, on foggy nights, the Ghost Carp
- **Master Angler**: a badge for catching every fish (all but the legends) at 80% of its biggest size or more.
  The Badges tab shows how far along you are

## Playing together

Up to four people can fish the same lake. Choose **Play together** on the title screen.

- **Host online**: the game connects to the Lantern Lake online server (in Europe) and gives you a short
  **room code** like `K7Q2-M9XT`. No router settings needed, and it works behind any home network. The code is
  copied for you, shown in the chat, and kept in the pause menu
  (*Copy room code*). Send it to your friends. You can also open a game that is already running from the pause
  menu (*Open my lake to friends*)
- **Join**: paste the room code (*Paste*, or Ctrl+V) and click *Join*. A typing mistake in a code is caught
  before connecting. Lakes hosted on the same Wi-Fi show up by themselves, and you can still type an address
  like `192.168.1.20`
- *Host on this Wi-Fi only* keeps the lake on your home network
- The first time you host, Windows asks whether Lantern Lake may use the network. Allow it, or friends can't
  reach you

**The online server.** It only passes your game's messages between you and your friends. It stores nothing, and
it doesn't log addresses or room codes. Your own game still checks every newcomer. Someone who keeps guessing
codes is shut out for a while, and a code stops working when you close your lake. If your connection to the
server drops for a moment, your game reconnects with the same code.

**Without the server.** If the online server can't be reached, the game falls back to asking your router to
open its port, and gives you a longer room code like `7KQ2M-9X4TB-HC1PE-W3RA`. That code holds your address and a
secret key that changes every time you host. Anyone joining from the internet needs the key, someone who keeps
guessing is shut out for ten minutes, and a connection that floods the lake with messages is dropped. Closing
your lake (or the game) closes the port on the router again.

If going online doesn't work, the chat says why:

- *Automatic port opening is switched off*: turn on UPnP in your router's settings, or forward TCP port
  24680 to your computer by hand (the chat shows its address). You still get a room code
- *Your internet provider shares one address between many homes*: friends can't reach your lake directly.
  Let a friend host, or both install a VPN app such as Tailscale and join with its address

When it uses the router, to learn your public address the game asks the router and also sends one tiny request to a public STUN server
(Cloudflare's, or Google's as a backup), the same kind of service video calls use. Nothing about you is sent.

How it works:

- Everyone keeps their own save: coins, fish, journal, gear and badges. While you visit, you follow the host's
  clock, weather and events, and your own lake keeps its own calendar. You go back to it when you leave
- Friends stand beside you on the dock. If they row out to the same spot as you, you see their boats on the
  water. In Fernwick you see them walking the street. A card on the right lists who is here and where they are
- Catches are shared in the chat. Rare fish get a toast for everyone. On festival days your friends join the
  standings, so you can race each other for first place
- Bedtime is a vote: press Z after 6 PM and you settle down to rest. The night ends when everyone has rested.
  Casting again gets you back up
- While friends are here the lake never pauses, not even in menus
- Press **G** for the Friends window: click a fish in your basket to send it to a friend (it lands in their
  basket), or start a **fishing race**. Everyone gets three minutes, the most fish wins, and the winner gets
  100 coins
- The Friends window's **Expedition** tab starts a shared outing. Together you catch three different kinds of
  fish, someone photographs an animal, and then everyone brings a cooked dish from their pantry to a lakeside
  feast (at least two dishes, or one each for bigger groups). The expedition shows as your tracked objective
  and progress goes to the chat. At the feast everyone earns a souvenir for the cabin: a pennant, a framed
  group photo, or an expedition lantern. Once you have all three, it's coins and golden lures instead. Friends
  who join partway through catch up on the progress. *Call it a day* ends the outing early

## The calendar

Each season is one week long: Moonday, Tideday, Leafday, Feastday, Fishday, Lanternday, Starday.
The calendar (K) shows a three-day weather forecast, the moon phase and every event.

- **Moonday**: Grandma Rosie's almanac letter lists the week's events
- **Tideday and Lanternday**: Wren's Wagon, a houseboat shop, moors on the lake from 6 AM to 8 PM. It sells
  hats, outfits for Biscuit, Moon Lures and Storm Flies
- **Feastday**: a festival with its own rules. Spring Blossom Derby (biggest fish), summer Lantern Night
  (most fish, at night, with fireworks and lanterns), autumn Harvest Haul (longest total), winter Frost Cup
  (points by rarity). The Festival Goldfish only bites on festival days
- **Fishday**: a fish run. One species bites four times as often and sells for 1.5x
- **Starday**: a meteor shower from 9 PM. The sky stays clear, stars fall constantly, and the Starfall Shiner
  only bites tonight
- **Birthdays**: eight villagers have birthdays. Bring them their favourite fish for a gift (a frog hat, a cat
  bow, a rowboat, a garden gnome and more)

## Features

- Day and night cycle (one day is 12 real minutes), four seven-day seasons, and weather: clear, cloudy, rain with
  thunder, fog and snow
- 70 fish, including event fish, 9 that only live at the rowboat spots, 19 from the sea at Saltmarsh, 15 caught
  with the crab pot, fly rod, ice auger or on rare nights, and 3 that arrive in year two, plus treasures and 10
  bottled letters to collect
- Saltmarsh, a second region down the river: a harbour village with five new neighbours, tides that change what
  bites, daily orders, beachcombing, a boatyard and a lighthouse to light again
- Aim your casts. Bubbling hotspots on the water give quicker bites and rarer fish
- A character creator with a living diorama: skin, hair colour and style, eyes, beards, five tops in eight
  seasonal palettes, trousers and boots, a rod keepsake, a way of waiting for bites, and Biscuit's coat
- Cabin fish tank (8 fish) and a wardrobe with 7 hats and 5 outfits for Biscuit
- Six colour morphs that any lake fish can bite in (golden, ghost, shadow, koi, starry and prism), and a hatchery
  pond where pairs lay eggs and the young can inherit their parents' colours
- The Drowned Stair: a roguelike fishing dungeon under the hill. Start with nothing, find gear for five slots in
  a twelve-slot bag, beat a boss fish every fifth floor, and climb out with your haul, or lose it all
- 33 badges with coin rewards (Journal, Badges tab)
- A walkable aquarium with twelve themed exhibits, benches and visitors
- A cabin garden with 13 crops, and 19 animals to photograph for the Nature page and frame on your wall
- Three shoreline restoration projects that change the lake and bring new animals
- Biscuit's discoveries in Fernwick: Grandma Rosie's diary, her old lures, and a secret
- A calm HUD that steps aside while you fish, with one tracked objective
- Four legend hunts, one a season, with tales, clues, crafted lures and three-stage fights
- Co-op for up to four players: over the internet with a room code, or on your home Wi-Fi, with gifts, races
  and shared expeditions
- Shop: rods, bait, a dock lantern and nine dock decorations, including a telescope that brings more and luckier
  shooting stars. Anything new on the dock gets a bouncing arrow and its name for a few seconds, so you see where
  it went. Until the town funds the lighthouse, its timber frame waits on the far shore
- Daily fish requests from the villagers through the mailbox
- Luck: pet Biscuit once a day, release fish, wish on shooting stars
- Generated ambience (water, rain, crickets, wind, birds, wind chimes, and the town sounds) and gentle kalimba
  music: a written tune for each season by day (*Thaw*, *Long Afternoon*, *Woodsmoke*, *First Snow*), for dawn
  (*Mist on the Water*), dusk (*Lanterns*), night (*Stars on the Lake*) and the village (*Market Day*, with a
  soft walking bass). Each plays once through, then the music rests for half a minute or so and you just hear
  the lake
- Three save slots (title screen, *Save slots*). Slot 1 is `save.json` and slots 2 and 3 are `save2.json` and
  `save3.json`. Deleting a slot keeps a `.bak` copy. The game saves automatically. Older saves are moved onto
  the new seven-day calendar

## Developer checks

```
python main.py --shots <folder>   # headless screenshots of every season, event and menu
python main.py --bot 1500         # headless auto-fishing soak test
# add  --size 1920x1080  to either one to test a different window size, and  --ui 75  for an interface size
python main.py --bot 150 --host --port 24791 --speed 8              # a bot that hosts (localhost only)
python main.py --bot 120 --join 127.0.0.1:24791 --name Mira       # a second bot that joins it
```

## Releasing an update

`tools\release.py` builds the exe and publishes updates through GitHub Releases. Its settings are in
`release.json` (`"github": "your-name/your-repo"`; the repository must be public).

```
python tools\release.py bump 1.5.1 "What changed." "Another change."
python tools\release.py build      # build\LanternLake (the exe + game) and release\<version>\
python tools\release.py install    # refresh E:\game\Lantern Lake (your saves there are kept)
python tools\release.py upload     # needs GITHUB_TOKEN set; makes the GitHub release
```

A release has three files: `manifest.json` (version, notes, checksum), `lantern-lake-game-<version>.zip` (what
the launcher downloads) and `LanternLake-<version>-windows.zip` (the full game, for new players). Launchers find
the newest release at `github.com/<repo>/releases/latest`. A change to `launcher\launcher.py` itself needs a new
full download: raise its `LAUNCHER_VERSION`, set `"min_launcher"` in release.json to match, and the old launcher
sends players to the release page instead of updating. `tools\make_art.py` redraws the icon and the banner.
