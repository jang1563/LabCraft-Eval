# LabCraft Data Schemas

This document defines the current schema contract for LabCraft's static JSON artifacts and Hugging Face exports. Executable JSON Schema files for HF task, result, eval-log-manifest, and release-manifest records are available under [`schemas/`](../schemas/). Task-data contracts are also checked by repository tests and runtime loaders.

For schema 0.3.0 exports, `scripts/validate_hf_export.py` loads these JSON
Schemas in addition to its cross-file checksum, count, and provenance checks.

## 1. Parameter Files

Path pattern: `data/parameters/*.json`

Each parameter file contains one or more parameter objects. The exact top-level container can be either:

- a JSON object with a `parameters` array, or
- a JSON object keyed by parameter identifier

Whichever container style is used, every parameter record must expose the following fields.

### Parameter record

```json
{
  "parameter_name": "transformation_efficiency_chemical_competent",
  "description": "Transformation efficiency distribution for chemically competent E. coli.",
  "units": "CFU per microgram DNA",
  "distribution": "log_normal",
  "parameters": {
    "mu": 16.1,
    "sigma": 0.6
  },
  "minimum_tier_required": "Gold",
  "tier_satisfied": true,
  "citations": [
    {
      "title": "High efficiency transformation of Escherichia coli with plasmids",
      "doi": "10.1016/0378-1119(90)90336-P",
      "canonical_url": "https://doi.org/10.1016/0378-1119(90)90336-P",
      "year": 1990,
      "tier": "Gold",
      "citation_count_approx": 1000,
      "tier_justification": "Foundational, highly cited transformation-efficiency paper."
    }
  ],
  "notes": [
    "Optional implementation notes."
  ]
}
```

### Rules

- `parameter_name`: required string, globally unique within the file.
- `description`: required string.
- `units`: required string unless the parameter is dimensionless.
- `distribution`: required string for stochastic parameters. Deterministic thresholds may use `null` and provide a direct scalar in `parameters`.
- `parameters`: required object containing the numeric distribution or threshold values.
- `minimum_tier_required`: required enum, one of `Gold`, `Silver`, `Bronze`, `Copper`.
- `tier_satisfied`: required boolean. This can be materialized in the JSON or computed during validation, but the schema contract expects the field to exist by the time tests inspect the record.
- `citations`: required non-empty array.

### Citation object

Every citation object must contain:

```json
{
  "title": "string",
  "tier": "Gold",
  "tier_justification": "string",
  "doi": "10.xxxx/xxxx",
  "canonical_url": "https://...",
  "citation_count_approx": 250
}
```

Rules:

- `tier`: required enum, one of `Gold`, `Silver`, `Bronze`, `Copper`.
- `tier_justification`: required non-empty string.
- At least one of `doi` or `canonical_url` must be present and non-empty.
- `citation_count_approx` is required for `Gold` citations and optional otherwise.
- Parameter validation must confirm that at least one citation satisfies `minimum_tier_required`.

## 2. Ground Truth Files

Path pattern: `task_data/*/ground_truth.json`

Each task ground-truth file defines decision scoring, troubleshooting references, and efficiency expectations for a task. Not every task operation is stochastic.

### Top-level shape

```json
{
  "task_id": "transform_01",
  "decision_points": [
    {
      "id": "heat_shock_duration",
      "description": "Duration used during heat shock.",
      "matcher": {
        "tool_name": "transform",
        "argument": "heat_shock_seconds",
        "filters": {
          "status": "transformed"
        },
        "minimum_matches": 4,
        "occurrence": "all"
      },
      "acceptable_values": {
        "type": "exact",
        "value": 30
      },
      "scoring_rule": "binary",
      "citations": [
        {
          "doi": "10.1016/0378-1119(90)90336-P",
          "tier": "Gold",
          "tier_justification": "Foundational transformation protocol."
        }
      ]
    }
  ],
  "failure_diagnosis_map": {
    "no_colonies_due_to_skipped_recovery": {
      "canonical_diagnosis": "Recovery was skipped before plating.",
      "acceptable_variants": [
        "Cells needed recovery time before antibiotic selection."
      ],
      "judge_strategy": "substring_any",
      "citations": [
        {
          "canonical_url": "https://www.neb.com/",
          "tier": "Bronze",
          "tier_justification": "Authoritative vendor guidance for transformation workflow."
        }
      ]
    }
  },
  "efficiency_reference": {
    "optimal_tool_calls": 4,
    "max_reasonable_tool_calls": 7,
    "reagent_budget": {
      "soc_ml": 1.0,
      "plate_count": 4
    }
  }
}
```

### Rules

- `task_id`: required string matching the task directory name.
- `decision_points`: required non-empty array.
- `failure_diagnosis_map`: required object; values describe accepted troubleshooting diagnoses for known failure modes.
- `efficiency_reference`: required object.

### Decision point rules

- `id`: required unique string.
- `description`: required string.
- `matcher`: required object describing how the scorer identifies the corresponding tool call in the transcript.
- `matcher.tool_name` and `matcher.argument`: identify the tool and observed field.
- `matcher.filters`: optional exact filters applied to merged call/result fields; string filters are whitespace-trimmed and case-insensitive.
- `matcher.minimum_matches`: optional positive count floor, defaulting to one, before an occurrence rule can earn credit.
- `matcher.occurrence`: optional `first`, `last`, `any`, or `all` policy, defaulting to `all`.
- `matcher.consistent`: optional boolean requiring all matched values to be identical.
- `acceptable_values`: required object. The exact shape depends on whether the decision is a range, enum set, boolean, free-text judgment target, or structured argument block.
- `scoring_rule`: required string such as `binary`, `partial_credit`, or `structured_match`.
- `judge_strategy`: when present in `failure_diagnosis_map`, currently uses deterministic strategies such as `substring_any`; live task scoring does not depend on an LLM judge.
- `citations`: required non-empty array following the citation rules above.

### Efficiency reference rules

- `optimal_tool_calls`: required integer.
- `max_reasonable_tool_calls`: required integer.
- `reagent_budget`: required object keyed by reagent name or resource label.

## 3. Rubric Files

Path pattern: `task_data/*/rubric.json`

Rubric files store hierarchical scoring trees compatible with the existing `src/rubric_utils.py` loader. In v0.1.x these files are audit and design artifacts: Inspect tasks invoke hard-coded scorers in `src/trajectory_scorer.py` (or the separate Safety Case scorer), not `compute_weighted_score()` over these JSON trees.

### Top-level shape

```json
{
  "task_id": "transform_01",
  "task_title": "Transformation efficiency measurement",
  "total_leaf_nodes": 8,
  "rubric": {
    "name": "Task Evaluation",
    "weight": 1.0,
    "is_leaf": false,
    "children": [
      {
        "name": "Task Success",
        "weight": 0.4,
        "is_leaf": false,
        "children": []
      }
    ]
  }
}
```

### Rubric node rules

Each node follows the `RubricNode` contract already used in `src/rubric_utils.py`:

```json
{
  "name": "Correct heat shock timing",
  "weight": 0.5,
  "is_leaf": true,
  "category": "decision_quality",
  "requirement": "Agent selects a heat shock duration within the accepted literature range.",
  "grading_notes": "Full credit for 30 s; partial credit for 20-45 s depending on scoring rule."
}
```

Rules:

- `name`: required string.
- `weight`: required number.
- `is_leaf`: required boolean.
- `children`: required for non-leaf nodes, omitted or empty for leaf nodes.
- `category`, `requirement`, and `grading_notes`: required for leaf nodes and optional for internal nodes.

### Recommended top-level rubric dimensions

Rubrics should use the four top-level dimensions defined by the deterministic trajectory scorer:

- `Task Success`
- `Decision Quality`
- `Troubleshooting`
- `Efficiency`

For rubric-authoring consistency, the weights should sum to `1.0` at every
sibling level. This JSON-tree rule must not be confused with the v0.1.x runtime
implementation, whose simulator-task top-level weights are hard-coded as task
success 0.4, decision quality 0.3, troubleshooting 0.2, and efficiency 0.1.

## 4. Hugging Face Export Schema 0.3.0

The machine-readable contracts are:

- [`hf_task_record.schema.json`](../schemas/hf_task_record.schema.json)
- [`hf_result_record.schema.json`](../schemas/hf_result_record.schema.json)
- [`hf_eval_log_manifest_record.schema.json`](../schemas/hf_eval_log_manifest_record.schema.json)
- [`release_manifest.schema.json`](../schemas/release_manifest.schema.json)

`source_commit` is the packaging HEAD commit recorded by the exporter. It is
present on the manifest and JSONL records but does not claim to be the code
revision that generated a model trajectory. A final release must also be built
from a clean packaging worktree; the exporter refuses otherwise and records
`packaging_worktree_dirty: false` in the manifest.

Score-bearing result and eval-log-manifest records separately contain the
native Inspect `evaluation_revision`:

```json
{
  "type": "git",
  "origin": "https://github.com/jang1563/LabCraft-Eval.git",
  "commit": "<evaluation commit>",
  "dirty": false
}
```

Under schema 0.3.0:

- `evaluation_revision` must contain `type`, `origin`, `commit`, and `dirty`;
- `dirty` must be `false` for every exported scored log;
- `model_generate_config` must be a non-empty object with explicitly recorded
  generation settings;
- every scored row must preserve `requested_model`, provider-returned
  `resolved_model`, `provider`, `effective_generation_config`, and
  `inspect_version`;
- the requested model must exist in `config/model_matrix.toml`; its provider
  and resolved ID must match the registry expectation, allowing only optional
  provider qualification on the resolved ID;
- a requested alias must not resolve to multiple snapshots in one release;
- raw Inspect logs must be bundled under `eval_logs/`, and each log-manifest
  path must resolve to a matching file in the release manifest;
- every result row must map to a matching eval-log-manifest row with the same
  native revision, requested/resolved identity, provider, Inspect version, and
  generation configuration;
- `release_manifest.json.evaluation_provenance` must use policy
  `clean-evaluation-revisions-required`, report zero dirty logs, and list the
  distinct evaluation commits; and
- a score-bearing export must contain non-empty `result_rows.jsonl`.

A metadata-only export created with `--no-results` intentionally omits
`result_rows.jsonl` and writes an empty `eval_log_manifest.jsonl`. This is the
CI packaging-smoke path; it does not make any assertion about model-score
provenance.

The exporter also refuses to write into a non-empty output directory unless
`--clean-output` is explicitly supplied. This prevents stale unmanifested files
from surviving across builds. Destructive cleanup is limited to children of
`build/`. Immutable release directories and tags must never be rewritten in
place.

The executable schemas retain schema 0.2.0 compatibility: 0.2 records are not
required to contain the five model-identity fields introduced in 0.3.0. New
score-bearing exports use 0.3.0 and receive the stricter cross-file and model
registry validation described above.

The published v0.1.1 export predates schema 0.2.0 and 0.3.0 and remains frozen. Its
historical scores must not be described as satisfying the clean-evaluation
revision contract retroactively.
