# Installing the profile

Everything goes into `github.com/AKilalours/AKilalours`.

## Repo layout when you are done

```
AKilalours/
├── README.md                        ← the assembled profile
├── build_hero.py                    ← regenerates the hero SVGs
├── assets/
│   ├── hero-dark.svg
│   ├── hero-light.svg
│   └── graph-preview.gif
├── docs/
│   └── index.html                   ← the interactive 3D graph, served by Pages
├── profile-3d-contrib/              ← created by the Action on first run
└── .github/workflows/
    └── profile-3d.yml
```

## Steps

```bash
gh repo clone AKilalours/AKilalours ~/Projects/profile
cd ~/Projects/profile
mkdir -p assets docs .github/workflows
# copy the delivered files into the paths above, replacing README.md
git add -A && git commit -m "Rebuild profile: animated hero, 3D contributions, interactive project graph"
git push
```

Then two settings changes:

1. **Settings → Pages** → Source *Deploy from a branch*, branch `main`, folder `/docs`.
   Publishes at `https://akilalours.github.io/AKilalours/`.
2. **Actions tab** → run **3D contribution calendar** once manually, so you are not
   waiting until 03:15 UTC for the first render. Until it runs, the contribution
   block shows a broken image.

## Still open

**Four demo links are held back** until you confirm they load. Add them to the matching
`<details>` block once verified:

- `huggingface.co/spaces/Akilalourdes/forge-detect` — returned 401, likely private
- `panagramforge-...streamlit.app` — could not verify
- both `chronicguard-ai-...streamlit.app` deployments — not verified

**`akilalours.github.io/opendrivefm` is not linked**, deliberately. It is live and it is
your best-looking asset, but it publishes 317 FPS, ADE 2.457 m and 553K params, which
your own OpenDriveFM README explicitly retracts as not reproducing from the code. Fix the
page, then add the link. `MLOPS_ONEPAGER.md` carries the same figures.

**Two repos are worth renaming** so the links make sense. `Panagram_Forge` reads as
nothing to do with FORGE, and `rag-adversarial-robustness-eval-harness` contains a voice
translator. GitHub redirects old URLs automatically.

**Guardian Drive's own README** still says "Kalman fusion" in three places, including next
to the 0.882 risk score. Your `docs/maturity_levels.md` marks EKF as *Described*, not
implemented. The profile says visual-inertial odometry instead, which is accurate, but
the repo contradicts it.

## Regenerating

- **Hero:** edit constants at the top of `build_hero.py`, run `python build_hero.py`.
  Fixed seed, so output is reproducible.
- **Graph:** generated. Its `DOMAINS` and `REPOS` constants sit between
  `// CATALOG:START` and `// CATALOG:END` and are rewritten by the catalog workflow.
  Edit `data/catalog.json`, not the HTML.
- **Contribution calendar:** regenerates itself nightly.

## Repository catalog (auto-categorized)

`.github/workflows/repo-catalog.yml` runs every six hours, on any push that touches
`data/catalog.json`, and on demand from the Actions tab. It lists every public repo,
places each in an area, and rewrites three generated blocks:

| Block | Where | What |
|---|---|---|
| `<!-- REEL:START/END -->` | README | animated flagship reel, open buttons, demo GIF strip |
| `<!-- CATALOG:START/END -->` | README | overview chart, one animated card per repo, by area |
| `// CATALOG:START/END` | docs/index.html | the 3D graph's domains and nodes |

Images go to `assets/generated/`; a per-run `?v=` query defeats GitHub's image cache.
The workflow only commits when something other than the timestamp changed.

**How a repo is placed**, first match wins:

1. An entry under `repos` in `data/catalog.json` (title, blurb, metric, demo).
2. A GitHub topic `cat-<id>` on the repo, e.g. `cat-autonomy`, `cat-llm`, `cat-health`.
   This is the quickest fix and needs no edit here.
3. Forks go to `forks`. Tiny repos with no README go to `foundations`.
4. Keyword scoring over name, description, topics and README. A close call between
   two areas is not guessed: it is parked.
5. Otherwise the repo appears under **Just shipped, not yet categorized** at the top,
   with a NEW badge, and the run summary lists it.

On the 29 current non-fork repos, with every hand entry removed, the keyword stage
put 21 in the right area, parked 7 for review, and put 1 in a defensible but
different area (distress keyword spotting scored as safety, filed as health). So for
a brand-new repo expect the right section about 3 times in 4, and a visible "not
sorted yet" rather than a wrong section most of the rest of the time. 29 repos is a
small sample; treat those numbers as a sanity check, not a benchmark.

**To hide a repo**, add its name to `hide`. **To change the reel or demo GIFs**, edit
`reel` and `demos`. Demo GIFs live in `assets/demos/`; keep each under about 2 MB or
GitHub's image proxy may refuse it.

**Tests:** `python .github/scripts/test_build_catalog.py` (also runs in the workflow
before anything is generated).

**Local dry run:** `python .github/scripts/build_catalog.py --dry-run` with
`GITHUB_TOKEN` set.
