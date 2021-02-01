#!/usr/bin/env bash

RULES=../rules

icd  /nlmumc/home/rods

# Clean up
if ils test1.file; then
    irm test1.file
fi

if ils test2.file; then
    irm test2.file
fi

# Test files
iput pep_tests.sh test1.file

# imeta add

irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if ! imeta add -d test1.file a4 v4 u4; then
    echo ERROR imeta add -C test1.file a4 v4 u4 should work
    exit 1
fi

if imeta add -d test1.file a4 v4 root_daniel; then
    echo ERROR imeta add -d test1.file a4 v4 root_daniel should NOT work
    exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file

# imeta mod
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

imeta add -d test1.file a4 v4 u4

if ! imeta mod -d test1.file a4 v4 u4 n:a2 v:v2 u:u2; then
    echo ERROR imeta mod -d test1.file a4 v4 u4 n:a2 v:v2 u:u2 should work
     exit 1
fi

if imeta mod -d test1.file lastName Doe root_0_s n:a2 v:v2 u:u2; then
    echo ERROR  imeta mod -d test1.file lastName Doe root_0_s n:a2 v:v2 u:u2 should NOT work
     exit 1
fi

if imeta mod -d test1.file a2 v2 u2 n:a2 v:v2 u:root_daniel; then
    echo ERROR  imeta mod -d test1.file a2 v2 u2 n:a2 v:v2 u:root_daniel should NOT work
     exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file

# imeta set
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if ! imeta set -d test1.file a4 v4 u4; then
    echo ERROR imeta set -d test1.file a4 v4 u4 should work
    exit 1
fi

if imeta set -d test1.file a4 v4 root_daniel; then
   echo ERROR  imeta set -d test1.file a4 v4 root_daniel should NOT work
   exit 1
fi

if imeta set -d test1.file lastName test ; then
   echo ERROR imeta set -d test1.file lastName test   should NOT work
   exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file

# imeta rm
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"
imeta add -d test1.file a4 v4 u4

if ! imeta rm -d test1.file a4 v4 u4; then
    echo ERROR imeta rm -d test1.file a4 v4 u4 should work
    exit 1
fi

if imeta rm -d test1.file firstName John root_0_s; then
   echo ERROR  imeta rm -d test1.file firstName John root_0_s should NOT work
   exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file
iput pep_tests.sh test2.file

# imeta cp
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

imeta add -d test1.file test1 test1 root_lalalla

if ! imeta cp -d -d test1.file test2.file; then
    echo ERROR imeta cp -d -d test1.file test2.file should work
    exit 1
fi

imeta rmw -d /nlmumc/home/rods/test1.file % % %
imeta add -d /nlmumc/home/rods/test1.file  test2 test2 root_0_s

if imeta cp -d -d test2.file test1.file; then
    echo ERROR imeta cp -d -d test2.file test1.file should work
    exit 1
fi

# Cleanup
irm test1.file
irm test2.file
iput pep_tests.sh test1.file

# imeta rmw
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"
imeta add -d test1.file a4 v4 u4


if ! imeta rmw -d test1.file a4 % %; then
    echo ERROR imeta rmw -d test1.file a4 % % should work
    exit 1
fi

if imeta rmw -d test1.file % % %; then
   echo ERROR imeta rmw -d test1.file % % % should NOT work
   exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file

# setJsonSchemaToObj
if ! irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"; then
    echo ERROR irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'" should work
    exit 1
fi

irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://google.com'" "*jsonRoot='root'"; then
   echo ERROR irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'" should NOT work
   exit 1
fi

# Cleanup
irm test1.file
iput pep_tests.sh test1.file

# setJsonToObj
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"

if ! irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"; then
    echo ERROR irule -F setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'" should work
    exit 1
fi

if irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21'"; then
    echo ERROR irule -F setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21'" should not work
    exit 1
fi

if irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":\"21\"}'"; then
    echo ERROR irule -F setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":\"21\"}'" should not work
    exit 1
fi

# setJsonToObj with iRODS object as schema

iput weight.json weight.json
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='i:/nlmumc/home/rods/weight.json'" "*jsonRoot='weight'"

if ! irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='weight'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"weight\":21}'"; then
    echo ERROR irule -F setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='weight'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"weight\":21}'" should work
    exit 1
fi

# Cleanup
irm test1.file
irm weight.json
iput pep_tests.sh test1.file

# getJsonFromObj
irule -F $RULES/setJsonSchemaToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F $RULES/setJsonToObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if ! irule -F $RULES/getJsonFromObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" ; then
    echo ERROR irule -F getJsonFromObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'" should work
    exit 1
fi

res=$(irule -F $RULES/getJsonFromObj.r "*object='/nlmumc/home/rods/test1.file'" "*objectType='-d'" "*jsonRoot='root'")


if ! [ "$res" == '{"lastName": "Doe", "age": 21, "firstName": "John"}' ]; then
    echo ERROR Output of getJsonFromObj.r is not as expected
    exit 1
fi

# Cleanup
irm test1.file

echo DONE all tests passed
