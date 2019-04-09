def main(rule_args, callback, rei):
    arg = global_vars["*arg"][1:-1]
    callback.writeLine("stdout", "arg = " + arg)
    
INPUT *arg="some argument"
OUTPUT ruleExecOut