# SC26 Beyond Code Pairs — Progressive 2-D OpenCode Hands-on

Run `/bcp-demo` in [OpenCode](https://opencode.ai/) from the repository's `SC26` directory.

This version intentionally cannot finish after one easy translation. The model must complete three Questioner–Solver–Verifier rounds while translating a 2-D Fortran heat-diffusion routine to C++:

1. **Gate 1 — one step:** translate the five-point stencil, preserve four boundaries, and map Fortran `(i,j)` storage to flat C++ offset `i + nx*j`.
2. **Gate 2 — time loop:** add zero/multiple steps, double buffering, odd/even swap parity, final output selection, and `last_max_delta`.
3. **Gate 3 — adversarial regression:** Questioner creates two new asymmetric cases, including rectangular dimensions and both odd/even step counts; Solver audits the full solution before final verification.

Even if the code passes each gate on its first attempt, attendees see three distinct reasoning cycles. Repairs happen only in response to real compiler or numerical evidence.

## Prerequisites and start

- OpenCode installed with a model selected in its UI. No model, API key, or endpoint is hardcoded here.
- Python 3.9+, `gfortran`, and `g++` on `PATH`.
- A temporary teaching environment is recommended because model-generated code is executed locally; this harness is not an OS sandbox.

```bash
git clone https://github.com/thelechen/beyond-code-pairs-translation.git
cd beyond-code-pairs-translation/SC26
opencode
```

Then enter:

```text
/bcp-demo
```

The command inherits the model you selected and orchestrates all three gates. It never fabricates a model error. If a gate fails, Questioner reads the exact report and Solver gets one evidence-based repair attempt before the exercise stops.

## Read the result

Generated evidence is under `tutorial_demo/opencode_e2e/runs/opencode_latest/`:

```text
questioner_stage_01.md              # layout/boundary translation request
solver_stage_01.md                  # Solver's Gate 1 explanation
gate_01_attempt_01.json             # real compile/numeric evidence
candidate_gate_01_attempt_01.cpp    # exact submitted code
questioner_stage_02.md              # multi-step/double-buffer request
gate_02_attempt_01.json
questioner_stage_03.md              # adversarial-test strategy
questioner_cases.json               # two model-generated grids
gate_03_attempt_01.json
transcript.md                       # readable role-labelled record
events.jsonl                        # structured record
```

From a second terminal at the `SC26` directory:

```bash
python3 tutorial_demo/opencode_e2e/harness.py status
less tutorial_demo/opencode_e2e/runs/opencode_latest/transcript.md
```

Read the artifacts in gate order. In each JSON report, check `compile.exit_code`, `overall_pass`, then each case's reference and candidate output. Useful discussion questions include: Which rectangular case exposes a wrong stride? Why can an even/odd swap bug survive a one-step test? Why must the boundary remain unchanged? Why is a compile success not semantic equivalence?

## Optional labelled repair exercise

After Gate 3 passes, `/bcp-repair` replaces the verified candidate with a known stale-buffer fixture, then asks the real Questioner/Solver roles to diagnose and repair it. The transcript marks it **INSTRUCTOR-INJECTED** and **NOT an LLM error**.

## Reset safely

```bash
make clean
opencode
```

`make clean` removes only generated run artifacts and local Python caches. It preserves source, fixtures, harness, tests, `.opencode/`, documentation, and the Makefile. Save the run directory elsewhere first if you want to keep its transcript. `/bcp-demo` also resets the default run at initialization.

## Instructor smoke test

This validates the deterministic harness and bundled fixtures without calling a model:

```bash
python3 -m unittest discover -s tutorial_demo/opencode_e2e/tests -v
```

This remains a compact teaching adaptation of the Beyond Code Pairs workflow, not a reproduction of the full research data-generation pipeline. Source paper: [Beyond Code Pairs — ACL 2026](https://aclanthology.org/2026.acl-long.1557/).
