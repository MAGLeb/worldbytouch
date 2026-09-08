# worldbytouch.com

Static site for World by Touch – tactile 3D-printed maps. Deployed on Cloudflare Pages.
Accounts, domain, mail and what all of it costs: `docs/INFRA.md` (local only,
gitignored — it holds account ids and is not in the repository).

```
site/index.html      English
site/sr/index.html   Serbian (Gajica latin)
site/sent/           thank-you page the contact form redirects to (EN)
site/sr/sent/        the same in Serbian
site/style.css       shared, light + dark
site/favicon.svg
site/assets/         photos (hand-picked crops) and renders (core/render_site_assets.py)
functions/api/       Cloudflare Pages Function behind the contact form
docs/content/        source material for the copy, not published
```

No build step, no JavaScript on the page, no external requests from the browser. The
contact form posts to a function on this same domain, so the footer's claim stays literally
true and the form still works with scripting switched off: the answer is a redirect, not a
script rewriting the page.

`site/` is the publish root: everything inside it is served. Nothing that is not meant to be
public may live there. That is why `.env` and everything under `docs/` sit outside it.

## Deploy

```bash
python tools/stamp_css.py
wrangler pages deploy site --project-name worldbytouch --branch main
```

Stamp first, every time. Cloudflare serves `/style.css` with `max-age=14400`, so
without the hash in the link a returning visitor can hold four-hour-old CSS against
new markup: every class added in that release renders unstyled, and nothing on this
end shows it. `tools/stamp_css.py` writes a hash of the stylesheet into the link in
both pages, so the URL changes whenever the file does.

Direct upload, not the GitHub integration. `site/assets/reader.jpg` and
`site/assets/author.jpg` are deliberately gitignored (photographs of people), so a
repository-driven build would ship the site with two broken images. Deploy from the working
copy instead.

## Local preview

```bash
python3 -m http.server 8080 --directory site
```

## Editing notes

- **Photographs are the first print. Renders are the current files.** They are not the same
  object: the printed set carries raised Arabic numerals and the old braille dots, while the
  files now generate braille number labels with anchor ridges and 1.6 mm domed dots, and no
  capital-city bumps. Every figure is marked with a `First print` or `Now` chip.
- **One render on the page, and only in `What his hands found`.** A generated picture next to
  a photograph of the real object always loses, and scattering renders through the page made
  the product look like a model of itself. They stay in the README, which is a technical
  document. When the second version is printed and photographed, that render goes and the
  photograph takes its place – the note under the block already says so.
  Keep that distinction: it is what makes the page credible. Re-tag or re-shoot whenever
  either side changes.
- Renders come from `core/render_site_assets.py`, run against the current
  `data/output/printready/*.stl`:

  ```bash
  xvfb-run -a .venv/bin/python core/render_site_assets.py
  ```

  Every camera the site uses lives in that script. Re-render after any geometry change, or
  the page starts describing files that no longer exist. The photographs are not produced
  by it; their sources and crops are listed in its docstring.
- `README.md` embeds six of these renders straight from `site/assets/` instead of keeping a
  second copy. Renaming or deleting one breaks the README too, so re-render in place.
- The renders lean on ambient occlusion (`render_previews._ssao`). Cream filament on a light
  backdrop hides its own relief, and without the contact shadow a border ridge, a braille
  dome and the flat plate all shade alike: the picture goes pale and says nothing. Keep it on.
- The floor plan in the commissions section is a drawing, not a product shot. No plan has
  been printed yet. The figure is an inline SVG and its caption says so in the first six
  words; if a plan does get built, replace both together.
- The `27 countries labelled in braille` figure comes from the build log of
  `create_country_labels_mesh`. Re-check it after changing the map bounds, the country table
  or the label clearance ladder.
- Both language versions must stay content-identical. Their tag structure is currently
  element-for-element the same; keep it that way so a change in one is easy to mirror.
- Short dashes only (`–`). No em dashes anywhere, including `<title>`, Open Graph tags and the
  text inside the `mailto:` links.
- The video has not been shot. Its place is marked by the `VIDEO SLOT` comment after the
  gallery in both pages, and `.video-slot` in the stylesheet is kept for it. When the film
  exists, it goes there with a captions track and the full transcript printed beside the
  player: part of this audience cannot see the picture and part cannot hear the sound.
- Every call to action on the page is an anchor to `#contact`, which is a real form. It
  posts to `functions/api/contact.js`, which validates, sends through Resend and redirects to
  `/sent/` or `/sr/sent/`. A failure renders its own small page with the address on it, so
  nobody loses what they typed without being told.
- The form needs three variables on the Pages project, set once with
  `wrangler pages secret put <NAME> --project-name worldbytouch`: `RESEND_API_KEY`,
  `RESEND_FROM` and `CONTACT_TO`. The key lives in `.env` and nowhere else in the repository.
- The hidden `company` field is a spam trap. A filled one is accepted with the same redirect
  and never sent, so a bot learns nothing from the response.
- The `From €150` figure is the only published price. Custom work, plans included, stays
  quote-only.
- The four figures in the stats band are inline SVG drawn from the real geometry: the tile
  grid with its dovetails, the terrain steps over a ribbed sea, 27 written the way the map
  writes it (anchor ridge, then the cells for 2 and 7), and a print letter beside its braille
  cell. If the geometry changes, they are drawings and will not follow it on their own.
- The footer claims no cookies, no tracking and nothing loaded from another server. Keep it
  literally true: no analytics, no hosted fonts, no CDN, no embeds.
- Accessibility is part of the product claim here: semantic headings with no skipped levels,
  alt text that describes what is in the picture, visible focus rings, contrast at or above
  4.5:1 in both themes, keyboard order. Test with a screen reader before shipping changes.
