"""Unit tests; run with pytest in the iRODS container (no server connection needed)."""
import importlib.util
import json
from pathlib import Path
from subprocess import CalledProcessError
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rule():
    # Load only this rule and the real decorator, without importing all server rules.
    root = Path(__file__).resolve().parents[1] / "datahubirodsruleset"
    decorator = load_module("unlock_decorator", root / "decorator.py")
    modules = {
        "datahubirodsruleset": ModuleType("datahubirodsruleset"),
        "datahubirodsruleset.decorator": decorator,
        "irods_types": SimpleNamespace(RodsObjStat=Mock()),
        "session_vars": SimpleNamespace(get_map=Mock(return_value={
            "client_user": {"user_name": "admin", "user_type": "rodsadmin"},
            "proxy_user": {"user_type": "rodsadmin"},
        })),
        "genquery": SimpleNamespace(row_iterator=Mock(return_value=[]), AS_LIST=1),
    }
    with patch.dict(sys.modules, modules):
        module = load_module("unlock_rule", root / "drop_zones/admin_unlock_direct_dropzone.py")
    module.check_call = Mock()
    callback = Mock()
    def exit_rule(code, message):
        raise RuntimeError(message)
    callback.msiExit.side_effect = exit_rule
    callback.getCollectionAVU.return_value = {"arguments": [None, None, "open"]}
    return module, callback


def invoke(rule, token="crazy-frog"):
    module, callback = rule
    args = [token, ""]
    module.admin_unlock_direct_dropzone(args, callback, None)
    return json.loads(args[1])


@pytest.mark.parametrize("client", [None, {}, {"user_type": "rodsuser"}, {"user_type": "groupadmin"}])
def test_reject_non_admin_even_with_admin_proxy(rule, client):
    module, callback = rule
    module.session_vars.get_map.return_value["client_user"] = client
    with pytest.raises(RuntimeError, match="Only rodsadmin"):
        invoke(rule)
    callback.msiObjStat.assert_not_called()
    module.check_call.assert_not_called()


@pytest.mark.parametrize("state", ["", "validating", "ingesting", "ingested", "error-sync", "warning"])
def test_reject_state(rule, state):
    module, callback = rule
    callback.getCollectionAVU.return_value["arguments"][2] = state
    with pytest.raises(RuntimeError, match="in state"):
        invoke(rule)
    module.row_iterator.assert_not_called()
    module.check_call.assert_not_called()


@pytest.mark.parametrize("state", ["open", "warning-validation-incorrect", "warning-unsupported-character"])
def test_allowed_empty_dropzone(rule, state):
    module, callback = rule
    callback.getCollectionAVU.return_value["arguments"][2] = state
    assert invoke(rule) == {"unlocked_replica_count": 0}
    module.check_call.assert_not_called()


@pytest.mark.parametrize("token", ["", "../crazy-frog", "/nlmumc/ingest/zones/crazy-frog", "crazy-frog/nested", "bad'quote", "crazy-frog\n"])
def test_invalid_token(rule, token):
    module, callback = rule
    with pytest.raises(Exception, match="Invalid dropzone token"):
        invoke(rule, token)
    callback.msiObjStat.assert_not_called()
    module.check_call.assert_not_called()


def test_missing_dropzone_or_state(rule):
    module, callback = rule
    callback.msiObjStat.side_effect = RuntimeError("not found")
    with pytest.raises(RuntimeError, match="not found"):
        invoke(rule)
    module.check_call.assert_not_called()
    callback.msiObjStat.side_effect = None
    callback.getCollectionAVU.side_effect = RuntimeError("missing state")
    with pytest.raises(RuntimeError, match="missing state"):
        invoke(rule)
    module.check_call.assert_not_called()


def test_recursive_replica_selection_and_literal_boundary(rule):
    module, callback = rule
    root = "/nlmumc/ingest/direct/crazy_frog-token"
    module.row_iterator.side_effect = [
        [[root, "file'quoted", "0"], [root, "file'quoted", "1"]],
        [[root + "/nested", "file", "0"], [root + "extra/nested", "sibling", "0"],
         [root.replace("_", "X") + "/nested", "wildcard", "0"]],
    ]
    assert invoke(rule, "crazy_frog-token") == {"unlocked_replica_count": 3}
    assert [call.args[0][3:6] for call in module.check_call.call_args_list] == [
        [root + "/file'quoted", "replica_number", "0"],
        [root + "/file'quoted", "replica_number", "1"],
        [root + "/nested/file", "replica_number", "0"],
    ]
    for call in module.check_call.call_args_list:
        assert call.args[0][-2:] == ["DATA_REPL_STATUS", "0"]
        assert call.kwargs == {"shell": False}
    assert callback.msiWriteRodsLog.call_count == 3
    assert {call[0] for call in callback.method_calls} == {"msiObjStat", "getCollectionAVU", "msiWriteRodsLog"}


def test_partial_failure_stops_and_reports_replica(rule):
    module, callback = rule
    root = "/nlmumc/ingest/direct/crazy-frog"
    module.row_iterator.side_effect = [[[root, "a", "0"], [root, "b", "1"], [root, "c", "0"]], []]
    module.check_call.side_effect = [None, CalledProcessError(1, "iadmin")]
    with pytest.raises(RuntimeError, match="/b' replica 1 after 1 successful updates"):
        invoke(rule)
    assert module.check_call.call_count == 2
    assert callback.msiWriteRodsLog.call_count == 1
