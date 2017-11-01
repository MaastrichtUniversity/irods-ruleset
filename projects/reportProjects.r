# This rule returns a JSON string with information about all projects. Outcome can be used for reporting purposes.
#
# Call with (execute as rodsadmin user with full permission to /nlmumc/projects)
#
# irule -F reportProjects.r

irule_dummy() {
    IRULE_reportProjects(*result);

    writeLine("stdout", *result);
}

IRULE_reportProjects(*result) {
    *jsonStr = '[]';

	foreach ( *Row in SELECT COLL_NAME WHERE COLL_PARENT_NAME = "/nlmumc/projects" ) {
		# Declare variables
		*outcome = "";
		*size = 0;
		*title = "";
        *resource = "";
		*managers = "";
        
        # Retrieve the project from the directory name
		uuChopPath(*Row.COLL_NAME, *dir, *project);
		
		# Retrieve AVUs based on project
		getCollectionAVU("/nlmumc/projects/*project","title",*title,"","true");
		getCollectionAVU("/nlmumc/projects/*project","resource",*resource,"","true");
		
		# Retrieve the project manager(s)
		listProjectManagers(*project,*managers);

		# Calculate the size of this project
		getFolderSize("/nlmumc/projects/*project", *dataSize) # dataSize is the result variable that will be created by this rule
		
		# Validate the contents of variables and construct json object
		if ( *title == "" ) {
            *titleStr = "no-title-AVU-set";
        } else {
            *titleStr = *title;
        }
		
		if ( *resource == "" ) {
            *resourceStr = "no-resource-AVU-set";
        } else {
            *resourceStr = *resource;
        }

		# Outcome contains the results from this iteration
		*outcome = '{"project":"*project", "resource": "*resourceStr", "dataSize": "*dataSize MB", "managers": *managers}';

		# Title needs proper escaping before adding to JSON. That's why we pass it through msi_json_objops
        msiString2KeyValPair("", *titleKvp);
        msiAddKeyVal(*titleKvp, "title", *titleStr);
        msi_json_objops(*outcome, *titleKvp, "add");

		# Append the final outcome to the jsonString
		msi_json_arrayops(*jsonStr, *outcome, "add", *size)
	}

    # jsonStr now contains information about all projects. Return this in the result variable
    *result = *jsonStr;
}

INPUT *result=''
OUTPUT ruleExecOut
