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
# Switch user with as rods:
#
# export clientUserName=psuppers
#
# Rule explanation:
#	This rule aim to abstract and simplify the execution of python rules by command line.
#	To achieve it, we use 2 special python features
#
# 1) getattr()
#	rule_name = get_client_username
# getattr(ctx.callback, rule_name)("")
#		is equivalent to
# ctx.callback.get_client_username("")
#
# 2) (un)packing list argument *args
#	args = ["foo", "bar", 42]
# ctx.callback.test(*args)
#		is equivalent to
#	ctx.callback.test("foo", "bar", 42)

@make(inputs=[0, 1], outputs=[2], handler=Output.STDOUT)
def test_rule_output(ctx, rule_name, args):
		# Case the list argument is empty and the rule expect no argument
    if args == "":
        output = getattr(ctx.callback, rule_name)("")
        ctx.callback.writeLine("stdout", output["arguments"][0])
		# The rule expect some arguments, and test_rule_output expect them as a csv string
    else:
        args = args.split(",")
        # we need to add a empty string as the last index for the output argument.
        args.append("")
        output = getattr(ctx.callback, rule_name)(*args)
        ctx.callback.writeLine("stdout", str(output["arguments"][len(args)-1]))
