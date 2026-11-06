from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_cases import conftest as suite_config
from test_cases import utils


def config(parallel=True):
    options = {"numprocesses": 2 if parallel else 0, "dist": "loadgroup"}
    return SimpleNamespace(getoption=lambda name, default=None: options.get(name, default))


def item(marked, class_name=None, ingest=False):
    marks = []
    return SimpleNamespace(
        nodeid=f"test_suite.py::{class_name}::test_one", cls=class_name,
        fixturenames=["ingest_scenario"] if ingest else [],
        get_closest_marker=lambda name: marked, add_marker=marks.append, marks=marks,
    )


def test_unmarked_tests_cannot_enter_parallel_execution():
    with pytest.raises(pytest.UsageError, match="Unmarked tests must run sequentially"):
        suite_config.pytest_collection_finish(SimpleNamespace(config=config(), items=[item(False)]))


def test_safety_check_applies_after_marker_deselection():
    safe = item(True, "TestSafe")
    unsafe = item(False, "TestUnsafe")
    items = [safe, unsafe]
    suite_config.pytest_collection_modifyitems(config(), items)
    items.remove(unsafe)
    suite_config.pytest_collection_finish(SimpleNamespace(config=config(), items=items))
    assert safe.marks[0].args == ("test_suite.py::TestSafe",)
    assert not unsafe.marks


@pytest.mark.parametrize("parallel,marked,ingest", [(False, False, False), (True, True, True)])
def test_sequential_classes_and_existing_ingest_groups_are_unchanged(parallel, marked, ingest):
    test = item(marked, "TestSuite", ingest)
    suite_config.pytest_collection_modifyitems(config(parallel), [test])
    suite_config.pytest_collection_finish(SimpleNamespace(config=config(parallel), items=[test]))
    assert not test.marks


def test_empty_parallel_phase_needs_no_scheduler_validation():
    suite_config.pytest_collection_finish(SimpleNamespace(config=config(), items=[]))


def test_setup_preparation_shares_worker_index_but_explicit_reindex_still_runs(monkeypatch):
    resets = []
    monkeypatch.setattr(utils.subprocess, "check_call", lambda *args, **kwargs: resets.append(True))
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw0")
    utils.prepare_project_collections_index()
    assert not resets
    utils.run_index_all_project_collections_metadata()
    assert len(resets) == 1
    monkeypatch.delenv("PYTEST_XDIST_WORKER")
    utils.prepare_project_collections_index()
    assert len(resets) == 2


def test_processes_have_separate_complete_metadata_caches():
    root = str(Path(__file__).resolve().parents[2])
    script = '''import json
from pathlib import Path
from types import SimpleNamespace
from test_cases import utils
utils.requests.get = lambda url: SimpleNamespace(text='{"complete": true}')
utils.get_instance()
utils.get_schema()
assert json.loads(Path(utils.TMP_INSTANCE_PATH).read_text()) == {"complete": True}
assert json.loads(Path(utils.TMP_SCHEMA_PATH).read_text()) == {"complete": True}
print(json.dumps([utils.TMP_INSTANCE_PATH, utils.TMP_SCHEMA_PATH]))
'''

    def download(_):
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                                env=dict(os.environ, PYTHONPATH=root), timeout=15)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = [path for pair in executor.map(download, range(2)) for path in pair]
    assert len(set(paths)) == 4
    assert all(not Path(path).exists() for path in paths)


@pytest.mark.parametrize("wait,rule", [
    (utils.wait_for_change_project_permissions_to_finish, "changeProjectPermission"),
    (utils.wait_for_revoke_project_collection_user_acl, "msiSetACL"),
])
def test_delayed_rule_waits_are_scoped_to_the_project(monkeypatch, wait, rule):
    commands = []

    def query(command, **kwargs):
        commands.append(command)
        raise subprocess.CalledProcessError(1, command, output="CAT_NO_ROWS_FOUND")

    monkeypatch.setattr(utils.subprocess, "check_output", query)
    wait("P000000123")
    assert len(commands) == 1
    if rule == "changeProjectPermission":
        assert commands[0][:2] == ["iquest", "%s"]
        assert "RULE_EXEC_NAME LIKE '%changeProjectPermission%'" in commands[0][2]
        assert "RULE_EXEC_CONTEXT LIKE '%P000000123%'" in commands[0][2]
    else:
        assert f"grep {rule} | grep 'P000000123'" in commands[0]


def test_permission_wait_polls_pending_rule_ids_and_reports_query_errors(monkeypatch):
    outputs = iter(["123", "456"])
    sleeps = []

    def query(command, **kwargs):
        try:
            return next(outputs)
        except StopIteration:
            raise subprocess.CalledProcessError(1, command, output="CAT_NO_ROWS_FOUND")

    monkeypatch.setattr(utils.subprocess, "check_output", query)
    monkeypatch.setattr(utils.time, "sleep", sleeps.append)
    utils.wait_for_change_project_permissions_to_finish("P000000123")
    assert sleeps == [3, 3]

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(2, command, output="Catalog unavailable")

    monkeypatch.setattr(utils.subprocess, "check_output", fail)
    with pytest.raises(subprocess.CalledProcessError):
        utils.wait_for_change_project_permissions_to_finish("P000000123")


def test_live_suite_selection_covers_all_tests_without_parallel_global_mutations():
    root = Path(__file__).resolve().parents[2]

    def collect(*options):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
             *options, "test_cases"],
            cwd=root, env=dict(os.environ, PYTHONPATH=str(root)),
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return {line for line in result.stdout.splitlines() if line.startswith("test_cases/")}

    all_tests = collect()
    parallel = collect("-n", "3", "--dist", "loadgroup", "-m", "parallel")
    sequential = collect("-m", "not parallel")
    assert parallel and sequential
    assert parallel.isdisjoint(sequential)
    assert parallel | sequential == all_tests
    for unsafe in ("TestValidateDropzone", "TestProjects", "TestPolicies", "TestDeleteProjectData",
                   "TestRevokeProjectUserAccess::", "TestTapeRetryUM", "test_tape_resource_down",
                   "test_re_index_all_project_collections_metadata", "test_stop_ingest.py"):
        assert not any(unsafe in node for node in parallel), unsafe
    assert any("TestRevokeProjectUserAccessWithActiveProcess" in node for node in parallel)
