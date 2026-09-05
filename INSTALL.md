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
- **Graph:** edit the `REPOS` array in `docs/index.html`. Add entries as
  `["Name", "domain", locOrNull, "repo-slug", "liveUrlOrNull"]`.
- **Contribution calendar:** regenerates itself nightly.
