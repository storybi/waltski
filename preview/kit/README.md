# Ikon resort picker + Skiinut 2.0 redesign (preview, Oct 30, 2026)

Not live yet: waiting for Mark's approval. The preview is at www.skiinut.com/preview/ and in the claude.ai artifact "Skiinut Preview".

- `resorts.py` — the 42 US resorts on the 2026/27 full Ikon Pass: coordinates, OnTheSnow path, cam pictures, cam and trail-map pages.
- `apply.py <artifact index.html> <out.html> [ski_out.js]` — adds the resort picker, cams, trail map, collapsed Weather Elsewhere and the new design to the News artifact page.
- `ski_conditions.py` — the extended `scripts/ski_conditions.py` (ticker, outlook and resort weather for every Ikon resort). On approval it replaces `scripts/ski_conditions.py`.
- `hub.js`, `design.css` — the resort hub script and the design system that `apply.py` appends.
