#!/usr/bin/env python3
"""Render the IGN 26 landing page from content/*.json.

    python3 build.py

Writes index.html (English) and id.html (Indonesian) at the repo root.
Structure lives here, copy lives in content/. Icons are inlined from
assets/icons/*.svg (Lucide, ISC) so the page has no runtime dependency
beyond the two Google Fonts.
"""

from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import struct
import sys

ROOT = pathlib.Path(__file__).parent
ICONS = ROOT / "assets" / "icons"
IMG = "assets/img"
SITE = "https://igos-nusantara.or.id"
ISO_URL = "https://r2.igos-nusantara.or.id/iso/beta/ign26-bayu-beta6.iso"
GITHUB_URL = "https://github.com/igos-nusantara/bayu/issues"
VIDEO_ID = "-EVUW16QUBw"
NIGHTLY_URL = "https://r2.igos-nusantara.or.id/iso/nightly/ign26-bayu-harian-latest.iso"

# Relative path from the page being rendered back to the site root: "" for the
# landing pages, "../" for docs/, "../../" for docs/id/.
_root = ""

_icon_cache: dict[str, str] = {}
_size_cache: dict[str, tuple[int, int]] = {}


def e(text) -> str:
    """Escape a value for HTML text or an attribute."""
    return html.escape(str(text), quote=True)


def asset(path: str) -> str:
    """A CSS/JS URL with a content hash appended.

    Hosts cache these aggressively (here.now and GitHub Pages both do), so
    without the hash a returning visitor keeps the previous stylesheet after
    a deploy. The query changes only when the file changes.
    """
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:8]
    return f"{_root}{path}?v={digest}"


def image_size(name: str) -> tuple[int, int]:
    """Intrinsic pixel size of a PNG or JPEG in assets/img.

    Every <img> carries width and height so the browser can reserve the right
    box before a lazy image arrives. Without them the figures collapse to zero
    height and the page jumps as you scroll.
    """
    if name in _size_cache:
        return _size_cache[name]
    data = (ROOT / IMG / name).read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
    elif data[:2] == b"\xff\xd8":
        i, w, h = 2, 0, 0
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker, seglen = data[i + 1], struct.unpack(">H", data[i + 2 : i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                break
            i += 2 + seglen
        if not w:
            raise SystemExit(f"could not read JPEG size: {name}")
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8 ":
            w, h = (x & 0x3FFF for x in struct.unpack("<HH", data[26:30]))
        elif kind == b"VP8L":
            b = int.from_bytes(data[21:25], "little")
            w, h = (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
        elif kind == b"VP8X":
            w, h = int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
        else:
            raise SystemExit(f"could not read WebP size: {name}")
    else:
        raise SystemExit(f"unsupported image: {name}")
    _size_cache[name] = (w, h)
    return w, h


def img(name: str, alt: str, *, lazy: bool = True, extra: str = "") -> str:
    """An <img> in assets/img, with intrinsic dimensions filled in."""
    w, h = image_size(name)
    load = (
        'loading="lazy" decoding="async"'
        if lazy
        else 'loading="eager" fetchpriority="high" decoding="async"'
    )
    return (
        f'<img src="{_root}{IMG}/{name}" alt="{e(alt)}" width="{w}" height="{h}" '
        f"{load}{(' ' + extra) if extra else ''} />"
    )


def icon(name: str, size: int = 20, cls: str = "") -> str:
    """Inline a Lucide icon, sized and stripped of its license comment."""
    if name not in _icon_cache:
        path = ICONS / f"{name}.svg"
        if not path.exists():
            raise SystemExit(f"missing icon: {path}")
        svg = path.read_text(encoding="utf-8")
        svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S).strip()
        svg = re.sub(r"\s+", " ", svg)
        _icon_cache[name] = svg
    svg = _icon_cache[name]
    svg = svg.replace('width="24"', f'width="{size}"', 1)
    svg = svg.replace('height="24"', f'height="{size}"', 1)
    svg = svg.replace("<svg", '<svg aria-hidden="true" focusable="false"', 1)
    if cls:
        svg = svg.replace('class="lucide', f'class="{cls} lucide', 1)
    return svg


def tile(name: str, color: str, size: int = 19) -> str:
    return (
        f'<span class="tile" style="background:var(--{e(color)})">'
        f"{icon(name, size)}</span>"
    )


def section_head(d: dict, extra: str = "") -> str:
    return (
        '<div class="sec-head">'
        f'<p class="eyebrow">{e(d["eyebrow"])}</p>'
        f'<h2 class="h-sec">{e(d["title"])}</h2>'
        f'<p class="lede">{e(d["body"])}</p>'
        f"{extra}</div>"
    )


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


def header(c: dict) -> str:
    n = c["nav"]
    links = "".join(
        f'<a href="{e(l["href"])}">{e(l["label"])}</a>' for l in n["links"]
    )
    en_cur = "true" if c["lang"] == "en" else "false"
    id_cur = "true" if c["lang"] == "id" else "false"
    en_href = c.get("en_href", "index.html")
    id_href = c.get("id_href", "id.html")
    return f"""<header class="site-header">
  <div class="wrap nav">
    <a class="brand" href="{e(c.get('home', c['page']))}">
      {img("logo.jpg", "", lazy=False)}
      <span>IGOS Nusantara</span>
    </a>
    <nav id="nav-links" class="nav-links" aria-label="{e(n['menu_label'])}">{links}</nav>
    <div class="nav-actions">
      <div class="lang">
        <a href="{en_href}" hreflang="en" aria-current="{en_cur}">EN</a>
        <a href="{id_href}" hreflang="id" aria-current="{id_cur}">ID</a>
      </div>
      <a class="nav-gh" href="{GITHUB_URL}" title="{e(n['github'])}" aria-label="{e(n['github'])}"><svg aria-hidden="true" focusable="false" width="18" height="18" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg></a>
      <a class="btn btn-primary btn-nav" href="#download">
        {icon('download', 15)}<span class="btn-text">{e(n['cta'])}</span>
      </a>
      <button class="nav-toggle" type="button" aria-expanded="false"
              aria-controls="nav-links" aria-label="{e(n['menu_label'])}">
        {icon('menu', 20)}
      </button>
    </div>
  </div>
</header>"""


def hero(c: dict) -> str:
    h, s = c["hero"], c["slider"]
    meta = "".join(f"<li>{e(m)}</li>" for m in h["meta"])
    slides = "".join(
        img(sl["img"], sl["label"], lazy=(i != 0))
        for i, sl in enumerate(s["slides"])
    )
    thumbs = "".join(
        '<button type="button" role="tab" aria-selected="{sel}" data-label="{lab}">'
        "<figure>{im}<figcaption>{num} · {lab}</figcaption></figure></button>".format(
            sel="true" if i == 0 else "false",
            lab=e(sl["label"]),
            im=img(sl["img"], ""),
            num=f"{i + 1:02d}",
        )
        for i, sl in enumerate(s["slides"])
    )
    return f"""<section class="hero">
  <div class="wrap">
    <p class="badge">{e(h['badge'])}</p>
    <h1>{e(h['h1'])}</h1>
    <p class="hero-sub">{e(h['sub'])}</p>
    <div class="hero-cta">
      <a class="btn btn-primary" href="#download">
        {icon('hard-drive-download', 18)}{e(h['cta_primary'])}
      </a>
      <a class="btn btn-ghost" href="#bayu">
        {icon('book-open', 18)}{e(h['cta_secondary'])}
      </a>
    </div>
    <ul class="hero-meta">{meta}</ul>

    <div class="slider" data-slider tabindex="0" role="group" aria-label="{e(s['label'])}">
      <div class="slider-stage">
        {slides}
        <button class="slider-btn slider-prev" type="button" aria-label="{e(s['prev'])}">
          {icon('chevron-left', 20)}
        </button>
        <button class="slider-btn slider-next" type="button" aria-label="{e(s['next'])}">
          {icon('chevron-right', 20)}
        </button>
        <p class="slider-counter" aria-hidden="true">
          <b><span data-slide-current>01</span> / <span data-slide-total>06</span></b>
          <span></span>
          <em style="font-style:normal" data-slide-label></em>
        </p>
      </div>
      <div class="slider-thumbs" role="tablist" aria-label="{e(s['label'])}">{thumbs}</div>
    </div>
  </div>
</section>"""


def stats(c: dict) -> str:
    items = "".join(
        f"<li><dl><dt>{e(s['value'])}</dt><dd>{e(s['label'])}</dd></dl></li>"
        for s in c["stats"]
    )
    return f'<section class="stats"><div class="wrap"><ul>{items}</ul></div></section>'


def codename(c: dict) -> str:
    d = c["codename"]
    return f"""<section class="section band-navy" id="codename">
  <div class="wrap">
    {section_head(d)}
    <div class="video">
      <iframe src="https://www.youtube-nocookie.com/embed/{VIDEO_ID}" title="{e(d['video_title'])}"
        loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" allowfullscreen
        referrerpolicy="strict-origin-when-cross-origin"></iframe>
    </div>
  </div>
</section>"""


def bayu(c: dict) -> str:
    d = c["bayu"]
    shots = "".join(
        f'<div class="shot">{img(s["img"], s["alt"])}</div>'
        for s in d["shots"]
    )
    cards = "".join(
        f'<article class="card">{tile(x["icon"], x["color"])}'
        f'<h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></article>'
        for x in d["components"]
    )
    w = d["wallpaper"]
    phases = "".join(
        f'<figure class="cap"><div class="shot">{img(p["img"], p["alt"])}</div>'
        f'<figcaption><strong>{e(p["name"])}</strong><br />{e(p["when"])}</figcaption></figure>'
        for p in w["phases"]
    )
    return f"""<section class="section band-light" id="bayu">
  <div class="wrap">
    {section_head(d)}
    <div class="grid g2" style="margin-top:48px">{shots}</div>
    <div class="grid g4" style="margin-top:48px">{cards}</div>
    <h3 class="h-sec is-sm" style="margin-top:64px">{e(w["title"])}</h3>
    <p class="lede">{e(w["body"])}</p>
    <div class="grid g4" style="margin-top:28px">{phases}</div>
  </div>
</section>"""


def pitaloka(c: dict) -> str:
    d = c["pitaloka"]
    swatches = [
        ("accent", "#3385FF"), ("success", "#2FB457"), ("warning", "#F0A030"),
        ("danger", "#E8453C"), ("tile-indigo", "#5B5BE6"), ("tile-cyan", "#17B8CE"),
        ("tile-purple", "#7B61FF"), ("tile-orange", "#F0893A"), ("tile-pink", "#D858C8"),
        ("tile-red", "#F0555E"), ("tile-green", "#2FB457"), ("tile-gray", "#7A818C"),
    ]
    radii = [("tile", 7), ("control", 8), ("menu", 10), ("card", 12), ("pill", 999)]

    files = "".join(
        '<div>{ic}<code>{f}</code><span>{t}</span></div>'.format(
            ic=icon("braces" if i == 0 else "chevron-right", 14),
            f=e(o["file"]),
            t=e(o["target"]),
        )
        for i, o in enumerate(d["outputs"])
    )
    sw = "".join(
        f'<div><b style="background:{hexv}"></b><small>{hexv}</small></div>'
        for _, hexv in swatches
    )
    tr = "".join(
        '<div><b style="font-size:{s}px;font-weight:{w}">Aa</b>'
        "<i>{n}</i><code>{sp}</code></div>".format(
            s=r["size"], w=r["weight"], n=e(r["name"]), sp=e(r["spec"])
        )
        for r in d["type_rows"]
    )
    rd = "".join(
        f'<div><b style="border-radius:{v}px"></b>'
        f"<small>{n} · {v}</small></div>"
        for n, v in radii
    )
    themes = "".join(
        '<figure><h3><b style="background:{dot}"></b>{name}<code>{tok}</code></h3>'
        '<div class="shot">{im}</div></figure>'.format(
            dot=t["dot"], name=e(t["name"]), tok=e(t["token"]), im=img(t["img"], t["alt"]),
        )
        for t in d["themes"]
    )
    return f"""<section class="section band-ink theme-dark" id="pitaloka">
  <div class="wrap">
    <div class="split">
      <div>
        {section_head(d)}
        <div class="filelist">{files}</div>
      </div>
      <div>
        <div class="spec"><h3>{e(d['colors_label'])}</h3><div class="swatches">{sw}</div></div>
        <div class="spec"><h3>{e(d['type_label'])}</h3><div class="typerows">{tr}</div></div>
        <div class="spec"><h3>{e(d['radius_label'])}</h3><div class="radii">{rd}</div></div>
      </div>
    </div>
    <div class="themes">{themes}</div>
    <p class="lede" style="margin-top:24px">{e(d['caption'])}</p>
  </div>
</section>"""


def store(c: dict) -> str:
    d = c["store"]
    counts = "".join(
        '<div><h3>{ic}{n}</h3><b>{v}</b><small>{lab}</small></div>'.format(
            ic=f'<span style="color:var(--{x["color"]});display:flex">{icon(x["icon"], 16)}</span>',
            n=e(x["name"]), v=e(x["value"]), lab=e(d["counts_label"]),
        )
        for x in d["counts"]
    )
    details = "".join(
        '<figure class="cap"><div class="shot">{im}</div>'
        "<figcaption>{cap}</figcaption></figure>".format(
            im=img(x["img"], x["alt"]), cap=e(x["caption"])
        )
        for x in d["details"]
    )
    feats = "".join(
        f'<article>{icon(f["icon"], 20)}<h3>{e(f["title"])}</h3><p>{e(f["body"])}</p></article>'
        for f in d["features"]
    )
    hs = d["hero_shot"]
    return f"""<section class="section band-card" id="store">
  <div class="wrap">
    <div class="store-head">
      {section_head(d)}
      <div class="counts">{counts}</div>
    </div>
    <div class="shot" style="margin-top:48px">
      {img(hs['img'], hs['alt'])}
    </div>
    <div class="grid g2" style="margin-top:24px">{details}</div>
    <div class="features">{feats}</div>
  </div>
</section>"""


def lapis(c: dict) -> str:
    d = c["lapis"]
    checks = "".join(
        f"<li>{icon('check', 16)}<span>{e(x)}</span></li>" for x in d["checks"]
    )
    layers = []
    for i, l in enumerate(d["layers"]):
        if i:
            layers.append(f'<div class="layer-arrow">{icon("chevron-down", 15)}</div>')
        layers.append(
            f'<div class="layer">{tile(l["icon"], l["color"], 16)}'
            f'<div><h4>{e(l["title"])}</h4><p>{e(l["body"])}</p></div></div>'
        )
    reqs = "".join(f"<li>{e(r)}</li>" for r in d["reqs"])
    return f"""<section class="section band-navy" id="lapis">
  <div class="wrap">
    <div class="split">
      <div>
        {section_head(d)}
        <ul class="checks" style="margin-top:20px">{checks}</ul>
      </div>
      <div class="stack">
        <h3>{e(d['stack_label'])}</h3>
        {''.join(layers)}
      </div>
    </div>
    <div class="reqbar">
      <h3>{e(d['req_label'])}</h3>
      <ul>{reqs}</ul>
      <a href="{e(d['repo_url'])}">{icon('external-link', 15)}{e(d['repo'])}</a>
    </div>
  </div>
</section>"""


def nabau(c: dict) -> str:
    d = c["nabau"]
    f = d["featured"]
    steps = "".join(
        f'<li><b>{e(s["n"])}</b><div><h3>{e(s["title"])}</h3><p>{e(s["body"])}</p></div></li>'
        for s in d["steps"]
    )
    strip = "".join(
        f'<figure>{img(t["img"], t["label"])}'
        f"<figcaption>{e(t['label'])}</figcaption></figure>"
        for t in d["strip"]
    )
    guar = "".join(
        f'<article class="card">{icon(g["icon"], 19, "accent-ico")}'
        f'<h3>{e(g["title"])}</h3><p>{e(g["body"])}</p></article>'
        for g in d["guarantees"]
    )
    return f"""<section class="section band-light" id="nabau">
  <div class="wrap">
    {section_head(d)}
    <div class="nabau-main">
      <figure class="cap">
        <div class="shot">{img(f['img'], f['alt'])}</div>
        <figcaption>{e(f['caption'])}</figcaption>
      </figure>
      <ul class="steps">{steps}</ul>
    </div>
    <div class="strip">{strip}</div>
    <div class="grid g4" style="margin-top:48px">{guar}</div>
  </div>
</section>"""


def more(c: dict) -> str:
    d = c["more"]
    items = "".join(
        f'<article class="more-card">{tile(x["icon"], x["color"], 18)}'
        f'<div><h3>{e(x["title"])}</h3><p>{e(x["body"])}</p></div></article>'
        for x in d["items"]
    )
    return f"""<section class="section band-card">
  <div class="wrap">
    <div class="sec-head">
      <p class="eyebrow">{e(d['eyebrow'])}</p>
      <h2 class="h-sec is-sm">{e(d['title'])}</h2>
    </div>
    <div class="more-grid">{items}</div>
  </div>
</section>"""


def download(c: dict) -> str:
    d = c["download"]
    facts = "".join(f"<div><dt>{e(x['k'])}</dt><dd>{e(x['v'])}</dd></div>" for x in d["facts"])
    cmds = "".join(f"<p>{e(x)}</p>" for x in d["cmds"])
    sysr = "".join(f"<div><dt>{e(x['k'])}</dt><dd>{e(x['v'])}</dd></div>" for x in d["sys"])
    return f"""<section class="section download" id="download">
  <div class="wrap">
    <p class="eyebrow">{e(d['eyebrow'])}</p>
    <h2 class="h-sec">{e(d['title'])}</h2>
    <p class="lede" style="max-width:56ch">{e(d['sub'])}</p>

    <div class="iso">
      <div>
        <div class="iso-head">
          <h3>{e(d['name'])}</h3><span class="tag">{e(d['tag'])}</span>
        </div>
        <p>{e(d['body'])}</p>
        <dl>{facts}</dl>
      </div>
      <div class="iso-action">
        <a class="btn btn-primary" href="{ISO_URL}">
          {icon('hard-drive-download', 18)}{e(d['button'])}
        </a>
        <code>{ISO_URL}</code>
        <a class="btn btn-ghost" href="{NIGHTLY_URL}">
          {icon('hard-drive-download', 18)}{e(d['nightly_button'])}
        </a>
        <small>{e(d['nightly_note'])}</small>
        <small>{e(d['host_note'])}</small>
      </div>
    </div>

    <div class="dl-bottom">
      <div class="panel">
        <h3>{e(d['cmd_title'])}</h3>
        <div class="term" id="dl-cmds">
          <button class="copy" type="button" data-copy="dl-cmds"
                  data-copied="{e(d['copied'])}">{e(d['copy'])}</button>
          {cmds}
        </div>
        <small>{e(d['cmd_note'])}</small>
      </div>
      <div class="panel sysreq">
        <h3>{e(d['sys_title'])}</h3>
        <dl>{sysr}</dl>
      </div>
    </div>
  </div>
</section>"""


def footer(c: dict) -> str:
    d = c["footer"]
    cols = "".join(
        "<div><h3>{h}</h3><ul>{items}</ul></div>".format(
            h=e(col["head"]),
            items="".join(
                f'<li><a href="{e(i["href"])}">{e(i["label"])}</a></li>'
                for i in col["items"]
            ),
        )
        for col in d["columns"]
    )
    links = "".join(f'<a href="{e(l["href"])}">{e(l["label"])}</a>' for l in d["links"])
    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="foot-top">
      <div class="foot-brand">
        <a class="brand" href="{e(c.get('home', c['page']))}">
          {img("logo.jpg", "")}
          <span>IGOS Nusantara<small>{e(d['tagline'])}</small></span>
        </a>
        <p>{e(d['about'])}</p>
      </div>
      <div class="foot-cols">{cols}</div>
    </div>
    <div class="foot-bottom">
      <p>{e(d['legal'])}</p>
      <nav>{links}</nav>
    </div>
  </div>
</footer>"""


# --------------------------------------------------------------------------


def head(lang: str, title: str, description: str, canonical: str, other: str) -> str:
    """Everything from the doctype to the opening <body>."""
    other_lang = "id" if lang == "en" else "en"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{e(description)}" />
<link rel="canonical" href="{canonical}" />
<link rel="alternate" hreflang="{other_lang}" href="{other}" />
<link rel="alternate" hreflang="{lang}" href="{canonical}" />
<link rel="icon" href="{_root}{IMG}/logo.jpg" />
<meta name="theme-color" content="#07121f" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="{'en_US' if lang == 'en' else 'id_ID'}" />
<meta property="og:url" content="{canonical}" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(description)}" />
<meta property="og:image" content="{SITE}/{IMG}/og.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:image" content="{SITE}/{IMG}/og.jpg" />
<meta name="twitter:card" content="summary_large_image" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="{asset("assets/css/pitaloka.css")}" />
<link rel="stylesheet" href="{asset("assets/css/site.css")}" />
</head>
<body>"""


def render(c: dict) -> str:
    m = c["meta"]
    canonical = f"{SITE}/{c['page']}" if c["page"] != "index.html" else f"{SITE}/"
    other = f"{SITE}/{c['other_page']}" if c["other_page"] != "index.html" else f"{SITE}/"
    return f"""{head(c['lang'], m['title'], m['description'], canonical, other)}
<a class="skip-link" href="#main">{e(c['skip'])}</a>
{header(c)}
<main id="main">
{hero(c)}
{stats(c)}
{codename(c)}
{bayu(c)}
{pitaloka(c)}
{store(c)}
{lapis(c)}
{nabau(c)}
{more(c)}
{download(c)}
</main>
{footer(c)}
<script src="{asset("assets/js/site.js")}" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Docs: content/docs/{en,id}.json -> docs/*.html and docs/id/*.html
# --------------------------------------------------------------------------


def inline(text: str) -> str:
    """Escape text, then allow `code`, **bold** and [label](href)."""
    t = e(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)


def plain(text: str) -> str:
    """The same text with the inline markup removed, for meta tags."""
    text = re.sub(r"\[([^\]]+)\]\([^)\s]+\)", r"\1", text)
    return text.replace("`", "").replace("**", "")


def shot(name: str, alt: str, caption: str = "") -> str:
    """A screenshot that opens at full size when clicked."""
    cap = f"<figcaption>{inline(caption)}</figcaption>" if caption else ""
    return (
        f'<figure class="doc-shot"><a href="{_root}{IMG}/{e(name)}">'
        f"{img(name, alt)}</a>{cap}</figure>"
    )


def block(b: dict, n: int, L: dict) -> str:
    """One content block. n numbers the copy buttons on the page."""
    if "p" in b:
        return f"<p>{inline(b['p'])}</p>"
    if "h" in b:
        return f'<h2 id="{e(b["id"])}">{e(b["h"])}</h2>'
    if "list" in b:
        return "<ul class=\"doc-list\">" + "".join(f"<li>{inline(x)}</li>" for x in b["list"]) + "</ul>"
    if "steps" in b:
        items = []
        for s in b["steps"]:
            s = {"t": s} if isinstance(s, str) else s
            pic = shot(s["img"], s["alt"]) if "img" in s else ""
            items.append(f"<li><p>{inline(s['t'])}</p>{pic}</li>")
        return f'<ol class="doc-steps">{"".join(items)}</ol>'
    if "img" in b:
        return shot(b["img"], b["alt"], b.get("caption", ""))
    if "cmd" in b or "code" in b:
        # cmd lines get a "$" prompt; code is file content and gets none.
        lines = "".join(f"<p>{e(x)}</p>" for x in b.get("cmd", b.get("code")))
        cls = "term doc-term" if "cmd" in b else "term doc-term is-code"
        return (
            f'<div class="{cls}" id="cmd-{n}"><button class="copy" type="button" '
            f'data-copy="cmd-{n}" data-copied="{e(L["copied"])}">{e(L["copy"])}</button>'
            f"{lines}</div>"
        )
    if "note" in b:
        warn = b.get("kind") == "warn"
        ico = icon("triangle-alert" if warn else "info", 18)
        return f'<aside class="note{" note-warn" if warn else ""}">{ico}<p>{inline(b["note"])}</p></aside>'
    if "table" in b:
        head = "".join(f"<th>{e(x)}</th>" for x in b["head"])
        rows = "".join(
            "<tr>" + "".join(f"<td>{inline(x)}</td>" for x in r) + "</tr>" for r in b["table"]
        )
        return f'<div class="doc-table"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    if "cards" in b:
        cards = "".join(
            f'<a class="doc-card" href="{e(x["href"])}">{tile(x["icon"], x["color"], 18)}'
            f'<span><b>{e(x["title"])}</b><small>{e(x["body"])}</small></span></a>'
            for x in b["cards"]
        )
        return f'<div class="doc-cards">{cards}</div>'
    raise SystemExit(f"unknown docs block: {sorted(b)}")


def doc_page(d: dict, site: dict, i: int) -> str:
    """One docs page. site is the landing content, for header and footer."""
    pages, L = d["pages"], d["labels"]
    p = pages[i]
    out = lambda slug: f"{slug}.html"  # pages of one language share a folder
    landing = site["page"]

    def link(href: str) -> str:
        if href.startswith("#"):
            return f"{_root}{landing}{href}"
        return href if href.startswith("http") else f"{_root}{href}"

    # The landing page's header and footer, with links made relative to here.
    c = json.loads(json.dumps(site))
    for l in c["nav"]["links"]:
        l["href"] = link(l["href"])
    for col in c["footer"]["columns"]:
        for it in col["items"]:
            it["href"] = link(it["href"])
    en_dir, id_dir = ("", "id/") if d["lang"] == "en" else ("../", "")
    c.update(home=f"{_root}{landing}", en_href=f"{en_dir}{out(p['slug'])}", id_href=f"{id_dir}{out(p['slug'])}")

    current = ' aria-current="page"'
    nav = "".join(
        f'<li><a href="{out(x["slug"])}"{current if j == i else ""}>{e(x["nav"])}</a></li>'
        for j, x in enumerate(pages)
    )
    pager = ""
    if i > 0:
        pr = pages[i - 1]
        pager += f'<a class="prev" href="{out(pr["slug"])}"><small>{icon("arrow-left", 14)}{e(L["prev"])}</small>{e(pr["nav"])}</a>'
    if i + 1 < len(pages):
        nx = pages[i + 1]
        pager += f'<a class="next" href="{out(nx["slug"])}"><small>{e(L["next"])}{icon("arrow-right", 14)}</small>{e(nx["nav"])}</a>'
    body = "".join(block(b, n, L) for n, b in enumerate(p["blocks"]))

    path = f"{d['dir']}{'' if p['slug'] == 'index' else out(p['slug'])}"
    other_dir = "docs/id/" if d["lang"] == "en" else "docs/"
    other = f"{other_dir}{'' if p['slug'] == 'index' else out(p['slug'])}"
    title = f"{p['title']} · {L['site']}"
    return f"""{head(d['lang'], title, plain(p['lede']), f"{SITE}/{path}", f"{SITE}/{other}")}
<a class="skip-link" href="#main">{e(site['skip'])}</a>
{header(c)}
<div class="wrap docs">
  <details class="docs-nav">
    <summary>{icon("book-open", 16)}{e(L['menu'])}</summary>
    <p class="eyebrow">{e(L['site'])}</p>
    <ul>{nav}</ul>
  </details>
  <main id="main" class="doc">
    <p class="eyebrow">{e(L['site'])}</p>
    <h1>{e(p['title'])}</h1>
    <p class="lede">{inline(p['lede'])}</p>
    {body}
    <nav class="doc-pager" aria-label="{e(L['pager'])}">{pager}</nav>
  </main>
</div>
{footer(c)}
<script src="{asset("assets/js/site.js")}" defer></script>
</body>
</html>
"""


def main() -> int:
    global _root
    sites = {}
    for name in ("en", "id"):
        c = json.loads((ROOT / "content" / f"{name}.json").read_text(encoding="utf-8"))
        sites[name] = c
        out = ROOT / c["page"]
        out.write_text(render(c), encoding="utf-8")
        print(f"wrote {out.name}  ({out.stat().st_size // 1024} KB)")
    for name in ("en", "id"):
        d = json.loads((ROOT / "content" / "docs" / f"{name}.json").read_text(encoding="utf-8"))
        folder = ROOT / d["dir"]
        folder.mkdir(parents=True, exist_ok=True)
        _root = "../" * d["dir"].count("/")
        for i, p in enumerate(d["pages"]):
            (folder / f"{p['slug']}.html").write_text(doc_page(d, sites[name], i), encoding="utf-8")
        print(f"wrote {d['dir']}  ({len(d['pages'])} pages)")
        _root = ""
    return 0


if __name__ == "__main__":
    sys.exit(main())
