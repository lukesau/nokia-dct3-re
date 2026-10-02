"""Per-product paths for the games mapping tools.

GAMES_PRODUCT selects the firmware the tools work on (default 3210); the
Makefile exports it. Generated files stay in the ignored run directory.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = {
    "3210": {
        "image": "roms/3210f600a_swap16.bin",
        "run_dir": "run_games",
        "symbols": "ghidra/symbols/3210.csv",
        "notes": "docs/data/games_function_notes.json",
        "doc": "docs/games_applications.md",
        "inner": "0x240600-0x244000,0x2621c0-0x263500",
    },
    "3310": {
        "image": "roms/3310f639e_swap16.bin",
        "run_dir": "run_games_3310",
        "symbols": "ghidra/symbols/3310.csv",
        "notes": "docs/data/games_function_notes_3310.json",
        "doc": "docs/games_applications_3310.md",
        "inner": "0x2576a0-0x25a584",
    },
}

def name():
    product = os.environ.get("GAMES_PRODUCT") or "3210"
    if product not in PRODUCTS:
        raise SystemExit(f"GAMES_PRODUCT={product}: expected one of {', '.join(PRODUCTS)}")
    return product

def get(key):
    return PRODUCTS[name()][key]

def path(key):
    return ROOT / get(key)
