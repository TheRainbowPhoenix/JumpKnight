"""Windows pygame debug controls. Never imported on the calculator."""
from collections import deque
from core import PW, PH, JUMP


class Desktop:
    def __init__(self, g):
        self.g = g
        self.pg = g.pygame
        previous = getattr(g, '_tinyking_desktop', None)
        self.original_poll = previous.original_poll if previous else g.pollevent
        self.original_get = previous.original_get if previous else self.pg.event.get
        self.pending = deque()
        self.flying = False
        self.held = False
        self.fly_key = None
        g.pollevent = self.poll
        g._tinyking_desktop = self

    def events(self, *args, **kwargs):
        pg = self.pg
        for ev in self.original_get(*args, **kwargs):
            is_key = ev.type in (pg.KEYDOWN, pg.KEYUP)
            special = is_key and (getattr(ev, 'unicode', '') == '\u00b2'
                      or getattr(ev, 'scancode', -1) == 53
                      or ev.key in (pg.K_BACKQUOTE, 178) or ev.key == self.fly_key)
            if special:
                if ev.type == pg.KEYDOWN:
                    if not self.held:
                        self.flying = not self.flying
                    self.held = True
                    self.fly_key = ev.key
                else:
                    self.held = False
                continue
            self.pending.append(ev)
        # The old simulator returns after one event. Feed one at a time so
        # unrelated queued key/touch events are preserved instead of dropped.
        return [self.pending.popleft()] if self.pending else []

    def poll(self):
        self.pg.event.get = self.events
        try:
            return self.original_poll()
        finally:
            self.pg.event.get = self.original_get

    def step(self, p, world, keys):
        g = self.g
        if p.flying and not self.flying:
            world.update(p.y)
            boxes = world.boxes
            for i in range(0, len(boxes), 5):
                if (p.x < (boxes[i] + boxes[i + 2]) * 256 and p.x + PW * 256 > boxes[i] * 256
                        and p.y < (boxes[i + 1] + boxes[i + 3]) * 256
                        and p.y + PH * 256 > boxes[i + 1] * 256):
                    self.flying = True
                    print('Fly: move clear of solid terrain before switching noclip off.')
                    break
        if p.flying != self.flying:
            p.flying = self.flying
            p.vx = p.vy = p.charge = 0
            p.grounded = False
            p.crash = -1
            p.previous = keys | JUMP
            self.pg.display.set_caption('Tinyking - FLY / NOCLIP (\u00b2 toggles)' if p.flying else 'Tinyking')
        if not p.flying:
            return False
        speed = (24 if g.keydown(g.KEY_SHIFT) else 8) * 256
        dx = int(g.keydown(g.KEY_RIGHT) or g.keydown(g.KEY_9)) - int(g.keydown(g.KEY_LEFT) or g.keydown(g.KEY_7))
        dy = int(g.keydown(g.KEY_DOWN)) - int(g.keydown(g.KEY_UP))
        p.x = max(0, min((world.width - PW) * 256, p.x + dx * speed))
        p.y = max(0, min((world.height - PH) * 256, p.y + dy * speed))
        if dx:
            p.facing = dx
        p.vx = p.vy = p.charge = 0
        p.crash = -1
        p.landed = p.bounced = p.grounded = False
        return True
