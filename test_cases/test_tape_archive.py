"""Tape flows with directly seeded projects; no dropzones or ingestion required.

Run serially with the retry suite: resource availability checks modify shared
resource status temporarily.
"""
import subprocess

import pytest

from test_cases.tape_helpers import (
    TAPE, DISK, REPLICATED_DISK, command, run_rule, replicas,
    payload, project, wait_for_operation, assert_active_process,
    assert_on_resource, assert_restored,
)


@pytest.fixture(params=[DISK, REPLICATED_DISK, "replRescUMCeph01"])
def disk(request):
    return request.param


@pytest.fixture
def disk_project(project, disk):
    command("imeta", "set", "-C", project.rsplit("/", 1)[0], "resource", disk)
    return project


def start_and_wait(operation, collection, target):
    run_rule(f"start_{operation}", target, "rods")
    assert_active_process(collection)
    attribute = "archiveState" if operation == "archive" else "unArchiveState"
    wait_for_operation(collection, attribute)


def test_archive(disk_project, disk, payload, tmp_path):
    large = f"{disk_project}/large_file"
    small = f"{disk_project}/small_file"
    local = tmp_path / "small"
    local.write_text("Below the tape size threshold.")
    command("iput", "-K", "-R", disk, str(payload), large)
    command("iput", "-K", "-R", disk, str(local), small)
    small_before = replicas(small)

    start_and_wait("archive", disk_project, disk_project)

    assert_on_resource(large, TAPE)
    assert replicas(small) == small_before
    assert_on_resource(small, disk)


def test_unarchive_collection(disk_project, disk, tmp_path):
    local = tmp_path / "payload"
    local.write_text("Restore every file in the collection.")
    command("imkdir", f"{disk_project}/nested")
    paths = [f"{disk_project}/file", f"{disk_project}/nested/file"]
    for path in paths:
        command("iput", "-K", "-R", TAPE, str(local), path)

    start_and_wait("unarchive", disk_project, disk_project)

    for index, path in enumerate(paths):
        assert_on_resource(path, disk)
        assert_restored(path, local, tmp_path / f"restored-{index}")


def test_unarchive_file(disk_project, disk, tmp_path):
    local = tmp_path / "payload"
    local.write_text("Restore only the requested file.")
    target = f"{disk_project}/file"
    sibling = f"{disk_project}/sibling"
    for path in (target, sibling):
        command("iput", "-K", "-R", TAPE, str(local), path)
    sibling_before = replicas(sibling)

    start_and_wait("unarchive", disk_project, target)

    assert_on_resource(target, disk)
    assert replicas(sibling) == sibling_before
    assert_restored(target, local, tmp_path / "restored")


def assert_rejected(collection):
    for operation in ("archive", "unarchive"):
        with pytest.raises(subprocess.CalledProcessError):
            run_rule(f"start_{operation}", collection, "rods")


def test_tape_avu_permissions(project):
    path = project.rsplit("/", 1)[0]
    command("imeta", "set", "-C", path, "enableArchive", "false")
    command("imeta", "set", "-C", path, "enableUnarchive", "false")
    assert_rejected(project)


@pytest.mark.parametrize("attribute,state", [
    ("archiveState", "in-queue-for-archival"),
    ("unArchiveState", "in-queue-for-unarchival"),
])
def test_tape_running_process(project, attribute, state):
    command("imeta", "-M", "set", "-C", project, attribute, state)
    assert_rejected(project)


@pytest.mark.parametrize("resource", [TAPE, DISK, REPLICATED_DISK, "replRescUMCeph01"])
def test_tape_resource_down(project, resource):
    if resource != TAPE:
        command("imeta", "set", "-C", project.rsplit("/", 1)[0], "resource", resource)
    status = command("iquest", "%s", f"SELECT RESC_STATUS WHERE RESC_NAME = '{resource}'")
    try:
        command("iadmin", "modresc", resource, "status", "down")
        assert_rejected(project)
    finally:
        # Newly initialized resources have an empty status, which also means up.
        command("iadmin", "modresc", resource, "status", status or "up")


def test_unarchive_invalid_path():
    with pytest.raises(subprocess.CalledProcessError):
        run_rule("start_unarchive", "/nlmumc/home/rods", "rods")


@pytest.mark.parametrize("operation", ["archive", "unarchive"])
def test_without_service_account(project, operation):
    with pytest.raises(subprocess.CalledProcessError):
        command("/rules/tests/run_test.sh", "-r", f"start_{operation}", "-a", f"{project},rods", "-u", "rods")


def test_tape_with_non_existent_pc(project):
    assert_rejected(f"{project.rsplit('/', 1)[0]}/C000000002")
