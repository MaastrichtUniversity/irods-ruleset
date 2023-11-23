# /rules/tests/run_test.sh -r get_project_usage_report
import json

from dhpythonirodsutils import formatters
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error


from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.utils import FALSE_AS_STRING, TRUE_AS_STRING


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
    output = []

    resource_prices = get_prices_of_resources(ctx)

    for result in row_iterator(
        "COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/projects'", AS_LIST, ctx.callback
    ):
        project_path = result[0]

        project_dict = get_project_details(ctx, project_path)

        collection_size_per_resource = json.loads(
            ctx.callback.get_collection_size_per_resource(project_dict["id"], "")[
                "arguments"
            ][1]
        )
        collections = collection_size_per_resource.values()
        for collection in collections:
            for collection_resource in collection:
                if collection_resource["resourceName"] not in project_dict["storage"]:
                    project_dict["storage"][collection_resource["resourceName"]] = {
                        "size": int(collection_resource["size"])
                    }
                else:
                    project_dict["storage"][collection_resource["resourceName"]][
                        "size"
                    ] += int(collection_resource["size"])

        project_dict = get_cost_of_project(project_dict, resource_prices)
        output.append(project_dict)
    return format_output(output)


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


def get_project_details(ctx, project_path):
    project_id = formatters.get_project_id_from_project_path(project_path)

    budget_number = ctx.callback.getCollectionAVU(
        project_path, "responsibleCostCenter", "", "", TRUE_AS_STRING
    )["arguments"][2]
    data_steward = ctx.callback.getCollectionAVU(
        project_path, "dataSteward", "", "", TRUE_AS_STRING
    )["arguments"][2]
    title = ctx.callback.getCollectionAVU(
        project_path, "title", "", "", TRUE_AS_STRING
    )["arguments"][2]
    principal_investigator = ctx.callback.getCollectionAVU(
        project_path, "OBI:0000103", "", "", TRUE_AS_STRING
    )["arguments"][2]

    return {
        "id": project_id,
        "title": title,
        "data_steward": data_steward,
        "budget_number": budget_number,
        "principal_investigator": principal_investigator,
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
                    "id": "{}_{}".format(project["id"], resource),
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
