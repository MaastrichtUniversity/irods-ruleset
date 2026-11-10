import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from test_cases.utils import create_project, remove_project


pytestmark = pytest.mark.parallel
ENGINE = "irods_rule_engine_plugin-irods_rule_language-instance"
RULES = Path(__file__).resolve().parents[1] / "native_irods_ruleset" / "misc"


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def metadata(path):
    result = command("iquest", "%s|%s", f"SELECT META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE WHERE COLL_NAME = '{path}'")
    return dict(line.split("|", 1) for line in result.splitlines())


def set_size(project, collection, installed):
    if installed:
        return command("irule", "-r", ENGINE,
                       f'setCollectionSize("{project}","{collection}","true","true")', "null", "ruleExecOut")
    return command("irule", "-r", ENGINE, "-F", str(RULES / "setCollectionSize.r"),
                   f"*project='{project}'", f"*projectCollection='{collection}'",
                   "*openPC='true'", "*closePC='true'")


@pytest.fixture(scope="module")
def statistics_objects(tmp_path_factory):
    created = create_project(SimpleNamespace(
        project_title="COLLECTION_STATISTICS_TEST", manager1="jmelius", manager2="opalmen",
        ingest_resource="ires-hnas-umResource", destination_resource="passRescUM01",
        budget_number="UM-30001234X",
    ))
    project = created["project_id"]
    path = created["project_path"]
    try:
        collection = path + "/C000000001"
        empty = path + "/C000000002"
        command("imkdir", collection)
        command("imkdir", empty)
        local = tmp_path_factory.mktemp("statistics")
        payload = local / "payload"
        payload.mkdir()
        # More than one GenQuery page, including an empty file.
        for index in range(270):
            (payload / f"file{index:03d}").write_bytes(b"x" * index)
        command("ireg", "-r", "-R", "demoResc", str(payload), collection + "/payload")
        for name in ("file001", "file002"):
            command("irepl", "-R", "replRescAZM02", collection + "/payload/" + name)
        orphan = local / "orphan"
        orphan.write_bytes(b"1234567")
        command("iput", "-R", "stagingResc01", str(orphan), collection + "/orphan")
        resources = {}
        for name in ("rootResc", "replRescAZM02", "stagingResc01"):
            resources[name] = command("iquest", "%s", f"SELECT RESC_ID WHERE RESC_NAME = '{name}'")
        yield project, collection, empty, resources
    finally:
        remove_project(path)


@pytest.mark.parametrize("installed", [False, True])
def test_set_collection_statistics_preserves_replica_totals_and_metadata(statistics_objects, installed):
    project, collection, _, resources = statistics_objects
    command("ichmod", "-M", "own", "rods", collection)
    original = metadata(collection)
    for attribute in ("dcat:byteSize_resc_999999999", "numFiles_resc_999999999", "unrelated"):
        command("imeta", "set", "-C", collection, attribute, "keep")
    set_size(project, "C000000001", installed)
    values = metadata(collection)
    expected = dict(original)
    expected.update({"dcat:byteSize": "36322", "numFiles": "271", "unrelated": "keep"})
    for resource, size, count in (("rootResc", "36315", "270"),
                                  ("replRescAZM02", "3", "2"), ("stagingResc01", "7", "1")):
        expected["dcat:byteSize_resc_" + resources[resource]] = size
        expected["numFiles_resc_" + resources[resource]] = count
    assert values == expected
    assert "rods#nlmumc:read" in command("ils", "-A", collection)
    # Opening/closing the collection must not change descendant permissions.
    assert "rods#nlmumc:own" in command("ils", "-A", collection + "/payload")


@pytest.mark.parametrize("installed", [False, True])
def test_empty_collection_removes_stale_resource_statistics(statistics_objects, installed):
    project, _, empty, _ = statistics_objects
    command("ichmod", "-M", "own", "rods", empty)
    command("imeta", "set", "-C", empty, "dcat:byteSize_resc_999999999", "10")
    command("imeta", "set", "-C", empty, "numFiles_resc_999999999", "1")
    set_size(project, "C000000002", installed)
    assert metadata(empty) == {"dcat:byteSize": "0", "numFiles": "0"}


def test_resource_summary_ignores_nested_size_avus(statistics_objects):
    project, collection, _, resources = statistics_objects
    set_size(project, "C000000001", True)
    resource = resources["rootResc"]
    command("imeta", "set", "-C", collection + "/payload", "dcat:byteSize", "1")
    command("imeta", "set", "-C", collection + "/payload", "dcat:byteSize_resc_" + resource, "1")
    result = json.loads(command("/rules/tests/run_test.sh", "-r", "get_collection_size_per_resource", "-a", project))
    assert list(result) == ["C000000001"]
    assert len(result["C000000001"]) == 3
    rows = {row["resourceName"]: row for row in result["C000000001"]}
    assert rows["rootResc"] == {
        "resourceName": "rootResc", "resourceId": resource, "size": "36315", "relativeSize": 100.0,
    }
