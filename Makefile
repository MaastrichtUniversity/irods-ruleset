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
	pip3 uninstall -y dh-python-irods-utils --break-system-packages
	tmpdir="$$(mktemp -d /tmp/datahub-irods-ruleset.XXXXXX)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	cp -a . "$$tmpdir/src"; \
	rm -rf "$$tmpdir/src/build" "$$tmpdir/src/datahub_irods_ruleset.egg-info"; \
	pip3 install --user "$$tmpdir/src" --break-system-packages --no-warn-script-location

.PHONY: subdirs $(RULEDIRS)
.PHONY: all
