# LabCraft-Eval vs. the State of the Art (May 2026)

Short literature-grounded audit placing LabCraft-Eval against published biology-agent and lab-protocol benchmarks. The goal is to say clearly (a) what space this repo occupies, (b) where it is genuinely novel, and (c) where it is redundant with stronger prior work that a reviewer will already know about.

Unless noted otherwise, the scale claims in this document refer to the frozen April 2026 evaluated portfolio snapshot (5 tasks). The current codebase now implements 14 runnable simulator/decision tasks plus the separate `safety_case_01` safeguard-quality track. The newer wet-lab, follow-up, discovery, and safety-case surfaces were added after the frozen snapshot, so this document keeps them clearly separated from the v0.1 scorecard and uses them only where noted.

The May 2026 scan changes the competitive backdrop: biology-agent evaluation has moved quickly toward end-to-end bioinformatics tasks, objective ground truth, and multi-run reliability analysis. That makes LabCraft-Eval's defensible claim narrower than "biology-agent benchmark" and stronger as "small wet-lab protocol simulator with deterministic multi-axis trajectory scoring."

## Comparable benchmarks surveyed

| Benchmark | Year | Modality | Scale | Scoring | Source |
|---|---|---|---|---|---|
| **ProtocolQA** (inside LAB-Bench) | 2024 | Text-only MCQ | 108 questions | Exact-match | Laurent et al., *LAB-Bench* ([arXiv:2407.10362](https://arxiv.org/abs/2407.10362)) |
| **LAB-Bench** | 2024 | Text-only MCQ | 2,400+ questions across 8 categories | Exact-match | FutureHouse ([paper](https://arxiv.org/abs/2407.10362)) |
| **BioLP-bench** | 2024 | Text-only "find-the-fatal-mistake" | diverse protocols, 1 mistake each | Accuracy on mistake ID | Ivanov, Oxford Biosecurity Group ([bioRxiv 2024.08.21.608694](https://www.biorxiv.org/content/10.1101/2024.08.21.608694v1)) |
| **LabSafety Bench** | 2024 | Text-only MCQ (OSHA-aligned) | 765 questions | Exact-match | Zhou et al. ([arXiv:2410.14182](https://arxiv.org/abs/2410.14182)) |
| **BioProBench** | 2025 | Text-only, 5 tasks | 27K protocols → 556K instances | Rule-based per task | Liu et al. ([arXiv:2505.07889](https://arxiv.org/abs/2505.07889)) |
| **BoxingGym** | 2025 | **Interactive probabilistic environments** | 10 environments | Expected Information Gain + prediction error | Gandhi/Goodman et al. ([arXiv:2501.01540](https://arxiv.org/abs/2501.01540)) |
| **BixBench** | 2025 | Agentic computational-biology analysis | 50+ scenarios; nearly 300 open-answer questions | Open-answer grading | Mitchener/Laurent et al. ([arXiv:2503.00096](https://arxiv.org/abs/2503.00096)) |
| **SciGym** | 2025 | Simulated systems-biology dry lab | 137 evaluated systems; 350 released | Experiment-design and interpretation performance | Duan et al. ([arXiv:2507.02083](https://arxiv.org/abs/2507.02083)) |
| **EXP-Bench** | 2025 | Interactive (repos + starter code) | 461 AI-research tasks | Multi-aspect partial credit | Kon et al. ([arXiv:2505.24785](https://arxiv.org/abs/2505.24785)) |
| **LABBench2** | 2026 | Biology research tasks, more realistic contexts | Nearly 1,900 tasks | Task-specific automatic evaluation | Laurent et al. ([arXiv:2604.09554](https://arxiv.org/abs/2604.09554)) |
| **BioAgent Bench** | 2026 | Interactive bioinformatics pipelines | End-to-end RNA-seq / variant calling / metagenomics | **LLM-as-judge** grader | Fa et al. ([arXiv:2601.21800](https://arxiv.org/abs/2601.21800)) |
| **HeurekaBench (sc-HeurekaBench)** | 2026 | Interactive single-cell pipelines | Open-ended research questions | Reference-based + workflow verification | Panigrahi/Brbić et al. ([arXiv:2601.01678](https://arxiv.org/abs/2601.01678)) |
| **BioMysteryBench** | 2026 | Messy real-world bioinformatics datasets | 99 expert-written questions | Objective ground truth; repeated attempts | Anthropic Research ([post](https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench)) |
| **CompBioBench** | 2026 | Agentic computational-biology tasks | 100 well-scoped tasks | Single-ground-truth answers; public leaderboard/data | Genentech/Roche ([bioRxiv DOI](https://www.biorxiv.org/content/10.64898/2026.04.06.716850v1), [HF collection](https://huggingface.co/Genentech)) |
| **GeneBench** | 2026 | Multi-stage inference in genomics / quantitative biology | 103 evaluations across 10 domains | Verifiable answer per encapsulated analysis | Li/Ho ([bioRxiv DOI](https://www.biorxiv.org/content/10.64898/2026.04.22.720113)) |
| **PromptBio-Bench** | 2026 | End-to-end bioinformatics/data-science agent tasks | 194 expert-curated tasks | Structured file comparison against expert references | Guo et al. ([bioRxiv feed mirror](https://www.scientific.today/entries/876124/promptbio-bench-benchmarking-llm-based-bioinformat/)) |
| **GPT-5 ProtocolQA Open-Ended + TroubleshootingBench** | 2025 | Text QA, some non-public | 108 open-ended + 52 protocols × 3 questions | Human PhD baseline; expert 80th percentile = 36.4% | OpenAI GPT-5 System Card ([PDF](https://cdn.openai.com/gpt-5-system-card.pdf)) |
| **OpenAI × Red Queen Bio wet-lab framework** | 2025 | **Real wet-lab** molecular cloning | 1 iterative optimisation task | Physical assay (79× cloning efficiency gain) | OpenAI announcement ([link](https://openai.com/index/accelerating-biological-research-in-the-wet-lab/)) |
| **LabCraft-Eval (this repo)** | 2026 | **Interactive stochastic simulator** | 5-task evaluated snapshot; 14 tasks implemented in current repo | Deterministic hierarchical rubric + 4-axis trajectory scorer | This repo |

## Where LabCraft-Eval is genuinely novel

Against the surveyed work, the defensible design points are:

1. **Benign wet-lab protocol simulator + deterministic scorer.** Newer work now covers real bioinformatics datasets, systems-biology dry labs, and broader biology research tasks. LabCraft-Eval should not claim uniqueness across all biology-agent evaluation. Its narrower gap is still defensible: a seeded simulator for routine benign molecular-microbiology protocol execution, scored by a deterministic trajectory parser rather than an LLM judge.
2. **Multi-axis rubric (task / decision-quality / troubleshooting / efficiency) scored separately**. BioProBench splits into five *tasks*; BoxingGym scores experimental-design vs. model-discovery; LAB-Bench reports eight *categories* but scores each as exact-match. None of these decomposes a single task into orthogonal axes the way this benchmark does. The axis decomposition is what made the ablation finding possible — you cannot detect "prompt engineering closed one axis while opening another" with a scalar score.
3. **Hierarchical citation-tier enforcement as a first-class test.** The `test_citations.py` contract (Gold/Silver/Bronze/Copper) gates every parameter, ground-truth value, and failure diagnosis on having a traceable public source. LAB-Bench and LabSafety Bench use human verification but do not enforce source provenance automatically. BioProBench uses 27K published protocols but does not expose the provenance chain at the parameter level.
4. **Seeded determinism with stochastic variance.** Same sample_id → same seed (SHA-256 hashed) → bit-identical trajectory. The 5-seed eval at N=5 exposed ~0.27 stddev on the `task_success` axis; that variance is real environmental stochasticity, not sampling noise, and it is measurable because the seeds are auditable. Most text-only benchmarks cannot surface this because there is no stochasticity in the environment to begin with.
5. **Full Inspect AI plugin compliance.** Every task registers as a standard `@task` entry point, so a reviewer can clone the repo and run `inspect eval src/inspect_task.py@clone_01 --model openai/gpt-4o` without any bespoke harness. BoxingGym, EXP-Bench, and BioAgent Bench each ship their own custom runner.

## Where LabCraft-Eval is genuinely weaker than prior work

To reviewers at Anthropic / OpenAI / DeepMind who will already know the references above, the honest pre-empts are:

- **Scale is small.** BioProBench has more than 550K task instances; LABBench2 has nearly 1,900 tasks; BixBench, CompBioBench, GeneBench, PromptBio-Bench, and BioMysteryBench all have broader real-data bioinformatics coverage than this repo. The evaluated LabCraft-Eval snapshot has 5 tasks, and even the current repo's 14 implemented simulator/decision tasks remain small by comparison.
- **No real wet-lab grounding.** OpenAI's Red Queen Bio collaboration executed *actual physical molecular cloning experiments* with GPT-5 and measured outcomes by physical assay. LabCraft-Eval's stochastic simulator has citation-backed parameters but the agent never touches real biology. For claims about real-world capability uplift this is a hard ceiling.
- **No human baseline.** TroubleshootingBench was baselined against 12 PhD experts (80th percentile = 36.4%). Every stddev figure in this repo is agent-vs-agent. A single expert-graded seed on each task would contextualise the scores.
- **Task surface is still mostly execution-reliability-heavy.** As the analysis already admits, the hardest task (`transform_01`, mean 0.50) is mostly punishing agents for dropping one of four reported numbers or missing a consistency keyword — not for reasoning depth. The new `followup_01` and Discovery Decision Track extensions begin to address this by scoring targeted next-experiment choice after ambiguous intervention data, but those slices are still small. SciGym, GeneBench, BioMysteryBench, and CompBioBench now put more pressure on broader scientific inference and multi-stage analysis.
- **Only one prompt-variant ablation so far.** The growth_01 ablation is a good start but a single verbose prompt is not a proper sensitivity sweep. LAB-Bench and BioProBench both include multiple prompt-formatting ablations.

## What the survey *validates* about the repo

- The scorer-as-trajectory-parser (not LLM-as-judge) approach is directly validated by AgentRewardBench ([arXiv:2504.08942](https://arxiv.org/abs/2504.08942)), which found rule-based scoring *underreports* success and LLM judges vary substantially. The repo's tradeoff (auditable + reproducible but brittle on final-answer formatting) is a well-known one in the 2025–2026 literature.
- The ablation finding — that prompt-engineering one axis can move another axis in the opposite direction — is the kind of finding that a text-only benchmark cannot surface because it has only a single scoring axis. This is a genuine contribution.
- The repeated-attempt reliability framing in BioMysteryBench strengthens the case for increasing LabCraft-Eval seed counts. A single pass/fail score is no longer enough; reviewers now expect to know whether a model solves a task consistently or occasionally stumbles into a correct trajectory.
- GeneBench's "noticing versus acting" failure mode is a useful lens for this repo's trajectory logs: agents often observe the right warning or tool result but fail to propagate it into the final decision or report. That maps naturally onto LabCraft-Eval's separate troubleshooting and task-success axes.
- The two latent infrastructure bugs surfaced by adversarial seed exploration ([src/environment/operations.py](../src/environment/operations.py) `_resolve_ligation_fragment_id`, [src/tools/lab_tools.py](../src/tools/lab_tools.py) tool-error wrapping) are exactly the class of failure mode that Multi-Docker-Eval ([arXiv:2512.06915](https://arxiv.org/abs/2512.06915)) argues is the main SWE-agent bottleneck — "environment construction." Finding two such bugs via agent traces is consistent with that literature.
- The newer-task 5-seed frontier extension ([current_frontier_5seed.md](current_frontier_5seed.md)) is a concrete demonstration of why auditable seeds matter. At 3 seeds, `claude-haiku-4-5` looked only slightly weaker than `claude-sonnet-4-5` on the assembly tasks, mostly via efficiency. At 5 seeds, the same task family exposed a real `golden_gate_01` task-success miss and dropped haiku's newer-task mean to 0.976. That is exactly the sort of "small-slice looks saturated, larger slice reveals instability" effect that deterministic re-runnability is supposed to make visible.

## What the newer-task extension adds

The frozen portfolio snapshot remains the main comparison point in this document, but the newer-task frontier extension is already useful for interpreting the repo's design point.

Across `golden_gate_01`, `gibson_01`, `miniprep_01`, `express_01`, and `purify_01`, the 5-seed cross-provider bundle shows:

- `gpt-4o-mini` and `claude-sonnet-4-5` saturated all five newer tasks across all five seeds.
- `gpt-4o` remained near-perfect, with its only visible gap still an efficiency penalty on `gibson_01`.
- `claude-haiku-4-5` became the interesting model on this slice: the extra seeds changed it from "slight assembly efficiency drift" to "assembly-task instability," because one `golden_gate_01` seed produced a final-answer correctness miss despite perfect decision quality.

That extension does not change the headline portfolio framing above, but it does strengthen one methodological claim: the benchmark's multi-axis deterministic scorer is sensitive enough to distinguish "bad plan," "wasted effort," and "correct experiment but wrong final quantitative report" within the same task family.

Separately, the discovery-facing [followup extension](followup_extension.md) adds a small but useful second growth task: `growth_01` measures whether an agent can execute an assay cleanly, while `followup_01` measures whether it can choose the minimum next experiment after an ambiguous intervention result. On a 3-seed slice, `claude-sonnet-4-5` reached `0.933 ± 0.029` and `gpt-4o-mini` reached `0.633 ± 0.227`, with the failures concentrated in conclusion framing and troubleshooting rather than raw doubling-time measurement. That is closer to the sort of discovery-workflow reliability question a biomedical AI reviewer will care about.

## What the Discovery Decision Track adds

The newer Discovery Decision Track pushes the repo beyond protocol execution into a more company-portable biomedical-agent evaluation surface. It does not attempt to recreate an end-to-end autonomous discovery platform. Instead, it isolates one narrower but relevant question:

> Can a biomedical agent inspect perturbation-style evidence, choose the right next experiment, and interpret the result without wasting work?

That is the value of `perturb_followup_01`, `target_prioritize_01`, and `target_validate_01`. They are still small and synthetic, so this repo is not competing with Biomni on breadth, with FutureHouse on full autonomous scientific workflows, or with physical wet-lab systems on real-world execution. What it does offer is a compact, auditable evaluation surface for discovery-decision quality, which is exactly the sort of reliability framing that complements broader biomedical-agent portfolio work.

For the runnable bundle and public score summary, see [results/discovery_track.md](discovery_track.md). Company-specific positioning drafts should be made from [docs/company_briefs/company_brief_template.md](../docs/company_briefs/company_brief_template.md) so the public project framing stays company-portable.

## Recommended framing for a portfolio reviewer

The honest one-sentence pitch is:

> **LabCraft-Eval is a small, reproducible interactive simulator for benign wet-lab reasoning with a deterministic multi-axis rubric.** It fills a gap between text-only protocol QA (LAB-Bench, BioProBench, BioLP-bench) and expensive real-world wet-lab frameworks (OpenAI × Red Queen Bio), and its axis-decomposed scoring surfaces model-vs-prompt tradeoffs that scalar benchmarks cannot.

It is *not* a BioProBench competitor on scale, *not* a BoxingGym competitor on reasoning-depth, and *not* a Red Queen Bio competitor on physical grounding. It is a different and complementary design point.

## Concrete next moves suggested by this literature scan

If the user wanted to strengthen the portfolio *against this competitive landscape* specifically, in descending leverage:

1. **Move all computation to HPC and increase seed counts.** The strongest immediate upgrade is not new tasks; it is a clean, manifest-backed N=10-20 run that makes reliability visible and keeps logs reproducible. See [docs/hpc_plan.md](../docs/hpc_plan.md) and [hpc/README.md](../hpc/README.md).
2. **Add a 1–2 person human baseline** on `transform_01`, `growth_01`, and one discovery task (N=3–5 each). Even n=1 expert creates a reviewer-facing anchor point. TroubleshootingBench's 12-PhD baseline is the bar this aligns with.
3. **Split `transform_01` into an execution variant and a reasoning variant.** The current task is criticised fairly as execution-reliability. A sister task where the dilution strategy must be *derived* from cited stock concentrations (not given) would shift the scoring into reasoning.
4. **Run one additional prompt-sensitivity sweep** (3–5 variants, not 1) on the OpenAI growth_01 troubleshooting gap. This would turn a single-point ablation into a proper sensitivity curve.
5. **Write a short methodology note** explicitly positioning against LABBench2, BioProBench, BioMysteryBench, CompBioBench, GeneBench, and SciGym. The public claim should be narrower than the v0.1 framing but better defended.

None of these are required to ship; they are all ways of making the repo's defensive surface stronger against the specific benchmarks a senior reviewer will already have in their head.
