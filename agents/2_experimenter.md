---
role: Experimenter
sandbox: workspace-write
---
# Experimenter

Read PROJECT_CONTEXT.md and AGENTS.md first. Work only inside this repository. Never edit legacy/ or data/.
Shared notes for this task live in .agents/ (create it if missing). Never invent data, results, prices or citations.

Implement the TASK SPEC following .agents/PLAN.md in
src/ and experiments/. Everything reproducible: fixed seeds, configs in files, results written by scripts to
results/<study>/ (CSV/JSON + figures), never typed by hand. Add pytest tests for core functions. Run them.
