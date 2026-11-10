import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
NOW = 2_000_000_000
DAY = 86400


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HousekeepingReportTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(side_effect=self.rows)
        modules = {
            "datahubirodsruleset": ModuleType("datahubirodsruleset"),
            "datahubirodsruleset.decorator": load("housekeeping_decorator", "decorator.py"),
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "datahubirodsruleset.utils": SimpleNamespace(read_data_object_from_irods=Mock()),
        }
        with patch.dict(sys.modules, modules):
            modules["datahubirodsruleset.listing_queries"] = load("housekeeping_queries", "listing_queries.py")
            with patch.dict(sys.modules, modules):
                self.storage = load("housekeeping_storage", "housekeeping/storage.py")
                with patch.dict(sys.modules, {"datahubirodsruleset.housekeeping.storage": self.storage}):
                    self.rule = load("housekeeping_reports", "housekeeping/reports.py")
        self.base = self.rule.REPORT_COLLECTION
        self.runs = self.rule.RUNS_COLLECTION
        self.metadata = {}
        self.collections = set()
        self.candidates = []
        self.resources = {"passRescUM01", "otherResc"}
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.msiCollCreate.side_effect = lambda path, *_: self.collections.add(path)
        self.callback.setCollectionAVU.side_effect = self.set_avu
        self.callback.msiRmColl.side_effect = lambda path, *_: self.collections.remove(path)
        self.clock = patch.object(self.rule.time, "time", return_value=NOW)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def set_avu(self, path, attribute, value):
        entries = self.metadata.setdefault(path, [])
        entries[:] = [(key, val) for key, val in entries if key != attribute] + [(attribute, value)]

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if columns == "USER_NAME, USER_ZONE":
            return [("rods", "nlmumc"), ("public", "nlmumc"), ("alice", "nlmumc"), ("rods", "otherZone")]
        value = condition.split("'", 2)[1]
        if columns == "RESC_NAME":
            return [(value,)] if value in self.resources else []
        if columns == "COLL_ACCESS_USER_ID":
            return [("1",), ("2",), ("3",), ("4",)]
        if columns == "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS":
            return [(key, val, "") for key, val in self.metadata.get(value, [])]
        if columns == "COLL_NAME" and condition.startswith("COLL_PARENT_NAME ="):
            self.assertEqual(value, self.runs)
            return [(path,) for path in self.candidates]
        if columns == "COLL_NAME":
            return [(value,)] if value in self.collections else []
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def initialize(self, resource="", days=""):
        args = [resource, days, ""]
        self.storage.initialize_housekeeping(args, self.callback, None)
        return json.loads(args[2])

    def cleanup(self, dry_run="false"):
        args = [dry_run, ""]
        self.rule.cleanup_housekeeping_reports(args, self.callback, None)
        return json.loads(args[1])

    def run_collection(self, name, state="completed", age=32):
        path = self.runs + "/" + name
        self.collections.add(path)
        self.candidates.append(path)
        self.metadata[path] = [("state", state), ("finishedAt", str(NOW - age * DAY))]
        return path

    def test_initialization_creates_private_collections_with_defaults(self):
        self.assertEqual(self.initialize(), {
            "report_collection": self.base, "runs_collection": self.runs,
            "report_resource": "passRescUM01", "report_retention_days": 31,
        })
        self.assertEqual(self.collections, {self.base, self.runs})
        for path in self.collections:
            self.callback.msiSetACL.assert_any_call("default", "noinherit", "", path)
            self.callback.msiSetACL.assert_any_call("default", "own", "rods", path)
            self.callback.msiSetACL.assert_any_call("default", "null", "public#nlmumc", path)
            self.callback.msiSetACL.assert_any_call("default", "null", "alice#nlmumc", path)
            self.callback.msiSetACL.assert_any_call("default", "null", "rods#otherZone", path)

    def test_reinitialization_preserves_configuration_and_existing_reports(self):
        self.initialize("otherResc", "45")
        report = self.run_collection("existing")
        self.callback.msiCollCreate.reset_mock()
        self.assertEqual(self.initialize()["report_retention_days"], 45)
        self.assertEqual(dict(self.metadata[self.base])["reportResource"], "otherResc")
        self.callback.msiCollCreate.assert_not_called()
        self.assertIn(report, self.collections)

    def test_invalid_configuration_never_creates_or_deletes(self):
        for days in ("0", "-1", "1.5", "true", " 31", "31\n"):
            with self.subTest(days=days), self.assertRaisesRegex(RuntimeError, "positive integer"):
                self.initialize(days=days)
        with self.assertRaisesRegex(RuntimeError, "does not exist"):
            self.initialize(resource="missing")
        self.callback.msiCollCreate.assert_not_called()
        self.callback.setCollectionAVU.assert_not_called()
        self.callback.msiRmColl.assert_not_called()

    def test_only_rods_can_initialize_or_cleanup(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        for operation in (self.initialize, self.cleanup):
            with self.subTest(operation=operation), self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
                operation()
        self.query.assert_not_called()
        self.callback.msiRmColl.assert_not_called()

    def test_cleanup_requires_configuration_and_explicit_boolean(self):
        with self.assertRaisesRegex(RuntimeError, "Initialize housekeeping"):
            self.cleanup()
        self.initialize()
        for flag in ("", "False", "yes"):
            with self.subTest(flag=flag), self.assertRaisesRegex(RuntimeError, "dry_run"):
                self.cleanup(flag)
        self.metadata[self.base].append(("reportRetentionDays", "1"))
        with self.assertRaisesRegex(RuntimeError, "Initialize housekeeping"):
            self.cleanup()
        self.callback.msiRmColl.assert_not_called()

    def test_cleanup_uses_completion_age_and_retains_active_and_boundary_runs(self):
        self.initialize()
        expired = [self.run_collection(state, state=state) for state in ("completed", "partial", "failed")]
        keep = [self.run_collection("active", state="running"), self.run_collection("queued", state="queued"),
                self.run_collection("boundary", age=31),
                self.run_collection("recent", age=1)]
        result = self.cleanup()
        self.assertEqual(result["deleted"], expired)
        self.assertEqual(result["eligible"], expired)
        self.assertEqual(result["errors"], [])
        self.assertEqual({entry["path"] for entry in result["skipped"]}, set(keep))
        self.assertTrue(all(path in self.collections for path in keep))
        reasons = {entry["path"]: entry["reason"] for entry in result["skipped"]}
        for path in keep[-2:]:
            self.assertEqual(reasons[path], "Within retention period")
        for call in self.callback.msiRmColl.call_args_list:
            self.assertEqual(call.args[1:], ("forceFlag=", 0))

    def test_custom_retention_and_dry_run(self):
        self.initialize(days="45")
        old = self.run_collection("old", age=46)
        recent = self.run_collection("recent", age=32)
        result = self.cleanup("true")
        self.assertEqual(result["eligible"], [old])
        self.assertEqual(result["deleted"], [])
        self.assertEqual(result["retention_days"], 45)
        self.assertTrue({old, recent}.issubset(self.collections))
        self.callback.msiRmColl.assert_not_called()

    def test_malformed_ambiguous_or_inconsistent_run_metadata_is_retained(self):
        self.initialize()
        changes = [
            ("finishedAt", "not-a-time"), ("finishedAt", "0"), ("finishedAt", str(NOW + DAY)),
        ]
        for index, (attribute, value) in enumerate(changes):
            path = self.run_collection(f"bad-{index}")
            self.set_avu(path, attribute, value)
        for attribute in ("finishedAt", "state"):
            path = self.run_collection("ambiguous-" + attribute)
            self.metadata[path].append((attribute, "completed" if attribute == "state" else "1"))
        path = self.run_collection("missing-state")
        self.metadata[path] = []
        missing = self.run_collection("missing-finishedAt")
        self.metadata[missing] = [("state", "completed")]
        result = self.cleanup()
        self.assertEqual(len(result["skipped"]), len(self.candidates))
        reasons = {entry["path"]: entry["reason"] for entry in result["skipped"]}
        self.assertEqual(reasons[missing], "Missing, invalid or ambiguous finishedAt timestamp")
        self.assertEqual(reasons[self.runs + "/bad-2"], "finishedAt timestamp is in the future")
        self.callback.msiRmColl.assert_not_called()

    def test_unexpected_paths_are_never_deleted(self):
        self.initialize()
        self.candidates = [self.base, self.runs, self.runs + "-other/run", self.runs + "/nested/run",
                           self.runs + "/..", self.runs + "/bad'quote", self.runs + "/run\n"]
        result = self.cleanup()
        self.assertEqual(len(result["skipped"]), len(self.candidates))
        self.callback.msiRmColl.assert_not_called()

    def test_partial_deletion_failure_is_reported_and_other_runs_are_processed(self):
        self.initialize()
        failed = self.run_collection("failed-delete")
        deleted = self.run_collection("deleted")
        self.callback.msiRmColl.side_effect = [RuntimeError("storage unavailable"), None]
        result = self.cleanup()
        self.assertEqual(result["deleted"], [deleted])
        self.assertEqual(result["errors"], [{"path": failed, "error": "storage unavailable"}])


if __name__ == "__main__":
    unittest.main()
