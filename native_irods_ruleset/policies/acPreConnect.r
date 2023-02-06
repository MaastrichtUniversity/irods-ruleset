# Control the SSL requirements for iRODS-connections. The options are:
# "CS_NEG_REFUSE" for no SSL,
# "CS_NEG_REQUIRE" to demand SSL,
# "CS_NEG_DONT_CARE" to allow the server to decide
# Source: https://github.com/irods-contrib/metalnx-web/blob/master/docs/Getting-Started.md#setup-irods-negotiation
acPreConnect(*OUT) { *OUT="CS_NEG_REQUIRE"; }
