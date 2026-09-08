"""Integration tests against the development tape and project resources.

Run as irods on icat with the workspace rules installed. Each case creates and
removes its own project, without requiring ingestion or external account setup.
"""
import json
import subprocess
import time

import pytest

from dhpythonirodsutils.enums import ArchiveState, ProcessAttribute, UnarchiveState


TAPE = "arcRescSURF01"
DISK = "passRescUM01"


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


@pytest.fixture(scope="module")
def payload(tmp_path_factory):
    path = tmp_path_factory.mktemp("tape-restart") / "payload"
    with path.open("wb") as data:
        data.truncate(262144001)  # Above the development tape's minimumFileSize.
    return path


@pytest.fixture
def project():
    # Allocate normally: creating a project directly also updates the global counter.
    result = command(
        "/rules/tests/run_test.sh", "-r", "create_new_project", "-a",
        f"ires-hnas-umResource,{DISK},TapeRestartTest,rods,rods,UM-30001234X,{{}}",
    )
    path = json.loads(result)["project_path"]
    try:
        collection = f"{path}/C000000001"
        command("imkdir", collection)
        for attribute, value in (
            ("enableArchive", "true"), ("enableUnarchive", "true"),
            ("resource", DISK), ("archiveDestinationResource", TAPE),
        ):
            command("imeta", "set", "-C", path, attribute, value)
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


@pytest.mark.parametrize("operation,single_file", [("archive", False), ("unarchive", False), ("unarchive", True)])
@pytest.mark.parametrize("status", ["0", "2", "3", "4"])
def test_restart_repairs_partial_transfer(project, payload, tmp_path, operation, single_file, status):
    source, destination = (DISK, TAPE) if operation == "archive" else (TAPE, DISK)
    file_path = f"{project}/interrupted"
    completed_path = f"{project}/completed"
    small = tmp_path / "small"
    small.write_text("already transferred")
    command("iput", "-K", "-R", source, str(payload), file_path)
    command("iput", "-K", "-R", destination, str(small), completed_path)
    completed_replicas = replicas(completed_path)
    command("ichmod", "-rM", "own", "service-surfarchive", project)
    command("env", "clientUserName=service-surfarchive", "irepl", "-R", destination, file_path)
    replica_number = next(number for number, _, hierarchy in replicas(file_path) if destination in hierarchy.split(";"))
    command("iadmin", "modrepl", "logical_path", file_path, "replica_number", replica_number, "DATA_REPL_STATUS", status)

    attribute = ProcessAttribute.ARCHIVE.value if operation == "archive" else ProcessAttribute.UNARCHIVE.value
    error = ArchiveState.ERROR_ARCHIVE_FAILED.value if operation == "archive" else UnarchiveState.ERROR_UNARCHIVE_FAILED.value
    command("imeta", "-M", "set", "-C", project, attribute, error)
    run_rule(f"restart_{operation}", file_path if single_file else project)

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        state = command(
            "iquest", "%s",
            f"SELECT META_COLL_ATTR_VALUE WHERE COLL_NAME = '{project}' AND META_COLL_ATTR_NAME = '{attribute}'",
        )
        assert "error-" not in state, state
        if not state or "CAT_NO_ROWS_FOUND" in state:
            break
        time.sleep(1)
    else:
        pytest.fail(f"Restart did not complete: {state}")

    remaining = replicas(file_path)
    assert remaining and all(value == "1" and destination in hierarchy.split(";") for _, value, hierarchy in remaining)
    assert replicas(completed_path) == completed_replicas
    command("env", "clientUserName=service-surfarchive", "iget", "-K", file_path, str(tmp_path / "restored"))
    assert (tmp_path / "restored").stat().st_size == payload.stat().st_size


def test_preparation_preserves_sources_good_replicas_and_scope(project, tmp_path):
    payload = tmp_path / "small"
    payload.write_text("replica cleanup scope")
    scope = f"{project}/scope"
    sibling = f"{scope}0"
    command("imkdir", sibling)
    command("imkdir", "-p", f"{scope}/nested")
    paths = [f"{scope}/good", f"{scope}/stale", f"{scope}/locked", f"{scope}/nested/locked", f"{sibling}/locked"]
    before = {}
    try:
        for path, status in zip(paths, ["1", "0", "2", "3", "4"]):
            command("iput", "-R", DISK, str(payload), path)
            command("irepl", "-R", TAPE, path)
            number = next(number for number, _, hierarchy in replicas(path) if hierarchy == TAPE)
            command("iadmin", "modrepl", "logical_path", path, "replica_number", number, "DATA_REPL_STATUS", status)
            before[path] = replicas(path)
        command("ichmod", "-rM", "own", "service-surfarchive", project)
        run_rule("prepare_tape_restart", paths[2], TAPE)
        assert next(status for _, status, hierarchy in replicas(paths[2]) if hierarchy == TAPE) == "0"
        assert replicas(paths[3]) == before[paths[3]]

        run_rule("prepare_tape_restart", scope, TAPE)
        for path in paths[:4]:
            after = replicas(path)
            assert [row for row in after if row[2] != TAPE] == [row for row in before[path] if row[2] != TAPE]
            assert next(status for _, status, hierarchy in after if hierarchy == TAPE) == ("1" if path == paths[0] else "0")
        assert replicas(paths[4]) == before[paths[4]]
    finally:
        # Unlock only replicas created by this test so fixture teardown can remove them.
        for path in before:
            for number, status, _ in replicas(path):
                if status in ("2", "3", "4"):
                    command("iadmin", "modrepl", "logical_path", path, "replica_number", number, "DATA_REPL_STATUS", "0")
