"""48-row static panel; only changed charge segments, digits and LED redraw."""
import struct
import gint as g
from core import PH

CHARGE_COLOR = 0xf4c5
READY_COLOR, DOWN_COLOR = 0x6d28, 0xd986
FLY_COLOR = 0x5dff


class Hud:
    def __init__(self, pak):
        self.panel = pak.hud()
        self.font = pak.digits()
        self.fall_font = pak._sprite('FALL_DIGITS', 100, 16, False)
        self.falls = -1
        self.fall_digits = [-1, -1, -1, -1, -1]
        self.base = struct.unpack('<H', pak.read('HUD_META'))[0]
        self.started = False
        self.charge = 0
        self.elevation = -1
        self.status = -1
        self.digits = [-1, -1, -1, -1, -1]

    def draw(self, p):
        dirty = False
        if not self.started:
            g.dsubimage(0, 480, self.panel, 0, 0, 320, 48)
            self.started = True
            dirty = True
        if self.charge < p.charge:
            for segment in range(self.charge, p.charge):
                x = 10 + segment * 7
                g.drect(x, 508, x + 5, 516, CHARGE_COLOR)
            dirty = True
        elif self.charge > p.charge:
            x = 10 + p.charge * 7
            w = (self.charge - p.charge) * 7 - 1
            g.dsubimage(x, 508, self.panel, x, 28, w, 9)
            dirty = True
        self.charge = p.charge
        falls = min(99999, p.falls)
        if falls != self.falls:
            remaining, divisor = falls, 10000
            for i in range(5):
                digit = remaining // divisor
                remaining -= digit * divisor
                divisor //= 10
                if digit != self.fall_digits[i]:
                    g.dsubimage(153 + i * 12, 502, self.fall_font, digit * 10, 0, 10, 16)
                    self.fall_digits[i] = digit
            self.falls = falls
            dirty = True
        status = 3 if p.flying else (2 if p.crash >= 0 else (1 if p.charge else 0))
        if status != self.status:
            color = FLY_COLOR if status == 3 else (DOWN_COLOR if status == 2 else (CHARGE_COLOR if status == 1 else READY_COLOR))
            g.drect(178, 520, 182, 523, color)
            self.status = status
            dirty = True
        elevation = min(99999, max(0, (self.base - (p.y >> 8) - PH) * 3 // 2))
        if elevation != self.elevation:
            remaining, divisor = elevation, 10000
            for i in range(5):
                digit = remaining // divisor
                remaining -= digit * divisor
                divisor //= 10
                if digit != self.digits[i]:
                    g.dsubimage(231 + i * 12, 504, self.font, digit * 10, 0, 10, 14)
                    self.digits[i] = digit
            self.elevation = elevation
            dirty = True
        return dirty
