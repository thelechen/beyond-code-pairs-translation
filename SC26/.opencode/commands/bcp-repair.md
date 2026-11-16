---
description: Optional labelled stale-buffer failure and evidence-based repair
agent: bcp-orchestrator
---

Continue a completed `/bcp-demo` with the current model. Never present the injected error as a model mistake. Use only the callable child subagents `bcp-questioner` and `bcp-solver` for role artifacts. If either invocation fails or is unavailable, stop; the orchestrator must never write or repair their files itself.

1. Run `python3 tutorial_demo/opencode_e2e/harness.py status`; stop unless Gate 3 is PASS.
2. Run `python3 tutorial_demo/opencode_e2e/harness.py inject`. This saves the verified candidate and installs an explicitly labelled stale double-buffer fixture.
3. Run `python3 tutorial_demo/opencode_e2e/harness.py verify --stage 3`; it must fail numerically. Read the exact new Gate 3 report.
4. Ask `bcp-questioner` for repair feedback in `questioner_feedback_gate_03_attempt_XX.md`, explicitly identifying the instructor injection. Ask `bcp-solver` to repair `candidate.cpp` and record the repair in `solver_stage_03.md`.
5. Run `verify --stage 3` again, with at most one further evidence-based repair. Then run `transcript` and clearly separate agent output, tool evidence, and the instructor fixture.
