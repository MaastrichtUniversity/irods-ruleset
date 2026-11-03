"""Bulk implementation behind list_active_drop_zones and process polling."""
import json

from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.listing_queries import accounts, in_conditions, metadata_for_paths


def _native_value(value):
    # The native JSON helpers interpret scalar strings as JSON, except for
    # explicitly encoded titles. Preserve those public output types.
    try:
        return json.loads(value)
    except ValueError:
        return value


@make(inputs=[0], outputs=[1], handler=Output.STORE)
def list_active_drop_zones(ctx, report):
    return list_drop_zones(ctx, report == "true")[0]


def list_drop_zones(ctx, report=False):
    username = ctx.callback.get_client_username("")["arguments"][0]
    parents = []
    for kind, parent in (("mounted", "/nlmumc/ingest/zones"), ("direct", "/nlmumc/ingest/direct")):
        permitted = ctx.callback.checkDropZoneACL(username, kind, "")["arguments"][2]
        if permitted == "true":
            parents.append(parent)
    if not parents:
        ctx.callback.msiExit(
            "-818000", f"User '{username}' has insufficient DropZone permissions on /nlmumc/ingest/zones"
        )

    rows = []
    for condition in in_conditions("COLL_PARENT_NAME", parents):
        rows.extend(row_iterator(
            "COLL_NAME, order_desc(COLL_MODIFY_TIME), COLL_PARENT_NAME, COLL_CREATE_TIME",
            condition + " AND COLL_ACCESS_NAME = 'own'", AS_LIST, ctx.callback,
        ))
    metadata = metadata_for_paths(ctx, (row[0] for row in rows), ())
    project_paths = [f"/nlmumc/projects/{values['project']}" for values in metadata.values() if values.get("project")]
    projects = metadata_for_paths(ctx, project_paths, ("title", "enableDropzoneSharing", "resource"))
    creators = {}
    for condition in in_conditions("USER_NAME", (values.get("creator", "") for values in metadata.values())):
        creators.update({account["name"]: account["displayName"] for account in accounts(ctx, condition).values()})

    # Report mode historically derives userName from mounted-dropzone ACLs,
    # including when reporting a direct token. Keep that compatibility behavior.
    report_names = {}
    if report:
        acl_rows = []
        for condition in in_conditions("COLL_NAME", ("/nlmumc/ingest/zones/" + row[0].rsplit("/", 1)[1] for row in rows)):
            acl_rows.extend(row_iterator("COLL_NAME, COLL_ACCESS_USER_ID", condition, AS_LIST, ctx.callback))
        report_accounts = {}
        for condition in in_conditions("USER_ID", (row[1] for row in acl_rows)):
            report_accounts.update(accounts(ctx, condition))
        for path, identifier in acl_rows:
            name = report_accounts.get(identifier, {}).get("name", "")
            if name.endswith(("@mumc.nl", "@maastrichtuniversity.nl")):
                report_names.setdefault(path, []).append(name)

    output = []
    for path, modified, parent, created in rows:
        values = metadata.get(path, {})
        project = values.get("project", "")
        project_values = projects.get(f"/nlmumc/projects/{project}", {})
        creator = values.get("creator", "")
        title = values.get("title", "")
        item = {
            "token": path.rsplit("/", 1)[1], "type": "mounted" if parent.endswith("/zones") else "direct",
            "title": title or "no-title-AVU-set", "state": values.get("state") or "no-state-AVU-set",
            "validateState": values.get("validateState") or "N/A", "validateMsg": values.get("validateMsg") or "N/A",
            "project": project or "no-project-AVU-set",
            "projectTitle": project_values.get("title", "") if project else "No-projectTitle-AVU-set",
            "enableDropzoneSharing": project_values.get("enableDropzoneSharing", "") if project else "false",
            "date": modified if values else "", "modifyDate": modified if values else "",
            "creationDate": created if values else "", "totalSize": values.get("totalSize") or "0",
            "destination": values.get("destination", ""), "creator": creators.get(creator) or creator,
            "dropzoneSize": values.get("dropzoneSize") or "0",
            "dropzoneSizeUpdated": values.get("dropzoneSizeUpdated") or "0",
            "sharedWithMe": "false" if username == creator else "true",
        }
        for key in item:
            if key not in ("title", "projectTitle"):
                item[key] = _native_value(item[key])
        if report:
            mounted_path = "/nlmumc/ingest/zones/" + item["token"]
            names = report_names.get(mounted_path, [])
            if not names:
                ctx.callback.msiWriteRodsLog("ERROR: Missing creator for dropzone " + mounted_path, 0)
            elif len(names) > 1:
                ctx.callback.msiWriteRodsLog(
                    "WARNING: list_active_drop_zones found multiple creators for DropZone " + mounted_path +
                    ". Only the first will be displayed in the report", 0,
                )
            item["userName"] = names[-1] if names else "N/A"
        output.append(item)
    return output, projects
