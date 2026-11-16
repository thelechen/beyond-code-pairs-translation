# SC26 OpenCode Hands-on — Progressive 2-D translation

1. Clone `thelechen/beyond-code-pairs-translation` and enter `SC26`.
2. Confirm Python, `gfortran`, `g++`, and OpenCode are installed.
3. Start `opencode` and select the model you want attendees to use.
4. Enter **`/bcp-demo`**.
5. Watch three required gates: one 2-D step, multi-step double buffering, then model-generated adversarial regression.
6. Read `tutorial_demo/opencode_e2e/runs/opencode_latest/transcript.md` and the three `gate_XX_attempt_YY.json` reports.
7. Optional after Gate 3 passes: enter **`/bcp-repair`** for a clearly labelled instructor-injected stale-buffer bug and real model-driven repair.

The exercise does not set a model or API endpoint. See `tutorial_demo/opencode_e2e/README.md` for signatures, artifacts, evidence interpretation, and safety notes.

## Start a fresh run

```bash
make clean
opencode
```

`make clean` removes only generated run files and Python caches. It preserves all exercise sources, fixtures, tests, OpenCode definitions, documentation, and the Makefile.
