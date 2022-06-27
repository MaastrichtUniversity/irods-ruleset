# Gets fired before accessing a file
acPreprocForDataObjOpen {
  ON($writeFlag == "0") {
    # Disallow downloading files that are on tape
    if ($filePath like regex "/nfs/archivelinks/irmdh.*") {
      cut;
      msiOprDisallowed;
    }
  }
}
