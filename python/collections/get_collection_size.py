# /rules/tests/run_test.sh -r get_collection_size -a "/nlmumc/projects/P000000028/C000000001,B,floor" -j
@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_collection_size(ctx, project_collection_path, unit, round):
    """
    Get the collection's size. The returned value can be formatted by unit and rounded.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    project_collection_path: str
        Project collection absolute path
    unit: str
        Format the size to the correct unit: B, KiB, GiB, TiB
    round: str
        none, floor, ceiling

    Returns
    -------
    float
        The collection's size
    """
    from math import floor
    from math import ceil

    size_bytes = float(ctx.callback.getCollectionAVU(project_collection_path, "dcat:byteSize", "", "0", FALSE_AS_STRING)["arguments"][2])

    if unit == "B":
        size = size_bytes
    elif unit == "KiB":
        size = size_bytes / 1024
    elif unit == "MiB":
        size = size_bytes / 1024 / 1024
    elif unit == "GiB":
        size = size_bytes / 1024 / 1024 / 1024
    elif unit == "TiB":
        size = size_bytes / 1024 / 1024 / 1024
    else:
        ctx.callback.msiExit("-1", "Invalid input for 'unit'. Options are: B | KiB | MiB | GiB | TiB")

    # Do the rounding
    if round == "none":
        size = size
    elif round == "floor":
        size = floor(size)
    elif round == "ceiling":
        size = ceil(size)
    else:
        ctx.callback.msiExit("-1", "Invalid input for 'round'. Options are: none | floor | ceiling")

    return size
