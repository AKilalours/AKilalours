"""Tests for build_catalog.py. Run: python .github/scripts/test_build_catalog.py

Each test guards a failure that would otherwise be silent on the profile:
a repo vanishing, a wrong-but-confident category, a broken README, or an SVG
GitHub refuses to render.
"""
import datetime as dt
import json
import pathlib
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_catalog as b  # noqa: E402

CAT = json.loads(b.CATALOG.read_text())
NOW = dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)


def repo(name, **kw):
    base = {"name": name, "fork": False, "language": "Python", "stargazers_count": 0,
            "pushed_at": "2026-10-30T00:00:00Z", "created_at": "2026-10-28T00:00:00Z",
            "size": 500, "description": None, "topics": [], "homepage": None,
            "archived": False, "private": False, "html_url": f"https://github.com/x/{name}"}
    base.update(kw)
    return base


class Classify(unittest.TestCase):
    def test_catalog_entry_wins(self):
        self.assertEqual(b.classify(repo("opendrivefm"), "", CAT)[0], "autonomy")

    def test_topic_overrides_keywords(self):
        r = repo("lidar-thing", topics=["cat-health"])
        self.assertEqual(b.classify(r, "lidar bev nuscenes", CAT), ("health", "topic cat-health"))

    def test_fork_goes_to_forks(self):
        self.assertEqual(b.classify(repo("carla2", fork=True), "", CAT)[0], "forks")

    def test_unknown_repo_is_visible_not_dropped(self):
        # The original failure mode of hand-maintained lists: a new repo is never shown.
        self.assertEqual(b.classify(repo("misc"), "hello world " * 20, CAT)[0], "new")

    def test_clear_keywords_classify(self):
        md = "Camera-only BEV occupancy on nuScenes with LiDAR supervision and trajectory heads."
        self.assertEqual(b.classify(repo("new-perception"), md, CAT)[0], "autonomy")

    def test_close_call_is_parked_not_guessed(self):
        md = "A RAG agent with LangGraph for patient triage in clinical care."  # llm vs health
        cid, why = b.classify(repo("tie"), md, CAT)
        self.assertEqual(cid, "new")
        self.assertIn("ambiguous", why)

    def test_keyword_needs_word_boundary(self):
        # "care" must not fire inside "scared", "bev" not inside "abbreviation".
        self.assertEqual(b.keyword_score("scared abbreviation", ["care", "bev"]), 0)


class Build(unittest.TestCase):
    def setUp(self):
        self.repos = [repo("opendrivefm"), repo("brand-new-thing", description="Something unrelated."),
                      repo("AKilalours"), repo("secret", private=True), repo("carla", fork=True)]
        self.res = b.build(self.repos, {}, CAT, NOW, "https://raw.example", write=False)

    def test_hidden_and_private_excluded(self):
        names = {i["name"] for i in self.res["items"]}
        self.assertEqual(names, {"opendrivefm", "brand-new-thing", "carla"})

    def test_new_repo_gets_card_and_badge(self):
        item = next(i for i in self.res["items"] if i["name"] == "brand-new-thing")
        self.assertTrue(item["is_new"])
        self.assertIn("card-brand-new-thing.svg", self.res["files"])
        self.assertIn("card-brand-new-thing.svg", self.res["markdown"])

    def test_every_svg_is_well_formed(self):
        # GitHub shows a broken image for invalid XML, with no error anywhere.
        for name, body in self.res["files"].items():
            with self.subTest(name=name):
                xml.dom.minidom.parseString(body)

    def test_svg_escapes_hostile_text(self):
        r = repo("x", description='<script>alert(1)</script> & "quotes"')
        res = b.build([r], {}, CAT, NOW, "https://raw.example", write=False)
        body = res["files"]["card-x.svg"]
        self.assertNotIn("<script>", body)
        xml.dom.minidom.parseString(body)

    def test_replace_block_fails_loudly_without_markers(self):
        with self.assertRaises(SystemExit):
            b.replace_block("no markers here", "<!-- A -->", "<!-- B -->", "x", "README.md")

    def test_replace_block_is_idempotent(self):
        t = "a\n<!-- A -->\nold\n<!-- B -->\nz"
        once = b.replace_block(t, "<!-- A -->", "<!-- B -->", "new", "f")
        self.assertEqual(once, b.replace_block(once, "<!-- A -->", "<!-- B -->", "new", "f"))

    def test_graph_js_excludes_forks(self):
        self.assertNotIn('"carla"', self.res["graph"])


class Card(unittest.TestCase):
    def test_metric_is_never_truncated(self):
        # A clipped "AUROC 0.434 to 0.7..." misstates a result; drop it whole instead.
        item = {"name": "x", "title": "X", "blurb": "b", "metric": "a very long metric 0.123 that cannot fit " * 2,
                "language": "Jupyter Notebook", "fork": False, "stars": 1, "updated": "Oct 2026",
                "is_new": False, "is_active": False, "demo": "https://d"}
        body = b.card_svg(item, "#58a6ff")
        self.assertNotIn("0.123", body)
        self.assertNotIn("\u2026", body)

    def test_long_metric_drops_date_first(self):
        item = {"name": "x", "title": "X", "blurb": "b", "metric": "faithfulness 0.595 (goal 0.70)",
                "language": "Python", "fork": False, "stars": 1, "updated": "Sep 2026",
                "is_new": False, "is_active": False, "demo": "https://d"}
        body = b.card_svg(item, "#58a6ff")
        self.assertIn("faithfulness 0.595 (goal 0.70)", body)


class Summary(unittest.TestCase):
    def test_skips_badges_and_credits(self):
        md = ("![b](https://img.shields.io/x)\n### *Built by* **Someone Long Name Here And More Words**\n"
              "A detection service for machine-written text, built as a full pipeline rather than a notebook.\n")
        self.assertTrue(b.readme_summary(md).startswith("A detection service"))


if __name__ == "__main__":
    unittest.main()
