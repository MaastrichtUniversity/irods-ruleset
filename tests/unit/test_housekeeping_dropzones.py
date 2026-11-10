import importlib.util
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
DIRECT = "/nlmumc/ingest/direct/direct-token"
MOUNTED = "/nlmumc/ingest/zones/mounted-token"
PROJECT = "/nlmumc/projects/P000000001"
STAGING_DIRECT = "/staging/ingest/direct"
STAGING_ZONES = "/staging/ingest/zones"
MOUNTED_ROOT = "/mnt/ingest/zones"


class HousekeepingDropzoneTests(unittest.TestCase):
    def setUp(self):
        modules = {"genquery": SimpleNamespace(row_iterator=self.rows, AS_LIST=object())}
        for name in ("datahubirodsruleset", "datahubirodsruleset.housekeeping"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        for relative in ("decorator.py", "listing_queries.py", "housekeeping/storage.py",
                         "housekeeping/check_dropzone_consistency.py"):
            name = "datahubirodsruleset." + relative[:-3].replace("/", ".")
            spec = importlib.util.spec_from_file_location(name, ROOT / relative)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        self.rule = module
        self.callback = Mock()
        self.ctx = SimpleNamespace(callback=self.callback)
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.get_dropzone_disk_inventory.side_effect = self.remote
        self.collections = [DIRECT, MOUNTED, DIRECT + "/nested"]
        self.metadata = {DIRECT: {"state": "open"}, MOUNTED: {"project": "P000000001", "state": "ingesting"}}
        self.projects = {PROJECT: {"ingestResource": "ingest-um"}}
        self.resources = [("staging", "um", "/staging"), ("ingest-um", "um", "/vault"),
                          ("ingest-azm", "azm", "/vault")]
        self.staging = [("staging",)]
        self.nonempty = [DIRECT + "/nested"]
        self.disk = {("um", STAGING_DIRECT): ["direct-token"], ("um", STAGING_ZONES): ["mounted-token"],
                     ("um", MOUNTED_ROOT): ["mounted-token"], ("azm", MOUNTED_ROOT): []}
        self.events = []

    def rows(self, columns, condition, mode, callback):
        self.events.append("catalog")
        if columns == "RESC_NAME, RESC_LOC, RESC_VAULT_PATH":
            return self.resources
        if columns == "RESC_NAME":
            return self.staging
        if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            if condition.startswith("COLL_PARENT_NAME"):
                return [(path, key, value) for path, values in self.projects.items() for key, value in values.items()]
            paths, attributes = condition.split(" AND ")
            return [(path, key, value) for path, values in self.metadata.items()
                    if path in re.findall("'([^']*)'", paths)
                    for key, value in values.items() if key in re.findall("'([^']*)'", attributes)]
        if columns == "COLL_NAME":
            parent = condition.split("'")[1]
            if "DATA_ID" in condition:
                return [(path,) for path in self.nonempty if path.startswith(parent[:-1])]
            return [(path,) for path in self.collections if path.rsplit("/", 1)[0] == parent]
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def remote(self, host, roots, output):
        self.events.append("remote")
        inventories = []
        for root in json.loads(roots):
            value = self.disk[(host, root)]
            if isinstance(value, Exception):
                inventories.append({"root": root, "execution_status": "failed", "error": str(value)})
            else:
                inventories.append({"root": root, "execution_status": "completed", "directories": value})
        return {"arguments": [host, roots, json.dumps(inventories)]}

    def audit(self):
        return self.rule._audit_dropzone_consistency(self.ctx)

    def test_matching_catalog_and_disk_use_one_remote_call_per_host_after_catalog_reads(self):
        report = self.audit()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"]["catalog_dropzones"], 2)
        self.assertEqual(report["summary"]["locations_scanned"], 3)
        self.callback.get_dropzone_disk_inventory.assert_called_once()
        self.assertEqual(self.events[-1], "remote")
        self.assertNotIn("remote", self.events[:-1])

    def test_disk_only_directories_are_reported_in_each_location_without_token_filtering(self):
        for key in self.disk:
            if key[0] == "um":
                self.disk[key].append("old directory's remnant")
        report = self.audit()
        self.assertEqual(report["execution_status"], "completed")
        self.assertEqual(report["summary"]["missing_in_irods"], 3)
        self.assertEqual({entry["location"] for entry in report["findings"]},
                         {"staging_direct", "staging_zones", "mounted_data"})
        self.assertTrue(all(entry["kind"] == "missing_in_irods" for entry in report["findings"]))

    def test_missing_direct_directory_uses_nested_objects_to_mark_catalog_nonempty(self):
        self.disk[("um", STAGING_DIRECT)] = []
        finding, = self.audit()["findings"]
        self.assertEqual(finding["logical_path"], DIRECT)
        self.assertIs(finding["catalog_empty"], False)
        self.assertEqual(finding["state"], "open")
        self.assertEqual(finding["physical_path"], STAGING_DIRECT + "/direct-token")

    def test_either_or_both_mounted_locations_can_be_missing_even_for_empty_catalog(self):
        for missing in ((STAGING_ZONES,), (MOUNTED_ROOT,), (STAGING_ZONES, MOUNTED_ROOT)):
            with self.subTest(missing=missing):
                for root in (STAGING_ZONES, MOUNTED_ROOT):
                    self.disk[("um", root)] = [] if root in missing else ["mounted-token"]
                findings = self.audit()["findings"]
                self.assertEqual(len(findings), len(missing))
                self.assertTrue(all(entry["catalog_empty"] for entry in findings))
                self.assertTrue(all(entry["project"] == "P000000001" for entry in findings))

    def test_all_project_hosts_are_scanned_without_dropzones_and_duplicate_hosts_are_batched(self):
        self.projects[PROJECT + "2"] = {"ingestResource": "ingest-azm"}
        self.projects[PROJECT + "3"] = {"ingestResource": "ingest-azm"}
        self.disk[("azm", MOUNTED_ROOT)] = ["abandoned"]
        report = self.audit()
        self.assertEqual(self.callback.get_dropzone_disk_inventory.call_count, 2)
        finding, = report["findings"]
        self.assertEqual((finding["token"], finding["host"]), ("abandoned", "azm"))

    def test_unreferenced_hosts_are_not_scanned(self):
        self.disk[("azm", MOUNTED_ROOT)] = ["outside-coverage"]
        self.assertEqual(self.audit()["findings"], [])
        self.assertEqual(self.callback.get_dropzone_disk_inventory.call_args.args[0], "um")

    def test_copy_on_wrong_host_does_not_satisfy_expected_host_or_become_an_orphan(self):
        self.projects[PROJECT + "2"] = {"ingestResource": "ingest-azm"}
        self.disk[("um", MOUNTED_ROOT)] = []
        self.disk[("azm", MOUNTED_ROOT)] = ["mounted-token"]
        finding, = self.audit()["findings"]
        self.assertEqual((finding["kind"], finding["host"]), ("missing_on_disk", "um"))

    def test_missing_project_metadata_fails_mapping_but_keeps_staging_findings(self):
        self.metadata[MOUNTED] = {}
        self.disk[("um", STAGING_ZONES)] = []
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertEqual(report["errors"][0]["logical_path"], MOUNTED)
        finding, = report["findings"]
        self.assertEqual(finding["location"], "staging_zones")

    def test_missing_project_resource_is_an_error_even_without_current_dropzones(self):
        self.projects[PROJECT + "2"] = {"ingestResource": "removed-resource"}
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertEqual(report["errors"][0]["resource"], "removed-resource")
        self.assertEqual(report["summary"]["locations_scanned"], 3)

    def test_ambiguous_or_absent_staging_keeps_mounted_audit(self):
        for staging in ([], [("staging",), ("other-staging",)]):
            with self.subTest(staging=staging):
                self.staging = staging
                self.disk[("um", MOUNTED_ROOT)] = ["mounted-token", "orphan"]
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["summary"]["locations_scanned"], 1)
                self.assertEqual(report["findings"][0]["token"], "orphan")

    def test_failed_root_never_looks_empty_and_other_roots_still_report(self):
        self.disk[("um", STAGING_ZONES)] = PermissionError("unreadable root")
        self.disk[("um", STAGING_DIRECT)] = []
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertEqual(report["errors"][0]["error"], "unreadable root")
        self.assertEqual(report["summary"]["locations_scanned"], 2)
        finding, = report["findings"]
        self.assertEqual(finding["logical_path"], DIRECT)

    def test_staging_without_physical_host_or_vault_does_not_prevent_mounted_scans(self):
        for host, vault in (("EMPTY_RESC_HOST", "/staging"), ("um", "EMPTY_RESC_PATH")):
            with self.subTest(host=host, vault=vault):
                self.resources[0] = ("staging", host, vault)
                report = self.audit()
                self.assertEqual(report["execution_status"], "failed")
                self.assertEqual(report["summary"]["locations_scanned"], 1)
                self.assertEqual(report["errors"][0]["location"], "staging")

    def test_unreachable_host_preserves_successful_host_results(self):
        self.projects[PROJECT + "2"] = {"ingestResource": "ingest-azm"}

        def remote(host, roots, output):
            if host == "azm":
                raise RuntimeError("offline")
            return self.remote(host, roots, output)

        self.callback.get_dropzone_disk_inventory.side_effect = remote
        report = self.audit()
        self.assertEqual(report["execution_status"], "failed")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["summary"]["locations_scanned"], 3)
        self.assertEqual(report["errors"][0]["host"], "azm")

    def test_worker_reports_missing_root_and_continues_without_recursing_or_including_files(self):
        with TemporaryDirectory() as root:
            directory = Path(root) / "any name's valid"
            directory.mkdir()
            (directory / "nested").mkdir()
            (Path(root) / "ordinary-file").touch()
            args = [json.dumps([root + "/missing", root]), ""]
            self.rule.scan_dropzone_directories(args, self.callback, None)
            failed, completed = json.loads(args[1])
            self.assertEqual(failed["execution_status"], "failed")
            self.assertNotIn("directories", failed)
            self.assertEqual(completed["directories"], [directory.name])

    def test_worker_denies_non_rods_before_reading_disk(self):
        self.callback.get_client_username.return_value = {"arguments": ["jmelius"]}
        with patch.object(self.rule.os, "scandir") as scan:
            with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
                self.rule.scan_dropzone_directories(["[]", ""], self.callback, None)
        scan.assert_not_called()

    def test_worker_discards_partial_inventory_when_a_directory_cannot_be_inspected(self):
        def entries():
            yield SimpleNamespace(name="visible", is_dir=lambda: True)
            raise PermissionError("cannot inspect directory")

        with patch.object(self.rule.os, "scandir") as scan:
            scan.return_value.__enter__.return_value = entries()
            args = [json.dumps(["/unreadable"]), ""]
            self.rule.scan_dropzone_directories(args, self.callback, None)
        failed, = json.loads(args[1])
        self.assertEqual(failed["execution_status"], "failed")
        self.assertNotIn("directories", failed)


if __name__ == "__main__":
    unittest.main()
