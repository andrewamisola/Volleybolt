# Achievements — design spec (2026-10-01)

Owner-approved scope: the 20-achievement list below, "approach 1" (one rules list), shown in a new
Achievements tab inside Career, announced on the end-of-match screen, with a red dot on Career until
seen. Later, achievements are what cosmetic unlocks and a Steam bridge hang off.

## 1. Rules

- **Counts in any match you play:** vs AI, online 1v1, online doubles. **Never** in spectate or the
  headless simulator (`isSpectating()` / `_simHeadless`).
- **"You" = the local side**: `localSide = gameMode === 'pvp' ? getLocalSide() : 'left'` (doubles:
  your team). Never key on `'left'`/`'player'` directly — that breaks for the online guest.
- **Live pass only:** every counter sits behind `!isResimulating` / `!ctx.isResimulating`, so rollback
  re-simulation never double-counts. Achievements never touch sim state (determinism unaffected).
- **Awarded at match end only.** Per-match feats are collected during the match, then checked and saved
  together when the match ends (same moment career stats are committed). A match you quit earns
  nothing — consistent with career stats today.
- **Symmetric game, one-sided bookkeeping:** the AI earns nothing; nothing about the rules changes.

## 2. The list (stable IDs for Steam later)

| ID | Name | Earned when |
|---|---|---|
| **Milestones** (lifetime) | | |
| `FIRST_BRINE` | First Brine | Win your first match |
| `SEASONED` | Seasoned | Win 10 matches |
| `PICKLED` | Pickled | Win 50 matches |
| `FERMENTED` | Fermented | Win 100 matches |
| `WALL_OF_DILL` | Wall of Dill | 500 successful parries |
| `PYROMANCER` | Pyromancer | Cast 1,000 Fireballs |
| **Feats** (one match) | | |
| `PICKLE_MONK` | Pickle Monk | Win without casting anything (no Fireball, Chill Dill, Thunderstorm or Juice) — paddle and parry only. Rare. |
| `CLEAN_SWEEP` | Clean Sweep | Win without losing a round |
| `COMEBACK_KID` | Comeback Kid | Win after being pushed back to your own core |
| `SPEED_BRINE` | Speed Brine | Win with the match clock under 3:00 |
| `MARATHON` | Marathon | Win with the match clock past 10:00 |
| `UNTOUCHED` | Untouched | Win a round with your structure at the same HP it started the round with |
| **Spell mastery** | | |
| `RETURN_TO_SENDER` | Return to Sender | Parry an enemy Chill Dill and freeze its caster with it |
| `COLD_WAR` | Cold War | Cancel an enemy Chill Dill with your own (the Shatter clash) |
| `STORM_CHASER` | Storm Chaser | Zap 3 projectiles with one Thunderstorm |
| `MAX_RALLY` | Max Rally | Send a Fireball up to top tier yourself (your hit/parry takes it to 6 damage) |
| `JUICE_CLASH_CHAMPION` | Juice Clash Champion | Win a beam clash |
| `PICKLED_IN_ICE` | Pickled in Ice | Freeze opponents 5 times in one match |
| **Pressure** | | |
| `OVERTIME_HERO` | Overtime Hero | Win a round in overtime (round 10+) |
| `DEMOLITION` | Demolition | Break the enemy territory, then win at their core the very next round (a two-round finishing push, no lost round in between) |

Feats marked "win a round" (Untouched, Overtime Hero) and the spell-mastery ones only need to happen
during a match; they don't require winning the match. They are still awarded when the match ends.

## 3. Architecture (approach 1: one rules list)

A single new block in index.html, `Achievements`, next to `StatTracker`:

- **`ACHIEVEMENTS`** — the table above as data: `{ id, name, desc, group, check, progress? }`.
  Milestones read lifetime numbers from `StatTracker.get(key, 'career')` and expose
  `progress: () => [current, target]` for the progress bar.
- **`matchFlags`** — a plain per-match object (`castsByMe`, `roundsLost`, `wasOnOwnCore`,
  `untouchedRound`, `overtimeRoundWon`, `returnToSender`, `coldWar`, `stormChaser`, `maxRally`,
  `beamClashWon`, `freezesInflicted`), reset in `resetGame()`.
- **`Achievements.note(event, data)`** — the only call game code makes. Each hook is one line.
- **`Achievements.evaluateMatchEnd(localWon)`** — called once from `endRound` when `gameOver` is set,
  after `StatTracker.commitMatch()`. Runs every `check`, returns the newly unlocked IDs, saves them,
  and stores them for the end screen.
- **Storage:** localStorage `volleybolt_achievements` =
  `{ v: 1, unlocked: { ID: { at: <epoch ms> } }, seen: { ID: true } }`. Read with try/catch; a
  corrupt or missing entry means "nothing unlocked".
- **Steam hook:** `Achievements.onUnlock(cb)` — empty today; a later Steamworks bridge subscribes and
  calls `SetAchievement(ID)`.

## 4. Where each achievement is detected

| Achievement | Hook (current lines) |
|---|---|
| Win milestones, Clean Sweep, Comeback Kid, Speed/Marathon, Pickle Monk | `endRound` (~27764): `localWon` (27833); match over at `gameOver = true`; clock from `getMatchClockFrames()` (3600 frames = 1 min) |
| Wall of Dill | career `parries_successful` (14160) — fix it to count the local side |
| Pyromancer | career `fireball_casts` (27064) |
| Pickle Monk (casts) | `tryNetworkCast` success / `onCast` for fireball, frostbolt, thunderstorm, Juice — local caster |
| Comeback Kid | after `currentStage` changes in `endRound` (27901 / 27942): `isOwnCore(localSide, currentStage)` |
| Untouched | snapshot structure HP in `resetRound()` (25766); compare at `endRound` (covers fireballs, beam and clash damage alike) |
| Overtime Hero | `endRound`: local side won and `totalRoundsPlayed >= SIM_RULES.overtimeStart` after the increment |
| Return to Sender | frostbolt `onPaddleHit` (2598), live block: `proj.isParried && proj.parriedBy === localOwner` and the frozen side isn't local. Add `proj.castBy` at spawn (13515) and carry it through rollback snapshots so a double-parry can't fake it |
| Cold War | `onChillClash` (sim.js:355) — pass both projectiles; one is local, one enemy |
| Storm Chaser | `thunderstormZap` (24853): `zapsToPerform >= 3` and the caster is local |
| Max Rally | the three tier raises (fireball `onPaddleHit` 2505, `parryProjectile` 14169, overpower sim.js:410/416): tier reaches 4 from a local hit |
| Juice Clash Champion | `onBeamClashResolve` (24796): `winner` is local |
| Pickled in Ice | frostbolt `onPaddleHit` freeze (2605): frozen side isn't local → `freezesInflicted++` |
| Demolition | `endRound`: when `territoryFalls` and the winner is local, `matchFlags.territoryBrokeRound = totalRoundsPlayed` (after the increment). At the local match win: `territoryBrokeRound === totalRoundsPlayed - 1`. Only possible under `SIM_RULES.lanes` `'moba'` (live) / `'fresh'` — the lanes that destroy territories |

## 5. Bugs to fix along the way (found while mapping hooks)

These are wrong today and would make achievements wrong:

1. **`isLocalPlayer` goes stale.** After playing online as the guest (or a non-left doubles slot),
   single-player keeps `combatants.left.isLocalPlayer === false`, so Fireball/Chill career casts stop
   counting. Reset it at single-player match start.
2. **Thunderstorm career stats count everyone's casts** (24895) — gate on the local caster.
3. **Round/match win-loss stats and `parries_successful` key on the left side** — wrong for the online
   guest. Switch to `localWon` / local side.
4. **`damage_dealt` / `damage_taken` aren't rollback-gated** (27717/27721) — double-count online.
5. Unused career stats get wired while we're in there: `projectiles_blocked` (paddle blocks),
   `freeze_time_inflicted` (1.0 s per freeze). "Perfect parry" has no definition in the game today,
   so `parries_perfect` stays unused (not needed by any achievement).

## 6. UI

- **Career screen gets two tabs:** *Stats* (today's card grid, unchanged) and *Achievements*. Tab
  styling follows the existing menu buttons; gamepad/keyboard switch with the same page control How To
  Play uses.
- **Achievements tab:** a grid of cards grouped Milestones / Feats / Spell mastery / Pressure. Each card:
  name, one-line description, locked (dimmed) or unlocked (gold rim + date). Milestones show a progress
  bar (`37 / 50`). Newly unlocked, not-yet-seen cards get a small red dot; opening the tab marks them seen.
- **Red dot** on the main-menu Career button (and the Achievements tab) while anything is unseen.
- **End screen:** after the match summary, a "Achievement unlocked" strip listing what this match
  earned (name + description), rising in with the rest of the end screen. Nothing pops up mid-match.

## 7. Testing

- `dbg.achievements` — `list()`, `reset()`, `unlock(id)` for UI checks.
- `dbg.achTest = true` lets a spectated / headless sim match count for the **left** side, so the
  headless simulator can exercise every hook quickly (normally excluded). Run ~40 sim matches and
  check the counts look sane (e.g. Pickle Monk ~never, Clean Sweep sometimes, Max Rally often).
- Determinism oracle (`dbg.determinism`, `aiDeterminism`) must be unchanged — achievements never write
  sim state. `proj.castBy` is the one new sim field; it's not hashed (presentation/bookkeeping only),
  so the fold should hold.
- Online: verify a guest win credits the guest, and a rollback-heavy match doesn't double count.

## 8. Resolved — Demolition (owner, 2026-10-01)

The draft said "destroy both enemy territories and their core in one match", but each side has **one**
territory and you can't reach the enemy core without breaking it, so every win would have earned it.
Owner picked **back-to-back push**: the round that breaks the enemy territory is immediately followed
by the winning round at their core. Losing at the core after breaking the territory sends you back
over the (still-down) territory to Midfield, and that push no longer counts.

## 9. Out of scope

Cosmetic unlocks, Steam integration itself, hidden/secret achievements, per-mode achievement sets,
cloud sync.
