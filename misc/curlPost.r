
# Call with
#
# irule -F /rules/misc/curlPost.r "*url='http://httpbin.org/post'" "*data='Sent from iRODS'"
                      

irule_dummy() {
    IRULE_curlPost(*url, *data, *response);
    writeLine("stdout", "server response: "++*response);
}

IRULE_curlPost(*url, *data, *response) {
    *postFields."data" = *data
    msiCurlPost(*url, *postFields, *response);
}


INPUT *url='',*data=''
OUTPUT ruleExecOut

