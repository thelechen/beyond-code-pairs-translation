import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import harness


@unittest.skipUnless(shutil.which("gfortran") and shutil.which("g++"), "requires gfortran and g++")
class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.assertEqual(harness.init(self.run), 0)
        harness.save_json(self.run / "questioner_cases.json", {
            "cases": [
                {"name": "q_spiky", "x": [-8, 5, 0, 5, -2, 99]},
                {"name": "q_fractional", "x": [0.125, -2.5, 7.75, 4.5]}
            ]})
        (self.run / "questioner_plan.md").write_text("Questioner test plan (test fixture, no model)")
        self.assertEqual(harness.check_tests(self.run), 0)

    def test_good_bad_repaired_and_provenance(self):
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        (self.run / "solver_01.md").write_text("Solver test fixture, not actual model output")
        self.assertEqual(harness.verify(self.run), 0)
        self.assertTrue(harness.load_json(self.run / "test_attempt_01.json")["overall_pass"])
        self.assertEqual(harness.inject(self.run), 0)
        self.assertEqual(harness.verify(self.run), 1)
        report = harness.load_json(self.run / "test_attempt_02.json")
        self.assertTrue(any(not case["pass"] for case in report["cases"]))
        self.assertTrue(harness.load_json(self.run / "injection.json")["NOT_LLM_ERROR"])
        (self.run / "questioner_feedback_02.md").write_text("Instructor fixture uses x[i] instead of x[i+1]")
        shutil.copyfile(BASE / "fixtures/candidate_good.cpp", self.run / "candidate.cpp")
        (self.run / "solver_03.md").write_text("Solver test fixture repair, not actual model output")
        self.assertEqual(harness.verify(self.run), 0)
        self.assertEqual(harness.transcript(self.run), 0)
        trace = (self.run / "transcript.md").read_text()
        self.assertIn("INSTRUCTOR-INJECTED buggy C++ fixture, attempt 2", trace)
        self.assertIn("Targeted repair instruction before attempt 3", trace)
        events = [json.loads(l) for l in (self.run / "events.jsonl").read_text().splitlines()]
        self.assertTrue(any(e["role"] == "Questioner" for e in events))
        self.assertTrue(any(e["role"] == "Solver" for e in events))
        self.assertTrue(any(e["role"] == "Tool" for e in events))
        self.assertTrue(any(e["role"] == "Instructor" for e in events))

    def test_reference_and_invalid_questioner_cases(self):
        self.assertTrue(harness.load_json(self.run / "reference_validation.json")["pass"])
        harness.save_json(self.run / "questioner_cases.json", {"cases": [{"name":"bad", "x":[1, 2]}]})
        self.assertEqual(harness.check_tests(self.run), 1)

    def test_compilation_failure_captured_not_falsely_passed(self):
        (self.run / "candidate.cpp").write_text("#include <vector>\nvoid wrong_symbol() {}\n")
        self.assertEqual(harness.verify(self.run), 1)
        r = harness.load_json(self.run / "test_attempt_01.json")
        self.assertNotEqual(r["compile"]["exit_code"], 0)
        self.assertFalse(r["overall_pass"])
        self.assertIn("undefined reference", r["compile"]["stderr"])

    def test_init_resets_prior_role_files(self):
        (self.run / "candidate.cpp").write_text("stale")
        (self.run / "questioner_cases.json").write_text("stale")
        (self.run / "questioner_feedback_01.md").write_text("stale")
        self.assertEqual(harness.init(self.run), 0)
        for name in ("candidate.cpp", "questioner_cases.json", "questioner_feedback_01.md"):
            self.assertFalse((self.run / name).exists())


if __name__ == "__main__":
    unittest.main()
