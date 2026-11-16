# Lantern Lake guide

[Back to Lantern Lake](../README.md)

## Controls

| Action | Input |
|---|---|
| Wind up and cast | Hold left click or Space, point where it should land (mouse or arrow keys), let go |
| Hook a bite | Click when the bobber goes under (ignore nibbles) |
| Reel | Keep the golden arc on the fish (mouse, or A / D). Hold to reel faster, let go when it lunges |
| Leap | When the fish jumps, click or press Space as the shrinking ring meets the gold ring |
| Keep / put in tank / release a catch | Space / T / R |
| Journal, Shop, Cabin, Calendar, Rest | J, S, C, K, Z (or the buttons bottom-right) |
| Change bait | Tab |
| Lake map (row to another spot) | B, the Boat button, or click the rowboat by the dock |
| The lanterns (your long-term goal) | L, or click the lantern line on the left of the screen |
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
Calendar, Cabin, Pet Biscuit, Mailbox, Wren's Wagon (when it's moored), Lake map, Lanterns, Walk to Fernwick /
Back to the lake, Rest until morning, Photo mode, music on/off, Chat (when playing together) and the four
emotes. When a shooting star is falling, *Wish on the shooting star!* is at the top. In photo mode the bottom
button takes a photo, the left button saves a picture of the screen, and any other button leaves.

Text boxes (your name, the host's address, chat) open an **on-screen keyboard** when you use a controller:
d-pad or stick to pick a key, bottom button to type, right button to delete, top button for a space, left
button for capitals, and Menu / Options / + when you're done.

## Options

Open Options from the title screen or the pause menu (Esc). Settings are kept in `settings.json`, separate from
your save, so they stay the same when you start a new game.

- **Audio**: master, music, sound effects and ambience volume sliders
- **Display**: fullscreen, window size, interface size (50% to 110% for the HUD and menus), frame rate limit
  (30 / 60 / 120 / 144), a frame rate counter, screen shake (off / gentle / full) and the camera zoom while reeling.
  The interface size row lists which sizes land on whole screen pixels for your window. Those are the sharpest
  and also the fastest to draw (on a 1080p screen: 67% and 100%)
- **Gameplay**: relaxed reeling, day length (slow, normal or quick days), 12 or 24-hour clock, the HUD style
  (see below), hints, pausing when you switch to another window, and the first-day tips (seven short tips at the top of the screen
  in a new game, each gone once you've done it, with a Skip button)
- **Controls**: rebind the keyboard keys, or see the controller buttons when a pad is in use

### The HUD

The top left shows the clock and **one tracked objective**: a villager's request, a birthday or today's festival.
When there are two, a small arrow on the card switches between them (dots show which one you're on). The live
festival comes first, then the request. Under it are the day's notes: snacks, visitors, fish runs, the sky.

The **HUD** setting (Options > Gameplay) has three styles:

- **Calm** (the default): while a cast is out, the menu toolbar slides away and the day's notes step aside, so
  it's just you and the water. The keys (J, S, C, K...) still work, and pointing at the bottom-right corner while
  you wait for a bite brings the toolbar back
- **Compact**: like Calm, with a small clock, coin and bait display
- **Full**: everything stays on screen, as before

The whole screen, menus and text included, is pixel art on the lake's 640x360 grid. Panels have wooden frames,
and the text uses a bitmap font drawn in code (`pixfont.py`). Fullscreen uses your monitor's own resolution, and
whole-number sizes (1280x720, 1920x1080, 2560x1440) give perfectly square pixels. Other window sizes are scaled
with a sharp-then-smooth filter so the pixels stay even.

## Reeling

The hooked fish swims around a ring and you steer a golden arc to stay on it. While it is inside the arc
the line comes in, and outside it the fish gets away. Holding the button reels faster but builds line strain.
Fish shake and show a "!" before they lunge, and holding through a lunge snaps the line. Calm fish drift,
small ones dart, eels zigzag and big fish make long runs. Rarer fish also leap out of the water for a timing
challenge (Perfect gives a big boost, a miss costs you), and golden glimmers on the ring are worth a few coins.
The camera leans in during the fight. Better rods have a wider, faster arc. "Relaxed reeling" in the pause
menu gives a wider arc, longer warnings and slower leaps. The arc has brackets and the strain bar is hatched,
so it does not rely on colour.

## The rowboat and fishing spots

Wren's Wagon sells a rowboat for 500 coins. Fen's birthday gift, the Little Rowboat, works too. Once you have
one, open the lake map (B) and row to one of three new places. Biscuit comes along. You row home
automatically when you rest for the night.

- **Lily Cove**: shallow water full of lily pads and frogs. Bites come quickly, but casts never reach deep water.
  Home of the Mud Bullhead, the Lily Gourami and the Velvet Tench
- **The Deep**: the middle of the lake. Bites are slow, but there are few small fish and more rare ones,
  bigger catches and more pearl clams. Home of the Silver Cisco, the Midnight Burbot and the legendary Mossback
  Muskie
- **Willow Creek**: where the river comes in. The current carries your bobber downstream while you wait.
  Home of the Creek Chub, the Sail Grayling and the River King Salmon. In autumn the salmon run upstream at
  any hour

Each spot also has some of the lake's own fish. The map shows how many species you've found at each spot, and
the journal has a second page (Rowboat) for the new fish.

## Fernwick village

Press T (or the Town button) to walk up the lane to Fernwick, a little village street three screens long.
Walk with A and D or click where you want to go. Clicking a shop or a neighbour walks you there and goes
in. Seven townsfolk keep their own day: they open their shops, wander the street, shelter under umbrellas
in the rain and gather in the square in the evening. Shops keep opening hours.

- **Old Tom's Tackle**: the shop you know, inside a real building now
- **Mabel's Bakery**: one treat a day each, lasting until bedtime. Honey Bun (luck), Lakeside Tea (fish bite
  sooner), Blueberry Pie (bigger fish) and Star Cookie (rare fish come more often). The *Recipes* tab sells
  her recipe cards for your kitchen
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
- **Lookout bench**: sit at the east end and watch the lake for a little luck. On a clear night, lie back and look
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
at closing time.

Every fish you donate swims in one of ten themed exhibits: Lantern Lake, Lily Cove, Willow Creek, The Deep,
Legends of the Lake (a round brass porthole), Under the Ice, Crab Pot Corner, Spring & Summer, Autumn & Winter,
and Weather & Wonders. Press E at a tank to see who belongs there, read about them, and donate straight from
your basket.

- **Finish an exhibit** for a one-time coin reward, from 150 to 600 coins. Finish five for the *Curator* badge. If
  you filled exhibits before they existed, Juniper pays you the first time you walk in
- **Benches** sit in front of four of the tanks. Sit a while to read about the fish drifting past (+0.3 luck,
  once a day)
- **Visitors**: two neighbours wander in each day and react to your discoveries. Chat with them for a little
  friendship, once a day each

Talk to anyone (E) once a day to grow your friendship, and give them a fish. Everyone has a favourite, and a
loved fish counts for a lot. At 3, 6 and 10 hearts they send you a letter with a gift. Finishing a mailbox
request also makes a friend. Resting for the night walks you home to the lake.

What people say changes with the season, the weather, the time of day and festivals, and close friends talk
more openly. At **5 hearts** each neighbour has a short scene with you, played out on the street the next time
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

When a lantern is ready it pulses on the far shore. Row to its spot and light it from the lanterns window, which
plays a short scene and gives you some luck. Once all four burn, come down to the dock one evening (after 7:30 PM) for
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

The cabin's **Home** tab shows your room. Click a spot on the wall or floor, then pick something from the
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

- **Host online**: the game asks your router to open its port and gives you a **room code** like
  `7KQ2M-9X4TB-HC1PE-W3RA`. It is copied for you, shown in the chat, and kept in the pause menu
  (*Copy room code*). Send it to your friends. You can also open a game that is already running from the pause
  menu (*Open my lake to friends*)
- **Join**: paste the room code (*Paste*, or Ctrl+V) and click *Join*. A typing mistake in a code is caught
  before connecting. Lakes hosted on the same Wi-Fi show up by themselves, and you can still type an address
  like `192.168.1.20`
- *Host on this Wi-Fi only* keeps the lake on your home network
- The first time you host, Windows asks whether Lantern Lake may use the network. Allow it, or friends can't
  reach you

The room code holds your address and a secret key that changes every time you host. Anyone joining from the
internet needs the key. Someone who keeps guessing is shut out for ten minutes, and a connection that floods
the lake with messages is dropped. Closing your lake (or the game) closes the port on the router again.

If going online doesn't work, the chat says why:

- *Automatic port opening is switched off*: turn on UPnP in your router's settings, or forward TCP port
  24680 to your computer by hand (the chat shows its address). You still get a room code
- *Your internet provider shares one address between many homes*: friends can't reach your lake directly.
  Let a friend host, or both install a VPN app such as Tailscale and join with its address

To learn your public address, the game asks the router and also sends one tiny request to a public STUN server
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
- 51 fish, including event fish, 9 that only live at the rowboat spots, 15 caught with the crab pot, fly rod,
  ice auger or on rare nights, and 3 that arrive in year two, plus treasures and 10 bottled letters to collect
- Aim your casts. Bubbling hotspots on the water give quicker bites and rarer fish
- Cabin fish tank (8 fish) and a wardrobe with 7 hats and 5 outfits for Biscuit
- 27 badges with coin rewards (Journal, Badges tab)
- A walkable aquarium with ten themed exhibits, benches and visitors
- A cabin garden with 13 crops, and 19 animals to photograph for the Nature page and frame on your wall
- Three shoreline restoration projects that change the lake and bring new animals
- Biscuit's discoveries in Fernwick: Grandma Rosie's diary, her old lures, and a secret
- A calm HUD that steps aside while you fish, with one tracked objective
- Four legend hunts, one a season, with tales, clues, crafted lures and three-stage fights
- Co-op for up to four players: over the internet with a room code, or on your home Wi-Fi, with gifts, races
  and shared expeditions
- Shop: rods, bait, a dock lantern and nine dock decorations, including a telescope that brings more and luckier
  shooting stars
- Daily fish requests from the villagers through the mailbox
- Luck: pet Biscuit once a day, release fish, wish on shooting stars
- Generated ambience (water, rain, crickets, wind, birds, wind chimes, and the town sounds) and gentle kalimba
  music that changes with the seasons (bright spring, lazy summer, a minor-key autumn, slow winter bells), with a
  soft walking bass in Fernwick
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
