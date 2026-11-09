"""Integer wind and six tiny particles. No per-tick containers or trig."""
import gint as g
from core import PW, PH


class Weather:
    def __init__(self, pak, rooms):
        self.pak, self.rooms = pak, rooms
        self.settings = pak.read('WEATHER')
        self.gusts = pak.read('GUSTS')
        self.screen = -1
        self.masks = b''
        self.enabled = False
        self.clock = self.phase = 0
        self.dirty = False
        self.x = [((i * 97 + 31) % 316) for i in range(6)]
        self.y = [((i * 73 + 13) % 236) + (i // 3) * 240 for i in range(6)]
        self.old_x = self.x[:]
        self.old_y = self.y[:]
        self.active = bytearray(6)
        self.old_active = bytearray(6)
        self.room = -1

    def tick(self, p):
        screen = max(0, min(self.rooms * 2 - 1, self.rooms * 2 - 1 - (p.y >> 8) // 240))
        if screen != self.screen:
            old = self.screen
            self.masks = self.pak.read('AIR_%03d' % screen)
            self.screen = screen
            if not self.settings[screen * 4]:
                self.enabled = False
            elif p.grounded or old > screen:
                self.enabled = True
        elif p.grounded and self.settings[screen * 4]:
            self.enabled = True
        self.phase = (self.phase + 1) % 392
        self.clock += 1
        if self.clock >= 3:
            self.clock = 0
            room = (p.y >> 8) // 480
            if 0 <= room < self.rooms:
                index = (self.rooms * 2 - 2 - room * 2) * 4
                if (self.settings[index] or self.settings[index + 3]
                        or self.settings[index + 4] or self.settings[index + 7]):
                    self.dirty = True

    def marked(self, x, y, offset=0):
        # Same integer cell edges as the scaled collision atlas.
        cx = min(59, max(0, ((x + 1) * 3 - 1) // 16))
        cy = min(44, max(0, ((y + 1) * 3 - 1) // 16))
        bit = cy * 60 + cx
        return self.masks[offset + (bit >> 3)] & (1 << (bit & 7))

    def velocity(self, screen):
        index = screen * 4
        if not self.settings[index]:
            return 0
        strength = self.settings[index + 1]
        direction = self.settings[index + 2]
        if direction:
            return -strength if direction == 255 else strength
        index = self.phase * 2
        gust = self.gusts[index] | (self.gusts[index + 1] << 8)
        if gust >= 32768:
            gust -= 65536
        # Symmetric rounding avoids a persistent leftward bias near calm.
        product = gust * strength
        return (product + 128) // 256 if product >= 0 else -((-product + 128) // 256)

    def force(self, p):
        if not self.enabled or p.flying or (p.crash >= 0 and not p.ice):
            return 0
        x, y = p.x >> 8, (p.y >> 8) % 240
        left = max(0, ((x + 1) * 3 - 1) // 16)
        right = min(59, ((x + PW) * 3 - 1) // 16)
        top = max(0, ((y + 1) * 3 - 1) // 16)
        bottom = min(44, ((y + PH) * 3 - 1) // 16)
        for cy in range(top, bottom + 1):
            for cx in range(left, right + 1):
                bit = cy * 60 + cx
                if self.masks[bit >> 3] & (1 << (bit & 7)):
                    return 0
        if p.grounded and (self.marked(x, min(239, y + PH), 338)
                           or self.marked(x + PW - 1, min(239, y + PH), 338)):
            return 0
        return self.velocity(self.screen)

    def prepare(self, room, background, full):
        changed = full or self.dirty
        if not changed:
            return False
        for i in range(6):
            self.old_x[i], self.old_y[i] = self.x[i], self.y[i]
            self.old_active[i] = self.active[i] if not full else 0
            if self.old_active[i]:
                g.dsubimage(self.x[i], self.y[i], background, self.x[i], self.y[i], 3, 3)
            half = i // 3
            screen = self.rooms * 2 - 1 - room * 2 - half
            index = screen * 4
            kind = self.settings[index + 3]
            wind = self.velocity(screen)
            self.active[i] = bool(kind or self.settings[index])
            self.x[i] = (self.x[i] + (wind // 12 if wind else 1)) % 317
            self.y[i] = half * 240 + ((self.y[i] % 240 + (9 if kind == 1 else 2)) % 237)
        self.room = room
        self.dirty = False
        return True

    def draw(self, x, y, w, h, changed, secrets, speech):
        for i in range(6):
            if changed and self.old_active[i]:
                for cover in secrets.covers:
                    if cover.visible:
                        cover.patch(self.old_x[i], self.old_y[i], 3, 3)
            if self.active[i]:
                px, py = self.x[i], self.y[i]
                # Keep the king readable; particles never touch the HUD.
                if not (px < x + w and px + 3 > x and py < y + h and py + 3 > y):
                    screen = self.rooms * 2 - 1 - self.room * 2 - i // 3
                    rain = self.settings[screen * 4 + 3] == 1
                    g.drect(px, py, px if rain else px + 1, py + 2 if rain else py + 1,
                            0x9d7f if rain else 0xef7b)
            if speech.visible:
                if changed and self.old_active[i]:
                    speech.patch(self.old_x[i], self.old_y[i], 3, 3)
                if self.active[i]:
                    speech.patch(self.x[i], self.y[i], 3, 3)
