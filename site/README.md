# worldbytouch.com

Static site for World by Touch – tactile 3D-printed maps. Deployed on Cloudflare Pages.

```
index.html        English
sr/index.html     Serbian (Gajica latin)
style.css         shared, light + dark
favicon.svg
assets/           photos and renders (copied from the blind_map repo)
```

No build step, no JavaScript, no external requests. The whole site works offline from the
folder.

## Deploy

Cloudflare Pages → connect this repository → build command: none, output directory: `/`.
Every push to `main` redeploys.

## Local preview

```bash
python3 -m http.server 8080
```

## Editing notes

- **Photographs are the first print. Renders are the current files.** They are not the same
  object: the printed set carries raised Arabic numerals and the old braille dots, while the
  files now generate braille number labels with anchor ridges and 1.6 mm domed dots, and no
  capital-city bumps. Every figure is marked with a `First print` or `Current files` tag.
  Keep that distinction: it is what makes the page credible. Re-tag or re-shoot whenever
  either side changes.
- Renders come from `blind_map/core/render_previews.py` run against the current
  `data/output/printready/*.stl`. Re-render after any geometry change, or the site starts
  describing files that no longer exist.
- The `27 countries labelled in braille` figure comes from the build log of
  `create_country_labels_mesh`. Re-check it after changing the map bounds, the country table
  or the label clearance ladder.
- Both language versions must stay content-identical. Their tag structure is currently
  element-for-element the same; keep it that way so a change in one is easy to mirror.
- Short dashes only (`–`). No em dashes anywhere, including `<title>`, Open Graph tags and the
  text inside the `mailto:` links.
- The hero video goes into the `.video-slot` block on both pages. Keep the captions track and
  print a text transcript next to the player: this site is read by the people it is about.
- Both `mailto:` links carry a pre-filled three-question intake. If you change the questions,
  change them in both languages.
- The `From €150` figure is the only published price. Custom work stays quote-only.
- Accessibility is part of the product claim here: semantic headings with no skipped levels,
  alt text that describes what is in the picture, visible focus rings, contrast at or above
  4.5:1 in both themes, keyboard order. Test with a screen reader before shipping changes.
