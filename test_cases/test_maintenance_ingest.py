"""Mocked maintenance ingest tests. Run from the repository root with:

    python3 -m unittest test_cases.test_maintenance_ingest -v

No iRODS server, large files, or external Python packages are needed.
"""

import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[1] / "datahubirodsruleset"
GIB = 1024 ** 3
HOUR = 3600
START = 2_000_000_000
END = START + 24 * HOUR
DROPZONE = "/nlmumc/ingest/direct/example-token"


def fake_package(name, path):
    module = ModuleType(name)
    module.__path__ = [str(path)]
    return module


class MaintenanceSchedulingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_modules = {
            "datahubirodsruleset": fake_package("datahubirodsruleset", ROOT),
            "datahubirodsruleset.ingest": fake_package("datahubirodsruleset.ingest", ROOT / "ingest"),
            "datahubirodsruleset.formatters": ModuleType("datahubirodsruleset.formatters"),
            "datahubirodsruleset.utils": ModuleType("datahubirodsruleset.utils"),
            "dhpythonirodsutils": ModuleType("dhpythonirodsutils"),
            "dhpythonirodsutils.enums": ModuleType("dhpythonirodsutils.enums"),
            "dhpythonirodsutils.formatters": ModuleType("dhpythonirodsutils.formatters"),
        }
        fake_modules["datahubirodsruleset.formatters"].format_dropzone_path = (
            lambda ctx, token, kind: f"/nlmumc/ingest/{'direct' if kind == 'direct' else 'zones'}/{token}"
        )
        fake_modules["datahubirodsruleset.utils"].TRUE_AS_STRING = "true"
        fake_modules["datahubirodsruleset.utils"].FALSE_AS_STRING = "false"
        fake_modules["dhpythonirodsutils.formatters"].format_string_to_boolean = lambda value: value == "true"
        fake_modules["dhpythonirodsutils"].formatters = fake_modules["dhpythonirodsutils.formatters"]
        fake_modules["dhpythonirodsutils.enums"].DropzoneState = SimpleNamespace(
            IN_QUEUE_FOR_VALIDATION=SimpleNamespace(value="in-queue-for-validation"),
            IN_QUEUE_FOR_INGESTION=SimpleNamespace(value="in-queue-for-ingestion"),
            WARNING_VALIDATION_INCORRECT=SimpleNamespace(value="warning-validation-incorrect"),
            WARNING_UNSUPPORTED_CHARACTER=SimpleNamespace(value="warning-unsupported-character"),
        )
        cls.modules_patch = patch.dict(sys.modules, fake_modules)
        cls.modules_patch.start()
        cls.maintenance = importlib.import_module("datahubirodsruleset.ingest.maintenance")
        cls.process = importlib.import_module("datahubirodsruleset.ingest.process_dropzone")
        cls.start_rule = importlib.import_module("datahubirodsruleset.ingest.start_ingest")
        cls.scheduler = importlib.import_module("datahubirodsruleset.ingest.schedule_maintenance_ingest")
        cls.setter = importlib.import_module("datahubirodsruleset.ingest.set_ingest_maintenance_window")

    @classmethod
    def tearDownClass(cls):
        cls.modules_patch.stop()

    def setUp(self):
        self.callback = Mock()
        self.catalog = {
            (DROPZONE, "state"): "open",
            (self.maintenance.MAINTENANCE_COLLECTION, "maintenanceStart"): str(START),
            (self.maintenance.MAINTENANCE_COLLECTION, "maintenanceEnd"): str(END),
        }
        self.size = 500 * GIB
        self.callback.getCollectionAVU.side_effect = lambda path, name, _, fallback, fatal: {
            "arguments": [path, name, self.catalog.get((path, name), fallback)]
        }
        self.callback.is_dropzone_state_ingestable.return_value = {"arguments": ["", "true"]}
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(ValueError(message))
        self.scheduler.validate = Mock(side_effect=self.validate)
        self.scheduler.stop_ingestion = Mock(
            side_effect=lambda *args: (_ for _ in ()).throw(ValueError("validation failed"))
        )
        self.scheduler.ingest = Mock()

    def validate(self, ctx, token, depositor, kind):
        path = f"/nlmumc/ingest/{'direct' if kind == 'direct' else 'zones'}/{token}"
        self.catalog[(path, "totalSize")] = str(self.size)
        return {"validation_errors": [], "project_id": "P000000001"}, path

    def submit(self, now, kind="direct"):
        with patch.object(self.start_rule.time, "time", return_value=now):
            self.start_rule.start_ingest(["alice", "example-token", kind], self.callback, None)

    def preflight(self, now, kind="direct"):
        with patch.object(self.scheduler.time, "time", return_value=now):
            self.scheduler.schedule_maintenance_ingest(
                ["example-token", "alice", kind, str(START), str(END)], self.callback, None
            )

    def assert_initial_preflight(self, kind="direct"):
        self.assertEqual(self.callback.delayExec.call_count, 1)
        args = self.callback.delayExec.call_args.args
        self.assertIn("<PLUSET>1s</PLUSET>", args[0])
        self.assertEqual(
            args[1], f"schedule_maintenance_ingest('example-token', 'alice', '{kind}', '{START}', '{END}')"
        )
        self.scheduler.validate.assert_not_called()
        self.callback.validate_dropzone.assert_not_called()

    def assert_waiting_until_end(self, now, kind="direct"):
        self.assertEqual(self.callback.delayExec.call_count, 2)
        args = self.callback.delayExec.call_args.args
        self.assertIn(f"<PLUSET>{END - now}s</PLUSET>", args[0])
        self.assertEqual(args[1], f"process_dropzone('example-token', 'alice', '{kind}')")
        self.scheduler.ingest.assert_not_called()

    def test_start_ingest_does_not_validate_synchronously(self):
        self.submit(START - HOUR)
        self.assert_initial_preflight()
        self.callback.setCollectionAVU.assert_called_once_with(
            DROPZONE, "state", "in-queue-for-validation"
        )

    def test_each_size_boundary_is_inclusive(self):
        for size_gib, lead_hours in ((500, 120), (400, 96), (300, 72), (200, 48), (100, 24), (0, 8)):
            with self.subTest(size=size_gib):
                self.setUp()
                self.size = size_gib * GIB
                now = START - lead_hours * HOUR
                self.submit(now)
                self.assert_initial_preflight()
                self.preflight(now)
                self.assert_waiting_until_end(now)

    def test_just_below_threshold_starts_after_async_validation(self):
        for size_gib, lead_hours in ((500, 120), (400, 96), (300, 72), (200, 48), (100, 24)):
            with self.subTest(size=size_gib):
                self.setUp()
                self.size = size_gib * GIB - 1
                now = START - lead_hours * HOUR
                self.submit(now)
                self.preflight(now)
                self.assertEqual(self.callback.delayExec.call_count, 1)
                self.scheduler.ingest.assert_called_once()

    def test_one_second_before_lead_time_starts_after_async_validation(self):
        for size_gib, lead_hours in ((400, 96), (300, 72), (200, 48), (100, 24), (0, 8)):
            with self.subTest(size=size_gib):
                self.setUp()
                self.size = size_gib * GIB
                now = START - lead_hours * HOUR - 1
                self.submit(now)
                self.preflight(now)
                self.assertEqual(self.callback.delayExec.call_count, 1)
                self.scheduler.ingest.assert_called_once()

    def test_all_sizes_wait_in_final_eight_hours_and_during_window(self):
        for now in (START - 8 * HOUR, START, END - 1):
            with self.subTest(now=now):
                self.setUp()
                self.size = 0
                self.submit(now)
                self.preflight(now)
                self.assert_waiting_until_end(now)

    def test_validation_finishing_after_window_starts_ingest(self):
        self.submit(END - HOUR)
        self.preflight(END)
        self.assertEqual(self.callback.delayExec.call_count, 1)
        self.scheduler.ingest.assert_called_once()

    def test_outside_window_keeps_existing_queue_behavior(self):
        for now in (START - 120 * HOUR - 1, END):
            with self.subTest(now=now):
                self.setUp()
                self.submit(now)
                self.assertEqual(self.callback.delayExec.call_count, 1)
                args = self.callback.delayExec.call_args.args
                self.assertIn("<PLUSET>1s</PLUSET>", args[0])
                self.assertEqual(args[1], "process_dropzone('example-token', 'alice', 'direct')")
                self.scheduler.validate.assert_not_called()

    def test_window_update_does_not_reschedule_existing_job(self):
        now = START - 8 * HOUR
        self.size = 0
        self.submit(now)
        self.catalog[(self.maintenance.MAINTENANCE_COLLECTION, "maintenanceEnd")] = str(END + HOUR)
        self.preflight(now)
        self.assert_waiting_until_end(now)

    def test_absent_window_keeps_existing_queue_behavior(self):
        del self.catalog[(self.maintenance.MAINTENANCE_COLLECTION, "maintenanceStart")]
        del self.catalog[(self.maintenance.MAINTENANCE_COLLECTION, "maintenanceEnd")]
        self.submit(START - HOUR)
        self.assertEqual(
            self.callback.delayExec.call_args.args[1],
            "process_dropzone('example-token', 'alice', 'direct')",
        )
        self.scheduler.validate.assert_not_called()

    def test_invalid_window_fails_before_state_change(self):
        for start, end in ((None, str(END)), ("bad", str(END)), (str(END), str(START))):
            with self.subTest(start=start, end=end):
                self.setUp()
                key = (self.maintenance.MAINTENANCE_COLLECTION, "maintenanceStart")
                if start is None:
                    del self.catalog[key]
                else:
                    self.catalog[key] = start
                self.catalog[(self.maintenance.MAINTENANCE_COLLECTION, "maintenanceEnd")] = end
                with self.assertRaisesRegex(ValueError, "Invalid ingest maintenance window"):
                    self.submit(START - HOUR)
                self.callback.setCollectionAVU.assert_not_called()
                self.callback.delayExec.assert_not_called()

    def test_validation_error_stops_only_in_delayed_rule(self):
        self.scheduler.validate.side_effect = None
        self.scheduler.validate.return_value = (
            {"validation_errors": ["invalid metadata"], "project_id": "P000000001"}, DROPZONE
        )
        self.submit(START - HOUR)
        self.assert_initial_preflight()
        with self.assertRaisesRegex(ValueError, "validation failed"):
            self.preflight(START - HOUR)
        self.assertEqual(self.callback.delayExec.call_count, 1)
        self.scheduler.ingest.assert_not_called()

    def test_delayed_process_revalidates_and_rejects_changed_dropzone(self):
        now = START - HOUR
        self.submit(now)
        self.preflight(now)
        self.assert_waiting_until_end(now)
        self.callback.validate_dropzone.return_value = {"arguments": [
            DROPZONE, "alice", "direct",
            json.dumps({"project_id": "P000000001", "validation_errors": ["project changed"]}),
        ]}
        with self.assertRaisesRegex(ValueError, "Dropzone validation failed"):
            self.process.process_dropzone(["example-token", "alice", "direct"], self.callback, None)
        self.callback.validate_dropzone.assert_called_once_with(DROPZONE, "alice", "direct", "")
        self.callback.setCollectionAVU.assert_any_call(
            DROPZONE, "state", "warning-validation-incorrect"
        )
        self.callback.perform_ingest.assert_not_called()

    def test_mounted_dropzone_uses_its_validated_size(self):
        self.size = 400 * GIB
        now = START - 96 * HOUR
        self.submit(now, "mounted")
        self.assert_initial_preflight("mounted")
        self.preflight(now, "mounted")
        self.assert_waiting_until_end(now, "mounted")
        self.scheduler.validate.assert_called_once()

    def test_setter_requires_rods_and_valid_timestamps(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with self.assertRaisesRegex(ValueError, "Only rods"):
            self.setter.set_ingest_maintenance_window([str(START), str(END)], self.callback, None)
        self.callback.setCollectionAVU.assert_not_called()
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        for start, end in (("bad", str(END)), (str(END), str(START)), (str(START), "")):
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    self.setter.set_ingest_maintenance_window([start, end], self.callback, None)
                self.callback.setCollectionAVU.assert_not_called()

    def test_setter_writes_both_avus(self):
        self.setter.set_ingest_maintenance_window([str(START), str(END)], self.callback, None)
        self.assertEqual(self.callback.setCollectionAVU.call_args_list, [
            call("/nlmumc/ingest/zones", "maintenanceStart", str(START)),
            call("/nlmumc/ingest/zones", "maintenanceEnd", str(END)),
        ])


if __name__ == "__main__":
    unittest.main()
