"""This sub-package contains the rules related to DataHub resources (ingest & destination)"""
# Public rules
from datahubirodsruleset.resources.get_resource_size_for_all_collections import get_resource_size_for_all_collections

# Private rules
from datahubirodsruleset.resources.get_direct_ingest_resource_host import get_direct_ingest_resource_host
