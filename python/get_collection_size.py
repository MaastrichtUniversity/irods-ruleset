from math import floor
from math import ceil


@make(inputs=[0, 1, 2], outputs=[3], handler=Output.STORE)
def get_collection_size(ctx, collection, unit, round):

    size_bytes = float(ctx.callback.getCollectionAVU(collection, "dcat:byteSize", "", "0", "false")["arguments"][2])

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
        ctx.callback.failmsg(-1, "Invalid input for 'unit'. Options are: B | KiB | MiB | GiB | TiB")

    # Do the rounding
    if round == "none":
        size = size
    elif round == "floor":
        size = floor(size)
    elif round == "ceiling":
        size = ceil(size)
    else:
        ctx.callback.failmsg(-1, "Invalid input for 'round'. Options are: none | floor | ceiling")

    return size
