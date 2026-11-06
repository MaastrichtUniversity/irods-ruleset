from collections import defaultdict
from itertools import groupby

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def calculate_collection_statistics(ctx, collection_path):
    """Return size/count AVUs as a native key-value string for setCollectionSize."""
    total_size = 0
    total_count = 0
    resource_sizes = defaultdict(int)
    resource_counts = defaultdict(int)
    rows = row_iterator(
        "order(DATA_ID), DATA_SIZE, RESC_ID, RESC_PARENT",
        f"COLL_NAME like '{collection_path}%'",
        AS_LIST,
        ctx.callback,
    )
    # Ordering keeps memory bounded by one logical file's replicas, rather than
    # retaining every file ID in a potentially very large collection.
    for _, replicas in groupby(rows, key=lambda row: row[0]):
        # Match the distinct DATA_ID, DATA_SIZE projection of the native size
        # rules, including replicas with different sizes. Counts use DATA_ID only.
        sizes = set()
        sizes_by_resource = defaultdict(set)
        for _, data_size, resource_id, parent_id in replicas:
            sizes.add(int(data_size))
            # Preserve getResourcesInCollection's immediate-parent/orphan grouping.
            sizes_by_resource[parent_id or resource_id].add(int(data_size))
        total_size += sum(sizes)
        total_count += 1
        for resource_id, sizes in sizes_by_resource.items():
            resource_sizes[resource_id] += sum(sizes)
            resource_counts[resource_id] += 1

    values = [
        f"dcat:byteSize={total_size}",
        f"numFiles={total_count}",
    ]
    for resource_id, size in resource_sizes.items():
        values.extend([
            f"dcat:byteSize_resc_{resource_id}={size}",
            f"numFiles_resc_{resource_id}={resource_counts[resource_id]}",
        ])
    return "%".join(values)
