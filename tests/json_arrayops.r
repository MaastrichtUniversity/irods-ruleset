# Simple rule to test microservice
#
# Call with
#
# irule -F json_arrayops.r

irule_dummy() {
    writeLine("stdout", "Testing msi_json_arrayops ...");
    IRULE_msi_json_arrayops_test();
}

IRULE_msi_json_arrayops_test {

   *json_str = '[]';

   *item1 = 'test & and %';
   *item2 = 'U123456-ru.nl';
   *item3 = '{"type":"PMID","id":"12345"}';
   *item4 = '{"type":"arXiv","id":"xyz/abc"}';
   *item5 = 'null';
   *item6 = 'true';
   *item7 = 'false';
   *item8 = '["DICOM","test"]';

    ## build JSON array
   *size = 0;
   *ec = errorcode( msi_json_arrayops(*json_str, *item1, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item2, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item3, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item4, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item8, "add", *size) );
   writeLine("stdout", "Check 1: adding new values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *size");

   # adding 'null' is not supported and will not extend the JSON array
   *ec = errorcode( msi_json_arrayops(*json_str, *item5, "add", *size) );
   writeLine("stdout", "Check 2: adding 'null' value to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *size");

   # adding those will append additional boolean values to array
   *ec = errorcode( msi_json_arrayops(*json_str, *item6, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item7, "add", *size) );
   writeLine("stdout", "Check 3: adding boolean values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *size");

   # adding those will not change array because they are already present in it
   *ec = errorcode( msi_json_arrayops(*json_str, *item1, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item2, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item3, "add", *size) );
   *ec = errorcode( msi_json_arrayops(*json_str, *item4, "add", *size) );
   writeLine("stdout", "Check 4: adding pre-existing values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *size");

   # size operation
   *idx = 0;
   *ec = errorcode( msi_json_arrayops(*json_str, "", "size", *idx) );
   writeLine("stdout", "Check 9: Determine size of JSON array. Outcome:");
   writeLine("stdout", "    *json_str max idx: *idx");

   # get operation
   *idx = 2;
   *item11 = "";
   *ec = errorcode( msi_json_arrayops(*json_str, *item11, "get", *idx) );
   writeLine("stdout", "Check 10: Get an object from the JSON array. Outcome:");
   writeLine("stdout", "    *json_str value '*item11' retrieved from idx: *idx");


   writeLine("stdout", "\n");
   writeLine("stdout", "\n");
   writeLine("stdout", "\n");
   writeLine("stdout", "\n");

   *json_str = '[]';
   *output = "";
   json_arrayops_add(*json_str, *item1 , *output );
   json_arrayops_add(*json_str, *item2 , *output );
   json_arrayops_add(*json_str, *item3 , *output );
   json_arrayops_add(*json_str, *item4 , *output );
   json_arrayops_add(*json_str, *item8 , *output );
   writeLine("stdout", "Check 1: adding new values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size:  *output ");

    *test = *output

    if (int(*test) == 5){
        writeLine("stdout", "TEST SUCCESS FULL");
    }


   # adding 'null' is not supported and will not extend the JSON array
   json_arrayops_add(*json_str, *item5 , *output );
   writeLine("stdout", "Check 2: adding 'null' value to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *output");

   # adding those will append additional boolean values to array
   json_arrayops_add(*json_str, *item6 , *output );
   json_arrayops_add(*json_str, *item7 , *output );
   writeLine("stdout", "Check 3: adding boolean values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *output");

   # adding those will not change array because they are already present in it
   json_arrayops_add(*json_str, *item1 , *output );
   json_arrayops_add(*json_str, *item2 , *output );
   json_arrayops_add(*json_str, *item3 , *output );
   json_arrayops_add(*json_str, *item4 , *output );
   writeLine("stdout", "Check 4: adding pre-existing values to JSON array. Outcome:");
   writeLine("stdout", "    *json_str size: *output");

   # size operation
   json_arrayops_size(*json_str, *output);
   writeLine("stdout", "Check 9: Determine size of JSON array. Outcome:");
   writeLine("stdout", "    *json_str max idx: *output");

   # get operation
   *idx = "2";
   *item11 = "";
   json_arrayops_get(*json_str, *idx , *item11 );
   writeLine("stdout", "Check 10: Get an object from the JSON array. Outcome:");
   writeLine("stdout", "    *json_str value '*item11' retrieved from idx: *idx");


}

OUTPUT ruleExecOut
