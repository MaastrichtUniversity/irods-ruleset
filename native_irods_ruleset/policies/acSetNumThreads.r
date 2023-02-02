# Enforce single threaded iRODS data connections when using Ceph S3 resources
# The arguments for msiSetNumThreads are:
# 1) sizePerThrInMb - integer value in MBytes to calculate the number of threads (default: 32)
# 2) maxNumThr      - the maximum number of threads to use (default: 4).
# 3) windowSize     - the tcp window size in Bytes for the parallel transfer (default: 1048576).
acSetNumThreads {
    # Session variables $rescName and $KVPairs are not always present and their existence needs to be checked first.
    # For instance, during replication it only exists for one of the two resources.
    # It errors, but doesn't affect the outcome of the replication.
    # Note: The ERROR is catched below and thus suppressed from the rodsLog

    *error = errorcode(msiGetValByKey($KVPairs,"rescName",*out));
    if ( *error == 0 ) {
        if ($KVPairs.rescName == "UM-Ceph-S3-AC" || $KVPairs.rescName == "UM-Ceph-S3-GL") {
            msiSetNumThreads("default","0","default");
        } else {
            msiSetNumThreads("default","16","default");
        }
    }
}