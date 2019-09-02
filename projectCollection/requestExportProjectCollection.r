# Call with
# irule -s -F requestExportProjectCollection.r *message='{"project": "P000000001", "collection": "C000000012"}' \
#   *collection='/nlmumc/projects/P000000014/C000000001' *repository='Dataverse' \
#   *amqpHost='rabbitmq' *amqpPort=5672 *amqpUser='user'  *amqpPass='password'
#
# Update exporterState AVU and send message to the queue to be process




irule_dummy() {
    IRULE_requestExportProjectCollection(*message, *collection, *repository, *amqpHost, *amqpPort, *amqpUser, *amqpPass);
}

IRULE_requestExportProjectCollection(*message, *collection, *repository, *amqpHost, *amqpPort, *amqpUser, *amqpPass){
    *status = *repository ++ ":in-queue-for-export";
    msiAddKeyVal(*metaKV, "exporterState", *status);
    msiAssociateKeyValuePairsToObj(*metaKV, *collection, "-C");
    # hostname, port, user, password, exchange, routing_key, message
    msi_amqp_basic_publish(*amqpHost, int(*amqpPort), *amqpUser, *amqpPass, "datahub.events_tx", "projectCollection.exporter.requested", *message );
}


INPUT *message='', *collection='', *repository='', *amqpHost='', *amqpPort='', *amqpUser='',  *amqpPass=''
OUTPUT ruleExecOut