import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import harness


def generated_cases():
    return {
        "cases": [
            {"name": "q_rect_odd", "nx": 4, "ny": 5, "steps": 3, "alpha": 0.13,
             "grid": [90, 91, 92, 93, 80, -4, 6, 83, 70, 8, -9, 73,
                      60, 3, 11, 63, 50, 51, 52, 53]},
            {"name": "q_square_even", "nx": 5, "ny": 5, "steps": 4, "alpha": 0.21,
             "grid": [1, 2, 3, 4, 5, 6, -7, 8, 9, 10, 11, 12, 40, -14, 15,
                      16, 17, 18, 19, 20, 21, 22, 23, 24, 25]},
        ]
    }


@unittest.skipUnless(shutil.which("gfortran") and shutil.which("g++"),
                     "requires gfortran and g++")
class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.assertEqual(harness.init(self.run), 0)

    def add_questioner_artifacts(self):
        for stage in range(1, 4):
            (self.run / f"questioner_stage_{stage:02d}.md").write_text(
                f"Questioner stage {stage} test fixture", encoding="utf-8")
            (self.run / f"solver_stage_{stage:02d}.md").write_text(
                f"Solver stage {stage} test fixture", encoding="utf-8")
        harness.save_json(self.run / "questioner_cases.json", generated_cases())

    def test_progressive_good_candidate_and_transcript(self):
        self.add_questioner_artifacts()
        self.assertEqual(harness.check_tests(self.run), 0)
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        self.assertEqual(harness.verify(self.run, 1), 0)
        self.assertEqual(harness.verify(self.run, 2), 0)
        self.assertEqual(harness.verify(self.run, 3), 0)
        for stage in range(1, 4):
            report = harness.load_json(self.run / f"gate_{stage:02d}_attempt_01.json")
            self.assertTrue(report["overall_pass"])
            self.assertEqual(report["gate"], stage)
        self.assertEqual(harness.transcript(self.run), 0)
        transcript = (self.run / "transcript.md").read_text(encoding="utf-8")
        self.assertIn("Gate 1 independent verification", transcript)
        self.assertIn("Gate 3 generated cases", transcript)

    def test_gate_order_is_enforced(self):
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        self.assertEqual(harness.verify(self.run, 2), 2)
        self.assertFalse(list(self.run.glob("gate_02_attempt_*.json")))

    def test_invalid_questioner_cases_rejected(self):
        bad = generated_cases()
        bad["cases"][1]["steps"] = 3
        harness.save_json(self.run / "questioner_cases.json", bad)
        self.assertEqual(harness.check_tests(self.run), 1)

    def test_compilation_failure_is_captured(self):
        (self.run / "candidate.cpp").write_text(
            "#include <vector>\nvoid wrong_symbol() {}\n", encoding="utf-8")
        self.assertEqual(harness.verify(self.run, 1), 1)
        report = harness.load_json(self.run / "gate_01_attempt_01.json")
        self.assertNotEqual(report["compile"]["exit_code"], 0)
        self.assertTrue(report["compile"]["stderr"])
        self.assertFalse(report["overall_pass"])

    def test_injected_bug_fails_then_repair_passes(self):
        self.add_questioner_artifacts()
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        for stage in range(1, 4):
            self.assertEqual(harness.verify(self.run, stage), 0)
        self.assertEqual(harness.inject(self.run), 0)
        self.assertEqual(harness.verify(self.run, 3), 1)
        failed = harness.load_json(self.run / "gate_03_attempt_02.json")
        self.assertTrue(any(not item["pass"] for item in failed["cases"] if item["mode"] == 2))
        (self.run / "questioner_feedback_gate_03_attempt_02.md").write_text(
            "Instructor fixture returned the stale buffer.", encoding="utf-8")
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        self.assertEqual(harness.verify(self.run, 3), 0)
        self.assertEqual(harness.transcript(self.run), 0)
        transcript = (self.run / "transcript.md").read_text(encoding="utf-8")
        self.assertIn("INSTRUCTOR-INJECTED candidate", transcript)
        events = [json.loads(line) for line in (self.run / "events.jsonl").read_text().splitlines()]
        self.assertTrue(any(event["role"] == "Instructor" for event in events))

    def test_init_resets_generated_files(self):
        (self.run / "candidate.cpp").write_text("stale", encoding="utf-8")
        (self.run / "questioner_cases.json").write_text("stale", encoding="utf-8")
        (self.run / "gate_01_attempt_01.json").write_text("stale", encoding="utf-8")
        self.assertEqual(harness.init(self.run), 0)
        for name in ("candidate.cpp", "questioner_cases.json", "gate_01_attempt_01.json"):
            self.assertFalse((self.run / name).exists())


if __name__ == "__main__":
    unittest.main()
