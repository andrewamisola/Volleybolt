# Pickle Wizard — Static Head-Locked Face

**Date:** 2026-06-24
**Status:** Approved design, prototype-first
**Scope:** Stop the pickle wizard's painted face from distorting when the body rig animates. Keep the face a clean, static image that rides the head rigidly. No expressions, no flipbook.

## Problem

The pickle wizard model (`.pickle/pickle_wizard_v1.glb`) is a single fused, **skinned** mesh: body, hat, cloak, and face are all one primitive with one texture. The face (eyes + smile) is painted into that texture. Because the face geometry is skinned to the body skeleton, any squash/lean/bob from the animation rig **stretches and smears the painted features**. The face reads as a dead, distorting mask.

The desired look is FF9/PS1-authentic: a flat, static 2D face that does **not** warp, but **does** move rigidly with the head (translate + rotate) so it stays seated as the body animates.

## Approach: head-bone-locked face decal

Lift the face off the deforming body and put it on a separate, **non-skinned** plane that is attached to the `Head` bone.

- Non-skinned ⇒ the plane never deforms, so the features never warp.
- `attachToBone(Head, root)` ⇒ the plane inherits the head bone's world transform, so it follows leans/bobs naturally.
- Works across **every** existing animation clip (idle, cast_loop, cast_release, parry, victory, defeat) for free, because it only ever follows the bone.

### Rig facts (verified from the GLB)
- 24 joints, 1 skin. Relevant bones: `neck` → `Head` → `headfront` → `head_end`.
- `Head` is the attach target. `headfront` gives the front-of-face position and forward direction for seating/orienting the plane.
- Idle animation present: `Armature|Idle|baselayer`.

## Components

1. **Face sprite** — `.pickle/pickle_face.png`, a transparent-background PNG of just the eyes + smile, cropped from the clean front-on concept render `.pickle/pickle_wizard_v1.png` (896×1200) using Pillow (already installed). No Blender needed.
2. **Body-face neutralization** — the opaque decal sits flush and covers the original painted face. If edge bleed shows, patch that region of the body texture to plain green as a follow-up (not required for the prototype).
3. **Attach + offset** — create the plane, `attachToBone` it to `Head`, apply a small forward offset + rotation (derived from `headfront`) so it seats on the face. Tunable constants for offset/scale/rotation.

## Build order (prototype-first)

1. Crop `pickle_face.png` from the concept render.
2. Prototype the head-locked plane **in `pickle_viewer.html`** (standalone, zero risk to the game). Verify the face stays crisp through the full idle animation and follows head motion.
3. User eyeballs it in the viewer; tune offset/scale/rotation.
4. Only after approval: port the same ~15 lines into `loadMeshyWizard` in `index.html`, applied per character (P1/P2).

## Out of scope (YAGNI)

- Facial expressions, blinking, lip-sync, flipbooks.
- 3D geometry for face/hat/cloak.
- Re-rigging or re-generating the model.
- Committing the pickle into the game proper — the pickle direction itself is still a separate pending yes/no.

## Success criteria

- In the viewer, the face is a clean, undistorted image during the idle (and any) animation.
- The face translates/rotates with the head bone (no detachment, no warping).
- No change to body animation behavior.
