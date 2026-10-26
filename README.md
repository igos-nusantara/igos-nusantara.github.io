# igos-nusantara.github.io

The IGN 26 landing page, in English and Indonesian.

Plain static HTML, CSS and a little vanilla JavaScript — no framework, no
bundler, no npm. GitHub Pages serves the repo root as-is.

## Layout

```
index.html          generated — English
id.html             generated — Indonesian
build.py            renders both pages
content/en.json     all English copy
content/id.json     all Indonesian copy
assets/css/pitaloka.css   design tokens, generated from Pitaloka tokens.json
assets/css/site.css       layout and components
assets/js/site.js         hero slider, mobile nav, copy buttons
assets/icons/*.svg        Lucide icons, inlined at build time
assets/img/*              screenshots and the logo
.nojekyll           tells GitHub Pages to serve the files untouched
```

`index.html` and `id.html` are committed so the site works with nothing but a
checkout, but they are build output — **edit `content/*.json` or `build.py`,
never the HTML**, then rebuild.

## Build

```sh
python3 build.py
```

No dependencies beyond the standard library. It reads the two content files,
inlines the icons, measures every image so each `<img>` carries its real
`width`/`height` (lazy-loaded figures would otherwise collapse to zero height
and make the page jump), and writes the two HTML files.

## Editing copy

Everything a translator needs is in `content/en.json` and `content/id.json`.
The two files have identical shapes; if you add a key to one, add it to the
other. Image filenames in the JSON are relative to `assets/img/`.

## Design system

Colours, radii, spacing and type come from
[Pitaloka](https://pitaloka.igos-nusantara.or.id), the design system shared by
BAYU's GTK 4 and Qt 6 applications. `assets/css/pitaloka.css` is a transcription
of its `tokens.json` as CSS custom properties, so the site and the desktop stay
in step. To refresh it:

```sh
curl -s https://pitaloka.igos-nusantara.or.id/tokens/tokens.json | less
```

The `--navy-*` variables at the bottom of that file are the only values that do
*not* come from Pitaloka; they are marketing shades for the dark bands.

## Adding an icon

Icons are [Lucide](https://lucide.dev) (ISC), fetched once and inlined so the
page has no runtime icon dependency:

```sh
curl -sL -o assets/icons/NAME.svg \
  https://unpkg.com/lucide-static@1.61.0/icons/NAME.svg
```

Then reference `NAME` from the JSON or from `build.py`.

## Download link

The ISO URL lives in one place, `ISO_URL` in `build.py`, and is also repeated in
the `content/*.json` command blocks and footer links. Change it in all of them
when the release moves off the nightly path.

## Licence

Page content and code: GPL-3.0 / BSD-3-Clause, matching IGN 26.
Lucide icons: ISC. Inter and JetBrains Mono: SIL Open Font License.
