# Agent pipeline

Every Codex task runs through five agents in order (engine.py, `pipeline` field of the task can override):

| # | Agent | Sandbox | Output |
|---|---|---|---|
| 1 | Methodologist | read-only | agents/1_methodologist.md |
| 2 | Experimenter | workspace-write | agents/2_experimenter.md |
| 3 | Statistician | workspace-write | agents/3_statistician.md |
| 4 | Reviewer 2 | read-only | agents/4_reviewer2.md |
| 5 | Fixer & Documenter | workspace-write | agents/5_fixer.md |

Then the lead (Claude) reviews .agents/*.md and the diff, and merges to main or sends a fix task.
Role prompts: agents/<n>_<role>.md. Each agent sees the TASK SPEC plus the files written by earlier agents.
