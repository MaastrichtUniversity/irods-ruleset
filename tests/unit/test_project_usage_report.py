import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectUsageReportTests(unittest.TestCase):
    def setUp(self):
        self.paths = [f"/nlmumc/projects/P{i:09d}" for i in range(1, 4)]
        self.metadata = [
            (path, attribute, value)
            for path in self.paths
            for attribute, value in (
                ("responsibleCostCenter", "123"), ("dataSteward", "steward"),
                ("title", "Project's title"), ("OBI:0000103", "investigator"),
            )
        ]
        self.sizes = [
            (self.paths[0] + "/C000000001", "dcat:byteSize_resc_10", "1500000000"),
            (self.paths[0] + "/C000000002", "dcat:byteSize_resc_10", "2000000000"),
            (self.paths[0] + "/C000000001", "dcat:byteSize_resc_20", "1500000000"),
            (self.paths[0] + "/C000000002", "dcat:byteSize_resc_20", "2000000000"),
            (self.paths[1] + "/C000000001/data", "dcat:byteSize_resc_10", "0"),
        ]
        self.prices = [("10", "disk", "NCIT:C88193", "12"), ("20", "replica", "NCIT:C88193", "24")]
        self.query = Mock(side_effect=self.rows)
        modules = {
            "datahubirodsruleset": ModuleType("datahubirodsruleset"),
            "datahubirodsruleset.decorator": load("usage_decorator", ROOT / "decorator.py"),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(
                get_project_id_from_project_path=lambda path: path.rsplit("/", 1)[1],
            )),
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
        }
        with patch.dict(sys.modules, modules):
            self.rule = load("usage_report", ROOT / "projects/get_project_usage_report.py")
        self.callback = Mock()
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if columns == "COLL_NAME":
            self.assertEqual(condition, "COLL_PARENT_NAME = '/nlmumc/projects'")
            return [(path,) for path in self.paths]
        if columns == "RESC_NAME, RESC_ID":
            return [("disk", "10"), ("replica", "20")]
        if condition == "META_RESC_ATTR_NAME = 'NCIT:C88193'":
            return self.prices
        if "META_COLL_ATTR_NAME in" in condition:
            self.assertIn("COLL_PARENT_NAME = '/nlmumc/projects'", condition)
            return self.metadata
        if "META_COLL_ATTR_NAME like 'dcat:byteSize_resc%'" in condition:
            self.assertIn("COLL_NAME like '/nlmumc/projects/%/%'", condition)
            return self.sizes
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def invoke(self):
        output = [""]
        self.rule.get_project_usage_report(output, self.callback, None)
        self.callback.getCollectionAVU.assert_not_called()
        self.callback.get_collection_size_per_resource.assert_not_called()
        return json.loads(output[0])

    def test_aggregates_collections_and_keeps_replica_costs_and_report_fields(self):
        self.assertEqual(self.invoke(), [
            {
                "budget_number": "123", "data_steward": "steward",
                "principal_investigator": "investigator", "id": "P000000001_disk",
                "project_id": "P000000001", "title": "Project's title",
                "resource": {"cost_per_month": 3.5, "cost_per_year": 42.0,
                             "size": 3500000000, "resource": "disk"},
            },
            {
                "budget_number": "123", "data_steward": "steward",
                "principal_investigator": "investigator", "id": "P000000001_replica",
                "project_id": "P000000001", "title": "Project's title",
                "resource": {"cost_per_month": 7.0, "cost_per_year": 84.0,
                             "size": 3500000000, "resource": "replica"},
            },
            {
                "budget_number": "123", "data_steward": "steward",
                "principal_investigator": "investigator", "id": "P000000002_disk",
                "project_id": "P000000002", "title": "Project's title",
                "resource": {"cost_per_month": 0.0, "cost_per_year": 0.0,
                             "size": 0, "resource": "disk"},
            },
        ])
        self.assertEqual(self.query.call_count, 5)

    def test_no_projects_skips_bulk_queries(self):
        self.paths.clear()
        self.assertEqual(self.invoke(), [])
        self.assertEqual(self.query.call_count, 1)

    def test_required_metadata_still_fails_for_missing_or_empty_values(self):
        original = self.metadata[:]
        for attribute in ("responsibleCostCenter", "dataSteward", "title", "OBI:0000103"):
            for empty in (False, True):
                with self.subTest(attribute=attribute, empty=empty):
                    self.metadata = [row for row in original if row[:2] != (self.paths[2], attribute)]
                    if empty:
                        self.metadata.append((self.paths[2], attribute, ""))
                    with self.assertRaisesRegex(RuntimeError, f"The attribute '{attribute}'.*has no value in iCAT"):
                        self.invoke()

    def test_uses_last_value_like_legacy_metadata_helper(self):
        self.metadata.append((self.paths[0], "title", "Updated title"))
        self.assertEqual(self.invoke()[0]["title"], "Updated title")

    def test_sizes_from_projects_outside_the_project_listing_are_ignored(self):
        self.sizes.append(("/nlmumc/projects/P999999999/C000000001", "dcat:byteSize_resc_10", "1"))
        self.assertEqual(len(self.invoke()), 3)

    def test_large_byte_counts_are_summed_as_integers(self):
        self.sizes = [(self.paths[0] + "/C000000001", "dcat:byteSize_resc_10", str(2**53 + 1))]
        self.assertEqual(self.invoke()[0]["resource"]["size"], 2**53 + 1)

    def test_missing_resource_price_still_fails(self):
        self.prices.pop()
        with self.assertRaises(KeyError):
            self.invoke()

    def test_thousand_projects_still_use_five_queries(self):
        self.paths = [f"/nlmumc/projects/P{i:09d}" for i in range(1, 1001)]
        self.metadata = [(path, attribute, "value") for path in self.paths
                         for attribute in ("responsibleCostCenter", "dataSteward", "title", "OBI:0000103")]
        self.sizes = [(path + "/C000000001", "dcat:byteSize_resc_10", "1000000000") for path in self.paths]
        self.assertEqual(len(self.invoke()), 1000)
        self.assertEqual(self.query.call_count, 5)


if __name__ == "__main__":
    unittest.main()
