# Multiplayer Rework Log

## 2026-01-?? (Session Notes)

### Intent
- Make multiplayer perspective consistent so host/guest see correct "your"/"enemy" sides, colors, damage, and UI behavior.
- Eliminate ownership bugs caused by world-side assumptions (left/right X position).

### Plan (High-Level)
1. Inventory multiplayer flows (host/guest state, camera flip, UI labels, damage, inputs, colors).
2. Define a single source of truth for perspective (local side/team) and map all systems to it.
3. Refactor ownership-sensitive logic to use ownership/team instead of world X.
4. Harden camera/UI transitions and reset paths.
5. Add diagnostics and a quick multiplayer test matrix.

### Initial Findings (Before Changes)
- Gate damage uses world X position (left/right) instead of projectile ownership; guest can damage the wrong tower.
- Parry resolution is gated by isHost, which can prevent one side from parrying in PvP simulation.
- Health bars and GUI labels still map to left/right world sides; guest perspective is only partially swapped.
- Upgrade selection is not synchronized; host/guest can diverge.
- Cancel mana reward uses hardcoded 'player'/'ai' owners (left/right), not local/remote.

### Changes
- Added local/remote helpers and PvP parry state tracking with deterministic timers.
- Mapped combatant UI elements to local/remote perspective in PvP (mana/cast/health).
- Synced health bar updates to local/remote towers in PvP.
- Ensured parry button in PvP feeds net input instead of single-player callback.
- Shared selected upgrade from host to guest on match start.
- Implemented PvP parry detection for both sides and synced local parry UI.
- Added PvP parry aiming for right-side player via input direction.
- Switched tower damage targeting to projectile ownership and update ownership on blocks/parries.
- Removed random fireball launch angle; aim now derives from movement input.
- Captured move accumulator and stage state in rollback snapshots.
- Restored projectile ownership during rollback sync.
- Updated score display and win/lose messaging to be local-perspective in PvP.
- Throttled PvP UI updates to reduce per-frame DOM churn.
- Mapped frozen text to local perspective in PvP.
