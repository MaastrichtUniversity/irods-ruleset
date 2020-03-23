# Call with
# irule -s -F requestExportProjectCollection.r *message='{"project": "P000000014", "collection": "C000000001"}' \
#   *project='P000000014'  *collection='C000000001' *repository='Dataverse' \
#   *amqpHost='rabbitmq' *amqpPort=5672 *amqpUser='user' *amqpPass='password'
#
# This rule creates an AVU called 'exporterState' and sends the message to the amqp queue to be processed by another application
# Make sure to call this rule as 'rodsadmin' because it will open a collection using admin-mode.

irule_dummy() {
    IRULE_requestExportProjectCollection(*message, *project, *collection, *repository, *amqpHost, *amqpPort, *amqpUser, *amqpPass);
}

IRULE_requestExportProjectCollection(*message, *project, *collection, *repository, *amqpHost, *amqpPort, *amqpUser, *amqpPass){
    # Open collection to modify state AVU
    openProjectCollection(*project, *collection, 'rods', 'own');

    # Create state AVU
    *status = *repository ++ ":in-queue-for-export";
    msiAddKeyVal(*metaKV, "exporterState", *status);
    msiAssociateKeyValuePairsToObj(*metaKV, "/nlmumc/projects/*project/*collection", "-C");

    # Send the message to the queue and it will be processed by the open access ETL worker
    # Arguments: msi_amqp_basic_publish(hostname, port, user, password, exchange, routing_key, message)
    msi_amqp_basic_publish(*amqpHost, int(*amqpPort), *amqpUser, *amqpPass, "datahub.events_tx", "projectCollection.exporter.requested", *message );
}


INPUT *message='', *project='', *collection='', *repository='', *amqpHost='', *amqpPort='', *amqpUser='',  *amqpPass=''
OUTPUT ruleExecOut