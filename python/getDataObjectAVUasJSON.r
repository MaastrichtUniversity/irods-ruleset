# irule -r irods_rule_engine_plugin-python-instance -F getDataObjectAVUasJSON.r "*collName='/nlmumc/projects/P000000003/C000000001'"  "*dataObject='metadata.xml'"

from genquery import ( row_iterator, paged_iterator, AS_DICT, AS_LIST )
import json

def main(rule_args, callback, rei):
    coll_name = global_vars["*collName"][1:-1]  # strip the quotes
    data_object = global_vars["*dataObject"][1:-1]  # strip the quotes
    my_results_list = []
    rows = row_iterator(
            ["META_DATA_ATTR_NAME","META_DATA_ATTR_VALUE","META_DATA_ATTR_UNITS"],           # requested columns
            "COLL_NAME = '" + coll_name +"' AND DATA_NAME = '" + data_object + "'",                                                 # condition for query
            AS_DICT,                                                                         # retrieve as key/value structure
            callback)
    for row in rows:
        my_results_list.append({
            "a": row["META_DATA_ATTR_NAME"],
            "v": row["META_DATA_ATTR_VALUE"],
            "u": row["META_DATA_ATTR_UNITS"]
        })
    callback.writeLine("stdout", json.dumps(my_results_list))

INPUT *collName='/nlmumc/projects/P000000003/C000000001',  *dataObject='metadata.xml'
OUTPUT ruleExecOut

