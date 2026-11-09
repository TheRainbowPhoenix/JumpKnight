"""Tinyking entry point. See README for the runtime files and asset pack."""
import time
from core import Player, step, EXIT, PW
from video import Video
from pak import Pak
from world import World
from weather import Weather


def asset_path():
    path = __file__.replace('\\', '/')
    return (path.rsplit('/', 1)[0] + '/' if '/' in path else '') + 'tower.gmpak'


def run(filename=None):
    if filename is None:
        filename = asset_path()
    pak = Pak(filename)
    try:
        play(pak)
    finally:
        pak.close()


def play(pak):
    world = World(pak)
    p = Player(world.spawn_x, world.spawn_y)
    video = Video(pak)
    desktop = video.desktop
    weather = Weather(pak, world.rooms)
    video.weather = weather
    last = time.ticks_ms()
    debt = 0
    while True:
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, last)
        last = now
        # 30 Hz exactly over time; cap recovery at four ticks after a stall.
        debt = min(debt + max(0, elapsed) * 30, 4000)
        if debt < 1000:
            time.sleep_ms((1000 - debt + 29) // 30)
            continue
        keys = video.keys((p.x >> 8) + PW // 2, p.crash >= 0)
        if keys & EXIT:
            return
        while debt >= 1000:
            world.update(p.y)
            weather.tick(p)
            if desktop is None or not desktop.step(p, world, keys):
                step(p, keys, world.boxes, world.width, weather.force(p))
            if p.y > world.height * 256:
                falls = p.falls + 1
                p = Player(world.spawn_x, world.spawn_y)
                p.falls = falls
            debt -= 1000
        video.draw(p, world.boxes)


run()
