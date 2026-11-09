"""Integer-only 30 Hz simulation. No platform imports or per-tick containers.

Q8 positions are top-left. Boxes are flat (x, y, width, height, kind) pixels;
kind 0 is solid, 1 is one-way, 2..5 are triangles, 6 is solid ice.
Worlds must start without overlaps.
"""
LEFT, RIGHT, JUMP, EXIT = 1, 2, 4, 8
RECOVER = 16
Q = 256
PW, PH = 12, 17
CRASH_W, CRASH_H = 20, 10
SPLAT_TICKS = 15
# Original 30 Hz values scaled uniformly by 2/3 with the map (Q8).
AIR, GRAVITY, MAX_FALL = 1195, 171, 3413
WALK = 512
CHARGE = 18
JUMP_SPEED = 2901
# Q8 velocity in 30 Hz units, per source 60 Hz half-step (scale 2/3).
ICE_FRICTION, ICE_PUSH = 34, 68


class Player:
    def __init__(self, x, y):
        self.x = x * Q
        self.y = y * Q
        self.vx = 0
        self.vy = 0
        self.grounded = False
        self.charge = 0
        self.direction = 0
        self.previous = 0
        self.landed = False
        self.bounced = False
        self.facing = 1
        # -1: normal; >0: hard-landing lock; 0: down, awaiting recovery input.
        self.crash = -1
        self.flying = False
        self.falls = 0
        self.ice = False


def step(p, keys, boxes, width, wind=0):
    # Ground walking is controllable; airborne velocity stays committed.
    dx = (1 if keys & RIGHT else 0) - (1 if keys & LEFT else 0)
    p.landed = False
    p.bounced = False
    down = p.crash >= 0 and p.grounded
    on_ice = p.ice and p.grounded
    if down:
        p.vy = p.charge = 0
        if not on_ice:
            p.vx = 0
        if p.crash > 0:
            p.crash -= 1
        elif keys & RECOVER and not p.previous & RECOVER:
            p.crash = -1
        if not on_ice:
            p.previous = keys
            return  # Recovery never also starts charging a jump.
    if p.grounded and not down:
        if not on_ice:
            p.vx = dx * WALK
        if dx:
            p.facing = dx
        if keys & JUMP and (p.charge or not p.previous & JUMP):
            p.charge += 1
            p.direction = dx
            if dx:
                p.facing = dx
        if p.charge:
            if not on_ice:
                p.vx = 0
            if not keys & JUMP or p.charge >= CHARGE:
                p.vy = -max(342, JUMP_SPEED * p.charge // CHARGE)
                p.vx = max(-AIR, min(AIR, p.vx + p.direction * AIR)) if on_ice else p.direction * AIR
                p.charge = 0
                p.direction = 0
                p.grounded = False
    else:
        p.charge = 0
    p.previous = keys

    # Sweep each axis against rectangles: thin platforms cannot be tunnelled.
    x, y = p.x, p.y
    # Two source 60 Hz wind kicks per 30 Hz movement: the first half-step
    # uses half the new velocity increment, the second uses the whole kick.
    if on_ice and p.grounded:
        # Integrate both source half-steps: push only towards a walking
        # target when slower/opposed, move, then apply passive friction.
        # Charging and splats retain momentum and receive no steering push.
        total = 0
        target = dx * WALK if not (p.charge or down) else 0
        first_wind = wind // 2
        for half in range(2):
            if target and ((target > 0) != (p.vx > 0) or abs(target) > abs(p.vx)):
                p.vx = min(target, p.vx + ICE_PUSH) if p.vx < target else max(target, p.vx - ICE_PUSH)
            p.vx += first_wind if half == 0 else wind - first_wind
            total += p.vx
            p.vx = max(0, p.vx - ICE_FRICTION) if p.vx > 0 else min(0, p.vx + ICE_FRICTION)
        movement = total // 2 if total >= 0 else -((-total) // 2)
        target_x = x + movement
    else:
        p.vx += wind
        correction = (wind + 2) // 4 if wind >= 0 else -((-wind + 2) // 4)
        target_x = x + p.vx - correction
    nx = target_x
    i = 0
    while i < len(boxes):
        if boxes[i + 4] != 1:
            bx, by = boxes[i] * Q, boxes[i + 1] * Q
            br, bb = bx + boxes[i + 2] * Q, by + boxes[i + 3] * Q
            if y < bb and y + PH * Q > by:
                kind = boxes[i + 4]
                left, right = bx, br
                if kind == 2:
                    left = br - (min(bb, y + PH * Q) - by) * boxes[i + 2] // boxes[i + 3]
                elif kind == 3:
                    right = bx + (min(bb, y + PH * Q) - by) * boxes[i + 2] // boxes[i + 3]
                elif kind == 4:
                    right = br - (max(by, y) - by) * boxes[i + 2] // boxes[i + 3]
                elif kind == 5:
                    left = bx + (max(by, y) - by) * boxes[i + 2] // boxes[i + 3]
                if target_x > x and x + PW * Q <= left and nx + PW * Q > left:
                    nx = left - PW * Q
                elif target_x < x and x >= right and nx < right:
                    nx = right
        i += 5
    if nx < 0:
        nx = 0
    elif nx > (width - PW) * Q:
        nx = (width - PW) * Q
    if nx != target_x:
        p.vx = 0 if p.grounded else -(p.vx // 2)
        p.bounced = True
    p.x = nx

    # A small downward probe rechecks support each tick, including walk-offs.
    vy = p.vy if p.vy else GRAVITY
    ny = y + vy
    p.grounded = False
    floor_kind = 0
    floor_ice = False
    i = 0
    while i < len(boxes):
        bx, by = boxes[i] * Q, boxes[i + 1] * Q
        br, bb = bx + boxes[i + 2] * Q, by + boxes[i + 3] * Q
        if nx < br and nx + PW * Q > bx:
            kind = boxes[i + 4]
            floor, ceiling = by, bb
            if kind == 2:
                floor = bb - (min(br, nx + PW * Q) - bx) * boxes[i + 3] // boxes[i + 2]
            elif kind == 3:
                floor = by + (max(bx, nx) - bx) * boxes[i + 3] // boxes[i + 2]
            elif kind == 4:
                ceiling = bb - (max(bx, nx) - bx) * boxes[i + 3] // boxes[i + 2]
            elif kind == 5:
                ceiling = by + (min(br, nx + PW * Q) - bx) * boxes[i + 3] // boxes[i + 2]
            if vy > 0 and y + PH * Q <= floor and ny + PH * Q >= floor:
                floor_ice = (floor_ice or kind == 6) if ny == floor - PH * Q else kind == 6
                ny = floor - PH * Q
                p.grounded = True
                floor_kind = kind
            elif vy < 0 and kind != 1 and y >= ceiling and ny < ceiling:
                ny = ceiling
        i += 5
    if ny < 0:
        ny = 0
    p.y = ny
    p.ice = p.grounded and floor_ice
    if p.grounded and floor_kind in (2, 3):
        # Project onto the 45-degree tangent using integer halves. Slopes
        # never become a grounded charging surface; gravity slides the king.
        tangent = (vy - p.vx) // 2 if floor_kind == 2 else (vy + p.vx) // 2
        tangent = max(-2560, min(2560, tangent))
        p.vx = -tangent if floor_kind == 2 else tangent
        p.vy = min(MAX_FALL, tangent + GRAVITY)
        p.grounded = p.landed = False
        p.charge = 0
        return
    if p.grounded:
        p.landed = p.vy > 0
        if p.landed and vy >= MAX_FALL:
            p.falls += 1
            p.crash = SPLAT_TICKS
            p.charge = 0
            p.direction = 0
        if not p.ice:
            p.vx = 0
        elif not on_ice:
            p.vx = max(0, p.vx - ICE_FRICTION * 2) if p.vx > 0 else min(0, p.vx + ICE_FRICTION * 2)
        p.vy = 0
    elif ny != y + vy:
        p.vy = GRAVITY
    else:
        p.vy = min(vy + GRAVITY, MAX_FALL)
