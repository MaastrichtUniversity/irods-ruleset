# Call with
#
# Needs iRODS admin right
#
# irule -F create-ingest.r "*token='bla-token'" "*user='p.vanschayck'" "*project='foo'" "*title='bar'" "*existingDir=''"

createIngest {
    remote("ires","") {
		*tokenColl = /nlmumc/ingest/zones/*token;

		*code = errorcode(msiCollCreate(*tokenColl, 0, *status));

		if ( *code == -809000 ) {
			failmsg(-1, "Token already in use");
		} else if ( *code != 0 ) {
			fail(*code);
		}

		msiAddKeyVal(*metaKV, "project", *project);
		msiAddKeyVal(*metaKV, "title", *title);
		msiAssociateKeyValuePairsToObj(*metaKV, "*tokenColl", "-C");

		if ( *existingDir != "" ) {
			*phyDir = *existingDir
		} else {
			*phyDir = "/mnt/ingest/zones/" ++ *token
			msiExecCmd("enable-ingest-zone.sh", *user ++ " " ++ *phyDir, "null", "null", "null", *status);
		}

#		msiPhyPathReg(*tokenColl, "demoResc", *phyDir, "mountPoint", *status);
		msiPhyPathReg(*tokenColl, "iresResource", *phyDir, "mountPoint", *status);

		# Set the ACL's on the iRODS collection
		msiSetACL("default", "own", *user, *tokenColl)
	}
}

INPUT *user="",*token="",*project="",*existingDir=""
OUTPUT ruleExecOut
