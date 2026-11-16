#!/usr/bin/env python3
"""Independent compiler/numeric oracle for the OpenCode Beyond Code Pairs demo.

No model APIs are used here: OpenCode owns Questioner and Solver messages.
The trusted driver compiles model-produced *function only* and compares it to
an independently executed Fortran reference on multiple inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUN_DEFAULT = ROOT / "runs" / "opencode_latest"
FIXTURES = ROOT / "fixtures"
REQUIRED_FILES = ("source.f90", "driver.f90", "driver.cpp")
BASE_CASES = [
    {"name": "ramp", "x": [0, 2, 4, 8, 16, 32, 64, 128]},
    {"name": "constant", "x": [1, 1, 1, 1, 1, 1, 1, 1]},
    {"name": "n3_minimal", "x": [2, 8, 14]},
    {"name": "alternating_signs", "x": [-8, 5, -1, 10, -3, 12]},
    {"name": "linear_gradient", "x": [-17, -11, -5, 1, 7, 13, 19]},
    {"name": "irregular", "x": [3.25, -8.5, 0.5, 4.75, 10.125, -2.0, 7.0]},
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cmd(cmd: list[str], cwd: Path, *, input_str: str | None = None,
            timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), input=input_str,
                           text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout,
                "stderr": p.stderr, "timeout": False}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"cmd": cmd, "exit_code": None, "stdout": "",
                "stderr": str(e), "timeout": True}


def validate_cases_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Missing Questioner output: {path}. Run the bcp-questioner subagent first.")
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Questioner file must be JSON object: {\"cases\": [{\"name\": ..., \"x\": [...]}, ...]}")
    cases = payload["cases"]
    if not 1 <= len(cases) <= 4:
        raise ValueError("Questioner must supply 1-4 extra test cases")
    names = {case["name"] for case in BASE_CASES}
    validated: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Every case must be an object")
        name, xs = case.get("name"), case.get("x")
        if not isinstance(name, str) or not name.replace("_", "").isalnum() or not 1 <= len(name) <= 32:
            raise ValueError(f"Invalid case name {name!r}; use <=32 ASCII alphanumeric/underscore chars")
        if name in names:
            raise ValueError(f"Duplicate case name: {name}")
        if not isinstance(xs, list) or not 3 <= len(xs) <= 64:
            raise ValueError(f"Case {name} requires 3-64 input numbers")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or abs(x) > 1e8 for x in xs):
            raise ValueError(f"Case {name} contains invalid/nonfinite/out-of-range numbers")
        validated.append({"name": name, "x": [float(x) for x in xs]})
        names.add(name)
    return validated


def all_cases(run: Path, require_questioner: bool = True) -> list[dict[str, Any]]:
    qp = run / "questioner_cases.json"
    if require_questioner:
        return BASE_CASES + validate_cases_json(qp)
    return BASE_CASES + (validate_cases_json(qp) if qp.exists() else [])


def python_oracle(x: list[float]) -> list[float]:
    return [(x[i - 1] + 2 * x[i] + x[i + 1]) / 4 for i in range(1, len(x) - 1)]


def encoded_input(x: list[float]) -> str:
    return f"{len(x)}\n" + " ".join(f"{v:.17g}" for v in x) + "\n"


def numeric_output(out: str, n: int) -> list[float]:
    vals = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        try:
            value = float(line.strip().replace("D", "E").replace("d", "e"))
        except ValueError as e:
            raise ValueError(f"Unexpected nonnumeric output {line!r}") from e
        if not math.isfinite(value):
            raise ValueError("Nonfinite output")
        vals.append(value)
    if len(vals) != n - 2:
        raise ValueError(f"Expected {n-2} numerical lines, got {len(vals)}")
    return vals


def same(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) and all(math.isclose(x, y, rel_tol=1e-10, abs_tol=1e-10)
                                     for x, y in zip(a, b))


def prepare_reference(run: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    c = run_cmd(["gfortran", "-O0", "-fcheck=all", "-o", "fortran_reference", "source.f90", "driver.f90"], run)
    info: dict[str, Any] = {"compile": c, "case_results": []}
    if c["exit_code"] != 0:
        info["pass"] = False
        return info
    for case in cases:
        r = run_cmd([str(run / "fortran_reference")], run,
                    input_str=encoded_input(case["x"]), timeout=5)
        result: dict[str, Any] = {"name": case["name"], "input": case["x"], "run": r}
        try:
            vals = numeric_output(r["stdout"], len(case["x"])) if r["exit_code"] == 0 else []
            result["values"] = vals
            result["pass"] = r["exit_code"] == 0 and same(vals, python_oracle(case["x"]))
        except ValueError as e:
            result["pass"], result["parse_error"] = False, str(e)
        info["case_results"].append(result)
    info["pass"] = all(case["pass"] for case in info["case_results"])
    return info


def init(run: Path) -> int:
    run.mkdir(parents=True, exist_ok=True)
    # A new /bcp-demo run must never accidentally reuse an earlier model response.
    for pattern in ("questioner_plan.md", "questioner_cases.json", "questioner_feedback_*.md",
                    "solver_*.md", "candidate.cpp", "candidate_before_injection.cpp"):
        for stale in run.glob(pattern):
            stale.unlink()
    for filename in REQUIRED_FILES:
        shutil.copyfile(ROOT / filename, run / filename)
    # Avoid replacing earlier actual agent output; only clear derived results.
    for p in run.glob("test_attempt_*.json"):
        p.unlink()
    for p in run.glob("candidate_attempt_*.cpp"):
        p.unlink()
    for p in (run / "transcript.md", run / "events.jsonl", run / "reference_validation.json",
              run / "fortran_reference", run / "cpp_candidate", run / "injection.json"):
        if p.exists():
            p.unlink()
    save_json(run / "manifest.json", {"created": now(), "mode": "opencode-live", "reference": "source.f90",
                                       "notes": "Questioner and Solver files are produced by OpenCode; test runner is deterministic"})
    r = prepare_reference(run, BASE_CASES)
    save_json(run / "reference_validation.json", r)
    if not r["pass"]:
        print("Reference failed: open reference_validation.json")
        return 1
    print(f"READY. Reference compiled and passed {len(BASE_CASES)} independent numeric tests.")
    print(f"Run directory: {run}")
    print("NEXT: @bcp-questioner writes questioner_cases.json + questioner_plan.md")
    return 0


def check_tests(run: Path) -> int:
    try:
        cases = all_cases(run)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"QUESTIONER TESTS ERROR: {e}")
        return 1
    print(f"QUESTIONER TESTS VALIDATED: {len(cases) - len(BASE_CASES)} extra cases, {len(cases)} total.")
    print("NEXT: @bcp-solver writes candidate.cpp and solver_01.md")
    return 0


def verify(run: Path) -> int:
    if not (run / "manifest.json").exists():
        print("Run 'init' first")
        return 2
    if not (run / "candidate.cpp").exists():
        print("Missing Solver output: candidate.cpp")
        return 2
    try:
        cases = all_cases(run)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"QUESTIONER TESTS ERROR: {e}")
        return 2
    attempt = 1 + len(list(run.glob("test_attempt_*.json")))
    shutil.copyfile(run / "candidate.cpp", run / f"candidate_attempt_{attempt:02d}.cpp")
    candidate_sha = hashlib.sha256((run / "candidate.cpp").read_bytes()).hexdigest()
    ref = prepare_reference(run, cases)
    if not ref["pass"]:
        print("Fortran reference verification FAILED. See report.")
        return 2
    cc = run_cmd(["g++", "-std=c++17", "-O0", "-Wall", "-Wextra", "-pedantic",
                  "-o", "cpp_candidate", "candidate.cpp", "driver.cpp"], run)
    report: dict[str, Any] = {"timestamp": now(), "attempt": attempt, "candidate_sha256": candidate_sha,
                              "compile": cc, "cases": [], "questioner_cases": len(cases) - len(BASE_CASES),
                              "reference_pass": ref["pass"], "overall_pass": False}
    if cc["exit_code"] == 0:
        for c, frc in zip(cases, ref["case_results"]):
            rr = run_cmd([str(run / "cpp_candidate")], run, input_str=encoded_input(c["x"]), timeout=5)
            outcome: dict[str, Any] = {"name": c["name"], "input": c["x"],
                                      "reference_output": frc["values"], "candidate_run": rr}
            try:
                values = numeric_output(rr["stdout"], len(c["x"])) if rr["exit_code"] == 0 else []
                outcome["candidate_output"] = values
                outcome["pass"] = rr["exit_code"] == 0 and same(values, frc["values"])
                if not outcome["pass"]:
                    outcome["error"] = "Numerical mismatch or nonzero exit code"
            except ValueError as e:
                outcome["pass"], outcome["error"] = False, str(e)
            report["cases"].append(outcome)
    report["overall_pass"] = cc["exit_code"] == 0 and all(c["pass"] for c in report["cases"])
    save_json(run / f"test_attempt_{attempt:02d}.json", report)
    state = "PASS" if report["overall_pass"] else "FAIL"
    print(f"ATTEMPT {attempt:02d}: {state}; compile exit {cc['exit_code']}")
    for result in report["cases"]:
        print(f"  {'PASS' if result['pass'] else 'FAIL'} {result['name']}: expected {result['reference_output']} got {result.get('candidate_output', [])}")
    if cc["exit_code"] != 0:
        print("  Compiler stderr:", cc["stderr"][:2200])
    print(f"Report: {run / f'test_attempt_{attempt:02d}.json'}")
    if not report["overall_pass"]:
        print(f"NEXT: @bcp-questioner writes questioner_feedback_{attempt:02d}.md; @bcp-solver repairs candidate.cpp")
        return 1
    print("NEXT: run 'transcript'. Optional: run 'inject' for a labelled teaching repair exercise.")
    return 0


def inject(run: Path) -> int:
    reports = sorted(run.glob("test_attempt_*.json"))
    if not reports or not load_json(reports[-1]).get("overall_pass"):
        print("Injection allowed only AFTER an actual verified PASS. Run /bcp-demo first.")
        return 2
    if (run / "injection.json").exists():
        print("This run already includes an injected fixture. Use /bcp-demo to start a fresh experiment.")
        return 2
    dst = run / "candidate_before_injection.cpp"
    shutil.copyfile(run / "candidate.cpp", dst)
    shutil.copyfile(FIXTURES / "candidate_buggy.cpp", run / "candidate.cpp")
    save_json(run / "injection.json", {"timestamp": now(), "explicitly_injected": True,
                                        "what": "Replace candidate.cpp with a known bad 1-D stencil fixture",
                                        "source": "fixtures/candidate_buggy.cpp",
                                        "original_candidate_saved": dst.name,
                                        "NOT_LLM_ERROR": True})
    print("INSTRUCTOR-INJECTED BUG (NOT a model failure). Original saved as candidate_before_injection.cpp.")
    print("NEXT: verify -> @bcp-questioner feedback -> @bcp-solver repair -> verify")
    return 0


def add_segment(events: list[dict[str, Any]], role: str, heading: str, body: str, file: str) -> None:
    events.append({"role": role, "title": heading, "file": file, "text": body})


def transcript(run: Path) -> int:
    if not (run / "manifest.json").exists():
        print("Run 'init' first")
        return 2
    events: list[dict[str, Any]] = []
    def add_file(role: str, title: str, rel: str):
        p = run / rel
        if p.exists():
            add_segment(events, role, title, p.read_text(encoding="utf-8"), rel)
    add_file("Source", "Given Fortran kernel", "source.f90")
    add_file("Tool", "Validated Fortran baseline", "reference_validation.json")
    add_file("Questioner", "Test strategy and translation request (actual OpenCode subagent artifact)", "questioner_plan.md")
    add_file("Questioner", "Questioner-generated numeric test cases", "questioner_cases.json")
    reports = sorted(run.glob("test_attempt_*.json"))
    for p in reports:
        idx = int(p.stem.split("_")[-1])
        if idx > 1:
            add_file("Questioner", f"Targeted repair instruction before attempt {idx}", f"questioner_feedback_{idx-1:02d}.md")
        candidate_file = run / f"candidate_attempt_{idx:02d}.cpp"
        injected = (run / "injection.json").exists() and candidate_file.exists() and (
            candidate_file.read_bytes() == (FIXTURES / "candidate_buggy.cpp").read_bytes()
        )
        if injected:
            add_file("Instructor", f"INSTRUCTOR-INJECTED buggy C++ fixture, attempt {idx} — NOT an LLM error",
                     f"candidate_attempt_{idx:02d}.cpp")
        else:
            add_file("Solver", f"Solver-submitted C++ candidate, attempt {idx}",
                     f"candidate_attempt_{idx:02d}.cpp")
        add_file("Solver", f"Solver agent notes, attempt {idx}", f"solver_{idx:02d}.md")
        add_file("Tool", f"Independent compilation and numerical tests, attempt {idx}", p.name)
    add_file("Instructor", "Explicitly injected failure marker (not produced by model)", "injection.json")
    (run / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")
    chunks = ["# Beyond Code Pairs — OpenCode end-to-end transcript", "",
              "**Provenance:** Questioner/Solver sections reproduce files saved during the exercise; "
              "they are NOT the complete hidden OpenCode session transcript. Tool sections record real local "
              "compiler/runtime results. An Instructor-injected fixture, if present, "
              "is explicitly labelled and must not be presented as a model mistake.", ""]
    for e in events:
        chunks += [f"## [{e['role']}] {e['title']}", f"Source: `{e['file']}`", "",
                   f"```{'json' if e['file'].endswith('.json') else 'cpp' if e['file'].endswith('.cpp') else 'fortran' if e['file'].endswith('.f90') else 'text'}",
                   e["text"].rstrip(), "```", ""]
    (run / "transcript.md").write_text("\n".join(chunks), encoding="utf-8")
    print(f"Transcript: {run/'transcript.md'}")
    print(f"Events JSONL: {run/'events.jsonl'} ({len(events)} events)")
    if reports:
        last = load_json(reports[-1])
        print(f"Final verification: {'PASS' if last['overall_pass'] else 'FAIL'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "check-tests", "verify", "inject", "transcript", "status"])
    parser.add_argument("--run-dir", type=Path, default=RUN_DEFAULT)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.action == "init": return init(run)
    if args.action == "check-tests": return check_tests(run)
    if args.action == "verify": return verify(run)
    if args.action == "inject": return inject(run)
    if args.action == "transcript": return transcript(run)
    if args.action == "status":
        reports = sorted(run.glob("test_attempt_*.json"))
        print(f"Run: {run}\nAttempts: {len(reports)}")
        for p in reports:
            print(p.name, "PASS" if load_json(p).get("overall_pass") else "FAIL")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
