# SC26 Beyond Code Pairs — OpenCode-powered End-to-End Hands-on

**One command:** `/bcp-demo` in [OpenCode](https://opencode.ai/), run from the repository's `SC26` directory, where this tutorial and its `.opencode/` definitions live.

**Goal:** watch a real Questioner propose extra unit tests, a real Solver translate a small Fortran stencil into C++, and an independent compiler/test runner decide whether code is numerically correct. On failure, Questioner uses the real error and Solver repairs; all roles and tool outputs are preserved as actual file artifacts.

This is a **minimal classroom adaptation** of the two-phase approach in the paper and `src/agent.py`, NOT a claim to run the full paper pipeline. Here the original Fortran kernel and trusted drivers are already provided; the Questioner designs new tests and the Solver translates the computation.

## Prerequisites

- OpenCode installed and usable. You choose a model in OpenCode before running the command (e.g. your chosen free model). This project deliberately sets NO model in commands/agents and NO API key or endpoint.
- Python 3.9 or newer, `gfortran`, `g++` available on PATH. No `pip install` needed for the demo.
- A temporary/containerized teaching environment strongly recommended for model-generated code. The demo's working directory is **not** a security sandbox.

## Start from an existing repository clone

```bash
git clone https://github.com/thelechen/beyond-code-pairs-translation.git
cd beyond-code-pairs-translation/SC26
opencode
```

In the OpenCode UI, select your preferred model if needed, then type:

```text
/bcp-demo
```

**What happens:**

1. Deterministic Phase A: run Fortran source with trusted `driver.f90`, verify 6 baseline cases.
2. Actual `bcp-questioner`: creates `questioner_plan.md` plus 2 extra cases in `questioner_cases.json`.
3. Actual `bcp-solver`: creates `candidate.cpp` from the Fortran source and Questioner plan; code is a function with no `main`.
4. Trusted Python harness compiles it with `driver.cpp`, runs ALL cases on Fortran and C++, and numerically compares each element (`abs_tol=rel_tol=1e-10`).
5. If any case fails, Questioner writes a feedback prompt based on the compiler/stderr/numerical mismatch; Solver revises C++; iterate up to 2 repairs.
6. Markdown/JSONL full transcript is assembled from actual artifacts.

The same OpenCode model is inherited by Questioner and Solver (neither role pins a different model). If the model already writes correct C++ on its first attempt, there is **no fabricated error**.

### Guaranteed repair exercise, separately labelled

After a successful `/bcp-demo` run, type:

```text
/bcp-repair
```

This preserves your original successful candidate under `candidate_before_injection.cpp`, intentionally places a known bad stencil fixture in its place, runs a failing numerical check, then asks real Questioner/Solver agents to diagnose and repair it. The generated record clearly says **INSTRUCTOR-INJECTED** and **NOT an LLM error**.

## Inspect the log and actual source code

All files are in:

```text
tutorial_demo/opencode_e2e/runs/opencode_latest/
├── source.f90                # provided original kernel
├── questioner_plan.md        # actual Questioner response
├── questioner_cases.json     # actual Questioner-added test inputs
├── candidate_attempt_01.cpp # exact C++ code submitted on attempt 1
├── test_attempt_01.json     # real compiler/runtime and case-by-case results
├── questioner_feedback_01.md # if first attempt failed
├── candidate_attempt_02.cpp # second attempt / repaired code
├── solver_01.md              # Solver explanation for attempt 1
├── transcript.md             # all role messages and tool evidence
└── events.jsonl              # structured role-labelled artifacts
```

From a separate terminal at the repo root:

```bash
python3 tutorial_demo/opencode_e2e/harness.py status
less tutorial_demo/opencode_e2e/runs/opencode_latest/transcript.md
# Or inspect the data behind the log:
cat tutorial_demo/opencode_e2e/runs/opencode_latest/events.jsonl
```

**Discussion prompts:** Why is compiling insufficient? Which test caught the indexing mistake? What changed after receiving compiler/numerical evidence? Why retain *question, candidate, test result, and repair*, rather than only a final code pair?

## Optional manual harness smoke test (no OpenCode)

Useful to validate workshop machines and dependencies before attendees arrive. This **does not use an LLM**:

```bash
python3 tutorial_demo/opencode_e2e/harness.py init
# A manually supplied Questioner fixture is needed for this smoke test;
# the unittest suite creates one temporarily.
python3 -m unittest discover -s tutorial_demo/opencode_e2e/tests -v
```

## Reset / limitations

The demo works in `runs/opencode_latest`. To discard a previous run and start clean, exit OpenCode and run the following from the `SC26` directory:

```bash
make clean
opencode
```

`make clean` deletes only `runs/opencode_latest` and local Python caches. It preserves the exercise source, fixtures, harness, tests, `.opencode/` configuration, documentation, and Makefile. Copy the run directory somewhere else first if you want to keep a previous transcript. Running `/bcp-demo` without cleaning also calls `init`, which resets the default run directory.

Use only the example's bundled Fortran input; do not let arbitrary downloaded projects run in this demo without proper sandboxing. The numeric tests are concrete checks, not a formal semantic-equivalence proof.

Source paper: [Beyond Code Pairs — ACL 2026](https://aclanthology.org/2026.acl-long.1557/). This add-on does not modify the research pipeline under `src/`.

### About log fidelity

`events.jsonl` captures the real *saved outputs* from Questioner/Solver and the full compiler/test reports, not every hidden internal OpenCode tool call. For the complete OpenCode parent/child conversation records, use the version-supported session exporter (`opencode session list`, then `opencode session export <session-id>`); review for secrets before sharing. The harness never fabricates agent messages.
