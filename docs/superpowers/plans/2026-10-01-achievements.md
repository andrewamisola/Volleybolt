# Achievements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 20 achievements to Dueling Pickles. They are earned in any match you play, judged when the match ends, shown in a new Achievements tab inside Career and on the end-of-match screen, and flagged by a red dot until you've seen them.

**Architecture:** One new `Achievements` module in `index.html`, right after `StatTracker`. It holds the rules list as data, the per-match flags, localStorage persistence and the "who is me" logic. Game code talks to it through a single one-line call, `Achievements.note(event, data)`, placed on the LIVE pass only (never while resimulating), plus `Achievements.evaluateMatchEnd(winnerSide)` where the match ends. Nothing in the module writes sim state. The one new projectile field (`castBy`) is bookkeeping: not hashed, but carried through rollback snapshots.

**Tech Stack:** Vanilla JS in a single `index.html` (~29k lines) plus the ES module `js/sim.js`, Babylon.js, DOM menus styled in `styles.css`. **No unit-test framework.** The test harness is (a) console snippets run in the game page, (b) the determinism oracles `dbg.determinism` / `dbg.aiDeterminism`, and (c) the headless match simulator `dbg.simMatch` / `dbg.simBatchAsync`. "Run the test" means: start the dev server with the browser-preview tool (`preview_start` with name `volleybolt`, serves `http://localhost:8000/index.html`), reload, then run the snippet through the preview's JavaScript tool (or paste it into the dev console). Top-level `let`s and functions of the main script (`isResimulating`, `gameState`, `combatants`, `endRound`, `dealDamageToTower`, `buildSimCtx`, ...) are reachable from there.

**Spec:** `docs/superpowers/specs/2026-10-01-achievements-design.md` (owner-approved 2026-10-01; Demolition resolved in §8).

## Global Constraints

- Work on branch `achievements` (cut from `castle-spells-lighting`). Owner merges when confirmed. Commit after every task. End each commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Determinism is law** (`docs/SHARED_CORE.md`): achievements never write sim state. Every `Achievements.note(...)` call and every new `StatTracker.increment(...)` sits behind `!isResimulating` / `!ctx.isResimulating` (or inside an existing block that already is). Do not reorder, add or remove any arithmetic on sim fields.
- **Oracle gate:** in Task 1 Step 1 you record the baseline folds. After every later task, `dbg.determinism(180, 12345).fold`, `dbg.determinism(180, 99999).fold` and `JSON.stringify(dbg.aiDeterminism(50, 42))` must equal that baseline exactly. Run them from a FRESH single-player match (reload → `startSinglesMatch()` → wait for `gameState === 'playing'`). If any value moves, STOP: something touched sim state.
- **"You" = the local side**: the `side` of whichever combatant has `isLocalPlayer === true`. Never key on `'left'` / `'player'` directly. That breaks for the online guest (plays Red) and for doubles seats.
- **Counts in:** vs AI, online 1v1, online doubles. **Never** in spectate, the headless simulator, or as an online-doubles spectator (no local combatant). Exception: when `dbg.achTest = true`, spectate/headless count for Blue (`'left'`), tallied into `Achievements.testCounts` and **never saved**.
- **Personal vs side events.** Casts (Pickle Monk, Pyromancer, Storm Chaser) belong to the wizard you control (`c.isLocalPlayer && c.side === localSide`). Everything else (parries, freezes, tiers, clashes, rounds) is per side. In doubles, a teammate's parry counts for your side.
- **Awarded at match end only.** A match you quit earns nothing (consistent with career stats). One deliberate exception: on page load, milestones whose career number is already past the target are unlocked silently (backfill), as unseen, so the dot shows. Otherwise a player with 50 wins would see "First Brine" locked at "50 / 1".
- `evaluateMatchEnd` takes `winnerSide` (`'left'|'right'`), not the spec's `localWon`. The module works out "local" itself, so every call site passes the same thing.
- Stable IDs (Steam later): `FIRST_BRINE SEASONED PICKLED FERMENTED WALL_OF_DILL PYROMANCER PICKLE_MONK CLEAN_SWEEP COMEBACK_KID SPEED_BRINE MARATHON UNTOUCHED RETURN_TO_SENDER COLD_WAR STORM_CHASER MAX_RALLY JUICE_CLASH_CHAMPION PICKLED_IN_ICE OVERTIME_HERO DEMOLITION`.
- Storage key `volleybolt_achievements`, shape `{ v: 1, unlocked: { ID: { at: <epoch ms> } }, seen: { ID: true } }`. Every read is wrapped in try/catch; corrupt or missing means "nothing unlocked".
- Match clock: `getMatchClockFrames()`, 3600 frames = 1 minute. Speed Brine `< 3:00`, Marathon `> 10:00`.
- Overtime round = `totalRoundsPlayed >= SIM_RULES.overtimeStart` (10) after `endRound`'s increment.
- Typography: menus use the existing career-card language (steel window, `#c9a8ff` titles, `#ffe39a` values). The end screen uses its existing Manrope 800 uppercase labels. No new fonts.
- When `js/sim.js` changes, bump its cache-buster in `index.html` (`js/sim.js?v=51-chill-clash-fx` → `js/sim.js?v=52-achievements`).
- Line numbers below are "currently ~N" and drift as edits land. Always anchor on the quoted code.
- Per project memory: do **not** drive real gameplay through browser automation (token waste). Console snippets and the headless simulator are fine. For the final look, ask the owner for screenshots.

## Review Focus

1. **Online guest / doubles seat.** A guest (Red) or a Blue-Back doubles player wins: their wins, parries, damage and achievements credit *their* side, never Blue's. Pinned by Task 1 test 1c (local side follows `isLocalPlayer`) and Task 2 tests 2b/2c/2d (flip the local flag to Red, then check every career stat credits Red).
2. **Rollback resimulation.** A replayed frame (parry, freeze, tier raise, damage) must not double-count. Pinned by Task 2 test 2b (damage with `isResimulating = true` doesn't count) and Task 4 test 4b (frostbolt freeze and fireball tier raise with `ctx.isResimulating = true` leave the flags untouched).
3. **Existing careers.** Someone already past a milestone threshold sees it unlocked (and dotted) on first load, not locked with an over-full bar. Pinned by Task 1 test 1e (`backfill`).
4. **Viewers earn nothing.** Spectate, the headless simulator, and an online-doubles spectator (no local combatant) never unlock or save anything unless `dbg.achTest` is on. Pinned by Task 1 test 1c/1f and Task 3 test 3a (headless run without `achTest` leaves storage untouched).
5. **Quit or stale end screen.** Quitting mid-match earns nothing, and the "Achievement unlocked" strip never carries over from a previous match. Pinned by Task 3 test 3c (`resetGame()` clears flags and `lastUnlocked`) and Task 6 test 6a (empty `lastUnlocked` hides the strip).

---

### Task 1: Achievements core module

The rules list, the per-match flags, `note()`, `judge()`, `evaluateMatchEnd()`, storage, seen-state, milestone backfill, and the `dbg.achievements` console helpers. Purely additive: nothing calls it yet, so the game plays exactly as before.

**Files:**
- Modify: `index.html`. Insert the module right after `window.StatTracker = StatTracker;` (currently ~1714), before the `// SPELL REGISTRY` banner.
- Modify: `index.html`. Insert `dbg.achievements` right before the `// ---- Headless MATCH SIMULATOR` comment (currently ~24034).

**Interfaces:**
- Consumes (existing globals): `StatTracker.get(key, 'career')`, `getAllCombatants()`, `isOwnCore(side, stage)`, `spectating` (top-level `let`), `window._simHeadless`, `SIM_RULES.overtimeStart`, `window.getMatchClockFrames()`.
- Produces `window.Achievements`:
  - `LIST`: `Array<{ id, name, desc, group: 'milestones'|'feats'|'mastery'|'pressure', stat?, target?, check?(flags, won) }>` (20 entries, spec order).
  - `note(event: string, data: object): void`. Events and payloads:
    - `'roundStart'` `{ stage: 0..4, hp: { left: number, right: number } }`
    - `'roundEnd'` `{ winnerSide: 'left'|'right', territoryFalls: boolean, roundNo: number, hp: { left, right } }`
    - `'cast'` `{ c: combatant }`
    - `'zap'` `{ c: combatant, count: number }`
    - `'freeze'` `{ frozenSide: 'left'|'right', proj }` (proj carries `isParried`, `parriedBy`, `castBy`)
    - `'chillClash'` `{ a: proj, b: proj }`
    - `'tier'` `{ side: 'left'|'right', from: number, to: number }`
    - `'beamClash'` `{ winnerSide: 'left'|'right' }`
  - `evaluateMatchEnd(winnerSide): string[]` returns the newly unlocked IDs (`[]` in test mode).
  - `judge(flags, won: boolean, careerGet: (key) => number): string[]` (pure).
  - `resetMatch(): void`, `flags(): object` (a copy), `localSide(): 'left'|'right'|null`, `isMe(c): boolean`.
  - `lastUnlocked(): string[]`, `unlockedAt(id): number|null`, `progress(id): [current, target]|null`, `unseenIds(): string[]`, `markAllSeen(): void`, `unlock(ids): string[]`, `backfill(careerGet): string[]`, `onUnlock(cb): void`, `load(): void`, `_wipe(): void`, `testCounts: object`.
- Produces `window.dbg.achievements`: `list()`, `reset()`, `unlock(id)`, `counts()`.

- [ ] **Step 1: Record the determinism baseline**

Reload the page. In the console:

```js
(async () => {
  startSinglesMatch();
  while (gameState !== 'playing') await new Promise(r => setTimeout(r, 250));
  const base = {
    d12345: dbg.determinism(180, 12345).fold,
    d99999: dbg.determinism(180, 99999).fold,
    ai: JSON.stringify(dbg.aiDeterminism(50, 42)),
  };
  console.log('BASELINE', JSON.stringify(base));
  window.__achBaseline = base;
})();
```

Write the printed `BASELINE` line into your task notes. Every later "oracle check" step compares against it.

- [ ] **Step 2: Write the failing test**

Reload the page and stay on the main menu (no match). Run:

```js
// TEST 1: Achievements core. Main menu, fresh reload.
(() => {
  const A = window.Achievements;
  const KEY = 'volleybolt_achievements';
  const backup = localStorage.getItem(KEY);
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  try {
    // 1a: the list
    console.assert(A && A.LIST.length === 20, '1a: 20 achievements', A && A.LIST.length);
    console.assert(new Set(A.LIST.map(a => a.id)).size === 20, '1a: ids unique');
    console.assert(A.LIST.every(a => ['milestones','feats','mastery','pressure'].includes(a.group)), '1a: groups');

    // 1b: judge (pure)
    A.resetMatch();
    const base = A.flags();
    const car = (k) => ({ matches_won: 12, parries_successful: 499, fireball_casts: 1000 }[k] || 0);
    console.assert(eq(A.judge(base, false, car), ['FIRST_BRINE','SEASONED','PYROMANCER']), '1b: milestones only on a loss', A.judge(base, false, car));
    const quick = { ...base, castsByMe: 0, roundsLost: 0, clockFrames: 2 * 3600 };
    const qh = A.judge(quick, true, () => 0);
    console.assert(['PICKLE_MONK','CLEAN_SWEEP','SPEED_BRINE'].every(id => qh.includes(id)), '1b: quick clean win', qh);
    console.assert(!qh.includes('MARATHON') && !qh.includes('COMEBACK_KID') && !qh.includes('DEMOLITION'), '1b: no false feats', qh);
    console.assert(A.judge({ ...base, castsByMe: 1, clockFrames: 11 * 3600 }, true, () => 0).includes('MARATHON'), '1b: marathon');
    console.assert(!A.judge({ ...base, castsByMe: 1 }, true, () => 0).includes('PICKLE_MONK'), '1b: a cast breaks Pickle Monk');
    console.assert(A.judge({ ...base, territoryBrokeRound: 4, lastRoundNo: 5 }, true, () => 0).includes('DEMOLITION'), '1b: demolition back-to-back');
    console.assert(!A.judge({ ...base, territoryBrokeRound: 4, lastRoundNo: 6 }, true, () => 0).includes('DEMOLITION'), '1b: demolition gap');
    console.assert(!A.judge({ ...base, territoryBrokeRound: 4, lastRoundNo: 5 }, false, () => 0).includes('DEMOLITION'), '1b: demolition needs the win');
    console.assert(!A.judge({ ...base, freezesInflicted: 4 }, false, () => 0).includes('PICKLED_IN_ICE'), '1b: 4 freezes');
    console.assert(A.judge({ ...base, freezesInflicted: 5 }, false, () => 0).includes('PICKLED_IN_ICE'), '1b: 5 freezes');

    // 1c: who is "me"
    console.assert(A.localSide() === 'left', '1c: SP local side is left', A.localSide());
    combatants.left.isLocalPlayer = false; combatants.right.isLocalPlayer = true;
    console.assert(A.localSide() === 'right', '1c: guest is right');
    console.assert(A.isMe(combatants.right) && !A.isMe(combatants.left), '1c: isMe follows the flag');
    combatants.right.isLocalPlayer = false;
    console.assert(A.localSide() === null, '1c: no local combatant (doubles spectator) = nobody');
    combatants.left.isLocalPlayer = true;
    window._simHeadless = true;
    console.assert(A.localSide() === null, '1c: headless earns nothing');
    window.dbg.achTest = true;
    console.assert(A.localSide() === 'left', '1c: achTest counts Blue');
    window.dbg.achTest = false; window._simHeadless = false;

    // 1d: note() flow
    A.resetMatch();
    A.note('roundStart', { stage: 0, hp: { left: 20, right: 20 } });
    console.assert(A.flags().wasOnOwnCore === true, '1d: own core seen');
    A.note('roundEnd', { winnerSide: 'left', territoryFalls: false, roundNo: 10, hp: { left: 20, right: 0 } });
    let f = A.flags();
    console.assert(f.untouchedRound && f.overtimeRoundWon && f.lastRoundNo === 10, '1d: untouched + overtime', f);
    A.note('roundStart', { stage: 3, hp: { left: 20, right: 20 } });
    A.note('roundEnd', { winnerSide: 'left', territoryFalls: true, roundNo: 11, hp: { left: 14, right: 0 } });
    A.note('roundStart', { stage: 4, hp: { left: 20, right: 20 } });
    A.note('roundEnd', { winnerSide: 'right', territoryFalls: false, roundNo: 12, hp: { left: 0, right: 3 } });
    f = A.flags();
    console.assert(f.territoryBrokeRound === 11 && f.roundsLost === 1, '1d: territory + loss', f);
    A.note('cast', { c: combatants.left }); A.note('cast', { c: combatants.right });
    console.assert(A.flags().castsByMe === 1, '1d: only my casts');
    A.note('freeze', { frozenSide: 'right', proj: { isParried: true, parriedBy: 'player', castBy: 'ai' } });
    A.note('freeze', { frozenSide: 'left', proj: { isParried: false, parriedBy: null, castBy: 'ai' } });
    f = A.flags();
    console.assert(f.freezesInflicted === 1 && f.returnToSender, '1d: freeze + return to sender', f);
    A.note('chillClash', { a: { castBy: 'player' }, b: { castBy: 'ai' } });
    A.note('tier', { side: 'left', from: 3, to: 4 });
    A.note('beamClash', { winnerSide: 'left' });
    A.note('zap', { c: combatants.left, count: 3 });
    f = A.flags();
    console.assert(f.coldWar && f.maxRally && f.beamClashWon && f.stormChaser, '1d: mastery flags', f);
    A.resetMatch();
    A.note('freeze', { frozenSide: 'right', proj: { isParried: true, parriedBy: 'player', castBy: 'player' } });
    A.note('chillClash', { a: { castBy: 'player' }, b: { castBy: 'player' } });
    A.note('tier', { side: 'left', from: 4, to: 4 });
    A.note('tier', { side: 'right', from: 3, to: 4 });
    A.note('zap', { c: combatants.left, count: 2 });
    A.note('beamClash', { winnerSide: 'right' });
    f = A.flags();
    console.assert(!f.returnToSender && !f.coldWar && !f.maxRally && !f.stormChaser && !f.beamClashWon, '1d: near-misses stay false', f);

    // 1e: storage, seen, backfill, corruption
    A._wipe();
    console.assert(eq(A.unlock(['COLD_WAR']), ['COLD_WAR']) && eq(A.unlock(['COLD_WAR']), []), '1e: unlock once');
    console.assert(A.unlockedAt('COLD_WAR') > 0 && A.unseenIds().includes('COLD_WAR'), '1e: unlocked + unseen');
    A.markAllSeen();
    console.assert(A.unseenIds().length === 0, '1e: seen');
    A.load();
    console.assert(A.unlockedAt('COLD_WAR') > 0 && A.unseenIds().length === 0, '1e: persisted');
    A._wipe();
    console.assert(eq(A.backfill(k => k === 'matches_won' ? 12 : 0), ['FIRST_BRINE','SEASONED']), '1e: backfill');
    const pr = A.progress('PICKLED');
    console.assert(pr.length === 2 && pr[1] === 50 && pr[0] <= 50 && A.progress('COLD_WAR') === null, '1e: progress shape', pr);
    localStorage.setItem(KEY, '{nope');
    A.load();
    console.assert(A.unlockedAt('COLD_WAR') === null && A.unseenIds().length === 0, '1e: corrupt = nothing');

    // 1f: test mode tallies, never saves
    A._wipe();
    window._simHeadless = true; window.dbg.achTest = true;
    A.resetMatch();
    A.note('tier', { side: 'left', from: 3, to: 4 });
    const before = A.testCounts.MAX_RALLY || 0;
    console.assert(eq(A.evaluateMatchEnd('right'), []), '1f: test mode returns nothing');
    console.assert((A.testCounts.MAX_RALLY || 0) === before + 1, '1f: tallied');
    console.assert(localStorage.getItem(KEY) === null, '1f: nothing saved');
    window._simHeadless = false; window.dbg.achTest = false;
    window._simHeadless = true;
    A.resetMatch();
    console.assert(eq(A.evaluateMatchEnd('left'), []) && localStorage.getItem(KEY) === null, '1f: headless without achTest = nothing');
    window._simHeadless = false;
    console.log('TEST 1 done (check for assertion errors above)');
  } finally {
    window._simHeadless = false; if (window.dbg) window.dbg.achTest = false;
    combatants.left.isLocalPlayer = true; combatants.right.isLocalPlayer = false;
    if (backup === null) localStorage.removeItem(KEY); else localStorage.setItem(KEY, backup);
    if (window.Achievements) Achievements.load();
  }
})();
```

- [ ] **Step 3: Run test to verify it fails**

Expected: `TypeError: Cannot read properties of undefined (reading 'LIST')` (`window.Achievements` doesn't exist yet). The `finally` still restores state.

- [ ] **Step 4: Write the module**

Insert right after `window.StatTracker = StatTracker;`:

```js
        // ============================================================
        // ACHIEVEMENTS (spec: docs/superpowers/specs/2026-10-01-achievements-design.md)
        // ============================================================
        // One rules list. Game code calls Achievements.note(event, data) on the LIVE pass only
        // (never while resimulating) and evaluateMatchEnd(winnerSide) where a match ends; nothing
        // here writes sim state, so determinism is untouched. "You" = the side of the combatant
        // flagged isLocalPlayer (an online guest is Red). Spectate, the headless simulator and an
        // online-doubles spectator earn nothing, unless dbg.achTest is on: then Blue counts, tallied
        // into testCounts and never saved. Steam later: subscribe with onUnlock(cb).
        const Achievements = (() => {
            const STORAGE_KEY = 'volleybolt_achievements';
            const FRAMES_PER_MIN = 3600;
            const LIST = [
                // Milestones (lifetime) read the career StatTracker
                { id: 'FIRST_BRINE', name: 'First Brine', desc: 'Win your first match', group: 'milestones', stat: 'matches_won', target: 1 },
                { id: 'SEASONED', name: 'Seasoned', desc: 'Win 10 matches', group: 'milestones', stat: 'matches_won', target: 10 },
                { id: 'PICKLED', name: 'Pickled', desc: 'Win 50 matches', group: 'milestones', stat: 'matches_won', target: 50 },
                { id: 'FERMENTED', name: 'Fermented', desc: 'Win 100 matches', group: 'milestones', stat: 'matches_won', target: 100 },
                { id: 'WALL_OF_DILL', name: 'Wall of Dill', desc: '500 successful parries', group: 'milestones', stat: 'parries_successful', target: 500 },
                { id: 'PYROMANCER', name: 'Pyromancer', desc: 'Cast 1,000 Fireballs', group: 'milestones', stat: 'fireball_casts', target: 1000 },
                // Feats (one match)
                { id: 'PICKLE_MONK', name: 'Pickle Monk', desc: 'Win without casting anything: paddle and parry only', group: 'feats', check: (m, won) => won && m.castsByMe === 0 },
                { id: 'CLEAN_SWEEP', name: 'Clean Sweep', desc: 'Win without losing a round', group: 'feats', check: (m, won) => won && m.roundsLost === 0 },
                { id: 'COMEBACK_KID', name: 'Comeback Kid', desc: 'Win after being pushed back to your own core', group: 'feats', check: (m, won) => won && m.wasOnOwnCore },
                { id: 'SPEED_BRINE', name: 'Speed Brine', desc: 'Win with the match clock under 3:00', group: 'feats', check: (m, won) => won && m.clockFrames < 3 * FRAMES_PER_MIN },
                { id: 'MARATHON', name: 'Marathon', desc: 'Win with the match clock past 10:00', group: 'feats', check: (m, won) => won && m.clockFrames > 10 * FRAMES_PER_MIN },
                { id: 'UNTOUCHED', name: 'Untouched', desc: 'Win a round without your structure taking a hit', group: 'feats', check: (m) => m.untouchedRound },
                // Spell mastery
                { id: 'RETURN_TO_SENDER', name: 'Return to Sender', desc: 'Parry an enemy Chill Dill and freeze its caster with it', group: 'mastery', check: (m) => m.returnToSender },
                { id: 'COLD_WAR', name: 'Cold War', desc: 'Cancel an enemy Chill Dill with your own', group: 'mastery', check: (m) => m.coldWar },
                { id: 'STORM_CHASER', name: 'Storm Chaser', desc: 'Zap 3 projectiles with one Thunderstorm', group: 'mastery', check: (m) => m.stormChaser },
                { id: 'MAX_RALLY', name: 'Max Rally', desc: 'Send a Fireball up to top tier yourself', group: 'mastery', check: (m) => m.maxRally },
                { id: 'JUICE_CLASH_CHAMPION', name: 'Juice Clash Champion', desc: 'Win a beam clash', group: 'mastery', check: (m) => m.beamClashWon },
                { id: 'PICKLED_IN_ICE', name: 'Pickled in Ice', desc: 'Freeze opponents 5 times in one match', group: 'mastery', check: (m) => m.freezesInflicted >= 5 },
                // Pressure
                { id: 'OVERTIME_HERO', name: 'Overtime Hero', desc: 'Win a round in overtime (round 10+)', group: 'pressure', check: (m) => m.overtimeRoundWon },
                { id: 'DEMOLITION', name: 'Demolition', desc: 'Break the enemy territory, then win at their core the very next round', group: 'pressure',
                  check: (m, won) => won && m.territoryBrokeRound > 0 && m.territoryBrokeRound === m.lastRoundNo - 1 },
            ];
            const byId = {};
            for (const a of LIST) byId[a.id] = a;

            const freshFlags = () => ({
                castsByMe: 0, roundsLost: 0, wasOnOwnCore: false, roundStartHp: null, untouchedRound: false,
                overtimeRoundWon: false, territoryBrokeRound: 0, lastRoundNo: 0, returnToSender: false,
                coldWar: false, stormChaser: false, maxRally: false, beamClashWon: false, freezesInflicted: 0,
                clockFrames: 0,
            });
            let m = freshFlags();
            let state = { v: 1, unlocked: {}, seen: {} };
            let last = [];
            const testCounts = {};
            const unlockListeners = [];

            function load() {
                state = { v: 1, unlocked: {}, seen: {} };
                try {
                    const raw = localStorage.getItem(STORAGE_KEY);
                    const s = raw ? JSON.parse(raw) : null;
                    if (s && s.v === 1 && s.unlocked && typeof s.unlocked === 'object') {
                        state.unlocked = s.unlocked;
                        state.seen = (s.seen && typeof s.seen === 'object') ? s.seen : {};
                    }
                } catch (e) { console.warn('Achievements: could not load', e); }
            }
            function save() {
                try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
                catch (e) { console.warn('Achievements: could not save', e); }
            }

            const testMode = () => !!(window.dbg && window.dbg.achTest) && (spectating || !!window._simHeadless);
            function localSide() {
                if (spectating || window._simHeadless) return testMode() ? 'left' : null;
                for (const c of getAllCombatants()) if (c && c.isLocalPlayer) return c.side;
                return null;   // online-doubles spectator: no seat, nothing to earn
            }
            const ownerOf = (side) => side === 'left' ? 'player' : 'ai';
            function isMe(c) { const L = localSide(); return !!(c && L && c.isLocalPlayer && c.side === L); }

            function note(event, d) {
                const L = localSide();
                if (!L || !d) return;
                switch (event) {
                    case 'roundStart':
                        if (isOwnCore(L, d.stage)) m.wasOnOwnCore = true;
                        m.roundStartHp = d.hp[L];
                        break;
                    case 'roundEnd':
                        m.lastRoundNo = d.roundNo;
                        if (d.winnerSide === L) {
                            if (m.roundStartHp !== null && d.hp[L] === m.roundStartHp) m.untouchedRound = true;
                            if (d.roundNo >= SIM_RULES.overtimeStart) m.overtimeRoundWon = true;
                            if (d.territoryFalls) m.territoryBrokeRound = d.roundNo;
                        } else {
                            m.roundsLost++;
                        }
                        break;
                    case 'cast': if (isMe(d.c)) m.castsByMe++; break;
                    case 'zap': if (isMe(d.c) && d.count >= 3) m.stormChaser = true; break;
                    case 'freeze': {
                        if (d.frozenSide === L) break;
                        m.freezesInflicted++;
                        const p = d.proj;
                        if (p && p.isParried && p.parriedBy === ownerOf(L) && p.castBy === ownerOf(d.frozenSide)) m.returnToSender = true;
                        break;
                    }
                    case 'chillClash': {
                        const mine = ownerOf(L);
                        if (d.a && d.b && ((d.a.castBy === mine) !== (d.b.castBy === mine))) m.coldWar = true;
                        break;
                    }
                    case 'tier': if (d.side === L && d.from < 4 && d.to >= 4) m.maxRally = true; break;
                    case 'beamClash': if (d.winnerSide === L) m.beamClashWon = true; break;
                }
            }

            // Pure: which achievement ids does this match satisfy? Exported for console tests.
            function judge(flags, won, careerGet) {
                const ids = [];
                for (const a of LIST) {
                    const hit = a.stat ? careerGet(a.stat) >= a.target : !!a.check(flags, won);
                    if (hit) ids.push(a.id);
                }
                return ids;
            }
            function unlock(ids) {
                const fresh = ids.filter(id => byId[id] && !state.unlocked[id]);
                if (!fresh.length) return [];
                const at = Date.now();
                for (const id of fresh) { state.unlocked[id] = { at }; delete state.seen[id]; }
                save();
                for (const id of fresh) for (const cb of unlockListeners) {
                    try { cb(id); } catch (e) { console.error('Achievements onUnlock listener error:', e); }
                }
                return fresh;
            }
            function evaluateMatchEnd(winnerSide) {
                last = [];
                const L = localSide();
                if (!L) return [];
                m.clockFrames = window.getMatchClockFrames ? window.getMatchClockFrames() : 0;
                const hits = judge(m, winnerSide === L, (k) => StatTracker.get(k, 'career'));
                if (testMode()) {
                    testCounts._matches = (testCounts._matches || 0) + 1;
                    for (const id of hits) if (!byId[id].stat) testCounts[id] = (testCounts[id] || 0) + 1;
                    return [];
                }
                last = unlock(hits);
                return last.slice();
            }
            // Milestones already earned by an existing career unlock on load (unseen, so the dot shows).
            function backfill(careerGet) {
                return unlock(LIST.filter(a => a.stat && careerGet(a.stat) >= a.target).map(a => a.id));
            }

            load();
            backfill((k) => StatTracker.get(k, 'career'));

            return {
                LIST, note, judge, evaluateMatchEnd, unlock, backfill, load, localSide, isMe, testCounts,
                resetMatch() { m = freshFlags(); last = []; },
                flags: () => ({ ...m }),
                lastUnlocked: () => last.slice(),
                unlockedAt: (id) => (state.unlocked[id] ? state.unlocked[id].at : null),
                progress(id) {
                    const a = byId[id];
                    if (!a || !a.stat) return null;
                    return [Math.min(StatTracker.get(a.stat, 'career'), a.target), a.target];
                },
                unseenIds: () => Object.keys(state.unlocked).filter(id => byId[id] && !state.seen[id]),
                markAllSeen() {
                    let changed = false;
                    for (const id of Object.keys(state.unlocked)) if (!state.seen[id]) { state.seen[id] = true; changed = true; }
                    if (changed) save();
                },
                onUnlock(cb) { unlockListeners.push(cb); },
                _wipe() { try { localStorage.removeItem(STORAGE_KEY); } catch (e) {} load(); },
            };
        })();
        window.Achievements = Achievements;
```

Then, right before `// ---- Headless MATCH SIMULATOR — dbg.simMatch ...`, add:

```js
        // Achievements console helpers. dbg.achTest = true makes spectate/headless matches count for
        // Blue into Achievements.testCounts (never saved), e.g. before dbg.simBatchAsync.
        window.dbg.achievements = {
            list() {
                console.table(Achievements.LIST.map(a => ({ id: a.id, group: a.group, unlocked: Achievements.unlockedAt(a.id) ? new Date(Achievements.unlockedAt(a.id)).toLocaleString() : '', seen: !Achievements.unseenIds().includes(a.id) })));
            },
            reset() { Achievements._wipe(); if (window.refreshAchievementDots) refreshAchievementDots(); return 'achievements wiped'; },
            unlock(id) { const r = Achievements.unlock([id]); if (window.refreshAchievementDots) refreshAchievementDots(); return r; },
            counts() { return { ...Achievements.testCounts }; },
        };
```

(`refreshAchievementDots` arrives in Task 5. The `window.` guard keeps this safe until then.)

- [ ] **Step 5: Run test to verify it passes**

Reload, stay on the main menu, run the Step 2 snippet.
Expected: `TEST 1 done`, **no** assertion errors. Then run `dbg.achievements.list()`: a 20-row table.

- [ ] **Step 6: Oracle check**

Run the Step 1 snippet again. All three values must equal the recorded baseline.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Achievements: core module (rules list, flags, storage, backfill, dbg helpers)"
```

---

### Task 2: Local-side career bookkeeping (spec §5)

Fixes the five career-stat bugs that would make milestones wrong, using `Achievements.localSide()` / `isMe()` from Task 1.

**Files:**
- Modify: `index.html`, at `startSinglesMatch` (~21665), `startDoublesMatch` (~21764), the `thunderstormZap` dep (~26020), `executeThunderstorm` (~27605), `endRound` (~28983–29058), `parryProjectile` (~15240), `dealDamageToTower` (~28838), the fireball `onPaddleHit` (~2528) and the frostbolt `onPaddleHit` (~2618).

**Interfaces:**
- Consumes: `Achievements.localSide()`, `Achievements.isMe(c)` (Task 1).
- Produces: career stats that credit the local side. `endRound` gains a local `const meSide`, which Task 3 does **not** rely on.

- [ ] **Step 1: Write the failing test**

Reload. Run (it starts a single-player match and pauses it; reload afterwards, since none of this is saved until a match is committed):

```js
// TEST 2: local-side career stats. Starts and pauses an SP match.
(async () => {
  combatants.left.isLocalPlayer = false; combatants.right.isLocalPlayer = true;   // stale guest flags
  startSinglesMatch();
  while (gameState !== 'playing') await new Promise(r => setTimeout(r, 250));
  dbg.pause(true);
  const S = StatTracker, g = (k) => S.get(k, 'career');
  // 2a: single player always resets to Blue = me
  console.assert(combatants.left.isLocalPlayer === true && combatants.right.isLocalPlayer === false, '2a: SP resets local flags');

  // 2b: damage: rollback-gated, local-side keyed
  let dd = g('damage_dealt'), dt = g('damage_taken');
  isResimulating = true; dealDamageToTower(false, 3, 0); isResimulating = false;
  console.assert(g('damage_dealt') === dd, '2b: resim damage not counted');
  dealDamageToTower(false, 3, 0);
  console.assert(g('damage_dealt') === dd + 3, '2b: dealt counted');
  dealDamageToTower(true, 2, 0);
  console.assert(g('damage_taken') === dt + 2, '2b: taken counted');
  combatants.left.isLocalPlayer = false; combatants.right.isLocalPlayer = true;   // play as the guest (Red)
  dd = g('damage_dealt'); dealDamageToTower(true, 1, 0);
  console.assert(g('damage_dealt') === dd + 1, '2b: guest hitting Blue = dealt');

  // 2c: parries: the local side's only
  const fake = (owner, velX) => ({ type: 'frostbolt', owner, velX, velZ: 0, velY: 0, x: velX < 0 ? -8 : 8, y: 0.7, z: 0, volleyCount: 0, speed: 20, isParried: false, parriedBy: null, mesh: { position: { y: 0.7 } } });
  let pp = g('parries_successful');
  window.parryProjectile(fake('player', 20), 'ai', 0);
  console.assert(g('parries_successful') === pp + 1, '2c: guest parry counts');
  window.parryProjectile(fake('ai', -20), 'player', 0);
  console.assert(g('parries_successful') === pp + 1, '2c: Blue parry does not count for the guest');
  combatants.left.isLocalPlayer = true; combatants.right.isLocalPlayer = false;
  pp = g('parries_successful');
  window.parryProjectile(fake('ai', -20), 'player', 0);
  console.assert(g('parries_successful') === pp + 1, '2c: SP parry counts');

  // 2d: rounds: local-side keyed (guest wins as Red)
  combatants.left.isLocalPlayer = false; combatants.right.isLocalPlayer = true;
  const rw = g('rounds_won'), rl = g('rounds_lost');
  roundActive = true; endRound('right');
  console.assert(g('rounds_won') === rw + 1 && g('rounds_lost') === rl, '2d: guest round win', g('rounds_won'), g('rounds_lost'));
  roundActive = true; endRound('left');
  console.assert(g('rounds_lost') === rl + 1, '2d: guest round loss');
  combatants.left.isLocalPlayer = true; combatants.right.isLocalPlayer = false;

  // 2e: freeze time inflicted (frostbolt hits the enemy shield)
  const fz = g('freeze_time_inflicted');
  const ctx = buildSimCtx();
  ABILITY_REGISTRY.frostbolt.behavior.onPaddleHit({ type: 'frostbolt', owner: 'player', x: 8, z: 0, isParried: false }, 'right', ctx, 'right');
  console.assert(Math.abs(g('freeze_time_inflicted') - (fz + 1)) < 1e-9, '2e: freeze time +1s', g('freeze_time_inflicted'));
  combatants.right.freezeTime = 0;
  console.log('TEST 2 done (check for assertion errors above). Reload the page now.');
})();
```

- [ ] **Step 2: Run test to verify it fails**

Expected assertion failures: `2a`, `2b: resim damage not counted`, `2b: guest hitting Blue = dealt`, `2c: guest parry counts`, `2d: guest round win`, `2e`.

- [ ] **Step 3: Implement the fixes**

**3a, stale `isLocalPlayer`.** In `startSinglesMatch`, right after `exitDoublesState();`:

```js
            // A previous online match can leave Red flagged as ours (we were the guest). Single player
            // is always Blue; career stats and achievements key on isLocalPlayer.
            for (const c of getAllCombatants()) if (c) c.isLocalPlayer = (c === combatants.left);
```

In `startDoublesMatch`, right after `setupDoublesMatchCommon();`, add the same two-line block (local doubles: you are the Blue front).

**3b, Thunderstorm career gated on the local caster.** In the `thunderstormZap` dep, replace `if (window.StatTracker) {` (the block holding `StatTracker.increment('thunderstorm_casts');`) with:

```js
                        if (window.StatTracker && window.Achievements && Achievements.isMe(casterC)) {
```

In `executeThunderstorm`, replace `if (isPlayer || c.isLocalPlayer) {` (the "Track stats (only for local player)" block) with:

```js
            if (!isResimulating && window.Achievements && Achievements.isMe(c)) {
```

**3c, rounds/matches keyed on the local side.** In `endRound`, right after `const presWon = spectating || localWon;` add:

```js
            const meSide = window.Achievements ? Achievements.localSide() : null;   // null: spectator, nothing to count
```

Right after `const aiHealth = ...;` (the "Save gate health before transitioning" pair), add:

```js
            // Career round stats belong to the LOCAL side (an online guest plays Red).
            if (meSide) {
                if (winnerSide === meSide) {
                    StatTracker.increment('rounds_won');
                    if ((meSide === 'left' ? playerHealth : aiHealth) === stageMaxHealth(meSide)) StatTracker.increment('perfect_rounds');
                } else {
                    StatTracker.increment('rounds_lost');
                }
            }
```

Then delete the old increments: in the `winnerOwner === 'player'` branch remove the `StatTracker.increment('rounds_won');` line and the `if (playerHealth === stageMaxHealth('left')) { StatTracker.increment('perfect_rounds'); }` block (with its comments). In the `else` branch remove `StatTracker.increment('rounds_lost');` and its comment. In **both** game-over blocks replace `StatTracker.increment('matches_won');` / `StatTracker.increment('matches_lost');` with:

```js
                    if (meSide) StatTracker.increment(winnerSide === meSide ? 'matches_won' : 'matches_lost');
```

**3d, parries keyed on the local side.** In `parryProjectile`, replace `if (!isResimulating && parryer === 'player') {` with:

```js
                if (!isResimulating && window.Achievements && Achievements.localSide() === (parryer === 'player' ? 'left' : 'right')) {
```

**3e, damage rollback-gated and local-keyed.** In `dealDamageToTower`, delete the two lines `StatTracker.increment('damage_taken', damage);` and `StatTracker.increment('damage_dealt', damage);` (and their `// Player took/dealt damage` comments). Insert right before `updateHealthBars();`:

```js
            // Career damage belongs to the LOCAL side, counted once (the sim calls this during rollback resim too).
            const meSide = window.Achievements ? Achievements.localSide() : null;
            if (!isResimulating && meSide) {
                StatTracker.increment((isPlayerTower ? 'left' : 'right') === meSide ? 'damage_taken' : 'damage_dealt', damage);
            }
```

**3f, wire `projectiles_blocked`.** In the fireball `onPaddleHit`, replace

```js
                        if (!ctx.isResimulating) { ctx.deps.playSound('block', px, 0.6); ctx.deps.onShieldBlock(railKey || side); }
```

with

```js
                        if (!ctx.isResimulating) {
                            ctx.deps.playSound('block', px, 0.6); ctx.deps.onShieldBlock(railKey || side);
                            if (window.StatTracker && window.Achievements && Achievements.localSide() === side) StatTracker.increment('projectiles_blocked');
                        }
```

**3g, wire `freeze_time_inflicted`.** In the frostbolt `onPaddleHit`, inside the existing `if (!ctx.isResimulating) {` block, after `ctx.deps.showFrozenText(...)`, add:

```js
                            const me = window.Achievements ? Achievements.localSide() : null;
                            if (me && side !== me && window.StatTracker) StatTracker.increment('freeze_time_inflicted', ctx.abilities.frostbolt.freezeDuration);
```

- [ ] **Step 4: Run test to verify it passes**

Reload, run the Step 1 snippet. Expected: `TEST 2 done`, **no** assertion errors. Reload.

- [ ] **Step 5: Oracle check**

Reload, run Task 1 Step 1's snippet. All three values must equal the baseline.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Career stats credit the local side: guest wins/parries/damage, rollback-gated damage, stale isLocalPlayer, blocked + freeze-time wired"
```

---

### Task 3: Match-flow hooks (rounds, match end)

Wires `resetMatch`, `roundStart`, `roundEnd` and `evaluateMatchEnd` into the round loop. After this task, Clean Sweep, Comeback Kid, Speed Brine, Marathon, Untouched, Overtime Hero, Demolition and the milestones work end to end.

**Files:**
- Modify: `index.html`, at `resetGame` (~26795), `resetRound` (~26891) and `endRound` (~28974, ~29017, ~29058).

**Interfaces:**
- Consumes: `Achievements.resetMatch()`, `note('roundStart' | 'roundEnd', ...)`, `evaluateMatchEnd(winnerSide)` (Task 1).
- Produces: `Achievements.lastUnlocked()` is filled at every real match end and empty after `resetGame()`. Task 6 reads it.

- [ ] **Step 1: Write the failing test**

Reload. Run:

```js
// TEST 3: match-flow hooks via the headless simulator.
(() => {
  const KEY = 'volleybolt_achievements';
  const backup = localStorage.getItem(KEY);
  try {
    // 3a: a headless match without achTest touches nothing
    dbg.achTest = false;
    const before = localStorage.getItem(KEY);
    dbg.simMatch(7);
    console.assert(localStorage.getItem(KEY) === before, '3a: headless saved nothing');

    // 3b: with achTest the flags track the real match
    dbg.achTest = true;
    const n0 = Achievements.testCounts._matches || 0;
    const r = dbg.simMatch(7);
    const f = Achievements.flags();
    console.assert(r.winner, '3b: match finished', r);
    console.assert((Achievements.testCounts._matches || 0) === n0 + 1, '3b: evaluated once');
    console.assert(f.lastRoundNo === r.rounds, '3b: last round number', f.lastRoundNo, r.rounds);
    console.assert(f.roundsLost === (r.log.match(/R/g) || []).length, '3b: rounds lost = Red rounds', f.roundsLost, r.log);
    console.assert(f.clockFrames > 0, '3b: clock read', f.clockFrames);
    console.assert(f.wasOnOwnCore === r.stages.includes('0'), '3b: own-core flag agrees with the stage trace', r.stages);   // r.stages = each round's stage digit

    // 3c: resetGame clears flags and the end-screen list
    resetGame();
    const g = Achievements.flags();
    console.assert(g.lastRoundNo === 0 && g.roundsLost === 0 && Achievements.lastUnlocked().length === 0, '3c: fresh after resetGame', g);
    console.log('TEST 3 done (check for assertion errors above). Reload the page now.');
  } finally {
    dbg.achTest = false;
    if (backup === null) localStorage.removeItem(KEY); else localStorage.setItem(KEY, backup);
    Achievements.load();
  }
})();
```

- [ ] **Step 2: Run test to verify it fails**

Expected: `3b: evaluated once` and `3b: last round number` fail (nothing is wired yet).

- [ ] **Step 3: Wire the hooks**

At the very top of `resetGame()` body (before `roundLog = [];`):

```js
            if (window.Achievements) Achievements.resetMatch();   // quitting mid-match earns nothing; fresh flags
```

In `resetRound()`, right after `if (combatants.right) combatants.right.towerHealth = aiGateHealth;`:

```js
            if (window.Achievements) Achievements.note('roundStart', { stage: currentStage, hp: { left: playerGateHealth, right: aiGateHealth } });
```

In `endRound()`, right after the two lines `const playerHealth = ...;` / `const aiHealth = ...;` (and after Task 2's career-stats block):

```js
            if (window.Achievements) Achievements.note('roundEnd', { winnerSide, territoryFalls, roundNo: totalRoundsPlayed, hp: { left: playerHealth, right: aiHealth } });
```

In **both** game-over blocks, right after `StatTracker.commitMatch();`:

```js
                    if (window.Achievements) Achievements.evaluateMatchEnd(winnerSide);   // after commit: milestones read the new career
```

- [ ] **Step 4: Run test to verify it passes**

Reload, run the Step 1 snippet. Expected: `TEST 3 done`, **no** assertion errors.

- [ ] **Step 5: Oracle check**

Reload, run Task 1 Step 1's snippet. All three values must equal the baseline.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Achievements: round/match hooks (resetGame, resetRound, endRound, match-end evaluation)"
```

---

### Task 4: Spell hooks, `castBy`, and the simulator sanity run

Wires casts, freezes, Chill clashes, Thunderstorm zaps, fireball tier raises and beam clashes. Adds `proj.castBy` to Chill Dills and carries it through rollback snapshots.

**Files:**
- Modify: `index.html`, at `spawnFrostbolt` (~14595), `captureGameState` projectiles (~24727), `restoreGameState` (~24943, ~24964), the fireball `onPaddleHit` (~2505/2528), the frostbolt `onCast` (~2584) and `onPaddleHit` (~2618), `parryProjectile` (~15249), `completeCasting`'s fireball counter (~28184), the sim deps `onChillClash` (~25842), `onOverpower` (neighbour, new `noteAchievement`), `onJuiceActivate` (~25901), `onBeamClashResolve` (~25921), `thunderstormZap` (~26017), `executeThunderstorm` (~27605), and the `sim.js` script tag (~764).
- Modify: `js/sim.js`, at the Chill-vs-Chill clash call (~355) and overpower (~410, ~416).

**Interfaces:**
- Consumes: `Achievements.note(...)` (Task 1); the payload shapes listed in Task 1.
- Produces: `proj.castBy: 'player'|'ai'` on every Chill Dill (never hashed); sim dep `noteAchievement(event, data)`; `onChillClash(midX, midZ, a, b)` now receives both projectiles.

- [ ] **Step 1: Write the failing test**

Reload. Run:

```js
// TEST 4: spell hooks. Main menu (combatants exist), fresh reload.
(() => {
  const A = Achievements;
  // 4a: castBy on spawn + through a snapshot
  const p = window.spawnFrostbolt('ai', 8, 0, -20, 0);
  console.assert(p.castBy === 'ai', '4a: castBy at spawn', p.castBy);
  const snap = captureGameState();
  const sp = snap.projectiles.find(x => x.id === p.id);
  console.assert(sp && sp.castBy === 'ai', '4a: castBy in snapshot', sp);
  p.castBy = 'player'; restoreGameState(snap);
  const back = projectiles.find(x => x.id === p.id);
  console.assert(back && back.castBy === 'ai', '4a: castBy restored', back && back.castBy);
  window.destroyProjectile(back || p);

  // 4b: sim hooks are rollback-gated
  A.resetMatch();
  const ctx = buildSimCtx(); ctx.isResimulating = true;
  ABILITY_REGISTRY.frostbolt.behavior.onPaddleHit({ type: 'frostbolt', owner: 'player', castBy: 'ai', isParried: true, parriedBy: 'player', x: 8, z: 0 }, 'right', ctx, 'right');
  const fb = { type: 'fireball', owner: 'ai', x: 8, z: 0, velX: -20, velZ: 0, volleyCount: 3, hitboxRadius: 0.3 };
  ABILITY_REGISTRY.fireball.behavior.onPaddleHit(fb, 'left', ctx, 'left');
  let f = A.flags();
  console.assert(f.freezesInflicted === 0 && !f.returnToSender && !f.maxRally, '4b: resim notes nothing', f);
  // live pass
  const live = buildSimCtx(); live.isResimulating = false;
  ABILITY_REGISTRY.frostbolt.behavior.onPaddleHit({ type: 'frostbolt', owner: 'player', castBy: 'ai', isParried: true, parriedBy: 'player', x: 8, z: 0 }, 'right', live, 'right');
  const fb2 = { type: 'fireball', owner: 'ai', x: 8, z: 0, velX: -20, velZ: 0, volleyCount: 3, hitboxRadius: 0.3 };
  ABILITY_REGISTRY.fireball.behavior.onPaddleHit(fb2, 'left', live, 'left');
  f = A.flags();
  console.assert(f.freezesInflicted === 1 && f.returnToSender && f.maxRally, '4b: live notes', f);
  combatants.right.freezeTime = 0;

  // 4c: deps
  A.resetMatch();
  const deps = buildSimCtx().deps;
  deps.onBeamClashResolve(combatants.left, combatants.right, 0);
  deps.onChillClash(0, 0, { castBy: 'player' }, { castBy: 'ai' });
  deps.noteAchievement('tier', { side: 'left', from: 3, to: 4 });
  deps.onJuiceActivate(combatants.left);
  f = A.flags();
  console.assert(f.beamClashWon && f.coldWar && f.maxRally && f.castsByMe === 1, '4c: deps note', f);
  if (window.onJuiceEnd) window.onJuiceEnd(combatants.left);
  A.resetMatch();
  console.log('TEST 4 done (check for assertion errors above). Reload the page now.');
})();
```

- [ ] **Step 2: Run test to verify it fails**

Expected: `4a: castBy at spawn` fails, and `deps.noteAchievement is not a function` stops the run at 4c (or `4b: live notes` fails first).

- [ ] **Step 3: `castBy` and the snapshot**

In `window.spawnFrostbolt`'s `proj` literal, after `parriedBy: null,` add:

```js
                    castBy: owner,  // who CAST it (owner flips on a parry); bookkeeping only, never hashed
```

In `captureGameState`'s `projectiles.map(...)`, after `parriedBy: p.parriedBy || null,` add `castBy: p.castBy || null,`.

In `restoreGameState`: after `existing.parriedBy = sp.parriedBy;` add `existing.castBy = sp.castBy;`. After `newProj.parriedBy = sp.parriedBy;` add `newProj.castBy = sp.castBy;`.

- [ ] **Step 4: Hooks in index.html**

Fireball `onPaddleHit`: in the live block from Task 2 (`if (!ctx.isResimulating) { ... projectiles_blocked ... }`), add as its last line (`proj.volleyCount++` already ran above):

```js
                            if (window.Achievements) Achievements.note('tier', { side, from: proj.volleyCount - 1, to: proj.volleyCount });
```

Frostbolt `onCast`: inside the existing `if (!ctx.isResimulating) {` block, after the `frostbolt_casts` line:

```js
                            if (window.Achievements) Achievements.note('cast', { c: combatant });
```

Frostbolt `onPaddleHit`: inside the existing `if (!ctx.isResimulating) {` block (after Task 2's freeze-time lines):

```js
                            if (window.Achievements) Achievements.note('freeze', { frozenSide: side, proj });
```

`parryProjectile`: replace

```js
                    proj.volleyCount = Math.min((proj.volleyCount || 0) + 1, 4);
```

with (same arithmetic):

```js
                    const vcBefore = proj.volleyCount || 0;
                    proj.volleyCount = Math.min(vcBefore + 1, 4);
                    if (!isResimulating && window.Achievements) Achievements.note('tier', { side: parryer === 'player' ? 'left' : 'right', from: vcBefore, to: proj.volleyCount });
```

`completeCasting`'s fireball counter: inside `if (!isResimulating) {`, after the `fireball_casts` line:

```js
                if (window.Achievements) Achievements.note('cast', { c });
```

Sim deps (the object holding `onChillClash`, `onOverpower`, ...):
- Change `onChillClash: (midX, midZ) => {` to `onChillClash: (midX, midZ, a, b) => {` and add as its first body line: `if (window.Achievements) Achievements.note('chillClash', { a, b });`
- Add a new dep right after the `onOverpower` entry:

```js
            // Achievements bookkeeping from js/sim.js (called on the live pass only; writes no sim state).
            noteAchievement: (event, data) => { if (window.Achievements) Achievements.note(event, data); },
```

- In `onJuiceActivate`, add as first line: `if (window.Achievements) Achievements.note('cast', { c: combatant });`
- In `onBeamClashResolve`, add as first line: `if (window.Achievements && winner) Achievements.note('beamClash', { winnerSide: winner.side });`
- In `thunderstormZap`, inside the `else` branch (zapped > 0), right after `if (window.showSpellCastText) ...`:

```js
                        if (window.Achievements) { Achievements.note('cast', { c: casterC }); Achievements.note('zap', { c: casterC, count: zapsToPerform }); }
```

`executeThunderstorm`: inside Task 2's `if (!isResimulating && window.Achievements && Achievements.isMe(c)) {` block, nothing changes. Right **before** that block add:

```js
            if (!isResimulating && window.Achievements) { Achievements.note('cast', { c }); Achievements.note('zap', { c, count: zapsToPerform }); }
```

- [ ] **Step 5: Hooks in js/sim.js**

At the Chill-vs-Chill clash (~355), pass both projectiles:

```js
                        if (!isResimulating) (D.onChillClash || D.onFrostboltCancel)((proj.x + other.x) * 0.5, (proj.z + other.z) * 0.5, proj, other);
```

Overpower (~410 and ~416): same arithmetic, with the pre-value kept. Replace

```js
                        proj.volleyCount = Math.min((proj.volleyCount || 0) + 1, 4);
```

with

```js
                        const vcP = proj.volleyCount || 0;
                        proj.volleyCount = Math.min(vcP + 1, 4);
                        if (!isResimulating && D.noteAchievement) D.noteAchievement('tier', { side: proj.owner === 'player' ? 'left' : 'right', from: vcP, to: proj.volleyCount });
```

and

```js
                        other.volleyCount = Math.min((other.volleyCount || 0) + 1, 4);
```

with

```js
                        const vcO = other.volleyCount || 0;
                        other.volleyCount = Math.min(vcO + 1, 4);
                        if (!isResimulating && D.noteAchievement) D.noteAchievement('tier', { side: other.owner === 'player' ? 'left' : 'right', from: vcO, to: other.volleyCount });
```

In `index.html`, bump the cache-buster: `js/sim.js?v=51-chill-clash-fx` → `js/sim.js?v=52-achievements`.

- [ ] **Step 6: Run test to verify it passes**

Reload, run the Step 1 snippet. Expected: `TEST 4 done`, **no** assertion errors. Reload.

- [ ] **Step 7: Oracle check**

Reload, run Task 1 Step 1's snippet. All three values must equal the baseline (`castBy` isn't hashed, and the tier arithmetic is unchanged).

- [ ] **Step 8: Simulator sanity run (spec §7)**

Reload. Run:

```js
dbg.achTest = true; Achievements.testCounts._matches = 0;
for (const k of Object.keys(Achievements.testCounts)) if (k !== '_matches') delete Achievements.testCounts[k];
dbg.simBatchAsync(1, 40);
```

Poll `window.__simOut.done` until `true` (a few minutes). Then run `({ ...dbg.achievements.counts(), err: __simOut.error })`, then `dbg.achTest = false`.

Expected: `err` is null and `_matches === 40`; `PICKLE_MONK` is absent (the AI always casts); `MAX_RALLY` and `UNTOUCHED` are present; at least one of `CLEAN_SWEEP` / `SPEED_BRINE` / `MARATHON` / `COMEBACK_KID` / `DEMOLITION` is present; no count exceeds 40. Paste the counts into your report. If `MAX_RALLY` is 0, a tier hook is dead: STOP and investigate.

- [ ] **Step 9: Commit**

```bash
git add index.html js/sim.js
git commit -m "Achievements: spell hooks (casts, freezes, Chill clash, zaps, tier raises, beam clash) + castBy through rollback"
```

---

### Task 5: Career Achievements tab + red dots

Career gets two tabs, *Stats* (unchanged) and *Achievements*. The main-menu Career button and the tab show a red dot while anything is unseen. Opening the tab marks everything seen.

**Files:**
- Modify: `index.html`, the `#careerScreen` markup (~316–328), the `#domBtnCareer` markup (~90), `populateCareer` area (~22076), `wireDOMMenu`'s Career wiring (~22171), `showMenuScreen` prompts (~22314), `setDOMMenuVisible` (~22228), and gamepad left/right paging (~4877).
- Modify: `styles.css`, after the Career block (`#careerScreen .menu-btn.menu-btn-ghost { margin-left: 0; }`, ~3287).

**Interfaces:**
- Consumes: `Achievements.LIST`, `unlockedAt(id)`, `progress(id)`, `unseenIds()`, `markAllSeen()` (Task 1).
- Produces: `window.careerSetTab(i: 0|1)`, `window.refreshAchievementDots()`, `window.populateAchievements()`.

- [ ] **Step 1: Write the failing test**

Reload, stay on the main menu. Run:

```js
// TEST 5: Career tabs + dots. Main menu.
(() => {
  const KEY = 'volleybolt_achievements';
  const backup = localStorage.getItem(KEY);
  const $ = (id) => document.getElementById(id);
  try {
    Achievements._wipe(); Achievements.unlock(['COLD_WAR']);
    refreshAchievementDots();
    console.assert($('careerMenuDot') && !$('careerMenuDot').hidden, '5a: menu dot on');
    $('domBtnCareer').click();
    console.assert($('careerScreen').classList.contains('visible'), '5b: career open');
    console.assert(!$('careerList').hidden && $('achList').hidden, '5b: opens on Stats');
    console.assert(!$('achTabDot').hidden, '5b: tab dot on');
    careerSetTab(1);
    console.assert($('careerList').hidden && !$('achList').hidden, '5c: achievements tab shown');
    console.assert($('achList').querySelectorAll('.ach-row').length === 20, '5c: 20 rows');
    console.assert($('achList').querySelectorAll('.ach-row.is-unlocked').length === 1, '5c: one unlocked');
    console.assert($('achList').querySelector('.ach-row.is-unlocked .ach-dot'), '5c: new card dotted this time');
    console.assert($('achList').querySelectorAll('.ach-progress').length >= 1, '5c: milestone progress bars');
    console.assert(Achievements.unseenIds().length === 0 && $('achTabDot').hidden && $('careerMenuDot').hidden, '5d: opening marks seen');
    document.dispatchEvent(new KeyboardEvent('keydown', { code: 'ArrowLeft' }));
    console.assert(!$('careerList').hidden, '5e: ArrowLeft back to Stats');
    $('careerBack').click();
    console.log('TEST 5 done (check for assertion errors above)');
  } finally {
    if (backup === null) localStorage.removeItem(KEY); else localStorage.setItem(KEY, backup);
    Achievements.load(); if (window.refreshAchievementDots) refreshAchievementDots();
  }
})();
```

- [ ] **Step 2: Run test to verify it fails**

Expected: `ReferenceError: refreshAchievementDots is not defined`.

- [ ] **Step 3: Markup**

In `#domBtnCareer`, after `<span class="menu-btn-label">Career</span>`, add:

```html
                    <span class="ach-dot" id="careerMenuDot" hidden aria-label="New achievement"></span>
```

In `#careerScreen`, replace `<div id="careerList" class="career-list"></div>` with:

```html
                <div class="career-tabs" role="tablist">
                    <button type="button" class="career-tab active" id="careerTabStats" role="tab" aria-selected="true">Stats</button>
                    <button type="button" class="career-tab" id="careerTabAch" role="tab" aria-selected="false">Achievements<span class="ach-dot" id="achTabDot" hidden></span></button>
                </div>
                <div id="careerList" class="career-list"></div>
                <div id="achList" class="ach-list" hidden></div>
```

(The tabs aren't `.menu-btn`, so gamepad focus skips them. The controller switches tabs with ←/→ like How to Play's pages, and Back stays the only focus stop.)

- [ ] **Step 4: Rendering + wiring**

Right after `populateCareer()`'s closing brace, add:

```js
        // Achievements tab: the four groups as career-card windows. Unlocked = gold rim + date;
        // milestones show a progress bar while locked; a red dot marks cards not yet seen.
        const ACH_GROUPS = [
            ['milestones', 'Milestones'], ['feats', 'Feats'], ['mastery', 'Spell Mastery'], ['pressure', 'Pressure'],
        ];
        function populateAchievements() {
            const list = document.getElementById('achList');
            if (!list || !window.Achievements) return;
            const unseen = new Set(Achievements.unseenIds());
            list.innerHTML = '';
            for (const [group, title] of ACH_GROUPS) {
                const card = document.createElement('div');
                card.className = 'career-card ach-card';
                const head = document.createElement('div');
                head.className = 'career-card-title';
                head.textContent = title;
                card.appendChild(head);
                for (const a of Achievements.LIST) {
                    if (a.group !== group) continue;
                    const at = Achievements.unlockedAt(a.id);
                    const row = document.createElement('div');
                    row.className = 'ach-row ' + (at ? 'is-unlocked' : 'is-locked');
                    const top = document.createElement('div');
                    top.className = 'ach-top';
                    const name = document.createElement('span');
                    name.className = 'ach-name';
                    name.textContent = a.name;
                    top.appendChild(name);
                    if (at && unseen.has(a.id)) {
                        const dot = document.createElement('span');
                        dot.className = 'ach-dot';
                        top.appendChild(dot);
                    }
                    const meta = document.createElement('span');
                    meta.className = 'ach-meta';
                    const prog = !at ? Achievements.progress(a.id) : null;
                    meta.textContent = at ? new Date(at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
                        : prog ? prog[0].toLocaleString() + ' / ' + prog[1].toLocaleString() : '';
                    top.appendChild(meta);
                    row.appendChild(top);
                    const desc = document.createElement('div');
                    desc.className = 'ach-desc';
                    desc.textContent = a.desc;
                    row.appendChild(desc);
                    if (prog) {
                        const bar = document.createElement('div');
                        bar.className = 'ach-progress';
                        const fill = document.createElement('i');
                        fill.style.width = Math.round(100 * prog[0] / prog[1]) + '%';
                        bar.appendChild(fill);
                        row.appendChild(bar);
                    }
                    card.appendChild(row);
                }
                list.appendChild(card);
            }
        }
        window.populateAchievements = populateAchievements;

        // Red dot on the main-menu Career button and the Achievements tab while anything is unseen.
        function refreshAchievementDots() {
            const on = !!(window.Achievements && Achievements.unseenIds().length);
            for (const id of ['careerMenuDot', 'achTabDot']) {
                const d = document.getElementById(id);
                if (d) d.hidden = !on;
            }
        }
        window.refreshAchievementDots = refreshAchievementDots;

        // Career tabs: 0 = Stats, 1 = Achievements (opening it marks everything seen).
        function careerSetTab(i) {
            const ach = i === 1;
            const stats = document.getElementById('careerList'), achList = document.getElementById('achList');
            const tS = document.getElementById('careerTabStats'), tA = document.getElementById('careerTabAch');
            if (!stats || !achList || !tS || !tA) return;
            stats.hidden = ach; achList.hidden = !ach;
            tS.classList.toggle('active', !ach); tA.classList.toggle('active', ach);
            tS.setAttribute('aria-selected', String(!ach)); tA.setAttribute('aria-selected', String(ach));
            if (ach) {
                populateAchievements();             // draws this visit's dots first...
                if (window.Achievements) Achievements.markAllSeen();
                refreshAchievementDots();           // ...then clears the menu/tab dots
            }
        }
        window.careerSetTab = careerSetTab;
```

In `wireDOMMenu`, replace the Career click line with:

```js
            if (btnCareer) btnCareer.addEventListener('click', () => { populateCareer(); careerSetTab(0); refreshAchievementDots(); showMenuScreen('careerScreen', 'menu'); });
            const tabStats = document.getElementById('careerTabStats');
            const tabAch = document.getElementById('careerTabAch');
            if (tabStats) tabStats.addEventListener('click', () => careerSetTab(0));
            if (tabAch) tabAch.addEventListener('click', () => careerSetTab(1));
            document.addEventListener('keydown', (e) => {
                const screen = document.getElementById('careerScreen');
                if (!screen || !screen.classList.contains('visible')) return;
                if (e.code !== 'ArrowLeft' && e.code !== 'ArrowRight') return;
                careerSetTab(e.code === 'ArrowRight' ? 1 : 0);
                if (window.ToneSFX) ToneSFX.uiHover();
                e.preventDefault();
            });
```

In `setDOMMenuVisible`, inside `if (show) {`, add as the last line: `if (window.refreshAchievementDots) refreshAchievementDots();`

In `showMenuScreen`'s prompt chain, before the final `else`, add:

```js
                else if (id === 'careerScreen') setGamepadPrompts([{ action: 'page' }, { action: 'back' }]);
```

In the gamepad left/right block, after the `howToPlayScreen` branch, add:

```js
                } else if (root.id === 'careerScreen' && window.careerSetTab) {
                    careerSetTab(rightEdge ? 1 : 0);
                    if (window.ToneSFX) ToneSFX.uiHover();
```

- [ ] **Step 5: Styles**

Append after `#careerScreen .menu-btn.menu-btn-ghost { margin-left: 0; }`:

```css
/* ---- Career tabs: Stats / Achievements ---- */
.career-tabs { display: flex; gap: 10px; margin-bottom: 14px; }
.career-tab {
    font: inherit; font-size: 22px; letter-spacing: 1px; cursor: pointer;
    color: #9aa0b3; background: none; border: 2px solid transparent; border-radius: 8px;
    padding: 6px 18px 7px;
}
.career-tab:hover { color: #fff4c2; }
.career-tab.active {
    color: #ffe39a;
    background: linear-gradient(180deg, rgba(52, 62, 84, 0.9) 0%, rgba(22, 27, 40, 0.92) 100%);
    border-color: rgba(224, 230, 240, 0.85);
}
.career-list[hidden], .ach-list[hidden] { display: none; }
.ach-dot {
    display: inline-block; width: 11px; height: 11px; margin-left: 8px; vertical-align: super;
    border-radius: 50%; background: #e2463c; box-shadow: 0 0 0 2px rgba(16, 24, 40, 0.9);
}
.ach-dot[hidden] { display: none; }

/* ---- Achievements tab: four group windows, 2x2 like the stats ---- */
.ach-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(420px, auto));
    gap: 16px 18px;
    max-height: 64vh;
    overflow-y: auto;
}
.ach-row { padding: 5px 0 6px 12px; border-left: 3px solid transparent; }
.ach-row + .ach-row { border-top: 1px solid rgba(224, 230, 240, 0.12); }
.ach-top { display: flex; align-items: baseline; gap: 8px; }
.ach-name { font-size: 19px; }
.ach-meta { margin-left: auto; font-size: 15px; color: #9aa0b3; white-space: nowrap; }
.ach-desc { font-size: 15px; color: #c8c3d8; }
.ach-row.is-locked .ach-name { color: #9aa0b3; }
.ach-row.is-locked .ach-desc { opacity: 0.7; }
.ach-row.is-unlocked { border-left-color: #f0c050; }
.ach-row.is-unlocked .ach-name { color: #ffe39a; }
.ach-row.is-unlocked .ach-meta { color: #f0c050; }
.ach-row .ach-dot { margin-left: 0; vertical-align: middle; }
.ach-progress { height: 5px; margin-top: 5px; background: rgba(224, 230, 240, 0.15); border-radius: 3px; overflow: hidden; }
.ach-progress > i { display: block; height: 100%; background: #c9a8ff; }
```

- [ ] **Step 6: Run test to verify it passes**

Reload, run the Step 1 snippet. Expected: `TEST 5 done`, **no** assertion errors. Then `dbg.achievements.unlock('MAX_RALLY')`, open Career → Achievements, and take one screenshot of the tab for the report (screenshot only, no gameplay automation). Afterwards run `dbg.achievements.reset()` and reload.

- [ ] **Step 7: Oracle check**

Reload, run Task 1 Step 1's snippet. All three values must equal the baseline.

- [ ] **Step 8: Commit**

```bash
git add index.html styles.css
git commit -m "Career: Achievements tab (grouped cards, progress, dates) + red dots on Career and the tab"
```

---

### Task 6: End-screen "Achievement unlocked" strip

After the match summary, the end screen lists what this match earned. It rises in with the rest of the end screen. Nothing pops up mid-match.

**Files:**
- Modify: `index.html`, add `renderAchievementStrip` next to `ensureEndScreen` (~26617); call it from `showVictoryScreen` after `renderMatchSummary(ensureEndScreen(), false);` (~26290); refresh dots after a match end (same spot).
- Modify: `styles.css`, after the `#endScreen #victoryButtons` rule (~3882).

**Interfaces:**
- Consumes: `Achievements.lastUnlocked()`, `Achievements.LIST` (Task 1); `lastUnlocked` filled by Task 3 and cleared by `resetGame()`.
- Produces: `window.renderAchievementStrip(root)`. `#endAchStrip` is hidden when the list is empty.

- [ ] **Step 1: Write the failing test**

Reload, stay on the main menu. Run:

```js
// TEST 6: end-screen strip. Main menu (renders into the hidden end screen).
(() => {
  const root = ensureEndScreen();
  renderMatchSummary(root, false);
  // 6a: nothing earned -> no strip
  Achievements.resetMatch();
  renderAchievementStrip(root);
  const strip = document.getElementById('endAchStrip');
  console.assert(strip && strip.hidden, '6a: empty list hides the strip');
  // 6b: chips, capped at 4 + "more"
  const ids = ['COLD_WAR', 'MAX_RALLY', 'UNTOUCHED', 'CLEAN_SWEEP', 'SPEED_BRINE', 'FIRST_BRINE'];
  renderAchievementStrip(root, ids);
  console.assert(!strip.hidden, '6b: shown');
  console.assert(strip.querySelectorAll('.end-ach-chip').length === 4, '6b: 4 chips', strip.querySelectorAll('.end-ach-chip').length);
  console.assert(/\+2 more/.test(strip.textContent), '6b: overflow chip', strip.textContent);
  console.assert(strip.previousElementSibling && strip.previousElementSibling.id === 'msStats', '6b: sits under the stats');
  console.log('TEST 6 done (check for assertion errors above)');
})();
```

- [ ] **Step 2: Run test to verify it fails**

Expected: `ReferenceError: renderAchievementStrip is not defined`.

- [ ] **Step 3: Implement**

Right after `ensureEndScreen()`'s closing brace, add:

```js
        // "Achievement unlocked" strip under the match summary: what THIS match earned (empty = hidden).
        // ids defaults to Achievements.lastUnlocked(); passing ids is for console tests / previews.
        const END_ACH_MAX = 4;
        function renderAchievementStrip(root, ids) {
            const content = root.querySelector('.end-content');
            const stats = root.querySelector('.ms-stats');
            if (!content || !stats) return;
            let strip = document.getElementById('endAchStrip');
            if (!strip) {
                strip = document.createElement('div');
                strip.id = 'endAchStrip';
                strip.className = 'end-ach';
                content.insertBefore(strip, stats.nextSibling);
            }
            const list = (ids || (window.Achievements ? Achievements.lastUnlocked() : []))
                .map(id => window.Achievements && Achievements.LIST.find(a => a.id === id)).filter(Boolean);
            strip.innerHTML = '';
            strip.hidden = list.length === 0;
            for (const a of list.slice(0, END_ACH_MAX)) {
                const chip = document.createElement('div');
                chip.className = 'end-ach-chip';
                const kicker = document.createElement('div');
                kicker.className = 'end-ach-kicker';
                kicker.textContent = 'Achievement unlocked';
                const name = document.createElement('div');
                name.className = 'end-ach-name';
                name.textContent = a.name;
                const desc = document.createElement('div');
                desc.className = 'end-ach-desc';
                desc.textContent = a.desc;
                chip.append(kicker, name, desc);
                strip.appendChild(chip);
            }
            if (list.length > END_ACH_MAX) {
                const more = document.createElement('div');
                more.className = 'end-ach-chip end-ach-more';
                more.textContent = '+' + (list.length - END_ACH_MAX) + ' more';
                strip.appendChild(more);
            }
        }
        window.renderAchievementStrip = renderAchievementStrip;
```

In `showVictoryScreen`, right after `renderMatchSummary(ensureEndScreen(), false);`:

```js
            renderAchievementStrip(ensureEndScreen());
            if (window.refreshAchievementDots) refreshAchievementDots();   // the menu dot is waiting on Continue
```

- [ ] **Step 4: Styles**

Append after the `#endScreen #victoryButtons { ... }` rule:

```css
/* "Achievement unlocked" strip under the stat bars; rises in after the summary */
#endScreen .end-ach {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 12px 16px; max-width: 1500px; margin-top: 4px;
}
#endScreen .end-ach[hidden] { display: none; }
#endScreen .end-ach-chip {
    min-width: 240px; max-width: 340px; padding: 8px 18px 10px;
    background: linear-gradient(180deg, rgba(52, 62, 84, 0.9) 0%, rgba(22, 27, 40, 0.92) 100%);
    border: 2px solid #f0c050; border-radius: 10px;
    box-shadow: inset 0 0 0 1px rgba(16, 24, 40, 0.7), 5px 5px 0 rgba(0, 0, 0, 0.45);
    animation: menuRise 0.5s ease 0.5s both;
}
#endScreen .end-ach-kicker {
    font-family: 'Manrope UI', 'Manrope', sans-serif; font-weight: 800; font-size: 13px;
    letter-spacing: 0.16em; text-transform: uppercase; color: #f0c050;
}
#endScreen .end-ach-name {
    font-family: 'Manrope UI', 'Manrope', sans-serif; font-weight: 800; font-size: 24px; color: #ffe39a;
}
#endScreen .end-ach-desc { font-family: 'Manrope', sans-serif; font-size: 15px; color: #c8c3d8; }
#endScreen .end-ach-more {
    min-width: 0; display: flex; align-items: center;
    font-family: 'Manrope UI', 'Manrope', sans-serif; font-weight: 800; font-size: 20px; color: #ffe39a;
}
```

- [ ] **Step 5: Run test to verify it passes**

Reload, run the Step 1 snippet. Expected: `TEST 6 done`, **no** assertion errors.

Visual check with one screenshot (no gameplay automation): start a 1v1 (`startSinglesMatch()`), wait for `gameState === 'playing'`, then run `dbg.win()`. Once the Victory screen is up, run `renderAchievementStrip(ensureEndScreen(), ['COLD_WAR','MAX_RALLY','UNTOUCHED'])` and take one screenshot. The strip must sit under the stat bars, above the buttons, and clear of the corner team names. If it collides, reduce `#endScreen .end-content`'s `gap` for this case. Do not shrink the existing elements. Reload afterwards.

- [ ] **Step 6: Oracle check**

Reload, run Task 1 Step 1's snippet. All three values must equal the baseline.

- [ ] **Step 7: Commit**

```bash
git add index.html styles.css
git commit -m "End screen: 'Achievement unlocked' strip under the match summary"
```

---

### Task 7: Release checks, docs, owner hand-off

**Files:**
- Modify: `docs/agents/presentation-ui-ux.md` and `docs/agents/gameplay-combat.md` (append one Working Log entry each).
- Modify: the project memory file `volleybolt-3d-props-backdrop.md` (achievements line) or a new `volleybolt-achievements.md` memory plus its `MEMORY.md` pointer.

- [ ] **Step 1: Full regression**

Reload, then run, in order: TEST 1 (Task 1 Step 2), TEST 3, TEST 4, TEST 5, TEST 6 (reload between those that ask for it), and the oracle snippet. Everything passes and the oracle equals the baseline.

- [ ] **Step 2: Working Log entries**

Append to each agent doc's Working Log (match the file's existing entry format):
- `presentation-ui-ux.md`: Career Stats/Achievements tabs (←/→ and gamepad paging; tabs aren't focus stops), red dots (menu + tab, cleared on opening the tab), the end-screen strip (max 4 + "+N more", hidden when empty).
- `gameplay-combat.md`: Achievements module + hooks, all behind `!isResimulating`; `proj.castBy` (not hashed, snapshot-carried); career stats now credit the local side (guest/doubles); damage career stats rollback-gated; oracle unchanged.

- [ ] **Step 3: Commit**

```bash
git add docs/agents/presentation-ui-ux.md docs/agents/gameplay-combat.md
git commit -m "Docs: achievements working-log entries"
```

- [ ] **Step 4: Owner playtest hand-off**

Push the branch (`git push -u origin achievements`). Ask the owner to play 2–3 vs-AI matches and send screenshots of: (1) the end screen after a match that unlocked something, (2) the main menu with the Career dot, (3) the Career → Achievements tab. If someone can host one online 1v1, ask the guest to confirm their win credits them. Remaining open item: online-doubles verification needs four seats. Don't merge; the owner merges when confirmed.

- [ ] **Step 5: Memory**

Update the project memory: achievements implemented on branch `achievements` (not merged); `dbg.achTest` + `dbg.achievements` for testing; milestone backfill on load; career stats now credit the local side. Point `MEMORY.md` at it.
