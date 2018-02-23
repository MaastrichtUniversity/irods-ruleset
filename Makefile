# The rule dirs to be processed
RULEDIRS = ingest misc projects projectCollection

# The make target
all: $(RULEDIRS)
$(RULEDIRS):
	$(MAKE) -C $(@:build-%=%)

# The install target
install: $(RULEDIRS)
$(RULEDIRS):
	$(MAKE) -C $(@:install-%=%) install

.PHONY: subdirs $(RULEDIRS)
.PHONY: all