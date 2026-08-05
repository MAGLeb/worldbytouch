#!/usr/bin/env python3
"""Stamp the stylesheet link in both pages with a hash of the stylesheet.

Cloudflare serves `/style.css` with `max-age=14400`, so for four hours after a
deploy a returning visitor can hold the old stylesheet and receive new markup:
every class added in that release renders unstyled, and the page looks broken in
a way nothing on this end can see. The query string makes the URL change
whenever the file changes, which is enough to defeat that.

Run it before every deploy:

    python tools/stamp_css.py && wrangler pages deploy site --project-name worldbytouch
"""
import hashlib
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
PAGES = (SITE / "index.html", SITE / "sr" / "index.html")
CSS = SITE / "style.css"


def main():
    digest = hashlib.sha256(CSS.read_bytes()).hexdigest()[:8]
    changed = []
    for page in PAGES:
        src = page.read_text()
        out, n = re.subn(r'href="/style\.css(?:\?v=[0-9a-f]+)?"',
                         f'href="/style.css?v={digest}"', src, count=1)
        if n != 1:
            sys.exit(f"{page}: no stylesheet link to stamp")
        if out != src:
            page.write_text(out)
            changed.append(str(page.relative_to(SITE.parent)))
    print(f"style.css -> v={digest}" + (f" ({', '.join(changed)} updated)" if changed
                                        else " (already current)"))


if __name__ == "__main__":
    main()
