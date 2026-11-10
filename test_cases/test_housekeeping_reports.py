"""Live report storage/retention checks; run sequentially as rods on icat."""

import json
import os
import subprocess
import time
import uuid

import pytest


def command(*args, env=None):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=env).strip()


def rule(name, *args, env=None):
    expression = f"test_rule_output({json.dumps(name)}, {json.dumps(','.join(map(str, args)))})"
    return json.loads(command(
        "irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance",
        expression, "null", "ruleExecOut", env=env,
    ))


def test_initialize_housekeeping_rejects_non_rods_user():
    environment = dict(os.environ, clientUserName="jmelius")
    with pytest.raises(subprocess.CalledProcessError):
        rule("initialize_housekeeping", "", "", env=environment)


def test_cleanup_housekeeping_reports_rejects_non_rods_user():
    environment = dict(os.environ, clientUserName="jmelius")
    with pytest.raises(subprocess.CalledProcessError):
        rule("cleanup_housekeeping_reports", "false", env=environment)


def test_housekeeping_storage_and_retention(tmp_path):
    config = rule("initialize_housekeeping", "", "")
    preview = rule("cleanup_housekeeping_reports", "true")
    if preview["eligible"]:
        pytest.skip("Existing expired reports must be collected/cleaned before this destructive integration test")
    base = config["report_collection"]
    runs = config["runs_collection"]
    root_acl = command("ils", "-A", base)
    assert "rods#nlmumc:own" in root_acl
    assert "Inheritance - Disabled" in root_acl
    assert "public#" not in root_acl

    prefix = "test-" + uuid.uuid4().hex
    paths = []
    local = tmp_path / "summary.json"
    local.write_text('{"test": true}\n')
    now = int(time.time())
    expired = now - (config["report_retention_days"] + 1) * 86400
    try:
        for name, state, finished in (
            ("expired", "completed", expired),
            ("running", "running", expired),
            ("missing-finishedAt", "completed", None),
            ("recent", "completed", now),
            ("ambiguous", "completed", expired),
        ):
            path = runs + "/" + prefix + "-" + name
            paths.append(path)
            command("imkdir", path)
            command("iput", "-R", config["report_resource"], str(local), path + "/summary.json")
            command("imeta", "set", "-C", path, "state", state)
            if finished is not None:
                command("imeta", "set", "-C", path, "finishedAt", str(finished))
            if name == "ambiguous":
                # Same attribute/value with different units must also be ambiguous.
                command("imeta", "add", "-C", path, "finishedAt", str(finished), "seconds")
            replicas = command("ils", "-L", path)
            assert config["report_resource"] in replicas
            assert "rootResc;" not in replicas

        preview = rule("cleanup_housekeeping_reports", "true")
        assert preview["eligible"] == [paths[0]]
        assert preview["deleted"] == []
        command("ils", paths[0])

        result = rule("cleanup_housekeeping_reports", "false")
        assert result["deleted"] == [paths[0]]
        assert result["errors"] == []
        with pytest.raises(subprocess.CalledProcessError):
            command("ils", paths[0])
        paths.pop(0)
        for path in paths:
            command("ils", path + "/summary.json")
        assert rule("initialize_housekeeping", "", "") == config
    finally:
        for path in paths:
            command("irm", "-rf", path)
