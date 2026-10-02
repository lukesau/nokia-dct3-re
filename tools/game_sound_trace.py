#!/usr/bin/env python3
"""Lists the buzzer notes of every game sound in a MAME error.log made with
mame_nokia_3310_game_sound_log.lua and -verbose: one line per sound, each
note as hertz x milliseconds of emulated time."""
import re
import sys

SOUND = re.compile(r"GSND f1 ([0-9a-f]+)")
BUZZER = re.compile(r"buzzer: enabled=([01]) divider=(\d+) frequency=\d+ volume=\d+ t=([\d.]+)")


def notes(events):
    """(enabled, divider, time) writes to (hertz, ms) notes; the last write
    at one instant is the one that sounds."""
    settled = []
    for enabled, divider, t in events:
        if settled and t - settled[-1][2] < 0.0005:
            settled.pop()
        settled.append((enabled, divider, t))
    out = []
    for (enabled, divider, t), (_, _, end) in zip(settled, settled[1:]):
        if not enabled:
            continue
        if out and out[-1][0] == divider:
            out[-1][1] += end - t
        else:
            out.append([divider, end - t])
    return [(13_000_000 / divider, 1000 * length) for divider, length in out]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: game_sound_trace.py MAME_ERROR_LOG")
    sound, events = None, []

    def flush():
        if sound is not None:
            print(f"0x{sound}: " + " ".join(f"{hz:.0f}x{ms:.1f}" for hz, ms in notes(events)))

    for line in open(sys.argv[1], errors="replace"):
        match = SOUND.search(line)
        if match:
            flush()
            sound, events = match.group(1), []
            continue
        match = BUZZER.search(line)
        if match and sound is not None:
            events.append((match.group(1) == "1", int(match.group(2)), float(match.group(3))))
    flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
