# Shared Core — read this before any pillar

Every agent loads this first. It is the law that binds all four pillars.

## Determinism is global law
Volleybolt ships **rollback netcode**, so the simulation must produce identical output
on both clients given identical inputs. This is not just the Netcode agent's concern —
it constrains anyone who writes simulation-affecting code.

- Fixed timestep for sim logic — never tie game state to render framerate.
- No `Math.random()` / `Date.now()` / `performance.now()` inside the sim. Use the seeded
  RNG, and treat the seed as a synced input.
- Game state must be serializable (save / load a single frame) so rollback can re-simulate.
- Same operation order on both clients. Float drift is how you desync.

## Global conventions
- Internal `docs/*.md` files are an agent's working memory; the external links in each
  agent doc are the stable canon.
- Sentence-case headings, present tense, append-only Working Logs (never rewrite history).

## Reference
- [Determinism for netcode (Gaffer on Games)](https://gafferongames.com/post/deterministic_lockstep/)
- [Preparing a game for deterministic netcode](https://yal.cc/preparing-your-game-for-deterministic-netcode/)

_Part of [the project master](../PROJECT.md)._
