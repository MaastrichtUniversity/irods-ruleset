import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


RULE = Path(__file__).resolve().parents[2] / "datahubirodsruleset/housekeeping/check_physical_files.py"
ROOT_FILE = "/nlmumc/projects/root file"
NESTED_FILE = "/nlmumc/projects/P000000001/C000000001/.metadata_versions/nested file"


def missing(path=ROOT_FILE, physical_path="/vault/some file", host="resource.example.org"):
    return (f"Physical file {physical_path} on server {host} is missing, "
            f"corresponding to iRODS object {path}\n")


class HousekeepingPhysicalFileTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("housekeeping_physical_files", RULE)
        self.rule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.rule)
        self.command = SimpleNamespace(stdout="", stderr="", returncode=0)
        self.rule.run = Mock(return_value=self.command)

    def audit(self):
        return self.rule._audit_physical_files(None)

    def test_clean_scan_runs_the_whole_tree_once_without_a_shell(self):
        report = self.audit()
        self.rule.run.assert_called_once_with(
            ["iscan", "-d", "-r", "/nlmumc/projects/"],
            capture_output=True, text=True, shell=False, check=False,
        )
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"], {"missing_physical_copies": 0, "files_with_findings": 0, "errors": 0})
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["stdout"], "")
        self.assertEqual(report["stderr"], "")
        self.assertEqual(report["return_code"], 0)

    def test_missing_copies_preserve_root_nested_hidden_and_space_containing_paths(self):
        self.command.stdout = (missing() + missing(physical_path="/other vault/copy", host="other.example.org")
                               + missing(NESTED_FILE, "/vault/nested file"))
        self.command.returncode = 94  # POSIX status for UNIX_FILE_STAT_ERR - ENOENT.
        report = self.audit()
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"], {"missing_physical_copies": 3, "files_with_findings": 2, "errors": 0})
        self.assertEqual(report["findings"], [
            {"path": ROOT_FILE, "physical_path": "/vault/some file", "host": "resource.example.org"},
            {"path": ROOT_FILE, "physical_path": "/other vault/copy", "host": "other.example.org"},
            {"path": NESTED_FILE, "physical_path": "/vault/nested file", "host": "resource.example.org"},
        ])
        self.assertEqual(report["stdout"], self.command.stdout)
        self.assertEqual(report["return_code"], 94)

    def test_findings_with_zero_exit_status_still_report_missing_copies(self):
        self.command.stdout = missing()
        report = self.audit()
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"]["missing_physical_copies"], 1)

    def test_outside_scope_findings_are_only_retained_in_raw_output(self):
        self.command.stdout = (missing("/nlmumc/projects-backup/file") + missing("/nlmumc/home/rods/file")
                               + missing("/nlmumc/projects"))
        self.command.returncode = 94
        report = self.audit()
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["stdout"], self.command.stdout)

    def test_blank_lines_are_ignored_without_changing_raw_output(self):
        self.command.stdout = "\n \n" + missing() + "\n"
        self.assertEqual(self.audit()["execution_status"], "completed")
        self.assertEqual(self.audit()["stdout"], self.command.stdout)

    def test_missing_file_exit_code_without_a_message_is_a_failure(self):
        self.command.returncode = 94
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertIn("return code 94", report["error"])

    def test_other_exit_codes_fail_even_when_findings_are_present(self):
        self.command.stdout = missing()
        for status in (2, 7, 83, -9):
            with self.subTest(status=status):
                self.command.returncode = status
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["summary"]["missing_physical_copies"], 1)
                self.assertIn(f"return code {status}", report["error"])
                self.assertEqual(report["return_code"], status)

    def test_authentication_and_connection_diagnostics_are_preserved(self):
        for status, message in ((7, "authentication failed\n"), (2, "connection refused\n")):
            with self.subTest(status=status):
                self.command.returncode = status
                self.command.stderr = message
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["stderr"], message)
                self.assertIn(message.strip(), report["error"])

    def test_unexpected_stdout_fails_without_losing_findings(self):
        self.command.stdout = missing() + "Could not find the requested data object or collection in iRODS.\n"
        for status in (0, 94):
            with self.subTest(status=status):
                self.command.returncode = status
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["summary"]["missing_physical_copies"], 1)
                self.assertEqual(report["stdout"], self.command.stdout)
                self.assertIn("Unexpected iscan output", report["error"])

    def test_stderr_fails_even_with_an_accepted_exit_code_and_findings(self):
        self.command.stdout = missing()
        self.command.stderr = "resource unavailable\n"
        for status in (0, 94):
            with self.subTest(status=status):
                self.command.returncode = status
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["summary"]["missing_physical_copies"], 1)
                self.assertIn("resource unavailable", report["error"])

    def test_unavailable_command_has_a_failed_report_with_no_return_code(self):
        self.rule.run.side_effect = FileNotFoundError("iscan unavailable")
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertIsNone(report["return_code"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["stdout"], "")
        self.assertEqual(report["stderr"], "")
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertIn("iscan unavailable", report["error"])


if __name__ == "__main__":
    unittest.main()
