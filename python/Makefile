# Makefile to build and install the iRODS ruleset
#
#   make - 1) combine rules and 2) copy rules and assets to the "/etc/irods" dir
#

# Input files.

RULE_FILES = $(wildcard *.py)
# Filter out core.py to be able to position it first during the concatenation
FILTER := $(filter-out core.py,$(RULE_FILES))
ASSETS_SRC = assets/

# Output files.

RULESET_NAME = core.py
RULES_DEST ?= /etc/irods
RULESET_FILE := $(RULES_DEST)/$(RULESET_NAME)
ASSETS_DST := $(RULES_DEST)/${ASSETS_SRC}

# Make targets.

all: $(RULESET_FILE) $(ASSETS_DST)


$(RULESET_FILE): $(FILTER)
    # Concatenate all *.py with core.py on the first position
	cat core.py $(FILTER) > $(RULESET_FILE)

$(ASSETS_DST):
 	# Copy assets files
	cp -ra $(ASSETS_SRC) $(ASSETS_DST)

