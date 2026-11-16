---
description: SC26 progressive 2-D Fortran→C++ Questioner–Solver experiment
agent: bcp-orchestrator
---

Run the COMPLETE three-gate Beyond Code Pairs exercise with the CURRENT OpenCode model. Work only in `tutorial_demo/opencode_e2e/` and `runs/opencode_latest/`. Never set a model or call an external model API. Use the Task/subagent tool with exact IDs `bcp-questioner` and `bcp-solver` for every model-generated plan, candidate, and repair. Never create or edit their artifacts yourself.

**FAIL CLOSED:** If either named subagent is missing from the callable subagent tool, denied, fails, or does not create the required files, STOP and report that exact failure. Do not use `general`, another agent, scripted fixtures, or the parent/orchestrator as a substitute. A visible `@` entry alone is not proof that programmatic subagent invocation succeeded.

1. Run `python3 tutorial_demo/opencode_e2e/harness.py init`. Stop if the trusted Fortran/Python cross-check fails.

2. **Gate 1 — one heat step.** Launch `bcp-questioner` as a child subagent for Stage 1 and wait for it to write `questioner_stage_01.md`. Then launch `bcp-solver` as a child subagent for Stage 1 and wait for `candidate.cpp` containing `heat_step_2d` plus `solver_stage_01.md`. Run `python3 tutorial_demo/opencode_e2e/harness.py verify --stage 1`. On failure, launch the same named child roles for evidence-based feedback and one repair, then verify once more. Stop the experiment if a child invocation or the retry fails.

3. **Gate 2 — multiple steps.** Only after Gate 1 passes, launch `bcp-questioner` for Stage 2 using the Gate 1 evidence; it writes `questioner_stage_02.md`. Launch `bcp-solver` to extend the same `candidate.cpp` with `heat_solve_2d`, double buffering, zero-step behavior, boundary preservation, and final-step `last_max_delta`; it writes `solver_stage_02.md`. Run `verify --stage 2`. Allow one evidence-based repair through the same two child roles if needed; stop if a child invocation or the retry fails.

4. **Gate 3 — adversarial regression.** Only after Gate 2 passes, launch `bcp-questioner` for Stage 3. It writes `questioner_stage_03.md` and exactly two new cases in `questioner_cases.json`, including a rectangular grid and odd/even step counts. Run `python3 tutorial_demo/opencode_e2e/harness.py check-tests`; use the same Questioner child to correct invalid JSON once. Launch `bcp-solver` to audit/revise the full candidate and write `solver_stage_03.md`. Run `verify --stage 3`; allow one genuine evidence-based repair through the named children if needed.

5. Always run `python3 tutorial_demo/opencode_e2e/harness.py transcript` after the three gates or a verifier failure. Report each gate's outcome, attempts, failed case names, and transcript paths. A correct candidate may pass each gate on its first attempt, but it still completes three distinct child-Questioner–child-Solver–Verifier rounds. If orchestration itself fails before artifacts exist, stop without fabricating a transcript narrative.

This is a teaching adaptation, not the paper's full data-generation pipeline. Compile only this bundled toy source; the harness is not an OS security sandbox.
