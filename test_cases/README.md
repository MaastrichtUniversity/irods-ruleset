# Prerequisites for the full test suite
```
iCAT, iRES, iRES-centos, iRES-s3-1 and iRES-S3-2 containers need to be up

SRAM-Sync needs to have run 

EPIC PID needs to run (Error-post ingestion)
```
# Prevent pytest cache warnings
```
Make sure the irods user has write access to the test_cases folder
chmod 755 /rules/test_cases
```

# How to run all the test cases
```
./rit.sh exec ires
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v .
```
# How to run a single test file
```
./rit.sh exec ires
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py
```
# How to run a single test case
```
./rit.sh exec ires
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM
```
# How to run a single test
```
./rit.sh exec ires
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM::test_collection_avu
```
