@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def perform_ingest_post_hook(ctx, project_id, collection_id, source_collection, difference):
    destination_collection = "/nlmumc/projects/{}/{}".format(project_id, collection_id)
    # Calculate and set the byteSize and numFiles AVU. false/false because collection
    # is already open and needs to stay open
    ctx.callback.setCollectionSize(project_id, collection_id, "false", "false")
    num_files = ctx.callback.getCollectionAVU(destination_collection, "numFiles", "", "", "true")["arguments"][2]
    size = ctx.callback.getCollectionAVU(destination_collection, "dcat:byteSize", "", "", "true")["arguments"][2]

    avg_speed = float(size) / 1024 / 1024 / float(difference)
    size_gib = float(size) / 1024 / 1024 / 1024

    ctx.callback.msiWriteRodsLog("{} : Ingested {} GiB in {} files".format(source_collection, size_gib, num_files), 0)
    ctx.callback.msiWriteRodsLog("{} : Sync took {} seconds".format(source_collection, difference), 0)
    ctx.callback.msiWriteRodsLog("{} : AVG speed was {} MiB/s".format(source_collection, avg_speed), 0)
