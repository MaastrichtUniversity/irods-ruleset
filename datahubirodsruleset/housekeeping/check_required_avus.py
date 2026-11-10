# Run through the housekeeping controller as rods:
# /rules/tests/run_test.sh -r run_housekeeping -a "required_avus,async" -j
"""Internal audit of required project and project-collection AVU names."""

import re

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.housekeeping.ingest_state import is_unfinished_ingest


PROJECT_AVUS = (
    "OBI:0000103", "archiveDestinationResource", "authorizationPeriodEndDate",
    "collectionMetadataSchemas", "dataRetentionPeriodEndDate", "dataSteward",
    "enableArchive", "enableContributorEditMetadata", "enableDropzoneSharing",
    "enableUnarchive", "ingestResource", "latestProjectCollectionNumber", "resource",
    "responsibleCostCenter", "storageQuotaGb", "title",
)
PROJECT_COLLECTION_AVUS = (
    "PID", "creator", "dcat:byteSize", "depositor", "latest_version_number",
    "numFiles", "schemaName", "schemaVersion", "title",
)
PROJECT_CONDITION = "COLL_PARENT_NAME = '/nlmumc/projects'"
PROJECT_COLLECTION_CONDITION = "COLL_PARENT_NAME like '/nlmumc/projects/P_________'"


def _audit_required_avus(ctx):
    projects = {
        path: set() for path, in row_iterator("COLL_NAME", PROJECT_CONDITION, AS_LIST, ctx.callback)
        if re.fullmatch(r"/nlmumc/projects/P[0-9]{9}", path)
    }
    collections = {
        path: set() for path, in row_iterator("COLL_NAME", PROJECT_COLLECTION_CONDITION, AS_LIST, ctx.callback)
        if re.fullmatch(r"/nlmumc/projects/P[0-9]{9}/C[0-9]{9}", path)
        and path.rsplit("/", 1)[0] in projects
    }
    # Enumerate independently of metadata to include bare projects and count
    # unfinished PCs. Fetch names in bulk, not one query per AVU.
    for condition, entities in ((PROJECT_CONDITION, projects), (PROJECT_COLLECTION_CONDITION, collections)):
        if entities:
            for path, attribute in row_iterator(
                "COLL_NAME, META_COLL_ATTR_NAME", condition, AS_LIST, ctx.callback
            ):
                if path in entities:
                    entities[path].add(attribute)

    findings = []
    for path, attributes in sorted(projects.items()):
        missing = sorted(set(PROJECT_AVUS) - attributes)
        if missing:
            findings.append({"entity_type": "project", "path": path, "missing_avus": missing})
    project_findings = len(findings)
    skipped_ingests = 0
    for path, attributes in sorted(collections.items()):
        if is_unfinished_ingest(attributes):
            skipped_ingests += 1
            continue
        missing = set(PROJECT_COLLECTION_AVUS) - attributes
        size_ids = {match[1] for attribute in attributes
                    if (match := re.fullmatch(r"dcat:byteSize_resc_([0-9]+)", attribute))}
        count_ids = {match[1] for attribute in attributes
                     if (match := re.fullmatch(r"numFiles_resc_([0-9]+)", attribute))}
        missing.update(f"numFiles_resc_{identifier}" for identifier in size_ids - count_ids)
        missing.update(f"dcat:byteSize_resc_{identifier}" for identifier in count_ids - size_ids)
        missing_pair = not bool(size_ids & count_ids)
        if missing or missing_pair:
            findings.append({"entity_type": "project_collection", "path": path,
                             "missing_avus": sorted(missing), "missing_resource_avu_pair": missing_pair})
    return {
        "check": "required_avus", "execution_status": "completed",
        "summary": {"projects_checked": len(projects),
                    "project_collections_checked": len(collections) - skipped_ingests,
                    "project_collections_skipped_unfinished_ingest": skipped_ingests,
                    "projects_with_findings": project_findings,
                    "project_collections_with_findings": len(findings) - project_findings},
        "findings": findings,
    }


