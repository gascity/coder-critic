"""Offline configuration regressions; live execution is tested separately."""
import pathlib
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_two_coding_workers_not_five_specialists(self):
        agents = list((ROOT / "agents").glob("*/agent.toml"))
        self.assertEqual(sorted(p.parent.name for p in agents), ["coder", "coder-b"])
        for agent in agents:
            self.assertEqual(tomllib.loads(agent.read_text())["max_active_sessions"], 1)

    def test_parallel_implementations_then_join(self):
        formula = tomllib.loads((ROOT / "formulas/parallel-summary.toml").read_text())
        steps = {s["id"]: s for s in formula["steps"]}
        self.assertEqual(set(steps), {"parse", "aggregate", "integrate"})
        for name in ("parse", "aggregate"):
            self.assertFalse(steps[name].get("needs"))
        self.assertEqual(steps["parse"]["metadata"]["gc.run_target"], "coder")
        self.assertEqual(steps["aggregate"]["metadata"]["gc.run_target"], "coder-b")
        self.assertEqual(set(steps["integrate"]["needs"]), {"parse", "aggregate"})
        self.assertEqual(steps["integrate"]["check"]["max_attempts"], 2)

    def test_pack_matches_tested_release(self):
        pack = tomllib.loads((ROOT / "pack.toml").read_text())
        for imp in pack["imports"].values():
            self.assertEqual(imp["version"], "sha:f895c0ff47d6ee9334ed282a416387eb5b084d24")

    def test_reserved_work_gets_an_explicit_start_timestamp(self):
        city = tomllib.loads((ROOT / "city.toml").read_text())
        self.assertIn("Bash(bd update *)", city["providers"]["claude"]["args_append"])
        for name in ("coder", "coder-b"):
            prompt = (ROOT / "agents" / name / "prompt.template.md").read_text()
            self.assertIn("bd update ID --status in_progress", prompt)

    def test_no_third_llm_maintenance_worker(self):
        city = tomllib.loads((ROOT / "city.toml").read_text())
        patches = {p["name"]: p for p in city["patches"]["agent"]}
        self.assertTrue(patches["bd.dog"]["suspended"])

    def test_observed_read_only_probes_are_preauthorized(self):
        city = tomllib.loads((ROOT / "city.toml").read_text())
        allowed = city["providers"]["claude"]["args_append"]
        for command in ("Bash(ls *)", "Bash(echo *)", "Bash(python3 *)"):
            self.assertIn(command, allowed)
        self.assertNotIn("--dangerously-skip-permissions", allowed)
        self.assertEqual(city["providers"]["claude"]["option_defaults"]["permission_mode"], "auto")


if __name__ == "__main__":
    unittest.main(verbosity=2)
