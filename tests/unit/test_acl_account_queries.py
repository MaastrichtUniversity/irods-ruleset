import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"
COLLECTION = PROJECT + "/C000000001"
BACKUP = "/nlmumc/backup/projects/P000000001"


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ACLAccountQueryTests(unittest.TestCase):
    def setUp(self):
        self.entries = [("30", "read_object", ""), ("10", "own", ""), ("20", "modify_object", "")]
        self.identities = [("10", "alice", "rodsuser"), ("20", "team", "rodsgroup"), ("30", "rods", "rodsadmin")]
        self.file_entries = [("20",), ("10",)]
        self.query = Mock(side_effect=self.rows)
        self.callback = Mock()
        self.ctx = SimpleNamespace(callback=self.callback, delayExec=self.callback.delayExec)
        self.callback.get_project_process_activity.return_value = {"arguments": [None, '{"has_process_activity": false}']}
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        self.batch_acl = Mock()
        root = ModuleType("datahubirodsruleset")
        root.__path__ = []
        root.IRODS_BACKUP_ACL_BASE_PATH = "/nlmumc/backup"
        root.IRODS_ZONE_BASE_PATH = "/nlmumc"
        root.FALSE_AS_STRING = "false"
        root.map_access_name_to_access_level = lambda value: {"read_object": "read", "modify_object": "write"}.get(value, value)
        root.apply_batch_acl_operation = self.batch_acl
        root.get_elastic_search_connection = Mock()
        root.COLLECTION_METADATA_INDEX = "collections"
        root.apply_batch_collection_avu_operation = Mock()
        modules = {
            "datahubirodsruleset": root,
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "dhpythonirodsutils": SimpleNamespace(formatters=SimpleNamespace(
                get_project_id_from_project_path=lambda path: path.rsplit("/", 1)[1])),
            "dhpythonirodsutils.enums": SimpleNamespace(
                DataDeletionAttribute=SimpleNamespace(STATE=SimpleNamespace(value="deletionState")),
                DataDeletionState=SimpleNamespace(PENDING=SimpleNamespace(value="pending"), DELETED=SimpleNamespace(value="deleted"))),
            "datahubirodsruleset.formatters": SimpleNamespace(
                format_project_path=lambda ctx, project: "/nlmumc/projects/" + project,
                format_project_collection_path=lambda ctx, project, collection: "/nlmumc/projects/" + project + "/" + collection),
            "datahubirodsruleset.collections.get_project_collection_process_activity": SimpleNamespace(
                check_project_collection_process_activity=Mock(return_value=False)),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        load("datahubirodsruleset.decorator", "decorator.py")
        load("datahubirodsruleset.listing_queries", "listing_queries.py")
        self.close = load("close_collection", "projects/close_project_collection.py")
        self.revoke_collection = load("datahubirodsruleset.data_deletion.revoke_project_collection_user_access",
                                      "data_deletion/revoke_project_collection_user_access.py")
        self.restore_collection = load("datahubirodsruleset.data_deletion.restore_project_collection_user_access",
                                       "data_deletion/restore_project_collection_user_access.py")
        self.restore_project = load("datahubirodsruleset.data_deletion.restore_project_user_access",
                                    "data_deletion/restore_project_user_access.py")
        self.revoke_project = load("revoke_project", "data_deletion/revoke_project_user_access.py")

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        if columns == "USER_ID, USER_NAME, USER_TYPE":
            identifiers = re.findall(r"'([^']*)'", condition)
            self.assertLessEqual(len(identifiers), 20)
            self.assertLess(len(condition.encode()), 1024)
            return [row for row in reversed(self.identities) if row[0] in identifiers]
        if columns == "DATA_ACCESS_USER_ID":
            self.assertIn("DATA_NAME = 'instance.json'", condition)
            return self.file_entries
        if columns == "COLL_ACCESS_USER_ID":
            return [(row[0],) for row in self.entries]
        if columns == "COLL_ACCESS_USER_ID, COLL_ACCESS_NAME, COLL_ACCESS_TYPE":
            return self.entries
        if columns == "COLL_NAME":
            return []
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def close_collection(self):
        self.close.close_project_collection(["P000000001", "C000000001", ""], self.callback, None)

    def test_close_removes_individual_and_group_access_before_restoring_project_access(self):
        self.close_collection()
        self.assertEqual(self.callback.msiSetACL.call_args_list, [
            call("recursive", "admin:null", "team", COLLECTION),
            call("recursive", "admin:null", "alice", COLLECTION),
            call("recursive", "admin:read", "rods", COLLECTION),
            call("recursive", "admin:read", "alice", COLLECTION),
            call("recursive", "admin:read", "team", COLLECTION),
        ])
        self.assertEqual(self.query.call_count, 4)

    def test_close_reads_project_acl_after_revoking_collection_access(self):
        events = Mock()
        events.attach_mock(self.query, "query")
        events.attach_mock(self.callback.msiSetACL, "acl")
        self.close_collection()
        last_removal = max(i for i, event in enumerate(events.mock_calls)
                           if event[0] == "acl" and event.args[1] == "admin:null")
        project_query = next(i for i, event in enumerate(events.mock_calls)
                             if event[0] == "query" and event.args[0] == "COLL_ACCESS_USER_ID")
        self.assertGreater(project_query, last_removal)

    def test_close_skips_unresolved_ids_and_preserves_duplicate_entry_operations(self):
        self.file_entries = [("missing",), ("10",), ("10",)]
        self.entries = []
        self.close_collection()
        self.assertEqual(self.callback.msiSetACL.call_args_list,
                         [call("recursive", "admin:null", "alice", COLLECTION)] * 2)

    def test_empty_acls_do_not_query_accounts_or_write_permissions(self):
        self.entries = self.file_entries = []
        self.close_collection()
        self.assertEqual(self.query.call_count, 2)
        self.callback.msiSetACL.assert_not_called()

    def test_thousand_accounts_use_bounded_batches(self):
        self.identities = [(str(9000000000000000000 + i), f"user{i}", "rodsuser") for i in range(1000)]
        self.entries = [(identifier, "own", "") for identifier, _, _ in self.identities]
        self.file_entries = [(row[0],) for row in self.identities]
        self.close_collection()
        self.assertEqual(self.query.call_count, 102)
        self.assertEqual(self.callback.msiSetACL.call_count, 2000)

    def add_service_accounts(self):
        names = self.revoke_collection.SERVICE_ACCOUNT_ALLOW_LIST + ["service-other"]
        self.identities += [(str(100 + i), name, "rodsuser") for i, name in enumerate(names)]
        self.entries += [(str(100 + i), "own", "") for i in range(len(names))]

    def test_revoke_collection_preserves_admin_service_filters_groups_and_delayed_operations(self):
        self.add_service_accounts()
        self.revoke_collection.revoke_project_collection_user_acl(self.ctx, COLLECTION)
        expected_names = ["alice", "team", "service-other"]
        self.batch_acl.assert_called_once_with(self.ctx, COLLECTION,
                                              [{"entity_name": name, "acl": "null"} for name in expected_names])
        self.assertEqual(self.callback.delayExec.call_args.args[1], "".join(
            f"msiSetACL('recursive', 'admin:null', '{name}', '{COLLECTION}');" for name in expected_names))
        self.assertEqual(self.query.call_count, 2)

    def test_restore_collection_includes_admins_services_and_groups_in_acl_order(self):
        self.add_service_accounts()
        self.restore_collection.restore_project_collection_user_acl(self.ctx, PROJECT, COLLECTION)
        identities = {identifier: name for identifier, name, _ in self.identities}
        self.assertEqual(self.callback.msiSetACL.call_args_list,
                         [call("recursive", "admin:read", identities[row[0]], COLLECTION) for row in self.entries])
        self.assertEqual(self.query.call_count, 2)

    def test_restore_project_preserves_access_levels_and_skips_unresolved_ids(self):
        self.entries.append(("missing", "own", ""))
        self.restore_project.restore_project_user_acl(self.ctx, PROJECT, BACKUP)
        self.batch_acl.assert_called_once_with(self.ctx, PROJECT, [
            {"entity_name": "rods", "acl": "read"},
            {"entity_name": "alice", "acl": "own"},
            {"entity_name": "team", "acl": "write"},
        ])
        self.assertEqual(self.query.call_count, 2)

    def test_revoke_project_backs_up_all_accounts_and_only_revokes_eligible_accounts(self):
        self.add_service_accounts()
        self.revoke_project.revoke_project_user_access([PROJECT, "reason", "description"], self.callback, None)
        expected = []
        identities = {identifier: (name, kind) for identifier, name, kind in self.identities}
        for identifier, access, _ in self.entries:
            name, kind = identities[identifier]
            expected.append(call("default", {"read_object": "read", "modify_object": "write"}.get(access, access), name, BACKUP))
            if kind != "rodsadmin" and name not in self.revoke_collection.SERVICE_ACCOUNT_ALLOW_LIST:
                expected.append(call("default", "null", name, PROJECT))
        self.assertEqual(self.callback.msiSetACL.call_args_list, expected)
        self.callback.setCollectionAVU.assert_called_once_with(PROJECT, "deletionState", "pending")
        self.assertEqual(self.query.call_count, 3)

    def test_active_project_process_prevents_revoke_queries_and_writes(self):
        self.callback.get_project_process_activity.return_value = {"arguments": [None, json.dumps({"has_process_activity": True})]}
        with self.assertRaisesRegex(RuntimeError, "active proces"):
            self.revoke_project.revoke_project_user_access([PROJECT, "reason", "description"], self.callback, None)
        self.query.assert_not_called()
        self.callback.msiSetACL.assert_not_called()
        self.callback.msiCollCreate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
