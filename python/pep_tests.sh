#!/usr/bin/env bash

cd /rules/python

icd  /nlmumc/home/rods

if ils /nlmumc/home/rods/setJsonToObj.r; then
    irm /nlmumc/home/rods/setJsonToObj.r
fi
if ils /nlmumc/home/rods/getJsonFromObj.r; then
    irm /nlmumc/home/rods/getJsonFromObj.r
fi


# imeta add
iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if ! imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4; then
    echo ERROR imeta add -C /nlmumc/home/rods/setJsonToObj.r a4 v4 u4 should work
    exit 1
fi

if imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 root_daniel; then
    echo ERROR imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 root_daniel should NOT work
    exit 1
fi

irm /nlmumc/home/rods/setJsonToObj.r


#imeta mod

iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"
imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4

if ! imeta mod -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4 n:a2 v:v2 u:u2; then
    echo ERROR imeta mod -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4 n:a2 v:v2 u:u2 should work
     exit 1
fi

if imeta mod -d /nlmumc/home/rods/setJsonToObj.r lastName Doe root_0_s n:a2 v:v2 u:u2; then
    echo ERROR  imeta mod -d /nlmumc/home/rods/setJsonToObj.r lastName Doe root_0_s n:a2 v:v2 u:u2 should NOT work
     exit 1
fi

if imeta mod -d /nlmumc/home/rods/setJsonToObj.r a2 v2 u2 n:a2 v:v2 u:root_daniel; then
    echo ERROR  imeta mod -d /nlmumc/home/rods/setJsonToObj.r a2 v2 u2 n:a2 v:v2 u:root_daniel should NOT work
     exit 1
fi

irm /nlmumc/home/rods/setJsonToObj.r

#imeta set

iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

if ! imeta set -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4; then
    echo ERROR imeta set -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4 should work
    exit 1
fi

if imeta set -d /nlmumc/home/rods/setJsonToObj.r a4 v4 root_daniel; then
   echo ERROR  imeta set -d /nlmumc/home/rods/setJsonToObj.r a4 v4 root_daniel should NOT work
   exit 1
fi

if imeta set -d /nlmumc/home/rods/setJsonToObj.r lastName test ; then
   echo ERROR imeta set -d /nlmumc/home/rods/setJsonToObj.r lastName test   should NOT work
   exit 1
fi



irm /nlmumc/home/rods/setJsonToObj.r

# imeta rm

iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"
imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4

if ! imeta rm -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4; then
    echo ERROR imeta rm -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4 should work
    exit 1
fi

if imeta rm -d /nlmumc/home/rods/setJsonToObj.r firstName John root_0_s; then
   echo ERROR  imeta rm -d /nlmumc/home/rods/setJsonToObj.r firstName John root_0_s should NOT work
   exit 1
fi

irm /nlmumc/home/rods/setJsonToObj.r

# imeta cp
iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"

iput getJsonFromObj.r
imeta add -d /nlmumc/home/rods/getJsonFromObj.r  test1 test1 root_lalalla

if ! imeta cp -d -d getJsonFromObj.r setJsonToObj.r; then
    echo ERROR imeta cp -d -d getJsonFromObj.r setJsonToObj.r should work
    exit 1
fi

imeta rmw -d /nlmumc/home/rods/getJsonFromObj.r % % %
imeta add -d /nlmumc/home/rods/getJsonFromObj.r  test2 test2 root_0_s

if imeta cp -d -d getJsonFromObj.r setJsonToObj.r; then
    echo ERROR imeta cp -d -d getJsonFromObj.r setJsonToObj.r should work
    exit 1
fi

irm /nlmumc/home/rods/setJsonToObj.r
irm /nlmumc/home/rods/getJsonFromObj.r

#imeta rmw
iput setJsonToObj.r
irule -F setJsonSchemaToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonSchema='https://api.myjson.com/bins/17vejk'" "*jsonRoot='root'"
irule -F setJsonToObj.r "*object='/nlmumc/home/rods/setJsonToObj.r'" "*objectType='-d'" "*jsonRoot='root'" "*jsonString='{\"firstName\":\"John\",\"lastName\":\"Doe\",\"age\":21}'"
imeta add -d /nlmumc/home/rods/setJsonToObj.r a4 v4 u4


if ! imeta rmw -d /nlmumc/home/rods/setJsonToObj.r a4 % %; then
    echo ERROR imeta rmw -d /nlmumc/home/rods/setJsonToObj.r a4 % % should work
    exit 1
fi

if imeta rmw -d /nlmumc/home/rods/setJsonToObj.r % % %; then
   echo ERROR imeta rmw -d /nlmumc/home/rods/setJsonToObj.r % % % should NOT work
   exit 1
fi

irm /nlmumc/home/rods/setJsonToObj.r

echo DONE all tests passed

#imeta addw -d /nlmumc/home/rods/% a4 v4 root_daniel