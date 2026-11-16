# SC26 OpenCode Hands-on — 2-minute setup

This add-on is designed for Le Chen's **Beyond Code Pairs** tutorial exercise.
It does not change `src/agent.py` or training/data files in the original repository.

1. Add this ZIP's contents at the root of `thelechen/beyond-code-pairs-translation` (keep the hidden `.opencode` directory).
2. Install Python, `gfortran`, `g++`; OpenCode and the selected model are assumed ready.
3. In the project root, run `opencode`.
4. Inside OpenCode, enter **`/bcp-demo`**.
5. Inspect `tutorial_demo/opencode_e2e/runs/opencode_latest/transcript.md` and `events.jsonl`.
6. Optional, after a pass: **`/bcp-repair`** for a clearly-labelled instructor-injected error and actual Questioner–Solver repair.

Read `tutorial_demo/opencode_e2e/README.md` for prerequisites, evidence provenance, safety, and troubleshooting. No model or API endpoint is hardcoded.
