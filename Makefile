# Makefile to build and install the iRODS ruleset
#
#   make - 1) combine rules and copy it to the "/etc/irods" dir
#          2) (Re-)Install the package datahub-irods-ruleset for the irods user
#

# The rule dirs to be processed
RULEDIRS = native_irods_ruleset

# --break-system-packages is only available from pip >= 22.3 (absent on older Ubuntu 22.04 installs)
PIP_BREAK_FLAG := $(shell pip3 install --help 2>&1 | grep -q break-system-packages && echo --break-system-packages)

# The make target
all: $(RULEDIRS) pip-install

$(RULEDIRS):
	$(MAKE) -C $(@:build-%=%)

# pip install the DataHub iRODS ruleset
pip-install:
	echo "from datahubirodsruleset import *\n" > /etc/irods/core.py
	pip3 uninstall -y dh-python-irods-utils $(PIP_BREAK_FLAG)
	tmpdir="$$(mktemp -d /tmp/datahub-irods-ruleset.XXXXXX)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	cp -a . "$$tmpdir/src"; \
	rm -rf "$$tmpdir/src/build" "$$tmpdir/src/datahub_irods_ruleset.egg-info"; \
	pip3 install --user "$$tmpdir/src" $(PIP_BREAK_FLAG) --no-warn-script-location

.PHONY: subdirs $(RULEDIRS)
.PHONY: all
