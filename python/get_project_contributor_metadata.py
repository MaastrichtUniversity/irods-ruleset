@make(inputs=[0], outputs=[1], handler=Output.STORE)
def get_project_contributors_metadata(ctx, project_id):
    project_path = "/nlmumc/projects/{}".format(project_id)
    project = {"principalInvestigator": ctx.callback.getCollectionAVU(project_path, "OBI:0000103", "", "", "true")[
        "arguments"
    ][2]}
    ret = ctx.get_username_attribute_value(project["principalInvestigator"], "email", "result")["arguments"][2]
    project["principalInvestigatorEmail"] = json.loads(ret)["value"]
    ret = ctx.get_username_attribute_value(project["principalInvestigator"], "displayName", "result")["arguments"][2]
    project["principalInvestigatorDisplayName"] = json.loads(ret)["value"]
    pi_split_display_name = project["principalInvestigatorDisplayName"].split(" ")
    project["principalInvestigatorGivenName"] = pi_split_display_name[0]
    project["principalInvestigatorFamilyName"] = pi_split_display_name[1]

    project["dataSteward"] = ctx.callback.getCollectionAVU(project_path, "dataSteward", "", "", "true")["arguments"][2]
    ret = ctx.get_username_attribute_value(project["dataSteward"], "email", "result")["arguments"][2]
    project["dataStewardEmail"] = json.loads(ret)["value"]
    ret = ctx.get_username_attribute_value(project["dataSteward"], "displayName", "result")["arguments"][2]
    project["dataStewardDisplayName"] = json.loads(ret)["value"]
    ds_split_display_name = project["dataStewardDisplayName"].split(" ")
    project["dataStewardGivenName"] = ds_split_display_name[0]
    project["dataStewardFamilyName"] = ds_split_display_name[1]

    return project
