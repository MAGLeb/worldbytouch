#!/usr/bin/env python3
"""
Serbian Latin (Gajica) Braille alphabet — 30 letters.

Dot patterns VERIFIED 2026-06-23 against Wiktionary per-cell pages for
Yugoslav / Serbo-Croatian Braille (each Braille-cell page states which
Latin/Cyrillic letter it encodes). NOT guessed — the base letters follow
international Braille; the 8 Serbian-specific cells were each cross-checked
on their own cell page (e.g. ⠻ = dž, ⠹ = đ — a pair the table summaries
routinely swap).

Dot numbering:
    1 4
    2 5
    3 6
"""

# (display glyph, dot tuple) in Serbian Gajica alphabet order
SERBIAN_GAJICA = [
    ("A",  (1,)),
    ("B",  (1, 2)),
    ("C",  (1, 4)),
    ("Č",  (1, 6)),
    ("Ć",  (1, 4, 6)),
    ("D",  (1, 4, 5)),
    ("Dž", (1, 2, 4, 5, 6)),
    ("Đ",  (1, 4, 5, 6)),
    ("E",  (1, 5)),
    ("F",  (1, 2, 4)),
    ("G",  (1, 2, 4, 5)),
    ("H",  (1, 2, 5)),
    ("I",  (2, 4)),
    ("J",  (2, 4, 5)),
    ("K",  (1, 3)),
    ("L",  (1, 2, 3)),
    ("Lj", (1, 2, 6)),
    ("M",  (1, 3, 4)),
    ("N",  (1, 3, 4, 5)),
    ("Nj", (1, 2, 4, 6)),
    ("O",  (1, 3, 5)),
    ("P",  (1, 2, 3, 4)),
    ("R",  (1, 2, 3, 5)),
    ("S",  (2, 3, 4)),
    ("Š",  (1, 5, 6)),
    ("T",  (2, 3, 4, 5)),
    ("U",  (1, 3, 6)),
    ("V",  (1, 2, 3, 6)),
    ("Z",  (1, 3, 5, 6)),
    ("Ž",  (2, 3, 4, 6)),
]

# lowercase grapheme -> dot tuple (digraph keys are 2 chars: "dž","lj","nj")
SERBIAN_DOTS = {disp.lower(): dots for disp, dots in SERBIAN_GAJICA}
DIGRAPHS = ("dž", "lj", "nj")


def tokenize(text):
    """Split Serbian Latin text into graphemes; dž/lj/nj are single cells."""
    text = text.lower()
    out, i = [], 0
    while i < len(text):
        if text[i:i + 2] in DIGRAPHS:
            out.append(text[i:i + 2])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return out
