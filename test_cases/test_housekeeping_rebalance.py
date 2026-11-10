"""Synchronous rebalance verification scoped to disposable replication resources."""

import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import uuid


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def test_rebalance_recreates_missing_replicas_on_each_resource(tmp_path, monkeypatch):
    prefix = "hk-rebalance-" + uuid.uuid4().hex
    collection = "/nlmumc/home/rods/" + prefix
    parents, leaves, links = [], [], []
    created_collection = False
    local = tmp_path / "payload.txt"
    local.write_text("rebalance test\n")
    try:
        command("imkdir", collection)
        created_collection = True
        for index in range(2):
            parent = f"{prefix}-{index}"
            command("iadmin", "mkresc", parent, "replication")
            parents.append(parent)
            for child_index in range(2):
                child = f"{parent}-leaf-{child_index}"
                vault = tmp_path / f"vault-{index}-{child_index}"
                vault.mkdir()
                command("iadmin", "mkresc", child, "unixfilesystem", f"icat.dh.local:{vault}")
                leaves.append(child)
                command("iadmin", "addchildtoresc", parent, child)
                links.append((parent, child))
            path = collection + f"/{index}.txt"
            command("iput", "-R", parent, str(local), path)
            assert command("ils", "-l", path).count(" & ") == 2
            command("itrim", "-N", "1", "-n", "1", path)
            assert command("ils", "-l", path).count(" & ") == 1

        # GenQuery is a server-only module. Supply its inventory from iquest,
        # restricting this test to its own resources; all rebalance commands run
        # normally against iRODS and recreate actual missing file replicas.
        inventory = command("iquest", "%s", "select RESC_NAME where RESC_TYPE_NAME = 'replication'").splitlines()
        resources = sorted(name for name in inventory if name.startswith(prefix))
        assert resources == parents
        monkeypatch.setitem(sys.modules, "genquery", SimpleNamespace(
            row_iterator=lambda *args: [(name,) for name in resources], AS_LIST=object(),
        ))
        source = Path(__file__).resolve().parents[1] / "datahubirodsruleset/housekeeping/rebalance_resources.py"
        spec = importlib.util.spec_from_file_location("live_housekeeping_rebalance", source)
        rule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rule)
        report = rule._rebalance_resources(SimpleNamespace(callback=None))
        assert report["execution_status"] == "completed"
        assert report["summary"] == {"resources_found": 2, "resources_rebalanced": 2, "resources_failed": 0}
        assert [entry["resource"] for entry in report["resources"]] == parents
        for index in range(2):
            assert command("ils", "-l", collection + f"/{index}.txt").count(" & ") == 2
    finally:
        if created_collection:
            command("irm", "-rf", collection)
        for parent, child in reversed(links):
            command("iadmin", "rmchildfromresc", parent, child)
        for resource in reversed(leaves + parents):
            command("iadmin", "rmresc", resource)
