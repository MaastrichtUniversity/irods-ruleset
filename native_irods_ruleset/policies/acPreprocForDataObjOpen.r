# Gets fired before accessing a file
acPreprocForDataObjOpen {
  # Disallow downloading files that are on tape
  if ($writeFlag == "0" && $rescName == "arcRescSURF01" && $userNameClient != "service-surfarchive") {
    cut;
    msiOprDisallowed;
  }
}
