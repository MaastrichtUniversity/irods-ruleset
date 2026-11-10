# /rules/tests/run_test.sh -r run_housekeeping -a "dropzone_consistency,sync" -j
"""Compare catalog dropzones with directories on staging and project ingest hosts."""

import json
import os

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.housekeeping.storage import _require_rods
from datahubirodsruleset.listing_queries import collection_metadata, metadata_for_paths, query_value


PARENTS = {"direct": "/nlmumc/ingest/direct", "mounted": "/nlmumc/ingest/zones"}
MOUNTED_ROOT = "/mnt/ingest/zones"


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def scan_dropzone_directories(ctx, roots_json):
    """Internal rods-only remote worker; return one complete inventory per root."""
    _require_rods(ctx)
    inventories = []
    for root in json.loads(roots_json):
        try:
            with os.scandir(root) as entries:
                directories = sorted(entry.name for entry in entries if entry.is_dir())
        except OSError as error:
            inventories.append({"root": root, "execution_status": "failed", "error": str(error)})
        else:
            inventories.append({"root": root, "execution_status": "completed", "directories": directories})
    return inventories


def _catalog_dropzones(ctx):
    dropzones = {}
    for kind, parent in PARENTS.items():
        for path, in row_iterator(
            "COLL_NAME", "COLL_PARENT_NAME = " + query_value(parent), AS_LIST, ctx.callback,
        ):
            dropzones[path] = {"type": kind, "token": path.rsplit("/", 1)[1],
                               "logical_path": path, "catalog_empty": True}
    metadata = metadata_for_paths(ctx, dropzones, ("project", "state"))
    for path, entry in dropzones.items():
        entry.update(metadata.get(path, {}))
    # Selecting only COLL_NAME gives distinct collections with data objects,
    # rather than fetching every file or inspecting any physical file contents.
    for parent in PARENTS.values():
        for path, in row_iterator(
            "COLL_NAME", "COLL_NAME like " + query_value(parent + "/%") + " AND DATA_ID > '0'",
            AS_LIST, ctx.callback,
        ):
            dropzone = parent + "/" + path[len(parent) + 1:].split("/", 1)[0]
            if dropzone in dropzones:
                dropzones[dropzone]["catalog_empty"] = False
    return dropzones


def _audit_dropzone_consistency(ctx):
    dropzones = _catalog_dropzones(ctx)
    resources = {name: (host, vault) for name, host, vault in row_iterator(
        "RESC_NAME, RESC_LOC, RESC_VAULT_PATH", "", AS_LIST, ctx.callback,
    )}
    staging = list(row_iterator(
        "RESC_NAME", "META_RESC_ATTR_NAME = 'directIngestResc' AND META_RESC_ATTR_VALUE = 'true'",
        AS_LIST, ctx.callback,
    ))
    projects = collection_metadata(ctx, "COLL_PARENT_NAME = '/nlmumc/projects'", ("ingestResource",))
    errors, locations = [], []
    if len(staging) != 1:
        errors.append({"location": "staging", "error": "Expected exactly one directIngestResc=true resource",
                       "resources": [name for name, in staging]})
    else:
        host, vault = resources[staging[0][0]]
        if not host or host == "EMPTY_RESC_HOST" or not vault.startswith("/"):
            errors.append({"location": "staging", "error": "Staging resource has no physical host/vault"})
        else:
            for kind, suffix in (("direct", "direct"), ("mounted", "zones")):
                locations.append({"location": "staging_" + suffix, "type": kind, "host": host,
                                  "root": os.path.join(vault, "ingest", suffix)})

    project_hosts = {}
    for project, values in sorted(projects.items()):
        resource = values["ingestResource"]
        host = resources.get(resource, (None, None))[0]
        if not host or host == "EMPTY_RESC_HOST":
            errors.append({"project": project, "resource": resource, "error": "Cannot resolve project ingest host"})
        else:
            project_hosts[project] = host
    for host in sorted(set(project_hosts.values())):
        locations.append({"location": "mounted_data", "type": "mounted", "host": host, "root": MOUNTED_ROOT})

    mounted_hosts = {}
    for path, entry in dropzones.items():
        if entry["type"] == "mounted":
            project = "/nlmumc/projects/" + entry.get("project", "")
            if project not in project_hosts:
                errors.append({"logical_path": path, "project": entry.get("project"),
                               "error": "Cannot resolve mounted dropzone ingest host"})
            else:
                mounted_hosts[path] = project_hosts[project]

    # Finish catalog queries before making remote calls, and batch roots on a
    # shared host (e.g. staging plus mounted data) into a single remote request.
    inventories = {}
    for host in sorted({location["host"] for location in locations}):
        roots = [location["root"] for location in locations if location["host"] == host]
        try:
            result = ctx.callback.get_dropzone_disk_inventory(host, json.dumps(roots), "")["arguments"][2]
            inventories[host] = {entry["root"]: entry for entry in json.loads(result)}
        except Exception as error:
            inventories[host] = {root: {"execution_status": "failed", "error": str(error)} for root in roots}

    findings, scans = [], []
    for location in locations:
        kind, host, root = location["type"], location["host"], location["root"]
        expected = {entry["token"]: entry for path, entry in dropzones.items()
                    if entry["type"] == kind and (location["location"] != "mounted_data"
                                                  or mounted_hosts.get(path) == host)}
        inventory = inventories[host].get(root, {"execution_status": "failed", "error": "Missing root inventory"})
        scan = dict(location, execution_status=inventory["execution_status"], catalog_dropzones=len(expected))
        scans.append(scan)
        if inventory["execution_status"] != "completed":
            errors.append(dict(location, error=inventory["error"]))
            continue
        directories = set(inventory["directories"])
        missing = sorted(set(expected) - directories)
        orphaned = sorted(token for token in directories if PARENTS[kind] + "/" + token not in dropzones)
        scan.update(directories=len(directories), missing_on_disk=len(missing), missing_in_irods=len(orphaned))
        for token in missing:
            findings.append(dict(expected[token], kind="missing_on_disk", location=location["location"],
                                 host=host, physical_path=os.path.join(root, token)))
        for token in orphaned:
            findings.append({"kind": "missing_in_irods", "type": kind, "token": token,
                             "location": location["location"], "host": host,
                             "logical_path": PARENTS[kind] + "/" + token, "physical_path": os.path.join(root, token)})
    return {
        "check": "dropzone_consistency", "execution_status": "failed" if errors else "completed",
        "summary": {"catalog_dropzones": len(dropzones), "locations_scanned": sum(
            scan["execution_status"] == "completed" for scan in scans),
            "missing_on_disk": sum(finding["kind"] == "missing_on_disk" for finding in findings),
            "missing_in_irods": sum(finding["kind"] == "missing_in_irods" for finding in findings),
            "errors": len(errors)},
        "scans": scans, "findings": findings, "errors": errors,
    }
