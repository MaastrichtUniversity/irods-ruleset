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
# A local source install reinstalls the ruleset even when its version is unchanged.
# Build the selected utility tag before replacing the installed utility package.
pip-install:
	echo "from datahubirodsruleset import *\n" > /etc/irods/core.py
	set -e; tmpdir="$$(mktemp -d /tmp/datahub-irods-ruleset.XXXXXX)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	cp -a . "$$tmpdir/src"; \
	rm -rf "$$tmpdir/src/build" "$$tmpdir/src/datahub_irods_ruleset.egg-info"; \
	(cd "$$tmpdir/src" && python3 setup.py egg_info); \
	utils_requirement="$$(grep '^dh-python-irods-utils[[:space:]@]' "$$tmpdir/src/datahub_irods_ruleset.egg-info/requires.txt")"; \
	pip3 wheel --no-deps --wheel-dir "$$tmpdir/wheels" "$$utils_requirement"; \
	pip3 install --user --no-deps --force-reinstall "$$tmpdir"/wheels/dh_python_irods_utils-*.whl $(PIP_BREAK_FLAG) --no-warn-script-location; \
	pip3 install --user "$$tmpdir/src" $(PIP_BREAK_FLAG) --no-warn-script-location

.PHONY: subdirs $(RULEDIRS)
.PHONY: all
