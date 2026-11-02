# /rules/tests/run_test.sh -r get_project_usage_report
from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


from datahubirodsruleset.decorator import make, Output


@make(inputs=[], outputs=[0], handler=Output.STORE)
def get_project_usage_report(ctx):
    """
    OPS report rule.
    HAS TO BE CALLED AS RODSADMIN.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    List
        The resources that data is stored on and the amount of data stored on them.
        This includes replicated resources (so that amount is already doubled!)
    """
    project_metadata = {}
    for project_path, in row_iterator(
        "COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback
    ):
        project_metadata[project_path] = {}

    if not project_metadata:
        return []

    # Fetch the required AVUs once for all projects, rather than fetching all
    # project metadata four times per project through getCollectionAVU.
    for project_path, attribute, value in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "COLL_PARENT_NAME = '/nlmumc/projects' AND "
        "META_COLL_ATTR_NAME in ('responsibleCostCenter','dataSteward','title','OBI:0000103')",
        AS_LIST,
        ctx.callback,
    ):
        if project_path in project_metadata:
            project_metadata[project_path][attribute] = value

    projects = {
        path: get_project_details(ctx, path, metadata)
        for path, metadata in project_metadata.items()
    }
    resource_prices = get_prices_of_resources(ctx)
    resources = {
        resource_id: name
        for name, resource_id in row_iterator("RESC_NAME, RESC_ID", "", AS_LIST, ctx.callback)
    }

    # Only the per-resource byte counts are needed here. The collection-size
    # rule also queries totals and calculates percentages for every project.
    for collection_path, attribute, size in row_iterator(
        "COLL_NAME, META_COLL_ATTR_NAME, META_COLL_ATTR_VALUE",
        "META_COLL_ATTR_NAME like 'dcat:byteSize_resc%' AND COLL_NAME like '/nlmumc/projects/%/%'",
        AS_LIST,
        ctx.callback,
    ):
        project_path = "/".join(collection_path.split("/")[:4])
        if project_path not in projects:
            continue
        resource_name = resources[attribute.removeprefix("dcat:byteSize_resc_")]
        storage = projects[project_path]["storage"]
        if resource_name not in storage:
            storage[resource_name] = {"size": 0}
        storage[resource_name]["size"] += int(size)

    return format_output([
        get_cost_of_project(project, resource_prices) for project in projects.values()
    ])


def get_prices_of_resources(ctx):
    resource_prices = {}
    for result in row_iterator(
        "RESC_ID,RESC_NAME,META_RESC_ATTR_NAME,META_RESC_ATTR_VALUE",
        "META_RESC_ATTR_NAME = 'NCIT:C88193'",
        AS_LIST,
        ctx.callback,
    ):
        resource_prices[result[1]] = result[3]

    return resource_prices


def get_cost_of_project(project_dict, resource_prices):
    import copy

    dict_copy = copy.deepcopy(project_dict["storage"])
    for key, value in dict_copy.items():
        cost_per_year = (
            float(value["size"]) / 1000 / 1000 / 1000 * float(resource_prices[key])
        )
        project_dict["storage"][key]["cost_per_year"] = round(cost_per_year, 2)
        project_dict["storage"][key]["cost_per_month"] = round(cost_per_year / 12, 2)
    return project_dict


def get_project_details(ctx, project_path, metadata):
    project_id = formatters.get_project_id_from_project_path(project_path)

    # Preserve getCollectionAVU's fatal behavior for missing or empty values.
    for attribute in ("responsibleCostCenter", "dataSteward", "title", "OBI:0000103"):
        if metadata.get(attribute, "") == "":
            ctx.callback.msiExit(
                "-1", f"ERROR: The attribute '{attribute}' of collection '{project_path}' has no value in iCAT"
            )

    return {
        "id": project_id,
        "title": metadata["title"],
        "data_steward": metadata["dataSteward"],
        "budget_number": metadata["responsibleCostCenter"],
        "principal_investigator": metadata["OBI:0000103"],
        "storage": {},
    }


def format_output(output):
    result = []
    for project in output:
        for resource, value in project["storage"].items():
            result.append(
                {
                    "budget_number": project["budget_number"],
                    "data_steward": project["data_steward"],
                    "principal_investigator": project["principal_investigator"],
                    "id": f"{project['id']}_{resource}",
                    "project_id": project["id"],
                    "title": project["title"],
                    "resource": {
                        "cost_per_month": value["cost_per_month"],
                        "cost_per_year": value["cost_per_year"],
                        "size": value["size"],
                        "resource": resource
                    }
                }
            )
    return result
