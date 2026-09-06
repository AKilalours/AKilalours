#!/usr/bin/env python3
"""
Answer a project question opened through the issue form, using data/projects.json
as the only source of numbers.

The point of this bot is that it cannot make a number up. It reports what is in
the data file, including "not published", and links to the repo so the asker can
check. If it has nothing, it says so and leaves the issue open for a human reply.

Env: GH_TOKEN, GH_REPO (owner/name), ISSUE_NUMBER, ISSUE_BODY, ISSUE_TITLE.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
PROJECTS = DATA["projects"]
USER = DATA["user"]

TOKEN = os.environ["GH_TOKEN"]
REPO = os.environ["GH_REPO"]
NUMBER = os.environ["ISSUE_NUMBER"]
BODY = os.environ.get("ISSUE_BODY", "")
TITLE = os.environ.get("ISSUE_TITLE", "")


def api(method: str, path: str, payload: dict | None = None,
        tolerate: tuple[int, ...] = ()) -> int:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=json.dumps(payload).encode() if payload else None,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-ask-bot",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        if err.code in tolerate:
            return err.code
        raise


# Colours match the domain palette used across the profile.
LABEL_COLOURS = {
    "ask": "58a6ff", "dispute": "d29922", "answered": "3fb950",
    "perception": "58a6ff", "retrieval": "a371f7", "search": "3fb950",
    "health": "ff7b72", "safety": "f2cc60", "other": "8b949e",
}


def ensure_labels(names: list[str]) -> None:
    """Create any label that does not exist yet.

    An issue form silently drops a label the repo does not have, so relying on
    labels existing is how this bot ends up looking broken in a fresh repo.
    422 means it already exists, which is the normal case after the first run.
    """
    for name in names:
        api("POST", "labels",
            {"name": name, "color": LABEL_COLOURS.get(name, "8b949e")},
            tolerate=(422,))


def find_project(text: str) -> dict | None:
    """Match on display name first, then id, then slug. Longest name wins so
    'SafetyEval Lab' is not shadowed by a shorter partial match."""
    haystack = text.lower()
    candidates = sorted(PROJECTS, key=lambda p: -len(p["name"]))
    for p in candidates:
        for needle in (p["name"], p["id"], p["slug"]):
            if re.search(r"\b" + re.escape(needle.lower()) + r"\b", haystack):
                return p
    return None


def fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def render(p: dict, dispute: bool = False) -> str:
    url = f"https://github.com/{USER}/{p['slug']}"
    lines = []
    if dispute:
        # A dispute gets the claim laid out plainly and then left open for a human
        # reply. The bot's job here is to make sure the argument is about the real
        # numbers rather than about the README's prose.
        lines += [
            "Thanks for this. Here is exactly what I currently claim for this project and "
            "how it was measured, so the disagreement is about the real thing. I will reply "
            "myself; this comment is not the answer.",
            "",
        ]
    lines += [
        f"### {p['name']} \u00b7 {p['tagline']}",
        "",
        f"`{p['stack']}` · [repo]({url})"
        + (f" · [live demo]({p['demo']})" if p.get("demo") else ""),
        "",
    ]

    if p["metrics"]:
        lines += ["| measurement | value | my target | status |", "|---|---|---|---|"]
        for m in p["metrics"]:
            if m["value"] is None:
                value = "not published yet"
            elif m["value"] <= 1.0:
                value = fmt(m["value"])
                if m["ci"]:
                    value += f" &nbsp;<sub>95% CI [{m['ci'][0]:.3f}, {m['ci'][1]:.3f}]</sub>"
            else:
                value = str(int(m["value"]))

            target = fmt(m["target"]) if m["target"] else "none stated"
            if m["value"] is None:
                status = "threshold defined, value pending"
            elif m["status"] == "superseded":
                status = "superseded, kept so the fix is visible"
            elif m["target"] and m["value"] < m["target"]:
                status = "**below my own target**"
            else:
                status = "current"
            lines.append(f"| {m['name']} | {value} | {target} | {status} |")
        lines.append("")
    else:
        lines += [
            "I have not published a measurement for this project yet. "
            "Rather than quote something unverified, here is what it does and how it is built:",
            "",
        ]

    lines += [f"**What I found building it.** {p['finding']}", ""]
    lines += [
        "---",
        "<sub>Answered automatically from "
        f"[`data/projects.json`](https://github.com/{USER}/{USER}/blob/main/data/projects.json), "
        "the same file the README tiles and the benchmark board are generated from. "
        "If a number here disagrees with the repo, the repo is right and this is a bug worth reporting.</sub>",
    ]
    return "\n".join(lines)


def main() -> None:
    project = find_project(f"{TITLE}\n{BODY}")

    if project is None:
        names = ", ".join(f"`{p['name']}`" for p in PROJECTS)
        comment = (
            "I could not tell which project this is about, so I am leaving this open "
            "for a human answer rather than guessing.\n\n"
            f"If you meant one of these, mention it by name and I will reply with its numbers: {names}."
        )
        api("POST", f"issues/{NUMBER}/comments", {"body": comment})
        return

    dispute = "[dispute]" in TITLE.lower()
    api("POST", f"issues/{NUMBER}/comments", {"body": render(project, dispute)})

    # A dispute is never labelled "answered" by a bot. It stays open until a person
    # has actually engaged with the argument.
    labels = [project["domain"]] if dispute else ["answered", project["domain"]]
    labels.append("dispute" if dispute else "ask")
    ensure_labels(labels)
    api("POST", f"issues/{NUMBER}/labels", {"labels": labels})
    print(f"{'acknowledged dispute' if dispute else 'answered'} for {project['name']}")


if __name__ == "__main__":
    main()
