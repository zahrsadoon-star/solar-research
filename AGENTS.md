# Instructions for coding agents (Codex) - research track

You are the implementer. Claude is the lead: it writes the task spec, reviews your work and commits.

Research integrity rules (non-negotiable)
1. Never fabricate data, results, citations or DOIs. Only cite papers you have actually located; mark anything unverified `[UNVERIFIED]`.
2. Never tune methods or cherry-pick runs to make results look better. Report negative or weak results as they are.
3. Every number in the manuscript must be produced by a script in this repo and stored in `results/`.
4. Fixed random seeds, multiple independent runs, and the statistical test used must be stated.
5. Every equation in `method/` states its source and the file/function implementing it.
6. Do not modify `legacy/`, `data/` or `legacy/REFERENCE_RESULTS.md`.

Engineering rules
- Python >= 3.11, type hints, docstrings with units; pytest tests for core functions; run `python -m pytest -q` before finishing.
- Do exactly the task in the spec. Do not commit or push.
- Finish by writing `CODEX_REPORT.md` (overwrite): what you did, files touched, checks run, open questions.
