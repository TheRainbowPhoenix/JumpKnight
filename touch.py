"""Tick-based touch debounce, independent of gint and wall-clock floats.

DOWN/DRAG renew contact; UP must remain quiet for two ticks before release.
One-tick contacts are ignored. A contact expires after 24 silent ticks if
the driver loses UP, so a stuck touch cannot repeat jumps after landing.
"""
from core import LEFT, RIGHT, JUMP


class Touch:
    def __init__(self):
        self.raw = False
        self.age = 0
        self.quiet = 0
        self.release = 0
        self.active = False
        self.x = 160
        self.direction = 0

    def contact(self, x, y):
        if 0 <= x < 320 and 0 <= y < 528:
            self.x = x
            self.raw = True
            self.quiet = 0
            self.release = 0

    def lift(self):
        self.raw = False

    def tick(self, player_x):
        self.quiet += 1
        if self.quiet > 24:
            self.raw = False
        if self.raw:
            self.age = min(2, self.age + 1)
            self.release = 0
            if self.age >= 2:
                self.active = True
                # A dead band around the player makes vertical jumps possible.
                # Hysteresis keeps a jittering stylus from changing direction.
                delta = self.x - player_x
                if delta < -20:
                    self.direction = LEFT
                elif delta > 20:
                    self.direction = RIGHT
                elif -10 <= delta <= 10:
                    self.direction = 0
        else:
            self.release += 1
            if not self.active or self.release >= 2:
                self.active = False
                self.age = 0
                self.direction = 0
        return (self.direction | JUMP) if self.active else 0
