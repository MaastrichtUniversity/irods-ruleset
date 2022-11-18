# Check if key exists in a list
# Returns true if key is in list, false if the key is not in the list
checkIfKeyInList(*list, *key) {
    errormsg(msiGetValByKey(*list, *key, *val), *err) == 0;
}
