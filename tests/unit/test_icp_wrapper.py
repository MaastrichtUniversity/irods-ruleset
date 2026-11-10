import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest
from dhpythonirodsutils import enums


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def copy_rule(monkeypatch):
    root = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
    decorator = load_module("icp_test_decorator", root / "decorator.py")
    modules = {
        "irods_types": ModuleType("irods_types"),
        "session_vars": ModuleType("session_vars"),
        "genquery": ModuleType("genquery"),
        "dhpythonirodsutils": SimpleNamespace(formatters=Mock(), loggers=Mock()),
        "dhpythonirodsutils.enums": enums,
        "datahubirodsruleset": ModuleType("datahubirodsruleset"),
        "datahubirodsruleset.decorator": decorator,
        "datahubirodsruleset.formatters": SimpleNamespace(
            format_project_path=lambda ctx, project: "/nlmumc/projects/" + project,
        ),
    }
    with patch.dict(sys.modules, modules):
        module = load_module("icp_test_utils", root / "utils.py")
    command = Mock()
    monkeypatch.setattr(module, "check_call", command)
    ctx = SimpleNamespace(callback=Mock())
    ctx.callback.getCollectionAVU.return_value = {"arguments": [None, None, "testResource"]}
    return module.icp_wrapper, ctx, command


def test_disabled_transfer_threading_copies_without_worker_threads(copy_rule):
    copy, ctx, command = copy_rule

    copy(ctx, "source", "destination", "P000000001", False, transfer_threading=False)

    ctx.callback.msiDataObjCopy.assert_called_once_with(
        "source", "destination", "destRescName=testResource++++numThreads=-1", 0,
    )
    command.assert_not_called()


def test_default_allows_server_configured_transfer_threads(copy_rule):
    copy, ctx, command = copy_rule

    copy(ctx, "source", "destination", "P000000001", False)

    ctx.callback.msiDataObjCopy.assert_called_once_with(
        "source", "destination", "destRescName=testResource++++numThreads=0", 0,
    )
    command.assert_not_called()


@pytest.mark.parametrize("transfer_threading,expected_command", [
    (True, ["icp", "-f", "-R", "testResource", "source", "destination"]),
    (False, ["icp", "-f", "-R", "testResource", "-N", "0", "source", "destination"]),
])
def test_overwrites_keep_icp_and_respect_transfer_threading(copy_rule, transfer_threading, expected_command):
    copy, ctx, command = copy_rule

    copy(ctx, "source", "destination", "P000000001", True, transfer_threading=transfer_threading)

    assert command.call_args_list == [
        call(["ichmod", "-M", "own", "rods", "source"], shell=False),
        call(expected_command, shell=False),
    ]
    ctx.callback.msiDataObjCopy.assert_not_called()
