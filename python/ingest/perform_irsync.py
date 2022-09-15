@make(inputs=range(3), outputs=[], handler=Output.STORE)
def perform_irsync(ctx, source_collection, destination_collection, destination_resource):
    import subprocess
    return_code = subprocess.check_call(["irsync", "-R", destination_resource, "-r", source_collection, "i:" + destination_collection], shell=False)
    ctx.callback.msiWriteRodsLog("Exit code of irsync: " + str(return_code) ,0)
