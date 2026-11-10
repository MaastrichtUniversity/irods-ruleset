"""Recognize unfinished ingests from project-collection attribute names."""


INGEST_COMPLETION_AVUS = (
    "creator", "depositor", "PID", "latest_version_number", "schemaName", "schemaVersion",
)


def is_unfinished_ingest(attributes):
    return not any(attribute in attributes for attribute in INGEST_COMPLETION_AVUS)
