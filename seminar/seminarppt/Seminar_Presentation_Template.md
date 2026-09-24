# Seminar Presentation — Reusable Outline Template

*Fill in the \[bracketed] parts with your own topic. Keep bullets short, technical, and numeric wherever possible — avoid vague filler sentences.*

\---

## Slide 1 — Title Slide

* **Title**: \[Topic Name]
* Name: \[Your Name]
* Roll No / UID: \[ ]
* Class: \[ ]
* Guide: \[Guide's Name], \[Designation]
* Department / Institution

\---

## Slide 2 — Agenda

Numbered list of the sections that follow (this exact 7-part order works well):

1. Introduction and Objective
2. Literature Survey — Supporting Papers
3. Literature Survey — Base Paper (deep dive)
4. Applications and Relevance
5. Comparison with Alternate Approaches
6. Conclusion
7. References

\---

## Slide 3 — Introduction and Motivation

* **Introduction**: 1-2 sentences on why this problem matters (real-world stakes)
* **Motivation**: What existing approaches miss / get wrong (the gap)
* **Objective**: "We review N papers — \[list them] — to trace how \[field] evolved, and understand how each contributes a capability the base paper later applies to \[concrete problem]."

*Optional: a "core challenge" callout box (e.g., a formula, complexity bottleneck, or key limitation the whole field is working around).*

\---

## Slide 4 — Literature Survey Overview Table

One table, one row per paper:

|#|Paper|Core Approach|Role|
|-|-|-|-|
|1|\[Paper 1 title, authors, year]|\[1-liner]|Survey|
|2|\[Paper 2]||Survey|
|N|\[Base paper]||**Base paper**|

\---

## Slides 5–8 — One Slide Per Supporting Paper

Repeat this exact 4-part micro-structure for every paper (keeps them easy to compare):

**\[Paper Title]**
*Authors, Venue, Year · Role: \[one-line role in the lineage]*

* **Methodology** (3-5 bullets)

  * Core technique / architecture step
  * Key mechanism (attention type, loss function, training strategy)
  * How it differs from prior work
* **Relevance** (1-2 bullets)

  * What question this paper was trying to answer
* **Key Findings** (2-4 bullets, WITH NUMBERS)

  * Headline accuracy/metric with dataset name
  * Any comparison to a baseline, stated numerically
* **Limitations** (2-3 bullets)

  * Technical shortcoming
  * Cost / scalability issue

\---

## Slides 9–15 — Base Paper Deep Dive (multiple slides)

This section gets significantly more depth than the supporting papers. Suggested slide breakdown:

**a) Overview slide**

* Objective (2-3 bullets)
* Main contributions (bullet list of named components/modules)
* Evaluated on (datasets/benchmarks)
* Headline result callout box (accuracy %, params, comparison to prior SOTA)
* Simple block diagram: \[Method Name] → \[Component 1] \[Component 2] \[Component 3]

**b) Problem being addressed**

* What the naive/baseline approach does and its limitation
* Why a balance/tradeoff matters (cost vs. capability)

**c) Main idea / core mechanism**

* Name the key innovation
* Explain the mechanism in plain terms
* Include the paper's own architecture figure with caption + citation (e.g., "Fig. 3b — \[description] (Author et al., Year)")

**d) Overall architecture**

* Stage-by-stage or module-by-module breakdown
* Include the full pipeline diagram
* Note what changes at each stage (resolution, channels, attention type)

**e) Component deep-dives (1 slide per major component)**

* What it is
* What it captures / why it exists
* Why it's efficient/cheap (or expensive)
* Its limitation, and how another component compensates

**f) Experimental setup**

* Datasets (size, classes, metric used) — one line each
* Model variants (params, config)
* Training details (optimizer, epochs, hardware) — keep to a compact block

**g) Results**

* A comparison table: Model | Params | \[Metric 1] | \[Metric 2] | \[Metric 3]
* Bold/highlight your base paper's row
* 2-3 "key observations" bullets stating exact deltas (e.g., "+2.1% Top-1 over Swin-T")
* Ablation callout: "removing \[component] drops \[metric] to \[X]%"

\---

## Slide 16 — Applications and Relevance

* What the base paper demonstrates that single-modality/simpler approaches can't
* Reusable pattern/insight transferable to other problems
* **Limitations** (as a named sub-section): dataset scale, compute cost, generalization risk

\---

## Slide 17 — Comparison Table (all papers, base paper included)

One consolidated table:

|Paper|Approach|Strength|Main Limitation|
|-|-|-|-|
|Paper 1||||
|Paper 2||||
|**Base paper**||||

End with a short **"Why the base paper was chosen"** callout — 2-3 sentences tying together why it's the most complete/applicable synthesis of the ideas above it.

\---

## Slide 18 — Conclusion

* **One dense paragraph** (not bullets) that:

  1. Traces the narrative arc across the surveyed papers
  2. States what the base paper adds/fuses
  3. States the headline result again
  4. Ends with a forward-looking statement (what this confirms for the field / future work)

\---

## Slide 19 — References

* Full formal citation (APA or IEEE, be consistent) for **every** paper mentioned anywhere in the deck — including ones only referenced in passing (e.g., foundational papers like "Attention Is All You Need," "BERT") even if they didn't get their own slide.

\---

## Formatting Rules Checklist

* \[ ] Every content slide header includes a section tag (e.g., "02 · LITERATURE SURVEY — PAPER 1") and slide number
* \[ ] Every paper slide uses the same sub-heading structure (Objective/Methodology/Advantage/Limitation or similar) — consistency lets the audience pattern-match across slides
* \[ ] Diagrams are pulled from the actual source paper, captioned with figure number + citation
* \[ ] Every claim has a number attached where possible (%, params, FLOPs, dataset size) — avoid "performs better," write "+2.1% Top-1"
* \[ ] Bullets are short (one line each); no long paragraphs except the Conclusion slide
* \[ ] Comparison table appears at least twice: once for supporting papers only (early), once for all papers including base paper (before conclusion)

