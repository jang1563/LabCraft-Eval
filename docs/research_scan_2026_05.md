# May 2026 Biology-Agent Benchmark Scan

Prepared: 2026-05-16

This note records the current public landscape relevant to BioProtocolBench. It
is deliberately separate from the README so the public entry point can stay
compact while the research positioning remains auditable.

## BioProtocolBench Public Surface

- GitHub repository: <https://github.com/jang1563/BioProtocolBench>
- Current remote `main` during scan: `151319ac734c65c0fe86e8f1f6296334fde13b2d`
- Public release: `v0.1.0`, published 2026-04-25
- No newer GitHub release, tag, issue, or pull request was found during the
  scan.
- Search for the exact project name mainly returns this repository or is
  confounded with BioProBench. I did not find an additional public paper or blog
  post for this exact BioProtocolBench project.

## Important New or Updated Comparables

### LABBench2

Source: <https://arxiv.org/abs/2604.09554>

LABBench2 is a May 2026-revised continuation of LAB-Bench with nearly 1,900
biology research tasks in more realistic contexts. It is now a primary
reference for "AI systems performing useful biology research tasks."

Impact on BioProtocolBench: avoid broad claims about measuring biology research
capability. Position BioProtocolBench as wet-lab protocol simulation and
trajectory reliability.

### BioProBench v3

Source: <https://arxiv.org/abs/2505.07889>

BioProBench was revised in January 2026. The abstract now emphasizes
BioProCorpus, more than 550,000 task instances, quantitative precision, safety
awareness, and ProAgent.

Impact: keep the README distinction clear. BioProBench is large-scale
procedural-text understanding; BioProtocolBench is small-scale interactive
execution in a stochastic simulator.

### BioAgent Bench

Source: <https://arxiv.org/abs/2601.21800>

BioAgent Bench evaluates end-to-end bioinformatics pipelines such as RNA-seq,
variant calling, and metagenomics, including robustness perturbations. It uses
an LLM-based grader for pipeline progress and outcome validity.

Impact: useful contrast with deterministic scoring. Do not compete on breadth.

### HeurekaBench / sc-HeurekaBench

Source: <https://arxiv.org/abs/2601.01678>

HeurekaBench constructs open-ended research questions grounded in scientific
studies and code repositories, with a single-cell instantiation.

Impact: raises the bar for "AI co-scientist" claims. BioProtocolBench should
stay in the narrower protocol-execution and discovery-decision lane.

### BioMysteryBench

Source: <https://www.anthropic.com/research/Evaluating-Claude-For-Bioinformatics-With-BioMysteryBench>

Anthropic's BioMysteryBench contains 99 expert-written bioinformatics questions
from real-world datasets with objective ground truth and repeated attempts. The
post emphasizes reliability: easy tasks tend to be solved consistently, while
hard-task wins are often brittle.

Impact: BioProtocolBench should report seed-level reliability, not just mean
score. This directly motivates an HPC N=10-20 v0.2 bundle.

### CompBioBench

Sources: <https://www.biorxiv.org/content/10.64898/2026.04.06.716850v1> and
<https://huggingface.co/Genentech>

Genentech/Roche released CompBioBench v1, a 100-task benchmark for well-scoped,
verifiable computational biology problems, with public Hugging Face data and a
leaderboard.

Impact: another reason to avoid broad computational-biology-agent claims.
BioProtocolBench remains complementary only if framed around simulated wet-lab
protocol trajectories.

### GeneBench

Source: <https://www.biorxiv.org/content/10.64898/2026.04.22.720113>

GeneBench targets realistic multi-stage inference in genomics and quantitative
biology. It emphasizes inferential forks where plausible wrong choices
propagate into wrong final answers.

Impact: its "noticing versus acting" failure mode maps well onto
BioProtocolBench's separated troubleshooting and task-success axes.

### PromptBio-Bench

Source: <https://www.scientific.today/entries/876124/promptbio-bench-benchmarking-llm-based-bioinformat/>

PromptBio-Bench is a May 2026 bioRxiv preprint with 194 expert-curated
bioinformatics/data-science tasks and structured file comparison against expert
references.

Impact: reinforces that the broader agentic bioinformatics space is getting
crowded and larger-scale.

### BixBench

Source: <https://arxiv.org/abs/2503.00096>

BixBench remains a central benchmark for real-world computational-biology
analysis tasks, with more than 50 scenarios and nearly 300 open-answer
questions.

Impact: cite as a stronger benchmark for computational biology; position
BioProtocolBench elsewhere.

### SciGym

Source: <https://arxiv.org/abs/2507.02083>

SciGym uses systems-biology dry labs for iterative experiment design and
analysis. It is closer to BioProtocolBench's simulator idea than many
bioinformatics benchmarks, but targets hidden mechanism discovery rather than
routine molecular-microbiology protocol execution.

Impact: BioProtocolBench can honestly say it is smaller and narrower, with a
different simulator domain and deterministic trajectory rubric.

## Revised Claim

Recommended one-sentence claim:

> BioProtocolBench is a compact, reproducible, interactive benchmark for benign
> wet-lab protocol execution and discovery-decision reliability, distinguished
> by seeded stochastic simulation and deterministic multi-axis trajectory
> scoring.

Claims to avoid:

- "first biology-agent benchmark"
- "general biomedical agent benchmark"
- "real wet-lab capability benchmark"
- "large-scale procedural biology benchmark"

## Immediate Planning Consequences

1. Run larger-seed bundles on HPC, with manifests and separate log directories.
2. Add human baseline pilot before making stronger public claims.
3. Add a reasoning-heavy sister task or prompt-sensitivity sweep before arguing
   that the benchmark probes reasoning depth rather than execution reliability.
4. Keep v0.1 frozen results separate from any v0.2 HPC bundle.
