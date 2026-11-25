"""Hero media and tagline for each repo, turned into profile tiles.

A repo's README is treated as the source of truth for how it looks:
  * hero media  = the first GIF / video near the top of the README, else the
                  first screenshot. Badges, icons and SVGs are ignored.
  * tagline     = the first real line under the title.

`ensure_tile` turns the hero media into a 480x348 GIF with the title and one
line baked in, the same style as the hand-made tiles. Tiles are cached and only
rebuilt when the source file, title or caption changes.

Security: media is only downloaded from GitHub hosts that serve the owner's own
content, capped in size, and decoded by ffmpeg with network protocols disabled.
The workflow token can write to the profile repo, so arbitrary third-party
files are never fed to a decoder there.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

TILE_W, TILE_H, BAR_H = 480, 300, 48
MAX_TILE_BYTES = 2_300_000
MAX_SOURCE_BYTES = 40_000_000
SCAN_CHARS = 9000

ANIMATED = (".gif", ".mp4", ".webm", ".mov", ".m4v")
STILL = (".png", ".jpg", ".jpeg", ".webp")
SKIP = re.compile(
    r"shields\.io|badge|/actions/workflows/|skillicons|readme-typing|github-readme-stats|"
    r"komarev|visitor|hits\.|gravatar|avatars\.githubusercontent|profile-3d|snake|"
    r"(?:^|[/_.-])(?:logo|icons?|favicon|emoji|btn|button)s?(?:[/_.-]|$)", re.I)
FONT_BOLD = ["/usr/share/fonts/opentype/inter/Inter-Bold.otf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT_REG = ["/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
# (fps, palette colours, seconds): tried in order until the tile fits.
ATTEMPTS = [(8, 96, 8), (6, 80, 8), (5, 64, 7), (4, 48, 6)]


# ------------------------------------------------------------------ discovery
def trusted(url: str, owner: str) -> bool:
    u = urllib.parse.urlparse(url)
    path = u.path.lower()
    o = owner.lower()
    if u.scheme != "https":
        return False
    if u.netloc == "raw.githubusercontent.com":
        return path.startswith(f"/{o}/")
    if u.netloc == "github.com":
        return path.startswith(f"/{o}/") or path.startswith("/user-attachments/")
    return u.netloc in ("user-images.githubusercontent.com", "private-user-images.githubusercontent.com")


def resolve(src: str, owner: str, repo: str) -> str:
    """README-relative path or blob URL -> a URL that serves the raw bytes."""
    src = html_unescape(src.strip())
    if src.startswith("//"):
        src = "https:" + src
    if not re.match(r"https?://", src):
        path = re.sub(r"^(\./)+", "", src).lstrip("/")
        path = urllib.parse.quote(urllib.parse.unquote(path), safe="/")  # "cover image.png"
        return f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/(?:blob|raw)/([^/]+)/(.+?)(?:\?raw=true)?$", src)
    if m:
        return f"https://raw.githubusercontent.com/{m[1]}/{m[2]}/{m[3]}/{m[4]}"
    return src


def html_unescape(s: str) -> str:
    return s.replace("&amp;", "&")


def find_hero_media(md: str, owner: str, repo: str) -> str | None:
    """First animated media near the top of the README, else first screenshot."""
    head = re.sub(r"<!--.*?-->", " ", md[:SCAN_CHARS], flags=re.S)
    # Media shown on the page outranks media only linked from it: a README that
    # wraps a GIF in a link to a 4K video wants the GIF seen.
    shown_p = [r"<img[^>]+src=[\"']([^\"']+)[\"']",
               r"<(?:video|source)[^>]+src=[\"']([^\"']+)[\"']",
               r"!\[[^\]]*\]\(\s*<?([^)\s>]+)",
               r"(?m)^\s*(https://github\.com/user-attachments/assets/[0-9a-f-]+)\s*$"]
    linked_p = [r"\]\(\s*<?([^)\s>]+\.(?:mp4|webm|mov|m4v))",
                r"href=[\"']([^\"']+\.(?:mp4|webm|mov|m4v))[\"']"]

    def scan(patterns):
        hits = sorted((m.start(), m.group(1)) for p in patterns for m in re.finditer(p, head, flags=re.I))
        animated = still = None
        for _, src in hits:
            if SKIP.search(src):
                continue
            url = resolve(src, owner, repo)
            if not trusted(url, owner):
                continue
            ext = pathlib.PurePosixPath(urllib.parse.urlparse(url).path).suffix.lower()
            if "user-attachments/assets/" in url and not ext:
                ext = ".mp4"  # drag-and-drop uploads in a README are almost always videos
            if ext in ANIMATED and animated is None:
                animated = url
            elif ext in STILL and still is None:
                still = url
        return animated, still

    shown_anim, shown_still = scan(shown_p)
    linked_anim, _ = scan(linked_p)
    animated, still = shown_anim or linked_anim, shown_still
    return animated or still


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def clean_line(line: str) -> str:
    s = re.sub(r"<[^>]*>|<[^>]*$|^[^<]*?>", " ", line)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = EMOJI.sub("", s)
    s = re.sub(r"&nbsp;|&middot;", " ", s)
    s = re.sub(r"[*_`#>|]", "", s)
    return re.sub(r"\s+", " ", s).strip(" -:·")


def find_tagline(md: str, limit: int = 140) -> str:
    """The first real line under the README title: what a visitor should read."""
    text = re.sub(r"```.*?```|<!--.*?-->", " ", md[:SCAN_CHARS], flags=re.S)
    lines = text.splitlines()
    start = 0
    for i, l in enumerate(lines):
        if re.match(r"\s*(#\s|<h1)", l, re.I):
            start = i + 1
            break
    in_note = False
    for l in lines[start:start + 40]:
        if re.match(r"\s*(?:##\s|<h2)", l, re.I):
            break  # the tagline lives between the title and the first section
        if in_note or re.match(r"\s*<(?:sub|small)>", l, re.I):
            in_note = not re.search(r"</(?:sub|small)>", l, re.I)
            continue  # footnotes such as "the demo sleeps when idle", even over several lines
        if len(re.sub(r"<a\b[^>]*>.*?</a>|<[^>]+>|[\s\u00b7|]", "", l)) < 5 and "<a" in l:
            continue  # HTML link rows
        if re.search(r"<img|!\[|shields\.io|badge|src=", l, re.I) and len(clean_line(l)) < 40:
            continue
        # Link-only lines ("Live demo", "Interactive evidence") are navigation, not a description.
        if "\u2197" in l or re.fullmatch(r"\s*(?:[*_]*\[[^\]]*\]\([^)]*\)[*_]*\s*[\u00b7|,]?\s*)+", l):
            continue
        if re.match(r"\s*(?:\$ |git |pip |npm |cd )", l):
            continue
        s = clean_line(l)
        if len(s) < 20 or re.match(r"(?i)(built by|table of contents|---|live repo)", s):
            continue
        if not re.search(r"[a-z]{3}", s):
            continue
        return s if len(s) <= limit else s[: limit - 1].rsplit(" ", 1)[0] + "..."
    return ""


def fit_caption(text: str, width: int = 66) -> str:
    """One line for the tile bar: whole sentences if they fit, else cut at a word."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= width:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = ""
    for s in sentences:
        nxt = f"{out} {s}".strip()
        if len(nxt) > width:
            break
        out = nxt
    if len(out) >= 20:
        return out
    cut = text[: width - 3].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return cut + "..."


# ----------------------------------------------------------------- selection
def select_showcase(items: list[dict], hero: dict[str, str | None], pinned: list[dict],
                    size: int, skip_categories: set[str]) -> list[dict]:
    """Pinned tiles first (at most `size`), then every repo with media, newest first.

    `items` are newest-first. Returns dicts with repo, and either `file` (pinned,
    hand-made) or `source` (auto, to be rendered).
    """
    by = {i["name"]: i for i in items}
    out = [dict(p, pinned=True) for p in pinned if p["repo"] in by][:size]
    taken = {p["repo"] for p in out}
    # Every auto candidate is returned, newest first: the caller stops once
    # `size` tiles actually rendered, so one broken video does not leave a gap.
    moving, still = [], []
    for i in items:
        if i["name"] in taken or i["fork"] or i["category"] in skip_categories:
            continue
        src = hero.get(i["name"])
        if src:
            (moving if is_animated(src) else still).append({"repo": i["name"], "source": src, "pinned": False})
    # It is a video grid: anything that moves comes before a still screenshot.
    return out + moving + still


def is_animated(url: str) -> bool:
    ext = pathlib.PurePosixPath(urllib.parse.urlparse(url).path).suffix.lower()
    return ext in ANIMATED or ("user-attachments/assets/" in url and not ext)


# ---------------------------------------------------------------- rendering
def first_existing(paths: list[str]) -> str:
    for p in paths:
        if pathlib.Path(p).exists():
            return p
    raise RuntimeError("no usable font found: install fonts-inter or fonts-dejavu")


def fingerprint(url: str) -> str:
    """Cheap change check without downloading: ETag, else length + date."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "profile-catalog"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            h = r.headers
            return h.get("ETag") or f'{h.get("Content-Length")}-{h.get("Last-Modified")}'
    except Exception:  # noqa: BLE001 - unknown means "rebuild", which is safe
        return ""


def download(url: str, dest: pathlib.Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-catalog"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as fh:
        total = 0
        while chunk := r.read(1 << 16):
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                raise ValueError(f"source over {MAX_SOURCE_BYTES} bytes")
            fh.write(chunk)


def render_tile(src: pathlib.Path, out: pathlib.Path, title: str, caption: str, color: str) -> int:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not installed")
    bold, reg = first_existing(FONT_BOLD), first_existing(FONT_REG)
    with tempfile.TemporaryDirectory() as td:
        tf, cf = pathlib.Path(td, "t.txt"), pathlib.Path(td, "c.txt")
        tf.write_text(title[:40])
        cf.write_text(caption)
        for fps, colors, secs in ATTEMPTS:
            vf = (f"[0:v]fps={fps},scale={TILE_W}:{TILE_H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                  f"pad={TILE_W}:{TILE_H}:(ow-iw)/2:(oh-ih)/2:color=0x0d1117,"
                  f"pad={TILE_W}:{TILE_H + BAR_H}:0:0:color=0x0d1117,"
                  f"drawbox=x=0:y={TILE_H}:w=4:h={BAR_H}:color=0x{color.lstrip('#')}:t=fill,"
                  f"drawtext=fontfile={bold}:textfile={tf}:fontsize=15:fontcolor=0xe6edf3:x=16:y={TILE_H + 9},"
                  f"drawtext=fontfile={reg}:textfile={cf}:fontsize=12:fontcolor=0x9198a1:x=16:y={TILE_H + 28},"
                  f"split[a][b];[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
                  f"[b][p]paletteuse=dither=none:diff_mode=rectangle")
            cmd = ["ffmpeg", "-v", "error", "-y", "-protocol_whitelist", "file", "-t", str(secs),
                   "-i", str(src), "-filter_complex", vf, "-loop", "0", str(out)]
            subprocess.run(cmd, check=True, timeout=300, capture_output=True)
            size = out.stat().st_size
            if size <= MAX_TILE_BYTES:
                return size
        out.unlink(missing_ok=True)
        raise ValueError("tile still too large at the lowest quality setting")


def ensure_tile(entry: dict, title: str, caption: str, color: str, root: pathlib.Path,
                auto_dir: pathlib.Path, manifest: dict, log=print) -> str | None:
    """Return the repo-relative tile path, rebuilding only when something changed."""
    repo, url = entry["repo"], entry["source"]
    name = re.sub(r"[^a-z0-9]+", "-", repo.lower()).strip("-") + ".gif"
    out = auto_dir / name
    fp = fingerprint(url)
    key = hashlib.sha256(json.dumps([url, fp, title, caption, color]).encode()).hexdigest()[:16]
    old = manifest.get(repo, {})
    if out.exists() and fp and old.get("key") == key:
        return out.relative_to(root).as_posix()
    try:
        with tempfile.TemporaryDirectory() as td:
            src = pathlib.Path(td, "src")
            download(url, src)
            size = render_tile(src, out, title, caption, color)
    except Exception as exc:  # noqa: BLE001 - one bad repo must not block the rest
        log(f"warning: no tile for {repo}: {exc}")
        return None
    manifest[repo] = {"source": url, "key": key, "bytes": size, "title": title, "caption": caption}
    log(f"tile: {repo} ({size // 1024} KB) from {url}")
    return out.relative_to(root).as_posix()
