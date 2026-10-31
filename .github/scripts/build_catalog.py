#!/usr/bin/env python3
"""Build the auto-categorized repository catalog for the profile README.

What it does, in order:
  1. Lists every public repo of the owner from the GitHub REST API.
  2. Classifies each one (see `classify`): explicit entry in data/catalog.json,
     then a `cat-<id>` topic, then fork / tiny-repo rules, then keyword scoring,
     then the `new` bucket. A repo is never silently dropped: if nothing matches
     it lands in a visible "Just shipped" section with a NEW badge.
  3. Writes one animated SVG card per repo, a header per category, an overview
     chart and the flagship reel into assets/generated/.
  4. Replaces the block between <!-- CATALOG:START --> and <!-- CATALOG:END -->
     in README.md, and the block between // CATALOG:START and // CATALOG:END in
     docs/index.html so the 3D graph picks up new repos too.

Standard library only, so the Action needs no pip install.

Offline / test usage:
  python build_catalog.py --fixture repos.json --readme-dir readmes/
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data" / "catalog.json"
OUT = ROOT / "assets" / "generated"
README = ROOT / "README.md"
GRAPH = ROOT / "docs" / "index.html"
RAW = "https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"

LANG_COLORS = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a", "HTML": "#e34c26", "Java": "#b07219", "C++": "#f34b7d",
    "Go": "#00ADD8", "Rust": "#dea584", "Shell": "#89e051", "CSS": "#563d7c",
}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# --------------------------------------------------------------------------- io
def gh_get(url: str, token: str | None, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "profile-catalog"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def fetch_repos(owner: str, token: str | None) -> list[dict]:
    repos, page = [], 1
    while True:
        data = json.loads(gh_get(
            f"https://api.github.com/users/{owner}/repos?per_page=100&page={page}&type=owner", token))
        repos += data
        if len(data) < 100:
            return repos
        page += 1


def fetch_readme(owner: str, repo: str, token: str | None) -> str:
    try:
        body = json.loads(gh_get(f"https://api.github.com/repos/{owner}/{repo}/readme", token))
        return base64.b64decode(body["content"]).decode("utf-8", "replace")
    except (urllib.error.HTTPError, KeyError, ValueError):
        return ""


# --------------------------------------------------------------- text helpers
def readme_summary(md: str, limit: int = 140) -> str:
    """First real sentence of a README: no badges, HTML, tables, headings or credits."""
    md = re.sub(r"```.*?```", " ", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    for line in md.splitlines():
        s = re.sub(r"<[^>]+>", " ", line)
        s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"[*_`#>|]", "", s).strip()
        s = re.sub(r"\s+", " ", s)
        if len(s) < 45 or re.match(r"(?i)(built by|live repo|course|table of contents|---)", s):
            continue
        if not re.search(r"[a-z]{3}", s) or s.count("─") or s.count("█"):
            continue
        return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "..."
    return ""


def pretty_name(name: str) -> str:
    s = re.sub(r"[-_]+", " ", name).strip()
    return s[:1].upper() + s[1:]


def wrap(text: str, width: int, lines: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            out.append(cur)
            cur = w
            if len(out) == lines:
                break
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and " ".join(out) != " ".join(words):
        out[-1] = out[-1][: width - 3].rstrip(" ,.;:") + "..."
    return out


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- classification
def keyword_score(text: str, keywords: list[str], cap: int = 1) -> int:
    """Distinct keyword hits; with cap > 1, repeated mentions count up to `cap` each,
    so a README that talks about patients for pages outweighs one passing mention."""
    total = 0
    for k in keywords:
        n = len(re.findall(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", text))
        total += min(n, cap)
    return total


def classify(repo: dict, readme: str, cat: dict) -> tuple[str, str]:
    """Return (category_id, reason). The reason is written to docs/catalog.json so
    a wrong placement can be traced to the rule that caused it."""
    ids = {c["id"] for c in cat["categories"]}
    rules = cat["rules"]
    entry = cat["repos"].get(repo["name"], {})
    if entry.get("category") in ids:
        return entry["category"], "catalog.json"
    for t in repo.get("topics") or []:
        if t.startswith("cat-") and t[4:] in ids:
            return t[4:], f"topic {t}"
    if repo.get("fork"):
        return rules["forks_category"], "fork"
    if repo.get("size", 0) < rules["tiny_repo_kb"] and not readme.strip():
        return rules["tiny_category"], "tiny repo, no README"

    name = repo["name"].lower().replace("-", " ").replace("_", " ")
    desc = (repo.get("description") or "").lower()
    topics = " ".join(repo.get("topics") or []).lower().replace("-", " ")
    body = readme[:15000].lower()
    scores = []
    for c in cat["categories"]:
        kw = c.get("keywords") or []
        if not kw:
            continue
        s = (3 * keyword_score(name, kw) + 4 * keyword_score(topics, kw)
             + 2 * keyword_score(desc, kw) + keyword_score(body, kw, cap=rules.get("body_cap", 1)))
        scores.append((s, c["id"]))
    scores.sort(reverse=True)
    (top, best), (second, runner) = scores[0], scores[1]
    if top < rules["min_keyword_score"]:
        return rules["fallback_category"], f"no rule matched (best {best} {top})"
    # A close call is parked in the visible `new` bucket instead of guessed: a
    # confidently wrong section is worse than an honest "not sorted yet".
    if top < rules.get("min_margin", 1.0) * second:
        return rules["fallback_category"], f"ambiguous ({best} {top} vs {runner} {second})"
    return best, f"keywords ({best} {top} vs {runner} {second})"


# ------------------------------------------------------------------------- svg
def age_days(iso: str, now: dt.datetime) -> int:
    return (now - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days


def card_footer(item: dict, lang: str, lcol: str, color: str) -> tuple[str, str]:
    """Footer row: language, stars, date, live marker, metric chip on the right.

    Widths are estimated per character. A metric is never truncated, because a
    clipped number misstates the result. To make room the date goes first, then
    the word "live" (the green dot stays); if it still does not fit the chip is
    omitted and the build log says so.
    """
    cw, right = 6.4, 404
    m = item.get("metric") or ""
    chip_w = len(m) * 6.3 + 16 if m else 0
    for show_date, live_word in ((True, True), (False, True), (False, False)):
        parts, x = [], 40
        parts.append(f'<text x="{x}" y="111" class="f">{esc(lang)}</text>')
        x += len(lang) * cw + 12
        parts.append(f'<text x="{x:.0f}" y="111" class="f">&#9733; {item["stars"]}</text>')
        x += (len(str(item["stars"])) + 2) * cw + 10
        if show_date:
            parts.append(f'<text x="{x:.0f}" y="111" class="f">{esc(item["updated"])}</text>')
            x += len(item["updated"]) * cw + 10
        if item.get("demo"):
            parts.append(f'<circle cx="{x + 4:.0f}" cy="107" r="3.5" fill="#3fb950"/>')
            x += 12
            if live_word:
                parts.append(f'<text x="{x:.0f}" y="111" class="f" style="fill:#3fb950">live</text>')
                x += 32
        if not m or right - x >= chip_w:
            break
    footer = f'<circle cx="30" cy="107" r="5" fill="{lcol}"/>' + "".join(parts)
    metric = ""
    if m and right - x >= chip_w:
        metric = (f'<rect x="{right - chip_w:.0f}" y="96" width="{chip_w:.0f}" height="20" rx="10" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-opacity=".5"/>'
                  f'<text x="{right - chip_w / 2:.0f}" y="110" text-anchor="middle" class="m" fill="{color}">{esc(m)}</text>')
    elif m:
        print(f"warning: metric for {item['name']!r} does not fit its card and was omitted: {m!r}", file=sys.stderr)
    return footer, metric


def card_svg(item: dict, color: str) -> str:
    """420x128 repo card. Dark by design so it reads on both GitHub themes."""
    lines = wrap(item["blurb"] or "No description yet.", 58, 2)
    lang = {"Jupyter Notebook": "Jupyter"}.get(item["language"], item["language"]) or ("Fork" if item["fork"] else "Docs")
    lcol = LANG_COLORS.get(item["language"] or "", "#8b949e")
    badges = ""
    x = 24 + min(len(item["title"]), 30) * 9.2 + 10
    if item["is_new"]:
        badges += (f'<g class="pop"><rect x="{x:.0f}" y="16" width="38" height="18" rx="9" fill="#ffa657"/>'
                   f'<text x="{x + 19:.0f}" y="29" text-anchor="middle" class="b">NEW</text></g>')
    pulse = ""
    if item["is_active"]:
        pulse = ('<circle cx="398" cy="24" r="4" fill="#3fb950"/>'
                 '<circle cx="398" cy="24" r="4" fill="none" stroke="#3fb950" class="pulse"/>')
    footer, metric = card_footer(item, lang, lcol, color)
    blurb = "".join(f'<text x="24" y="{58 + i * 18}" class="d">{esc(l)}</text>' for i, l in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="420" height="128" viewBox="0 0 420 128" role="img" aria-label="{esc(item["title"])}">
<style>
text{{font-family:{FONT}}}
.t{{font-size:16px;font-weight:600;fill:#e6edf3}} .d{{font-size:12.5px;fill:#9198a1}}
.f{{font-size:12px;fill:#9198a1}} .m{{font-size:11px;font-weight:600}} .b{{font-size:10px;font-weight:700;fill:#0d1117}}
.card{{animation:rise .7s cubic-bezier(.2,.7,.2,1) both}}
.bar{{transform-origin:0 0;animation:grow 1.1s .25s cubic-bezier(.2,.7,.2,1) both}}
.pulse{{transform-origin:398px 24px;animation:ping 1.8s ease-out infinite}}
.pop{{animation:pop 2.4s ease-in-out infinite}}
.sheen{{animation:sheen 6s 1.2s ease-in-out infinite}}
@keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes ping{{0%{{transform:scale(1);opacity:.9}}100%{{transform:scale(3.2);opacity:0}}}}
@keyframes pop{{0%,100%{{opacity:1}}50%{{opacity:.55}}}}
@keyframes sheen{{0%{{transform:translateX(-160px)}}35%,100%{{transform:translateX(620px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs><clipPath id="c"><rect x=".5" y=".5" width="419" height="127" rx="12"/></clipPath>
<linearGradient id="s" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<g class="card"><g clip-path="url(#c)">
<rect width="420" height="128" fill="#0d1117"/>
<rect class="sheen" x="0" y="0" width="120" height="128" fill="url(#s)"/>
<rect class="bar" x="0" y="0" width="5" height="128" fill="{color}"/>
</g>
<rect x=".5" y=".5" width="419" height="127" rx="12" fill="none" stroke="#30363d"/>
<text x="24" y="30" class="t">{esc(item["title"][:30])}</text>{badges}{pulse}
{blurb}
{footer}
{metric}</g></svg>'''


def header_svg(c: dict, count: int) -> str:
    color = c["color"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="54" viewBox="0 0 860 54" role="img" aria-label="{esc(c["label"])}">
<style>
text{{font-family:{FONT}}} .h{{font-size:19px;font-weight:700;fill:{color}}} .s{{font-size:12.5px;fill:#8b949e}}
.n{{font-size:12px;font-weight:700;fill:{color}}}
.line{{animation:draw 1.4s cubic-bezier(.2,.7,.2,1) both}}
.run{{animation:run 4.5s linear infinite}}
.in{{animation:in .6s both}}
@keyframes draw{{from{{stroke-dashoffset:860}}to{{stroke-dashoffset:0}}}}
@keyframes run{{from{{transform:translateX(-80px)}}to{{transform:translateX(880px)}}}}
@keyframes in{{from{{opacity:0;transform:translateX(-10px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<g class="in"><rect x="2" y="9" width="14" height="14" rx="4" fill="{color}"/>
<text x="26" y="22" class="h">{esc(c["label"])}</text>
<text x="26" y="41" class="s">{esc(c["blurb"])}</text></g>
<rect x="{858 - (len(str(count)) + 6) * 8.2:.0f}" y="8" width="{(len(str(count)) + 6) * 8.2:.0f}" height="20" rx="10" fill="{color}" fill-opacity=".14"/>
<text x="{858 - (len(str(count)) + 6) * 4.1:.0f}" y="22" text-anchor="middle" class="n">{count} repo{"s" if count != 1 else ""}</text>
<line class="line" x1="0" y1="52" x2="860" y2="52" stroke="{color}" stroke-opacity=".45" stroke-width="1.5" stroke-dasharray="860"/>
<rect class="run" x="0" y="51" width="70" height="3" rx="1.5" fill="{color}"/>
</svg>'''


def overview_svg(groups: list[tuple[dict, list]], total: int, stamp: str) -> str:
    rows = [(c, len(items)) for c, items in groups if items and c.get("layout") != "chips"]
    extra = [(c, len(items)) for c, items in groups if items and c.get("layout") == "chips"]
    work = sum(n for _, n in rows)
    note = ", plus " + " and ".join(f"{n} {c.get('noun', c['id'])}" for c, n in extra) if extra else ""
    h = 64 + len(rows) * 30
    mx = max(n for _, n in rows)
    body = []
    for i, (c, n) in enumerate(rows):
        y = 52 + i * 30
        w = 430 * n / mx
        body.append(
            f'<g style="animation-delay:{i * .12:.2f}s" class="row">'
            f'<text x="0" y="{y + 13}" class="l">{esc(c["label"])}</text>'
            f'<rect x="300" y="{y}" width="430" height="18" rx="9" fill="#161b22"/>'
            f'<rect x="300" y="{y}" width="{w:.1f}" height="18" rx="9" fill="{c["color"]}" class="bar" style="animation-delay:{.2 + i * .12:.2f}s"/>'
            f'<text x="{300 + w + 10:.1f}" y="{y + 13}" class="v" fill="{c["color"]}">{n}</text></g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="{h}" viewBox="0 0 860 {h}" role="img" aria-label="{total} repositories by area">
<style>
text{{font-family:{FONT}}} .k{{font-size:28px;font-weight:800;fill:#e6edf3}} .ks{{font-size:13px;fill:#8b949e}}
.l{{font-size:13px;fill:#c9d1d9}} .v{{font-size:13px;font-weight:700}}
.row{{animation:fade .5s both}} .bar{{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.7,.2,1) both}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}} @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<rect width="860" height="{h}" fill="#0d1117" rx="14"/>
<g transform="translate(28,0)">
<text x="0" y="36" class="k">{work}</text><text x="{18 * len(str(work)) + 8}" y="36" class="ks">original projects in {len(rows)} areas{esc(note)}. Sorted automatically, updated {esc(stamp)}.</text>
{"".join(body)}</g></svg>'''


def reel_svg(slides: list[dict]) -> str:
    """Auto-playing reel, one flagship per 4s slide, pure CSS so GitHub renders it."""
    n, per = len(slides), 4
    total = n * per
    on, off = 100 / n, 100 / n
    fade = 1.5
    groups = []
    for i, s in enumerate(slides):
        color = s["color"]
        lines = wrap(s["blurb"], 64, 2)
        groups.append(f'''<g class="slide" style="animation-delay:{i * per}s">
<rect x="40" y="40" width="{len(s["cat_label"]) * 7 + 24:.0f}" height="24" rx="12" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-opacity=".5"/>
<text x="52" y="57" class="chip" fill="{color}">{esc(s["cat_label"])}</text>
<text x="40" y="112" class="title">{esc(s["title"])}</text>
{"".join(f'<text x="40" y="{146 + j * 22}" class="desc">{esc(l)}</text>' for j, l in enumerate(lines))}
<text x="40" y="222" class="metric" fill="{color}">{esc(s.get("metric") or s["language"] or "")}</text>
<rect x="40" y="244" width="780" height="3" rx="1.5" fill="#21262d"/>
<rect x="40" y="244" width="780" height="3" rx="1.5" fill="{color}" class="prog" style="animation-delay:{i * per}s"/>
<circle cx="760" cy="120" r="58" fill="none" stroke="{color}" stroke-opacity=".25" stroke-width="2"/>
<circle cx="760" cy="120" r="58" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-dasharray="365" class="ring" style="animation-delay:{i * per}s" transform="rotate(-90 760 120)"/>
<text x="760" y="128" text-anchor="middle" class="idx" fill="{color}">{i + 1:02d}</text>
</g>''')
    dots = "".join(
        f'<circle cx="{430 - (n - 1) * 9 + i * 18}" cy="276" r="4" fill="#30363d"/>'
        f'<circle cx="{430 - (n - 1) * 9 + i * 18}" cy="276" r="4" fill="#e6edf3" class="dot" style="animation-delay:{i * per}s"/>'
        for i in range(n))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="292" viewBox="0 0 860 292" role="img" aria-label="Animated reel of flagship projects">
<style>
text{{font-family:{FONT}}}
.chip{{font-size:12px;font-weight:700;letter-spacing:.3px}} .title{{font-size:38px;font-weight:800;fill:#e6edf3}}
.desc{{font-size:16px;fill:#9198a1}} .metric{{font-size:17px;font-weight:700}} .idx{{font-size:26px;font-weight:800}}
.slide,.dot{{opacity:0;animation:show {total}s infinite}}
.prog{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:prog {total}s linear infinite}}
.ring{{stroke-dashoffset:365;animation:ring {total}s ease-out infinite}}
@keyframes show{{0%{{opacity:0}}{fade:.2f}%{{opacity:1}}{on - fade:.2f}%{{opacity:1}}{on:.2f}%,100%{{opacity:0}}}}
@keyframes prog{{0%{{transform:scaleX(0)}}{on:.2f}%,100%{{transform:scaleX(1)}}}}
@keyframes ring{{0%{{stroke-dashoffset:365}}{on * .6:.2f}%,100%{{stroke-dashoffset:60}}}}
@media (prefers-reduced-motion:reduce){{.slide{{animation:none}}.slide:first-of-type{{opacity:1}}}}
</style>
<rect width="860" height="292" rx="16" fill="#0d1117"/><rect x=".5" y=".5" width="859" height="291" rx="16" fill="none" stroke="#30363d"/>
{"".join(groups)}
{dots}
</svg>'''


# ---------------------------------------------------------------------- render
def replace_block(text: str, start: str, end: str, new: str, where: str) -> str:
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        raise SystemExit(f"error: markers {start} / {end} not found in {where}")
    return pat.sub(lambda _: f"{start}\n{new}\n{end}", text, count=1)


def build(repos: list[dict], readmes: dict[str, str], cat: dict, now: dt.datetime,
          raw_base: str, write: bool = True) -> dict:
    owner = cat["owner"]
    cats = {c["id"]: c for c in cat["categories"]}
    items, report = [], []
    for r in repos:
        if r["name"] in cat["hide"] or r.get("private") or r.get("archived"):
            continue
        md = readmes.get(r["name"], "")
        cid, why = classify(r, md, cat)
        e = cat["repos"].get(r["name"], {})
        blurb = e.get("blurb") or r.get("description") or readme_summary(md)
        items.append({
            "name": r["name"], "title": e.get("title") or (r["name"] if r.get("fork") else pretty_name(r["name"])),
            "category": cid, "reason": why, "blurb": blurb or "",
            "metric": e.get("metric"), "demo": e.get("demo") or (r.get("homepage") or None),
            "loc": e.get("loc"), "language": r.get("language"), "fork": r.get("fork", False),
            "stars": r.get("stargazers_count", 0), "pushed": r["pushed_at"],
            "updated": dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")).strftime("%b %Y"),
            "is_new": age_days(r["created_at"], now) <= cat["new_badge_days"] and not r.get("fork"),
            "is_active": age_days(r["pushed_at"], now) <= cat["active_days"] and not r.get("fork"),
            "url": r["html_url"],
        })
        report.append((r["name"], cid, why))
    items.sort(key=lambda i: i["pushed"], reverse=True)

    order = ["new"] + [c["id"] for c in cat["categories"] if c["id"] != "new"]
    groups = [(cats[cid], [i for i in items if i["category"] == cid]) for cid in order]
    stamp = now.strftime("%b %d, %Y")

    files: dict[str, str] = {}
    for i in items:
        files[f"card-{slug(i['name'])}.svg"] = card_svg(i, cats[i["category"]]["color"])
    for c, its in groups:
        if its:
            files[f"head-{c['id']}.svg"] = header_svg(c, len(its))
    files["overview.svg"] = overview_svg(groups, len(items), stamp)
    by_name = {i["name"]: i for i in items}
    slides = [dict(by_name[n], color=cats[by_name[n]["category"]]["color"],
                   cat_label=cats[by_name[n]["category"]]["label"])
              for n in cat.get("reel", []) if n in by_name]
    if slides:
        files["reel.svg"] = reel_svg(slides)

    # Cache-busting query: camo caches images, so a changed card must change URL.
    ver = now.strftime("%Y%m%d%H")
    img = lambda f: f"{raw_base}/assets/generated/{f}?v={ver}"  # noqa: E731

    md = [f"<!-- generated by .github/scripts/build_catalog.py on {now.isoformat(timespec='minutes')} - do not edit by hand -->",
          '<div align="center">', "", f'<img src="{img("overview.svg")}" width="100%" alt="{len(items)} repositories by area"/>', "", "</div>", ""]
    for c, its in groups:
        if not its:
            continue
        md += [f'<img src="{img("head-" + c["id"] + ".svg")}" width="100%" alt="{esc(c["label"])}"/>', ""]
        if c.get("layout") == "chips":
            chips = []
            for i in its:
                chips.append(f'<a href="{i["url"]}"><img src="https://img.shields.io/badge/{shield_label(i["title"])}-{c["color"][1:]}?style=flat-square&labelColor=161b22" alt="{esc(i["title"])}"/></a>')
            md += ['<p align="left">', " ".join(chips), "</p>", ""]
        else:
            md += ['<p align="center">']
            for i in its:
                md += [f'<a href="{i["url"]}"><img src="{img("card-" + slug(i["name"]) + ".svg")}" width="49%" alt="{esc(i["title"])}: {esc(i["blurb"])}"/></a>']
            md += ["</p>", ""]
    catalog_md = "\n".join(md)

    # Reel + demo strip. Generated too, so changing `reel` or `demos` in
    # catalog.json is the only edit needed.
    reel = ['<div align="center">', ""]
    if slides:
        reel += [f'<img src="{img("reel.svg")}" width="100%" alt="Animated reel: {esc(", ".join(s["title"] for s in slides))}"/>', ""]
        pills = []
        for s in slides:
            pills.append(f'<a href="{s["url"]}"><img src="https://img.shields.io/badge/{shield_label(s["title"])}-%E2%86%97-{s["color"][1:]}?style=for-the-badge&labelColor=0d1117" alt="Open {esc(s["title"])}"/></a>')
        reel += [" ".join(pills), ""]
    demos = [d for d in cat.get("demos", []) if d["repo"] in by_name and (ROOT / d["file"]).exists()]
    if demos:
        reel += ["<table><tr>"]
        for d in demos:
            reel += [f'<td align="center" width="{100 // len(demos)}%"><a href="{by_name[d["repo"]]["url"]}">'
                     f'<img src="{raw_base}/{d["file"]}" width="100%" alt="{esc(d["caption"])}"/></a>'
                     f'<br/><sub>{esc(d["caption"])}</sub></td>']
        reel += ["</tr></table>", ""]
    reel += ["</div>"]
    reel_md = "\n".join(reel)

    graph_js = render_graph(cat, items)
    data = {"generated": now.isoformat(timespec="minutes"),
            "repos": [{k: i[k] for k in ("name", "title", "category", "reason", "blurb", "url", "demo")} for i in items]}

    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        keep = set(files)
        for old in OUT.glob("*.svg"):
            if old.name not in keep:
                old.unlink()
        for name, body in files.items():
            (OUT / name).write_text(body)
        text = replace_block(README.read_text(), "<!-- CATALOG:START -->", "<!-- CATALOG:END -->", catalog_md, "README.md")
        text = replace_block(text, "<!-- REEL:START -->", "<!-- REEL:END -->", reel_md, "README.md")
        README.write_text(text)
        if GRAPH.exists():
            GRAPH.write_text(replace_block(GRAPH.read_text(), "// CATALOG:START", "// CATALOG:END", graph_js, "docs/index.html"))
        (ROOT / "docs" / "catalog.json").write_text(json.dumps(data, indent=2) + "\n")

    return {"items": items, "files": files, "markdown": catalog_md, "reel": reel_md, "report": report, "graph": graph_js}


def render_graph(cat: dict, items: list[dict]) -> str:
    """The 3D graph keeps its own code; only its DOMAINS and REPOS constants are generated."""
    used = [c for c in cat["categories"] if any(i["category"] == c["id"] for i in items) and c["id"] != "forks"]
    dom = ",\n".join(f'  {c["id"]}: {{ label: {json.dumps(c["label"])}, color: 0x{c["color"][1:]} }}' for c in used)
    rows = ",\n".join(
        f'  [{json.dumps(i["title"])}, {json.dumps(i["category"])}, {json.dumps(i["loc"])}, {json.dumps(i["name"])}, {json.dumps(i["demo"])}]'
        for i in items if i["category"] != "forks")
    return f"const DOMAINS = {{\n{dom},\n}};\n\nconst REPOS = [\n  // title, category, measured python LOC, repo slug, live demo\n{rows},\n];"


def shield_label(text: str) -> str:
    """shields.io static-badge escaping: '-' -> '--', '_' -> '__', space -> '_'."""
    import urllib.parse
    s = text.replace("-", "--").replace("_", "__").replace(" ", "_")
    return urllib.parse.quote(s, safe="_-")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="repos JSON instead of the live API")
    ap.add_argument("--readme-dir", help="directory of <repo>.md instead of the live API")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cat = json.loads(CATALOG.read_text())
    owner = cat["owner"]
    token = os.environ.get("GITHUB_TOKEN")

    if args.fixture:
        repos = json.loads(pathlib.Path(args.fixture).read_text())
    else:
        repos = fetch_repos(owner, token)

    readmes = {}
    for r in repos:
        if r["name"] in cat["hide"] or r.get("fork"):
            continue
        # README text is only needed for repos the catalog does not describe.
        e = cat["repos"].get(r["name"], {})
        if e.get("category") and e.get("blurb"):
            continue
        if args.readme_dir:
            p = pathlib.Path(args.readme_dir) / f"{r['name']}.md"
            readmes[r["name"]] = p.read_text(errors="replace") if p.exists() else ""
        else:
            readmes[r["name"]] = fetch_readme(owner, r["name"], token)

    now = dt.datetime.now(dt.timezone.utc)
    raw_base = f"https://raw.githubusercontent.com/{owner}/{owner}/main"
    res = build(repos, readmes, cat, now, raw_base, write=not args.dry_run)

    width = max(len(n) for n, _, _ in res["report"])
    for n, c, why in sorted(res["report"], key=lambda x: (x[1], x[0])):
        print(f"  {n:<{width}}  {c:<12} {why}")
    unplaced = [n for n, c, _ in res["report"] if c == cat["rules"]["fallback_category"]]
    if unplaced and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write("### Repos waiting for a category\n\n" + "\n".join(f"- `{n}`: add a `cat-<id>` topic or an entry in data/catalog.json" for n in unplaced) + "\n")
    print(f"\n{len(res['items'])} repos, {len(res['files'])} images, {len(unplaced)} uncategorized")


if __name__ == "__main__":
    sys.exit(main())
