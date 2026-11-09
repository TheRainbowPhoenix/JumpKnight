"""GMPK v1 reader. Type-4 P4 images are read into reusable native buffers."""
import struct
import gint as g
from core import PW, PH, CRASH_W, CRASH_H


class Pak:
    def __init__(self, filename):
        self.f = open(filename, 'rb')
        try:
            magic, version, toc = struct.unpack('<4sHI', self.f.read(10))
            self.f.seek(0, 2)
            self.size = self.f.tell()
            if magic != b'GMPK' or version != 1 or not 10 <= toc <= self.size - 4:
                raise ValueError('Invalid GMPAK header')
            self.end = toc
            self.f.seek(toc)
            count = struct.unpack('<I', self.f.read(4))[0]
            if count > 512 or toc + 4 + count * 25 != self.size:
                raise ValueError('Invalid GMPAK table')
            self.table = self.f.read(count * 25)
            self.buffer = bytearray(320 * 480 // 2)
            self.view = memoryview(self.buffer)
            self.palette = bytearray(32)
            self.background = g.image(g.IMAGE_P4_RGB565, 16, 320, 480, 160,
                                      self.view, self.palette)
            self.offset = self.length = self.kind = 0
        except Exception:
            self.f.close()
            raise

    def find(self, name):
        key = name.encode('ascii')
        if len(key) > 16:
            raise ValueError('GMPAK name too long')
        key += b'\0' * (16 - len(key))
        for i in range(0, len(self.table), 25):
            if self.table[i:i + 16] == key:
                self.kind, self.offset, self.length = struct.unpack_from('<BII', self.table, i + 16)
                if self.offset < 10 or self.offset + self.length > self.end:
                    raise ValueError('GMPAK entry outside payload')
                self.f.seek(self.offset)
                return self.length
        raise ValueError('Missing GMPAK entry: ' + name)

    def read(self, name, limit=16384):
        size = self.find(name)
        if size > limit:
            raise ValueError('GMPAK entry too large')
        data = self.f.read(size)
        if len(data) != size:
            raise ValueError('Truncated GMPAK entry')
        return data

    def load_background(self, room):
        size = self.find('BG_%03d' % room)
        header = self.f.read(14)
        fmt, w, h, stride, cc, pal_len, data_len = struct.unpack('<BHHHBHI', header)
        if (self.kind != 4 or fmt != 5 or w != 320 or h != 480
                or stride != 160 or cc != 16 or pal_len != 32 or data_len != 76800
                or size != 14 + 32 + 76800):
            raise ValueError('Expected fixed 320x480 P4 background')
        if self.f.readinto(self.palette) != 32 or self.f.readinto(self.view) != 76800:
            raise ValueError('Truncated GMPAK image')
        # The pygame simulator snapshots buffers at image construction; native
        # gint reads them at draw time. Refresh only that desktop snapshot when
        # a room changes, retaining the same image/buffers on the calculator.
        decode = getattr(self.background, '_decode_image', None)
        if decode is not None:
            self.background.surface = decode()
        return self.background

    def sprite(self):
        return self._sprite('KING', PW * 4, PH)

    def splat(self):
        return self._sprite('SPLAT', CRASH_W * 2, CRASH_H)

    def hud(self):
        return self._sprite('HUD', 320, 48, False)

    def digits(self):
        return self._sprite('DIGITS', 100, 14, False)

    def _sprite(self, name, width, height, alpha=True):
        data = self.read(name, 16384)
        if self.kind != 4 or len(data) < 14:
            raise ValueError('Invalid sprite')
        fmt, w, h, stride, cc, plen, dlen = struct.unpack_from('<BHHHBHI', data)
        # Pack IDs are stable serialization values, not firmware enum values.
        if (fmt != (6 if alpha else 5) or cc != 16 or plen != 32
                or w != width or h != height or stride != width // 2 or dlen != width // 2 * height
                or len(data) != 14 + plen + dlen):
            raise ValueError('Invalid sprite %s: %r' % (name, (fmt, w, h, stride, cc, plen, dlen, len(data))))
        view = memoryview(data)
        return g.image(g.IMAGE_P4_RGB565A if alpha else g.IMAGE_P4_RGB565,
                       cc, w, h, stride, view[46:], view[14:46])

    def close(self):
        self.f.close()
