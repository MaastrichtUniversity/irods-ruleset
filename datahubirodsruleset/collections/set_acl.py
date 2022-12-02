# /rules/tests/run_test.sh -r set_acl -a "default,admin:own,jmelius,/nlmumc/projects/P000000028/C000000001"
from datahubirodsruleset.decorator import make, Output


@make(inputs=range(4), outputs=[], handler=Output.STORE)
def set_acl(ctx, mode, access_level, username, irods_collection_path):
    """
    Set the ACL of a given collection

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.
    mode : str
        'default', 'recursive' expected values
    access_level : str
        access level: 'own', 'write', 'read'. Add the prefix 'admin:' to set the ACL as an admin; e.g: 'admin:own'
    username : str
        The username
    irods_collection_path : str
        The absolute path of the collection
    """
    ctx.callback.msiSetACL(mode, access_level, username, irods_collection_path)
