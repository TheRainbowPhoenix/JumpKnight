"""A few baked speech pages, advanced on a timer or fresh tap/Enter."""
import struct
import gint as g
from core import PW, PH


class Speech:
    def __init__(self, pak):
        self.pak = pak
        self.npc_x, self.npc_y, self.room, self.count = struct.unpack('<HHHH', pak.read('TALK_META'))
        self.x, self.y, self.w, self.h = 32, 370, 256, 64
        self.visible = self.seen = self.next = self.suppress = False
        self.page = -1
        self.timer = self.delay = 0
        self.image = None
        self.changed = False
        self.was_visible = False

    def update(self, p):
        self.changed = False
        self.was_visible = self.visible
        near = (not p.flying and p.crash < 0 and p.grounded
                and abs((p.x >> 8) + PW // 2 - self.npc_x) < 100
                and abs((p.y >> 8) + PH - self.npc_y) < 20)
        if self.visible and not near:
            self.visible = False
            self.changed = True
            self.seen = True
        elif self.visible:
            self.timer += 1
            if self.next or self.timer >= 120:
                self.page += 1
                self.timer = 0
                self.changed = True
                if self.page >= self.count:
                    self.visible = False
                    self.seen = True
                else:
                    self.image = self.pak._sprite('TALK_%d' % self.page, 256, 64)
        elif near:
            self.delay += 1
            if self.next or (not self.seen and self.delay >= 30):
                self.visible = True
                self.page = self.timer = 0
                self.image = self.pak._sprite('TALK_0', 256, 64)
                self.changed = True
        else:
            self.delay = 0
        self.next = False

    def clear(self, background, full):
        if self.was_visible and not self.visible and not full:
            g.dsubimage(self.x, self.y, background, self.x, self.y, self.w, self.h)

    def patch(self, x, y, w, h):
        left, top = max(x, self.x), max(y, self.y)
        right, bottom = min(x + w, self.x + self.w), min(y + h, self.y + self.h)
        if right > left and bottom > top:
            g.dsubimage(left, top, self.image, left - self.x, top - self.y, right - left, bottom - top)

    def draw(self, full, moved, old_x, old_y, old_w, old_h, x, y, w, h):
        if not self.visible:
            return
        if full or self.changed:
            g.dsubimage(self.x, self.y, self.image, 0, 0, self.w, self.h)
        elif moved:
            self.patch(old_x, old_y, old_w, old_h)
            self.patch(x, y, w, h)
