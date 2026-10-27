# irods-ruleset

The rulesets for the DataHub iRODS installation

## Usage
Individual rule files can be run using irule. For example:

```bash
irule -F misc/getUsers.r "*showServiceAccounts='true'"

``` 

### irule_dummy
All rule files contain a irule_dummy() rule as first rule. This function is called 
by the irule command. During installaton to a ruleset this irule_dummy() function is stripped 
away (see below).

## Installation
The included makefile will strip away comments, remove the irule_dummy(), and remove the 
INPUT/OUTPUT lines. It will then place the resulting .re file in /etc/irods.

Inside an iRODS container, run `make` in `/rules` to install the native rules and
the Python ruleset. The Python package is installed from a temporary source copy,
so changes are reinstalled even when the package version is unchanged.

For `dh-python-irods-utils`, the Git requirement is read from the package metadata
generated from `setup.py`. Its wheel is built while the installed utility package
remains available, then force reinstalled without reinstalling its dependencies.
This applies changes to the selected Git tag even if the utility package's Python
version is unchanged. A failed wheel build stops installation and leaves the
installed utility package in place.

This avoids leaving iRODS without its utility dependency during the build, but
does not make updates atomic: pip still replaces Python packages, native rule
files are copied separately, and running Python processes may retain imported code.
Updates during an ingest are therefore not guaranteed to be disruption-free.

This destination directory can be overridden

```bash
mkdir /tmp/foo
make RULES_DEST=/tmp/foo
```  