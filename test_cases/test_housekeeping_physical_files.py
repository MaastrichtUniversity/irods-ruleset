"""Live physical-file audit; run sequentially as irods/rods on development icat."""

import json
from pathlib import Path
import re
import subprocess
import uuid

from test_cases.test_housekeeping_avus import check, command


def test_missing_physical_copy_is_reported_despite_a_surviving_copy(tmp_path):
    prefix = "hk-physical-" + uuid.uuid4().hex
    collection = "/nlmumc/projects/" + prefix
    path = collection + "/nested/.metadata_versions/some file"
    source = tmp_path / "payload"
    payload = "housekeeping physical-file audit"
    source.write_text(payload + "\n")
    resources, reports = [], []
    created = False
    physical = None
    backup = tmp_path / "missing-copy"

    def audit():
        try:
            result = check("physical_files")
        except subprocess.CalledProcessError as error:
            match = re.search(r"report: (/nlmumc/home/rods/housekeeping/runs/[^/\s]+)/summary.json", error.output)
            if match:
                reports.append(match[1])
            raise
        reports.append(result["run_collection"])
        assert result["state"] == "completed"
        entry = result["checks"]["physical_files"]
        assert entry["report_path"] == result["run_collection"] + "/checks/physical_files.json"
        report = json.loads(command("iget", entry["report_path"], "-"))
        assert report["execution_status"] == "completed"
        return report

    try:
        command("imkdir", "-p", collection + "/nested/.metadata_versions")
        created = True
        for index in range(2):
            resource = f"{prefix}-{index}"
            vault = tmp_path / f"vault-{index}"
            vault.mkdir()
            command("iadmin", "mkresc", resource, "unixfilesystem", f"icat.dh.local:{vault}")
            resources.append(resource)
        command("iput", "-R", resources[0], str(source), path)
        command("irepl", "-R", resources[1], path)
        physical = Path(command(
            "iquest", "%s", "select DATA_PATH where "
            f"COLL_NAME = '{collection}/nested/.metadata_versions' and DATA_NAME = 'some file' "
            f"and RESC_NAME = '{resources[0]}'",
        ))
        assert physical.is_relative_to(tmp_path / "vault-0")
        physical.rename(backup)
        assert command("iget", "-R", resources[1], path, "-") == payload

        report = audit()
        assert [entry for entry in report["findings"] if entry["path"] == path] == [
            {"path": path, "physical_path": str(physical), "host": "icat.dh.local"},
        ]
        assert report["summary"]["missing_physical_copies"] >= 1
        backup.rename(physical)
        assert not any(entry["path"] == path for entry in audit()["findings"])
    finally:
        # Always restore the physical copy before removing catalog fixtures.
        if backup.exists():
            backup.rename(physical)
        if created:
            command("irm", "-rf", collection)
        for resource in reversed(resources):
            command("iadmin", "rmresc", resource)
        for report in reports:
            command("irm", "-rf", report)
