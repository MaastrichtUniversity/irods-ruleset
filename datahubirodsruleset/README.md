# datahub-irods-ruleset


DataHub iRODS python ruleset package


## Usage

Individual rule files can be run using the ``run_test`` bash script. For example:

```bash
/rules/tests/run_test.sh -r get_project_details -a "/nlmumc/projects/P000000001,false" -u jmelius -j
```
See ``tests/README.md`` for more details


## Installation

This package needs to be installed as the irods user.
It can be done by executing the Makefile, it will take care of the pip install from the local source files.

Inside the docker container:
```bash
su irods
cd /rules && make
``` 
Outside the docker container:
```bash
docker exec -it --user irods corpus_icat_1 make -C /rules
``` 

The iRODS Python Rule Engine Plugin expects the rules in ``/etc/irods/core.py`` 
``core.py`` only contains a single import for this package:
```python
from datahubirodsruleset import *
```


## Create a new rule

1. Define the content of the rule in a new function, preferably in a new file and maybe new sub-package
2. Decorate the new function with the Yoda rule decorator. e.g: create a new rule ``get_project_details`` in the sub-package ``projects``
```python
# datahubirodsruleset.projects.get_project_details
from datahubirodsruleset.decorator import make, Output

@make(inputs=[0, 1], outputs=[2], handler=Output.STORE)
def get_project_details(ctx, project_path, show_service_accounts):
    ...
```
3. Make sure the function/rule is imported into the package namespace. e.g:
```python
# Add this line in datahubirodsruleset.projects.__init__ 
from datahubirodsruleset.projects.get_project_details import get_project_details
```
```python
# Add this line in datahubirodsruleset.__init__ 
from datahubirodsruleset.projects import *
```
During runtime, all the rules need to be available to the  iRODS Python Rule Engine Plugin.


## Public/Private label

Inside the (sub-)package `__init__` file, a rule can be listed either below the public or private comments.
This is ONLY a label, all server rules can be executed by irods clients, e.g: icommands, python-irods-client, etc ... 
 * Public:
This label indicates the rule is safe to be executed by irods clients

 * Private:
This label indicates the rule is usually only called by other rules and/or is not safe to be executed by irods clients, because it is part of a larger workflow (ingest, tape)


## Acknowledgements

* Special thanks to [Utrecht University](https://github.com/UtrechtUniversity) for inspiration on this [package](https://utrechtuniversity.github.io/yoda/design/other/python-plugin.html) and the [Yoda rule decorator](https://github.com/UtrechtUniversity/yoda-ruleset/blob/development/util/rule.py) 
