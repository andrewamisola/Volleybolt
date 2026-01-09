# Debug Guide - BabylonPong

## Quick Debug Setup

### Enable Debug Mode
Add to browser console or modify index.html:
```javascript
// Show collision boxes
scene.debugLayer.show();

// Log ball state every frame
engine.runRenderLoop(() => {
    console.log(`Ball: x=${ball.position.x.toFixed(2)}, y=${ball.position.y.toFixed(2)}, z=${ball.position.z.toFixed(2)}`);
    console.log(`Vel: vx=${ballVelX.toFixed(2)}, vy=${ballVelY.toFixed(2)}, vz=${ballVelZ.toFixed(2)}`);
});
```

### Freeze Ball for Testing
```javascript
// In console:
inPlay = false;
ball.position = new BABYLON.Vector3(X, Y, Z);  // Set exact position
```

### Test Parry Window
```javascript
// Move ball to specific position near player paddle
ball.position.x = playerPaddle.position.x + 2;  // Within parry window
ball.position.z = playerPaddle.position.z;
ballVelX = -5;  // Moving toward player
inPlay = true;
```

---

## Test Scenarios

### Scenario 1: Basic Paddle Hit
**Purpose**: Verify ball bounces off paddles correctly

**Steps**:
1. Press SPACE to serve
2. Let ball reach AI paddle
3. Let ball return to player paddle
4. Move paddle to intercept

**Expected**:
- Ball reverses X direction on hit
- Ball gains slight Z deflection based on hit position
- Score doesn't change

---

### Scenario 2: Parry Mechanic
**Purpose**: Verify parry triggers correctly

**Steps**:
1. Serve ball
2. Let it return toward player
3. When ball is within ~2.5 units of paddle, press SPACE
4. Observe ball behavior

**Expected**:
- Ball shrinks (0.5x scale)
- Ball changes to blue particles
- Ball speeds up (1.8x)
- Screen flashes briefly
- Ball launches upward with increased velocity

---

### Scenario 3: Directional Parry
**Purpose**: Verify aiming works during parry

**Steps**:
1. Serve ball
2. When ball returns, hold W + press SPACE
3. Repeat with S + SPACE

**Expected**:
- W + SPACE: Ball goes toward top of screen (negative Z)
- S + SPACE: Ball goes toward bottom of screen (positive Z)
- Neutral SPACE: Ball continues roughly same Z direction

---

### Scenario 4: Bounce Over Paddle
**Purpose**: Verify ball can't score while bouncing high

**Steps**:
1. Parry the ball (to get high bounce)
2. Position so ball is mid-bounce over opponent's paddle area
3. Watch if collision triggers

**Expected**:
- Ball must be below Y=0.8 to trigger paddle collision
- If ball is bouncing high over paddle, no collision
- Ball continues past paddle and scores

---

### Scenario 5: Single Bounce Limit
**Purpose**: Verify ball only bounces once per volley

**Steps**:
1. Parry ball to get initial bounce
2. Watch ball trajectory

**Expected**:
- Ball bounces once off table after parry
- Ball does NOT bounce again (goes through table level)
- bounceRetention = 0 means no second bounce

---

### Scenario 6: AI Tracking
**Purpose**: Verify AI follows ball but is beatable

**Steps**:
1. Serve ball
2. Watch AI paddle movement
3. Try directing ball to corners with directional parry

**Expected**:
- AI tracks ball X position
- AI has slight delay (imperfection threshold of 0.3)
- AI speed (11) is slower than parried ball
- AI should miss some shots, especially aimed ones

---

## Common Issues & Debugging

### Ball Goes Through Paddle
**Check**:
1. Is `maxHitHeight` set correctly? (default 0.8)
2. Is ball Y position being checked in collision?
3. Log positions: `console.log(ball.position.y, maxHitHeight)`

### Parry Not Triggering
**Check**:
1. Is ball moving toward player? (`ballVelX < 0`)
2. Is ball within parryWindow? (default 2.5 units)
3. Is ball within paddle Z range?
4. Is canParry true? (not on cooldown)

### Controls Not Responding
**Check**:
1. Is focus on browser window?
2. Check console for errors
3. Verify event listeners are attached
4. Test with `console.log(keys)` on keydown

### Ball Stuck or Jittering
**Check**:
1. Delta time calculation
2. Multiple collision triggers per frame
3. Position clamping conflicts

---

## Debug Variables to Add

For easier debugging, consider adding these toggleable variables:
```javascript
const DEBUG = {
    showColliders: false,
    logBallState: false,
    logCollisions: false,
    slowMotion: false,
    invinciblePlayer: false
};
```

Then wrap debug code in checks:
```javascript
if (DEBUG.logBallState) {
    console.log(`Ball: ${ball.position.x}, ${ball.position.y}, ${ball.position.z}`);
}
```
