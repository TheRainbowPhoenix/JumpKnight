"""Load only current/adjacent collision rooms from the asset pack."""
import struct


class World:
    def __init__(self, pak):
        self.pak = pak
        self.width, self.rooms, self.spawn_x, self.spawn_y = struct.unpack('<HHHH', pak.read('WORLD'))
        if self.width != 320 or not 1 <= self.rooms <= 100:
            raise ValueError('Invalid tower dimensions')
        self.height = self.rooms * 480
        self.room = -1
        self.boxes = []
        self.band = -1
        self.bands = []
        self.band_start = 0

    def update(self, y):
        room = max(0, min(self.rooms - 1, (y >> 8) // 480))
        band = (y >> 8) // 64
        if self.room == room:
            if self.band != band:
                self.boxes = self.bands[band - self.band_start]
                self.band = band
            return
        boxes = []
        for r in range(max(0, room - 1), min(self.rooms, room + 2)):
            data = self.pak.read('COL_%03d' % r)
            if self.pak.kind != 5 or len(data) % 9:
                raise ValueError('Invalid collision entry')
            for i in range(0, len(data), 9):
                x, by, w, h, kind = struct.unpack_from('<hhHHB', data, i)
                if not (0 <= x < 320 and 0 <= by < 480 and 0 < w <= 320 - x
                        and 0 < h <= 480 - by and kind <= 6):
                    raise ValueError('Invalid collision rectangle')
                boxes.extend((x, by + r * 480, w, h, kind))
        # Precompute local vertical broad-phase bands only when rooms change.
        # Covers player height + full upward/downward sweep at any band edge.
        self.band_start = room * 480 // 64
        band_end = ((room + 1) * 480 - 1) // 64
        self.bands = []
        for b in range(self.band_start, band_end + 1):
            near = []
            low, high = b * 64 - 32, (b + 1) * 64 + 48
            for i in range(0, len(boxes), 5):
                if boxes[i + 1] < high and boxes[i + 1] + boxes[i + 3] > low:
                    near.extend(boxes[i:i + 5])
            self.bands.append(near)
        self.boxes = self.bands[band - self.band_start]
        self.band = band
        self.room = room
