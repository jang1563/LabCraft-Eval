---
title: LabCraft-Eval Leaderboard
emoji: 📊
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: cc-by-nc-4.0
---

# LabCraft-Eval Leaderboard

Read-only leaderboard for manifest-backed LabCraft-Eval Hugging Face dataset
releases. The checked-in app defaults to the current v0.1.2 metadata and task
contract, which intentionally has no scores, and provides a separate selector
for the frozen v0.1.1 historical provisional score bundle. It reads exported
JSONL files and eligible plots from:

<https://huggingface.co/datasets/jang1563/LabCraft-Eval>

It does not scrape GitHub Markdown pages or recompute benchmark scores. Files
are selected from an allowlisted immutable dataset commit and its expected
release manifest, then verified before display; historical copied plots are
hidden for metadata-only releases.
