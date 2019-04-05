import json
import sys
import jsonavu


def pythonFunctionCore(rule_args, callback, rei):
	arg = global_vars["*arg"][1:-1]                # strip the quotes
	callback.writeLine("stdout", "arg = " + arg)


def getProjectDetailsAsAVU(rule_args, callback, rei):
	project = global_vars["*project"][1:-1]                # strip the quotes
	ret_val = callback.detailsProject(project, 'false', "")
	managers = ret_val['arguments'][2]
	callback.writeLine("stdout", "Project = " + project)
	callback.writeLine("stdout", "Managers = " + str(managers))

	data = json.loads(managers)
	avu = jsonavu.json2avu(data, "root")
	max_a_len = len(max(avu, key=lambda k: len(str(k["a"])))["a"])
	max_v_len = len(max(avu, key=lambda k: len(str(k["v"])))["v"])
	out_format = "%" + str(max_a_len + 5) + "s %" + str(max_v_len + 5) + "s %15s"
	for i in avu:
		callback.writeLine("stdout", out_format % (i["a"], i["v"], i["u"]))
