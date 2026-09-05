<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AKilalours/AKilalours/main/assets/hero-dark.svg" />
  <img src="https://raw.githubusercontent.com/AKilalours/AKilalours/main/assets/hero-light.svg" alt="Akila Lourdes Miriyala Francis, machine learning engineer" width="100%" />
</picture>

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=17&duration=3600&pause=1000&center=true&vCenter=true&width=900&color=58A6FF&lines=Machine+learning+engineer+%C2%B7+Brooklyn%2C+NY;BEV+perception+%C2%B7+agentic+RAG+%C2%B7+learning-to-rank;I+publish+the+numbers%2C+including+the+bad+ones" alt="" />

<br/>

<a href="https://www.linkedin.com/in/akila-lourdes-miriyala-francis-5b047019a"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
<a href="https://scholar.google.com/citations?user=1GIm0M8AAAAJ"><img src="https://img.shields.io/badge/Google_Scholar-4285F4?style=flat-square&logo=googlescholar&logoColor=white" alt="Google Scholar" /></a>
<a href="mailto:akilalourdes@gmail.com"><img src="https://img.shields.io/badge/Email-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email" /></a>

</div>

<br/>

I build perception, retrieval and ranking systems, and I care most about the part people
skip: proving they actually work. Several of the projects below exist because a harness I
wrote disagreed with a number I had published.

MS Artificial Intelligence at LIU Brooklyn, graduating December 2026. Machine learning
intern on the R&D team at Jaan Health, working on clinical NLP over patient care
timelines.

<div align="center">

<!-- Computed in .github/workflows/profile-stats.yml straight from GitHub's GraphQL
     contributionsCollection over a rolling 365 days, the same source the profile
     header uses. Third-party stat services read the public REST API and miss private
     contributions, so their numbers disagree with the profile. These do not. -->
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAKilalours%2FAKilalours%2Foutput%2Fcontrib.json&style=for-the-badge" alt="Contributions in the last 365 days" />
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAKilalours%2FAKilalours%2Foutput%2Fcommits.json&style=for-the-badge" alt="Commits" />
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAKilalours%2FAKilalours%2Foutput%2Fprs.json&style=for-the-badge" alt="Pull requests" />
<img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAKilalours%2FAKilalours%2Foutput%2Frepos.json&style=for-the-badge" alt="Public repositories" />

</div>

<br/>

<div align="center">

<a href="https://akilalours.github.io/AKilalours/">
  <img src="https://raw.githubusercontent.com/AKilalours/AKilalours/main/assets/graph-preview.gif" alt="Interactive 3D graph of my repositories, clustered by domain and sized by lines of code" width="82%" />
</a>

<sub><b><a href="https://akilalours.github.io/AKilalours/">Open the interactive version</a></b> &nbsp;·&nbsp; drag to orbit, click a node to open the repo</sub>

</div>

<br/>

## Selected work

<details>
<summary><b>OpenDriveFM</b> &nbsp;·&nbsp; trust-aware multi-camera BEV perception &nbsp;<sub>nuScenes · PyTorch Lightning</sub></summary>

<br/>

Camera-only occupancy and trajectory prediction from six surround cameras, plus the
fault-detection and robustness harness built around it. Every reported number is produced
by a script in the repo and written to a JSON artifact.

**The finding I care about.** The `CameraTrustScorer` is meant to notice when a camera
degrades. The harness scored it as binary classification over 82 held-out frames, 5 fault
types and 6 cameras, with bootstrap CIs over 1,000 resamples:

| Checkpoint | Pooled AUROC | 95% CI |
|---|---|---|
| v11 baseline | 0.434 | [0.419, 0.449] |
| fix v1, pooled hinge | 0.652 | [0.636, 0.668] |
| fix v2, stratified + worst-case | **0.764** | [0.750, 0.777] |

The baseline confidence interval sits entirely below 0.5. The scorer was not weak, it was
inverted: trust went *up* when a camera was degraded. The harness is what caught it.

Also here: a dual-branch trust estimator combining a learned CNN with Laplacian-variance
and Sobel edge-density statistics, trained with a contrastive margin loss; a synthetic
fault-injection suite (blur, glare, occlusion, rain streaks, sensor noise); a transformer
over multi-camera temporal sequences; and a TensorRT-ready graph with no custom CUDA ops.
Inference runs on Apple Silicon via the MPS backend.

[Repo](https://github.com/AKilalours/opendrivefm) &nbsp;·&nbsp; [Live demo](https://huggingface.co/spaces/Akilalourdes/opendrivefm)

</details>

<details>
<summary><b>FORGE</b> &nbsp;·&nbsp; AI-generated text detection &nbsp;<sub>DeBERTa-v3 · FastAPI · 66 tests</sub></summary>

<br/>

A detection service for machine-written text, built as a full pipeline rather than a
notebook: DeBERTa-v3 fine-tuned on an RTX 4090, served behind FastAPI, with a Streamlit
front end.

188 Python modules and 66 tests, the most thoroughly tested thing I have written.

[Repo](https://github.com/AKilalours/Panagram_Forge)

</details>

<details>
<summary><b>StreamLens</b> &nbsp;·&nbsp; hybrid search and learning-to-rank &nbsp;<sub>LightGBM · Kafka · FastAPI</sub></summary>

<br/>

A three-stage retrieval pipeline. BM25 and FAISS dense retrieval are merged by a tunable
min-max normalised blend, reranked by a LightGBM LambdaRank model over 15 retrieval and
text-overlap features, then optionally refined by a cross-encoder precision stage.

Event streaming through Kafka with automatic fallback to Redis Streams and then to a
no-op, so the service degrades instead of failing.

The lesson worth telling: inference needed explicit schema-drift reconciliation because
models had been trained against inconsistent feature sets over time. That is a production
ML failure mode you only learn by hitting it.

[Repo](https://github.com/AKilalours/streaming-canvas-search-ltr)

</details>

<details>
<summary><b>Guardian Drive</b> &nbsp;·&nbsp; multimodal driver-safety monitoring &nbsp;<sub>PointPillars · BEV · physiological signals</sub></summary>

<br/>

Physiological signal monitoring fused with a vision perception stack. Built with
[Akilan Manivannan](https://github.com/akilanmanivannan).

A PointPillars 3D detector written from scratch, pillar feature network through voxelizer
to center head, with trained checkpoints. A BEVFormer-style encoder using spatial
cross-attention and temporal self-attention. Visual-inertial odometry with IMU
preintegration and an SO(3) exponential map. A lock-free single-producer single-consumer
ring buffer in C++ for low-latency telemetry handoff.

Ingests nuScenes, Argoverse2, KITTI and BDD100K for vision, WESAD and PTB-XL for
physiological signals. Safety decisions run through a rule-based state machine with
threshold hysteresis, not a learned policy.

[Repo](https://github.com/AKilalours/guardian-drive) &nbsp;·&nbsp; [Live demo](https://huggingface.co/spaces/Akilalourdes/guardian-drive-demo) <sub>(wakes on first visit)</sub>

</details>

<details>
<summary><b>SafetyEval Lab</b> &nbsp;·&nbsp; structured LLM safety evaluation &nbsp;<sub>Pydantic · 46 tests · CI</sub></summary>

<br/>

A typed framework for evaluating model behaviour across reward hacking, sycophancy and
prompt injection. Pydantic taxonomies for each category, a provider adapter that runs
against a deterministic mock by default and live models only when explicitly enabled, and
Wilson score intervals on pass rates so small-sample results carry honest confidence
bounds rather than a bare percentage.

Framework stage. The default evaluated "model" is a rule-based stub, not an LLM.

[Repo](https://github.com/AKilalours/akila-safety-eval-lab)

</details>

<details>
<summary><b>NeuraPilot</b> &nbsp;·&nbsp; agentic RAG tutoring engine &nbsp;<sub>LangGraph · ChromaDB · Ollama</sub></summary>

<br/>

A LangGraph state machine, classify to rewrite to retrieve to rerank to generate, over
ChromaDB with MMR retrieval, swappable between local Ollama and OpenAI.

The interesting part is the evaluation. My RAGAS-style harness reported perfect
faithfulness on every question, including a control question the system answered from
model knowledge instead of the documents. The score parser was reading the judge's
sentence count rather than its score and clamping it to 1.0. I fixed the parser,
implemented the grounding guard that had been an accepted-but-unused parameter, and added
regression tests that fail against the old code.

Measured after the fix, on 16 questions over two lecture decks with `llama3.1:8b`:
faithfulness **0.595**, answer relevance **0.847**, context precision **0.437**. The
first is below my own 0.70 target and the third says retrieval is the weak stage. Those
are the real numbers.

[Repo](https://github.com/AKilalours/neurapilot)

</details>

<details>
<summary><b>ChronicGuard</b> &nbsp;·&nbsp; patient message triage &nbsp;<sub>TF-IDF · SBERT · RAG</sub></summary>

<br/>

Classifies inbound patient messages by intent and ordinal risk level, retrieves the
relevant care protocol from ChromaDB, and drafts a response. Built with
[Akilan Manivannan](https://github.com/akilanmanivannan).

The evaluation harness treats urgent-case recall below 0.92 as a hard failure and reports
calibration by Brier score, because a triage system that is well calibrated on average and
misses urgent cases is worse than useless. Trained on synthetic messages.

[Repo](https://github.com/AKilalours/chronicguard-ai)

</details>

<details>
<summary><b>GI Lesion Screening</b> &nbsp;·&nbsp; endoscopic image classification &nbsp;<sub>EfficientNet-B3 · Grad-CAM</sub></summary>

<br/>

EfficientNet-B3 with a dual-head design, binary plus 8-class, on Kvasir v2. Inverse
frequency class weights for the binary head and focal loss for the multi-class head.
Grad-CAM implemented directly with PyTorch forward and backward hooks rather than a
library.

95.44% binary accuracy &nbsp;·&nbsp; 0.991 ROC-AUC &nbsp;·&nbsp; Cohen's κ 0.931 on the 8-class task.

[Repo](https://github.com/AKilalours/Esophageal-Cancer-Detection)

</details>

<details>
<summary><b>Offline Voice RAG Assistant</b> &nbsp;·&nbsp; local speech-to-answer &nbsp;<sub>faster-whisper · BGE · Coqui</sub></summary>

<br/>

Speech in, retrieved and cited answer out, running locally. faster-whisper for ASR with
int8 CPU quantisation, two retrieval backends compared under measured latency (sparse
TF-IDF against dense BGE-small with a `ms-marco` cross-encoder reranker), Coqui VITS for
speech synthesis. Citation integrity is enforced in the RAG path, with a policy-injection
blocklist and RBAC gating.

[Repo](https://github.com/AKilalours/rag-adversarial-robustness-eval-harness)

</details>

<br/>

## Contribution activity

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AKilalours/AKilalours/main/profile-3d-contrib/profile-night-green.svg" />
  <img src="https://raw.githubusercontent.com/AKilalours/AKilalours/main/profile-3d-contrib/profile-green-animate.svg" alt="Isometric 3D view of the last year of contributions" width="100%" />
</picture>


</div>

<details>
<summary>🐍 Snake and 👾 Pac-Man versions of the same graph</summary>

<br/>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AKilalours/AKilalours/output/snake-dark.svg" />
  <img src="https://raw.githubusercontent.com/AKilalours/AKilalours/output/snake-light.svg" alt="Snake animation traversing the contribution graph" width="100%" />
</picture>

<br/><br/>

<img src="https://raw.githubusercontent.com/AKilalours/AKilalours/output/pacman-contribution-graph.svg" alt="Pac-Man traversing the contribution graph" width="100%" />

</div>

</details>

<details>
<summary>📊 Repository activity at a glance</summary>

<br/>

<table>
  <thead>
    <tr>
      <td><b>Project</b></td><td><b>Stars</b></td><td><b>Forks</b></td><td><b>Issues</b></td><td><b>Last commit</b></td>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="https://github.com/AKilalours/opendrivefm"><b>OpenDriveFM</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/opendrivefm?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/opendrivefm?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/opendrivefm?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/opendrivefm?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/Panagram_Forge"><b>FORGE</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/Panagram_Forge?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/Panagram_Forge?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/Panagram_Forge?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/Panagram_Forge?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/streaming-canvas-search-ltr"><b>StreamLens</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/streaming-canvas-search-ltr?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/streaming-canvas-search-ltr?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/streaming-canvas-search-ltr?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/streaming-canvas-search-ltr?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/guardian-drive"><b>Guardian Drive</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/guardian-drive?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/guardian-drive?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/guardian-drive?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/guardian-drive?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/akila-safety-eval-lab"><b>SafetyEval Lab</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/akila-safety-eval-lab?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/akila-safety-eval-lab?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/akila-safety-eval-lab?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/akila-safety-eval-lab?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/neurapilot"><b>NeuraPilot</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/neurapilot?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/neurapilot?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/neurapilot?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/neurapilot?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/chronicguard-ai"><b>ChronicGuard</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/chronicguard-ai?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/chronicguard-ai?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/chronicguard-ai?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/chronicguard-ai?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
    <tr>
      <td><a href="https://github.com/AKilalours/Esophageal-Cancer-Detection"><b>GI Lesion Screening</b></a></td>
      <td><img alt="stars" src="https://img.shields.io/github/stars/AKilalours/Esophageal-Cancer-Detection?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="forks" src="https://img.shields.io/github/forks/AKilalours/Esophageal-Cancer-Detection?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="issues" src="https://img.shields.io/github/issues/AKilalours/Esophageal-Cancer-Detection?style=flat-square&labelColor=161b22&color=30363d"/></td>
      <td><img alt="last-commit" src="https://img.shields.io/github/last-commit/AKilalours/Esophageal-Cancer-Detection?style=flat-square&labelColor=161b22&color=30363d"/></td>
    </tr>
  </tbody>
</table>

<sub>Badges are live from the GitHub API, so this table never goes stale.</sub>

</details>

<br/>

## Tools

**Modelling** &nbsp; PyTorch · PyTorch Lightning · Transformers · scikit-learn · LightGBM
**Retrieval** &nbsp; LangChain · LangGraph · ChromaDB · FAISS · BM25 · sentence-transformers
**Serving** &nbsp; FastAPI · Streamlit · Docker · Ollama
**Data & streaming** &nbsp; PySpark · Kafka · Redis · SQLite · pandas · NumPy
**Languages** &nbsp; Python · C++ · SQL · TypeScript

<br/>

## Publication

Co-author, *Cryptocurrency price prediction*, AIP Conference Proceedings **3175**, 020004 (2025).
[Google Scholar](https://scholar.google.com/citations?user=1GIm0M8AAAAJ)

<br/>

<div align="center">
<sub>Brooklyn, NY &nbsp;·&nbsp; <a href="https://www.linkedin.com/in/akila-lourdes-miriyala-francis-5b047019a">LinkedIn</a> &nbsp;·&nbsp; <a href="mailto:akilalourdes@gmail.com">Email</a></sub>
</div>
