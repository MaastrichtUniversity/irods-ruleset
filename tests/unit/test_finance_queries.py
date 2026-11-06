import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FinanceQueryTests(unittest.TestCase):
    def setUp(self):
        self.projects = [PROJECT, PROJECT + "-empty"]
        self.collections = [PROJECT + "/C000000001", PROJECT + "/C000000002"]
        self.sizes = [(self.collections[0], "dcat:byteSize_resc_10", "1000000000"),
                      (self.collections[0], "dcat:byteSize_resc_20", "2000000000")]
        self.prices = [("10", "12"), ("20", "24")]
        self.metadata = [(path, attr, value) for path in self.projects for attr, value in
                         (("responsibleCostCenter", "123"), ("title", "Project's title"))]
        self.query = Mock(side_effect=self.rows)
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        avus = SimpleNamespace(**{key: SimpleNamespace(value=value) for key, value in
                               dict(PRINCIPAL_INVESTIGATOR="OBI:0000103", DATA_STEWARD="dataSteward",
                                    RESPONSIBLE_COST_CENTER="responsibleCostCenter", TITLE="title").items()})
        modules = {
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(
                get_project_id_from_project_path=lambda path: path.rsplit("/", 1)[1])),
            "dhpythonirodsutils.enums": SimpleNamespace(ProjectAVUs=avus),
        }
        for name in ("datahubirodsruleset", "datahubirodsruleset.projects"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        load("datahubirodsruleset.decorator", "decorator.py")
        load("datahubirodsruleset.listing_queries", "listing_queries.py")
        self.finance = load("datahubirodsruleset.projects.get_project_finance", "projects/get_project_finance.py")
        self.listing = load("finance_listing", "projects/list_projects_finance.py")

    def selected(self, condition, column):
        match = re.search(re.escape(column) + r" (?:in \((.*?)\)|= ('(?:[^']|'')*'))", condition)
        if not match:
            return None
        return [value.replace("''", "'") for value in re.findall(r"'((?:[^']|'')*)'", match[1] or match[2])]

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if " in (" in condition:
            self.assertLess(len(condition.encode()), 1024)
        parents = self.selected(condition, "COLL_PARENT_NAME")
        paths = self.selected(condition, "COLL_NAME")
        if "META_RESC_ATTR" in columns:
            return self.prices
        if columns == "COLL_NAME" and "META_COLL_ATTR_VALUE" in condition:
            self.assertEqual(self.selected(condition, "META_COLL_ATTR_VALUE"), ["alice"])
            self.assertEqual(self.selected(condition, "META_COLL_ATTR_NAME"), ["OBI:0000103", "dataSteward"])
            return [(path,) for path in self.projects] + [(self.projects[0],)] if self.projects else []
        if columns == "COLL_NAME":
            return [(path,) for path in self.collections if path.rsplit("/", 1)[0] in parents]
        if "META_COLL_ATTR_NAME like 'dcat:byteSize_resc_%'" in condition:
            return [row for row in self.sizes if row[0].rsplit("/", 1)[0] in parents]
        if "META_COLL_ATTR_NAME in" in condition:
            return [row for row in self.metadata if row[0] in paths]
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def single(self, path=PROJECT):
        args = [path, ""]
        self.finance.get_project_finance(args, self.callback, None)
        return json.loads(args[1])

    def listing_result(self):
        args = [""]
        self.listing.get_projects_finance(args, self.callback, None)
        self.callback.getCollectionAVU.assert_not_called()
        self.callback.get_project_finance.assert_not_called()
        return json.loads(args[0])

    def test_finance_preserves_replica_sizes_costs_units_and_empty_collections(self):
        self.assertEqual(self.single(), {
            "project_cost_yearly": 60.0, "project_cost_monthly": 5.0,
            "project_size_gib": 3000000000 / 1024**3,
            "project_size_gb": (3000000000 / 1024**3) * 1.024**3,
            "collections": [
                {"collection": self.collections[0], "data_size_gib": 3000000000 / 1024**3,
                 "collection_storage_cost": 60.0, "details_per_resource": [
                     {"resource": "10", "data_size_gb_on_resource": 1.0,
                      "price_per_gb_per_year": 12.0, "storage_cost_on_resource": 12.0},
                     {"resource": "20", "data_size_gb_on_resource": 2.0,
                      "price_per_gb_per_year": 24.0, "storage_cost_on_resource": 48.0}]},
                {"collection": self.collections[1], "data_size_gib": 0.0,
                 "collection_storage_cost": 0, "details_per_resource": []}],
        })

    def test_listing_preserves_required_metadata_deduplicates_projects_and_keeps_empty_projects(self):
        result = {project["project_id"]: project for project in self.listing_result()}
        self.assertEqual(len(result), 2)
        self.assertEqual(result["P000000001"]["budget_number"], "123")
        self.assertEqual(result["P000000001"]["title"], "Project's title")
        self.assertEqual(result["P000000001"]["project_cost_yearly"], 60.0)
        self.assertEqual(result["P000000001-empty"]["collections"], [])
        self.assertEqual(result["P000000001-empty"]["project_size_gib"], 0)

    def test_missing_and_empty_required_metadata_still_fail(self):
        original = self.metadata[:]
        for attr in ("title", "responsibleCostCenter"):
            for empty in (False, True):
                with self.subTest(attr=attr, empty=empty):
                    self.metadata = [row for row in original if row[:2] != (PROJECT, attr)]
                    if empty:
                        self.metadata.append((PROJECT, attr, ""))
                    with self.assertRaisesRegex(RuntimeError, f"The attribute '{attr}'.*has no value in iCAT"):
                        self.listing_result()

    def test_missing_or_invalid_resource_price_still_fails(self):
        self.prices = [("10", "12")]
        with self.assertRaises(KeyError):
            self.single()
        self.prices.append(("20", ""))
        with self.assertRaises(ValueError):
            self.single()

    def test_metadata_uses_last_value_and_size_rows_are_not_collapsed(self):
        self.metadata.append((PROJECT, "title", "Updated"))
        self.sizes.append((self.collections[0], "dcat:byteSize_resc_10", "500000000"))
        result = self.listing_result()[0]
        self.assertEqual(result["title"], "Updated")
        self.assertEqual(result["project_cost_yearly"], 66.0)

    def test_no_projects_skips_detail_queries(self):
        self.projects = []
        self.assertEqual(self.listing_result(), [])
        self.assertEqual(self.query.call_count, 1)

    def test_nested_and_unselected_collections_are_excluded(self):
        self.collections += [self.collections[0] + "/nested", "/nlmumc/projects/other/C000000001"]
        self.sizes += [(path, "dcat:byteSize_resc_10", "999") for path in self.collections[2:]]
        self.assertEqual(len(self.single()["collections"]), 2)
        self.assertEqual(self.single()["project_cost_yearly"], 60.0)

    def test_thousand_collections_use_three_queries(self):
        self.collections = [PROJECT + f"/C{i:09d}" for i in range(1000)]
        self.sizes = [(path, "dcat:byteSize_resc_" + resource, "1000000000")
                      for path in self.collections for resource in ("10", "20")]
        self.assertEqual(self.single()["project_cost_yearly"], 36000.0)
        self.assertEqual(self.query.call_count, 3)

    def test_many_projects_share_prices_and_use_bounded_queries(self):
        self.projects = [f"/nlmumc/projects/P{i:09d}" for i in range(45)]
        self.collections = [path + "/C000000001" for path in self.projects]
        self.metadata = [(path, attr, "value") for path in self.projects for attr in ("title", "responsibleCostCenter")]
        self.sizes = [(path, "dcat:byteSize_resc_10", "1000000000") for path in self.collections]
        self.assertEqual(len(self.listing_result()), 45)
        self.assertEqual(self.query.call_count, 1 + 3 * math.ceil(45 / 20) + 1)


if __name__ == "__main__":
    unittest.main()
