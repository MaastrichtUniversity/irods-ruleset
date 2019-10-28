# This rule will retrieve the total size of a collection (folder) in iRODS from an iCAT AVU
# Call with
#
# irule -F getResourcesInCollection.r "*collection='/nlmumc/projects/P000000001/C000000001'"
#

irule_dummy() {
    IRULE_getResourcesInCollection(*collection, *result);
    writeLine("stdout", *result);
}

IRULE_getResourcesInCollection(*collection, *result) {
    # *resources is a Key pair Value object to store resource type for each resource. key -> resource ID; value ->  "parent" or "orphan"
    *resources;

    # Determine all parent resources (= coordResc) used in this collection
    # Some resources do not have a parent and return an empty string. These are excluded from the SQL result here and being tackled by the orphan call further down.
    foreach ( *Row in SELECT RESC_PARENT WHERE RESC_PARENT != "" and COLL_NAME like "*collection%") {
        # reset *id and *type
        *id = 0
        *type = ""

        # Add values to resources kvp
        *id = *Row.RESC_PARENT;
        *type = "parent";
        *resources.*id = *type;
    }

    # Repeat for orphan resources (parentless)
    foreach ( *Row in SELECT RESC_ID WHERE RESC_PARENT == "" and COLL_NAME like "*collection%") {
        # reset *id and *type
        *id = 0
        *type = ""

        # Add values to resources kvp
        *id = *Row.RESC_ID;
        *type = "orphan";
        *resources.*id = *type;
    }

    # Example result
    # KeyValue[3]:10002=parent;60742=orphan;83598=orphan;
    *result = *resources;
}

INPUT *collection=""
OUTPUT ruleExecOut