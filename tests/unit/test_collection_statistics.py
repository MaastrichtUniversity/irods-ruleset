import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"


class CollectionStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(return_value=[])
        modules = {
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(
                get_collection_id_from_project_collection_path=lambda path: path.split("/")[4])),
            "datahubirodsruleset.formatters": SimpleNamespace(format_project_path=lambda ctx, project: PROJECT),
        }
        for name in ("datahubirodsruleset", "datahubirodsruleset.collections"):
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.load("decorator.py")
        self.statistics = self.load("collections/calculate_collection_statistics.py")
        self.summary = self.load("collections/get_collection_size_per_resource.py")

    def load(self, relative):
        name = "datahubirodsruleset." + relative[:-3].replace("/", ".")
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    def calculate(self):
        args = [PROJECT + "/C000000001", ""]
        self.statistics.calculate_collection_statistics(args, Mock(), None)
        self.assertEqual(self.query.call_count, 1)
        self.assertEqual(self.query.call_args.args[0], "order(DATA_ID), DATA_SIZE, RESC_ID, RESC_PARENT")
        return dict(pair.split("=") for pair in args[1].split("%"))

    def test_replica_deduplication_globally_and_per_immediate_parent(self):
        self.query.return_value = iter([
            ("1", "100", "11", "10"), ("1", "100", "12", "10"),
            ("1", "100", "21", "20"), ("2", "0", "11", "10"),
            ("3", "7", "30", ""),
        ])
        self.assertEqual(self.calculate(), {
            "dcat:byteSize": "107", "numFiles": "3",
            "dcat:byteSize_resc_10": "100", "numFiles_resc_10": "2",
            "dcat:byteSize_resc_20": "100", "numFiles_resc_20": "1",
            "dcat:byteSize_resc_30": "7", "numFiles_resc_30": "1",
        })

    def test_differing_replica_sizes_preserve_distinct_native_size_projection(self):
        self.query.return_value = [("1", "100", "11", "10"), ("1", "90", "12", "10")]
        self.assertEqual(self.calculate(), {
            "dcat:byteSize": "190", "numFiles": "1",
            "dcat:byteSize_resc_10": "190", "numFiles_resc_10": "1",
        })

    def test_empty_collection_has_only_zero_totals(self):
        self.assertEqual(self.calculate(), {"dcat:byteSize": "0", "numFiles": "0"})

    def test_large_byte_counts_and_streamed_rows(self):
        self.query.return_value = ((str(index), str(2**40), "30", "") for index in range(600))
        self.assertEqual(self.calculate(), {
            "dcat:byteSize": str(600 * 2**40), "numFiles": "600",
            "dcat:byteSize_resc_30": str(600 * 2**40), "numFiles_resc_30": "600",
        })

    def test_resource_summary_filters_nested_metadata_and_preserves_output_types(self):
        root = PROJECT + "/C000000001"
        metadata = [(root, "dcat:byteSize_resc_10", "40"), (root, "dcat:byteSize", "100"),
                    (root, "dcat:byteSize_resc_20", "60"), (root, "dcat:byteSize_note", "ignored"),
                    (root + "/nested", "dcat:byteSize", "1"),
                    (root + "/nested", "dcat:byteSize_resc_10", "1")]

        def rows(columns, condition, mode, callback):
            if columns == "RESC_NAME, RESC_ID":
                return [("first", "10"), ("second", "20")]
            self.assertIn(f"COLL_PARENT_NAME = '{PROJECT}'", condition)
            children = [row for row in metadata if row[0].rsplit("/", 1)[0] == PROJECT]
            return children

        self.query.side_effect = rows
        args = ["P000000001", ""]
        self.summary.get_collection_size_per_resource(args, Mock(), None)
        self.assertEqual(json.loads(args[1]), {"C000000001": [
            {"resourceName": "first", "resourceId": "10", "size": "40", "relativeSize": 40.0},
            {"resourceName": "second", "resourceId": "20", "size": "60", "relativeSize": 60.0},
        ]})
        self.assertEqual(self.query.call_count, 2)


if __name__ == "__main__":
    unittest.main()
