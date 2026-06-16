# Security and Safety Reporting

LabCraft-Eval welcomes reports about security vulnerabilities, benchmark safety
scope issues, and provenance problems.

## Supported Versions

The public `main` branch and the latest tagged release are the supported
surfaces. Historical result bundles are preserved for reproducibility; if a
historical bundle has a concern, report it with the exact commit SHA and result
path.

## What to Report

Please report:

- A software vulnerability in the runner, scripts, packaging, or CI.
- A leaked secret or credential.
- Benchmark content that appears to exceed the safety scope in `SAFETY.md`.
- Missing or unreliable provenance for a task, parameter, reagent, safety
  statement, or ground-truth value.
- A scoring bug that materially changes reported benchmark results.

## How to Report

For ordinary bugs, open a GitHub issue.

For sensitive security or safety concerns, use GitHub private vulnerability
reporting if enabled on the repository. If private reporting is not available,
open a minimal public issue that states the affected file or release bundle and
asks the maintainer to establish a private channel. Do not include exploit
details, secrets, or biological details that would expand beyond `SAFETY.md` in
a public issue.

## Response Expectations

The maintainer will aim to:

- Acknowledge sensitive reports within 7 days.
- Triage whether the issue affects code, benchmark content, scoring, public
  results, or release metadata.
- Publish a fix, mitigation, or documented non-issue when appropriate.
- Preserve reproducibility by recording corrections in `CHANGELOG.md` rather
  than silently rewriting historical bundles.

## Safety Scope

This policy is about reporting. The benchmark's biological scope is defined in
`SAFETY.md`, which overrides examples or shorthand in issues, pull requests, and
documentation.
