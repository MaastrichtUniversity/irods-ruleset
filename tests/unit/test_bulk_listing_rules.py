import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
ATTRIBUTES = ("title", "resource", "collectionMetadataSchemas")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BulkRuleTestCase(unittest.TestCase):
    def load_rule(self, path, name):
        self.query = Mock(side_effect=self.rows)
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        self.callback.get_user_id.return_value = {"arguments": [None, "10"]}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        modules = {
            "datahubirodsruleset": ModuleType("datahubirodsruleset"),
            "datahubirodsruleset.decorator": load("bulk_decorator", ROOT / "decorator.py"),
            "datahubirodsruleset.utils": SimpleNamespace(TRUE_AS_STRING="true", FALSE_AS_STRING="false"),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(
                get_project_id_from_project_path=lambda path: path.rsplit("/", 1)[1],
                format_string_to_boolean=lambda value: value == "true",
            )),
            "dhpythonirodsutils.enums": SimpleNamespace(ProjectAVUs=SimpleNamespace(
                TITLE=SimpleNamespace(value=ATTRIBUTES[0]), RESOURCE=SimpleNamespace(value=ATTRIBUTES[1]),
                COLLECTION_METADATA_SCHEMAS=SimpleNamespace(value=ATTRIBUTES[2]),
            )),
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
        }
        with patch.dict(sys.modules, modules):
            module = load("bulk_" + name, ROOT / path)
        self.function = getattr(module, name)

    def invoke(self, *inputs):
        args = list(inputs) + [""]
        self.function(args, self.callback, None)
        return json.loads(args[-1])

    def batch_ids(self, condition):
        match = re.search(r"(?:COLL_ID|USER_ID) in \(([^)]+)\)", condition)
        self.assertIsNotNone(match)
        ids = re.findall(r"'([0-9]+)'", match[1])
        self.assertLessEqual(len(ids), 20)
        self.assertLess(len(condition), 1024)
        return ids


class ContributingProjectsTests(BulkRuleTestCase):
    def setUp(self):
        self.projects = [("500", "/nlmumc/projects/P000000002"), ("400", "/nlmumc/projects/P000000003")]
        self.groups = [("10",), ("20",)]
        self.metadata = [(identifier, attribute, value) for identifier, path in self.projects
                         for attribute, value in zip(ATTRIBUTES, ("Project's title", "disk", "general"))]
        self.acls = [("500", identifier, access) for identifier, access in (
            ("10", "own"), ("20", "modify_object"), ("30", "read_object"), ("40", "read_object"),
            ("50", "own"), ("60", "modify_object"), ("70", "modify_object"), ("80", "read_object"),
        )] + [("400", "10", "own"), ("400", "20", "modify_object")]
        self.accounts = [
            ("10", "alice", "rodsuser"), ("20", "team", "rodsgroup"), ("30", "bob", "rodsuser"),
            ("40", "service-sync", "rodsuser"), ("50", "rods", "rodsadmin"),
            ("60", "ann-service-person", "rodsuser"), ("70", "no-metadata", "rodsuser"),
            ("80", "no-metadata-group", "rodsgroup"),
        ]
        self.account_metadata = [("10", "displayName", "Alice"), ("20", "description", "Team description"),
                                 ("20", "displayName", "Team"), ("30", "displayName", "Bob")]
        self.load_rule("projects/list_contributing_projects.py", "list_contributing_projects")

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if columns == "USER_GROUP_ID":
            return self.groups
        if columns == "COLL_ID, order(COLL_NAME)":
            self.assertIn("COLL_ACCESS_NAME in ('own', 'modify_object')", condition)
            self.assertIn("COLL_ACCESS_USER_ID in ('10','20')", condition)
            return self.projects
        ids = self.batch_ids(condition)
        if columns == "COLL_ID, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            self.assertTrue(set(ids) <= {identifier for identifier, _ in self.projects})
            self.assertNotIn("COLL_ACCESS", columns)
            return [row for row in self.metadata if row[0] in ids]
        if columns == "COLL_ID, COLL_ACCESS_USER_ID, COLL_ACCESS_NAME":
            self.assertTrue(set(ids) <= {identifier for identifier, _ in self.projects})
            return [row for row in self.acls if row[0] in ids]
        if columns == "USER_ID, USER_NAME, USER_TYPE":
            return [row for row in self.accounts if row[0] in ids]
        if columns == "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE":
            return [row for row in self.account_metadata if row[0] in ids]
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def test_preserves_full_roles_defaults_and_excludes_read_only_projects(self):
        # This unselected project must never enter a metadata or ACL query.
        self.metadata.append(("999", "title", "Read only"))
        self.acls.append(("999", "10", "read_object"))
        result = self.invoke("false")
        self.assertEqual([project["id"] for project in result], ["P000000002", "P000000003"])
        self.assertEqual(result[0], {
            "id": "P000000002", "title": "Project's title", "resource": "disk", "collectionMetadataSchemas": "general",
            "managers": {"users": ["alice"], "groups": [], "groupObjects": [],
                         "userObjects": [{"userName": "alice", "userId": "10", "displayName": "Alice"}]},
            "contributors": {"users": ["no-metadata"], "groups": ["team"],
                             "groupObjects": [{"groupName": "team", "groupId": "20", "displayName": "Team", "description": "Team description"}],
                             "userObjects": [{"userName": "no-metadata", "userId": "70", "displayName": "no-metadata"}]},
            "viewers": {"users": ["bob"], "groups": ["no-metadata-group"],
                        "groupObjects": [{"groupName": "no-metadata-group", "groupId": "80", "displayName": "no-metadata-group", "description": ""}],
                        "userObjects": [{"userName": "bob", "userId": "30", "displayName": "Bob"}]},
        })
        self.callback.list_project_managers.assert_not_called()
        self.callback.list_project_contributors.assert_not_called()
        self.callback.list_project_viewers.assert_not_called()
        self.callback.getCollectionAVU.assert_not_called()
        self.assertEqual(self.query.call_count, 6)

    def test_service_accounts_flag_keeps_existing_substring_filter_and_account_types(self):
        result = self.invoke("true")[0]
        self.assertEqual(result["viewers"]["users"], ["bob", "service-sync"])
        self.assertEqual(result["contributors"]["users"], ["ann-service-person", "no-metadata"])
        self.assertEqual(result["managers"]["users"], ["alice"])

    def test_missing_or_empty_required_metadata_still_fails(self):
        original = self.metadata[:]
        for attribute, empty in itertools.product(ATTRIBUTES, (False, True)):
            with self.subTest(attribute=attribute, empty=empty):
                self.metadata = [row for row in original if row[:2] != ("500", attribute)]
                if empty:
                    self.metadata.append(("500", attribute, ""))
                with self.assertRaisesRegex(RuntimeError, f"The attribute '{attribute}'.*has no value in iCAT"):
                    self.invoke("false")

    def test_last_metadata_values_are_used(self):
        self.metadata.append(("500", "title", "Updated title"))
        self.account_metadata.append(("20", "displayName", "Updated team"))
        project = self.invoke("false")[0]
        self.assertEqual(project["title"], "Updated title")
        self.assertEqual(project["contributors"]["groupObjects"][0]["displayName"], "Updated team")

    def test_no_projects_or_memberships_skip_detail_queries(self):
        self.projects = []
        self.assertEqual(self.invoke("false"), [])
        self.assertEqual(self.query.call_count, 2)
        self.query.reset_mock()
        self.groups = []
        self.assertEqual(self.invoke("false"), [])
        self.assertEqual(self.query.call_count, 1)

    def test_project_without_acl_entries_has_empty_roles(self):
        self.acls = []
        result = self.invoke("false")
        self.assertEqual(result[0]["viewers"], {"users": [], "groups": [], "groupObjects": [], "userObjects": []})
        self.assertEqual(self.query.call_count, 4)

    def test_thousand_projects_resolve_shared_accounts_once_in_bounded_batches(self):
        self.projects = [(str(9000000000000000000 + i), f"/nlmumc/projects/P{i:09d}") for i in range(1, 1001)]
        self.metadata = [(identifier, attribute, "value") for identifier, _ in self.projects for attribute in ATTRIBUTES]
        self.acls = [(identifier, "10", "own") for identifier, _ in self.projects]
        self.assertEqual(len(self.invoke("false")), 1000)
        self.assertEqual(self.query.call_count, 2 + 2 * math.ceil(1000 / 20) + 2)
        identity_queries = [call for call in self.query.call_args_list if call.args[0] == "USER_ID, USER_NAME, USER_TYPE"]
        self.assertEqual(len(identity_queries), 1)

    def test_many_distinct_accounts_also_use_bounded_batches(self):
        self.accounts = [(str(9000000000000000000 + i), f"user{i}", "rodsuser") for i in range(45)]
        self.acls = [("500", identifier, "own") for identifier, _, _ in self.accounts]
        self.account_metadata = []
        self.assertEqual(len(self.invoke("false")[0]["managers"]["users"]), 45)
        self.assertEqual(self.query.call_count, 2 + 2 + 2 * math.ceil(45 / 20))


class MembershipListingTests(BulkRuleTestCase):
    def setUp(self):
        self.users = [("10", "alice"), ("11", "service-sync"), ("12", "ann-service-person"), ("13", "lonely")]
        self.memberships = [("10", "alice", "10"), ("10", "DH-ingest", "90"),
                            ("10", "public", "91"), ("10", "rodsadmin", "92"),
                            ("10", "DH-project-admins", "93"), ("10", "team-a", "20"), ("10", "team-z", "21"),
                            ("11", "team-a", "20"), ("12", "team-z", "21"), ("13", "lonely", "13")]
        self.metadata = [("20", "description", "Description"), ("20", "displayName", "Team A")]
        self.load_rule("users/get_all_user_groups_membership.py", "get_all_users_groups_memberships")

    def rows(self, columns, condition, mode, callback):
        if columns == "USER_ID, USER_NAME":
            self.assertEqual(condition, "USER_TYPE = 'rodsuser'")
            return self.users
        if columns == "USER_ID, order(USER_GROUP_NAME), USER_GROUP_ID":
            return sorted(self.memberships, key=lambda row: row[1])
        if columns == "USER_ID, META_USER_ATTR_NAME, META_USER_ATTR_VALUE":
            self.assertIn("USER_TYPE = 'rodsgroup'", condition)
            self.assertIn("META_USER_ATTR_NAME in ('displayName','description')", condition)
            return self.metadata
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def test_all_flag_combinations_keep_users_groups_names_and_defaults(self):
        for service, special, username, extended in itertools.product(("false", "true"), repeat=4):
            with self.subTest(service=service, special=special, username=username, extended=extended):
                self.query.reset_mock()
                result = self.invoke(service, special, username, extended)
                expected_ids = {"10", "12", "13"} | ({"11"} if service == "true" else set())
                self.assertEqual(set(result), expected_ids)
                names = ["team-a", "team-z"]
                if special == "true":
                    names = ["DH-ingest", "DH-project-admins", "public", "rodsadmin"] + names
                self.assertEqual(result["10"]["group_names"], names)
                self.assertEqual(result["10"]["user_name"], "alice" if username == "true" else None)
                self.assertEqual(result["13"]["group_names"], [])
                self.assertEqual(result["12"]["groups"], [{
                    "groupId": "21", "name": "team-z", "displayName": "team-z", "description": "",
                }] if extended == "true" else [])
                if extended == "true":
                    self.assertEqual(result["10"]["groups"][-2], {
                        "groupId": "20", "name": "team-a", "displayName": "Team A", "description": "Description",
                    })
                else:
                    self.assertEqual(result["10"]["groups"], [])
                self.assertEqual(self.query.call_count, 3 if extended == "true" else 2)
        self.callback.get_users.assert_not_called()
        self.callback.get_user_group_memberships.assert_not_called()

    def test_empty_users_skip_membership_and_metadata_queries(self):
        self.users = []
        self.assertEqual(self.invoke("false", "false", "false", "true"), {})
        self.assertEqual(self.query.call_count, 1)

    def test_empty_and_duplicate_group_metadata_keep_last_value(self):
        self.metadata += [("20", "displayName", ""), ("20", "description", "Updated")]
        result = self.invoke("true", "false", "true", "true")
        self.assertEqual(result["10"]["groups"][0]["displayName"], "")
        self.assertEqual(result["11"]["groups"][0]["description"], "Updated")

    def test_thousand_users_with_shared_groups_still_use_three_queries(self):
        self.users = [(str(i), f"user{i}") for i in range(1000)]
        self.memberships = [(str(i), "team-a", "2000") for i in range(1000)]
        self.metadata = [("2000", "displayName", "Team A")]
        result = self.invoke("false", "false", "true", "true")
        self.assertEqual(len(result), 1000)
        self.assertEqual(result["999"]["groups"][0]["displayName"], "Team A")
        self.assertEqual(self.query.call_count, 3)


class ResourceUsageListingTests(BulkRuleTestCase):
    def setUp(self):
        self.paths = [("/nlmumc/projects/P000000001",), ("/nlmumc/projects/P000000002",)]
        self.names = [("disk", "10"), ("replica", "20"), ("unpriced", "30")]
        self.prices = [("disk", "12"), ("replica", "24")]
        self.sizes = [(self.paths[0][0] + "/C000000001", "dcat:byteSize_resc_10", "1500000000"),
                      (self.paths[1][0] + "/C000000002", "dcat:byteSize_resc_10", "2000000000"),
                      (self.paths[0][0] + "/C000000001", "dcat:byteSize_resc_20", "1500000000"),
                      (self.paths[1][0] + "/C000000002", "dcat:byteSize_resc_20", "2000000000")]
        self.load_rule("resources/get_resource_size_for_all_collections.py", "get_resource_size_for_all_collections")

    def rows(self, columns, condition, mode, callback):
        if columns == "COLL_NAME":
            return self.paths
        if columns == "RESC_NAME, RESC_ID":
            return self.names
        if columns == "RESC_NAME, META_RESC_ATTR_VALUE":
            self.assertEqual(condition, "META_RESC_ATTR_NAME = 'NCIT:C88193'")
            return self.prices
        if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            self.assertIn("COLL_NAME like '/nlmumc/projects/%/%'", condition)
            self.assertIn("META_COLL_ATTR_NAME like 'dcat:byteSize_resc%'", condition)
            return self.sizes
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def test_sums_across_projects_and_keeps_replica_sizes_and_rounding(self):
        self.assertEqual(self.invoke(), {
            "disk": {"size": 3500000000, "cost_per_year": 42.0, "cost_per_month": 3.5},
            "replica": {"size": 3500000000, "cost_per_year": 84.0, "cost_per_month": 7.0},
        })
        self.assertEqual(self.query.call_count, 4)
        self.callback.get_collection_size_per_resource.assert_not_called()
        self.callback.getResourceAVU.assert_not_called()

    def test_missing_or_empty_prices_default_to_zero(self):
        self.prices = [("disk", "")]
        result = self.invoke()
        self.assertEqual(result["disk"]["cost_per_year"], 0.0)
        self.assertEqual(result["replica"]["cost_per_month"], 0.0)

    def test_large_integer_zero_sizes_and_unknown_project_filter(self):
        self.sizes = [(self.paths[0][0] + "/C000000001/data", "dcat:byteSize_resc_10", str(2**53 + 1)),
                      (self.paths[0][0] + "/C000000002", "dcat:byteSize_resc_20", "0"),
                      ("/nlmumc/projects/P999999999/C000000001", "dcat:byteSize_resc_10", "999")]
        result = self.invoke()
        self.assertEqual(result["disk"]["size"], 2**53 + 1)
        self.assertEqual(result["replica"]["size"], 0)

    def test_no_projects_skips_remaining_queries(self):
        self.paths = []
        self.assertEqual(self.invoke(), {})
        self.assertEqual(self.query.call_count, 1)

    def test_thousand_projects_still_use_four_queries(self):
        self.paths = [(f"/nlmumc/projects/P{i:09d}",) for i in range(1000)]
        self.sizes = [(path + "/C000000001", "dcat:byteSize_resc_10", "1000000000") for path, in self.paths]
        self.assertEqual(self.invoke()["disk"]["size"], 1000000000000)
        self.assertEqual(self.query.call_count, 4)


if __name__ == "__main__":
    unittest.main()
