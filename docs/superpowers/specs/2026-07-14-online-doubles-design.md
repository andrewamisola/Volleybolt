# Online Doubles (M2 netcode + M3 lobby) — Design

**Date:** 2026-07-14
**Status:** Approved (Andrew: "you play with your team, your friends, like a co-op. Let's do it.")
**Owner:** Andrew
**Parent:** docs/superpowers/specs/2026-07-12-doubles-mode-design.md (M1 shipped; its locked
decisions all apply)

## Goal

Four people (or fewer, with AI filling) join a pregame lobby, pick red/blue
fighting-game-style, ready up, and play 2v2 online — co-op with your friends on a team.
Ships as one push: M2 (4-player netcode) + M3 (lobby) together.

## Architecture decisions (approved)

| Decision | Value |
|---|---|
| Topology | **Host-relay star**: up to 3 guests connect to the host (room code, PeerJS); every client sends its inputs to the host; the host broadcasts the merged per-frame input set; all four clients run the identical deterministic sim with rollback |
| AI slots | **Virtual players, host-authoritative**: the HOST computes AI inputs (existing deterministic doubles AI) and relays them exactly like a remote player's inputs. No client-side AI recomputation online (keeps the AI's reaction-lag rings out of rollback snapshots — no new desync surface). Local doubles keeps today's local AI driver unchanged |
| INPUT_DELAY | ~4 frames in ONLINE DOUBLES ONLY (guest↔guest = two hops). 1v1 PvP keeps its current value. Exact number tuned during implementation; a named constant |
| Hash sync | Star-shaped: host broadcasts its frame hashes; each guest compares locally; sustained divergence (badStreak pattern from the 1v1 desync work) → host broadcasts DESYNC_ABORT → everyone exits via the standing "Match lost sync" overlay |
| Classic 1v1 | **Untouched.** Online Doubles is a separate flow ("Online Doubles" entry in the multiplayer menu); the shipped 1v1 lobby/netcode/pins are not edited except provably-additive plumbing |
| Slot numbering | Join order; host = P1. Each peer's Settings name replaces their own P# everywhere (tags, STATUS, combat log) — the M1 naming rule, fed over the wire at join |
| Host migration | None. Host disconnect mid-match = match over via the standing disconnect overlay for all. Guest disconnect mid-match = their slot's inputs become AI (host swaps the virtual-player driver in for that slot, announced in the combat log) — the co-op survives a friend dropping |
| Late join | No. Lobby only, pre-match |

## Lobby VISUAL redesign (Andrew, 2026-07-14 — replaces the slot-card grid; protocol unchanged)

Owner: "It should be a clear RED and BLUE side on the RIGHT and LEFT side of the screen.
Then the client player will press LEFT or RIGHT to go on either side, moving their [P1]."

- Full-screen split: BLUE zone = LEFT half, RED zone = RIGHT half (court orientation).
- Each player is a floating name tag ([P1]/custom name) that SLIDES to the side they pick.
- Controls: ←/→ (A/D, d-pad) = move to that side (front seat first, back if taken, full
  side ignored); ↑/↓ = swap front/back with your teammate; Enter = ready (✓ on the tag).
  Mouse buttons remain for all three.
- AI seats render as ghosted tags at 50% opacity (name-tag opacity language).
- Room code large top-center; host START bottom-center; leave button unobtrusive.

## The lobby (M3 — fighting-game style, decisions locked in M1 spec)

- Host creates a room → room code (existing PeerJS id flow) → up to 3 guests join.
- Four slot cards: **Blue Front / Blue Back / Red Front / Red Back**, showing player name
  (or "AI" for empty slots), team color, ready check.
- Picking a side fills its FRONT slot first, then BACK. **Swap** trades front/back with
  your teammate (request → host applies → broadcast). Both teammates can be humans —
  that's the co-op.
- **Ready** per human; host's **Start Match** gates on all humans ready.
- Host owns the lobby state machine (slots[4]: {peerId|'AI', name, ready}) and broadcasts
  LOBBY_STATE on every change; guests render from the broadcast (no guest-side authority).
- Lobby disconnect: slot frees, broadcast updates. In-lobby chat/emotes: out of scope.
- AI fill happens at Start: empty slots become host-driven virtual players.

## Netcode specifics (M2)

- **Connections:** host holds up to 3 DataConnections (unordered, GGPO-style redundancy —
  reuse the 1v1 transport patterns: INPUT_REDUNDANCY history piggyback, INPUT_ACK, PING/PONG
  per guest).
- **Input protocol:** guests send their own slot's input per frame (same
  {moveDir,parry,fireball,frostbolt,thunderstorm,juice} shape). Host merges four streams
  (its own + guests + virtual players) into a per-frame INPUT_SET broadcast: {frame,
  inputs: [p1..p4], history: [...]}. Guests feed the sim from INPUT_SETs; the host feeds
  it from its merge directly.
- **Sim mapping:** slots map to combatant keys (Blue Front=left, Blue Back=leftBack,
  Red Front=right, Red Back=rightBack). The sim consumes them exactly as local doubles
  does today (leftInput/rightInput + ctx.backInputs) — the sim itself is UNCHANGED.
- **Rollback:** existing snapshot/restore already covers back slots (M1 Task 8). Prediction:
  repeat-last-input per remote slot (including virtual players, which are "remote" to
  guests and locally-known to the host). Rollback window/stall logic follows the 1v1
  machinery, widened to 4 input histories.
- **Frame pacing:** the 1v1 frame-advantage/stall logic generalizes: a client stalls on the
  OLDEST confirmed frame across all streams it needs.
- **Determinism guardrails:** doubles goldens (47424ad5/6e043c14/0e029492) are the reference
  — a desync means netcode, not sim. AI virtual players run ONLY on the host (guests never
  execute decideAI online — enforced by driver structure, not a flag check).

## Out of scope

- Host migration, late join, spectators, lobby chat, matchmaking/discovery (room codes
  only), TURN relay (still the audit follow-up), mobile/touch.
- Any edit to classic 1v1 flows beyond provably-additive shared plumbing.
- Balance changes. Ragdoll/timber (parked).

## Verification contract

1. All six pinned goldens byte-identical after every task that touches shared code
   (singles a90063b5/5e5eca1b, AI e6fdfae9, doubles 47424ad5/6e043c14, aiDoubles 0e029492 —
   header is authoritative).
2. Local doubles + singles + classic 1v1 play identically (no new code on their paths, or
   additive-only with identity walks).
3. `?v=` bump on any js/sim.js edit (none expected — the sim is untouched by design).
4. No Math.random in any new code (virtual-player AI runs the existing seeded brain).
5. Owner-delegated in-browser verification allowed (standing authorization): multi-tab
   lobby/match smoke tests + hash-sync observation are in bounds; feel judgments are Andrew's.
6. Desync tooling: dbg.report() must include the 4-peer sync state (extend the sync block
   for the star topology).

## Milestones within the push

- **W1 — lobby skeleton:** room create/join for 4, slot state machine, side pick + swap +
  ready + start, AI fill, names over the wire. Match starts into LOCAL-style doubles for
  the host only (guests get a "match started" stub) — proves the lobby before netcode.
- **W2 — input mesh:** INPUT_SET protocol, 4-stream histories, host merge + relay, virtual
  players, guests run the sim. No rollback yet (lockstep with input delay) — proves
  determinism across 4 machines (hash compare from frame 0).
- **W3 — rollback + resilience:** prediction/rollback over 4 streams, frame pacing/stall,
  star hash-sync + desync abort, guest-drop→AI swap, host-drop→match over, dbg.report
  extension.
- **W4 — polish + ship:** lobby UX polish (colorblind, gamepad nav, prompts), end-to-end
  multi-tab verification, goldens re-verified, itch zip, push.
