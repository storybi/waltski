#!/usr/bin/env python3
"""Keep the live-data job's fresher blocks when index.html is rebuilt from the claude.ai artifact (Mark, Oct 31, 2026).

usage: python3 scripts/keep_live_data.py <base index.html (the repo's current copy)> <built index.html (rewritten in place)>

Copies these statements from the base page into the built page, so a rebuild never steps them back to the morning refresh:
  var SNAP / var SNAP_AT  (cam snapshots)       var SEA_GAME / var ORE_GAME  (live football strips)
Without this, a mid-day rebuild put last week's Ducks game back on the site during a live game, which hid the live field and the
resort card's football button.
"""
import re
import sys

PATS = [r'var SNAP = \{.*?\};', r'var SNAP_AT = ".*?";', r'var SEA_GAME = \{.*?\};', r'var ORE_GAME = \{.*?\};']


def keep(base, built):
    for pat in PATS:
        mb, ms = re.search(pat, base, re.S), re.search(pat, built, re.S)
        if mb and ms:
            built = built[:ms.start()] + mb.group(0) + built[ms.end():]
    return built


if __name__ == "__main__":
    base = open(sys.argv[1], encoding="utf-8").read()
    built = open(sys.argv[2], encoding="utf-8").read()
    open(sys.argv[2], "w", encoding="utf-8").write(keep(base, built))
    print("keep_live_data: kept SNAP, SNAP_AT, SEA_GAME, ORE_GAME from the base page")
