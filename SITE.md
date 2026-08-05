# worldbytouch.com

Static site for World by Touch – tactile 3D-printed maps. Deployed on Cloudflare Pages.

```
site/index.html      English
site/sr/index.html   Serbian (Gajica latin)
site/style.css       shared, light + dark
site/favicon.svg
site/assets/         photos (hand-picked crops) and renders (core/render_site_assets.py)
content/             source material for the copy, not published
```

No build step, no JavaScript, no external requests. The whole site works offline from the
folder.

`site/` is the publish root: everything inside it is served. Nothing that is not meant to be
public may live there. That is why `.env`, `content/` and this file sit outside it.

## Deploy

```bash
wrangler pages deploy site --project-name worldbytouch --branch main
```

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
  capital-city bumps. Every figure is marked with a `First print` or `Current files` tag.
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
- Four `mailto:` links, two intakes, both three questions: the hero button, the closing band
  and the custom price card ask region / who reads it / how many copies; the ready-made price
  card asks braille language / how many copies / where it ships. Change them in both
  languages at once.
- The `From €150` figure is the only published price. Custom work stays quote-only.
- The footer claims no cookies, no tracking and nothing loaded from another server. Keep it
  literally true: no analytics, no hosted fonts, no CDN, no embeds.
- Accessibility is part of the product claim here: semantic headings with no skipped levels,
  alt text that describes what is in the picture, visible focus rings, contrast at or above
  4.5:1 in both themes, keyboard order. Test with a screen reader before shipping changes.
