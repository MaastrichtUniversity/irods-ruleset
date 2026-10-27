"""Direct fixtures and helpers for development tape integration tests."""
import filecmp
import json
import subprocess
import time

import pytest
from dhpythonirodsutils.enums import ProcessState


COLLECTION_TITLE = "Tape test collection"
TAPE = "arcRescSURF01"
DISK = "passRescUM01"
REPLICATED_DISK = "replRescAZM02"


def command(*args):
    try:
        return subprocess.check_output(args, encoding="utf-8", stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as err:
        if args[0] == "iquest" and "CAT_NO_ROWS_FOUND" in err.output:
            return ""
        print(err.output)
        raise


def run_rule(name, *args):
    return command("/rules/tests/run_test.sh", "-r", name, "-a", ",".join(args), "-u", "service-surfarchive")


def replicas(path):
    collection, name = path.rsplit("/", 1)
    output = command(
        "iquest", "%s|%s|%s",
        f"SELECT DATA_REPL_NUM, DATA_REPL_STATUS, DATA_RESC_HIER WHERE COLL_NAME = '{collection}' AND DATA_NAME = '{name}'",
    )
    return [tuple(row.split("|")) for row in output.splitlines()]


def wait_for_operation(project, attribute, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = command(
            "iquest", "%s",
            f"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{project}' AND META_COLL_ATTR_NAME = '{attribute}'",
        )
        assert "error-" not in state, state
        if not state or "CAT_NO_ROWS_FOUND" in state:
            scope = command(
                "iquest", "%s",
                f"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{project}' AND META_COLL_ATTR_NAME = 'unArchivePath'",
            )
            if not scope or "CAT_NO_ROWS_FOUND" in scope:
                return
        time.sleep(1)
    pytest.fail(f"Tape operation did not complete: {state}")


@pytest.fixture(scope="module")
def payload(tmp_path_factory):
    path = tmp_path_factory.mktemp("tape") / "payload"
    with path.open("wb") as data:
        data.truncate(262144001)  # Above the development tape's minimumFileSize.
    return path


@pytest.fixture
def project(request):
    disk = getattr(request, "param", DISK)
    # Allocate normally: creating a project directly also updates the global counter.
    result = command(
        "/rules/tests/run_test.sh", "-r", "create_new_project", "-a",
        f"ires-hnas-umResource,{disk},TapeTest,rods,rods,UM-30001234X,{{}}",
    )
    path = json.loads(result)["project_path"]
    try:
        collection = f"{path}/C000000001"
        command("imkdir", collection)
        for attribute, value in (
            ("enableArchive", "true"), ("enableUnarchive", "true"),
            ("resource", disk), ("archiveDestinationResource", TAPE),
        ):
            command("imeta", "set", "-C", path, attribute, value)
        command("imeta", "set", "-C", collection, "title", COLLECTION_TITLE)
        command("ichmod", "-rM", "own", "service-surfarchive", collection)
        yield collection
    finally:
        command("ichmod", "-rM", "own", "rods", path)
        locked = command(
            "iquest", "%s|%s|%s",
            f"SELECT COLL_NAME, DATA_NAME, DATA_REPL_NUM WHERE COLL_NAME LIKE '{path}/%'"
            " AND DATA_REPL_STATUS in ('2', '3', '4')",
        )
        for row in locked.splitlines():
            collection, name, number = row.split("|")
            command("iadmin", "modrepl", "logical_path", f"{collection}/{name}",
                    "replica_number", number, "DATA_REPL_STATUS", "0")
        command("irm", "-rf", path)


def assert_active_process(collection):
    processes = json.loads(command(
        "/rules/tests/run_test.sh", "-r", "get_user_active_processes", "-a", "false,true,true",
    ))
    project_id, collection_id = collection.rsplit("/", 2)[1:]
    matches = [
        process for process in processes[ProcessState.IN_PROGRESS.value]
        if process["project_id"] == project_id and process["collection_id"] == collection_id
    ]
    assert len(matches) == 1, processes
    process = matches[0]
    assert process["repository"] == "SURFSara Tape"
    assert process["collection_title"] == COLLECTION_TITLE
    assert process["state"]


def assert_on_resource(path, resource):
    resource_id = command("iquest", "%s", f"SELECT RESC_ID WHERE RESC_NAME = '{resource}'")
    children = command("iquest", "%s", f"SELECT RESC_ID WHERE RESC_PARENT = '{resource_id}'")
    expected = len(children.splitlines()) or 1
    remaining = replicas(path)
    assert len(remaining) == expected, remaining
    assert all(status == "1" and resource in hierarchy.split(";") for _, status, hierarchy in remaining), remaining


def assert_restored(path, original, destination):
    command("env", "clientUserName=service-surfarchive", "iget", "-K", path, str(destination))
    assert filecmp.cmp(original, destination, shallow=False)
