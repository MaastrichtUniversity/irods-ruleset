import importlib.util
from pathlib import Path
from subprocess import CalledProcessError
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


RULE = Path(__file__).resolve().parents[2] / "datahubirodsruleset/housekeeping/rebalance_resources.py"


class HousekeepingRebalanceTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(return_value=[("replication-a",), ("replication-b",)])
        with patch.dict(sys.modules, {"genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object())}):
            spec = importlib.util.spec_from_file_location("housekeeping_rebalance", RULE)
            self.rule = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.rule)
        self.rule.run = Mock(return_value=SimpleNamespace(stdout="rebalanced\n"))
        self.ctx = SimpleNamespace(callback=Mock())

    def test_fetches_replication_resources_before_running_commands_sequentially(self):
        events = []

        def inventory():
            events.append("fetch-a")
            yield ("replication-a",)
            events.append("fetch-b")
            yield ("replication-b",)
            events.append("inventory-complete")

        self.query.return_value = inventory()

        def rebalance(command, **kwargs):
            events.append(command[2])
            self.assertEqual(command, ["iadmin", "modresc", command[2], "rebalance"])
            self.assertEqual(kwargs, {"check": True, "stdout": self.rule.PIPE,
                                     "stderr": self.rule.STDOUT, "text": True, "shell": False})
            return SimpleNamespace(stdout="rebalanced\n")

        self.rule.run.side_effect = rebalance
        report = self.rule._rebalance_resources(self.ctx)
        self.query.assert_called_once_with(
            "order(RESC_NAME)", "RESC_TYPE_NAME = 'replication'", self.rule.AS_LIST, self.ctx.callback,
        )
        self.assertEqual(events, ["fetch-a", "fetch-b", "inventory-complete", "replication-a", "replication-b"])
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"], {"resources_found": 2, "resources_rebalanced": 2, "resources_failed": 0})
        self.assertEqual([entry["output"] for entry in report["resources"]], ["rebalanced", "rebalanced"])

    def test_failed_resource_is_reported_and_later_resources_still_run(self):
        self.rule.run.side_effect = [
            CalledProcessError(4, ["iadmin", "modresc", "replication-a", "rebalance"], output="resource unavailable\n"),
            SimpleNamespace(stdout="done"),
        ]
        report = self.rule._rebalance_resources(self.ctx)
        self.assertEqual(self.rule.run.call_count, 2)
        self.assertEqual(report["execution_status"], "failed")
        self.assertEqual(report["summary"], {"resources_found": 2, "resources_rebalanced": 1, "resources_failed": 1})
        self.assertEqual(report["resources"][0]["return_code"], 4)
        self.assertEqual(report["resources"][0]["output"], "resource unavailable")
        self.assertEqual(report["resources"][1]["execution_status"], "completed")

    def test_command_start_failure_is_reported_and_processing_continues(self):
        self.rule.run.side_effect = [OSError("cannot start iadmin"), SimpleNamespace(stdout="")]
        report = self.rule._rebalance_resources(self.ctx)
        self.assertEqual(report["resources"][0]["error"], "cannot start iadmin")
        self.assertEqual(report["summary"]["resources_rebalanced"], 1)

    def test_empty_inventory_succeeds_without_running_commands(self):
        self.query.return_value = []
        report = self.rule._rebalance_resources(self.ctx)
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"], {"resources_found": 0, "resources_rebalanced": 0, "resources_failed": 0})
        self.assertEqual(report["resources"], [])
        self.rule.run.assert_not_called()

    def test_inventory_error_never_starts_rebalance(self):
        def failed_inventory():
            yield ("replication-a",)
            raise RuntimeError("catalogue unavailable")

        self.query.return_value = failed_inventory()
        with self.assertRaisesRegex(RuntimeError, "catalogue unavailable"):
            self.rule._rebalance_resources(self.ctx)
        self.rule.run.assert_not_called()

    def test_resource_names_are_passed_as_literal_command_arguments(self):
        name = "resource-with'quotes;$(literal)"
        self.query.return_value = [(name,)]
        self.rule._rebalance_resources(self.ctx)
        self.assertEqual(self.rule.run.call_args.args[0], ["iadmin", "modresc", name, "rebalance"])
        self.assertIs(self.rule.run.call_args.kwargs["shell"], False)


if __name__ == "__main__":
    unittest.main()
