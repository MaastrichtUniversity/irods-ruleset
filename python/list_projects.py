@make(inputs=[], outputs=[0], handler=Output.STORE)
def list_projects(ctx):
    """
        Get a listing of all (authorized) projects

        Parameters
        ----------
        ctx : Context
            Combined type of a callback and rei struct.

        Returns
        -------
        TODO: Update documentation. Will it really return a list?
        list
            a json list of projects objects
        """

    # TODO: do not call reportProjects, but reconstruct the required business logic using smaller rules.
    # value = ""
    # for result in row_iterator("META_USER_ATTR_VALUE",
    #                            "USER_NAME = '{}' AND META_USER_ATTR_NAME = '{}'".format(username, attribute),
    #                            AS_LIST,
    #                            ctx.callback):
    #     value = result[0]



    # Note 1: When calling a rule without input arguments you need to provide a (empty or nonsense) string.
    # Note 2: Retrieving the rule outcome is done with '["arguments"][0]'
    value = ctx.callback.reportProjects("")["arguments"][0]

    return {"value": value}
