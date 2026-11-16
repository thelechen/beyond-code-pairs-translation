---
description: SC26 end-to-end Fortran→C++ Questioner–Solver demo with real compiler and numerical feedback
agent: build
---

Run a COMPLETE Beyond Code Pairs SC26 hands-on experiment from a supplied Fortran 1-D stencil to verified C++ using my CURRENT OpenCode model. Keep all activity within `tutorial_demo/opencode_e2e/` and its `runs/opencode_latest` directory. Do not configure or override models and do not use OpenAI SDK/API calls. Use OpenCode subagents `bcp-questioner` and `bcp-solver` for ALL LLM-generated dialogue/code; do not impersonate them yourself.

Do this STEP BY STEP, always waiting for subagent completion and checking files before continuing:

1. Run `python3 tutorial_demo/opencode_e2e/harness.py init`. This compiles the trusted Fortran reference and verifies six fixed numerical input cases. Stop on failure and explain prerequisites.
2. Launch **bcp-questioner** subagent: ask it to inspect the Fortran code, write `tutorial_demo/opencode_e2e/runs/opencode_latest/questioner_plan.md` and `questioner_cases.json` (two *new, model-generated* test vectors), according to its role instructions. Wait until both files exist. Run `python3 tutorial_demo/opencode_e2e/harness.py check-tests`. If invalid, ask Questioner to fix once. DO NOT substitute scripted tests without telling user.
3. Launch **bcp-solver** subagent: ask it to translate the source with the Questioner plan into `runs/opencode_latest/candidate.cpp`, and to write `solver_01.md`. Wait until these files exist.
4. Run `python3 tutorial_demo/opencode_e2e/harness.py verify`. The harness compiles C++ and Fortran and numerically compares each output. It writes `test_attempt_01.json` and an archived `candidate_attempt_01.cpp`. Do not treat a nonzero exit code as a shell-tool failure that prevents reading its report; it is the intended verification signal.
5. If FAIL, loop up to **two repairs**: launch bcp-questioner to write `questioner_feedback_XX.md` based on EXACT failed report/test outputs; then launch bcp-solver to revise `candidate.cpp` and write `solver_YY.md`. Call `verify` again. STOP on PASS or two repairs. For genuinely failed compile or numerical tests, NEVER claim success.
6. Run `python3 tutorial_demo/opencode_e2e/harness.py transcript` whether PASS or FAIL. This creates `transcript.md` and `events.jsonl`, with real Questioner/Solver file artifacts and captured tool results. Summarize final status, attempt count, test case names, paths to logs, and the actual failure/repair loop if any.
7. If first attempt was already correct, explain that this is GOOD; offer to run `/bcp-repair` to get a **separately labelled, instructor-injected** failure and actual model-driven repair. Do not silently introduce a bug in this main command.

This exercise is a **small teaching adaptation** of `src/agent.py`: a trusted Fortran driver and independent test oracle are supplied, Questioner generates additional tests and diagnostic requests, and Solver makes the translation. Do not say that it reproduces the paper's full data-generation pipeline.

Practical safety: only compile toy code from this trusted local example, within this working directory; OpenCode-generated code is untrusted and must not run in a sensitive environment. The example harness is NOT an OS sandbox.
