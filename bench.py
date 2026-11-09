"""Run on fxcp for real timings; also works with the headless host build.

Drawing time includes dupdate. No per-frame printing or sample arrays.
"""
import time
import gc
from core import Player, step, LEFT, RIGHT, JUMP
from pak import Pak
from world import World
from video import Video
from weather import Weather

path = __file__.replace('\\', '/')
pak = Pak((path.rsplit('/', 1)[0] + '/' if '/' in path else '') + 'tower.gmpak')
world = World(pak)
p = Player(world.spawn_x, world.spawn_y)
world.update(p.y)
video = Video(pak)
weather = Weather(pak, world.rooms)
video.weather = weather
weather.tick(p)
video.draw(p, world.boxes)
gc.collect()
heap_start = gc.mem_alloc()
update_total = draw_total = update_max = draw_max = 0
for tick in range(600):
    keys = (RIGHT if (tick // 90) & 1 else LEFT) | (JUMP if tick % 60 < 18 else 0)
    t0 = time.ticks_us()
    world.update(p.y)
    weather.tick(p)
    step(p, keys, world.boxes, world.width, weather.force(p))
    t1 = time.ticks_us()
    video.draw(p, world.boxes)
    t2 = time.ticks_us()
    update_us = time.ticks_diff(t1, t0)
    draw_us = time.ticks_diff(t2, t1)
    update_total += update_us
    draw_total += draw_us
    update_max = max(update_max, update_us)
    draw_max = max(draw_max, draw_us)
heap_end = gc.mem_alloc()
print('600 ticks; update mean/max us:', update_total // 600, update_max)
print('draw+transfer mean/max us:', draw_total // 600, draw_max)
print('heap before/after:', heap_start, heap_end)
print('Timing applies only to the machine running this benchmark.')
pak.close()
