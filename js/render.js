// ============================================================
// VOLLEYBOLT - Renderer
//
// Owns the Babylon scene. Reads sim state (never writes it) and
// consumes sim events for effects. All effect animations advance by
// real frame dt - nothing assumes 60fps.
//
// Per-projectile point lights and shadow casters were removed on
// purpose: StandardMaterial only applies 4 simultaneous lights, so
// they popped visibly with several projectiles. Emissive + glow
// layer + bloom sells the effect without the light budget.
// ============================================================

import * as C from './config.js';

const B = () => window.BABYLON;

export async function initRender(canvas, { onModelsLoaded } = {}) {
    const BABYLON = B();
    const engine = new BABYLON.Engine(canvas, true);
    const scene = new BABYLON.Scene(engine);
    scene.clearColor = new BABYLON.Color4(0.02, 0.015, 0.05, 1);

    // Subtle depth fog
    scene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
    scene.fogDensity = 0.008;
    scene.fogColor = new BABYLON.Color3(0.03, 0.02, 0.07);

    // --- Camera ---
    const camera = new BABYLON.ArcRotateCamera(
        'camera', -Math.PI / 2, Math.PI / 3, 30, new BABYLON.Vector3(0, 0, 0), scene);
    camera.inputs.clear();
    const cam = {
        camera,
        baseAlpha: -Math.PI / 2,
        baseBeta: Math.PI / 3,
        baseRadius: 30,
        baseTarget: new BABYLON.Vector3(0, 0, 0),
        shake: 0,
        driftX: 0,
        flipped: false
    };

    // --- Post-processing ---
    // hdr must stay false: the HDR pipeline assumes a linear-space workflow,
    // which double-gammas StandardMaterial output and washes out the scene.
    const pipeline = new BABYLON.DefaultRenderingPipeline('default', false, scene, [camera]);
    pipeline.fxaaEnabled = true;
    pipeline.bloomEnabled = true;
    pipeline.bloomThreshold = 0.9;
    pipeline.bloomWeight = 0.12;
    pipeline.bloomKernel = 32;
    pipeline.bloomScale = 0.5;
    pipeline.imageProcessingEnabled = true;
    pipeline.imageProcessing.vignetteEnabled = true;
    pipeline.imageProcessing.vignetteWeight = 1.8;
    pipeline.imageProcessing.vignetteColor = new BABYLON.Color4(0, 0, 0, 1);

    // --- Lighting ---
    const light = new BABYLON.DirectionalLight('light', new BABYLON.Vector3(0.3, -1, 0.3), scene);
    light.intensity = 1.2;
    light.position = new BABYLON.Vector3(0, 20, -10);
    const shadowGenerator = new BABYLON.ShadowGenerator(1024, light);
    shadowGenerator.useBlurExponentialShadowMap = true;
    const ambient = new BABYLON.HemisphericLight('ambient', new BABYLON.Vector3(0, 1, 0), scene);
    ambient.intensity = 0.4;

    const glow = new BABYLON.GlowLayer('glow', scene);
    glow.intensity = 0.6;

    const flareTexture = new BABYLON.Texture('https://assets.babylonjs.com/textures/flare.png', scene);

    // --- Table / walls ---
    const tableMat = new BABYLON.StandardMaterial('tableMat', scene);
    tableMat.diffuseColor = new BABYLON.Color3(0.08, 0.1, 0.12);
    tableMat.specularColor = new BABYLON.Color3(0.2, 0.2, 0.2);
    const stageTex = new BABYLON.Texture('textures/stage_floor.png', scene, false, true,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE,
        () => {
            stageTex.uScale = 4; stageTex.vScale = 2.4;
            tableMat.diffuseTexture = stageTex;
            tableMat.diffuseColor = new BABYLON.Color3(0.7, 0.7, 0.7);
            tableMat.specularColor = new BABYLON.Color3(0.1, 0.1, 0.1);
        }, () => { /* no texture - dark color */ });

    const table = BABYLON.MeshBuilder.CreateBox('table',
        { width: C.TABLE_W, height: 0.2, depth: C.TABLE_D }, scene);
    table.position.y = -0.1;
    table.material = tableMat;
    table.receiveShadows = true;

    const wallMat = new BABYLON.StandardMaterial('wallMat', scene);
    wallMat.diffuseColor = new BABYLON.Color3(0.25, 0.25, 0.3);
    wallMat.emissiveColor = new BABYLON.Color3(0.08, 0.08, 0.1);
    for (const zSign of [-1, 1]) {
        const wall = BABYLON.MeshBuilder.CreateBox('wall' + zSign,
            { width: C.TABLE_W, height: 0.4, depth: 0.4 }, scene);
        wall.position.set(0, 0.2, zSign * C.TABLE_D / 2);
        wall.material = wallMat;
        shadowGenerator.addShadowCaster(wall);
    }

    // Center line dashes
    const lineMat = new BABYLON.StandardMaterial('lineMat', scene);
    lineMat.diffuseColor = new BABYLON.Color3(0.3, 0.3, 0.35);
    lineMat.emissiveColor = new BABYLON.Color3(0.12, 0.12, 0.15);
    for (let z = -C.TABLE_D / 2 + 0.5; z < C.TABLE_D / 2; z += 1.2) {
        const dash = BABYLON.MeshBuilder.CreateBox('dash',
            { width: 0.15, height: 0.02, depth: 0.6 }, scene);
        dash.position.set(0, 0.01, z);
        dash.material = lineMat;
    }

    // --- Arena dressing: corner torches (2 shared lights) + ambient dust ---
    const torchLights = [];
    for (const xSign of [-1, 1]) {
        const torchLight = new BABYLON.PointLight('torchLight' + xSign,
            new BABYLON.Vector3(xSign * 8.5, 2.6, 0), scene);
        torchLight.diffuse = new BABYLON.Color3(1, 0.55, 0.2);
        torchLight.intensity = 0.45;
        torchLight.range = 14;
        torchLights.push({ light: torchLight, base: 0.45, t: xSign * 3 });
        for (const zSign of [-1, 1]) {
            const post = BABYLON.MeshBuilder.CreateCylinder('torchPost', {
                height: 2.2, diameterTop: 0.12, diameterBottom: 0.2
            }, scene);
            post.position.set(xSign * 9.2, 1.1, zSign * 5.4);
            post.material = wallMat;
            const flame = BABYLON.MeshBuilder.CreateSphere('flame', { diameter: 0.28 }, scene);
            flame.position.set(xSign * 9.2, 2.35, zSign * 5.4);
            const flameMat = new BABYLON.StandardMaterial('flameMat', scene);
            flameMat.emissiveColor = new BABYLON.Color3(1, 0.6, 0.15);
            flameMat.disableLighting = true;
            flame.material = flameMat;
            const fp = new BABYLON.ParticleSystem('torchFire', 18, scene);
            fp.particleTexture = flareTexture;
            fp.emitter = flame;
            fp.minEmitBox = new BABYLON.Vector3(-0.05, 0, -0.05);
            fp.maxEmitBox = new BABYLON.Vector3(0.05, 0.1, 0.05);
            fp.color1 = new BABYLON.Color4(1, 0.8, 0.3, 1);
            fp.color2 = new BABYLON.Color4(1, 0.4, 0.05, 1);
            fp.colorDead = new BABYLON.Color4(0.4, 0.1, 0, 0);
            fp.minSize = 0.15; fp.maxSize = 0.35;
            fp.minLifeTime = 0.2; fp.maxLifeTime = 0.5;
            fp.emitRate = 16;
            fp.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
            fp.direction1 = new BABYLON.Vector3(-0.2, 1, -0.2);
            fp.direction2 = new BABYLON.Vector3(0.2, 1.8, 0.2);
            fp.gravity = new BABYLON.Vector3(0, 0.5, 0);
            fp.minEmitPower = 0.3; fp.maxEmitPower = 0.7;
            fp.start();
        }
    }

    const dust = new BABYLON.ParticleSystem('dust', 60, scene);
    dust.particleTexture = flareTexture;
    dust.emitter = new BABYLON.Vector3(0, 1.5, 0);
    dust.minEmitBox = new BABYLON.Vector3(-10, -1.5, -6);
    dust.maxEmitBox = new BABYLON.Vector3(10, 2.5, 6);
    dust.color1 = new BABYLON.Color4(0.5, 0.55, 0.8, 0.12);
    dust.color2 = new BABYLON.Color4(0.7, 0.6, 0.9, 0.08);
    dust.colorDead = new BABYLON.Color4(0.3, 0.3, 0.5, 0);
    dust.minSize = 0.04; dust.maxSize = 0.12;
    dust.minLifeTime = 4; dust.maxLifeTime = 8;
    dust.emitRate = 8;
    dust.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
    dust.direction1 = new BABYLON.Vector3(-0.1, 0.05, -0.1);
    dust.direction2 = new BABYLON.Vector3(0.1, 0.15, 0.1);
    dust.minEmitPower = 0.1; dust.maxEmitPower = 0.3;
    dust.start();

    // --- Gates ---
    const playerGateMat = new BABYLON.StandardMaterial('playerGateMat', scene);
    playerGateMat.diffuseColor = new BABYLON.Color3(0.35, 0.38, 0.5);
    playerGateMat.emissiveColor = new BABYLON.Color3(0.05, 0.08, 0.15);
    const aiGateMat = new BABYLON.StandardMaterial('aiGateMat', scene);
    aiGateMat.diffuseColor = new BABYLON.Color3(0.5, 0.32, 0.32);
    aiGateMat.emissiveColor = new BABYLON.Color3(0.15, 0.05, 0.05);
    const keystoneMat = new BABYLON.StandardMaterial('keystoneMat', scene);
    keystoneMat.diffuseColor = new BABYLON.Color3(0.45, 0.42, 0.38);
    keystoneMat.emissiveColor = new BABYLON.Color3(0.1, 0.09, 0.08);
    const gateBaseDiffuse = {
        left: playerGateMat.diffuseColor.clone(),
        right: aiGateMat.diffuseColor.clone()
    };

    const stoneTex = new BABYLON.Texture('textures/gate_stone.png', scene, false, true,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE,
        () => {
            playerGateMat.diffuseTexture = stoneTex;
            playerGateMat.diffuseColor = new BABYLON.Color3(0.6, 0.65, 0.8);
            aiGateMat.diffuseTexture = stoneTex.clone();
            aiGateMat.diffuseColor = new BABYLON.Color3(0.8, 0.6, 0.6);
            keystoneMat.diffuseTexture = stoneTex.clone();
            gateBaseDiffuse.left = playerGateMat.diffuseColor.clone();
            gateBaseDiffuse.right = aiGateMat.diffuseColor.clone();
        }, () => { /* colors only */ });

    const brickW = 1.2, brickH = 0.8, brickD = 1.8;
    const gateRows = 5, gateCols = 6;
    const archCenterCol = Math.floor(gateCols / 2);
    const isInArch = (row, col) => {
        const colDist = Math.abs(col - archCenterCol);
        if (colDist > 1.5) return false;
        if (row < 2) return colDist <= 1;
        if (row === 2) return colDist < 1;
        return false;
    };

    const bricks = { left: [], right: [] };
    const createGate = (side) => {
        const mat = side === 'left' ? playerGateMat : aiGateMat;
        const xSign = side === 'left' ? -1 : 1;
        for (let row = 0; row < gateRows; row++) {
            for (let col = 0; col < gateCols; col++) {
                if (isInArch(row, col)) continue;
                const brick = BABYLON.MeshBuilder.CreateBox(`${side}Brick_${row}_${col}`,
                    { width: brickW, height: brickH, depth: brickD }, scene);
                const offsetX = (row % 2) * (brickW * 0.25);
                const z = (col - (gateCols - 1) / 2) * brickD;
                brick.position.set(xSign * (C.GATE_X + offsetX), brickH / 2 + row * brickH, z);
                brick.originalPos = brick.position.clone();
                brick.originalZ = z;
                brick.material = mat;
                shadowGenerator.addShadowCaster(brick);
                brick.receiveShadows = true;
                bricks[side].push(brick);
            }
        }
        for (let i = -1; i <= 1; i++) {
            const keystone = BABYLON.MeshBuilder.CreateBox(`${side}Keystone_${i}`,
                { width: brickW * 0.8, height: brickH * 0.8, depth: brickD * 0.7 }, scene);
            const angle = (i + 1) * (Math.PI / 4);
            const archRadius = brickD * 0.8;
            const z = Math.sin(angle - Math.PI / 2) * archRadius * 0.5;
            const y = brickH / 2 + 2 * brickH + Math.cos(angle - Math.PI / 2) * archRadius * 0.3 + 0.3;
            keystone.position.set(xSign * C.GATE_X, y, z);
            keystone.rotation.x = i * 0.3;
            keystone.originalPos = keystone.position.clone();
            keystone.originalRot = keystone.rotation.clone();
            keystone.originalZ = z;
            keystone.material = keystoneMat;
            shadowGenerator.addShadowCaster(keystone);
            bricks[side].push(keystone);
        }
    };
    createGate('left');
    createGate('right');

    // dt-driven effect lists (replaces the old fixed-0.016 rAF loops)
    const explodingBricks = [];
    const iceShards = [];
    const impactFlashes = [];
    const charFlashes = [];
    const delayedCalls = [];   // { t, fn }

    function destroyBrickAt(side, hitZ) {
        const visible = bricks[side].filter(b => b.isVisible && !b.isDestroying);
        if (visible.length === 0) return;
        let closest = null, closestDist = Infinity;
        for (const brick of visible) {
            const dist = Math.abs(brick.originalZ - hitZ);
            if (dist < closestDist) { closestDist = dist; closest = brick; }
        }
        if (!closest) return;
        closest.isDestroying = true;
        const outward = side === 'left' ? -1 : 1;
        explodingBricks.push({
            mesh: closest, t: 0, dur: 1.2,
            velX: outward * (3 + Math.random() * 5),
            velY: 2 + Math.random() * 6,
            velZ: (Math.random() - 0.5) * 8,
            rotX: (Math.random() - 0.5) * 12,
            rotY: (Math.random() - 0.5) * 12,
            rotZ: (Math.random() - 0.5) * 12
        });
    }

    function resetBricks() {
        explodingBricks.length = 0;
        for (const side of ['left', 'right']) {
            for (const brick of bricks[side]) {
                brick.isVisible = true;
                brick.isDestroying = false;
                brick.visibility = 1;
                if (brick.originalPos) brick.position.copyFrom(brick.originalPos);
                if (brick.originalRot) brick.rotation.copyFrom(brick.originalRot);
                else brick.rotation.set(0, 0, 0);
            }
        }
    }

    function createImpactFlash(x, y, z, color, size = 1.5) {
        const flash = BABYLON.MeshBuilder.CreateSphere('impact', { diameter: size }, scene);
        flash.position.set(x, y, z);
        const mat = new BABYLON.StandardMaterial('impactMat', scene);
        mat.emissiveColor = color;
        mat.alpha = 0.8;
        mat.disableLighting = true;
        flash.material = mat;
        impactFlashes.push({ mesh: flash, mat, alpha: 0.8, scale: 1 });
    }

    // --- Wizards ---
    const wizardVisuals = { left: null, right: null };

    function makeWizardVisual(side) {
        const xSign = side === 'left' ? -1 : 1;
        const mat = new BABYLON.StandardMaterial(side + 'PaddleMat', scene);
        if (side === 'left') {
            mat.diffuseColor = new BABYLON.Color3(0.2, 0.5, 1);
            mat.emissiveColor = new BABYLON.Color3(0.15, 0.35, 0.7);
        } else {
            mat.diffuseColor = new BABYLON.Color3(1, 0.3, 0.3);
            mat.emissiveColor = new BABYLON.Color3(0.7, 0.2, 0.2);
        }
        const paddle = BABYLON.MeshBuilder.CreateBox(side + 'Paddle',
            { width: 0.4, height: 0.5, depth: 2.5 }, scene);
        paddle.position.set(xSign * C.PADDLE_X, 0.25, 0);
        paddle.material = mat;
        paddle.visibility = 0;
        shadowGenerator.addShadowCaster(paddle);

        const vis = {
            side, paddle,
            animations: {},
            current: 'idle',
            lockT: 0,
            blends: [],          // active crossfades { from, to, t }
            flashMeshes: [],
            frozenPaused: false,
            iceBlock: null,
            iceLight: null,
            modelLoaded: false
        };

        // Ice block (crystalline frozen effect)
        const iceMat = new BABYLON.StandardMaterial(side + 'IceMat', scene);
        iceMat.diffuseColor = new BABYLON.Color3(0.7, 0.85, 1);
        iceMat.emissiveColor = new BABYLON.Color3(0.2, 0.4, 0.6);
        iceMat.specularColor = new BABYLON.Color3(1, 1, 1);
        iceMat.specularPower = 128;
        iceMat.alpha = 0.5;
        iceMat.backFaceCulling = false;
        const iceInnerMat = new BABYLON.StandardMaterial(side + 'IceInnerMat', scene);
        iceInnerMat.diffuseColor = new BABYLON.Color3(0.9, 0.95, 1);
        iceInnerMat.emissiveColor = new BABYLON.Color3(0.3, 0.5, 0.7);
        iceInnerMat.alpha = 0.3;
        iceInnerMat.backFaceCulling = false;

        const iceRoot = new BABYLON.TransformNode(side + 'IceRoot', scene);
        iceRoot.parent = paddle;
        iceRoot.position.y = 1.0;
        const pieces = [
            { size: [0.8, 2.0, 0.6], pos: [0, 0, 0], rotY: Math.PI / 6, mat: iceMat },
            { size: [0.5, 1.8, 0.4], pos: [0.3, 0.1, 0.2], rotY: Math.PI / 4, rotZ: 0.1, mat: iceMat },
            { size: [0.5, 1.6, 0.35], pos: [-0.25, -0.1, -0.15], rotY: -Math.PI / 5, rotZ: -0.08, mat: iceMat },
            { size: [0.3, 0.5, 0.25], pos: [0, 1.1, 0], rotX: 0.2, rotZ: 0.15, mat: iceMat },
            { size: [0.5, 1.5, 0.4], pos: [0, 0, 0], mat: iceInnerMat }
        ];
        for (const p of pieces) {
            const m = BABYLON.MeshBuilder.CreateBox(side + 'Ice',
                { width: p.size[0], height: p.size[1], depth: p.size[2] }, scene);
            m.material = p.mat;
            m.parent = iceRoot;
            m.position.set(p.pos[0], p.pos[1], p.pos[2]);
            if (p.rotX) m.rotation.x = p.rotX;
            if (p.rotY) m.rotation.y = p.rotY;
            if (p.rotZ) m.rotation.z = p.rotZ;
        }
        iceRoot.setEnabled(false);
        vis.iceBlock = iceRoot;
        vis.iceMat = iceMat;
        return vis;
    }

    wizardVisuals.left = makeWizardVisual('left');
    wizardVisuals.right = makeWizardVisual('right');

    // Model loading (both sides load the same combined GLB)
    let modelsPending = 2;
    const modelDone = () => {
        modelsPending--;
        if (modelsPending === 0 && onModelsLoaded) onModelsLoaded();
    };

    for (const side of ['left', 'right']) {
        const vis = wizardVisuals[side];
        BABYLON.SceneLoader.ImportMesh('', 'models/', 'wizard_combined.glb', scene,
            (meshes, particleSystems, skeletons, animationGroups) => {
                const root = new BABYLON.TransformNode(side + 'WizardRoot', scene);
                meshes.forEach(m => {
                    if (!m.parent || m.parent === scene) m.parent = root;
                    if (m.material) m.material.backFaceCulling = true;
                    shadowGenerator.addShadowCaster(m);
                });
                root.parent = vis.paddle;
                root.position.set(0, -0.25, 0);
                root.rotation.y = side === 'left' ? Math.PI / 2 : -Math.PI / 2;
                vis.paddle.visibility = 0;
                animationGroups.forEach(anim => {
                    vis.animations[anim.name.toLowerCase()] = anim;
                    anim.stop();
                });
                if (vis.animations['idle']) vis.animations['idle'].play(true);
                vis.flashMeshes = meshes.filter(m => m.material);
                vis.modelLoaded = true;
                modelDone();
            },
            null,
            () => {
                // No model - show the plain paddle
                vis.paddle.visibility = 1;
                modelDone();
            });
    }

    // --- Animation controller (dt-based crossfade) ---
    const BLEND_TIME = 0.2;

    function playAnim(vis, name, { loop = true, lockMs = 0, speed = 1.0, startFrame = 0 } = {}) {
        const key = name.toLowerCase();
        const toAnim = vis.animations[key];
        if (!toAnim || vis.current === key) return;
        const fromAnim = vis.animations[vis.current];
        toAnim.speedRatio = speed;
        toAnim.setWeightForAllAnimatables(0);
        if (startFrame > 0) toAnim.start(loop, speed, startFrame);
        else toAnim.play(loop);
        vis.blends = vis.blends.filter(b => b.to !== toAnim); // dedupe
        vis.blends.push({ from: fromAnim, to: toAnim, t: 0 });
        vis.current = key;
        if (lockMs > 0) vis.lockT = lockMs / 1000;
    }

    function updateAnims(vis, dt) {
        if (vis.lockT > 0) vis.lockT -= dt;
        for (let i = vis.blends.length - 1; i >= 0; i--) {
            const b = vis.blends[i];
            b.t += dt / BLEND_TIME;
            if (b.t >= 1) {
                if (b.from) { b.from.stop(); b.from.setWeightForAllAnimatables(1); }
                b.to.setWeightForAllAnimatables(1);
                vis.blends.splice(i, 1);
            } else {
                if (b.from) b.from.setWeightForAllAnimatables(1 - b.t);
                b.to.setWeightForAllAnimatables(b.t);
            }
        }
    }

    function freezeAnims(vis) {
        Object.values(vis.animations).forEach(a => a && a.pause());
        vis.frozenPaused = true;
    }
    function unfreezeAnims(vis) {
        const current = vis.animations[vis.current];
        if (current) current.play(true);
        vis.frozenPaused = false;
    }

    function flashCharacter(vis, isParry) {
        if (vis.flashMeshes.length === 0) return;
        const isLeft = vis.side === 'left';
        const color = isParry
            ? (isLeft ? new BABYLON.Color3(0.5, 0.8, 1) : new BABYLON.Color3(1, 0.6, 0.8))
            : (isLeft ? new BABYLON.Color3(0.3, 0.5, 0.8) : new BABYLON.Color3(0.8, 0.4, 0.4));
        const intensity = isParry ? 0.5 : 0.1;
        const originals = vis.flashMeshes.map(m => m.material ? m.material.emissiveColor.clone() : null);
        vis.flashMeshes.forEach(m => {
            if (m.material) m.material.emissiveColor = color.scale(intensity);
        });
        charFlashes.push({ meshes: vis.flashMeshes, originals, color: color.scale(intensity), t: -0.05 });
    }

    function shatterIce(vis) {
        const worldPos = vis.paddle.position.clone();
        worldPos.y += 1.0;
        for (let i = 0; i < 6; i++) {
            const size = 0.1 + Math.random() * 0.15;
            const shard = BABYLON.MeshBuilder.CreateBox('iceShard', {
                width: size, height: size * (1 + Math.random()), depth: size * 0.7
            }, scene);
            shard.material = vis.iceMat;
            shard.position = worldPos.clone();
            shard.position.x += (Math.random() - 0.5) * 0.5;
            shard.position.y += (Math.random() - 0.5) * 0.8;
            shard.position.z += (Math.random() - 0.5) * 0.5;
            shard.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
            iceShards.push({
                mesh: shard, t: 0, dur: 0.6,
                velX: (Math.random() - 0.5) * 6,
                velY: 3 + Math.random() * 4,
                velZ: (Math.random() - 0.5) * 6,
                rotX: (Math.random() - 0.5) * 15,
                rotY: (Math.random() - 0.5) * 15,
                rotZ: (Math.random() - 0.5) * 15
            });
        }
    }

    // --- Projectile visuals ---
    const projVisuals = new Map(); // id -> visual

    const fireballCoreMat = new BABYLON.StandardMaterial('fireballCoreMat', scene);
    fireballCoreMat.emissiveColor = new BABYLON.Color3(1, 0.8, 0.3);
    fireballCoreMat.diffuseColor = new BABYLON.Color3(1, 0.5, 0.1);
    fireballCoreMat.specularColor = new BABYLON.Color3(0, 0, 0);
    const frostCoreMat = new BABYLON.StandardMaterial('frostCoreMat', scene);
    frostCoreMat.diffuseColor = new BABYLON.Color3(0.7, 0.9, 1);
    frostCoreMat.emissiveColor = new BABYLON.Color3(0.4, 0.7, 0.95);
    frostCoreMat.specularColor = new BABYLON.Color3(1, 1, 1);
    frostCoreMat.specularPower = 64;
    const lightningCoreMat = new BABYLON.StandardMaterial('lightningCoreMat', scene);
    lightningCoreMat.emissiveColor = new BABYLON.Color3(1, 1, 0.6);
    lightningCoreMat.diffuseColor = new BABYLON.Color3(1, 1, 0.4);
    lightningCoreMat.specularColor = new BABYLON.Color3(0, 0, 0);

    function addParticles(emitter, cfg) {
        const ps = new BABYLON.ParticleSystem('proj', cfg.count, scene);
        ps.particleTexture = flareTexture;
        ps.emitter = emitter;
        ps.minEmitBox = new BABYLON.Vector3(-cfg.box, -cfg.box, -cfg.box);
        ps.maxEmitBox = new BABYLON.Vector3(cfg.box, cfg.box, cfg.box);
        ps.color1 = new BABYLON.Color4(...cfg.c1);
        ps.color2 = new BABYLON.Color4(...cfg.c2);
        ps.colorDead = new BABYLON.Color4(...cfg.cDead);
        ps.minSize = cfg.size[0]; ps.maxSize = cfg.size[1];
        ps.minLifeTime = cfg.life[0]; ps.maxLifeTime = cfg.life[1];
        ps.emitRate = cfg.rate;
        ps.blendMode = BABYLON.ParticleSystem.BLENDMODE_ADD;
        ps.direction1 = new BABYLON.Vector3(...(cfg.dir1 || [-1, -0.5, -1]));
        ps.direction2 = new BABYLON.Vector3(...(cfg.dir2 || [1, 1, 1]));
        ps.gravity = new BABYLON.Vector3(...(cfg.grav || [0, 0, 0]));
        ps.minEmitPower = cfg.power[0]; ps.maxEmitPower = cfg.power[1];
        ps.start();
        return ps;
    }

    function createProjVisual(proj) {
        const vis = { type: proj.type, particles: [] };
        const vDir = Math.sign(proj.velX);

        if (proj.type === 'frostbolt') {
            vis.mesh = BABYLON.MeshBuilder.CreateIcoSphere('frostbolt' + proj.id,
                { radius: 0.2, subdivisions: 1 }, scene);
            vis.mesh.material = frostCoreMat;
            vis.glow = BABYLON.MeshBuilder.CreateSphere('frostGlow' + proj.id, { diameter: 0.7 }, scene);
            vis.glowMat = new BABYLON.StandardMaterial('fgm' + proj.id, scene);
            vis.glowMat.emissiveColor = new BABYLON.Color3(0.3, 0.6, 0.9);
            vis.glowMat.alpha = 0.25;
            vis.glowMat.backFaceCulling = false;
            vis.trailColor = new BABYLON.Color3(0.4, 0.7, 1);
            vis.particles.push(addParticles(vis.mesh, {
                count: 60, box: 0.05, rate: 60,
                c1: [0.9, 0.95, 1, 1], c2: [0.5, 0.8, 1, 1], cDead: [0.3, 0.5, 0.7, 0],
                size: [0.08, 0.2], life: [0.1, 0.2], power: [0.8, 1.5]
            }));
            vis.particles.push(addParticles(vis.mesh, {
                count: 40, box: 0.1, rate: 40,
                c1: [0.6, 0.8, 1, 0.6], c2: [0.4, 0.6, 0.9, 0.4], cDead: [0.2, 0.3, 0.5, 0],
                size: [0.25, 0.5], life: [0.2, 0.4], power: [0.5, 1.5],
                dir1: [-vDir * 1.5, -0.3, -0.5], dir2: [-vDir * 3, 0.3, 0.5],
                grav: [-vDir * 2, -0.5, 0]
            }));
        } else if (proj.type === 'lightning') {
            vis.mesh = BABYLON.MeshBuilder.CreateSphere('lightning' + proj.id, { diameter: 0.3 }, scene);
            vis.mesh.material = lightningCoreMat;
            vis.glow = BABYLON.MeshBuilder.CreateSphere('lightGlow' + proj.id, { diameter: 0.6 }, scene);
            vis.glowMat = new BABYLON.StandardMaterial('lgm' + proj.id, scene);
            vis.glowMat.emissiveColor = new BABYLON.Color3(0.9, 0.9, 0.3);
            vis.glowMat.alpha = 0.3;
            vis.glowMat.backFaceCulling = false;
            vis.trailColor = new BABYLON.Color3(1, 1, 0.4);
            vis.jitter = true;
            vis.particles.push(addParticles(vis.mesh, {
                count: 40, box: 0.08, rate: 50,
                c1: [1, 1, 0.8, 1], c2: [1, 0.95, 0.4, 1], cDead: [0.6, 0.6, 0.1, 0],
                size: [0.05, 0.18], life: [0.05, 0.15], power: [1.5, 3]
            }));
        } else {
            // fireball
            vis.mesh = BABYLON.MeshBuilder.CreateSphere('fireball' + proj.id, { diameter: 0.45 }, scene);
            vis.mesh.material = fireballCoreMat;
            vis.glow = BABYLON.MeshBuilder.CreateSphere('fireGlow' + proj.id, { diameter: 0.8 }, scene);
            vis.glowMat = new BABYLON.StandardMaterial('ggm' + proj.id, scene);
            vis.glowMat.emissiveColor = new BABYLON.Color3(1, 0.4, 0.05);
            vis.glowMat.alpha = 0.3;
            vis.glowMat.backFaceCulling = false;
            vis.trailColor = new BABYLON.Color3(1, 0.3, 0.05);
            vis.particles.push(addParticles(vis.mesh, {
                count: 80, box: 0.05, rate: 80,
                c1: [1, 0.9, 0.5, 1], c2: [1, 0.5, 0.1, 1], cDead: [1, 0.2, 0, 0],
                size: [0.2, 0.5], life: [0.05, 0.15], power: [1, 2]
            }));
            vis.particles.push(addParticles(vis.mesh, {
                count: 50, box: 0.15, rate: 50,
                c1: [1, 0.4, 0.1, 0.8], c2: [0.8, 0.2, 0.05, 0.6], cDead: [0.3, 0.1, 0, 0],
                size: [0.3, 0.6], life: [0.15, 0.35], power: [1, 2.5],
                dir1: [-vDir * 2, -0.5, -1], dir2: [-vDir * 4, 0.5, 1],
                grav: [-vDir * 3, 1, 0]
            }));
        }

        vis.mesh.position.set(proj.x, proj.y, proj.z);
        vis.mesh.rotationQuaternion = BABYLON.Quaternion.Identity();
        if (vis.glow) {
            vis.glow.material = vis.glowMat;
            vis.glow.parent = vis.mesh;
        }
        vis.trail = new BABYLON.TrailMesh('trail' + proj.id, vis.mesh, scene,
            proj.type === 'fireball' ? 0.25 : 0.18, proj.type === 'fireball' ? 30 : 25, true);
        vis.trailMat = new BABYLON.StandardMaterial('tm' + proj.id, scene);
        vis.trailMat.emissiveColor = vis.trailColor;
        vis.trailMat.diffuseColor = new BABYLON.Color3(0, 0, 0);
        vis.trailMat.alpha = proj.type === 'fireball' ? 0.6 : 0.5;
        vis.trailMat.backFaceCulling = false;
        vis.trail.material = vis.trailMat;

        projVisuals.set(proj.id, vis);
        return vis;
    }

    function destroyProjVisual(id) {
        const vis = projVisuals.get(id);
        if (!vis) return;
        projVisuals.delete(id);
        // dispose(false): the flare texture is shared
        for (const ps of vis.particles) ps.dispose(false);
        if (vis.trail) vis.trail.dispose();
        if (vis.trailMat) vis.trailMat.dispose();
        if (vis.glow) vis.glow.dispose();
        if (vis.glowMat) vis.glowMat.dispose();
        if (vis.mesh) vis.mesh.dispose();
    }

    // Volley tier: longer particle lifetimes at higher tiers
    function updateProjTier(id, volley) {
        const vis = projVisuals.get(id);
        if (!vis || vis.particles.length === 0) return;
        const core = vis.particles[0];
        const tier = volley >= 3 ? 3 : (volley >= 1 ? 2 : 1);
        core.minLifeTime = 0.05 + tier * 0.05;
        core.maxLifeTime = 0.15 + tier * 0.1;
    }

    // --- Per-frame effect updates ---
    scene.onBeforeRenderObservable.add(() => {
        const dt = Math.min(engine.getDeltaTime() / 1000, 0.1);

        // Exploding bricks
        for (let i = explodingBricks.length - 1; i >= 0; i--) {
            const b = explodingBricks[i];
            b.t += dt;
            const progress = b.t / b.dur;
            if (progress < 1) {
                b.velY -= 15 * dt;
                b.mesh.position.x += b.velX * dt;
                b.mesh.position.y += b.velY * dt;
                b.mesh.position.z += b.velZ * dt;
                b.mesh.rotation.x += b.rotX * dt;
                b.mesh.rotation.y += b.rotY * dt;
                b.mesh.rotation.z += b.rotZ * dt;
                if (progress > 0.5) b.mesh.visibility = 1 - (progress - 0.5) / 0.5;
            } else {
                b.mesh.isVisible = false;
                b.mesh.visibility = 1;
                explodingBricks.splice(i, 1);
            }
        }

        // Ice shards
        for (let i = iceShards.length - 1; i >= 0; i--) {
            const s = iceShards[i];
            s.t += dt;
            const progress = s.t / s.dur;
            if (progress < 1) {
                s.velY -= 20 * dt;
                s.mesh.position.x += s.velX * dt;
                s.mesh.position.y += s.velY * dt;
                s.mesh.position.z += s.velZ * dt;
                s.mesh.rotation.x += s.rotX * dt;
                s.mesh.rotation.y += s.rotY * dt;
                s.mesh.rotation.z += s.rotZ * dt;
                if (progress > 0.4) s.mesh.visibility = 1 - (progress - 0.4) / 0.6;
            } else {
                s.mesh.dispose();
                iceShards.splice(i, 1);
            }
        }

        // Impact flashes
        for (let i = impactFlashes.length - 1; i >= 0; i--) {
            const f = impactFlashes[i];
            f.alpha -= 4.8 * dt;
            f.scale += 9 * dt;
            f.mat.alpha = Math.max(0, f.alpha);
            f.mesh.scaling.setAll(f.scale);
            if (f.alpha <= 0) {
                f.mesh.dispose();
                f.mat.dispose();
                impactFlashes.splice(i, 1);
            }
        }

        // Character emissive flashes (hold briefly, then fade)
        for (let i = charFlashes.length - 1; i >= 0; i--) {
            const f = charFlashes[i];
            f.t += dt;
            if (f.t < 0) continue;
            const progress = Math.min(1, f.t / 0.3);
            f.meshes.forEach((m, idx) => {
                if (m.material && f.originals[idx]) {
                    m.material.emissiveColor = BABYLON.Color3.Lerp(f.color, f.originals[idx], progress);
                }
            });
            if (progress >= 1) charFlashes.splice(i, 1);
        }

        // Delayed calls (brick destruction stagger)
        for (let i = delayedCalls.length - 1; i >= 0; i--) {
            delayedCalls[i].t -= dt;
            if (delayedCalls[i].t <= 0) {
                const fn = delayedCalls[i].fn;
                delayedCalls.splice(i, 1);
                fn();
            }
        }

        // Animation controllers
        updateAnims(wizardVisuals.left, dt);
        updateAnims(wizardVisuals.right, dt);

        // Torch flicker
        for (const t of torchLights) {
            t.t += dt;
            t.light.intensity = t.base + Math.sin(t.t * 9) * 0.08 + Math.random() * 0.05;
        }
    });

    // ---------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------
    const lerp = (a, b, t) => a + (b - a) * t;

    function syncFromSim(sim, alpha) {
        for (const side of ['left', 'right']) {
            const w = sim.wizards[side];
            const vis = wizardVisuals[side];
            vis.paddle.position.z = lerp(w.prevZ, w.z, alpha);

            // Ice block visual state
            if (w.freezeT > 0) {
                if (!vis.iceBlock.isEnabled()) vis.iceBlock.setEnabled(true);
                vis.iceBlock.rotation.y = Math.sin(w.freezeT * 3) * 0.08;
            } else if (vis.iceBlock.isEnabled()) {
                vis.iceBlock.setEnabled(false);
            }

            // Movement / idle animations (skip while locked, frozen, or casting)
            if (vis.lockT <= 0 && !vis.frozenPaused) {
                const move = w.lastMove;
                const atTop = w.z >= C.PADDLE_BOUND - 0.001;
                const atBottom = w.z <= -C.PADDLE_BOUND + 0.001;
                const canMove = !(move > 0 && atTop) && !(move < 0 && atBottom);
                if (move > 0 && canMove) playAnim(vis, 'left');
                else if (move < 0 && canMove) playAnim(vis, 'right');
                else if (!w.casting) playAnim(vis, 'idle');
            }
        }

        // Projectiles
        for (const proj of sim.projectiles) {
            let vis = projVisuals.get(proj.id);
            if (!vis) vis = createProjVisual(proj);
            let x = lerp(proj.prevX, proj.x, alpha);
            let z = lerp(proj.prevZ, proj.z, alpha);
            const y = lerp(proj.prevY, proj.y, alpha);
            if (vis.jitter) {
                x += (Math.random() - 0.5) * 0.12;
                z += (Math.random() - 0.5) * 0.12;
            }
            vis.mesh.position.set(x, y, z);

            // Type-specific idle animation
            if (vis.type === 'frostbolt') {
                const rotation = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.Y, proj.time * 3);
                const tilt = BABYLON.Quaternion.RotationAxis(BABYLON.Axis.X, Math.sin(proj.time * 2) * 0.3);
                vis.mesh.rotationQuaternion = rotation.multiply(tilt);
                if (vis.glowMat) {
                    vis.glowMat.alpha = 0.2 + Math.sin(proj.time * 10) * 0.08;
                    vis.glow.scaling.setAll(1 + Math.sin(proj.time * 8) * 0.08);
                }
            } else if (vis.type === 'fireball') {
                if (vis.glowMat) {
                    vis.glowMat.alpha = 0.25 + Math.sin(proj.time * 20) * 0.1;
                    vis.glow.scaling.setAll(1 + Math.sin(proj.time * 15) * 0.1);
                }
            } else if (vis.type === 'lightning' && vis.glowMat) {
                vis.glowMat.alpha = 0.2 + Math.random() * 0.2;
            }
        }
        // Remove visuals for projectiles that no longer exist (safety net;
        // destroy events normally handle this)
        if (projVisuals.size > sim.projectiles.length) {
            const alive = new Set(sim.projectiles.map(p => p.id));
            for (const id of [...projVisuals.keys()]) {
                if (!alive.has(id)) destroyProjVisual(id);
            }
        }

        // Gate damage tint
        for (const side of ['left', 'right']) {
            const pct = sim.gateHP[side] / C.MAX_GATE_HP;
            const mat = side === 'left' ? playerGateMat : aiGateMat;
            const base = gateBaseDiffuse[side];
            const dim = 0.5 + 0.5 * pct;
            mat.diffuseColor.set(base.r * dim, base.g * dim, base.b * dim);
        }

        // Camera: shake decay, drift toward action, push-in when a gate is low
        cam.shake *= Math.exp(-6 * (engine.getDeltaTime() / 1000));
        let actionX = 0;
        if (sim.projectiles.length > 0) {
            for (const p of sim.projectiles) actionX += p.x;
            actionX /= sim.projectiles.length;
        }
        cam.driftX = lerp(cam.driftX, Math.max(-1.5, Math.min(1.5, actionX * 0.25)), 0.03);
        const minPct = Math.min(sim.gateHP.left, sim.gateHP.right) / C.MAX_GATE_HP;
        const targetRadius = cam.baseRadius - (1 - minPct) * 2.5;
        camera.radius = lerp(camera.radius, targetRadius, 0.02);
        camera.target.x = cam.driftX + (Math.random() - 0.5) * cam.shake;
        camera.target.y = (Math.random() - 0.5) * cam.shake * 0.6;
        camera.target.z = (Math.random() - 0.5) * cam.shake;
        camera.alpha = cam.baseAlpha + (cam.flipped ? Math.PI : 0);
    }

    function handleEvents(events, sim) {
        for (const e of events) {
            switch (e.type) {
                case 'spawn':
                    createProjVisual(e.proj);
                    break;
                case 'destroy':
                    destroyProjVisual(e.id);
                    break;
                case 'block': {
                    flashCharacter(wizardVisuals[e.side], false);
                    updateProjTier(e.id, e.volley);
                    break;
                }
                case 'parryAttempt': {
                    const vis = wizardVisuals[e.side];
                    playAnim(vis, 'parry', { loop: false, lockMs: 500, speed: 3.0, startFrame: 20 });
                    break;
                }
                case 'parry': {
                    flashCharacter(wizardVisuals[e.side], true);
                    const color = e.side === 'left'
                        ? new BABYLON.Color3(0.5, 0.8, 1) : new BABYLON.Color3(1, 0.3, 0.6);
                    createImpactFlash(e.x, C.TABLE_Y, e.z, color, 2.0);
                    break;
                }
                case 'castStart':
                    playAnim(wizardVisuals[e.side], 'charging');
                    break;
                case 'castCancel':
                    playAnim(wizardVisuals[e.side], 'idle');
                    break;
                case 'castComplete':
                case 'castInstant':
                    playAnim(wizardVisuals[e.side], 'cast', { loop: false, lockMs: 470, speed: 1.5 });
                    break;
                case 'freeze': {
                    freezeAnims(wizardVisuals[e.side]);
                    createImpactFlash(e.x, C.TABLE_Y, e.z, new BABYLON.Color3(0.5, 0.8, 1), 2.0);
                    break;
                }
                case 'unfreeze': {
                    const vis = wizardVisuals[e.side];
                    shatterIce(vis);
                    unfreezeAnims(vis);
                    break;
                }
                case 'gateHit': {
                    const gateX = e.side === 'left' ? -C.GATE_X : C.GATE_X;
                    const color = e.projType === 'lightning'
                        ? new BABYLON.Color3(1, 1, 0.4) : new BABYLON.Color3(1, 0.7, 0.2);
                    createImpactFlash(gateX, 1, e.z, color, 1.5 + e.damage * 0.5);
                    cam.shake = Math.min(0.6, 0.15 + e.damage * 0.08);
                    for (let i = 0; i < e.damage; i++) {
                        const z = e.z;
                        delayedCalls.push({
                            t: i * 0.08,
                            fn: () => destroyBrickAt(e.side, z + (Math.random() - 0.5) * 2)
                        });
                    }
                    break;
                }
                case 'gateFizzle': {
                    const gateX = e.side === 'left' ? -C.GATE_X : C.GATE_X;
                    createImpactFlash(gateX, 1, e.z, new BABYLON.Color3(0.5, 0.8, 1), 1.0);
                    break;
                }
                case 'roundReset':
                case 'matchReset': {
                    resetBricks();
                    for (const side of ['left', 'right']) {
                        const vis = wizardVisuals[side];
                        vis.iceBlock.setEnabled(false);
                        if (vis.frozenPaused) unfreezeAnims(vis);
                        playAnim(vis, 'idle');
                    }
                    break;
                }
                default:
                    break;
            }
        }
    }

    // Project a world position to screen coords (for damage numbers)
    function projectToScreen(x, y, z) {
        const pos = BABYLON.Vector3.Project(
            new BABYLON.Vector3(x, y, z),
            BABYLON.Matrix.Identity(),
            scene.getTransformMatrix(),
            camera.viewport.toGlobal(engine.getRenderWidth(), engine.getRenderHeight()));
        return { x: pos.x, y: pos.y };
    }

    function setViewFlipped(flipped) {
        cam.flipped = flipped;
    }

    engine.runRenderLoop(() => scene.render());
    window.addEventListener('resize', () => engine.resize());

    return {
        engine, scene,
        syncFromSim,
        handleEvents,
        projectToScreen,
        setViewFlipped,
        onFrame: (fn) => scene.onBeforeRenderObservable.add(fn)
    };
}
