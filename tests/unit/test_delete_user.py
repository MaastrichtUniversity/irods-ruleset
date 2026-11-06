import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
PROJECT = "/nlmumc/projects/P000000001"


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DeleteUserTests(unittest.TestCase):
    def setUp(self):
        self.query = Mock(side_effect=self.rows)
        modules = {
            "genquery": SimpleNamespace(row_iterator=self.query, AS_LIST=object()),
            "datahubirodsruleset": ModuleType("datahubirodsruleset"),
            "datahubirodsruleset.decorator": load("delete_decorator", "decorator.py"),
            "datahubirodsruleset.utils": SimpleNamespace(FALSE_AS_STRING="false", TRUE_AS_STRING="true"),
        }
        with patch.dict(sys.modules, modules):
            self.check = load("check_deletable_rule", "users/check_user_is_deletable.py")
            self.delete = load("delete_user_rule", "users/delete_user.py")
        self.callback = Mock()
        self.callback.get_client_username.return_value = {"arguments": ["rods"]}
        self.callback.get_user_id.return_value = {"arguments": ["alice", "10"]}
        self.callback.get_user_attribute_value.return_value = {"arguments": [None, None, None, '{"value": "true"}']}
        self.callback.check_user_is_deletable.side_effect = self.check_callback
        self.callback.msiExit.side_effect = lambda code, message: (_ for _ in ()).throw(RuntimeError(message))
        self.metadata = []
        self.owners = [(PROJECT, "1"), (PROJECT, "10"), (PROJECT, "20")]
        self.dropzones = []

    def rows(self, columns, condition, mode, callback):
        self.assertIs(callback, self.callback)
        def project_rows(rows):
            if "COLL_PARENT_NAME = '/nlmumc/projects'" in condition:
                return [row for row in rows if row[0].rsplit("/", 1)[0] == "/nlmumc/projects"]
            return rows

        if columns == "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE":
            return project_rows(self.metadata)
        if columns == "COLL_NAME, COLL_ACCESS_USER_ID":
            return project_rows(self.owners)
        if columns == "COLL_ACCESS_USER_ID, COLL_NAME":
            return [(owner, path) for path, owner in project_rows(self.owners) if owner == "10"]
        if columns == "count(COLL_ACCESS_NAME)":
            path = condition.split("'")[1]
            return [(str(sum(1 for row in self.owners if row[0] == path)),)]
        if columns == "COLL_NAME, META_COLL_ATTR_VALUE":
            self.assertEqual(condition, "COLL_NAME like '/nlmumc/ingest/%/%' AND META_COLL_ATTR_NAME = 'creator' AND META_COLL_ATTR_VALUE = 'alice'")
            return self.dropzones
        self.fail(f"Unexpected query: {columns} WHERE {condition}")

    def check_callback(self, username, output):
        args = [username, output]
        self.check.check_user_is_deletable(args, self.callback, None)
        return {"arguments": args}

    def invoke_check(self):
        return json.loads(self.check_callback("alice", "")["arguments"][1])

    def invoke_delete(self):
        args = ["alice", ""]
        self.delete.delete_user(args, self.callback, None)
        return json.loads(args[1])

    def test_last_manager_is_blocked_and_other_projects_do_not_affect_count(self):
        self.owners = [(PROJECT, "1"), (PROJECT, "10"), (PROJECT + "-other", "20")]
        self.assertEqual(self.invoke_check(), {
            "is_deletable": False,
            "reasons": [f"alice is the only manager left for project '{PROJECT}'"],
        })

    def test_owner_count_threshold_and_target_membership_are_preserved(self):
        for ids, deletable in [([], True), (["10"], False), (["1", "10"], False),
                               (["1", "10", "20"], True), (["1", "20"], True)]:
            with self.subTest(ids=ids):
                self.owners = [(PROJECT, identifier) for identifier in ids]
                self.assertEqual(self.invoke_check()["is_deletable"], deletable)

    def test_nested_collection_ownership_and_metadata_are_not_project_roles(self):
        self.owners += [(PROJECT + "/C000000001/folder", "10")]
        self.metadata = [(PROJECT + "/C000000001", "dataSteward", "alice")]
        self.assertEqual(self.invoke_check(), {"is_deletable": True, "reasons": []})

    def test_all_deletion_blockers_are_reported(self):
        self.callback.get_user_attribute_value.return_value["arguments"][3] = '{"value": "false"}'
        self.metadata = [(PROJECT, "dataSteward", "alice"), (PROJECT, "OBI:0000103", "alice")]
        self.owners.pop()
        dropzone = "/nlmumc/ingest/direct/token"
        self.dropzones = [(dropzone, "alice")]
        self.assertEqual(self.invoke_check(), {
            "is_deletable": False,
            "reasons": [
                "This user does not have a pending deletion procedure",
                f"alice is the dataSteward for project {PROJECT}",
                f"alice is the OBI:0000103 for project {PROJECT}",
                f"alice is the only manager left for project '{PROJECT}'",
                f"alice has an open dropzone {dropzone}",
            ],
        })

    def test_missing_pending_deletion_flag_still_blocks_deletion(self):
        self.callback.get_user_attribute_value.return_value["arguments"][3] = '{"value": ""}'
        self.assertEqual(self.invoke_check(), {
            "is_deletable": False, "reasons": ["This user does not have a pending deletion procedure"],
        })

    def test_nonexistent_user_fails_before_project_queries(self):
        self.callback.get_user_id.return_value = {"arguments": ["alice", ""]}
        with self.assertRaisesRegex(RuntimeError, "Username alice does not exist"):
            self.invoke_check()
        self.query.assert_not_called()

    def test_thousand_projects_and_nested_folders_still_need_three_queries(self):
        self.owners = [(f"/nlmumc/projects/P{i:09d}", owner)
                       for i in range(1000) for owner in ("1", "10", "20")]
        self.owners += [(path + "/C000000001/folder", "10") for path, owner in self.owners[:]]
        self.assertEqual(self.invoke_check(), {"is_deletable": True, "reasons": []})
        self.assertEqual(self.query.call_count, 3)

    def test_delete_runs_rmuser_only_after_successful_checks(self):
        with patch("subprocess.check_call") as command:
            self.assertEqual(self.invoke_delete(), {"success": True, "deleted_user": "alice"})
        command.assert_called_once_with(["iadmin", "rmuser", "alice"], shell=False)
        self.assertEqual(self.query.call_count, 3)

    def test_failed_checks_never_run_rmuser(self):
        self.owners.pop()
        with patch("subprocess.check_call") as command:
            with self.assertRaisesRegex(RuntimeError, "not valid for deletion"):
                self.invoke_delete()
        command.assert_not_called()

    def test_non_rods_caller_never_checks_or_deletes_user(self):
        self.callback.get_client_username.return_value = {"arguments": ["alice"]}
        with patch("subprocess.check_call") as command:
            with self.assertRaisesRegex(RuntimeError, "only be called by RODS"):
                self.invoke_delete()
        self.callback.check_user_is_deletable.assert_not_called()
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
