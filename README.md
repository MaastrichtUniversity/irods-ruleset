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

This destination directory can be overridden

```bash
mkdir /tmp/foo
make RULES_DEST=/tmp/foo
```  