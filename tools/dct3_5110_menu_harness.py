#!/usr/bin/env python3
"""Render the 5110 (NSE-1 v5.28) Games menus with the phone's own UI code.

Builds on dct3_5110_game_harness.py. Here the whole flash runs natively: the
menu engine (0x24c000..), the games applications (0x278d60..0x2793e0), the
widget layer and its paint pass (0x2354e0), the fonts and the LCD routines.
The game harness's stubs stay (heap, scheduler, tones, status posts), plus
the phone state query. What the phone sets up at boot is written directly
(BOOT_STATE), so a page can be drawn without running the boot.

Each page is reached the way the phone reaches it: the main menu and the
games list are the firmware's static menus, a game's menu is built by the
games application, and Level, Instructions, Top score and the game-over
note are the applications and notes the menu items start.
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dct3_5110_game_harness import (GAME_INDEX, GAME_RECORDS, GAMES, Harness,  # noqa: E402
                                    Stop, save_frames)

# Menu engine
MENU_CREATE = 0x24dd70         # (level, flags, 5, 0, 0): a level built at run time
MENU_ENTER = 0x24daf8          # (level, item)
MENU_OPEN = 0x24e6c8           # (descriptor, item id, enable mask): a static menu
MENU_SELECT = 0x24da40         # (item): select and draw
MENU_RETURN = 0x24de04         # back to the level's remembered entry
MAIN_MENU = 0x2a0a7c           # {table 0x2a09a0, 10 entries, flags 0x10}
GAMES_MENU = 0x2a93cc          # {table 0x2a937c, 3 entries, flags 0xc0}
GAMES_ENTRY = 6                # Games in the main menu
SHORTCUT_ACTIVE = 0x105d34     # main menu number entry open; the path shows "_"

# Games applications (application table 0x2a6e18, 8 bytes per id)
APP_SOFTKEY = 0x28a940         # sets the softkey of the current application
APP_GAMES = 0x27907c           # application 0x58
APP_PLAY = 0x2792cc            # 0x59
APP_LEVEL = 0x278dc8           # 0x5a
APP_INSTRUCTIONS = 0x278efa    # 0x5b
ST_ENTER = 0x5dc               # an application's first status
ST_GAMES_ITEM = 0x1130         # a games list entry was chosen
ST_MENU_ITEM = 0x1131          # a game's menu entry was chosen
ST_GAME_OVER = 0x1132          # posted by a game (0x5132: status 0x1132 + 1 arg)
ST_UP, ST_DOWN = 0x367, 0x366  # scroll keys as the applications see them
STATUS_ARG = 0x10a50f          # the posted status's argument (item id, tone)
MENU_BUILD = 0x278f78          # puts a game's menu entries into level 2

PAINT = 0x2354e0               # widget lists to the framebuffer
FONT_INIT = 0x253a4c
PHONE_STATE = 0x28ee7e         # 3, 5, 6 or 7 lets text draw

# What the phone sets up before the menus run.
BOOT_STATE = [
    (0x10fcf0, 1, 1, "language: English"),
    (0x10fd55, 1, 1, "script flags: Latin (0x08 right to left, 0x16 others)"),
    (0x106f80, 0x2b0050, 4, "character map for the English text block"),
    (0x10fd57, 3, 1, "most rows a list shows"),
    (0x10b602, 0x01ff, 2, "main menu entries shown: 1..9, no SIM services"),
]
INDICATOR_SLOTS = (0x108e54, 0x16)  # 22 slots of 12 bytes, +4 = 0x16 when free

ITEMS = {"level": 3, "new": 1, "continue": 6, "lastview": 6, "top": 4,
         "instructions": 5}
RESUME = {"none": 0, "continue": 1, "lastview": 3}


class MenuHarness(Harness):
    def __init__(self, image, verbose=False):
        super().__init__(image, verbose, native=[(0x200000, 0x300000, "flash")])
        self.stubs[PHONE_STATE] = ("phone_state", lambda: 3)
        for addr, value, size, _ in BOOT_STATE:
            self.mu.mem_write(addr, value.to_bytes(size, "big"))
        base, slots = INDICATOR_SLOTS
        for i in range(slots):
            self.w8(base + 12 * i + 4, 0x16)
        self.call(FONT_INIT)
        self.app_current = self.r32(0x28a964)  # current application id (u8)

    def w16(self, a, v):
        self.mu.mem_write(a, struct.pack(">H", v & 0xFFFF))

    def paint(self):
        self.call(PAINT)
        self.snap()

    # --- pages ------------------------------------------------------------
    def main(self, item=GAMES_ENTRY, shortcut=False):
        self.call(MENU_OPEN, MAIN_MENU, 0, 0)
        self.w8(SHORTCUT_ACTIVE, 1 if shortcut else 0)
        self.call(MENU_SELECT, item)

    def games(self, game):
        self.main()
        self.call(MENU_CREATE, 2, 0xc0, 5, 0, 0)   # the games app's level
        self.call(MENU_OPEN, GAMES_MENU, 0, 0x7)
        self.w8(SHORTCUT_ACTIVE, 0)
        self.call(MENU_SELECT, game + 1)

    def menu(self, game, resume="none", item=None):
        """A game's menu. Choosing the game keeps Continue but drops Last
        view, which shows when a game that has ended returns to the menu."""
        self.games(game)
        self.w8(GAME_RECORDS + 8 * game + 5, RESUME[resume])
        self.w8(STATUS_ARG, game)
        self.w8(GAME_INDEX, game)
        self.call(APP_GAMES, ST_GAMES_ITEM)
        if resume == "lastview":
            self.w8(GAME_RECORDS + 8 * game + 5, RESUME[resume])
            self.call(MENU_BUILD)
            self.call(MENU_RETURN)
        if item is not None:
            self.call(MENU_SELECT, item)

    def app(self, app_id, handler, game):
        self.w8(GAME_INDEX, game)
        self.w8(self.app_current, app_id)
        self.call(handler, ST_ENTER)
        self.call(APP_SOFTKEY)

    def level(self, game, level, keys=()):
        self.set_level(game, level)
        self.app(0x5a, APP_LEVEL, game)
        for k in keys:
            self.paint()
            self.call(APP_LEVEL, ST_UP if k == "up" else ST_DOWN)

    def instructions(self, game):
        self.app(0x5b, APP_INSTRUCTIONS, game)

    def top_score(self, game, top):
        self.menu(game)
        self.w16(GAME_RECORDS + 8 * game + 2, top)
        self.w8(STATUS_ARG, 4)
        self.call(APP_GAMES, ST_MENU_ITEM)

    def game_over(self, game, score, top, tone=0x11):
        r = GAME_RECORDS + 8 * game
        self.w16(r, score)
        self.w16(r + 2, top)
        self.w8(r + 6, 1)
        self.w8(GAME_INDEX, game)
        self.w8(STATUS_ARG, tone)
        self.call(APP_PLAY, ST_GAME_OVER)


def ascii_frame(fb):
    return "\n".join("".join("#" if p else "." for p in row) for row in fb)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image", default="roms/noki5110/5110f528a.fls")
    ap.add_argument("page", choices=["main", "games", "menu", "level",
                                     "instructions", "topscore", "gameover"])
    ap.add_argument("--game", default="snake", help="snake, memory, logic or 0..2")
    ap.add_argument("--item", type=int, help="entry to select (main, menu)")
    ap.add_argument("--resume", choices=RESUME, default="none",
                    help="menu: what the second entry is")
    ap.add_argument("--level", type=int, default=0, help="level index")
    ap.add_argument("--keys", default="", help="level: up/down presses, e.g. 'up up down'")
    ap.add_argument("--score", type=int, default=0)
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--tone", type=lambda s: int(s, 0), default=0x11,
                    help="gameover: the argument the game posts (Snake 0x11, Logic 0x13)")
    ap.add_argument("--shortcut", action="store_true",
                    help="main: the number entry is open, as right after Menu")
    ap.add_argument("--out", help="directory for PNGs and a contact sheet")
    ap.add_argument("--ascii", action="store_true", help="print the last frame")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    names = {v: k for k, v in GAMES.items()}
    game = names[a.game] if a.game in names else int(a.game)

    h = MenuHarness(a.image, a.verbose)
    status = 0
    try:
        if a.page == "main":
            h.main(a.item or GAMES_ENTRY, a.shortcut)
        elif a.page == "games":
            h.games(game)
        elif a.page == "menu":
            h.menu(game, a.resume, a.item)
        elif a.page == "level":
            h.level(game, a.level, a.keys.split())
        elif a.page == "instructions":
            h.instructions(game)
        elif a.page == "topscore":
            h.top_score(game, a.top)
        elif a.page == "gameover":
            h.game_over(game, a.score, a.top, a.tone)
        h.paint()
    except Stop as e:
        print("stopped:", e)
        status = 1
    print("\n".join(h.log[-12:]))
    for t, kind, tone in h.sounds:
        print(f"  tone post {kind:#x} id {tone:#x}")
    if a.ascii and h.frames:
        print(ascii_frame(h.frames[-1][1]))
    if a.out:
        save_frames(h.frames, a.out)
    return status


if __name__ == "__main__":
    sys.exit(main())
