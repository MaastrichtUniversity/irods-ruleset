"""Live AVU audit and persisted-report checks; run sequentially as rods on icat."""

import json
import os
import subprocess

import pytest


PROJECT_AVUS = """
OBI:0000103 archiveDestinationResource authorizationPeriodEndDate collectionMetadataSchemas
dataRetentionPeriodEndDate dataSteward enableArchive enableContributorEditMetadata
enableDropzoneSharing enableUnarchive ingestResource latestProjectCollectionNumber
resource responsibleCostCenter storageQuotaGb title
""".split()
COLLECTION_AVUS = """
PID creator dcat:byteSize depositor latest_version_number numFiles schemaName schemaVersion title
""".split()


def command(*args, env=None):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=env).strip()


def check(checks="required_avus", env=None):
    return json.loads(command(
        "irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance",
        f'test_rule_output("run_housekeeping", {json.dumps(checks + ",sync")})', "null", "ruleExecOut", env=env,
    ))


def latest_project_number():
    return command("iquest", "%s", "select META_COLL_ATTR_VALUE where COLL_NAME = '/nlmumc/projects' "
                   "and META_COLL_ATTR_NAME = 'latest_project_number'")


def test_required_avus_rejects_non_rods_user():
    environment = dict(os.environ, clientUserName="jmelius")
    with pytest.raises(subprocess.CalledProcessError):
        check(env=environment)


def test_required_avus_and_report_storage():
    previous_number = latest_project_number()
    project_number = int(previous_number) + 1
    project = f"/nlmumc/projects/P{project_number:09d}"
    complete = project + "/C000000001"
    incomplete = project + "/C000000002"
    bare = project + "/C000000003"
    reports = []
    created = False
    try:
        command("imkdir", project)
        created = True
        for path in (complete, incomplete, bare, complete + "/nested"):
            command("imkdir", path)
        for attribute in PROJECT_AVUS:
            if attribute != "title":
                command("imeta", "set", "-C", project, attribute, "test")
        for path in (complete, incomplete):
            for attribute in COLLECTION_AVUS:
                if path != incomplete or attribute != "PID":
                    command("imeta", "set", "-C", path, attribute, "test")
            command("imeta", "set", "-C", path, "dcat:byteSize_resc_10", "0")
        command("imeta", "set", "-C", complete, "numFiles_resc_10", "0")
        before = command("imeta", "ls", "-C", project)

        result = check()
        reports.append(result["run_collection"])
        assert result["state"] == "completed"
        report_path = result["checks"]["required_avus"]["report_path"]
        report = json.loads(command("iget", report_path, "-"))
        findings = {finding["path"]: finding for finding in report["findings"]}
        assert findings[project]["missing_avus"] == ["title"]
        assert complete not in findings
        assert complete + "/nested" not in findings
        assert findings[incomplete]["missing_avus"] == ["PID", "numFiles_resc_10"]
        assert findings[incomplete]["missing_resource_avu_pair"] is True
        assert bare not in findings
        assert report["summary"]["project_collections_skipped_unfinished_ingest"] >= 1
        assert command("imeta", "ls", "-C", project) == before
        assert "passRescUM01" in command("ils", "-L", report_path)
        status = json.loads(command("iget", result["run_collection"] + "/status.json", "-"))
        assert status["state"] == "completed"

        command("imeta", "set", "-C", project, "title", "test")
        command("imeta", "set", "-C", incomplete, "PID", "test")
        command("imeta", "set", "-C", incomplete, "numFiles_resc_10", "0")
        command("irm", "-rf", bare)
        result = check()
        reports.append(result["run_collection"])
        report = json.loads(command("iget", result["checks"]["required_avus"]["report_path"], "-"))
        assert not any(finding["path"] == project or finding["path"].startswith(project + "/")
                       for finding in report["findings"])
    finally:
        for path in reports:
            command("irm", "-rf", path)
        if created:
            command("irm", "-rf", project)
            # Do not roll back the counter if another project was created meanwhile.
            if latest_project_number() == str(project_number):
                command("imeta", "set", "-C", "/nlmumc/projects", "latest_project_number", previous_number)


def test_controller_selected_checks_share_one_run():
    preview = json.loads(command(
        "irule", "-r", "irods_rule_engine_plugin-irods_rule_language-instance",
        'test_rule_output("cleanup_housekeeping_reports", "true")', "null", "ruleExecOut",
    ))
    if preview["eligible"]:
        pytest.skip("Existing expired reports must be cleaned before testing the cleanup selection")
    result = check("required_avus+cleanup_reports")
    try:
        assert result["state"] == "completed"
        assert list(result["checks"]) == ["required_avus", "cleanup_reports"]
        config = json.loads(command("iget", result["run_collection"] + "/config.json", "-"))
        assert config == {"checks": ["required_avus", "cleanup_reports"],
                          "report_resource": "passRescUM01", "execution_mode": "sync"}
        for name, entry in result["checks"].items():
            assert entry["report_path"] == result["run_collection"] + f"/checks/{name}.json"
            report = json.loads(command("iget", entry["report_path"], "-"))
            assert report["execution_status"] == "completed"
        cleanup = result["checks"]["cleanup_reports"]
        assert cleanup["summary"]["deleted"] == 0
        assert cleanup["summary"]["errors"] == 0
        assert "passRescUM01" in command("ils", "-L", cleanup["report_path"])
        summary = json.loads(command("iget", result["summary_path"], "-"))
        assert summary == result
    finally:
        command("irm", "-rf", result["run_collection"])
