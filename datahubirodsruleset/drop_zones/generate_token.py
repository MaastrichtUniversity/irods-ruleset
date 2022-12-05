# /rules/tests/run_test.sh -r generate_token
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output

DROPZONE_NAME_FORMAT = "{}-{}"


@make(inputs=[], outputs=[0], handler=Output.STORE)
def generate_token(ctx):
    """
    Generates a new, unused dropzone token.

    Parameters
    ----------
    ctx : Context
        Combined type of callback and rei struct.

    Returns
    -------
    string
        The requested new DZ-token
    """
    adjectives_file = open("/rules/datahubirodsruleset/assets/adjectives.txt", "r")
    nouns_file = open("/rules/datahubirodsruleset/assets/nouns.txt", "r")
    adjectives = adjectives_file.read().split("\n")
    nouns = nouns_file.read().split("\n")

    existing_tokens = []
    for row in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/ingest/zones'", AS_LIST, ctx.callback):
        existing_tokens.append(row[0][21:])

    for row in row_iterator("COLL_NAME", "COLL_PARENT_NAME = '/nlmumc/ingest/direct'", AS_LIST, ctx.callback):
        existing_tokens.append(row[0][22:])

    token = random_token(adjectives, nouns, existing_tokens)
    return '"' + token + '"'


def random_token(adjectives, nouns, existing_tokens):
    from random import SystemRandom

    sys_rand = SystemRandom()
    chosen_adjective = adjectives[sys_rand.randrange(0, len(adjectives) - 1)]
    chosen_noun = nouns[sys_rand.randrange(0, len(nouns) - 1)]
    new_token = DROPZONE_NAME_FORMAT.format(chosen_adjective, chosen_noun)
    # If the newly generated token already exists, call this function again
    if new_token in existing_tokens:
        random_token(adjectives, nouns, existing_tokens)

    return new_token
