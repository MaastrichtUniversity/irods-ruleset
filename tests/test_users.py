import json
import subprocess


def test_rule_get_all_users_groups_memberships():
    rule_users = '/rules/tests/run_test.sh -r get_all_users_groups_memberships -a "false,false,true,false"'
    ret_users = subprocess.check_output(rule_users, shell=True)

    users = json.loads(ret_users)
    assert users is not None

    username = "jmelius"
    rule_user_id = '/rules/tests/run_test.sh -r get_user_id -a "{username}"'.format(username=username)
    ret_user_id = subprocess.check_output(rule_user_id, shell=True)

    user_id = str(json.loads(ret_user_id))
    assert len(users[user_id]["group_names"]) > 0
    assert users[user_id]["user_name"] == username


def test_get_all_users_id():
    rule = "/rules/tests/run_test.sh -r get_all_users_id -j"
    ret = subprocess.check_output(rule, shell=True)

    users = json.loads(ret)
    assert len(users) > 0


def test_get_contributing_project():
    rule = '/rules/tests/run_test.sh -r get_contributing_project -a "P000000010,false" -u psuppers'
    ret = subprocess.check_output(rule, shell=True)

    project = json.loads(ret)
    assert "psuppers" in project["managers"]["users"]
    assert project["id"] == "P000000010"
    assert project["title"] == "(MDL) Placeholder project"


def test_rule_get_groups():
    rule = '/rules/tests/run_test.sh -r get_groups -a "false" -u jmelius'
    ret = subprocess.check_output(rule, shell=True)

    groups = json.loads(ret)
    assert groups is not None
    assert len(groups) == 5
    assert groups[3]["name"] == "m4i-nanoscopy-phd0815"
    assert groups[3]["groupId"].isdigit() is True
    assert groups[3]["displayName"] == "Novel approach for smashing ions"
    assert groups[3]["description"] == "CO for PhD project of P7000815"


def test_get_service_accounts_id():
    rule = '/rules/tests/run_test.sh -r get_service_accounts_id'
    ret = subprocess.check_output(rule, shell=True)

    users = json.loads(ret)
    assert len(users) > 0


def test_get_temporary_password_lifetime():
    rule = '/rules/tests/run_test.sh -r get_temporary_password_lifetime'
    ret = subprocess.check_output(rule, shell=True)

    ttl = json.loads(ret)
    assert isinstance(ttl, int)
    assert ttl > 0


def test_get_user_admin_status():
    rule = '/rules/tests/run_test.sh -r get_user_admin_status -a "jmelius"'
    ret = subprocess.check_output(rule, shell=True)

    is_admin = json.loads(ret)
    assert isinstance(is_admin, bool)
    assert is_admin is True


def test_get_user_attribute_value():
    rule = '/rules/tests/run_test.sh -r get_user_attribute_value -a "jmelius,eduPersonUniqueID,false"'
    ret = subprocess.check_output(rule, shell=True)

    avu = json.loads(ret)
    assert avu["value"] == "jmelius@sram.surf.nl"


def test_get_user_group_memberships():
    rule = '/rules/tests/run_test.sh -r get_user_group_memberships -a "false,pvanschay2"'
    ret = subprocess.check_output(rule, shell=True)

    groups = json.loads(ret)
    assert groups[0]["name"] == "datahub"
    assert groups[0]["displayName"] == "DataHub"
    assert groups[1]["name"] == "m4i-nanoscopy"
    assert groups[1]["displayName"] == "Nanoscopy"


def test_get_user_id():
    rule = '/rules/tests/run_test.sh -r get_user_id -a "jmelius"'
    ret = subprocess.check_output(rule, shell=True)

    user_id = json.loads(ret)
    assert isinstance(user_id, int)


def test_get_user_internal_affiliation_status():
    rule = '/rules/tests/run_test.sh -r get_user_internal_affiliation_status -a "jmelius"'
    ret = subprocess.check_output(rule, shell=True)

    is_internal = json.loads(ret)
    assert isinstance(is_internal, bool)
    assert is_internal is True


def test_get_user_metadata():
    rule = '/rules/tests/run_test.sh -r get_user_metadata -a "auser"'
    ret = subprocess.check_output(rule, shell=True)

    user = json.loads(ret)
    assert user["username"] == "auser"
    assert user["givenName"] == "Additional"
    assert user["familyName"] == "User newly created in LDAP"
    assert user["displayName"] == "Additional User newly created in LDAP"
    assert user["email"] == "auser"


def test_get_user_or_group_by_id():
    rule = '/rules/tests/run_test.sh -r get_user_or_group_by_id -a "10001"'
    ret = subprocess.check_output(rule, shell=True)

    group = json.loads(ret)
    assert group["account_type"] == "rodsgroup"
    assert group["groupName"] == "rodsadmin"
    assert group["displayName"] == "rodsadmin"
    assert group["groupId"] == "10001"
    assert group["description"] == ""


def test_get_set_user_attribute_value():
    username = "jmelius"
    attribute = "foo"
    value = "bar"

    rule = '/rules/tests/run_test.sh -r set_user_attribute_value -a "{},{},{}"'.format(username, attribute, value)
    subprocess.check_output(rule, shell=True)

    rule = '/rules/tests/run_test.sh -r get_user_attribute_value -a "{},{},false"'.format(username, attribute)
    ret = subprocess.check_output(rule, shell=True)

    avu = json.loads(ret)
    assert avu["value"] == value

    # clean up
    cmd = 'imeta rm -u {} {} {}'.format(username, attribute, value)
    subprocess.check_output(cmd, shell=True)
