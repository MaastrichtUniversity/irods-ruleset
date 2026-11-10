# Run through the housekeeping controller as rods:
# /rules/tests/run_test.sh -r run_housekeeping -a "replica_status,async" -j
"""Audit non-good project replicas after fetching their complete inventory."""

import re

from dhpythonirodsutils.enums import ProcessAttribute, ReplicaStatus
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.housekeeping.ingest_state import INGEST_COMPLETION_AVUS, is_unfinished_ingest
from datahubirodsruleset.listing_queries import metadata_for_paths


def _audit_replica_status(ctx):
    candidates = []
    for condition in ("COLL_NAME = '/nlmumc/projects'", "COLL_NAME LIKE '/nlmumc/projects/%'"):
        for collection, name, replica, status, resource in row_iterator(
            "COLL_NAME, DATA_NAME, DATA_REPL_NUM, DATA_REPL_STATUS, DATA_RESC_NAME",
            condition + f" AND DATA_REPL_STATUS != '{ReplicaStatus.GOOD.value}'",
            AS_LIST, ctx.callback,
        ):
            match = re.match(r"(/nlmumc/projects/P[0-9]{9}/C[0-9]{9})(?:/|$)", collection)
            candidates.append({"path": collection + "/" + name,
                               "project_collection": match[1] if match else None,
                               "replica_number": replica, "replica_status": status, "resource": resource})

    # Do not interleave metadata reads with the potentially long replica scan.
    paths = sorted({entry["project_collection"] for entry in candidates if entry["project_collection"]})
    tape_attributes = (ProcessAttribute.ARCHIVE.value, ProcessAttribute.UNARCHIVE.value)
    metadata = metadata_for_paths(ctx, paths, INGEST_COMPLETION_AVUS + tape_attributes)
    findings = []
    skipped_tape = 0
    skipped_ingests = 0
    for entry in sorted(candidates, key=lambda entry: (entry["path"], entry["replica_number"])):
        path = entry["project_collection"]
        if path:
            attributes = metadata.get(path, {})
            if any(attribute in attributes for attribute in tape_attributes):
                skipped_tape += 1
                continue
            if is_unfinished_ingest(attributes):
                skipped_ingests += 1
                continue
        findings.append(entry)
    return {
        "check": "replica_status", "execution_status": "completed",
        "summary": {"candidate_replicas": len(candidates),
                    "replicas_skipped_tape_operation": skipped_tape,
                    "replicas_skipped_unfinished_ingest": skipped_ingests,
                    "replicas_with_findings": len(findings),
                    "files_with_findings": len({entry["path"] for entry in findings})},
        "findings": findings,
    }
