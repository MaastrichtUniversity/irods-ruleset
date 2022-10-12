# How to run all the test case
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