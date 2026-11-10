"""Sequential live dropzone audit on UM/AZM; only UUID-prefixed fixtures are changed."""

import json
import os
from pathlib import PurePosixPath
import re
import subprocess
import time
import uuid

import pytest


def command(*args, env=None):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=env, timeout=60).strip()


def rule(name, arguments, env=None):
    return json.loads(command(
        "irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance",
        f"test_rule_output({json.dumps(name)}, {json.dumps(arguments)})", "null", "ruleExecOut", env=env,
    ))


def remote_directory(tmp_path, host, path, create):
    code = ("def main(rule_args, callback, rei):\n"
            "    from pathlib import Path\n"
            f"    path = Path({path!r})\n"
            # The development UM/AZM hosts can expose the same backing share.
            + ("    path.mkdir(exist_ok=True)\n" if create else "    if path.exists():\n        path.rmdir()\n"))
    source = tmp_path / "housekeeping_directory.r"
    source.write_text(
        "def main(rule_args, callback, rei):\n"
        f"    callback.py_remote({host!r}, '<INST_NAME>irods_rule_engine_plugin-python-instance</INST_NAME>', {code!r}, '')\n"
        "INPUT null\nOUTPUT ruleExecOut\n"
    )
    command("irule", "-r", "irods_rule_engine_plugin-python-instance", "-F", str(source))


def test_dropzone_consistency_rejects_non_rods_user():
    environment = dict(os.environ, clientUserName="jmelius")
    with pytest.raises(subprocess.CalledProcessError):
        rule("run_housekeeping", "dropzone_consistency,sync", env=environment)


def test_scan_dropzone_directories_rejects_non_rods_user():
    environment = dict(os.environ, clientUserName="jmelius")
    with pytest.raises(subprocess.CalledProcessError):
        rule("scan_dropzone_directories", "[]", env=environment)


def test_dropzone_consistency_both_directions_and_async_reporting(tmp_path):
    resources = {}
    for line in command("iquest", "%s|%s", "select RESC_NAME, RESC_LOC").splitlines():
        name, host = line.split("|", 1)
        resources[name] = host
    projects = {}
    for line in command(
        "iquest", "%s|%s", "select COLL_NAME, META_COLL_ATTR_VALUE where COLL_PARENT_NAME = '/nlmumc/projects' "
        "and META_COLL_ATTR_NAME = 'ingestResource'",
    ).splitlines():
        project, resource = line.split("|", 1)
        projects.setdefault(resources[resource], project)
    staging_host, vault = command(
        "iquest", "%s|%s", "select RESC_LOC, RESC_VAULT_PATH where META_RESC_ATTR_NAME = 'directIngestResc' "
        "and META_RESC_ATTR_VALUE = 'true'",
    ).split("|", 1)
    assert len(projects) >= 2, "This live test requires project references to both UM and AZM ingest hosts"
    hosts = sorted(projects)[:2]
    prefix = "hk-dropzone-" + uuid.uuid4().hex
    direct = prefix + "-direct"
    mounted = [prefix + "-mounted-" + str(index) for index in range(2)]
    orphan = prefix + "-orphan"
    direct_root = str(PurePosixPath(vault) / "ingest/direct")
    staging_root = str(PurePosixPath(vault) / "ingest/zones")
    disk, collections, reports = [], [], []

    def directory(host, root, token):
        path = root + "/" + token
        remote_directory(tmp_path, host, path, True)
        disk.append((host, path))
        return host, path

    def audit(mode="sync"):
        try:
            result = rule("run_housekeeping", "dropzone_consistency," + mode)
        except subprocess.CalledProcessError as error:
            # Sync failures still persist a run; include it in fixture cleanup.
            match = re.search(r"report: (/nlmumc/home/rods/housekeeping/runs/[^/\s]+)/summary.json", error.output)
            if match:
                reports.append(match[1])
            raise
        reports.append(result["run_collection"])
        if mode == "async":
            deadline = time.monotonic() + 45
            while result["state"] in ("queued", "running") and time.monotonic() < deadline:
                time.sleep(0.5)
                result = rule("get_housekeeping_status", result["run_id"])
        assert result["state"] == "completed", result
        report = json.loads(command("iget", result["checks"]["dropzone_consistency"]["report_path"], "-"))
        persisted = json.loads(command("iget", result["summary_path"], "-"))
        assert persisted == result
        assert report["execution_status"] == "completed"
        return report

    try:
        for token, parent, project in [(direct, "/nlmumc/ingest/direct", projects[hosts[0]])] + [
            (token, "/nlmumc/ingest/zones", projects[host]) for host, token in zip(hosts, mounted)
        ]:
            path = parent + "/" + token
            command("imkdir", path)
            collections.append(path)
            command("imeta", "set", "-C", path, "project", project.rsplit("/", 1)[1])
            command("imeta", "set", "-C", path, "state", "open")
        direct_directory = directory(staging_host, direct_root, direct)
        mounted_directories = []
        for host, token in zip(hosts, mounted):
            mounted_directories.append(directory(staging_host, staging_root, token))
            mounted_directories.append(directory(host, "/mnt/ingest/zones", token))
        for host, root in [(staging_host, direct_root), (staging_host, staging_root)] + [
            (host, "/mnt/ingest/zones") for host in hosts
        ]:
            directory(host, root, orphan)
        before = {path: command("imeta", "ls", "-C", path) for path in collections}

        report = audit()
        findings = [entry for entry in report["findings"] if entry["token"].startswith(prefix)]
        assert len(findings) == 4
        assert all(entry["kind"] == "missing_in_irods" and entry["token"] == orphan for entry in findings)

        # Remove the direct directory, both mounted locations on one host, and
        # only mounted data on the other host. The audit must report each path.
        for host, path in [direct_directory] + mounted_directories[:2] + mounted_directories[3:]:
            remote_directory(tmp_path, host, path, False)
        report = audit()
        missing = [entry for entry in report["findings"]
                   if entry["token"].startswith(prefix) and entry["kind"] == "missing_on_disk"]
        assert len(missing) == 4
        assert all(entry["catalog_empty"] is True and entry["state"] == "open" for entry in missing)
        assert {entry["location"] for entry in missing if entry["token"] == mounted[0]} == {
            "staging_zones", "mounted_data",
        }
        async_report = audit("async")
        assert async_report["findings"] == report["findings"]
        assert {path: command("imeta", "ls", "-C", path) for path in collections} == before
    finally:
        for host, path in reversed(disk):
            remote_directory(tmp_path, host, path, False)
        for path in reversed(collections):
            command("irm", "-rf", path)
        for path in reports:
            command("irm", "-rf", path)
