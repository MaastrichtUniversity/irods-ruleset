import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"
COLLECTION = PROJECT + "/C000000001"
PROJECT_REQUIRED = {
    "OBI:0000103", "archiveDestinationResource", "authorizationPeriodEndDate",
    "collectionMetadataSchemas", "dataRetentionPeriodEndDate", "dataSteward", "enableArchive",
    "enableContributorEditMetadata", "enableDropzoneSharing", "enableUnarchive", "ingestResource",
    "latestProjectCollectionNumber", "resource", "responsibleCostCenter", "storageQuotaGb", "title",
}
COLLECTION_REQUIRED = {
    "PID", "creator", "dcat:byteSize", "depositor", "latest_version_number", "numFiles",
    "schemaName", "schemaVersion", "title",
}


class HousekeepingAVUTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(side_effect=self.rows)
        modules = {
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "datahubirodsruleset.utils": SimpleNamespace(read_data_object_from_irods=self.read_document),
            "dhpythonirodsutils": ModuleType("dhpythonirodsutils"),
            "dhpythonirodsutils.enums": SimpleNamespace(
                ReplicaStatus=SimpleNamespace(GOOD=SimpleNamespace(value="1")),
                ProcessAttribute=SimpleNamespace(ARCHIVE=SimpleNamespace(value="archiveState"),
                                                 UNARCHIVE=SimpleNamespace(value="unArchiveState")),
            ),
        }
        for name in ("datahubirodsruleset", "datahubirodsruleset.housekeeping"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.load("decorator.py")
        self.load("listing_queries.py")
        self.storage = self.load("housekeeping/storage.py")
        self.reports = self.load("housekeeping/reports.py")
        self.ingest_state = self.load("housekeeping/ingest_state.py")
        self.rule = self.load("housekeeping/check_required_avus.py")
        self.replica_rule = self.load("housekeeping/check_replica_status.py")
        self.physical_files = self.load("housekeeping/check_physical_files.py")
        self.rebalance = self.load("housekeeping/rebalance_resources.py")
        self.dropzones = self.load("housekeeping/check_dropzone_consistency.py")
        self.executor = self.load("housekeeping/execute_housekeeping.py")
        self.controller = self.load("housekeeping/run_housekeeping.py")
        self.projects = [PROJECT]
        self.collections = [COLLECTION]
        self.attributes = {
            PROJECT: set(PROJECT_REQUIRED),
            COLLECTION: COLLECTION_REQUIRED | {"dcat:byteSize_resc_10", "numFiles_resc_10"},
        }
        self.replicas = []
        self.collection_metadata = {COLLECTION: {"creator": "test"}}
        self.resource = "passRescUM01"
        self.expected_report_resource = "passRescUM01"
        self.retention_days = "31"
        self.report_collections = {self.reports.REPORT_COLLECTION, self.reports.RUNS_COLLECTION}
        self.resources = {"passRescUM01", "otherResc"}
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.msiDataObjCreate.side_effect = self.create_document
        self.callback.msiDataObjWrite.side_effect = self.write_document
        self.callback.setCollectionAVU.side_effect = self.set_avu
        self.callback.msiCollCreate.side_effect = lambda path, *_: self.report_collections.add(path)
        self.documents = {}
        self.descriptors = {}
        self.run_metadata = {}
        self.reads = []
        self.run_inventory = []

    def load(self, relative):
        name = "datahubirodsruleset." + relative[:-3].replace("/", ".")
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if columns == "RESC_NAME":
            resource = condition.split("'")[1]
            return [(resource,)] if resource in self.resources else []
        if columns == "COLL_ACCESS_USER_ID":
            return [("1",), ("2",)]
        if columns == "USER_NAME, USER_ZONE":
            return [("rods", "nlmumc"), ("public", "nlmumc")]
        if columns == "COLL_NAME" and condition.startswith(f"COLL_NAME = '{self.reports.REPORT_COLLECTION}"):
            path = condition.split("'")[1]
            return [(path,)] if path in self.report_collections else []
        if columns == "COLL_NAME, COLL_CREATE_TIME":
            self.assertEqual(condition, f"COLL_PARENT_NAME = '{self.reports.RUNS_COLLECTION}'")
            return iter(self.run_inventory)
        if columns == "COLL_NAME, DATA_NAME, DATA_REPL_NUM, DATA_REPL_STATUS, DATA_RESC_NAME":
            self.assertIn("AND DATA_REPL_STATUS != '1'", condition)
            direct = condition.startswith("COLL_NAME =")
            return [row for row in self.replicas if row[3] != "1" and (
                row[0] == "/nlmumc/projects" if direct else row[0].startswith("/nlmumc/projects/")
            )]
        if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            path_condition, attribute_condition = condition.split(" AND ")
            paths = re.findall(r"'([^']*)'", path_condition)
            attributes = re.findall(r"'([^']*)'", attribute_condition)
            return [(path, attribute, value) for path in paths
                    for attribute, value in self.collection_metadata.get(path, {}).items() if attribute in attributes]
        if columns == "META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE, META_COLL_ATTR_UNITS":
            if condition == f"COLL_NAME = '{self.reports.REPORT_COLLECTION}'":
                return [(key, value, "") for key, value in (
                    ("reportResource", self.resource), ("reportRetentionDays", self.retention_days),
                ) if value is not None]
            path = condition.split("'")[1]
            return [(key, value, "") for key, value in self.run_metadata.get(path, {}).items()]
        paths = self.projects if condition == self.rule.PROJECT_CONDITION else self.collections
        if columns == "COLL_NAME":
            return [(path,) for path in paths]
        if columns == "COLL_NAME, META_COLL_ATTR_NAME":
            return [(path, attribute) for path in paths for attribute in self.attributes.get(path, ())]
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def create_document(self, path, options, descriptor):
        self.assertEqual(options, f"destRescName={self.expected_report_resource}++++forceFlag=")
        descriptor = len(self.descriptors)
        self.descriptors[descriptor] = path
        return {"arguments": [path, options, descriptor]}

    def write_document(self, descriptor, document, _):
        self.documents[self.descriptors[descriptor]] = json.loads(document)

    def read_document(self, ctx, path):
        self.reads.append(path)
        return json.dumps(self.documents[path])

    def set_avu(self, path, attribute, value):
        if path == self.reports.REPORT_COLLECTION:
            if attribute == "reportResource":
                self.resource = value
            elif attribute == "reportRetentionDays":
                self.retention_days = value
        self.run_metadata.setdefault(path, {})[attribute] = value

    def audit(self):
        return self.rule._audit_required_avus(SimpleNamespace(callback=self.callback))

    def invoke(self, checks="required_avus", mode="sync"):
        args = [checks, mode, ""]
        self.controller.run_housekeeping(args, self.callback, None)
        return json.loads(args[-1])

    def get_status(self, run_id):
        args = [run_id, ""]
        self.reports.get_housekeeping_status(args, self.callback, None)
        return json.loads(args[1])

    def list_runs(self, limit="50", offset="0"):
        args = [limit, offset, ""]
        self.reports.list_housekeeping_runs(args, self.callback, None)
        return json.loads(args[2])

    def get_report(self, run_id, check="required_avus"):
        args = [run_id, check, ""]
        self.reports.get_housekeeping_report(args, self.callback, None)
        return json.loads(args[2])

    def test_complete_project_and_pc_have_no_findings_and_use_four_bulk_queries(self):
        report = self.audit()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["summary"], {
            "projects_checked": 1, "project_collections_checked": 1,
            "project_collections_skipped_unfinished_ingest": 0,
            "projects_with_findings": 0, "project_collections_with_findings": 0,
        })
        self.assertEqual(self.query.call_count, 4)
        self.assertEqual(set(self.rule.PROJECT_AVUS), PROJECT_REQUIRED)
        self.assertEqual(set(self.rule.PROJECT_COLLECTION_AVUS), COLLECTION_REQUIRED)

    def test_dropzone_check_is_registered_and_findings_are_persisted_without_failing_run(self):
        self.assertIs(self.executor.CHECKS["dropzone_consistency"], self.dropzones._audit_dropzone_consistency)
        report = {"check": "dropzone_consistency", "execution_status": "completed",
                  "summary": {"missing_on_disk": 1}, "findings": [{"kind": "missing_on_disk"}]}
        with patch.dict(self.executor.CHECKS, {"dropzone_consistency": Mock(return_value=report)}):
            result = self.invoke("dropzone_consistency")
        self.assertEqual(result["state"], "completed")
        self.assertEqual(self.documents[result["checks"]["dropzone_consistency"]["report_path"]], report)

    def test_physical_file_check_is_registered_and_persists_findings_in_sync_and_async_modes(self):
        self.assertIs(self.executor.CHECKS["physical_files"], self.physical_files._audit_physical_files)
        output = ("Physical file /vault/missing file on server resource.example.org is missing, "
                  f"corresponding to iRODS object {COLLECTION}/missing file\n")
        for mode in ("sync", "async"):
            with self.subTest(mode=mode), patch.object(self.physical_files, "run", return_value=SimpleNamespace(
                stdout=output, stderr="", returncode=94,
            )) as command:
                result = self.invoke("physical_files", mode)
                if mode == "async":
                    command.assert_not_called()
                    self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
                    result = self.get_status(result["run_id"])
                command.assert_called_once()
                self.assertEqual(result["state"], "completed")
                entry = result["checks"]["physical_files"]
                self.assertEqual(entry["report_path"], result["run_collection"] + "/checks/physical_files.json")
                self.assertEqual(entry["summary"]["missing_physical_copies"], 1)
                report = self.documents[entry["report_path"]]
                self.assertEqual(report["stdout"], output)
                self.assertEqual(report["findings"], [{"path": COLLECTION + "/missing file",
                                                      "physical_path": "/vault/missing file",
                                                      "host": "resource.example.org"}])

    def test_physical_file_failure_is_persisted_and_later_selected_checks_still_run(self):
        with patch.object(self.physical_files, "run", side_effect=FileNotFoundError("iscan unavailable")):
            with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
                self.invoke("physical_files+required_avus")
        summary = next(document for path, document in self.documents.items() if path.endswith("/summary.json"))
        self.assertEqual(summary["state"], "partial")
        entry = summary["checks"]["physical_files"]
        self.assertEqual(entry["execution_status"], "failed")
        self.assertIn("iscan unavailable", entry["error"])
        self.assertIsNone(self.documents[entry["report_path"]]["return_code"])
        self.assertEqual(summary["checks"]["required_avus"]["execution_status"], "completed")

    def test_physical_file_check_denies_non_rods_before_starting_iscan(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with patch.object(self.physical_files, "run") as command:
            with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
                self.invoke("physical_files")
        command.assert_not_called()

    def test_every_required_project_avu_is_checked(self):
        for attribute in PROJECT_REQUIRED:
            with self.subTest(attribute=attribute):
                self.attributes[PROJECT] = PROJECT_REQUIRED - {attribute}
                self.assertEqual(self.audit()["findings"], [{
                    "entity_type": "project", "path": PROJECT, "missing_avus": [attribute],
                }])

    def test_every_required_collection_avu_is_checked(self):
        for attribute in COLLECTION_REQUIRED:
            with self.subTest(attribute=attribute):
                self.attributes[COLLECTION] = (COLLECTION_REQUIRED - {attribute}) | {
                    "dcat:byteSize_resc_10", "numFiles_resc_10",
                }
                self.assertEqual(self.audit()["findings"], [{
                    "entity_type": "project_collection", "path": COLLECTION,
                    "missing_avus": [attribute], "missing_resource_avu_pair": False,
                }])

    def test_bare_projects_are_reported_and_bare_collections_are_skipped(self):
        self.attributes = {}
        report = self.audit()
        self.assertEqual(report["findings"], [
            {"entity_type": "project", "path": PROJECT, "missing_avus": sorted(PROJECT_REQUIRED)},
        ])
        self.assertEqual(report["summary"]["projects_checked"], 1)
        self.assertEqual(report["summary"]["project_collections_checked"], 0)
        self.assertEqual(report["summary"]["project_collections_skipped_unfinished_ingest"], 1)

    def test_all_completion_avus_must_be_missing_to_skip_a_collection(self):
        self.attributes[COLLECTION] -= set(self.ingest_state.INGEST_COMPLETION_AVUS)
        self.assertEqual(self.audit()["findings"], [])
        self.assertEqual(self.audit()["summary"]["project_collections_skipped_unfinished_ingest"], 1)
        for attribute in self.ingest_state.INGEST_COMPLETION_AVUS:
            with self.subTest(attribute=attribute):
                self.attributes[COLLECTION] = {attribute}
                report = self.audit()
                self.assertEqual(report["summary"]["project_collections_checked"], 1)
                self.assertEqual(report["findings"][0]["missing_avus"], sorted(COLLECTION_REQUIRED - {attribute}))

    def test_multiple_matching_resource_pairs_are_allowed(self):
        self.attributes[COLLECTION].update({"dcat:byteSize_resc_20", "numFiles_resc_20"})
        self.assertEqual(self.audit()["findings"], [])

    def test_resource_pair_requires_the_same_numeric_id(self):
        self.attributes[COLLECTION] = COLLECTION_REQUIRED | {"dcat:byteSize_resc_10", "numFiles_resc_20"}
        finding = self.audit()["findings"][0]
        self.assertEqual(finding["missing_avus"], ["dcat:byteSize_resc_20", "numFiles_resc_10"])
        self.assertTrue(finding["missing_resource_avu_pair"])

    def test_unpaired_additional_resource_is_reported_even_with_a_valid_pair(self):
        self.attributes[COLLECTION].add("dcat:byteSize_resc_20")
        finding = self.audit()["findings"][0]
        self.assertEqual(finding["missing_avus"], ["numFiles_resc_20"])
        self.assertFalse(finding["missing_resource_avu_pair"])

    def test_invalid_resource_suffixes_do_not_satisfy_the_pair_requirement(self):
        self.attributes[COLLECTION] = COLLECTION_REQUIRED | {
            "dcat:byteSize_resc_", "numFiles_resc_", "dcat:byteSize_resc_bad", "numFiles_resc_bad",
            "dcat:byteSize_resc_10_extra", "numFiles_resc_10_extra",
        }
        finding = self.audit()["findings"][0]
        self.assertEqual(finding["missing_avus"], [])
        self.assertTrue(finding["missing_resource_avu_pair"])

    def test_nested_collections_and_other_names_are_outside_scope(self):
        self.projects += ["/nlmumc/projects/other", PROJECT + "/nested", "/other/P000000001"]
        self.collections += [COLLECTION + "/nested", PROJECT + "/.metadata_versions",
                             PROJECT + "other/C000000001", "/other/P000000001/C000000001"]
        report = self.audit()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["summary"]["projects_checked"], 1)
        self.assertEqual(report["summary"]["project_collections_checked"], 1)

    def test_large_scope_still_uses_bulk_queries(self):
        self.projects = [f"/nlmumc/projects/P{index:09d}" for index in range(1000)]
        self.collections = [path + "/C000000001" for path in self.projects]
        self.attributes = {path: PROJECT_REQUIRED for path in self.projects}
        self.attributes.update({path: COLLECTION_REQUIRED | {"dcat:byteSize_resc_10", "numFiles_resc_10"}
                                for path in self.collections})
        self.assertEqual(self.audit()["findings"], [])
        self.assertEqual(self.query.call_count, 4)

    def test_empty_zone_is_reported_with_zero_counts(self):
        self.projects = []
        self.collections = []
        self.assertEqual(self.audit()["summary"], {
            "projects_checked": 0, "project_collections_checked": 0,
            "project_collections_skipped_unfinished_ingest": 0,
            "projects_with_findings": 0, "project_collections_with_findings": 0,
        })

    def test_replica_scan_reports_each_bad_replica_including_nested_and_root_files(self):
        self.replicas = [
            (COLLECTION, "file", "0", "1", "good-resource"),
            (COLLECTION, "file", "1", "0", "disk"),
            (COLLECTION, "file", "2", "2", "disk"),
            (COLLECTION + "/nested", "file", "0", "3", "disk"),
            (COLLECTION + "/.metadata_versions/1", "instance.json", "0", "4", "disk"),
            (COLLECTION, "unknown", "0", "9", "disk"),
            ("/nlmumc/projects", "root", "0", "0", "disk"),
            (PROJECT, "project-root", "0", "0", "disk"),
            (PROJECT + "/C000000001extra", "other", "0", "0", "disk"),
            ("/nlmumc/projects-other", "outside", "0", "0", "disk"),
            ("/nlmumc/home", "outside", "0", "0", "disk"),
        ]
        report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"], {
            "candidate_replicas": 8, "replicas_skipped_tape_operation": 0,
            "replicas_skipped_unfinished_ingest": 0, "replicas_with_findings": 8, "files_with_findings": 7,
        })
        self.assertIn({"path": COLLECTION + "/file", "project_collection": COLLECTION,
                       "replica_number": "1", "replica_status": "0", "resource": "disk"}, report["findings"])
        for finding in report["findings"]:
            if finding["path"].startswith(COLLECTION + "/"):
                self.assertEqual(finding["project_collection"], COLLECTION)
            else:
                self.assertIsNone(finding["project_collection"])
        self.assertEqual({finding["replica_status"] for finding in report["findings"]}, {"0", "2", "3", "4", "9"})

    def test_replica_scan_skips_any_tape_avu_by_presence_before_ingest_filter(self):
        self.replicas = [(COLLECTION + "/nested", "file", "0", "0", "disk")]
        for attribute in ("archiveState", "unArchiveState"):
            for value in ("in-queue-for-archival", "archive-in-progress 1/2", "error-archive-failed", "archive-done",
                          "in-queue-for-unarchival", "unarchive-in-progress 1/2", "error-unarchive-failed",
                          "unarchive-done", ""):
                with self.subTest(attribute=attribute, value=value):
                    self.collection_metadata = {COLLECTION: {attribute: value}}
                    report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
                    self.assertEqual(report["findings"], [])
                    self.assertEqual(report["summary"]["replicas_skipped_tape_operation"], 1)
                    self.assertEqual(report["summary"]["replicas_skipped_unfinished_ingest"], 0)

    def test_replica_scan_uses_the_same_ingest_predicate_and_ignores_avu_values(self):
        self.replicas = [(COLLECTION, "file", "0", "0", "disk")]
        for attributes in ({}, {"title": "test", "numFiles": "1", "dcat:byteSize": "10"}):
            self.collection_metadata = {COLLECTION: attributes}
            report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["summary"]["replicas_skipped_unfinished_ingest"], 1)
        for attribute in self.ingest_state.INGEST_COMPLETION_AVUS:
            with self.subTest(attribute=attribute):
                self.collection_metadata = {COLLECTION: {attribute: ""}}
                report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
                self.assertEqual(report["summary"]["replicas_with_findings"], 1)
                self.assertEqual(report["summary"]["replicas_skipped_unfinished_ingest"], 0)

    def test_replica_scan_exhausts_both_inventories_before_reading_metadata(self):
        self.replicas = [("/nlmumc/projects", "root", "0", "0", "disk"),
                         (COLLECTION, "file", "0", "0", "disk")]
        events = []

        def rows(columns, condition, mode, callback):
            if "DATA_REPL_NUM" in columns:
                def inventory():
                    yield from self.rows(columns, condition, mode, callback)
                    events.append("inventory-complete")
                return inventory()
            self.assertEqual(events, ["inventory-complete", "inventory-complete"])
            return self.rows(columns, condition, mode, callback)

        self.query.side_effect = rows
        self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
        self.assertEqual(self.query.call_count, 3)

    def test_replica_scan_batches_distinct_collection_metadata_paths(self):
        paths = [PROJECT + f"/C{index:09d}" for index in range(45)]
        self.replicas = [(path, name, "0", "0", "disk") for path in paths for name in ("one", "two")]
        self.collection_metadata = {path: {"creator": "test"} for path in paths}
        report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
        self.assertEqual(report["summary"]["replicas_with_findings"], 90)
        metadata_calls = [call for call in self.query.call_args_list if "META_COLL_ATTR_NAME" in call.args[0]]
        queried_paths = []
        for call in metadata_calls:
            batch = re.findall(r"'([^']*)'", call.args[1].split(" AND ")[0])
            self.assertLessEqual(len(batch), 20)
            queried_paths.extend(batch)
        self.assertLess(len(metadata_calls), len(paths))
        self.assertEqual(queried_paths, paths)

    def test_empty_replica_inventory_has_zero_counts_and_no_metadata_queries(self):
        report = self.replica_rule._audit_replica_status(SimpleNamespace(callback=self.callback))
        self.assertEqual(report["findings"], [])
        self.assertTrue(all(value == 0 for value in report["summary"].values()))
        self.assertEqual(self.query.call_count, 2)

    def test_replica_inventory_failure_does_not_read_metadata_or_report_partial_findings(self):
        def rows(columns, condition, mode, callback):
            if "DATA_REPL_NUM" in columns:
                def inventory():
                    yield (COLLECTION, "file", "0", "0", "disk")
                    raise RuntimeError("replica query failed")
                return inventory()
            self.assertNotIn("COLL_NAME, META_COLL_ATTR_NAME", columns)
            return self.rows(columns, condition, mode, callback)

        self.query.side_effect = rows
        with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
            self.invoke("replica_status")
        report = next(document for path, document in self.documents.items() if path.endswith("/checks/replica_status.json"))
        self.assertEqual(report, {"check": "replica_status", "execution_status": "failed", "error": "replica query failed"})

    def test_replica_metadata_failure_is_persisted_as_failed(self):
        self.replicas = [(COLLECTION, "file", "0", "0", "disk")]

        def rows(columns, condition, mode, callback):
            if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
                raise RuntimeError("metadata query failed")
            return self.rows(columns, condition, mode, callback)

        self.query.side_effect = rows
        with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
            self.invoke("replica_status")
        report = next(document for path, document in self.documents.items() if path.endswith("/checks/replica_status.json"))
        self.assertEqual(report["error"], "metadata query failed")

    def test_replica_check_registration_and_combined_sync_and_async_reporting(self):
        self.assertIs(self.executor.CHECKS["replica_status"], self.replica_rule._audit_replica_status)
        self.replicas = [(COLLECTION, "file", "0", "0", "disk")]
        for mode in ("sync", "async"):
            with self.subTest(mode=mode):
                result = self.invoke("required_avus+replica_status", mode)
                if mode == "async":
                    self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
                    result = self.get_status(result["run_id"])
                self.assertEqual(result["state"], "completed")
                self.assertEqual(list(result["checks"]), ["required_avus", "replica_status"])
                check = result["checks"]["replica_status"]
                self.assertEqual(check["report_path"], result["run_collection"] + "/checks/replica_status.json")
                self.assertEqual(check["summary"]["replicas_with_findings"], 1)
                self.assertEqual(len(self.documents[check["report_path"]]["findings"]), 1)

    def test_run_persists_findings_on_configured_resource_without_repairing_metadata(self):
        self.attributes[PROJECT].remove("title")
        result = self.invoke()
        run_path = result["run_collection"]
        self.assertEqual(result["state"], "completed")
        check = result["checks"]["required_avus"]
        self.assertEqual(check["summary"]["projects_with_findings"], 1)
        self.assertEqual(self.documents[check["report_path"]]["findings"][0]["missing_avus"], ["title"])
        self.assertEqual(self.documents[run_path + "/status.json"]["state"], "completed")
        self.assertEqual(self.documents[run_path + "/config.json"], {
            "checks": ["required_avus"], "report_resource": "passRescUM01", "execution_mode": "sync",
        })
        self.assertEqual(self.documents[run_path + "/summary.json"]["run_id"], result["run_id"])
        for call in self.callback.setCollectionAVU.call_args_list:
            self.assertEqual(call.args[0], run_path)
        self.assertEqual(self.callback.msiDataObjClose.call_count, 8)
        self.callback.delayExec.assert_not_called()

    def test_catalogue_failure_is_persisted_as_failed_and_raised(self):
        original = self.query.side_effect

        def fail_inventory(columns, condition, mode, callback):
            if columns == "COLL_NAME" and condition == self.rule.PROJECT_CONDITION:
                raise RuntimeError("catalogue unavailable")
            return original(columns, condition, mode, callback)

        self.query.side_effect = fail_inventory
        with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
            self.invoke()
        summaries = [document for path, document in self.documents.items() if path.endswith("/summary.json")]
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["state"], "failed")
        self.assertEqual(summaries[0]["checks"]["required_avus"]["error"], "catalogue unavailable")
        run_path = self.callback.msiCollCreate.call_args_list[0].args[0]
        self.callback.setCollectionAVU.assert_any_call(run_path, "state", "failed")

    def test_report_write_failure_closes_descriptor_and_does_not_publish_completion(self):
        self.callback.msiDataObjWrite.side_effect = RuntimeError("storage unavailable")
        with self.assertRaisesRegex(RuntimeError, "storage unavailable"):
            self.invoke()
        self.callback.msiDataObjClose.assert_called_once()
        self.assertEqual([call.args[2] for call in self.callback.setCollectionAVU.call_args_list], ["queued"])

    def test_only_rods_can_run_the_check(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
            self.invoke()
        self.query.assert_not_called()
        self.callback.msiCollCreate.assert_not_called()

    def test_existing_storage_without_resource_is_not_reinitialized(self):
        self.resource = None
        with self.assertRaisesRegex(RuntimeError, "Initialize housekeeping"):
            self.invoke()
        self.callback.msiCollCreate.assert_not_called()

    def test_first_sync_run_initializes_private_storage_with_defaults(self):
        self.report_collections.clear()
        self.resource = self.retention_days = None
        result = self.invoke()
        self.assertEqual(result["state"], "completed")
        self.assertEqual((self.resource, self.retention_days), ("passRescUM01", "31"))
        for path in (self.reports.REPORT_COLLECTION, self.reports.RUNS_COLLECTION):
            self.assertIn(path, self.report_collections)
            self.callback.msiSetACL.assert_any_call("default", "noinherit", "", path)
            self.callback.msiSetACL.assert_any_call("default", "own", "rods", path)
            self.callback.msiSetACL.assert_any_call("default", "null", "public#nlmumc", path)
        self.assertEqual(self.documents[result["run_collection"] + "/config.json"]["report_resource"], "passRescUM01")
        self.callback.delayExec.assert_not_called()

    def test_first_async_run_initializes_storage_before_queueing_worker(self):
        self.report_collections.clear()
        self.resource = self.retention_days = None
        result = self.invoke(mode="async")
        self.assertEqual(result["state"], "queued")
        self.assertEqual((self.resource, self.retention_days), ("passRescUM01", "31"))
        self.assertIn(self.reports.RUNS_COLLECTION, self.report_collections)
        self.callback.delayExec.assert_called_once()
        self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
        self.assertEqual(self.get_status(result["run_id"])["state"], "completed")

    def test_first_run_with_missing_default_resource_does_not_create_or_queue(self):
        self.report_collections.clear()
        self.resource = self.retention_days = None
        self.resources.clear()
        with self.assertRaisesRegex(RuntimeError, "Report resource does not exist"):
            self.invoke(mode="async")
        self.callback.msiCollCreate.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.callback.delayExec.assert_not_called()
        self.assertEqual(self.documents, {})

    def test_initialization_failure_does_not_write_reports_or_queue_work(self):
        self.report_collections.clear()
        self.resource = self.retention_days = None
        self.callback.msiSetACL.side_effect = RuntimeError("permission setup failed")
        with self.assertRaisesRegex(RuntimeError, "permission setup failed"):
            self.invoke(mode="async")
        self.callback.delayExec.assert_not_called()
        self.assertEqual(self.documents, {})

    def test_existing_configuration_and_permissions_are_preserved(self):
        self.resource = self.expected_report_resource = "otherResc"
        self.retention_days = "45"
        result = self.invoke()
        self.assertEqual(self.documents[result["run_collection"] + "/config.json"]["report_resource"], "otherResc")
        self.assertEqual(self.retention_days, "45")
        self.callback.msiSetACL.assert_not_called()
        self.assertTrue(all(call.args[0] != self.reports.REPORT_COLLECTION
                            for call in self.callback.setCollectionAVU.call_args_list))
        self.assertTrue(all(call.args[0] not in (self.reports.REPORT_COLLECTION, self.reports.RUNS_COLLECTION)
                            for call in self.callback.msiCollCreate.call_args_list))

    def test_existing_storage_without_runs_collection_is_not_repaired(self):
        self.report_collections.remove(self.reports.RUNS_COLLECTION)
        with self.assertRaisesRegex(RuntimeError, "Initialize housekeeping"):
            self.invoke()
        self.callback.msiCollCreate.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.callback.setCollectionAVU.assert_not_called()

    def test_existing_storage_with_invalid_retention_is_not_reinitialized(self):
        for days in (None, "", "0", "invalid"):
            self.retention_days = days
            with self.subTest(days=days), self.assertRaisesRegex(RuntimeError, "reportRetentionDays"):
                self.invoke()
        self.callback.msiCollCreate.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.callback.setCollectionAVU.assert_not_called()

    def test_existing_storage_with_unknown_resource_is_not_reinitialized(self):
        self.resource = "missing"
        with self.assertRaisesRegex(RuntimeError, "Report resource does not exist"):
            self.invoke()
        self.callback.msiCollCreate.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.callback.setCollectionAVU.assert_not_called()

    def test_selection_is_validated_before_any_work(self):
        for checks in ("", "  ", "unknown", "cleanup_reports unknown"):
            with self.subTest(checks=checks), self.assertRaises(RuntimeError):
                self.invoke(checks)
        self.query.assert_not_called()
        self.callback.msiCollCreate.assert_not_called()

    def test_multiple_checks_share_one_run_and_duplicate_selections_are_deduplicated(self):
        second = Mock(return_value={"check": "second", "execution_status": "completed", "summary": {"ok": 1}})
        with patch.dict(self.executor.CHECKS, {"second": second}):
            result = self.invoke("required_avus+second+required_avus")
        self.assertEqual(result["state"], "completed")
        self.assertEqual(list(result["checks"]), ["required_avus", "second"])
        second.assert_called_once()
        run_path = result["run_collection"]
        self.assertEqual(self.callback.msiCollCreate.call_count, 2)
        self.assertEqual(self.documents[run_path + "/config.json"]["checks"], ["required_avus", "second"])
        for entry in result["checks"].values():
            self.assertTrue(entry["report_path"].startswith(run_path + "/checks/"))

    def test_plus_list_preserves_order_and_whitespace_lists_remain_supported(self):
        self.assertEqual(self.controller._selected_checks("required_avus+rebalance_resources+cleanup_reports"),
                         ["required_avus", "rebalance_resources", "cleanup_reports"])
        self.assertEqual(self.controller._selected_checks("required_avus cleanup_reports"),
                         ["required_avus", "cleanup_reports"])
        with self.assertRaisesRegex(RuntimeError, "Unknown housekeeping checks"):
            self.controller._selected_checks("required_avus+unknown")

    def test_failed_check_does_not_prevent_later_checks_and_run_is_partial(self):
        failed = Mock(side_effect=RuntimeError("check unavailable"))
        with patch.dict(self.executor.CHECKS, {"failed_check": failed}):
            with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
                self.invoke("failed_check required_avus")
        summary = next(document for path, document in self.documents.items() if path.endswith("/summary.json"))
        self.assertEqual(summary["state"], "partial")
        self.assertEqual(summary["checks"]["failed_check"]["error"], "check unavailable")
        self.assertEqual(summary["checks"]["required_avus"]["execution_status"], "completed")

    def test_only_selected_check_runs_and_cleanup_results_are_persisted(self):
        cleanup = {"deleted": ["expired"], "skipped": [], "errors": []}
        with patch.object(self.executor, "_cleanup_housekeeping_reports", return_value=cleanup) as operation:
            result = self.invoke("cleanup_reports")
        operation.assert_called_once()
        self.assertEqual(operation.call_args.args[1], "false")
        self.assertEqual(result["checks"]["cleanup_reports"]["summary"], {"deleted": 1, "skipped": 0, "errors": 0})
        self.assertEqual(list(result["checks"]), ["cleanup_reports"])
        self.assertEqual(self.query.call_count, 4)  # storage validation only; no AVU scan

    def test_cleanup_deletion_errors_fail_the_run(self):
        cleanup = {"deleted": [], "skipped": [], "errors": [{"path": "expired", "error": "locked"}]}
        with patch.object(self.executor, "_cleanup_housekeeping_reports", return_value=cleanup):
            with self.assertRaisesRegex(RuntimeError, "Housekeeping checks failed"):
                self.invoke("cleanup_reports")
        summary = next(document for path, document in self.documents.items() if path.endswith("/summary.json"))
        self.assertEqual(summary["state"], "failed")
        self.assertEqual(summary["checks"]["cleanup_reports"]["summary"]["errors"], 1)

    def test_async_only_persists_submission_and_enqueues_worker(self):
        check = Mock()
        with patch.dict(self.executor.CHECKS, {"required_avus": check}):
            result = self.invoke(mode="async")
        self.assertEqual(result["state"], "queued")
        self.assertNotIn("started_at", result)
        check.assert_not_called()
        self.assertEqual(self.query.call_count, 4)
        self.assertEqual(set(self.documents), {result["run_collection"] + "/config.json", result["status_path"]})
        self.callback.delayExec.assert_called_once_with(
            self.controller.DELAY_OPTIONS, f"execute_housekeeping('{result['run_id']}')", "",
        )
        self.assertIn("REPEAT 0 TIMES", self.callback.delayExec.call_args.args[0])

    def test_omitted_mode_is_rejected_before_work(self):
        with self.assertRaisesRegex(RuntimeError, "Execution mode"):
            self.controller.run_housekeeping(["required_avus", ""], self.callback, None)
        self.query.assert_not_called()
        self.callback.msiCollCreate.assert_not_called()

    def test_invalid_mode_is_rejected_before_work(self):
        for mode in ("invalid", ""):
            with self.subTest(mode=mode), self.assertRaisesRegex(RuntimeError, "Execution mode"):
                self.invoke(mode=mode)
        self.query.assert_not_called()
        self.callback.msiCollCreate.assert_not_called()

    def test_rebalance_task_is_registered_and_uses_controller_reporting(self):
        self.assertIs(self.executor.CHECKS["rebalance_resources"], self.rebalance._rebalance_resources)
        report = {"check": "rebalance_resources", "execution_status": "completed",
                  "summary": {"resources_found": 2, "resources_rebalanced": 2, "resources_failed": 0},
                  "resources": [{"resource": "replication-one", "execution_status": "completed"}]}
        with patch.dict(self.executor.CHECKS, {"rebalance_resources": Mock(return_value=report)}):
            result = self.invoke("rebalance_resources")
        check = result["checks"]["rebalance_resources"]
        self.assertEqual(check["summary"], report["summary"])
        self.assertEqual(self.documents[check["report_path"]], report)

    def test_queue_submission_error_is_persisted_as_failed_and_raised(self):
        self.callback.delayExec.side_effect = RuntimeError("delay server unavailable")
        with self.assertRaisesRegex(RuntimeError, "Could not queue housekeeping"):
            self.invoke(mode="async")
        summary = next(document for path, document in self.documents.items() if path.endswith("/summary.json"))
        self.assertEqual(summary["state"], "failed")
        self.assertIn("delay server unavailable", summary["error"])
        self.assertEqual(self.get_status(summary["run_id"]), summary)

    def test_delayed_worker_uses_saved_config_and_is_not_replayed(self):
        result = self.invoke(mode="async")
        self.resource = "changed-after-submission"
        self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
        summary = self.get_status(result["run_id"])
        self.assertEqual(summary["state"], "completed")
        self.assertEqual(summary["checks"]["required_avus"]["summary"]["projects_checked"], 1)
        writes = self.callback.msiDataObjWrite.call_count
        self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
        self.assertEqual(self.callback.msiDataObjWrite.call_count, writes)

    def test_delayed_check_failure_is_recorded_without_retrying_worker(self):
        result = self.invoke(mode="async")
        failed = Mock(side_effect=RuntimeError("catalogue unavailable"))
        with patch.dict(self.executor.CHECKS, {"required_avus": failed}):
            self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
        summary = self.get_status(result["run_id"])
        self.assertEqual(summary["state"], "failed")
        self.assertEqual(summary["checks"]["required_avus"]["error"], "catalogue unavailable")

    def test_polling_pending_runs_does_not_read_mutable_status_file(self):
        result = self.invoke(mode="async")
        self.assertEqual(self.get_status(result["run_id"])["state"], "queued")
        self.run_metadata[result["run_collection"]]["state"] = "running"
        self.assertEqual(self.get_status(result["run_id"])["state"], "running")
        self.assertEqual(self.reads, [])

    def test_invalid_run_ids_and_non_admin_polling_are_rejected(self):
        for run_id in ("../other", "", "2026-11-09_bad", "2026-11-09_" + "a" * 32 + "/nested"):
            with self.subTest(run_id=run_id), self.assertRaisesRegex(RuntimeError, "Invalid housekeeping run ID"):
                self.get_status(run_id)
        self.query.assert_not_called()
        result = self.invoke(mode="async")
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
            self.get_status(result["run_id"])
        with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
            self.executor.execute_housekeeping([result["run_id"]], self.callback, None)

    def test_list_runs_returns_empty_and_out_of_range_pages(self):
        self.assertEqual(self.list_runs(), {"runs": [], "total": 0, "limit": 50, "offset": 0})
        result = self.invoke()
        self.run_inventory = [(result["run_collection"], "02000000000")]
        self.assertEqual(self.list_runs(offset="1"), {"runs": [], "total": 1, "limit": 50, "offset": 1})
        self.assertEqual(self.reads, [])

    def test_list_runs_orders_by_creation_time_and_reads_only_requested_page(self):
        oldest, newest, middle = [self.invoke() for _ in range(3)]
        self.run_inventory = [(oldest["run_collection"], "01999999998"),
                              (newest["run_collection"], "02000000000"),
                              (middle["run_collection"], "01999999999")]
        page = self.list_runs(limit="1", offset="1")
        self.assertEqual(page, {"runs": [dict(middle, created_at=1_999_999_999)],
                                "total": 3, "limit": 1, "offset": 1})
        self.assertEqual(self.reads, [middle["summary_path"]])
        self.assertEqual(self.list_runs(limit="1")["runs"][0]["run_id"], newest["run_id"])

    def test_list_runs_breaks_creation_time_ties_by_run_id(self):
        results = [self.invoke(mode="async") for _ in range(3)]
        self.run_inventory = [(result["run_collection"], "02000000000") for result in results]
        expected = sorted((result["run_id"] for result in results), reverse=True)
        self.assertEqual([self.list_runs("1", str(index))["runs"][0]["run_id"] for index in range(3)], expected)

    def test_list_runs_skips_non_controller_collections_and_nested_paths(self):
        result = self.invoke(mode="async")
        self.run_inventory = [(self.reports.RUNS_COLLECTION + "/unrelated", "02000000000"),
                              (result["run_collection"] + "/checks", "02000000000"),
                              (result["run_collection"], "02000000000")]
        page = self.list_runs()
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["runs"][0]["run_id"], result["run_id"])

    def test_list_active_runs_does_not_read_mutable_files(self):
        results = [self.invoke(mode="async") for _ in range(2)]
        self.run_metadata[results[1]["run_collection"]]["state"] = "running"
        self.run_inventory = [(result["run_collection"], "02000000000") for result in results]
        self.assertEqual({run["state"] for run in self.list_runs()["runs"]}, {"queued", "running"})
        self.assertEqual(self.reads, [])

    def test_list_pagination_is_validated_before_catalog_access(self):
        for limit in ("", "0", "101", "-1", "1.5", "true", " 1", "1\n"):
            with self.subTest(limit=limit), self.assertRaisesRegex(RuntimeError, "limit"):
                self.list_runs(limit=limit)
        for offset in ("", "-1", "1.5", "true", " 0", "0\n"):
            with self.subTest(offset=offset), self.assertRaisesRegex(RuntimeError, "offset"):
                self.list_runs(offset=offset)
        self.query.assert_not_called()

    def test_report_returns_full_output_and_supports_historical_checks(self):
        report = {"check": "historical_check", "execution_status": "completed",
                  "summary": {"findings": 1}, "findings": [{"path": COLLECTION}],
                  "stdout": "some output\n", "stderr": "diagnostics\n", "return_code": 0}
        with patch.dict(self.executor.CHECKS, {"historical_check": Mock(return_value=report)}):
            result = self.invoke("historical_check")
        self.assertEqual(self.get_report(result["run_id"], "historical_check"), report)
        self.assertEqual(self.reads, [result["summary_path"], result["checks"]["historical_check"]["report_path"]])

    def test_report_retrieves_failed_checks_and_list_includes_partial_and_failed_runs(self):
        results = []
        for checks, state in (("broken", "failed"), ("broken+required_avus", "partial")):
            with self.subTest(state=state):
                with patch.dict(self.executor.CHECKS, {"broken": Mock(side_effect=RuntimeError("check failed"))}):
                    result = self.invoke(checks, mode="async")
                    self.executor.execute_housekeeping([result["run_id"]], self.callback, None)
                summary = self.get_status(result["run_id"])
                self.assertEqual(summary["state"], state)
                self.assertEqual(self.get_report(result["run_id"], "broken"), {
                    "check": "broken", "execution_status": "failed", "error": "check failed",
                })
                results.append(result)
        self.run_inventory = [(result["run_collection"], "02000000000") for result in results]
        self.assertEqual({run["state"] for run in self.list_runs()["runs"]}, {"failed", "partial"})

    def test_report_rejects_active_missing_and_unexecuted_checks(self):
        result = self.invoke(mode="async")
        for state in ("queued", "running"):
            self.run_metadata[result["run_collection"]]["state"] = state
            with self.subTest(state=state), self.assertRaisesRegex(RuntimeError, "terminal runs"):
                self.get_report(result["run_id"])
        self.assertEqual(self.reads, [])
        missing_id = "2026-11-10_" + "a" * 32
        with self.assertRaisesRegex(RuntimeError, "does not exist"):
            self.get_report(missing_id)
        finished = self.invoke()
        with self.assertRaisesRegex(RuntimeError, "no report"):
            self.get_report(finished["run_id"], "replica_status")
        self.assertEqual(self.reads, [finished["summary_path"]])

    def test_read_rules_reject_non_admins_before_any_reads(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
            self.list_runs()
        with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
            self.get_report("2026-11-10_" + "a" * 32)
        self.query.assert_not_called()
        self.assertEqual(self.reads, [])

    def test_rules_are_exported_for_irods(self):
        package = self.load("housekeeping/__init__.py")
        exports = {}
        with patch.dict(sys.modules, {"datahubirodsruleset.housekeeping": package}):
            exec("from datahubirodsruleset.housekeeping import *", exports)
        for module, names in (
            (self.storage, ("initialize_housekeeping",)),
            (self.reports, ("cleanup_housekeeping_reports", "get_housekeeping_status",
                            "list_housekeeping_runs", "get_housekeeping_report")),
            (self.controller, ("run_housekeeping",)),
            (self.executor, ("execute_housekeeping",)),
            (self.dropzones, ("scan_dropzone_directories",)),
        ):
            for name in names:
                self.assertIs(exports[name], getattr(module, name))

    def test_report_rejects_paths_before_any_reads(self):
        for run_id in ("../other", "", "2026-11-10_bad", "2026-11-10_" + "a" * 32 + "/nested"):
            with self.subTest(run_id=run_id), self.assertRaisesRegex(RuntimeError, "Invalid housekeeping run ID"):
                self.get_report(run_id)
        for check in ("", "../config", "required_avus.json", "/other", "required_avus/other", "check\n"):
            with self.subTest(check=check), self.assertRaisesRegex(RuntimeError, "Invalid housekeeping check name"):
                self.get_report("2026-11-10_" + "a" * 32, check)
        self.query.assert_not_called()
        self.assertEqual(self.reads, [])


if __name__ == "__main__":
    unittest.main()
