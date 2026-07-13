# Doubles Mode — Design

**Date:** 2026-07-12
**Status:** M1 approved for planning. M2/M3 sketched only — each gets its own spec later.
**Owner:** Andrew

## Goal

Bring back 2v2 Doubles — this time built on the deterministic sim (the legacy doubles was
deleted 2026-07-01 in `b7e492b` along with `updateGameLogic`; nothing revivable remains).
End state across all milestones: four people join a pregame lobby, pick red/blue
fighting-game-style, ready up, and play 2v2 online. AI fills any empty slots.

## Decomposition (approved: Approach A — three stacked, individually shippable milestones)

- **M1 (this spec):** Doubles rules on the deterministic sim, playable locally as
  1 human + 3 AI from the Start Battle menu. Zero netcode changes.
- **M2 (future spec):** 4-player netcode — host-relay star topology (guests connect to the
  host, host relays inputs, all four clients run the sim with rollback). Doubles-only
  `INPUT_DELAY` increase (~3-4 frames) expected for the relay hop.
- **M3 (future spec):** 4-player lobby — P1-P4 join, side select (red/blue; front slot
  fills first, Swap button to trade front/back before readying), ready-up, AI fills
  empty slots at match start.

Rationale: every M2 desync gets debugged against rules already proven in M1 — netcode
bugs and rules bugs never overlap. Each milestone merges to master green without touching
singles or 2-player PvP.

## Locked decisions (apply to all milestones)

| Decision | Value |
|---|---|
| Slot filling | Any mix — 1-4 humans, AI fills empty slots |
| Court model | Front/back rails per side |
| Arena scaling | Doubles court Z extent = singles × **4/3** (tennis 27→36 ft ratio); X unchanged |
| Kits | Full kit per wizard (fireball / frostbolt / thunderstorm / parry) |
| Mana | **Shared team pool**, singles-sized — per-side casts/sec identical to singles |
| Juice | **Shared team bar**; charge events from either teammate feed it |
| Overdrive caster | **PROVISIONAL: front wizard only** (no friendly block in the beam path). Revisit after playtest — explicitly not final |
| Friendly fire | Projectiles never collide with the caster's own team (teammates can't block your shots) |
| Freeze | Frostbolt freezes only the wizard it hits |
| Match structure | Identical to singles (tug-of-war stages, gate health, round flow). Revisit after playtest if the campaign frame feels wrong for party matches |
| Position pick (M3) | Choosing a side fills FRONT first, then BACK; lobby Swap button trades positions |
| Randomness | **None, ever** — all AI seeded-deterministic (standing design law) |

## M1 — Architecture

### teamSize, not a new gameMode

Doubles is `gameMode: 'single'` + `teamSize: 2` (a new ctx/const, default 1). It is NOT a
new gameMode value. Every existing singles path — input, pause, HUD plumbing, GameSM,
the parry-HUD fix — works untouched; only code that genuinely cares about the second rail
checks `teamSize`. In M2, online doubles becomes `gameMode: 'pvp'` + `teamSize: 2`: the
two axes compose instead of forking.

### Combatant schema

`combatants` grows two nullable slots: `{ left, right, leftBack, rightBack }`.
- `left` / `right` keep meaning the **FRONT** wizards — all existing sim references stay
  semantically correct.
- `leftBack` / `rightBack` are `null` in singles and 2-player PvP.
- **Safety invariant:** when the back slots are null, the sim's math is byte-identical to
  today. The singles goldens must not move (see Verification).
- The existing combatant fields `position` (`'front'`/`'back'`) and `aiCurrentTarget`
  are used as originally intended.

### Court geometry

- BACK wizard stands on today's singles rail (same X as the current singles paddle —
  last line of defense).
- FRONT wizard gets a new advanced rail toward midfield (exact X offset chosen in
  implementation; must clear both block arcs without overlap).
- Each wizard carries their own block arc — same shared `BLOCK_ARC` params (reshape once,
  all four follow). A ball that beats the front arc continues to the back arc, then the gate.
- Arena Z extent × 4/3 in doubles (resize hook exists at the legacy `resizeArena` site,
  index.html ~8531). Ortho camera zooms out proportionally to frame the wider court.

### Shared team resources

- **Mana:** one pool per team, same size/regen as a singles wizard's. Any teammate's cast
  spends from it. Keeps per-side spell density identical to singles; coordination becomes
  a skill ("don't burn the counter-frostbolt mana").
- **Juice:** one team bar; both teammates' charge events feed it. Overdrive trigger:
  front wizard only (provisional, above). Overdrive itself is unchanged.
- Both live in sim state and enter the state hash.

## M1 — AI design (the mirror-lock defense)

Concern (Andrew): identical deterministic AIs could perfectly counter each other into
degenerate loops. Defense is structural asymmetry, never randomness:

- **Role profiles:** FRONT = interception, block pressure, offensive casting;
  BACK = gate coverage, counter-casting, holds shared mana longer before spending.
- **Per-slot reaction lags:** each AI slot decides on a differently-lagged view
  (mechanism already exists in the singles AI).
- **Coprime decision cadences:** slots re-evaluate on different frame intervals
  (e.g. 7 vs 11 vs 13 frames) so no two AIs ever sync decision phases.
- Difficulty setting applies to the opposing team; the human's AI teammate plays at a
  fixed competent level.
- If playtests still find stalemates: tune profile numbers. Data, not dice.

## M1 — Mode entry & HUD

- Start Battle mode-select gains a **Doubles** entry (existing DOM arcane-menu system).
- Human is **Blue Front** in M1 (provisional Overdrive seat).
- HUD stays singles-shaped: own cast bar/cooldowns as-is; mana bar shows the TEAM pool;
  Juice bar shows the TEAM bar; one new small teammate status chip (teammate cooldowns +
  frozen state).
- Four wizard models: blue front/back, red front/back; back wizards shade-shifted
  (respect the colorblind toggle for the red team). Each wizard has their own block arc
  visual and floor line.

## M1 — Out of scope

- Any netcode change (M2). Any lobby change (M3).
- Human position choice (front vs back) — M1 human is always Blue Front; picking comes
  with the M3 lobby.
- Final Overdrive-caster rule (provisional front-only ships; decision revisited on
  playtest feedback).
- Balance tuning beyond the structural decisions above (shared pools, singles-sized).
- Doubles-specific spells/talents.

## Verification contract ("wire it up safely")

1. **Singles/PvP goldens are inviolable.** `dbg.determinism(180, 12345) = 6c6801a3` and
   seed `99999 = 574d9f9c` (per the `js/sim.js` header pin — re-read the header at
   verification time, never trust docs) must be byte-identical after EVERY task that
   touches `js/sim.js`. Null back slots ⇒ identical math paths. Any drift = stop and
   investigate, never re-pin.
2. **New doubles goldens:** a doubles variant of the determinism oracle
   (`teamSize: 2`, fixed seeds, 180 frames) and a doubles AI oracle, each verified by
   two identical runs before pinning; recorded in the `js/sim.js` header.
3. **`?v=` cache bump** on `js/sim.js` on every sim edit (standing rule).
4. **No `Math.random`** in any new code, AI included (grep gate).
5. **2-player PvP untouched:** no edits to connection/input/rollback code in M1.
6. **Andrew playtests manually** — no automated browser driving. Each landed chunk ships
   with a short manual checklist (mode entry, rails, arcs, shared pools, AI behavior,
   goldens via `?dev` console).

## Open questions (deliberately deferred)

- Overdrive caster rule (front-only is provisional).
- Match structure for doubles (identical ships; revisit if playtests want faster party
  format).
- Shared mana pool size (singles-sized ships; 1.5× is the fallback if two wizards feel
  starved).
