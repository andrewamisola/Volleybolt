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
- **Singles vs AI — a matched bot** (revised 2026-10-02 with the owner): every match start (`resetGame` → `Rank.prepareMatchAI`) rates a bot at **your MMR ± up to 75** (seeded per match). Its **skill** (0..1) comes from that MMR through a **measured curve** (below), and slides every lever continuously between three anchors — Bronze (0), **Gold (0.5 = today's AI, exactly)**, Master (1):

  | lever | Bronze | Gold | Master |
  |---|---|---|---|
  | perfect-parry share | 25% | 50% | 92% |
  | early-whiff share (3 s lockout) | 35% | 25% | 3% |
  | reaction delay (frames) | 12 | 6 | 2 |
  | parry / dodge sight (frames) | 12 / 15 | 7 / 9 | 3 / 4 |
  | positioning deadzone | 0.85 | 0.65 | 0.45 |
  | open-lane sharpness | 0.3 | 0.7 | 1.0 |
  | cast cadence | 6 | 5 | 3 |
  | Chill Dill never-counter / decision time | 50% / x1.5 | 25% / x1 | 3% / x0.5 |
  | returns sent straight back (no aim) | 50% | 0% | 0% |
  | beam-clash mash (frames per press) | 15 | 9 | 5 |
  | smart Overdrive / counter-clash | from skill 0.25 / 0.35 | yes | yes |

  **Calibration** (`dbg.botCal`, headless bot vs the 0.5 bot, 60-120 matches per point, ~23 Elo side bias corrected): skill 0.1 → −686, 0.3 → −460, 0.5 → 0, 0.75 → +387, 1.0 → +460 Elo. Pinned at 0.5 = 1350 MMR, `RANK.SKILL_CURVE` = `[0,550] [0.1,664] [0.3,890] [0.5,1350] [0.75,1737] [1,1810]`: bots span **Bronze III → Diamond III**. **Honest cap**: a bot is never rated outside that span, so past ~1810 only real players move you (Elo self-limits against the best bot) — Diamond II+ and Master are earned against people. (The first Master anchors topped out at ~Platinum II; they were pushed harder to stretch the curve.)

  Its **style** is a hidden weighted pick (Balanced 40%, Aggressive / Defensive / Control 20% each) — what it spends on, never how well: *Aggressive* casts ~2x as often and keeps casting while a ball is still >0.9 s away, Fireball first, stacks balls even into a block, Thunderstorm only at 3+ incoming, Overdrive on any lane; *Defensive* is a counter-puncher: holds the centre while recharging, blocks/parries first, attacks only into an opening (you out of position or frozen), an empty court or with mana full, Overdrive only into a freeze or a clash. Tuned by sim at skill 1 (vs Balanced, both sides): the first 'turtle' (2-mana bank, zap every ball) stalled a mirror forever; a 1-mana reserve made it win 85-94%; no reserve = 45%, with Aggressive ~69% and Control ~64%; *Control* lines up on you, casts Chill Dill from wide angles (it homes), Fireball only into a freeze or while Chill Dill recharges. (Styles pushed further apart 2026-10-02 at the owner's request; STYLE_EDGE below was measured on the milder first version — re-run dbg.botCal.) Measured style edges vs Balanced at equal skill: Aggressive −47, Control −47, **Defensive +143** Elo (`RANK.STYLE_EDGE`); the matchmaker plays a style at the skill of (rating − edge), so a bot's real strength matches the rank it shows. Competence only, never stats (symmetry principle). Players see the bot's **rank** (under Red's tower bar in its tier colour, and "Red · Gold II" on the end screen), never its style. Doubles, spectate, online and every oracle keep `AI_PROFILE` (= skill 0.5 Balanced).
- **Online 1v1**: each peer sends `{ mmr, games }` with the existing match-start handshake (host: `START_MATCH.rank`; guest: its `LOADOUT.rank` reply). Each side updates its own rating locally from the result and the opponent's MMR. If the opponent's rating never arrived (older client), the match is unrated.
- **Spectate**: both sides are the strongest bot (skill 1) with a random hidden style each per match, never Defensive vs Defensive (owner: "make them Masters so it's fun to watch").
- **Not rated**: doubles (local or online), spectate, the headless match simulator, the dev debug-end.
- **Abandons**: quitting a rated match mid-way (pause → Quit/Leave), or closing the page during one, records a **loss** (a pending marker is saved at match start and settled on the next load). An online **disconnect** is not counted either way (P2P drops can't be told apart from rage-quits).

## The offense/defense triangle (rules, live 2026-10-02)
Owner: aggression had no payoff (every attack is a ball that can come back bigger; defensive tools are pure value; waiting was free), so styles were really "how passive". Three rule switches in `SIM_RULES` (set false/0 to restore the old rule):
- `engagedTrickle` — the passive Juice trickle only runs while you have an attack in flight or a cast in progress (waiting no longer charges your ultimate).
- `pressureJuice: 12` — the attacker earns Juice when the opponent has to block its ball (forcing a defense is progress).
- `blockNoTier` — a plain block no longer raises a ball's tier; only a parry (the skilled defense) escalates it (softer backfire).

AI styles are now about **risk tolerance**, not cast frequency: Aggressive commits to casts (`castBail -0.4`), sharp far-side returns, Overdrive with a ball still incoming; Defensive bails early (`castBail 0.6`), safe returns, counter-punches only into openings. Measured at skill 1, all pairings, both sides (16 per pairing): per-style win rate 38–60% → **45–60%** with the rules (Aggressive 38→46%), a real cycle (Defensive > Aggressive > Control > Balanced > Defensive), no stalls, match length unchanged (3.6 min). The skill curve moved too (skill gaps compound under pressure): re-measured as a chain of 0.1 steps, `SKILL_CURVE` = 0→40, 0.1→484, 0.2→664, 0.3→944, 0.4→1170, 0.5→1350, 0.6→1576, 0.75→1924, 1→2341 — bots now span Bronze III → **Master**, so the honest cap no longer reserves Diamond II+/Master for people. Style edges for ranked (vs Balanced, Elo, at skill 0.5 / 1): Aggressive −176 / −44, Defensive +241 / −255, Control +120 / +70 — strongly skill-dependent, so `RANK.STYLE_EDGE` is interpolated by the bot's skill. Determinism pins moved with the rules: `d12345 7131e022`, `d99999 34056572` (AI-only fold `ac10e83e` unchanged).

## Storage
`localStorage.volleybolt_rank = { v:1, mmr, games, wins, losses, peak, history:[…last 10], pending }` — local for now, the future account system replaces it (same as name + loadout). Nothing touches the sim, the state hash or rollback; rank fields ride on presentation messages only.

## Art
Pixel-first 16px emblems (tools/build_rank_icons.py → textures/rank/emblems.png): Unranked (grey shield, ?), Bronze, Silver, Gold (shield + star), Platinum (winged shield), Diamond (gem), Master (crowned gem). Division numerals are text.

## Out of scope (later)
Server-side matchmaking and anti-tamper (local storage is trivially editable), seasons/decay, doubles rating, showing ranks in the lobby before a match.
