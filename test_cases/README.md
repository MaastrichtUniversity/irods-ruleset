# Prerequisites for the full test suite
```
icat, ires-hnas-um, ires-hnas-azm, ires-ceph-ac and ires-ceph-gl containers need to be up

keycloak needs to have run

sram-sync needs to have run

epicpid needs to be up (Error-post ingestion)

elasticsearch needs to be up
```
# Prevent pytest cache warnings
```
Make sure the irods user has write access to the test_cases folder (inside ires-hnas-um container)
chmod 777 /rules/test_cases
or
add the argument -p no:cacheprovider
/var/lib/irods/.local/bin/pytest -v -p no:cacheprovider .
```

# How to run all the test cases
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v .
/var/lib/irods/.local/bin/pytest -v -p no:cacheprovider .
```

# How to run all the test cases with print enabled
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v -s -p no:cacheprovider .
```

# How to run a single test file
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py
```
# How to run a single test case
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM
```
# How to run a single test
```
./rit.sh exec ires-hnas-um
su irods
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -v test_direct_ingest.py::TestDirectIngestUM::test_collection_avu
```

# How to run all the test cases in parallel
```
./rit.sh exec icat
su irods
pip install pytest-xdist
cd /rules/test_cases
/var/lib/irods/.local/bin/pytest -p no:cacheprovider -n 3 --dist loadfile -v .
```