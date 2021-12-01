# Call with
#
# irule 'test_rule_output("RULE_NAME", "CSV_ARGUMENT_LIST")' null ruleExecOut
#
# Examples:
# irule 'test_rule_output("get_client_username", "")' null ruleExecOut
# irule 'test_rule_output("list_projects", "true")' null ruleExecOut | python -m json.tool
# irule 'test_rule_output("get_project_details", "/nlmumc/projects/P000000015,true")' null ruleExecOut | python -m json.tool
# irule 'test_rule_output("get_collection_size", "/nlmumc/projects/P000000014/C000000001,B,floor")' null ruleExecOut | python -m json.tool
# irule 'test_rule_output("get_collection_attribute_value", "/nlmumc/projects/P000000014/C000000001,title")' null ruleExecOut | python -m json.tool
#
#
# Switch user with as rods
#
# export clientUserName=psuppers

@make(inputs=[0, 1], outputs=[2], handler=Output.STDOUT)
def test_rule_output(ctx, rule_name, args):
    if args == "":
        output = getattr(ctx.callback, rule_name)("")
        ctx.callback.writeLine("stdout", output["arguments"][0])
    else:
        args = args.split(",")
        args.append("")
        output = getattr(ctx.callback, rule_name)(*args)
        ctx.callback.writeLine("stdout", str(output["arguments"][len(args)-1]))
