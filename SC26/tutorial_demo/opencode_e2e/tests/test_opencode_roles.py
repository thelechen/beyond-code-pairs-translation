import unittest
from pathlib import Path


SC26 = Path(__file__).resolve().parents[3]
AGENTS = SC26 / ".opencode" / "agents"
COMMANDS = SC26 / ".opencode" / "commands"


class OpenCodeRoleIsolationTests(unittest.TestCase):
    def read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_commands_use_strict_orchestrator_and_fail_closed(self):
        for name in ("bcp-demo.md", "bcp-repair.md"):
            text = self.read(COMMANDS / name)
            self.assertIn("agent: bcp-orchestrator", text)
            self.assertNotIn("agent: build", text)
            self.assertIn("stop", text.lower())
            self.assertIn("never", text.lower())

    def test_orchestrator_cannot_edit_and_only_launches_named_roles(self):
        text = self.read(AGENTS / "bcp-orchestrator.md")
        self.assertIn("mode: primary", text)
        self.assertIn("permission:\n  edit: deny", text)
        self.assertIn("call_omo_agent: deny", text)
        self.assertIn('bash:\n    "*": deny', text)
        self.assertIn('"python3 tutorial_demo/opencode_e2e/harness.py *": allow', text)
        self.assertIn('task:\n    "*": deny', text)
        self.assertIn('"bcp-questioner": allow', text)
        self.assertIn('"bcp-solver": allow', text)

    def test_role_agents_have_narrow_write_permissions(self):
        questioner = self.read(AGENTS / "bcp-questioner.md")
        solver = self.read(AGENTS / "bcp-solver.md")
        for text in (questioner, solver):
            self.assertIn("permission:\n  bash: deny", text)
            self.assertIn('edit:\n    "*": deny', text)
        self.assertIn("runs/opencode_latest/questioner_*", questioner)
        self.assertNotIn('candidate.cpp": allow', questioner)
        self.assertIn("runs/opencode_latest/candidate.cpp", solver)
        self.assertIn("runs/opencode_latest/solver_stage_*.md", solver)


if __name__ == "__main__":
    unittest.main()
