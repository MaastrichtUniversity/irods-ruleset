# /rules/tests/run_test.sh -r get_all_deleted_users -j
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error
from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_all_deleted_users(ctx):

    output = []

    for account in row_iterator("USER_NAME", "META_USER_ATTR_NAME = 'pendingDeletionProcedure'", AS_LIST, ctx.callback):
        output.append(account[0])

    return output

    #username = {output.spit(",")}
    #attribute_to_query = "'dataSteward', 'OBI:0000103'"
    #rule_result = {}


    #for query_result in row_iterator(
    #    "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
    #    "META_COLL_ATTR_VALUE in ({}) AND META_COLL_ATTR_NAME in ({})".format(username, attribute_to_query),
    #    AS_LIST,
    #    ctx.callback,
    #):
    #    username = query_result[0]
    #    attribute = query_result[1]
    #    value = query_result[2]
    #    if username not in rule_result:
    #        rule_result[username] = {attribute: value}
    #    else:
    #        rule_result[username][attribute] = value

    #return rule_result
