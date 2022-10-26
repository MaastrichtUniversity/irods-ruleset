# Makefile to build and install the iRODS ruleset
#
#   make - combine rules and copy it to the "/etc/irods" dir
#

# The rule dirs to be processed
RULEDIRS = ingest misc policies projects projectCollection tapeArchive python

# The make target
all: $(RULEDIRS)

$(RULEDIRS):
	$(MAKE) -C $(@:build-%=%)

.PHONY: subdirs $(RULEDIRS)
.PHONY: all
