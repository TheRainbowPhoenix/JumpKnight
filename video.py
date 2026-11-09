"""Small gint adapter. World simulation remains independent of this module."""
import gint as g
from core import PW, PH, CRASH_W, CRASH_H
from touch import Touch
from hud import Hud
from speech import Speech
from hidden_walls import Secrets
try:
    from micropython import const
    import sys
    # The pygame simulator injects a dummy micropython module too.
    _MICROPYTHON = 'MicroPython' in sys.version
except ImportError:
    _MICROPYTHON = False


class Video:
    def __init__(self, pak=None):
        self.pak = pak
        self.background = None
        self.king = pak.sprite() if pak else None
        self.splat = pak.splat() if pak else None
        self.hud = Hud(pak) if pak else None
        self.speech = Speech(pak) if pak else None
        self.secrets = Secrets(pak) if pak else None
        self.touch = Touch()
        self.enter_down = False
        self.desktop = None
        if not _MICROPYTHON and hasattr(g, 'pygame'):
            import os
            if os.name == 'nt':
                from desktop import Desktop
                self.desktop = Desktop(g)
        self.old_frame = -1
        self.camera = -1
        self.old_x = 0
        self.old_y = 0
        self.old_w = PW
        self.old_h = PH
        self.old_charge = -1
        self.visible = []
        self.weather = None

    def fly_step(self, p, world, keys):
        return self.desktop.step(p, world, keys) if self.desktop else False

    def keys(self, player_x=160, crashed=False):
        # Drain before querying keys: clearevents() would discard touch events.
        # Limit event work so a noisy driver cannot starve the physics tick.
        for _ in range(24):
            ev = g.pollevent()
            if ev.type == g.KEYEV_NONE:
                break
            if ev.type == g.KEYEV_TOUCH_DOWN or ev.type == g.KEYEV_TOUCH_DRAG:
                self.touch.contact(ev.x, ev.y)
            elif ev.type == g.KEYEV_TOUCH_UP:
                self.touch.lift()
        was_touch = self.touch.active
        touch_keys = self.touch.tick(player_x)
        enter = bool(g.keydown(g.KEY_EXE))
        recover = (self.touch.active and not was_touch) or (enter and not self.enter_down)
        self.enter_down = enter
        if self.speech:
            if recover and not crashed:
                self.speech.next = True
                if self.speech.visible and self.touch.active:
                    self.speech.suppress = True
            if self.speech.suppress:
                if touch_keys & 4:
                    touch_keys &= ~4
                else:
                    self.speech.suppress = False
        return (touch_keys | (16 if recover else 0)
                | (1 if g.keydown(g.KEY_LEFT) or g.keydown(g.KEY_7) else 0)
                | (2 if g.keydown(g.KEY_RIGHT) or g.keydown(g.KEY_9) else 0)
                | (4 if g.keydown(g.KEY_SHIFT) else 0)
                | (8 if g.keydown(g.KEY_EXIT) else 0))

    def draw(self, p, boxes):
        if self.speech:
            self.speech.update(p)
        hud_dirty = self.hud.draw(p) if self.hud else False
        x, y = p.x >> 8, p.y >> 8
        camera = max(0, y // 480) * 480
        w, h = PW, PH
        sx = sy_source = 0
        frame = (2 if p.charge else 0) + (1 if p.facing < 0 else 0)
        if p.crash >= 0:
            frame = 4 + (1 if p.facing < 0 else 0)
            w, h = CRASH_W, CRASH_H
            x += (PW - w) // 2
            y += PH - h
            sx = (frame - 4) * CRASH_W
        else:
            sx = frame * PW
        # A wider splat can cross the screen/room edge. Clip both the drawn
        # destination and its source so later background repairs stay in bounds.
        if x < 0:
            sx -= x
            w += x
            x = 0
        w = min(w, 320 - x)
        if y < camera:
            sy_source = camera - y
            h -= sy_source
            y = camera
        h = max(0, min(h, camera + 480 - y))
        if (self.camera >= 0 and x == self.old_x and y == self.old_y + self.camera
                and p.charge == self.old_charge and frame == self.old_frame
                and not (self.weather and self.weather.dirty)
                and not (self.speech and self.speech.changed)):
            if hud_dirty:
                g.dupdate()
            return
        full = camera != self.camera
        moved = (full or x != self.old_x or y != self.old_y + camera or frame != self.old_frame
                 or bool(self.speech and self.speech.changed))
        if full:
            if self.pak:
                self.background = self.pak.load_background(camera // 480)
                # gint's native blit command stores the line count in 8 bits.
                # A 480-line call truncates to 224; keep each strip below 256.
                g.dsubimage(0, 0, self.background, 0, 0, 320, 240)
                g.dsubimage(0, 240, self.background, 0, 240, 320, 240)
                self.secrets.load(camera // 480)
            else:
                g.dclear(g.C_WHITE)
            # Allocate only at a room transition; steady drawing visits only
            # the few visible platforms, rather than the entire tower.
            self.visible = []
            i = 0
            while i < len(boxes):
                by = boxes[i + 1] - camera
                if by < 480 and by + boxes[i + 3] > 0:
                    self.visible.append(i)
                i += 5
        else:
            if self.speech:
                self.speech.clear(self.background, full)
        if self.secrets and self.secrets.prepare(p, self.background, full):
            moved = True
        weather_changed = False
        if self.weather:
            weather_changed = self.weather.prepare(camera // 480, self.background, full)
            moved |= weather_changed
        if not full and moved and self.old_w > 0 and self.old_h > 0:
            if self.background:
                g.dsubimage(self.old_x, self.old_y, self.background,
                            self.old_x, self.old_y, self.old_w, self.old_h)
            else:
                g.drect(self.old_x, self.old_y, self.old_x + self.old_w - 1,
                        self.old_y + self.old_h - 1, g.C_WHITE)
        cursor = 0
        while not self.pak and moved and cursor < len(self.visible):
            i = self.visible[cursor]
            bx, by = boxes[i], boxes[i + 1] - camera
            br, bb = bx + boxes[i + 2] - 1, by + boxes[i + 3] - 1
            if bb >= 0 and by < 480:
                if full or (bx < self.old_x + self.old_w and br >= self.old_x
                            and by < self.old_y + self.old_h and bb >= self.old_y):
                    if full:
                        g.drect(bx, max(0, by), br, min(479, bb), g.C_BLACK)
                    else:
                        g.drect(max(bx, self.old_x), max(by, self.old_y),
                                min(br, self.old_x + self.old_w - 1),
                                min(479, bb, self.old_y + self.old_h - 1), g.C_BLACK)
            cursor += 1
        sy = y - camera
        if moved and w > 0 and h > 0:
            if self.king:
                g.dsubimage(x, sy, self.splat if frame >= 4 else self.king,
                            sx, sy_source, w, h)
            else:
                g.drect(x, sy, x + w - 1, sy + h - 1, g.C_BLACK)
        if not self.hud and full:
            if p.charge:
                g.drect(0, 490, p.charge * 8 - 1, 497, g.C_BLACK)
        elif not self.hud and self.old_charge < p.charge:
            g.drect(self.old_charge * 8, 490, p.charge * 8 - 1, 497, g.C_BLACK)
        elif not self.hud and self.old_charge > p.charge:
            g.drect(p.charge * 8, 490, self.old_charge * 8 - 1, 497, g.C_WHITE)
        if self.secrets:
            self.secrets.draw(moved, self.old_x, self.old_y, self.old_w, self.old_h, x, sy, w, h)
        if self.weather:
            self.weather.draw(x, sy, w, h, weather_changed, self.secrets, self.speech)
        if self.speech:
            self.speech.draw(full, moved, self.old_x, self.old_y, self.old_w, self.old_h,
                             x, sy, w, h)
        self.old_x, self.old_y = x, sy
        self.old_w, self.old_h = w, h
        self.old_charge = p.charge
        self.camera = camera
        self.old_frame = frame
        g.dupdate()
