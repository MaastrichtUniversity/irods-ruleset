@make(inputs=[0, 1, 2, 3], outputs=[], handler=Output.STORE)
def set_post_ingestion_error_avu(ctx, collection, attribute, value, message):
        #TODO WORK IN PROGRESS
        kvp = ctx.callback.msiString2KeyValPair("{}={}".format(attribute, value), irods_types.BytesBuf())["arguments"][1]
        ctx.callback.msiSetKeyValuePairsToObj(kvp, collection, "-C")
        ctx.callback.msiWriteRodsLog("Ingest failed of {} with error status {}".format(collection, value), 0);
        ctx.callback.msiWriteRodsLog(message, 0);
        # ctx.callback.closeProjectCollection(project_id, collection_id)
        ctx.callback.msiExit("-1", "{} for {}".format(message, collection))






