@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def direct_ingest(ctx, username, token):
    """
    Start a direct ingest

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.
    username: str
        The username, ie 'dlinssen'
    token: str
        The token, ie 'crazy-frog'

    Returns
    -------
    list
        a json list of projects objects
    """
    ### THIS IS ENTIRELY POC STATE CODE NOT MEANT FOR PRODUCION DEPLOYMENT
    ## STILL TODO:
    # Check for project's ingest resource status before start of ingest
    # Delayed execution of ingest_nested_delay.py rule https://github.com/UtrechtUniversity/irods-ruleset-uu/blob/96886239bfcbdc80d42304925eb5a4034ac0a897/vault.py#L189-L195
    # Validation (?)
    # Setting Creator AVU
    # Setting collection size as AVU
    # Get PID without Mirth
    # Set State AVU to ingested at the end
    # Remove 'size ingested' AVU
    # Close project collection
    # Remove dropzone with delay 24H

    source_collection = "/nlmumc/ingest/zones/{}".format(token)

    has_dropzone_permission = ''
    has_dropzone_permission = ctx.callback.checkDropZoneACL(username, '')
    if(has_dropzone_permission == 'false'):
        ctx.callback.msiExit("-818000", "User '{}' has insufficient DropZone permissions on /nlmumc/ingest/zones".format(username))

    try:
        ctx.callback.msiObjStat(source_collection, irods_types.RodsObjStat())
    except RuntimeError:
        # -814000 CAT_UNKNOWN_COLLECTION
        ctx.callback.msiExit("-814000", "Unknown ingest zone")


    # Get dropzone metadata
    # Note: Retrieving the rule outcome is done with '["arguments"][2]'
    state = ''
    project = ''
    title = ''
    project = ctx.callback.getCollectionAVU(source_collection, "project", "", "", "true")["arguments"][2]
    title = ctx.callback.getCollectionAVU(source_collection, "title", "", "", "true")["arguments"][2]    
    state = ctx.callback.getCollectionAVU(source_collection, "state", "", "", "true")["arguments"][2]

    #TODO: Check for project's ingest resource status to start ingestion


    # Check for valid state to start ingestion
    if state != "open" and state != "warning-validation-incorrect": 
        ctx.callback.msiExit("-1", "Invalid state to start ingestion.")
       
    ctx.callback.msiWriteRodsLog("Starting ingestion {}:".format(source_collection), 0)

    # Set 'state' AVU to 'ingesting'
    kvp = ctx.callback.msiString2KeyValPair('{}={}'.format('state', 'ingesting'), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, source_collection, "-C")
    
    # Create Project Collection
    project_collection =ctx.callback.createProjectCollection(project, '', title)["arguments"][1]
    destination_collection = '/nlmumc/projects/{}/{}'.format(project, project_collection) 

    ctx.callback.msiWriteRodsLog("Ingesting {} to {}".format(source_collection, destination_collection), 0)

    # Add destination AVU to dropzone
    kvp = ctx.callback.msiString2KeyValPair('{}={}'.format('destination', project_collection), irods_types.BytesBuf())["arguments"][1]
    ctx.callback.msiSetKeyValuePairsToObj(kvp, source_collection, "-C")

    # Call the ingest delay rule
    ctx.callback.ingest_nested_delay(source_collection, destination_collection)

    return ''
