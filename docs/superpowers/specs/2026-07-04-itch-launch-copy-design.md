# Volleybolt itch.io Launch Copy and Kit

**Date:** 2026-07-04
**Status:** Draft for owner review
**Author:** Claude (with Andrew)
**Purpose:** Everything written needed to publish Volleybolt on itch.io as a free, in-browser open playtest, and to funnel players into Discord and toward a future Steam release.

**Voice:** Modeled on the League of Legends "How to Play" page. Second person. Short declarative sentences, rarely over 15 words. Section headers are imperative and uppercase. Colons introduce mechanics. No em dashes. Exclamation points are rare. State mechanics as facts and let them sell the game. Do not close sections on a slogan.

**Placeholders to fill before publishing:** `[DISCORD_INVITE]` (the Discord invite URL), `[STEAM_URL]` (the Steam page once it exists), `[PLAY_URL]` (the itch project URL or embed), and `[CONFIRM_KEYS]` (exact keybinds). These are the only unresolved items.

---

## 1. Positioning

**Game name:** Volleybolt

**Tagline (recommended):** Volleybolt. Pong, Evolved.

**Tagline alternates (objective, pick one):**
- Volleybolt. Pong, Evolved.
- Real-time spell duels. Perfectly fair.
- Rally. Cast. Topple the tower.
- A 1v1 spell duel where skill is the only advantage.

**One-liner (itch "short description" field, keep under ~200 characters):**
Volleybolt is a 1v1 spell duel. Rally a volley, break it past your opponent with spells, and destroy their tower. Both players are identical, so matches come down to skill.

**Elevator pitch (2 sentences, for a Steam blurb or a tweet):**
Volleybolt is a real-time 1v1 game that turns a rally of Pong into a spell duel with a tower to destroy. Both wizards are identical, so every match is decided by timing, positioning, and shot selection.

---

## 2. itch.io store description (paste-ready)

### 2.1 Short description (the summary field itch shows on cards and search)

> Volleybolt is a 1v1 spell duel. Rally a volley, break it past your opponent with spells, and destroy their tower. Both players are identical, so matches come down to skill.

### 2.2 Full "About" body (paste into the page description)

Volleybolt is a real-time 1v1 game that turns a rally of Pong into a spell duel with a tower to destroy.

You and your opponent rally a volley back and forth. You cast spells to break the volley past your opponent and land it on their tower. Take the tower down and you win the stage. Win the stage and you push forward. Reach their core and destroy it to win the match.

**EVERYTHING IS FAIR**

Both wizards are identical. Same speed. Same mana. Same cooldowns. Same spells. Nothing is unlocked, bought, or leveled to make you stronger. The only thing that changes a match is how well each player reads the volley, times a cast, and holds position.

**KNOW YOUR SPELLS**

Fireball: your main attack. Send a shot at the enemy tower.
Frostbolt: freeze an opponent who is lined up in front of you.
Thunderstorm: clear several incoming shots at once when you are under pressure.
Parry: send an incoming shot straight back at whoever cast it.

Mana and cooldowns gate every spell. You pick your moments.

**UNLEASH OVERDRIVE**

Every action charges your Overdrive bar. Casts, parries, damage dealt, hits taken.
Fill it and unleash a channeled beam. Aim it by moving. It burns through fireballs and melts the enemy tower.
Your opponent has two answers: stand in the beam's lane to block it, or freeze you during the windup to cancel it.
If both players fire at once, the beams clash in the middle. Hold the line or lose it.

**PLAY SOLO OR ONLINE**

Solo: face an AI that reads your skill and adjusts to keep matches close. Beat it and it sharpens. Lose and it eases off.
Online: play real-time matches against another player.

**PICK UP AND PLAY**

Volleybolt runs in your browser. No download. No account. Keyboard and controller are both supported.

**THE PLAYTEST IS OPEN**

Volleybolt is in active development and free to play right now. Play a few matches, then tell us what felt good and what did not. Join the Discord to send feedback and follow the build. Wishlist on Steam to get the full release at launch.

Play now: [PLAY_URL]
Join the Discord: [DISCORD_INVITE]
Wishlist on Steam: [STEAM_URL]

### 2.3 Controls block (paste under the About body or into a "How to Play" section)

**HOW TO PLAY**

Move your wizard up and down to cover the volley.
Cast a spell to break the volley past your opponent.
Parry a shot to send it back before it reaches your tower.
Fill your Overdrive bar and unleash the beam.
Watch your mana and cooldowns. You cannot cast on empty.

Keyboard: W and S or the arrow keys to move. 1, 2, 3 for spells. Space to parry. Q for Overdrive. Escape to pause.
Controller: stick or d-pad to move. Face buttons for spells. RB to parry. Y for Overdrive. Start to pause.

(CONFIRMED from code 2026-07-06: keys[Digit1-3]=loadout slots, Space=parry, Q/KeyQ=juice, Esc=pause; pad GP={slot0:X(2), slot1:A(0), slot2:B(1), ult:Y(3), parry:RB(5)}.)

---

## 3. Feature bullets (the scannable list)

Use these on itch under the description or as a short "Features" block. Objective, one line each.

- Real-time 1v1 spell duels.
- Fully symmetric. No upgrades, no pay-to-win. Skill decides every match.
- Four spells: Fireball, Frostbolt, Thunderstorm, and Parry.
- Overdrive: charge an ultimate beam, aim it by moving, clash it against theirs.
- Rally the volley, break it, and topple the enemy tower across a MOBA-style push.
- An adaptive AI that tracks your skill and keeps matches close.
- Online 1v1 against another player.
- Keyboard and controller support.
- Plays in your browser. No download.
- Low-poly, PS1-era art with a CRT finish.

---

## 4. itch.io page setup

Concrete settings for the itch.io "Edit game" form.

- **Title:** Volleybolt
- **Short description / tagline:** the one-liner from section 1.
- **Classification:** Games.
- **Kind of project:** HTML (playable in browser). Upload the build as a zip with `index.html` at the root, or embed the hosted build.
- **Pricing:** No payments (free). Optionally enable "donations" so fans can tip, but keep the price free and the barrier at zero for the playtest.
- **Uploads / embed:** set the viewport to the game's 16:9 ratio. Suggested embed size: 1280 x 720 (or 960 x 540 for lower-power machines). Enable the fullscreen button. Enable "Click to launch" so audio starts on a user gesture. Leave "mobile friendly" off. This game targets keyboard and controller.
- **Genre:** Action.
- **Tags (itch allows up to 10, use specific ones):** `1v1`, `arcade`, `competitive`, `fantasy`, `magic`, `multiplayer`, `pvp`, `retro`, `singleplayer`, `wizards`. (Alternates if you want to swap: `pong`, `versus`, `low-poly`, `local-multiplayer`.)
- **Community:** turn Comments on. Add the Discord link as a page link (see section 6).
- **Links:** add "Wishlist on Steam" as an external link once `[STEAM_URL]` exists.
- **Visibility:** publish as Public when ready, or Restricted while you share it with a first wave of testers.

---

## 5. Asset checklist (what to capture and make)

The page needs images. **UPDATE 2026-07-06: the `brand/` pack (from the art-bible pass) already covers most of this** — spell GIFs (`brand/spells/fireball.gif`, `frostbolt.gif`, `thunder.gif`, `parry.gif`), world shots (`brand/world/arena-wide-1/2.png`, `arena-fireball-rally.png`, `tower-blue/red.png`), UI (`brand/ui/main-menu.png`), and character turnarounds. Still worth capturing fresh: an OVERDRIVE beam shot / clash GIF (the new signature moment — best cover-image candidate) and a tower-fall. Capture the rest from the running game if the brand crops don't fit itch's ratios.

- **Cover image (required):** 630 x 500 px. itch crops it to that ratio, so frame it there. Put the logo and one clean action shot of a spell mid-volley. An animated GIF is allowed for the cover and stands out in listings.
- **Screenshots (3 to 5):** 
  1. A Fireball breaking past the opponent toward the tower.
  2. A Frostbolt freeze landing on a lined-up opponent.
  3. Thunderstorm clearing multiple incoming shots.
  4. A Parry sending a shot back.
  5. The tower taking a hit or falling at the end of a stage.
- **Trailer or hero GIF (optional but high value):** a 10 to 20 second loop. Shot list: rally, one Parry, one Frostbolt freeze, a Thunderstorm clear, a tower falling. No text overlay needed. Capture at the game's native resolution so the CRT and PS1 look read clearly.
- **Logo / banner:** reuse the existing Volleybolt wordmark from the landing page and design system for a consistent look.

Capture tip: play a real match against the AI and record it, then cut the cleanest few seconds of each spell.

---

## 6. Community and funnel copy

### 6.1 Discord call to action (paste-ready)

**JOIN THE DISCORD**

Volleybolt is built in the open. Come play, report bugs, and shape what gets built next. Post feedback after a match and it goes straight to the dev.
Join: [DISCORD_INVITE]

Short button label: `Join the Discord`

### 6.2 Steam funnel (paste-ready, use once the Steam page is live)

**COMING TO STEAM**

The full version of Volleybolt is coming to Steam. Wishlist it now to get notified at launch and to help the game get seen.
Wishlist: [STEAM_URL]

Short button label: `Wishlist on Steam`

Note: a Steam wishlist only works once you have a Steam "Coming Soon" page. Until then, keep the copy but point it at Discord, or hide the Steam button.

---

## 7. Launch devlog (first post, paste-ready)

Title: **The Volleybolt playtest is open**

Volleybolt is playable in your browser right now, and it is free.

Volleybolt is a real-time 1v1 spell duel. You rally a volley, cast spells to break it past your opponent, and destroy their tower. Both players are identical, so matches come down to skill.

This is an open playtest. The game is in active development, and your feedback decides what gets built next. Play a few matches against the AI or another player, then tell me what felt good and what did not.

What I want to hear:
- Did matches feel fair.
- Did any spell feel too strong or too weak.
- Did the AI feel like a good opponent at your level.
- Anything that broke.

Play now: [PLAY_URL]
Join the Discord: [DISCORD_INVITE]

Thanks for playing.

---

## 8. Notes for consistency

- Keep the name styled as "Volleybolt," one word, capital V.
- Keep "Pong, Evolved." as the tagline unless section 1 alternates are chosen.
- The four spells are Fireball, Frostbolt, Thunderstorm, and Parry. Do not list spells that are cut (Gravity Sphere, Snowball, Spark, Boulder are not live).
- Describe fairness as a feature, not a slogan. State it plainly: identical stats, no upgrades, no pay-to-win.
- Do not mention the pickle-wizard theme. It is a character skin, not the game's identity, and it is not final.
- No em dashes anywhere in published copy.
