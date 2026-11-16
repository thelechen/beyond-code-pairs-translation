#!/usr/bin/env python3
"""Progressive compiler/numeric oracle for the SC26 Beyond Code Pairs demo.

OpenCode owns the Questioner/Solver dialogue.  This harness independently
compiles the supplied Fortran reference and verifies three increasingly hard
C++ translation gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUN_DEFAULT = ROOT / "runs" / "opencode_latest"
FIXTURES = ROOT / "fixtures"
REQUIRED_FILES = ("source.f90", "driver.f90", "driver.cpp", "driver_step.cpp")


def case(name: str, nx: int, ny: int, steps: int, alpha: float,
         grid: list[float], mode: int) -> dict[str, Any]:
    return {"name": name, "nx": nx, "ny": ny, "steps": steps,
            "alpha": alpha, "grid": grid, "mode": mode}


GATE1_CASES = [
    case("g1_center_pulse", 3, 3, 1, 0.20,
         [1, 2, 3, 4, 20, 6, 7, 8, 9], 1),
    case("g1_rectangular_layout", 4, 5, 1, 0.125,
         [0, 1, 2, 3, 10, -4, 6, 13, 20, 7, -8, 23,
          30, 11, 12, 33, 40, 41, 42, 43], 1),
    case("g1_boundary_sentinels", 6, 4, 1, 0.25,
         [91, 92, 93, 94, 95, 96, 81, 1, 3, 7, 9, 86,
          71, -2, 8, -4, 6, 76, 61, 62, 63, 64, 65, 66], 1),
]

GATE2_CASES = [
    case("g2_zero_steps", 5, 4, 0, 0.20,
         [10, 11, 12, 13, 14, 20, 1, -2, 5, 24,
          30, 7, 4, -3, 34, 40, 41, 42, 43, 44], 2),
    case("g2_even_steps", 5, 5, 2, 0.20,
         [0, 1, 2, 3, 4, 10, 0, 0, 0, 14, 20, 0, 50, 0, 24,
          30, 0, 0, 0, 34, 40, 41, 42, 43, 44], 2),
    case("g2_odd_steps", 5, 5, 3, 0.15,
         [9, 8, 7, 6, 5, 4, -3, 2, 11, 12, 13, 17, -19, 23, 24,
          25, 29, 31, -37, 39, 40, 41, 42, 43, 44], 2),
    case("g2_rectangular_five_steps", 6, 4, 5, 0.10,
         [100, 101, 102, 103, 104, 105, 90, -5, 2, 8, -1, 95,
          80, 7, -9, 4, 12, 85, 70, 71, 72, 73, 74, 75], 2),
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
        result = subprocess.run(cmd, cwd=str(cwd), input=input_str, text=True,
                                capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr, "timeout": False}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"cmd": cmd, "exit_code": None, "stdout": "",
                "stderr": str(exc), "timeout": True}


def index(i: int, j: int, nx: int) -> int:
    return i + nx * j


def heat_step_python(nx: int, ny: int, alpha: float,
                     values: list[float]) -> tuple[list[float], float]:
    output = list(values)
    last_max_delta = 0.0
    for j in range(1, ny - 1):
        for i in range(1, nx - 1):
            k = index(i, j, nx)
            output[k] = values[k] + alpha * (
                values[k - 1] + values[k + 1] + values[k - nx] + values[k + nx]
                - 4.0 * values[k])
            last_max_delta = max(last_max_delta, abs(output[k] - values[k]))
    return output, last_max_delta


def solve_python(nx: int, ny: int, steps: int, alpha: float,
                 values: list[float]) -> tuple[list[float], float]:
    current = list(values)
    last_max_delta = 0.0
    for _ in range(steps):
        current, last_max_delta = heat_step_python(nx, ny, alpha, current)
    return current, last_max_delta


def expected(c: dict[str, Any]) -> tuple[list[float], float]:
    if c["mode"] == 1:
        return heat_step_python(c["nx"], c["ny"], c["alpha"], c["grid"])
    return solve_python(c["nx"], c["ny"], c["steps"], c["alpha"], c["grid"])


def encoded_input(c: dict[str, Any]) -> str:
    header = f'{c["mode"]} {c["nx"]} {c["ny"]} {c["steps"]} {c["alpha"]:.17g}\n'
    return header + " ".join(f"{value:.17g}" for value in c["grid"]) + "\n"


def numeric_output(text: str, count: int) -> tuple[list[float], float]:
    values: list[float] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = float(line.strip().replace("D", "E").replace("d", "e"))
        except ValueError as exc:
            raise ValueError(f"Unexpected nonnumeric output {line!r}") from exc
        if not math.isfinite(value):
            raise ValueError("Nonfinite output")
        values.append(value)
    if len(values) != count + 1:
        raise ValueError(f"Expected {count + 1} numerical lines, got {len(values)}")
    return values[1:], values[0]


def close_scalar(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)


def close_list(a: list[float], b: list[float]) -> bool:
    return len(a) == len(b) and all(close_scalar(x, y) for x, y in zip(a, b))


def validate_cases_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Missing Questioner output: {path}")
    payload = load_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError('Expected {"cases": [...]}')
    raw_cases = payload["cases"]
    if len(raw_cases) != 2:
        raise ValueError("Gate 3 requires exactly two Questioner cases")
    names = {c["name"] for c in GATE1_CASES + GATE2_CASES}
    validated: list[dict[str, Any]] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("Every Questioner case must be an object")
        name = raw.get("name")
        nx, ny, steps = raw.get("nx"), raw.get("ny"), raw.get("steps")
        alpha, grid = raw.get("alpha"), raw.get("grid")
        if not isinstance(name, str) or not name.replace("_", "").isalnum() or not 1 <= len(name) <= 40:
            raise ValueError(f"Invalid case name: {name!r}")
        if name in names:
            raise ValueError(f"Duplicate case name: {name}")
        if isinstance(nx, bool) or not isinstance(nx, int) or not 3 <= nx <= 10:
            raise ValueError(f"{name}: nx must be an integer from 3 to 10")
        if isinstance(ny, bool) or not isinstance(ny, int) or not 3 <= ny <= 10:
            raise ValueError(f"{name}: ny must be an integer from 3 to 10")
        if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 8:
            raise ValueError(f"{name}: steps must be an integer from 1 to 8")
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0.0 <= alpha <= 0.25:
            raise ValueError(f"{name}: alpha must be finite and in [0, 0.25]")
        if not isinstance(grid, list) or len(grid) != nx * ny:
            raise ValueError(f"{name}: grid must contain nx*ny values in i + nx*j order")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
               not math.isfinite(v) or abs(v) > 1e8 for v in grid):
            raise ValueError(f"{name}: grid contains an invalid value")
        if len({float(v) for v in grid}) < 4:
            raise ValueError(f"{name}: use a nontrivial asymmetric grid")
        validated.append(case(name, nx, ny, steps, float(alpha),
                              [float(v) for v in grid], 2))
        names.add(name)
    if not any(c["nx"] != c["ny"] for c in validated):
        raise ValueError("At least one Gate 3 case must be rectangular")
    if {c["steps"] % 2 for c in validated} != {0, 1}:
        raise ValueError("Gate 3 cases must use one even and one odd step count")
    return validated


def prepare_reference(run: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    compile_result = run_cmd(["gfortran", "-O0", "-fcheck=all", "-Wall",
                              "-o", "fortran_reference", "source.f90", "driver.f90"], run)
    info: dict[str, Any] = {"compile": compile_result, "case_results": []}
    if compile_result["exit_code"] != 0:
        info["pass"] = False
        return info
    for c in cases:
        process = run_cmd([str(run / "fortran_reference")], run,
                          input_str=encoded_input(c), timeout=5)
        expected_grid, expected_delta = expected(c)
        result: dict[str, Any] = {"name": c["name"], "run": process,
                                  "expected_grid": expected_grid,
                                  "expected_last_max_delta": expected_delta}
        try:
            actual_grid, actual_delta = numeric_output(process["stdout"], c["nx"] * c["ny"])
            result["actual_grid"] = actual_grid
            result["actual_last_max_delta"] = actual_delta
            result["pass"] = (process["exit_code"] == 0 and
                              close_list(actual_grid, expected_grid) and
                              close_scalar(actual_delta, expected_delta))
        except ValueError as exc:
            result["pass"], result["parse_error"] = False, str(exc)
        info["case_results"].append(result)
    info["pass"] = all(item["pass"] for item in info["case_results"])
    return info


def latest_gate_pass(run: Path, stage: int) -> bool:
    reports = sorted(run.glob(f"gate_{stage:02d}_attempt_*.json"))
    return bool(reports and load_json(reports[-1]).get("overall_pass"))


def init(run: Path) -> int:
    run.mkdir(parents=True, exist_ok=True)
    for pattern in ("questioner_stage_*.md", "questioner_cases.json",
                    "questioner_feedback_*.md", "solver_stage_*.md",
                    "candidate.cpp", "candidate_before_injection.cpp",
                    "gate_*_attempt_*.json", "candidate_gate_*_attempt_*.cpp"):
        for stale in run.glob(pattern):
            stale.unlink()
    for filename in REQUIRED_FILES:
        shutil.copyfile(ROOT / filename, run / filename)
    for name in ("transcript.md", "events.jsonl", "reference_validation.json",
                 "fortran_reference", "cpp_candidate", "injection.json"):
        path = run / name
        if path.exists():
            path.unlink()
    save_json(run / "manifest.json", {
        "created": now(), "mode": "opencode-progressive-2d",
        "layout": "flat offset i + nx*j matches Fortran column-major storage",
        "gates": ["one 2-D step", "multi-step double buffering", "adversarial regression"]})
    reference = prepare_reference(run, GATE1_CASES + GATE2_CASES)
    save_json(run / "reference_validation.json", reference)
    if not reference["pass"]:
        print("REFERENCE FAILED: inspect reference_validation.json")
        return 1
    print(f"READY: Fortran reference passed {len(GATE1_CASES) + len(GATE2_CASES)} fixed cases.")
    print("NEXT: Questioner Stage 1 plans the one-step translation.")
    return 0


def check_tests(run: Path) -> int:
    try:
        cases = validate_cases_json(run / "questioner_cases.json")
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"QUESTIONER TESTS ERROR: {exc}")
        return 1
    print("QUESTIONER TESTS VALIDATED: " + ", ".join(c["name"] for c in cases))
    return 0


def verify(run: Path, stage: int) -> int:
    if not (run / "manifest.json").exists():
        print("Run init first")
        return 2
    if not (run / "candidate.cpp").exists():
        print("Missing Solver output: candidate.cpp")
        return 2
    if stage == 2 and not latest_gate_pass(run, 1):
        print("Gate 2 is locked until Gate 1 passes")
        return 2
    if stage == 3 and not latest_gate_pass(run, 2):
        print("Gate 3 is locked until Gate 2 passes")
        return 2
    cases = list(GATE1_CASES)
    if stage >= 2:
        cases += GATE2_CASES
    if stage == 3:
        try:
            cases += validate_cases_json(run / "questioner_cases.json")
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"QUESTIONER TESTS ERROR: {exc}")
            return 2

    attempt = 1 + len(list(run.glob(f"gate_{stage:02d}_attempt_*.json")))
    archived = run / f"candidate_gate_{stage:02d}_attempt_{attempt:02d}.cpp"
    shutil.copyfile(run / "candidate.cpp", archived)
    candidate_sha = hashlib.sha256((run / "candidate.cpp").read_bytes()).hexdigest()
    reference = prepare_reference(run, cases)
    driver = "driver_step.cpp" if stage == 1 else "driver.cpp"
    compile_result = run_cmd(["g++", "-std=c++17", "-O0", "-Wall", "-Wextra",
                              "-pedantic", "-o", "cpp_candidate",
                              "candidate.cpp", driver], run)
    report: dict[str, Any] = {
        "timestamp": now(), "gate": stage, "attempt": attempt,
        "candidate_sha256": candidate_sha, "driver": driver,
        "compile": compile_result, "reference_pass": reference["pass"],
        "cases": [], "overall_pass": False}
    if compile_result["exit_code"] == 0 and reference["pass"]:
        for c, ref_case in zip(cases, reference["case_results"]):
            process = run_cmd([str(run / "cpp_candidate")], run,
                              input_str=encoded_input(c), timeout=5)
            outcome: dict[str, Any] = {
                "name": c["name"], "mode": c["mode"], "nx": c["nx"],
                "ny": c["ny"], "steps": c["steps"],
                "reference_grid": ref_case["actual_grid"],
                "reference_last_max_delta": ref_case["actual_last_max_delta"],
                "candidate_run": process}
            try:
                grid, delta = numeric_output(process["stdout"], c["nx"] * c["ny"])
                outcome["candidate_grid"] = grid
                outcome["candidate_last_max_delta"] = delta
                outcome["pass"] = (process["exit_code"] == 0 and
                                   close_list(grid, ref_case["actual_grid"]) and
                                   close_scalar(delta, ref_case["actual_last_max_delta"]))
                if not outcome["pass"]:
                    outcome["error"] = "Numerical mismatch or nonzero exit code"
            except ValueError as exc:
                outcome["pass"], outcome["error"] = False, str(exc)
            report["cases"].append(outcome)
    report["overall_pass"] = (compile_result["exit_code"] == 0 and reference["pass"] and
                              len(report["cases"]) == len(cases) and
                              all(item["pass"] for item in report["cases"]))
    report_path = run / f"gate_{stage:02d}_attempt_{attempt:02d}.json"
    save_json(report_path, report)
    state = "PASS" if report["overall_pass"] else "FAIL"
    print(f"GATE {stage} ATTEMPT {attempt:02d}: {state}")
    if compile_result["exit_code"] != 0:
        print("Compiler stderr:", compile_result["stderr"][:2200])
    for result in report["cases"]:
        print(f"  {'PASS' if result['pass'] else 'FAIL'} {result['name']}")
    print(f"Report: {report_path}")
    return 0 if report["overall_pass"] else 1


def inject(run: Path) -> int:
    if not latest_gate_pass(run, 3):
        print("Injection is allowed only after Gate 3 passes")
        return 2
    if (run / "injection.json").exists():
        print("This run already contains an injected fixture")
        return 2
    shutil.copyfile(run / "candidate.cpp", run / "candidate_before_injection.cpp")
    shutil.copyfile(FIXTURES / "candidate_buggy.cpp", run / "candidate.cpp")
    save_json(run / "injection.json", {
        "timestamp": now(), "explicitly_injected": True,
        "what": "Stale double-buffer output after the final swap",
        "source": "fixtures/candidate_buggy.cpp", "NOT_LLM_ERROR": True})
    print("INSTRUCTOR-INJECTED stale-buffer bug installed; this is not a model failure.")
    return 0


def transcript(run: Path) -> int:
    if not (run / "manifest.json").exists():
        print("Run init first")
        return 2
    events: list[dict[str, Any]] = []

    def add(role: str, title: str, path: Path) -> None:
        if path.exists():
            events.append({"role": role, "title": title,
                           "file": path.name, "text": path.read_text(encoding="utf-8")})

    add("Source", "Given Fortran heat solver", run / "source.f90")
    add("Tool", "Validated fixed Fortran baseline", run / "reference_validation.json")
    for stage in range(1, 4):
        add("Questioner", f"Gate {stage} plan", run / f"questioner_stage_{stage:02d}.md")
        if stage == 3:
            add("Questioner", "Gate 3 generated cases", run / "questioner_cases.json")
        add("Solver", f"Gate {stage} solver notes", run / f"solver_stage_{stage:02d}.md")
        for report_path in sorted(run.glob(f"gate_{stage:02d}_attempt_*.json")):
            attempt = int(report_path.stem.split("_")[-1])
            candidate = run / f"candidate_gate_{stage:02d}_attempt_{attempt:02d}.cpp"
            injected = ((run / "injection.json").exists() and candidate.exists() and
                        candidate.read_bytes() == (FIXTURES / "candidate_buggy.cpp").read_bytes())
            add("Instructor" if injected else "Solver",
                ("INSTRUCTOR-INJECTED candidate — NOT an LLM error" if injected else
                 f"Gate {stage} candidate attempt {attempt}"), candidate)
            if attempt > 1:
                add("Questioner", f"Gate {stage} repair feedback before attempt {attempt}",
                    run / f"questioner_feedback_gate_{stage:02d}_attempt_{attempt-1:02d}.md")
            add("Tool", f"Gate {stage} independent verification attempt {attempt}", report_path)
    add("Instructor", "Explicit injection marker", run / "injection.json")
    (run / "events.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in events) + "\n",
        encoding="utf-8")
    chunks = ["# Beyond Code Pairs — progressive 2-D OpenCode transcript", "",
              "Questioner/Solver sections are saved OpenCode artifacts. Tool sections are real ",
              "compiler/runtime reports. Instructor fixtures are explicitly labelled.", ""]
    for event in events:
        suffix = Path(event["file"]).suffix
        language = {".json": "json", ".cpp": "cpp", ".f90": "fortran"}.get(suffix, "text")
        chunks += [f'## [{event["role"]}] {event["title"]}',
                   f'Source: `{event["file"]}`', "", f"```{language}",
                   event["text"].rstrip(), "```", ""]
    (run / "transcript.md").write_text("\n".join(chunks), encoding="utf-8")
    print(f"Transcript: {run / 'transcript.md'}")
    print(f"Events: {run / 'events.jsonl'} ({len(events)} records)")
    return 0


def status(run: Path) -> int:
    if not (run / "manifest.json").exists():
        print("No active run. Start with init or /bcp-demo.")
        return 0
    print(f"Run: {run}")
    for stage in range(1, 4):
        reports = sorted(run.glob(f"gate_{stage:02d}_attempt_*.json"))
        if not reports:
            print(f"Gate {stage}: NOT RUN")
        else:
            latest = load_json(reports[-1])
            print(f"Gate {stage}: {'PASS' if latest['overall_pass'] else 'FAIL'} "
                  f"({len(reports)} attempt(s))")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "check-tests", "verify", "inject",
                                           "transcript", "status"])
    parser.add_argument("--stage", type=int, choices=[1, 2, 3])
    parser.add_argument("--run-dir", type=Path, default=RUN_DEFAULT)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if args.action == "init":
        return init(run)
    if args.action == "check-tests":
        return check_tests(run)
    if args.action == "verify":
        if args.stage is None:
            parser.error("verify requires --stage 1, 2, or 3")
        return verify(run, args.stage)
    if args.action == "inject":
        return inject(run)
    if args.action == "transcript":
        return transcript(run)
    return status(run)


if __name__ == "__main__":
    raise SystemExit(main())
