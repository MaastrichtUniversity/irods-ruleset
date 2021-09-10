import time 

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def ingest_nested_delay(ctx, source_collection, destination_collection):
    """
    The delay that triggers the actual ingest

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    source_collection: str
        The source, ie '/nlmumc/ingest/zones/crazy-frog'
    destination_collection: str
        The destination, ie '/nlmumc/projects/P00000001/C00000001'

    Returns
    -------

    """

    before = time.time()

    # Calling this method which is recursive and walks over the entire collection to be ingested
    walk_collection(ctx, source_collection, destination_collection)

    after = time.time()
    difference = float(after - before) + 1

    # Calculate the number of files and total size of the ProjectCollection
    size = ctx.callback.calcCollectionSize(destination_collection, "B", "ceiling", '')['arguments'][3]
    num_files = ctx.callback.calcCollectionFiles(destination_collection, '')['arguments'][1]

    avg_speed = float(size) / 1024 / 1024 / difference
    size_gib = float(size) / 1024 / 1024 / 1024

    ctx.callback.msiWriteRodsLog("{} : Ingested {} GiB in {} files".format(source_collection, size_gib, num_files), 0)
    ctx.callback.msiWriteRodsLog("{} : Sync took {} seconds".format(source_collection, difference), 0)
    ctx.callback.msiWriteRodsLog("{} : AVG speed was {} MiB/s".format(source_collection, avg_speed), 0)

    return ''


def walk_collection(ctx, source_collection, destination_collection):
    iter = row_iterator(
        "COLL_NAME",
        "COLL_PARENT_NAME = '" + source_collection + "' ",
        AS_LIST, ctx.callback)
    # In this first loop, we get all of the subfolders of the folder we are currently iterating
    for row in iter:
        # Here we replace the current folder path to the destination location 
        # example: '/nlmumc/ingest/zones/crazy-frog/testfolder' becomes '/nlmumc/projects/P00000001/C00000001/testfolder'
        new_path = row[0].replace(source_collection, destination_collection)
        status = 0
        # TODO: Do something based on the provided status
        # Here, it creates the new subfolder inside of the collection
        ctx.callback.msiCollCreate(new_path, 0, status)
        # Then, it calls this same function again and the subfolder is looped over to see if it also has any subfolders
        walk_collection(ctx, row[0], new_path)

    iter = row_iterator(
        "DATA_NAME",
        "COLL_NAME = '" + source_collection + "' ",
        AS_LIST, ctx.callback)
    # In this loop, all of the rows that come out are files. row[0] equals the filename
    for row in iter:
        # The source and destination collection are concatinated with the filename here     
        old_path = source_collection + '/' + row[0]
        new_path = destination_collection + '/' + row[0]
        # Copying the actual file over from source --> destination
        # TODO: Figure out if the 'numThreads' is still applicable here, since these are 
        # individual files and not an entire collection.
        ctx.callback.msiDataObjCopy(old_path, new_path, 'numThreads=10++++forceFlag=', 0)
