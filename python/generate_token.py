from random import randrange

TOKEN_FORMAT = '{}-{}'

@make(inputs=[], outputs=[0], handler=Output.STORE)
def generate_token(ctx):
    """
    Generates a new, unused dropzone token.

    Parameters
    ----------
    ctx : Context
        Combined type of a callback and rei struct.

    Returns
    -------
    string
        The requested new DZ-token
    """
    adjectives_file = open('/rules/python/assets/adjectives.txt', 'r')
    nouns_file = open('/rules/python/assets/nouns.txt', 'r')
    adjectives = adjectives_file.read().split('\n')
    nouns = nouns_file.read().split('\n')

    existing_tokens = []
    for row in row_iterator("COLL_NAME",
                                  "COLL_PARENT_NAME = '/nlmumc/ingest/zones'",
                                  AS_LIST,
                                  ctx.callback):
        existing_tokens.append(row[0][21:])

    token = random_token(adjectives, nouns, existing_tokens)
    return token

def random_token(adjectives, nouns, existing_tokens):
    chosen_adjective = adjectives[randrange(0, len(adjectives) - 1)]
    chosen_noun = nouns[randrange(0, len(nouns) - 1)]
    new_token = TOKEN_FORMAT.format(chosen_adjective, chosen_noun)
    # If the newly generated token already exists, call this function again
    if new_token in existing_tokens:
        random_token(adjectives, nouns, existing_tokens)

    return new_token
