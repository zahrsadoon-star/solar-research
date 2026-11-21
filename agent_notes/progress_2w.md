# Progress on PLAN_2W.md

## Day 1 - Thu 22 Oct
- [x] Claude team launched: Reviewer 2, Statistician, Literature officer (cloud)
- [x] Codex N-version dispatch check queued (20261022-s1-dispatch-nversion)
- [x] Close WP1 fix: merged 22 Oct 00:5x after lead check of all Reviewer-2 MUST-FIX items (51 tests pass)

- [x] Team review outputs integrated (17:45 run): Reviewer-2 pilot report (MAJOR_REVISION) + Literature round 1 brought to main from claude/s1-robustness-wip; synthesis in agent_notes/S1_day1_lead_synthesis.md
- [ ] N-version check: first attempt failed (stale worktree dir); re-specified against dispatch v2 as 20261022-s1-dispatch-v2-verify (queued)

## Day 2 prep (17:45 run)
- [x] Reviewer 2 on protocol v0.9 -> FREEZE_AFTER_EDITS (agent_notes/claude_reviewer2_protocol.md)
- [x] Statistician on protocol v0.9 -> exact settings list (agent_notes/claude_statistician_protocol.md)
- [x] Literature round 2: all open DOIs resolved; novelty threats found (literature/S1_doi_followup.md)
- [x] Protocol v1.0-rc written by the lead (22 Oct 18:50 run): all R2 MUST items + ST settings + dispatch section 9; R2/ST conflicts resolved as [LEAD] (two-sided Q1, no p-values for exploratory pairs, ST seed rule, label grid==0 primary)
- [x] Literature officer (Claude agent): v1.0 refs verified (literature/S1_protocol_v1_refs.md); Naumann calendar model copied from the dissertation (journal text behind CAPTCHA); Iraq 2018 holidays with source disagreements; K&V fixed-b polynomial from a secondary source only
- [x] WP2 pending task amended (amendment 2) to implement v1.0-rc
- [ ] Independent consistency check of v1.0-rc, then hash (lead, 23 Oct)

## Day 2 prep (00:36 run) (done early, 22 Oct 00:36 run)
- [x] method/S1_protocol.md DRAFT v0.9 (Claude Statistician agent + lead edits; fixed: weather file is already local time, no second shift). Freeze on day 2 after Reviewer-2 pass.
- [x] studies/S1_outage_forecasting/references_verified.md (Claude Literature officer; 28 references, DOIs checked; Politis & White 2004 still unverified)
- [x] WP2 harness queued (20261022-s1-wp2-harness), implements the draft via config

## Track B (product) - days 1-2
- [x] p02 skeleton + fix (4-column loader) merged, 27 tests
- [x] p03 battery model merged (ROADMAP 1.2), 107 tests total
- [x] Port research PV model into solarsizer/pv.py: p05 merged 22 Oct 18:4x (APPROVE, 183 tests pass in lead re-run; cross-repo equivalence 1e-9; ROADMAP 1.1)

## 22 Oct 18:45 run (parallel to the 18:38 run)
- [x] method/S1_ageing_model.md: Naumann LFP calendar + cycle model copied from the open-access 2018 TUM dissertation (Ch. 5, Eqs. 5.1-5.30, Tables 5.1/5.3), cross-checked against Collath 2022/2023 and SimSES; journal texts not readable (CAPTCHA). Second-agent check against the dissertation launched.
- [x] literature/S1_round3_verification.md: Hansen 2005, White 2000, Kuensch 1989 (Crossref), Holm 1979 (JSTOR); K&V 2005 fixed-b polynomial UNVERIFIED; Iraq 2018 calendar: Eid al-Fitr 15 vs 16 Jun by authority, Ramadan start and Eid al-Adha day 1 UNVERIFIED.
- [x] Engine: stale undeletable worktree dirs no longer fail a task (fresh path); dispatch-v2-verify re-queued (2nd failure was this bug, not code).

## 23 Oct 00:36 run (after Zaher's narrowing)
- [x] Benchmark v1 (cloud) reviewed by the lead: causal features, month-split excludes test-month targets, no leakage found.
- [x] Queued 20261023-s1-bench-verify (independent N-version check of the numbers) and 20261023-s1-bench-step1-significance (DM + block bootstrap, top group).
- [x] wp2-harness failed (Codex timeout) - obsolete under the new scope, left in queue/failed; dispatch/wp3 parked.
- [x] Daily report 2026-10-22 written (both repos).
- [ ] Next steps after significance is reviewed: tuning (same budget), feature importance, LSTM.

## 2026-10-23 08:36 (lead)
- Merged the independent N-version check of benchmark v1 (`benchmark/verify/`): REPRODUCED, 80/80 metric comparisons within the predeclared tolerances; no time-ordered leakage found. This covers the 3 references + LR + RF only, not the other 10 algorithms.
- Added `.gitattributes` so the verifier's frozen-hash check also passes on Windows checkouts (autocrlf).
- Open from the reviewer: benchmark README says 18 features (actual 19); random-split uplift explanation needs softening; RF diff (0.0034) cause unknown.

## 2026-10-24 00:36 (lead)
- PC was off ~10:00-00:16 on 23 Oct (14:36 and 22:36 check-ins missed); daily report 2026-10-23 written now.
- Step 1 significance landed on main from a cloud session (18:32): RF/Extra Trees top group, no single winner.
- The older Codex significance task started 00:20 with different settings; it will be reviewed as an independent check of step 1, not merged over it.
- Queued 20261024-s1-bench-step2-tuning (equal budget K=20, nested time-ordered selection, new tuning.py only).

## 2026-10-29 02:55 (lead, late 22:36 run)
- PC asleep ~02:15 24 Oct to ~02:50 29 Oct: no engine runs, no check-ins for 5 days.
- Codex step1-significance: NOT merged (MAJOR_REVISION, gate stopped it). Windows rerun of benchmark.py drifts from the published Linux numbers (max Brier 0.0013, mostly XGBoost/GB, max rank change 3). Lead decision: cross-platform variability, document it. Fix task queued: independent significance check on the original predictions, compare top groups with main (cec3552).

## 2026-11-21 04:31 Baghdad (lead, 00:36 run fired late; PC clock shows +08:00)
- No check-ins 17-20 Nov (pause until 19 Nov, then PC/schedule). All 4 tasks queued on 16 Nov failed on 17 Nov:
  p08-config and p09-ci because Codex lost network (transient); step2-tuning hit the Codex timeout while running the
  full grid (code + partial outputs committed on its branch, NOT reviewed, NOT merged); fix2-significance never started
  (branch locked by a stale worktree).
- Product: MERGED p04 economics and p07 optimisers into solar-sizing-tool main (fixer closed both MUST-FIX; lead
  re-ran merged suite 535 passed, ruff clean; ROADMAP 1.4/1.5 ticked). p06 EMS held: lead decision = self-discharge
  capped at C_min (consistent with battery.py and legacy); fix task queued.
- Queued 5: fix-p06-ems, 20261121-p08-config, 20261121-p09-ci, 20261121-s1-bench-step2-finish (make tuning resumable,
  only K=1 sanity check inside Codex; lead runs the full grid on the PC afterwards), fix3-step1-significance.
- No S1 numbers changed this run. No Claude agents used.

- 2026-11-21 08:36 (lead, light run): product EMS Mode 0 merged (620 tests). S1 step-2 tuning and the step-1 significance check did not run: Codex lost its connection at 11:00 PC time, then hit its usage limit; both requeued unchanged. No new S1 numbers today so far.
