"""Tests for media.py. Run: python .github/scripts/test_media.py

Each test pins a way the auto-video grid could quietly go wrong: a badge
shown as a "demo", a 4K video picked over the GIF on the page, a footnote
used as the description, or a tile re-rendered (and re-committed) every run.
"""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import media  # noqa: E402

O, R = "AKilalours", "demo"


class HeroMedia(unittest.TestCase):
    def test_badges_and_icons_are_never_the_hero(self):
        md = ('<img src="https://img.shields.io/badge/x-y-z"/>\n'
              '<img src="https://github.com/AKilalours/demo/actions/workflows/ci.yml/badge.svg"/>\n'
              '<img src="docs/logo.png"/>\n![tour](docs/tour.gif)')
        self.assertEqual(media.find_hero_media(md, O, R),
                         "https://raw.githubusercontent.com/AKilalours/demo/HEAD/docs/tour.gif")

    def test_gif_on_the_page_beats_linked_video(self):
        # Thursday's README wraps home-tour.gif in a link to a 4K mp4.
        md = '<a href="docs/home-4k.mp4"><img src="docs/home-tour.gif"></a>'
        self.assertTrue(media.find_hero_media(md, O, R).endswith("docs/home-tour.gif"))

    def test_linked_video_used_when_nothing_moves_on_page(self):
        md = "[Watch the demo](docs/demo.mp4)"
        self.assertTrue(media.find_hero_media(md, O, R).endswith("docs/demo.mp4"))

    def test_moving_media_beats_earlier_screenshot(self):
        md = "![cover](cover.png)\n\n![run](run.gif)"
        self.assertTrue(media.find_hero_media(md, O, R).endswith("run.gif"))

    def test_drag_and_drop_upload_counts_as_video(self):
        md = "# T\n\nhttps://github.com/user-attachments/assets/0f1e2d3c-aaaa-bbbb-cccc-1234567890ab\n"
        url = media.find_hero_media(md, O, R)
        self.assertIn("user-attachments", url)
        self.assertTrue(media.is_animated(url))

    def test_third_party_hosts_are_not_downloaded(self):
        # The workflow token can push to the profile repo; never decode a stranger's file there.
        md = '<img src="https://evil.example.com/x.gif"/>\n<img src="https://raw.githubusercontent.com/someoneelse/r/main/a.gif"/>'
        self.assertIsNone(media.find_hero_media(md, O, R))

    def test_relative_paths_with_spaces_resolve(self):
        self.assertEqual(media.resolve("./cover image.png", O, R),
                         "https://raw.githubusercontent.com/AKilalours/demo/HEAD/cover%20image.png")

    def test_blob_url_becomes_raw(self):
        self.assertEqual(media.resolve("https://github.com/AKilalours/demo/blob/main/a.gif?raw=true", O, R),
                         "https://raw.githubusercontent.com/AKilalours/demo/main/a.gif")


class Tagline(unittest.TestCase):
    def test_line_under_title(self):
        md = "# 🗂️ Ask Me First\n### Most people don't know how to talk to AI. So this AI asks first.\n"
        self.assertEqual(media.find_tagline(md), "Most people don't know how to talk to AI. So this AI asks first.")

    def test_skips_badges_links_and_footnotes(self):
        md = ("<h1>Forge</h1>\n<img src='https://img.shields.io/badge/a-b-c'/>\n"
              '<a href="x"><b>Interactive evidence ↗</b></a> ·\n'
              "<sub><i>The demo sleeps when idle. First load takes about two minutes\n"
              "while the container wakes.</i></sub>\n"
              "A controlled experiment, not a product claim.\n")
        self.assertEqual(media.find_tagline(md), "A controlled experiment, not a product claim.")

    def test_stops_at_first_section(self):
        md = "# T\n\n## Install\nThis line is in a section and is not a tagline at all.\n"
        self.assertEqual(media.find_tagline(md), "")

    def test_caption_prefers_whole_sentences(self):
        s = "One sentence in. A booked, paid, on-policy dinner out. Nothing happens until you approve."
        self.assertEqual(media.fit_caption(s), "One sentence in. A booked, paid, on-policy dinner out.")
        self.assertLessEqual(len(media.fit_caption("word " * 40)), 66)


class Showcase(unittest.TestCase):
    def items(self):
        mk = lambda n, cat="llm", fork=False: {"name": n, "category": cat, "fork": fork}  # noqa: E731
        return [mk("newest-still"), mk("fork-gif", fork=True), mk("course", "foundations"),
                mk("new-gif"), mk("pinned-one"), mk("old-gif")]

    def test_order_pinned_then_moving_then_still(self):
        hero = {"newest-still": "https://x/a.png", "fork-gif": "https://x/f.gif", "course": "https://x/c.gif",
                "new-gif": "https://x/n.gif", "pinned-one": "https://x/p.gif", "old-gif": "https://x/o.mp4"}
        out = media.select_showcase(self.items(), hero, [{"repo": "pinned-one", "file": "p.gif"}], 6, {"foundations"})
        self.assertEqual([e["repo"] for e in out], ["pinned-one", "new-gif", "old-gif", "newest-still"])
        self.assertTrue(out[0]["pinned"])


class TileCache(unittest.TestCase):
    def test_rebuilds_only_when_source_or_text_changes(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            auto = root / "assets" / "demos" / "auto"
            auto.mkdir(parents=True)
            manifest = {}
            entry = {"repo": "demo", "source": "https://raw.githubusercontent.com/AKilalours/demo/HEAD/a.gif"}

            def fake_render(src, out, *a):
                out.write_bytes(b"GIF89a")
                return 6

            with mock.patch.object(media, "fingerprint", return_value='"etag-1"'), \
                 mock.patch.object(media, "download"), \
                 mock.patch.object(media, "render_tile", side_effect=fake_render) as render:
                p1 = media.ensure_tile(entry, "Demo", "cap", "#a371f7", root, auto, manifest, log=lambda *_: None)
                p2 = media.ensure_tile(entry, "Demo", "cap", "#a371f7", root, auto, manifest, log=lambda *_: None)
                self.assertEqual(render.call_count, 1)  # cached second time
                media.ensure_tile(entry, "Demo", "new caption", "#a371f7", root, auto, manifest, log=lambda *_: None)
                self.assertEqual(render.call_count, 2)  # text changed
            self.assertEqual(p1, "assets/demos/auto/demo.gif")
            self.assertEqual(p1, p2)

    def test_unknown_fingerprint_rebuilds_instead_of_trusting_cache(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            auto = root / "assets" / "demos" / "auto"
            auto.mkdir(parents=True)
            (auto / "demo.gif").write_bytes(b"old")
            entry = {"repo": "demo", "source": "https://raw.githubusercontent.com/AKilalours/demo/HEAD/a.gif"}
            with mock.patch.object(media, "fingerprint", return_value=""), \
                 mock.patch.object(media, "download"), \
                 mock.patch.object(media, "render_tile", return_value=3) as render:
                media.ensure_tile(entry, "Demo", "cap", "#fff", root, auto, {}, log=lambda *_: None)
            self.assertEqual(render.call_count, 1)

    def test_broken_source_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            auto = root / "a" / "b" / "auto"
            auto.mkdir(parents=True)
            logs = []
            entry = {"repo": "demo", "source": "https://raw.githubusercontent.com/AKilalours/demo/HEAD/a.gif"}
            with mock.patch.object(media, "fingerprint", return_value="x"), \
                 mock.patch.object(media, "download", side_effect=OSError("404")):
                self.assertIsNone(media.ensure_tile(entry, "D", "c", "#fff", root, auto, {}, log=logs.append))
            self.assertIn("404", logs[0])


def can_render() -> bool:
    try:
        media.first_existing(media.FONT_BOLD)
        return bool(media.shutil.which("ffmpeg"))
    except RuntimeError:
        return False


# Runs on the CI runner; skipped on a laptop without ffmpeg or the Linux fonts.
@unittest.skipUnless(can_render(), "ffmpeg or tile fonts not installed")
class Render(unittest.TestCase):
    def test_real_tile_has_the_fixed_size_and_fits_the_budget(self):
        with tempfile.TemporaryDirectory() as td:
            src, out = pathlib.Path(td, "src.gif"), pathlib.Path(td, "out.gif")
            media.subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=10",
                                  "-t", "3", str(src)], check=True)
            size = media.render_tile(src, out, "Title", "A caption that fits.", "#58a6ff")
            self.assertLessEqual(size, media.MAX_TILE_BYTES)
            probe = media.subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                                          "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True)
            self.assertEqual(probe.stdout.strip(), f"{media.TILE_W},{media.TILE_H + media.BAR_H}")


if __name__ == "__main__":
    unittest.main()
