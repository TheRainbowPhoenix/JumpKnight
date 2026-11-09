"""Original illusory-wall overlays with instant reveal instead of a fade loop."""
import struct
import gint as g
from core import PW, PH


class Cover:
    def __init__(self, pak, x, y, w, h, serial):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.image = pak._sprite('HIDE_%02d' % serial, w, h)
        data = pak.read('HIT_%02d' % serial)
        self.hitboxes = []
        for i in range(0, len(data), 8):
            self.hitboxes.extend(struct.unpack_from('<hhhh', data, i))
        self.visible = False
        self.changed = True

    def touches(self, px, py):
        boxes = self.hitboxes
        for i in range(0, len(boxes), 4):
            if (px < boxes[i] + boxes[i + 2] and px + PW > boxes[i]
                    and py < boxes[i + 1] + boxes[i + 3] and py + PH > boxes[i + 1]):
                return True
        return False

    def patch(self, x, y, w, h):
        left, top = max(self.x, x), max(self.y, y)
        right, bottom = min(self.x + self.w, x + w), min(self.y + self.h, y + h)
        if right > left and bottom > top:
            g.dsubimage(left, top, self.image, left - self.x, top - self.y, right - left, bottom - top)


class Secrets:
    def __init__(self, pak):
        self.pak = pak
        self.room = -1
        self.covers = []
        self.dirty = False
        self.left = self.top = self.right = self.bottom = 0

    def load(self, room):
        self.covers = []
        data = self.pak.read('SEC_%03d' % room)
        for i in range(0, len(data), 10):
            x, y, w, h, serial = struct.unpack_from('<HHHHH', data, i)
            self.covers.append(Cover(self.pak, x, y, w, h, serial))
        self.room = room

    def prepare(self, p, background, full):
        changed = False
        self.dirty = False
        px, py = p.x >> 8, (p.y >> 8) - self.room * 480
        for cover in self.covers:
            visible = not cover.touches(px, py)
            cover.changed = full or visible != cover.visible
            if cover.changed and not full:
                if not self.dirty:
                    self.left, self.top = cover.x, cover.y
                    self.right, self.bottom = cover.x + cover.w, cover.y + cover.h
                else:
                    self.left, self.top = min(self.left, cover.x), min(self.top, cover.y)
                    self.right, self.bottom = max(self.right, cover.x + cover.w), max(self.bottom, cover.y + cover.h)
                self.dirty = True
            if cover.visible and not visible and not full:
                g.dsubimage(cover.x, cover.y, background, cover.x, cover.y, cover.w, cover.h)
            cover.visible = visible
            changed |= cover.changed
        return changed

    def draw(self, moved, old_x, old_y, old_w, old_h, x, y, w, h):
        for cover in self.covers:
            if cover.visible:
                if cover.changed:
                    g.dsubimage(cover.x, cover.y, cover.image, 0, 0, cover.w, cover.h)
                else:
                    if self.dirty:
                        cover.patch(self.left, self.top, self.right - self.left, self.bottom - self.top)
                if moved:
                    cover.patch(old_x, old_y, old_w, old_h)
                    cover.patch(x, y, w, h)
