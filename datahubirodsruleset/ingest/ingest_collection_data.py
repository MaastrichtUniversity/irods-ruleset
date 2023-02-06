import irods_types  # pylint: disable=import-error

from dhpythonirodsutils.enums import ProjectAVUs
from genquery import row_iterator, AS_LIST  # pylint: disable=import-error

from datahubirodsruleset.decorator import make, Output
from datahubirodsruleset.formatters import format_project_path
from datahubirodsruleset.utils import TRUE_AS_STRING


@make(inputs=range(3), outputs=[3], handler=Output.STORE)
def ingest_collection_data(ctx, source_collection, destination_collection, project_id):
    """
     Ingest the input source collection toward the destination collection.
     Ingest:
         * Check the destination collection replica in case of retry
         * Create the destination collection sub-folders, if required
         * Rename individually each files inside the source collection to the destination collection
             - Not renaming the whole source collection to preserve the dropzone folder and its AVU (e.g:state, etc ...)
         * Replicate each files inside the destination collection to the project resource
         * Trim each files original replica at the input ingest resource

     Parameters
     ----------
     ctx : Context
         Combined type of callback and rei struct.
     source_collection: str
         The absolute path of the source collection/dropzone
     destination_collection: str
         The absolute path of the destination project collection
     project_id: str
         The project id, e.g: P00000010

    Returns
     -------
     int
         The sum of the ingestion status codes. 0 is success.
    """
    project_path = format_project_path(ctx, project_id)
    destination_resource = ctx.callback.getCollectionAVU(
        project_path, ProjectAVUs.RESOURCE.value, "", "", TRUE_AS_STRING
    )["arguments"][2]

    # TODO Change to query instead of hardcoded ingest_resource value?
    ingest_resource = "stagingResc01"
    ingest_manager = CollectionIngestManager()
    ctx.callback.msiWriteRodsLog(
        "INFO: Start replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )
    replicate_status = ingest_manager.check_collection_replication(ctx, destination_collection, destination_resource)
    trim_status = ingest_manager.check_collection_trim(ctx, destination_collection, ingest_resource)

    ingest_manager.create_destination_collection_sub_folders(ctx, source_collection, destination_collection)
    source_collection_status = ingest_manager.do_ingest_collection_data(
        ctx, source_collection, destination_collection, ingest_resource, destination_resource
    )
    ctx.callback.msiWriteRodsLog("INFO: \t\tRetry replicate_status: {}".format(str(replicate_status)), 0)
    ctx.callback.msiWriteRodsLog("INFO: \t\tRetry trim_status: {}".format(str(trim_status)), 0)
    ctx.callback.msiWriteRodsLog("INFO: \t\tsource_collection_status: {}".format(str(source_collection_status)), 0)
    ctx.callback.msiWriteRodsLog(
        "INFO: End replication from '{}' to '{}'".format(source_collection, destination_collection), 0
    )

    return replicate_status + trim_status + source_collection_status


class CollectionIngestManager:
    def do_ingest_collection_data(
        self, ctx, source_collection, destination_collection, ingest_resource, destination_resource
    ):
        """
        Query the source collection to list all the data files and call the following operations for each of them:
            * rename_collection_data
            * calculate_checksum_collection_data
            * replicate_collection_data
            * trim_collection_data

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        source_collection: str
            The absolute path of the source collection/dropzone.
        destination_collection: str
            The absolute path of the destination project collection.
        ingest_resource: str
            The resource name where the data are before the ingestion.
        destination_resource: str
            The resource name where to replicate the data during the ingestion.

        Returns
        -------
        int
            The sum of the ingestion status codes. 0 is success.
        """
        rename_status = 0
        replicate_status = 0
        trim_status = 0
        checksum_status = 0

        # This query get all the sub-files inside the collection
        query_iter = row_iterator(
            "DATA_NAME, COLL_NAME", "COLL_NAME like '{}%'".format(source_collection), AS_LIST, ctx.callback
        )
        for row in query_iter:
            source_file_name = row[0]
            source_file_base_path = row[1]
            source_file_full_path = source_file_base_path + "/" + source_file_name

            # Build destination paths. Example:
            # source_file_base_path = /nlmumc/ingest/direct/crazy-frog/sub1
            # source_collection = /nlmumc/ingest/direct/crazy-frog
            # sub_folder_path = /sub1
            sub_folder_path = source_file_base_path.replace(source_collection, "")
            destination_file_base_path = destination_collection + sub_folder_path
            destination_file_full_path = destination_file_base_path + "/" + source_file_name

            # Move the file to the destination location
            rename_status += self.rename_collection_data(ctx, source_file_full_path, destination_file_full_path)

            # Calculate the checksum value of the current data file
            checksum_status += self.calculate_checksum_collection_data(ctx, destination_file_full_path)

            # Replicate to the project resource
            replicate_status += self.replicate_collection_data(ctx, destination_file_full_path, destination_resource)

            # Trim original ingest replica
            trim_status += self.trim_collection_data(ctx, destination_file_full_path, ingest_resource)

        return rename_status + checksum_status + replicate_status + trim_status

    @staticmethod
    def create_destination_collection_sub_folders(ctx, source_collection, destination_collection):
        """
        Check if the destination collection sub-folders exist. If not, create them.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        source_collection: str
            The absolute path of the source collection/dropzone.
        destination_collection: str
            The absolute path of the destination project collection. e.g: /nlmumc/projects/P00000010/C00000001
        """
        query_iter = row_iterator("COLL_NAME", "COLL_NAME like '{}%'".format(source_collection), AS_LIST, ctx.callback)
        for row in query_iter:
            collection_sub_folder_path = row[0]
            sub_folder_path = collection_sub_folder_path.replace(source_collection, "")
            collection_sub_folder = destination_collection + sub_folder_path

            ctx.callback.msiWriteRodsLog("DEBUG: \tcollection_sub_folder: {}".format(collection_sub_folder), 0)

            if collection_sub_folder != destination_collection + "/":
                try:
                    # Check if the sub-folder exists
                    ctx.callback.msiObjStat(collection_sub_folder, irods_types.RodsObjStat())
                except RuntimeError:
                    ctx.callback.msiWriteRodsLog("DEBUG: \tCreate sub-folder: {}".format(collection_sub_folder), 0)
                    ctx.callback.msiCollCreate(collection_sub_folder, 1, 0)

    @staticmethod
    def rename_collection_data(ctx, source_file_full_path, destination_file_full_path):
        """
        Rename the collection data file from the 'ingest zone' to the 'project zone'.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        source_file_full_path: str
            The absolute path of the source data file. e.g: /nlmumc/ingest/direct/crazy-frog/sub1/foobar.txt
        destination_file_full_path: str
            The absolute path of the destination data file.  e.g: /nlmumc/projects/P00000010/C00000001/sub1/foobar.txt

        Returns
        -------
        int
            The status code of the rename operation. 0 is success.
        """
        rename_status = 1
        try:
            ctx.callback.msiWriteRodsLog(
                "DEBUG: \tRename file '{}' to '{}'".format(source_file_full_path, destination_file_full_path),
                0,
            )
            ret_rename = ctx.callback.msiDataObjRename(source_file_full_path, destination_file_full_path, 0, 0)
            rename_status = int(ret_rename["arguments"][3])
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("ERROR: \tRename failed for: {}".format(destination_file_full_path), 0)
            rename_status = 1
        if rename_status != 0:
            return 1
        return 0

    def check_collection_replication(self, ctx, destination_collection, destination_resource):
        """
        In case of retry, query the destination collection and check if each data files has:
            * a checksum value
            * two replica

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        destination_collection: str
            The absolute path of the destination project collection. e.g: /nlmumc/projects/P00000010/C00000001
        destination_resource: str
            The resource name where to replicate the data during the ingestion.

        Returns
        -------
        int
            The sum of the checksum and replication status codes. 0 is success.
        """
        checksum_status = 0
        replicate_status = 0
        replica_counter = {}
        resource_query_iter = row_iterator(
            "DATA_RESC_HIER, COLL_NAME, DATA_NAME",
            "COLL_NAME like '{}%'".format(destination_collection),
            AS_LIST,
            ctx.callback,
        )
        for row in resource_query_iter:
            file_resource_hierarchy = row[0]
            destination_file_full_path = row[1] + "/" + row[2]
            if destination_file_full_path not in replica_counter:
                replica_counter[destination_file_full_path] = 0
            if destination_resource in file_resource_hierarchy:
                replica_counter[destination_file_full_path] += 1

        for destination_file_full_path in replica_counter:
            if replica_counter[destination_file_full_path] < 2:
                checksum_status += self.calculate_checksum_collection_data(ctx, destination_file_full_path)
                replicate_status += self.replicate_collection_data(
                    ctx, destination_file_full_path, destination_resource
                )

        return replicate_status + checksum_status

    @staticmethod
    def replicate_collection_data(ctx, destination_file_full_path, destination_resource):
        """
        Replicate the input data file to the input resource.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        destination_file_full_path: str
            The absolute path of the destination data file.  e.g: /nlmumc/projects/P00000010/C00000001/sub1/foobar.txt
        destination_resource: str
            The resource name where to replicate the data during the ingestion.

        Returns
        -------
        int
            The replication status code. 0 is success.
        """
        replication_status = 1
        try:
            ctx.callback.msiWriteRodsLog("DEBUG: \tStart replication for: {}".format(destination_file_full_path), 0)
            ret_replication = ctx.callback.msiDataObjRepl(
                destination_file_full_path,
                "destRescName={}++++verifyChksum=".format(destination_resource),
                0,
            )
            replication_status = int(ret_replication["arguments"][2])
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("ERROR: \tReplication failed for: {}".format(destination_file_full_path), 0)
            replication_status = 1
        if replication_status != 0:
            return 1
        return 0

    def check_collection_trim(self, ctx, destination_collection, ingest_resource):
        """
        In case of retry, query the destination collection and check if each data files has still a replica at
        the ingestion resource.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        destination_collection: str
            The absolute path of the destination project collection. e.g: /nlmumc/projects/P00000010/C00000001
        ingest_resource: str
            The resource name where the data are before the ingestion.

        Returns
        -------
        int
            The trim status code. 0 is success.
        """
        trim_status = 0
        resource_query_iter = row_iterator(
            "COLL_NAME, DATA_NAME",
            "COLL_NAME like '{}%' AND DATA_RESC_NAME = '{}'".format(destination_collection, ingest_resource),
            AS_LIST,
            ctx.callback,
        )
        for row in resource_query_iter:
            data_path = row[0] + "/" + row[1]
            trim_status += self.trim_collection_data(ctx, data_path, ingest_resource)

        return trim_status

    @staticmethod
    def trim_collection_data(ctx, destination_file_full_path, ingest_resource):
        """
        Trim the input data file of the input resource.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        destination_file_full_path: str
            The absolute path of the destination data file.  e.g: /nlmumc/projects/P00000010/C00000001/sub1/foobar.txt
        ingest_resource: str
            The resource name where the data are before the ingestion.

        Returns
        -------
        int
            The trim status code. 0 is success.
        """
        trim_status = 1
        try:
            ctx.callback.msiWriteRodsLog("DEBUG: \tStart to trim for: {}".format(destination_file_full_path), 0)
            ret_trim = ctx.callback.msiDataObjTrim(destination_file_full_path, ingest_resource, "null", "2", "null", 0)
            # msiDataObjTrim returns 1 if a replica is trimmed, 0 if nothing trimmed
            trim_status = int(ret_trim["arguments"][5])
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("ERROR: \tTrim failed for: {}".format(destination_file_full_path), 0)
            trim_status = 2
        if trim_status != 1:
            return 1
        return 0

    @staticmethod
    def calculate_checksum_collection_data(ctx, destination_file_full_path):
        """
        Run the checksum calculation for the input data file.

        Parameters
        ----------
        ctx : Context
            Combined type of callback and rei struct.
        destination_file_full_path: str
            The absolute path of the destination data file.  e.g: /nlmumc/projects/P00000010/C00000001/sub1/foobar.txt

        Returns
        -------
        int
            The checksum calculation status code. 0 is success.
        """
        checksum_status = 1
        try:
            ctx.callback.msiWriteRodsLog("DEBUG: \tStart checksum for: {}".format(destination_file_full_path), 0)
            ret_checksum = ctx.callback.msiDataObjChksum(destination_file_full_path, "", 0)
            checksum_status = int(ret_checksum["arguments"][2])
        except RuntimeError:
            ctx.callback.msiWriteRodsLog("ERROR: \tChecksum failed for: {}".format(destination_file_full_path), 0)
            checksum_status = 1
        if checksum_status != 0:
            return 1
        return 0
