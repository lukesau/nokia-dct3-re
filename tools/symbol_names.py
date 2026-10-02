"""Symbol lookup over the product symbol map, ghidra/symbols/3210.csv by default (plus an optional extra CSV, which wins)."""
import csv
from pathlib import Path
import games_product as P
ROOT = Path(__file__).resolve().parents[1]
def load(extra=None):
    names = {}
    for p in [P.path("symbols")] + ([Path(extra)] if extra else []):
        if not p.exists(): continue
        for row in csv.reader(open(p)):
            if len(row) >= 3 and row[0] != "address":
                addr = int(row[0], 16)
                # Only code addresses carry a Thumb bit; RAM/data labels may be odd.
                names[addr & ~1 if row[1] == "function" else addr] = row[2]
    return names
def is_auto(name):
    return name is None or name.startswith(("FUN_", "thunk_FUN_", "callback_", "func_"))
