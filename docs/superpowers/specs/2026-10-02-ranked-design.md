# Ranked: MMR (Elo) + tiers + divisions — design

Owner request (2026-10-02): "a rank system: elo, MMR, bronze, silver, gold, platinum, diamond, master, maybe Roman numerals 1, 2, 3". Asked for draft + spec + plan + execution in one shot, so the decisions below were made without a review round; each is easy to retune (all numbers live in one `RANK` table).

## What the player sees
- **Rank** = tier + division: Bronze III → II → I, Silver III … Diamond I, then **Master** (no divisions; shows the MMR number instead). III is the bottom of a tier, I the top (LoL/Valorant convention).
- **MMR** (the Elo number) is shown alongside the rank, with a progress bar to the next division (each division = 100 MMR).
- **Placements**: the first 5 rated matches show "Unranked — Placement n/5"; the rank is revealed after the 5th.
- After every rated match the end screen shows a **rank card**: emblem, rank, "+18 MMR" / "−21 MMR", the bar filling or draining, and "Promoted!" / "Demoted" / "Placed: Gold II" when it changes.
- **Career → Ranked** tab (between Stats and Achievements): big emblem, rank, MMR + bar, ranked W–L and win rate, peak rank, the last 10 results, and the tier ladder with each tier's MMR floor.

## Rating model
- One hidden-precision number, `mmr`, start **1000** (Silver II). Plain Elo:
  `expected = 1 / (1 + 10^((opp − mmr) / 400))`, `delta = round(K · (score − expected))`, a win is always ≥ +1 and a loss ≤ −1; MMR never drops below 0.
- **K**: 64 during placements (fast sorting), 32 until 30 rated matches, then 24.
- **Bands**: division i (0..14) starts at `600 + 100·i`; Bronze III is everything below 700; **Master ≥ 2100**. Rank is a pure function of MMR (no hidden LP, no demotion shields — simple, honest, retunable).
- **Peak**: highest MMR reached after placements.

## What counts (rated)
- **Singles vs AI**: the AI is one fixed profile (symmetry principle: no stat crutches), so it is a fixed-rating opponent, **AI = 1200** (Gold III floor). Elo self-limits: a player who beats it 90% of the time settles around 1580 (Platinum III); Diamond and Master effectively need human opponents.
- **Online 1v1**: each peer sends `{ mmr, games }` with the existing match-start handshake (host: `START_MATCH.rank`; guest: its `LOADOUT.rank` reply). Each side updates its own rating locally from the result and the opponent's MMR. If the opponent's rating never arrived (older client), the match is unrated.
- **Not rated**: doubles (local or online), spectate, the headless match simulator, the dev debug-end.
- **Abandons**: quitting a rated match mid-way (pause → Quit/Leave), or closing the page during one, records a **loss** (a pending marker is saved at match start and settled on the next load). An online **disconnect** is not counted either way (P2P drops can't be told apart from rage-quits).

## Storage
`localStorage.volleybolt_rank = { v:1, mmr, games, wins, losses, peak, history:[…last 10], pending }` — local for now, the future account system replaces it (same as name + loadout). Nothing touches the sim, the state hash or rollback; rank fields ride on presentation messages only.

## Art
Pixel-first 16px emblems (tools/build_rank_icons.py → textures/rank/emblems.png): Unranked (grey shield, ?), Bronze, Silver, Gold (shield + star), Platinum (winged shield), Diamond (gem), Master (crowned gem). Division numerals are text.

## Out of scope (later)
Server-side matchmaking and anti-tamper (local storage is trivially editable), seasons/decay, doubles rating, showing ranks in the lobby before a match.
