# Enforce single threaded iRODS data connections when using Ceph S3 resources
# The arguments for msiSetNumThreads are:
# 1) sizePerThrInMb - integer value in MBytes to calculate the number of threads (default: 32)
# 2) maxNumThr      - the maximum number of threads to use (default: 4).
# 3) windowSize     - the tcp window size in Bytes for the parallel transfer (default: 1048576).
acSetNumThreads {
    # rescName is not present for every invocation. Iterate over the keys first
    # because msiGetValByKey logs an error when asked for a missing key.
    foreach (*key in $KVPairs) {
        if (*key == "rescName") {
            if ($KVPairs.rescName == "UM-Ceph-S3-AC" || $KVPairs.rescName == "UM-Ceph-S3-GL" || $KVPairs.rescName == "AZM-storage2" || $KVPairs.rescName == "AZM-storage2-repl") {
                msiSetNumThreads("default","0","default");
            } else {
                msiSetNumThreads("default","4","default");
            }
        }
    }
}
