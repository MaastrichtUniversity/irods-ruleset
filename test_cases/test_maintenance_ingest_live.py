"""Small live maintenance tests; all payloads are 1 KiB.

Run from docker-dev via the usual iCAT test runner:
    ./rit.sh test irods test_maintenance_ingest_live.py -s

Requires the normal ingest test services and current ruleset. Run serially:
these cases temporarily replace zone-wide maintenance AVUs. Large size tiers
remain mocked in test_maintenance_ingest.py.
"""

from contextlib import ExitStack
import os
import re
import subprocess
import time
from types import SimpleNamespace

import pytest


MAINTENANCE = "/nlmumc/ingest/zones"
ATTRIBUTES = ("maintenanceStart", "maintenanceEnd")
HOUR = 3600


def command(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if check and result.returncode:
        pytest.fail(f"{args!r} failed:\n{result.stdout}\n{result.stderr}")
    return result


def rule(name, *args):
    return command("/rules/tests/run_test.sh", "-r", name, "-a", ",".join(map(str, args)))


def mounted_payload(tmp_path, project_id, token, remove=False):
    """Manage the tiny file on its resource host while pytest runs on iCAT."""
    payload_path = f"/mnt/ingest/zones/{token}/maintenance-test.bin"
    remote_code = (
        "def main(rule_args, callback, rei):\n"
        "    from pathlib import Path\n"
        f"    payload = Path({payload_path!r})\n"
    )
    if remove:
        remote_code += (
            "    if payload.exists():\n"
            "        payload.unlink()\n"
            "    if payload.parent.exists() and not any(payload.parent.iterdir()):\n"
            "        payload.parent.rmdir()\n"
        )
    else:
        remote_code += "    payload.write_bytes(b'x' * 1024)\n"
    rule_file = tmp_path / "maintenance_payload.r"
    rule_file.write_text(
        "def main(rule_args, callback, rei):\n"
        f"    host = callback.get_dropzone_resource_host('mounted', {project_id!r}, '')['arguments'][2]\n"
        f"    callback.py_remote(host, '<INST_NAME>irods_rule_engine_plugin-python-instance</INST_NAME>', {remote_code!r}, '')\n"
        "INPUT null\nOUTPUT ruleExecOut\n"
    )
    command("irule", "-r", "irods_rule_engine_plugin-python-instance", "-F", str(rule_file))


def avu(path, attribute):
    # Read all metadata so an absent attribute is not a command error.
    output = command("imeta", "ls", "-C", path).stdout
    values = re.findall(
        rf"^attribute: {re.escape(attribute)}\nvalue: (.*)$", output, re.MULTILINE
    )
    assert len(values) <= 1, f"Multiple {attribute} values on {path}"
    return values[0] if values else None


def clear_window():
    for attribute in ATTRIBUTES:
        value = avu(MAINTENANCE, attribute)
        if value is not None:
            command("imeta", "rm", "-C", MAINTENANCE, attribute, value)


def set_window(start, end):
    rule("set_ingest_maintenance_window", start, end)
    assert avu(MAINTENANCE, ATTRIBUTES[0]) == str(start)
    assert avu(MAINTENANCE, ATTRIBUTES[1]) == str(end)
    print(f"Maintenance start={start}, end={end}", flush=True)


def queued(token):
    output = command("iqstat", "-a", "-l").stdout
    entries = []
    for match in re.finditer(r"(?ms)^[ \t]*id:\s*(\d+)\s*\n(.*?)(?=^[ \t]*id:|\Z)", output):
        if token in match[2]:
            entries.append((match[1], match[2]))
    assert token not in output or entries, f"Could not parse iqstat output for {token}: {output}"
    return entries


def wait_for_process(token, end):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        for rule_id, body in queued(token):
            if f"process_dropzone('{token}'" in body:
                execution = re.search(r"^[ \t]*time:\s*(\d+)", body, re.MULTILINE)
                assert execution, body
                assert end <= int(execution[1]) <= end + 5, body
                print(f"{token}: queued rule {rule_id} for {execution[1]}", flush=True)
                return rule_id
        time.sleep(1)
    pytest.fail(f"No deferred process_dropzone appeared for {token}")


def wait_for_state(path, expected, not_before=None):
    deadline = time.monotonic() + 300
    previous = None
    while time.monotonic() < deadline:
        state = avu(path, "state")
        if state != previous:
            print(f"{path}: {state}", flush=True)
            previous = state
        if not_before is not None and time.time() < not_before:
            assert avu(path, "destination") is None, "Ingestion started before maintenance ended"
        if state == expected:
            assert not_before is None or time.time() >= not_before
            return
        assert not state or not state.startswith(("error-", "warning-")), state
        time.sleep(1)
    pytest.fail(f"Timed out waiting for {expected}; last state was {previous}")


@pytest.fixture
def live(tmp_path):
    assert not os.environ.get("PYTEST_XDIST_WORKER"), "Run maintenance tests serially"
    from test_cases import utils

    saved = {name: avu(MAINTENANCE, name) for name in ATTRIBUTES}

    def restore_window():
        clear_window()
        for name, value in saved.items():
            if value is not None:
                command("imeta", "set", "-C", MAINTENANCE, name, value)

    with ExitStack() as cleanup:
        cleanup.callback(restore_window)
        clear_window()
        info = SimpleNamespace(
            project_title="MAINTENANCE_SMALL_TEST", depositor="jmelius",
            manager1="jmelius", manager2="opalmen", ingest_resource="ires-hnas-umResource",
            destination_resource="passRescUM01", budget_number="UM-30001234X",
            schema_name="DataHub_general_schema", schema_version="1.0.0",
            collection_title="maintenance_test",
        )
        project = utils.create_project(info)
        info.project_id = project["project_id"]
        cleanup.callback(utils.remove_project, project["project_path"])

        def make(kind="direct"):
            info.dropzone_type = kind
            token = utils.create_dropzone(info)
            path = f"/nlmumc/ingest/{'direct' if kind == 'direct' else 'zones'}/{token}"

            def remove():
                for rule_id, _ in queued(token):
                    command("iqdel", rule_id)
                assert not queued(token), f"Test rules still queued for {token}"
                if command("ils", path, check=False).returncode == 0:
                    utils.remove_dropzone(token, kind)
                if kind == "mounted":
                    mounted_payload(tmp_path, info.project_id, token, remove=True)

            cleanup.callback(remove)
            utils.add_metadata_files_to_dropzone(token, kind)
            if kind == "mounted":
                mounted_payload(tmp_path, info.project_id, token)
            else:
                source = tmp_path / "maintenance-test.bin"
                source.write_bytes(b"x" * 1024)
                command("iput", "-R", "stagingResc01", str(source), f"{path}/{source.name}")
                for name in ("instance.json", "schema.json"):
                    rule("set_acl", "default", "admin:own", info.depositor, f"{path}/{name}")
                rule("set_acl", "recursive", "admin:own", "rods", path)
            return token, path, kind

        def submit(zone):
            token, _, kind = zone
            started = time.monotonic()
            rule("start_ingest", info.depositor, token, kind)
            print(f"{token}: start_ingest returned after {time.monotonic() - started:.2f}s", flush=True)

        yield SimpleNamespace(make=make, submit=submit)


@pytest.mark.parametrize("kind", ["direct", "mounted"])
def test_small_ingest_waits_in_final_eight_hours(live, kind):
    zone = live.make(kind)
    token, path, _ = zone
    start = int(time.time()) + 8 * HOUR - 300
    end = start + HOUR
    set_window(start, end)
    live.submit(zone)
    rule_id = wait_for_process(token, end)
    assert avu(path, "state") == "in-queue-for-validation"
    assert 0 < int(avu(path, "totalSize")) < 100 * 1024 ** 3
    assert avu(path, "destination") is None
    # Updating the announcement must not change an already queued job.
    set_window(start, end + HOUR)
    assert wait_for_process(token, end) == rule_id


@pytest.mark.parametrize("window", ["absent", "before_lead", "expired"])
def test_small_ingest_runs_without_maintenance_wait(live, window):
    zone = live.make()
    now = int(time.time())
    if window == "before_lead":
        set_window(now + 24 * HOUR, now + 25 * HOUR)
    elif window == "expired":
        set_window(now - 2 * HOUR, now - HOUR)
    live.submit(zone)
    wait_for_state(zone[1], "ingested")


@pytest.mark.parametrize("change_metadata", [False, True], ids=["release", "revalidate"])
def test_short_window_release(live, change_metadata):
    zone = live.make()
    token, path, _ = zone
    end = int(time.time()) + 90
    set_window(int(time.time()) - 60, end)
    live.submit(zone)
    wait_for_process(token, end)
    assert avu(path, "destination") is None
    if change_metadata:
        # Invalidating the metadata after preflight proves validation runs again.
        assert command("ils", "/nlmumc/projects/P999999999", check=False).returncode != 0
        command("imeta", "set", "-C", path, "project", "P999999999")
        expected = "warning-validation-incorrect"
    else:
        expected = "ingested"
    wait_for_state(path, expected, not_before=end)
    if change_metadata:
        assert avu(path, "destination") is None
