# Makefile to build and install the iRODS ruleset
#
#   make - 1) combine rules and copy it to the "/etc/irods" dir
#          2) (Re-)Install the package datahub-irods-ruleset for the irods user
#

# The rule dirs to be processed
RULEDIRS = native_irods_ruleset

# The make target
all: $(RULEDIRS) pip-install

$(RULEDIRS):
	$(MAKE) -C $(@:build-%=%)

# pip install the DataHub iRODS ruleset
pip-install:
	echo "from datahubirodsruleset import *\n" > /etc/irods/core.py
	pip3 uninstall -y dh-python-irods-utils
	pip3 install --user .

.PHONY: subdirs $(RULEDIRS)
.PHONY: all
