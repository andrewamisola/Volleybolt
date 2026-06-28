// ============================================================
// VOLLEYBOLT - Online multiplayer (PeerJS, input-delay lockstep)
//
// Both clients run the same deterministic sim. Each tick T, a player
// schedules their local input for tick T + INPUT_DELAY and sends it;
// the sim only advances past a tick once both sides' inputs for it
// are known. Host plays 'left', joiner plays 'right'.
// ============================================================

import { INPUT_DELAY_TICKS } from './config.js';
import { EMPTY_INPUT } from './sim.js';

const ROOM_PREFIX = 'volleybolt-';

function randomCode() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 5; i++) code += chars[Math.floor(Math.random() * chars.length)];
    return code;
}

export function createLockstep() {
    const local = new Map();   // tick -> input frame
    const remote = new Map();
    let scheduledThrough = -1;

    // Pre-fill the first delay window with empty inputs on both sides
    for (let t = 0; t < INPUT_DELAY_TICKS; t++) {
        local.set(t, { ...EMPTY_INPUT });
        remote.set(t, { ...EMPTY_INPUT });
        scheduledThrough = t;
    }

    return {
        inputDelay: INPUT_DELAY_TICKS,
        scheduledThrough: () => scheduledThrough,
        // Schedule local input for an exact tick. Returns the list of
        // {tick, frame} entries that must be sent to the remote (gaps are
        // filled with empty inputs so neither side can deadlock).
        scheduleLocal(tick, frame) {
            if (tick <= scheduledThrough) return [];
            const toSend = [];
            for (let t = scheduledThrough + 1; t < tick; t++) {
                const filler = { ...EMPTY_INPUT };
                local.set(t, filler);
                toSend.push({ tick: t, frame: filler });
            }
            local.set(tick, frame);
            toSend.push({ tick, frame });
            scheduledThrough = tick;
            return toSend;
        },
        addRemote(tick, frame) {
            remote.set(tick, frame);
        },
        canAdvance(tick) {
            return local.has(tick) && remote.has(tick);
        },
        inputsFor(tick) {
            return { local: local.get(tick) || EMPTY_INPUT, remote: remote.get(tick) || EMPTY_INPUT };
        },
        prune(beforeTick) {
            for (const t of local.keys()) if (t < beforeTick) local.delete(t);
            for (const t of remote.keys()) if (t < beforeTick) remote.delete(t);
        }
    };
}

// ---------------------------------------------------------------
// Connection
// callbacks: { onOpen(code), onConnected(), onStart(seed), onInput(tick, frame),
//              onClose(), onError(msg) }
// ---------------------------------------------------------------
export function host(callbacks) {
    if (typeof window.Peer === 'undefined') {
        callbacks.onError('PeerJS failed to load (offline?)');
        return null;
    }
    const code = randomCode();
    const peer = new window.Peer(ROOM_PREFIX + code);
    const session = makeSession(peer, callbacks, true);

    peer.on('open', () => callbacks.onOpen(code));
    peer.on('error', (err) => callbacks.onError(describePeerError(err)));
    peer.on('connection', (conn) => {
        if (session.conn) { conn.close(); return; } // one opponent only
        session.attach(conn);
    });
    return session;
}

export function join(code, callbacks) {
    if (typeof window.Peer === 'undefined') {
        callbacks.onError('PeerJS failed to load (offline?)');
        return null;
    }
    const peer = new window.Peer();
    const session = makeSession(peer, callbacks, false);

    peer.on('open', () => {
        const conn = peer.connect(ROOM_PREFIX + code.toUpperCase().trim(), { reliable: true });
        session.attach(conn);
    });
    peer.on('error', (err) => callbacks.onError(describePeerError(err)));
    return session;
}

function makeSession(peer, callbacks, isHost) {
    const session = {
        peer,
        conn: null,
        isHost,
        localSide: isHost ? 'left' : 'right',
        remoteSide: isHost ? 'right' : 'left',
        connected: false,
        attach(conn) {
            session.conn = conn;
            conn.on('open', () => {
                session.connected = true;
                callbacks.onConnected();
                if (isHost) {
                    const seed = (Math.random() * 0x7FFFFFFF) | 0;
                    session.seed = seed;
                    conn.send({ t: 'start', seed });
                    callbacks.onStart(seed);
                }
            });
            conn.on('data', (msg) => {
                if (!msg || typeof msg !== 'object') return;
                if (msg.t === 'start' && !isHost) {
                    session.seed = msg.seed;
                    callbacks.onStart(msg.seed);
                } else if (msg.t === 'in') {
                    callbacks.onInput(msg.tick, msg.f);
                }
            });
            conn.on('close', () => {
                session.connected = false;
                callbacks.onClose();
            });
            conn.on('error', (err) => callbacks.onError(String(err)));
        },
        sendInput(tick, frame) {
            if (session.conn && session.connected) {
                session.conn.send({ t: 'in', tick, f: frame });
            }
        },
        destroy() {
            try { if (session.conn) session.conn.close(); } catch (e) { /* noop */ }
            try { peer.destroy(); } catch (e) { /* noop */ }
        }
    };
    return session;
}

function describePeerError(err) {
    const type = err && err.type;
    switch (type) {
        case 'peer-unavailable': return 'Room not found - check the code';
        case 'unavailable-id': return 'Room code collision - try hosting again';
        case 'network': return 'Cannot reach the signaling server';
        case 'browser-incompatible': return 'Browser does not support WebRTC';
        default: return 'Connection error: ' + (type || err);
    }
}
