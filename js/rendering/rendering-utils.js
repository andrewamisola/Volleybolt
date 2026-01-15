/**
 * Volleybolt - Rendering Utilities
 *
 * Color palettes, visual effects, and rendering helpers.
 * These utilities require BABYLON to be loaded (via CDN).
 */

const BABYLON = window.BABYLON;

// ============================================================
// NES PALETTE - Authentic 8-bit colors from the NES PPU
// ============================================================

export const NES_PALETTE = {
    // Blacks & Grays
    black:      "#0F0F0F",
    darkGray:   "#3D3D3D",
    gray:       "#7C7C7C",
    lightGray:  "#BCBCBC",

    // Blues
    darkBlue:   "#0000BC",
    blue:       "#0078F8",
    lightBlue:  "#3CBCFC",
    paleBlue:   "#A4E4FC",

    // Reds
    darkRed:    "#A80020",
    red:        "#F83800",
    lightRed:   "#F87858",

    // Greens
    darkGreen:  "#005800",
    green:      "#00A800",
    lightGreen: "#58D854",

    // Yellows & Golds
    orange:     "#E45C10",
    gold:       "#FC9838",
    yellow:     "#F8D878",
    cream:      "#F8F8F8",

    // Browns
    darkBrown:  "#503000",
    brown:      "#AC7C00",
    tan:        "#F8B800",

    // Purples
    purple:     "#6844FC",
    lavender:   "#B8B8F8"
};

/**
 * Get NES palette as BABYLON.Color3 objects
 * Must be called after BABYLON is loaded
 */
export function getNESColors() {
    if (!BABYLON) return null;

    return {
        black:      BABYLON.Color3.FromHexString(NES_PALETTE.black),
        darkGray:   BABYLON.Color3.FromHexString(NES_PALETTE.darkGray),
        gray:       BABYLON.Color3.FromHexString(NES_PALETTE.gray),
        lightGray:  BABYLON.Color3.FromHexString(NES_PALETTE.lightGray),
        darkBlue:   BABYLON.Color3.FromHexString(NES_PALETTE.darkBlue),
        blue:       BABYLON.Color3.FromHexString(NES_PALETTE.blue),
        lightBlue:  BABYLON.Color3.FromHexString(NES_PALETTE.lightBlue),
        paleBlue:   BABYLON.Color3.FromHexString(NES_PALETTE.paleBlue),
        darkRed:    BABYLON.Color3.FromHexString(NES_PALETTE.darkRed),
        red:        BABYLON.Color3.FromHexString(NES_PALETTE.red),
        lightRed:   BABYLON.Color3.FromHexString(NES_PALETTE.lightRed),
        darkGreen:  BABYLON.Color3.FromHexString(NES_PALETTE.darkGreen),
        green:      BABYLON.Color3.FromHexString(NES_PALETTE.green),
        lightGreen: BABYLON.Color3.FromHexString(NES_PALETTE.lightGreen),
        orange:     BABYLON.Color3.FromHexString(NES_PALETTE.orange),
        gold:       BABYLON.Color3.FromHexString(NES_PALETTE.gold),
        yellow:     BABYLON.Color3.FromHexString(NES_PALETTE.yellow),
        cream:      BABYLON.Color3.FromHexString(NES_PALETTE.cream),
        darkBrown:  BABYLON.Color3.FromHexString(NES_PALETTE.darkBrown),
        brown:      BABYLON.Color3.FromHexString(NES_PALETTE.brown),
        tan:        BABYLON.Color3.FromHexString(NES_PALETTE.tan),
        purple:     BABYLON.Color3.FromHexString(NES_PALETTE.purple),
        lavender:   BABYLON.Color3.FromHexString(NES_PALETTE.lavender)
    };
}

// ============================================================
// GRAYBOX PALETTE - Environment colors using NES palette
// ============================================================

export const GRAYBOX_PALETTE = {
    // Environment
    ground:     NES_PALETTE.black,
    lane:       NES_PALETTE.darkGray,
    laneLight:  NES_PALETTE.gray,
    wall:       NES_PALETTE.darkBrown,
    jungle:     NES_PALETTE.darkGreen,
    structure:  NES_PALETTE.brown,

    // Team colors
    blue:       NES_PALETTE.blue,
    blueLight:  NES_PALETTE.lightBlue,
    red:        NES_PALETTE.red,
    redLight:   NES_PALETTE.lightRed,

    // Neutral accents
    gold:       NES_PALETTE.gold,
    white:      NES_PALETTE.cream
};

/**
 * Get graybox palette as BABYLON.Color3 objects
 */
export function getGrayboxColors() {
    if (!BABYLON) return null;

    return {
        ground:     BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.ground),
        lane:       BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.lane),
        laneLight:  BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.laneLight),
        wall:       BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.wall),
        jungle:     BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.jungle),
        structure:  BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.structure),
        blue:       BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.blue),
        blueLight:  BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.blueLight),
        red:        BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.red),
        redLight:   BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.redLight),
        gold:       BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.gold),
        white:      BABYLON.Color3.FromHexString(GRAYBOX_PALETTE.white)
    };
}

// ============================================================
// LEGACY MCM PALETTE - Compatibility aliases
// ============================================================

export const MCM_PALETTE = {
    mistBlue:   GRAYBOX_PALETTE.lane,
    mistLight:  GRAYBOX_PALETTE.laneLight,
    mistDark:   GRAYBOX_PALETTE.wall,
    teak:       GRAYBOX_PALETTE.structure,
    teakDark:   GRAYBOX_PALETTE.jungle,
    teakLight:  GRAYBOX_PALETTE.wall,
    gold:       GRAYBOX_PALETTE.gold,
    goldBright: GRAYBOX_PALETTE.gold,
    goldDark:   GRAYBOX_PALETTE.gold,
    cream:      GRAYBOX_PALETTE.white,
    pennyTile:  GRAYBOX_PALETTE.lane,
    walnut:     GRAYBOX_PALETTE.structure,
    walnutDark: GRAYBOX_PALETTE.jungle,
    brass:      GRAYBOX_PALETTE.gold,
    mustard:    GRAYBOX_PALETTE.gold,
    orange:     GRAYBOX_PALETTE.gold,
    chiliRed:   GRAYBOX_PALETTE.red,
    teal:       GRAYBOX_PALETTE.blue
};

// ============================================================
// RETRO RESOLUTION UTILITIES
// ============================================================

const RETRO_BASE_W = 960;
const RETRO_BASE_H = 720;

/**
 * Apply D2-style retro resolution with integer upscaling
 */
export function applyRetroResolution(engine, canvas) {
    if (!engine || !canvas) return;

    const cw = canvas.clientWidth;
    const ch = canvas.clientHeight;

    // Choose limiting scale to preserve 4:3 and not exceed either axis
    const scaleW = cw / RETRO_BASE_W;
    const scaleH = ch / RETRO_BASE_H;
    const scale = Math.max(1, Math.floor(Math.min(scaleW, scaleH)));

    // renderWidth = cw / hardwareScalingLevel
    const targetW = RETRO_BASE_W * scale;
    const targetH = RETRO_BASE_H * scale;

    const hsl = Math.max(cw / targetW, ch / targetH);
    engine.setHardwareScalingLevel(hsl);
}

/**
 * Create 4:3 CRT aspect ratio handler
 */
export function create4to3Handler(gameContainer) {
    const resize = () => {
        const windowW = window.innerWidth;
        const windowH = window.innerHeight;
        const targetRatio = 4 / 3;

        let width, height;
        if (windowW / windowH > targetRatio) {
            height = windowH;
            width = height * targetRatio;
        } else {
            width = windowW;
            height = width / targetRatio;
        }

        gameContainer.style.width = width + 'px';
        gameContainer.style.height = height + 'px';
    };

    resize();
    return resize;
}

// ============================================================
// SCREEN SHAKE SYSTEM
// ============================================================

let shakeIntensity = 0;
let shakeDuration = 0;
let cameraBasePosition = null;

/**
 * Initialize screen shake for a camera
 */
export function initScreenShake(camera) {
    if (!camera || !BABYLON) return;
    cameraBasePosition = camera.target.clone();
}

/**
 * Trigger screen shake effect
 */
export function screenShake(intensity = 0.3, duration = 0.2) {
    shakeIntensity = intensity;
    shakeDuration = duration;
}

/**
 * Update screen shake (call from render loop)
 */
export function updateScreenShake(camera, dt) {
    if (!camera || !cameraBasePosition || !BABYLON) return;

    if (shakeDuration > 0) {
        shakeDuration -= dt;
        const shakeX = (Math.random() - 0.5) * 2 * shakeIntensity;
        const shakeY = (Math.random() - 0.5) * 2 * shakeIntensity;
        camera.target = cameraBasePosition.add(new BABYLON.Vector3(shakeX, shakeY, 0));
        shakeIntensity *= 0.9;  // Decay
    } else {
        camera.target = cameraBasePosition;
    }
}

// ============================================================
// IMPACT DECALS
// ============================================================

const impactDecals = [];
const MAX_DECALS = 20;

/**
 * Create an impact decal at a position
 */
export function createImpactDecal(scene, position, type = 'burn', direction = null) {
    if (!scene || !BABYLON) return;

    let decal;

    // Overpower: thin pointed oval streak
    if (type === 'overpower' && direction) {
        const streakLength = 1.8 + Math.random() * 0.5;
        const streakWidth = 0.01;
        decal = BABYLON.MeshBuilder.CreateDisc("streakDecal", {
            radius: 0.5,
            tessellation: 12
        }, scene);
        decal.position.set(position.x, 0.01, position.z);
        decal.rotation.x = Math.PI / 2;
        decal.scaling.x = streakLength;
        decal.scaling.z = streakWidth;
        const angle = Math.atan2(direction.z, direction.x);
        decal.rotation.y = -angle;
    } else {
        // Regular circular decal
        const decalSize = 0.5 + Math.random() * 0.5;
        decal = BABYLON.MeshBuilder.CreateDisc("decal", {
            radius: decalSize,
            tessellation: 8
        }, scene);
        decal.position.set(position.x, 0.01, position.z);
        decal.rotation.x = Math.PI / 2;
        decal.rotation.y = Math.random() * Math.PI * 2;
    }

    const decalMat = new BABYLON.StandardMaterial("decalMat", scene);
    decalMat.disableLighting = true;

    if (type === 'overpower') {
        decalMat.emissiveColor = new BABYLON.Color3(0.2, 0.08, 0.02);
        decalMat.alpha = 0.85;
    } else if (type === 'burn' || type === 'fire') {
        decalMat.emissiveColor = new BABYLON.Color3(0.35, 0.15, 0.05);
        decalMat.alpha = 0.7;
    } else if (type === 'frost') {
        decalMat.emissiveColor = new BABYLON.Color3(0.1, 0.2, 0.3);
        decalMat.alpha = 0.5;
    }

    decal.material = decalMat;
    impactDecals.push({ mesh: decal, life: 5 });

    // Remove oldest if too many
    if (impactDecals.length > MAX_DECALS) {
        const old = impactDecals.shift();
        old.mesh.dispose();
    }
}

/**
 * Update impact decals (call from render loop)
 */
export function updateImpactDecals(dt) {
    for (let i = impactDecals.length - 1; i >= 0; i--) {
        const d = impactDecals[i];
        d.life -= dt;

        if (d.life <= 0) {
            d.mesh.dispose();
            impactDecals.splice(i, 1);
        } else if (d.life < 2) {
            // Stepped fading
            const fadeProgress = (2 - d.life) / 2;
            const alphaSteps = [0.6, 0.45, 0.3, 0.15, 0];
            const stepIndex = Math.min(Math.floor(fadeProgress * alphaSteps.length), alphaSteps.length - 1);
            d.mesh.material.alpha = alphaSteps[stepIndex];
        }
    }
}

/**
 * Clear all impact decals
 */
export function clearImpactDecals() {
    for (const d of impactDecals) {
        d.mesh.dispose();
    }
    impactDecals.length = 0;
}

// ============================================================
// STEPPED UI/ANIMATION TIMING
// ============================================================

const UI_STEP_MS = 40;  // 25fps (D2 style)
let lastUIStepTime = 0;
let uiSteppingEnabled = true;

/**
 * Check if UI should update this frame (25fps stepping)
 */
export function shouldStepUI() {
    if (!uiSteppingEnabled) return true;
    const now = performance.now();
    if (now - lastUIStepTime >= UI_STEP_MS) {
        lastUIStepTime = now;
        return true;
    }
    return false;
}

/**
 * Enable/disable UI stepping
 */
export function setUIStepping(enabled) {
    uiSteppingEnabled = enabled;
    console.log("UI stepping: " + (enabled ? "25fps" : "smooth"));
}

// PS1-style framerate
let ps1ThrottleEnabled = false;
let PS1_FRAME_TIME = 1000 / 20;

/**
 * Enable/disable PS1 framerate throttling
 */
export function setPS1Framerate(enabled, fps = 20) {
    ps1ThrottleEnabled = enabled;
    PS1_FRAME_TIME = 1000 / fps;
    console.log("PS1 framerate: " + (enabled ? fps + "fps" : "smooth"));
}

/**
 * Check if PS1 throttle is enabled and get frame time
 */
export function getPS1Settings() {
    return { enabled: ps1ThrottleEnabled, frameTime: PS1_FRAME_TIME };
}

// ============================================================
// CAMERA UTILITIES
// ============================================================

let defaultCameraAlpha = -Math.PI / 2;

/**
 * Flip camera for client (PvP - see from opponent's side)
 */
export function flipCameraForClient(camera) {
    if (camera) {
        camera.alpha = Math.PI / 2;
    }
}

/**
 * Reset camera to default (host view)
 */
export function resetCameraToDefault(camera) {
    if (camera) {
        camera.alpha = defaultCameraAlpha;
    }
}

/**
 * Set the default camera alpha
 */
export function setDefaultCameraAlpha(alpha) {
    defaultCameraAlpha = alpha;
}

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window
// ============================================================
// NOTE: Many rendering functions are STILL DEFINED in index.html and
// should NOT be overwritten. Only export constants that don't conflict.

if (typeof window !== 'undefined') {
    // Palettes only - these are safe constants
    window.NES_PALETTE = NES_PALETTE;
    window.GRAYBOX_PALETTE = GRAYBOX_PALETTE;
    window.MCM_PALETTE = MCM_PALETTE;
    window.getNESColors = getNESColors;
    window.getGrayboxColors = getGrayboxColors;

    // NOTE: The following are STILL DEFINED in index.html:
    // - screenShake, createImpactDecal (visual effects)
    // - shouldStepUI, setUIStepping, setPS1Framerate (timing)
    // - flipCameraForClient, resetCameraToDefault (camera)
    // Do NOT overwrite them!
}
