# Game Lifecycle, Camera & Multiplayer — Design

**Date:** 2026-06-24
**Status:** Approved design (combined audit)
**Scope:** Rebuild the game's boot/menu/match/end lifecycle around one explicit state machine with a single authoritative match-build path; lock the camera to a fixed shared-world wide shot; make the menu a 2D backdrop with no 3D camera; provide a lean multiplayer host/join lobby; and clean up the dead `js/` module scaffolding. Single combined spec covering single-player and multiplayer.

## Problem

The game runs from an inline ~890KB monolith in `index.html`. Menu↔play↔end is an implicit state machine (`gameState` flags) with **scattered, piecemeal "soft" resets** (`resetGame`, `resetRound`, `showTalentScreen`, `returnToMenuTransition`, plus "belt-and-suspenders" visibility toggles). Consequences:

- **Off-angle menu camera** leaks between states — the menu camera pose persists/drifts.
- **Stale end-scene**: after victory/defeat, Continue returns to the menu but the 3D scene isn't rebuilt; starting a new match shows the stale end-state ("loads the end scene").
- A half-finished `js/` module extraction loads broken scripts: `js/main.js` (diagnostic-only) imports `updateGravityUI` which `ui-system.js` doesn't export → hard ES-module crash; `<script src="js/config/ability-registry.js">` 404s. The game runs entirely from inline code (proven: main.js crashes yet the game works), so these are dead scaffolding.

Goal: make the game **boot and transition like a real game** — clean loading → menu → match → end → menu — with no leaked state.

## Decisions (locked)

- **Camera:** one camera, one **fixed wide-shot pose**. No menu camera, no per-client mirroring, no follow.
- **World model:** shared/absolute (fighting-game / MOBA style, *not* mirrored). Players occupy fixed sides: **host = left, guest = right** (P1/P2 in single-player).
- **Menu:** pure **2D backdrop** (simple CSS title screen for now; art swappable later). The 3D engine is idle while in menu — **no 3D camera exists in menu**, which removes the off-angle-camera bug class at the root.
- **Lifecycle:** assets load **once** at boot; one authoritative `startMatch()` builds a fully fresh match; `endMatch()` returns to the 2D menu. Single-player starts at **midfield** (current stage 2).
- **Multiplayer:** lean — Host or Join (short code), then Start. Built on existing PeerJS P2P.

## State machine

One module owns `state` and all transitions. Nothing outside it mutates scene/camera/UI visibility.

```
BOOT → MENU → MATCH → GAMEOVER → MENU
                          ↘ (Continue) ↗
MENU → LOBBY → MATCH        (multiplayer)
LOBBY/MATCH → (disconnect/quit) → MENU
```

Each state has exactly one entry function:
- `enterBoot()` — load engine + all assets (pickle GLBs, textures, audio) with a progress bar → MENU.
- `enterMenu()` — show 2D title backdrop + `Start Battle` / `Multiplayer`; pause/idle the 3D engine; hide all gameplay UI and the 3D view.
- `startMatch(opts)` — see below.
- `enterGameOver(result)` — show victory/defeat overlay over the frozen match; Continue → `endMatch()`.
- `enterLobby()` — host/join UI.

## Match lifecycle (core)

**`startMatch(opts)`** — single fresh build used by BOTH single-player and multiplayer. `opts` = `{ mode: 'single'|'pvp', role?: 'host'|'guest', seed?, upgrade? }`. Builds, in order, from one source of truth:
1. Stage geometry positioned for the **starting stage** (midfield); gates → full health.
2. Combatants → start positions, idle animation, scores 0, cooldowns/mana cleared.
3. **Camera → the one fixed wide-shot pose** (set explicitly, every match).
4. Gameplay UI shown; 3D view revealed; 2D menu hidden.
5. `mode==='pvp'` seeds RNG from `seed` and wires the existing input-sync.

**`endMatch()`** — stop the match loop, hide gameplay UI + 3D view, return to `enterMenu()`. Called on Continue (after GAMEOVER), on quit, and on multiplayer disconnect. No partial state can survive because the next `startMatch()` rebuilds everything.

This single path **replaces** the tangle of `resetGame` / `resetRound` (match-state portions) / `showTalentScreen` / `returnToMenuTransition` / the duplicate win handlers. `resetRound` logic that is still needed *within* a match (between rounds/stages) stays, but match-entry no longer depends on it for a clean slate.

**Fixes:** off-angle camera (no menu camera + camera set fresh each match), stale end-scene, Continue-doesn't-reload.

## Camera

- A single camera; `startMatch()` sets its fixed wide-shot pose (full arena, both sides visible). No `MENU_CAMERA`, no `setOrthoForMenu` menu transition, no camera animation between menu and play.
- Shared world: host/P1 = left, guest/P2 = right. **Remove** the `applyClientPerspective(flip)` mirroring path entirely (simpler, desync-proof). Each client controls only its own paddle; no input flipping needed since the world is shared.

## Multiplayer (lean)

- `Multiplayer` → **Lobby**: **Host** generates a short join code; **Join** enters a code. On both-ready, host calls `startMatch({mode:'pvp', role, seed})` and signals the guest (existing `START_MATCH` message) to do the same with the shared seed.
- Reuse existing PeerJS connection, input sync, ping/heartbeat, and disconnect detection. Disconnect → `endMatch()` → MENU (replaces the current `handleDisconnect` ad-hoc reset).
- No room list, matchmaking, or spectators — host/join/start only.

## Cleanup folded in

- Remove the dead module `<script type="module">` tags (`js/config/ability-registry.js` [missing], `js/main.js` [diagnostic-only], and the other extraction modules if unused by the running game) → eliminates the ES-module crash + 404. Verify no remaining inline dependency before removing each.
- Retire the now-unused soft-reset helpers and `applyClientPerspective` mirroring once the state machine owns transitions.

## Out of scope (YAGNI)

- Extracting the monolith into modules (the broken extraction is removed, not completed).
- Dynamic/follow cameras, per-client mirrored views, spectator mode, matchmaking/room lists.
- Menu background art (placeholder CSS title screen now; art later).
- Pickle character/animation work (already landed; left untouched).

## Success criteria

- Boot shows one loading screen, then a 2D menu with **no 3D camera artifacts**.
- `Start Battle` → fresh single-player match at midfield, fixed wide camera, every time.
- Victory/Defeat → Continue → clean 2D menu → starting again gives a fresh match (no stale end-scene, no off-angle camera).
- `Multiplayer` → host/join by code → both land in the same shared-world match (host left, guest right); disconnect returns both cleanly to the menu.
- No ES-module crash or `ability-registry.js` 404 in the console.
