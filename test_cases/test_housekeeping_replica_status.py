"""Live replica audit fixtures; run sequentially as rods on development icat."""

import json
from types import SimpleNamespace
import uuid

import pytest

from dhpythonirodsutils.enums import ArchiveState, ProcessAttribute, ReplicaStatus, UnarchiveState

from test_cases.test_housekeeping_avus import COLLECTION_AVUS, PROJECT_AVUS, check, command, latest_project_number


@pytest.fixture(scope="module")
def replica_collection(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("housekeeping-replicas")
    previous_number = latest_project_number()
    project_number = int(previous_number) + 1
    project = f"/nlmumc/projects/P{project_number:09d}"
    complete = project + "/C000000001"
    unfinished = project + "/C000000002"
    tape = project + "/C000000003"
    source = tmp_path / "payload"
    source.write_text("housekeeping replica audit\n")
    root_file = "/nlmumc/projects/housekeeping-" + uuid.uuid4().hex
    reports = []
    modified = []
    created = False
    root_created = False

    def put(path):
        command("iput", "-R", "passRescUM01", str(source), path)

    def mark_bad(path, status):
        collection, name = path.rsplit("/", 1)
        row = command("iquest", "%s|%s", "SELECT DATA_REPL_NUM, DATA_RESC_NAME "
                      f"WHERE COLL_NAME = '{collection}' AND DATA_NAME = '{name}' AND DATA_REPL_NUM = '0'")
        replica, resource = row.split("|")
        modified.append((path, replica))
        command("iadmin", "modrepl", "logical_path", path, "replica_number", replica, "DATA_REPL_STATUS", status)
        return {"path": path, "project_collection": complete if path.startswith(complete + "/") else None,
                "replica_number": replica, "replica_status": status, "resource": resource}

    def audit(checks="replica_status"):
        result = check(checks)
        reports.append(result["run_collection"])
        assert result["state"] == "completed"
        entry = result["checks"]["replica_status"]
        assert entry["report_path"] == result["run_collection"] + "/checks/replica_status.json"
        report = json.loads(command("iget", entry["report_path"], "-"))
        return result, report

    try:
        command("imkdir", project)
        created = True
        for path in (complete, unfinished, tape, complete + "/nested", complete + "/.metadata_versions"):
            command("imkdir", path)
        for attribute in PROJECT_AVUS:
            value = "passRescUM01" if attribute == "resource" else "test"
            command("imeta", "set", "-C", project, attribute, value)
        for attribute in COLLECTION_AVUS:
            command("imeta", "set", "-C", complete, attribute, "test")
        for attribute in ("dcat:byteSize_resc_10", "numFiles_resc_10"):
            command("imeta", "set", "-C", complete, attribute, "0")
        for path in (unfinished, tape):
            command("imeta", "set", "-C", path, "title", "Unfinished ingest")

        expected = []
        for index, status in enumerate((ReplicaStatus.STALE.value, ReplicaStatus.INTERMEDIATE.value,
                                       ReplicaStatus.READ_LOCKED.value, ReplicaStatus.WRITE_LOCKED.value)):
            parent = (complete, complete + "/nested", complete + "/.metadata_versions", complete)[index]
            path = f"{parent}/file-{status}"
            put(path)
            if index == 0:
                # A remaining good replica must not hide the bad one.
                command("irepl", "-R", "rootResc", path)
            expected.append(mark_bad(path, status))
        put(complete + "/good")
        put(unfinished + "/file")
        mark_bad(unfinished + "/file", ReplicaStatus.STALE.value)
        put(tape + "/file")
        mark_bad(tape + "/file", ReplicaStatus.STALE.value)
        put(root_file)
        root_created = True
        expected.append(mark_bad(root_file, ReplicaStatus.STALE.value))
        yield SimpleNamespace(project=project, complete=complete, unfinished=unfinished, tape=tape,
                              root_file=root_file, expected=expected, audit=audit)
    finally:
        # Restore all test replicas, including locked/intermediate ones, before removing fixtures.
        for path, replica in modified:
            command("iadmin", "modrepl", "logical_path", path, "replica_number", replica,
                    "DATA_REPL_STATUS", ReplicaStatus.GOOD.value)
        for path in reports:
            command("irm", "-rf", path)
        if root_created:
            command("irm", "-f", root_file)
        if created:
            command("irm", "-rf", project)
            if latest_project_number() == str(project_number):
                command("imeta", "set", "-C", "/nlmumc/projects", "latest_project_number", previous_number)


def test_non_good_replicas_are_reported(replica_collection):
    fixture = replica_collection
    before = command("imeta", "ls", "-C", fixture.complete)
    _, report = fixture.audit()
    owned = [finding for finding in report["findings"]
             if finding["path"].startswith(fixture.project + "/") or finding["path"] == fixture.root_file]
    assert sorted(owned, key=lambda entry: entry["path"]) == sorted(fixture.expected, key=lambda entry: entry["path"])
    assert command("imeta", "ls", "-C", fixture.complete) == before


def test_unfinished_ingests_are_excluded_from_both_audits(replica_collection):
    fixture = replica_collection
    result, report = fixture.audit("required_avus+replica_status")
    assert not any(finding["path"].startswith((fixture.unfinished + "/", fixture.tape + "/"))
                   for finding in report["findings"])
    assert report["summary"]["replicas_skipped_unfinished_ingest"] >= 2
    avus = json.loads(command("iget", result["checks"]["required_avus"]["report_path"], "-"))
    assert not any(finding["path"].startswith(fixture.project + "/") or finding["path"] == fixture.project
                   for finding in avus["findings"])
    assert avus["summary"]["project_collections_skipped_unfinished_ingest"] >= 2


@pytest.mark.parametrize("attribute,state", [
    pytest.param(attribute, state, id=f"{attribute}-{state.name.lower()}")
    for attribute, states in ((ProcessAttribute.ARCHIVE.value, ArchiveState),
                              (ProcessAttribute.UNARCHIVE.value, UnarchiveState))
    for state in states
])
def test_tape_operation_excludes_collection(replica_collection, attribute, state):
    tape = replica_collection.tape
    # Completion metadata ensures the tape AVU alone causes the exclusion.
    command("imeta", "set", "-C", tape, "creator", "test")
    value = state.value.format(1, 2)
    try:
        command("imeta", "set", "-C", tape, attribute, value)
        try:
            _, report = replica_collection.audit()
            assert not any(finding["path"].startswith(tape + "/") for finding in report["findings"])
            assert report["summary"]["replicas_skipped_tape_operation"] >= 1
        finally:
            command("imeta", "rm", "-C", tape, attribute, value)
    finally:
        command("imeta", "rm", "-C", tape, "creator", "test")


def test_completion_attribute_makes_collection_eligible_for_both_audits(replica_collection):
    unfinished = replica_collection.unfinished
    command("imeta", "set", "-C", unfinished, "creator", "test")
    try:
        result, report = replica_collection.audit("required_avus+replica_status")
        assert any(finding["path"] == unfinished + "/file" for finding in report["findings"])
        avus = json.loads(command("iget", result["checks"]["required_avus"]["report_path"], "-"))
        assert any(finding["path"] == unfinished and "PID" in finding["missing_avus"] for finding in avus["findings"])
    finally:
        command("imeta", "rm", "-C", unfinished, "creator", "test")
