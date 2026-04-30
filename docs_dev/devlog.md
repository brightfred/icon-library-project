Let's write the devlog. I'll draft it based on everything we've built — you can edit it to add your own voice and observations.
docs_dev/devlog.md:
markdown# OpenMark Icons — Research Devlog

A running log of experiments, decisions, and findings as we build
an RL-trained SVG icon generator with visual feedback.

---

## Project Goal

Build an open-source, locally-running AI system that generates
high-quality stroke-only SVG icons for science, engineering, and
environment domains — domains that existing icon libraries underserve.

The system should:
- Generate icons that conform to a strict style guide (24x24, stroke-only, currentColor)
- Improve over time through human review feedback
- Eventually require minimal human intervention

---

## Why This Matters

Science, engineering, aquaculture, and environment icons are consistently
behind paywalls. Developers building tools in these domains either pay
repeatedly or use generic icons that don't communicate the right concepts.

OpenMark Icons aims to be the MIT-licensed answer — a free, open,
AI-generated library that gets better the more it is used.

---

## Stack

| Component | Tool | Notes |
|---|---|---|
| Icon library site | GitHub Pages | Auto-deploys on push |
| Generation pipeline | Python | Queue → generate → validate → commit |
| SVG validator | Custom | Enforces style guide strictly |
| SVG scorer | Heuristic | Rewards curves, path count, roundness |
| SVG normalizer | Custom | Converts OmniSVG 200x200 → 24x24 stroke |
| Backend 1 | Ollama + Qwen2.5-Coder | Text LLM, fast, weak design sense |
| Backend 2 | OmniSVG 4B | Visual model, better shapes, slow |
| Backend 3 | Fine-tuned Qwen 7B | Our own model, trained on 8k icons |
| Fine-tuning | Unsloth + QLoRA | RTX 5070, ~6 hours per run |
| Hardware | RTX 5070 16GB | Windows, Git Bash |

---

## Experiment Log

### 2026-04-27 — Baseline: Ollama + Qwen2.5-Coder

**What we tried:** Generate icons using a generic code LLM with a
strict system prompt enforcing style guide rules.

**Result:** Syntactically valid SVG every time. Visually useless.
The model generates connected lines that vaguely suggest shapes
but are not recognizable as icons.

**Key insight:** LLMs generate SVG as *text tokens*, not as *shapes*.
They have no spatial understanding. A model that has read millions of
SVG files knows the syntax but cannot reason about what the output
looks like visually.

**Example — science-laser:**
```svg

  

```
Passes all validation. Looks like a random blob.

---

### 2026-04-28 — OmniSVG 4B

**What we tried:** OmniSVG is a NeurIPS 2025 model that tokenizes
SVG commands as discrete coordinate tokens rather than text. It has
genuine visual understanding — trained on 2M annotated SVG assets.

**Setup challenges:**
- Requires Qwen2.5-VL base model (separate download, 7GB)
- OmniSVG weights are fine-tuned on top (8GB)
- transformers version conflict (needed 4.51.0, not 5.x)
- decoder.py required two patches for PyTorch 2.11 compatibility
- Windows encoding issues (PYTHONIOENCODING fix)
- 8B model exceeds 12.8GB VRAM — had to use 4B

**Result:** Generates recognizable shapes. Flask looks like a flask.
But outputs filled 200x200 SVG — wrong format for our style guide.

**Solution:** Built SVGNormalizer — scales 200→24, removes fills,
adds stroke, enforces currentColor.

**Remaining problem:** Generic prompts produce generic results.
"Conical flask" → something flask-shaped but anatomically wrong.

**Key insight:** OmniSVG needs anatomical prompts to produce
correct multi-part icons. Generic concept names are not enough.

---

### 2026-04-29 — Fine-tuning Qwen2.5-Coder-1.5B

**What we tried:** Supervised fine-tuning on 8,392 SVG examples
from Lucide (1,703), Tabler (5,039), Phosphor (1,512), and our
own icons (138, 3x weighted).

**Training:** Unsloth + QLoRA, 3 epochs, ~85 minutes on RTX 5070.
Final loss: 0.4477. Eval loss: 0.4072.

**Result:** Outputs are valid SVG with correct style guide format.
Concept accuracy is poor — model learned syntax but not design.
A "flask" prompt produces circles and lines, not a flask shape.

**Key insight:** 1.5B parameters is not enough capacity to reliably
associate concepts with correct geometric shapes while also learning
SVG syntax. The model memorizes format, not meaning.

---

### 2026-04-30 — Fine-tuning Qwen2.5-Coder-7B

**What we tried:** Same dataset, same approach, 7B parameter model.
Training: ~5h47m on RTX 5070. Final loss: 0.3758.

**Result:** Meaningfully better. Flask prompt produces a recognizable
conical shape. Single path, correct proportions, proper bezier curves.

**Remaining problems:**
- Single-path icons — no anatomical decomposition
- No curves on complex shapes — everything angular
- Concept accuracy degrades on non-common concepts

**Key insight:** Supervised fine-tuning on text→SVG pairs teaches
syntax and common shapes but cannot teach *design*. The model has
no feedback about whether its output *looks correct*. It cannot
see what it draws.

---

## The Core Problem

Every approach so far fails for the same reason:

**The model generates SVG without ever seeing the result.**

A human designer draws, looks, adjusts. Our models predict the next
token without any visual feedback loop. No matter how much training
data we add, supervised fine-tuning alone cannot close this gap.

---

## The Solution: Reinforcement Learning from Visual Feedback

**Architecture:**
Prompt → Generator → SVG → Renderer → PNG → Reward Model → Score
↓
Generator weights ← RL Update ←─┘

**Reward components:**

1. CLIP concept accuracy — does the rendered icon look like the concept?
2. Style guide compliance — does it follow stroke/viewBox/color rules?
3. Human preference — does it match the aesthetic decisions of the curator?

**Why this hasn't been done for icons:**
- Most RL-from-visual-feedback work targets photorealistic images
- SVG is structured code, not pixels — the reward needs to understand both
- Icon-specific constraints (24x24, stroke-only) are a novel sub-problem
- Human preference integration in a tight generation loop is unexplored

---

## Benchmark Icons

Ten concepts that span difficulty and domain. We measure every
improvement against these:

| # | Concept | Difficulty | Why |
|---|---|---|---|
| 1 | gear | easy | Geometric, well-defined |
| 2 | flask | easy | Simple silhouette |
| 3 | leaf | medium | Organic curve |
| 4 | wave | medium | Pure bezier test |
| 5 | atom | medium | Ellipses + circle |
| 6 | thermometer | medium | Tube + bulb |
| 7 | dna | hard | Complex, science-specific |
| 8 | microscope | hard | Multi-part anatomy |
| 9 | circuit | hard | Angular, engineering |
| 10 | fish | hard | Organic, animal shape |

---

## Review Flag System

Icons are reviewed with specific flags that map directly to
training signals:

**Concept accuracy:**
- `correct` — recognizable as the concept
- `wrong-concept` — drew something else entirely
- `partial` — some elements correct, missing key parts

**Anatomy:**
- `missing-parts` — key anatomical parts absent
- `wrong-proportions` — parts present but wrong size/position
- `disconnected` — parts don't form a coherent whole

**Stroke quality:**
- `too-complex` — too many paths, unreadable at 16px
- `too-simple` — one path, no anatomical detail
- `filled` — using fill instead of stroke
- `wrong-weight` — stroke too thick or thin

**Design quality:**
- `unbalanced` — weight distributed poorly
- `not-centered` — icon not centered in viewBox
- `good` — approved

---

## Current Status

- [x] Generation pipeline (queue → generate → validate → commit)
- [x] Three backends (Ollama, OmniSVG, fine-tuned)
- [x] Training data pipeline (8,392 examples)
- [x] Fine-tuned 7B model (loss 0.3758)
- [x] Review UI with flag system
- [ ] SVG renderer (SVG → PNG)
- [ ] CLIP scorer (concept accuracy)
- [ ] Preference model (learns from reviews)
- [ ] RL training loop (GRPO)
- [ ] Benchmark evaluation

---

## Next Steps

1. `research/reward/renderer.py` — SVG → PNG pipeline
2. `research/reward/clip_scorer.py` — CLIP concept accuracy
3. `research/reward/preference_model.py` — learned style reward
4. `research/evaluation/benchmark.py` — measure quality on 10 concepts
5. `research/training/rl_train.py` — GRPO training loop

---

## Open Questions

- What CLIP model gives best results for icon-sized images?
- How many human reviews are needed before preference model is reliable?
- Can we use the style guide rules as a differentiable reward signal?
- Is GRPO or PPO better for this token-generation task?
- At what point does the RL loop produce diminishing returns?

---

## References

- OmniSVG: A Unified Scalable Vector Graphics Generation Model (NeurIPS 2025)
- CLIP: Learning Transferable Visual Models From Natural Language Supervision
- GRPO: Group Relative Policy Optimization
- Unsloth: Fast LLM fine-tuning
- Lucide Icons (MIT), Tabler Icons (MIT), Phosphor Icons (MIT)